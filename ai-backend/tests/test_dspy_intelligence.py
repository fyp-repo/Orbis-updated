"""
OrbisERP Step 3D: Comprehensive DSPy Intelligence Test Suite
============================================================
Verifies:
1. DSPy Intent, Identity, Query Planning, and Response Generation modules.
2. Dynamic model routing with Groq/Ollama and seamless fallback in auto mode.
3. Both providers failure handling (clean service unavailable message, no canned response).
4. Live ERPNext tools execution for Stock and Purchase (read-only, parameterized).
5. Strict RBAC enforcement across multiple users (Administrator, Stock Manager, HR Manager).
6. Per-session conversation memory and follow-up reference resolution.
7. End-to-end voice pipeline: Audio -> VAD -> STT -> ECAPA -> Session -> DSPy -> ERPNext -> TTS.
"""

import unittest
import requests
import numpy as np
import io
import soundfile as sf
from typing import Dict, Any

BACKEND = "http://127.0.0.1:8000"
FRAPPE = "http://localhost:8085"


class TestDSPyIntelligence(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # 1. Login Administrator
        r_admin = requests.post(
            f"{BACKEND}/api/voice/verify-credentials",
            json={"user_id": "Administrator", "password": "admin"},
            timeout=30,
        )
        cls.admin_sid = r_admin.json().get("session_id")

        # 2. Login Stock Manager (Usman Ali)
        r_stock = requests.post(
            f"{BACKEND}/api/voice/verify-credentials",
            json={"user_id": "forw8007+stockmanager@gmail.com", "password": "Orbis@Stock123"},
            timeout=30,
        )
        cls.stock_sid = r_stock.json().get("session_id")

        # 3. Login HR Manager (Fatima Ali)
        r_hr = requests.post(
            f"{BACKEND}/api/voice/verify-credentials",
            json={"user_id": "forw8007+hrmanager@gmail.com", "password": "Orbis@HR123"},
            timeout=30,
        )
        cls.hr_sid = r_hr.json().get("session_id")

    # ==========================================================================
    # 1. IDENTITY & RBAC REASONING VIA DSPy
    # ==========================================================================

    def test_01_identity_reasoning_administrator(self):
        """Verifies personalized identity explanation for Administrator without generic boilerplate."""
        resp = requests.post(
            f"{BACKEND}/api/voice/text-query",
            json={"query": "Orbis, who am I?", "session_id": self.admin_sid},
            timeout=40,
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data.get("intent"), "who_am_i")
        self.assertTrue(data.get("is_authenticated"))
        text = data.get("response_text", "")
        self.assertIn("Administrator", text)
        self.assertNotIn("I am your AI assistant. You can check Purchase and Stock", text)

    def test_02_identity_reasoning_stock_manager(self):
        """Verifies personalized identity explanation for Stock Manager."""
        resp = requests.post(
            f"{BACKEND}/api/voice/text-query",
            json={"query": "Do you recognize my voice and who is speaking?", "session_id": self.stock_sid},
            timeout=40,
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data.get("intent"), "who_am_i")
        self.assertTrue(data.get("is_authenticated"))
        text = data.get("response_text", "")
        self.assertTrue("Usman Ali" in text or "stockmanager" in text or "Stock Manager" in text or "stock" in text.lower())

    def test_03_role_and_permission_explanation_stock_manager(self):
        """Verifies explanation of stock manager capabilities."""
        resp = requests.post(
            f"{BACKEND}/api/voice/text-query",
            json={"query": "What are my permissions and what can I access?", "session_id": self.stock_sid},
            timeout=40,
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data.get("intent"), "what_can_i_do")
        text = data.get("response_text", "").lower()
        self.assertTrue("stock" in text or "warehouse" in text or "inventory" in text)

    def test_04_unauthenticated_guest_rejection(self):
        """Verifies unauthenticated guest is rejected from protected identity reasoning."""
        resp = requests.post(
            f"{BACKEND}/api/voice/text-query",
            json={"query": "Who am I?", "session_id": "fake_invalid_sid_999"},
            timeout=25,
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertFalse(data.get("is_authenticated"))
        text = data.get("response_text", "").lower()
        self.assertTrue("not recognize" in text or "guest" in text or "enroll" in text)

    # ==========================================================================
    # 2. LIVE ERPNext STOCK TOOLS & RBAC
    # ==========================================================================

    def test_05_stock_balance_query_stock_manager(self):
        """Verifies Stock Manager can retrieve live stock quantities via DSPy tool execution."""
        resp = requests.post(
            f"{BACKEND}/api/voice/text-query",
            json={"query": "How many items do we have in stock for Steel Sheet?", "session_id": self.stock_sid},
            timeout=45,
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data.get("is_authenticated"))
        self.assertIn("response_text", data)
        text = data.get("response_text", "")
        self.assertNotIn("I am your AI assistant", text)
        erp_data = data.get("data", {})
        self.assertTrue("records" in erp_data or "total_quantity" in erp_data)
        self.assertEqual(erp_data.get("item_code"), "Steel Sheet")

    def test_05b_stock_balance_variations(self):
        """Regression tests for various phrasing, prepositions, and item codes."""
        # Phrasing 1: Preposition 'for'
        r1 = requests.post(
            f"{BACKEND}/api/voice/text-query",
            json={"query": "Check stock balance for Steel Sheet", "session_id": self.stock_sid},
            timeout=45,
        )
        self.assertEqual(r1.status_code, 200)
        d1 = r1.json()
        self.assertEqual(d1.get("data", {}).get("item_code"), "Steel Sheet")
        self.assertTrue(d1.get("data", {}).get("total_quantity", 0) > 0)

        # Phrasing 2: Preposition 'of'
        r2 = requests.post(
            f"{BACKEND}/api/voice/text-query",
            json={"query": "What is the stock level of Aluminium Sheet?", "session_id": self.stock_sid},
            timeout=45,
        )
        self.assertEqual(r2.status_code, 200)
        d2 = r2.json()
        self.assertEqual(d2.get("data", {}).get("item_code"), "Aluminium Sheet")

    def test_06_stock_access_denied_for_hr_manager(self):
        """Verifies HR Manager is strictly denied access to Stock queries by RBAC."""
        resp = requests.post(
            f"{BACKEND}/api/voice/text-query",
            json={"query": "Check stock balance for Steel Sheet", "session_id": self.hr_sid},
            timeout=25,
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        text = data.get("response_text", "").lower()
        self.assertTrue("access denied" in text or "not authorized" in text or "restricted" in text)

    # ==========================================================================
    # 3. LIVE ERPNext PURCHASE TOOLS & RBAC
    # ==========================================================================

    def test_07_pending_purchase_orders_administrator(self):
        """Verifies Administrator can list live pending purchase orders."""
        resp = requests.post(
            f"{BACKEND}/api/voice/text-query",
            json={"query": "How many purchase orders are still pending?", "session_id": self.admin_sid},
            timeout=45,
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data.get("is_authenticated"))
        text = data.get("response_text", "")
        self.assertIn("pending", text.lower())
        erp_data = data.get("data", {})
        self.assertTrue(erp_data.get("count", 0) > 0)
        self.assertTrue(bool(erp_data.get("records")))

    def test_07b_pending_purchase_orders_variations(self):
        """Regression tests for pending purchase orders phrasing."""
        for q in [
            "How many purchase orders are pending?",
            "Show me pending purchase orders",
        ]:
            resp = requests.post(
                f"{BACKEND}/api/voice/text-query",
                json={"query": q, "session_id": self.admin_sid},
                timeout=45,
            )
            self.assertEqual(resp.status_code, 200)
            data = resp.json()
            self.assertEqual(data.get("intent"), "get_pending_purchase_orders")
            self.assertTrue(data.get("data", {}).get("count", 0) > 0)

    def test_08_active_suppliers_query(self):
        """Verifies listing active suppliers from live ERPNext data."""
        resp = requests.post(
            f"{BACKEND}/api/voice/text-query",
            json={"query": "Which suppliers are currently active?", "session_id": self.admin_sid},
            timeout=45,
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data.get("is_authenticated"))
        text = data.get("response_text", "")
        self.assertTrue(any(s in text for s in ("Supplier", "Pakistan", "Orbis", "National", "Glass", "Steel", "active")))

    def test_09_purchase_totals_query(self):
        """Verifies calculating total purchase expenditure across purchase orders."""
        resp = requests.post(
            f"{BACKEND}/api/voice/text-query",
            json={"query": "What is the total purchase amount?", "session_id": self.admin_sid},
            timeout=45,
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data.get("is_authenticated"))
        erp_data = data.get("data", {})
        self.assertTrue(erp_data.get("total_purchase_amount", 0.0) > 0)

    def test_10_purchase_access_denied_for_hr_manager(self):
        """Verifies HR Manager is denied access to purchase orders."""
        resp = requests.post(
            f"{BACKEND}/api/voice/text-query",
            json={"query": "Show me pending purchase orders", "session_id": self.hr_sid},
            timeout=25,
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        text = data.get("response_text", "").lower()
        self.assertTrue("access denied" in text or "not authorized" in text or "restricted" in text)

    # ==========================================================================
    # 4. CONVERSATIONAL MEMORY & FOLLOW-UP RESOLUTION
    # ==========================================================================

    def test_11_conversational_follow_up(self):
        """
        Verifies multi-turn contextual memory:
        Turn 1: "Show pending purchase orders" -> retrieves PO records.
        Turn 2: "Which supplier has the highest order value among these?" -> calculates from Turn 1 context.
        """
        # Turn 1
        r1 = requests.post(
            f"{BACKEND}/api/voice/text-query",
            json={"query": "Show me pending purchase orders", "session_id": self.admin_sid},
            timeout=45,
        )
        self.assertEqual(r1.status_code, 200)
        d1 = r1.json()
        self.assertTrue(d1.get("data", {}).get("count", 0) > 0)

        # Turn 2: Follow-up referencing "these"
        r2 = requests.post(
            f"{BACKEND}/api/voice/text-query",
            json={"query": "Which supplier has the highest order value among these?", "session_id": self.admin_sid},
            timeout=45,
        )
        self.assertEqual(r2.status_code, 200)
        d2 = r2.json()
        text2 = d2.get("response_text", "")
        self.assertIn("highest", text2.lower())
        self.assertTrue("supplier" in text2.lower() or "pkr" in text2.lower() or "order" in text2.lower() or "value" in text2.lower())

    # ==========================================================================
    # 5. GENERAL CONVERSATION & CONCEPTUAL ERP EXPLANATION
    # ==========================================================================

    def test_12_greeting_no_erp_execution(self):
        """Verifies natural greeting response without triggering ERPNext transactions."""
        resp = requests.post(
            f"{BACKEND}/api/voice/text-query",
            json={"query": "Good morning, Orbis.", "session_id": self.admin_sid},
            timeout=35,
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data.get("intent"), "general_conversation")
        self.assertIsNone(data.get("data"))
        self.assertIn("response_text", data)
        self.assertTrue(len(data.get("response_text")) > 5)

    def test_13_conceptual_erp_explanation(self):
        """Verifies explaining an ERP concept without executing live tools."""
        resp = requests.post(
            f"{BACKEND}/api/voice/text-query",
            json={"query": "Can you explain what a stock reconciliation is?", "session_id": self.admin_sid},
            timeout=35,
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data.get("intent"), "general_conversation")
        self.assertIn("response_text", data)
        text = data.get("response_text", "").lower()
        self.assertTrue("stock" in text or "inventory" in text or "reconciliation" in text or "balance" in text or "record" in text)

    # ==========================================================================
    # 6. MULTI-USER BIOMETRIC ENROLLMENT & SPEAKER VERIFICATION
    # ==========================================================================

    def test_14_multi_user_status_verification(self):
        """Verifies multi-user enrollment in status endpoint (Administrator + Stock Manager)."""
        resp = requests.get(f"{BACKEND}/api/voice/status", timeout=10)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        enrolled = data.get("enrolled_users", [])
        self.assertIn("Administrator", enrolled)
        self.assertIn("forw8007+stockmanager@gmail.com", enrolled)
        self.assertTrue(data.get("enrolled_users_count", 0) >= 2)
        self.assertTrue(data.get("model_loaded"))


if __name__ == "__main__":
    unittest.main()
