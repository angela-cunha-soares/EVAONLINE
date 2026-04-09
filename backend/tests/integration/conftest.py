"""
Integration Tests Configuration

Fixtures específicas para testes de integração (DB/Redis reais).
"""

import pytest


# ============================================================================
# DATABASE FIXTURES (Integration)
# ============================================================================


@pytest.fixture(scope="function")
def clean_db(db_session):
    """
    Banco limpo para cada teste de integração.

    Trunca tabelas principais antes do teste.
    """
    from backend.tests.helpers.database_utils import DatabaseUtils

    # Truncar tabelas principais
    tables = ["climate_data", "regional_coverage", "visitor_stats"]
    for table in tables:
        try:
            DatabaseUtils.truncate_table(db_session, table)
        except Exception:
            # Tabela pode não existir ainda
            pass

    yield db_session


# ============================================================================
# SAMPLE DATA FIXTURES
# ============================================================================


@pytest.fixture
def sample_climate_data():
    """Dados climáticos de exemplo para testes."""
    from backend.tests.fixtures.factories.climate_data_factory import (
        ClimateDataFactory,
    )

    return ClimateDataFactory.create_sample_data()


@pytest.fixture
def sample_90_day_series():
    """Série de 90 dias de dados climáticos."""
    from backend.tests.fixtures.factories.climate_data_factory import (
        ClimateDataFactory,
    )

    return ClimateDataFactory.create_90_day_series()


@pytest.fixture
def sample_point_geometry():
    """Geometria POINT de exemplo."""
    from backend.tests.fixtures.factories.geometry_factory import (
        GeometryFactory,
    )

    return GeometryFactory.create_point_ewkt()
