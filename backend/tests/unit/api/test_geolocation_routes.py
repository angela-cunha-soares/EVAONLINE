"""Tests for backend/api/routes/geolocation_routes.py."""

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from fastapi import FastAPI

from backend.api.routes.geolocation_routes import router


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


class TestTrackGeolocation:
    @patch("backend.api.routes.geolocation_routes.GeolocationService")
    def test_track_success(self, mock_service_cls, client):
        mock_service = MagicMock()
        mock_visitor = MagicMock()
        mock_visitor.visitor_id = "visitor_abc"
        mock_visitor.visit_count = 1
        mock_service.create_or_update_visitor.return_value = mock_visitor
        mock_service_cls.return_value = mock_service

        resp = client.post("/api/v1/geolocation/track", json={
            "visitor_id": "visitor_abc",
            "session_id": "sess_xyz",
            "latitude": -15.79,
            "longitude": -47.88,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert data["visitor_id"] == "visitor_abc"

    @patch("backend.api.routes.geolocation_routes.GeolocationService")
    def test_track_without_coordinates(self, mock_service_cls, client):
        mock_service = MagicMock()
        mock_visitor = MagicMock()
        mock_visitor.visitor_id = "visitor_abc"
        mock_visitor.visit_count = 2
        mock_service.create_or_update_visitor.return_value = mock_visitor
        mock_service_cls.return_value = mock_service

        resp = client.post("/api/v1/geolocation/track", json={
            "visitor_id": "visitor_abc",
            "session_id": "sess_xyz",
        })
        assert resp.status_code == 200

    @patch("backend.api.routes.geolocation_routes.GeolocationService")
    def test_track_exception(self, mock_service_cls, client):
        mock_service_cls.return_value.create_or_update_visitor.side_effect = Exception("DB error")

        resp = client.post("/api/v1/geolocation/track", json={
            "visitor_id": "visitor_abc",
            "session_id": "sess_xyz",
        })
        assert resp.status_code == 500

    def test_track_invalid_coords(self, client):
        """Latitude out of range should fail validation."""
        resp = client.post("/api/v1/geolocation/track", json={
            "visitor_id": "visitor_abc",
            "session_id": "sess_xyz",
            "latitude": 999,
        })
        assert resp.status_code == 422
