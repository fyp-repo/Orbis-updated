"""
OrbisERP Security Module — Credential Verification & RBAC Boundary
===================================================================
Verifies ERPNext user credentials server-side during voice enrollment.
Ensures voice profiles can only be associated with genuine, enabled ERPNext accounts.
Never stores or persists ERPNext passwords.
Extracts and validates genuine Frappe session cookies (sid).
"""

import re
import requests
from urllib.parse import unquote
from typing import Optional, Tuple, Dict, Any
from app.core.config import settings


def normalize_spoken_email(spoken_text: str) -> str:
    """
    Normalizes spoken email phrases into standard email format.
    E.g. 'ayesha dot tahir at gmail dot com' -> 'ayesha.tahir@gmail.com'
    Supports 'dot', 'at', 'underscore', 'hyphen' and spelled letters.
    """
    if not spoken_text:
        return ""

    cleaned = spoken_text.strip().lower()
    # Strip conversational prefixes
    cleaned = re.sub(
        r"^(my email is|my email address is|email is|my email|it is|it's|email|i am|this is)\s*",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )

    # Convert spoken symbols
    replacements = [
        (r"\b(at the rate of|at the rate|at sign|at)\b", "@"),
        (r"\b(dot|period|point)\b", "."),
        (r"\b(underscore|under score)\b", "_"),
        (r"\b(hyphen|dash|minus)\b", "-"),
    ]
    for pattern, sym in replacements:
        cleaned = re.sub(pattern, sym, cleaned, flags=re.IGNORECASE)

    # Normalize whitespace around @ and dots
    parts = cleaned.split("@")
    if len(parts) == 2:
        local_part = re.sub(r"\s+", "", parts[0])
        domain_part = re.sub(r"\s+", "", parts[1])
        cleaned = f"{local_part}@{domain_part}"
    else:
        # If there is no '@' symbol, the utterance is not an email dictation.
        # Return empty string to prevent concatenating random command words.
        return ""

    return cleaned


def check_erpnext_user_exists(user_id: str) -> Dict[str, Any]:
    """
    Checks whether user_id / email exists and is active/enabled in ERPNext.
    Resolves both primary key `name` (e.g. 'Administrator') and email/username (e.g. 'forw8007@gmail.com').
    Returns: {"exists": bool, "is_enabled": bool, "full_name": Optional[str], "canonical_user_id": Optional[str]}
    """
    if not user_id:
        return {"exists": False, "is_enabled": False, "full_name": None, "canonical_user_id": None}

    headers = {"Authorization": f"token {settings.erpnext_api_key}:{settings.erpnext_api_secret}"}
    clean_id = user_id.strip()

    # 1. Direct lookup by User.name (primary key)
    try:
        url = f"{settings.erpnext_base_url}/api/resource/User/{clean_id}"
        resp = requests.get(url, headers=headers, timeout=5)
        if resp.status_code == 200:
            data = resp.json().get("data", {})
            return {
                "exists": True,
                "is_enabled": bool(data.get("enabled", 1)),
                "full_name": data.get("full_name") or clean_id,
                "canonical_user_id": data.get("name") or clean_id,
            }
    except Exception:
        pass

    # 2. Lookup by email or username
    try:
        url = f"{settings.erpnext_base_url}/api/resource/User"
        # Check by email
        params = {"filters": f'[["User","email","=","{clean_id}"]]'}
        resp = requests.get(url, headers=headers, params=params, timeout=5)
        if resp.status_code == 200:
            data_list = resp.json().get("data", [])
            if data_list:
                doc_name = data_list[0].get("name")
                doc_url = f"{settings.erpnext_base_url}/api/resource/User/{doc_name}"
                doc_resp = requests.get(doc_url, headers=headers, timeout=5)
                if doc_resp.status_code == 200:
                    data = doc_resp.json().get("data", {})
                    return {
                        "exists": True,
                        "is_enabled": bool(data.get("enabled", 1)),
                        "full_name": data.get("full_name") or doc_name,
                        "canonical_user_id": data.get("name") or doc_name,
                    }

        # Check by username
        params = {"filters": f'[["User","username","=","{clean_id}"]]'}
        resp = requests.get(url, headers=headers, params=params, timeout=5)
        if resp.status_code == 200:
            data_list = resp.json().get("data", [])
            if data_list:
                doc_name = data_list[0].get("name")
                doc_url = f"{settings.erpnext_base_url}/api/resource/User/{doc_name}"
                doc_resp = requests.get(doc_url, headers=headers, timeout=5)
                if doc_resp.status_code == 200:
                    data = doc_resp.json().get("data", {})
                    return {
                        "exists": True,
                        "is_enabled": bool(data.get("enabled", 1)),
                        "full_name": data.get("full_name") or doc_name,
                        "canonical_user_id": data.get("name") or doc_name,
                    }
    except Exception:
        pass

    return {"exists": False, "is_enabled": False, "full_name": None, "canonical_user_id": None}


