"""
Unit Tests - Weather Utilities & Geographic Utilities (Application Layer)

Tests:
- WeatherConversionUtils: unit conversions (wind, temperature, radiation)
- ElevationUtils: FAO-56 atmospheric corrections
- EToVariableValidator: source variable completeness
- GeographicUtils: bounding box detection
- Geo Utils (core): Haversine distance, region detection

Reference: Article Section 2.2 (Data Harmonization)
"""

import pytest

from backend.api.services.weather_utils import (
    WeatherConversionUtils,
    ElevationUtils,
)
from backend.api.services.geographic_utils import GeographicUtils
from backend.api.services.eto_variable_validator import EToVariableValidator
from backend.core.utils.geo_utils import (
    haversine_distance,
    detect_geographic_region,
)


# ============================================================================
# WeatherConversionUtils
# ============================================================================


@pytest.mark.unit
class TestWeatherConversions:
    """Tests for meteorological unit conversion functions."""

    def test_wind_10m_to_2m(self):
        """FAO-56 Eq. 47: u2 = u10 × 4.87 / ln(67.8×10 - 5.42) ≈ u10 × 0.748."""
        result = WeatherConversionUtils.convert_wind_10m_to_2m(10.0)
        assert result == pytest.approx(7.48, abs=0.1)

    def test_wind_10m_to_2m_zero(self):
        result = WeatherConversionUtils.convert_wind_10m_to_2m(0.0)
        assert result == pytest.approx(0.0, abs=0.01)

    def test_wind_10m_to_2m_none(self):
        result = WeatherConversionUtils.convert_wind_10m_to_2m(None)
        assert result is None

    def test_fahrenheit_to_celsius(self):
        assert WeatherConversionUtils.fahrenheit_to_celsius(32.0) == pytest.approx(0.0)
        assert WeatherConversionUtils.fahrenheit_to_celsius(212.0) == pytest.approx(100.0)

    def test_celsius_to_fahrenheit(self):
        assert WeatherConversionUtils.celsius_to_fahrenheit(0.0) == pytest.approx(32.0)
        assert WeatherConversionUtils.celsius_to_fahrenheit(100.0) == pytest.approx(212.0)

    def test_mph_to_ms(self):
        result = WeatherConversionUtils.mph_to_ms(1.0)
        assert result == pytest.approx(0.44704, abs=0.001)

    def test_wh_to_mj(self):
        result = WeatherConversionUtils.wh_per_m2_to_mj_per_m2(1000.0)
        assert result == pytest.approx(3.6, abs=0.01)


# ============================================================================
# ElevationUtils
# ============================================================================


@pytest.mark.unit
class TestElevationUtils:
    """Tests for FAO-56 elevation-based corrections."""

    def test_atmospheric_pressure_sea_level(self):
        """FAO-56 Eq. 7: P ≈ 101.3 kPa at z = 0."""
        p = ElevationUtils.calculate_atmospheric_pressure(0.0)
        assert p == pytest.approx(101.3, abs=0.5)

    def test_atmospheric_pressure_decreases_with_altitude(self):
        p0 = ElevationUtils.calculate_atmospheric_pressure(0.0)
        p500 = ElevationUtils.calculate_atmospheric_pressure(500.0)
        p2000 = ElevationUtils.calculate_atmospheric_pressure(2000.0)
        assert p0 > p500 > p2000

    def test_psychrometric_constant_sea_level(self):
        """FAO-56 Eq. 8: γ ≈ 0.0665 kPa/°C at z = 0."""
        gamma = ElevationUtils.calculate_psychrometric_constant(0.0)
        assert gamma == pytest.approx(0.0665, abs=0.005)

    def test_elevation_correction_factor_keys(self):
        factors = ElevationUtils.get_elevation_correction_factor(580.0)
        assert "pressure" in factors
        assert "gamma" in factors
        assert "elevation" in factors
        assert factors["elevation"] == 580.0


# ============================================================================
# GeographicUtils (bounding boxes)
# ============================================================================


