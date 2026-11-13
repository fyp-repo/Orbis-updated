"""
OrbisERP Live ERPNext Tools Module
==================================
Secure, read-only ERPNext tool layer for Stock and Purchase operations.
Enforces:
1. Strict Frappe RBAC per user session (never bypasses permissions).
2. Parameter validation and sanitization (no raw SQL/shell/code execution).
3. Live queries against Frappe REST API (no hardcoded sample values).
4. Detailed structured output with human-readable summary for DSPy reasoning.
"""

import json
import logging
import requests
from typing import Any, Dict, List, Optional, Tuple
from app.core.config import settings
from app.core.security import (
    check_user_stock_permission,
    check_user_purchase_permission,
    resolve_active_user_session,
    check_erpnext_user_exists,
)

logger = logging.getLogger("orbis.ai.erp_tools")


def _get_auth_context(
    authenticated_user: str, session_id: Optional[str] = None
) -> Tuple[Dict[str, str], Dict[str, str], Optional[str]]:
    """
    Builds request headers and cookies strictly adhering to user identity.
    Returns: (headers, cookies, error_message)
    """
    headers = {"Content-Type": "application/json"}
    cookies: Dict[str, str] = {}

    # 1. Resolve authentic Frappe session for this user
    user_sid = resolve_active_user_session(authenticated_user, session_id)
    if user_sid:
        cookies["sid"] = user_sid
        return headers, cookies, None

    # 2. Administrator using their own API credentials
    if authenticated_user == "Administrator":
        headers["Authorization"] = f"token {settings.erpnext_api_key}:{settings.erpnext_api_secret}"
        return headers, cookies, None

    # 3. For any other user, shared Administrator token is strictly PROHIBITED
    return (
        headers,
        cookies,
        f"Active ERPNext session required for '{authenticated_user}'. Please log in to authenticate.",
    )


# ==============================================================================
# STOCK TOOLS
# ==============================================================================


def get_stock_balance(
    authenticated_user: str,
    session_id: Optional[str] = None,
    item_code: Optional[str] = None,
    warehouse: Optional[str] = None,
) -> Dict[str, Any]:
    """Retrieves live stock balance (Bin records) for an item and/or warehouse."""
    perm = check_user_stock_permission(authenticated_user)
    if not perm.allowed:
        return {"success": False, "error": "PERMISSION_DENIED", "message": perm.reason}

    headers, cookies, err = _get_auth_context(authenticated_user, session_id)
    if err:
        return {"success": False, "error": "SESSION_REQUIRED", "message": err}

    filters: List[List[Any]] = []
    if item_code and item_code.lower() not in ("none", "null", "all"):
        filters.append(["item_code", "like", f"%{item_code.strip()}%"])
    if warehouse and warehouse.lower() not in ("none", "null", "all"):
        filters.append(["warehouse", "like", f"%{warehouse.strip()}%"])

    params = {
        "fields": json.dumps(["item_code", "warehouse", "actual_qty", "projected_qty", "valuation_rate"]),
        "limit_page_length": 10,
    }
    if filters:
        params["filters"] = json.dumps(filters)

    try:
        url = f"{settings.erpnext_base_url}/api/resource/Bin"
        resp = requests.get(url, headers=headers, cookies=cookies, params=params, timeout=6)
        if resp.status_code == 200:
            bins = resp.json().get("data", [])
            total_qty = sum(float(b.get("actual_qty", 0.0)) for b in bins)
            return {
                "success": True,
                "tool": "get_stock_balance",
                "item_code": item_code,
                "warehouse": warehouse,
                "count": len(bins),
                "total_quantity": total_qty,
                "records": bins,
            }
        elif resp.status_code == 403:
            return {"success": False, "error": "FORBIDDEN", "message": f"Frappe denied access for '{authenticated_user}'."}
        else:
            return {"success": False, "error": f"HTTP_{resp.status_code}", "message": resp.text[:200]}
    except Exception as e:
        return {"success": False, "error": "CONNECTION_ERROR", "message": str(e)}


