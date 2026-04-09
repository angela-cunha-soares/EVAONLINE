"""
Unit Tests Configuration

Fixtures específicas para testes unitários (mocked).
"""

import pytest
from unittest.mock import Mock


# ============================================================================
# MOCK FIXTURES
# ============================================================================


@pytest.fixture
def mock_nasa_power_client():
    """Mock do cliente NASA Power."""
    mock_client = Mock()
    mock_client.get_climate_data.return_value = {
        "temperature_max": 32.5,
        "temperature_min": 18.2,
        "humidity": 65.0,
    }
    return mock_client


@pytest.fixture
def mock_redis_client():
    """Mock do cliente Redis."""
    mock_redis = Mock()
    mock_redis.get.return_value = None
    mock_redis.set.return_value = True
    return mock_redis


@pytest.fixture
def mock_db_session():
    """Mock da sessão de banco de dados."""
    mock_session = Mock()
    return mock_session
