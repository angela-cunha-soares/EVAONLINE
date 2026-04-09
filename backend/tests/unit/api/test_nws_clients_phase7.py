"""
Phase 7 – NWS clients comprehensive tests.

Covers:
- NWSForecastClient: config, grid metadata, parsing, conversions,
  solar radiation, daily aggregation, health_check, coverage
- NWSStationsClient: config, _val, wind conversion, aggregate_to_daily,
  health_check, find_nearest_active_station, get_observations
"""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ═══════════════════════════════════════════════════════════════
# NWS Forecast Client
# ═══════════════════════════════════════════════════════════════


class TestNWSForecastConfig:
    def test_defaults(self):
        from backend.api.services.nws_forecast.nws_forecast_client import (
            NWSConfig,
        )

        cfg = NWSConfig()
        assert cfg.base_url == "https://api.weather.gov"
        assert cfg.timeout == 30
        assert cfg.retry_attempts == 3


class TestNWSForecastClientSync:
    """Test synchronous / pure methods of NWSForecastClient."""

    def _make_client(self):
        from backend.api.services.nws_forecast.nws_forecast_client import (
            NWSForecastClient,
            NWSConfig,
        )

        cfg = NWSConfig()
        with patch("httpx.AsyncClient"):
            client = NWSForecastClient(config=cfg)
        return client

    def test_estimate_pressure_sea_level(self):
        client = self._make_client()
        assert client._estimate_pressure_from_elevation(None) == 1013.25

    def test_estimate_pressure_high_altitude(self):
        client = self._make_client()
        p = client._estimate_pressure_from_elevation(1000)
        assert 800 < p < 950  # ~885 hPa at 1000m

    def test_calculate_extraterrestrial_radiation(self):
        client = self._make_client()
        ra = client._calculate_extraterrestrial_radiation(45.0, 172)  # summer solstice
        assert ra > 30  # high northern latitudes get lots of Ra in summer

    def test_ra_equator_equinox(self):
        client = self._make_client()
        ra = client._calculate_extraterrestrial_radiation(0.0, 80)  # spring equinox
        assert 30 < ra < 42

    def test_get_uom_from_layer(self):
        client = self._make_client()
        assert client._get_uom_from_layer({"uom": "wmoUnit:degC"}) == "wmoUnit:degC"
        assert client._get_uom_from_layer(None) is None
        assert client._get_uom_from_layer({}) is None

    def test_parse_grid_time_series_empty(self):
        client = self._make_client()
        assert client._parse_grid_time_series([]) == {}

    def test_parse_grid_time_series_valid(self):
        client = self._make_client()
        values = [
            {"validTime": "2024-01-01T00:00:00+00:00/PT1H", "value": 22.5},
            {"validTime": "2024-01-01T01:00:00+00:00/PT1H", "value": 21.0},
        ]
        result = client._parse_grid_time_series(values)
        assert len(result) == 2
        assert 22.5 in result.values()

    def test_parse_grid_time_series_z_format(self):
        client = self._make_client()
        values = [{"validTime": "2024-01-01T00:00:00Z/PT1H", "value": 10}]
        result = client._parse_grid_time_series(values)
        assert len(result) == 1

    def test_parse_grid_time_series_missing_value(self):
        client = self._make_client()
        values = [{"validTime": "2024-01-01T00:00:00+00:00/PT1H", "value": None}]
        result = client._parse_grid_time_series(values)
        assert len(result) == 0

    def test_is_in_coverage_usa(self):
        client = self._make_client()
        assert client.is_in_coverage(39.7, -104.9) is True

    def test_is_in_coverage_outside(self):
        client = self._make_client()
        assert client.is_in_coverage(-23.5, -46.6) is False  # São Paulo

    def test_get_attribution(self):
        client = self._make_client()
        attr = client.get_attribution()
        assert "NOAA" in attr["source"]

    def test_get_data_availability_info(self):
        client = self._make_client()
        info = client.get_data_availability_info()
        assert info["forecast_horizon"]["days"] == 5


