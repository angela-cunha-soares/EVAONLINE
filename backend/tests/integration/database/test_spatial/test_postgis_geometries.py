"""
Integration Tests for Geographic Utilities

Tests: Validação de utilitários geográficos Python
"""

import pytest


@pytest.mark.integration
class TestGeographicUtilities:
    """Testa utilitários geográficos."""

    def test_brazil_detection(self):
        """Testa detecção de coordenadas dentro do Brasil."""
        from backend.core.utils.geo_utils import detect_geographic_region

        assert detect_geographic_region(-22.9, -43.2) == "brasil"
        assert detect_geographic_region(-9.97, -67.81) == "brasil"

    def test_outside_brazil(self):
        """Testa coordenadas fora do Brasil."""
        from backend.core.utils.geo_utils import detect_geographic_region

        assert detect_geographic_region(-34.6, -58.38) == "global"  # Buenos Aires
        assert detect_geographic_region(-32.889, -68.846) == "global"  # Mendoza
