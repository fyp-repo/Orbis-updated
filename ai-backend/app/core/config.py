"""
OrbisERP AI Layer — Core Configuration Module
=============================================
Manages server-side configuration using Pydantic Settings.
All secrets (Groq API keys, ERPNext tokens) are strictly validated and loaded server-side only.
"""

from pathlib import Path
from typing import List
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent.parent
ENV_FILE = BASE_DIR / ".env"


class Settings(BaseSettings):
    # Service Information
    ai_service_name: str = Field(default="OrbisERP AI Layer", alias="AI_SERVICE_NAME")
    ai_service_port: int = Field(default=8000, alias="AI_SERVICE_PORT")
    ai_service_host: str = Field(default="127.0.0.1", alias="AI_SERVICE_HOST")
    debug: bool = Field(default=False, alias="DEBUG")

    # Allowed CORS Origins
    cors_origins: List[str] = Field(
        default=["http://localhost:8085", "http://127.0.0.1:8085"],
        alias="CORS_ORIGINS",
    )

    # ERPNext Backend Target (Server-Side Only)
    erpnext_base_url: str = Field(
        default="http://localhost:8085", alias="ERPNEXT_BASE_URL"
    )
    erpnext_api_key: str = Field(default="", alias="ERPNEXT_API_KEY")
    erpnext_api_secret: str = Field(default="", alias="ERPNEXT_API_SECRET")

    # LLM Provider Selection: "groq", "ollama", or "auto" (Groq with Ollama fallback)
    llm_provider: str = Field(default="auto", alias="LLM_PROVIDER")

    # Groq Cloud LLM Configuration (Server-Side Only)
    groq_api_key: str = Field(default="", alias="GROQ_API_KEY")
    groq_model: str = Field(default="llama-3.3-70b-versatile", alias="GROQ_MODEL")

    # Local Ollama LLM Configuration (Server-Side Only)
    ollama_base_url: str = Field(
        default="http://localhost:11434", alias="OLLAMA_BASE_URL"
    )
    ollama_model: str = Field(default="llama3.2:1b", alias="OLLAMA_MODEL")

    # Orbis Voice & Runtime Settings
    orbis_env: str = Field(default="development", alias="ORBIS_ENV")
    orbis_voice_similarity_threshold: float = Field(
        default=0.68, alias="ORBIS_VOICE_SIMILARITY_THRESHOLD"
    )
    vad_endpoint_silence_seconds: int = Field(
        default=10, alias="VAD_ENDPOINT_SILENCE_SECONDS"
    )

    # Administrative Maintenance & Scope Boundaries
    # Note: AI_ALLOWED_USER specifies the system user authorized for administrative maintenance tasks
    # (e.g. system diagnostics, maintenance scripts). It DOES NOT restrict normal voice enrollment,
    # biometric speaker verification, or intent execution for enabled ERPNext users with valid roles.
    ai_allowed_user: str = Field(default="Administrator", alias="AI_ALLOWED_USER")
    ai_default_module: str = Field(default="Stock", alias="AI_DEFAULT_MODULE")

    model_config = SettingsConfigDict(
        env_file=(str(ENV_FILE), ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


settings = Settings()
