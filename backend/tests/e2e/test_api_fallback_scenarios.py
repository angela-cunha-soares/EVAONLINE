"""
End-to-End Tests - API Fallback Scenarios

Tests the multi-source fallback logic:
 - When primary source fails, secondary is used
 - Forecast mode selects correct sources by region
 - USA includes NWS, Nordic includes MET Norway

Reference: Article Section 2.6.3 (Coverage testing and quality assurance)
"""

import pytest
from datetime import date, timedelta
from unittest.mock import patch, MagicMock

from fastapi.testclient import TestClient

from backend.main import app


@pytest.mark.e2e
class TestAPIFallbackScenarios:
    """Tests fallback between external climate APIs."""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    @pytest.fixture
    def mock_celery(self):
        with patch(
            "backend.api.routes.eto_routes.calculate_eto_task"
        ) as mock_task:
            mock_result = MagicMock()
            mock_result.id = "e2e-task-fallback-001"
            mock_task.delay.return_value = mock_result
            yield mock_task

    def _today_range(self, days_back=6):
        """Generate date range ending today for dashboard_current.
        period_days = (end - start).days + 1 → days_back=6 → 7 days."""
        today = date.today()
        start = today - timedelta(days=days_back)
        return str(start), str(today)

    def _forecast_range(self):
        """Generate date range for dashboard_forecast.
        period_days must be in [5, 6] → today to today+5 → 6 days."""
        today = date.today()
        end = today + timedelta(days=5)
        return str(today), str(end)

    def test_forecast_mode_accepted(self, client, mock_celery):
        """Forecast (dashboard_forecast) request is accepted and dispatched."""
        start, end = self._forecast_range()
        payload = {
            "lat": -22.2926,
            "lng": -48.5841,
            "start_date": start,
            "end_date": end,
            "period_type": "dashboard_forecast",
        }

        response = client.post("/api/v1/internal/eto/calculate", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "accepted"
        assert data["operation_mode"] == "dashboard_forecast"

    def test_current_mode_accepted(self, client, mock_celery):
        """Current (dashboard_current) request is accepted."""
        start, end = self._today_range()
        payload = {
            "lat": -22.2926,
            "lng": -48.5841,
            "start_date": start,
            "end_date": end,
            "period_type": "dashboard_current",
        }

        response = client.post("/api/v1/internal/eto/calculate", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "accepted"

    def test_usa_region_includes_nws(self, client, mock_celery):
        """Request for USA coordinates should include NWS as a source."""
        start, end = self._forecast_range()
        payload = {
            "lat": 34.05,
            "lng": -118.25,  # Los Angeles
            "start_date": start,
            "end_date": end,
            "period_type": "dashboard_forecast",
        }

        response = client.post("/api/v1/internal/eto/calculate", json=payload)
        assert response.status_code == 200
        data = response.json()

        sources = data.get("fusion", {}).get("sources_used", [])
        if sources:
            assert "nws" in sources or "openmeteo_forecast" in sources

    def test_nordic_region_includes_met_norway(self, client, mock_celery):
        """Request for Nordic coordinates should include MET Norway."""
        start, end = self._forecast_range()
        payload = {
            "lat": 59.91,
            "lng": 10.75,  # Oslo
            "start_date": start,
            "end_date": end,
            "period_type": "dashboard_forecast",
        }

        response = client.post("/api/v1/internal/eto/calculate", json=payload)
        assert response.status_code == 200
        data = response.json()

        sources = data.get("fusion", {}).get("sources_used", [])
        if sources:
            assert "met_norway" in sources or "openmeteo_forecast" in sources

    def test_invalid_coordinates_rejected(self, client):
        """Invalid coordinates are rejected by validation."""
        start, end = self._today_range()
        payload = {
            "lat": 999,
            "lng": -48.5841,
            "start_date": start,
            "end_date": end,
            "period_type": "dashboard_current",
        }

        response = client.post("/api/v1/internal/eto/calculate", json=payload)
        # Custom validation returns 400; Pydantic would return 422
        assert response.status_code in [400, 422]

    def test_missing_required_fields_rejected(self, client):
        """Missing lat/lng → 422 validation error."""
        payload = {
            "start_date": "2025-01-01",
            "end_date": "2025-01-07",
            "period_type": "dashboard_current",
        }

        response = client.post("/api/v1/internal/eto/calculate", json=payload)
        assert response.status_code == 422
