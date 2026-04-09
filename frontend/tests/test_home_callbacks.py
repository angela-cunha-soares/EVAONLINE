"""
Tests for frontend/callbacks/home_callbacks.py — standalone functions.

Focus on:
- get_location_info (with mocked Nominatim)
- create_selection_info_card
"""

from unittest.mock import MagicMock, patch



# ---------------------------------------------------------------------------
# get_location_info
# ---------------------------------------------------------------------------
class TestGetLocationInfo:
    """Tests for the reverse-geocoding helper `get_location_info`."""

    def _get_fn(self):
        from frontend.callbacks.home_callbacks import get_location_info
        return get_location_info

    @patch("frontend.callbacks.home_callbacks.geolocator")
    @patch("frontend.callbacks.home_callbacks.get_timezone_for_location")
    def test_valid_location(self, mock_tz, mock_geo):
        mock_tz.return_value = "America/Sao_Paulo"
        mock_location = MagicMock()
        mock_location.raw = {
            "address": {
                "city": "Piracicaba",
                "country": "Brasil",
                "state": "São Paulo",
            }
        }
        mock_location.address = "Piracicaba, SP, Brasil"
        mock_geo.reverse.return_value = mock_location

        result = self._get_fn()(-22.725, -47.649)
        assert result["city"] == "Piracicaba"
        assert result["country"] == "Brasil"
        assert result["state"] == "São Paulo"
        assert result["timezone"] == "America/Sao_Paulo"

    @patch("frontend.callbacks.home_callbacks.geolocator")
    @patch("frontend.callbacks.home_callbacks.get_timezone_for_location")
    def test_no_geocoding_result(self, mock_tz, mock_geo):
        mock_tz.return_value = "UTC"
        mock_geo.reverse.return_value = None

        result = self._get_fn()(0.0, 0.0)
        assert result["city"] == "Local desconhecido"
        assert result["timezone"] == "UTC"

    @patch("frontend.callbacks.home_callbacks.geolocator")
    @patch("frontend.callbacks.home_callbacks.get_timezone_for_location")
    def test_geocoder_exception(self, mock_tz, mock_geo):
        mock_tz.return_value = "UTC"
        mock_geo.reverse.side_effect = Exception("timeout")

        result = self._get_fn()(10.0, 20.0)
        assert result["city"] == "Erro ao obter localização"
        assert "timezone" in result

    @patch("frontend.callbacks.home_callbacks.geolocator")
    @patch("frontend.callbacks.home_callbacks.get_timezone_for_location")
    def test_town_fallback(self, mock_tz, mock_geo):
        """When 'city' is missing, should fall back to 'town'."""
        mock_tz.return_value = "Europe/London"
        mock_location = MagicMock()
        mock_location.raw = {"address": {"town": "Smallville", "country": "UK"}}
        mock_location.address = "Smallville, UK"
        mock_geo.reverse.return_value = mock_location

        result = self._get_fn()(51.5, -0.1)
        assert result["city"] == "Smallville"

    @patch("frontend.callbacks.home_callbacks.geolocator")
    @patch("frontend.callbacks.home_callbacks.get_timezone_for_location")
    def test_village_fallback(self, mock_tz, mock_geo):
        mock_tz.return_value = "Asia/Tokyo"
        mock_location = MagicMock()
        mock_location.raw = {"address": {"village": "Takayama", "country": "Japan"}}
        mock_location.address = "Takayama, Japan"
        mock_geo.reverse.return_value = mock_location

        result = self._get_fn()(36.1, 137.2)
        assert result["city"] == "Takayama"

    @patch("frontend.callbacks.home_callbacks.geolocator")
    @patch("frontend.callbacks.home_callbacks.get_timezone_for_location")
    def test_municipality_fallback(self, mock_tz, mock_geo):
        mock_tz.return_value = "America/Sao_Paulo"
        mock_location = MagicMock()
        mock_location.raw = {"address": {"municipality": "Campinas", "country": "Brasil"}}
        mock_location.address = "Campinas, SP, Brasil"
        mock_geo.reverse.return_value = mock_location

        result = self._get_fn()(-22.9, -47.06)
        assert result["city"] == "Campinas"

    @patch("frontend.callbacks.home_callbacks.geolocator")
    @patch("frontend.callbacks.home_callbacks.get_timezone_for_location")
    def test_no_city_fields_returns_unknown(self, mock_tz, mock_geo):
        mock_tz.return_value = "UTC"
        mock_location = MagicMock()
        mock_location.raw = {"address": {"country": "Ocean"}}
        mock_location.address = "Ocean"
        mock_geo.reverse.return_value = mock_location

        result = self._get_fn()(0.0, 0.0)
        assert result["city"] == "Local desconhecido"

    @patch("frontend.callbacks.home_callbacks.geolocator")
    @patch("frontend.callbacks.home_callbacks.get_timezone_for_location")
    def test_timezone_exception_fallback(self, mock_tz, mock_geo):
        """If timezone detection fails, should fallback to UTC."""
        mock_tz.side_effect = Exception("tz error")
        mock_location = MagicMock()
        mock_location.raw = {"address": {"city": "Test", "country": "Test"}}
        mock_location.address = "Test"
        mock_geo.reverse.return_value = mock_location

        result = self._get_fn()(10.0, 20.0)
        assert result["timezone"] == "UTC"


