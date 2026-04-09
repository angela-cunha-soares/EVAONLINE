"""
Integration Tests for Climate Endpoints

Tests: /api/climate endpoints (real FastAPI routes)
"""

import pytest


@pytest.mark.integration
@pytest.mark.requires_docker
class TestClimateEndpoints:
    """Testa endpoints de clima (integração)."""

    def test_get_climate_data(self, api_client):
        """Testa GET /api/climate/data."""
        response = api_client.get(
            "/api/climate/data",
            params={"lat": -22.25, "lon": -48.5, "start_date": "2025-01-01"},
        )
        # TODO: Implementar teste real
        assert response.status_code in [200, 404]
