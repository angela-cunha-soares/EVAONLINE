"""
Tests for weather_utils — WeatherConversionUtils, WeatherValidationUtils,
WeatherAggregationUtils, CacheUtils, METNorwayAggregationUtils, ElevationUtils.

All methods are @staticmethod / @classmethod — pure logic, no dependencies.
"""

import pytest
from datetime import datetime, timezone, timedelta

from backend.api.services.weather_utils import (
    WeatherConversionUtils,
    WeatherValidationUtils,
    WeatherAggregationUtils,
    CacheUtils,
    METNorwayAggregationUtils,
    ElevationUtils,
)


# ════════════════════════════════════════════════════════════════════
# WeatherConversionUtils
# ════════════════════════════════════════════════════════════════════

class TestWeatherConversionUtils:

    # --- Wind conversion ---
    def test_wind_10m_to_2m(self):
        assert WeatherConversionUtils.convert_wind_10m_to_2m(10.0) == pytest.approx(7.48, rel=1e-2)

    def test_wind_10m_to_2m_none(self):
        assert WeatherConversionUtils.convert_wind_10m_to_2m(None) is None

    def test_wind_10m_to_2m_zero(self):
        assert WeatherConversionUtils.convert_wind_10m_to_2m(0.0) == 0.0

    # --- Temperature conversions ---
    def test_fahrenheit_to_celsius_32f(self):
        assert WeatherConversionUtils.fahrenheit_to_celsius(32.0) == pytest.approx(0.0)

    def test_fahrenheit_to_celsius_212f(self):
        assert WeatherConversionUtils.fahrenheit_to_celsius(212.0) == pytest.approx(100.0)

    def test_fahrenheit_to_celsius_none(self):
        assert WeatherConversionUtils.fahrenheit_to_celsius(None) is None

    def test_celsius_to_fahrenheit_0c(self):
        assert WeatherConversionUtils.celsius_to_fahrenheit(0.0) == pytest.approx(32.0)

    def test_celsius_to_fahrenheit_100c(self):
        assert WeatherConversionUtils.celsius_to_fahrenheit(100.0) == pytest.approx(212.0)

    def test_celsius_to_fahrenheit_none(self):
        assert WeatherConversionUtils.celsius_to_fahrenheit(None) is None

    def test_roundtrip_temperature(self):
        for t in [-40, 0, 25, 37, 100]:
            f = WeatherConversionUtils.celsius_to_fahrenheit(float(t))
            c = WeatherConversionUtils.fahrenheit_to_celsius(f)
            assert c == pytest.approx(float(t), abs=0.01)

    # --- Speed conversions ---
    def test_mph_to_ms(self):
        assert WeatherConversionUtils.mph_to_ms(1.0) == pytest.approx(0.44704)

    def test_mph_to_ms_none(self):
        assert WeatherConversionUtils.mph_to_ms(None) is None

    def test_ms_to_mph(self):
        assert WeatherConversionUtils.ms_to_mph(1.0) == pytest.approx(2.23694)

    def test_ms_to_mph_none(self):
        assert WeatherConversionUtils.ms_to_mph(None) is None

    def test_roundtrip_speed(self):
        for s in [0, 1, 5, 10, 50]:
            ms = WeatherConversionUtils.mph_to_ms(float(s))
            mph = WeatherConversionUtils.ms_to_mph(ms)
            assert mph == pytest.approx(float(s), rel=1e-3)

    # --- Radiation conversions ---
    def test_wh_to_mj(self):
        assert WeatherConversionUtils.wh_per_m2_to_mj_per_m2(1000.0) == pytest.approx(3.6, rel=1e-2)

    def test_wh_to_mj_none(self):
        assert WeatherConversionUtils.wh_per_m2_to_mj_per_m2(None) is None

    def test_mj_to_wh(self):
        assert WeatherConversionUtils.mj_per_m2_to_wh_per_m2(1.0) == pytest.approx(277.778, rel=1e-2)

    def test_mj_to_wh_none(self):
        assert WeatherConversionUtils.mj_per_m2_to_wh_per_m2(None) is None

    def test_roundtrip_radiation(self):
        for val in [100, 500, 1000, 5000]:
            mj = WeatherConversionUtils.wh_per_m2_to_mj_per_m2(float(val))
            wh = WeatherConversionUtils.mj_per_m2_to_wh_per_m2(mj)
            assert wh == pytest.approx(float(val), rel=1e-2)


