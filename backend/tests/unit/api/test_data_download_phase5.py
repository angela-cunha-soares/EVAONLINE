"""
Phase 5 Tests: download_weather_data() — Full Pipeline.

Tests the main data download orchestration function that:
1. Validates coordinates and dates
2. Detects operation mode
3. Selects sources via ClimateSourceManager
4. Downloads from NASA POWER, Open-Meteo Archive/Forecast, MET Norway, NWS
5. Harmonizes column names to NASA schema
6. Concatenates multi-source DataFrames
7. Replaces -999 sentinels, removes all-NaN rows
8. Reports warnings for missing data

Coverage target: backend/api/services/data_download.py (29% → 70%+)
Lines 97-762 (the entire download body after validation).
"""

import asyncio
from datetime import date, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pandas as pd
import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run(coro):
    """Run an async coroutine in a fresh event loop."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def _source_result(sources, warnings=None):
    """Fake return of ClimateSourceManager.get_sources_for_data_download."""
    return {
        "sources": sources,
        "warnings": warnings or [],
        "location_info": {"region": "global"},
    }


def _nasa_records(n=3, start="2025-01-01"):
    """Create n fake NASA POWER-style records."""
    base = pd.to_datetime(start)
    return [
        SimpleNamespace(
            date=(base + timedelta(days=i)).strftime("%Y-%m-%d"),
            temp_max=30.0 + i,
            temp_min=18.0 + i,
            temp_mean=24.0 + i,
            humidity=65.0,
            wind_speed=3.5,
            solar_radiation=22.0,
            precipitation=1.0,
        )
        for i in range(n)
    ]


def _openmeteo_records(n=3, start="2025-01-01", source="archive"):
    """Create n fake Open-Meteo-style dict records."""
    base = pd.to_datetime(start)
    return [
        {
            "date": (base + timedelta(days=i)).strftime("%Y-%m-%d"),
            "temperature_2m_max": 29.0 + i,
            "temperature_2m_min": 17.0 + i,
            "temperature_2m_mean": 23.0 + i,
            "relative_humidity_2m_mean": 60.0,
            "wind_speed_2m_mean": 4.0,
            "shortwave_radiation_sum": 20.0,
            "precipitation_sum": 2.0,
        }
        for i in range(n)
    ]


def _met_records(n=3, start="2025-01-01"):
    """Create n fake MET Norway-style dict records."""
    base = pd.to_datetime(start)
    return [
        {
            "date": (base + timedelta(days=i)).strftime("%Y-%m-%d"),
            "temp_max": 28.0 + i,
            "temp_min": 16.0 + i,
            "temp_mean": 22.0 + i,
            "humidity_mean": 70.0,
            "precipitation_sum": 3.0,
        }
        for i in range(n)
    ]


def _nws_records(n=3, start="2025-01-01"):
    """Create n fake NWS Forecast-style records (SimpleNamespace)."""
    base = pd.to_datetime(start)
    return [
        SimpleNamespace(
            date=(base + timedelta(days=i)).strftime("%Y-%m-%d"),
            temp_max=27.0 + i,
            temp_min=15.0 + i,
            temp_mean=21.0 + i,
            humidity_mean=68.0,
            wind_speed_mean=5.0,
            precipitation_sum=1.5,
            solar_radiation=19.0,
            pressure_mean=1013.0,
            dewpoint_mean=12.0,
        )
        for i in range(n)
    ]


# ===========================================================================
# Shared patches — validation always passes, mode detected, manager selects
# ===========================================================================

_BASE_PATCHES = {
    "backend.api.services.climate_validation.ClimateValidationService.validate_coordinates": (
        True,
        {"location_name": "Test"},
    ),
    "backend.api.services.climate_validation.ClimateValidationService.validate_date_range": (
        True,
        {"period_days": 3, "errors": []},
    ),
    "backend.api.services.climate_validation.ClimateValidationService.detect_mode_from_dates": (
        "dashboard_current",
        None,
    ),
    "backend.api.services.climate_validation.ClimateValidationService.validate_request_mode": (
        True,
        {"errors": []},
    ),
}


def _apply_base_patches(extra_patches=None):
    """Build a list of patch context-managers for the common validations."""
    patches = {}
    patches.update(_BASE_PATCHES)
    if extra_patches:
        patches.update(extra_patches)
    return patches


# ===========================================================================
# Test: Single-source download — NASA POWER
# ===========================================================================


class TestDownloadNASA:
    """Tests for NASA POWER single-source download path."""

    @pytest.fixture(autouse=True)
    def _fresh_loop(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        yield
        loop.close()

    @patch("backend.api.services.data_download.ClimateSourceManager")
    @patch("backend.api.services.data_download.ClimateValidationService")
    def test_nasa_single_source_success(self, mock_validation, mock_mgr_cls):
        """Test successful NASA POWER download with 3 days of data."""
        # Validation stubs
        mock_validation.validate_coordinates.return_value = (True, {})
        mock_validation.validate_date_range.return_value = (
            True,
            {"period_days": 3, "errors": []},
        )
        mock_validation.detect_mode_from_dates.return_value = (
            "dashboard_current",
            None,
        )
        mock_validation.validate_request_mode.return_value = (True, {})

        mock_mgr = MagicMock()
        mock_mgr.get_sources_for_data_download.return_value = _source_result(
            ["nasa_power"]
        )
        mock_mgr_cls.return_value = mock_mgr

        # Mock the sync adapter import
        mock_adapter = MagicMock()
        mock_adapter.get_daily_data_sync.return_value = _nasa_records(3)

        with patch(
            "backend.api.services.nasa_power.nasa_power_sync_adapter.NASAPowerSyncAdapter",
            return_value=mock_adapter,
        ):
            from backend.api.services.data_download import (
                download_weather_data,
            )

            df, warnings = _run(
                download_weather_data(
                    data_source="nasa_power",
                    data_inicial="2025-01-01",
                    data_final="2025-01-03",
                    longitude=-46.6,
                    latitude=-23.5,
                )
            )

        assert len(df) == 3
        assert "T2M_MAX" in df.columns
        assert "source" in df.columns
        assert (df["source"] == "nasa_power").all()

    @patch("backend.api.services.data_download.ClimateSourceManager")
    @patch("backend.api.services.data_download.ClimateValidationService")
    def test_nasa_empty_returns_raises(self, mock_validation, mock_mgr_cls):
        """No data from selected sources raises ValueError."""
        mock_validation.validate_coordinates.return_value = (True, {})
        mock_validation.validate_date_range.return_value = (
            True,
            {"period_days": 3, "errors": []},
        )
        mock_validation.detect_mode_from_dates.return_value = (
            "dashboard_current",
            None,
        )
        mock_validation.validate_request_mode.return_value = (True, {})

        mock_mgr = MagicMock()
        mock_mgr.get_sources_for_data_download.return_value = _source_result(
            ["nasa_power"]
        )
        mock_mgr_cls.return_value = mock_mgr

        mock_adapter = MagicMock()
        mock_adapter.get_daily_data_sync.return_value = []  # No data

        with patch(
            "backend.api.services.nasa_power.nasa_power_sync_adapter.NASAPowerSyncAdapter",
            return_value=mock_adapter,
        ):
            from backend.api.services.data_download import (
                download_weather_data,
            )

            with pytest.raises(ValueError, match="No sources provided valid data"):
                _run(
                    download_weather_data(
                        data_source="nasa_power",
                        data_inicial="2025-01-01",
                        data_final="2025-01-03",
                        longitude=-46.6,
                        latitude=-23.5,
                    )
                )


# ===========================================================================
# Test: Single-source download — Open-Meteo Archive
# ===========================================================================


class TestDownloadOpenMeteoArchive:
    """Tests for Open-Meteo Archive single-source path."""

    @pytest.fixture(autouse=True)
    def _fresh_loop(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        yield
        loop.close()

    @patch("backend.api.services.data_download.ClimateSourceManager")
    @patch("backend.api.services.data_download.ClimateValidationService")
    def test_openmeteo_archive_harmonizes_columns(
        self, mock_validation, mock_mgr_cls
    ):
        """Archive data harmonized to NASA variable names."""
        mock_validation.validate_coordinates.return_value = (True, {})
        mock_validation.validate_date_range.return_value = (
            True,
            {"period_days": 3, "errors": []},
        )
        mock_validation.detect_mode_from_dates.return_value = (
            "dashboard_current",
            None,
        )
        mock_validation.validate_request_mode.return_value = (True, {})

        mock_mgr = MagicMock()
        mock_mgr.get_sources_for_data_download.return_value = _source_result(
            ["openmeteo_archive"]
        )
        mock_mgr_cls.return_value = mock_mgr

        mock_adapter = MagicMock()
        mock_adapter.get_daily_data_sync.return_value = _openmeteo_records(3)

        with patch(
            "backend.api.services.openmeteo_archive.openmeteo_archive_sync_adapter.OpenMeteoArchiveSyncAdapter",
            return_value=mock_adapter,
        ):
            from backend.api.services.data_download import (
                download_weather_data,
            )

            df, warnings = _run(
                download_weather_data(
                    data_source="openmeteo_archive",
                    data_inicial="2025-01-01",
                    data_final="2025-01-03",
                    longitude=-46.6,
                    latitude=-23.5,
                )
            )

        # Should have both original + harmonized columns
        assert "T2M_MAX" in df.columns
        assert "T2M_MIN" in df.columns
        assert "RH2M" in df.columns
        assert (df["source"] == "openmeteo_archive").all()

    @patch("backend.api.services.data_download.ClimateSourceManager")
    @patch("backend.api.services.data_download.ClimateValidationService")
    def test_archive_skipped_when_period_too_recent(
        self, mock_validation, mock_mgr_cls
    ):
        """Archive skipped when start > archive_max_date (today - 3 days)."""
        mock_validation.validate_coordinates.return_value = (True, {})
        # Use future dates
        mock_validation.validate_date_range.return_value = (
            True,
            {"period_days": 3, "errors": []},
        )
        mock_validation.detect_mode_from_dates.return_value = (
            "dashboard_forecast",
            None,
        )
        mock_validation.validate_request_mode.return_value = (True, {})

        mock_mgr = MagicMock()
        mock_mgr.get_sources_for_data_download.return_value = _source_result(
            ["openmeteo_archive"]
        )
        mock_mgr_cls.return_value = mock_mgr

        # Future dates — archive will be skipped
        tomorrow = (date.today() + timedelta(days=1)).isoformat()
        next_week = (date.today() + timedelta(days=7)).isoformat()

        from backend.api.services.data_download import download_weather_data

        with pytest.raises(ValueError, match="No sources provided valid data"):
            _run(
                download_weather_data(
                    data_source="openmeteo_archive",
                    data_inicial=tomorrow,
                    data_final=next_week,
                    longitude=-46.6,
                    latitude=-23.5,
                )
            )


# ===========================================================================
# Test: Single-source download — Open-Meteo Forecast
# ===========================================================================


class TestDownloadOpenMeteoForecast:
    """Tests for Open-Meteo Forecast single-source path."""

    @pytest.fixture(autouse=True)
    def _fresh_loop(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        yield
        loop.close()

    @patch("backend.api.services.data_download.ClimateSourceManager")
    @patch("backend.api.services.data_download.ClimateValidationService")
    def test_forecast_success(self, mock_validation, mock_mgr_cls):
        """Forecast data download and harmonization."""
        mock_validation.validate_coordinates.return_value = (True, {})
        mock_validation.validate_date_range.return_value = (
            True,
            {"period_days": 3, "errors": []},
        )
        mock_validation.detect_mode_from_dates.return_value = (
            "dashboard_current",
            None,
        )
        mock_validation.validate_request_mode.return_value = (True, {})

        mock_mgr = MagicMock()
        mock_mgr.get_sources_for_data_download.return_value = _source_result(
            ["openmeteo_forecast"]
        )
        mock_mgr_cls.return_value = mock_mgr

        today_str = date.today().isoformat()
        records = _openmeteo_records(3, start=today_str)

        mock_adapter = MagicMock()
        mock_adapter.get_daily_data_sync.return_value = records

        with patch(
            "backend.api.services.openmeteo_forecast.openmeteo_forecast_sync_adapter.OpenMeteoForecastSyncAdapter",
            return_value=mock_adapter,
        ):
            from backend.api.services.data_download import (
                download_weather_data,
            )

            df, warnings = _run(
                download_weather_data(
                    data_source="openmeteo_forecast",
                    data_inicial=today_str,
                    data_final=(date.today() + timedelta(days=2)).isoformat(),
                    longitude=-46.6,
                    latitude=-23.5,
                )
            )

        assert len(df) == 3
        assert "ALLSKY_SFC_SW_DWN" in df.columns
        assert (df["source"] == "openmeteo_forecast").all()


# ===========================================================================
# Test: Single-source download — MET Norway
# ===========================================================================


class TestDownloadMETNorway:
    """Tests for MET Norway download path."""

    @pytest.fixture(autouse=True)
    def _fresh_loop(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        yield
        loop.close()

    @patch("backend.api.services.data_download.ClimateSourceManager")
    @patch("backend.api.services.data_download.ClimateValidationService")
    def test_met_norway_success(self, mock_validation, mock_mgr_cls):
        """MET Norway download with dict records and harmonization."""
        mock_validation.validate_coordinates.return_value = (True, {})
        mock_validation.validate_date_range.return_value = (
            True,
            {"period_days": 3, "errors": []},
        )
        mock_validation.detect_mode_from_dates.return_value = (
            "dashboard_current",
            None,
        )
        mock_validation.validate_request_mode.return_value = (True, {})

        mock_mgr = MagicMock()
        mock_mgr.get_sources_for_data_download.return_value = _source_result(
            ["met_norway"]
        )
        mock_mgr_cls.return_value = mock_mgr

        today_str = date.today().isoformat()
        mock_client = AsyncMock()
        mock_client.get_daily_forecast.return_value = _met_records(3, start=today_str)

        with patch(
            "backend.api.services.met_norway.met_norway_client.METNorwayClient",
            return_value=mock_client,
        ), patch(
            "backend.api.services.met_norway.met_norway_client.METNorwayClient.get_recommended_variables",
            return_value=[
                "temperature_2m_max",
                "temperature_2m_min",
                "precipitation_sum",
            ],
        ):
            from backend.api.services.data_download import (
                download_weather_data,
            )

            df, warnings = _run(
                download_weather_data(
                    data_source="met_norway",
                    data_inicial=today_str,
                    data_final=(date.today() + timedelta(days=2)).isoformat(),
                    longitude=10.75,
                    latitude=59.91,
                )
            )

        assert len(df) == 3
        assert "T2M_MAX" in df.columns
        assert (df["source"] == "met_norway").all()
        # CC-BY attribution warning present
        assert any("CC-BY" in w for w in warnings)


# ===========================================================================
# Test: Single-source download — NWS Forecast
# ===========================================================================


class TestDownloadNWSForecast:
    """Tests for NWS Forecast download (USA only)."""

    @pytest.fixture(autouse=True)
    def _fresh_loop(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        yield
        loop.close()

    @patch("backend.api.services.data_download.ClimateSourceManager")
    @patch("backend.api.services.data_download.ClimateValidationService")
    def test_nws_forecast_success(self, mock_validation, mock_mgr_cls):
        """NWS Forecast download and harmonization."""
        mock_validation.validate_coordinates.return_value = (True, {})
        mock_validation.validate_date_range.return_value = (
            True,
            {"period_days": 3, "errors": []},
        )
        mock_validation.detect_mode_from_dates.return_value = (
            "dashboard_forecast",
            None,
        )
        mock_validation.validate_request_mode.return_value = (True, {})

        mock_mgr = MagicMock()
        mock_mgr.get_sources_for_data_download.return_value = _source_result(
            ["nws_forecast"]
        )
        mock_mgr_cls.return_value = mock_mgr

        today_str = date.today().isoformat()
        mock_adapter = MagicMock()
        mock_adapter.get_daily_data_sync.return_value = _nws_records(3, start=today_str)

        with patch(
            "backend.api.services.nws_forecast.nws_forecast_sync_adapter.NWSDailyForecastSyncAdapter",
            return_value=mock_adapter,
        ):
            from backend.api.services.data_download import (
                download_weather_data,
            )

            df, warnings = _run(
                download_weather_data(
                    data_source="nws_forecast",
                    data_inicial=today_str,
                    data_final=(date.today() + timedelta(days=2)).isoformat(),
                    longitude=-74.0,
                    latitude=40.7,
                )
            )

        assert len(df) == 3
        assert "T2M_MAX" in df.columns
        assert "WS2M" in df.columns
        assert (df["source"] == "nws_forecast").all()


# ===========================================================================
# Test: Multi-source (Data Fusion) download
# ===========================================================================


class TestDownloadMultiSource:
    """Tests for data fusion multi-source download."""

    @pytest.fixture(autouse=True)
    def _fresh_loop(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        yield
        loop.close()

    @patch("backend.api.services.data_download.ClimateSourceManager")
    @patch("backend.api.services.data_download.ClimateValidationService")
    def test_data_fusion_two_sources(self, mock_validation, mock_mgr_cls):
        """Data fusion selects and concatenates 2 sources."""
        mock_validation.validate_coordinates.return_value = (True, {})
        mock_validation.validate_date_range.return_value = (
            True,
            {"period_days": 3, "errors": []},
        )
        mock_validation.detect_mode_from_dates.return_value = (
            "dashboard_current",
            None,
        )
        mock_validation.validate_request_mode.return_value = (True, {})

        mock_mgr = MagicMock()
        mock_mgr.get_sources_for_data_download.return_value = _source_result(
            ["nasa_power", "openmeteo_archive"]
        )
        mock_mgr_cls.return_value = mock_mgr

        mock_nasa = MagicMock()
        mock_nasa.get_daily_data_sync.return_value = _nasa_records(3)

        mock_archive = MagicMock()
        mock_archive.get_daily_data_sync.return_value = _openmeteo_records(3)

        with patch(
            "backend.api.services.nasa_power.nasa_power_sync_adapter.NASAPowerSyncAdapter",
            return_value=mock_nasa,
        ), patch(
            "backend.api.services.openmeteo_archive.openmeteo_archive_sync_adapter.OpenMeteoArchiveSyncAdapter",
            return_value=mock_archive,
        ):
            from backend.api.services.data_download import (
                download_weather_data,
            )

            df, warnings = _run(
                download_weather_data(
                    data_source="data fusion",
                    data_inicial="2025-01-01",
                    data_final="2025-01-03",
                    longitude=-46.6,
                    latitude=-23.5,
                )
            )

        # Both sources concatenated: 3 + 3 = 6 rows
        assert len(df) == 6
        sources = df["source"].unique()
        assert "nasa_power" in sources
        assert "openmeteo_archive" in sources

    @patch("backend.api.services.data_download.ClimateSourceManager")
    @patch("backend.api.services.data_download.ClimateValidationService")
    def test_unavailable_source_raises(self, mock_validation, mock_mgr_cls):
        """Requesting unavailable source raises ValueError."""
        mock_validation.validate_coordinates.return_value = (True, {})
        mock_validation.validate_date_range.return_value = (
            True,
            {"period_days": 3, "errors": []},
        )
        mock_validation.detect_mode_from_dates.return_value = (
            "dashboard_current",
            None,
        )
        mock_validation.validate_request_mode.return_value = (True, {})

        mock_mgr = MagicMock()
        # Manager returns only nasa_power, but user requested nws_forecast
        mock_mgr.get_sources_for_data_download.return_value = _source_result(
            ["nasa_power"]
        )
        mock_mgr_cls.return_value = mock_mgr

        from backend.api.services.data_download import download_weather_data

        with pytest.raises(ValueError, match="unavailable"):
            _run(
                download_weather_data(
                    data_source="nws_forecast",
                    data_inicial="2025-01-01",
                    data_final="2025-01-03",
                    longitude=-46.6,
                    latitude=-23.5,
                )
            )


# ===========================================================================
# Test: Edge cases — sentinel values, mode fallback, partial failures
# ===========================================================================


class TestDownloadEdgeCases:
    """Tests for edge cases in data download."""

    @pytest.fixture(autouse=True)
    def _fresh_loop(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        yield
        loop.close()

    @patch("backend.api.services.data_download.ClimateSourceManager")
    @patch("backend.api.services.data_download.ClimateValidationService")
    def test_sentinel_values_replaced(self, mock_validation, mock_mgr_cls):
        """-999 sentinel values replaced with NaN."""
        mock_validation.validate_coordinates.return_value = (True, {})
        mock_validation.validate_date_range.return_value = (
            True,
            {"period_days": 3, "errors": []},
        )
        mock_validation.detect_mode_from_dates.return_value = (
            "dashboard_current",
            None,
        )
        mock_validation.validate_request_mode.return_value = (True, {})

        mock_mgr = MagicMock()
        mock_mgr.get_sources_for_data_download.return_value = _source_result(
            ["nasa_power"]
        )
        mock_mgr_cls.return_value = mock_mgr

        records = _nasa_records(3)
        records[1].temp_max = -999.0  # Sentinel

        mock_adapter = MagicMock()
        mock_adapter.get_daily_data_sync.return_value = records

        with patch(
            "backend.api.services.nasa_power.nasa_power_sync_adapter.NASAPowerSyncAdapter",
            return_value=mock_adapter,
        ):
            from backend.api.services.data_download import (
                download_weather_data,
            )

            df, warnings = _run(
                download_weather_data(
                    data_source="nasa_power",
                    data_inicial="2025-01-01",
                    data_final="2025-01-03",
                    longitude=-46.6,
                    latitude=-23.5,
                )
            )

        # -999 should be replaced with NaN
        assert pd.isna(df["T2M_MAX"].iloc[1])

    @patch("backend.api.services.data_download.ClimateSourceManager")
    @patch("backend.api.services.data_download.ClimateValidationService")
    def test_mode_fallback_to_forecast(self, mock_validation, mock_mgr_cls):
        """When mode detection fails, falls back based on dates."""
        mock_validation.validate_coordinates.return_value = (True, {})
        mock_validation.validate_date_range.return_value = (
            True,
            {"period_days": 3, "errors": []},
        )
        mock_validation.detect_mode_from_dates.return_value = (
            None,
            "Cannot detect mode",
        )
        mock_validation.validate_request_mode.return_value = (True, {})

        mock_mgr = MagicMock()
        mock_mgr.get_sources_for_data_download.return_value = _source_result(
            ["openmeteo_forecast"]
        )
        mock_mgr_cls.return_value = mock_mgr

        tomorrow = (date.today() + timedelta(days=1)).isoformat()
        in_3_days = (date.today() + timedelta(days=3)).isoformat()

        mock_adapter = MagicMock()
        mock_adapter.get_daily_data_sync.return_value = _openmeteo_records(
            3, start=tomorrow
        )

        with patch(
            "backend.api.services.openmeteo_forecast.openmeteo_forecast_sync_adapter.OpenMeteoForecastSyncAdapter",
            return_value=mock_adapter,
        ):
            from backend.api.services.data_download import (
                download_weather_data,
            )

            df, warnings = _run(
                download_weather_data(
                    data_source="openmeteo_forecast",
                    data_inicial=tomorrow,
                    data_final=in_3_days,
                    longitude=-46.6,
                    latitude=-23.5,
                )
            )

        assert len(df) == 3
        # Should have mode-fallback warning
        assert any("Mode not detected" in w for w in warnings)

    @patch("backend.api.services.data_download.ClimateSourceManager")
    @patch("backend.api.services.data_download.ClimateValidationService")
    def test_source_error_adds_warning_continues(
        self, mock_validation, mock_mgr_cls
    ):
        """One source fails but another succeeds — partial download."""
        mock_validation.validate_coordinates.return_value = (True, {})
        mock_validation.validate_date_range.return_value = (
            True,
            {"period_days": 3, "errors": []},
        )
        mock_validation.detect_mode_from_dates.return_value = (
            "dashboard_current",
            None,
        )
        mock_validation.validate_request_mode.return_value = (True, {})

        mock_mgr = MagicMock()
        mock_mgr.get_sources_for_data_download.return_value = _source_result(
            ["nasa_power", "openmeteo_archive"]
        )
        mock_mgr_cls.return_value = mock_mgr

        # NASA fails, Archive succeeds
        mock_nasa = MagicMock()
        mock_nasa.get_daily_data_sync.side_effect = ConnectionError("API down")

        mock_archive = MagicMock()
        mock_archive.get_daily_data_sync.return_value = _openmeteo_records(3)

        with patch(
            "backend.api.services.nasa_power.nasa_power_sync_adapter.NASAPowerSyncAdapter",
            return_value=mock_nasa,
        ), patch(
            "backend.api.services.openmeteo_archive.openmeteo_archive_sync_adapter.OpenMeteoArchiveSyncAdapter",
            return_value=mock_archive,
        ):
            from backend.api.services.data_download import (
                download_weather_data,
            )

            df, warnings = _run(
                download_weather_data(
                    data_source="data fusion",
                    data_inicial="2025-01-01",
                    data_final="2025-01-03",
                    longitude=-46.6,
                    latitude=-23.5,
                )
            )

        # Only archive data returned
        assert len(df) == 3
        assert (df["source"] == "openmeteo_archive").all()
        # Warning about NASA failure
        assert any("nasa_power" in w and "error" in w for w in warnings)

    @patch("backend.api.services.data_download.ClimateSourceManager")
    @patch("backend.api.services.data_download.ClimateValidationService")
    def test_comma_separated_sources(self, mock_validation, mock_mgr_cls):
        """Comma-separated source string parsed correctly."""
        mock_validation.validate_coordinates.return_value = (True, {})
        mock_validation.validate_date_range.return_value = (
            True,
            {"period_days": 3, "errors": []},
        )
        mock_validation.detect_mode_from_dates.return_value = (
            "dashboard_current",
            None,
        )
        mock_validation.validate_request_mode.return_value = (True, {})

        mock_mgr = MagicMock()
        mock_mgr.get_sources_for_data_download.return_value = _source_result(
            ["nasa_power", "openmeteo_archive"]
        )
        mock_mgr_cls.return_value = mock_mgr

        mock_nasa = MagicMock()
        mock_nasa.get_daily_data_sync.return_value = _nasa_records(3)

        mock_archive = MagicMock()
        mock_archive.get_daily_data_sync.return_value = _openmeteo_records(3)

        with patch(
            "backend.api.services.nasa_power.nasa_power_sync_adapter.NASAPowerSyncAdapter",
            return_value=mock_nasa,
        ), patch(
            "backend.api.services.openmeteo_archive.openmeteo_archive_sync_adapter.OpenMeteoArchiveSyncAdapter",
            return_value=mock_archive,
        ):
            from backend.api.services.data_download import (
                download_weather_data,
            )

            df, warnings = _run(
                download_weather_data(
                    data_source="nasa_power,openmeteo_archive",
                    data_inicial="2025-01-01",
                    data_final="2025-01-03",
                    longitude=-46.6,
                    latitude=-23.5,
                )
            )

        assert len(df) == 6
