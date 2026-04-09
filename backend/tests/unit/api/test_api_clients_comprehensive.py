"""
Comprehensive tests for API service clients:
- NWS Stations (pure-logic methods)
- OpenMeteo Archive (validation, cache key)
- OpenMeteo Forecast (wind conversion, validation, TTL)
- NASA POWER (_parse_response, _format_date)
- MET Norway (pure helpers)
- OpenTopo models
"""
from datetime import datetime, date, timedelta
from unittest.mock import patch

import numpy as np
import pytest


# ════════════════════════════════════════════════════════════════
# NWS Stations Client — Pure-logic methods
# ════════════════════════════════════════════════════════════════
class TestNWSStationsHelpers:

    def _make_client(self):
        with patch("httpx.AsyncClient"):
            from backend.api.services.nws_stations.nws_stations_client import (
                NWSStationsClient, NWSStationsConfig,
            )
            return NWSStationsClient(config=NWSStationsConfig())

    def test_val_dict_with_value(self):
        client = self._make_client()
        assert client._val({"value": 25.5}) == 25.5

    def test_val_none_data(self):
        client = self._make_client()
        assert client._val(None) is None

    def test_val_none_value(self):
        client = self._make_client()
        assert client._val({"value": None}) is None

    def test_val_empty_dict(self):
        client = self._make_client()
        assert client._val({}) is None

    def test_extract_wind_speed_ms_conversion(self):
        from backend.api.services.nws_stations.nws_stations_client import NWSStationsClient
        # 36 km/h → 10 m/s
        result = NWSStationsClient._extract_wind_speed_ms({"value": 36.0})
        assert result is not None
        assert abs(result - 10.0) < 0.1

    def test_extract_wind_speed_ms_none(self):
        from backend.api.services.nws_stations.nws_stations_client import NWSStationsClient
        assert NWSStationsClient._extract_wind_speed_ms(None) is None

    def test_convert_wind_to_2m_standard(self):
        """10m wind to 2m (FAO-56 Eq. 47)"""
        from backend.api.services.nws_stations.nws_stations_client import NWSStationsClient
        # 5 m/s at 10m → ~3.8 m/s at 2m (factor ≈ 0.748)
        result = NWSStationsClient.convert_wind_to_2m(5.0, z=10.0)
        assert result is not None
        assert 3.0 < result < 4.5

    def test_convert_wind_to_2m_at_2m(self):
        """Already at 2m → same value"""
        from backend.api.services.nws_stations.nws_stations_client import NWSStationsClient
        result = NWSStationsClient.convert_wind_to_2m(3.0, z=2.0)
        assert result is not None
        assert abs(result - 3.0) < 0.5

    def test_convert_wind_to_2m_minimum(self):
        """Very low wind → enforced minimum 0.5"""
        from backend.api.services.nws_stations.nws_stations_client import NWSStationsClient
        result = NWSStationsClient.convert_wind_to_2m(0.1, z=10.0)
        assert result >= 0.5

    def test_convert_wind_to_2m_none(self):
        from backend.api.services.nws_stations.nws_stations_client import NWSStationsClient
        assert NWSStationsClient.convert_wind_to_2m(None) is None

    def test_get_data_availability_info(self):
        from backend.api.services.nws_stations.nws_stations_client import NWSStationsClient
        info = NWSStationsClient.get_data_availability_info()
        assert isinstance(info, dict)

    def test_pydantic_models(self):
        from backend.api.services.nws_stations.nws_stations_client import (
            NWSStation, NWSObservation, DailyEToData,
        )
        station = NWSStation(
            station_id="KJFK", name="JFK Airport",
            latitude=40.64, longitude=-73.78,
            elevation_m=3.9, timezone="America/New_York",
            distance_km=5.0, is_active=True,
        )
        assert station.station_id == "KJFK"

    def test_aggregate_to_daily(self):
        """Test daily aggregation from observations"""
        from backend.api.services.nws_stations.nws_stations_client import (
            NWSStationsClient, NWSStation, NWSObservation,
        )
        client = self._make_client()
        station = NWSStation(
            station_id="KJFK", name="JFK Airport",
            latitude=40.64, longitude=-73.78,
            elevation_m=3.9, timezone="America/New_York",
            distance_km=5.0, is_active=True,
        )
        now = datetime.now()
        obs = [
            NWSObservation(
                station_id="KJFK",
                timestamp=now.replace(hour=h).isoformat(),
                temp_celsius=20.0 + h * 0.5,
                dewpoint_celsius=12.0,
                humidity_percent=65.0,
                wind_speed_ms=3.0,
                wind_speed_2m_ms=2.3,
            )
            for h in range(0, 24, 3)  # 8 observations
        ]
        result = client.aggregate_to_daily(obs, station)
        assert isinstance(result, list)


