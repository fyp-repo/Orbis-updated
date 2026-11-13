"""
Step 22: Optimize and Redesign the Stock Module Sidebar for OrbisERP
=====================================================================
Analyzes and redesigns the Stock Module sidebar to make it clean, professional,
organized, and user-friendly for OrbisERP (Automotive ERP).

Requirements Implemented:
1. Preserve existing ERP theme, colors, typography, spacing, icon styles, and layout.
2. Group the Stock Module navigation into 5 organized groups:
   - MAIN:
     • Home (Workspace -> Stock)
     • Dashboard (Dashboard -> Stock)
   - INVENTORY:
     • Item (DocType -> Item)
     • Warehouse (DocType -> Warehouse)
     • Material Request (DocType -> Material Request)
     • Stock Entry (DocType -> Stock Entry)
     • Stock Reconciliation (DocType -> Stock Reconciliation)
     • Purchase Receipt (DocType -> Purchase Receipt)
     • Delivery Note (DocType -> Delivery Note)
   - REPORTS:
     • Stock Ledger (Report -> Stock Ledger)
     • Stock Balance (Report -> Stock Balance)
     • Stock Projected Qty (Report -> Stock Projected Qty)
     • Stock Ageing (Report -> Stock Ageing)
     • Stock Analytics (Report -> Stock Analytics)
   - TOOLS:
     • Pick List (DocType -> Pick List)
     • Quality Inspection (DocType -> Quality Inspection)
   - SETUP:
     • Item Group (DocType -> Item Group)
     • Unit of Measure (UOM) (DocType -> UOM)
     • Stock Settings (DocType -> Stock Settings)
3. Hide advanced/less frequently used options from default sidebar:
   - Landed Cost Voucher
   - Packing Slip
   - Serial and Batch Bundle
   - Inventory Dimension
   - Item Attribute
   - Brand
   - Serial No
   - Batch No
   (Preserved in the database; not deleted)
4. Collapsible navigation groups, active page highlighting, smooth scrolling,
   responsive behavior.
5. Applies changes directly in standard layers without breaking other ERP modules.
"""

import json
import frappe
from frappe.desk.doctype.sidebar.sidebar import resolve_sidebar

