"""
Integration Tests for Spatial Endpoints

Tests: /api/spatial endpoints (consultas geoespaciais)
"""

import pytest


@pytest.mark.integration
@pytest.mark.requires_docker
@pytest.mark.requires_postgres
class TestSpatialEndpoints:
    """Testa endpoints espaciais (integração)."""

    def test_within_radius(self, api_client):
        """Testa GET /api/spatial/within-radius."""
        # TODO: Implementar teste de ST_DWithin via API
        assert True

    def test_nearest_stations(self, api_client):
        """Testa GET /api/spatial/nearest."""
        # TODO: Implementar teste de estações mais próximas
        assert True