def verify_erpnext_credentials(user_id: str, password: str) -> Dict[str, Any]:
    """
    Verifies user credentials directly against Frappe /api/method/login.
    Does NOT store the password.
    Extracts the authenticated Frappe session ID (sid).
    Resolves the canonical Frappe user ID for both emails and usernames.
    Returns validation status, session_id, user full name, and enabled state.
    """
    if not user_id or not password:
        return {"is_valid": False, "reason": "Username/email and password are required"}

    login_url = f"{settings.erpnext_base_url}/api/method/login"
    session = requests.Session()

    try:
        # 1. Native Frappe Authentication
        resp = session.post(
            login_url,
            data={"usr": user_id, "pwd": password},
            timeout=8,
        )

        if resp.status_code != 200 or resp.json().get("message") != "Logged In":
            return {
                "is_valid": False,
                "reason": "Invalid ERPNext username or password",
                "error_code": "AUTH_FAILED",
            }

        # Canonical Frappe user ID from response cookie or resolver (unquoted)
        raw_cookie_user = session.cookies.get("user_id")
        canonical_user = unquote(raw_cookie_user) if raw_cookie_user else resp.json().get("user_id")
        full_name = resp.json().get("full_name", user_id)
        sid = session.cookies.get("sid")

        if not canonical_user:
            user_info = check_erpnext_user_exists(user_id)
            canonical_user = user_info.get("canonical_user_id") or user_id

        # 2. Check User Status (Enabled / Active) using server-side service credentials
        user_info = check_erpnext_user_exists(canonical_user)
        if user_info["exists"] and not user_info["is_enabled"]:
            return {
                "is_valid": False,
                "reason": f"ERPNext account '{canonical_user}' is disabled. Enrollment prohibited.",
                "error_code": "ACCOUNT_DISABLED",
            }
        if user_info.get("full_name"):
            full_name = user_info["full_name"]

        return {
            "is_valid": True,
            "user_id": canonical_user,
            "login_input": user_id,
            "full_name": full_name,
            "session_id": sid,
            "reason": "ERPNext credentials and authenticated session verified",
        }

    except Exception as e:
        return {
            "is_valid": False,
            "reason": f"Failed to contact ERPNext authentication endpoint: {e}",
            "error_code": "CONNECTION_ERROR",
        }
    finally:
        session.close()


