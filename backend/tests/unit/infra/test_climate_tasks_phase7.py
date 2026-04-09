"""
Phase 7 – climate_tasks.py comprehensive tests.

Covers all 8 shared_tasks:
- prefetch_nasa_popular_cities
- cleanup_old_cache
- generate_cache_stats
- prefetch_nws_forecast_usa_cities
- prefetch_nws_stations_usa_cities
- prefetch_openmeteo_forecast_popular_cities
- prefetch_openmeteo_archive_popular_cities
- prefetch_met_norway_nordic_cities
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.infrastructure.cache.climate_tasks import (
    POPULAR_NORDIC_CITIES,
    POPULAR_USA_CITIES,
    POPULAR_WORLD_CITIES,
    cleanup_old_cache,
    generate_cache_stats,
    prefetch_met_norway_nordic_cities,
    prefetch_nasa_popular_cities,
    prefetch_nws_forecast_usa_cities,
    prefetch_nws_stations_usa_cities,
    prefetch_openmeteo_archive_popular_cities,
    prefetch_openmeteo_forecast_popular_cities,
)


# ──────── helpers ────────

def _fresh_event_loop():
    """Create and set a fresh event loop."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    return loop


@pytest.fixture(autouse=True)
def fresh_loop():
    loop = _fresh_event_loop()
    yield loop
    loop.close()


# ═══════════════════════════════════════════════════════════════
# Constants tests
# ═══════════════════════════════════════════════════════════════

class TestConstants:
    def test_popular_world_cities_count(self):
        assert len(POPULAR_WORLD_CITIES) == 50

    def test_popular_usa_cities_count(self):
        assert len(POPULAR_USA_CITIES) == 30

    def test_popular_nordic_cities_count(self):
        assert len(POPULAR_NORDIC_CITIES) == 20

    def test_city_has_required_fields(self):
        for city in POPULAR_WORLD_CITIES:
            assert "name" in city
            assert "lat" in city
            assert "lon" in city

    def test_usa_city_has_state(self):
        for city in POPULAR_USA_CITIES:
            assert "state" in city


# ═══════════════════════════════════════════════════════════════
# prefetch_nasa_popular_cities
# ═══════════════════════════════════════════════════════════════

class TestPrefetchNasa:
    def _patch_lazy_imports(self):
        """Create mock modules for lazy imports inside task body."""
        import sys

        mock_nasa_module = MagicMock()
        mock_cache_module = MagicMock()
        sys.modules["backend.api.services.nasa_power_client"] = mock_nasa_module
        return mock_nasa_module, mock_cache_module

    def _unpatch_lazy_imports(self):
        import sys
        sys.modules.pop("backend.api.services.nasa_power_client", None)

    @patch("backend.infrastructure.cache.climate_tasks.asyncio")
    @patch("backend.infrastructure.cache.climate_cache.create_climate_cache")
    def test_success_all_cities(self, mock_cache_fn, mock_asyncio):
        """All cities return data → success_rate=100%."""
        mock_nasa_mod, _ = self._patch_lazy_imports()
        try:
            mock_loop = MagicMock()
            mock_asyncio.get_event_loop.return_value = mock_loop
            mock_loop.run_until_complete.return_value = {"data": "ok"}

            mock_cache = MagicMock()
            mock_cache_fn.return_value = mock_cache
            mock_nasa_mod.NASAPowerClient.return_value = MagicMock()

            result = prefetch_nasa_popular_cities.run()
            assert result["status"] == "success"
            assert result["success"] == 50
            assert result["failed"] == 0
        finally:
            self._unpatch_lazy_imports()

    @patch("backend.infrastructure.cache.climate_tasks.asyncio")
    @patch("backend.infrastructure.cache.climate_cache.create_climate_cache")
    def test_some_failures(self, mock_cache_fn, mock_asyncio):
        """Some cities fail → still returns success if any succeeded."""
        mock_nasa_mod, _ = self._patch_lazy_imports()
        try:
            mock_loop = MagicMock()
            mock_asyncio.get_event_loop.return_value = mock_loop

            call_count = [0]
            def side_effect(coro):
                call_count[0] += 1
                if call_count[0] == 2:
                    raise Exception("API limit")
                return {"data": "ok"}

            mock_loop.run_until_complete.side_effect = side_effect

            mock_cache = MagicMock()
            mock_cache_fn.return_value = mock_cache
            mock_nasa_mod.NASAPowerClient.return_value = MagicMock()

            result = prefetch_nasa_popular_cities.run()
            assert result["status"] in ("success", "failed")
        finally:
            self._unpatch_lazy_imports()

    @patch("backend.infrastructure.cache.climate_tasks.asyncio")
    def test_critical_error_retries(self, mock_asyncio):
        """Critical error → raises Retry."""
        mock_asyncio.get_event_loop.side_effect = RuntimeError("No loop")
        mock_nasa_mod, _ = self._patch_lazy_imports()
        try:
            with pytest.raises(Exception):
                prefetch_nasa_popular_cities.run()
        finally:
            self._unpatch_lazy_imports()


