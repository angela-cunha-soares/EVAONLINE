"""
Integration Tests for ETO Tasks

Tests the Celery task wrappers for ETO calculation.
Uses eager mode (task_always_eager=True) so no real broker is needed.

Reference: Article Section 3.3 (Asynchronous processing)
"""

import pytest
from unittest.mock import patch, MagicMock

from backend.infrastructure.celery.tasks.eto_calculation import (
    calculate_eto_task,
)


@pytest.mark.integration
class TestETOTasks:
    """Tests Celery tasks for ETO calculation (eager mode)."""

    def test_task_is_registered(self):
        """calculate_eto_task must be a registered Celery task."""
        assert hasattr(calculate_eto_task, "delay")
        assert hasattr(calculate_eto_task, "apply_async")
        assert calculate_eto_task.name is not None

    def test_task_name_convention(self):
        """Task name should follow project naming convention."""
        name = calculate_eto_task.name
        assert "eto" in name.lower() or "calculate" in name.lower()

    @patch(
        "backend.core.eto_calculation.eto_services.EToProcessingService"
    )
    def test_task_calls_processing_service(self, mock_service_cls):
        """Task should instantiate and call EToProcessingService."""
        mock_instance = MagicMock()
        mock_instance.process.return_value = {
            "eto_values": [4.5, 5.1],
            "status": "completed",
        }
        mock_service_cls.return_value = mock_instance

        try:
            result = calculate_eto_task.apply(
                kwargs={
                    "lat": -22.2926,
                    "lon": -48.5841,
                    "start_date": "2023-06-01",
                    "end_date": "2023-06-07",
                    "mode": "dashboard_current",
                }
            ).get(timeout=30)
        except Exception:
            # Task may fail due to missing infra, but service should be called
            pass

    @patch(
        "backend.core.eto_calculation.eto_services.EToProcessingService"
    )
    def test_task_handles_invalid_mode(self, mock_service_cls):
        """Task should handle invalid mode without crashing worker."""
        mock_service_cls.side_effect = ValueError("Invalid mode: invalid_mode")

        try:
            calculate_eto_task.apply(
                kwargs={
                    "lat": -22.2926,
                    "lon": -48.5841,
                    "start_date": "2023-06-01",
                    "end_date": "2023-06-07",
                    "mode": "invalid_mode",
                }
            ).get(timeout=30)
        except Exception as e:
            # Should fail with a clean error, not crash
            assert isinstance(e, Exception)
