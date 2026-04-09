"""
Integration Tests for Spatial Repository

Tests: Operações de busca por proximidade (Python/Haversine)
"""

import pytest


@pytest.mark.integration
class TestSpatialRepository:
    """Testa operações de proximidade geográfica."""

    def test_find_within_radius(self):
        """Testa busca de cidades dentro de raio."""
        from backend.core.data_processing.historical_loader import (
            HistoricalDataLoader,
        )

        loader = HistoricalDataLoader()
        found, ref = loader.get_reference_for_location(-22.72, -47.64)
        assert found is True
        assert ref["city"] is not None

    def test_outside_radius(self):
        """Testa localização fora do raio de qualquer cidade."""
        from backend.core.data_processing.historical_loader import (
            HistoricalDataLoader,
        )

        loader = HistoricalDataLoader()
        # Middle of Pacific Ocean
        found, _ = loader.get_reference_for_location(0.0, -150.0)
        assert found is False
