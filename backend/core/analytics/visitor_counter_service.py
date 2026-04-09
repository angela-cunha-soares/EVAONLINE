"""
Serviço de contagem de visitantes usando Redis + PostgreSQL
"""

from datetime import datetime
from typing import Dict, Optional

import redis
from sqlalchemy.orm import Session

from backend.database.models.visitor_stats import VisitorStats


class VisitorCounterService:
    """Gerencia contagem de visitantes em tempo real com persistência"""

    def __init__(self, redis_client: redis.Redis, db_session: Session):
        self.redis = redis_client
        self.db = db_session
        self.REDIS_KEY_VISITORS = "visitors:count"
        self.REDIS_KEY_UNIQUE_TODAY = "visitors:unique:today"
        self.REDIS_KEY_PEAK_HOUR = "visitors:peak_hour"
        self.REDIS_KEY_HOURLY = "visitors:hourly"  # Contador por hora

    def increment_visitor(
        self, session_id: str = None, ip_address: str = None
    ) -> Dict:
        """
        Incrementa contador de visitantes no Redis com deduplicação por sessão.

        Se session_id for fornecido, verifica se já foi contado hoje.
        Sessões repetidas NÃO incrementam o total (evita inflação).
        Se nem session_id nem ip_address disponíveis, NÃO incrementa
        (segurança contra inflação acidental).

        Args:
            session_id: ID único da sessão do usuário (ex: "sess_abc123")
            ip_address: IP do visitante (fallback para deduplicação)

        Returns:
            Dict com estatísticas atualizadas
        """
        try:
            # Determinar chave de deduplicação
            dedup_key = session_id or (
                f"ip_{ip_address}" if ip_address else None
            )

            # Sem identificador → não incrementar (evita inflação)
            if not dedup_key:
                return self.get_stats()

            is_new_visitor = not self.redis.sismember(
                self.REDIS_KEY_UNIQUE_TODAY, dedup_key
            )
            if is_new_visitor:
                self.redis.sadd(self.REDIS_KEY_UNIQUE_TODAY, dedup_key)
                # Expirar set à meia-noite (~24h)
                self.redis.expire(self.REDIS_KEY_UNIQUE_TODAY, 86400)

            # Incrementar total APENAS se visitante novo
            if is_new_visitor:
                self.redis.incr(self.REDIS_KEY_VISITORS)

            # Incrementar hora atual (page views, sempre conta)
            current_hour = datetime.utcnow().strftime("%H:00")
            hourly_key = f"{self.REDIS_KEY_HOURLY}:{current_hour}"
            self.redis.incr(hourly_key)
            self.redis.expire(hourly_key, 86400)  # TTL 24h

            # Obter counts
            total = int(self.redis.get(self.REDIS_KEY_VISITORS) or 0)
            hourly = int(self.redis.get(hourly_key) or 0)
            unique_today = self.redis.scard(self.REDIS_KEY_UNIQUE_TODAY) or 0

            return {
                "total_visitors": total,
                "current_hour_visitors": hourly,
                "unique_today": unique_today,
                "is_new_visitor": is_new_visitor,
                "current_hour": current_hour,
                "timestamp": datetime.utcnow().isoformat(),
            }
        except Exception as e:
            return {"error": str(e)}

    def get_stats(self) -> Dict:
        """Retorna estatísticas atuais dos visitantes"""
        try:
            total = int(self.redis.get(self.REDIS_KEY_VISITORS) or 0)
            current_hour = datetime.utcnow().strftime("%H:00")
            hourly_key = f"{self.REDIS_KEY_HOURLY}:{current_hour}"
            hourly = int(self.redis.get(hourly_key) or 0)

            # Obter pico de hora do dia
            peak_hour = self.redis.get(self.REDIS_KEY_PEAK_HOUR)
            if peak_hour and isinstance(peak_hour, bytes):
                peak_hour = peak_hour.decode()

            return {
                "total_visitors": total,
                "current_hour_visitors": hourly,
                "current_hour": current_hour,
                "peak_hour": peak_hour,
                "timestamp": datetime.utcnow().isoformat(),
            }
        except Exception as e:
            return {"error": str(e)}

    def sync_to_database(self) -> Dict:
        """
        Sincroniza dados de Redis para PostgreSQL
        Útil para persistência em longo prazo
        """
        try:
            total = int(self.redis.get(self.REDIS_KEY_VISITORS) or 0)
            current_hour = datetime.utcnow().strftime("%H:%M")

            # Buscar ou criar registro no banco
            stats = self.db.query(VisitorStats).first()
            if not stats:
                stats = VisitorStats(
                    total_visitors=total,
                    unique_visitors_today=total,
                    last_sync=datetime.utcnow(),
                    peak_hour=current_hour,
                )
                self.db.add(stats)
            else:
                stats.total_visitors = total  # type: ignore[assignment]
                stats.last_sync = datetime.utcnow()  # type: ignore[assignment]
                stats.peak_hour = current_hour  # type: ignore[assignment]

            self.db.commit()

            return {
                "status": "synced",
                "total_visitors": total,
                "last_sync": datetime.utcnow().isoformat(),
            }
        except Exception as e:
            self.db.rollback()
            return {"error": str(e)}

    def get_database_stats(self) -> Optional[Dict]:
        """Retorna estatísticas persistidas no banco de dados"""
        try:
            stats = self.db.query(VisitorStats).first()
            if stats:
                last_sync = getattr(stats, "last_sync", None)
                created_at = getattr(stats, "created_at", None)
                return {
                    "total_visitors": stats.total_visitors,
                    "unique_visitors_today": stats.unique_visitors_today,
                    "peak_hour": stats.peak_hour,
                    "last_sync": (
                        last_sync.isoformat() if last_sync else None
                    ),
                    "created_at": (
                        created_at.isoformat() if created_at else None
                    ),
                }
            return None
        except Exception as e:
            return {"error": str(e)}
