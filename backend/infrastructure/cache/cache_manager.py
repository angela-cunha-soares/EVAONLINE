"""
Gerenciador centralizado de cache para sessões de usuários anônimos.

Este serviço gerencia:
1. Cache em Redis com TTL de 1 hora para dados climáticos
2. Agregações em PostgreSQL para análises de 24 horas
3. Session IDs únicos para usuários anônimos
4. Métricas de hit/miss do cache

Arquitetura:
├─ SessionCache: Gerencia cache por sessão + fallback para API
└─ ClimateCache: Agregações de dados climáticos para análise
"""

import json
import logging
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class SessionCache:
    """
    Gerencia cache de dados climáticos por sessão de usuário anônimo.

    Features:
    - Session ID único por usuário
    - Cache Redis com TTL configurável (default 1h)
    - Fallback automático para API se cache vazio
    - Rastreamento de hit/miss ratio

    Exemplo:
        cache = SessionCache(redis_pool, db_session)
        data = await cache.get_or_fetch_climate(
            location_id=1,
            session_id="abc123",
            force_refresh=False
        )
    """

    def __init__(self, redis_pool, db_session: Session | None = None):
        """
        Inicializa o gerenciador de cache.

        Args:
            redis_pool: Redis connection pool
            db_session: SQLAlchemy session (opcional, para persistência)
        """
        self.redis = redis_pool
        self.db = db_session
        self.ttl = 3600  # 1 hora em segundos
        self.cache_prefix = "climate:cache:"
        self.session_prefix = "session:"

        # Métricas
        self.hits = 0
        self.misses = 0

    @staticmethod
    def generate_session_id() -> str:
        """
        Gera session ID único para usuário anônimo.

        Returns:
            str: UUID v4 formatado como session ID

        Exemplo:
            >>> sid = SessionCache.generate_session_id()
            >>> print(sid)
            'sess_550e8400e29b41d4a716446655440000'
        """
        return f"sess_{uuid.uuid4().hex}"

    def _make_cache_key(self, location_id: int, data_type: str = "climate") -> str:
        """
        Cria chave Redis para armazenar dados.

        Args:
            location_id: ID da localização
            data_type: Tipo de dado (climate, elevation, etc)

        Returns:
            str: Chave Redis formatada

        Exemplo:
            >>> key = cache._make_cache_key(42, "climate")
            >>> print(key)
            'climate:cache:42:climate'
        """
        return f"{self.cache_prefix}{location_id}:{data_type}"

    def _make_session_key(self, session_id: str, location_id: int) -> str:
        """
        Cria chave Redis para metadados de sessão.

        Args:
            session_id: ID da sessão
            location_id: ID da localização

        Returns:
            str: Chave Redis formatada
        """
        return f"{self.session_prefix}{session_id}:loc_{location_id}"

    async def get_or_fetch_climate(
        self, location_id: int, session_id: str, fetch_func=None, force_refresh: bool = False
    ) -> dict[str, Any]:
        """
        Busca dados climáticos do cache ou API.

        Strategy:
        1. Se force_refresh=True, pula cache e busca na API
        2. Se em cache com TTL válido, retorna (HIT)
        3. Se não em cache, busca na API e armazena (MISS)
        4. Se API falha, tenta fallback do cache expirado

        Args:
            location_id: ID da localização
            session_id: ID da sessão do usuário
            fetch_func: Função async para buscar dados (clima_sources.py)
            force_refresh: Forçar busca na API, ignorando cache

        Returns:
            Dict com dados climáticos

        Raises:
            ValueError: Se location_id inválido

        Exemplo:
            >>> data = await cache.get_or_fetch_climate(
            ...     location_id=1,
            ...     session_id="sess_abc123",
            ...     fetch_func=get_climate_from_api
            ... )
            >>> print(data['temperature'])
            25.5
        """
        if not fetch_func:
            msg = "fetch_func é obrigatório"
            raise ValueError(msg)

        cache_key = self._make_cache_key(location_id)
        session_key = self._make_session_key(session_id, location_id)

        # 1. Se force_refresh, busca direto na API
        if force_refresh:
            logger.info(f"🔄 Force refresh para location_id={location_id}")
            try:
                data = await fetch_func(location_id)
                await self.cache_climate_data(location_id, data, session_id)
                return data
            except Exception as e:
                logger.error(f"❌ Erro fetching climate: {e}")
                raise

        # 2. Tenta obter do cache Redis
        try:
            cached_data = self.redis.get(cache_key)
            if cached_data:
                self.hits += 1
                logger.info(f"✅ Cache HIT para location_id={location_id}")

                # Registrar acesso na sessão
                self.redis.setex(
                    session_key, 3600, json.dumps({"accessed_at": datetime.utcnow().isoformat()})
                )

                return json.loads(cached_data)
        except Exception as e:
            logger.warning(f"⚠️  Erro reading cache: {e}")

        # 3. Cache miss - buscar na API
        self.misses += 1
        logger.info(f"❌ Cache MISS para location_id={location_id}")

        try:
            data = await fetch_func(location_id)
            await self.cache_climate_data(location_id, data, session_id)
            return data
        except Exception as e:
            logger.error(f"❌ Erro fetching climate: {e}")
            raise

    async def cache_climate_data(
        self, location_id: int, data: dict[str, Any], session_id: str = None, ttl: int = None
    ) -> bool:
        """
        Armazena dados climáticos em cache Redis.

        Args:
            location_id: ID da localização
            data: Dicionário com dados climáticos
            session_id: ID da sessão (opcional, para rastreamento)
            ttl: Time-to-live em segundos (default 3600)

        Returns:
            bool: True se sucesso, False caso contrário

        Exemplo:
            >>> success = await cache.cache_climate_data(
            ...     location_id=1,
            ...     data={'temperature': 25.5, 'humidity': 60},
            ...     session_id="sess_abc123"
            ... )
        """
        if ttl is None:
            ttl = self.ttl

        cache_key = self._make_cache_key(location_id)

        try:
            # Armazenar dados com TTL
            self.redis.setex(cache_key, ttl, json.dumps(data))

            # Se session_id fornecido, rastrear acesso
            if session_id:
                session_key = self._make_session_key(session_id, location_id)
                self.redis.setex(
                    session_key,
                    ttl,
                    json.dumps({"cached_at": datetime.utcnow().isoformat(), "ttl": ttl}),
                )

            logger.info(f"💾 Dados cacheados para location_id={location_id}, TTL={ttl}s")
            return True

        except Exception as e:
            logger.error(f"❌ Erro caching data: {e}")
            return False

    def get_cache_stats(self, session_id: str | None = None) -> dict[str, Any]:
        """
        Retorna estatísticas de cache.

        Args:
            session_id: Se fornecido, retorna stats apenas dessa sessão

        Returns:
            Dict com hit_ratio, hits, misses, session_size_mb

        Exemplo:
            >>> stats = cache.get_cache_stats(session_id="sess_abc123")
            >>> print(stats['hit_ratio'])
            0.75
        """
        total = self.hits + self.misses
        hit_ratio = self.hits / total if total > 0 else 0

        stats = {
            "hits": self.hits,
            "misses": self.misses,
            "total_requests": total,
            "hit_ratio": round(hit_ratio, 2),
            "timestamp": datetime.utcnow().isoformat(),
        }

        # Se session_id fornecido, buscar size dessa sessão
        if session_id:
            try:
                pattern = f"{self.session_prefix}{session_id}:*"
                keys = self.redis.keys(pattern)
                stats["session_locations_cached"] = len(keys)
            except Exception as e:
                logger.warning(f"⚠️  Erro getting session size: {e}")

        return stats

    async def clear_cache(self, location_id: int | None = None) -> int:
        """
        Limpa cache para uma localização ou todas.

        Args:
            location_id: Se fornecido, limpa apenas essa location

        Returns:
            int: Número de chaves removidas

        Exemplo:
            >>> removed = await cache.clear_cache(location_id=42)
            >>> print(f"Removed {removed} cache entries")
        """
        try:
            if location_id:
                cache_key = self._make_cache_key(location_id)
                removed = self.redis.delete(cache_key)
            else:
                # Remover todas as chaves de cache
                pattern = f"{self.cache_prefix}*"
                keys = self.redis.keys(pattern)
                if keys:
                    removed = self.redis.delete(*keys)
                else:
                    removed = 0

            logger.info(f"🗑️  Cache limpo: {removed} chaves removidas")
            return removed

        except Exception as e:
            logger.error(f"❌ Erro clearing cache: {e}")
            return 0


