"""
Phase 4 Tests: Climate Tasks (Celery prefetch tasks).

Tests the Celery shared_tasks in climate_tasks.py:
- City list constants: POPULAR_WORLD_CITIES, POPULAR_USA_CITIES, POPULAR_NORDIC_CITIES
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
import sys
import types
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def _fresh_event_loop():
    """Ensure a fresh event loop (prevents 'loop is closed' in full suite)."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield
    loop.close()



# ============================================================================
# City Constants Tests
# ============================================================================

class TestCityConstants:
    """Tests for POPULAR_WORLD_CITIES, POPULAR_USA_CITIES, POPULAR_NORDIC_CITIES."""

    def test_popular_world_cities_count(self):
        from backend.infrastructure.cache.climate_tasks import POPULAR_WORLD_CITIES
        assert len(POPULAR_WORLD_CITIES) == 50

    def test_popular_world_cities_structure(self):
        from backend.infrastructure.cache.climate_tasks import POPULAR_WORLD_CITIES
        for city in POPULAR_WORLD_CITIES:
            assert "name" in city
            assert "lat" in city
            assert "lon" in city
            assert "country" in city
            assert -90 <= city["lat"] <= 90
            assert -180 <= city["lon"] <= 180

    def test_popular_usa_cities_count(self):
        from backend.infrastructure.cache.climate_tasks import POPULAR_USA_CITIES
        assert len(POPULAR_USA_CITIES) >= 20

    def test_popular_usa_cities_structure(self):
        from backend.infrastructure.cache.climate_tasks import POPULAR_USA_CITIES
        for city in POPULAR_USA_CITIES:
            assert "name" in city
            assert "lat" in city
            assert "lon" in city
            assert "state" in city

    def test_popular_nordic_cities_count(self):
        from backend.infrastructure.cache.climate_tasks import POPULAR_NORDIC_CITIES
        assert len(POPULAR_NORDIC_CITIES) >= 15

    def test_popular_nordic_cities_structure(self):
        from backend.infrastructure.cache.climate_tasks import POPULAR_NORDIC_CITIES
        for city in POPULAR_NORDIC_CITIES:
            assert "name" in city
            assert "lat" in city
            assert "lon" in city
            assert "country" in city

    def test_world_cities_has_known_cities(self):
        from backend.infrastructure.cache.climate_tasks import POPULAR_WORLD_CITIES
        names = [c["name"] for c in POPULAR_WORLD_CITIES]
        assert "Paris" in names
        assert "Tokyo" in names
        assert "São Paulo" in names

    def test_usa_cities_has_known_cities(self):
        from backend.infrastructure.cache.climate_tasks import POPULAR_USA_CITIES
        names = [c["name"] for c in POPULAR_USA_CITIES]
        assert "New York" in names
        assert "Los Angeles" in names
        assert "Denver" in names

    def test_nordic_cities_has_oslo(self):
        from backend.infrastructure.cache.climate_tasks import POPULAR_NORDIC_CITIES
        names = [c["name"] for c in POPULAR_NORDIC_CITIES]
        assert "Oslo" in names

    def test_world_cities_no_duplicates(self):
        from backend.infrastructure.cache.climate_tasks import POPULAR_WORLD_CITIES
        names = [c["name"] for c in POPULAR_WORLD_CITIES]
        assert len(names) == len(set(names))

    def test_usa_cities_no_duplicates(self):
        from backend.infrastructure.cache.climate_tasks import POPULAR_USA_CITIES
        names = [c["name"] for c in POPULAR_USA_CITIES]
        assert len(names) == len(set(names))

    def test_nordic_cities_no_duplicates(self):
        from backend.infrastructure.cache.climate_tasks import POPULAR_NORDIC_CITIES
        names = [c["name"] for c in POPULAR_NORDIC_CITIES]
        assert len(names) == len(set(names))

    def test_usa_cities_coordinates_in_americas(self):
        from backend.infrastructure.cache.climate_tasks import POPULAR_USA_CITIES
        for city in POPULAR_USA_CITIES:
            # USA latitudes generally 18-72, longitudes -180 to -64
            assert 18 <= city["lat"] <= 72, f"{city['name']} lat out of range"
            assert -180 <= city["lon"] <= -64, f"{city['name']} lon out of range"

    def test_nordic_cities_in_scandinavia(self):
        from backend.infrastructure.cache.climate_tasks import POPULAR_NORDIC_CITIES
        for city in POPULAR_NORDIC_CITIES:
            assert 54 <= city["lat"] <= 72, f"{city['name']} lat out of range"
            assert -25 <= city["lon"] <= 35, f"{city['name']} lon out of range"