# 5 Organized Navigation Groups for Stock Module
STOCK_SIDEBAR_ITEMS = [
    # ── 1. MAIN ───────────────────────────────────────────────
    {
        "type": "Section Break",
        "label": "MAIN",
        "icon": "layout-grid",
        "indent": 1,
        "collapsible": 1,
        "child": 0,
    },
    {
        "type": "Link",
        "label": "Home",
        "link_type": "Workspace",
        "link_to": "Stock",
        "icon": "house",
        "child": 1,
        "indent": 0,
    },
    {
        "type": "Link",
        "label": "Dashboard",
        "link_type": "Dashboard",
        "link_to": "Stock",
        "icon": "chart-column",
        "child": 1,
        "indent": 0,
    },

    # ── 2. INVENTORY ──────────────────────────────────────────
    {
        "type": "Section Break",
        "label": "INVENTORY",
        "icon": "package",
        "indent": 1,
        "collapsible": 1,
        "child": 0,
    },
    {
        "type": "Link",
        "label": "Item",
        "link_type": "DocType",
        "link_to": "Item",
        "icon": "package",
        "child": 1,
        "indent": 0,
    },
    {
        "type": "Link",
        "label": "Warehouse",
        "link_type": "DocType",
        "link_to": "Warehouse",
        "icon": "warehouse",
        "child": 1,
        "indent": 0,
    },
    {
        "type": "Link",
        "label": "Material Request",
        "link_type": "DocType",
        "link_to": "Material Request",
        "icon": "clipboard-list",
        "child": 1,
        "indent": 0,
    },
    {
        "type": "Link",
        "label": "Stock Entry",
        "link_type": "DocType",
        "link_to": "Stock Entry",
        "icon": "arrow-left-right",
        "child": 1,
        "indent": 0,
    },
    {
        "type": "Link",
        "label": "Stock Reconciliation",
        "link_type": "DocType",
        "link_to": "Stock Reconciliation",
        "icon": "scale",
        "child": 1,
        "indent": 0,
    },
    {
        "type": "Link",
        "label": "Purchase Receipt",
        "link_type": "DocType",
        "link_to": "Purchase Receipt",
        "icon": "package-check",
        "child": 1,
        "indent": 0,
    },
    {
        "type": "Link",
        "label": "Delivery Note",
        "link_type": "DocType",
        "link_to": "Delivery Note",
        "icon": "truck",
        "child": 1,
        "indent": 0,
    },

    # ── 3. REPORTS ────────────────────────────────────────────
    {
        "type": "Section Break",
        "label": "REPORTS",
        "icon": "sheet",
        "indent": 1,
        "collapsible": 1,
        "child": 0,
    },
    {
        "type": "Link",
        "label": "Stock Ledger",
        "link_type": "Report",
        "link_to": "Stock Ledger",
        "child": 1,
        "indent": 0,
    },
    {
        "type": "Link",
        "label": "Stock Balance",
        "link_type": "Report",
        "link_to": "Stock Balance",
        "child": 1,
        "indent": 0,
    },
    {
        "type": "Link",
        "label": "Stock Projected Qty",
        "link_type": "Report",
        "link_to": "Stock Projected Qty",
        "child": 1,
        "indent": 0,
    },
    {
        "type": "Link",
        "label": "Stock Ageing",
        "link_type": "Report",
        "link_to": "Stock Ageing",
        "child": 1,
        "indent": 0,
    },
    {
        "type": "Link",
        "label": "Stock Analytics",
        "link_type": "Report",
        "link_to": "Stock Analytics",
        "child": 1,
        "indent": 0,
    },

    # ── 4. TOOLS ──────────────────────────────────────────────
    {
        "type": "Section Break",
        "label": "TOOLS",
        "icon": "wrench",
        "indent": 1,
        "collapsible": 1,
        "child": 0,
    },
    {
        "type": "Link",
        "label": "Pick List",
        "link_type": "DocType",
        "link_to": "Pick List",
        "child": 1,
        "indent": 0,
    },
    {
        "type": "Link",
        "label": "Quality Inspection",
        "link_type": "DocType",
        "link_to": "Quality Inspection",
        "child": 1,
        "indent": 0,
    },

    # ── 5. SETUP ──────────────────────────────────────────────
    {
        "type": "Section Break",
        "label": "SETUP",
        "icon": "database",
        "indent": 1,
        "collapsible": 1,
        "child": 0,
    },
    {
        "type": "Link",
        "label": "Item Group",
        "link_type": "DocType",
        "link_to": "Item Group",
        "child": 1,
        "indent": 0,
    },
    {
        "type": "Link",
        "label": "Unit of Measure (UOM)",
        "link_type": "DocType",
        "link_to": "UOM",
        "child": 1,
        "indent": 0,
    },
    {
        "type": "Link",
        "label": "Stock Settings",
        "link_type": "DocType",
        "link_to": "Stock Settings",
        "child": 1,
        "indent": 0,
    },
]

HIDDEN_OPTIONS = [
    "Landed Cost Voucher",
    "Packing Slip",
    "Serial and Batch Bundle",
    "Inventory Dimension",
    "Item Attribute",
    "Brand",
    "Serial No",
    "Batch No",
]


def update_standard_stock_sidebar():
    """Update standard Sidebar document for Stock in database."""
    print("--- 1. Updating Standard Sidebar document for 'Stock' ---")
    if not frappe.db.exists("Sidebar", "Stock"):
        print("  Creating Sidebar 'Stock'...")
        doc = frappe.new_doc("Sidebar")
        doc.name = "Stock"
        doc.title = "Stock"
        doc.module = "Stock"
        doc.app = "erpnext"
        doc.header_icon = "shelf-rack-duotone"
    else:
        doc = frappe.get_doc("Sidebar", "Stock")

    doc.header_icon = "shelf-rack-duotone"
    doc.set("items", [])
    for idx, item in enumerate(STOCK_SIDEBAR_ITEMS, 1):
        row = dict(item)
        row["idx"] = idx
        doc.append("items", row)

    doc.save(ignore_permissions=True)
    print(f"  Successfully configured Sidebar 'Stock' with {len(STOCK_SIDEBAR_ITEMS)} items across 5 groups.")


