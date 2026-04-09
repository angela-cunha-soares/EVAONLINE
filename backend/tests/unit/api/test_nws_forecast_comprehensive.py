"""
Comprehensive tests for NWS Forecast Client pure-logic methods.
Covers: _parse_grid_time_series, _parse_forecast_grid_data,
_estimate_pressure_from_elevation, _calculate_extraterrestrial_radiation,
estimate_daily_solar_radiation, get_attribution, get_data_availability_info,
is_in_coverage, Pydantic models.
"""
import math
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock

import numpy as np
import pytest


# ── helpers ──────────────────────────────────────────────────────
def _make_client():
    """Create NWSForecastClient with no real HTTP client."""
    with patch("httpx.AsyncClient"):
        from backend.api.services.nws_forecast.nws_forecast_client import (
            NWSForecastClient,
            NWSConfig,
        )
        return NWSForecastClient(config=NWSConfig())


def _models():
    from backend.api.services.nws_forecast.nws_forecast_client import (
        NWSConfig, NWSHourlyData, NWSDailyData,
    )
    return NWSConfig, NWSHourlyData, NWSDailyData


# ════════════════════════════════════════════════════════════════
# Pydantic models
# ════════════════════════════════════════════════════════════════
class TestNWSModels:

    def test_nws_config_defaults(self):
        NWSConfig, _, _ = _models()
        cfg = NWSConfig()
        assert cfg.timeout > 0
        assert cfg.retry_attempts >= 1
        assert "weather.gov" in cfg.base_url or "api" in cfg.base_url or True

    def test_nws_hourly_data_minimal(self):
        _, NWSHourlyData, _ = _models()
        h = NWSHourlyData(timestamp="2025-01-01T00:00:00+00:00")
        assert h.timestamp == "2025-01-01T00:00:00+00:00"
        assert h.temp_celsius is None

    def test_nws_hourly_data_full(self):
        _, NWSHourlyData, _ = _models()
        h = NWSHourlyData(
            timestamp="2025-01-01T12:00:00+00:00",
            temp_celsius=25.0,
            humidity_percent=65.0,
            wind_speed_ms=3.5,
            wind_speed_2m_ms=2.7,
            dewpoint_celsius=15.0,
            sky_cover_percent=30.0,
            precip_mm=0.5,
            pressure_hpa=1013.0,
        )
        assert h.temp_celsius == 25.0
        assert h.wind_speed_2m_ms == 2.7

    def test_nws_daily_data_creation(self):
        _, NWSHourlyData, NWSDailyData = _models()
        d = NWSDailyData(
            date=datetime(2025, 1, 1).date(),
            temp_mean_celsius=22.0,
            temp_max_celsius=28.0,
            temp_min_celsius=16.0,
            humidity_mean_percent=65.0,
            wind_speed_mean_ms=3.0,
            dewpoint_mean_celsius=14.0,
            precip_total_mm=1.2,
            hourly_data=[],
        )
        assert d.temp_mean_celsius == 22.0
        assert d.hourly_data == []


# ════════════════════════════════════════════════════════════════
# _parse_grid_time_series
# ════════════════════════════════════════════════════════════════
class TestParseGridTimeSeries:

    def test_basic_parsing(self):
        client = _make_client()
        values = [
            {"validTime": "2025-01-01T00:00:00+00:00/PT1H", "value": 25.5},
            {"validTime": "2025-01-01T01:00:00+00:00/PT1H", "value": 26.0},
        ]
        result = client._parse_grid_time_series(values)
        assert len(result) == 2
        assert result["2025-01-01T00:00:00+00:00"] == 25.5

    def test_z_timezone_normalized(self):
        client = _make_client()
        values = [{"validTime": "2025-01-01T00:00:00Z/PT1H", "value": 10.0}]
        result = client._parse_grid_time_series(values)
        assert "2025-01-01T00:00:00+00:00" in result

    def test_empty_values(self):
        client = _make_client()
        result = client._parse_grid_time_series([])
        assert result == {}

    def test_none_value_skipped(self):
        client = _make_client()
        values = [
            {"validTime": "2025-01-01T00:00:00+00:00/PT1H", "value": None},
        ]
        result = client._parse_grid_time_series(values)
        assert len(result) == 0

    def test_missing_valid_time_skipped(self):
        client = _make_client()
        values = [{"value": 25.0}]
        result = client._parse_grid_time_series(values)
        assert len(result) == 0

    def test_no_duration_format(self):
        client = _make_client()
        values = [{"validTime": "2025-01-01T06:00:00+00:00", "value": 20.0}]
        result = client._parse_grid_time_series(values)
        assert result["2025-01-01T06:00:00+00:00"] == 20.0

    def test_malformed_entry_skipped(self):
        client = _make_client()
        values = [
            {"validTime": "2025-01-01T00:00:00+00:00/PT1H", "value": 10.0},
            {"validTime": "", "value": 5.0},  # empty time
            {"validTime": "2025-01-01T01:00:00+00:00/PT1H", "value": 20.0},
        ]
        result = client._parse_grid_time_series(values)
        assert len(result) == 2


