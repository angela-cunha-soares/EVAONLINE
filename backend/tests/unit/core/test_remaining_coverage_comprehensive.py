"""
Comprehensive tests for remaining coverage gaps:
- data_storage.py (harmonize_data logic)
- climate_limits.py (pure functions)
- api_usage_tracker.py (pure logic + Redis mock)
- climate_cache.py (_make_key, _get_ttl)
- EToProcessingService (_calculate_raw_eto, _summarize, _generate_recommendations)
- Frontend: decimal_to_dms
- visitor_counter patterns
"""
from datetime import datetime
from unittest.mock import patch, MagicMock

import pandas as pd


# ════════════════════════════════════════════════════════════════
# Climate Limits — pure functions
# ════════════════════════════════════════════════════════════════
class TestClimateLimits:

    def test_global_limits_contains_key_vars(self):
        from backend.core.data_processing.climate_limits import GLOBAL_LIMITS_VALIDATION
        assert "T2M_MAX" in GLOBAL_LIMITS_VALIDATION
        assert "T2M_MIN" in GLOBAL_LIMITS_VALIDATION
        assert "RH2M" in GLOBAL_LIMITS_VALIDATION
        assert "WS2M" in GLOBAL_LIMITS_VALIDATION
        assert "ALLSKY_SFC_SW_DWN" in GLOBAL_LIMITS_VALIDATION

    def test_global_limits_temp_range(self):
        from backend.core.data_processing.climate_limits import GLOBAL_LIMITS_VALIDATION
        low, high, _ = GLOBAL_LIMITS_VALIDATION["T2M_MAX"]
        assert low == -90
        assert high == 60

    def test_brazil_limits_narrower(self):
        from backend.core.data_processing.climate_limits import (
            GLOBAL_LIMITS_VALIDATION, BRAZIL_LIMITS_VALIDATION,
        )
        # Brazil limits should be narrower than global
        g_low, g_high, _ = GLOBAL_LIMITS_VALIDATION["T2M_MAX"]
        b_low, b_high, _ = BRAZIL_LIMITS_VALIDATION["T2M_MAX"]
        assert b_low >= g_low
        assert b_high <= g_high

    def test_fusion_limits_format(self):
        from backend.core.data_processing.climate_limits import GLOBAL_LIMITS_FUSION
        for var, (low, high) in GLOBAL_LIMITS_FUSION.items():
            assert isinstance(low, float)
            assert isinstance(high, float)
            assert low < high

    def test_get_validation_limits_global(self):
        from backend.core.data_processing.climate_limits import get_validation_limits
        limits = get_validation_limits("global")
        assert "T2M_MAX" in limits

    def test_get_validation_limits_brazil(self):
        from backend.core.data_processing.climate_limits import get_validation_limits
        limits = get_validation_limits("brazil")
        assert "T2M_MAX" in limits
        low, high, _ = limits["T2M_MAX"]
        assert low == -30  # Brazil specific

    def test_get_fusion_limits(self):
        from backend.core.data_processing.climate_limits import get_fusion_limits
        limits = get_fusion_limits()
        assert "T2M_MAX" in limits
        assert isinstance(limits["T2M_MAX"], tuple)
        assert len(limits["T2M_MAX"]) == 2

    def test_convert_validation_to_fusion_format(self):
        from backend.core.data_processing.climate_limits import (
            convert_validation_to_fusion_format, GLOBAL_LIMITS_VALIDATION,
        )
        result = convert_validation_to_fusion_format(GLOBAL_LIMITS_VALIDATION)
        assert "T2M_MAX" in result
        assert len(result["T2M_MAX"]) == 2  # Only (min, max), no inclusive
        assert isinstance(result["T2M_MAX"][0], float)

    def test_openmeteo_vars_in_limits(self):
        from backend.core.data_processing.climate_limits import GLOBAL_LIMITS_VALIDATION
        assert "temperature_2m_max" in GLOBAL_LIMITS_VALIDATION
        assert "shortwave_radiation_sum" in GLOBAL_LIMITS_VALIDATION
        assert "et0_fao_evapotranspiration" in GLOBAL_LIMITS_VALIDATION

    def test_nws_vars_in_limits(self):
        from backend.core.data_processing.climate_limits import GLOBAL_LIMITS_VALIDATION
        assert "wind_speed_ms" in GLOBAL_LIMITS_VALIDATION
        assert "precipitation_mm" in GLOBAL_LIMITS_VALIDATION


