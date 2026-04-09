"""
Shared fixtures for all EVAonline tests
"""

import asyncio
import os
from typing import AsyncGenerator, Generator
from unittest.mock import MagicMock

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from httpx import AsyncClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

# Imports do projeto
from backend.database.connection import Base, get_db
from backend.main import app


# ============================================================================
# AUTO-SKIP requires_postgres WHEN POSTGRESQL IS NOT AVAILABLE
# ============================================================================
def _postgres_is_available() -> bool:
    """Check if PostgreSQL is reachable on localhost:5432."""
    try:
        eng = create_engine(
            f"postgresql+psycopg://{os.environ.get('POSTGRES_USER', 'evaonline')}"
            f":{os.environ.get('POSTGRES_PASSWORD', '')}"
            f"@localhost:5432/{os.environ.get('POSTGRES_DB', 'evaonline')}",
            connect_args={"connect_timeout": 3},
        )
        with eng.connect() as conn:
            conn.execute(text("SELECT 1"))
        eng.dispose()
        return True
    except Exception:
        return False


_POSTGRES_AVAILABLE: bool | None = None


def pytest_collection_modifyitems(config, items):
    """Skip tests marked requires_postgres when PostgreSQL is not available."""
    global _POSTGRES_AVAILABLE
    if _POSTGRES_AVAILABLE is None:
        _POSTGRES_AVAILABLE = _postgres_is_available()

    if _POSTGRES_AVAILABLE:
        return  # PostgreSQL available — run all tests

    skip_pg = pytest.mark.skip(reason="PostgreSQL not available")
    for item in items:
        if "requires_postgres" in item.keywords:
            item.add_marker(skip_pg)


# ============================================================================
# CONFIGURAÇÃO DO AMBIENTE DE TESTES
# ============================================================================
# Load .env so POSTGRES_PASSWORD etc. are available
from dotenv import load_dotenv

load_dotenv()


def _build_pg_url() -> str:
    """Build PostgreSQL URL for the test database using Docker services."""
    user = os.environ.get("POSTGRES_USER", "evaonline")
    pw = os.environ.get("POSTGRES_PASSWORD", "")
    db = os.environ.get("POSTGRES_DB", "evaonline")
    return f"postgresql+psycopg://{user}:{pw}@localhost:5432/{db}"


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Configura variáveis de ambiente para testes"""
    os.environ["ENVIRONMENT"] = "testing"
    os.environ["REDIS_URL"] = "redis://localhost:6379/15"
    os.environ["CELERY_BROKER_URL"] = "redis://localhost:6379/14"
    os.environ["LOG_LEVEL"] = "ERROR"

    # Enable Celery eager mode so tasks run inline (no worker needed)
    from backend.infrastructure.celery.celery_config import celery_app

    celery_app.conf.update(
        task_always_eager=True,
        task_eager_propagates=True,
    )

    yield


# ============================================================================
# DATABASE FIXTURES
# ============================================================================
@pytest.fixture(scope="session")
def _pg_engine():
    """Engine PostgreSQL (Docker) — shared across the whole test session."""
    engine = create_engine(
        _build_pg_url(),
        pool_size=5,
        max_overflow=10,
    )
    # Create all tables (if not already present)
    Base.metadata.create_all(bind=engine)
    yield engine
    engine.dispose()


@pytest.fixture(scope="function")
def test_db_engine(_pg_engine):
    """Engine do banco de dados para testes (PostgreSQL Docker)."""
    yield _pg_engine


@pytest.fixture(scope="function")
def test_db_session(test_db_engine) -> Generator[Session, None, None]:
    """Sessão do banco de dados para testes — cada teste roda numa transação com rollback."""
    connection = test_db_engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)

    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture(scope="function")
def db_session(test_db_session) -> Generator[Session, None, None]:
    """Alias for test_db_session (used by integration/performance tests)."""
    yield test_db_session


@pytest.fixture(scope="function")
def override_get_db(test_db_session):
    """Override da dependência get_db do FastAPI"""

    def _override_get_db():
        try:
            yield test_db_session
        finally:
            test_db_session.close()

    app.dependency_overrides[get_db] = _override_get_db
    yield
    app.dependency_overrides.clear()


# ============================================================================
# API CLIENT FIXTURES
# ============================================================================
@pytest.fixture(scope="function")
def test_client(override_get_db) -> Generator[TestClient, None, None]:
    """Cliente de teste síncrono para a API"""
    with TestClient(app) as client:
        yield client


@pytest.fixture(scope="function")
def api_client(test_client) -> Generator[TestClient, None, None]:
    """Alias for test_client (used by integration tests)"""
    yield test_client


@pytest_asyncio.fixture(scope="function")
async def async_test_client(
    override_get_db,
) -> AsyncGenerator[AsyncClient, None]:
    """Cliente de teste assíncrono para a API"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


# ============================================================================
# REDIS FIXTURES
# ============================================================================
@pytest.fixture(scope="function")
def mock_redis():
    """Mock do Redis para testes unitários"""
    try:
        import fakeredis

        redis_client = fakeredis.FakeRedis(decode_responses=True)
        yield redis_client
        redis_client.flushdb()
    except ImportError:
        # Se fakeredis não estiver instalado, usa mock
        mock = MagicMock()
        mock.get.return_value = None
        mock.set.return_value = True
        mock.delete.return_value = True
        mock.exists.return_value = False
        yield mock


# ============================================================================
# CELERY FIXTURES
# ============================================================================
@pytest.fixture(scope="function")
def mock_celery():
    """Mock do Celery para testes unitários"""
    mock = MagicMock()
    mock.send_task.return_value.id = "test-task-id-123"
    mock.AsyncResult.return_value.state = "SUCCESS"
    mock.AsyncResult.return_value.result = {"status": "completed"}
    yield mock


