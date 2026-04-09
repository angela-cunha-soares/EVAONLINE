"""
Phase 4 Tests: Pure Functions Across API Clients.

Tests pure computation methods that require zero mocking:
- NWS Forecast Client: parse_grid_time_series, pressure estimation, Ra, Rs, attribution
- MET Norway Client: round_coordinates, is_in_nordic, recommended_variables, attribution, coverage
- NWS Stations Client: _val, _extract_wind_speed_ms, convert_wind_to_2m, aggregate_to_daily, availability
- OpenMeteo Archive Client: _validate_inputs, _get_cache_key, get_info
- OpenMeteo Forecast Client: convert_wind_10m_to_2m, _validate_inputs, _get_cache_key, get_info, _get_ttl
"""

from datetime import datetime, timedelta
from unittest.mock import patch

import numpy as np
import pytest


# ============================================================================
# NWS Forecast Client Pure Functions
# ============================================================================

class TestNWSForecastPureFunctions:
    """Tests for pure methods in NWSForecastClient."""

    @pytest.fixture
    def client(self):
        with patch("httpx.AsyncClient"):
            from backend.api.services.nws_forecast.nws_forecast_client import (
                NWSForecastClient,
            )
            return NWSForecastClient()

    # --- _parse_grid_time_series ---

    def test_parse_grid_time_series_basic(self, client):
        values = [
            {"validTime": "2025-11-28T00:00:00+00:00/PT1H", "value": 25.5},
            {"validTime": "2025-11-28T01:00:00+00:00/PT1H", "value": 24.0},
        ]
        result = client._parse_grid_time_series(values)
        assert len(result) == 2
        assert result["2025-11-28T00:00:00+00:00"] == 25.5
        assert result["2025-11-28T01:00:00+00:00"] == 24.0

    def test_parse_grid_time_series_z_timezone(self, client):
        values = [
            {"validTime": "2025-11-28T00:00:00Z/PT1H", "value": 10.0},
        ]
        result = client._parse_grid_time_series(values)
        assert "2025-11-28T00:00:00+00:00" in result
        assert result["2025-11-28T00:00:00+00:00"] == 10.0

    def test_parse_grid_time_series_no_duration(self, client):
        values = [
            {"validTime": "2025-11-28T00:00:00+00:00", "value": 15.0},
        ]
        result = client._parse_grid_time_series(values)
        assert result["2025-11-28T00:00:00+00:00"] == 15.0

    def test_parse_grid_time_series_skips_null_value(self, client):
        values = [
            {"validTime": "2025-11-28T00:00:00+00:00/PT1H", "value": None},
            {"validTime": "2025-11-28T01:00:00+00:00/PT1H", "value": 20.0},
        ]
        result = client._parse_grid_time_series(values)
        assert len(result) == 1

    def test_parse_grid_time_series_skips_empty_time(self, client):
        values = [
            {"validTime": "", "value": 5.0},
            {"validTime": "2025-11-28T01:00:00+00:00/PT1H", "value": 20.0},
        ]
        result = client._parse_grid_time_series(values)
        assert len(result) == 1

    def test_parse_grid_time_series_empty_input(self, client):
        result = client._parse_grid_time_series([])
        assert result == {}

    # --- _get_uom_from_layer ---

    def test_get_uom_from_layer_valid(self, client):
        layer = {"uom": "wmoUnit:degC", "values": []}
        assert client._get_uom_from_layer(layer) == "wmoUnit:degC"

    def test_get_uom_from_layer_none(self, client):
        assert client._get_uom_from_layer(None) is None

    def test_get_uom_from_layer_missing_key(self, client):
        assert client._get_uom_from_layer({"values": []}) is None

    # --- _estimate_pressure_from_elevation ---

    def test_pressure_sea_level(self, client):
        assert client._estimate_pressure_from_elevation(None) == 1013.25

    def test_pressure_at_zero_elevation(self, client):
        p = client._estimate_pressure_from_elevation(0)
        assert abs(p - 1013.0) < 2  # Very close to sea level

    def test_pressure_at_1000m(self, client):
        p = client._estimate_pressure_from_elevation(1000)
        assert 880 < p < 910  # ~899 hPa

    def test_pressure_at_denver(self, client):
        # Denver ~1609m, expected ~835 hPa
        p = client._estimate_pressure_from_elevation(1609)
        assert 820 < p < 850

    def test_pressure_at_high_altitude(self, client):
        p = client._estimate_pressure_from_elevation(3000)
        assert 680 < p < 730

    # --- _calculate_extraterrestrial_radiation ---

    def test_ra_summer_solstice_equator(self, client):
        ra = client._calculate_extraterrestrial_radiation(0.0, 172)
        assert 30 < ra < 45  # MJ/m2/day at equator

    def test_ra_winter_solstice_45n(self, client):
        ra = client._calculate_extraterrestrial_radiation(45.0, 355)
        assert 10 < ra < 25

    def test_ra_returns_positive(self, client):
        ra = client._calculate_extraterrestrial_radiation(30.0, 1)
        assert ra > 0

    def test_ra_returns_float(self, client):
        ra = client._calculate_extraterrestrial_radiation(40.0, 100)
        assert isinstance(ra, float)

    def test_ra_higher_in_summer(self, client):
        ra_summer = client._calculate_extraterrestrial_radiation(40.0, 172)
        ra_winter = client._calculate_extraterrestrial_radiation(40.0, 355)
        assert ra_summer > ra_winter

    # --- estimate_daily_solar_radiation ---

    def test_solar_radiation_with_clear_sky(self, client):
        from backend.api.services.nws_forecast.nws_forecast_client import (
            NWSDailyData,
            NWSHourlyData,
        )
        hourly = [
            NWSHourlyData(
                timestamp=f"2025-06-15T{h:02d}:00:00+00:00",
                sky_cover_percent=10.0,
                dewpoint_celsius=15.0,
            )
            for h in range(24)
        ]
        day = NWSDailyData(
            date=datetime(2025, 6, 15),
            dewpoint_mean_celsius=15.0,
            hourly_data=hourly,
        )
        rs = client.estimate_daily_solar_radiation(40.0, day, method="usa_asos")
        assert rs is not None
        assert rs > 0

    def test_solar_radiation_overcast(self, client):
        from backend.api.services.nws_forecast.nws_forecast_client import (
            NWSDailyData,
            NWSHourlyData,
        )
        hourly = [
            NWSHourlyData(
                timestamp=f"2025-06-15T{h:02d}:00:00+00:00",
                sky_cover_percent=100.0,
                dewpoint_celsius=20.0,
            )
            for h in range(24)
        ]
        day = NWSDailyData(
            date=datetime(2025, 6, 15),
            dewpoint_mean_celsius=20.0,
            hourly_data=hourly,
        )
        rs = client.estimate_daily_solar_radiation(40.0, day, method="usa_asos")
        assert rs is not None
        assert rs > 0

    def test_solar_radiation_fao_method(self, client):
        from backend.api.services.nws_forecast.nws_forecast_client import (
            NWSDailyData,
            NWSHourlyData,
        )
        hourly = [
            NWSHourlyData(
                timestamp=f"2025-06-15T{h:02d}:00:00+00:00",
                sky_cover_percent=50.0,
            )
            for h in range(24)
        ]
        day = NWSDailyData(
            date=datetime(2025, 6, 15),
            hourly_data=hourly,
        )
        rs = client.estimate_daily_solar_radiation(
            40.0, day, method="fao_standard"
        )
        assert rs is not None

    def test_solar_radiation_usa_south_summer(self, client):
        from backend.api.services.nws_forecast.nws_forecast_client import (
            NWSDailyData,
            NWSHourlyData,
        )
        hourly = [
            NWSHourlyData(
                timestamp=f"2025-07-15T{h:02d}:00:00+00:00",
                sky_cover_percent=40.0,
            )
            for h in range(24)
        ]
        day = NWSDailyData(
            date=datetime(2025, 7, 15),  # July = summer
            hourly_data=hourly,
        )
        rs = client.estimate_daily_solar_radiation(
            30.0, day, method="usa_south"
        )
        assert rs is not None

    def test_solar_radiation_usa_south_winter(self, client):
        from backend.api.services.nws_forecast.nws_forecast_client import (
            NWSDailyData,
            NWSHourlyData,
        )
        hourly = [
            NWSHourlyData(
                timestamp=f"2025-01-15T{h:02d}:00:00+00:00",
                sky_cover_percent=60.0,
            )
            for h in range(24)
        ]
        day = NWSDailyData(
            date=datetime(2025, 1, 15),  # January = winter
            hourly_data=hourly,
        )
        rs = client.estimate_daily_solar_radiation(
            30.0, day, method="usa_south"
        )
        assert rs is not None

    def test_solar_radiation_invalid_method(self, client):
        from backend.api.services.nws_forecast.nws_forecast_client import (
            NWSDailyData,
            NWSHourlyData,
        )
        hourly = [
            NWSHourlyData(
                timestamp="2025-06-15T12:00:00+00:00",
                sky_cover_percent=50.0,
            )
        ]
        day = NWSDailyData(
            date=datetime(2025, 6, 15),
            hourly_data=hourly,
        )
        with pytest.raises(ValueError, match="Invalid method"):
            client.estimate_daily_solar_radiation(40.0, day, method="invalid")

    def test_solar_radiation_no_sky_cover_returns_none(self, client):
        from backend.api.services.nws_forecast.nws_forecast_client import (
            NWSDailyData,
            NWSHourlyData,
        )
        hourly = [
            NWSHourlyData(
                timestamp="2025-06-15T12:00:00+00:00",
                sky_cover_percent=None,
            )
        ]
        day = NWSDailyData(
            date=datetime(2025, 6, 15),
            hourly_data=hourly,
        )
        rs = client.estimate_daily_solar_radiation(40.0, day)
        assert rs is None

    # --- Attribution and metadata ---

    def test_get_attribution(self, client):
        attr = client.get_attribution()
        assert isinstance(attr, dict)
        assert "source" in attr
        assert "NOAA" in attr["source"] or "NWS" in attr["source"]

    def test_get_data_availability_info(self, client):
        info = client.get_data_availability_info()
        assert "coverage" in info
        assert "forecast_horizon" in info

    def test_is_in_coverage_usa(self, client):
        assert client.is_in_coverage(40.0, -100.0) is True

    def test_is_in_coverage_outside(self, client):
        assert client.is_in_coverage(0.0, 0.0) is False


