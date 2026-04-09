"""
Tests for Spatial Queries

Tests: Query handlers para consultas espaciais
"""

import pytest


@pytest.mark.unit
class TestSpatialQueries:
    """Testa queries espaciais."""

    def test_detect_region(self):
        """Testa detecção de região geográfica."""
        from backend.core.utils.geo_utils import detect_geographic_region

        assert detect_geographic_region(-22.9, -43.2) == "brasil"
        assert detect_geographic_region(40.71, -74.0) == "usa"

    def test_reference_city_lookup(self):
        """Testa busca de cidade de referência mais próxima."""
        from backend.core.data_processing.historical_loader import (
            HistoricalDataLoader,
        )

        loader = HistoricalDataLoader()
        found, ref = loader.get_reference_for_location(-22.72, -47.64)
        assert found is True