@pytest.mark.unit
class TestGeographicUtils:
    """Tests for geographic bounding box utilities."""

    LOCATIONS = {
        "brazil": (-22.29, -48.58),    # Jaú, SP
        "usa": (40.71, -74.01),         # New York
        "nordic": (59.91, 10.75),       # Oslo
        "outside": (35.0, 139.0),       # Tokyo
    }

    def test_is_in_brazil(self):
        assert GeographicUtils.is_in_brazil(*self.LOCATIONS["brazil"])
        assert not GeographicUtils.is_in_brazil(*self.LOCATIONS["usa"])

    def test_is_in_usa(self):
        assert GeographicUtils.is_in_usa(*self.LOCATIONS["usa"])
        assert not GeographicUtils.is_in_usa(*self.LOCATIONS["brazil"])

    def test_is_in_nordic(self):
        assert GeographicUtils.is_in_nordic(*self.LOCATIONS["nordic"])
        assert not GeographicUtils.is_in_nordic(*self.LOCATIONS["brazil"])

    def test_is_valid_coordinate(self):
        assert GeographicUtils.is_valid_coordinate(-22.29, -48.58)
        assert not GeographicUtils.is_valid_coordinate(100.0, 200.0)


# ============================================================================
# Haversine Distance (core geo)
# ============================================================================


@pytest.mark.unit
class TestHaversineDistance:
    """Tests for Haversine great-circle distance calculation."""

    def test_same_point_zero_distance(self):
        d = haversine_distance(-22.29, -48.58, -22.29, -48.58)
        assert d == pytest.approx(0.0, abs=0.01)

    def test_known_distance_sp_rj(self):
        """São Paulo → Rio de Janeiro ≈ 360 km."""
        d = haversine_distance(-23.55, -46.63, -22.91, -43.17)
        assert 340 < d < 400

    def test_antipodal_points(self):
        """Points on opposite sides of Earth ≈ 20,000 km."""
        d = haversine_distance(0, 0, 0, 180)
        assert d == pytest.approx(20015, rel=0.01)

    def test_equator_distance_per_degree(self):
        """1 degree of longitude at equator ≈ 111 km."""
        d = haversine_distance(0, 0, 0, 1)
        assert 110 < d < 112


# ============================================================================
# Geographic Region Detection (core)
# ============================================================================


@pytest.mark.unit
class TestRegionDetection:
    """Tests for detect_geographic_region function."""

    def test_brazil(self):
        region = detect_geographic_region(-22.29, -48.58)
        assert region == "brasil"

    def test_usa(self):
        region = detect_geographic_region(40.71, -74.01)
        assert region == "usa"

    def test_europe(self):
        region = detect_geographic_region(48.86, 2.35)  # Paris
        assert region == "global"

    def test_global_ocean(self):
        """Mid-Pacific should return 'global'."""
        region = detect_geographic_region(0.0, -170.0)
        assert region == "global"


# ============================================================================
# EToVariableValidator
# ============================================================================


@pytest.mark.unit
class TestEToVariableValidator:
    """Tests for climate source ETo variable completeness."""

    def test_nasa_power_has_all_eto_variables(self):
        assert EToVariableValidator.has_all_eto_variables("nasa_power")

    def test_openmeteo_archive_has_all_eto_variables(self):
        assert EToVariableValidator.has_all_eto_variables("openmeteo_archive")

    def test_openmeteo_forecast_has_all_eto_variables(self):
        assert EToVariableValidator.has_all_eto_variables("openmeteo_forecast")

    def test_sources_with_complete_eto(self):
        """At least 3 sources should have complete ETo capability."""
        complete = EToVariableValidator.get_sources_with_complete_eto()
        assert len(complete) >= 3

    def test_required_variables_count(self):
        """FAO-56 requires 6 meteorological variables."""
        assert len(EToVariableValidator.REQUIRED_VARIABLES) == 6


# ============================================================================
# WeatherValidationUtils — Physical Range Checks
# ============================================================================

from backend.api.services.weather_utils import (
    WeatherValidationUtils,
    WeatherAggregationUtils,
    CacheUtils,
    METNorwayAggregationUtils,
)
from datetime import datetime, timedelta, timezone


