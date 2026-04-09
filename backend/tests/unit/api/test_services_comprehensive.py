"""
Tests for EToVariableValidator, timezone_utils, GeographicUtils, TimezoneUtils.

All pure-logic or lightweight-mock tests covering:
- EToVariableValidator: variable completeness checking per source
- timezone_utils: timezone detection, today calculation
- GeographicUtils: region detection, recommended sources, coordinates
- TimezoneUtils: ensure_naive, ensure_utc, make_aware, compare_dates_safe
- validate_coordinates decorator
"""

import pytest
from datetime import datetime, date, timezone
from backend.api.services.eto_variable_validator import EToVariableValidator
from backend.api.services.geographic_utils import (
    GeographicUtils,
    TimezoneUtils,
    validate_coordinates,
)
from backend.api.services.timezone_utils import (
    get_timezone_for_location,
    get_today_for_location,
    get_today_utc,
)


# ════════════════════════════════════════════════════════════════════
# EToVariableValidator
# ════════════════════════════════════════════════════════════════════

class TestEToVariableValidator:

    def test_nasa_power_has_all(self):
        assert EToVariableValidator.has_all_eto_variables("nasa_power") is True

    def test_openmeteo_archive_has_all(self):
        assert EToVariableValidator.has_all_eto_variables("openmeteo_archive") is True

    def test_openmeteo_forecast_has_all(self):
        assert EToVariableValidator.has_all_eto_variables("openmeteo_forecast") is True

    def test_met_norway_incomplete(self):
        assert EToVariableValidator.has_all_eto_variables("met_norway") is False

    def test_nws_forecast_incomplete(self):
        assert EToVariableValidator.has_all_eto_variables("nws_forecast") is False

    def test_nws_stations_incomplete(self):
        assert EToVariableValidator.has_all_eto_variables("nws_stations") is False

    def test_unknown_source(self):
        assert EToVariableValidator.has_all_eto_variables("nonexistent") is False

    def test_missing_variables_met_norway(self):
        missing = EToVariableValidator.get_missing_variables("met_norway")
        assert "wind_speed" in missing or "solar_radiation" in missing

    def test_missing_variables_unknown_source(self):
        missing = EToVariableValidator.get_missing_variables("nonexistent")
        assert missing == EToVariableValidator.REQUIRED_VARIABLES

    def test_available_variables_nasa(self):
        avail = EToVariableValidator.get_available_variables("nasa_power")
        assert "temperature_max" in avail
        assert "solar_radiation" in avail

    def test_available_variables_unknown(self):
        avail = EToVariableValidator.get_available_variables("nonexistent")
        assert avail == set()

    def test_get_sources_with_complete_eto(self):
        sources = EToVariableValidator.get_sources_with_complete_eto()
        assert "nasa_power" in sources
        assert "openmeteo_archive" in sources
        assert "openmeteo_forecast" in sources
        assert "met_norway" not in sources

    def test_get_source_description_complete(self):
        desc = EToVariableValidator.get_source_description("nasa_power")
        assert desc["has_complete_eto"] is True
        assert "Complete" in desc["description"]
        assert desc["missing_variables"] == []

    def test_get_source_description_incomplete(self):
        desc = EToVariableValidator.get_source_description("met_norway")
        assert desc["has_complete_eto"] is False
        assert "Incomplete" in desc["description"]
        assert len(desc["missing_variables"]) > 0

    def test_get_source_description_unknown(self):
        desc = EToVariableValidator.get_source_description("nonexistent")
        assert desc["has_complete_eto"] is False


# ════════════════════════════════════════════════════════════════════
# GeographicUtils — region detection
# ════════════════════════════════════════════════════════════════════

