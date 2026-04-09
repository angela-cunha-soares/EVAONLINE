"""
Phase 7 – cache_manager.py + climate_cache.py comprehensive tests.

Covers:
- SessionCache: generate_session_id, _make_cache_key, _make_session_key,
  get_or_fetch_climate, cache_climate_data, get_cache_stats, clear_cache
- ClimateCache: aggregate_hourly_data, get_cached_aggregate
- ClimateCacheService: _make_key, _get_ttl, get, set, delete, exists,
  get_ttl_remaining, close, ping
- create_climate_cache factory
"""

import json
import pickle
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.infrastructure.cache.cache_manager import (
    ClimateCache,
    SessionCache,
)


# ═══════════════════════════════════════════════════════════════
# SessionCache
# ═══════════════════════════════════════════════════════════════


class TestSessionCache:
    def test_generate_session_id(self):
        sid = SessionCache.generate_session_id()
        assert sid.startswith("sess_")
        assert len(sid) > 10

    def test_unique_session_ids(self):
        ids = {SessionCache.generate_session_id() for _ in range(100)}
        assert len(ids) == 100

    def test_make_cache_key(self):
        cache = SessionCache(redis_pool=MagicMock())
        key = cache._make_cache_key(42, "climate")
        assert key == "climate:cache:42:climate"

    def test_make_cache_key_default_type(self):
        cache = SessionCache(redis_pool=MagicMock())
        key = cache._make_cache_key(1)
        assert "climate" in key

    def test_make_session_key(self):
        cache = SessionCache(redis_pool=MagicMock())
        key = cache._make_session_key("sess_abc", 1)
        assert key == "session:sess_abc:loc_1"

    @pytest.mark.asyncio
    async def test_get_or_fetch_no_fetch_func_raises(self):
        cache = SessionCache(redis_pool=MagicMock())
        with pytest.raises(ValueError, match="fetch_func"):
            await cache.get_or_fetch_climate(1, "sess_abc")

    @pytest.mark.asyncio
    async def test_get_or_fetch_force_refresh(self):
        mock_redis = MagicMock()
        mock_redis.setex = MagicMock()
        cache = SessionCache(redis_pool=mock_redis)

        async def fetch(loc_id):
            return {"temp": 25}

        result = await cache.get_or_fetch_climate(
            1, "sess_abc", fetch_func=fetch, force_refresh=True
        )
        assert result["temp"] == 25

    @pytest.mark.asyncio
    async def test_get_or_fetch_cache_hit(self):
        mock_redis = MagicMock()
        mock_redis.get.return_value = json.dumps({"temp": 22})
        mock_redis.setex = MagicMock()
        cache = SessionCache(redis_pool=mock_redis)

        async def fetch(loc_id):
            return {"temp": 99}

        result = await cache.get_or_fetch_climate(
            1, "sess_abc", fetch_func=fetch
        )
        assert result["temp"] == 22
        assert cache.hits == 1

    @pytest.mark.asyncio
    async def test_get_or_fetch_cache_miss(self):
        mock_redis = MagicMock()
        mock_redis.get.return_value = None
        mock_redis.setex = MagicMock()
        cache = SessionCache(redis_pool=mock_redis)

        async def fetch(loc_id):
            return {"temp": 30}

        result = await cache.get_or_fetch_climate(
            1, "sess_abc", fetch_func=fetch
        )
        assert result["temp"] == 30
        assert cache.misses == 1

    @pytest.mark.asyncio
    async def test_get_or_fetch_redis_error_falls_through(self):
        mock_redis = MagicMock()
        mock_redis.get.side_effect = Exception("Redis down")
        mock_redis.setex = MagicMock()
        cache = SessionCache(redis_pool=mock_redis)

        async def fetch(loc_id):
            return {"temp": 28}

        result = await cache.get_or_fetch_climate(
            1, "sess_abc", fetch_func=fetch
        )
        assert result["temp"] == 28

    @pytest.mark.asyncio
    async def test_cache_climate_data(self):
        mock_redis = MagicMock()
        cache = SessionCache(redis_pool=mock_redis)

        result = await cache.cache_climate_data(
            1, {"temp": 25}, "sess_abc"
        )
        assert result is True
        mock_redis.setex.assert_called()

    @pytest.mark.asyncio
    async def test_cache_climate_data_error(self):
        mock_redis = MagicMock()
        mock_redis.setex.side_effect = Exception("Write error")
        cache = SessionCache(redis_pool=mock_redis)

        result = await cache.cache_climate_data(1, {"temp": 25})
        assert result is False

    def test_get_cache_stats(self):
        mock_redis = MagicMock()
        cache = SessionCache(redis_pool=mock_redis)
        cache.hits = 3
        cache.misses = 1

        stats = cache.get_cache_stats()
        assert stats["hits"] == 3
        assert stats["misses"] == 1
        assert stats["hit_ratio"] == 0.75

    def test_get_cache_stats_zero_total(self):
        cache = SessionCache(redis_pool=MagicMock())
        stats = cache.get_cache_stats()
        assert stats["hit_ratio"] == 0

    def test_get_cache_stats_with_session(self):
        mock_redis = MagicMock()
        mock_redis.keys.return_value = [b"k1", b"k2"]
        cache = SessionCache(redis_pool=mock_redis)

        stats = cache.get_cache_stats(session_id="sess_abc")
        assert stats["session_locations_cached"] == 2

    @pytest.mark.asyncio
    async def test_clear_cache_single(self):
        mock_redis = MagicMock()
        mock_redis.delete.return_value = 1
        cache = SessionCache(redis_pool=mock_redis)

        removed = await cache.clear_cache(location_id=42)
        assert removed == 1

    @pytest.mark.asyncio
    async def test_clear_cache_all(self):
        mock_redis = MagicMock()
        mock_redis.keys.return_value = [b"k1", b"k2", b"k3"]
        mock_redis.delete.return_value = 3
        cache = SessionCache(redis_pool=mock_redis)

        removed = await cache.clear_cache()
        assert removed == 3

    @pytest.mark.asyncio
    async def test_clear_cache_error(self):
        mock_redis = MagicMock()
        mock_redis.delete.side_effect = Exception("Error")
        cache = SessionCache(redis_pool=mock_redis)

        removed = await cache.clear_cache(location_id=1)
        assert removed == 0


