"""
OrbisERP Model Router Module
============================
Routes DSPy inference requests through Groq and Ollama backends.
Enforces:
1. Configurable provider selection: 'groq', 'ollama', 'auto'.
2. In 'auto' mode: attempts Groq first; upon timeout, 404, or failure, seamlessly falls back to Ollama.
3. Implements a transient circuit-breaker for unavailable cloud models to avoid repeated network timeouts.
4. If both providers fail: raises ReasoningServiceUnavailableError (never silently uses generic canned sentences).
"""

import time
import logging
from typing import Any, Callable, Dict, Optional, Tuple
import dspy
from app.core.config import settings
from app.ai.dspy_config import DSPyConfigManager

logger = logging.getLogger("orbis.ai.model_router")


class ReasoningServiceUnavailableError(Exception):
    """Raised when all configured LLM reasoning providers fail."""
    pass


class ModelRouter:
    """Dispatches DSPy module executions with intelligent provider fallback and circuit breaker."""

    def __init__(self):
        self.provider_mode = (settings.llm_provider or "auto").lower()
        self._groq_failed_until: float = 0.0

    def execute_with_fallback(self, func: Callable[..., Any], *args, **kwargs) -> Tuple[Any, str]:
        """
        Executes a DSPy function or module call using the configured provider policy.
        Returns: (result, provider_name_used)
        """
        mode = self.provider_mode
        now = time.time()

        if mode == "groq":
            groq_lm = DSPyConfigManager.get_groq_lm()
            if not groq_lm:
                raise ReasoningServiceUnavailableError(
                    "Groq is configured as provider, but GROQ_API_KEY is missing or invalid."
                )
            with dspy.context(lm=groq_lm):
                try:
                    result = func(*args, **kwargs)
                    return result, f"groq/{settings.groq_model}"
                except Exception as e:
                    logger.error(f"Groq inference failed: {e}")
                    raise ReasoningServiceUnavailableError(f"Groq reasoning failed: {e}")

        elif mode == "ollama":
            ollama_lm = DSPyConfigManager.get_ollama_lm()
            if not ollama_lm:
                raise ReasoningServiceUnavailableError(
                    "Ollama is configured as provider, but could not be initialized."
                )
            with dspy.context(lm=ollama_lm):
                try:
                    result = func(*args, **kwargs)
                    return result, f"ollama/{settings.ollama_model}"
                except Exception as e:
                    logger.error(f"Ollama inference failed: {e}")
                    raise ReasoningServiceUnavailableError(f"Ollama local reasoning failed: {e}")

        else:  # "auto" mode: Groq first -> Ollama fallback
            groq_available = (now > self._groq_failed_until)
            if groq_available:
                groq_lm = DSPyConfigManager.get_groq_lm()
                if groq_lm:
                    try:
                        with dspy.context(lm=groq_lm):
                            result = func(*args, **kwargs)
                            return result, f"groq/{settings.groq_model}"
                    except Exception as groq_err:
                        # Circuit-breaker: skip Groq for 60 seconds on model/network failure
                        self._groq_failed_until = now + 60.0
                        logger.warning(
                            f"Groq cloud inference unavailable ({groq_err}). Falling back to local Ollama ({settings.ollama_model})."
                        )

            # Fallback to Ollama
            ollama_lm = DSPyConfigManager.get_ollama_lm()
            if ollama_lm:
                try:
                    with dspy.context(lm=ollama_lm):
                        result = func(*args, **kwargs)
                        return result, f"ollama/{settings.ollama_model}"
                except Exception as ollama_err:
                    logger.error(f"Ollama local inference failed during fallback: {ollama_err}")
                    raise ReasoningServiceUnavailableError(
                        "The Orbis conversational reasoning service is temporarily unavailable. "
                        "Both cloud (Groq) and local (Ollama) intelligence backends could not be reached."
                    )
            else:
                raise ReasoningServiceUnavailableError(
                    "The Orbis conversational reasoning service is temporarily unavailable. "
                    "Cloud provider failed and local Ollama is not initialized."
                )