def verify_erpnext_session(sid: Optional[str]) -> Dict[str, Any]:
    """
    Validates a Frappe session ID (sid) against Frappe server.
    Ensures client requests cannot forge arbitrary ERPNext identities.
    Returns:
        dict: {"is_authenticated": bool, "user": str, "roles": list}
    """
    if not sid or not sid.strip():
        return {"is_authenticated": False, "user": "Guest", "roles": ["Guest"]}

    try:
        url = f"{settings.erpnext_base_url}/api/method/frappe.auth.get_logged_user"
        cookies = {"sid": sid.strip()}
        resp = requests.get(url, cookies=cookies, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            user = data.get("message")
            if user and user != "Guest":
                # Get actual user roles from Frappe
                roles = get_user_roles(user)
                return {
                    "is_authenticated": True,
                    "user": user,
                    "roles": roles,
                }
    except Exception:
        pass

    return {"is_authenticated": False, "user": "Guest", "roles": ["Guest"]}


def get_user_roles(user_id: str) -> list[str]:
    """Retrieves assigned Frappe roles for a user using backend API credentials."""
    if not user_id or user_id == "Guest":
        return ["Guest"]

    canonical_user = user_id
    if "@" in user_id:
        user_info = check_erpnext_user_exists(user_id)
        if user_info.get("canonical_user_id"):
            canonical_user = user_info["canonical_user_id"]

    try:
        url = f"{settings.erpnext_base_url}/api/resource/User/{canonical_user}"
        headers = {"Authorization": f"token {settings.erpnext_api_key}:{settings.erpnext_api_secret}"}
        resp = requests.get(url, headers=headers, timeout=5)
        if resp.status_code == 200:
            data = resp.json().get("data", {})
            raw_roles = data.get("roles", [])
            return [r.get("role") for r in raw_roles if isinstance(r, dict) and "role" in r]
    except Exception:
        pass

    return []


class PermissionResult:
    """Boolean-compatible result with explanatory reason."""
    def __init__(self, allowed: bool, reason: str):
        self.allowed = bool(allowed)
        self.reason = reason

    def __bool__(self):
        return self.allowed

    def __iter__(self):
        return iter((self.allowed, self.reason))

    def __repr__(self):
        return f"PermissionResult(allowed={self.allowed}, reason='{self.reason}')"


def check_user_stock_permission(user_id: str) -> PermissionResult:
    """
    Checks if user is authorized to access Stock Balance / Warehouse info.
    Strictly prohibits Guest access.
    """
    if not user_id or user_id == "Guest":
        return PermissionResult(False, "Access denied. User 'Guest' is not authorized to access Stock Balance.")

    canonical_user = user_id
    if "@" in user_id:
        user_info = check_erpnext_user_exists(user_id)
        if user_info.get("canonical_user_id"):
            canonical_user = user_info["canonical_user_id"]

    if canonical_user == "Administrator":
        return PermissionResult(True, "Administrator access granted")

    roles = get_user_roles(canonical_user)
    authorized_roles = {"Stock Manager", "Stock User", "System Manager"}

    if any(r in authorized_roles for r in roles):
        return PermissionResult(True, f"Authorized by role: {', '.join(set(roles) & authorized_roles)}")

    return PermissionResult(False, f"Access denied. User '{user_id}' does not have Stock Manager or Stock User roles.")


def check_user_purchase_permission(user_id: str) -> PermissionResult:
    """
    Checks if user is authorized to access Purchase Orders / Suppliers / Invoices.
    Strictly prohibits Guest access.
    """
    if not user_id or user_id == "Guest":
        return PermissionResult(False, "Access denied. User 'Guest' is not authorized to access Purchase records.")

    canonical_user = user_id
    if "@" in user_id:
        user_info = check_erpnext_user_exists(user_id)
        if user_info.get("canonical_user_id"):
            canonical_user = user_info["canonical_user_id"]

    if canonical_user == "Administrator":
        return PermissionResult(True, "Administrator access granted")

    roles = get_user_roles(canonical_user)
    authorized_roles = {"Purchase Manager", "Purchase User", "System Manager"}

    if any(r in authorized_roles for r in roles):
        return PermissionResult(True, f"Authorized by role: {', '.join(set(roles) & authorized_roles)}")

    return PermissionResult(False, f"Access denied. User '{user_id}' does not have Purchase Manager or Purchase User roles.")


def resolve_active_user_session(user_id: str, client_sid: Optional[str] = None) -> Optional[str]:
    """
    Validates and resolves a legitimate Frappe session (sid) for the user.
    Never trusts client-supplied sid unless validated against Frappe get_logged_user.
    Never uses a shared Administrator API token to bypass user-level permissions.
    """
    if not user_id or user_id == "Guest":
        return None

    # 1. If client provided a session ID, verify it strictly belongs to user_id
    if client_sid and client_sid.strip():
        sess_check = verify_erpnext_session(client_sid)
        if sess_check["is_authenticated"]:
            logged_user = sess_check["user"]
            canonical = check_erpnext_user_exists(user_id).get("canonical_user_id", user_id)
            if logged_user == user_id or logged_user == canonical:
                return client_sid.strip()

    # 2. Check stored session from voice_profiles.db
    try:
        from pathlib import Path
        import sqlite3
        db_path = Path(__file__).resolve().parent.parent.parent / "voice_profiles.db"
        if db_path.exists():
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT session_id FROM voice_profiles WHERE user_id = ?", (user_id,))
                row = cursor.fetchone()
                if row and row[0]:
                    stored_sid = row[0]
                    sess_check = verify_erpnext_session(stored_sid)
                    if sess_check["is_authenticated"]:
                        return stored_sid
    except Exception:
        pass

    return None