# ════════════════════════════════════════════════════════════════════
# WeatherValidationUtils
# ════════════════════════════════════════════════════════════════════

class TestWeatherValidationUtils:

    # --- Temperature validation ---
    def test_valid_temperature_global(self):
        assert WeatherValidationUtils.is_valid_temperature(25.0, region="global") is True

    def test_invalid_temperature_too_high(self):
        assert WeatherValidationUtils.is_valid_temperature(100.0, region="global") is False

    def test_temperature_none_valid(self):
        assert WeatherValidationUtils.is_valid_temperature(None) is True

    def test_valid_temperature_brazil(self):
        assert WeatherValidationUtils.is_valid_temperature(35.0, region="brazil") is True

    # --- Humidity validation ---
    def test_valid_humidity(self):
        assert WeatherValidationUtils.is_valid_humidity(65.0, region="global") is True

    def test_invalid_humidity_negative(self):
        assert WeatherValidationUtils.is_valid_humidity(-5.0, region="global") is False

    def test_invalid_humidity_above_100(self):
        assert WeatherValidationUtils.is_valid_humidity(110.0, region="global") is False

    def test_humidity_none_valid(self):
        assert WeatherValidationUtils.is_valid_humidity(None) is True

    # --- Wind speed validation ---
    def test_valid_wind(self):
        assert WeatherValidationUtils.is_valid_wind_speed(5.0, region="global") is True

    def test_invalid_wind_negative(self):
        assert WeatherValidationUtils.is_valid_wind_speed(-1.0, region="global") is False

    def test_wind_none_valid(self):
        assert WeatherValidationUtils.is_valid_wind_speed(None) is True

    # --- Precipitation validation ---
    def test_valid_precipitation(self):
        assert WeatherValidationUtils.is_valid_precipitation(10.0, region="global") is True

    def test_invalid_precipitation_negative(self):
        assert WeatherValidationUtils.is_valid_precipitation(-1.0, region="global") is False

    def test_precipitation_none_valid(self):
        assert WeatherValidationUtils.is_valid_precipitation(None) is True

    # --- Solar radiation validation ---
    def test_valid_solar(self):
        assert WeatherValidationUtils.is_valid_solar_radiation(20.0, region="global") is True

    def test_invalid_solar_negative(self):
        assert WeatherValidationUtils.is_valid_solar_radiation(-5.0, region="global") is False

    def test_solar_none_valid(self):
        assert WeatherValidationUtils.is_valid_solar_radiation(None) is True

    # --- get_validation_limits ---
    def test_get_limits_global(self):
        limits = WeatherValidationUtils.get_validation_limits(region="global")
        assert "temperature" in limits
        assert "humidity" in limits
        assert "wind" in limits
        assert "precipitation" in limits
        assert "solar" in limits

    def test_get_limits_brazil(self):
        limits = WeatherValidationUtils.get_validation_limits(region="brazil")
        assert limits["precipitation"][1] == 450.0

    def test_get_limits_auto_detect_brazil(self):
        limits = WeatherValidationUtils.get_validation_limits(lat=-23.5, lon=-46.6)
        # São Paulo should detect as brazil
        assert "temperature" in limits

    def test_get_limits_unknown_region_fallback(self):
        limits = WeatherValidationUtils.get_validation_limits(region="mars")
        # Should fallback to global
        assert "temperature" in limits

    # --- validate_daily_data ---
    def test_validate_all_valid(self):
        data = {
            "temp_max": 35.0,
            "temp_min": 20.0,
            "temp_mean": 27.5,
            "humidity_mean": 65.0,
            "wind_speed_2m_mean": 2.5,
            "precipitation_sum": 5.0,
            "solar_radiation": 20.0,
        }
        assert WeatherValidationUtils.validate_daily_data(data, region="global") is True

    def test_validate_empty_data(self):
        """Empty dict → all None → all True"""
        assert WeatherValidationUtils.validate_daily_data({}) is True

    def test_validate_partial_data(self):
        data = {"temp_max": 35.0}
        assert WeatherValidationUtils.validate_daily_data(data, region="global") is True

    def test_validate_invalid_temp(self):
        data = {"temp_max": 100.0}  # Invalid
        assert WeatherValidationUtils.validate_daily_data(data, region="global") is False