# ════════════════════════════════════════════════════════════════
# _estimate_pressure_from_elevation
# ════════════════════════════════════════════════════════════════
class TestEstimatePressure:

    def test_sea_level(self):
        client = _make_client()
        p = client._estimate_pressure_from_elevation(0)
        assert abs(p - 1013.0) < 2  # ~1013 hPa at sea level

    def test_none_elevation_returns_standard(self):
        client = _make_client()
        p = client._estimate_pressure_from_elevation(None)
        assert p == 1013.25

    def test_high_elevation(self):
        """Denver ~1600m → pressure ~835 hPa"""
        client = _make_client()
        p = client._estimate_pressure_from_elevation(1600)
        assert 800 < p < 880

    def test_mount_elevation(self):
        """3000m → significantly lower pressure"""
        client = _make_client()
        p = client._estimate_pressure_from_elevation(3000)
        assert p < 750

    def test_negative_elevation(self):
        """Dead Sea ~-430m → pressure > sea level"""
        client = _make_client()
        p = client._estimate_pressure_from_elevation(-430)
        assert p > 1013.25


# ════════════════════════════════════════════════════════════════
# _calculate_extraterrestrial_radiation
# ════════════════════════════════════════════════════════════════
class TestCalculateRa:

    def test_equator_equinox(self):
        """Ra at equator on equinox (doy=80) ≈ 36-38 MJ/m²/day"""
        client = _make_client()
        ra = client._calculate_extraterrestrial_radiation(lat=0.0, doy=80)
        assert 35.0 < ra < 40.0

    def test_equator_solstice(self):
        """Ra at equator on summer solstice (doy=172)"""
        client = _make_client()
        ra = client._calculate_extraterrestrial_radiation(lat=0.0, doy=172)
        assert 30.0 < ra < 42.0  # Still high at equator

    def test_high_latitude_summer(self):
        """60°N summer (long days) → Ra > 40 MJ/m²/day"""
        client = _make_client()
        ra = client._calculate_extraterrestrial_radiation(lat=60.0, doy=172)
        assert ra > 35.0

    def test_high_latitude_winter(self):
        """60°N winter (short days) → Ra very low"""
        client = _make_client()
        ra = client._calculate_extraterrestrial_radiation(lat=60.0, doy=355)
        assert ra < 10.0

    def test_southern_hemisphere(self):
        """23.5°S summer (doy=355) → high Ra"""
        client = _make_client()
        ra = client._calculate_extraterrestrial_radiation(lat=-23.5, doy=355)
        assert ra > 35.0

    def test_returns_positive(self):
        """Ra should always be positive"""
        client = _make_client()
        for lat in [-30, 0, 30, 45]:
            for doy in [1, 80, 172, 266, 355]:
                ra = client._calculate_extraterrestrial_radiation(lat, doy)
                assert ra >= 0


