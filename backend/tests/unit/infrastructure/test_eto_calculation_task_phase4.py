"""
Phase 4 Tests: ETo Calculation Celery Task.

Tests the calculate_eto_task Celery task:
- Successful ETo calculation flow
- Validation failures (coordinates, dates)
- Auto-mode detection
- Email sending flows (start, result, error)
- NWS station lookup (USA region)
- Ocean warning (no_data elevation)
- Database save handling
- Retry logic for API errors
- No retry for validation errors
"""

import asyncio
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def _fresh_event_loop():
    """Ensure a fresh event loop (prevents 'loop is closed' in full suite)."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield
    loop.close()


# ============================================================================
# Helpers - mock the heavy imports
# ============================================================================

def _make_mock_self(task_id="test-task-123", retries=0, max_retries=2):
    """Create a mock Celery task self with request context."""
    mock_self = MagicMock()
    mock_self.request.id = task_id
    mock_self.request.retries = retries
    mock_self.max_retries = max_retries
    return mock_self


def _basic_result():
    """Return a minimal successful result from process_location."""
    return {
        "et0_series": [
            {"date": "2025-01-01", "et0_mm_day": 3.5},
            {"date": "2025-01-02", "et0_mm_day": 4.1},
        ],
        "elevation": {"value": 120, "source": "srtm", "no_data": False},
        "quality_metrics": {"completeness": 0.95},
        "sources_used": ["nasa_power"],
        "summary": {"mean_eto": 3.8},
    }


def _call_eto_task(mock_self, **kwargs):
    """Call calculate_eto_task bypassing Celery's __call__ (bind=True).

    Celery's @task(bind=True) auto-injects ``self`` via __call__,
    so passing mock_self as a positional arg causes conflicts.
    Access the raw function via run.__func__ to skip method binding.
    """
    from backend.infrastructure.celery.tasks.eto_calculation import (
        calculate_eto_task,
    )
    raw_fn = calculate_eto_task.run.__func__
    return raw_fn(mock_self, **kwargs)


# ============================================================================
# Test Class
# ============================================================================

class TestCalculateEToTask:
    """Tests for calculate_eto_task."""

    @patch("backend.infrastructure.celery.tasks.eto_calculation.celery_app")
    @patch("backend.database.connection.get_db")
    @patch("backend.database.data_storage.save_climate_data")
    @patch("backend.api.services.climate_source_manager.ClimateSourceManager")
    @patch("backend.api.services.climate_validation.ClimateValidationService")
    @patch("backend.core.eto_calculation.eto_services.EToProcessingService")
    @patch("nest_asyncio.apply")
    def test_successful_calculation(
        self,
        mock_nest,
        mock_service_cls,
        mock_validation_cls,
        mock_manager_cls,
        mock_save,
        mock_get_db,
        mock_celery,
    ):
        """Test basic successful ETo calculation."""
        # Setup validation
        mock_validation_cls.validate_coordinates.return_value = (True, None)
        mock_validation_cls.detect_mode_from_dates.return_value = (
            "dashboard_current",
            None,
        )

        # Setup source manager
        mock_manager = MagicMock()
        mock_manager.get_sources_for_data_download.return_value = {
            "sources": ["nasa_power"],
            "location_info": {"region": "south_america"},
        }
        mock_manager_cls.return_value = mock_manager

        # Setup ETo service
        mock_service = MagicMock()
        result_data = _basic_result()

        # Mock process_location as coroutine
        async def mock_process(*args, **kwargs):
            return result_data

        mock_service.process_location = mock_process
        mock_service_cls.return_value = mock_service

        # Setup DB
        mock_db = MagicMock()
        mock_get_db.return_value = iter([mock_db])
        mock_save.return_value = 2

        mock_self = _make_mock_self()

        result = _call_eto_task(
            mock_self,
            lat=-23.5,
            lon=-46.6,
            start_date="2025-01-01",
            end_date="2025-01-02",
        )

        assert result["task_id"] == "test-task-123"
        assert "processing_time_seconds" in result
        assert result["et0_series"] == result_data["et0_series"]
        assert result["email_sent"] is False
        assert result["nws_station"] is None

    @patch("backend.infrastructure.celery.tasks.eto_calculation.celery_app")
    @patch("backend.api.services.climate_validation.ClimateValidationService")
    @patch("nest_asyncio.apply")
    def test_invalid_coordinates_returns_error(
        self, mock_nest, mock_validation_cls, mock_celery
    ):
        """Test that invalid coordinates returns error dict (no retry)."""
        mock_validation_cls.validate_coordinates.return_value = (False, "Invalid")

        mock_self = _make_mock_self()

        result = _call_eto_task(
            mock_self,
            lat=999.0,
            lon=999.0,
            start_date="2025-01-01",
            end_date="2025-01-02",
        )

        # ValueError → no retry, returns error dict
        assert "error" in result
        assert result["task_id"] == "test-task-123"

    @patch("backend.infrastructure.celery.tasks.eto_calculation.celery_app")
    @patch("backend.database.connection.get_db")
    @patch("backend.database.data_storage.save_climate_data")
    @patch("backend.api.services.climate_source_manager.ClimateSourceManager")
    @patch("backend.api.services.climate_validation.ClimateValidationService")
    @patch("backend.core.eto_calculation.eto_services.EToProcessingService")
    @patch("nest_asyncio.apply")
    def test_auto_detect_mode(
        self,
        mock_nest,
        mock_service_cls,
        mock_validation_cls,
        mock_manager_cls,
        mock_save,
        mock_get_db,
        mock_celery,
    ):
        """Test auto-detection of mode when mode=None."""
        mock_validation_cls.validate_coordinates.return_value = (True, None)
        mock_validation_cls.detect_mode_from_dates.return_value = (
            "historical_data",
            None,
        )

        mock_manager = MagicMock()
        mock_manager.get_sources_for_data_download.return_value = {
            "sources": ["nasa_power"],
            "location_info": {"region": "europe"},
        }
        mock_manager_cls.return_value = mock_manager

        mock_service = MagicMock()

        async def mock_process(*args, **kwargs):
            return _basic_result()

        mock_service.process_location = mock_process
        mock_service_cls.return_value = mock_service

        mock_db = MagicMock()
        mock_get_db.return_value = iter([mock_db])
        mock_save.return_value = 2

        mock_self = _make_mock_self()

        result = _call_eto_task(
            mock_self,
            lat=48.8,
            lon=2.3,
            start_date="2024-01-01",
            end_date="2024-06-30",
            mode=None,
        )

        assert result["mode"] == "historical_data"

    @patch("backend.infrastructure.celery.tasks.eto_calculation.celery_app")
    @patch("backend.database.connection.get_db")
    @patch("backend.database.data_storage.save_climate_data")
    @patch("backend.api.services.climate_source_manager.ClimateSourceManager")
    @patch("backend.api.services.climate_validation.ClimateValidationService")
    @patch("backend.core.eto_calculation.eto_services.EToProcessingService")
    @patch("nest_asyncio.apply")
    def test_ocean_warning_when_no_data_elevation(
        self,
        mock_nest,
        mock_service_cls,
        mock_validation_cls,
        mock_manager_cls,
        mock_save,
        mock_get_db,
        mock_celery,
    ):
        """Test ocean warning is set when elevation has no_data=True."""
        mock_validation_cls.validate_coordinates.return_value = (True, None)
        mock_validation_cls.detect_mode_from_dates.return_value = (
            "dashboard_current",
            None,
        )

        mock_manager = MagicMock()
        mock_manager.get_sources_for_data_download.return_value = {
            "sources": ["nasa_power"],
            "location_info": {"region": "atlantic_ocean"},
        }
        mock_manager_cls.return_value = mock_manager

        ocean_result = _basic_result()
        ocean_result["elevation"] = {"value": None, "source": "srtm", "no_data": True}

        mock_service = MagicMock()

        async def mock_process(*args, **kwargs):
            return ocean_result

        mock_service.process_location = mock_process
        mock_service_cls.return_value = mock_service

        mock_db = MagicMock()
        mock_get_db.return_value = iter([mock_db])
        mock_save.return_value = 0

        mock_self = _make_mock_self()

        result = _call_eto_task(
            mock_self,
            lat=30.0,
            lon=-40.0,
            start_date="2025-01-01",
            end_date="2025-01-02",
        )

        assert result.get("ocean_warning") is True

    @patch("backend.infrastructure.celery.tasks.eto_calculation.celery_app")
    @patch("backend.database.connection.get_db")
    @patch("backend.database.data_storage.save_climate_data")
    @patch("backend.api.services.climate_source_manager.ClimateSourceManager")
    @patch("backend.api.services.climate_validation.ClimateValidationService")
    @patch("backend.core.eto_calculation.eto_services.EToProcessingService")
    @patch("nest_asyncio.apply")
    def test_db_save_error_does_not_fail_task(
        self,
        mock_nest,
        mock_service_cls,
        mock_validation_cls,
        mock_manager_cls,
        mock_save,
        mock_get_db,
        mock_celery,
    ):
        """Test that database save error is handled gracefully."""
        mock_validation_cls.validate_coordinates.return_value = (True, None)
        mock_validation_cls.detect_mode_from_dates.return_value = (
            "dashboard_current",
            None,
        )

        mock_manager = MagicMock()
        mock_manager.get_sources_for_data_download.return_value = {
            "sources": ["nasa_power"],
            "location_info": {"region": "south_america"},
        }
        mock_manager_cls.return_value = mock_manager

        mock_service = MagicMock()

        async def mock_process(*args, **kwargs):
            return _basic_result()

        mock_service.process_location = mock_process
        mock_service_cls.return_value = mock_service

        # DB fails
        mock_get_db.return_value = iter([MagicMock()])
        mock_save.side_effect = Exception("DB connection lost")

        mock_self = _make_mock_self()

        # Should not raise — DB errors are caught
        result = _call_eto_task(
            mock_self,
            lat=-23.5,
            lon=-46.6,
            start_date="2025-01-01",
            end_date="2025-01-02",
        )

        assert result["task_id"] == "test-task-123"
        assert "et0_series" in result

    @patch("backend.infrastructure.celery.tasks.eto_calculation.celery_app")
    @patch("backend.core.utils.email_utils.send_html_email")
    @patch("backend.core.utils.email_utils.validate_email")
    @patch("backend.core.utils.email_templates.create_processing_started_email")
    @patch("backend.database.connection.get_db")
    @patch("backend.database.data_storage.save_climate_data")
    @patch("backend.api.services.climate_source_manager.ClimateSourceManager")
    @patch("backend.api.services.climate_validation.ClimateValidationService")
    @patch("backend.core.eto_calculation.eto_services.EToProcessingService")
    @patch("nest_asyncio.apply")
    def test_email_mode_sends_start_email(
        self,
        mock_nest,
        mock_service_cls,
        mock_validation_cls,
        mock_manager_cls,
        mock_save,
        mock_get_db,
        mock_start_email,
        mock_validate_email,
        mock_send_html,
        mock_celery,
    ):
        """Test that historical_email mode sends start email."""
        mock_validate_email.return_value = True
        mock_start_email.return_value = ("Processing", "<html>Started</html>")

        mock_validation_cls.validate_coordinates.return_value = (True, None)

        mock_manager = MagicMock()
        mock_manager.get_sources_for_data_download.return_value = {
            "sources": ["nasa_power"],
            "location_info": {"region": "south_america"},
        }
        mock_manager_cls.return_value = mock_manager

        mock_service = MagicMock()

        async def mock_process(*args, **kwargs):
            return _basic_result()

        mock_service.process_location = mock_process
        mock_service_cls.return_value = mock_service

        mock_db = MagicMock()
        mock_get_db.return_value = iter([mock_db])
        mock_save.return_value = 2

        mock_self = _make_mock_self()

        result = _call_eto_task(
            mock_self,
            lat=-23.5,
            lon=-46.6,
            start_date="2024-01-01",
            end_date="2024-12-31",
            mode="historical_email",
            email="test@example.com",
        )

        # Email should have been sent
        mock_send_html.assert_called()

    @patch("backend.infrastructure.celery.tasks.eto_calculation.celery_app")
    @patch("backend.api.services.climate_source_manager.ClimateSourceManager")
    @patch("backend.api.services.climate_validation.ClimateValidationService")
    @patch("backend.core.eto_calculation.eto_services.EToProcessingService")
    @patch("nest_asyncio.apply")
    def test_api_error_triggers_retry(
        self,
        mock_nest,
        mock_service_cls,
        mock_validation_cls,
        mock_manager_cls,
        mock_celery,
    ):
        """Test that API errors trigger retry with backoff."""
        mock_validation_cls.validate_coordinates.return_value = (True, None)
        mock_validation_cls.detect_mode_from_dates.return_value = (
            "dashboard_current",
            None,
        )

        mock_manager = MagicMock()
        mock_manager.get_sources_for_data_download.return_value = {
            "sources": ["nasa_power"],
            "location_info": {"region": "south_america"},
        }
        mock_manager_cls.return_value = mock_manager

        mock_service = MagicMock()

        async def mock_process(*args, **kwargs):
            raise ConnectionError("NASA Power API timeout")

        mock_service.process_location = mock_process
        mock_service_cls.return_value = mock_service

        mock_self = _make_mock_self(retries=0)
        mock_self.retry.side_effect = Exception("Retry triggered")

        with pytest.raises(Exception, match="Retry triggered"):
            _call_eto_task(
                mock_self,
                lat=-23.5,
                lon=-46.6,
                start_date="2025-01-01",
                end_date="2025-01-02",
            )

        mock_self.retry.assert_called_once()

    @patch("backend.infrastructure.celery.tasks.eto_calculation.celery_app")
    @patch("backend.api.services.climate_source_manager.ClimateSourceManager")
    @patch("backend.api.services.climate_validation.ClimateValidationService")
    @patch("backend.core.eto_calculation.eto_services.EToProcessingService")
    @patch("nest_asyncio.apply")
    def test_api_error_max_retries_returns_error(
        self,
        mock_nest,
        mock_service_cls,
        mock_validation_cls,
        mock_manager_cls,
        mock_celery,
    ):
        """Test that API error after max retries returns error dict."""
        mock_validation_cls.validate_coordinates.return_value = (True, None)
        mock_validation_cls.detect_mode_from_dates.return_value = (
            "dashboard_current",
            None,
        )

        mock_manager = MagicMock()
        mock_manager.get_sources_for_data_download.return_value = {
            "sources": ["nasa_power"],
            "location_info": {"region": "south_america"},
        }
        mock_manager_cls.return_value = mock_manager

        mock_service = MagicMock()

        async def mock_process(*args, **kwargs):
            raise ConnectionError("NASA Power API timeout")

        mock_service.process_location = mock_process
        mock_service_cls.return_value = mock_service

        # Already at max retries
        mock_self = _make_mock_self(retries=2)

        result = _call_eto_task(
            mock_self,
            lat=-23.5,
            lon=-46.6,
            start_date="2025-01-01",
            end_date="2025-01-02",
        )

        assert "error" in result
        assert "timeout" in result["error"].lower()

    @patch("backend.infrastructure.celery.tasks.eto_calculation.celery_app")
    @patch("backend.database.connection.get_db")
    @patch("backend.database.data_storage.save_climate_data")
    @patch("backend.api.services.climate_source_manager.ClimateSourceManager")
    @patch("backend.api.services.climate_validation.ClimateValidationService")
    @patch("backend.core.eto_calculation.eto_services.EToProcessingService")
    @patch("nest_asyncio.apply")
    def test_usa_region_with_forecast_mode(
        self,
        mock_nest,
        mock_service_cls,
        mock_validation_cls,
        mock_manager_cls,
        mock_save,
        mock_get_db,
        mock_celery,
    ):
        """Test that USA region + forecast triggers NWS station lookup."""
        mock_validation_cls.validate_coordinates.return_value = (True, None)

        mock_manager = MagicMock()
        mock_manager.get_sources_for_data_download.return_value = {
            "sources": ["nws_forecast"],
            "location_info": {"region": "usa_continental"},
        }
        mock_manager_cls.return_value = mock_manager

        mock_service = MagicMock()
        result_data = _basic_result()

        async def mock_process(*args, **kwargs):
            return result_data

        mock_service.process_location = mock_process
        mock_service_cls.return_value = mock_service

        mock_db = MagicMock()
        mock_get_db.return_value = iter([mock_db])
        mock_save.return_value = 2

        # Mock httpx for NWS station lookup
        mock_grid_resp = MagicMock()
        mock_grid_resp.status_code = 200
        mock_grid_resp.json.return_value = {
            "properties": {
                "gridId": "OKX",
                "gridX": 33,
                "gridY": 37,
                "timeZone": "America/New_York",
            }
        }

        mock_stations_resp = MagicMock()
        mock_stations_resp.status_code = 200
        mock_stations_resp.json.return_value = {
            "features": [
                {
                    "properties": {
                        "stationIdentifier": "KJFK",
                        "name": "JFK Airport",
                        "elevation": {"value": 4},
                    },
                    "geometry": {"coordinates": [-73.78, 40.64]},
                }
            ]
        }

        mock_obs_resp = MagicMock()
        mock_obs_resp.status_code = 200
        mock_obs_resp.json.return_value = {
            "properties": {
                "timestamp": "2025-01-01T12:00:00Z",
                "temperature": {"value": 5.0},
                "relativeHumidity": {"value": 65.0},
                "windSpeed": {"value": 18.0},
            }
        }

        with patch("httpx.get") as mock_httpx_get:
            mock_httpx_get.side_effect = [
                mock_grid_resp,
                mock_stations_resp,
                mock_obs_resp,
            ]

            mock_self = _make_mock_self()

            result = _call_eto_task(
                mock_self,
                lat=40.7,
                lon=-74.0,
                start_date="2025-01-01",
                end_date="2025-01-02",
                mode="dashboard_current",
            )

            assert result["nws_station"] is not None
            assert result["nws_station"]["station_id"] == "KJFK"
            assert result["nws_station"]["station_name"] == "JFK Airport"
            assert result["nws_station"]["distance_km"] > 0

    @patch("backend.infrastructure.celery.tasks.eto_calculation.celery_app")
    @patch("backend.database.connection.get_db")
    @patch("backend.database.data_storage.save_climate_data")
    @patch("backend.api.services.climate_source_manager.ClimateSourceManager")
    @patch("backend.api.services.climate_validation.ClimateValidationService")
    @patch("backend.core.eto_calculation.eto_services.EToProcessingService")
    @patch("nest_asyncio.apply")
    def test_nws_station_lookup_error_handled_gracefully(
        self,
        mock_nest,
        mock_service_cls,
        mock_validation_cls,
        mock_manager_cls,
        mock_save,
        mock_get_db,
        mock_celery,
    ):
        """Test that NWS station lookup failure doesn't crash the task."""
        mock_validation_cls.validate_coordinates.return_value = (True, None)

        mock_manager = MagicMock()
        mock_manager.get_sources_for_data_download.return_value = {
            "sources": ["nws_forecast"],
            "location_info": {"region": "usa_continental"},
        }
        mock_manager_cls.return_value = mock_manager

        mock_service = MagicMock()

        async def mock_process(*args, **kwargs):
            return _basic_result()

        mock_service.process_location = mock_process
        mock_service_cls.return_value = mock_service

        mock_db = MagicMock()
        mock_get_db.return_value = iter([mock_db])
        mock_save.return_value = 2

        with patch("httpx.get") as mock_httpx_get:
            mock_httpx_get.side_effect = Exception("NWS API down")

            mock_self = _make_mock_self()

            result = _call_eto_task(
                mock_self,
                lat=40.7,
                lon=-74.0,
                start_date="2025-01-01",
                end_date="2025-01-02",
                mode="dashboard_current",
            )

            # Task succeeds despite NWS station lookup failure
            assert result["nws_station"] is None
            assert "et0_series" in result

    @patch("backend.infrastructure.celery.tasks.eto_calculation.celery_app")
    @patch("backend.database.connection.get_db")
    @patch("backend.database.data_storage.save_climate_data")
    @patch("backend.api.services.climate_source_manager.ClimateSourceManager")
    @patch("backend.api.services.climate_validation.ClimateValidationService")
    @patch("backend.core.eto_calculation.eto_services.EToProcessingService")
    @patch("nest_asyncio.apply")
    def test_mode_fallback_when_detection_fails(
        self,
        mock_nest,
        mock_service_cls,
        mock_validation_cls,
        mock_manager_cls,
        mock_save,
        mock_get_db,
        mock_celery,
    ):
        """Test fallback to dashboard_current when mode detection fails."""
        mock_validation_cls.validate_coordinates.return_value = (True, None)
        mock_validation_cls.detect_mode_from_dates.return_value = (None, "Cannot detect")

        mock_manager = MagicMock()
        mock_manager.get_sources_for_data_download.return_value = {
            "sources": ["nasa_power"],
            "location_info": {"region": "europe"},
        }
        mock_manager_cls.return_value = mock_manager

        mock_service = MagicMock()

        async def mock_process(*args, **kwargs):
            return _basic_result()

        mock_service.process_location = mock_process
        mock_service_cls.return_value = mock_service

        mock_db = MagicMock()
        mock_get_db.return_value = iter([mock_db])
        mock_save.return_value = 2

        mock_self = _make_mock_self()

        result = _call_eto_task(
            mock_self,
            lat=48.8,
            lon=2.3,
            start_date="2025-01-01",
            end_date="2025-01-02",
            mode=None,
        )

        # Should fall back to dashboard_current
        assert result["mode"] == "dashboard_current"

    @patch("backend.infrastructure.celery.tasks.eto_calculation.celery_app")
    @patch("backend.database.connection.get_db")
    @patch("backend.database.data_storage.save_climate_data")
    @patch("backend.api.services.climate_source_manager.ClimateSourceManager")
    @patch("backend.api.services.climate_validation.ClimateValidationService")
    @patch("backend.core.eto_calculation.eto_services.EToProcessingService")
    @patch("nest_asyncio.apply")
    def test_enable_fusion_passed_to_service(
        self,
        mock_nest,
        mock_service_cls,
        mock_validation_cls,
        mock_manager_cls,
        mock_save,
        mock_get_db,
        mock_celery,
    ):
        """Test that enable_fusion flag is forwarded to the processing service."""
        mock_validation_cls.validate_coordinates.return_value = (True, None)
        mock_validation_cls.detect_mode_from_dates.return_value = (
            "dashboard_current",
            None,
        )

        mock_manager = MagicMock()
        mock_manager.get_sources_for_data_download.return_value = {
            "sources": ["nasa_power", "openmeteo"],
            "location_info": {"region": "south_america"},
        }
        mock_manager_cls.return_value = mock_manager

        mock_service = MagicMock()
        captured_kwargs = {}

        async def mock_process(*args, **kwargs):
            captured_kwargs.update(kwargs)
            return _basic_result()

        mock_service.process_location = mock_process
        mock_service_cls.return_value = mock_service

        mock_db = MagicMock()
        mock_get_db.return_value = iter([mock_db])
        mock_save.return_value = 2

        mock_self = _make_mock_self()

        _call_eto_task(
            mock_self,
            lat=-23.5,
            lon=-46.6,
            start_date="2025-01-01",
            end_date="2025-01-02",
            enable_fusion=True,
        )

        assert captured_kwargs.get("enable_fusion") is True

    @patch("backend.infrastructure.celery.tasks.eto_calculation.celery_app")
    @patch("backend.database.connection.get_db")
    @patch("backend.database.data_storage.save_climate_data")
    @patch("backend.api.services.climate_source_manager.ClimateSourceManager")
    @patch("backend.api.services.climate_validation.ClimateValidationService")
    @patch("backend.core.eto_calculation.eto_services.EToProcessingService")
    @patch("nest_asyncio.apply")
    def test_empty_et0_series_skips_db_save(
        self,
        mock_nest,
        mock_service_cls,
        mock_validation_cls,
        mock_manager_cls,
        mock_save,
        mock_get_db,
        mock_celery,
    ):
        """Test that empty et0_series doesn't attempt to save to DB."""
        mock_validation_cls.validate_coordinates.return_value = (True, None)
        mock_validation_cls.detect_mode_from_dates.return_value = (
            "dashboard_current",
            None,
        )

        mock_manager = MagicMock()
        mock_manager.get_sources_for_data_download.return_value = {
            "sources": ["nasa_power"],
            "location_info": {"region": "south_america"},
        }
        mock_manager_cls.return_value = mock_manager

        mock_service = MagicMock()
        empty_result = _basic_result()
        empty_result["et0_series"] = []

        async def mock_process(*args, **kwargs):
            return empty_result

        mock_service.process_location = mock_process
        mock_service_cls.return_value = mock_service

        mock_db = MagicMock()
        mock_get_db.return_value = iter([mock_db])

        mock_self = _make_mock_self()

        result = _call_eto_task(
            mock_self,
            lat=-23.5,
            lon=-46.6,
            start_date="2025-01-01",
            end_date="2025-01-02",
        )

        # Should not try to save empty data
        mock_save.assert_not_called()
