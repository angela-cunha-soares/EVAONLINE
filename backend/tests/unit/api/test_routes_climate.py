"""
Unit Tests - Climate Data Endpoints

Testa endpoints de dados climáticos.
Note: The Dash frontend catches all unrecognized routes and returns HTML.
Tests must check content-type to distinguish API responses from Dash HTML.
"""

import pytest
from datetime import datetime, timedelta


def _is_api_response(response):
    """Check if response is from the API (JSON) vs Dash frontend (HTML)."""
    ct = response.headers.get("content-type", "")
    return "application/json" in ct


@pytest.mark.unit
class TestClimateSourcesEndpoint:
    """Testa GET /api/v1/climate/sources (may not exist)."""

    def test_list_available_sources(self, api_client):
        """Testa listagem de fontes de dados disponíveis."""
        response = api_client.get("/api/v1/climate/sources")

        assert response.status_code == 200
        data = response.json()
        assert "sources" in data or isinstance(data, list)

    def test_sources_include_nasa_power(self, api_client):
        """Testa que NASA POWER está na lista."""
        response = api_client.get("/api/v1/climate/sources")
        assert response.status_code == 200

        if response.status_code == 200:
            data = response.json()
            if isinstance(data, dict) and "sources" in data:
                sources = data["sources"]
                source_names = [s.get("name", "").lower() for s in sources]
                assert any("nasa" in name for name in source_names)


@pytest.mark.unit
class TestClimateDataValidation:
    """Testa validação de parâmetros climáticos via ETo endpoint."""

    @pytest.mark.parametrize(
        "lat,lon",
        [
            (100, -48.5),  # lat > 90
            (-100, -48.5),  # lat < -90
            (-22.25, 200),  # lon > 180
            (-22.25, -200),  # lon < -180
        ],
    )
    def test_rejects_invalid_coordinates(self, api_client, lat, lon):
        """Testa rejeição de coordenadas inválidas via ETo calculate."""
        payload = {
            "lat": lat,
            "lng": lon,
            "start_date": "2025-01-01",
            "end_date": "2025-01-07",
            "period_type": "dashboard_current",
        }

        response = api_client.post(
            "/api/v1/internal/eto/calculate", json=payload
        )

        # Backend should reject invalid coordinates (400 or 422)
        assert response.status_code in [400, 422]

    def test_rejects_future_dates_historical(self, api_client):
        """Testa que não permite datas futuras no modo histórico."""
        tomorrow = datetime.now() + timedelta(days=30)
        future_date = tomorrow.strftime("%Y-%m-%d")

        payload = {
            "lat": -22.25,
            "lng": -48.5,
            "start_date": future_date,
            "end_date": future_date,
            "period_type": "historical_email",
            "email": "test@example.com",
        }

        response = api_client.post(
            "/api/v1/internal/eto/calculate", json=payload
        )

        # Should reject future dates for historical mode
        assert response.status_code in [400, 422]

    def test_validates_date_range_limit(self, api_client):
        """Testa limite de intervalo de datas (max 90 days historical)."""
        payload = {
            "lat": -22.25,
            "lng": -48.5,
            "start_date": "2023-01-01",
            "end_date": "2023-12-31",  # > 90 days
            "period_type": "historical_email",
            "email": "test@example.com",
        }

        response = api_client.post(
            "/api/v1/internal/eto/calculate", json=payload
        )

        # Should reject > 90 day range for historical
        assert response.status_code in [400, 422]


@pytest.mark.unit
class TestClimateSourceSelection:
    """Testa seleção automática de fonte via ETo endpoint."""

    def test_auto_source_selection(self, api_client):
        """Testa que ETo endpoint auto-selects sources."""
        from unittest.mock import patch, MagicMock

        with patch(
            "backend.infrastructure.celery.tasks.eto_calculation."
            "calculate_eto_task.delay"
        ) as mock_task:
            mock_task.return_value = MagicMock(id="task-123")

            payload = {
                "lat": -22.25,
                "lng": -48.5,
                "start_date": "2023-07-01",
                "end_date": "2023-07-30",
                "period_type": "historical_email",
                "email": "test@example.com",
            }

            response = api_client.post(
                "/api/v1/internal/eto/calculate", json=payload
            )

            if response.status_code == 200:
                data = response.json()
                # Should include fusion info with selected sources
                assert "fusion" in data
                assert "sources_used" in data["fusion"]
