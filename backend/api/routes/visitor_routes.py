"""
Rotas para contador de visitantes em tempo real
"""

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session
import redis
from typing import Optional

from backend.database.connection import get_db
from backend.database.redis_pool import get_redis_client
from backend.core.analytics.visitor_counter_service import (
    VisitorCounterService,
)

router = APIRouter(prefix="/visitors", tags=["Visitors"])


class VisitorIncrementRequest(BaseModel):
    """Body para incrementar visitante (session_id opcional)."""

    session_id: Optional[str] = None


@router.post("/increment")
async def increment_visitor_count(
    request: Request,
    body: VisitorIncrementRequest = VisitorIncrementRequest(),
    redis_client: redis.Redis = Depends(get_redis_client),
    db: Session = Depends(get_db),
):
    """
    Incrementa contador de visitantes com deduplicação por sessão.

    Body (opcional):
        {"session_id": "sess_abc123"}

    Se session_id for fornecido, visitantes repetidos no mesmo dia
    NÃO incrementam o total (apenas page views por hora).
    Fallback: usa IP do visitante para deduplicação.

    Returns:
        Dict com estatísticas atualizadas
    """
    # Extrair IP real (respeita X-Forwarded-For do nginx)
    ip_address = request.headers.get(
        "X-Forwarded-For", request.client.host if request.client else None
    )
    if ip_address and "," in ip_address:
        ip_address = ip_address.split(",")[0].strip()

    service = VisitorCounterService(redis_client, db)
    return service.increment_visitor(
        session_id=body.session_id, ip_address=ip_address
    )


@router.get("/stats")
async def get_visitor_stats(
    redis_client: redis.Redis = Depends(get_redis_client),
    db: Session = Depends(get_db),
):
    """
    Retorna estatísticas de visitantes em tempo real.

    Returns:
        Dict com:
        - total_visitors: Total de visitas
        - current_hour_visitors: Visitas na hora atual
        - current_hour: Hora atual (formato HH:00)
        - timestamp: Timestamp UTC
    """
    service = VisitorCounterService(redis_client, db)
    return service.get_stats()


@router.post("/sync")
async def sync_visitor_stats(
    redis_client: redis.Redis = Depends(get_redis_client),
    db: Session = Depends(get_db),
):
    """
    Sincroniza estatísticas do Redis para PostgreSQL.
    Útil para backup e análises de longo prazo.

    Returns:
        Dict com status da sincronização
    """
    service = VisitorCounterService(redis_client, db)
    return service.sync_to_database()


@router.get("/stats/database")
async def get_database_visitor_stats(db: Session = Depends(get_db)):
    """
    Retorna estatísticas persistidas no PostgreSQL.

    Returns:
        Dict com estatísticas do banco de dados
    """
    service = VisitorCounterService(None, db)  # Redis não necessário aqui
    return service.get_database_stats()
