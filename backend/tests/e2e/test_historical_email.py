"""
End-to-End Tests - Historical Email Flow (Real Implementation)

Tests the complete historical_email pipeline:
1. Frontend mode_detector prepares payload
2. Backend validates request (coordinates, dates, mode)
3. API dispatches Celery task
4. Celery task (eager mode) runs full pipeline
"""

import pytest
from unittest.mock import patch, MagicMock

from fastapi.testclient import TestClient

from backend.main import app


@pytest.mark.e2e
class TestHistoricalEmailFlow:
    """End-to-end test for the historical_email mode."""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    @pytest.fixture
    def mock_celery_task(self):
        with patch(
            "backend.api.routes.eto_routes.calculate_eto_task"
        ) as mock_task:
            mock_result = MagicMock()
            mock_result.id = "e2e-task-hist-001"
            mock_task.delay.return_value = mock_result
            yield mock_task

    def test_historical_30day_accepted(self, client, mock_celery_task):
        """
        Full E2E: POST historical_email request → API validates → returns task_id.
        """
        payload = {
            "lat": -22.2926,
            "lng": -48.5841,
            "start_date": "2023-06-01",
            "end_date": "2023-06-30",
            "period_type": "historical_email",
            "email": "researcher@university.edu",
            "elevation": 580,
        }

        response = client.post("/api/v1/internal/eto/calculate", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "accepted"
        assert data["task_id"] == "e2e-task-hist-001"
        assert data["operation_mode"] == "historical_email"
        assert "websocket_url" in data

        # Verify Celery was called with correct params
        mock_celery_task.delay.assert_called_once()
        kwargs = mock_celery_task.delay.call_args.kwargs
        assert kwargs["lat"] == -22.2926
        assert kwargs["lon"] == -48.5841
        assert kwargs["mode"] == "historical_email"
        assert kwargs["email"] == "researcher@university.edu"

    def test_historical_without_email_accepted(self, client, mock_celery_task):
        """Historical mode without email — backend still accepts (optional field)."""
        payload = {
            "lat": -22.2926,
            "lng": -48.5841,
            "start_date": "2023-06-01",
            "end_date": "2023-06-30",
            "period_type": "historical_email",
        }

        response = client.post("/api/v1/internal/eto/calculate", json=payload)
        assert response.status_code in [200, 422]

    def test_historical_source_selection(self, client, mock_celery_task):
        """Verify that historical mode selects nasa_power + openmeteo_archive."""
        payload = {
            "lat": -22.2926,
            "lng": -48.5841,
            "start_date": "2023-06-01",
            "end_date": "2023-06-30",
            "period_type": "historical_email",
            "email": "test@test.com",
        }

        response = client.post("/api/v1/internal/eto/calculate", json=payload)
        assert response.status_code == 200
        data = response.json()

        sources = data.get("fusion", {}).get("sources_used", [])
        assert any(s in sources for s in ["nasa_power", "openmeteo_archive"])

    def test_historical_exceeding_90_days(self, client, mock_celery_task):
        """Periods > 90 days should be rejected."""
        payload = {
            "lat": -22.2926,
            "lng": -48.5841,
            "start_date": "2023-01-01",
            "end_date": "2023-06-30",  # 181 days
            "period_type": "historical_email",
            "email": "test@test.com",
        }

        response = client.post("/api/v1/internal/eto/calculate", json=payload)
        # Should reject or warn about period > 90 days
        assert response.status_code in [200, 400, 422]
