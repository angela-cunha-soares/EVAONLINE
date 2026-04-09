"""Tests for backend/api/routes/health.py."""

import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from fastapi import FastAPI

from backend.api.routes.health import router


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    return TestClient(app)


class TestHealthCheck:
    def test_health_returns_ok(self, client):
        resp = client.get("/api/v1/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["service"] == "evaonline-api"
        assert "version" in data
        assert "timestamp" in data

    @patch("backend.api.routes.health.perform_full_health_check")
    def test_detailed_health_success(self, mock_health, client):
        mock_health.return_value = {"overall_status": "healthy", "components": {}}
        resp = client.get("/api/v1/health/detailed")
        assert resp.status_code == 200
        data = resp.json()
        assert "api" in data
        assert data["api"]["status"] == "healthy"

    @patch("backend.api.routes.health.perform_full_health_check")
    def test_detailed_health_failure(self, mock_health, client):
        mock_health.side_effect = Exception("DB down")
        resp = client.get("/api/v1/health/detailed")
        assert resp.status_code == 503

    @patch("backend.api.routes.health.perform_full_health_check")
    def test_ready_healthy(self, mock_health, client):
        mock_health.return_value = {"overall_status": "healthy"}
        resp = client.get("/api/v1/ready")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ready"

    @patch("backend.api.routes.health.perform_full_health_check")
    def test_ready_unhealthy(self, mock_health, client):
        mock_health.return_value = {"overall_status": "degraded"}
        resp = client.get("/api/v1/ready")
        assert resp.status_code == 503

    @patch("backend.api.routes.health.perform_full_health_check")
    def test_ready_exception(self, mock_health, client):
        mock_health.side_effect = Exception("crash")
        resp = client.get("/api/v1/ready")
        assert resp.status_code == 503
