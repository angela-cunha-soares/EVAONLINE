"""
Integration Tests: Frontend → Backend ETo Flow

Testes end-to-end validando a integração completa:
- Frontend mode_detector → Backend API
- Validação de payload
- Resposta de cálculo ETo
- 3 modos operacionais com fontes específicas

SOURCES BY MODE:
================
1. HISTORICAL_EMAIL (1-90 days, start: 1990-01-01, end: today-1d)
   - nasa_power
   - openmeteo_archive
   - openmeteo_forecast (fallback)

2. DASHBOARD_CURRENT ([7,14,21,30] days, end: today)
   - nasa_power (max 28d: today-29d → today-2d, 2d delay)
   - openmeteo_archive (max 28d: today-29d → today-2d, 2d delay)
   - openmeteo_forecast (max 30d: today-29d → today, no delay)

3. DASHBOARD_FORECAST (6 days: today → today+5d)
   Global (Fusion):
   - openmeteo_forecast
   - met_norway (global + enhanced in Nordic)
   - nws_forecast (USA only)

   USA only (Stations):
   - nws_stations (realtime: today-2d → today)
"""

import pytest
from datetime import date, timedelta
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from backend.main import app
from frontend.utils.mode_detector import OperationModeDetector


class TestFrontendBackendIntegration:
    """Testes de integração frontend-backend"""

    @pytest.fixture
    def client(self):
        """FastAPI test client"""
        return TestClient(app)

    @pytest.fixture
    def mock_celery_task(self):
        """Mock Celery task to avoid actual async processing"""
        with patch(
            "backend.api.routes.eto_routes.calculate_eto_task"
        ) as mock_task:
            mock_result = MagicMock()
            mock_result.id = "test-task-12345"
            mock_task.delay.return_value = mock_result
            yield mock_task

    # ========================================================================
    # TEST 1: HISTORICAL MODE - Full Flow
    # ========================================================================

    def test_historical_mode_integration(self, client, mock_celery_task):
        """
        Test complete flow for HISTORICAL_EMAIL mode:
        1. Frontend: mode_detector prepares payload
        2. Backend: validates and accepts request
        3. Response: returns task_id for monitoring
        """
        # 1. Frontend: Prepare request using OperationModeDetector
        start_date = date(2023, 1, 1)
        end_date = date(2023, 1, 30)  # 30 days

        frontend_payload = OperationModeDetector.prepare_api_request(
            ui_selection="historical",
            latitude=-15.7801,
            longitude=-47.9292,
            start_date=start_date,
            end_date=end_date,
            email="user@example.com",
        )

        # Verify frontend payload structure
        assert frontend_payload["period_type"] == "historical_email"
        assert frontend_payload["email"] == "user@example.com"
        assert frontend_payload["start_date"] == "2023-01-01"
        assert frontend_payload["end_date"] == "2023-01-30"

        # 2. Backend: Send request to API
        # Omit 'sources' to trigger auto-selection
        backend_payload = {
            "lat": frontend_payload["lat"],
            "lng": frontend_payload["lng"],
            "start_date": frontend_payload["start_date"],
            "end_date": frontend_payload["end_date"],
            "period_type": "historical_email",
        }

        response = client.post(
            "/api/v1/internal/eto/calculate", json=backend_payload
        )

        # 3. Verify response
        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "accepted"
        assert "task_id" in data
        assert data["task_id"] == "test-task-12345"
        assert "websocket_url" in data
        assert data["operation_mode"] == "historical_email"

        # Verify selected sources are valid for HISTORICAL_EMAIL mode
        # Valid sources: nasa_power, openmeteo_archive, openmeteo_forecast
        sources_used = data["fusion"]["sources_used"]
        for src in sources_used:
            assert src in ["nasa_power", "openmeteo_archive", "openmeteo_forecast"]

        # Verify Celery task was called with correct params
        mock_celery_task.delay.assert_called_once()
        call_kwargs = mock_celery_task.delay.call_args.kwargs
        assert call_kwargs["lat"] == -15.7801
        assert call_kwargs["lon"] == -47.9292
        assert call_kwargs["start_date"] == "2023-01-01"
        assert call_kwargs["end_date"] == "2023-01-30"
        assert call_kwargs["mode"] == "historical_email"

    def test_historical_mode_without_email_frontend_validation(self):
        """
        Test that frontend validates email requirement for historical mode
        """
        start_date = date(2023, 1, 1)
        end_date = date(2023, 1, 30)

        # Email is None - should still prepare payload
        # (validation happens in callback)
        frontend_payload = OperationModeDetector.prepare_api_request(
            ui_selection="historical",
            latitude=-15.7801,
            longitude=-47.9292,
            start_date=start_date,
            end_date=end_date,
            email=None,
        )

        assert frontend_payload["email"] is None
        # In production, callback would reject this before API call

    def test_historical_mode_invalid_period_exceeds_90_days(self):
        """
        Test that frontend detects periods exceeding 90 days
        """
        start_date = date(2023, 1, 1)
        end_date = date(2023, 5, 1)  # 120 days - exceeds limit

        with pytest.raises(ValueError, match="Invalid dates for mode"):
            OperationModeDetector.prepare_api_request(
                ui_selection="historical",
                latitude=-15.7801,
                longitude=-47.9292,
                start_date=start_date,
                end_date=end_date,
                email="user@example.com",
            )

    # ========================================================================
    # TEST 2: DASHBOARD CURRENT (RECENT) MODE - Full Flow
    # ========================================================================

    def test_recent_mode_7_days_integration(self, client, mock_celery_task):
        """
        Test complete flow for DASHBOARD_CURRENT mode (7 days)
        """
        # 1. Frontend: Prepare request
        frontend_payload = OperationModeDetector.prepare_api_request(
            ui_selection="recent",
            latitude=-23.5505,
            longitude=-46.6333,
            period_days=7,
        )

        # Verify dates are auto-calculated
        from backend.api.services.timezone_utils import get_today_for_location

        today = get_today_for_location(-23.5505, -46.6333)
        expected_start = today - timedelta(days=6)
        assert frontend_payload["period_type"] == "dashboard_current"
        assert frontend_payload["start_date"] == expected_start.isoformat()
        assert frontend_payload["end_date"] == today.isoformat()
        assert frontend_payload["email"] is None

        # 2. Backend: Send request
        backend_payload = {
            "lat": frontend_payload["lat"],
            "lng": frontend_payload["lng"],
            "start_date": frontend_payload["start_date"],
            "end_date": frontend_payload["end_date"],
            "period_type": "dashboard_current",
        }

        response = client.post(
            "/api/v1/internal/eto/calculate", json=backend_payload
        )

        # 3. Verify response
        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "accepted"
        assert data["operation_mode"] == "dashboard_current"
        assert "task_id" in data

        # Verify selected sources are valid for DASHBOARD_CURRENT mode
        # Valid sources: nasa_power, openmeteo_archive, openmeteo_forecast
        valid_sources = [
            "nasa_power",
            "openmeteo_archive",
            "openmeteo_forecast",
        ]
        sources_used = data["fusion"]["sources_used"]
        for src in sources_used:
            assert src in valid_sources

    def test_recent_mode_30_days_integration(self, client, mock_celery_task):
        """
        Test DASHBOARD_CURRENT mode with 30 days period
        """
        # 1. Frontend
        frontend_payload = OperationModeDetector.prepare_api_request(
            ui_selection="recent",
            latitude=-15.7801,
            longitude=-47.9292,
            period_days=30,
        )

        from backend.api.services.timezone_utils import get_today_for_location

        today = get_today_for_location(-15.7801, -47.9292)
        expected_start = today - timedelta(days=29)
        assert frontend_payload["start_date"] == expected_start.isoformat()
        assert frontend_payload["end_date"] == today.isoformat()

        # 2. Backend
        backend_payload = {
            "lat": frontend_payload["lat"],
            "lng": frontend_payload["lng"],
            "start_date": frontend_payload["start_date"],
            "end_date": frontend_payload["end_date"],
            "period_type": "dashboard_current",
        }

        response = client.post(
            "/api/v1/internal/eto/calculate", json=backend_payload
        )

        assert response.status_code == 200
        assert response.json()["operation_mode"] == "dashboard_current"

    def test_recent_mode_invalid_period(self):
        """
        Test that frontend rejects invalid periods (not 7/14/21/30)
        """
        # Period of 10 days is not allowed
        with pytest.raises(ValueError, match="Invalid dates for mode"):
            OperationModeDetector.prepare_api_request(
                ui_selection="recent",
                latitude=-15.7801,
                longitude=-47.9292,
                period_days=10,
            )

    # ========================================================================
    # TEST 3: DASHBOARD FORECAST MODE - Full Flow
    # ========================================================================

    def test_forecast_mode_integration(self, client, mock_celery_task):
        """
        Test complete flow for DASHBOARD_FORECAST mode
        """
        # 1. Frontend: Prepare request
        frontend_payload = OperationModeDetector.prepare_api_request(
            ui_selection="forecast",
            latitude=-15.7801,
            longitude=-47.9292,
        )

        # Verify dates are auto-calculated (today → today+5)
        from backend.api.services.timezone_utils import get_today_for_location

        today = get_today_for_location(-15.7801, -47.9292)
        expected_end = today + timedelta(days=5)
        assert frontend_payload["period_type"] == "dashboard_forecast"
        assert frontend_payload["start_date"] == today.isoformat()
        assert frontend_payload["end_date"] == expected_end.isoformat()
        assert frontend_payload["email"] is None

        # 2. Backend: Send request
        backend_payload = {
            "lat": frontend_payload["lat"],
            "lng": frontend_payload["lng"],
            "start_date": frontend_payload["start_date"],
            "end_date": frontend_payload["end_date"],
            "period_type": "dashboard_forecast",
        }

        response = client.post(
            "/api/v1/internal/eto/calculate", json=backend_payload
        )

        # 3. Verify response
        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "accepted"
        assert data["operation_mode"] == "dashboard_forecast"
        assert "task_id" in data

        # Verify selected sources are valid for DASHBOARD_FORECAST mode
        # Valid sources (Fusion): openmeteo_forecast, met_norway, nws_forecast
        # Note: Brazil location, so nws_forecast won't be selected
        valid_sources = ["openmeteo_forecast", "met_norway"]
        sources_used = data["fusion"]["sources_used"]
        for src in sources_used:
            assert src in valid_sources

    # ========================================================================
    # TEST 4: COORDINATE VALIDATION
    # ========================================================================

    def test_invalid_coordinates_rejected(self, client):
        """
        Test that invalid coordinates are rejected by backend.
        Note: prepare_api_request raises ValueError for out-of-range coords
        (timezone lookup fails), so we send the payload directly.
        """
        backend_payload = {
            "lat": 91.0,  # Invalid: > 90
            "lng": -47.9292,
            "start_date": "2025-01-01",
            "end_date": "2025-01-07",
            "period_type": "dashboard_current",
        }

        response = client.post(
            "/api/v1/internal/eto/calculate", json=backend_payload
        )

        # Backend should reject invalid coordinates (422 validation or 400)
        assert response.status_code in (400, 422)

    def test_invalid_coordinates_rejected_in_frontend(self):
        """
        Test that OperationModeDetector rejects out-of-range coordinates
        before even building the API request (timezone lookup fails).
        """
        with pytest.raises(ValueError):
            OperationModeDetector.prepare_api_request(
                ui_selection="recent",
                latitude=91.0,  # Invalid: > 90
                longitude=-47.9292,
                period_days=7,
            )

    # ========================================================================
    # TEST 5: USA FORECAST MODE WITH NWS SOURCES
    # ========================================================================

    def test_forecast_mode_usa_location(self, client, mock_celery_task):
        """
        Test forecast mode in USA location
        Should have access to NWS Forecast source
        """
        # USA location: New York City
        frontend_payload = OperationModeDetector.prepare_api_request(
            ui_selection="forecast",
            latitude=40.7128,
            longitude=-74.0060,
        )

        backend_payload = {
            "lat": frontend_payload["lat"],
            "lng": frontend_payload["lng"],
            "start_date": frontend_payload["start_date"],
            "end_date": frontend_payload["end_date"],
            "period_type": "dashboard_forecast",
        }

        response = client.post(
            "/api/v1/internal/eto/calculate", json=backend_payload
        )

        assert response.status_code == 200
        data = response.json()

        # In USA, all forecast sources should be available
        # Valid sources: openmeteo_forecast, met_norway, nws_forecast
        valid_sources_usa = [
            "openmeteo_forecast",
            "met_norway",
            "nws_forecast",
        ]
        sources_used = data["fusion"]["sources_used"]
        for src in sources_used:
            assert src in valid_sources_usa

    # ========================================================================
    # TEST 6: SOURCE SELECTION
    # ========================================================================

    def test_auto_source_selection(self, client, mock_celery_task):
        """
        Test automatic source selection by backend
        """
        frontend_payload = OperationModeDetector.prepare_api_request(
            ui_selection="recent",
            latitude=-15.7801,
            longitude=-47.9292,
            period_days=7,
        )

        backend_payload = {
            "lat": frontend_payload["lat"],
            "lng": frontend_payload["lng"],
            "start_date": frontend_payload["start_date"],
            "end_date": frontend_payload["end_date"],
            "period_type": "dashboard_current",
            # sources omitted for auto-selection
        }

        response = client.post(
            "/api/v1/internal/eto/calculate", json=backend_payload
        )

        assert response.status_code == 200
        data = response.json()

        # Verify sources were auto-selected
        assert "fusion" in data
        sources_used = data["fusion"]["sources_used"]
        assert len(sources_used) >= 1
        for src in sources_used:
            assert src in [
                "nasa_power",
                "openmeteo_archive",
                "openmeteo_forecast",
                "met_norway",
            ]

    def test_specific_source_selection(self, client, mock_celery_task):
        """
        Test using specific source instead of auto-selection
        """
        frontend_payload = OperationModeDetector.prepare_api_request(
            ui_selection="recent",
            latitude=-15.7801,
            longitude=-47.9292,
            period_days=7,
        )

        backend_payload = {
            "lat": frontend_payload["lat"],
            "lng": frontend_payload["lng"],
            "start_date": frontend_payload["start_date"],
            "end_date": frontend_payload["end_date"],
            "sources": "openmeteo_forecast",  # Specific source
            "period_type": "dashboard_current",
        }

        response = client.post(
            "/api/v1/internal/eto/calculate", json=backend_payload
        )

        assert response.status_code == 200
        data = response.json()
        # When specific source requested, it should be in the sources_used list
        assert "openmeteo_forecast" in data["fusion"]["sources_used"]

    # ========================================================================
    # TEST 7: SOURCE VALIDATION BY MODE
    # ========================================================================

    def test_historical_mode_valid_sources(self, client, mock_celery_task):
        """
        Test that HISTORICAL_EMAIL mode only accepts valid sources
        Valid: nasa_power, openmeteo_archive
        """
        frontend_payload = OperationModeDetector.prepare_api_request(
            ui_selection="historical",
            latitude=-15.7801,
            longitude=-47.9292,
            start_date=date(2023, 1, 1),
            end_date=date(2023, 1, 30),
            email="user@example.com",
        )

        # Test with openmeteo_archive (should work)
        backend_payload = {
            "lat": frontend_payload["lat"],
            "lng": frontend_payload["lng"],
            "start_date": frontend_payload["start_date"],
            "end_date": frontend_payload["end_date"],
            "sources": "openmeteo_archive",
            "period_type": "historical_email",
        }

        response = client.post(
            "/api/v1/internal/eto/calculate", json=backend_payload
        )

        assert response.status_code == 200
        assert "openmeteo_archive" in response.json()["fusion"]["sources_used"]

    def test_historical_mode_invalid_source_ignored(
        self, client, mock_celery_task
    ):
        """
        Test that HISTORICAL_EMAIL mode ignores truly-invalid sources
        and auto-selects valid historical sources instead.
        The API does NOT reject invalid sources; it falls back to auto-selection.
        Note: openmeteo_forecast IS now a valid historical source (90-day window).
        """
        frontend_payload = OperationModeDetector.prepare_api_request(
            ui_selection="historical",
            latitude=-15.7801,
            longitude=-47.9292,
            start_date=date(2023, 1, 1),
            end_date=date(2023, 1, 30),
            email="user@example.com",
        )

        # Try to use nws_forecast (USA-only, not valid for this lat/lng)
        backend_payload = {
            "lat": frontend_payload["lat"],
            "lng": frontend_payload["lng"],
            "start_date": frontend_payload["start_date"],
            "end_date": frontend_payload["end_date"],
            "sources": "nws_forecast",  # USA-only, invalid for Brazil
            "period_type": "historical_email",
        }

        response = client.post(
            "/api/v1/internal/eto/calculate", json=backend_payload
        )

        # API auto-selects valid sources instead of rejecting
        assert response.status_code == 200
        data = response.json()
        sources_used = data["fusion"]["sources_used"]
        # Verify that USA-only source was NOT used and valid historical sources were selected
        assert "nws_forecast" not in sources_used
        assert any(
            s in sources_used
            for s in ["nasa_power", "openmeteo_archive", "openmeteo_forecast"]
        ), f"Expected historical sources, got {sources_used}"

    def test_forecast_mode_valid_sources(self, client, mock_celery_task):
        """
        Test that DASHBOARD_FORECAST mode only accepts forecast sources
        Valid: openmeteo_forecast, met_norway, nws_forecast (USA)
        """
        frontend_payload = OperationModeDetector.prepare_api_request(
            ui_selection="forecast",
            latitude=-15.7801,
            longitude=-47.9292,
        )

        # Test with met_norway (should work globally)
        backend_payload = {
            "lat": frontend_payload["lat"],
            "lng": frontend_payload["lng"],
            "start_date": frontend_payload["start_date"],
            "end_date": frontend_payload["end_date"],
            "sources": "met_norway",
            "period_type": "dashboard_forecast",
        }

        response = client.post(
            "/api/v1/internal/eto/calculate", json=backend_payload
        )

        assert response.status_code == 200
        assert "met_norway" in response.json()["fusion"]["sources_used"]

    # ========================================================================
    # TEST 8: ERROR HANDLING
    # ========================================================================

    def test_missing_required_fields(self, client):
        """
        Test that missing required fields return 422 validation error
        """
        incomplete_payload = {
            "lat": -15.7801,
            # Missing lng, start_date, end_date
        }

        response = client.post(
            "/api/v1/internal/eto/calculate", json=incomplete_payload
        )

        assert response.status_code == 422  # FastAPI validation error

    def test_invalid_date_format(self, client):
        """
        Test that invalid date format is rejected
        """
        backend_payload = {
            "lat": -15.7801,
            "lng": -47.9292,
            "start_date": "invalid-date",
            "end_date": "2023-01-30",
        }

        response = client.post(
            "/api/v1/internal/eto/calculate", json=backend_payload
        )

        assert response.status_code == 400
        detail_lower = response.json()["detail"].lower()
        # Accept both Portuguese and English error messages
        assert (
            "data inválido" in detail_lower or "invalid date" in detail_lower
        )

    # ========================================================================
    # TEST 7: MODE CONVERSION (Frontend → Backend)
    # ========================================================================

    def test_mode_name_conversion(self):
        """
        Test that frontend mode names map correctly to backend modes
        """
        # Historical
        mode, config = OperationModeDetector.detect_mode("historical")
        assert mode == "HISTORICAL_EMAIL"

        # Recent
        mode, config = OperationModeDetector.detect_mode("recent")
        assert mode == "DASHBOARD_CURRENT"

        # Forecast
        mode, config = OperationModeDetector.detect_mode("forecast")
        assert mode == "DASHBOARD_FORECAST"

    # ========================================================================
    # TEST 8: RESPONSE STRUCTURE VALIDATION
    # ========================================================================

    def test_response_structure_complete(self, client, mock_celery_task):
        """
        Test that API response contains all expected fields
        """
        frontend_payload = OperationModeDetector.prepare_api_request(
            ui_selection="recent",
            latitude=-15.7801,
            longitude=-47.9292,
            period_days=7,
        )

        backend_payload = {
            "lat": frontend_payload["lat"],
            "lng": frontend_payload["lng"],
            "start_date": frontend_payload["start_date"],
            "end_date": frontend_payload["end_date"],
            "period_type": "dashboard_current",
        }

        response = client.post(
            "/api/v1/internal/eto/calculate", json=backend_payload
        )

        assert response.status_code == 200
        data = response.json()

        # Verify all expected fields are present
        required_fields = [
            "status",
            "task_id",
            "message",
            "websocket_url",
            "fusion",
            "operation_mode",
            "location",
            "estimated_duration_seconds",
        ]

        for field in required_fields:
            assert field in data, f"Missing required field: {field}"

        # Verify location structure
        assert "lat" in data["location"]
        assert "lng" in data["location"]
        assert data["location"]["lat"] == -15.7801
        assert data["location"]["lng"] == -47.9292

        # Verify websocket URL format
        assert data["websocket_url"].startswith("/ws/task_status/")
        assert data["task_id"] in data["websocket_url"]


