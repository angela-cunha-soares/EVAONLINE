"""
Phase 7 – eto_calculation.py Celery task comprehensive tests.

Covers calculate_eto_task (bind=True):
- Validation path (invalid coords → ValueError)
- Full pipeline: source selection → ETo processing → DB save → result
- Email mode: initial email + result email with attachment
- Error handling: retry for API errors, no retry for validation
- Mode auto-detection
- Ocean warning detection
"""

import sys
from contextlib import contextmanager
from unittest.mock import AsyncMock, MagicMock

import pytest



# ──── Helper: inject all lazy-imported modules ────

@contextmanager
def _inject_task_deps():
    """Inject mock modules for all lazy imports inside calculate_eto_task."""
    mock_eto_services = MagicMock()
    mock_validation = MagicMock()
    mock_source_manager = MagicMock()
    mock_source_availability = MagicMock()
    mock_data_storage = MagicMock()
    mock_connection = MagicMock()
    mock_email_utils = MagicMock()
    mock_email_templates = MagicMock()
    mock_nest = MagicMock()

    injected = {
        "backend.core.eto_calculation.eto_services": mock_eto_services,
        "backend.api.services.climate_validation": mock_validation,
        "backend.api.services.climate_source_manager": mock_source_manager,
        "backend.api.services.climate_source_availability": mock_source_availability,
        "backend.database.data_storage": mock_data_storage,
        "backend.database.connection": mock_connection,
        "backend.core.utils.email_utils": mock_email_utils,
        "backend.core.utils.email_templates": mock_email_templates,
        "nest_asyncio": mock_nest,
    }

    saved = {}
    for key, mock in injected.items():
        saved[key] = sys.modules.get(key)
        sys.modules[key] = mock

    mocks = {
        "eto_services": mock_eto_services,
        "validation": mock_validation,
        "source_manager": mock_source_manager,
        "source_availability": mock_source_availability,
        "data_storage": mock_data_storage,
        "connection": mock_connection,
        "email_utils": mock_email_utils,
        "email_templates": mock_email_templates,
    }

    try:
        yield mocks
    finally:
        for key, original in saved.items():
            if original is None:
                sys.modules.pop(key, None)
            else:
                sys.modules[key] = original


def _get_task():
    """Import and return the Celery task object."""
    from backend.infrastructure.celery.tasks.eto_calculation import (
        calculate_eto_task,
    )
    return calculate_eto_task


def _patch_task_context(task, task_id="test-123", retries=0):
    """Patch Celery task request context for testing bind=True tasks."""
    from celery.exceptions import Retry

    task.request.id = task_id
    task.request.retries = retries
    task.retry = MagicMock(side_effect=Retry("mocked retry"))


# ═══════════════════════════════════════════════════════════════
# Tests
# ═══════════════════════════════════════════════════════════════