def get_item_details(
    authenticated_user: str, session_id: Optional[str] = None, item_code: Optional[str] = None
) -> Dict[str, Any]:
    """Retrieves metadata and specifications for an inventory item."""
    perm = check_user_stock_permission(authenticated_user)
    if not perm.allowed:
        return {"success": False, "error": "PERMISSION_DENIED", "message": perm.reason}

    if not item_code:
        return {"success": False, "error": "INVALID_PARAMS", "message": "item_code is required"}

    headers, cookies, err = _get_auth_context(authenticated_user, session_id)
    if err:
        return {"success": False, "error": "SESSION_REQUIRED", "message": err}

    try:
        # Search by exact or partial item code
        url = f"{settings.erpnext_base_url}/api/resource/Item"
        params = {
            "filters": json.dumps([["item_code", "like", f"%{item_code.strip()}%"]]),
            "fields": json.dumps(["name", "item_name", "item_group", "stock_uom", "is_stock_item", "description"]),
            "limit_page_length": 3,
        }
        resp = requests.get(url, headers=headers, cookies=cookies, params=params, timeout=6)
        if resp.status_code == 200:
            items = resp.json().get("data", [])
            if not items:
                return {"success": True, "count": 0, "message": f"No item found matching '{item_code}'", "records": []}
            return {"success": True, "tool": "get_item_details", "records": items, "count": len(items)}
        return {"success": False, "error": f"HTTP_{resp.status_code}", "message": resp.text[:200]}
    except Exception as e:
        return {"success": False, "error": "CONNECTION_ERROR", "message": str(e)}


def get_warehouse_stock(
    authenticated_user: str, session_id: Optional[str] = None, warehouse: Optional[str] = None
) -> Dict[str, Any]:
    """Retrieves all stocked items inside a specific warehouse."""
    return get_stock_balance(authenticated_user, session_id=session_id, warehouse=warehouse)


def get_stock_ledger(
    authenticated_user: str,
    session_id: Optional[str] = None,
    item_code: Optional[str] = None,
    warehouse: Optional[str] = None,
    limit: int = 5,
) -> Dict[str, Any]:
    """Retrieves historical stock ledger transaction entries."""
    perm = check_user_stock_permission(authenticated_user)
    if not perm.allowed:
        return {"success": False, "error": "PERMISSION_DENIED", "message": perm.reason}

    headers, cookies, err = _get_auth_context(authenticated_user, session_id)
    if err:
        return {"success": False, "error": "SESSION_REQUIRED", "message": err}

    filters: List[List[Any]] = []
    if item_code and item_code.lower() not in ("none", "null", "all"):
        filters.append(["item_code", "like", f"%{item_code.strip()}%"])
    if warehouse and warehouse.lower() not in ("none", "null", "all"):
        filters.append(["warehouse", "like", f"%{warehouse.strip()}%"])

    params = {
        "fields": json.dumps(["name", "item_code", "warehouse", "actual_qty", "qty_after_transaction", "posting_date", "voucher_type"]),
        "order_by": "posting_date desc",
        "limit_page_length": min(int(limit), 10),
    }
    if filters:
        params["filters"] = json.dumps(filters)

    try:
        url = f"{settings.erpnext_base_url}/api/resource/Stock Ledger Entry"
        resp = requests.get(url, headers=headers, cookies=cookies, params=params, timeout=6)
        if resp.status_code == 200:
            entries = resp.json().get("data", [])
            return {"success": True, "tool": "get_stock_ledger", "records": entries, "count": len(entries)}
        return {"success": False, "error": f"HTTP_{resp.status_code}", "message": resp.text[:200]}
    except Exception as e:
        return {"success": False, "error": "CONNECTION_ERROR", "message": str(e)}


def get_projected_quantity(
    authenticated_user: str,
    session_id: Optional[str] = None,
    item_code: Optional[str] = None,
    warehouse: Optional[str] = None,
) -> Dict[str, Any]:
    """Retrieves projected inventory quantities considering purchase and sales orders."""
    res = get_stock_balance(authenticated_user, session_id=session_id, item_code=item_code, warehouse=warehouse)
    if not res.get("success"):
        return res
    records = res.get("records", [])
    total_projected = sum(float(b.get("projected_qty", 0.0)) for b in records)
    res["total_projected"] = total_projected
    res["tool"] = "get_projected_quantity"
    return res


def get_stock_ageing(
    authenticated_user: str, session_id: Optional[str] = None, item_code: Optional[str] = None
) -> Dict[str, Any]:
    """Retrieves stock ageing and recent batch receipt timestamps."""
    return get_stock_ledger(authenticated_user, session_id=session_id, item_code=item_code, limit=5)