@pytest.mark.unit
class TestGetValidationLimits:
    """Region-aware physical limits lookup."""

    def test_global_has_temperature_key(self):
        limits = WeatherValidationUtils.get_validation_limits()
        assert "temperature" in limits

    def test_global_has_humidity_key(self):
        limits = WeatherValidationUtils.get_validation_limits()
        assert "humidity" in limits

    def test_brazil_stricter_temperature(self):
        b = WeatherValidationUtils.get_validation_limits(region="brazil")
        g = WeatherValidationUtils.get_validation_limits(region="global")
        # Global should be at least as wide
        assert g["temperature"][0] <= b["temperature"][0]


@pytest.mark.unit
class TestIsValidTemperature:
    """Temperature range validation."""

    def test_normal(self):
        assert WeatherValidationUtils.is_valid_temperature(25.0) is True

    def test_extreme_cold_invalid(self):
        assert WeatherValidationUtils.is_valid_temperature(-100.0) is False

    def test_extreme_hot_invalid(self):
        assert WeatherValidationUtils.is_valid_temperature(65.0) is False

    def test_none_is_valid(self):
        assert WeatherValidationUtils.is_valid_temperature(None) is True


@pytest.mark.unit
class TestIsValidHumidity:
    """Humidity 0–100% validation."""

    def test_normal(self):
        assert WeatherValidationUtils.is_valid_humidity(65.0) is True

    def test_negative(self):
        assert WeatherValidationUtils.is_valid_humidity(-5.0) is False

    def test_over_100(self):
        assert WeatherValidationUtils.is_valid_humidity(105.0) is False

    def test_none_is_valid(self):
        assert WeatherValidationUtils.is_valid_humidity(None) is True


@pytest.mark.unit
class TestIsValidWindSpeed:
    """Wind speed non-negative + below regional max."""

    def test_normal(self):
        assert WeatherValidationUtils.is_valid_wind_speed(5.0) is True

    def test_negative(self):
        assert WeatherValidationUtils.is_valid_wind_speed(-1.0) is False

    def test_none_is_valid(self):
        assert WeatherValidationUtils.is_valid_wind_speed(None) is True


@pytest.mark.unit
class TestIsValidPrecipitation:
    """Precipitation non-negative."""

    def test_zero(self):
        assert WeatherValidationUtils.is_valid_precipitation(0.0) is True

    def test_negative(self):
        assert WeatherValidationUtils.is_valid_precipitation(-1.0) is False

    def test_none_is_valid(self):
        assert WeatherValidationUtils.is_valid_precipitation(None) is True


@pytest.mark.unit
class TestIsValidSolarRadiation:
    """Solar radiation range."""

    def test_normal(self):
        assert WeatherValidationUtils.is_valid_solar_radiation(20.0) is True

    def test_none_is_valid(self):
        assert WeatherValidationUtils.is_valid_solar_radiation(None) is True


@pytest.mark.unit
class TestValidateDailyData:
    """Full daily record validation."""

    def test_valid_complete(self):
        data = {
            "temp_max": 30.0, "temp_min": 18.0, "temp_mean": 24.0,
            "humidity_mean": 65.0, "wind_speed_2m_mean": 3.0,
            "precipitation_sum": 5.0, "solar_radiation": 20.0,
        }
        assert WeatherValidationUtils.validate_daily_data(data) is True

    def test_invalid_temperature(self):
        data = {"temp_max": 200.0}
        assert WeatherValidationUtils.validate_daily_data(data) is False

    def test_empty_is_valid(self):
        assert WeatherValidationUtils.validate_daily_data({}) is True


# ============================================================================
# WeatherAggregationUtils
# ============================================================================


@pytest.mark.unit
class TestAggregateTemperature:
    """Temperature aggregation."""

    def test_mean(self):
        assert WeatherAggregationUtils.aggregate_temperature([20.0, 30.0]) == pytest.approx(25.0)

    def test_max(self):
        assert WeatherAggregationUtils.aggregate_temperature([20.0, 30.0], method="max") == pytest.approx(30.0)

    def test_min(self):
        assert WeatherAggregationUtils.aggregate_temperature([20.0, 30.0], method="min") == pytest.approx(20.0)

    def test_empty_returns_none(self):
        assert WeatherAggregationUtils.aggregate_temperature([]) is None


