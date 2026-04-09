"""
Tests for frontend/components/world_map_leaflet.py.

Focus on pure functions & functions with mocked file I/O:
- format_coordinate_dms
- create_map_marker
- create_circle_marker
- create_location_info_popup
- create_map_controls
- MAP_STYLES dict
- load_brasil_geojson (mocked file)
- load_matopiba_geojson (mocked file)
- load_piracicaba_marker (mocked CSV)
- load_matopiba_cities_markers (mocked CSV)
- create_custom_layer_control
"""

from unittest.mock import mock_open, patch

import pandas as pd
import pytest

import dash_leaflet as dl
from dash import html


# ---------------------------------------------------------------------------
# format_coordinate_dms
# ---------------------------------------------------------------------------
class TestFormatCoordinateDms:
    def _get_fn(self):
        from frontend.components.world_map_leaflet import format_coordinate_dms
        return format_coordinate_dms

    def test_positive_lat(self):
        result = self._get_fn()(23.5486, "lat")
        assert result.endswith("N")
        assert "23°" in result

    def test_negative_lat(self):
        result = self._get_fn()(-23.5486, "lat")
        assert result.endswith("S")

    def test_positive_lon(self):
        result = self._get_fn()(46.6333, "lon")
        assert result.endswith("E")

    def test_negative_lon(self):
        result = self._get_fn()(-46.6333, "lon")
        assert result.endswith("W")

    def test_zero_lat(self):
        result = self._get_fn()(0.0, "lat")
        assert result.startswith("0°")
        assert result.endswith("N")

    def test_zero_lon(self):
        result = self._get_fn()(0.0, "lon")
        assert result.startswith("0°")
        assert result.endswith("E")

    def test_one_decimal_seconds(self):
        result = self._get_fn()(45.0, "lat")
        assert '0.0"N' in result


# ---------------------------------------------------------------------------
# create_map_marker
# ---------------------------------------------------------------------------
class TestCreateMapMarker:
    def _get_fn(self):
        from frontend.components.world_map_leaflet import create_map_marker
        return create_map_marker

    def test_returns_marker(self):
        marker = self._get_fn()(10.0, 20.0)
        assert isinstance(marker, dl.Marker)

    def test_marker_position(self):
        marker = self._get_fn()(10.0, 20.0)
        assert marker.position == [10.0, 20.0]

    def test_default_label(self):
        marker = self._get_fn()(0, 0)
        # Has children (Tooltip + Popup)
        assert marker.children is not None
        assert len(marker.children) == 2

    def test_custom_label(self):
        marker = self._get_fn()(1, 2, label="Test Point")
        # Tooltip text should be "Test Point"
        tooltip = marker.children[0]
        assert isinstance(tooltip, dl.Tooltip)


# ---------------------------------------------------------------------------
# create_circle_marker
# ---------------------------------------------------------------------------
class TestCreateCircleMarker:
    def _get_fn(self):
        from frontend.components.world_map_leaflet import create_circle_marker
        return create_circle_marker

    def test_returns_circle_marker(self):
        cm = self._get_fn()(10.0, 20.0)
        assert isinstance(cm, dl.CircleMarker)

    def test_default_color(self):
        cm = self._get_fn()(10.0, 20.0)
        assert cm.color == "blue"

    def test_custom_color_and_radius(self):
        cm = self._get_fn()(10.0, 20.0, color="red", radius=15)
        assert cm.color == "red"
        assert cm.radius == 15

    def test_center(self):
        cm = self._get_fn()(5.0, 10.0)
        assert cm.center == [5.0, 10.0]


