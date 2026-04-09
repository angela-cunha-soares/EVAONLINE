"""
Tests for infrastructure cache layer — SessionCache, ClimateCacheService, CacheManager.

Covers:
- SessionCache: generate_session_id, _make_cache_key, _make_session_key,
  get_or_fetch_climate, cache_climate_data, get_cache_stats, clear_cache
- ClimateCacheService: _make_key, _get_ttl, get, set, delete, exists, ping
- CacheManager (redis_manager): get_eto_data, save_eto_data
- ClimateCache: aggregate_hourly_data, get_cached_aggregate
"""

import json
import pickle
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from backend.infrastructure.cache.cache_manager import SessionCache, ClimateCache


# ════════════════════════════════════════════════════════════════════
# SessionCache — Pure logic helpers
# ════════════════════════════════════════════════════════════════════

class TestSessionCachePureLogic:

    def test_generate_session_id_format(self):
        sid = SessionCache.generate_session_id()
        assert sid.startswith("sess_")
        assert len(sid) == 37  # "sess_" + 32 hex chars

    def test_generate_session_id_unique(self):
        """Each call should generate a unique ID"""
        ids = {SessionCache.generate_session_id() for _ in range(100)}
        assert len(ids) == 100

    def test_make_cache_key(self):
        cache = SessionCache(redis_pool=MagicMock())
        key = cache._make_cache_key(42, "climate")
        assert "42" in key
        assert "climate" in key
        assert key == "climate:cache:42:climate"

    def test_make_cache_key_default_type(self):
        cache = SessionCache(redis_pool=MagicMock())
        key = cache._make_cache_key(1)
        assert "1" in key
        assert "climate" in key

    def test_make_session_key(self):
        cache = SessionCache(redis_pool=MagicMock())
        key = cache._make_session_key("sess_abc123", 42)
        assert "sess_abc123" in key
        assert "42" in key
        assert key == "session:sess_abc123:loc_42"

    def test_initial_metrics(self):
        cache = SessionCache(redis_pool=MagicMock())
        assert cache.hits == 0
        assert cache.misses == 0
        assert cache.ttl == 3600


# ════════════════════════════════════════════════════════════════════
# SessionCache — get_or_fetch_climate (mock Redis)
# ════════════════════════════════════════════════════════════════════

class TestSessionCacheGetOrFetch:

    @pytest.fixture
    def mock_redis(self):
        r = MagicMock()
        r.get.return_value = None
        r.setex.return_value = True
        r.delete.return_value = 1
        r.keys.return_value = []
        return r

    @pytest.fixture
    def cache(self, mock_redis):
        return SessionCache(redis_pool=mock_redis)

    @pytest.mark.asyncio
    async def test_cache_miss_fetches(self, cache):
        """Cache miss → calls fetch_func"""
        async def fetch(lid):
            return {"temperature": 25.0}

        result = await cache.get_or_fetch_climate(1, "sess_abc", fetch_func=fetch)
        assert result == {"temperature": 25.0}
        assert cache.misses == 1

    @pytest.mark.asyncio
    async def test_cache_hit(self, cache, mock_redis):
        """Cache hit → returns cached data"""
        mock_redis.get.return_value = json.dumps({"temperature": 25.0})
        
        async def fetch(lid):
            return {"temperature": 99.0}

        result = await cache.get_or_fetch_climate(1, "sess_abc", fetch_func=fetch)
        assert result == {"temperature": 25.0}
        assert cache.hits == 1

    @pytest.mark.asyncio
    async def test_force_refresh(self, cache, mock_redis):
        """force_refresh=True → always fetches from API"""
        mock_redis.get.return_value = json.dumps({"temperature": 25.0})

        async def fetch(lid):
            return {"temperature": 30.0}

        result = await cache.get_or_fetch_climate(
            1, "sess_abc", fetch_func=fetch, force_refresh=True
        )
        assert result == {"temperature": 30.0}

    @pytest.mark.asyncio
    async def test_no_fetch_func_raises(self, cache):
        with pytest.raises(ValueError, match="fetch_func"):
            await cache.get_or_fetch_climate(1, "sess_abc")


# ════════════════════════════════════════════════════════════════════
# SessionCache — cache_climate_data
# ════════════════════════════════════════════════════════════════════

