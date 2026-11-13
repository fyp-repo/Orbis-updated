"""
OrbisERP AI Layer — FastAPI Entrypoint
======================================
Provides the foundational application structure for the AI layer.
Maintains clean separation from ERPNext while securing all communication.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.routes import health, voice

app = FastAPI(
    title=settings.ai_service_name,
    version="0.1.0",
    description="Dedicated AI backend layer for OrbisERP (Car Manufacturing Pvt. Ltd.)",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
)

# CORS Configuration
# Restricts incoming requests strictly to the ERPNext Desk SPA domain
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# Register API Routers
app.include_router(health.router, prefix="/api")
app.include_router(voice.router, prefix="/api")


@app.get("/", summary="Root Index")
async def root():
    return {
        "service": settings.ai_service_name,
        "status": "operational",
        "description": "OrbisERP AI Layer Backend Foundation",
    }