# ============================================================================
# MET Norway Client Pure Functions
# ============================================================================

class TestMETNorwayPureFunctions:
    """Tests for pure/static methods in METNorwayClient."""

    # --- _round_coordinates ---

    def test_round_coordinates_basic(self):
        from backend.api.services.met_norway.met_norway_client import (
            METNorwayClient,
        )
        lat, lon = METNorwayClient._round_coordinates(59.91234567, 10.74567890)
        assert lat == 59.9123
        assert lon == 10.7457

    def test_round_coordinates_negative(self):
        from backend.api.services.met_norway.met_norway_client import (
            METNorwayClient,
        )
        lat, lon = METNorwayClient._round_coordinates(-23.550520, -46.633308)
        assert lat == -23.5505
        assert lon == -46.6333

    def test_round_coordinates_already_rounded(self):
        from backend.api.services.met_norway.met_norway_client import (
            METNorwayClient,
        )
        lat, lon = METNorwayClient._round_coordinates(60.0, 10.0)
        assert lat == 60.0
        assert lon == 10.0

    # --- is_in_nordic_region ---

    def test_is_in_nordic_oslo(self):
        from backend.api.services.met_norway.met_norway_client import (
            METNorwayClient,
        )
        assert METNorwayClient.is_in_nordic_region(59.9139, 10.7522) is True

    def test_is_in_nordic_stockholm(self):
        from backend.api.services.met_norway.met_norway_client import (
            METNorwayClient,
        )
        assert METNorwayClient.is_in_nordic_region(59.3293, 18.0686) is True

    def test_is_in_nordic_brazil(self):
        from backend.api.services.met_norway.met_norway_client import (
            METNorwayClient,
        )
        assert METNorwayClient.is_in_nordic_region(-15.7939, -47.8828) is False

    def test_is_in_nordic_usa(self):
        from backend.api.services.met_norway.met_norway_client import (
            METNorwayClient,
        )
        assert METNorwayClient.is_in_nordic_region(40.7128, -74.0060) is False

    # --- get_recommended_variables ---

    def test_recommended_variables_nordic(self):
        from backend.api.services.met_norway.met_norway_client import (
            METNorwayClient,
        )
        # Oslo
        vars_ = METNorwayClient.get_recommended_variables(59.9139, 10.7522)
        assert isinstance(vars_, list)
        assert len(vars_) > 0

    def test_recommended_variables_global(self):
        from backend.api.services.met_norway.met_norway_client import (
            METNorwayClient,
        )
        # São Paulo
        vars_ = METNorwayClient.get_recommended_variables(-23.5505, -46.6333)
        assert isinstance(vars_, list)
        assert len(vars_) > 0

    def test_recommended_variables_nordic_has_more(self):
        from backend.api.services.met_norway.met_norway_client import (
            METNorwayClient,
        )
        nordic_vars = METNorwayClient.get_recommended_variables(59.9139, 10.7522)
        global_vars = METNorwayClient.get_recommended_variables(-15.7939, -47.8828)
        # Nordic should have precipitation, global may not
        assert len(nordic_vars) >= len(global_vars)

    # --- get_attribution ---

    def test_get_attribution(self):
        with patch("httpx.AsyncClient"):
            from backend.api.services.met_norway.met_norway_client import (
                METNorwayClient,
            )
            client = METNorwayClient()
            attr = client.get_attribution()
            assert "MET Norway" in attr
            assert "CC" in attr.upper() or "4.0" in attr

    # --- get_coverage_info ---

    def test_get_coverage_info(self):
        with patch("httpx.AsyncClient"):
            from backend.api.services.met_norway.met_norway_client import (
                METNorwayClient,
            )
            client = METNorwayClient()
            info = client.get_coverage_info()
            assert "region" in info
            assert info["region"] == "GLOBAL"
            assert "quality_tiers" in info
            assert "nordic" in info["quality_tiers"]

    # --- get_data_availability_info ---

    def test_get_data_availability_info(self):
        from backend.api.services.met_norway.met_norway_client import (
            METNorwayClient,
        )
        info = METNorwayClient.get_data_availability_info()
        assert "forecast_horizon_days" in info
        assert info["forecast_horizon_days"] == 5
        assert "coverage" in info


