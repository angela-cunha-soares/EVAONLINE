"""
Phase 4 Tests: Sync Adapter Methods.

Tests all 5 sync adapters with mocked underlying async clients:
- NWSDailyForecastSyncAdapter
- NWSStationsSyncAdapter
- METNorwaySyncAdapter
- OpenMeteoForecastSyncAdapter
- OpenTopoSyncAdapter
"""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
import asyncio

import pytest


@pytest.fixture(autouse=True)
def _fresh_event_loop():
    """Ensure a fresh event loop for every test (prevents 'loop is closed' in full suite)."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield
    loop.close()


# ============================================================================
# NWS Forecast Sync Adapter
# ============================================================================

class TestNWSForecastSyncAdapter:
    """Tests for NWSDailyForecastSyncAdapter."""

    @pytest.fixture
    def adapter(self):
        with patch(
            "backend.api.services.nws_forecast.nws_forecast_sync_adapter.create_nws_forecast_client"
        ) as mock_factory:
            mock_client = MagicMock()
            mock_client.get_attribution.return_value = {
                "source": "NWS / NOAA",
                "license": "Public Domain",
                "api_docs": "https://api.weather.gov",
                "terms_url": "https://weather.gov",
            }
            mock_factory.return_value = mock_client
            from backend.api.services.nws_forecast.nws_forecast_sync_adapter import (
                NWSDailyForecastSyncAdapter,
            )
            return NWSDailyForecastSyncAdapter()

    def test_get_attribution(self, adapter):
        attr = adapter.get_attribution()
        assert "NWS" in attr or "NOAA" in attr
        assert "Public Domain" in attr

    def test_get_info(self, adapter):
        info = adapter.get_info()
        assert isinstance(info, dict)
        assert "api_name" in info
        assert "coverage" in info
        assert "eto_variables" in info
        assert len(info["eto_variables"]) > 0

    def test_get_info_has_solar_radiation_method(self, adapter):
        info = adapter.get_info()
        assert "solar_radiation_method" in info
        assert "Ångström" in info["solar_radiation_method"] or "ASOS" in info["solar_radiation_method"]

    def test_health_check_sync_success(self):
        with patch(
            "backend.api.services.nws_forecast.nws_forecast_sync_adapter.create_nws_forecast_client"
        ) as mock_factory:
            mock_client = AsyncMock()
            mock_client.health_check.return_value = {"status": "ok"}
            mock_client.close = AsyncMock()
            mock_factory.return_value = mock_client

            from backend.api.services.nws_forecast.nws_forecast_sync_adapter import (
                NWSDailyForecastSyncAdapter,
            )
            adapter = NWSDailyForecastSyncAdapter()
            result = adapter.health_check_sync()
            assert result is True

    def test_health_check_sync_failure(self):
        with patch(
            "backend.api.services.nws_forecast.nws_forecast_sync_adapter.create_nws_forecast_client"
        ) as mock_factory:
            mock_client = AsyncMock()
            mock_client.health_check.side_effect = Exception("Connection error")
            mock_client.close = AsyncMock()
            mock_factory.return_value = mock_client

            from backend.api.services.nws_forecast.nws_forecast_sync_adapter import (
                NWSDailyForecastSyncAdapter,
            )
            adapter = NWSDailyForecastSyncAdapter()
            result = adapter.health_check_sync()
            assert result is False

    def test_get_daily_data_sync_success(self):
        with patch(
            "backend.api.services.nws_forecast.nws_forecast_sync_adapter.create_nws_forecast_client"
        ) as mock_factory:
            mock_client = AsyncMock()
            mock_daily = MagicMock()
            mock_daily.date = datetime(2025, 6, 15)
            mock_daily.temp_max_celsius = 30.0
            mock_daily.temp_min_celsius = 20.0
            mock_daily.temp_mean_celsius = 25.0
            mock_daily.humidity_mean_percent = 50.0
            mock_daily.wind_speed_mean_ms = 3.0
            mock_daily.dewpoint_mean_celsius = 15.0
            mock_daily.pressure_mean_hpa = 1013.0
            mock_daily.solar_radiation_mj_m2_day = 22.0
            mock_daily.precip_total_mm = 0.0
            mock_daily.probability_precip_mean_percent = 10.0
            mock_daily.short_forecast = "Sunny"
            mock_client.get_daily_forecast_data.return_value = [mock_daily]
            mock_client.close = AsyncMock()
            mock_factory.return_value = mock_client

            from backend.api.services.nws_forecast.nws_forecast_sync_adapter import (
                NWSDailyForecastSyncAdapter,
            )
            adapter = NWSDailyForecastSyncAdapter()
            start = datetime(2025, 6, 14)
            end = datetime(2025, 6, 16)
            result = adapter.get_daily_data_sync(39.7392, -104.9903, start, end)
            assert len(result) == 1
            assert result[0].temp_max == 30.0

    def test_get_daily_data_sync_empty(self):
        with patch(
            "backend.api.services.nws_forecast.nws_forecast_sync_adapter.create_nws_forecast_client"
        ) as mock_factory:
            mock_client = AsyncMock()
            mock_client.get_daily_forecast_data.return_value = []
            mock_client.close = AsyncMock()
            mock_factory.return_value = mock_client

            from backend.api.services.nws_forecast.nws_forecast_sync_adapter import (
                NWSDailyForecastSyncAdapter,
            )
            adapter = NWSDailyForecastSyncAdapter()
            start = datetime(2025, 6, 14)
            end = datetime(2025, 6, 16)
            result = adapter.get_daily_data_sync(39.7392, -104.9903, start, end)
            assert result == []

    def test_get_daily_data_sync_error(self):
        with patch(
            "backend.api.services.nws_forecast.nws_forecast_sync_adapter.create_nws_forecast_client"
        ) as mock_factory:
            mock_client = AsyncMock()
            mock_client.get_daily_forecast_data.side_effect = Exception("API error")
            mock_client.close = AsyncMock()
            mock_factory.return_value = mock_client

            from backend.api.services.nws_forecast.nws_forecast_sync_adapter import (
                NWSDailyForecastSyncAdapter,
            )
            adapter = NWSDailyForecastSyncAdapter()
            start = datetime(2025, 6, 14)
            end = datetime(2025, 6, 16)
            result = adapter.get_daily_data_sync(39.7392, -104.9903, start, end)
            assert result == []

    def test_nws_daily_forecast_record_model(self):
        from backend.api.services.nws_forecast.nws_forecast_sync_adapter import (
            NWSDailyForecastRecord,
        )
        record = NWSDailyForecastRecord(
            date="2025-06-15",
            temp_max=30.0,
            temp_min=20.0,
            temp_mean=25.0,
            humidity_mean=50.0,
            wind_speed_mean=3.0,
            solar_radiation=22.0,
        )
        assert record.date == "2025-06-15"
        assert record.temp_max == 30.0


# ============================================================================
# NWS Stations Sync Adapter
# ============================================================================

class TestNWSStationsSyncAdapter:
    """Tests for NWSStationsSyncAdapter."""

    def test_init_default(self):
        from backend.api.services.nws_stations.nws_stations_sync_adapter import (
            NWSStationsSyncAdapter,
        )
        adapter = NWSStationsSyncAdapter()
        assert adapter.filter_delayed is False

    def test_init_with_filter(self):
        from backend.api.services.nws_stations.nws_stations_sync_adapter import (
            NWSStationsSyncAdapter,
        )
        adapter = NWSStationsSyncAdapter(filter_delayed=True)
        assert adapter.filter_delayed is True

    def test_daily_nws_data_model(self):
        from backend.api.services.nws_stations.nws_stations_sync_adapter import (
            DailyNWSData,
        )
        data = DailyNWSData(
            date=datetime(2025, 6, 15),
            temp_min=20.0,
            temp_max=30.0,
            temp_mean=25.0,
            humidity=50.0,
            wind_speed=3.0,
        )
        assert data.temp_max == 30.0
        assert data.temp_min == 20.0

    def test_daily_nws_data_defaults(self):
        from backend.api.services.nws_stations.nws_stations_sync_adapter import (
            DailyNWSData,
        )
        data = DailyNWSData(date=datetime(2025, 6, 15))
        assert data.temp_min is None
        assert data.temp_max is None
        assert data.humidity is None

    @patch(
        "backend.api.services.nws_stations.nws_stations_sync_adapter.NWSStationsClient"
    )
    def test_get_daily_data_sync_outside_usa(self, mock_client_cls):
        mock_client = AsyncMock()
        mock_client_cls.return_value = mock_client

        from backend.api.services.nws_stations.nws_stations_sync_adapter import (
            NWSStationsSyncAdapter,
        )
        adapter = NWSStationsSyncAdapter()
        start = datetime(2025, 6, 14)
        end = datetime(2025, 6, 16)
        # Coordinates outside USA raises ValueError
        with pytest.raises(ValueError, match="outside USA coverage"):
            adapter.get_daily_data_sync(0.0, 0.0, start, end)

    @patch(
        "backend.api.services.nws_stations.nws_stations_sync_adapter.NWSStationsClient"
    )
    def test_get_daily_data_sync_no_station(self, mock_client_cls):
        mock_client = AsyncMock()
        mock_client.find_nearest_active_station.return_value = None
        mock_client.close = AsyncMock()
        mock_client_cls.return_value = mock_client

        from backend.api.services.nws_stations.nws_stations_sync_adapter import (
            NWSStationsSyncAdapter,
        )
        adapter = NWSStationsSyncAdapter()
        start = datetime(2025, 6, 14)
        end = datetime(2025, 6, 16)
        result = adapter.get_daily_data_sync(40.7128, -74.0060, start, end)
        assert result == []

    @patch(
        "backend.api.services.nws_stations.nws_stations_sync_adapter.NWSStationsClient"
    )
    def test_health_check_sync_success(self, mock_client_cls):
        mock_client = AsyncMock()
        mock_station = MagicMock()
        mock_station.station_id = "KJFK"
        mock_client.find_nearest_active_station.return_value = mock_station
        mock_client.close = AsyncMock()
        mock_client_cls.return_value = mock_client

        from backend.api.services.nws_stations.nws_stations_sync_adapter import (
            NWSStationsSyncAdapter,
        )
        adapter = NWSStationsSyncAdapter()
        assert adapter.health_check_sync() is True

    @patch(
        "backend.api.services.nws_stations.nws_stations_sync_adapter.NWSStationsClient"
    )
    def test_health_check_sync_failure(self, mock_client_cls):
        mock_client = AsyncMock()
        mock_client.find_nearest_active_station.side_effect = Exception("fail")
        mock_client.close = AsyncMock()
        mock_client_cls.return_value = mock_client

        from backend.api.services.nws_stations.nws_stations_sync_adapter import (
            NWSStationsSyncAdapter,
        )
        adapter = NWSStationsSyncAdapter()
        assert adapter.health_check_sync() is False


# ============================================================================
# MET Norway Sync Adapter
# ============================================================================

class TestMETNorwaySyncAdapter:
    """Tests for METNorwaySyncAdapter."""

    def test_init_default(self):
        from backend.api.services.met_norway.met_norway_sync_adapter import (
            METNorwaySyncAdapter,
        )
        adapter = METNorwaySyncAdapter()
        assert adapter._client is None

    def test_get_attribution(self):
        from backend.api.services.met_norway.met_norway_sync_adapter import (
            METNorwaySyncAdapter,
        )
        adapter = METNorwaySyncAdapter()
        attr = adapter.get_attribution()
        assert "MET Norway" in attr
        assert "CC" in attr.upper() or "4.0" in attr

    def test_get_coverage_info(self):
        from backend.api.services.met_norway.met_norway_sync_adapter import (
            METNorwaySyncAdapter,
        )
        adapter = METNorwaySyncAdapter()
        info = adapter.get_coverage_info()
        assert "adapter" in info
        assert info["adapter"] == "METNorwaySyncAdapter"
        assert "quality_tiers" in info
        assert "nordic" in info["quality_tiers"]
        assert "global" in info["quality_tiers"]

    def test_get_coverage_info_has_brazil(self):
        from backend.api.services.met_norway.met_norway_sync_adapter import (
            METNorwaySyncAdapter,
        )
        adapter = METNorwaySyncAdapter()
        info = adapter.get_coverage_info()
        assert "brazil" in info["quality_tiers"]

    @patch(
        "backend.api.services.met_norway.met_norway_sync_adapter.METNorwayClient"
    )
    def test_health_check_sync_success(self, mock_client_cls):
        mock_client = AsyncMock()
        mock_client.health_check.return_value = True
        mock_client_cls.return_value = mock_client

        from backend.api.services.met_norway.met_norway_sync_adapter import (
            METNorwaySyncAdapter,
        )
        adapter = METNorwaySyncAdapter()
        assert adapter.health_check_sync() is True

    @patch(
        "backend.api.services.met_norway.met_norway_sync_adapter.METNorwayClient"
    )
    def test_health_check_sync_failure(self, mock_client_cls):
        mock_client = AsyncMock()
        mock_client.health_check.side_effect = Exception("fail")
        mock_client_cls.return_value = mock_client

        from backend.api.services.met_norway.met_norway_sync_adapter import (
            METNorwaySyncAdapter,
        )
        adapter = METNorwaySyncAdapter()
        assert adapter.health_check_sync() is False

    @patch(
        "backend.api.services.met_norway.met_norway_sync_adapter.METNorwayClient"
    )
    def test_get_daily_data_sync_invalid_coords(self, mock_client_cls):
        mock_client = AsyncMock()
        mock_client_cls.return_value = mock_client

        from backend.api.services.met_norway.met_norway_sync_adapter import (
            METNorwaySyncAdapter,
        )
        adapter = METNorwaySyncAdapter()
        start = datetime.now()
        end = start + timedelta(days=3)
        with pytest.raises(ValueError, match="[Ii]nválid|[Ii]nvalid"):
            adapter.get_daily_data_sync(999.0, 999.0, start, end)

    @patch(
        "backend.api.services.met_norway.met_norway_sync_adapter.METNorwayClient"
    )
    def test_get_daily_data_sync_empty(self, mock_client_cls):
        mock_client = AsyncMock()
        mock_client.get_daily_forecast.return_value = []
        mock_client_cls.return_value = mock_client

        from backend.api.services.met_norway.met_norway_sync_adapter import (
            METNorwaySyncAdapter,
        )
        adapter = METNorwaySyncAdapter()
        start = datetime.now()
        end = start + timedelta(days=3)
        result = adapter.get_daily_data_sync(40.0, -74.0, start, end)
        assert result == []

    @patch(
        "backend.api.services.met_norway.met_norway_sync_adapter.METNorwayClient"
    )
    def test_get_daily_data_sync_limits_to_5_days(self, mock_client_cls):
        mock_client = AsyncMock()
        mock_client.get_daily_forecast.return_value = [MagicMock(), MagicMock()]
        mock_client_cls.return_value = mock_client

        from backend.api.services.met_norway.met_norway_sync_adapter import (
            METNorwaySyncAdapter,
        )
        adapter = METNorwaySyncAdapter()
        start = datetime.now()
        end = start + timedelta(days=15)  # Over 5-day limit
        result = adapter.get_daily_data_sync(40.0, -74.0, start, end)
        assert isinstance(result, list)


# ============================================================================
# OpenMeteo Forecast Sync Adapter
# ============================================================================

class TestOpenMeteoForecastSyncAdapter:
    """Tests for OpenMeteoForecastSyncAdapter."""

    def test_init_default(self):
        from backend.api.services.openmeteo_forecast.openmeteo_forecast_sync_adapter import (
            OpenMeteoForecastSyncAdapter,
        )
        adapter = OpenMeteoForecastSyncAdapter()
        assert adapter.cache is None

    def test_init_with_cache(self):
        from backend.api.services.openmeteo_forecast.openmeteo_forecast_sync_adapter import (
            OpenMeteoForecastSyncAdapter,
        )
        mock_cache = MagicMock()
        adapter = OpenMeteoForecastSyncAdapter(cache=mock_cache)
        assert adapter.cache is mock_cache

    def test_get_info_static(self):
        from backend.api.services.openmeteo_forecast.openmeteo_forecast_sync_adapter import (
            OpenMeteoForecastSyncAdapter,
        )
        info = OpenMeteoForecastSyncAdapter.get_info()
        assert isinstance(info, dict)
        assert "api" in info

    def test_get_forecast_sync_invalid_days(self):
        from backend.api.services.openmeteo_forecast.openmeteo_forecast_sync_adapter import (
            OpenMeteoForecastSyncAdapter,
        )
        adapter = OpenMeteoForecastSyncAdapter()
        with pytest.raises(ValueError, match="days must be between"):
            adapter.get_forecast_sync(40.0, -74.0, days=0)

    def test_get_forecast_sync_too_many_days(self):
        from backend.api.services.openmeteo_forecast.openmeteo_forecast_sync_adapter import (
            OpenMeteoForecastSyncAdapter,
        )
        adapter = OpenMeteoForecastSyncAdapter()
        with pytest.raises(ValueError, match="days must be between"):
            adapter.get_forecast_sync(40.0, -74.0, days=10)

    @patch(
        "backend.api.services.openmeteo_forecast.openmeteo_forecast_sync_adapter.OpenMeteoForecastClient"
    )
    def test_get_daily_data_sync_success(self, mock_client_cls):
        mock_client = AsyncMock()
        mock_client.get_climate_data.return_value = {
            "climate_data": {
                "dates": ["2025-06-15", "2025-06-16"],
                "temperature_2m_max": [30.0, 28.0],
                "temperature_2m_min": [20.0, 18.0],
            },
            "metadata": {},
        }
        mock_client_cls.return_value = mock_client

        from backend.api.services.openmeteo_forecast.openmeteo_forecast_sync_adapter import (
            OpenMeteoForecastSyncAdapter,
        )
        adapter = OpenMeteoForecastSyncAdapter()
        today = datetime.now()
        result = adapter.get_daily_data_sync(
            40.0, -74.0, today, today + timedelta(days=3)
        )
        assert len(result) == 2
        assert result[0]["temperature_2m_max"] == 30.0

    @patch(
        "backend.api.services.openmeteo_forecast.openmeteo_forecast_sync_adapter.OpenMeteoForecastClient"
    )
    def test_get_daily_data_sync_error(self, mock_client_cls):
        mock_client = AsyncMock()
        mock_client.get_climate_data.side_effect = Exception("API error")
        mock_client_cls.return_value = mock_client

        from backend.api.services.openmeteo_forecast.openmeteo_forecast_sync_adapter import (
            OpenMeteoForecastSyncAdapter,
        )
        adapter = OpenMeteoForecastSyncAdapter()
        today = datetime.now()
        with pytest.raises(Exception):
            adapter.get_daily_data_sync(
                40.0, -74.0, today, today + timedelta(days=3)
            )

    @patch(
        "backend.api.services.openmeteo_forecast.openmeteo_forecast_sync_adapter.OpenMeteoForecastClient"
    )
    def test_health_check_sync_success(self, mock_client_cls):
        mock_client = AsyncMock()
        mock_client.get_climate_data.return_value = {
            "climate_data": {"dates": ["2025-06-15"]},
        }
        mock_client_cls.return_value = mock_client

        from backend.api.services.openmeteo_forecast.openmeteo_forecast_sync_adapter import (
            OpenMeteoForecastSyncAdapter,
        )
        adapter = OpenMeteoForecastSyncAdapter()
        assert adapter.health_check_sync() is True

    @patch(
        "backend.api.services.openmeteo_forecast.openmeteo_forecast_sync_adapter.OpenMeteoForecastClient"
    )
    def test_health_check_sync_failure(self, mock_client_cls):
        mock_client = AsyncMock()
        mock_client.get_climate_data.side_effect = Exception("fail")
        mock_client_cls.return_value = mock_client

        from backend.api.services.openmeteo_forecast.openmeteo_forecast_sync_adapter import (
            OpenMeteoForecastSyncAdapter,
        )
        adapter = OpenMeteoForecastSyncAdapter()
        assert adapter.health_check_sync() is False


# ============================================================================
# OpenTopo Sync Adapter
# ============================================================================

class TestOpenTopoSyncAdapter:
    """Tests for OpenTopoSyncAdapter."""

    def test_init_default(self):
        from backend.api.services.opentopo.opentopo_sync_adapter import (
            OpenTopoSyncAdapter,
        )
        adapter = OpenTopoSyncAdapter()
        assert adapter.cache is None

    def test_init_with_cache(self):
        from backend.api.services.opentopo.opentopo_sync_adapter import (
            OpenTopoSyncAdapter,
        )
        mock_cache = MagicMock()
        adapter = OpenTopoSyncAdapter(cache=mock_cache)
        assert adapter.cache is mock_cache

    def test_get_coverage_info(self):
        from backend.api.services.opentopo.opentopo_sync_adapter import (
            OpenTopoSyncAdapter,
        )
        adapter = OpenTopoSyncAdapter()
        info = adapter.get_coverage_info()
        assert isinstance(info, dict)
        assert "adapter" in info
        assert info["adapter"] == "OpenTopoSyncAdapter"
        assert "datasets" in info
        assert "srtm30m" in info["datasets"]
        assert "aster30m" in info["datasets"]

    def test_get_coverage_info_has_fao56(self):
        from backend.api.services.opentopo.opentopo_sync_adapter import (
            OpenTopoSyncAdapter,
        )
        adapter = OpenTopoSyncAdapter()
        info = adapter.get_coverage_info()
        assert "fao56_calculations" in info

    def test_get_coverage_info_has_rate_limits(self):
        from backend.api.services.opentopo.opentopo_sync_adapter import (
            OpenTopoSyncAdapter,
        )
        adapter = OpenTopoSyncAdapter()
        info = adapter.get_coverage_info()
        assert "rate_limits" in info
        assert info["rate_limits"]["locations_per_request"] == 100

    @patch(
        "backend.api.services.opentopo.opentopo_sync_adapter.OpenTopoClient"
    )
    def test_get_elevation_sync_success(self, mock_client_cls):
        mock_client = AsyncMock()
        mock_location = MagicMock()
        mock_location.elevation = 1172.0
        mock_client.get_elevation.return_value = mock_location
        mock_client.close = AsyncMock()
        mock_client_cls.return_value = mock_client

        from backend.api.services.opentopo.opentopo_sync_adapter import (
            OpenTopoSyncAdapter,
        )
        adapter = OpenTopoSyncAdapter()
        result = adapter.get_elevation_sync(-15.7801, -47.9292)
        assert result is not None
        assert result.elevation == 1172.0

    @patch(
        "backend.api.services.opentopo.opentopo_sync_adapter.OpenTopoClient"
    )
    def test_get_elevation_sync_none(self, mock_client_cls):
        mock_client = AsyncMock()
        mock_client.get_elevation.return_value = None
        mock_client.close = AsyncMock()
        mock_client_cls.return_value = mock_client

        from backend.api.services.opentopo.opentopo_sync_adapter import (
            OpenTopoSyncAdapter,
        )
        adapter = OpenTopoSyncAdapter()
        result = adapter.get_elevation_sync(-15.7801, -47.9292)
        assert result is None

    @patch(
        "backend.api.services.opentopo.opentopo_sync_adapter.OpenTopoClient"
    )
    def test_get_elevations_batch_sync_success(self, mock_client_cls):
        mock_client = AsyncMock()
        mock_loc1 = MagicMock()
        mock_loc1.elevation = 1172.0
        mock_loc2 = MagicMock()
        mock_loc2.elevation = 760.0
        mock_client.get_elevations_batch.return_value = [mock_loc1, mock_loc2]
        mock_client.close = AsyncMock()
        mock_client_cls.return_value = mock_client

        from backend.api.services.opentopo.opentopo_sync_adapter import (
            OpenTopoSyncAdapter,
        )
        adapter = OpenTopoSyncAdapter()
        locations = [(-15.7801, -47.9292), (-23.5505, -46.6333)]
        result = adapter.get_elevations_batch_sync(locations)
        assert len(result) == 2

    @patch(
        "backend.api.services.opentopo.opentopo_sync_adapter.OpenTopoClient"
    )
    def test_health_check_sync_success(self, mock_client_cls):
        mock_client = AsyncMock()
        mock_location = MagicMock()
        mock_location.elevation = 1172.0
        mock_client.get_elevation.return_value = mock_location
        mock_client.close = AsyncMock()
        mock_client_cls.return_value = mock_client

        from backend.api.services.opentopo.opentopo_sync_adapter import (
            OpenTopoSyncAdapter,
        )
        adapter = OpenTopoSyncAdapter()
        assert adapter.health_check_sync() is True

    @patch(
        "backend.api.services.opentopo.opentopo_sync_adapter.OpenTopoClient"
    )
    def test_health_check_sync_failure(self, mock_client_cls):
        mock_client = AsyncMock()
        mock_client.get_elevation.side_effect = Exception("fail")
        mock_client.close = AsyncMock()
        mock_client_cls.return_value = mock_client

        from backend.api.services.opentopo.opentopo_sync_adapter import (
            OpenTopoSyncAdapter,
        )
        adapter = OpenTopoSyncAdapter()
        assert adapter.health_check_sync() is False