class TestGeographicUtils:

    # --- is_in_usa ---
    def test_is_in_usa_denver(self):
        assert GeographicUtils.is_in_usa(39.74, -104.99) is True

    def test_is_in_usa_outside(self):
        assert GeographicUtils.is_in_usa(-15.79, -47.88) is False

    # --- is_in_nordic ---
    def test_is_in_nordic_oslo(self):
        assert GeographicUtils.is_in_nordic(59.91, 10.75) is True

    def test_is_in_nordic_outside(self):
        assert GeographicUtils.is_in_nordic(39.74, -104.99) is False

    # --- is_in_brazil ---
    def test_is_in_brazil_sao_paulo(self):
        assert GeographicUtils.is_in_brazil(-23.55, -46.63) is True

    def test_is_in_brazil_outside(self):
        assert GeographicUtils.is_in_brazil(39.74, -104.99) is False

    # --- is_valid_coordinate ---
    def test_valid_coordinate(self):
        assert GeographicUtils.is_valid_coordinate(0, 0) is True

    def test_valid_coordinate_extremes(self):
        assert GeographicUtils.is_valid_coordinate(90, 180) is True
        assert GeographicUtils.is_valid_coordinate(-90, -180) is True

    def test_invalid_coordinate(self):
        assert GeographicUtils.is_valid_coordinate(91, 0) is False
        assert GeographicUtils.is_valid_coordinate(0, 181) is False

    # --- is_in_bbox ---
    def test_is_in_bbox_inside(self):
        assert GeographicUtils.is_in_bbox(40, -100, GeographicUtils.USA_BBOX) is True

    def test_is_in_bbox_outside(self):
        assert GeographicUtils.is_in_bbox(0, 0, GeographicUtils.USA_BBOX) is False

    def test_is_in_bbox_invalid_coords(self):
        assert GeographicUtils.is_in_bbox(999, 999, GeographicUtils.USA_BBOX) is False

    # --- get_region ---
    def test_get_region_usa(self):
        assert GeographicUtils.get_region(39.74, -104.99) == "usa"

    def test_get_region_nordic(self):
        assert GeographicUtils.get_region(59.91, 10.75) == "nordic"

    def test_get_region_brazil(self):
        assert GeographicUtils.get_region(-23.55, -46.63) == "brazil"

    def test_get_region_global(self):
        assert GeographicUtils.get_region(35.68, 139.69) == "global"

    # --- get_recommended_sources ---
    def test_recommended_sources_usa(self):
        sources = GeographicUtils.get_recommended_sources(39.74, -104.99)
        assert "nws_forecast" in sources
        assert "nws_stations" in sources

    def test_recommended_sources_nordic(self):
        sources = GeographicUtils.get_recommended_sources(59.91, 10.75)
        assert "met_norway" in sources

    def test_recommended_sources_brazil(self):
        sources = GeographicUtils.get_recommended_sources(-23.55, -46.63)
        assert "openmeteo_forecast" in sources
        assert "nasa_power" in sources

    def test_recommended_sources_global(self):
        sources = GeographicUtils.get_recommended_sources(35.68, 139.69)
        assert "openmeteo_forecast" in sources


# ════════════════════════════════════════════════════════════════════
# TimezoneUtils
# ════════════════════════════════════════════════════════════════════