class TestNWSForecastSolarRadiation:
    def _make_client(self):
        from backend.api.services.nws_forecast.nws_forecast_client import (
            NWSForecastClient,
            NWSConfig,
        )

        with patch("httpx.AsyncClient"):
            return NWSForecastClient(config=NWSConfig())

    def test_estimate_solar_radiation_usa_asos(self):
        from backend.api.services.nws_forecast.nws_forecast_client import (
            NWSHourlyData,
            NWSDailyData,
        )

        client = self._make_client()
        hourly_data = [
            NWSHourlyData(
                timestamp=f"2024-06-15T{h:02d}:00:00+00:00",
                sky_cover_percent=30.0,
                dewpoint_celsius=15.0,
            )
            for h in range(24)
        ]
        day = NWSDailyData(
            date=datetime(2024, 6, 15),
            dewpoint_mean_celsius=15.0,
            hourly_data=hourly_data,
        )
        rs = client.estimate_daily_solar_radiation(40.0, day, method="usa_asos")
        assert rs is not None
        assert rs > 0

    def test_estimate_solar_radiation_fao(self):
        from backend.api.services.nws_forecast.nws_forecast_client import (
            NWSHourlyData,
            NWSDailyData,
        )

        client = self._make_client()
        hourly_data = [
            NWSHourlyData(
                timestamp=f"2024-06-15T{h:02d}:00:00+00:00",
                sky_cover_percent=50.0,
            )
            for h in range(24)
        ]
        day = NWSDailyData(
            date=datetime(2024, 6, 15),
            hourly_data=hourly_data,
        )
        rs = client.estimate_daily_solar_radiation(40.0, day, method="fao_standard")
        assert rs is not None
        assert rs > 0

    def test_estimate_solar_radiation_no_sky_cover(self):
        from backend.api.services.nws_forecast.nws_forecast_client import (
            NWSHourlyData,
            NWSDailyData,
        )

        client = self._make_client()
        hourly_data = [
            NWSHourlyData(timestamp=f"2024-06-15T00:00:00+00:00")
        ]
        day = NWSDailyData(
            date=datetime(2024, 6, 15),
            hourly_data=hourly_data,
        )
        assert client.estimate_daily_solar_radiation(40.0, day) is None

    def test_invalid_method(self):
        from backend.api.services.nws_forecast.nws_forecast_client import (
            NWSHourlyData,
            NWSDailyData,
        )

        client = self._make_client()
        hourly_data = [
            NWSHourlyData(
                timestamp="2024-06-15T00:00:00+00:00",
                sky_cover_percent=30.0,
            )
        ]
        day = NWSDailyData(
            date=datetime(2024, 6, 15),
            hourly_data=hourly_data,
        )
        with pytest.raises(ValueError, match="Invalid method"):
            client.estimate_daily_solar_radiation(40.0, day, method="bogus")

    def test_usa_south_seasonal(self):
        from backend.api.services.nws_forecast.nws_forecast_client import (
            NWSHourlyData,
            NWSDailyData,
        )

        client = self._make_client()
        for month in [3, 6, 10, 1]:  # spring, summer, fall, winter
            hourly_data = [
                NWSHourlyData(
                    timestamp=f"2024-{month:02d}-15T12:00:00+00:00",
                    sky_cover_percent=40.0,
                )
            ]
            day = NWSDailyData(
                date=datetime(2024, month, 15),
                hourly_data=hourly_data,
            )
            rs = client.estimate_daily_solar_radiation(
                30.0, day, method="usa_south"
            )
            assert rs is not None
            assert rs > 0


