"""
Health & Status Endpoint
========================
Provides a lightweight status check for the OrbisERP AI Layer.
Does not expose any API keys, credentials, or internal ERPNext configurations.
"""

from fastapi import APIRouter
from app.core.config import settings

router = APIRouter(tags=["Health"])


@router.get("/health", summary="Service Health Check")
async def health_check():
    """Returns basic service health status, configured capabilities, and readiness flag."""
    return {
        "status": "healthy",
        "service": settings.ai_service_name,
        "environment": settings.orbis_env,
        "version": "0.1.0",
        "scope": {
            "target_module": settings.ai_default_module,
            "mode": "voice_pipeline_ready",
        },
        "integrations": {
            "erpnext": {
                "base_url": settings.erpnext_base_url,
                "configured": bool(settings.erpnext_api_key and settings.erpnext_api_secret),
            },
            "ollama": {
                "base_url": settings.ollama_base_url,
                "model": settings.ollama_model,
                "configured": bool(settings.ollama_base_url),
            },
            "groq": {
                "model": settings.groq_model,
                "configured": bool(settings.groq_api_key),
            },
            "voice": {
                "similarity_threshold": settings.orbis_voice_similarity_threshold,
                "status": "ready",
            },
        },
    }