# ════════════════════════════════════════════════════════════════════
# WeatherAggregationUtils
# ════════════════════════════════════════════════════════════════════

class TestWeatherAggregationUtils:

    # --- aggregate_temperature ---
    def test_aggregate_temp_mean(self):
        result = WeatherAggregationUtils.aggregate_temperature([20, 22, 24], "mean")
        assert result == pytest.approx(22.0)

    def test_aggregate_temp_max(self):
        result = WeatherAggregationUtils.aggregate_temperature([20, 22, 24], "max")
        assert result == 24.0

    def test_aggregate_temp_min(self):
        result = WeatherAggregationUtils.aggregate_temperature([20, 22, 24], "min")
        assert result == 20.0

    def test_aggregate_temp_empty(self):
        assert WeatherAggregationUtils.aggregate_temperature([]) is None

    def test_aggregate_temp_with_nones(self):
        result = WeatherAggregationUtils.aggregate_temperature([20, None, 24], "mean")
        assert result == pytest.approx(22.0)

    def test_aggregate_temp_all_nones(self):
        assert WeatherAggregationUtils.aggregate_temperature([None, None]) is None

    def test_aggregate_temp_unknown_method(self):
        """Unknown method falls back to mean"""
        result = WeatherAggregationUtils.aggregate_temperature([20, 22, 24], "median")
        assert result == pytest.approx(22.0)

    # --- aggregate_precipitation ---
    def test_aggregate_precip_sum(self):
        result = WeatherAggregationUtils.aggregate_precipitation([1.5, 2.0, 0.5])
        assert result == pytest.approx(4.0)

    def test_aggregate_precip_empty(self):
        assert WeatherAggregationUtils.aggregate_precipitation([]) is None

    def test_aggregate_precip_with_nones(self):
        result = WeatherAggregationUtils.aggregate_precipitation([1.0, None, 3.0])
        assert result == pytest.approx(4.0)

    def test_aggregate_precip_all_nones(self):
        assert WeatherAggregationUtils.aggregate_precipitation([None, None]) is None

    # --- safe_division ---
    def test_safe_division_normal(self):
        assert WeatherAggregationUtils.safe_division(10, 2) == 5.0

    def test_safe_division_by_zero(self):
        assert WeatherAggregationUtils.safe_division(10, 0) is None

    def test_safe_division_none_numerator(self):
        assert WeatherAggregationUtils.safe_division(None, 5) is None

    def test_safe_division_none_denominator(self):
        assert WeatherAggregationUtils.safe_division(10, None) is None

    def test_safe_division_both_none(self):
        assert WeatherAggregationUtils.safe_division(None, None) is None

    # --- parse_rfc1123_date ---
    def test_parse_rfc1123_valid(self):
        dt = WeatherAggregationUtils.parse_rfc1123_date("Tue, 16 Jun 2020 12:13:49 GMT")
        assert dt is not None
        assert dt.year == 2020
        assert dt.month == 6
        assert dt.day == 16
        assert dt.tzinfo is not None

    def test_parse_rfc1123_none(self):
        assert WeatherAggregationUtils.parse_rfc1123_date(None) is None

    def test_parse_rfc1123_empty(self):
        assert WeatherAggregationUtils.parse_rfc1123_date("") is None

    def test_parse_rfc1123_invalid(self):
        assert WeatherAggregationUtils.parse_rfc1123_date("not-a-date") is None

    # --- calculate_cache_ttl ---
    def test_cache_ttl_valid_future(self):
        expires = datetime.now(timezone.utc) + timedelta(hours=2)
        ttl = WeatherAggregationUtils.calculate_cache_ttl(expires)
        assert 7100 <= ttl <= 7300  # ~7200 seconds

    def test_cache_ttl_none_default(self):
        assert WeatherAggregationUtils.calculate_cache_ttl(None) == 3600

    def test_cache_ttl_none_custom_default(self):
        assert WeatherAggregationUtils.calculate_cache_ttl(None, default_ttl=1800) == 1800

    def test_cache_ttl_past_min(self):
        """Expired → minimum 60s"""
        expires = datetime.now(timezone.utc) - timedelta(hours=1)
        ttl = WeatherAggregationUtils.calculate_cache_ttl(expires)
        assert ttl == 60

    def test_cache_ttl_far_future_max(self):
        """Very far future → capped at 86400s"""
        expires = datetime.now(timezone.utc) + timedelta(days=30)
        ttl = WeatherAggregationUtils.calculate_cache_ttl(expires)
        assert ttl == 86400

    # --- aggregate_hourly_to_daily ---
    def test_aggregate_hourly_basic(self):
        start = datetime(2024, 1, 15, tzinfo=timezone.utc)
        end = datetime(2024, 1, 15, 23, 59, 59, tzinfo=timezone.utc)
        timeseries = [
            {"time": "2024-01-15T12:00:00Z", "air_temperature": 20.5},
            {"time": "2024-01-15T13:00:00Z", "air_temperature": 21.0},
        ]
        result = WeatherAggregationUtils.aggregate_hourly_to_daily(
            timeseries, start, end,
            field_mapping={"air_temperature": "temperature_2m"},
        )
        assert "2024-01-15" in result
        assert len(result["2024-01-15"]) == 2

    def test_aggregate_hourly_empty(self):
        start = datetime(2024, 1, 15, tzinfo=timezone.utc)
        end = datetime(2024, 1, 15, 23, 59, 59, tzinfo=timezone.utc)
        result = WeatherAggregationUtils.aggregate_hourly_to_daily(
            [], start, end, field_mapping={}
        )
        assert result == {}

    def test_aggregate_hourly_filter_dates(self):
        """Entries outside range should be excluded"""
        start = datetime(2024, 1, 15, tzinfo=timezone.utc)
        end = datetime(2024, 1, 15, 23, 59, 59, tzinfo=timezone.utc)
        timeseries = [
            {"time": "2024-01-14T12:00:00Z", "air_temperature": 20.0},  # before
            {"time": "2024-01-15T12:00:00Z", "air_temperature": 21.0},  # in range
            {"time": "2024-01-16T12:00:00Z", "air_temperature": 22.0},  # after
        ]
        result = WeatherAggregationUtils.aggregate_hourly_to_daily(
            timeseries, start, end,
            field_mapping={"air_temperature": "temperature_2m"},
        )
        assert "2024-01-15" in result
        assert len(result) == 1