def search_items(
    authenticated_user: str, session_id: Optional[str] = None, search_term: str = "", limit: int = 5
) -> Dict[str, Any]:
    """Searches the automotive parts and materials catalogue."""
    perm = check_user_stock_permission(authenticated_user)
    if not perm.allowed:
        return {"success": False, "error": "PERMISSION_DENIED", "message": perm.reason}

    headers, cookies, err = _get_auth_context(authenticated_user, session_id)
    if err:
        return {"success": False, "error": "SESSION_REQUIRED", "message": err}

    params = {
        "fields": json.dumps(["name", "item_name", "item_group", "stock_uom"]),
        "limit_page_length": min(int(limit), 10),
    }
    if search_term and search_term.lower() not in ("all", "none", "items"):
        params["filters"] = json.dumps([["item_name", "like", f"%{search_term.strip()}%"]])

    try:
        url = f"{settings.erpnext_base_url}/api/resource/Item"
        resp = requests.get(url, headers=headers, cookies=cookies, params=params, timeout=6)
        if resp.status_code == 200:
            items = resp.json().get("data", [])
            return {"success": True, "tool": "search_items", "records": items, "count": len(items)}
        return {"success": False, "error": f"HTTP_{resp.status_code}", "message": resp.text[:200]}
    except Exception as e:
        return {"success": False, "error": "CONNECTION_ERROR", "message": str(e)}


def list_warehouses(
    authenticated_user: str, session_id: Optional[str] = None, limit: int = 10
) -> Dict[str, Any]:
    """Lists configured ERPNext warehouses and storage locations."""
    perm = check_user_stock_permission(authenticated_user)
    if not perm.allowed:
        return {"success": False, "error": "PERMISSION_DENIED", "message": perm.reason}

    headers, cookies, err = _get_auth_context(authenticated_user, session_id)
    if err:
        return {"success": False, "error": "SESSION_REQUIRED", "message": err}

    params = {
        "fields": json.dumps(["name", "warehouse_name", "company", "is_group"]),
        "limit_page_length": min(int(limit), 15),
    }

    try:
        url = f"{settings.erpnext_base_url}/api/resource/Warehouse"
        resp = requests.get(url, headers=headers, cookies=cookies, params=params, timeout=6)
        if resp.status_code == 200:
            whs = resp.json().get("data", [])
            return {"success": True, "tool": "list_warehouses", "records": whs, "count": len(whs)}
        return {"success": False, "error": f"HTTP_{resp.status_code}", "message": resp.text[:200]}
    except Exception as e:
        return {"success": False, "error": "CONNECTION_ERROR", "message": str(e)}


# ==============================================================================
# PURCHASE TOOLS
# ==============================================================================


def list_purchase_orders(
    authenticated_user: str,
    session_id: Optional[str] = None,
    limit: int = 5,
    status: Optional[str] = None,
) -> Dict[str, Any]:
    """Retrieves purchase orders with supplier, status, and grand total."""
    perm = check_user_purchase_permission(authenticated_user)
    if not perm.allowed:
        return {"success": False, "error": "PERMISSION_DENIED", "message": perm.reason}

    headers, cookies, err = _get_auth_context(authenticated_user, session_id)
    if err:
        return {"success": False, "error": "SESSION_REQUIRED", "message": err}

    params = {
        "fields": json.dumps(["name", "supplier", "status", "grand_total", "currency", "transaction_date"]),
        "order_by": "transaction_date desc",
        "limit_page_length": min(int(limit), 15),
    }
    if status and status.lower() not in ("all", "none"):
        params["filters"] = json.dumps([["status", "=", status.strip()]])

    try:
        url = f"{settings.erpnext_base_url}/api/resource/Purchase Order"
        resp = requests.get(url, headers=headers, cookies=cookies, params=params, timeout=6)
        if resp.status_code == 200:
            pos = resp.json().get("data", [])
            total_val = sum(float(p.get("grand_total", 0.0)) for p in pos)
            return {
                "success": True,
                "tool": "list_purchase_orders",
                "records": pos,
                "count": len(pos),
                "total_value": total_val,
            }
        return {"success": False, "error": f"HTTP_{resp.status_code}", "message": resp.text[:200]}
    except Exception as e:
        return {"success": False, "error": "CONNECTION_ERROR", "message": str(e)}