# ═══════════════════════════════════════════════════════════════
# ClimateCache (PostgreSQL aggregations)
# ═══════════════════════════════════════════════════════════════


class TestClimateCache:
    def test_aggregate_hourly_data_empty(self):
        cc = ClimateCache(redis_pool=MagicMock(), db_session=MagicMock())
        assert cc.aggregate_hourly_data(1, []) == {}

    def test_aggregate_hourly_data(self):
        cc = ClimateCache(redis_pool=MagicMock(), db_session=MagicMock())
        data = [
            {"temp": 20, "humidity": 60},
            {"temp": 24, "humidity": 70},
            {"temp": 22, "humidity": 65},
        ]
        result = cc.aggregate_hourly_data(1, data)
        assert result["temp_avg"] == 22.0
        assert result["temp_min"] == 20
        assert result["temp_max"] == 24
        assert result["humidity_avg"] == 65.0

    def test_aggregate_with_none_values(self):
        cc = ClimateCache(redis_pool=MagicMock(), db_session=MagicMock())
        data = [
            {"temp": 20, "humidity": None},
            {"temp": None, "humidity": 70},
        ]
        result = cc.aggregate_hourly_data(1, data)
        assert result["temp_avg"] == 20.0
        assert result["humidity_avg"] == 70.0

    def test_get_cached_aggregate_hit(self):
        mock_redis = MagicMock()
        mock_redis.get.return_value = json.dumps({"temp_avg": 22.0})
        cc = ClimateCache(redis_pool=mock_redis, db_session=MagicMock())

        result = cc.get_cached_aggregate(1)
        assert result["temp_avg"] == 22.0

    def test_get_cached_aggregate_miss(self):
        mock_redis = MagicMock()
        mock_redis.get.return_value = None
        cc = ClimateCache(redis_pool=mock_redis, db_session=MagicMock())

        result = cc.get_cached_aggregate(1)
        assert result is None

    def test_get_cached_aggregate_error(self):
        mock_redis = MagicMock()
        mock_redis.get.side_effect = Exception("Error")
        cc = ClimateCache(redis_pool=mock_redis, db_session=MagicMock())

        result = cc.get_cached_aggregate(1)
        assert result is None


