"""
Tests for frontend/callbacks/home_callbacks.py — register_layer_control_callbacks.

Tests the inner callbacks that control map layers, sidebar, manual coords, etc.
"""

from unittest.mock import MagicMock, patch
import pytest
from dash.exceptions import PreventUpdate


class TestRegisterLayerControlCallbacks:
    """Test inner callbacks from register_layer_control_callbacks."""

    def _register(self):
        """Register callbacks on a mock app and return captured functions."""
        mock_app = MagicMock()
        callbacks = {}

        def capture_callback(*args, **kwargs):
            def decorator(fn):
                callbacks[fn.__name__] = fn
                return fn
            return decorator

        mock_app.callback = capture_callback
        mock_app.clientside_callback = MagicMock()

        from frontend.callbacks.home_callbacks import register_layer_control_callbacks
        register_layer_control_callbacks(mock_app)
        return callbacks

    # -------------------------------------------------------------------------
    # toggle_layer_panel
    # -------------------------------------------------------------------------
    @patch("frontend.callbacks.home_callbacks.callback_context")
    def test_toggle_panel_no_trigger(self, mock_ctx):
        callbacks = self._register()
        fn = callbacks["toggle_layer_panel"]
        mock_ctx.triggered = []
        style = {"display": "none"}
        result = fn(0, 0, style)
        assert result == style

    @patch("frontend.callbacks.home_callbacks.callback_context")
    def test_toggle_panel_open(self, mock_ctx):
        callbacks = self._register()
        fn = callbacks["toggle_layer_panel"]
        mock_ctx.triggered = [{"prop_id": "layer-control-toggle.n_clicks"}]
        style = {"display": "none"}
        result = fn(1, 0, style)
        assert result["display"] == "block"

    @patch("frontend.callbacks.home_callbacks.callback_context")
    def test_toggle_panel_close_toggle(self, mock_ctx):
        callbacks = self._register()
        fn = callbacks["toggle_layer_panel"]
        mock_ctx.triggered = [{"prop_id": "layer-control-toggle.n_clicks"}]
        style = {"display": "block"}
        result = fn(2, 0, style)
        assert result["display"] == "none"

    @patch("frontend.callbacks.home_callbacks.callback_context")
    def test_toggle_panel_close_button(self, mock_ctx):
        callbacks = self._register()
        fn = callbacks["toggle_layer_panel"]
        mock_ctx.triggered = [{"prop_id": "layer-control-close.n_clicks"}]
        style = {"display": "block"}
        result = fn(0, 1, style)
        assert result["display"] == "none"

    # -------------------------------------------------------------------------
    # toggle_brasil_layer
    # -------------------------------------------------------------------------
    @patch("frontend.components.world_map_leaflet.load_brasil_geojson")
    def test_brasil_layer_enabled(self, mock_load):
        mock_geojson = MagicMock()
        mock_load.return_value = mock_geojson
        callbacks = self._register()
        fn = callbacks["toggle_brasil_layer"]
        result = fn(["brasil"])
        assert result == [mock_geojson]

    @patch("frontend.components.world_map_leaflet.load_brasil_geojson")
    def test_brasil_layer_returns_none(self, mock_load):
        mock_load.return_value = None
        callbacks = self._register()
        fn = callbacks["toggle_brasil_layer"]
        result = fn(["brasil"])
        assert result == []

    def test_brasil_layer_disabled(self):
        callbacks = self._register()
        fn = callbacks["toggle_brasil_layer"]
        assert fn([]) == []
        assert fn(None) == []

    # -------------------------------------------------------------------------
    # toggle_matopiba_layer
    # -------------------------------------------------------------------------
    @patch("frontend.components.world_map_leaflet.load_matopiba_geojson")
    def test_matopiba_layer_enabled(self, mock_load):
        mock_geojson = MagicMock()
        mock_load.return_value = mock_geojson
        callbacks = self._register()
        fn = callbacks["toggle_matopiba_layer"]
        result = fn(["matopiba"])
        assert result == [mock_geojson]

    @patch("frontend.components.world_map_leaflet.load_matopiba_geojson")
    def test_matopiba_layer_returns_none(self, mock_load):
        mock_load.return_value = None
        callbacks = self._register()
        fn = callbacks["toggle_matopiba_layer"]
        result = fn(["matopiba"])
        assert result == []

    def test_matopiba_layer_disabled(self):
        callbacks = self._register()
        fn = callbacks["toggle_matopiba_layer"]
        assert fn([]) == []

    # -------------------------------------------------------------------------
    # toggle_cities_layer
    # -------------------------------------------------------------------------
    @patch("frontend.components.world_map_leaflet.load_matopiba_cities_markers")
    def test_cities_layer_enabled(self, mock_load):
        markers = [MagicMock(), MagicMock()]
        mock_load.return_value = markers
        callbacks = self._register()
        fn = callbacks["toggle_cities_layer"]
        result = fn(["cities"])
        assert result == markers

    @patch("frontend.components.world_map_leaflet.load_matopiba_cities_markers")
    def test_cities_layer_empty(self, mock_load):
        mock_load.return_value = []
        callbacks = self._register()
        fn = callbacks["toggle_cities_layer"]
        result = fn(["cities"])
        assert result == []

    def test_cities_layer_disabled(self):
        callbacks = self._register()
        fn = callbacks["toggle_cities_layer"]
        assert fn([]) == []

    # -------------------------------------------------------------------------
    # toggle_piracicaba_layer
    # -------------------------------------------------------------------------
    @patch("frontend.components.world_map_leaflet.load_piracicaba_marker")
    def test_piracicaba_layer_enabled(self, mock_load):
        mock_marker = MagicMock()
        mock_load.return_value = mock_marker
        callbacks = self._register()
        fn = callbacks["toggle_piracicaba_layer"]
        result = fn(["piracicaba"])
        assert result == [mock_marker]

    @patch("frontend.components.world_map_leaflet.load_piracicaba_marker")
    def test_piracicaba_layer_returns_none(self, mock_load):
        mock_load.return_value = None
        callbacks = self._register()
        fn = callbacks["toggle_piracicaba_layer"]
        result = fn(["piracicaba"])
        assert result == []

    def test_piracicaba_layer_disabled(self):
        callbacks = self._register()
        fn = callbacks["toggle_piracicaba_layer"]
        assert fn([]) == []

    # -------------------------------------------------------------------------
    # sync_coords_for_calculation
    # -------------------------------------------------------------------------
    def test_sync_coords_valid(self):
        callbacks = self._register()
        fn = callbacks["sync_coords_for_calculation"]
        result = fn(1, {"lat": -23.5, "lon": -46.6})
        assert result == {"lat": -23.5, "lon": -46.6}

    def test_sync_coords_no_clicks(self):
        callbacks = self._register()
        fn = callbacks["sync_coords_for_calculation"]
        with pytest.raises(PreventUpdate):
            fn(None, {"lat": -23.5, "lon": -46.6})

    def test_sync_coords_no_location(self):
        callbacks = self._register()
        fn = callbacks["sync_coords_for_calculation"]
        with pytest.raises(PreventUpdate):
            fn(1, None)

    def test_sync_coords_missing_lat_lon(self):
        callbacks = self._register()
        fn = callbacks["sync_coords_for_calculation"]
        with pytest.raises(PreventUpdate):
            fn(1, {"lat": None, "lon": None})

    # -------------------------------------------------------------------------
    # toggle_sidebar
    # -------------------------------------------------------------------------
    def test_sidebar_open(self):
        callbacks = self._register()
        fn = callbacks["toggle_sidebar"]
        is_open, style, state = fn(1, False)
        assert is_open is True
        assert state is True
        assert style["marginLeft"] == "320px"

    def test_sidebar_close(self):
        callbacks = self._register()
        fn = callbacks["toggle_sidebar"]
        is_open, style, state = fn(2, True)
        assert is_open is False
        assert style["marginLeft"] == "0px"

    def test_sidebar_no_clicks(self):
        callbacks = self._register()
        fn = callbacks["toggle_sidebar"]
        with pytest.raises(PreventUpdate):
            fn(None, False)

    def test_sidebar_none_state(self):
        callbacks = self._register()
        fn = callbacks["toggle_sidebar"]
        is_open, style, state = fn(1, None)
        assert is_open is False

    # -------------------------------------------------------------------------
    # toggle_manual_input
    # -------------------------------------------------------------------------
    def test_manual_input_toggle_open(self):
        callbacks = self._register()
        fn = callbacks["toggle_manual_input"]
        assert fn(1, False) is True

    def test_manual_input_toggle_close(self):
        callbacks = self._register()
        fn = callbacks["toggle_manual_input"]
        assert fn(2, True) is False

    def test_manual_input_no_clicks(self):
        callbacks = self._register()
        fn = callbacks["toggle_manual_input"]
        with pytest.raises(PreventUpdate):
            fn(None, False)

    # -------------------------------------------------------------------------
    # populate_manual_fields
    # -------------------------------------------------------------------------
    def test_populate_fields_valid(self):
        callbacks = self._register()
        fn = callbacks["populate_manual_fields"]
        lat, lon, alt = fn({"lat": -22.72537, "lon": -47.64917})
        assert lat == -22.7254
        assert lon == -47.6492
        assert alt is None

    def test_populate_fields_no_data(self):
        callbacks = self._register()
        fn = callbacks["populate_manual_fields"]
        with pytest.raises(PreventUpdate):
            fn(None)

    def test_populate_fields_missing_coords(self):
        callbacks = self._register()
        fn = callbacks["populate_manual_fields"]
        with pytest.raises(PreventUpdate):
            fn({"lat": None, "lon": -47.0})

    # -------------------------------------------------------------------------
    # apply_manual_coords
    # -------------------------------------------------------------------------
    @patch("frontend.callbacks.home_callbacks.create_map_marker")
    def test_apply_manual_coords_valid(self, mock_marker):
        callbacks = self._register()
        fn = callbacks["apply_manual_coords"]
        mock_marker.return_value = MagicMock()

        result = fn(1, -23.5, -46.6, 800)
        # Returns 8-tuple
        assert len(result) == 8
        # map-click-data = location_data dict
        assert result[0] == {"lat": -23.5, "lon": -46.6}
        # selected-location-data
        assert result[1] == {"lat": -23.5, "lon": -46.6}
        # calculate-eto-btn disabled = True (waiting for data_type)
        assert result[5] is True
        # manual-elevation
        assert result[7] == 800

    def test_apply_manual_coords_no_clicks(self):
        callbacks = self._register()
        fn = callbacks["apply_manual_coords"]
        with pytest.raises(PreventUpdate):
            fn(None, -23, -46, None)

    def test_apply_manual_coords_missing_lat(self):
        callbacks = self._register()
        fn = callbacks["apply_manual_coords"]
        with pytest.raises(PreventUpdate):
            fn(1, None, -46.0, None)

    def test_apply_manual_coords_invalid_range(self):
        callbacks = self._register()
        fn = callbacks["apply_manual_coords"]
        with pytest.raises(PreventUpdate):
            fn(1, 100, -46.0, None)  # lat > 90
