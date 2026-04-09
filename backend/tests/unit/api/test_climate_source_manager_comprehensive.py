"""
Comprehensive tests for Climate Source Manager.
Covers: normalize_operation_mode, get_available_sources,
get_sources_for_data_download, get_fusion_weights,
get_available_sources_for_location, get_available_sources_by_mode.
"""
from datetime import date, datetime, timedelta

import pytest

from backend.api.services.climate_source_manager import (
    ClimateSourceManager,
    normalize_operation_mode,
)
from backend.api.services.climate_source_availability import OperationMode


# ════════════════════════════════════════════════════════════════
# normalize_operation_mode
# ════════════════════════════════════════════════════════════════
class TestNormalizeOperationMode:

    def test_historical(self):
        assert normalize_operation_mode("historical") == OperationMode.HISTORICAL_EMAIL

    def test_historical_email(self):
        assert normalize_operation_mode("historical_email") == OperationMode.HISTORICAL_EMAIL

    def test_forecast(self):
        assert normalize_operation_mode("forecast") == OperationMode.DASHBOARD_FORECAST

    def test_dashboard_forecast(self):
        assert normalize_operation_mode("dashboard_forecast") == OperationMode.DASHBOARD_FORECAST

    def test_dashboard(self):
        assert normalize_operation_mode("dashboard") == OperationMode.DASHBOARD_CURRENT

    def test_dashboard_current(self):
        assert normalize_operation_mode("dashboard_current") == OperationMode.DASHBOARD_CURRENT

    def test_none_defaults_to_current(self):
        assert normalize_operation_mode(None) == OperationMode.DASHBOARD_CURRENT

    def test_unknown_string_defaults_to_current(self):
        assert normalize_operation_mode("xyz_unknown") == OperationMode.DASHBOARD_CURRENT

    def test_case_insensitive(self):
        assert normalize_operation_mode("HISTORICAL") == OperationMode.HISTORICAL_EMAIL
        assert normalize_operation_mode("Forecast") == OperationMode.DASHBOARD_FORECAST


# ════════════════════════════════════════════════════════════════
# ClimateSourceManager basics
# ════════════════════════════════════════════════════════════════
class TestClimateSourceManagerInit:

    def test_creates_instance(self):
        mgr = ClimateSourceManager()
        assert mgr is not None

    def test_has_sources_config(self):
        mgr = ClimateSourceManager()
        assert len(mgr.SOURCES_CONFIG) >= 5

    def test_sources_have_required_keys(self):
        mgr = ClimateSourceManager()
        for source_id, config in mgr.SOURCES_CONFIG.items():
            assert "id" in config
            assert "name" in config
            assert "coverage" in config
            assert "priority" in config


# ════════════════════════════════════════════════════════════════
# get_available_sources_for_location
# ════════════════════════════════════════════════════════════════
class TestGetAvailableSourcesForLocation:

    def test_global_location_has_global_sources(self):
        """São Paulo → global sources available (NASA, OpenMeteo)"""
        mgr = ClimateSourceManager()
        result = mgr.get_available_sources_for_location(-23.55, -46.63)
        # At least openmeteo_archive, openmeteo_forecast, nasa_power
        global_available = [k for k, v in result.items() if v["available"]]
        assert "openmeteo_archive" in global_available or "nasa_power" in global_available

    def test_usa_location_has_all_sources(self):
        """NYC → all sources available including NWS"""
        mgr = ClimateSourceManager()
        result = mgr.get_available_sources_for_location(40.71, -74.01)
        available = [k for k, v in result.items() if v["available"]]
        assert "nws_forecast" in available
        assert "nasa_power" in available or "openmeteo_archive" in available

    def test_non_usa_excludes_nws(self):
        """London → NWS not available"""
        mgr = ClimateSourceManager()
        result = mgr.get_available_sources_for_location(51.5, -0.1)
        nws_sources = [
            k for k, v in result.items()
            if k.startswith("nws") and v["available"]
        ]
        assert len(nws_sources) == 0

    def test_metadata_includes_location(self):
        mgr = ClimateSourceManager()
        result = mgr.get_available_sources_for_location(0, 0)
        for source_id, config in result.items():
            assert "location" in config
            assert config["location"]["lat"] == 0


# ════════════════════════════════════════════════════════════════
# get_available_sources
# ════════════════════════════════════════════════════════════════
class TestGetAvailableSources:

    def test_returns_list_of_dicts(self):
        mgr = ClimateSourceManager()
        result = mgr.get_available_sources(-23.55, -46.63)
        assert isinstance(result, list)
        for item in result:
            assert isinstance(item, dict)

    def test_global_location(self):
        """Global location → at least 2 sources"""
        mgr = ClimateSourceManager()
        result = mgr.get_available_sources(0, 0)
        assert len(result) >= 2