class TestSessionCacheCacheData:

    @pytest.fixture
    def mock_redis(self):
        r = MagicMock()
        r.setex.return_value = True
        return r

    @pytest.fixture
    def cache(self, mock_redis):
        return SessionCache(redis_pool=mock_redis)

    @pytest.mark.asyncio
    async def test_cache_data_success(self, cache, mock_redis):
        result = await cache.cache_climate_data(
            1, {"temperature": 25.0}, session_id="sess_abc"
        )
        assert result is True
        mock_redis.setex.assert_called()

    @pytest.mark.asyncio
    async def test_cache_data_with_custom_ttl(self, cache, mock_redis):
        result = await cache.cache_climate_data(1, {"temp": 25}, ttl=7200)
        assert result is True

    @pytest.mark.asyncio
    async def test_cache_data_redis_error(self, cache, mock_redis):
        mock_redis.setex.side_effect = Exception("Redis down")
        result = await cache.cache_climate_data(1, {"temp": 25})
        assert result is False


# ════════════════════════════════════════════════════════════════════
# SessionCache — get_cache_stats
# ════════════════════════════════════════════════════════════════════

class TestSessionCacheStats:

    def test_initial_stats(self):
        cache = SessionCache(redis_pool=MagicMock())
        stats = cache.get_cache_stats()
        assert stats["hits"] == 0
        assert stats["misses"] == 0
        assert stats["hit_ratio"] == 0

    def test_after_hits(self):
        cache = SessionCache(redis_pool=MagicMock())
        cache.hits = 3
        cache.misses = 1
        stats = cache.get_cache_stats()
        assert stats["hit_ratio"] == 0.75

    def test_with_session_id(self):
        mock_redis = MagicMock()
        mock_redis.keys.return_value = ["key1", "key2", "key3"]
        cache = SessionCache(redis_pool=mock_redis)
        stats = cache.get_cache_stats(session_id="sess_abc")
        assert stats["session_locations_cached"] == 3


# ════════════════════════════════════════════════════════════════════
# SessionCache — clear_cache
# ════════════════════════════════════════════════════════════════════

class TestSessionCacheClear:

    @pytest.mark.asyncio
    async def test_clear_specific_location(self):
        mock_redis = MagicMock()
        mock_redis.delete.return_value = 1
        cache = SessionCache(redis_pool=mock_redis)
        removed = await cache.clear_cache(location_id=42)
        assert removed == 1

    @pytest.mark.asyncio
    async def test_clear_all(self):
        mock_redis = MagicMock()
        mock_redis.keys.return_value = ["k1", "k2"]
        mock_redis.delete.return_value = 2
        cache = SessionCache(redis_pool=mock_redis)
        removed = await cache.clear_cache()
        assert removed == 2

    @pytest.mark.asyncio
    async def test_clear_no_keys(self):
        mock_redis = MagicMock()
        mock_redis.keys.return_value = []
        cache = SessionCache(redis_pool=mock_redis)
        removed = await cache.clear_cache()
        assert removed == 0

    @pytest.mark.asyncio
    async def test_clear_redis_error(self):
        mock_redis = MagicMock()
        mock_redis.keys.side_effect = Exception("Redis down")
        cache = SessionCache(redis_pool=mock_redis)
        removed = await cache.clear_cache()
        assert removed == 0


# ════════════════════════════════════════════════════════════════════
# ClimateCache — aggregate_hourly_data
# ════════════════════════════════════════════════════════════════════

class TestClimateCacheAggregation:

    @pytest.fixture
    def cc(self):
        return ClimateCache(redis_pool=MagicMock(), db_session=MagicMock())

    def test_aggregate_basic(self, cc):
        hourly = [
            {"temp": 20, "humidity": 60},
            {"temp": 22, "humidity": 65},
            {"temp": 24, "humidity": 70},
        ]
        result = cc.aggregate_hourly_data(1, hourly)
        assert result["temp_avg"] == pytest.approx(22.0)
        assert result["temp_min"] == 20
        assert result["temp_max"] == 24
        assert result["humidity_avg"] == pytest.approx(65.0)

    def test_aggregate_empty(self, cc):
        assert cc.aggregate_hourly_data(1, []) == {}

    def test_aggregate_with_nones(self, cc):
        hourly = [
            {"temp": 20, "humidity": None},
            {"temp": None, "humidity": 65},
            {"temp": 24, "humidity": 70},
        ]
        result = cc.aggregate_hourly_data(1, hourly)
        assert result["temp_avg"] == pytest.approx(22.0)
        assert result["humidity_avg"] == pytest.approx(67.5)

    def test_get_cached_aggregate_hit(self, cc):
        cc.redis.get.return_value = json.dumps({"temp_avg": 22.0})
        result = cc.get_cached_aggregate(1)
        assert result == {"temp_avg": 22.0}

    def test_get_cached_aggregate_miss(self, cc):
        cc.redis.get.return_value = None
        result = cc.get_cached_aggregate(1)
        assert result is None

    def test_get_cached_aggregate_error(self, cc):
        cc.redis.get.side_effect = Exception("Redis error")
        result = cc.get_cached_aggregate(1)
        assert result is None


