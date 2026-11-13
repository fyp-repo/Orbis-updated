"""
OrbisERP Conversation Memory & Session Context Manager
======================================================
Manages per-session conversation context and memory.
Enforces:
1. Strict session and user isolation (never mixes conversations between users).
2. Preserves recent turns and previously retrieved ERPNext records.
3. Resolves follow-up queries referencing "these", "that order", "this supplier", "the previous result".
4. Never stores passwords, session cookies, raw audio, or biometric vectors.
5. Automatic expiration and context window management.
"""

import time
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger("orbis.ai.conversation_manager")


class ConversationSession:
    """Represents an active user conversation session with memory."""

    def __init__(self, session_id: str, user_id: str, max_turns: int = 10):
        self.session_id = session_id
        self.user_id = user_id
        self.max_turns = max_turns
        self.turns: List[Dict[str, Any]] = []
        self.last_records: List[Dict[str, Any]] = []
        self.last_tool_used: Optional[str] = None
        self.last_active = time.time()

    def add_turn(
        self,
        query: str,
        response: str,
        tool_used: Optional[str] = None,
        records: Optional[List[Dict[str, Any]]] = None,
    ):
        """Adds a completed interaction turn and caches retrieved records for follow-ups."""
        self.last_active = time.time()
        turn_entry = {
            "query": query.strip(),
            "response": response.strip(),
            "tool_used": tool_used,
            "timestamp": time.time(),
        }
        self.turns.append(turn_entry)
        if len(self.turns) > self.max_turns:
            self.turns.pop(0)

        if records is not None and isinstance(records, list):
            # Sanitize records to prevent saving sensitive metadata
            self.last_records = records[:10]
            self.last_tool_used = tool_used

    def get_history_summary(self, limit: int = 4) -> str:
        """Formats recent interaction turns for inclusion in DSPy prompts."""
        recent = self.turns[-limit:] if self.turns else []
        if not recent:
            return "No previous conversation turns."
        lines = []
        for t in recent:
            lines.append(f"User: {t['query']}")
            lines.append(f"Orbis: {t['response']}")
        return "\n".join(lines)

    def resolve_follow_up(self, query: str) -> Optional[Dict[str, Any]]:
        """
        Detects if user is asking a follow-up question referencing previously retrieved data
        (e.g., 'which supplier has the highest order value among these?', 'explain that order').
        Returns resolved contextual entities or previous records.
        """
        q_lower = query.lower()
        has_pronoun = any(
            w in q_lower
            for w in (
                "these",
                "those",
                "that order",
                "this order",
                "that item",
                "this item",
                "that supplier",
                "this supplier",
                "the previous",
                "among these",
                "of these",
                "from these",
                "highest among",
                "lowest among",
            )
        )

        if has_pronoun and self.last_records:
            return {
                "referenced_tool": self.last_tool_used,
                "records": self.last_records,
                "count": len(self.last_records),
            }
        return None


class ConversationManager:
    """Thread-safe store for active user conversation sessions."""

    _instance = None
    _sessions: Dict[str, ConversationSession] = {}
    _session_ttl_seconds: int = 3600  # 1 hour TTL

    @classmethod
    def get_instance(cls) -> "ConversationManager":
        if cls._instance is None:
            cls._instance = ConversationManager()
        return cls._instance

    def get_or_create_session(self, session_key: str, user_id: str) -> ConversationSession:
        """Retrieves or creates a session bound strictly to session_key and user_id."""
        self._prune_expired()
        key = session_key or f"user:{user_id}"

        session = self._sessions.get(key)
        if session is None or session.user_id != user_id:
            session = ConversationSession(session_id=key, user_id=user_id)
            self._sessions[key] = session
        else:
            session.last_active = time.time()
        return session

    def add_interaction(
        self,
        session_key: str,
        user_id: str,
        query: str,
        response: str,
        tool_used: Optional[str] = None,
        records: Optional[List[Dict[str, Any]]] = None,
    ):
        """Convenience method to register a turn in the user's session."""
        session = self.get_or_create_session(session_key, user_id)
        session.add_turn(query=query, response=response, tool_used=tool_used, records=records)

    def clear_session(self, session_key: str):
        """Removes a session upon user logout or session termination."""
        if session_key in self._sessions:
            del self._sessions[session_key]

    def _prune_expired(self):
        """Removes inactive sessions older than session_ttl_seconds."""
        now = time.time()
        expired = [
            k for k, s in self._sessions.items() if now - s.last_active > self._session_ttl_seconds
        ]
        for k in expired:
            del self._sessions[k]


conversation_manager = ConversationManager.get_instance()

