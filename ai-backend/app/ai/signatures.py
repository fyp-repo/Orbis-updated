"""
OrbisERP DSPy Signatures Module
===============================
Defines typed DSPy Signatures for:
1. IntentUnderstanding — Parsing natural questions, entities, and required modules
2. IdentityUnderstanding — Explaining authenticated user role and ERPNext RBAC
3. ERPNextQueryPlanning — Mapping questions to parameterized ERPNext tool calls
4. ResponseGeneration — Synthesizing natural, conversational, female-voiced responses
"""

import dspy


class IntentUnderstanding(dspy.Signature):
    """
    Analyzes the user's natural language question and determines the intent,
    extracted entity (item, warehouse, or order ID), and relevant ERP module.
    """
    question: str = dspy.InputField(desc="The user's actual question")
    user_identity: str = dspy.InputField(desc="The authenticated ERPNext username")
    conversation_context: str = dspy.InputField(desc="Recent conversation turns")

    intent: str = dspy.OutputField(desc="check_stock, list_items, check_warehouse, list_purchase_orders, pending_purchase_orders, list_suppliers, purchase_totals, who_am_i, what_can_i_do, or general_conversation")
    entities: str = dspy.OutputField(desc="Extracted item code, warehouse name, or PO number, or empty string")
    relevant_module: str = dspy.OutputField(desc="Stock, Purchase, Identity, or General")
    requires_live_data: str = dspy.OutputField(desc="'True' for ERP queries, 'False' for general chat")


class IdentityUnderstanding(dspy.Signature):
    """
    Explains the authenticated user account, assigned enterprise roles, and access permissions in natural conversational language.
    """
    user_name: str = dspy.InputField(desc="User's display name or email")
    erpnext_user: str = dspy.InputField(desc="Authenticated Frappe account ID")
    user_roles: str = dspy.InputField(desc="Assigned ERPNext enterprise roles")
    permissions: str = dspy.InputField(desc="Permitted operations and module restrictions")
    question: str = dspy.InputField(desc="The user's question regarding their identity or permissions")

    response: str = dspy.OutputField(desc="Natural, concise conversational response confirming their identity and roles (1-2 sentences, female assistant voice)")


class ERPNextQueryPlanning(dspy.Signature):
    """
    Selects the exact ERPNext tool and parameters based on the user's question and permissions.
    """
    question: str = dspy.InputField(desc="The user's question")
    authenticated_user: str = dspy.InputField(desc="The authenticated ERPNext user ID")
    available_tools: str = dspy.InputField(desc="List of available ERPNext tool names and descriptions")
    permission_context: str = dspy.InputField(desc="User's permitted modules and roles")
    conversation_history: str = dspy.InputField(desc="Recent conversation context")

    tool_name: str = dspy.OutputField(desc="Exact tool name from available_tools")
    arguments_json: str = dspy.OutputField(desc="JSON dictionary of tool arguments, e.g. {'item_code': 'Steel Sheet'}")


class ResponseGeneration(dspy.Signature):
    """
    Generates an accurate, natural conversational answer from live ERPNext data.
    Directly answers the user's question with facts from the data without repetitive introductory filler.
    """
    question: str = dspy.InputField(desc="The user's original question")
    erp_data_summary: str = dspy.InputField(desc="Live ERPNext data summary or records")
    conversation_history: str = dspy.InputField(desc="Recent conversation turns")
    user_role_context: str = dspy.InputField(desc="User identity and assigned roles")

    answer: str = dspy.OutputField(desc="Accurate, concise conversational answer (1-2 sentences)")