# ============================================================================
# NWS Stations Client Pure Functions
# ============================================================================

class TestNWSStationsPureFunctions:
    """Tests for pure/static methods in NWSStationsClient."""

    @pytest.fixture
    def client(self):
        with patch("httpx.AsyncClient"):
            from backend.api.services.nws_stations.nws_stations_client import (
                NWSStationsClient,
            )
            return NWSStationsClient()

    # --- _val ---

    def test_val_with_value(self, client):
        assert client._val({"value": 25.5}) == 25.5

    def test_val_none_data(self, client):
        assert client._val(None) is None

    def test_val_none_value(self, client):
        assert client._val({"value": None}) is None

    def test_val_empty_dict(self, client):
        assert client._val({}) is None

    def test_val_zero(self, client):
        assert client._val({"value": 0}) == 0.0

    def test_val_negative(self, client):
        assert client._val({"value": -10.5}) == -10.5

    # --- _extract_wind_speed_ms ---

    def test_extract_wind_speed_ms_basic(self):
        from backend.api.services.nws_stations.nws_stations_client import (
            NWSStationsClient,
        )
        result = NWSStationsClient._extract_wind_speed_ms({"value": 36.0})
        assert result == 10.0  # 36 km/h = 10 m/s

    def test_extract_wind_speed_ms_none(self):
        from backend.api.services.nws_stations.nws_stations_client import (
            NWSStationsClient,
        )
        assert NWSStationsClient._extract_wind_speed_ms(None) is None

    def test_extract_wind_speed_ms_null_value(self):
        from backend.api.services.nws_stations.nws_stations_client import (
            NWSStationsClient,
        )
        assert NWSStationsClient._extract_wind_speed_ms({"value": None}) is None

    def test_extract_wind_speed_ms_zero(self):
        from backend.api.services.nws_stations.nws_stations_client import (
            NWSStationsClient,
        )
        result = NWSStationsClient._extract_wind_speed_ms({"value": 0})
        assert result == 0.0

    # --- convert_wind_to_2m ---

    def test_convert_wind_to_2m_from_10m(self):
        from backend.api.services.nws_stations.nws_stations_client import (
            NWSStationsClient,
        )
        u2 = NWSStationsClient.convert_wind_to_2m(5.0, z=10.0)
        assert u2 is not None
        assert 3.0 < u2 < 5.0  # Should be reduced

    def test_convert_wind_to_2m_already_at_2m(self):
        from backend.api.services.nws_stations.nws_stations_client import (
            NWSStationsClient,
        )
        u2 = NWSStationsClient.convert_wind_to_2m(3.0, z=2.0)
        assert u2 == 3.0  # No conversion needed

    def test_convert_wind_to_2m_none(self):
        from backend.api.services.nws_stations.nws_stations_client import (
            NWSStationsClient,
        )
        assert NWSStationsClient.convert_wind_to_2m(None) is None

    def test_convert_wind_to_2m_minimum_05(self):
        from backend.api.services.nws_stations.nws_stations_client import (
            NWSStationsClient,
        )
        u2 = NWSStationsClient.convert_wind_to_2m(0.1, z=10.0)
        assert u2 >= 0.5  # Physical minimum

    def test_convert_wind_to_2m_at_2m_enforces_minimum(self):
        from backend.api.services.nws_stations.nws_stations_client import (
            NWSStationsClient,
        )
        u2 = NWSStationsClient.convert_wind_to_2m(0.1, z=2.0)
        assert u2 >= 0.5

    # --- aggregate_to_daily ---

    def test_aggregate_to_daily_basic(self, client):
        from backend.api.services.nws_stations.nws_stations_client import (
            NWSObservation,
            NWSStation,
        )
        import pytz

        station = NWSStation(
            stationIdentifier="KJFK",
            name="JFK Airport",
            latitude=40.6413,
            longitude=-73.7781,
            elevation_m=4.0,
            distance_km=1.0,
        )
        now = datetime.now(pytz.UTC)
        obs = [
            NWSObservation(
                station_id="KJFK",
                timestamp=now.replace(hour=6),
                temp_celsius=20.0,
                humidity_percent=60.0,
                wind_speed_2m_ms=3.0,
            ),
            NWSObservation(
                station_id="KJFK",
                timestamp=now.replace(hour=12),
                temp_celsius=30.0,
                humidity_percent=40.0,
                wind_speed_2m_ms=5.0,
            ),
            NWSObservation(
                station_id="KJFK",
                timestamp=now.replace(hour=18),
                temp_celsius=25.0,
                humidity_percent=50.0,
                wind_speed_2m_ms=4.0,
            ),
        ]
        result = client.aggregate_to_daily(obs, station)
        assert len(result) == 1
        day = result[0]
        assert day.T_max == 30.0
        assert day.T_min == 20.0
        assert day.station_id == "KJFK"

    def test_aggregate_to_daily_empty(self, client):
        from backend.api.services.nws_stations.nws_stations_client import (
            NWSStation,
        )
        station = NWSStation(
            stationIdentifier="KJFK",
            name="JFK",
            latitude=40.6413,
            longitude=-73.7781,
        )
        result = client.aggregate_to_daily([], station)
        assert result == []

    # --- get_data_availability_info ---

    def test_get_data_availability_info(self):
        from backend.api.services.nws_stations.nws_stations_client import (
            NWSStationsClient,
        )
        info = NWSStationsClient.get_data_availability_info()
        assert "source" in info
        assert "NOAA" in info["source"] or "NWS" in info["source"]
        assert "bbox" in info
        assert "known_issues" in info


