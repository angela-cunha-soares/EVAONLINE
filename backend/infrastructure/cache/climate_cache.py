"""
Serviço de cache especializado para dados climáticos.
Fornece cache inteligente com TTL dinâmico baseado na idade dos dados.

Features:
- TTL dinâmico: dados históricos (30d), recentes (1d), forecast (1h)
- Métricas Prometheus integradas
- Chaves únicas por fonte + coordenadas + período
- Async/await para alta performance
- Graceful degradation se Redis indisponível
"""

import pickle
from datetime import datetime
from typing import Any

from loguru import logger
from redis.asyncio import Redis

# from config.settings import get_settings
from config.settings.app_config import get_settings

settings = get_settings()


class ClimateCacheService:
    """
    Serviço de cache para dados climáticos com TTL dinâmico.

    Estratégia de TTL:
    - Dados históricos (>30 dias): 30 dias de cache
    - Dados recentes (7-30 dias): 1 dia de cache
    - Dados muito recentes (<7 dias): 12 horas de cache
    - Forecast (futuro): 1 hora de cache

    Chave do cache: {prefix}:{source}:{lat}:{lon}:{start}:{end}
    Exemplo: climate:nasa:48.86:2.35:20241001:20241008
    """

    # TTL constants (em segundos)
    TTL_HISTORICAL = 2592000  # 30 dias
    TTL_RECENT = 86400  # 1 dia
    TTL_VERY_RECENT = 43200  # 12 horas
    TTL_FORECAST = 3600  # 1 hora

    def __init__(self, prefix: str = "climate"):
        """
        Inicializa serviço de cache.

        Args:
            prefix: Prefixo para namespacing das chaves
                   (ex: 'climate', 'nasa', 'met')
        """
        self.prefix = prefix
        self.redis: Redis | None = None
        self._initialize_redis()

    def _initialize_redis(self):
        """Inicializa conexão Redis assíncrona."""
        try:
            self.redis = Redis.from_url(
                settings.REDIS_URL,
                decode_responses=False,
                socket_connect_timeout=5,
                socket_timeout=5,
            )
            logger.info(f"✅ ClimateCacheService inicializado: {self.prefix}")
        except Exception as e:
            logger.error(f"❌ Redis connection failed: {e}")
            self.redis = None

    def _make_key(
        self,
        source: str,
        lat: float,
        lon: float,
        start: datetime,
        end: datetime,
    ) -> str:
        """
        Gera chave única para cache.

        Formato: {prefix}:{source}:{lat}:{lon}:{start}:{end}
        Coordenadas arredondadas para 0.01° (~1km de precisão)

        Args:
            source: Nome da fonte de dados (ex: 'nasa_power', 'met_norway')
            lat: Latitude
            lon: Longitude
            start: Data inicial
            end: Data final

        Returns:
            str: Chave única formatada
        """
        # Arredonda coordenadas para reduzir variações mínimas
        lat_r = round(lat, 2)
        lon_r = round(lon, 2)

        # Formata datas como YYYYMMDD
        start_str = start.strftime("%Y%m%d")
        end_str = end.strftime("%Y%m%d")

        return f"{self.prefix}:{source}:{lat_r}:{lon_r}:{start_str}:{end_str}"

    def _get_ttl(self, start_date: datetime) -> int:
        """
        Calcula TTL dinâmico baseado na idade dos dados.

        Lógica:
        - Dados futuros (forecast): 1 hora
        - Dados <7 dias: 12 horas
        - Dados 7-30 dias: 1 dia
        - Dados >30 dias: 30 dias

        Args:
            start_date: Data inicial dos dados

        Returns:
            int: TTL em segundos
        """
        now = datetime.now()
        days_diff = (now - start_date).days

        if start_date > now:
            # Forecast (futuro)
            return self.TTL_FORECAST
        elif days_diff < 7:
            # Dados muito recentes
            return self.TTL_VERY_RECENT
        elif days_diff < 30:
            # Dados recentes
            return self.TTL_RECENT
        else:
            # Dados históricos
            return self.TTL_HISTORICAL

    async def get(
        self,
        source: str,
        lat: float,
        lon: float,
        start: datetime,
        end: datetime,
    ) -> Any | None:
        """
        Busca dados do cache.

        Args:
            source: Nome da fonte (ex: 'nasa_power')
            lat: Latitude
            lon: Longitude
            start: Data inicial
            end: Data final

        Returns:
            Dados deserializados ou None se não existir/erro
        """
        if not self.redis:
            logger.warning("Redis indisponível, cache desabilitado")
            return None

        key = self._make_key(source, lat, lon, start, end)

        try:
            data = await self.redis.get(key)

            if data:
                logger.info(f"🎯 Cache HIT: {key}")

                # Incrementa métrica Prometheus
                try:
                    from backend.api.middleware.prometheus_metrics import (
                        CACHE_HITS,
                    )

                    CACHE_HITS.labels(key=key).inc()
                except ImportError:
                    pass

                return pickle.loads(data)

            logger.info(f"❌ Cache MISS: {key}")

            # Incrementa métrica Prometheus
            try:
                from backend.api.middleware.prometheus_metrics import (
                    CACHE_MISSES,
                )

                CACHE_MISSES.labels(key=key).inc()
            except ImportError:
                pass

            return None

        except Exception as e:
            logger.error(f"Erro ao buscar cache: {e}")
            return None

    async def set(
        self,
        source: str,
        lat: float,
        lon: float,
        start: datetime,
        end: datetime,
        data: Any,
    ) -> bool:
        """
        Salva dados no cache com TTL dinâmico.

        Args:
            source: Nome da fonte
            lat: Latitude
            lon: Longitude
            start: Data inicial
            end: Data final
            data: Dados a serem salvos (serão serializados com pickle)

        Returns:
            bool: True se salvou com sucesso, False caso contrário
        """
        if not self.redis or not data:
            return False

        key = self._make_key(source, lat, lon, start, end)
        ttl = self._get_ttl(start)

        try:
            serialized = pickle.dumps(data)
            await self.redis.setex(key, ttl, serialized)

            ttl_hours = ttl / 3600
            logger.info(
                f"💾 Cache SAVE: {key} (TTL: {ttl}s / {ttl_hours:.1f}h)"
            )

            # Incrementa métrica de dados populares
            try:
                from backend.api.middleware.prometheus_metrics import (
                    POPULAR_DATA_ACCESSES,
                )

                POPULAR_DATA_ACCESSES.labels(key=key).inc()
            except ImportError:
                pass

            return True

        except Exception as e:
            logger.error(f"Erro ao salvar cache: {e}")
            return False

    async def delete(
        self,
        source: str,
        lat: float,
        lon: float,
        start: datetime,
        end: datetime,
    ) -> bool:
        """
        Remove dados do cache.

        Args:
            source: Nome da fonte
            lat: Latitude
            lon: Longitude
            start: Data inicial
            end: Data final

        Returns:
            bool: True se removeu com sucesso
        """
        if not self.redis:
            return False

        key = self._make_key(source, lat, lon, start, end)

        try:
            await self.redis.delete(key)
            logger.info(f"🗑️ Cache DELETE: {key}")
            return True

        except Exception as e:
            logger.error(f"Erro ao deletar cache: {e}")
            return False

    async def exists(
        self,
        source: str,
        lat: float,
        lon: float,
        start: datetime,
        end: datetime,
    ) -> bool:
        """
        Verifica se dados existem no cache.

        Args:
            source: Nome da fonte
            lat: Latitude
            lon: Longitude
            start: Data inicial
            end: Data final

        Returns:
            bool: True se existe no cache
        """
        if not self.redis:
            return False

        key = self._make_key(source, lat, lon, start, end)

        try:
            exists = await self.redis.exists(key)
            return bool(exists)

        except Exception as e:
            logger.error(f"Erro ao verificar cache: {e}")
            return False

    async def get_ttl_remaining(
        self,
        source: str,
        lat: float,
        lon: float,
        start: datetime,
        end: datetime,
    ) -> int | None:
        """
        Retorna TTL restante de uma chave em segundos.

        Returns:
            int: Segundos restantes ou None se não existir
        """
        if not self.redis:
            return None

        key = self._make_key(source, lat, lon, start, end)

        try:
            ttl = await self.redis.ttl(key)
            return ttl if ttl > 0 else None

        except Exception as e:
            logger.error(f"Erro ao buscar TTL: {e}")
            return None

    async def close(self):
        """Fecha conexão Redis."""
        if self.redis:
            await self.redis.close()
            logger.info(f"✅ Redis connection closed: {self.prefix}")

    async def ping(self) -> bool:
        """
        Testa conexão Redis.

        Returns:
            bool: True se Redis está acessível
        """
        if not self.redis:
            return False

        try:
            await self.redis.ping()
            return True
        except Exception:
            return False


# Factory function para criar cache services
def create_climate_cache(source: str) -> ClimateCacheService:
    """
    Factory function para criar cache service específico por fonte.

    Args:
        source: Nome da fonte ('nasa', 'met', 'nws', 'openmeteo')

    Returns:
        ClimateCacheService configurado
    """
    return ClimateCacheService(prefix=f"climate:{source}")