# ════════════════════════════════════════════════════════════════════
# CacheUtils
# ════════════════════════════════════════════════════════════════════

class TestCacheUtils:

    def test_parse_rfc1123_valid(self):
        dt = CacheUtils.parse_rfc1123_date("Tue, 16 Jun 2020 12:13:49 GMT")
        assert dt is not None
        assert dt.year == 2020
        assert dt.tzinfo == timezone.utc

    def test_parse_rfc1123_none(self):
        assert CacheUtils.parse_rfc1123_date(None) is None

    def test_parse_rfc1123_invalid(self):
        assert CacheUtils.parse_rfc1123_date("invalid") is None

    def test_cache_ttl_valid(self):
        expires = datetime.now(timezone.utc) + timedelta(hours=1)
        ttl = CacheUtils.calculate_cache_ttl(expires)
        assert 3500 <= ttl <= 3700

    def test_cache_ttl_expired(self):
        expires = datetime.now(timezone.utc) - timedelta(hours=1)
        ttl = CacheUtils.calculate_cache_ttl(expires)
        assert ttl == 60  # Minimum

    def test_cache_ttl_none(self):
        assert CacheUtils.calculate_cache_ttl(None) == 3600

    def test_cache_ttl_far_future(self):
        expires = datetime.now(timezone.utc) + timedelta(days=30)
        ttl = CacheUtils.calculate_cache_ttl(expires)
        assert ttl == 86400


# ════════════════════════════════════════════════════════════════════
# METNorwayAggregationUtils
# ════════════════════════════════════════════════════════════════════