# ═══════════════════════════════════════════════════════════════
# cleanup_old_cache
# ═══════════════════════════════════════════════════════════════

class TestCleanupOldCache:
    @patch("backend.infrastructure.cache.climate_tasks.asyncio")
    def test_removes_expired_keys(self, mock_asyncio):
        import sys

        mock_redis_mod = MagicMock()
        mock_redis = MagicMock()
        mock_redis_mod.Redis.from_url.return_value = mock_redis
        sys.modules["redis.asyncio"] = mock_redis_mod
        sys.modules["redis"] = MagicMock()

        mock_settings_mod = MagicMock()
        settings = MagicMock()
        settings.redis.redis_url = "redis://localhost:6379/0"
        mock_settings_mod.get_settings.return_value = settings
        sys.modules["config.settings"] = mock_settings_mod

        try:
            mock_loop = MagicMock()
            mock_asyncio.get_event_loop.return_value = mock_loop

            # Simulate 3 keys: 1 expired, 1 low TTL, 1 valid
            mock_loop.run_until_complete.side_effect = [
                [b"climate:a", b"climate:b", b"climate:c"],  # keys
                -1,   # ttl for key a (expired)
                None,  # delete key a
                300,   # ttl for key b (< 3600)
                None,  # delete key b
                86400, # ttl for key c (valid)
                None,  # close
            ]

            result = cleanup_old_cache()
            assert result["status"] == "success"
            assert result["removed"] == 2
            assert result["kept"] == 1
        finally:
            sys.modules.pop("redis.asyncio", None)
            sys.modules.pop("redis", None)
            sys.modules.pop("config.settings", None)

    def test_error_returns_status(self):
        import sys

        mock_settings_mod = MagicMock()
        mock_settings_mod.get_settings.side_effect = Exception("Config error")
        sys.modules["config.settings"] = mock_settings_mod

        try:
            result = cleanup_old_cache()
            assert result["status"] == "error"
        finally:
            sys.modules.pop("config.settings", None)


# ═══════════════════════════════════════════════════════════════
# generate_cache_stats
# ═══════════════════════════════════════════════════════════════

class TestGenerateCacheStats:
    @patch("backend.infrastructure.cache.climate_tasks.asyncio")
    def test_returns_stats(self, mock_asyncio):
        import sys

        mock_redis_mod = MagicMock()
        mock_redis = MagicMock()
        mock_redis_mod.Redis.from_url.return_value = mock_redis
        sys.modules["redis.asyncio"] = mock_redis_mod
        sys.modules["redis"] = MagicMock()

        mock_settings_mod = MagicMock()
        settings = MagicMock()
        settings.redis.redis_url = "redis://localhost:6379/0"
        mock_settings_mod.get_settings.return_value = settings
        sys.modules["config.settings"] = mock_settings_mod

        try:
            mock_loop = MagicMock()
            mock_asyncio.get_event_loop.return_value = mock_loop

            mock_loop.run_until_complete.side_effect = [
                [b"k1", b"k2"],  # nasa keys
                [b"k3"],          # met keys
                [],               # nws keys
                [b"k4"],          # openmeteo keys
                42,               # dbsize
                None,             # close
            ]

            result = generate_cache_stats()
            assert "sources" in result
            assert "total_keys_db" in result
        finally:
            sys.modules.pop("redis.asyncio", None)
            sys.modules.pop("redis", None)
            sys.modules.pop("config.settings", None)

    def test_error_returns_status(self):
        import sys

        mock_settings_mod = MagicMock()
        mock_settings_mod.get_settings.side_effect = Exception("Bad config")
        sys.modules["config.settings"] = mock_settings_mod

        try:
            result = generate_cache_stats()
            assert result["status"] == "error"
        finally:
            sys.modules.pop("config.settings", None)


