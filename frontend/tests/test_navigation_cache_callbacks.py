"""Tests for frontend/callbacks/navigation_callbacks.py and cache_callbacks.py."""

from unittest.mock import MagicMock


class TestNavigationCallbacks:
    """Test inner callbacks by registering on a mock app."""

    def _register(self):
        mock_app = MagicMock()
        callbacks = {}

        def capture_callback(*args, **kwargs):
            def decorator(fn):
                callbacks[fn.__name__] = fn
                return fn
            return decorator

        mock_app.callback = capture_callback
        mock_app.clientside_callback = MagicMock()

        from frontend.callbacks.navigation_callbacks import register_navigation_callbacks
        register_navigation_callbacks(mock_app)
        return callbacks

    def test_display_page_home(self):
        callbacks = self._register()
        fn = callbacks["display_page"]
        result = fn("/", "en")
        assert result is not None

    def test_display_page_documentation(self):
        callbacks = self._register()
        fn = callbacks["display_page"]
        result = fn("/documentation", "en")
        assert result is not None

    def test_display_page_about(self):
        callbacks = self._register()
        fn = callbacks["display_page"]
        result = fn("/about", "en")
        assert result is not None

    def test_display_page_architecture(self):
        callbacks = self._register()
        fn = callbacks["display_page"]
        result = fn("/architecture", "en")
        assert result is not None

    def test_display_page_architecture_pt(self):
        callbacks = self._register()
        fn = callbacks["display_page"]
        result = fn("/architecture", "pt")
        assert result is not None

    def test_display_page_none_lang(self):
        callbacks = self._register()
        fn = callbacks["display_page"]
        result = fn("/", None)
        assert result is not None

    def test_display_page_unknown_route(self):
        """Unknown routes should default to home."""
        callbacks = self._register()
        fn = callbacks["display_page"]
        result = fn("/unknown", "en")
        assert result is not None

    def test_toggle_navbar_open(self):
        callbacks = self._register()
        fn = callbacks["toggle_navbar"]
        assert fn(1, False) is True

    def test_toggle_navbar_close(self):
        callbacks = self._register()
        fn = callbacks["toggle_navbar"]
        assert fn(1, True) is False

    def test_toggle_navbar_no_clicks(self):
        callbacks = self._register()
        fn = callbacks["toggle_navbar"]
        assert fn(None, False) is False


class TestCacheCallbacks:
    """Test cache_callbacks.py inner callbacks."""

    def _register(self):
        mock_app = MagicMock()
        callbacks = {}

        def capture_callback(*args, **kwargs):
            def decorator(fn):
                callbacks[fn.__name__] = fn
                return fn
            return decorator

        mock_app.callback = capture_callback

        from frontend.callbacks.cache_callbacks import register_cache_callbacks
        register_cache_callbacks(mock_app)
        return callbacks

    def test_initialize_new_session(self):
        callbacks = self._register()
        fn = callbacks["initialize_session_id"]
        result = fn("/", None)
        assert result.startswith("sess_")
        assert len(result) > 10

    def test_keep_existing_session(self):
        callbacks = self._register()
        fn = callbacks["initialize_session_id"]
        result = fn("/", "sess_existing123")
        assert result == "sess_existing123"

    def test_session_uniqueness(self):
        callbacks = self._register()
        fn = callbacks["initialize_session_id"]
        s1 = fn("/", None)
        s2 = fn("/", None)
        assert s1 != s2