# ════════════════════════════════════════════════════════════════
# OpenMeteo Archive Client — Pure-logic
# ════════════════════════════════════════════════════════════════
class TestOpenMeteoArchiveHelpers:

    def _make_client(self):
        with patch("openmeteo_requests.Client"):
            from backend.api.services.openmeteo_archive.openmeteo_archive_client import (
                OpenMeteoArchiveClient,
            )
            return OpenMeteoArchiveClient(cache=None)

    def test_get_cache_key(self):
        client = self._make_client()
        key = client._get_cache_key(-23.55, -46.63, "2024-01-01", "2024-01-31")
        assert "openmeteo" in key.lower() or "climate" in key.lower()
        assert isinstance(key, str)

    def test_validate_inputs_valid(self):
        client = self._make_client()
        # Should not raise
        client._validate_inputs(-23.55, -46.63, "2024-01-01", "2024-06-30")

    def test_validate_inputs_invalid_coords(self):
        client = self._make_client()
        with pytest.raises((ValueError, Exception)):
            client._validate_inputs(100, -46.63, "2024-01-01", "2024-06-30")

    def test_validate_inputs_start_after_end(self):
        client = self._make_client()
        with pytest.raises((ValueError, Exception)):
            client._validate_inputs(-23.55, -46.63, "2024-12-31", "2024-01-01")

    def test_validate_inputs_too_early(self):
        """Before 1990 → should raise"""
        client = self._make_client()
        with pytest.raises((ValueError, Exception)):
            client._validate_inputs(-23.55, -46.63, "1989-01-01", "1989-12-31")

    def test_get_info(self):
        from backend.api.services.openmeteo_archive.openmeteo_archive_client import OpenMeteoArchiveClient
        info = OpenMeteoArchiveClient.get_info()
        assert isinstance(info, dict)

    def test_config_constants(self):
        from backend.api.services.openmeteo_archive.openmeteo_archive_client import OpenMeteoArchiveConfig
        assert OpenMeteoArchiveConfig.MIN_DATE.year == 1990
        assert OpenMeteoArchiveConfig.CACHE_TTL > 0
        assert len(OpenMeteoArchiveConfig.DAILY_VARIABLES) >= 5