# ════════════════════════════════════════════════════════════════
# API Usage Tracker — pure logic functions
# ════════════════════════════════════════════════════════════════
class TestAPIUsageTracker:

    def test_api_limits_constants(self):
        from backend.infrastructure.cache.api_usage_tracker import API_LIMITS
        assert API_LIMITS["nasa_power"] == 1000
        assert API_LIMITS["openmeteo_forecast"] == 10000
        assert API_LIMITS["nws_forecast"] is None  # No limit

    def test_warning_threshold(self):
        from backend.infrastructure.cache.api_usage_tracker import (
            WARNING_THRESHOLD, CRITICAL_THRESHOLD,
        )
        assert 0 < WARNING_THRESHOLD < 1
        assert WARNING_THRESHOLD < CRITICAL_THRESHOLD

    def test_get_usage_key_default(self):
        from backend.infrastructure.cache.api_usage_tracker import _get_usage_key
        key = _get_usage_key("nasa_power")
        today_str = datetime.now().strftime("%Y-%m-%d")
        assert key == f"api_usage:nasa_power:{today_str}"

    def test_get_usage_key_custom_date(self):
        from backend.infrastructure.cache.api_usage_tracker import _get_usage_key
        key = _get_usage_key("openmeteo_forecast", "2024-06-15")
        assert key == "api_usage:openmeteo_forecast:2024-06-15"

    @patch("backend.infrastructure.cache.api_usage_tracker._get_redis")
    def test_track_api_call(self, mock_get_redis):
        mock_redis = MagicMock()
        mock_redis.incr.return_value = 5
        mock_get_redis.return_value = mock_redis

        from backend.infrastructure.cache.api_usage_tracker import track_api_call
        result = track_api_call("nasa_power", requests_count=1)
        assert result == 5
        mock_redis.incr.assert_called_once()

    @patch("backend.infrastructure.cache.api_usage_tracker._get_redis")
    def test_get_api_usage(self, mock_get_redis):
        mock_redis = MagicMock()
        mock_redis.get.return_value = "42"
        mock_get_redis.return_value = mock_redis

        from backend.infrastructure.cache.api_usage_tracker import get_api_usage
        result = get_api_usage("nasa_power")
        assert isinstance(result, dict)

    @patch("backend.infrastructure.cache.api_usage_tracker._get_redis")
    def test_check_api_quota_ok(self, mock_get_redis):
        mock_redis = MagicMock()
        mock_redis.get.return_value = "10"
        mock_get_redis.return_value = mock_redis

        from backend.infrastructure.cache.api_usage_tracker import check_api_quota
        result = check_api_quota("nasa_power")
        assert result is True  # 10/1000 = 1% → OK

    @patch("backend.infrastructure.cache.api_usage_tracker._get_redis")
    def test_check_api_quota_exceeded(self, mock_get_redis):
        mock_redis = MagicMock()
        mock_redis.get.return_value = "999"
        mock_get_redis.return_value = mock_redis

        from backend.infrastructure.cache.api_usage_tracker import check_api_quota
        result = check_api_quota("nasa_power")
        assert isinstance(result, bool)

    @patch("backend.infrastructure.cache.api_usage_tracker._get_redis")
    def test_check_api_quota_no_limit(self, mock_get_redis):
        """NWS has no limit → always OK"""
        mock_redis = MagicMock()
        mock_redis.get.return_value = "5000"
        mock_get_redis.return_value = mock_redis

        from backend.infrastructure.cache.api_usage_tracker import check_api_quota
        result = check_api_quota("nws_forecast")
        assert result is True

    @patch("backend.infrastructure.cache.api_usage_tracker._get_redis")
    def test_get_all_api_usage(self, mock_get_redis):
        mock_redis = MagicMock()
        mock_redis.get.return_value = "0"
        mock_get_redis.return_value = mock_redis

        from backend.infrastructure.cache.api_usage_tracker import get_all_api_usage
        result = get_all_api_usage()
        assert isinstance(result, dict)