class TestMETNorwayAggregationUtils:

    def test_aggregate_hourly_basic(self):
        start = datetime(2024, 1, 15, tzinfo=timezone.utc)
        end = datetime(2024, 1, 15, 23, 59, 59, tzinfo=timezone.utc)
        timeseries = [
            {
                "time": "2024-01-15T12:00:00Z",
                "data": {
                    "instant": {"details": {
                        "air_temperature": 5.0,
                        "relative_humidity": 80.0,
                        "wind_speed": 4.0,
                    }},
                    "next_1_hours": {"details": {"precipitation_amount": 0.5}},
                },
            },
            {
                "time": "2024-01-15T13:00:00Z",
                "data": {
                    "instant": {"details": {
                        "air_temperature": 6.0,
                        "relative_humidity": 75.0,
                        "wind_speed": 3.5,
                    }},
                    "next_1_hours": {"details": {"precipitation_amount": 0.0}},
                },
            },
        ]
        result = METNorwayAggregationUtils.aggregate_hourly_to_daily(
            timeseries, start, end
        )
        from datetime import date
        key = date(2024, 1, 15)
        assert key in result
        assert len(result[key]["temp_values"]) == 2
        assert result[key]["temp_values"] == [5.0, 6.0]
        assert result[key]["precipitation_1h"] == [0.5, 0.0]
        assert result[key]["count"] == 2

    def test_aggregate_hourly_empty(self):
        start = datetime(2024, 1, 15, tzinfo=timezone.utc)
        end = datetime(2024, 1, 15, 23, 59, 59, tzinfo=timezone.utc)
        result = METNorwayAggregationUtils.aggregate_hourly_to_daily([], start, end)
        assert result == {}

    def test_calculate_daily_aggregations(self):
        from datetime import date
        daily_raw = {
            date(2024, 1, 15): {
                "temp_values": [5.0, 6.0, 4.0, 7.0],
                "humidity_values": [80.0, 75.0, 85.0, 70.0],
                "wind_speed_values": [4.0, 3.5, 5.0, 4.5],
                "precipitation_1h": [0.5, 0.0, 1.0, 0.0],
                "precipitation_6h": [],
                "temp_max_6h": [7.5],
                "temp_min_6h": [3.5],
                "count": 4,
            }
        }
        result = METNorwayAggregationUtils.calculate_daily_aggregations(
            daily_raw, WeatherConversionUtils()
        )
        assert len(result) == 1
        record = result[0]
        assert record["date"] == date(2024, 1, 15)
        assert record["temp_mean"] == pytest.approx(5.5)
        assert record["temp_max"] == 7.5  # From 6h
        assert record["temp_min"] == 3.5  # From 6h
        assert record["precipitation_sum"] == pytest.approx(1.5)
        # Wind converted from 10m to 2m
        assert record["wind_speed_2m_mean"] is not None

    def test_validate_daily_data_valid(self):
        data = [
            {"date": "2024-01-15", "temp_max": 7.0, "temp_min": 3.0,
             "humidity_mean": 75.0, "precipitation_sum": 1.5},
        ]
        assert METNorwayAggregationUtils.validate_daily_data(data) is True

    def test_validate_daily_data_empty(self):
        assert METNorwayAggregationUtils.validate_daily_data([]) is False

    def test_validate_daily_data_temp_inconsistent(self):
        data = [
            {"date": "2024-01-15", "temp_max": 3.0, "temp_min": 7.0},  # max < min
        ]
        assert METNorwayAggregationUtils.validate_daily_data(data) is False

    def test_validate_daily_data_negative_precip(self):
        data = [
            {"date": "2024-01-15", "precipitation_sum": -1.0},
        ]
        assert METNorwayAggregationUtils.validate_daily_data(data) is False

    def test_validate_daily_data_humidity_out_of_range(self):
        data = [
            {"date": "2024-01-15", "humidity_mean": 120.0},
        ]
        assert METNorwayAggregationUtils.validate_daily_data(data) is False


# ════════════════════════════════════════════════════════════════════
# ElevationUtils
# ════════════════════════════════════════════════════════════════════

