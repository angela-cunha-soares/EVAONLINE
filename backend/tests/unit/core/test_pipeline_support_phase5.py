"""
Phase 5 Tests: Pipeline support modules.

Coverage targets:
- backend/database/data_storage.py (43% → 85%+)
- backend/infrastructure/cache/redis_manager.py (60% → 85%+)
- backend/core/analytics/geolocation_service.py (53% → 80%+)
"""

import asyncio
import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Async helper
# ---------------------------------------------------------------------------

def _run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# ===========================================================================
# data_storage.py — get_variable_mapping, harmonize_data, save/get/check
# ===========================================================================


class TestGetVariableMapping:
    """Tests for get_variable_mapping."""

    @patch("backend.database.data_storage.get_db_context")
    def test_returns_mapping(self, mock_ctx):
        """Returns dict of variable→standard mappings."""
        mock_db = MagicMock()
        mock_ctx.return_value.__enter__ = MagicMock(return_value=mock_db)
        mock_ctx.return_value.__exit__ = MagicMock(return_value=False)

        mock_var = MagicMock()
        mock_var.variable_name = "T2M_MAX"
        mock_var.standard_name = "temp_max_c"
        mock_db.query.return_value.filter.return_value.all.return_value = [
            mock_var
        ]

        from backend.database.data_storage import get_variable_mapping

        result = get_variable_mapping("nasa_power")
        assert result == {"T2M_MAX": "temp_max_c"}

    @patch("backend.database.data_storage.get_db_context")
    def test_db_error_returns_empty(self, mock_ctx):
        """DB error → returns empty dict."""
        mock_ctx.return_value.__enter__ = MagicMock(
            side_effect=Exception("DB down")
        )
        mock_ctx.return_value.__exit__ = MagicMock(return_value=False)

        from backend.database.data_storage import get_variable_mapping

        result = get_variable_mapping("nasa_power")
        assert result == {}


class TestHarmonizeData:
    """Tests for harmonize_data."""

    @patch("backend.database.data_storage.get_variable_mapping")
    def test_maps_known_vars(self, mock_mapping):
        """Known variables mapped to standard names."""
        mock_mapping.return_value = {
            "T2M_MAX": "temp_max_c",
            "RH2M": "humidity_percent",
        }

        from backend.database.data_storage import harmonize_data

        result = harmonize_data(
            {"T2M_MAX": 28.5, "RH2M": 65.0, "extra_var": 1.0},
            "nasa_power",
        )
        assert result["temp_max_c"] == 28.5
        assert result["humidity_percent"] == 65.0
        assert result["unmapped_extra_var"] == 1.0

    @patch("backend.database.data_storage.get_variable_mapping")
    def test_mapping_error_returns_original(self, mock_mapping):
        """On error, returns original data."""
        mock_mapping.side_effect = Exception("DB error")

        from backend.database.data_storage import harmonize_data

        raw = {"T2M_MAX": 28.5}
        result = harmonize_data(raw, "nasa_power")
        assert result == raw