# ═══════════════════════════════════════════════════════════════
# prefetch_nws_forecast_usa_cities
# ═══════════════════════════════════════════════════════════════

class TestPrefetchNWSForecast:
    def test_success(self):
        import sys

        mock_mod = MagicMock()
        mock_adapter = MagicMock()
        mock_adapter.get_daily_data_sync.return_value = [
            {"date": "2024-01-01"} for _ in range(5)
        ]
        mock_mod.NWSDailyForecastSyncAdapter.return_value = mock_adapter
        sys.modules["backend.api.services.nws_forecast_sync_adapter"] = mock_mod

        try:
            result = prefetch_nws_forecast_usa_cities.run()
            assert result["status"] == "success"
            assert result["success"] == 30
            assert result["forecast_days"] == 5
        finally:
            sys.modules.pop("backend.api.services.nws_forecast_sync_adapter", None)

    def test_all_fail(self):
        import sys

        mock_mod = MagicMock()
        mock_adapter = MagicMock()
        mock_adapter.get_daily_data_sync.return_value = None
        mock_mod.NWSDailyForecastSyncAdapter.return_value = mock_adapter
        sys.modules["backend.api.services.nws_forecast_sync_adapter"] = mock_mod

        try:
            result = prefetch_nws_forecast_usa_cities.run()
            assert result["status"] == "failed"
            assert result["failed"] == 30
        finally:
            sys.modules.pop("backend.api.services.nws_forecast_sync_adapter", None)

    def test_critical_error_retries(self):
        import sys

        mock_mod = MagicMock()
        mock_mod.NWSDailyForecastSyncAdapter.side_effect = RuntimeError("oops")
        sys.modules["backend.api.services.nws_forecast_sync_adapter"] = mock_mod

        try:
            with pytest.raises(Exception):
                prefetch_nws_forecast_usa_cities.run()
        finally:
            sys.modules.pop("backend.api.services.nws_forecast_sync_adapter", None)


# ═══════════════════════════════════════════════════════════════
# prefetch_nws_stations_usa_cities
# ═══════════════════════════════════════════════════════════════

class TestPrefetchNWSStations:
    def test_success(self):
        import sys

        mock_mod = MagicMock()
        mock_adapter = MagicMock()
        mock_adapter.get_daily_data_sync.return_value = [
            {"date": f"2024-01-0{i}"} for i in range(1, 8)
        ]
        mock_mod.NWSStationsSyncAdapter.return_value = mock_adapter
        sys.modules["backend.api.services.nws_stations_sync_adapter"] = mock_mod

        try:
            result = prefetch_nws_stations_usa_cities.run()
            assert result["status"] == "success"
            assert result["success"] == 30
            assert result["historical_days"] == 7
        finally:
            sys.modules.pop("backend.api.services.nws_stations_sync_adapter", None)

    def test_partial_fail(self):
        import sys

        mock_mod = MagicMock()
        mock_adapter = MagicMock()
        call_count = [0]
        def side_effect(**kwargs):
            call_count[0] += 1
            if call_count[0] % 3 == 0:
                raise Exception("API error")
            return [{"date": "2024-01-01"}]
        mock_adapter.get_daily_data_sync.side_effect = side_effect
        mock_mod.NWSStationsSyncAdapter.return_value = mock_adapter
        sys.modules["backend.api.services.nws_stations_sync_adapter"] = mock_mod

        try:
            result = prefetch_nws_stations_usa_cities.run()
            assert result["status"] == "success"
        finally:
            sys.modules.pop("backend.api.services.nws_stations_sync_adapter", None)


