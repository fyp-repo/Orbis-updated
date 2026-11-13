"""
OrbisERP DSPy Configuration Module
==================================
Initializes and configures DSPy 3.x Language Model backends for:
1. Groq Cloud (Primary cloud reasoning, e.g. llama-3.3-70b-versatile)
2. Ollama Local (Local offline inference, e.g. llama3.2:1b)
Handles model initialization, timeouts, and fallback configuration.
"""

import logging
from typing import Optional, Tuple
import dspy
from app.core.config import settings

logger = logging.getLogger("orbis.ai.dspy_config")


class DSPyConfigManager:
    """Manages DSPy LM instantiation and runtime configuration."""

    _groq_lm: Optional[dspy.LM] = None
    _ollama_lm: Optional[dspy.LM] = None
    _current_lm: Optional[dspy.LM] = None
    _current_provider_name: str = "uninitialized"

    @classmethod
    def get_groq_lm(cls) -> Optional[dspy.LM]:
        """Returns or instantiates the Groq DSPy LM client."""
        if cls._groq_lm is None and settings.groq_api_key:
            try:
                # In DSPy 3.x, groq/<model> routes through LiteLLM
                cls._groq_lm = dspy.LM(
                    f"groq/{settings.groq_model}",
                    api_key=settings.groq_api_key,
                    temperature=0.2,
                    timeout=10,
                )
            except Exception as e:
                logger.warning(f"Failed to initialize Groq LM client: {e}")
        return cls._groq_lm

    @classmethod
    def get_ollama_lm(cls) -> Optional[dspy.LM]:
        """Returns or instantiates the Ollama DSPy LM client."""
        if cls._ollama_lm is None:
            try:
                # In DSPy 3.x, Ollama is accessed via OpenAI-compatible endpoint
                cls._ollama_lm = dspy.LM(
                    f"openai/{settings.ollama_model}",
                    api_base=f"{settings.ollama_base_url.rstrip('/')}/v1",
                    api_key="ollama",
                    temperature=0.2,
                    timeout=45,
                )
            except Exception as e:
                logger.warning(f"Failed to initialize Ollama LM client: {e}")
        return cls._ollama_lm

    @classmethod
    def configure_dspy(cls, provider: Optional[str] = None) -> Tuple[dspy.LM, str]:
        """
        Configures dspy.settings with the requested or auto-resolved provider.
        Returns (active_lm, provider_name).
        """
        target = (provider or settings.llm_provider or "auto").lower()

        if target == "groq":
            lm = cls.get_groq_lm()
            if not lm:
                raise RuntimeError("Groq LM requested but not configured or failed to initialize")
            dspy.configure(lm=lm)
            cls._current_lm = lm
            cls._current_provider_name = f"groq ({settings.groq_model})"
            return lm, cls._current_provider_name

        elif target == "ollama":
            lm = cls.get_ollama_lm()
            if not lm:
                raise RuntimeError("Ollama LM requested but failed to initialize")
            dspy.configure(lm=lm)
            cls._current_lm = lm
            cls._current_provider_name = f"ollama ({settings.ollama_model})"
            return lm, cls._current_provider_name

        else:  # "auto"
            # In auto mode, try Groq first; if not configured, use Ollama
            groq_lm = cls.get_groq_lm()
            if groq_lm:
                dspy.configure(lm=groq_lm)
                cls._current_lm = groq_lm
                cls._current_provider_name = f"groq ({settings.groq_model})"
                return groq_lm, cls._current_provider_name

            ollama_lm = cls.get_ollama_lm()
            if ollama_lm:
                dspy.configure(lm=ollama_lm)
                cls._current_lm = ollama_lm
                cls._current_provider_name = f"ollama ({settings.ollama_model})"
                return ollama_lm, cls._current_provider_name

            raise RuntimeError("No LLM provider available (both Groq and Ollama failed)")

    @classmethod
    def active_provider(cls) -> str:
        return cls._current_provider_name