def get_purchase_order_details(
    authenticated_user: str, session_id: Optional[str] = None, purchase_order_id: Optional[str] = None
) -> Dict[str, Any]:
    """Retrieves detailed information for a specific purchase order."""
    perm = check_user_purchase_permission(authenticated_user)
    if not perm.allowed:
        return {"success": False, "error": "PERMISSION_DENIED", "message": perm.reason}

    if not purchase_order_id:
        return {"success": False, "error": "INVALID_PARAMS", "message": "purchase_order_id is required"}

    headers, cookies, err = _get_auth_context(authenticated_user, session_id)
    if err:
        return {"success": False, "error": "SESSION_REQUIRED", "message": err}

    try:
        url = f"{settings.erpnext_base_url}/api/resource/Purchase Order/{purchase_order_id.strip()}"
        resp = requests.get(url, headers=headers, cookies=cookies, timeout=6)
        if resp.status_code == 200:
            data = resp.json().get("data", {})
            return {"success": True, "tool": "get_purchase_order_details", "record": data}
        return {"success": False, "error": f"HTTP_{resp.status_code}", "message": resp.text[:200]}
    except Exception as e:
        return {"success": False, "error": "CONNECTION_ERROR", "message": str(e)}


def get_pending_purchase_orders(
    authenticated_user: str, session_id: Optional[str] = None, limit: int = 5
) -> Dict[str, Any]:
    """Retrieves pending purchase orders (status 'To Receive and Bill' or 'To Bill')."""
    perm = check_user_purchase_permission(authenticated_user)
    if not perm.allowed:
        return {"success": False, "error": "PERMISSION_DENIED", "message": perm.reason}

    headers, cookies, err = _get_auth_context(authenticated_user, session_id)
    if err:
        return {"success": False, "error": "SESSION_REQUIRED", "message": err}

    params = {
        "filters": json.dumps([["status", "in", ["To Receive and Bill", "To Bill", "To Receive"]]]),
        "fields": json.dumps(["name", "supplier", "status", "grand_total", "currency", "transaction_date"]),
        "order_by": "grand_total desc",
        "limit_page_length": min(int(limit), 15),
    }

    try:
        url = f"{settings.erpnext_base_url}/api/resource/Purchase Order"
        resp = requests.get(url, headers=headers, cookies=cookies, params=params, timeout=6)
        if resp.status_code == 200:
            pos = resp.json().get("data", [])
            total_pending = sum(float(p.get("grand_total", 0.0)) for p in pos)
            return {
                "success": True,
                "tool": "get_pending_purchase_orders",
                "records": pos,
                "count": len(pos),
                "total_pending_amount": total_pending,
            }
        return {"success": False, "error": f"HTTP_{resp.status_code}", "message": resp.text[:200]}
    except Exception as e:
        return {"success": False, "error": "CONNECTION_ERROR", "message": str(e)}


def get_purchase_order_status(
    authenticated_user: str, session_id: Optional[str] = None, purchase_order_id: Optional[str] = None
) -> Dict[str, Any]:
    """Queries receipt and billing completion status for a purchase order."""
    return get_purchase_order_details(authenticated_user, session_id=session_id, purchase_order_id=purchase_order_id)


def list_suppliers(
    authenticated_user: str, session_id: Optional[str] = None, limit: int = 5
) -> Dict[str, Any]:
    """Lists registered component, parts, and material suppliers."""
    perm = check_user_purchase_permission(authenticated_user)
    if not perm.allowed:
        return {"success": False, "error": "PERMISSION_DENIED", "message": perm.reason}

    headers, cookies, err = _get_auth_context(authenticated_user, session_id)
    if err:
        return {"success": False, "error": "SESSION_REQUIRED", "message": err}

    params = {
        "fields": json.dumps(["name", "supplier_name", "supplier_group", "country"]),
        "limit_page_length": min(int(limit), 15),
    }

    try:
        url = f"{settings.erpnext_base_url}/api/resource/Supplier"
        resp = requests.get(url, headers=headers, cookies=cookies, params=params, timeout=6)
        if resp.status_code == 200:
            sups = resp.json().get("data", [])
            return {"success": True, "tool": "list_suppliers", "records": sups, "count": len(sups)}
        return {"success": False, "error": f"HTTP_{resp.status_code}", "message": resp.text[:200]}
    except Exception as e:
        return {"success": False, "error": "CONNECTION_ERROR", "message": str(e)}