# ═══════════════════════════════════════════════════════════════
# ClimateCacheService
# ═══════════════════════════════════════════════════════════════


class TestClimateCacheService:
    @patch("backend.infrastructure.cache.climate_cache.settings")
    @patch("backend.infrastructure.cache.climate_cache.Redis")
    def test_make_key(self, mock_redis_cls, mock_settings):
        mock_settings.REDIS_URL = "redis://localhost:6379/0"
        mock_redis_cls.from_url.return_value = MagicMock()

        from backend.infrastructure.cache.climate_cache import (
            ClimateCacheService,
        )

        svc = ClimateCacheService(prefix="climate:nasa")
        key = svc._make_key(
            "nasa_power", 48.8566, 2.3522,
            datetime(2024, 1, 1), datetime(2024, 1, 31),
        )
        assert "nasa_power" in key
        assert "48.86" in key
        assert "2.35" in key
        assert "20240101" in key

    @patch("backend.infrastructure.cache.climate_cache.settings")
    @patch("backend.infrastructure.cache.climate_cache.Redis")
    def test_get_ttl_forecast(self, mock_redis_cls, mock_settings):
        mock_settings.REDIS_URL = "redis://localhost:6379/0"
        mock_redis_cls.from_url.return_value = MagicMock()

        from backend.infrastructure.cache.climate_cache import (
            ClimateCacheService,
        )

        svc = ClimateCacheService()
        future = datetime.now() + timedelta(days=3)
        assert svc._get_ttl(future) == 3600  # 1 hour

    @patch("backend.infrastructure.cache.climate_cache.settings")
    @patch("backend.infrastructure.cache.climate_cache.Redis")
    def test_get_ttl_very_recent(self, mock_redis_cls, mock_settings):
        mock_settings.REDIS_URL = "redis://localhost:6379/0"
        mock_redis_cls.from_url.return_value = MagicMock()

        from backend.infrastructure.cache.climate_cache import (
            ClimateCacheService,
        )

        svc = ClimateCacheService()
        recent = datetime.now() - timedelta(days=3)
        assert svc._get_ttl(recent) == 43200  # 12 hours

    @patch("backend.infrastructure.cache.climate_cache.settings")
    @patch("backend.infrastructure.cache.climate_cache.Redis")
    def test_get_ttl_recent(self, mock_redis_cls, mock_settings):
        mock_settings.REDIS_URL = "redis://localhost:6379/0"
        mock_redis_cls.from_url.return_value = MagicMock()

        from backend.infrastructure.cache.climate_cache import (
            ClimateCacheService,
        )

        svc = ClimateCacheService()
        recent = datetime.now() - timedelta(days=15)
        assert svc._get_ttl(recent) == 86400  # 1 day

    @patch("backend.infrastructure.cache.climate_cache.settings")
    @patch("backend.infrastructure.cache.climate_cache.Redis")
    def test_get_ttl_historical(self, mock_redis_cls, mock_settings):
        mock_settings.REDIS_URL = "redis://localhost:6379/0"
        mock_redis_cls.from_url.return_value = MagicMock()

        from backend.infrastructure.cache.climate_cache import (
            ClimateCacheService,
        )

        svc = ClimateCacheService()
        old = datetime.now() - timedelta(days=60)
        assert svc._get_ttl(old) == 2592000  # 30 days

    @patch("backend.infrastructure.cache.climate_cache.settings")
    @patch("backend.infrastructure.cache.climate_cache.Redis")
    @pytest.mark.asyncio
    async def test_get_cache_hit(self, mock_redis_cls, mock_settings):
        mock_settings.REDIS_URL = "redis://localhost:6379/0"
        mock_redis = AsyncMock()
        mock_redis.get.return_value = pickle.dumps({"temp": 25})
        mock_redis_cls.from_url.return_value = mock_redis

        from backend.infrastructure.cache.climate_cache import (
            ClimateCacheService,
        )

        svc = ClimateCacheService()
        svc.redis = mock_redis

        result = await svc.get(
            "nasa", 48.0, 2.0,
            datetime(2024, 1, 1), datetime(2024, 1, 7),
        )
        assert result["temp"] == 25

    @patch("backend.infrastructure.cache.climate_cache.settings")
    @patch("backend.infrastructure.cache.climate_cache.Redis")
    @pytest.mark.asyncio
    async def test_get_cache_miss(self, mock_redis_cls, mock_settings):
        mock_settings.REDIS_URL = "redis://localhost:6379/0"
        mock_redis = AsyncMock()
        mock_redis.get.return_value = None
        mock_redis_cls.from_url.return_value = mock_redis

        from backend.infrastructure.cache.climate_cache import (
            ClimateCacheService,
        )

        svc = ClimateCacheService()
        svc.redis = mock_redis

        result = await svc.get(
            "nasa", 48.0, 2.0,
            datetime(2024, 1, 1), datetime(2024, 1, 7),
        )
        assert result is None

    @patch("backend.infrastructure.cache.climate_cache.settings")
    @patch("backend.infrastructure.cache.climate_cache.Redis")
    @pytest.mark.asyncio
    async def test_get_no_redis(self, mock_redis_cls, mock_settings):
        mock_settings.REDIS_URL = "redis://localhost:6379/0"
        mock_redis_cls.from_url.side_effect = Exception("No Redis")

        from backend.infrastructure.cache.climate_cache import (
            ClimateCacheService,
        )

        svc = ClimateCacheService()
        svc.redis = None

        result = await svc.get(
            "nasa", 48.0, 2.0,
            datetime(2024, 1, 1), datetime(2024, 1, 7),
        )
        assert result is None

    @patch("backend.infrastructure.cache.climate_cache.settings")
    @patch("backend.infrastructure.cache.climate_cache.Redis")
    @pytest.mark.asyncio
    async def test_set_success(self, mock_redis_cls, mock_settings):
        mock_settings.REDIS_URL = "redis://localhost:6379/0"
        mock_redis = AsyncMock()
        mock_redis_cls.from_url.return_value = mock_redis

        from backend.infrastructure.cache.climate_cache import (
            ClimateCacheService,
        )

        svc = ClimateCacheService()
        svc.redis = mock_redis

        result = await svc.set(
            "nasa", 48.0, 2.0,
            datetime(2024, 1, 1), datetime(2024, 1, 7),
            {"temp": 25},
        )
        assert result is True
        mock_redis.setex.assert_called_once()

    @patch("backend.infrastructure.cache.climate_cache.settings")
    @patch("backend.infrastructure.cache.climate_cache.Redis")
    @pytest.mark.asyncio
    async def test_set_no_data(self, mock_redis_cls, mock_settings):
        mock_settings.REDIS_URL = "redis://localhost:6379/0"
        mock_redis = AsyncMock()
        mock_redis_cls.from_url.return_value = mock_redis

        from backend.infrastructure.cache.climate_cache import (
            ClimateCacheService,
        )

        svc = ClimateCacheService()
        svc.redis = mock_redis

        result = await svc.set(
            "nasa", 48.0, 2.0,
            datetime(2024, 1, 1), datetime(2024, 1, 7),
            None,
        )
        assert result is False

    @patch("backend.infrastructure.cache.climate_cache.settings")
    @patch("backend.infrastructure.cache.climate_cache.Redis")
    @pytest.mark.asyncio
    async def test_delete_success(self, mock_redis_cls, mock_settings):
        mock_settings.REDIS_URL = "redis://localhost:6379/0"
        mock_redis = AsyncMock()
        mock_redis_cls.from_url.return_value = mock_redis

        from backend.infrastructure.cache.climate_cache import (
            ClimateCacheService,
        )

        svc = ClimateCacheService()
        svc.redis = mock_redis

        result = await svc.delete(
            "nasa", 48.0, 2.0,
            datetime(2024, 1, 1), datetime(2024, 1, 7),
        )
        assert result is True

    @patch("backend.infrastructure.cache.climate_cache.settings")
    @patch("backend.infrastructure.cache.climate_cache.Redis")
    @pytest.mark.asyncio
    async def test_exists(self, mock_redis_cls, mock_settings):
        mock_settings.REDIS_URL = "redis://localhost:6379/0"
        mock_redis = AsyncMock()
        mock_redis.exists.return_value = 1
        mock_redis_cls.from_url.return_value = mock_redis

        from backend.infrastructure.cache.climate_cache import (
            ClimateCacheService,
        )

        svc = ClimateCacheService()
        svc.redis = mock_redis

        result = await svc.exists(
            "nasa", 48.0, 2.0,
            datetime(2024, 1, 1), datetime(2024, 1, 7),
        )
        assert result is True

    @patch("backend.infrastructure.cache.climate_cache.settings")
    @patch("backend.infrastructure.cache.climate_cache.Redis")
    @pytest.mark.asyncio
    async def test_get_ttl_remaining(self, mock_redis_cls, mock_settings):
        mock_settings.REDIS_URL = "redis://localhost:6379/0"
        mock_redis = AsyncMock()
        mock_redis.ttl.return_value = 3600
        mock_redis_cls.from_url.return_value = mock_redis

        from backend.infrastructure.cache.climate_cache import (
            ClimateCacheService,
        )

        svc = ClimateCacheService()
        svc.redis = mock_redis

        result = await svc.get_ttl_remaining(
            "nasa", 48.0, 2.0,
            datetime(2024, 1, 1), datetime(2024, 1, 7),
        )
        assert result == 3600

    @patch("backend.infrastructure.cache.climate_cache.settings")
    @patch("backend.infrastructure.cache.climate_cache.Redis")
    @pytest.mark.asyncio
    async def test_close(self, mock_redis_cls, mock_settings):
        mock_settings.REDIS_URL = "redis://localhost:6379/0"
        mock_redis = AsyncMock()
        mock_redis_cls.from_url.return_value = mock_redis

        from backend.infrastructure.cache.climate_cache import (
            ClimateCacheService,
        )

        svc = ClimateCacheService()
        svc.redis = mock_redis

        await svc.close()
        mock_redis.close.assert_called_once()

    @patch("backend.infrastructure.cache.climate_cache.settings")
    @patch("backend.infrastructure.cache.climate_cache.Redis")
    @pytest.mark.asyncio
    async def test_ping_success(self, mock_redis_cls, mock_settings):
        mock_settings.REDIS_URL = "redis://localhost:6379/0"
        mock_redis = AsyncMock()
        mock_redis.ping.return_value = True
        mock_redis_cls.from_url.return_value = mock_redis

        from backend.infrastructure.cache.climate_cache import (
            ClimateCacheService,
        )

        svc = ClimateCacheService()
        svc.redis = mock_redis

        result = await svc.ping()
        assert result is True

    @patch("backend.infrastructure.cache.climate_cache.settings")
    @patch("backend.infrastructure.cache.climate_cache.Redis")
    @pytest.mark.asyncio
    async def test_ping_failure(self, mock_redis_cls, mock_settings):
        mock_settings.REDIS_URL = "redis://localhost:6379/0"
        mock_redis = AsyncMock()
        mock_redis.ping.side_effect = Exception("Connection refused")
        mock_redis_cls.from_url.return_value = mock_redis

        from backend.infrastructure.cache.climate_cache import (
            ClimateCacheService,
        )

        svc = ClimateCacheService()
        svc.redis = mock_redis

        result = await svc.ping()
        assert result is False


class TestCreateClimateCache:
    @patch("backend.infrastructure.cache.climate_cache.settings")
    @patch("backend.infrastructure.cache.climate_cache.Redis")
    def test_factory_creates_service(self, mock_redis_cls, mock_settings):
        mock_settings.REDIS_URL = "redis://localhost:6379/0"
        mock_redis_cls.from_url.return_value = MagicMock()

        from backend.infrastructure.cache.climate_cache import (
            create_climate_cache,
        )

        svc = create_climate_cache("nasa")
        assert svc.prefix == "climate:nasa"
