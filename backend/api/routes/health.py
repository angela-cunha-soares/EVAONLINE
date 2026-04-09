"""
Health Check Routes
"""

import time
from typing import Any, Dict

from fastapi import APIRouter, HTTPException

from backend.database.health_checks import perform_full_health_check
from config.settings import get_legacy_settings

router = APIRouter(tags=["Health"])
settings = get_legacy_settings()


# ============================================================================
# ENDPOINTS ESSENCIAIS (3)
# ============================================================================


@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """
    ✅ Health check básico.

    Returns:
        Dict com status básico da API
    """
    return {
        "status": "ok",
        "service": "evaonline-api",
        "version": settings.VERSION,
        "timestamp": time.time(),
    }


@router.get("/health/detailed")
async def detailed_health_check() -> Dict[str, Any]:
    """
    ✅ Health check detalhado (PostgreSQL, Redis, Celery).

    Returns:
        Dict com status detalhado de todos os componentes
    """
    try:
        health_data = perform_full_health_check()

        # Adicionar informações da API
        health_data.update(
            {
                "api": {
                    "status": "healthy",
                    "version": settings.VERSION,
                    "environment": settings.ENVIRONMENT,
                    "debug": settings.DEBUG,
                }
            }
        )

        return health_data

    except Exception as e:
        raise HTTPException(
            status_code=503, detail=f"Health check failed: {str(e)}"
        )


@router.get("/ready")
async def readiness_check() -> Dict[str, Any]:
    """
    ✅ Readiness check para Docker Compose (health check).

    Returns:
        Dict com status de prontidão
    """
    try:
        # Verificação básica: se conseguimos executar health check detalhado
        health_data = perform_full_health_check()
        overall_status = health_data.get("overall_status", "unknown")

        if overall_status == "healthy":
            return {
                "status": "ready",
                "service": "evaonline-api",
                "version": settings.VERSION,
            }
        else:
            raise HTTPException(
                status_code=503, detail=f"Service not ready: {overall_status}"
            )
    except Exception as e:
        raise HTTPException(
            status_code=503, detail=f"Readiness check failed: {str(e)}"
        )
