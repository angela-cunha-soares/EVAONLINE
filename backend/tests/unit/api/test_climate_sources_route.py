"""
Unit tests for backend/api/routes/climate_sources.py.

Tests the route handler logic with mocked dependencies.
"""

from unittest.mock import patch

from fastapi.testclient import TestClient


class TestGetAvailableSourcesNoCoords:
    """Test the /climate/sources/available endpoint without coordinates."""

    @patch("backend.api.routes.climate_sources._eto_validator")
    @patch("backend.api.routes.climate_sources._manager")
    def test_returns_all_sources(self, mock_manager, mock_validator):
        from backend.main import app

        mock_manager.SOURCES_CONFIG = {
            "openmeteo_archive": {
                "name": "Open-Meteo Archive",
                "coverage": "global",
                "license": "CC-BY-4.0",
                "temporal_range": "1990-present",
                "variables": ["temperature", "humidity"],
                "realtime": False,
                "priority": 1,
            },
        }
        mock_validator.get_source_description.return_value = {
            "has_complete_eto": True,
            "description": "Complete set",
            "missing_variables": [],
        }

        client = TestClient(app)
        response = client.get("/api/v1/climate/sources/available")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["total_sources"] >= 1
        assert data["location"] is None

    @patch("backend.api.routes.climate_sources._eto_validator")
    @patch("backend.api.routes.climate_sources._manager")
    def test_source_fields(self, mock_manager, mock_validator):
        from backend.main import app

        mock_manager.SOURCES_CONFIG = {
            "nasa_power": {
                "name": "NASA POWER",
                "coverage": "global",
                "license": "NASA",
                "temporal_range": "1990-present",
                "variables": ["T2M"],
                "realtime": False,
                "priority": 2,
            },
        }
        mock_validator.get_source_description.return_value = {
            "has_complete_eto": True,
            "description": "OK",
            "missing_variables": [],
        }

        client = TestClient(app)
        response = client.get("/api/v1/climate/sources/available")
        sources = response.json()["sources"]
        assert len(sources) >= 1

        src = sources[0]
        assert "id" in src
        assert "name" in src
        assert "coverage" in src
        assert "has_complete_eto" in src


class TestGetAvailableSourcesWithCoords:
    """Test the endpoint with lat/lon parameters."""

    @patch("backend.api.services.climate_source_selector.get_available_sources_for_frontend")
    @patch("backend.api.routes.climate_sources._eto_validator")
    @patch("backend.api.routes.climate_sources._manager")
    def test_with_coords(self, mock_manager, mock_validator, mock_frontend):
        from backend.main import app

        mock_manager.SOURCES_CONFIG = {
            "openmeteo_archive": {
                "name": "Open-Meteo Archive",
                "coverage": "global",
                "license": "CC-BY-4.0",
                "temporal_range": "1990-present",
                "variables": ["T2M"],
                "realtime": False,
                "priority": 1,
            },
        }
        mock_validator.get_source_description.return_value = {
            "has_complete_eto": True,
            "description": "OK",
            "missing_variables": [],
        }
        mock_frontend.return_value = {
            "sources": [
                {
                    "value": "openmeteo_archive",
                    "label": "Open-Meteo Archive",
                    "description": "Historical",
                }
            ],
            "location_info": {
                "region": "South America",
                "in_usa": False,
                "in_nordic": False,
            },
        }

        client = TestClient(app)
        response = client.get(
            "/api/v1/climate/sources/available",
            params={"lat": -23.55, "lon": -46.63},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["geographic_context"] == "global"


class TestRouterConfig:
    """Test router-level configuration."""

    def test_router_prefix(self):
        from backend.api.routes.climate_sources import router
        assert router.prefix == "/climate/sources"

    def test_router_tags(self):
        from backend.api.routes.climate_sources import router
        assert "Climate" in router.tags