# ════════════════════════════════════════════════════════════════
# OpenMeteo Forecast Client — Pure-logic
# ════════════════════════════════════════════════════════════════
class TestOpenMeteoForecastHelpers:

    def _make_client(self):
        with patch("openmeteo_requests.Client"):
            from backend.api.services.openmeteo_forecast.openmeteo_forecast_client import (
                OpenMeteoForecastClient,
            )
            return OpenMeteoForecastClient(cache=None)

    def test_convert_wind_10m_to_2m_numpy(self):
        """Vectorized wind conversion on numpy arrays"""
        from backend.api.services.openmeteo_forecast.openmeteo_forecast_client import OpenMeteoForecastClient
        u10 = np.array([5.0, 10.0, 0.1])
        result = OpenMeteoForecastClient.convert_wind_10m_to_2m(u10, height=10.0)
        assert isinstance(result, np.ndarray)
        assert len(result) == 3
        # 5 m/s at 10m → ~3.8 m/s at 2m
        assert 3.0 < result[0] < 4.5
        # Very low wind → min 0.5
        assert result[2] >= 0.5

    def test_convert_wind_at_2m_passthrough(self):
        """height=2 → no conversion needed"""
        from backend.api.services.openmeteo_forecast.openmeteo_forecast_client import OpenMeteoForecastClient
        u2 = np.array([3.0, 5.0])
        result = OpenMeteoForecastClient.convert_wind_10m_to_2m(u2, height=2.0)
        # Should be very close to input
        np.testing.assert_allclose(result, u2, atol=0.5)

    def test_get_cache_key(self):
        client = self._make_client()
        key = client._get_cache_key(-23.55, -46.63, "2025-01-01", "2025-01-06")
        assert isinstance(key, str)

    def test_get_ttl_future_dates(self):
        """Future dates → shorter TTL"""
        client = self._make_client()
        today = date.today()
        future_start = (today + timedelta(days=1)).isoformat()
        future_end = (today + timedelta(days=5)).isoformat()
        ttl = client._get_ttl_seconds(future_start, future_end)
        assert ttl <= 21600  # ≤ 6 hours for forecasts

    def test_get_ttl_past_dates(self):
        """Past dates → longer TTL"""
        client = self._make_client()
        past_start = "2024-01-01"
        past_end = "2024-01-30"
        ttl = client._get_ttl_seconds(past_start, past_end)
        assert ttl >= 3600

    def test_validate_inputs_valid(self):
        client = self._make_client()
        today = date.today()
        # Valid range: today-29d to today+5d
        start = (today - timedelta(days=10)).strftime("%Y-%m-%d")
        end = (today + timedelta(days=3)).strftime("%Y-%m-%d")
        client._validate_inputs(-23.55, -46.63, start, end)

    def test_validate_inputs_invalid_coords(self):
        client = self._make_client()
        with pytest.raises((ValueError, Exception)):
            client._validate_inputs(200, 0, "2025-01-01", "2025-01-06")

    def test_get_info(self):
        from backend.api.services.openmeteo_forecast.openmeteo_forecast_client import OpenMeteoForecastClient
        info = OpenMeteoForecastClient.get_info()
        assert isinstance(info, dict)

    def test_config_constants(self):
        from backend.api.services.openmeteo_forecast.openmeteo_forecast_client import OpenMeteoForecastConfig
        assert OpenMeteoForecastConfig.MAX_PAST_DAYS >= 29
        assert OpenMeteoForecastConfig.MAX_FUTURE_DAYS >= 5
        assert len(OpenMeteoForecastConfig.DAILY_VARIABLES) >= 5


# ════════════════════════════════════════════════════════════════
# NASA POWER Client — _parse_response, _format_date
# ════════════════════════════════════════════════════════════════
class TestNASAPowerHelpers:

    def _make_client(self):
        with patch("httpx.AsyncClient"):
            from backend.api.services.nasa_power.nasa_power_client import (
                NASAPowerClient, NASAPowerConfig,
            )
            return NASAPowerClient(config=NASAPowerConfig())

    def test_format_date(self):
        client = self._make_client()
        result = client._format_date("20240115")
        assert result == "2024-01-15"

    def test_parse_response_basic(self):
        client = self._make_client()
        data = {
            "properties": {
                "parameter": {
                    "T2M_MAX": {"20240101": 30.0, "20240102": 31.0},
                    "T2M_MIN": {"20240101": 18.0, "20240102": 19.0},
                    "T2M": {"20240101": 24.0, "20240102": 25.0},
                    "RH2M": {"20240101": 65.0, "20240102": 60.0},
                    "WS2M": {"20240101": 2.5, "20240102": 3.0},
                    "ALLSKY_SFC_SW_DWN": {"20240101": 20.0, "20240102": 22.0},
                    "PRECTOTCORR": {"20240101": 0.0, "20240102": 5.0},
                },
            },
        }
        result = client._parse_response(data)
        assert len(result) == 2
        assert result[0].date == "2024-01-01"
        assert result[0].temp_max == 30.0
        assert result[0].temp_min == 18.0
        assert result[1].precipitation == 5.0

    def test_parse_response_empty_params(self):
        client = self._make_client()
        data = {"properties": {"parameter": {}}}
        # Empty params → StopIteration (no dates to iterate)
        with pytest.raises(StopIteration):
            client._parse_response(data)

    def test_parse_response_missing_properties(self):
        client = self._make_client()
        data = {}
        # Missing properties key → ValueError
        with pytest.raises((KeyError, AttributeError, TypeError, ValueError)):
            client._parse_response(data)

    def test_pydantic_models(self):
        from backend.api.services.nasa_power.nasa_power_client import (
            NASAPowerConfig, NASAPowerData,
        )
        cfg = NASAPowerConfig()
        assert cfg.timeout > 0
        d = NASAPowerData(date="2024-01-01", temp_max=30.0, temp_min=18.0)
        assert d.temp_max == 30.0

    def test_get_data_availability_info(self):
        from backend.api.services.nasa_power.nasa_power_client import NASAPowerClient
        info = NASAPowerClient.get_data_availability_info()
        assert isinstance(info, dict)


