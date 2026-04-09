"""Tests for backend/api/routes/visitor_routes.py."""

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from fastapi import FastAPI

from backend.api.routes.visitor_routes import router
from backend.database.connection import get_db
from backend.database.redis_pool import get_redis_client


def _make_app():
    """Create a test app with mocked dependencies."""
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    return app


@pytest.fixture
def mock_db():
    return MagicMock()


@pytest.fixture
def mock_redis():
    return MagicMock()


@pytest.fixture
def client(mock_db, mock_redis):
    app = _make_app()
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_redis_client] = lambda: mock_redis
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


class TestIncrementVisitor:
    @patch("backend.api.routes.visitor_routes.VisitorCounterService")
    def test_increment_success(self, mock_svc_cls, client):
        mock_svc = MagicMock()
        mock_svc.increment_visitor.return_value = {
            "total_visitors": 100,
            "current_hour_visitors": 5,
        }
        mock_svc_cls.return_value = mock_svc

        resp = client.post("/api/v1/visitors/increment", json={"session_id": "sess_1"})
        assert resp.status_code == 200

    @patch("backend.api.routes.visitor_routes.VisitorCounterService")
    def test_increment_no_session(self, mock_svc_cls, client):
        mock_svc = MagicMock()
        mock_svc.increment_visitor.return_value = {"total_visitors": 101}
        mock_svc_cls.return_value = mock_svc

        resp = client.post("/api/v1/visitors/increment")
        assert resp.status_code == 200


class TestGetVisitorStats:
    @patch("backend.api.routes.visitor_routes.VisitorCounterService")
    def test_stats_success(self, mock_svc_cls, client):
        mock_svc = MagicMock()
        mock_svc.get_stats.return_value = {
            "total_visitors": 100,
            "current_hour_visitors": 5,
            "current_hour": "14:00",
        }
        mock_svc_cls.return_value = mock_svc

        resp = client.get("/api/v1/visitors/stats")
        assert resp.status_code == 200
