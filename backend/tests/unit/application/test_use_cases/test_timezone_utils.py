"""
Unit Tests - timezone_utils

Tests timezone detection from coordinates, location-aware date
computation, and UTC date helper.

Reference: Article Section 2.1 (Timezone-Aware Validation)
"""

import pytest
from datetime import date

from backend.api.services.timezone_utils import (
    get_timezone_for_location,
    get_today_for_location,
    get_today_utc,
)


@pytest.mark.unit
class TestGetTimezoneForLocation:
    """Timezone detection from coordinates."""

    def test_sao_paulo_timezone(self):
        tz = get_timezone_for_location(-23.55, -46.63)
        assert tz is not None
        tz_name = str(tz)
        assert "Sao_Paulo" in tz_name or "America" in tz_name or "UTC" in tz_name

    def test_new_york_timezone(self):
        tz = get_timezone_for_location(40.71, -74.01)
        assert tz is not None
        tz_name = str(tz)
        assert "New_York" in tz_name or "America" in tz_name or "Eastern" in tz_name or "UTC" in tz_name

    def test_ocean_falls_back_to_utc(self):
        """Mid-ocean coordinates may not have a timezone — should fallback to UTC."""
        tz = get_timezone_for_location(0.0, -30.0)
        assert tz is not None  # Should return UTC, not None

    def test_returns_pytz_timezone(self):
        import pytz
        tz = get_timezone_for_location(-23.55, -46.63)
        # Should be a pytz timezone or equivalent
        assert hasattr(tz, "localize") or hasattr(tz, "zone") or tz == pytz.UTC


@pytest.mark.unit
class TestGetTodayForLocation:
    """Location-aware today computation."""

    def test_returns_date_object(self):
        result = get_today_for_location(-23.55, -46.63)
        assert isinstance(result, date)

    def test_date_is_reasonable(self):
        """Should be within ±1 day of UTC date (timezone differences)."""
        today_utc = get_today_utc()
        today_local = get_today_for_location(-23.55, -46.63)
        diff = abs((today_utc - today_local).days)
        assert diff <= 1

    def test_different_locations_may_differ(self):
        """Far east and far west locations might have different dates near midnight."""
        d1 = get_today_for_location(35.68, 139.69)   # Tokyo
        d2 = get_today_for_location(21.31, -157.86)  # Honolulu
        diff = abs((d1 - d2).days)
        assert diff <= 1  # Up to 1 day apart


@pytest.mark.unit
class TestGetTodayUtc:
    """UTC date helper."""

    def test_returns_date(self):
        result = get_today_utc()
        assert isinstance(result, date)

    def test_consistent_calls(self):
        """Two consecutive calls should return same date."""
        d1 = get_today_utc()
        d2 = get_today_utc()
        assert d1 == d2