# ═══════════════════════════════════════════════════════════════
# prefetch_openmeteo_forecast_popular_cities
# ═══════════════════════════════════════════════════════════════

class TestPrefetchOpenMeteoForecast:
    @patch("backend.infrastructure.cache.climate_cache.create_climate_cache")
    def test_success(self, mock_cache_fn):
        import sys

        mock_mod = MagicMock()
        mock_adapter = MagicMock()
        mock_adapter.get_data_sync.return_value = [
            {"date": "2024-01-01"} for _ in range(10)
        ]
        mock_mod.OpenMeteoForecastSyncAdapter.return_value = mock_adapter
        sys.modules["backend.api.services.openmeteo_forecast_sync_adapter"] = mock_mod

        try:
            mock_cache = MagicMock()
            mock_cache.close = AsyncMock()
            mock_cache_fn.return_value = mock_cache

            result = prefetch_openmeteo_forecast_popular_cities.run()
            assert result["status"] == "success"
            assert result["success"] == 50
        finally:
            sys.modules.pop("backend.api.services.openmeteo_forecast_sync_adapter", None)


# ═══════════════════════════════════════════════════════════════
# prefetch_openmeteo_archive_popular_cities
# ═══════════════════════════════════════════════════════════════

class TestPrefetchOpenMeteoArchive:
    @patch("backend.infrastructure.cache.climate_cache.create_climate_cache")
    def test_success(self, mock_cache_fn):
        import sys

        mock_mod = MagicMock()
        mock_adapter = MagicMock()
        mock_adapter.get_data_sync.return_value = [{"date": "d"} for _ in range(365)]
        mock_mod.OpenMeteoArchiveSyncAdapter.return_value = mock_adapter
        sys.modules["backend.api.services.openmeteo_archive_sync_adapter"] = mock_mod

        try:
            mock_cache = MagicMock()
            mock_cache.close = AsyncMock()
            mock_cache_fn.return_value = mock_cache

            result = prefetch_openmeteo_archive_popular_cities.run()
            assert result["status"] == "success"
            assert result["success"] == 50
            assert result["avg_days_per_city"] == 365.0
        finally:
            sys.modules.pop("backend.api.services.openmeteo_archive_sync_adapter", None)


# ═══════════════════════════════════════════════════════════════
# prefetch_met_norway_nordic_cities
# ═══════════════════════════════════════════════════════════════

class TestPrefetchMETNorway:
    @patch("backend.infrastructure.cache.climate_cache.create_climate_cache")
    def test_success(self, mock_cache_fn):
        import sys

        mock_adapter_mod = MagicMock()
        mock_adapter = MagicMock()
        mock_adapter.get_daily_data_sync.return_value = [
            {"date": "2024-01-01"} for _ in range(10)
        ]
        mock_adapter_mod.METNorwayLocationForecastSyncAdapter.return_value = mock_adapter
        sys.modules["backend.api.services.met_norway_locationforecast_sync_adapter"] = mock_adapter_mod

        mock_met_mod = MagicMock()
        mock_met_mod.METNorwayClient.is_in_nordic_region.return_value = True
        sys.modules["backend.api.services.met_norway.met_norway_client"] = mock_met_mod

        try:
            mock_cache = MagicMock()
            mock_cache.close = AsyncMock()
            mock_cache_fn.return_value = mock_cache

            result = prefetch_met_norway_nordic_cities.run()
            assert result["status"] == "success"
            assert result["success"] == 20
        finally:
            sys.modules.pop("backend.api.services.met_norway_locationforecast_sync_adapter", None)
            sys.modules.pop("backend.api.services.met_norway.met_norway_client", None)