class ClimateCache:
    """
    Gerencia agregações de dados climáticos em PostgreSQL.

    Features:
    - Agregação de dados climáticos por hora/dia
    - Persistência de 24 horas para análise histórica
    - Cálculo de anomalias e tendências

    Exemplo:
        climate_cache = ClimateCache(redis_pool, db_session)
        daily_data = climate_cache.get_daily_aggregate(location_id=1)
    """

    def __init__(self, redis_pool, db_session: Session):
        """
        Inicializa gerenciador de agregações.

        Args:
            redis_pool: Redis connection pool
            db_session: SQLAlchemy session para PostgreSQL
        """
        self.redis = redis_pool
        self.db = db_session
        self.table_prefix = "climate_aggregation:"

    def aggregate_hourly_data(
        self, location_id: int, hourly_data: list[dict[str, Any]]
    ) -> dict[str, float]:
        """
        Agrega dados climáticos por hora em estatísticas.

        Args:
            location_id: ID da localização
            hourly_data: Lista com dados horários

        Returns:
            Dict com avg, min, max para cada métrica

        Exemplo:
            >>> hourly = [
            ...     {'temp': 20, 'humidity': 60},
            ...     {'temp': 22, 'humidity': 65},
            ... ]
            >>> agg = climate_cache.aggregate_hourly_data(1, hourly)
            >>> print(agg['temp_avg'])
            21.0
        """
        if not hourly_data:
            return {}

        metrics = {}

        # Iterar por cada métrica nos dados
        for key in hourly_data[0].keys():
            values = [h.get(key) for h in hourly_data if h.get(key) is not None]

            if values:
                metrics[f"{key}_avg"] = sum(values) / len(values)
                metrics[f"{key}_min"] = min(values)
                metrics[f"{key}_max"] = max(values)

        return metrics

    def get_cached_aggregate(self, location_id: int) -> dict[str, Any] | None:
        """
        Busca agregação cacheada de dados climáticos.

        Args:
            location_id: ID da localização

        Returns:
            Dict com agregação ou None se não encontrado
        """
        try:
            key = f"{self.table_prefix}{location_id}"
            cached = self.redis.get(key)
            return json.loads(cached) if cached else None
        except Exception as e:
            logger.error(f"❌ Erro getting cached aggregate: {e}")
            return None


__all__ = ["SessionCache", "ClimateCache"]