# ============================================================================
# OpenMeteo Archive Client Pure Functions
# ============================================================================

class TestOpenMeteoArchivePureFunctions:
    """Tests for pure methods in OpenMeteoArchiveClient."""

    @pytest.fixture
    def client(self):
        with patch(
            "backend.api.services.openmeteo_archive.openmeteo_archive_client.openmeteo_requests"
        ), patch(
            "backend.api.services.openmeteo_archive.openmeteo_archive_client.requests_cache"
        ), patch(
            "backend.api.services.openmeteo_archive.openmeteo_archive_client.retry"
        ):
            from backend.api.services.openmeteo_archive.openmeteo_archive_client import (
                OpenMeteoArchiveClient,
            )
            return OpenMeteoArchiveClient()

    # --- _get_cache_key ---

    def test_get_cache_key_format(self, client):
        key = client._get_cache_key(40.0, -74.0, "2024-01-01", "2024-01-31")
        assert "climate:openmeteo:archive:" in key
        assert "40.0" in key
        assert "-74.0" in key

    def test_get_cache_key_rounds(self, client):
        key = client._get_cache_key(40.12345, -74.56789, "2024-01-01", "2024-01-31")
        assert "40.12" in key
        assert "-74.57" in key

    def test_get_cache_key_different_dates(self, client):
        key1 = client._get_cache_key(40.0, -74.0, "2024-01-01", "2024-01-31")
        key2 = client._get_cache_key(40.0, -74.0, "2024-02-01", "2024-02-28")
        assert key1 != key2

    # --- _validate_inputs ---

    def test_validate_inputs_valid(self, client):
        # Should not raise
        client._validate_inputs(40.0, -74.0, "2024-01-01", "2024-06-30")

    def test_validate_inputs_invalid_coords(self, client):
        with pytest.raises(ValueError, match="Invalid coordinates"):
            client._validate_inputs(999.0, -74.0, "2024-01-01", "2024-06-30")

    def test_validate_inputs_invalid_date_format(self, client):
        with pytest.raises(ValueError):
            client._validate_inputs(40.0, -74.0, "not-a-date", "2024-06-30")

    def test_validate_inputs_start_after_end(self, client):
        with pytest.raises(ValueError, match="start_date must be <= end_date"):
            client._validate_inputs(40.0, -74.0, "2024-06-30", "2024-01-01")

    # --- get_info (static) ---

    def test_get_info(self):
        from backend.api.services.openmeteo_archive.openmeteo_archive_client import (
            OpenMeteoArchiveClient,
        )
        info = OpenMeteoArchiveClient.get_info()
        assert "api" in info
        assert "Archive" in info["api"] or "archive" in info["api"]
        assert "coverage" in info


