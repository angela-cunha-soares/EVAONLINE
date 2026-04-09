"""
ETo Calculation Routes
"""

import time
from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
from loguru import logger

from backend.database.connection import get_db

# Importar 5 módulos de clima
from backend.api.services.climate_validation import ClimateValidationService
from backend.api.services.climate_source_availability import (
    OperationMode,
)
from backend.api.services.climate_source_manager import ClimateSourceManager

# Rate limiter per-IP
from backend.api.middleware.rate_limiter import (
    check_calculation_limit,
    track_calculation,
)

# Importar task Celery para cálculos assíncronos
from backend.infrastructure.celery.tasks.eto_calculation import (
    calculate_eto_task,
)

# Mapeamento de period_type para OperationMode
# Centraliza conversão de strings antigas para novo enum
OPERATION_MODE_MAPPING = {
    "historical_email": OperationMode.HISTORICAL_EMAIL,
    "dashboard_current": OperationMode.DASHBOARD_CURRENT,
    "dashboard_forecast": OperationMode.DASHBOARD_FORECAST,
}

eto_router = APIRouter(prefix="/internal/eto", tags=["ETo"])


# ============================================================================
# SCHEMAS
# ============================================================================


class EToCalculationRequest(BaseModel):
    """Request para cálculo ETo.

    NOTA: Fusão de dados é SEMPRE automática.
    O sistema seleciona as melhores fontes baseado no period_type:
    - historical_email: NASA POWER + Open-Meteo Archive
    - dashboard_current: NASA POWER + Open-Meteo Archive + Open-Meteo Forecast
    - dashboard_forecast: Open-Meteo Forecast + MET Norway
    """

    lat: float
    lng: float
    start_date: str
    end_date: str
    period_type: Optional[str] = (
        "dashboard_current"  # historical_email, dashboard_current, dashboard_forecast
    )
    elevation: Optional[float] = None
    estado: Optional[str] = None
    cidade: Optional[str] = None
    email: Optional[str] = (
        None  # Email para notificações (modo historical_email)
    )
    visitor_id: Optional[str] = None  # ID único do visitante
    session_id: Optional[str] = None  # ID da sessão
    file_format: Optional[str] = "csv"  # csv (padrão) ou excel
    lang: Optional[str] = "en"  # Language for email templates (en/pt)


class LocationInfoRequest(BaseModel):
    """Request para informações de localização."""

    lat: float
    lng: float


# ============================================================================
# ENDPOINTS ESSENCIAIS (2) - Favoritos removidos
# ============================================================================