# ============================================================================
# Helper to create fake modules for local imports inside tasks
# ============================================================================

def _inject_fake_module(name, **attrs):
    """Create a fake module in sys.modules with given attributes."""
    mod = types.ModuleType(name)
    for k, v in attrs.items():
        setattr(mod, k, v)
    sys.modules[name] = mod
    return mod


# ============================================================================
# Prefetch NASA Task Tests
# ============================================================================

class TestPrefetchNASATask:
    """Tests for prefetch_nasa_popular_cities task."""

    def test_prefetch_nasa_success(self):
        """Test NASA prefetch with all cities succeeding."""
        mock_client = MagicMock()
        mock_cache = MagicMock()
        mock_cache_factory = MagicMock(return_value=mock_cache)
        mock_nasa_cls = MagicMock(return_value=mock_client)

        # Inject fake modules that the task imports locally
        _inject_fake_module(
            "backend.api.services.nasa_power_client",
            NASAPowerClient=mock_nasa_cls,
        )

        try:
            with patch(
                "backend.infrastructure.cache.climate_cache.create_climate_cache",
                mock_cache_factory,
            ), patch(
                "backend.infrastructure.cache.climate_tasks.asyncio"
            ) as mock_asyncio:
                mock_loop = MagicMock()
                mock_loop.run_until_complete.return_value = {"data": [1, 2]}
                mock_asyncio.get_event_loop.return_value = mock_loop

                from backend.infrastructure.cache.climate_tasks import (
                    prefetch_nasa_popular_cities,
                )

                result = prefetch_nasa_popular_cities()
                assert result["status"] == "success"
                assert result["total_cities"] == 50
                assert result["success"] == 50
                assert result["failed"] == 0
        finally:
            sys.modules.pop("backend.api.services.nasa_power_client", None)

    def test_prefetch_nasa_all_fail(self):
        """Test NASA prefetch with all cities failing (no data)."""
        mock_client = MagicMock()
        mock_cache = MagicMock()
        mock_cache_factory = MagicMock(return_value=mock_cache)
        mock_nasa_cls = MagicMock(return_value=mock_client)

        _inject_fake_module(
            "backend.api.services.nasa_power_client",
            NASAPowerClient=mock_nasa_cls,
        )

        try:
            with patch(
                "backend.infrastructure.cache.climate_cache.create_climate_cache",
                mock_cache_factory,
            ), patch(
                "backend.infrastructure.cache.climate_tasks.asyncio"
            ) as mock_asyncio:
                mock_loop = MagicMock()
                mock_loop.run_until_complete.return_value = None
                mock_asyncio.get_event_loop.return_value = mock_loop

                from backend.infrastructure.cache.climate_tasks import (
                    prefetch_nasa_popular_cities,
                )

                result = prefetch_nasa_popular_cities()
                assert result["failed"] == 50
                assert result["success"] == 0
                assert result["status"] == "failed"
        finally:
            sys.modules.pop("backend.api.services.nasa_power_client", None)

    def test_prefetch_nasa_partial_success(self):
        """Test NASA prefetch with some cities failing."""
        mock_client = MagicMock()
        mock_cache = MagicMock()
        mock_cache_factory = MagicMock(return_value=mock_cache)
        mock_nasa_cls = MagicMock(return_value=mock_client)

        _inject_fake_module(
            "backend.api.services.nasa_power_client",
            NASAPowerClient=mock_nasa_cls,
        )

        call_count = [0]

        def side_effect(coro):
            call_count[0] += 1
            # First 25 return data, rest return None
            if call_count[0] <= 25:
                return {"data": [1]}
            return None

        try:
            with patch(
                "backend.infrastructure.cache.climate_cache.create_climate_cache",
                mock_cache_factory,
            ), patch(
                "backend.infrastructure.cache.climate_tasks.asyncio"
            ) as mock_asyncio:
                mock_loop = MagicMock()
                mock_loop.run_until_complete.side_effect = side_effect
                mock_asyncio.get_event_loop.return_value = mock_loop

                from backend.infrastructure.cache.climate_tasks import (
                    prefetch_nasa_popular_cities,
                )

                result = prefetch_nasa_popular_cities()
                assert result["status"] == "success"
                assert result["success"] == 25
                assert result["failed"] == 25
        finally:
            sys.modules.pop("backend.api.services.nasa_power_client", None)