def get_supplier_details(
    authenticated_user: str, session_id: Optional[str] = None, supplier_id: Optional[str] = None
) -> Dict[str, Any]:
    """Retrieves details and supplier group for a specific supplier."""
    perm = check_user_purchase_permission(authenticated_user)
    if not perm.allowed:
        return {"success": False, "error": "PERMISSION_DENIED", "message": perm.reason}

    if not supplier_id:
        return {"success": False, "error": "INVALID_PARAMS", "message": "supplier_id is required"}

    headers, cookies, err = _get_auth_context(authenticated_user, session_id)
    if err:
        return {"success": False, "error": "SESSION_REQUIRED", "message": err}

    try:
        url = f"{settings.erpnext_base_url}/api/resource/Supplier/{supplier_id.strip()}"
        resp = requests.get(url, headers=headers, cookies=cookies, timeout=6)
        if resp.status_code == 200:
            data = resp.json().get("data", {})
            return {"success": True, "tool": "get_supplier_details", "record": data}
        return {"success": False, "error": f"HTTP_{resp.status_code}", "message": resp.text[:200]}
    except Exception as e:
        return {"success": False, "error": "CONNECTION_ERROR", "message": str(e)}


def get_purchase_invoices(
    authenticated_user: str,
    session_id: Optional[str] = None,
    limit: int = 5,
    status: Optional[str] = None,
) -> Dict[str, Any]:
    """Retrieves purchase invoices with supplier and billing amounts."""
    perm = check_user_purchase_permission(authenticated_user)
    if not perm.allowed:
        return {"success": False, "error": "PERMISSION_DENIED", "message": perm.reason}

    headers, cookies, err = _get_auth_context(authenticated_user, session_id)
    if err:
        return {"success": False, "error": "SESSION_REQUIRED", "message": err}

    params = {
        "fields": json.dumps(["name", "supplier", "status", "grand_total", "outstanding_amount", "posting_date"]),
        "order_by": "posting_date desc",
        "limit_page_length": min(int(limit), 15),
    }
    if status and status.lower() not in ("all", "none"):
        params["filters"] = json.dumps([["status", "=", status.strip()]])

    try:
        url = f"{settings.erpnext_base_url}/api/resource/Purchase Invoice"
        resp = requests.get(url, headers=headers, cookies=cookies, params=params, timeout=6)
        if resp.status_code == 200:
            invs = resp.json().get("data", [])
            return {"success": True, "tool": "get_purchase_invoices", "records": invs, "count": len(invs)}
        return {"success": False, "error": f"HTTP_{resp.status_code}", "message": resp.text[:200]}
    except Exception as e:
        return {"success": False, "error": "CONNECTION_ERROR", "message": str(e)}


def get_outstanding_purchase_invoices(
    authenticated_user: str, session_id: Optional[str] = None, limit: int = 5
) -> Dict[str, Any]:
    """Retrieves unpaid or partially paid purchase invoices."""
    perm = check_user_purchase_permission(authenticated_user)
    if not perm.allowed:
        return {"success": False, "error": "PERMISSION_DENIED", "message": perm.reason}

    headers, cookies, err = _get_auth_context(authenticated_user, session_id)
    if err:
        return {"success": False, "error": "SESSION_REQUIRED", "message": err}

    params = {
        "filters": json.dumps([["outstanding_amount", ">", 0]]),
        "fields": json.dumps(["name", "supplier", "status", "grand_total", "outstanding_amount", "posting_date"]),
        "order_by": "outstanding_amount desc",
        "limit_page_length": min(int(limit), 15),
    }

    try:
        url = f"{settings.erpnext_base_url}/api/resource/Purchase Invoice"
        resp = requests.get(url, headers=headers, cookies=cookies, params=params, timeout=6)
        if resp.status_code == 200:
            invs = resp.json().get("data", [])
            total_due = sum(float(inv.get("outstanding_amount", 0.0)) for inv in invs)
            return {
                "success": True,
                "tool": "get_outstanding_purchase_invoices",
                "records": invs,
                "count": len(invs),
                "total_outstanding": total_due,
            }
        return {"success": False, "error": f"HTTP_{resp.status_code}", "message": resp.text[:200]}
    except Exception as e:
        return {"success": False, "error": "CONNECTION_ERROR", "message": str(e)}


def get_purchase_totals(
    authenticated_user: str, session_id: Optional[str] = None
) -> Dict[str, Any]:
    """Calculates overall purchase expenditure across purchase orders."""
    res = list_purchase_orders(authenticated_user, session_id=session_id, limit=50)
    if not res.get("success"):
        return res
    records = res.get("records", [])
    total_val = sum(float(r.get("grand_total", 0.0)) for r in records)
    return {
        "success": True,
        "tool": "get_purchase_totals",
        "order_count": len(records),
        "total_purchase_amount": total_val,
        "currency": records[0].get("currency", "PKR") if records else "PKR",
    }


