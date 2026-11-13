"""
OrbisERP Voice Pipeline — Intent Router & Conversational AI Integration
========================================================================
Delegates conversational reasoning, live ERPNext tool execution, and RBAC
validation to the DSPy Reasoning Engine (app.ai.reasoning_engine).
Preserves existing method signatures and API compatibility.
"""

from typing import Dict, Any, Optional
from app.ai.reasoning_engine import reasoning_engine


class IntentRouter:
    """
    Adapter routing incoming speech / text queries to the DSPy Reasoning Engine.
    Enforces user RBAC both pre-call and natively via Frappe user session.
    NEVER uses a shared Administrator API token on behalf of other users.
    """

    def __init__(self):
        self.engine = reasoning_engine

    def process_query(
        self, query_text: str, authenticated_user: str, session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Dispatches query through the DSPy Conversational AI engine.
        Returns structured dictionary with intent, response_text, data, and auth status.
        """
        return self.engine.process_query(
            query_text=query_text,
            authenticated_user=authenticated_user,
            session_id=session_id,
        )


intent_router = IntentRouter()