# ============================================================================
# Cleanup Cache Tests
# ============================================================================

class TestCleanupOldCache:
    """Tests for cleanup_old_cache task."""

    def test_cleanup_removes_expired(self):
        """Test cleanup removes expired and low-TTL keys."""
        with patch(
            "backend.infrastructure.cache.climate_tasks.asyncio"
        ) as mock_asyncio, patch(
            "config.settings.get_settings"
        ) as mock_settings, patch(
            "redis.asyncio.Redis"
        ) as mock_redis_cls:
            mock_settings_obj = MagicMock()
            mock_settings_obj.redis.redis_url = "redis://localhost:6379/0"
            mock_settings.return_value = mock_settings_obj

            mock_redis = MagicMock()
            mock_redis_cls.from_url.return_value = mock_redis

            mock_loop = MagicMock()
            # keys, ttl1, delete1, ttl2, delete2, ttl3, close
            mock_loop.run_until_complete.side_effect = [
                [b"climate:k1", b"climate:k2", b"climate:k3"],
                -1,    # k1: expired -> delete
                1,     # delete result
                100,   # k2: low TTL -> delete
                1,     # delete result
                86400, # k3: valid TTL -> keep
                None,  # redis.close()
            ]
            mock_asyncio.get_event_loop.return_value = mock_loop

            from backend.infrastructure.cache.climate_tasks import (
                cleanup_old_cache,
            )
            result = cleanup_old_cache()
            assert result["status"] == "success"
            assert result["removed"] == 2
            assert result["kept"] == 1

    def test_cleanup_no_keys(self):
        """Test cleanup with no keys to clean."""
        with patch(
            "backend.infrastructure.cache.climate_tasks.asyncio"
        ) as mock_asyncio, patch(
            "config.settings.get_settings"
        ) as mock_settings, patch(
            "redis.asyncio.Redis"
        ) as mock_redis_cls:
            mock_settings_obj = MagicMock()
            mock_settings_obj.redis.redis_url = "redis://localhost:6379/0"
            mock_settings.return_value = mock_settings_obj
            mock_redis_cls.from_url.return_value = MagicMock()

            mock_loop = MagicMock()
            mock_loop.run_until_complete.side_effect = [
                [],    # no keys
                None,  # redis.close()
            ]
            mock_asyncio.get_event_loop.return_value = mock_loop

            from backend.infrastructure.cache.climate_tasks import (
                cleanup_old_cache,
            )
            result = cleanup_old_cache()
            assert result["status"] == "success"
            assert result["removed"] == 0

    def test_cleanup_redis_error(self):
        """Test cleanup handles Redis errors gracefully."""
        with patch(
            "backend.infrastructure.cache.climate_tasks.asyncio"
        ) as mock_asyncio, patch(
            "config.settings.get_settings"
        ) as mock_settings, patch(
            "redis.asyncio.Redis"
        ) as mock_redis_cls:
            mock_settings_obj = MagicMock()
            mock_settings_obj.redis.redis_url = "redis://localhost:6379/0"
            mock_settings.return_value = mock_settings_obj
            mock_redis_cls.from_url.side_effect = Exception("Redis down")

            mock_loop = MagicMock()
            mock_asyncio.get_event_loop.return_value = mock_loop

            from backend.infrastructure.cache.climate_tasks import (
                cleanup_old_cache,
            )
            result = cleanup_old_cache()
            assert result["status"] == "error"


# ============================================================================
# Generate Cache Stats Tests
# ============================================================================

