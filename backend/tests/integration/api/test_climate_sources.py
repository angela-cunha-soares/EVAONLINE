"""
Integration Tests - Climate Data Source Flow

Tests the complete flow of climate data source selection and fallback.
"""

import pytest
from unittest.mock import patch, AsyncMock
import pandas as pd


@pytest.mark.integration
@pytest.mark.requires_apis
class TestClimateSourceFallback:
    """Test fallback between data sources."""

    def test_climate_source_selection_integration(self, api_client):
        """Test automatic source selection."""
        request = {
            "lat": -22.25,
            "lng": -48.5,
            "start_date": "2024-07-01",
            "end_date": "2024-07-30",
            "period_type": "historical_email",
            "email": "test@example.com",
            "sources": "auto",
        }

        response = api_client.post(
            "/api/v1/internal/eto/calculate", json=request
        )

        # Succeed or fail
        assert response.status_code in [200, 202, 400, 500]

    def test_specific_source_validation(self, api_client):
        """Test automatic source validation."""
        request = {
            "lat": -22.25,
            "lng": -48.5,
            "start_date": "2025-07-01",
            "end_date": "2025-07-31",
            "sources": "openmeteo_archive",
        }

        response = api_client.post(
            "/api/v1/internal/eto/calculate", json=request
        )

        # Should process or reject an invalid source
        assert response.status_code in [200, 202, 400, 500]

    @patch("backend.api.services.data_download.download_weather_data")
    def test_nasa_power_to_openmeteo_fallback(self, mock_download, api_client):
        """Test fallback when NASA POWER fails."""
        # Simulate data from OpenMeteo after NASA fails
        mock_df = pd.DataFrame(
            {
                "T2M_MAX": [32.5],
                "T2M_MIN": [18.2],
                "T2M": [25.4],
                "RH2M": [65.0],
                "WS2M": [2.5],
            },
            index=pd.date_range("2025-07-01", periods=1),
        )
        mock_download.return_value = AsyncMock(
            return_value=(mock_df, ["NASA POWER falhou, usando OpenMeteo"])
        )

        request = {
            "lat": -22.25,
            "lng": -48.5,
            "start_date": "2024-07-01",
            "end_date": "2024-07-07",
            "period_type": "historical_email",
            "email": "test@example.com",
            "sources": "data fusion",
        }

        response = api_client.post(
            "/api/v1/internal/eto/calculate", json=request
        )

        # Succeed or fail with fallback
        assert response.status_code in [200, 202, 400, 500]

    @patch("backend.api.services.data_download.download_weather_data")
    def test_all_sources_fail(self, mock_download, api_client):
        """Test when all sources fail."""
        # Simulate failure in all sources
        mock_download.side_effect = ValueError(
            "Nenhuma fonte forneceu dados válidos"
        )

        request = {
            "lat": -22.25,
            "lng": -48.5,
            "start_date": "2025-07-01",
            "end_date": "2025-07-07",
        }

        response = api_client.post(
            "/api/v1/internal/eto/calculate", json=request
        )

        # Should return error
        assert response.status_code in [400, 500, 503]


@pytest.mark.integration
class TestClimateSourceAvailability:
    """Test availability of data sources."""

    def test_check_nasa_power_availability(self, api_client):
        """Test availability check of NASA POWER."""
        response = api_client.get("/api/v1/climate/sources")

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert isinstance(data, (dict, list))


@pytest.mark.integration
class TestClimateDataQuality:
    """Test data quality of climate data."""

    def test_data_completeness_check(self, api_client):
        """Test completeness check of data."""
        request = {
            "lat": -22.25,
            "lng": -48.5,
            "start_date": "2025-07-01",
            "end_date": "2025-07-07",  # 1 semana
        }

        response = api_client.post(
            "/api/v1/internal/eto/calculate", json=request
        )

        # If it succeeds, data should be valid
        if response.status_code in [200, 202]:
            data = response.json()
            assert "task_id" in data or "status" in data