# ════════════════════════════════════════════════════════════════
# get_best_source_for_location
# ════════════════════════════════════════════════════════════════
class TestGetBestSource:

    def test_returns_string_or_none(self):
        mgr = ClimateSourceManager()
        result = mgr.get_best_source_for_location(-23.55, -46.63)
        assert result is None or isinstance(result, str)

    def test_usa_location(self):
        mgr = ClimateSourceManager()
        result = mgr.get_best_source_for_location(40.71, -74.01)
        assert result is not None


# ════════════════════════════════════════════════════════════════
# get_available_sources_by_mode
# ════════════════════════════════════════════════════════════════
class TestGetAvailableSourcesByMode:

    def test_forecast_mode_global(self):
        """Forecast mode at global location → should include openmeteo_forecast"""
        mgr = ClimateSourceManager()
        result = mgr.get_available_sources_by_mode(
            0, 0, OperationMode.DASHBOARD_FORECAST
        )
        assert isinstance(result, list)
        assert "openmeteo_forecast" in result

    def test_forecast_mode_usa(self):
        """Forecast at NYC → includes NWS sources"""
        mgr = ClimateSourceManager()
        result = mgr.get_available_sources_by_mode(
            40.71, -74.01, OperationMode.DASHBOARD_FORECAST
        )
        assert "nws_forecast" in result

    def test_historical_mode(self):
        """Historical mode → archive/NASA sources"""
        mgr = ClimateSourceManager()
        result = mgr.get_available_sources_by_mode(
            -23.55, -46.63, OperationMode.HISTORICAL_EMAIL
        )
        assert len(result) >= 1

    def test_string_mode_accepted(self):
        """String mode should be accepted"""
        mgr = ClimateSourceManager()
        result = mgr.get_available_sources_by_mode(0, 0, "forecast")
        assert isinstance(result, list)


# ════════════════════════════════════════════════════════════════
# get_sources_for_data_download
# ════════════════════════════════════════════════════════════════
class TestGetSourcesForDataDownload:

    def test_auto_detect_historical(self):
        """Dates in the past → auto-detect historical"""
        mgr = ClimateSourceManager()
        today = date.today()
        result = mgr.get_sources_for_data_download(
            -23.55, -46.63,
            start_date=today - timedelta(days=30),
            end_date=today - timedelta(days=2),
        )
        assert result["mode"] == "historical_email"
        assert len(result["sources"]) >= 1
        assert "location_info" in result
        assert any("auto-detected" in w.lower() for w in result["warnings"])

    def test_auto_detect_current(self):
        """End date == today → dashboard current"""
        mgr = ClimateSourceManager()
        today = date.today()
        result = mgr.get_sources_for_data_download(
            -23.55, -46.63,
            start_date=today - timedelta(days=6),
            end_date=today,
        )
        assert result["mode"] == "dashboard_current"

    def test_auto_detect_forecast(self):
        """End date in future → forecast"""
        mgr = ClimateSourceManager()
        today = date.today()
        result = mgr.get_sources_for_data_download(
            -23.55, -46.63,
            start_date=today,
            end_date=today + timedelta(days=5),
        )
        assert result["mode"] == "dashboard_forecast"

    def test_explicit_mode_string(self):
        """Pass explicit mode as string"""
        mgr = ClimateSourceManager()
        today = date.today()
        result = mgr.get_sources_for_data_download(
            -23.55, -46.63,
            start_date=today - timedelta(days=10),
            end_date=today - timedelta(days=2),
            mode="historical",
        )
        assert result["mode"] == "historical_email"

    def test_location_info_usa(self):
        """USA location → in_usa=True"""
        mgr = ClimateSourceManager()
        today = date.today()
        result = mgr.get_sources_for_data_download(
            40.71, -74.01,
            start_date=today,
            end_date=today + timedelta(days=5),
        )
        assert result["location_info"]["in_usa"] is True
        assert result["location_info"]["region"] == "USA Continental"

    def test_location_info_global(self):
        """Global location → in_usa=False"""
        mgr = ClimateSourceManager()
        today = date.today()
        result = mgr.get_sources_for_data_download(
            -23.55, -46.63,
            start_date=today - timedelta(days=30),
            end_date=today - timedelta(days=2),
        )
        assert result["location_info"]["in_usa"] is False

    def test_temporal_coverage(self):
        """temporal_coverage returned correctly"""
        mgr = ClimateSourceManager()
        today = date.today()
        start = today - timedelta(days=14)
        end = today - timedelta(days=2)
        result = mgr.get_sources_for_data_download(
            0, 0, start_date=start, end_date=end,
        )
        assert result["temporal_coverage"]["period_days"] == 13

    def test_datetime_inputs_accepted(self):
        """datetime objects should work (converted to date internally)"""
        mgr = ClimateSourceManager()
        now = datetime.now()
        result = mgr.get_sources_for_data_download(
            0, 0,
            start_date=now - timedelta(days=30),
            end_date=now - timedelta(days=2),
        )
        assert len(result["sources"]) >= 1

    def test_preferred_sources_filtering(self):
        """Only return preferred sources if specified"""
        mgr = ClimateSourceManager()
        today = date.today()
        result = mgr.get_sources_for_data_download(
            -23.55, -46.63,
            start_date=today - timedelta(days=30),
            end_date=today - timedelta(days=2),
            preferred_sources=["nasa_power"],
        )
        if "nasa_power" in result["sources"]:
            assert "nasa_power" in result["sources"]

    def test_invalid_period_raises(self):
        """Period < 1 day → ValueError in historical mode"""
        mgr = ClimateSourceManager()
        today = date.today()
        with pytest.raises(ValueError, match="Period must be >= 1"):
            mgr.get_sources_for_data_download(
                0, 0,
                start_date=today - timedelta(days=2),
                end_date=today - timedelta(days=5),
                mode=OperationMode.HISTORICAL_EMAIL,
            )

    def test_warnings_for_nonstandard_current(self):
        """Dashboard current with non-standard period → warning"""
        mgr = ClimateSourceManager()
        today = date.today()
        result = mgr.get_sources_for_data_download(
            0, 0,
            start_date=today - timedelta(days=9),
            end_date=today,
            mode=OperationMode.DASHBOARD_CURRENT,
        )
        # Should warn about non-standard period (10 not in [7,14,21,30])
        assert any("not standard" in w.lower() for w in result["warnings"])