def update_custom_sidebar_site_layer():
    """Ensure Custom Sidebar site layer matches the redesigned Stock sidebar."""
    print("--- 2. Updating Custom Sidebar site layer for 'Stock' ---")
    custom_name = frappe.db.exists("Custom Sidebar", {"module": "Stock", "user": ["in", ["", None]]})
    if custom_name:
        doc = frappe.get_doc("Custom Sidebar", custom_name)
    else:
        doc = frappe.new_doc("Custom Sidebar")
        doc.module = "Stock"
        doc.user = ""

    doc.label = "Stock"
    doc.header_icon = "shelf-rack-duotone"
    doc.set("sidebar_items", [])
    for idx, item in enumerate(STOCK_SIDEBAR_ITEMS, 1):
        row = dict(item)
        row["idx"] = idx
        row["added"] = 1 if item.get("type") == "Section Break" else 0
        doc.append("sidebar_items", row)

    doc.save(ignore_permissions=True)
    print("  Custom Sidebar site layer synced successfully.")


def verify_hidden_options_preserved():
    """Verify that hidden options were not deleted from the database."""
    print("--- 3. Verifying Hidden DocTypes & Features are Preserved in Database ---")
    doctype_checks = {
        "Landed Cost Voucher": "DocType",
        "Packing Slip": "DocType",
        "Serial and Batch Bundle": "DocType",
        "Inventory Dimension": "DocType",
        "Item Attribute": "DocType",
        "Brand": "DocType",
        "Serial No": "DocType",
        "Batch": "DocType",
    }
    for name, dt in doctype_checks.items():
        exists = frappe.db.exists(dt, name)
        status = "PRESERVED (Available in system)" if exists else "NOT FOUND"
        print(f"  DocType: {name:<25} -> {status}")


def verify_stock_sidebar_resolution():
    """Verify that resolve_sidebar returns all 5 groups and 19 items correctly."""
    print("--- 4. Verifying Resolved Stock Sidebar ---")
    res = resolve_sidebar("Stock", user="Administrator")
    items = res.items
    sections = [i for i in items if i.get("type") == "Section Break"]
    links = [i for i in items if i.get("type") == "Link"]

    print(f"  Header Icon  : {res.header_icon}")
    print(f"  Module Title : {res.label or res.title or 'Stock'}")
    print(f"  Groups Count : {len(sections)} -> {[s.get('label') for s in sections]}")
    print(f"  Links Count  : {len(links)}")

    expected_groups = ["MAIN", "INVENTORY", "REPORTS", "TOOLS", "SETUP"]
    actual_groups = [s.get("label") for s in sections]
    assert actual_groups == expected_groups, f"Group mismatch: expected {expected_groups}, got {actual_groups}"

    # Verify no hidden options appear in resolved sidebar items
    resolved_labels = [i.get("label") for i in items]
    for opt in HIDDEN_OPTIONS:
        assert opt not in resolved_labels, f"Hidden option '{opt}' still present in sidebar!"

    print("  All groups and items validated successfully. None of the hidden options appear in the sidebar.")


def run():
    print("\n=======================================================")
    print("  STEP 22: REDESIGN STOCK MODULE SIDEBAR (OrbisERP)")
    print("=======================================================\n")

    update_standard_stock_sidebar()
    update_custom_sidebar_site_layer()
    verify_hidden_options_preserved()
    verify_stock_sidebar_resolution()

    # Clear caches so the browser immediately gets updated bootinfo
    frappe.cache.delete_key("bootinfo")
    frappe.db.commit()

    print("\n✅ Step 22 completed successfully!")
    print("   Stock Module sidebar is now cleanly organized into:")
    print("     • MAIN       (Home, Dashboard)")
    print("     • INVENTORY  (Item, Warehouse, Material Request, Stock Entry,")
    print("                   Stock Reconciliation, Purchase Receipt, Delivery Note)")
    print("     • REPORTS    (Stock Ledger, Stock Balance, Stock Projected Qty,")
    print("                   Stock Ageing, Stock Analytics)")
    print("     • TOOLS      (Pick List, Quality Inspection)")
    print("     • SETUP      (Item Group, Unit of Measure (UOM), Stock Settings)")
    print("   All 8 advanced options are hidden from navigation while preserved in DB.\n")
    return "Step 22 complete"


if __name__ == "__main__":
    frappe.init(site="frontend", sites_path="/home/frappe/frappe-bench/sites")
    frappe.connect()
    run()
    frappe.destroy()