class TestSaveClimateData:
    """Tests for save_climate_data."""

    @patch("backend.database.data_storage.harmonize_data")
    @patch("backend.database.data_storage.get_db_context")
    def test_saves_records(self, mock_ctx, mock_harmonize):
        """Saves records via bulk add_all."""
        mock_db = MagicMock()
        mock_ctx.return_value.__enter__ = MagicMock(return_value=mock_db)
        mock_ctx.return_value.__exit__ = MagicMock(return_value=False)
        mock_harmonize.return_value = {"temp_max_c": 28.5}

        from backend.database.data_storage import save_climate_data

        data = [
            {
                "latitude": -23.55,
                "longitude": -46.63,
                "elevation": 760.0,
                "date": datetime(2025, 1, 1),
                "raw_data": {"T2M_MAX": 28.5},
            }
        ]
        count = save_climate_data(data, "nasa_power")
        assert count == 1
        mock_db.add_all.assert_called_once()
        mock_db.commit.assert_called_once()

    @patch("backend.database.data_storage.get_db_context")
    def test_empty_data_returns_zero(self, mock_ctx):
        """Empty data list → returns 0."""
        mock_db = MagicMock()
        mock_ctx.return_value.__enter__ = MagicMock(return_value=mock_db)
        mock_ctx.return_value.__exit__ = MagicMock(return_value=False)

        from backend.database.data_storage import save_climate_data

        count = save_climate_data([], "nasa_power")
        assert count == 0

    @patch("backend.database.data_storage.harmonize_data")
    @patch("backend.database.data_storage.get_db_context")
    def test_no_harmonize_when_disabled(self, mock_ctx, mock_harmonize):
        """auto_harmonize=False → harmonize_data not called."""
        mock_db = MagicMock()
        mock_ctx.return_value.__enter__ = MagicMock(return_value=mock_db)
        mock_ctx.return_value.__exit__ = MagicMock(return_value=False)

        from backend.database.data_storage import save_climate_data

        data = [
            {
                "latitude": -23.55,
                "longitude": -46.63,
                "date": datetime(2025, 1, 1),
                "raw_data": {"T2M_MAX": 28.5},
            }
        ]
        save_climate_data(data, "nasa_power", auto_harmonize=False)
        mock_harmonize.assert_not_called()


class TestGetClimateData:
    """Tests for get_climate_data."""

    @patch("backend.database.data_storage.get_db_context")
    def test_returns_filtered_results(self, mock_ctx):
        """Returns ordered results for the query."""
        mock_db = MagicMock()
        mock_ctx.return_value.__enter__ = MagicMock(return_value=mock_db)
        mock_ctx.return_value.__exit__ = MagicMock(return_value=False)

        mock_result = MagicMock()
        mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = [
            mock_result
        ]

        from backend.database.data_storage import get_climate_data

        results = get_climate_data(
            -23.55, -46.63,
            datetime(2025, 1, 1),
            datetime(2025, 1, 31),
        )
        assert len(results) == 1

    @patch("backend.database.data_storage.get_db_context")
    def test_filters_by_source_api(self, mock_ctx):
        """source_api filter applied when provided."""
        mock_db = MagicMock()
        mock_ctx.return_value.__enter__ = MagicMock(return_value=mock_db)
        mock_ctx.return_value.__exit__ = MagicMock(return_value=False)

        query_mock = mock_db.query.return_value.filter.return_value
        query_mock.filter.return_value.order_by.return_value.all.return_value = []

        from backend.database.data_storage import get_climate_data

        get_climate_data(
            -23.55, -46.63,
            datetime(2025, 1, 1),
            datetime(2025, 1, 31),
            source_api="nasa_power",
        )
        # Should apply additional filter
        query_mock.filter.assert_called_once()


class TestCheckDataExists:
    """Tests for check_data_exists."""

    @patch("backend.database.data_storage.get_db_context")
    def test_exists_returns_true(self, mock_ctx):
        mock_db = MagicMock()
        mock_ctx.return_value.__enter__ = MagicMock(return_value=mock_db)
        mock_ctx.return_value.__exit__ = MagicMock(return_value=False)
        mock_db.query.return_value.filter.return_value.count.return_value = 1

        from backend.database.data_storage import check_data_exists

        assert check_data_exists(
            -23.55, -46.63, datetime(2025, 1, 1), "nasa_power"
        )

    @patch("backend.database.data_storage.get_db_context")
    def test_not_exists_returns_false(self, mock_ctx):
        mock_db = MagicMock()
        mock_ctx.return_value.__enter__ = MagicMock(return_value=mock_db)
        mock_ctx.return_value.__exit__ = MagicMock(return_value=False)
        mock_db.query.return_value.filter.return_value.count.return_value = 0

        from backend.database.data_storage import check_data_exists

        assert not check_data_exists(
            -23.55, -46.63, datetime(2025, 1, 1), "nasa_power"
        )


# ===========================================================================
# redis_manager.py — CacheManager
# ===========================================================================