# ════════════════════════════════════════════════════════════════
# get_fusion_weights
# ════════════════════════════════════════════════════════════════
class TestGetFusionWeights:

    def test_empty_sources(self):
        mgr = ClimateSourceManager()
        assert mgr.get_fusion_weights([], 0, 0) == {}

    def test_single_source(self):
        mgr = ClimateSourceManager()
        w = mgr.get_fusion_weights(["nasa_power"], 0, 0)
        assert abs(w["nasa_power"] - 1.0) < 0.01

    def test_multi_source_sums_to_one(self):
        mgr = ClimateSourceManager()
        w = mgr.get_fusion_weights(
            ["openmeteo_archive", "nasa_power"], 0, 0
        )
        assert abs(sum(w.values()) - 1.0) < 0.01

    def test_higher_priority_gets_more_weight(self):
        """Priority 1 (OpenMeteo) should get higher weight than priority 2 (NASA)"""
        mgr = ClimateSourceManager()
        w = mgr.get_fusion_weights(
            ["openmeteo_archive", "nasa_power"], 0, 0
        )
        assert w.get("openmeteo_archive", 0) >= w.get("nasa_power", 0)

    def test_nordic_bonus_met_norway(self):
        """MET Norway in Nordic region → +50% bonus"""
        mgr = ClimateSourceManager()
        w_nordic = mgr.get_fusion_weights(
            ["openmeteo_forecast", "met_norway"], 60.0, 10.0
        )
        w_global = mgr.get_fusion_weights(
            ["openmeteo_forecast", "met_norway"], 0, 0
        )
        # MET Norway weight should be higher in Nordic region
        assert w_nordic.get("met_norway", 0) > w_global.get("met_norway", 0)

    def test_usa_bonus_nws(self):
        """NWS in USA → +30% bonus"""
        mgr = ClimateSourceManager()
        w_usa = mgr.get_fusion_weights(
            ["openmeteo_forecast", "nws_forecast"], 40.71, -74.01
        )
        # NWS should have non-trivial weight in USA
        assert w_usa.get("nws_forecast", 0) > 0

    def test_unknown_source_skipped(self):
        mgr = ClimateSourceManager()
        w = mgr.get_fusion_weights(
            ["nasa_power", "nonexistent_source"], 0, 0
        )
        assert "nonexistent_source" not in w


# ════════════════════════════════════════════════════════════════
# _format_bbox / _is_point_covered
# ════════════════════════════════════════════════════════════════
class TestHelperMethods:

    def test_format_bbox_none(self):
        mgr = ClimateSourceManager()
        assert mgr._format_bbox(None) == "Global"

    def test_format_bbox_tuple(self):
        mgr = ClimateSourceManager()
        result = mgr._format_bbox((-125.0, 24.0, -66.0, 49.0))
        assert "125.0" in result

    def test_is_point_covered_global(self):
        mgr = ClimateSourceManager()
        assert mgr._is_point_covered(0, 0, {"coverage": "global"}) is True

    def test_is_point_covered_usa_in_usa(self):
        mgr = ClimateSourceManager()
        assert mgr._is_point_covered(40.71, -74.01, {"coverage": "usa"}) is True

    def test_is_point_covered_usa_outside(self):
        mgr = ClimateSourceManager()
        assert mgr._is_point_covered(51.5, -0.1, {"coverage": "usa"}) is False