# ---------------------------------------------------------------------------
# create_selection_info_card
# ---------------------------------------------------------------------------
class TestCreateSelectionInfoCard:
    """Tests for create_selection_info_card."""

    def _get_fn(self):
        from frontend.callbacks.home_callbacks import create_selection_info_card
        return create_selection_info_card

    def test_returns_card(self):
        import dash_bootstrap_components as dbc
        card = self._get_fn()({"lat": -23.55, "lon": -46.63})
        assert isinstance(card, dbc.Card)

    def test_default_zero_coords(self):
        card = self._get_fn()({})
        # Should work with missing keys (defaults to 0)
        assert card is not None

    def test_card_with_positive_coords(self):
        card = self._get_fn()({"lat": 45.0, "lon": 90.0})
        assert card is not None


# ---------------------------------------------------------------------------
# register_home_callbacks inner functions
# ---------------------------------------------------------------------------
class TestRegisterHomeCallbacks:
    """Test inner callbacks by registering on a mock app."""

    def _register(self):
        """Register callbacks on a mock app and return captured functions."""
        from unittest.mock import MagicMock
        mock_app = MagicMock()
        callbacks = {}

        def capture_callback(*args, **kwargs):
            def decorator(fn):
                callbacks[fn.__name__] = fn
                return fn
            return decorator

        mock_app.callback = capture_callback
        mock_app.clientside_callback = MagicMock()

        from frontend.callbacks.home_callbacks import register_home_callbacks
        register_home_callbacks(mock_app)
        return callbacks

    @patch("frontend.callbacks.home_callbacks.requests")
    def test_update_api_status_success(self, mock_requests):
        """Test API status callback with successful response."""
        callbacks = self._register()
        fn = callbacks["update_api_status"]

        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "service": "EVAonline",
            "version": "1.0.0",
            "status": "ok",
        }
        mock_requests.get.return_value = mock_resp

        result = fn(1)
        assert isinstance(result, list)

    @patch("frontend.callbacks.home_callbacks.requests")
    def test_update_api_status_connection_error(self, mock_requests):
        """Test API status callback with connection failure."""
        import requests as real_requests
        callbacks = self._register()
        fn = callbacks["update_api_status"]

        mock_requests.get.side_effect = real_requests.exceptions.ConnectionError("refused")
        mock_requests.exceptions = real_requests.exceptions

        result = fn(1)
        # Should return an error alert
        assert result is not None

    @patch("frontend.callbacks.home_callbacks.requests")
    def test_update_api_status_unexpected_error(self, mock_requests):
        """Test API status callback with unexpected exception."""
        callbacks = self._register()
        fn = callbacks["update_api_status"]

        mock_requests.get.side_effect = Exception("unexpected")
        mock_requests.exceptions = MagicMock()
        mock_requests.exceptions.RequestException = type("FakeReqExc", (Exception,), {})

        result = fn(1)
        assert result is not None

    @patch("frontend.callbacks.home_callbacks.requests")
    def test_update_services_status_success(self, mock_requests):
        """Test services status callback with successful response."""
        callbacks = self._register()
        fn = callbacks["update_services_status"]

        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "services": {
                "redis": {"name": "Redis", "status": "healthy", "available": True},
                "celery": {"name": "Celery", "status": "healthy", "available": True},
            },
            "total_services": 2,
            "healthy_count": 2,
        }
        mock_requests.get.return_value = mock_resp

        result = fn(1)
        assert isinstance(result, list)
        assert len(result) >= 2  # summary + service cards

    @patch("frontend.callbacks.home_callbacks.requests")
    def test_update_services_status_error(self, mock_requests):
        """Test services status callback with connection failure."""
        import requests as real_requests
        callbacks = self._register()
        fn = callbacks["update_services_status"]

        mock_requests.get.side_effect = real_requests.exceptions.ConnectionError("refused")
        mock_requests.exceptions = real_requests.exceptions

        result = fn(1)
        assert result is not None

    def test_handle_map_click_none(self):
        """Click data is None → returns defaults."""
        callbacks = self._register()
        fn = callbacks["handle_map_click"]

        result = fn(None, "en")
        assert result[0] is None  # map-click-data
        assert result[5] is True  # button disabled

    def test_handle_map_click_empty(self):
        """Click data is empty dict → returns defaults."""
        callbacks = self._register()
        fn = callbacks["handle_map_click"]

        result = fn({}, "en")
        assert result[0] is None

    def test_handle_map_click_valid_list(self):
        """Valid click with latlng as list."""
        callbacks = self._register()
        fn = callbacks["handle_map_click"]

        click_data = {"latlng": [-23.55, -46.63]}
        result = fn(click_data, "en")
        assert result[0] == {"lat": -23.55, "lon": -46.63}
        assert result[5] is True  # disabled - wait for data_type

    def test_handle_map_click_valid_dict(self):
        """Valid click with latlng as dict."""
        callbacks = self._register()
        fn = callbacks["handle_map_click"]

        click_data = {"latlng": {"lat": 40.0, "lng": -100.0}}
        result = fn(click_data, "en")
        assert result[0] == {"lat": 40.0, "lon": -100.0}

    def test_handle_map_click_missing_latlng(self):
        """Click data without latlng key."""
        callbacks = self._register()
        fn = callbacks["handle_map_click"]

        result = fn({"other": "data"}, "en")
        assert result[0] is None  # error

    def test_handle_map_click_malformed_latlng(self):
        """Click data with invalid latlng format."""
        callbacks = self._register()
        fn = callbacks["handle_map_click"]

        result = fn({"latlng": "invalid"}, "en")
        assert result[0] is None

    def test_translate_sidebar_en(self):
        """Translate sidebar to English."""
        callbacks = self._register()
        fn = callbacks["translate_sidebar"]

        result = fn("en", None)
        assert isinstance(result, tuple)
        assert len(result) == 13

    def test_translate_sidebar_pt(self):
        """Translate sidebar to Portuguese."""
        callbacks = self._register()
        fn = callbacks["translate_sidebar"]

        result = fn("pt", None)
        assert isinstance(result, tuple)

    def test_translate_sidebar_with_location(self):
        """Translate sidebar when location is already selected."""
        from dash import no_update
        callbacks = self._register()
        fn = callbacks["translate_sidebar"]

        result = fn("en", {"lat": -23.55, "lon": -46.63})
        # sidebar_location_display should be no_update
        assert result[12] is no_update

    def test_translate_layer_control_en(self):
        """Translate layer control to English."""
        callbacks = self._register()
        fn = callbacks["translate_layer_control"]

        result = fn("en")
        assert isinstance(result, tuple)
        assert len(result) == 6

    def test_translate_layer_control_pt(self):
        """Translate layer control to Portuguese."""
        callbacks = self._register()
        fn = callbacks["translate_layer_control"]

        result = fn("pt")
        assert isinstance(result, tuple)

    def test_translate_layer_control_none_lang(self):
        """None language defaults to English."""
        callbacks = self._register()
        fn = callbacks["translate_layer_control"]

        result = fn(None)
        assert isinstance(result, tuple)