class TestCalculateEtoTask:
    """Tests for calculate_eto_task."""

    def test_successful_calculation(self):
        with _inject_task_deps() as m:
            task = _get_task()
            _patch_task_context(task, "test-task-123")

            m["validation"].ClimateValidationService.validate_coordinates.return_value = (
                True, None,
            )
            m["validation"].ClimateValidationService.detect_mode_from_dates.return_value = (
                "DASHBOARD_CURRENT", None,
            )

            mock_mgr = MagicMock()
            mock_mgr.get_sources_for_data_download.return_value = {
                "sources": ["nasa_power"],
                "location_info": {"region": "south_america"},
            }
            m["source_manager"].ClimateSourceManager.return_value = mock_mgr

            eto_result = {
                "summary": {"mean_eto": 4.5},
                "et0_series": [{"date": "2024-06-01", "et0_mm_day": 4.5}],
                "quality_metrics": {},
                "elevation": {"value": 760},
            }
            mock_service = MagicMock()
            mock_service.process_location = AsyncMock(return_value=eto_result)
            m["eto_services"].EToProcessingService.return_value = mock_service

            mock_db = MagicMock()
            m["connection"].get_db.return_value = iter([mock_db])
            m["data_storage"].save_climate_data.return_value = 1

            result = task.run(
                lat=-23.55,
                lon=-46.63,
                start_date="2024-06-01",
                end_date="2024-06-14",
            )

            assert result["task_id"] == "test-task-123"
            assert "processing_time_seconds" in result
            assert result["email_sent"] is False

    def test_invalid_coordinates(self):
        with _inject_task_deps() as m:
            task = _get_task()
            _patch_task_context(task, "test-invalid")

            m["validation"].ClimateValidationService.validate_coordinates.return_value = (
                False, "Invalid",
            )

            result = task.run(
                lat=999,
                lon=999,
                start_date="2024-06-01",
                end_date="2024-06-14",
            )

            assert "error" in result

    def test_mode_auto_detection(self):
        with _inject_task_deps() as m:
            task = _get_task()
            _patch_task_context(task, "test-automode")

            m["validation"].ClimateValidationService.validate_coordinates.return_value = (
                True, None,
            )
            m["validation"].ClimateValidationService.detect_mode_from_dates.return_value = (
                "HISTORICAL", None,
            )

            mock_mgr = MagicMock()
            mock_mgr.get_sources_for_data_download.return_value = {
                "sources": ["nasa_power"],
                "location_info": {"region": "europe"},
            }
            m["source_manager"].ClimateSourceManager.return_value = mock_mgr

            mock_service = MagicMock()
            mock_service.process_location = AsyncMock(return_value={
                "summary": {},
                "et0_series": [],
                "elevation": {},
            })
            m["eto_services"].EToProcessingService.return_value = mock_service

            mock_db = MagicMock()
            m["connection"].get_db.return_value = iter([mock_db])

            result = task.run(
                lat=48.85,
                lon=2.35,
                start_date="2023-01-01",
                end_date="2023-12-31",
            )

            assert result["mode"] == "HISTORICAL"

    def test_email_mode_sends_email(self):
        with _inject_task_deps() as m:
            task = _get_task()
            _patch_task_context(task, "test-email")

            m["validation"].ClimateValidationService.validate_coordinates.return_value = (
                True, None,
            )
            m["validation"].ClimateValidationService.detect_mode_from_dates.return_value = (
                "HISTORICAL_EMAIL", None,
            )

            mock_mgr = MagicMock()
            mock_mgr.get_sources_for_data_download.return_value = {
                "sources": ["nasa_power"],
                "location_info": {"region": "south_america"},
            }
            m["source_manager"].ClimateSourceManager.return_value = mock_mgr

            mock_service = MagicMock()
            mock_service.process_location = AsyncMock(return_value={
                "summary": {},
                "et0_series": [{"date": "2024-06-01", "et0_mm_day": 4.0}],
                "elevation": {"value": 760},
            })
            m["eto_services"].EToProcessingService.return_value = mock_service

            mock_db = MagicMock()
            m["connection"].get_db.return_value = iter([mock_db])
            m["data_storage"].save_climate_data.return_value = 1

            # Email mocks
            m["email_utils"].validate_email.return_value = True
            m["email_utils"].send_html_email.return_value = True
            m["email_utils"].send_html_email_with_attachment.return_value = True
            m["email_templates"].create_processing_started_email.return_value = (
                "Subject", "<h1>Started</h1>",
            )
            m["email_templates"].create_data_ready_email.return_value = (
                "Data Ready", "<h1>Done</h1>",
            )

            # Mock pandas for file generation (lazy import inside email block)
            import pandas as _real_pd
            mock_pd = MagicMock()
            mock_df = MagicMock()
            mock_df.empty = False
            mock_pd.DataFrame.return_value = mock_df
            sys.modules["pandas"] = mock_pd

            try:
                result = task.run(
                    lat=-23.55,
                    lon=-46.63,
                    start_date="2024-06-01",
                    end_date="2024-06-14",
                    mode="HISTORICAL_EMAIL",
                    email="user@example.com",
                )

                assert result["email_sent"] is True
            finally:
                sys.modules["pandas"] = _real_pd

    def test_api_error_retries(self):
        from celery.exceptions import Retry

        with _inject_task_deps() as m:
            task = _get_task()
            _patch_task_context(task, "test-retry")

            m["validation"].ClimateValidationService.validate_coordinates.return_value = (
                True, None,
            )
            m["validation"].ClimateValidationService.detect_mode_from_dates.return_value = (
                "DASHBOARD_CURRENT", None,
            )

            mock_mgr = MagicMock()
            mock_mgr.get_sources_for_data_download.return_value = {
                "sources": ["nasa_power"],
                "location_info": {"region": "europe"},
            }
            m["source_manager"].ClimateSourceManager.return_value = mock_mgr

            mock_service = MagicMock()
            mock_service.process_location = AsyncMock(
                side_effect=ConnectionError("API down"),
            )
            m["eto_services"].EToProcessingService.return_value = mock_service

            with pytest.raises(Retry):
                task.run(
                    lat=48.85,
                    lon=2.35,
                    start_date="2024-06-01",
                    end_date="2024-06-14",
                )

            task.retry.assert_called_once()

    def test_db_save_error_continues(self):
        with _inject_task_deps() as m:
            task = _get_task()
            _patch_task_context(task, "test-dbfail")

            m["validation"].ClimateValidationService.validate_coordinates.return_value = (
                True, None,
            )
            m["validation"].ClimateValidationService.detect_mode_from_dates.return_value = (
                "DASHBOARD_CURRENT", None,
            )

            mock_mgr = MagicMock()
            mock_mgr.get_sources_for_data_download.return_value = {
                "sources": ["nasa_power"],
                "location_info": {"region": "europe"},
            }
            m["source_manager"].ClimateSourceManager.return_value = mock_mgr

            mock_service = MagicMock()
            mock_service.process_location = AsyncMock(return_value={
                "summary": {},
                "et0_series": [{"date": "2024-06-01", "et0_mm_day": 4.5}],
                "elevation": {},
            })
            m["eto_services"].EToProcessingService.return_value = mock_service

            mock_db = MagicMock()
            m["connection"].get_db.return_value = iter([mock_db])
            m["data_storage"].save_climate_data.side_effect = Exception("DB err")

            result = task.run(
                lat=48.85,
                lon=2.35,
                start_date="2024-06-01",
                end_date="2024-06-14",
            )

            assert result["task_id"] == "test-dbfail"

    def test_ocean_warning_set(self):
        """When elevation has no_data=True, ocean_warning should be set."""
        with _inject_task_deps() as m:
            task = _get_task()
            _patch_task_context(task, "test-ocean")

            m["validation"].ClimateValidationService.validate_coordinates.return_value = (
                True, None,
            )
            m["validation"].ClimateValidationService.detect_mode_from_dates.return_value = (
                "DASHBOARD_CURRENT", None,
            )

            mock_mgr = MagicMock()
            mock_mgr.get_sources_for_data_download.return_value = {
                "sources": ["nasa_power"],
                "location_info": {"region": "south_america"},
            }
            m["source_manager"].ClimateSourceManager.return_value = mock_mgr

            mock_service = MagicMock()
            mock_service.process_location = AsyncMock(return_value={
                "summary": {},
                "et0_series": [],
                "elevation": {"value": None, "no_data": True},
            })
            m["eto_services"].EToProcessingService.return_value = mock_service

            mock_db = MagicMock()
            m["connection"].get_db.return_value = iter([mock_db])

            result = task.run(
                lat=0.0,
                lon=-30.0,
                start_date="2024-06-01",
                end_date="2024-06-14",
            )

            assert result.get("ocean_warning") is True