class TestNWSForecastAsync:
    @pytest.mark.asyncio
    async def test_close(self):
        from backend.api.services.nws_forecast.nws_forecast_client import (
            NWSForecastClient,
            NWSConfig,
        )

        with patch("httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_cls.return_value = mock_client
            client = NWSForecastClient(config=NWSConfig())
            await client.close()
            mock_client.aclose.assert_called_once()

    @pytest.mark.asyncio
    async def test_context_manager(self):
        from backend.api.services.nws_forecast.nws_forecast_client import (
            NWSForecastClient,
            NWSConfig,
        )

        with patch("httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_cls.return_value = mock_client

            async with NWSForecastClient(config=NWSConfig()) as client:
                assert client is not None
            mock_client.aclose.assert_called_once()

    @pytest.mark.asyncio
    async def test_health_check_success(self):
        from backend.api.services.nws_forecast.nws_forecast_client import (
            NWSForecastClient,
            NWSConfig,
        )

        with patch("httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_resp = MagicMock()
            mock_resp.raise_for_status = MagicMock()
            mock_client.get.return_value = mock_resp
            mock_cls.return_value = mock_client

            client = NWSForecastClient(config=NWSConfig())
            result = await client.health_check()
            assert result["status"] == "ok"


class TestNWSForecastFactory:
    def test_create_forecast_client(self):
        from backend.api.services.nws_forecast.nws_forecast_client import (
            create_nws_forecast_client,
        )

        with patch("httpx.AsyncClient"):
            client = create_nws_forecast_client()
            assert client is not None


# ═══════════════════════════════════════════════════════════════
# NWS Stations Client
# ═══════════════════════════════════════════════════════════════


class TestNWSStationsConfig:
    def test_defaults(self):
        from backend.api.services.nws_stations.nws_stations_client import (
            NWSStationsConfig,
        )

        cfg = NWSStationsConfig()
        assert cfg.base_url == "https://api.weather.gov"
        assert cfg.observation_delay_threshold == 30
        assert cfg.max_days_back == 3


class TestNWSStationsClientSync:
    def _make_client(self):
        from backend.api.services.nws_stations.nws_stations_client import (
            NWSStationsClient,
        )

        with patch("httpx.AsyncClient"):
            return NWSStationsClient()

    def test_val_none(self):
        client = self._make_client()
        assert client._val(None) is None

    def test_val_missing_value(self):
        client = self._make_client()
        assert client._val({"value": None}) is None

    def test_val_valid(self):
        client = self._make_client()
        assert client._val({"value": 22.5}) == 22.5

    def test_extract_wind_speed_ms(self):
        from backend.api.services.nws_stations.nws_stations_client import (
            NWSStationsClient,
        )

        assert NWSStationsClient._extract_wind_speed_ms(None) is None
        assert NWSStationsClient._extract_wind_speed_ms({"value": None}) is None
        result = NWSStationsClient._extract_wind_speed_ms({"value": 36.0})
        assert abs(result - 10.0) < 0.01  # 36 km/h ≈ 10 m/s

    def test_convert_wind_to_2m_none(self):
        from backend.api.services.nws_stations.nws_stations_client import (
            NWSStationsClient,
        )

        assert NWSStationsClient.convert_wind_to_2m(None) is None

    def test_convert_wind_to_2m_at_2m(self):
        from backend.api.services.nws_stations.nws_stations_client import (
            NWSStationsClient,
        )

        result = NWSStationsClient.convert_wind_to_2m(3.0, z=2.0)
        assert result == 3.0

    def test_convert_wind_to_2m_at_10m(self):
        from backend.api.services.nws_stations.nws_stations_client import (
            NWSStationsClient,
        )

        result = NWSStationsClient.convert_wind_to_2m(5.0, z=10.0)
        assert 0.5 <= result < 5.0  # should be reduced

    def test_convert_wind_to_2m_minimum(self):
        from backend.api.services.nws_stations.nws_stations_client import (
            NWSStationsClient,
        )

        result = NWSStationsClient.convert_wind_to_2m(0.01, z=10.0)
        assert result >= 0.5  # physical minimum

    def test_get_data_availability_info(self):
        from backend.api.services.nws_stations.nws_stations_client import (
            NWSStationsClient,
        )

        info = NWSStationsClient.get_data_availability_info()
        assert info["source"] == "NWS Stations (NOAA)"
        assert "known_issues" in info

    def test_aggregate_to_daily_empty(self):
        client = self._make_client()
        from backend.api.services.nws_stations.nws_stations_client import (
            NWSStation,
        )

        station = NWSStation(
            stationIdentifier="KJFK",
            name="JFK Airport",
            latitude=40.6413,
            longitude=-73.7781,
        )
        result = client.aggregate_to_daily([], station)
        assert result == []

    def test_aggregate_to_daily_with_data(self):
        client = self._make_client()
        from backend.api.services.nws_stations.nws_stations_client import (
            NWSStation,
            NWSObservation,
        )
        import pytz

        station = NWSStation(
            stationIdentifier="KJFK",
            name="JFK Airport",
            latitude=40.6413,
            longitude=-73.7781,
        )
        now = datetime.now(pytz.UTC)
        observations = [
            NWSObservation(
                station_id="KJFK",
                timestamp=now - timedelta(hours=i),
                temp_celsius=20.0 + i * 0.5,
                humidity_percent=60.0 + i,
                wind_speed_2m_ms=2.0,
            )
            for i in range(24)
        ]
        result = client.aggregate_to_daily(observations, station)
        assert len(result) >= 1
        assert result[0].station_id == "KJFK"


class TestNWSStationsAsync:
    @pytest.mark.asyncio
    async def test_close(self):
        from backend.api.services.nws_stations.nws_stations_client import (
            NWSStationsClient,
        )

        with patch("httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_cls.return_value = mock_client
            client = NWSStationsClient()
            await client.close()
            mock_client.aclose.assert_called_once()

    @pytest.mark.asyncio
    async def test_health_check_success(self):
        from backend.api.services.nws_stations.nws_stations_client import (
            NWSStationsClient,
        )

        with patch("httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_resp = MagicMock()
            mock_resp.raise_for_status = MagicMock()
            mock_client.get.return_value = mock_resp
            mock_cls.return_value = mock_client

            client = NWSStationsClient()
            result = await client.health_check()
            assert result is True

    @pytest.mark.asyncio
    async def test_health_check_failure(self):
        from backend.api.services.nws_stations.nws_stations_client import (
            NWSStationsClient,
        )

        with patch("httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.get.side_effect = Exception("Timeout")
            mock_cls.return_value = mock_client

            client = NWSStationsClient()
            result = await client.health_check()
            assert result is False

    @pytest.mark.asyncio
    async def test_find_nearest_outside_usa(self):
        from backend.api.services.nws_stations.nws_stations_client import (
            NWSStationsClient,
        )

        with patch("httpx.AsyncClient"):
            client = NWSStationsClient()
            result = await client.find_nearest_active_station(-23.5, -46.6)
            assert result is None

    @pytest.mark.asyncio
    async def test_get_observations_error(self):
        from backend.api.services.nws_stations.nws_stations_client import (
            NWSStationsClient,
        )

        with patch("httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.get.side_effect = Exception("Network error")
            mock_cls.return_value = mock_client

            client = NWSStationsClient()
            result = await client.get_observations("KJFK")
            assert result == []


class TestCreateNWSStationsClient:
    def test_factory(self):
        from backend.api.services.nws_stations.nws_stations_client import (
            create_nws_client,
        )

        with patch("httpx.AsyncClient"):
            client = create_nws_client()
            assert client is not None
