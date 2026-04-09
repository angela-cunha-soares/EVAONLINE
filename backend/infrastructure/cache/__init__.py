"""
Sistema de cache da aplicação.
"""

from backend.infrastructure.cache.celery_tasks import cleanup_expired_data, update_popular_ranking
from backend.infrastructure.cache.climate_cache import ClimateCacheService, create_climate_cache
from backend.infrastructure.cache.climate_tasks import (
    cleanup_old_cache,
    generate_cache_stats,
    prefetch_nasa_popular_cities,
)

__all__ = [
    # Legacy tasks
    "cleanup_expired_data",
    "update_popular_ranking",
    # Climate cache service
    "ClimateCacheService",
    "create_climate_cache",
    # Climate tasks
    "prefetch_nasa_popular_cities",
    "cleanup_old_cache",
    "generate_cache_stats",
]
