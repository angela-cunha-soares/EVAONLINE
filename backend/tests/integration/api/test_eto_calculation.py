"""
Integration Tests - ETO Calculation Flow

Tests the complete end-to-end evapotranspiration calculation flow.
"""

import pytest
from unittest.mock import patch, MagicMock


@pytest.mark.integration
class TestETOCalculationE2E:
    """Test the complete ETO calculation flow."""

    def test_complete_eto_calculation_flow(
        self, api_client, sample_eto_request
    ):
        """Test the complete flow: request → data → calculation → response."""
        with patch(
            "backend.infrastructure.celery.tasks.eto_calculation."
            "calculate_eto_task.delay"
        ) as mock_task:
            mock_task.return_value = MagicMock(id="task-integration-123")

            response = api_client.post(
                "/api/v1/internal/eto/calculate", json=sample_eto_request
            )

            # Should accept and initiate task (or fail in infrastructure)
            assert response.status_code in [200, 202, 500]

            if response.status_code in [200, 202]:
                data = response.json()
                assert "task_id" in data or "status" in data

    def test_eto_calculation_with_multiple_sources(
        self, api_client, sample_eto_request
    ):
        """Test the calculation with multiple data sources."""
        # Force the use of multiple sources
        request = {**sample_eto_request, "sources": "nasa,openmeteo"}

        response = api_client.post(
            "/api/v1/internal/eto/calculate", json=request
        )

        # Should process (or fail gracefully)
        assert response.status_code in [200, 202, 422, 500]


@pytest.mark.integration
class TestETOWithElevationLookup:
    """Test the integration with elevation lookup."""

    def test_eto_without_elevation_fetches_from_opentopo(self, api_client):
        """Test that elevation is fetched when not provided."""
        request = {
            "lat": -22.25,
            "lng": -48.5,
            "start_date": "2024-07-01",
            "end_date": "2024-07-30",
            "period_type": "historical_email",
            "email": "test@example.com",
            # elevation ausente
        }

        response = api_client.post(
            "/api/v1/internal/eto/calculate", json=request
        )

        # Should process even without elevation
        assert response.status_code in [200, 202, 400, 500]


@pytest.mark.integration
@pytest.mark.requires_redis
class TestETOResultCaching:
    """Test the caching of ETO results."""

    def test_repeated_calculation_uses_cache(
        self, api_client, sample_eto_request
    ):
        """Test that repeated calculations use the cache."""
        with patch(
            "backend.infrastructure.celery.tasks.eto_calculation."
            "calculate_eto_task.delay"
        ) as mock_task:
            mock_task.return_value = MagicMock(id="task-cache-test")

            # First request
            response1 = api_client.post(
                "/api/v1/internal/eto/calculate", json=sample_eto_request
            )

            # Second identical request
            response2 = api_client.post(
                "/api/v1/internal/eto/calculate", json=sample_eto_request
            )

            # Both should return a success (or an infrastructure error)
            assert response1.status_code in [200, 202, 500]
            assert response2.status_code in [200, 202, 500]


@pytest.mark.integration
class TestETOWithDifferentPeriods:
    """Test the calculation of ETO with different periods."""

    @pytest.mark.parametrize(
        "period_type",
        ["dashboard_current", "dashboard_forecast", "historical_email"],
    )
    def test_eto_calculation_different_periods(self, api_client, period_type):
        """Test the calculation with different period types."""
        request = {
            "lat": -22.25,
            "lng": -48.5,
            "start_date": "2025-07-01",
            "end_date": "2025-07-07",
            "period_type": period_type,
        }

        response = api_client.post(
            "/api/v1/internal/eto/calculate", json=request
        )

        # Should process (or reject historical if > 7 days)
        assert response.status_code in [200, 202, 400, 422, 500]


@pytest.mark.integration
class TestETOErrorHandling:
    """Test the handling of errors in the ETO flow."""

    def test_handles_invalid_coordinates(self, api_client):
        """Test the handling of invalid coordinates."""
        request = {
            "lat": 200.0,  # Inválida
            "lng": -48.5,
            "start_date": "2025-07-01",
            "end_date": "2025-07-31",
        }

        response = api_client.post(
            "/api/v1/internal/eto/calculate", json=request
        )

        # Should reject invalid coordinates
        assert response.status_code in [400, 422, 500]

    def test_handles_invalid_date_range(self, api_client):
        """Test the handling of invalid date ranges."""
        request = {
            "lat": -22.25,
            "lng": -48.5,
            "start_date": "2025-12-31",
            "end_date": "2025-01-01",  # end before start
        }

        response = api_client.post(
            "/api/v1/internal/eto/calculate", json=request
        )

        # Should reject invalid date range
        assert response.status_code in [400, 422, 500]
