# backend/infrastructure/cache/redis_manager.py
import json
from datetime import datetime, timedelta
from typing import Any

from loguru import logger
from redis.asyncio import Redis
from sqlalchemy.orm import Session

from backend.api.main import CACHE_HITS, CACHE_MISSES, POPULAR_DATA_ACCESSES


class CacheManager:
    def __init__(
        self,
        redis_client: Redis,
        db_session: Session,
        eto_expiry: int = 86400,
        user_data_expiry: int = 2592000,
    ):
        self.redis = redis_client
        self.db = db_session
        self.eto_expiry = eto_expiry
        self.user_data_expiry = user_data_expiry

    async def get_eto_data(self, key: str) -> dict[str, Any] | None:
        data = await self._get_from_redis(key)
        if data:
            logger.info(f"Cache hit para key: {key}")
            CACHE_HITS.labels(key=key).inc()
            POPULAR_DATA_ACCESSES.labels(key=key).inc()
            return data

        logger.info(f"Cache miss para key: {key}, buscando no PostgreSQL")
        CACHE_MISSES.labels(key=key).inc()
        data = await self._get_from_postgres(key)
        if data:
            await self._set_in_redis(key, data, self.eto_expiry)
            POPULAR_DATA_ACCESSES.labels(key=key).inc()
            return data
        return None

    async def save_eto_data(self, key: str, data: dict[str, Any]):
        try:
            await self._set_in_redis(key, data, self.eto_expiry)
            await self._save_to_postgres(key, data)
            logger.info(f"Dados salvos com sucesso para key: {key}")
            POPULAR_DATA_ACCESSES.labels(key=key).inc()
        except Exception as e:
            logger.error(f"Erro ao salvar dados: {str(e)}")
            raise

    async def _get_from_redis(self, key: str) -> dict[str, Any] | None:
        try:
            data = await self.redis.get(key)
            return json.loads(data) if data else None
        except Exception as e:
            logger.error(f"Erro ao buscar do Redis: {str(e)}")
            return None

    async def _set_in_redis(self, key: str, data: dict[str, Any], expiry: int):
        try:
            await self.redis.setex(key, expiry, json.dumps(data))
        except Exception as e:
            logger.error(f"Erro ao salvar no Redis: {str(e)}")
            raise

    async def _get_from_postgres(self, key: str) -> dict[str, Any] | None:
        try:
            result = self.db.execute(
                """
                SELECT data, created_at
                FROM eto_results
                WHERE key = :key
                ORDER BY created_at DESC
                LIMIT 1
                """,
                {"key": key},
            ).first()
            if result:
                data, created_at = result
                if datetime.now() - created_at < timedelta(days=1):
                    return json.loads(data)
            return None
        except Exception as e:
            logger.error(f"Erro ao buscar do PostgreSQL: {str(e)}")
            return None

    async def _save_to_postgres(self, key: str, data: dict[str, Any]):
        try:
            self.db.execute(
                """
                INSERT INTO eto_results (key, data, created_at)
                VALUES (:key, :data, :created_at)
                """,
                {"key": key, "data": json.dumps(data), "created_at": datetime.now()},
            )
            self.db.commit()
        except Exception as e:
            logger.error(f"Erro ao salvar no PostgreSQL: {str(e)}")
            self.db.rollback()
            raise

    async def cleanup_expired_data(self):
        try:
            self.db.execute(
                """
                DELETE FROM eto_results
                WHERE created_at < :expiry_date
                """,
                {"expiry_date": datetime.now() - timedelta(seconds=self.eto_expiry)},
            )
            self.db.commit()
            logger.info("Limpeza de dados expirados concluída")
        except Exception as e:
            logger.error(f"Erro na limpeza de dados: {str(e)}")
            self.db.rollback()
            raise