# ════════════════════════════════════════════════════════════════
# MET Norway Client — Pure helpers
# ════════════════════════════════════════════════════════════════
class TestMETNorwayHelpers:

    def test_round_coordinates(self):
        from backend.api.services.met_norway.met_norway_client import METNorwayClient
        lat, lon = METNorwayClient._round_coordinates(59.91234567, 10.75234567)
        assert lat == round(59.91234567, 4)
        assert lon == round(10.75234567, 4)

    def test_is_in_nordic_oslo(self):
        from backend.api.services.met_norway.met_norway_client import METNorwayClient
        assert METNorwayClient.is_in_nordic_region(59.91, 10.75) is True

    def test_is_in_nordic_sao_paulo(self):
        from backend.api.services.met_norway.met_norway_client import METNorwayClient
        assert METNorwayClient.is_in_nordic_region(-23.55, -46.63) is False

    def test_get_recommended_variables_nordic(self):
        from backend.api.services.met_norway.met_norway_client import METNorwayClient
        vars_nordic = METNorwayClient.get_recommended_variables(59.91, 10.75)
        assert isinstance(vars_nordic, list)
        # Nordic should have more variables (including precip)
        assert len(vars_nordic) >= 4

    def test_get_recommended_variables_global(self):
        from backend.api.services.met_norway.met_norway_client import METNorwayClient
        vars_global = METNorwayClient.get_recommended_variables(0, 0)
        assert isinstance(vars_global, list)

    def test_get_attribution(self):
        with patch("httpx.AsyncClient"):
            from backend.api.services.met_norway.met_norway_client import METNorwayClient
            client = METNorwayClient()
            attr = client.get_attribution()
            assert isinstance(attr, str) or isinstance(attr, dict)

    def test_get_coverage_info(self):
        with patch("httpx.AsyncClient"):
            from backend.api.services.met_norway.met_norway_client import METNorwayClient
            client = METNorwayClient()
            info = client.get_coverage_info()
            assert isinstance(info, dict)

    def test_get_data_availability_info(self):
        from backend.api.services.met_norway.met_norway_client import METNorwayClient
        info = METNorwayClient.get_data_availability_info()
        assert isinstance(info, dict)

    def test_pydantic_models(self):
        from backend.api.services.met_norway.met_norway_client import (
            METNorwayDailyData, METNorwayConfig,
        )
        cfg = METNorwayConfig()
        assert cfg.timeout > 0
        d = METNorwayDailyData(
            date=datetime.now().date(),
            temp_max=25.0, temp_min=15.0, temp_mean=20.0,
            humidity_mean=65.0,
        )
        assert d.source == "met_norway"


