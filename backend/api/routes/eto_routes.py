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
    check_global_daily_cap,
    track_calculation,
    track_global_calculation,
)

# Security / abuse protection
from backend.api.security.internal_auth import verify_internal_token
from backend.api.security import abuse_monitor
from backend.api.security import email_verification
from backend.api.security.proof_of_work import verify_solution
from config.settings.app_config import get_settings

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
    pow_nonce: Optional[str] = None  # Proof-of-work solution (anti-bot)


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
    _internal: None = Depends(verify_internal_token),  # noqa: B008
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
        is_historical = period_type_str == "historical_email"

        sec = get_settings()
        # UX-changing protections are skipped in the automated test env.
        _sec_active = sec.ENVIRONMENT != "testing"

        # 0a. Proof-of-work (anti-bot) for dashboard modes, if enabled.
        if _sec_active and sec.REQUIRE_POW and not is_historical:
            pow_subject = request.visitor_id or client_ip
            if not verify_solution(pow_subject, request.pow_nonce or ""):
                abuse_monitor.record_block(
                    "visitor_id" if request.visitor_id else "IP",
                    pow_subject,
                    period_type_str,
                    reason="pow_failed",
                )
                raise HTTPException(
                    status_code=403,
                    detail="Anti-bot verification failed. Please retry.",
                )

        # 0b. Per-user rate limit (IP + visitor_id + email).
        allowed, rate_msg = check_calculation_limit(
            client_ip,
            period_type_str,
            visitor_id=request.visitor_id,
            email=request.email,
        )
        if not allowed:
            abuse_monitor.record_block(
                "email" if request.email else "IP",
                request.email or client_ip,
                period_type_str,
                reason="rate_limit",
            )
            raise HTTPException(status_code=429, detail=rate_msg)

        # 0c. Site-wide daily cap (protects external API quotas).
        global_ok, global_msg = check_global_daily_cap()
        if not global_ok:
            raise HTTPException(status_code=429, detail=global_msg)

        # (A verificação de e-mail do histórico acontece adiante, DEPOIS de
        #  resolver as fontes/elevação, para guardar o job exato como pendente.)

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

        # 5. Montar os kwargs resolvidos do job (usados no dispatch OU como
        #    pedido pendente aguardando confirmação de e-mail).
        task_kwargs = dict(
            lat=request.lat,
            lon=request.lng,
            start_date=request.start_date,
            end_date=request.end_date,
            sources=selected_sources,
            elevation=elevation,
            mode=operation_mode.value,
            email=request.email,
            visitor_id=request.visitor_id,
            session_id=request.session_id,
            file_format=request.file_format,
            enable_fusion=enable_fusion,
            lang=request.lang,
        )

        # 5a. Confirmação híbrida (histórico): se o e-mail NÃO estiver
        # verificado, NÃO despacha — guarda o job exato como pendente e envia
        # o link de confirmação; clicar nele enfileira este mesmo job.
        # Gate autoritativo no servidor (o do frontend é só UX).
        if _sec_active and is_historical and sec.REQUIRE_EMAIL_VERIFICATION:
            verified_now = bool(
                request.email
                and email_verification.is_verified(request.email)
            )
            logger.info(
                f"🔎 Historical gate: email={request.email!r} "
                f"verified={verified_now}"
            )
            if not verified_now:
                if request.email:
                    email_verification.send_verification(
                        request.email,
                        lang=request.lang or "en",
                        pending=task_kwargs,
                    )
                # Conta a requisição no limite diário mesmo pendente
                # (evita flood de pedidos/e-mails de confirmação).
                track_calculation(
                    client_ip,
                    period_type_str,
                    visitor_id=request.visitor_id,
                    email=request.email,
                )
                track_global_calculation()
                logger.warning(
                    f"🚫 Historical NOT dispatched — e-mail não verificado: "
                    f"{request.email!r}; link de confirmação enviado."
                )
                return {
                    "status": "verification_required",
                    "message": (
                        "Requisição registrada. Confira sua caixa de entrada "
                        "(e o spam) e clique no link de confirmação — o "
                        "cálculo entrará na fila de processamento."
                    ),
                }

        # 5b. Despacho (e-mail verificado, ou modos não-histórico).
        task = calculate_eto_task.delay(  # type: ignore[attr-defined]
            **task_kwargs
        )

        task_id = task.id
        logger.info(
            f"Task ETo iniciada: {task_id} para "
            f"({request.lat}, {request.lng}) - Fontes: {selected_sources}"
        )

        # 5b. Track calculation for rate limiting (per-user + site-wide)
        track_calculation(
            client_ip,
            period_type_str,
            visitor_id=request.visitor_id,
            email=request.email,
        )
        track_global_calculation()

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
        from timezonefinderL import TimezoneFinder

        tf = TimezoneFinder()
        tz_name = tf.timezone_at(lat=request.lat, lng=request.lng)

        # Fallback: If over ocean or unmapped area
        if not tz_name:
            tz_name = "UTC"

        # Try to get elevation from OpenTopo
        elevation_m = None
        try:
            from backend.api.services.opentopo.opentopo_sync_adapter import (
                OpenTopoSyncAdapter,
            )

            topo = OpenTopoSyncAdapter()
            result = topo.get_elevation_sync(
                lat=request.lat, lon=request.lng
            )
            if result and result.elevation is not None:
                elevation_m = result.elevation
        except Exception as elev_err:
            logger.warning(f"Elevation lookup failed: {elev_err}")

        return {
            "status": "success",
            "location": {
                "lat": request.lat,
                "lng": request.lng,
                "timezone": tz_name,
                "elevation_m": elevation_m,
            },
            "timestamp": time.time(),
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get location info: {str(e)}"
        )


# ============================================================================
# EMAIL VERIFICATION (novo fluxo do modo Histórico)
# ============================================================================


class VerificationRequest(BaseModel):
    """Solicitação para enviar o e-mail de verificação (modo histórico)."""

    email: str
    lang: Optional[str] = "en"


@eto_router.post("/request-verification")
async def request_email_verification(
    request: VerificationRequest,
    _internal: None = Depends(verify_internal_token),  # noqa: B008
) -> Dict[str, Any]:
    """
    Envia o e-mail de confirmação (se ainda não verificado).

    Chamado quando o usuário clica em "Confirme seu e-mail" no modo histórico,
    ANTES de liberar datas/formato/cálculo.
    """
    email = (request.email or "").strip()
    if not email or "@" not in email:
        raise HTTPException(status_code=400, detail="Invalid email")

    if email_verification.is_verified(email):
        return {"status": "verified", "verified": True}

    sent = email_verification.send_verification(email, lang=request.lang or "en")
    return {"status": "sent" if sent else "error", "verified": False}


@eto_router.get("/verification-status")
async def email_verification_status(
    email: str,
    _internal: None = Depends(verify_internal_token),  # noqa: B008
) -> Dict[str, Any]:
    """Retorna se o e-mail já foi confirmado (usado pelo polling do frontend)."""
    return {"verified": email_verification.is_verified((email or "").strip())}
