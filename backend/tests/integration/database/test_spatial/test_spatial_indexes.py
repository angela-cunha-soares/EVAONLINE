"""
Integration Tests for Database Indexes

Tests: Validação de índices essenciais
"""

import pytest
from sqlalchemy import text


@pytest.mark.integration
@pytest.mark.requires_postgres
class TestDatabaseIndexes:
    """Testa índices do banco de dados."""

    def test_regional_coverage_index_exists(self, db_session):
        """Testa que índice em region_id existe."""
        result = db_session.execute(
            text(
                """
                SELECT indexname FROM pg_indexes
                WHERE tablename = 'regional_coverage'
                AND indexname LIKE '%region_id%'
            """
            )
        )
        indexes = [row[0] for row in result]
        assert len(indexes) > 0, "Índice em region_id não encontrado"

    def test_climate_data_indexes(self, db_session):
        """Testa que índices de climate_data existem."""
        result = db_session.execute(
            text(
                """
                SELECT indexname FROM pg_indexes
                WHERE tablename = 'climate_data'
            """
            )
        )
        indexes = [row[0] for row in result]
        assert len(indexes) > 0, "Índices de climate_data não encontrados"