# ============================================================================
# DATA FIXTURES (Exemplos de dados climáticos)
# ============================================================================
@pytest.fixture
def sample_climate_data():
    """Dados climáticos de exemplo"""
    return {
        "latitude": -23.5505,
        "longitude": -46.6333,
        "date": "2024-01-15",
        "temperature_max": 28.5,
        "temperature_min": 19.2,
        "humidity": 65.0,
        "wind_speed": 3.5,
        "solar_radiation": 22.5,
        "precipitation": 0.0,
    }


@pytest.fixture
def sample_eto_request():
    """Requisição ETO de exemplo (historical)"""
    return {
        "lat": -23.5505,
        "lng": -46.6333,
        "start_date": "2024-01-01",
        "end_date": "2024-01-31",
        "period_type": "historical_email",
        "elevation": 760,
        "email": "test@example.com",
    }


@pytest.fixture
def sample_eto_request_recent():
    """Requisição ETO modo recente (7 dias)"""
    from datetime import date, timedelta

    today = date.today()
    return {
        "lat": -23.5505,
        "lng": -46.6333,
        "start_date": (today - timedelta(days=6)).isoformat(),
        "end_date": today.isoformat(),
        "period_type": "dashboard_current",
    }


@pytest.fixture
def sample_eto_request_forecast():
    """Requisição ETO modo previsão (6 dias)"""
    from datetime import date, timedelta

    today = date.today()
    return {
        "lat": -23.5505,
        "lng": -46.6333,
        "start_date": today.isoformat(),
        "end_date": (today + timedelta(days=5)).isoformat(),
        "period_type": "dashboard_forecast",
    }


@pytest.fixture
def sample_coordinates():
    """Coordenadas de exemplo para testes de integração."""
    return {
        "latitude": -23.5505,
        "longitude": -46.6333,
    }


@pytest.fixture
def sample_measurements():
    """Medições climáticas completas para cálculo FAO-56"""
    return {
        "T2M_MAX": 32.5,
        "T2M_MIN": 18.2,
        "T2M": 25.4,
        "RH2M": 65.0,
        "WS2M": 2.5,
        "PRECTOTCORR": 0.0,
        "ALLSKY_SFC_SW_DWN": 20.5,
        "latitude": -22.2926,
        "longitude": -48.5841,
        "date": "2024-01-15",
        "elevation_m": 580,
    }


@pytest.fixture
def sample_multi_source_df():
    """DataFrame multi-source para testes de fusão"""
    import pandas as pd

    dates = pd.date_range("2024-01-01", periods=5, freq="D")
    rows = []
    for d in dates:
        for src in ["nasa_power", "openmeteo_archive"]:
            rows.append(
                {
                    "date": d,
                    "source": src,
                    "T2M_MAX": 30.0 + (1.0 if src == "nasa_power" else 0.5),
                    "T2M_MIN": 18.0 + (0.5 if src == "nasa_power" else 0.2),
                    "T2M": 24.0 + (0.8 if src == "nasa_power" else 0.3),
                    "RH2M": 65.0,
                    "WS2M": 2.5,
                    "ALLSKY_SFC_SW_DWN": 20.0,
                    "PRECTOTCORR": 0.0,
                }
            )
    return pd.DataFrame(rows)


# ============================================================================
# MOCK EXTERNAL APIS
# ============================================================================


@pytest.fixture
def mock_nasa_power_api(monkeypatch):
    """Mock da API NASA POWER"""

    async def mock_fetch(*args, **kwargs):
        return {
            "properties": {
                "parameter": {
                    "T2M": {"20240115": 23.5},
                    "T2M_MAX": {"20240115": 28.5},
                    "T2M_MIN": {"20240115": 19.2},
                }
            }
        }

    monkeypatch.setattr(
        "backend.api.services.nasa_power.fetch_nasa_power_data", mock_fetch
    )


@pytest.fixture
def mock_openmeteo_api(monkeypatch):
    """Mock da API OpenMeteo"""

    async def mock_fetch(*args, **kwargs):
        return {
            "daily": {
                "time": ["2024-01-15"],
                "temperature_2m_max": [28.5],
                "temperature_2m_min": [19.2],
                "precipitation_sum": [0.0],
            }
        }

    monkeypatch.setattr(
        "backend.api.services.openmeteo_archive.fetch_openmeteo_data",
        mock_fetch,
    )


# ============================================================================
# PERFORMANCE FIXTURES
# ============================================================================


@pytest.fixture
def benchmark_timer():
    """Timer para testes de performance"""
    import time

    class Timer:
        def __enter__(self):
            self.start = time.perf_counter()
            return self

        def __exit__(self, *args):
            self.end = time.perf_counter()
            self.elapsed = self.end - self.start

    return Timer


# ============================================================================
# RATE LIMITER CLEANUP
# ============================================================================


@pytest.fixture(autouse=True)
def flush_rate_limit_keys():
    """Flush Redis rate-limit keys before each test so tests don't interfere."""
    try:
        from redis import Redis

        redis_pwd = os.environ.get("REDIS_PASSWORD") or None
        r = Redis(host="localhost", port=6379, password=redis_pwd, decode_responses=True)
        for key in r.scan_iter("calc_limit:*"):
            r.delete(key)
    except Exception:
        pass  # If Redis unavailable, skip cleanup
    yield


# ============================================================================
# CLEANUP
# ============================================================================


@pytest.fixture(autouse=True)
def cleanup_after_test():
    """Limpa recursos após cada teste"""
    yield
    # Cleanup code aqui se necessário
    try:
        loop = asyncio.get_running_loop()
        loop.run_until_complete(asyncio.sleep(0))
    except RuntimeError:
        pass  # No event loop running — nothing to clean up