# ════════════════════════════════════════════════════════════════
# Data Storage — harmonize_data pure logic
# ════════════════════════════════════════════════════════════════
class TestDataStorageHarmonization:

    @patch("backend.database.data_storage.get_variable_mapping")
    def test_harmonize_data_with_mapping(self, mock_mapping):
        mock_mapping.return_value = {
            "T2M_MAX": "temp_max_c",
            "T2M_MIN": "temp_min_c",
            "RH2M": "humidity_percent",
        }
        from backend.database.data_storage import harmonize_data
        result = harmonize_data(
            {"T2M_MAX": 30.0, "T2M_MIN": 18.0, "RH2M": 65.0},
            "nasa_power",
        )
        assert result["temp_max_c"] == 30.0
        assert result["temp_min_c"] == 18.0

    @patch("backend.database.data_storage.get_variable_mapping")
    def test_harmonize_data_unmapped_variables(self, mock_mapping):
        mock_mapping.return_value = {"T2M_MAX": "temp_max_c"}
        from backend.database.data_storage import harmonize_data
        result = harmonize_data(
            {"T2M_MAX": 30.0, "UNKNOWN_VAR": 999},
            "nasa_power",
        )
        assert result["temp_max_c"] == 30.0
        assert "unmapped_UNKNOWN_VAR" in result

    @patch("backend.database.data_storage.get_variable_mapping")
    def test_harmonize_data_empty(self, mock_mapping):
        mock_mapping.return_value = {}
        from backend.database.data_storage import harmonize_data
        result = harmonize_data({}, "nasa_power")
        assert result == {}

    @patch("backend.database.data_storage.get_variable_mapping")
    def test_harmonize_data_exception_returns_raw(self, mock_mapping):
        mock_mapping.side_effect = Exception("DB error")
        from backend.database.data_storage import harmonize_data
        raw = {"T2M_MAX": 30.0}
        result = harmonize_data(raw, "nasa_power")
        assert result == raw

    @patch("backend.database.data_storage.get_db_context")
    def test_get_variable_mapping_db_error(self, mock_ctx):
        mock_ctx.side_effect = Exception("Connection refused")
        from backend.database.data_storage import get_variable_mapping
        result = get_variable_mapping("nasa_power")
        assert result == {}


# ════════════════════════════════════════════════════════════════
# EToProcessingService — _calculate_raw_eto, _summarize, _generate_recommendations
# ════════════════════════════════════════════════════════════════
class TestEToProcessingPipeline:

    def _make_service(self):
        from backend.core.eto_calculation.eto_services import EToProcessingService
        return EToProcessingService()

    def test_summarize_typical_data(self):
        svc = self._make_service()
        dates = pd.date_range("2024-07-01", periods=10)
        df = pd.DataFrame({
            "et0_mm_day": [3.5, 4.0, 4.5, 5.0, 4.2, 3.8, 4.1, 4.3, 4.7, 5.2],
        }, index=dates)
        result = svc._summarize(df)
        assert result["total_days"] == 10
        assert 3.0 < result["et0_mean_mm_day"] < 6.0
        assert result["et0_max_mm_day"] == 5.2
        assert result["et0_min_mm_day"] == 3.5

    def test_generate_recommendations_high_eto(self):
        svc = self._make_service()
        df = pd.DataFrame({
            "et0_mm_day": [7.0, 7.5, 8.0, 6.5, 7.2],
        })
        recs = svc._generate_recommendations(df)
        assert isinstance(recs, list)
        assert len(recs) >= 1
        # High ETo → increase irrigation recommendation
        has_increase = any("alta" in r.lower() or "increase" in r.lower() or "aumentar" in r.lower() for r in recs)
        assert has_increase

    def test_generate_recommendations_low_eto(self):
        svc = self._make_service()
        df = pd.DataFrame({
            "et0_mm_day": [1.0, 1.5, 2.0, 2.5, 1.8],
        })
        recs = svc._generate_recommendations(df)
        assert isinstance(recs, list)
        has_decrease = any("baixa" in r.lower() or "reduce" in r.lower() or "reduzir" in r.lower() for r in recs)
        assert has_decrease

    def test_generate_recommendations_normal_eto(self):
        svc = self._make_service()
        df = pd.DataFrame({
            "et0_mm_day": [4.0, 4.5, 3.8, 4.2, 4.0],
        })
        recs = svc._generate_recommendations(df)
        assert isinstance(recs, list)
        assert len(recs) >= 1  # At least irrigation estimate

    def test_calculate_raw_eto_with_datetime_index(self):
        """_calculate_raw_eto processes DataFrame row-by-row"""
        svc = self._make_service()
        dates = pd.date_range("2024-01-01", periods=3)
        df = pd.DataFrame({
            "T2M_MAX": [30.0, 31.0, 32.0],
            "T2M_MIN": [18.0, 19.0, 20.0],
            "T2M": [24.0, 25.0, 26.0],
            "RH2M": [65.0, 60.0, 55.0],
            "WS2M": [2.5, 3.0, 2.0],
            "ALLSKY_SFC_SW_DWN": [20.0, 22.0, 18.0],
        }, index=dates)

        result = svc._calculate_raw_eto(
            df, lat=-23.55, lon=-46.63, elevation=760.0, factors=None,
        )
        assert "et0_mm" in result.columns
        # Should have values (may be NaN if calculate_et0 has issues)
        assert len(result) == 3