# ════════════════════════════════════════════════════════════════
# OpenTopo Client — Models and helpers
# ════════════════════════════════════════════════════════════════
class TestOpenTopoHelpers:

    def test_config_defaults(self):
        from backend.api.services.opentopo.opentopo_client import (
            OpenTopoConfig, OpenTopoLocation,
        )
        cfg = OpenTopoConfig()
        assert cfg.timeout > 0
        assert "srtm" in cfg.default_dataset.lower() or "aster" in cfg.default_dataset.lower()

    def test_location_model(self):
        from backend.api.services.opentopo.opentopo_client import OpenTopoLocation
        loc = OpenTopoLocation(
            lat=-15.78, lon=-47.93, elevation=1172.0, dataset="srtm30m",
        )
        assert loc.elevation == 1172.0
        assert loc.dataset == "srtm30m"


# ════════════════════════════════════════════════════════════════
# Historical Loader — ThreadSafeCache
# ════════════════════════════════════════════════════════════════
class TestThreadSafeCache:

    def test_get_set_basic(self):
        from backend.core.data_processing.historical_loader import ThreadSafeCache
        cache = ThreadSafeCache(max_size=5)
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"

    def test_get_missing(self):
        from backend.core.data_processing.historical_loader import ThreadSafeCache
        cache = ThreadSafeCache()
        assert cache.get("nonexistent") is None

    def test_lru_eviction(self):
        """When max_size exceeded, oldest items evicted"""
        from backend.core.data_processing.historical_loader import ThreadSafeCache
        cache = ThreadSafeCache(max_size=3)
        cache.set("a", 1)
        cache.set("b", 2)
        cache.set("c", 3)
        cache.set("d", 4)  # Should evict "a"
        assert cache.get("a") is None
        assert cache.get("d") == 4

    def test_clear(self):
        from backend.core.data_processing.historical_loader import ThreadSafeCache
        cache = ThreadSafeCache()
        cache.set("k", "v")
        cache.clear()
        assert cache.get("k") is None

    def test_access_refreshes_position(self):
        """Accessing an item refreshes its LRU position"""
        from backend.core.data_processing.historical_loader import ThreadSafeCache
        cache = ThreadSafeCache(max_size=3)
        cache.set("a", 1)
        cache.set("b", 2)
        cache.set("c", 3)
        cache.get("a")  # Access "a" → moves to most recent
        cache.set("d", 4)  # Should evict "b" (oldest unused)
        assert cache.get("a") == 1  # Still there
        assert cache.get("b") is None  # Evicted

    def test_overwrite_key(self):
        from backend.core.data_processing.historical_loader import ThreadSafeCache
        cache = ThreadSafeCache()
        cache.set("k", "old")
        cache.set("k", "new")
        assert cache.get("k") == "new"


# ════════════════════════════════════════════════════════════════
# Sync Adapters — smoke tests
# ════════════════════════════════════════════════════════════════
class TestSyncAdapters:

    def test_nws_forecast_sync_adapter_exists(self):
        from backend.api.services.nws_forecast.nws_forecast_sync_adapter import (
            NWSDailyForecastSyncAdapter,
        )
        assert NWSDailyForecastSyncAdapter is not None

    def test_nws_stations_sync_adapter_exists(self):
        from backend.api.services.nws_stations.nws_stations_sync_adapter import (
            NWSStationsSyncAdapter,
        )
        assert NWSStationsSyncAdapter is not None

    def test_met_norway_sync_adapter_exists(self):
        from backend.api.services.met_norway.met_norway_sync_adapter import (
            METNorwaySyncAdapter,
        )
        assert METNorwaySyncAdapter is not None

    def test_openmeteo_forecast_sync_adapter_exists(self):
        from backend.api.services.openmeteo_forecast.openmeteo_forecast_sync_adapter import (
            OpenMeteoForecastSyncAdapter,
        )
        assert OpenMeteoForecastSyncAdapter is not None

    def test_openmeteo_archive_sync_adapter_exists(self):
        from backend.api.services.openmeteo_archive.openmeteo_archive_sync_adapter import (
            OpenMeteoArchiveSyncAdapter,
        )
        assert OpenMeteoArchiveSyncAdapter is not None

    def test_opentopo_sync_adapter_exists(self):
        from backend.api.services.opentopo.opentopo_sync_adapter import (
            OpenTopoSyncAdapter,
        )
        assert OpenTopoSyncAdapter is not None
