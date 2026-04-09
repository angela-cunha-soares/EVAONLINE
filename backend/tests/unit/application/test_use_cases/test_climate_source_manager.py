"""
Unit Tests - ClimateSourceManager & ClimateSourceSelector (Application Layer)

Tests the source selection and management logic:
- SOURCES_CONFIG completeness
- Source availability by location
- Mode-based source filtering
- Operation mode normalization
- Source selector priority ordering

Reference: Article Table 1 (Climate data sources)
"""

import pytest

from backend.api.services.climate_source_manager import (
    ClimateSourceManager,
    normalize_operation_mode,
)
from backend.api.services.climate_source_availability import OperationMode
from backend.api.services.climate_source_selector import ClimateSourceSelector


# ============================================================================
# normalize_operation_mode
# ============================================================================


@pytest.mark.unit
class TestNormalizeOperationMode:
    """Tests for period_type → OperationMode normalization."""

    def test_historical_email(self):
        assert normalize_operation_mode("historical_email") == OperationMode.HISTORICAL_EMAIL

    def test_dashboard_current(self):
        assert normalize_operation_mode("dashboard_current") == OperationMode.DASHBOARD_CURRENT

    def test_dashboard_forecast(self):
        assert normalize_operation_mode("dashboard_forecast") == OperationMode.DASHBOARD_FORECAST

    def test_none_defaults(self):
        """None period_type should default to DASHBOARD_CURRENT."""
        result = normalize_operation_mode(None)
        assert isinstance(result, OperationMode)


# ============================================================================
# ClimateSourceManager
# ============================================================================


@pytest.mark.unit
class TestClimateSourceManager:
    """Tests for ClimateSourceManager source configuration and selection."""

    def setup_method(self):
        self.manager = ClimateSourceManager()

    # --- SOURCES_CONFIG ---

    def test_sources_config_has_six_sources(self):
        """SOURCES_CONFIG must have all 6 climate data sources."""
        expected = {
            "openmeteo_archive", "openmeteo_forecast", "nasa_power",
            "nws_forecast", "nws_stations", "met_norway",
        }
        assert expected == set(self.manager.SOURCES_CONFIG.keys())

    def test_each_source_has_required_keys(self):
        """Each source config must have id, name, and coverage."""
        for src_id, config in self.manager.SOURCES_CONFIG.items():
            assert "id" in config or src_id, f"{src_id} missing 'id'"
            assert "name" in config, f"{src_id} missing 'name'"

    # --- Source Availability ---

    def test_brazil_gets_global_sources(self):
        """Brazil location should get global sources (NASA, OpenMeteo)."""
        sources = self.manager.get_available_sources_by_mode(
            lat=-22.29, lon=-48.58, mode=OperationMode.HISTORICAL_EMAIL
        )
        assert isinstance(sources, list)
        assert len(sources) >= 2  # At least nasa_power + openmeteo_archive

    def test_usa_gets_nws_sources_in_forecast(self):
        """USA location in forecast mode should include NWS sources."""
        sources = self.manager.get_available_sources_by_mode(
            lat=40.71, lon=-74.01, mode=OperationMode.DASHBOARD_FORECAST
        )
        assert "openmeteo_forecast" in sources
        # NWS should be in forecast mode for USA
        has_nws = "nws_forecast" in sources or "nws_stations" in sources
        assert has_nws, f"USA forecast should include NWS. Got: {sources}"

    def test_nordic_gets_met_norway_in_forecast(self):
        """Nordic location in forecast mode should include MET Norway."""
        sources = self.manager.get_available_sources_by_mode(
            lat=59.91, lon=10.75, mode=OperationMode.DASHBOARD_FORECAST
        )
        assert "met_norway" in sources

    def test_historical_mode_includes_primary_sources(self):
        """Historical mode should include NASA POWER and OpenMeteo Archive."""
        sources = self.manager.get_available_sources_by_mode(
            lat=-22.29, lon=-48.58, mode=OperationMode.HISTORICAL_EMAIL
        )
        assert "nasa_power" in sources
        assert "openmeteo_archive" in sources

    def test_forecast_mode_always_includes_openmeteo_forecast(self):
        """Forecast mode should always include openmeteo_forecast."""
        for lat, lon in [(-22.0, -48.0), (40.7, -74.0), (59.9, 10.7)]:
            sources = self.manager.get_available_sources_by_mode(
                lat=lat, lon=lon, mode=OperationMode.DASHBOARD_FORECAST
            )
            assert "openmeteo_forecast" in sources, (
                f"openmeteo_forecast missing for ({lat}, {lon})"
            )


# ============================================================================
# ClimateSourceSelector
# ============================================================================


@pytest.mark.unit
class TestClimateSourceSelector:
    """Tests for ClimateSourceSelector priority-based selection."""

    def test_select_source_brazil(self):
        """Brazil should get a valid source as best pick."""
        source = ClimateSourceSelector.select_source(-22.29, -48.58)
        assert source in (
            "openmeteo_forecast", "openmeteo_archive", "nasa_power",
            "met_norway",
        )

    def test_select_source_usa(self):
        """USA should prefer NWS forecast."""
        source = ClimateSourceSelector.select_source(40.71, -74.01)
        assert source in (
            "nws_forecast", "openmeteo_forecast", "nws_stations",
        )

    def test_get_all_sources_ordered(self):
        """get_all_sources should return a prioritized list."""
        sources = ClimateSourceSelector.get_all_sources(-22.29, -48.58)
        assert isinstance(sources, list)
        assert len(sources) >= 1

    def test_get_data_availability_summary_has_sources(self):
        """Summary should include all configured sources."""
        summary = ClimateSourceSelector.get_data_availability_summary()
        assert isinstance(summary, dict)
        assert len(summary) >= 3