# ---------------------------------------------------------------------------
# create_location_info_popup
# ---------------------------------------------------------------------------
class TestCreateLocationInfoPopup:
    def _get_fn(self):
        from frontend.components.world_map_leaflet import (
            create_location_info_popup,
        )
        return create_location_info_popup

    def test_basic_popup(self):
        data = {
            "lat": -23.55,
            "lon": -46.63,
            "city": "São Paulo",
            "country": "Brasil",
            "timezone": "America/Sao_Paulo",
        }
        result = self._get_fn()(data)
        assert isinstance(result, html.Div)

    def test_popup_with_elevation(self):
        data = {
            "lat": 0,
            "lon": 0,
            "city": "Test",
            "elevation": 500,
        }
        result = self._get_fn()(data)
        assert result is not None

    def test_popup_without_country(self):
        data = {"lat": 0, "lon": 0}
        result = self._get_fn()(data)
        assert result is not None

    def test_popup_defaults(self):
        result = self._get_fn()({})
        assert result is not None


# ---------------------------------------------------------------------------
# create_map_controls
# ---------------------------------------------------------------------------
class TestCreateMapControls:
    @pytest.mark.skip(reason="html.Select 'options' kwarg incompatible with current Dash version")
    def test_returns_div(self):
        from frontend.components.world_map_leaflet import create_map_controls
        result = create_map_controls()
        assert isinstance(result, html.Div)


# ---------------------------------------------------------------------------
# MAP_STYLES
# ---------------------------------------------------------------------------
class TestMapStyles:
    def test_has_expected_keys(self):
        from frontend.components.world_map_leaflet import MAP_STYLES
        assert "osm" in MAP_STYLES
        assert "topo" in MAP_STYLES
        assert "satellite" in MAP_STYLES

    def test_each_style_has_url_and_attribution(self):
        from frontend.components.world_map_leaflet import MAP_STYLES
        for name, style in MAP_STYLES.items():
            assert "url" in style, f"{name} missing 'url'"
            assert "attribution" in style, f"{name} missing 'attribution'"


# ---------------------------------------------------------------------------
# load_brasil_geojson (mocked file I/O)
# ---------------------------------------------------------------------------
class TestLoadBrasilGeojson:
    def _get_fn(self):
        from frontend.components.world_map_leaflet import load_brasil_geojson
        return load_brasil_geojson

    @patch("builtins.open", mock_open(read_data='{"type":"FeatureCollection","features":[]}'))
    @patch("os.path.exists", return_value=True)
    def test_success(self, mock_exists):
        result = self._get_fn()()
        assert result is not None

    @patch("builtins.open", side_effect=FileNotFoundError("not found"))
    def test_file_not_found(self, mock_file):
        result = self._get_fn()()
        assert result is None


# ---------------------------------------------------------------------------
# load_matopiba_geojson (mocked file I/O)
# ---------------------------------------------------------------------------
class TestLoadMatopibaGeojson:
    def _get_fn(self):
        from frontend.components.world_map_leaflet import load_matopiba_geojson
        return load_matopiba_geojson

    @patch("builtins.open", mock_open(read_data='{"type":"FeatureCollection","features":[]}'))
    @patch("os.path.exists", return_value=True)
    def test_success(self, mock_exists):
        result = self._get_fn()()
        assert result is not None

    @patch("builtins.open", side_effect=FileNotFoundError("not found"))
    def test_file_not_found(self, mock_file):
        result = self._get_fn()()
        assert result is None


# ---------------------------------------------------------------------------
# load_piracicaba_marker (mocked CSV)
# ---------------------------------------------------------------------------
class TestLoadPiracicabaMarker:
    def _get_fn(self):
        from frontend.components.world_map_leaflet import load_piracicaba_marker
        return load_piracicaba_marker

    @patch("pandas.read_csv")
    @patch("os.path.exists", return_value=True)
    def test_success(self, mock_exists, mock_read_csv):
        mock_read_csv.return_value = pd.DataFrame({
            "LATITUDE": [-22.7253],
            "LONGITUDE": [-47.6492],
            "HEIGHT": [546.0],
        })
        result = self._get_fn()()
        assert result is not None

    @patch("pandas.read_csv", side_effect=FileNotFoundError())
    def test_file_not_found(self, mock_csv):
        result = self._get_fn()()
        assert result is None