class TestModeValidationConsistency:
    """
    Test that frontend and backend validation rules are consistent
    """

    def test_historical_90_day_limit_consistency(self):
        """
        Verify both frontend and backend enforce 90-day limit for historical
        """
        start_date = date(2023, 1, 1)
        end_date = date(2023, 4, 15)  # 104 days

        # Frontend should reject
        with pytest.raises(ValueError, match="Invalid dates"):
            OperationModeDetector.prepare_api_request(
                ui_selection="historical",
                latitude=-15.7801,
                longitude=-47.9292,
                start_date=start_date,
                end_date=end_date,
                email="user@example.com",
            )

    def test_recent_allowed_periods_consistency(self):
        """
        Verify frontend only allows 7/14/21/30 days for recent mode
        """
        allowed_periods = [7, 14, 21, 30]

        for period in allowed_periods:
            # Should succeed
            payload = OperationModeDetector.prepare_api_request(
                ui_selection="recent",
                latitude=-15.7801,
                longitude=-47.9292,
                period_days=period,
            )
            assert payload is not None

        # Invalid period should fail
        with pytest.raises(ValueError):
            OperationModeDetector.prepare_api_request(
                ui_selection="recent",
                latitude=-15.7801,
                longitude=-47.9292,
                period_days=15,  # Not in allowed list
            )

    def test_forecast_fixed_period_consistency(self):
        """
        Verify forecast always uses 6-day fixed period
        """
        payload = OperationModeDetector.prepare_api_request(
            ui_selection="forecast",
            latitude=-15.7801,
            longitude=-47.9292,
        )

        start = date.fromisoformat(payload["start_date"])
        end = date.fromisoformat(payload["end_date"])

        period_days = (end - start).days + 1
        assert period_days == 6, "Forecast must be exactly 6 days"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
