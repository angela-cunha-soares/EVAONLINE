"""
Performance Tests - Critical Queries

Tests: Benchmark of critical queries
"""

import pytest


@pytest.mark.performance
@pytest.mark.requires_postgres
class TestCriticalQueries:
    """Tests performance of critical queries."""

    def test_climate_data_query_performance(self, db_session):
        """Tests performance of climate data query."""
        # TODO: Benchmark de SELECT em climate_data
        # Target: < 100ms for 1000 records
        assert True

    def test_spatial_query_performance(self, db_session):
        """Testa performance de query espacial."""
        # TODO: Benchmark de ST_DWithin
        # Target: < 50ms com índice GIST
        assert True
