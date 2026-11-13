"""
OrbisERP DSPy Reasoning Modules
===============================
Implements reusable DSPy modules wrapping signatures for:
1. IntentModule — Natural language intent and entity understanding
2. IdentityModule — Personalized voice identity and RBAC explanation
3. QueryPlanningModule — Dynamic ERPNext tool call mapping
4. ResponseGenerationModule — Conversational answer synthesis from live data
5. GeneralConversationModule — Conversational and conceptual ERP assistance
"""

import dspy
from app.ai.signatures import (
    IntentUnderstanding,
    IdentityUnderstanding,
    ERPNextQueryPlanning,
    ResponseGeneration,
)


class GeneralExplanation(dspy.Signature):
    """
    Answers greetings and conceptual ERP questions (e.g. 'what is stock reconciliation',
    'good morning Orbis') in a friendly, professional female assistant tone without executing ERP tools.
    """
    question: str = dspy.InputField(desc="The user's greeting or general ERP question")
    user_context: str = dspy.InputField(desc="User's authenticated identity and role")
    conversation_history: str = dspy.InputField(desc="Recent conversation turns")

    response: str = dspy.OutputField(desc="Friendly, concise, professional answer (1-2 sentences)")


class IntentModule(dspy.Module):
    """DSPy module for natural language intent and entity extraction."""

    def __init__(self):
        super().__init__()
        self.predict_intent = dspy.Predict(IntentUnderstanding)

    def forward(self, question: str, user_identity: str, conversation_context: str = ""):
        return self.predict_intent(
            question=question,
            user_identity=user_identity,
            conversation_context=conversation_context or "No previous context",
        )


class IdentityModule(dspy.Module):
    """DSPy module for synthesizing personalized identity and authorization explanations."""

    def __init__(self):
        super().__init__()
        self.predict_identity = dspy.Predict(IdentityUnderstanding)

    def forward(
        self,
        user_name: str,
        erpnext_user: str,
        user_roles: str,
        permissions: str,
        question: str,
    ):
        return self.predict_identity(
            user_name=user_name,
            erpnext_user=erpnext_user,
            user_roles=user_roles,
            permissions=permissions,
            question=question,
        )


class QueryPlanningModule(dspy.Module):
    """DSPy module for determining which ERPNext tool to invoke with exact parameters."""

    def __init__(self):
        super().__init__()
        self.predict_plan = dspy.Predict(ERPNextQueryPlanning)

    def forward(
        self,
        question: str,
        authenticated_user: str,
        available_tools: str,
        permission_context: str,
        conversation_history: str = "",
    ):
        return self.predict_plan(
            question=question,
            authenticated_user=authenticated_user,
            available_tools=available_tools,
            permission_context=permission_context,
            conversation_history=conversation_history or "None",
        )


class ResponseGenerationModule(dspy.Module):
    """DSPy module for synthesizing conversational responses from live ERP data."""

    def __init__(self):
        super().__init__()
        self.predict_response = dspy.Predict(ResponseGeneration)

    def forward(
        self,
        question: str,
        erp_data_summary: str,
        conversation_history: str = "",
        user_role_context: str = "",
    ):
        return self.predict_response(
            question=question,
            erp_data_summary=erp_data_summary,
            conversation_history=conversation_history or "None",
            user_role_context=user_role_context,
        )


class GeneralConversationModule(dspy.Module):
    """DSPy module for greetings and conceptual ERP knowledge."""

    def __init__(self):
        super().__init__()
        self.predict_chat = dspy.Predict(GeneralExplanation)

    def forward(self, question: str, user_context: str = "", conversation_history: str = ""):
        return self.predict_chat(
            question=question,
            user_context=user_context or "Standard User",
            conversation_history=conversation_history or "None",
        )