class TestGenerateCacheStats:
    """Tests for generate_cache_stats task."""

    def test_generate_stats_success(self):
        """Test stats generation with data from multiple sources."""
        with patch(
            "backend.infrastructure.cache.climate_tasks.asyncio"
        ) as mock_asyncio, patch(
            "config.settings.get_settings"
        ) as mock_settings, patch(
            "redis.asyncio.Redis"
        ) as mock_redis_cls:
            mock_settings_obj = MagicMock()
            mock_settings_obj.redis.redis_url = "redis://localhost:6379/0"
            mock_settings.return_value = mock_settings_obj
            mock_redis_cls.from_url.return_value = MagicMock()

            mock_loop = MagicMock()
            # Keys for each source + dbsize + close
            mock_loop.run_until_complete.side_effect = [
                [b"climate:nasa:k1", b"climate:nasa:k2"],  # nasa
                [b"climate:met:k1"],  # met
                [],  # nws
                [b"climate:openmeteo:k1", b"climate:openmeteo:k2",
                 b"climate:openmeteo:k3"],  # openmeteo
                100,  # dbsize
                None,  # close
            ]
            mock_asyncio.get_event_loop.return_value = mock_loop

            from backend.infrastructure.cache.climate_tasks import (
                generate_cache_stats,
            )
            result = generate_cache_stats()
            assert "sources" in result
            assert result["sources"]["nasa"]["total_keys"] == 2
            assert result["sources"]["openmeteo"]["total_keys"] == 3
            assert result["total_keys_db"] == 100

    def test_generate_stats_error(self):
        """Test stats handles errors gracefully."""
        with patch(
            "backend.infrastructure.cache.climate_tasks.asyncio"
        ) as mock_asyncio, patch(
            "config.settings.get_settings"
        ) as mock_settings, patch(
            "redis.asyncio.Redis"
        ) as mock_redis_cls:
            mock_settings.side_effect = Exception("Config error")

            from backend.infrastructure.cache.climate_tasks import (
                generate_cache_stats,
            )
            result = generate_cache_stats()
            assert result["status"] == "error"


# ============================================================================
# Prefetch NWS Forecast Tests
# ============================================================================

class TestPrefetchNWSForecast:
    """Tests for prefetch_nws_forecast_usa_cities task."""

    def test_prefetch_nws_forecast_success(self):
        """Test NWS forecast prefetch with mocked adapter."""
        mock_adapter = MagicMock()
        mock_adapter.get_daily_data_sync.return_value = [MagicMock()]
        mock_adapter_cls = MagicMock(return_value=mock_adapter)

        _inject_fake_module(
            "backend.api.services.nws_forecast_sync_adapter",
            NWSDailyForecastSyncAdapter=mock_adapter_cls,
        )

        try:
            from backend.infrastructure.cache.climate_tasks import (
                prefetch_nws_forecast_usa_cities,
            )
            result = prefetch_nws_forecast_usa_cities()
            assert result["status"] == "success"
            assert "total_cities" in result
            assert result["forecast_days"] == 5
        finally:
            sys.modules.pop("backend.api.services.nws_forecast_sync_adapter", None)

    def test_prefetch_nws_forecast_all_fail(self):
        """Test NWS forecast prefetch when adapter returns empty."""
        mock_adapter = MagicMock()
        mock_adapter.get_daily_data_sync.return_value = []
        mock_adapter_cls = MagicMock(return_value=mock_adapter)

        _inject_fake_module(
            "backend.api.services.nws_forecast_sync_adapter",
            NWSDailyForecastSyncAdapter=mock_adapter_cls,
        )

        try:
            from backend.infrastructure.cache.climate_tasks import (
                prefetch_nws_forecast_usa_cities,
            )
            result = prefetch_nws_forecast_usa_cities()
            assert result["status"] == "failed"
        finally:
            sys.modules.pop("backend.api.services.nws_forecast_sync_adapter", None)


# ============================================================================
# Prefetch NWS Stations Tests
# ============================================================================

class TestPrefetchNWSStations:
    """Tests for prefetch_nws_stations_usa_cities task."""

    def test_prefetch_nws_stations_success(self):
        mock_adapter = MagicMock()
        mock_adapter.get_daily_data_sync.return_value = [MagicMock(), MagicMock()]
        mock_adapter_cls = MagicMock(return_value=mock_adapter)

        _inject_fake_module(
            "backend.api.services.nws_stations_sync_adapter",
            NWSStationsSyncAdapter=mock_adapter_cls,
        )

        try:
            from backend.infrastructure.cache.climate_tasks import (
                prefetch_nws_stations_usa_cities,
            )
            result = prefetch_nws_stations_usa_cities()
            assert result["status"] == "success"
            assert "total_cities" in result
        finally:
            sys.modules.pop("backend.api.services.nws_stations_sync_adapter", None)

    def test_prefetch_nws_stations_exception(self):
        mock_adapter = MagicMock()
        mock_adapter.get_daily_data_sync.side_effect = Exception("API timeout")
        mock_adapter_cls = MagicMock(return_value=mock_adapter)

        _inject_fake_module(
            "backend.api.services.nws_stations_sync_adapter",
            NWSStationsSyncAdapter=mock_adapter_cls,
        )

        try:
            from backend.infrastructure.cache.climate_tasks import (
                prefetch_nws_stations_usa_cities,
            )
            result = prefetch_nws_stations_usa_cities()
            # All cities fail but task completes
            assert result["status"] == "failed"
            assert result["success"] == 0
        finally:
            sys.modules.pop("backend.api.services.nws_stations_sync_adapter", None)