# ============================================================================
# OpenMeteo Forecast Client Pure Functions
# ============================================================================

class TestOpenMeteoForecastPureFunctions:
    """Tests for pure methods in OpenMeteoForecastClient."""

    @pytest.fixture
    def client(self):
        with patch(
            "backend.api.services.openmeteo_forecast.openmeteo_forecast_client.openmeteo_requests"
        ), patch(
            "backend.api.services.openmeteo_forecast.openmeteo_forecast_client.requests_cache"
        ), patch(
            "backend.api.services.openmeteo_forecast.openmeteo_forecast_client.retry"
        ):
            from backend.api.services.openmeteo_forecast.openmeteo_forecast_client import (
                OpenMeteoForecastClient,
            )
            return OpenMeteoForecastClient()

    # --- convert_wind_10m_to_2m (static) ---

    def test_convert_wind_basic(self):
        from backend.api.services.openmeteo_forecast.openmeteo_forecast_client import (
            OpenMeteoForecastClient,
        )
        u2 = OpenMeteoForecastClient.convert_wind_10m_to_2m(
            np.array([5.0]), height=10.0
        )
        assert 3.0 < float(u2[0]) < 5.0

    def test_convert_wind_at_2m(self):
        from backend.api.services.openmeteo_forecast.openmeteo_forecast_client import (
            OpenMeteoForecastClient,
        )
        u2 = OpenMeteoForecastClient.convert_wind_10m_to_2m(
            np.array([3.0]), height=2.0
        )
        assert float(u2[0]) == 3.0  # Already at 2m, no conversion

    def test_convert_wind_minimum(self):
        from backend.api.services.openmeteo_forecast.openmeteo_forecast_client import (
            OpenMeteoForecastClient,
        )
        u2 = OpenMeteoForecastClient.convert_wind_10m_to_2m(
            np.array([0.01]), height=10.0
        )
        assert float(u2[0]) >= 0.5  # Physical minimum

    # --- _get_cache_key ---

    def test_get_cache_key_format(self, client):
        key = client._get_cache_key(40.0, -74.0, "2024-01-01", "2024-01-31")
        assert "climate:openmeteo:forecast:" in key

    def test_get_cache_key_rounds_coords(self, client):
        key = client._get_cache_key(40.12345, -74.56789, "2024-01-01", "2024-01-31")
        assert "40.12" in key
        assert "-74.57" in key

    # --- _get_ttl_seconds ---

    def test_get_ttl_future_data(self, client):
        today = datetime.now().date()
        future = today + timedelta(days=3)
        ttl = client._get_ttl_seconds(str(today), str(future))
        assert ttl == 3600  # 1 hour for forecast data

    def test_get_ttl_past_data(self, client):
        today = datetime.now().date()
        past_start = today - timedelta(days=10)
        past_end = today - timedelta(days=5)
        ttl = client._get_ttl_seconds(str(past_start), str(past_end))
        assert ttl == 3600 * 6  # 6 hours for recent data

    def test_get_ttl_hours(self, client):
        today = datetime.now().date()
        future = today + timedelta(days=3)
        hours = client._get_ttl_hours(str(today), str(future))
        assert hours == 1

    # --- _validate_inputs ---

    def test_validate_inputs_valid(self, client):
        today = datetime.now().date()
        start = today - timedelta(days=5)
        end = today + timedelta(days=3)
        # Should not raise
        client._validate_inputs(40.0, -74.0, str(start), str(end))

    def test_validate_inputs_invalid_coords(self, client):
        with pytest.raises(ValueError):
            client._validate_inputs(999.0, -74.0, "2024-01-01", "2024-06-30")

    def test_validate_inputs_start_after_end(self, client):
        with pytest.raises(ValueError, match="start_date must be <= end_date"):
            client._validate_inputs(40.0, -74.0, "2025-06-30", "2025-01-01")

    def test_validate_inputs_date_too_old(self, client):
        with pytest.raises(ValueError, match="start_date must be"):
            client._validate_inputs(40.0, -74.0, "2020-01-01", "2020-01-31")

    def test_validate_inputs_date_too_far_future(self, client):
        future = datetime.now().date() + timedelta(days=30)
        with pytest.raises(ValueError, match="end_date must be"):
            client._validate_inputs(40.0, -74.0, str(datetime.now().date()), str(future))

    # --- get_info (static) ---

    def test_get_info(self):
        from backend.api.services.openmeteo_forecast.openmeteo_forecast_client import (
            OpenMeteoForecastClient,
        )
        info = OpenMeteoForecastClient.get_info()
        assert "api" in info
        assert "Forecast" in info["api"]
        assert "coverage" in info
        assert info["coverage"] == "Global"