class TestElevationUtils:

    # --- calculate_atmospheric_pressure ---
    def test_pressure_sea_level(self):
        """Sea level → ~101.3 kPa"""
        result = ElevationUtils.calculate_atmospheric_pressure(0)
        assert abs(result - 101.3) < 0.1

    def test_pressure_brasilia(self):
        """Brasília (1172m) → ~87.8 kPa (FAO-56 example)"""
        result = ElevationUtils.calculate_atmospheric_pressure(1172)
        assert abs(result - 87.8) < 1.0

    def test_pressure_la_paz(self):
        """La Paz (3640m) → ~65.5 kPa"""
        result = ElevationUtils.calculate_atmospheric_pressure(3640)
        assert abs(result - 65.5) < 2.0

    def test_pressure_decreases_with_altitude(self):
        elevations = [0, 500, 1000, 2000, 3000]
        pressures = [
            ElevationUtils.calculate_atmospheric_pressure(z) for z in elevations
        ]
        for i in range(1, len(pressures)):
            assert pressures[i] < pressures[i - 1]

    def test_pressure_invalid_elevation(self):
        with pytest.raises(ValueError, match="too low"):
            ElevationUtils.calculate_atmospheric_pressure(-2000)

    def test_pressure_dead_sea(self):
        """Dead Sea (-430m) should work"""
        result = ElevationUtils.calculate_atmospheric_pressure(-430)
        assert result > 101.3  # Higher than sea level

    # --- calculate_psychrometric_constant ---
    def test_gamma_sea_level(self):
        """Sea level → γ ≈ 0.0674 kPa/°C"""
        result = ElevationUtils.calculate_psychrometric_constant(0)
        assert abs(result - 0.0674) < 0.002

    def test_gamma_brasilia(self):
        """Brasília (1172m) → γ ≈ 0.0584 kPa/°C"""
        result = ElevationUtils.calculate_psychrometric_constant(1172)
        assert abs(result - 0.0584) < 0.003

    def test_gamma_decreases_with_altitude(self):
        elevations = [0, 500, 1000, 2000]
        gammas = [
            ElevationUtils.calculate_psychrometric_constant(z) for z in elevations
        ]
        for i in range(1, len(gammas)):
            assert gammas[i] < gammas[i - 1]

    # --- adjust_solar_radiation_for_elevation ---
    def test_solar_adjustment_sea_level(self):
        """Sea level → no adjustment"""
        result = ElevationUtils.adjust_solar_radiation_for_elevation(20.0, 0)
        assert result == pytest.approx(20.0)

    def test_solar_adjustment_1000m(self):
        """1000m → +10%"""
        result = ElevationUtils.adjust_solar_radiation_for_elevation(20.0, 1000)
        assert result == pytest.approx(22.0)

    def test_solar_adjustment_2000m(self):
        """2000m → +20%"""
        result = ElevationUtils.adjust_solar_radiation_for_elevation(20.0, 2000)
        assert result == pytest.approx(24.0)

    # --- get_elevation_correction_factor ---
    def test_correction_factor_complete(self):
        result = ElevationUtils.get_elevation_correction_factor(580)
        assert "pressure" in result
        assert "gamma" in result
        assert "solar_factor" in result
        assert "elevation" in result
        assert result["elevation"] == 580

    def test_correction_factor_sea_level(self):
        result = ElevationUtils.get_elevation_correction_factor(0)
        assert result["pressure"] == pytest.approx(101.3, rel=0.01)
        assert result["solar_factor"] == pytest.approx(1.0)

    def test_correction_factor_high_altitude(self):
        result = ElevationUtils.get_elevation_correction_factor(3000)
        assert result["pressure"] < 80  # Much lower than sea level
        assert result["solar_factor"] > 1.2

    # --- compare_elevation_impact ---
    def test_compare_elevation_small_diff(self):
        result = ElevationUtils.compare_elevation_impact(580, 575)
        assert result["elevation_diff_m"] == 5.0
        assert result["recommendation"] == "Negligenciável"
        assert result["eto_impact_pct"] < 0.1

    def test_compare_elevation_medium_diff(self):
        result = ElevationUtils.compare_elevation_impact(1172, 1150)
        assert result["elevation_diff_m"] == 22.0
        assert result["recommendation"] == "Pequeno"

    def test_compare_elevation_large_diff(self):
        result = ElevationUtils.compare_elevation_impact(1172, 1072)
        assert result["elevation_diff_m"] == 100.0
        assert result["recommendation"] in ["Significativo", "Crítico"]

    def test_compare_elevation_critical_diff(self):
        result = ElevationUtils.compare_elevation_impact(1172, 900)
        assert result["elevation_diff_m"] > 100
        assert result["recommendation"] == "Crítico"

    def test_compare_elevation_same(self):
        result = ElevationUtils.compare_elevation_impact(500, 500)
        assert result["elevation_diff_m"] == 0.0
        assert result["eto_impact_pct"] == 0.0