# ════════════════════════════════════════════════════════════════════
# ClimateCacheService — _make_key, _get_ttl (PURE LOGIC)
# ════════════════════════════════════════════════════════════════════

class TestClimateCacheServicePureLogic:

    @pytest.fixture
    def ccs(self):
        with patch("backend.infrastructure.cache.climate_cache.Redis") as MockRedis:
            MockRedis.from_url.return_value = MagicMock()
            from backend.infrastructure.cache.climate_cache import ClimateCacheService
            return ClimateCacheService(prefix="climate")

    def test_make_key_format(self, ccs):
        key = ccs._make_key(
            "nasa_power", 48.86, 2.35,
            datetime(2024, 10, 1), datetime(2024, 10, 8),
        )
        assert key == "climate:nasa_power:48.86:2.35:20241001:20241008"

    def test_make_key_coordinate_rounding(self, ccs):
        """Coordinates rounded to 2 decimals"""
        key = ccs._make_key(
            "nasa", 48.8611111, 2.35222222,
            datetime(2024, 1, 1), datetime(2024, 1, 7),
        )
        assert "48.86" in key
        assert "2.35" in key

    def test_get_ttl_historical(self, ccs):
        """Data > 30 days old → 30-day TTL"""
        old_date = datetime.now() - timedelta(days=60)
        ttl = ccs._get_ttl(old_date)
        assert ttl == ccs.TTL_HISTORICAL  # 2592000

    def test_get_ttl_recent(self, ccs):
        """Data 7-30 days old → 1-day TTL"""
        recent_date = datetime.now() - timedelta(days=15)
        ttl = ccs._get_ttl(recent_date)
        assert ttl == ccs.TTL_RECENT  # 86400

    def test_get_ttl_very_recent(self, ccs):
        """Data < 7 days old → 12-hour TTL"""
        very_recent = datetime.now() - timedelta(days=3)
        ttl = ccs._get_ttl(very_recent)
        assert ttl == ccs.TTL_VERY_RECENT  # 43200

    def test_get_ttl_forecast(self, ccs):
        """Future data → 1-hour TTL"""
        future = datetime.now() + timedelta(days=3)
        ttl = ccs._get_ttl(future)
        assert ttl == ccs.TTL_FORECAST  # 3600


# ════════════════════════════════════════════════════════════════════
# ClimateCacheService — async methods (mocked Redis)
# ════════════════════════════════════════════════════════════════════