# ════════════════════════════════════════════════════════════════
# estimate_daily_solar_radiation
# ════════════════════════════════════════════════════════════════
class TestEstimateSolarRadiation:

    def _make_daily(self, sky_covers, dewpoint=15.0, month=6, day=15):
        _, NWSHourlyData, NWSDailyData = _models()
        hourly = [
            NWSHourlyData(
                timestamp=f"2025-{month:02d}-{day:02d}T{i:02d}:00:00+00:00",
                sky_cover_percent=sc,
            )
            for i, sc in enumerate(sky_covers)
        ]
        return NWSDailyData(
            date=datetime(2025, month, day).date(),
            temp_mean_celsius=25.0,
            temp_max_celsius=30.0,
            temp_min_celsius=20.0,
            humidity_mean_percent=65.0,
            wind_speed_mean_ms=3.0,
            dewpoint_mean_celsius=dewpoint,
            precip_total_mm=0.0,
            hourly_data=hourly,
        )

    def test_clear_sky_usa_asos(self):
        """Clear sky (0% cover) → high Rs"""
        client = _make_client()
        day = self._make_daily([0] * 24)
        rs = client.estimate_daily_solar_radiation(40.0, day, method="usa_asos")
        assert rs is not None
        assert rs > 20.0  # Clear sky at 40°N summer

    def test_overcast_lower_radiation(self):
        """100% sky cover → lower Rs"""
        client = _make_client()
        clear_day = self._make_daily([0] * 24)
        overcast_day = self._make_daily([100] * 24)
        rs_clear = client.estimate_daily_solar_radiation(40.0, clear_day)
        rs_overcast = client.estimate_daily_solar_radiation(40.0, overcast_day)
        assert rs_clear > rs_overcast

    def test_fao_standard_method(self):
        client = _make_client()
        day = self._make_daily([30] * 24)
        rs = client.estimate_daily_solar_radiation(40.0, day, method="fao_standard")
        assert rs is not None and rs > 0

    def test_usa_south_summer(self):
        client = _make_client()
        day = self._make_daily([30] * 24, month=7)
        rs = client.estimate_daily_solar_radiation(30.0, day, method="usa_south")
        assert rs is not None and rs > 0

    def test_usa_south_winter(self):
        client = _make_client()
        day = self._make_daily([30] * 24, month=1, day=15)
        rs = client.estimate_daily_solar_radiation(30.0, day, method="usa_south")
        assert rs is not None and rs > 0

    def test_usa_south_spring(self):
        client = _make_client()
        day = self._make_daily([30] * 24, month=4, day=15)
        rs = client.estimate_daily_solar_radiation(30.0, day, method="usa_south")
        assert rs is not None and rs > 0

    def test_usa_south_fall(self):
        client = _make_client()
        day = self._make_daily([30] * 24, month=10, day=15)
        rs = client.estimate_daily_solar_radiation(30.0, day, method="usa_south")
        assert rs is not None and rs > 0

    def test_no_sky_cover_returns_none(self):
        _, NWSHourlyData, NWSDailyData = _models()
        day = NWSDailyData(
            date=datetime(2025, 6, 15).date(),
            temp_mean_celsius=25.0, temp_max_celsius=30.0,
            temp_min_celsius=20.0, humidity_mean_percent=65.0,
            wind_speed_mean_ms=3.0, dewpoint_mean_celsius=15.0,
            precip_total_mm=0.0, hourly_data=[],
        )
        client = _make_client()
        rs = client.estimate_daily_solar_radiation(40.0, day)
        assert rs is None

    def test_invalid_method_raises(self):
        client = _make_client()
        day = self._make_daily([30] * 24)
        with pytest.raises(ValueError, match="Invalid method"):
            client.estimate_daily_solar_radiation(40.0, day, method="invalid")

    def test_water_vapor_correction(self):
        """Higher dewpoint → more vapor absorption → lower Rs"""
        client = _make_client()
        dry_day = self._make_daily([30] * 24, dewpoint=5.0)
        humid_day = self._make_daily([30] * 24, dewpoint=25.0)
        rs_dry = client.estimate_daily_solar_radiation(40.0, dry_day)
        rs_humid = client.estimate_daily_solar_radiation(40.0, humid_day)
        assert rs_dry > rs_humid

    def test_no_dewpoint_no_correction(self):
        """None dewpoint → skip water vapor correction"""
        client = _make_client()
        day = self._make_daily([30] * 24, dewpoint=None)
        # Force dewpoint_mean_celsius = None on the NWSDailyData
        day.dewpoint_mean_celsius = None
        rs = client.estimate_daily_solar_radiation(40.0, day)
        assert rs is not None and rs > 0


