"""
Integration Tests for ETO Endpoints

Tests: /api/eto endpoints (cálculo de evapotranspiração)
"""

import pytest


@pytest.mark.integration
@pytest.mark.requires_docker
class TestETOEndpoints:
    """Testa endpoints de ETO (integração)."""

    def test_calculate_eto(self, api_client):
        """Testa POST /api/eto/calculate."""
        # TODO: Implementar teste real
        assert True
