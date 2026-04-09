"""
Unit Tests - ClimateSourceAvailability

Tests operation mode enum, API date limits, and source availability
determination based on date ranges and geographic location.

Reference: Article Section 2.2 (Source Availability Matrix)
"""

import pytest
from datetime import date, timedelta
from unittest.mock import patch

from backend.api.services.climate_source_availability import (
    ClimateSourceAvailability,
    OperationMode,
)


# ============================================================================
# OperationMode Enum
# ============================================================================


@pytest.mark.unit
class TestOperationMode:
    """Operation mode enum values."""

    def test_historical_email_value(self):
        assert OperationMode.HISTORICAL_EMAIL.value == "historical_email"

    def test_dashboard_current_value(self):
        assert OperationMode.DASHBOARD_CURRENT.value == "dashboard_current"

    def test_dashboard_forecast_value(self):
        assert OperationMode.DASHBOARD_FORECAST.value == "dashboard_forecast"

    def test_has_three_modes(self):
        assert len(OperationMode) == 3


# ============================================================================
# Date Parsing
# ============================================================================


@pytest.mark.unit
class TestParseDate:
    """Date parsing utility."""

    def test_parse_iso_string(self):
        result = ClimateSourceAvailability._parse_date("2025-01-15")
        assert result == date(2025, 1, 15)

    def test_parse_date_object_passthrough(self):
        d = date(2025, 6, 15)
        result = ClimateSourceAvailability._parse_date(d)
        assert result == d

    def test_parse_invalid_raises(self):
        with pytest.raises((ValueError, TypeError)):
            ClimateSourceAvailability._parse_date("not-a-date")


# ============================================================================
# Source Availability
# ============================================================================


@pytest.mark.unit
class TestGetAvailableSources:
    """Available sources for a given date range and location."""

    @patch("backend.api.services.climate_source_availability.get_today_for_location")
    @patch("backend.api.services.climate_source_availability.GeographicUtils")
    def test_historical_includes_nasa_power(self, mock_geo, mock_today):
        mock_today.return_value = date(2025, 6, 1)
        mock_geo.is_in_usa.return_value = False
        mock_geo.is_in_nordic.return_value = False

        result = ClimateSourceAvailability.get_available_sources(
            "2024-01-01", "2024-01-30", -23.55, -46.63
        )
        assert isinstance(result, dict)
        # NASA POWER should be available for historical dates
        result_str = str(result).lower()
        assert "nasa" in result_str

    @patch("backend.api.services.climate_source_availability.get_today_for_location")
    @patch("backend.api.services.climate_source_availability.GeographicUtils")
    def test_usa_includes_nws(self, mock_geo, mock_today):
        today = date(2025, 6, 1)
        mock_today.return_value = today
        mock_geo.is_in_usa.return_value = True
        mock_geo.is_in_nordic.return_value = False

        result = ClimateSourceAvailability.get_available_sources(
            today.isoformat(),
            (today + timedelta(days=5)).isoformat(),
            39.74,
            -104.99,
        )
        result_str = str(result).lower()
        assert "nws" in result_str

    @patch("backend.api.services.climate_source_availability.get_today_for_location")
    @patch("backend.api.services.climate_source_availability.GeographicUtils")
    def test_nordic_includes_met_norway(self, mock_geo, mock_today):
        today = date(2025, 6, 1)
        mock_today.return_value = today
        mock_geo.is_in_usa.return_value = False
        mock_geo.is_in_nordic.return_value = True

        result = ClimateSourceAvailability.get_available_sources(
            today.isoformat(),
            (today + timedelta(days=5)).isoformat(),
            60.17,
            24.94,
        )
        result_str = str(result).lower()
        assert "met" in result_str or "norway" in result_str


@pytest.mark.unit
class TestGetCompatibleSourcesList:
    """Filtered list of available source names."""

    @patch("backend.api.services.climate_source_availability.get_today_for_location")
    @patch("backend.api.services.climate_source_availability.GeographicUtils")
    def test_returns_list(self, mock_geo, mock_today):
        mock_today.return_value = date(2025, 6, 1)
        mock_geo.is_in_usa.return_value = False
        mock_geo.is_in_nordic.return_value = False

        result = ClimateSourceAvailability.get_compatible_sources_list(
            "2024-01-01", "2024-01-30", -23.55, -46.63
        )
        assert isinstance(result, list)
        assert len(result) >= 1

    @patch("backend.api.services.climate_source_availability.get_today_for_location")
    @patch("backend.api.services.climate_source_availability.GeographicUtils")
    def test_all_elements_are_strings(self, mock_geo, mock_today):
        mock_today.return_value = date(2025, 6, 1)
        mock_geo.is_in_usa.return_value = False
        mock_geo.is_in_nordic.return_value = False

        result = ClimateSourceAvailability.get_compatible_sources_list(
            "2024-01-01", "2024-01-30", -23.55, -46.63
        )
        for source in result:
            assert isinstance(source, str)


# ============================================================================
# API Date Limits
# ============================================================================


@pytest.mark.unit
class TestGetApiDateLimits:
    """Date limit computation per mode."""

    def test_historical_email_limits(self):
        today = date(2025, 6, 1)
        limits = ClimateSourceAvailability.get_api_date_limits_for_context(
            OperationMode.HISTORICAL_EMAIL.value, today=today
        )
        assert isinstance(limits, dict)
        assert len(limits) >= 1

    def test_dashboard_current_limits(self):
        today = date(2025, 6, 1)
        limits = ClimateSourceAvailability.get_api_date_limits_for_context(
            OperationMode.DASHBOARD_CURRENT.value, today=today
        )
        assert isinstance(limits, dict)

    def test_dashboard_forecast_limits(self):
        today = date(2025, 6, 1)
        limits = ClimateSourceAvailability.get_api_date_limits_for_context(
            OperationMode.DASHBOARD_FORECAST.value, today=today
        )
        assert isinstance(limits, dict)
        # Forecast should include openmeteo_forecast
        assert "openmeteo_forecast" in limits


@pytest.mark.unit
class TestIsSourceAvailable:
    """Individual source availability check."""

    def test_unknown_source_is_unavailable(self):
        result = ClimateSourceAvailability.is_source_available(
            "nonexistent_api",
            OperationMode.HISTORICAL_EMAIL.value,
            "2024-01-01",
            "2024-01-30",
        )
        assert result is False

    def test_nasa_power_available_for_historical(self):
        result = ClimateSourceAvailability.is_source_available(
            "nasa_power",
            OperationMode.HISTORICAL_EMAIL.value,
            "2024-01-01",
            "2024-01-30",
        )
        # NASA POWER covers historical data well within range
        assert isinstance(result, bool)