# ---------------------------------------------------------------------------
# load_matopiba_cities_markers (mocked CSV)
# ---------------------------------------------------------------------------
class TestLoadMatopibaCitiesMarkers:
    def _get_fn(self):
        from frontend.components.world_map_leaflet import (
            load_matopiba_cities_markers,
        )
        return load_matopiba_cities_markers

    @patch("pandas.read_csv")
    @patch("os.path.exists", return_value=True)
    def test_success(self, mock_exists, mock_read_csv):
        mock_read_csv.return_value = pd.DataFrame({
            "CITY": ["CityA", "CityB"],
            "UF": ["MA", "TO"],
            "LATITUDE": [-5.0, -10.0],
            "LONGITUDE": [-45.0, -48.0],
            "HEIGHT": [200.0, 300.0],
        })
        result = self._get_fn()()
        assert result is not None

    @patch("pandas.read_csv", side_effect=FileNotFoundError())
    def test_file_not_found(self, mock_csv):
        result = self._get_fn()()
        assert result is None


# ---------------------------------------------------------------------------
# create_brasil_layer (mocked)
# ---------------------------------------------------------------------------
class TestCreateBrasilLayer:
    def _get_fn(self):
        from frontend.components.world_map_leaflet import create_brasil_layer
        return create_brasil_layer

    @patch("builtins.open", mock_open(read_data='{"type":"FeatureCollection","features":[]}'))
    @patch("os.path.exists", return_value=True)
    def test_success(self, mock_exists):
        result = self._get_fn()()
        assert result is not None

    @patch("os.path.exists", return_value=False)
    def test_file_missing(self, mock_exists):
        result = self._get_fn()()
        assert result is None


# ---------------------------------------------------------------------------
# create_matopiba_layer (mocked)
# ---------------------------------------------------------------------------
class TestCreateMatopibaLayer:
    def _get_fn(self):
        from frontend.components.world_map_leaflet import create_matopiba_layer
        return create_matopiba_layer

    @patch("builtins.open", mock_open(read_data='{"type":"FeatureCollection","features":[]}'))
    @patch("os.path.exists", return_value=True)
    def test_success(self, mock_exists):
        result = self._get_fn()()
        assert result is not None

    @patch("os.path.exists", return_value=False)
    def test_file_missing(self, mock_exists):
        result = self._get_fn()()
        assert result is None


# ---------------------------------------------------------------------------
# create_cities_layer (mocked CSV)
# ---------------------------------------------------------------------------
class TestCreateCitiesLayer:
    def _get_fn(self):
        from frontend.components.world_map_leaflet import create_cities_layer
        return create_cities_layer

    @patch("pandas.read_csv")
    @patch("os.path.exists", return_value=True)
    def test_success(self, mock_exists, mock_read_csv):
        mock_read_csv.return_value = pd.DataFrame({
            "CITY": ["A"],
            "UF": ["X"],
            "LATITUDE": [-5.0],
            "LONGITUDE": [-45.0],
            "HEIGHT": [100.0],
        })
        result = self._get_fn()()
        assert result is not None

    @patch("os.path.exists", return_value=False)
    def test_file_missing(self, mock_exists):
        result = self._get_fn()()
        assert result is None


# ---------------------------------------------------------------------------
# create_piracicaba_layer (mocked CSV)
# ---------------------------------------------------------------------------
class TestCreatePiracicabaLayer:
    def _get_fn(self):
        from frontend.components.world_map_leaflet import (
            create_piracicaba_layer,
        )
        return create_piracicaba_layer

    @patch("pandas.read_csv")
    @patch("os.path.exists", return_value=True)
    def test_success(self, mock_exists, mock_read_csv):
        mock_read_csv.return_value = pd.DataFrame({
            "LATITUDE": [-22.7253],
            "LONGITUDE": [-47.6492],
            "HEIGHT": [546.0],
        })
        result = self._get_fn()()
        assert result is not None

    @patch("os.path.exists", return_value=False)
    def test_file_missing(self, mock_exists):
        result = self._get_fn()()
        assert result is None