class TestClimateCacheServiceAsync:

    @pytest.fixture
    def ccs(self):
        with patch("backend.infrastructure.cache.climate_cache.Redis") as MockRedis:
            mock_redis = AsyncMock()
            MockRedis.from_url.return_value = mock_redis
            from backend.infrastructure.cache.climate_cache import ClimateCacheService
            svc = ClimateCacheService(prefix="test")
            svc.redis = mock_redis
            return svc

    @pytest.mark.asyncio
    async def test_get_cache_hit(self, ccs):
        data = {"temperature": 25.0}
        ccs.redis.get = AsyncMock(return_value=pickle.dumps(data))
        result = await ccs.get("nasa", 48.86, 2.35, datetime(2024, 1, 1), datetime(2024, 1, 7))
        assert result == data

    @pytest.mark.asyncio
    async def test_get_cache_miss(self, ccs):
        ccs.redis.get = AsyncMock(return_value=None)
        result = await ccs.get("nasa", 48.86, 2.35, datetime(2024, 1, 1), datetime(2024, 1, 7))
        assert result is None

    @pytest.mark.asyncio
    async def test_set_success(self, ccs):
        ccs.redis.setex = AsyncMock()
        result = await ccs.set(
            "nasa", 48.86, 2.35,
            datetime(2024, 1, 1), datetime(2024, 1, 7),
            data={"temperature": 25.0},
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_set_no_redis(self, ccs):
        ccs.redis = None
        result = await ccs.set("nasa", 0, 0, datetime.now(), datetime.now(), data={})
        assert result is False

    @pytest.mark.asyncio
    async def test_set_no_data(self, ccs):
        result = await ccs.set("nasa", 0, 0, datetime.now(), datetime.now(), data=None)
        assert result is False

    @pytest.mark.asyncio
    async def test_delete_success(self, ccs):
        ccs.redis.delete = AsyncMock()
        result = await ccs.delete("nasa", 48.86, 2.35, datetime(2024, 1, 1), datetime(2024, 1, 7))
        assert result is True

    @pytest.mark.asyncio
    async def test_exists_true(self, ccs):
        ccs.redis.exists = AsyncMock(return_value=1)
        result = await ccs.exists("nasa", 48.86, 2.35, datetime(2024, 1, 1), datetime(2024, 1, 7))
        assert result is True

    @pytest.mark.asyncio
    async def test_exists_false(self, ccs):
        ccs.redis.exists = AsyncMock(return_value=0)
        result = await ccs.exists("nasa", 48.86, 2.35, datetime(2024, 1, 1), datetime(2024, 1, 7))
        assert result is False

    @pytest.mark.asyncio
    async def test_get_ttl_remaining(self, ccs):
        ccs.redis.ttl = AsyncMock(return_value=1800)
        result = await ccs.get_ttl_remaining("nasa", 48.86, 2.35, datetime(2024, 1, 1), datetime(2024, 1, 7))
        assert result == 1800

    @pytest.mark.asyncio
    async def test_get_ttl_remaining_expired(self, ccs):
        ccs.redis.ttl = AsyncMock(return_value=-1)
        result = await ccs.get_ttl_remaining("nasa", 48.86, 2.35, datetime(2024, 1, 1), datetime(2024, 1, 7))
        assert result is None

    @pytest.mark.asyncio
    async def test_ping_success(self, ccs):
        ccs.redis.ping = AsyncMock(return_value=True)
        result = await ccs.ping()
        assert result is True

    @pytest.mark.asyncio
    async def test_ping_failure(self, ccs):
        ccs.redis.ping = AsyncMock(side_effect=Exception("down"))
        result = await ccs.ping()
        assert result is False

    @pytest.mark.asyncio
    async def test_ping_no_redis(self, ccs):
        ccs.redis = None
        result = await ccs.ping()
        assert result is False

    @pytest.mark.asyncio
    async def test_get_no_redis(self, ccs):
        ccs.redis = None
        result = await ccs.get("nasa", 0, 0, datetime.now(), datetime.now())
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_no_redis(self, ccs):
        ccs.redis = None
        result = await ccs.delete("nasa", 0, 0, datetime.now(), datetime.now())
        assert result is False

    @pytest.mark.asyncio 
    async def test_exists_no_redis(self, ccs):
        ccs.redis = None
        result = await ccs.exists("nasa", 0, 0, datetime.now(), datetime.now())
        assert result is False


# ════════════════════════════════════════════════════════════════════
# CacheManager (redis_manager.py) — mocked
# ════════════════════════════════════════════════════════════════════

class TestCacheManager:

    @pytest.fixture
    def cm(self):
        import sys
        mock_hits = MagicMock()
        mock_misses = MagicMock()
        mock_pop = MagicMock()
        # Pre-inject mocked module-level symbols so import doesn't fail
        fake_main = MagicMock()
        fake_main.CACHE_HITS = mock_hits
        fake_main.CACHE_MISSES = mock_misses
        fake_main.POPULAR_DATA_ACCESSES = mock_pop
        saved = sys.modules.get("backend.api.main")
        sys.modules["backend.api.main"] = fake_main
        try:
            # Force reimport
            if "backend.infrastructure.cache.redis_manager" in sys.modules:
                del sys.modules["backend.infrastructure.cache.redis_manager"]
            from backend.infrastructure.cache.redis_manager import CacheManager
            mock_redis = AsyncMock()
            mock_db = MagicMock()
            cm = CacheManager(redis_client=mock_redis, db_session=mock_db)
            yield cm
        finally:
            if saved is not None:
                sys.modules["backend.api.main"] = saved
            else:
                sys.modules.pop("backend.api.main", None)

    @pytest.mark.asyncio
    async def test_get_eto_data_redis_hit(self, cm):
        cm.redis.get = AsyncMock(return_value=json.dumps({"et0": 4.5}))
        result = await cm.get_eto_data("test_key")
        assert result == {"et0": 4.5}

    @pytest.mark.asyncio
    async def test_get_eto_data_miss(self, cm):
        cm.redis.get = AsyncMock(return_value=None)
        cm.db.execute.return_value.first.return_value = None
        result = await cm.get_eto_data("test_key")
        assert result is None

    @pytest.mark.asyncio
    async def test_save_eto_data(self, cm):
        cm.redis.setex = AsyncMock()
        cm.db.execute = MagicMock()
        cm.db.commit = MagicMock()
        await cm.save_eto_data("test_key", {"et0": 4.5})
        cm.redis.setex.assert_called_once()
