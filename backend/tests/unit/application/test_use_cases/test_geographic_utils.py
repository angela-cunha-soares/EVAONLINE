"""
Unit Tests - GeographicUtils & TimezoneUtils

Tests geographic region detection (bounding boxes), coordinate validation,
and timezone-safe datetime helpers.

Reference: Article Section 2.2 (Regional Source Selection)
"""

import pytest
from datetime import datetime, timezone

from backend.api.services.geographic_utils import (
    GeographicUtils,
    TimezoneUtils,
)


# ============================================================================
# GeographicUtils — Region Detection
# ============================================================================


@pytest.mark.unit
class TestIsInUSA:
    """USA bounding box detection."""

    def test_denver_is_usa(self):
        assert GeographicUtils.is_in_usa(39.74, -104.99) is True

    def test_new_york_is_usa(self):
        assert GeographicUtils.is_in_usa(40.71, -74.01) is True

    def test_miami_is_usa(self):
        assert GeographicUtils.is_in_usa(25.76, -80.19) is True

    def test_london_not_usa(self):
        assert GeographicUtils.is_in_usa(51.51, -0.13) is False

    def test_sao_paulo_not_usa(self):
        assert GeographicUtils.is_in_usa(-23.55, -46.63) is False


@pytest.mark.unit
class TestIsInNordic:
    """Nordic bounding box detection."""

    def test_helsinki_is_nordic(self):
        assert GeographicUtils.is_in_nordic(60.17, 24.94) is True

    def test_oslo_is_nordic(self):
        assert GeographicUtils.is_in_nordic(59.91, 10.75) is True

    def test_paris_not_nordic(self):
        assert GeographicUtils.is_in_nordic(48.86, 2.35) is False

    def test_sao_paulo_not_nordic(self):
        assert GeographicUtils.is_in_nordic(-23.55, -46.63) is False


@pytest.mark.unit
class TestIsInBrazil:
    """Brazil bounding box detection."""

    def test_sao_paulo_is_brazil(self):
        assert GeographicUtils.is_in_brazil(-23.55, -46.63) is True

    def test_manaus_is_brazil(self):
        assert GeographicUtils.is_in_brazil(-3.12, -60.02) is True

    def test_buenos_aires_not_brazil(self):
        assert GeographicUtils.is_in_brazil(-34.60, -58.38) is False

    def test_new_york_not_brazil(self):
        assert GeographicUtils.is_in_brazil(40.71, -74.01) is False


@pytest.mark.unit
class TestIsValidCoordinate:
    """Global coordinate bounds validation."""

    def test_origin_valid(self):
        assert GeographicUtils.is_valid_coordinate(0, 0) is True

    def test_extremes_valid(self):
        assert GeographicUtils.is_valid_coordinate(-90, -180) is True
        assert GeographicUtils.is_valid_coordinate(90, 180) is True

    def test_latitude_out_of_range(self):
        assert GeographicUtils.is_valid_coordinate(91, 0) is False
        assert GeographicUtils.is_valid_coordinate(-91, 0) is False

    def test_longitude_out_of_range(self):
        assert GeographicUtils.is_valid_coordinate(0, 181) is False
        assert GeographicUtils.is_valid_coordinate(0, -181) is False


@pytest.mark.unit
class TestGetRegion:
    """Region priority: USA > Nordic > Brazil > Global."""

    def test_usa_region(self):
        assert GeographicUtils.get_region(39.74, -104.99) == "usa"

    def test_nordic_region(self):
        assert GeographicUtils.get_region(60.17, 24.94) == "nordic"

    def test_brazil_region(self):
        assert GeographicUtils.get_region(-23.55, -46.63) == "brazil"

    def test_global_fallback(self):
        # Antarctica — not in any special region
        region = GeographicUtils.get_region(-80.0, 0.0)
        assert region == "global"


@pytest.mark.unit
class TestGetRecommendedSources:
    """Source priority per region."""

    def test_usa_includes_nws(self):
        sources = GeographicUtils.get_recommended_sources(39.74, -104.99)
        assert any("nws" in s for s in sources)

    def test_nordic_includes_met_norway(self):
        sources = GeographicUtils.get_recommended_sources(60.17, 24.94)
        assert "met_norway" in sources

    def test_brazil_has_global_sources(self):
        sources = GeographicUtils.get_recommended_sources(-23.55, -46.63)
        assert len(sources) >= 2
        assert any("openmeteo" in s or "nasa" in s for s in sources)

    def test_all_regions_have_fallback(self):
        """Every region should have at least nasa_power + openmeteo as fallback."""
        for lat, lon in [(39.74, -104.99), (60.17, 24.94), (-23.55, -46.63), (-80, 0)]:
            sources = GeographicUtils.get_recommended_sources(lat, lon)
            assert len(sources) >= 2


@pytest.mark.unit
class TestIsInBbox:
    """Generic bounding box check."""

    def test_inside_bbox(self):
        bbox = (-10, -10, 10, 10)  # (west, south, east, north)
        assert GeographicUtils.is_in_bbox(0, 0, bbox) is True

    def test_outside_bbox(self):
        bbox = (-10, -10, 10, 10)
        assert GeographicUtils.is_in_bbox(20, 20, bbox) is False


# ============================================================================
# TimezoneUtils — Datetime Helpers
# ============================================================================


@pytest.mark.unit
class TestEnsureNaive:
    """Strip timezone from datetime."""

    def test_aware_becomes_naive(self):
        dt_aware = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)
        result = TimezoneUtils.ensure_naive(dt_aware)
        assert result.tzinfo is None

    def test_naive_stays_naive(self):
        dt_naive = datetime(2025, 1, 1, 12, 0)
        result = TimezoneUtils.ensure_naive(dt_naive)
        assert result.tzinfo is None
        assert result == dt_naive


@pytest.mark.unit
class TestEnsureUTC:
    """Force datetime to UTC."""

    def test_naive_becomes_utc(self):
        dt_naive = datetime(2025, 1, 1, 12, 0)
        result = TimezoneUtils.ensure_utc(dt_naive)
        assert result.tzinfo is not None

    def test_utc_stays_utc(self):
        dt_utc = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)
        result = TimezoneUtils.ensure_utc(dt_utc)
        assert result.tzinfo is not None


@pytest.mark.unit
class TestCompareDatesSafe:
    """Timezone-safe date comparison."""

    def test_less_than(self):
        dt1 = datetime(2025, 1, 1, tzinfo=timezone.utc)
        dt2 = datetime(2025, 1, 2, tzinfo=timezone.utc)
        assert TimezoneUtils.compare_dates_safe(dt1, dt2, "lt") is True
        assert TimezoneUtils.compare_dates_safe(dt2, dt1, "lt") is False

    def test_equal(self):
        dt1 = datetime(2025, 1, 1, tzinfo=timezone.utc)
        dt2 = datetime(2025, 1, 1, tzinfo=timezone.utc)
        assert TimezoneUtils.compare_dates_safe(dt1, dt2, "eq") is True

    def test_greater_than(self):
        dt1 = datetime(2025, 1, 2, tzinfo=timezone.utc)
        dt2 = datetime(2025, 1, 1, tzinfo=timezone.utc)
        assert TimezoneUtils.compare_dates_safe(dt1, dt2, "gt") is True
