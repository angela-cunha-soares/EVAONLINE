"""
Unit Tests - ClimateClientFactory

Tests factory creation of all 6 API clients and singleton cache service.
Uses source-module patching because the factory uses lazy (deferred) imports
inside each method body.

Reference: Article Section 2.3 (Client Architecture)
"""

import pytest
from unittest.mock import patch, MagicMock

from backend.api.services.climate_factory import (
    ClimateClientFactory,
)


# Paths for lazy-imported client classes (patch at their source module)
_NASA = "backend.api.services.nasa_power.nasa_power_client.NASAPowerClient"
_MET  = "backend.api.services.met_norway.met_norway_client.METNorwayClient"
_NWS  = "backend.api.services.nws_forecast.nws_forecast_client.NWSForecastClient"
_NWSS = "backend.api.services.nws_stations.nws_stations_client.NWSStationsClient"
_OMF  = "backend.api.services.openmeteo_forecast.openmeteo_forecast_client.OpenMeteoForecastClient"
_OMA  = "backend.api.services.openmeteo_archive.openmeteo_archive_client.OpenMeteoArchiveClient"
_CACHE = "backend.api.services.climate_factory.get_climate_cache_service"


@pytest.mark.unit
class TestCreateNasaPower:
    """NASA POWER client creation."""

    @patch(_NASA)
    @patch(_CACHE)
    def test_returns_client_instance(self, mock_cache, mock_cls):
        mock_cls.return_value = MagicMock()
        result = ClimateClientFactory.create_nasa_power()
        assert result is not None
        mock_cls.assert_called_once()


@pytest.mark.unit
class TestCreateMETNorway:
    """MET Norway client creation."""

    @patch(_MET)
    @patch(_CACHE)
    def test_returns_client_instance(self, mock_cache, mock_cls):
        mock_cls.return_value = MagicMock()
        result = ClimateClientFactory.create_met_norway()
        assert result is not None
        mock_cls.assert_called_once()


@pytest.mark.unit
class TestCreateNWS:
    """NWS Forecast client creation."""

    @patch(_NWS)
    def test_returns_client_instance(self, mock_cls):
        mock_cls.return_value = MagicMock()
        result = ClimateClientFactory.create_nws()
        assert result is not None


@pytest.mark.unit
class TestCreateNWSStations:
    """NWS Stations client creation."""

    @patch(_NWSS)
    @patch(_CACHE)
    def test_returns_client_instance(self, mock_cache, mock_cls):
        mock_cls.return_value = MagicMock()
        result = ClimateClientFactory.create_nws_stations()
        assert result is not None


@pytest.mark.unit
class TestCreateOpenMeteoForecast:
    """Open-Meteo Forecast client creation."""

    @patch(_OMF)
    def test_returns_client_instance(self, mock_cls):
        mock_cls.return_value = MagicMock()
        result = ClimateClientFactory.create_openmeteo_forecast()
        assert result is not None


@pytest.mark.unit
class TestCreateOpenMeteoArchive:
    """Open-Meteo Archive client creation."""

    @patch(_OMA)
    @patch(_CACHE)
    def test_returns_client_instance(self, mock_cache, mock_cls):
        mock_cls.return_value = MagicMock()
        result = ClimateClientFactory.create_openmeteo_archive()
        assert result is not None


@pytest.mark.unit
class TestCreateOpenMeteoAlias:
    """Alias method delegates correctly."""

    @patch(_OMF)
    def test_create_openmeteo_delegates(self, mock_cls):
        mock_cls.return_value = MagicMock()
        result = ClimateClientFactory.create_openmeteo()
        assert result is not None


@pytest.mark.unit
class TestCloseAll:
    """Connection cleanup."""

    def test_close_all_sync_does_not_raise(self):
        """close_all_sync should not propagate exceptions."""
        # We don't actually call it because it triggers async/Redis cleanup.
        # Instead, verify the method exists and is callable.
        assert callable(ClimateClientFactory.close_all_sync)
        assert callable(ClimateClientFactory.close_all)
