"""
OrbisERP DSPy Conversational Reasoning Engine
=============================================
Orchestrates:
1. ModelRouter for Groq cloud and Ollama local inference with fallback.
2. ConversationManager for per-session memory and follow-up reference resolution.
3. DSPy Modules (Intent, Identity, QueryPlanning, ResponseGeneration, GeneralConversation).
4. ERPNext Live Tools with strict user-bound Frappe RBAC validation.
5. Natural conversational responses without robotic or generic repetition.
"""

import json
import logging
import re
from typing import Any, Dict, List, Optional
from app.core.config import settings
from app.core.security import (
    check_user_stock_permission,
    check_user_purchase_permission,
    get_user_roles,
    check_erpnext_user_exists,
)
from app.ai.model_router import ModelRouter, ReasoningServiceUnavailableError
from app.ai.conversation_manager import conversation_manager
from app.ai.modules import (
    IntentModule,
    IdentityModule,
    QueryPlanningModule,
    ResponseGenerationModule,
    GeneralConversationModule,
)
from app.ai.erp_tools import TOOL_REGISTRY, TOOL_DESCRIPTIONS, execute_tool

logger = logging.getLogger("orbis.ai.reasoning_engine")


class ReasoningEngine:
    """Central conversational reasoning coordinator powered by DSPy."""

    def __init__(self):
        self.router = ModelRouter()
        self.intent_module = IntentModule()
        self.identity_module = IdentityModule()
        self.query_planner = QueryPlanningModule()
        self.response_generator = ResponseGenerationModule()
        self.general_chat = GeneralConversationModule()

    def _get_user_permission_summary(self, user_id: str, roles: List[str]) -> str:
        """Constructs an accurate permission summary based on actual Frappe roles."""
        if not user_id or user_id == "Guest":
            return "Unauthenticated Guest. No ERP operations permitted."

        canonical = check_erpnext_user_exists(user_id).get("canonical_user_id", user_id)
        if canonical == "Administrator" or "System Manager" in roles:
            return "Full Administrative privileges across all Orbis ERP modules including Stock, Purchasing, and System Management."

        allowed = []
        restricted = []

        stock_perm = check_user_stock_permission(user_id)
        if stock_perm.allowed:
            allowed.append("Automotive Stock Balances, Warehouse inventory inspection, Item catalogue")
        else:
            restricted.append("Stock and Inventory operations")

        purch_perm = check_user_purchase_permission(user_id)
        if purch_perm.allowed:
            allowed.append("Purchase Orders, Vendor/Supplier catalogue, and Purchase Invoices")
        else:
            restricted.append("Purchase and Procurement operations")

        if "HR Manager" in roles or "HR User" in roles:
            allowed.append("Human Resources, Employee directory, and Leave applications")

        summary = ""
        if allowed:
            summary += f"Permitted access: {'; '.join(allowed)}. "
        if restricted:
            summary += f"Restricted access: {'; '.join(restricted)}. "
        return summary.strip()

    def process_query(
        self,
        query_text: str,
        authenticated_user: str,
        session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Executes full DSPy Conversational AI pipeline:
        1. Contextual session resolution
        2. Natural Language Intent & Entity extraction
        3. Identity Reasoning or Live ERPNext Tool Planning & Execution
        4. Conversational Response Generation
        """
        query_clean = (query_text or "").strip()
        if not query_clean:
            return {
                "intent": "empty",
                "response_text": "I'm listening. How can I help you with Orbis ERP?",
                "data": None,
                "is_authenticated": bool(authenticated_user and authenticated_user != "Guest"),
                "provider_used": "none",
            }

        # 1. Resolve User and Role Context
        session_key = session_id or f"user:{authenticated_user}"
        user_info = check_erpnext_user_exists(authenticated_user)
        full_name = user_info.get("full_name") or authenticated_user
        roles = get_user_roles(authenticated_user)
        filtered_roles = [r for r in roles if r not in ("All", "Guest", "Blogger", "Customer", "Supplier")]
        roles_str = ", ".join(filtered_roles) if filtered_roles else "User"
        perm_summary = self._get_user_permission_summary(authenticated_user, roles)

        # 2. Retrieve Conversation Context
        session_ctx = conversation_manager.get_or_create_session(session_key, authenticated_user)
        history_summary = session_ctx.get_history_summary(limit=4)
        follow_up_data = session_ctx.resolve_follow_up(query_clean)

        provider_used = "dspy"

        try:
            # 3. Fast Deterministic Intent Pre-check for Identity & Permissions
            # (Allows instant zero-latency routing for standard identity queries, but generates natural responses via DSPy)
            q_lower = query_clean.lower()
            is_identity_query = any(
                p in q_lower
                for p in (
                    "who am i",
                    "who is speaking",
                    "my identity",
                    "recognize my voice",
                    "do you recognize me",
                    "what is my name",
                    "identify me",
                )
            )
            is_role_or_perm_query = any(
                p in q_lower
                for p in (
                    "what is my role",
                    "what are my roles",
                    "what can i do",
                    "what am i allowed to access",
                    "what are my permissions",
                    "what is my authorization",
                    "my access level",
                    "can i access purchase",
                    "can i access stock",
                )
            )

            # ==================================================================
            # BRANCH 1: Identity & Permission Understanding
            # ==================================================================
            if is_identity_query or is_role_or_perm_query:
                if not authenticated_user or authenticated_user == "Guest":
                    spoken = (
                        "I do not recognize your voice identity. You are currently connected as Guest. "
                        "Please complete voice enrollment or log in to access your ERPNext account."
                    )
                    return {
                        "intent": "who_am_i" if is_identity_query else "what_can_i_do",
                        "response_text": spoken,
                        "data": {"user": "Guest", "is_authenticated": False},
                        "is_authenticated": False,
                        "provider_used": "security_guardrail",
                    }

                # Generate personalized natural explanation using IdentityModule
                def _run_identity():
                    return self.identity_module(
                        user_name=full_name,
                        erpnext_user=authenticated_user,
                        user_roles=roles_str,
                        permissions=perm_summary,
                        question=query_clean,
                    )

                id_res, provider_used = self.router.execute_with_fallback(_run_identity)
                answer = getattr(id_res, "response", None) or getattr(id_res, "conversational_response", "")

                # Clean up answer
                if not answer or len(answer.strip()) < 10:
                    answer = f"I recognize your enrolled voice. You are logged in as {full_name}, and your ERPNext account has the {roles_str} roles. {perm_summary}"

                intent_name = "who_am_i" if is_identity_query else "what_can_i_do"
                conversation_manager.add_interaction(
                    session_key, authenticated_user, query_clean, answer, tool_used=intent_name
                )
                return {
                    "intent": intent_name,
                    "response_text": answer,
                    "data": {
                        "user_id": authenticated_user,
                        "full_name": full_name,
                        "roles": filtered_roles,
                        "permissions": perm_summary,
                    },
                    "is_authenticated": True,
                    "provider_used": provider_used,
                }

            # ==================================================================
            # BRANCH 2: Conversational Follow-Up over Cached Records
            # (e.g. "which supplier has the highest order value among these?")
            # ==================================================================
            if follow_up_data and ("highest" in q_lower or "lowest" in q_lower or "which supplier" in q_lower or "total" in q_lower):
                records = follow_up_data.get("records", [])
                if records:
                    # Sort or aggregate based on query
                    if "highest" in q_lower and any("grand_total" in r for r in records):
                        highest_rec = max(records, key=lambda x: float(x.get("grand_total", 0.0)))
                        sup = highest_rec.get("supplier") or highest_rec.get("name")
                        amt = float(highest_rec.get("grand_total", 0.0))
                        curr = highest_rec.get("currency", "PKR")
                        answer = f"Among the previously retrieved purchase orders, {sup} has the highest order value of {amt:,.2f} {curr}."
                        conversation_manager.add_interaction(
                            session_key, authenticated_user, query_clean, answer, tool_used="follow_up", records=records
                        )
                        return {
                            "intent": "follow_up_query",
                            "response_text": answer,
                            "data": {"highest_record": highest_rec, "records": records},
                            "is_authenticated": True,
                            "provider_used": "conversational_memory",
                        }

            # ==================================================================
            # BRANCH 3: Intent Classification & Routing
            # ==================================================================
            # Fast pattern rules (Specific Purchase intents strictly prioritized before generic Stock)
            if any(w in q_lower for w in (
                "pending purchase order", "pending purchase orders", "purchase orders are pending",
                "purchase orders are still pending", "orders are still pending", "orders pending",
                "pending orders", "orders are pending"
            )):
                predicted_intent = "get_pending_purchase_orders"
                requires_live_data = True
                relevant_module = "Purchase"
                provider_used = "pattern_router"
            elif any(w in q_lower for w in (
                "purchase orders", "purchase order", "show purchase orders", "list purchase orders", "all purchase orders"
            )):
                predicted_intent = "list_purchase_orders"
                requires_live_data = True
                relevant_module = "Purchase"
                provider_used = "pattern_router"
            elif any(w in q_lower for w in ("active suppliers", "list suppliers", "all suppliers", "suppliers", "vendor", "vendors")):
                predicted_intent = "list_suppliers"
                requires_live_data = True
                relevant_module = "Purchase"
                provider_used = "pattern_router"
            elif any(w in q_lower for w in ("total purchase", "purchase amount", "purchase total", "total spent on purchase", "purchase expenditure")):
                predicted_intent = "get_purchase_totals"
                requires_live_data = True
                relevant_module = "Purchase"
                provider_used = "pattern_router"
            elif any(w in q_lower for w in ("purchase invoice", "purchase invoices", "pending invoices")):
                predicted_intent = "get_purchase_invoices"
                requires_live_data = True
                relevant_module = "Purchase"
                provider_used = "pattern_router"
            elif any(w in q_lower for w in ("warehouses", "which warehouse", "warehouse list", "list warehouses", "all warehouses")):
                predicted_intent = "list_warehouses"
                requires_live_data = True
                relevant_module = "Stock"
                provider_used = "pattern_router"
            elif any(w in q_lower for w in ("stock ledger", "stock entry", "stock movement", "stock transactions")):
                predicted_intent = "stock_ledger"
                requires_live_data = True
                relevant_module = "Stock"
                provider_used = "pattern_router"
            elif any(w in q_lower for w in (
                "stock balance", "in stock", "stock level", "quantity of", "inventory of",
                "how many items", "how many units", "check stock", "stock of", "stock for"
            )):
                predicted_intent = "check_stock"
                requires_live_data = True
                relevant_module = "Stock"
                provider_used = "pattern_router"
            elif any(w in q_lower for w in ("what is a stock reconciliation", "explain stock reconciliation", "what is stock reconciliation", "what is a purchase order", "can you explain", "explain what")):
                predicted_intent = "general_conversation"
                requires_live_data = False
                provider_used = "conversational_router"
            elif any(w in q_lower for w in ("good morning", "good afternoon", "good evening", "hello", "hi orbis", "hey orbis")):
                predicted_intent = "general_conversation"
                requires_live_data = False
                provider_used = "conversational_router"
            elif "stock" in q_lower or ("how many" in q_lower and "order" not in q_lower and "supplier" not in q_lower):
                predicted_intent = "check_stock"
                requires_live_data = True
                relevant_module = "Stock"
                provider_used = "pattern_router"
            else:
                # Fallback to DSPy IntentModule
                def _run_intent():
                    return self.intent_module(
                        question=query_clean,
                        user_identity=f"{full_name} ({authenticated_user})",
                        conversation_context=history_summary,
                    )
                intent_pred, provider_used = self.router.execute_with_fallback(_run_intent)
                predicted_intent = (getattr(intent_pred, "intent", "") or "general_conversation").lower().strip()
                relevant_module = getattr(intent_pred, "relevant_module", "General").capitalize()
                requires_live_data = getattr(intent_pred, "requires_live_data", "False").lower() in ("true", "1", "yes")

            # ==================================================================
            # BRANCH 4: General Conversation / Greetings / Conceptual ERP Explanations
            # ==================================================================
            if predicted_intent in ("general_conversation", "clarification") and not requires_live_data:
                # Fast greeting dispatch to eliminate latency
                if any(w in q_lower for w in ("good morning", "good afternoon", "good evening", "hello", "hi orbis", "hey orbis")):
                    greeting_text = f"Good day, {full_name}. I am Orbis, your voice assistant for Orbis Automobile Manufacturing. How can I assist you with your operations today?"
                    conversation_manager.add_interaction(
                        session_key, authenticated_user, query_clean, greeting_text, tool_used="general_chat"
                    )
                    return {
                        "intent": "general_conversation",
                        "response_text": greeting_text,
                        "data": None,
                        "is_authenticated": (authenticated_user != "Guest"),
                        "provider_used": "direct_conversational_response",
                    }

                def _run_general():
                    return self.general_chat(
                        question=query_clean,
                        user_context=f"{full_name}, {roles_str}",
                        conversation_history=history_summary,
                    )

                chat_res, provider_used = self.router.execute_with_fallback(_run_general)
                answer = getattr(chat_res, "response", "") or "I am Orbis, your ERP assistant. How can I assist you with your operations today?"
                conversation_manager.add_interaction(
                    session_key, authenticated_user, query_clean, answer, tool_used="general_chat"
                )
                return {
                    "intent": "general_conversation",
                    "response_text": answer,
                    "data": None,
                    "is_authenticated": (authenticated_user != "Guest"),
                    "provider_used": provider_used,
                }

            # ==================================================================
            # BRANCH 5: Live ERPNext Tool Planning & Execution (Stock & Purchase)
            # ==================================================================
            # 5a. RBAC Verification
            if relevant_module == "Stock" or predicted_intent in ("check_stock", "list_items", "check_warehouse", "stock_ledger"):
                perm = check_user_stock_permission(authenticated_user)
                if not perm.allowed:
                    spoken = f"Access denied. Your account '{authenticated_user}' is not authorized to access Stock Balance or Inventory records."
                    return {
                        "intent": predicted_intent,
                        "response_text": spoken,
                        "data": {"error": "RBAC_RESTRICTED", "message": perm.reason},
                        "is_authenticated": (authenticated_user != "Guest"),
                        "provider_used": provider_used,
                    }

            if relevant_module == "Purchase" or predicted_intent in ("list_purchase_orders", "get_pending_purchase_orders", "list_suppliers", "get_purchase_totals", "get_purchase_invoices"):
                perm = check_user_purchase_permission(authenticated_user)
                if not perm.allowed:
                    spoken = f"Access denied. Your account '{authenticated_user}' is not authorized to access Purchase orders or procurement records."
                    return {
                        "intent": predicted_intent,
                        "response_text": spoken,
                        "data": {"error": "RBAC_RESTRICTED", "message": perm.reason},
                        "is_authenticated": (authenticated_user != "Guest"),
                        "provider_used": provider_used,
                    }

            # 5b. Tool Query Planning & Robust Entity Extraction
            direct_tool_map = {
                "check_stock": "get_stock_balance",
                "list_items": "search_items",
                "check_warehouse": "list_warehouses",
                "stock_ledger": "get_stock_ledger",
                "list_purchase_orders": "list_purchase_orders",
                "get_pending_purchase_orders": "get_pending_purchase_orders",
                "pending_purchase_orders": "get_pending_purchase_orders",
                "list_suppliers": "list_suppliers",
                "get_purchase_totals": "get_purchase_totals",
                "purchase_totals": "get_purchase_totals",
                "get_purchase_invoices": "get_purchase_invoices",
            }

            tool_name = None
            tool_args = {}

            def _extract_item_code(q: str) -> Optional[str]:
                # 1. Match 'for <item>' or 'of <item>'
                m1 = re.search(r'(?:for|of)\s+([a-zA-Z0-9\s\-]+?)(?:\s+in\s+stock|\s+do\s+we|\?|\.|$)', q, re.IGNORECASE)
                if m1:
                    it = m1.group(1).strip()
                    it = re.sub(r'^(?:the|our|an|a)\s+', '', it, flags=re.IGNORECASE).strip()
                    if it and it.lower() not in ('sale', 'purchase', 'inventory', 'stock', 'warehouse', 'items', 'item', 'units', 'unit'):
                        return it

                # 2. Match after 'stock' or 'quantity'
                m2 = re.search(r'(?:stock|quantity|balance|level)\s+(?:of|for|on)?\s*([a-zA-Z0-9\s\-]+?)(?:\s+in\s+stock|\?|\.|$)', q, re.IGNORECASE)
                if m2:
                    it = m2.group(1).strip()
                    it = re.sub(r'^(?:the|our|an|a)\s+', '', it, flags=re.IGNORECASE).strip()
                    if it and it.lower() not in ('sale', 'purchase', 'inventory', 'stock', 'warehouse', 'items', 'item', 'units', 'unit'):
                        return it

                # 3. Strip stop phrases and clean up
                cleaned = re.sub(r'(?i)\b(how\s+many\s+items?|how\s+many\s+units?|how\s+many|do\s+we\s+have|in\s+stock|check\s+stock\s+balance|check\s+stock|stock\s+balance|stock\s+level|what\s+is\s+the|what\s+is|available|currently|units?|items?|orbis)\b', '', q)
                cleaned = re.sub(r'[^\w\s\-]', ' ', cleaned).strip()
                words = [w for w in cleaned.split() if w.lower() not in ('for', 'of', 'in', 'the', 'a', 'an', 'at', 'on', 'to')]
                return ' '.join(words) if words else None

            if predicted_intent in direct_tool_map:
                tool_name = direct_tool_map[predicted_intent]
                if tool_name in ("get_stock_balance", "get_item_details"):
                    extracted = _extract_item_code(query_clean)
                    if extracted:
                        tool_args["item_code"] = extracted
            else:
                def _run_plan():
                    return self.query_planner(
                        question=query_clean,
                        authenticated_user=authenticated_user,
                        available_tools=TOOL_DESCRIPTIONS,
                        permission_context=perm_summary,
                        conversation_history=history_summary,
                    )

                plan_res, provider_used = self.router.execute_with_fallback(_run_plan)
                tool_name = (getattr(plan_res, "tool_name", "") or "").strip()
                args_str = getattr(plan_res, "arguments_json", "{}") or "{}"

                try:
                    m = re.search(r"\{.*\}", args_str, re.DOTALL)
                    if m:
                        tool_args = json.loads(m.group(0))
                    else:
                        tool_args = json.loads(args_str)
                except Exception:
                    tool_args = {}

                if tool_name not in TOOL_REGISTRY:
                    tool_name = direct_tool_map.get(predicted_intent, "get_stock_balance")

                if tool_name in ("get_stock_balance", "get_item_details") and not tool_args.get("item_code"):
                    extracted = _extract_item_code(query_clean)
                    if extracted:
                        tool_args["item_code"] = extracted

            # 5c. Execute Live Tool
            tool_result = execute_tool(tool_name, tool_args, authenticated_user, session_id=session_id)

            if not tool_result.get("success"):
                err_msg = tool_result.get("message", "Could not complete operation.")
                return {
                    "intent": predicted_intent,
                    "response_text": f"ERPNext query failed: {err_msg}",
                    "data": tool_result,
                    "is_authenticated": True,
                    "provider_used": provider_used,
                }

            # 5d. Synthesize Conversational Answer using ResponseGenerationModule
            records = tool_result.get("records") or tool_result.get("record") or []
            data_summary = json.dumps(tool_result, default=str)[:800]

            def _run_response():
                return self.response_generator(
                    question=query_clean,
                    erp_data_summary=data_summary,
                    conversation_history=history_summary,
                    user_role_context=f"{full_name} ({roles_str})",
                )

            resp_gen, provider_used = self.router.execute_with_fallback(_run_response)
            answer = getattr(resp_gen, "answer", "") or ""

            # Ensure answer is not empty or generic
            if not answer or len(answer.strip()) < 10:
                if tool_name == "get_stock_balance":
                    tot = tool_result.get("total_quantity", 0)
                    itm = tool_args.get("item_code") or "the requested item"
                    answer = f"We currently have {tot:.1f} units of {itm} in stock across active warehouses."
                elif tool_name == "get_pending_purchase_orders":
                    cnt = tool_result.get("count", 0)
                    tot = tool_result.get("total_pending_amount", 0.0)
                    answer = f"There are currently {cnt} pending purchase orders awaiting receipt or billing, with a total pending amount of PKR {tot:,.2f}."
                elif tool_name == "list_suppliers":
                    cnt = tool_result.get("count", 0)
                    names = [r.get("supplier_name") or r.get("name") for r in records[:5]]
                    answer = f"Orbis ERP has {cnt} registered active suppliers, including {', '.join(names)}."
                else:
                    answer = f"Query completed. Found {tool_result.get('count', 0)} matching records."

            # Register interaction in conversation memory
            cached_records = records if isinstance(records, list) else [records]
            conversation_manager.add_interaction(
                session_key, authenticated_user, query_clean, answer, tool_used=tool_name, records=cached_records
            )

            return {
                "status": "success",
                "intent": predicted_intent,
                "tool": tool_name,
                "response_text": answer,
                "data": tool_result,
                "is_authenticated": True,
                "provider_used": provider_used,
            }

        except ReasoningServiceUnavailableError as e:
            return {
                "status": "error",
                "intent": "service_unavailable",
                "response_text": str(e),
                "data": {"error": "SERVICE_UNAVAILABLE"},
                "is_authenticated": (authenticated_user != "Guest"),
                "provider_used": "none",
            }
        except Exception as e:
            logger.exception(f"Unexpected reasoning engine error: {e}")
            return {
                "status": "error",
                "intent": "error",
                "response_text": f"An unexpected error occurred during reasoning: {e}",
                "data": {"error": str(e)},
                "is_authenticated": (authenticated_user != "Guest"),
                "provider_used": "fallback",
            }


reasoning_engine = ReasoningEngine()
