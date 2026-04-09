"""
Integration Tests for Geo Operations

Tests: Operações geoespaciais (Haversine, Shapely)
Nota: Detecção geográfica agora é feita em Python (sem PostGIS)
"""

import pytest


@pytest.mark.integration
@pytest.mark.requires_postgres
class TestGeoOperations:
    """Testa operações geoespaciais em Python."""

    def test_haversine_distance(self):
        """Testa cálculo de distância Haversine."""
        from backend.core.utils.geo_utils import haversine_distance

        # São Paulo → Piracicaba ≈ 150 km
        dist = haversine_distance(-23.55, -46.63, -22.72, -47.64)
        assert 140 < dist < 170

    def test_detect_geographic_region(self):
        """Testa detecção de região geográfica."""
        from backend.core.utils.geo_utils import detect_geographic_region

        assert detect_geographic_region(-22.9, -43.2) == "brasil"
        assert detect_geographic_region(40.71, -74.0) == "usa"
        assert detect_geographic_region(60.17, 24.94) == "nordic"
        assert detect_geographic_region(35.68, 139.69) == "global"