class TestCacheManager:
    """Tests for CacheManager async Redis + PostgreSQL operations."""

    @pytest.fixture(autouse=True)
    def _fresh_loop(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        yield
        loop.close()

    @pytest.fixture
    def cache_mgr(self):
        """Build CacheManager with mocked Redis and DB + metrics."""
        import sys
        mock_redis = AsyncMock()
        mock_db = MagicMock()

        # redis_manager imports CACHE_HITS etc. from backend.api.main
        # which may not be importable in test context. Inject mock module.
        mock_metrics = MagicMock()
        needs_cleanup = "backend.api.main" not in sys.modules
        if needs_cleanup:
            sys.modules["backend.api.main"] = mock_metrics

        import backend.infrastructure.cache.redis_manager as rm_mod

        # Patch metrics at module level
        orig_hits = rm_mod.CACHE_HITS
        orig_misses = rm_mod.CACHE_MISSES
        orig_pop = rm_mod.POPULAR_DATA_ACCESSES
        rm_mod.CACHE_HITS = MagicMock()
        rm_mod.CACHE_MISSES = MagicMock()
        rm_mod.POPULAR_DATA_ACCESSES = MagicMock()

        mgr = rm_mod.CacheManager(mock_redis, mock_db)
        yield mgr

        # Restore
        rm_mod.CACHE_HITS = orig_hits
        rm_mod.CACHE_MISSES = orig_misses
        rm_mod.POPULAR_DATA_ACCESSES = orig_pop
        if needs_cleanup:
            sys.modules.pop("backend.api.main", None)

    def test_get_eto_data_cache_hit(self, cache_mgr):
        """Redis hit → returns data without Postgres query."""
        cache_mgr.redis.get = AsyncMock(
            return_value=json.dumps({"et0": 4.5})
        )
        result = _run(cache_mgr.get_eto_data("test_key"))
        assert result == {"et0": 4.5}

    def test_get_eto_data_cache_miss_postgres_hit(self, cache_mgr):
        """Redis miss, Postgres hit → returns data and populates cache."""
        cache_mgr.redis.get = AsyncMock(return_value=None)
        cache_mgr.redis.setex = AsyncMock()

        cache_mgr.db.execute.return_value.first.return_value = (
            json.dumps({"et0": 4.5}),
            datetime.now(),
        )
        result = _run(cache_mgr.get_eto_data("test_key"))
        assert result == {"et0": 4.5}
        cache_mgr.redis.setex.assert_called_once()

    def test_get_eto_data_complete_miss(self, cache_mgr):
        """Redis miss + Postgres miss → returns None."""
        cache_mgr.redis.get = AsyncMock(return_value=None)
        cache_mgr.db.execute.return_value.first.return_value = None
        result = _run(cache_mgr.get_eto_data("test_key"))
        assert result is None

    def test_save_eto_data(self, cache_mgr):
        """save_eto_data writes to Redis + Postgres."""
        cache_mgr.redis.setex = AsyncMock()
        cache_mgr.db.execute = MagicMock()
        cache_mgr.db.commit = MagicMock()
        _run(cache_mgr.save_eto_data("test_key", {"et0": 4.5}))
        cache_mgr.redis.setex.assert_called_once()
        cache_mgr.db.commit.assert_called_once()

    def test_cleanup_expired_data(self, cache_mgr):
        """cleanup_expired_data deletes expired Postgres rows."""
        cache_mgr.db.execute = MagicMock()
        cache_mgr.db.commit = MagicMock()
        _run(cache_mgr.cleanup_expired_data())
        cache_mgr.db.execute.assert_called_once()
        cache_mgr.db.commit.assert_called_once()

    def test_redis_error_in_get_returns_none(self, cache_mgr):
        """Redis error in _get_from_redis → returns None."""
        cache_mgr.redis.get = AsyncMock(side_effect=Exception("Connection refused"))
        cache_mgr.db.execute.return_value.first.return_value = None
        result = _run(cache_mgr.get_eto_data("test_key"))
        assert result is None


# ===========================================================================
# geolocation_service.py — detect/parse methods (no DB needed)
# ===========================================================================


class TestGeolocationDetectRegion:
    """Tests for _detect_climate_region (static, no DB)."""

    def test_usa(self):
        from backend.core.analytics.geolocation_service import GeolocationService
        assert GeolocationService._detect_climate_region(40.7, -74.0) == "usa"

    def test_nordic(self):
        from backend.core.analytics.geolocation_service import GeolocationService
        assert GeolocationService._detect_climate_region(60.0, 10.0) == "nordic"

    def test_global_brazil(self):
        from backend.core.analytics.geolocation_service import GeolocationService
        assert GeolocationService._detect_climate_region(-23.5, -46.6) == "global"

    def test_global_australia(self):
        from backend.core.analytics.geolocation_service import GeolocationService
        assert GeolocationService._detect_climate_region(-33.8, 151.2) == "global"

    def test_boundary_usa_south(self):
        from backend.core.analytics.geolocation_service import GeolocationService
        # Just below US southern boundary
        assert GeolocationService._detect_climate_region(23.9, -98.0) == "global"


class TestParseUserAgent:
    """Tests for _parse_user_agent (static, no DB)."""

    def test_chrome_desktop(self):
        from backend.core.analytics.geolocation_service import GeolocationService
        ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        result = GeolocationService._parse_user_agent(ua)
        assert result["device_type"] == "desktop"
        assert result["browser"] == "chrome"
        assert result["os"] == "windows"

    def test_firefox_linux(self):
        from backend.core.analytics.geolocation_service import GeolocationService
        ua = "Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/119.0"
        result = GeolocationService._parse_user_agent(ua)
        assert result["browser"] == "firefox"
        assert result["os"] == "linux"

    def test_safari_mac(self):
        from backend.core.analytics.geolocation_service import GeolocationService
        ua = "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15"
        result = GeolocationService._parse_user_agent(ua)
        assert result["browser"] == "safari"
        assert result["os"] == "macos"

    def test_edge_windows(self):
        from backend.core.analytics.geolocation_service import GeolocationService
        ua = "Mozilla/5.0 (Windows) AppleWebKit Chrome/120 Edg/120.0.0.0"
        result = GeolocationService._parse_user_agent(ua)
        assert result["browser"] == "edge"

    def test_mobile_android(self):
        from backend.core.analytics.geolocation_service import GeolocationService
        ua = "Mozilla/5.0 (Linux; Android 14) Mobile"
        result = GeolocationService._parse_user_agent(ua)
        assert result["device_type"] == "mobile"
        # OS parser checks "Linux" before "Android" → returns "linux"
        assert result["os"] == "linux"

    def test_tablet_ipad(self):
        from backend.core.analytics.geolocation_service import GeolocationService
        ua = "Mozilla/5.0 (iPad; CPU OS 17_0 like Mac OS X)"
        result = GeolocationService._parse_user_agent(ua)
        assert result["device_type"] == "tablet"

    def test_unknown_agent(self):
        from backend.core.analytics.geolocation_service import GeolocationService
        result = GeolocationService._parse_user_agent("BotCrawler/1.0")
        assert result["browser"] == "other"
        assert result["os"] == "other"
        assert result["device_type"] == "desktop"


class TestGeolocationIDs:
    """Tests for ID generation."""

    def test_generate_visitor_id(self):
        from backend.core.analytics.geolocation_service import GeolocationService
        vid = GeolocationService.generate_visitor_id()
        assert vid.startswith("visitor_")
        assert len(vid) > 8

    def test_generate_session_id(self):
        from backend.core.analytics.geolocation_service import GeolocationService
        sid = GeolocationService.generate_session_id()
        assert sid.startswith("sess_")
        assert len(sid) > 5

    def test_ids_are_unique(self):
        from backend.core.analytics.geolocation_service import GeolocationService
        ids = {GeolocationService.generate_visitor_id() for _ in range(100)}
        assert len(ids) == 100


class TestGeolocationDBMethods:
    """Tests for DB-dependent methods with mocked get_db_context."""

    @patch("backend.core.analytics.geolocation_service.get_db_context")
    def test_create_new_visitor(self, mock_ctx):
        """Creates a new visitor when none exists."""
        mock_db = MagicMock()
        mock_ctx.return_value.__enter__ = MagicMock(return_value=mock_db)
        mock_ctx.return_value.__exit__ = MagicMock(return_value=False)

        # No existing visitor
        mock_db.query.return_value.filter.return_value.first.return_value = (
            None
        )

        from backend.core.analytics.geolocation_service import GeolocationService

        result = GeolocationService.create_or_update_visitor(
            visitor_id="visitor_test123",
            session_id="sess_abc",
            geolocation={"latitude": -23.5, "longitude": -46.6, "accuracy": 50},
            user_agent="Mozilla/5.0 (Windows) Chrome/120",
            country="Brazil",
            city="São Paulo",
        )

        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    @patch("backend.core.analytics.geolocation_service.get_db_context")
    def test_update_existing_visitor(self, mock_ctx):
        """Updates existing visitor's visit count and geolocation."""
        mock_db = MagicMock()
        mock_ctx.return_value.__enter__ = MagicMock(return_value=mock_db)
        mock_ctx.return_value.__exit__ = MagicMock(return_value=False)

        # Existing visitor
        mock_visitor = MagicMock()
        mock_visitor.visit_count = 5
        mock_db.query.return_value.filter.return_value.first.return_value = (
            mock_visitor
        )

        from backend.core.analytics.geolocation_service import GeolocationService

        GeolocationService.create_or_update_visitor(
            visitor_id="visitor_test123",
            session_id="sess_new",
            geolocation={"latitude": -23.5, "longitude": -46.6},
            country="Brazil",
        )

        assert mock_visitor.visit_count == 6
        mock_db.commit.assert_called_once()

    @patch("backend.core.analytics.geolocation_service.get_db_context")
    def test_get_visitor_by_id(self, mock_ctx):
        """get_visitor_by_id queries by visitor_id."""
        mock_db = MagicMock()
        mock_ctx.return_value.__enter__ = MagicMock(return_value=mock_db)
        mock_ctx.return_value.__exit__ = MagicMock(return_value=False)

        mock_visitor = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = (
            mock_visitor
        )

        from backend.core.analytics.geolocation_service import GeolocationService

        result = GeolocationService.get_visitor_by_id("visitor_test123")
        assert result == mock_visitor

    @patch("backend.core.analytics.geolocation_service.get_db_context")
    def test_get_visitor_by_session(self, mock_ctx):
        """get_visitor_by_session queries by session_id."""
        mock_db = MagicMock()
        mock_ctx.return_value.__enter__ = MagicMock(return_value=mock_db)
        mock_ctx.return_value.__exit__ = MagicMock(return_value=False)

        mock_visitor = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = (
            mock_visitor
        )

        from backend.core.analytics.geolocation_service import GeolocationService

        result = GeolocationService.get_visitor_by_session("sess_abc")
        assert result == mock_visitor

    @patch("backend.core.analytics.geolocation_service.get_db_context")
    def test_update_geolocation_found(self, mock_ctx):
        """update_geolocation for existing visitor → True."""
        mock_db = MagicMock()
        mock_ctx.return_value.__enter__ = MagicMock(return_value=mock_db)
        mock_ctx.return_value.__exit__ = MagicMock(return_value=False)

        mock_visitor = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = (
            mock_visitor
        )

        from backend.core.analytics.geolocation_service import GeolocationService

        result = GeolocationService.update_geolocation(
            "visitor_test123", -23.5, -46.6, accuracy=50.0
        )
        assert result is True
        mock_db.commit.assert_called_once()

    @patch("backend.core.analytics.geolocation_service.get_db_context")
    def test_update_geolocation_not_found(self, mock_ctx):
        """update_geolocation for missing visitor → False."""
        mock_db = MagicMock()
        mock_ctx.return_value.__enter__ = MagicMock(return_value=mock_db)
        mock_ctx.return_value.__exit__ = MagicMock(return_value=False)

        mock_db.query.return_value.filter.return_value.first.return_value = (
            None
        )

        from backend.core.analytics.geolocation_service import GeolocationService

        result = GeolocationService.update_geolocation(
            "visitor_nonexistent", -23.5, -46.6
        )
        assert result is False