@eto_router.post("/calculate")
async def calculate_eto(
    request: EToCalculationRequest,
    fastapi_request: Request,
    db: Session = Depends(get_db),  # type: ignore[arg-type] # noqa: B008
) -> Dict[str, Any]:
    """
    🚀 Cálculo ETo assíncrono com progresso em tempo real.

    Inicia tarefa Celery e retorna task_id para monitoramento via WebSocket.

    Suporta:
    - Múltiplas fontes de dados
    - Auto-detecção de melhor fonte
    - Fusão de dados (Kalman)
    - Cache automático
    - Progresso em tempo real via WebSocket

    Modos de operação (period_type):
    - historical_email: 1-90 dias (apenas NASA POWER e OpenMeteo Archive)
    - dashboard_current: 7-30 dias (todas as APIs disponíveis)
    - dashboard_forecast: hoje até hoje+5d (apenas APIs de previsão)

    Resposta:
    {
        "status": "accepted",
        "task_id": "abc-123-def",
        "websocket_url": "/ws/task_status/abc-123-def",
        "message": "Cálculo iniciado. Use WebSocket para progresso.",
        "estimated_duration_seconds": "5-30"
    }

    Monitore progresso: WebSocket /ws/task_status/{task_id}
    """
    try:
        # 0. Rate limiting per-IP
        client_ip = (
            fastapi_request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
            or fastapi_request.headers.get("X-Real-IP", "")
            or fastapi_request.client.host  # type: ignore[union-attr]
            or "unknown"
        )
        period_type_str = (request.period_type or "dashboard_current").lower()

        allowed, rate_msg = check_calculation_limit(
            client_ip, period_type_str, visitor_id=request.visitor_id
        )
        if not allowed:
            raise HTTPException(status_code=429, detail=rate_msg)

        # 0b. Normalizar period_type para OperationMode

        # Usar mapeamento centralizado
        operation_mode = OPERATION_MODE_MAPPING.get(
            period_type_str, OperationMode.DASHBOARD_CURRENT
        )

        # 1. Usar ClimateValidationService (sempre modo "auto" para fusão)
        validator = ClimateValidationService()

        is_valid, validation_result = validator.validate_all(
            lat=request.lat,
            lon=request.lng,
            start_date=request.start_date,
            end_date=request.end_date,
            variables=["et0_fao_evapotranspiration"],
            source="auto",  # Sempre fusão automática
            mode=operation_mode.value,
        )

        if not is_valid:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Validação falhou: "
                    f"{validation_result.get('errors', {})}"
                ),
            )

        # 2. Usar ClimateSourceManager para auto-seleção de fontes
        manager = ClimateSourceManager()

        # FUSÃO AUTOMÁTICA: obter TODAS as fontes compatíveis para o modo
        compatible_sources = manager.get_available_sources_by_mode(
            lat=request.lat,
            lon=request.lng,
            mode=operation_mode,
        )

        if not compatible_sources:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Nenhuma fonte disponível para modo "
                    f"{operation_mode.value} na localização fornecida"
                ),
            )

        # Usar TODAS as fontes disponíveis para fusão Kalman
        selected_sources = compatible_sources
        enable_fusion = True  # Sempre fusão automática

        logger.info(
            f"Fusão automática: {operation_mode.value} em "
            f"({request.lat}, {request.lng}) → Fontes: {selected_sources}"
        )

        # 4. Obter elevação (se não fornecida)
        elevation = request.elevation
        if elevation is None:
            logger.info(
                f"Elevação não fornecida para ({request.lat}, {request.lng}), "
                f"será obtida via API"
            )

        # 5. Iniciar cálculo ETo assíncrono (Celery task)
        # Em vez de processar sincronamente, delegar para worker
        task = calculate_eto_task.delay(  # type: ignore[attr-defined]
            lat=request.lat,
            lon=request.lng,
            start_date=request.start_date,
            end_date=request.end_date,
            sources=selected_sources,  # Lista de fontes (uma ou várias)
            elevation=elevation,
            mode=operation_mode.value,  # String do modo
            email=request.email,  # Email para notificações
            visitor_id=request.visitor_id,  # ID único do visitante
            session_id=request.session_id,  # ID da sessão
            file_format=request.file_format,  # Formato: excel ou csv
            enable_fusion=enable_fusion,  # Flag de fusão Kalman
            lang=request.lang,  # Language for email templates
        )

        task_id = task.id
        logger.info(
            f"Task ETo iniciada: {task_id} para "
            f"({request.lat}, {request.lng}) - Fontes: {selected_sources}"
        )

        # 5b. Track calculation for rate limiting
        track_calculation(client_ip, period_type_str, visitor_id=request.visitor_id)

        # 6. Retornar task_id para monitoramento via WebSocket
        return {
            "status": "accepted",
            "task_id": task_id,
            "message": (
                "Cálculo ETo iniciado com fusão automática. "
                "Use WebSocket para acompanhar progresso."
            ),
            "websocket_url": f"/ws/task_status/{task_id}",
            # Informações de fusão (sempre automática)
            "fusion": {
                "enabled": True,
                "method": "kalman",
                "sources_used": selected_sources,
            },
            "operation_mode": operation_mode.value,
            "location": {
                "lat": request.lat,
                "lng": request.lng,
                "elevation_m": elevation,
            },
            "estimated_duration_seconds": "5-30",
        }

    except HTTPException:
        # Re-raise HTTPException to preserve status code (400, 404, etc)
        raise
    except ValueError as ve:
        raise HTTPException(
            status_code=400, detail=f"Formato de data inválido: {str(ve)}"
        )
    except Exception as e:
        import traceback

        traceback.print_exc()
        raise HTTPException(
            status_code=500, detail=f"ETo calculation failed: {str(e)}"
        )


@eto_router.post("/location-info")
async def get_location_info(request: LocationInfoRequest) -> Dict[str, Any]:
    """
    Informações de localização (timezone, elevação).
    """
    try:
        # TODO: Implementar busca real de timezone e elevação
        # Por enquanto, retorna estrutura básica
        return {
            "status": "success",
            "location": {
                "lat": request.lat,
                "lng": request.lng,
                "timezone": "America/Sao_Paulo",  # Placeholder
                "elevation_m": None,  # Placeholder
            },
            "timestamp": time.time(),
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get location info: {str(e)}"
        )
