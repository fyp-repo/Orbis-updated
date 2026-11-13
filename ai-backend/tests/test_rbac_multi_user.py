"""
Test Acceptance: Multi-User RBAC & Independent Authentication Verification
==========================================================================
Verifies:
1. Administrator independently authenticates and accesses Stock queries.
2. Normal enabled user (Stock Manager) independently authenticates with their own credentials
   and accesses Stock queries using their own Frappe session (never shared admin token).
3. Normal enabled user (HR Manager) independently authenticates with their own credentials
   and is strictly denied access to Stock queries.
4. Unauthorized users / Guests cannot access protected ERPNext endpoints.
"""

import unittest
import requests

BACKEND = "http://127.0.0.1:8000"
FRAPPE = "http://localhost:8085"


class TestRBACMultiUser(unittest.TestCase):

    def test_01_administrator_auth_and_stock_access(self):
        """Verifies Administrator authenticates and accesses stock."""
        r = requests.post(
            f"{BACKEND}/api/voice/verify-credentials",
            json={"user_id": "Administrator", "password": "admin"},
            timeout=8,
        )
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertTrue(data.get("is_valid"))
        self.assertEqual(data.get("user_id"), "Administrator")
        sid = data.get("session_id")
        self.assertTrue(bool(sid))

        # Query stock
        q_resp = requests.post(
            f"{BACKEND}/api/voice/text-query",
            json={"query": "check stock for sedan", "session_id": sid},
            timeout=15,
        )
        self.assertEqual(q_resp.status_code, 200)
        q_data = q_resp.json()
        self.assertEqual(q_data.get("intent"), "check_stock")
        self.assertTrue(q_data.get("is_authenticated"))
        self.assertIn("records", q_data.get("data", {}) or {})

    def test_02_stock_manager_auth_and_stock_access(self):
        """Verifies normal enabled user (Stock Manager) authenticates and accesses stock."""
        user = "forw8007+stockmanager@gmail.com"
        pwd = "Orbis@Stock123"

        r = requests.post(
            f"{BACKEND}/api/voice/verify-credentials",
            json={"user_id": user, "password": pwd},
            timeout=8,
        )
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertTrue(data.get("is_valid"))
        self.assertEqual(data.get("user_id"), user)
        self.assertEqual(data.get("full_name"), "Usman Ali")
        sid = data.get("session_id")
        self.assertTrue(bool(sid))

        # Query stock using the Stock Manager's authentic session
        q_resp = requests.post(
            f"{BACKEND}/api/voice/text-query",
            json={"query": "check stock for sedan", "session_id": sid},
            timeout=15,
        )
        self.assertEqual(q_resp.status_code, 200)
        q_data = q_resp.json()
        self.assertEqual(q_data.get("intent"), "check_stock")
        self.assertTrue(q_data.get("is_authenticated"))
        self.assertEqual(q_data.get("user_id"), user)
        self.assertIn("records", q_data.get("data", {}) or {})

    def test_03_hr_manager_auth_and_stock_denial(self):
        """Verifies normal enabled user (HR Manager) authenticates but is denied stock access."""
        user = "forw8007+hrmanager@gmail.com"
        pwd = "Orbis@HR123"

        r = requests.post(
            f"{BACKEND}/api/voice/verify-credentials",
            json={"user_id": user, "password": pwd},
            timeout=15,
        )
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertTrue(data.get("is_valid"))
        self.assertEqual(data.get("user_id"), user)
        self.assertEqual(data.get("full_name"), "Fatima Ali")
        sid = data.get("session_id")
        self.assertTrue(bool(sid))

        # Query stock using the HR Manager's authentic session
        q_resp = requests.post(
            f"{BACKEND}/api/voice/text-query",
            json={"query": "check stock for sedan", "session_id": sid},
            timeout=15,
        )
        self.assertEqual(q_resp.status_code, 200)
        q_data = q_resp.json()
        self.assertEqual(q_data.get("intent"), "check_stock")
        self.assertTrue(q_data.get("is_authenticated"))
        self.assertEqual(q_data.get("user_id"), user)
        # MUST BE STRICTLY REJECTED BY RBAC
        self.assertEqual(q_data.get("data", {}).get("error"), "RBAC_RESTRICTED")
        self.assertIn("Access denied", q_data.get("response_text", ""))

    def test_04_guest_and_unauthenticated_rejection(self):
        """Verifies Guest or forged session is strictly denied stock access."""
        q_resp = requests.post(
            f"{BACKEND}/api/voice/text-query",
            json={"query": "check stock for sedan", "session_id": "forged_invalid_sid_99999"},
            timeout=15,
        )
        self.assertEqual(q_resp.status_code, 200)
        q_data = q_resp.json()
        self.assertFalse(q_data.get("is_authenticated"))
        self.assertEqual(q_data.get("user_id"), "Guest")
        self.assertEqual(q_data.get("data", {}).get("error"), "RBAC_RESTRICTED")
        self.assertIn("Guest", q_data.get("response_text", ""))


if __name__ == "__main__":
    unittest.main()