@pytest.mark.unit
class TestAggregatePrecipitation:
    """Precipitation sum."""

    def test_sum(self):
        assert WeatherAggregationUtils.aggregate_precipitation([5.0, 10.0, 2.5]) == pytest.approx(17.5)

    def test_empty_returns_none(self):
        assert WeatherAggregationUtils.aggregate_precipitation([]) is None


@pytest.mark.unit
class TestSafeDivision:
    """Division with None/zero protection."""

    def test_normal(self):
        assert WeatherAggregationUtils.safe_division(10.0, 2.0) == pytest.approx(5.0)

    def test_zero_denominator(self):
        assert WeatherAggregationUtils.safe_division(10.0, 0.0) is None

    def test_none_numerator(self):
        assert WeatherAggregationUtils.safe_division(None, 2.0) is None

    def test_none_denominator(self):
        assert WeatherAggregationUtils.safe_division(10.0, None) is None


# ============================================================================
# CacheUtils
# ============================================================================


@pytest.mark.unit
class TestCacheUtilsParseDate:
    """RFC-1123 date parsing."""

    def test_valid(self):
        result = CacheUtils.parse_rfc1123_date("Thu, 01 Jan 2026 12:00:00 GMT")
        assert result is not None
        assert result.year == 2026

    def test_none(self):
        assert CacheUtils.parse_rfc1123_date(None) is None


@pytest.mark.unit
class TestCacheUtilsTTL:
    """Cache TTL calculation."""

    def test_default_when_none(self):
        assert CacheUtils.calculate_cache_ttl(None) == 3600

    def test_custom_default(self):
        assert CacheUtils.calculate_cache_ttl(None, default_ttl=7200) == 7200

    def test_minimum_60(self):
        expired = datetime.now(timezone.utc) - timedelta(hours=1)
        ttl = CacheUtils.calculate_cache_ttl(expired)
        assert ttl >= 60

    def test_maximum_86400(self):
        far = datetime.now(timezone.utc) + timedelta(days=30)
        ttl = CacheUtils.calculate_cache_ttl(far)
        assert ttl <= 86400


# ============================================================================
# METNorwayAggregationUtils
# ============================================================================


@pytest.mark.unit
class TestMETValidateDailyData:
    """MET Norway daily data validation."""

    def test_valid(self):
        data = [{"temp_max": 5.0, "temp_min": -2.0, "humidity_mean": 85.0, "precipitation_sum": 3.0}]
        assert METNorwayAggregationUtils.validate_daily_data(data) is True

    def test_empty_false(self):
        assert METNorwayAggregationUtils.validate_daily_data([]) is False

    def test_invalid_humidity(self):
        data = [{"temp_max": 5.0, "temp_min": -2.0, "humidity_mean": 150.0, "precipitation_sum": 0}]
        assert METNorwayAggregationUtils.validate_daily_data(data) is False

    def test_negative_precip(self):
        data = [{"temp_max": 5.0, "temp_min": -2.0, "humidity_mean": 50.0, "precipitation_sum": -1.0}]
        assert METNorwayAggregationUtils.validate_daily_data(data) is False


# ============================================================================
# Conversion roundtrips
# ============================================================================


@pytest.mark.unit
class TestConversionRoundtrips:
    """Verify conversions are invertible."""

    def test_fahrenheit_celsius_roundtrip(self):
        c = 25.0
        assert WeatherConversionUtils.fahrenheit_to_celsius(
            WeatherConversionUtils.celsius_to_fahrenheit(c)
        ) == pytest.approx(c)

    def test_radiation_roundtrip(self):
        mj = 20.5
        assert WeatherConversionUtils.wh_per_m2_to_mj_per_m2(
            WeatherConversionUtils.mj_per_m2_to_wh_per_m2(mj)
        ) == pytest.approx(mj, rel=1e-3)

    def test_mph_ms_roundtrip(self):
        mph = 10.0
        assert WeatherConversionUtils.ms_to_mph(
            WeatherConversionUtils.mph_to_ms(mph)
        ) == pytest.approx(mph, rel=1e-3)
