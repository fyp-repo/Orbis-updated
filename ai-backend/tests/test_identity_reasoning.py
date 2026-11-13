"""
Test Phase 6: Voice Identity & Capability Reasoning Workflow
============================================================
Verifies:
1. "who am I" / "who is speaking" query returns:
   - "I recognize your enrolled voice. Your authenticated ERPNext account is [user]. Your assigned roles are [roles]."
2. "what can I do" / "what are my roles" returns:
   - Role-specific operations (Stock Manager vs HR Manager vs Administrator).
3. Unauthenticated query politely requests enrollment or password verification.
4. Edge-TTS female audio is synthesized in response.
"""

import unittest
import requests

BACKEND = "http://127.0.0.1:8000"


class TestIdentityReasoning(unittest.TestCase):

    def setUp(self):
        # 1. Login Administrator
        r_admin = requests.post(
            f"{BACKEND}/api/voice/verify-credentials",
            json={"user_id": "Administrator", "password": "admin"},
            timeout=10,
        )
        self.admin_sid = r_admin.json().get("session_id")

        # 2. Login Stock Manager
        r_stock = requests.post(
            f"{BACKEND}/api/voice/verify-credentials",
            json={"user_id": "forw8007+stockmanager@gmail.com", "password": "Orbis@Stock123"},
            timeout=10,
        )
        self.stock_sid = r_stock.json().get("session_id")

        # 3. Login HR Manager
        r_hr = requests.post(
            f"{BACKEND}/api/voice/verify-credentials",
            json={"user_id": "forw8007+hrmanager@gmail.com", "password": "Orbis@HR123"},
            timeout=10,
        )
        self.hr_sid = r_hr.json().get("session_id")

    def test_01_who_am_i_administrator(self):
        resp = requests.post(
            f"{BACKEND}/api/voice/text-query",
            json={"query": "Orbis, who am I?", "session_id": self.admin_sid},
            timeout=15,
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data.get("intent"), "who_am_i")
        self.assertTrue(data.get("is_authenticated"))
        text = data.get("response_text", "")
        self.assertIn("Administrator", text)
        self.assertIn("roles are", text.lower())
        self.assertTrue(bool(data.get("audio_base64")))

    def test_02_who_am_i_stock_manager(self):
        resp = requests.post(
            f"{BACKEND}/api/voice/text-query",
            json={"query": "Orbis, who am I?", "session_id": self.stock_sid},
            timeout=15,
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data.get("intent"), "who_am_i")
        self.assertTrue(data.get("is_authenticated"))
        text = data.get("response_text", "")
        self.assertTrue("Usman Ali" in text or "stockmanager" in text)
        self.assertIn("roles are", text.lower())

    def test_03_what_can_i_do_stock_manager(self):
        resp = requests.post(
            f"{BACKEND}/api/voice/text-query",
            json={"query": "Orbis, what can I do?", "session_id": self.stock_sid},
            timeout=15,
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data.get("intent"), "what_can_i_do")
        text = data.get("response_text", "").lower()
        self.assertIn("stock", text)
        self.assertTrue("warehouse" in text or "balance" in text or "inventory" in text)

    def test_04_what_can_i_do_hr_manager(self):
        resp = requests.post(
            f"{BACKEND}/api/voice/text-query",
            json={"query": "What are my permissions and what can I do?", "session_id": self.hr_sid},
            timeout=15,
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data.get("intent"), "what_can_i_do")
        text = data.get("response_text", "").lower()
        self.assertTrue("human resources" in text or "hr" in text or "employee" in text or "leave" in text)

    def test_05_unauthenticated_identity_query(self):
        resp = requests.post(
            f"{BACKEND}/api/voice/text-query",
            json={"query": "Orbis, who am I?", "session_id": "invalid_session_id_999"},
            timeout=15,
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertFalse(data.get("is_authenticated"))
        text = data.get("response_text", "").lower()
        self.assertTrue("not authenticated" in text or "enroll" in text or "recognize" in text)


if __name__ == "__main__":
    unittest.main()