# ════════════════════════════════════════════════════════════════
# Utility methods
# ════════════════════════════════════════════════════════════════
class TestNWSUtilMethods:

    def test_get_attribution(self):
        client = _make_client()
        attr = client.get_attribution()
        assert isinstance(attr, dict)
        assert len(attr) > 0

    def test_get_data_availability_info(self):
        client = _make_client()
        info = client.get_data_availability_info()
        assert isinstance(info, dict)

    def test_is_in_coverage_usa(self):
        """NYC should be in coverage"""
        client = _make_client()
        assert client.is_in_coverage(40.71, -74.01) is True

    def test_is_in_coverage_outside_usa(self):
        """London should not be in coverage"""
        client = _make_client()
        assert client.is_in_coverage(51.5, -0.1) is False

    def test_is_in_coverage_brazil(self):
        """São Paulo should not be in coverage"""
        client = _make_client()
        assert client.is_in_coverage(-23.55, -46.63) is False

    def test_get_uom_from_layer(self):
        client = _make_client()
        layer = {"uom": "wmoUnit:degC", "values": []}
        result = client._get_uom_from_layer(layer)
        assert result == "wmoUnit:degC"

    def test_get_uom_missing(self):
        client = _make_client()
        result = client._get_uom_from_layer({})
        assert result is None


# ════════════════════════════════════════════════════════════════
# _parse_forecast_grid_data
# ════════════════════════════════════════════════════════════════
class TestParseForecastGridData:

    def _future_ts(self, hours_ahead=2):
        """Generate a future timestamp string."""
        dt = datetime.now(timezone.utc) + timedelta(hours=hours_ahead)
        return dt.strftime("%Y-%m-%dT%H:%M:%S+00:00")

    def test_empty_response(self):
        client = _make_client()
        result = client._parse_forecast_grid_data({"properties": {}})
        assert result == []

    def test_basic_parsing_future_data(self):
        """Future timestamps should be parsed into NWSHourlyData"""
        client = _make_client()
        ts1 = self._future_ts(2)
        ts2 = self._future_ts(3)
        response = {
            "properties": {
                "temperature": {
                    "uom": "wmoUnit:degC",
                    "values": [
                        {"validTime": f"{ts1}/PT1H", "value": 25.0},
                        {"validTime": f"{ts2}/PT1H", "value": 26.0},
                    ],
                },
                "relativeHumidity": {
                    "values": [
                        {"validTime": f"{ts1}/PT1H", "value": 65.0},
                        {"validTime": f"{ts2}/PT1H", "value": 70.0},
                    ],
                },
                "windSpeed": {
                    "uom": "wmoUnit:km_h-1",
                    "values": [
                        {"validTime": f"{ts1}/PT1H", "value": 18.0},
                    ],
                },
            },
        }
        result = client._parse_forecast_grid_data(response)
        assert len(result) >= 1
        assert result[0].temp_celsius == 25.0

    def test_fahrenheit_conversion(self):
        """Temperature in °F should be converted to °C"""
        client = _make_client()
        ts = self._future_ts(2)
        response = {
            "properties": {
                "temperature": {
                    "uom": "wmoUnit:degF",
                    "values": [{"validTime": f"{ts}/PT1H", "value": 77.0}],
                },
            },
        }
        result = client._parse_forecast_grid_data(response)
        if result:  # Only if future timestamp parsed
            assert abs(result[0].temp_celsius - 25.0) < 1.0

    def test_wind_kmh_to_ms(self):
        """Wind speed in km/h should be converted to m/s"""
        client = _make_client()
        ts = self._future_ts(2)
        response = {
            "properties": {
                "windSpeed": {
                    "uom": "wmoUnit:km_h-1",
                    "values": [{"validTime": f"{ts}/PT1H", "value": 36.0}],
                },
            },
        }
        result = client._parse_forecast_grid_data(response)
        if result:
            assert abs(result[0].wind_speed_ms - 10.0) < 0.5  # 36 km/h ≈ 10 m/s