# ==============================================================================
# TOOL REGISTRY & DISPATCHER
# ==============================================================================

TOOL_REGISTRY: Dict[str, Any] = {
    # Stock
    "get_stock_balance": get_stock_balance,
    "get_item_details": get_item_details,
    "get_warehouse_stock": get_warehouse_stock,
    "get_stock_ledger": get_stock_ledger,
    "get_projected_quantity": get_projected_quantity,
    "get_stock_ageing": get_stock_ageing,
    "search_items": search_items,
    "list_warehouses": list_warehouses,
    # Purchase
    "list_purchase_orders": list_purchase_orders,
    "get_purchase_order_details": get_purchase_order_details,
    "get_pending_purchase_orders": get_pending_purchase_orders,
    "get_purchase_order_status": get_purchase_order_status,
    "list_suppliers": list_suppliers,
    "get_supplier_details": get_supplier_details,
    "get_purchase_invoices": get_purchase_invoices,
    "get_outstanding_purchase_invoices": get_outstanding_purchase_invoices,
    "get_purchase_totals": get_purchase_totals,
}

TOOL_DESCRIPTIONS: str = """
- get_stock_balance(item_code, warehouse): Get current balance and quantities in stock
- get_item_details(item_code): Inspect specifications, item group, and description
- get_warehouse_stock(warehouse): List all inventory inside a specific warehouse
- get_stock_ledger(item_code, warehouse, limit): View historical inventory transactions
- get_projected_quantity(item_code, warehouse): View projected future stock levels
- get_stock_ageing(item_code): Inspect recent inventory receipts and ageing
- search_items(search_term, limit): Search materials and automotive parts catalog
- list_warehouses(limit): List all active ERPNext warehouses
- list_purchase_orders(limit, status): List purchase orders with totals and suppliers
- get_purchase_order_details(purchase_order_id): Full details of a specific purchase order
- get_pending_purchase_orders(limit): List purchase orders awaiting receipt or billing
- get_purchase_order_status(purchase_order_id): Receipt and billing completion status
- list_suppliers(limit): List registered vendors and component suppliers
- get_supplier_details(supplier_id): View vendor group, country, and contact details
- get_purchase_invoices(limit, status): List supplier purchase invoices
- get_outstanding_purchase_invoices(limit): List unpaid invoices with outstanding balances
- get_purchase_totals(): Summarize total purchase volume and order amounts
""".strip()


import inspect


def execute_tool(
    tool_name: str,
    arguments: Dict[str, Any],
    authenticated_user: str,
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Safely dispatches a planned tool call with parameter normalization, filtering, and RBAC."""
    tool_fn = TOOL_REGISTRY.get(tool_name)
    if not tool_fn:
        return {"success": False, "error": "UNKNOWN_TOOL", "message": f"Tool '{tool_name}' is not recognized."}

    sig = inspect.signature(tool_fn)
    param_names = set(sig.parameters.keys())

    clean_kwargs = dict(arguments or {})
    clean_kwargs.pop("authenticated_user", None)
    clean_kwargs.pop("session_id", None)

    # Alias normalization
    if "item_code" in param_names and "item_code" not in clean_kwargs:
        for alias in ("search_term", "item", "item_name", "part", "material", "name"):
            if alias in clean_kwargs and clean_kwargs[alias]:
                clean_kwargs["item_code"] = clean_kwargs.pop(alias)
                break

    if "search_term" in param_names and "search_term" not in clean_kwargs:
        for alias in ("item_code", "query", "term", "item", "name"):
            if alias in clean_kwargs and clean_kwargs[alias]:
                clean_kwargs["search_term"] = clean_kwargs.pop(alias)
                break

    if "purchase_order_id" in param_names and "purchase_order_id" not in clean_kwargs:
        for alias in ("po_id", "order_id", "id", "name"):
            if alias in clean_kwargs and clean_kwargs[alias]:
                clean_kwargs["purchase_order_id"] = clean_kwargs.pop(alias)
                break

    if "supplier_id" in param_names and "supplier_id" not in clean_kwargs:
        for alias in ("supplier", "vendor", "id", "name"):
            if alias in clean_kwargs and clean_kwargs[alias]:
                clean_kwargs["supplier_id"] = clean_kwargs.pop(alias)
                break

    # Filter only arguments accepted by tool_fn
    filtered_kwargs = {k: v for k, v in clean_kwargs.items() if k in param_names}

    return tool_fn(authenticated_user=authenticated_user, session_id=session_id, **filtered_kwargs)