class TestTimezoneUtils:

    def test_ensure_naive_from_aware(self):
        dt = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
        result = TimezoneUtils.ensure_naive(dt)
        assert result.tzinfo is None
        assert result.hour == 12

    def test_ensure_naive_already_naive(self):
        dt = datetime(2024, 1, 1, 12, 0)
        result = TimezoneUtils.ensure_naive(dt)
        assert result.tzinfo is None

    def test_ensure_naive_raises_for_non_datetime(self):
        with pytest.raises(TypeError):
            TimezoneUtils.ensure_naive("not a datetime")

    def test_ensure_utc_from_naive(self):
        dt = datetime(2024, 1, 1, 12, 0)
        result = TimezoneUtils.ensure_utc(dt)
        assert result.tzinfo is not None

    def test_ensure_utc_from_aware(self):
        dt = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
        result = TimezoneUtils.ensure_utc(dt)
        assert result.tzinfo is not None

    def test_ensure_utc_raises_for_non_datetime(self):
        with pytest.raises(TypeError):
            TimezoneUtils.ensure_utc("not a datetime")

    def test_make_aware_from_naive(self):
        dt = datetime(2024, 1, 1, 12, 0)
        result = TimezoneUtils.make_aware(dt)
        assert result.tzinfo is not None

    def test_make_aware_already_aware(self):
        dt = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
        result = TimezoneUtils.make_aware(dt)
        assert result.tzinfo is not None

    def test_make_aware_raises_for_non_datetime(self):
        with pytest.raises(TypeError):
            TimezoneUtils.make_aware("not a datetime")

    def test_compare_dates_safe_lt(self):
        d1 = datetime(2024, 1, 1)
        d2 = datetime(2024, 1, 2)
        assert TimezoneUtils.compare_dates_safe(d1, d2, "lt") is True

    def test_compare_dates_safe_le(self):
        d1 = datetime(2024, 1, 1)
        assert TimezoneUtils.compare_dates_safe(d1, d1, "le") is True

    def test_compare_dates_safe_gt(self):
        d1 = datetime(2024, 1, 2)
        d2 = datetime(2024, 1, 1)
        assert TimezoneUtils.compare_dates_safe(d1, d2, "gt") is True

    def test_compare_dates_safe_ge(self):
        d1 = datetime(2024, 1, 1)
        assert TimezoneUtils.compare_dates_safe(d1, d1, "ge") is True

    def test_compare_dates_safe_eq(self):
        d1 = datetime(2024, 1, 1)
        d2 = datetime(2024, 1, 1)
        assert TimezoneUtils.compare_dates_safe(d1, d2, "eq") is True

    def test_compare_dates_safe_mixed_types(self):
        dt = datetime(2024, 1, 1)
        d = date(2024, 1, 1)
        assert TimezoneUtils.compare_dates_safe(dt, d, "eq") is True

    def test_compare_dates_safe_invalid_comparison(self):
        d = datetime(2024, 1, 1)
        with pytest.raises(ValueError):
            TimezoneUtils.compare_dates_safe(d, d, "invalid")

    def test_compare_dates_safe_invalid_types(self):
        with pytest.raises(TypeError):
            TimezoneUtils.compare_dates_safe("2024-01-01", "2024-01-02", "lt")


# ════════════════════════════════════════════════════════════════════
# validate_coordinates decorator
# ════════════════════════════════════════════════════════════════════

class TestValidateCoordinatesDecorator:

    def test_valid_coordinates(self):
        @validate_coordinates
        def my_func(lat, lon):
            return f"{lat},{lon}"

        assert my_func(39.74, -104.99) == "39.74,-104.99"

    def test_invalid_latitude(self):
        @validate_coordinates
        def my_func(lat, lon):
            return True

        with pytest.raises(ValueError, match="Invalid coordinates"):
            my_func(999, 0)

    def test_invalid_longitude(self):
        @validate_coordinates
        def my_func(lat, lon):
            return True

        with pytest.raises(ValueError, match="Invalid coordinates"):
            my_func(0, 999)


# ════════════════════════════════════════════════════════════════════
# timezone_utils module functions
# ════════════════════════════════════════════════════════════════════

class TestTimezoneUtilsModule:

    def test_get_timezone_for_location_brazil(self):
        tz = get_timezone_for_location(-23.55, -46.63)
        assert tz is not None
        assert "Sao_Paulo" in str(tz) or "America" in str(tz)

    def test_get_timezone_for_location_utc_fallback(self):
        """Ocean location may return UTC"""
        tz = get_timezone_for_location(0.0, 0.0)
        assert tz is not None

    def test_get_today_for_location(self):
        today = get_today_for_location(-23.55, -46.63)
        assert isinstance(today, date)

    def test_get_today_utc(self):
        today = get_today_utc()
        assert isinstance(today, date)