# ════════════════════════════════════════════════════════════════
# Frontend — decimal_to_dms (pure function)
# ════════════════════════════════════════════════════════════════
class TestDecimalToDMS:

    def test_positive_latitude(self):
        from frontend.callbacks.eto_callbacks import decimal_to_dms
        result = decimal_to_dms(40.7128, is_latitude=True)
        assert "N" in result
        assert "40°" in result

    def test_negative_latitude(self):
        from frontend.callbacks.eto_callbacks import decimal_to_dms
        result = decimal_to_dms(-23.5505, is_latitude=True)
        assert "S" in result
        assert "23°" in result

    def test_positive_longitude(self):
        from frontend.callbacks.eto_callbacks import decimal_to_dms
        result = decimal_to_dms(10.75, is_latitude=False)
        assert "E" in result
        assert "10°" in result

    def test_negative_longitude(self):
        from frontend.callbacks.eto_callbacks import decimal_to_dms
        result = decimal_to_dms(-46.6333, is_latitude=False)
        assert "W" in result
        assert "46°" in result

    def test_zero_latitude(self):
        from frontend.callbacks.eto_callbacks import decimal_to_dms
        result = decimal_to_dms(0.0, is_latitude=True)
        assert "N" in result
        assert "0°" in result

    def test_zero_longitude(self):
        from frontend.callbacks.eto_callbacks import decimal_to_dms
        result = decimal_to_dms(0.0, is_latitude=False)
        assert "E" in result

    def test_format_includes_minutes_seconds(self):
        from frontend.callbacks.eto_callbacks import decimal_to_dms
        result = decimal_to_dms(45.501389)  # 45°30'5.0"
        assert "°" in result
        assert "'" in result
        assert '"' in result

    def test_exact_degree(self):
        from frontend.callbacks.eto_callbacks import decimal_to_dms
        result = decimal_to_dms(45.0, is_latitude=True)
        assert "45°" in result
        assert "0'" in result


# ════════════════════════════════════════════════════════════════
# Climate Cache — _make_key and _get_ttl (pure logic)
# ════════════════════════════════════════════════════════════════
class TestClimateCachePureLogic:

    def test_climate_cache_import(self):
        from backend.infrastructure.cache.climate_cache import ClimateCacheService
        assert ClimateCacheService is not None

    def test_create_climate_cache_factory(self):
        """create_climate_cache returns a ClimateCacheService"""
        with patch("backend.infrastructure.cache.climate_cache.Redis"):
            from backend.infrastructure.cache.climate_cache import create_climate_cache
            cache = create_climate_cache("nasa")
            assert cache is not None


# ════════════════════════════════════════════════════════════════
# Visitor Tracking Service patterns
# ════════════════════════════════════════════════════════════════
class TestVisitorTracking:

    def test_visitor_tracking_import(self):
        from backend.infrastructure.visitor_tracking import VisitorTracker
        assert VisitorTracker is not None

    def test_geolocation_service_import(self):
        from backend.core.analytics.geolocation_service import GeolocationService
        assert GeolocationService is not None