# ============================================================================
# Prefetch OpenMeteo Forecast Tests
# ============================================================================

class TestPrefetchOpenMeteoForecast:
    """Tests for prefetch_openmeteo_forecast_popular_cities task."""

    def test_prefetch_openmeteo_forecast_success(self):
        mock_adapter = MagicMock()
        mock_adapter.get_data_sync.return_value = [{"date": "2025-06-15"}]
        mock_adapter_cls = MagicMock(return_value=mock_adapter)

        # Task uses local `import asyncio` so we can't patch climate_tasks.asyncio.
        # Instead, make cache.close() return a real coroutine for run_until_complete.
        mock_cache = MagicMock()
        mock_cache.close = AsyncMock()
        mock_cache_factory = MagicMock(return_value=mock_cache)

        _inject_fake_module(
            "backend.api.services.openmeteo_forecast_sync_adapter",
            OpenMeteoForecastSyncAdapter=mock_adapter_cls,
        )

        try:
            with patch(
                "backend.infrastructure.cache.climate_cache.create_climate_cache",
                mock_cache_factory,
            ):
                from backend.infrastructure.cache.climate_tasks import (
                    prefetch_openmeteo_forecast_popular_cities,
                )
                result = prefetch_openmeteo_forecast_popular_cities()
                assert result["status"] == "success"
                assert "total_cities" in result
        finally:
            sys.modules.pop("backend.api.services.openmeteo_forecast_sync_adapter", None)


# ============================================================================
# Prefetch OpenMeteo Archive Tests
# ============================================================================

class TestPrefetchOpenMeteoArchive:
    """Tests for prefetch_openmeteo_archive_popular_cities task."""

    def test_prefetch_openmeteo_archive_success(self):
        mock_adapter = MagicMock()
        mock_adapter.get_data_sync.return_value = [{"date": "2025-01-01"}]
        mock_adapter_cls = MagicMock(return_value=mock_adapter)

        # Task uses local `import asyncio` — need real awaitable for cache.close()
        mock_cache = MagicMock()
        mock_cache.close = AsyncMock()
        mock_cache_factory = MagicMock(return_value=mock_cache)

        _inject_fake_module(
            "backend.api.services.openmeteo_archive_sync_adapter",
            OpenMeteoArchiveSyncAdapter=mock_adapter_cls,
        )

        try:
            with patch(
                "backend.infrastructure.cache.climate_cache.create_climate_cache",
                mock_cache_factory,
            ):
                from backend.infrastructure.cache.climate_tasks import (
                    prefetch_openmeteo_archive_popular_cities,
                )
                result = prefetch_openmeteo_archive_popular_cities()
                assert result["status"] == "success"
                assert "total_cities" in result
        finally:
            sys.modules.pop("backend.api.services.openmeteo_archive_sync_adapter", None)


# ============================================================================
# Prefetch MET Norway Tests
# ============================================================================

class TestPrefetchMETNorway:
    """Tests for prefetch_met_norway_nordic_cities task."""

    def test_prefetch_met_norway_success(self):
        mock_adapter = MagicMock()
        mock_adapter.get_daily_data_sync.return_value = [MagicMock()]
        mock_adapter_cls = MagicMock(return_value=mock_adapter)

        # Task uses local `import asyncio` — need real awaitable for cache.close()
        mock_cache = MagicMock()
        mock_cache.close = AsyncMock()
        mock_cache_factory = MagicMock(return_value=mock_cache)

        _inject_fake_module(
            "backend.api.services.met_norway_locationforecast_sync_adapter",
            METNorwayLocationForecastSyncAdapter=mock_adapter_cls,
        )

        try:
            with patch(
                "backend.infrastructure.cache.climate_cache.create_climate_cache",
                mock_cache_factory,
            ):
                from backend.infrastructure.cache.climate_tasks import (
                    prefetch_met_norway_nordic_cities,
                )
                result = prefetch_met_norway_nordic_cities()
                assert result["status"] == "success"
                assert "total_cities" in result
        finally:
            sys.modules.pop(
                "backend.api.services.met_norway_locationforecast_sync_adapter", None
            )
