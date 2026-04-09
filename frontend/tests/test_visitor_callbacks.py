"""
Tests for frontend/callbacks/visitor_callbacks.py.

All three callbacks call external HTTP endpoints, so we mock requests.
"""

from unittest.mock import MagicMock, patch

from dash import no_update


# ---------------------------------------------------------------------------
# update_visitor_counter (Callback 1)
# ---------------------------------------------------------------------------
class TestUpdateVisitorCounter:
    """Tests for the periodic visitor stats polling callback."""

    def _get_fn(self):
        from frontend.callbacks.visitor_callbacks import update_visitor_counter
        return update_visitor_counter

    @patch("frontend.callbacks.visitor_callbacks.requests")
    def test_successful_response(self, mock_requests):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "total_visitors": 1234,
            "current_hour_visitors": 56,
        }
        mock_requests.get.return_value = mock_resp

        total, hourly = self._get_fn()(1)
        assert total == "1,234"
        assert hourly == "56"

    @patch("frontend.callbacks.visitor_callbacks.requests")
    def test_non_200_response(self, mock_requests):
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_requests.get.return_value = mock_resp

        total, hourly = self._get_fn()(1)
        assert total is no_update
        assert hourly is no_update

    @patch("frontend.callbacks.visitor_callbacks.requests")
    def test_timeout_exception(self, mock_requests):
        import requests as real_requests
        mock_requests.exceptions = real_requests.exceptions
        mock_requests.get.side_effect = real_requests.exceptions.Timeout()

        total, hourly = self._get_fn()(1)
        assert total is no_update
        assert hourly is no_update

    @patch("frontend.callbacks.visitor_callbacks.requests")
    def test_connection_error(self, mock_requests):
        import requests as real_requests
        mock_requests.exceptions = real_requests.exceptions
        mock_requests.get.side_effect = real_requests.exceptions.ConnectionError()

        total, hourly = self._get_fn()(0)
        assert total == "offline"
        assert hourly == "offline"

    @patch("frontend.callbacks.visitor_callbacks.requests")
    def test_generic_exception(self, mock_requests):
        import requests as real_requests
        mock_requests.exceptions = real_requests.exceptions
        mock_requests.get.side_effect = ValueError("unexpected")

        total, hourly = self._get_fn()(1)
        assert total is no_update
        assert hourly is no_update

    @patch("frontend.callbacks.visitor_callbacks.requests")
    def test_logging_at_interval_30(self, mock_requests):
        """Every 30th interval should log stats."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "total_visitors": 100,
            "current_hour_visitors": 5,
        }
        mock_requests.get.return_value = mock_resp

        total, hourly = self._get_fn()(30)
        assert total == "100"
        assert hourly == "5"


# ---------------------------------------------------------------------------
# increment_visitor_on_session_start (Callback 2)
# ---------------------------------------------------------------------------
class TestIncrementVisitor:
    """Tests for the one-time visitor increment callback."""

    def _get_fn(self):
        from frontend.callbacks.visitor_callbacks import (
            increment_visitor_on_session_start,
        )
        return increment_visitor_on_session_start

    @patch("frontend.callbacks.visitor_callbacks.requests")
    def test_already_incremented(self, mock_requests):
        result = self._get_fn()("session-123", True)
        assert result is no_update
        mock_requests.post.assert_not_called()

    @patch("frontend.callbacks.visitor_callbacks.requests")
    def test_no_session_id(self, mock_requests):
        result = self._get_fn()(None, False)
        assert result is no_update

    @patch("frontend.callbacks.visitor_callbacks.requests")
    def test_successful_new_visitor(self, mock_requests):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "is_new_visitor": True,
            "total_visitors": 100,
        }
        mock_requests.post.return_value = mock_resp

        result = self._get_fn()("session-abc123", False)
        assert result is True

    @patch("frontend.callbacks.visitor_callbacks.requests")
    def test_successful_returning_visitor(self, mock_requests):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "is_new_visitor": False,
            "total_visitors": 100,
        }
        mock_requests.post.return_value = mock_resp

        result = self._get_fn()("session-abc123", False)
        assert result is True

    @patch("frontend.callbacks.visitor_callbacks.requests")
    def test_api_failure(self, mock_requests):
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_requests.post.return_value = mock_resp

        result = self._get_fn()("session-abc123", False)
        assert result is True  # Still marks as incremented

    @patch("frontend.callbacks.visitor_callbacks.requests")
    def test_connection_error(self, mock_requests):
        import requests as real_requests
        mock_requests.exceptions = real_requests.exceptions
        mock_requests.post.side_effect = real_requests.exceptions.ConnectionError()

        result = self._get_fn()("session-abc123", False)
        assert result is True


# ---------------------------------------------------------------------------
# translate_visitor_labels (Callback 3) — test module-level API_BASE_URL
# ---------------------------------------------------------------------------
class TestVisitorCallbacksConfig:
    """Test module-level configuration."""

    def test_api_base_url_defined(self):
        from frontend.callbacks.visitor_callbacks import API_BASE_URL
        assert isinstance(API_BASE_URL, str)
        assert "localhost" in API_BASE_URL or "127.0.0.1" in API_BASE_URL


# ---------------------------------------------------------------------------
# translate_visitor_labels (Callback 3)
# ---------------------------------------------------------------------------
class TestTranslateVisitorLabels:
    """Tests for footer/visitor label translation callback."""

    def _get_fn(self):
        from frontend.callbacks.visitor_callbacks import translate_visitor_labels
        return translate_visitor_labels

    @patch("frontend.callbacks.visitor_callbacks.t")
    def test_english_labels(self, mock_t):
        mock_t.side_effect = lambda lang, section, key, default="": default
        result = self._get_fn()("en")
        assert len(result) == 8
        assert result[0] == "Visitors: "
        assert result[1] == " | Last hour: "
        assert result[2] == "License"
        assert result[3] == "Documentation"

    @patch("frontend.callbacks.visitor_callbacks.t")
    def test_portuguese_labels(self, mock_t):
        translations = {
            "visitors": "Visitantes",
            "last_hour": "Última hora",
            "license": "Licença",
            "documentation": "Documentação",
            "copyright": ". Código aberto sob licença ",
            "developers": "Desenvolvedores",
            "partners": "Parceiros",
            "links": "Links Importantes",
        }
        mock_t.side_effect = lambda lang, section, key, default="": translations.get(key, default)
        result = self._get_fn()("pt")
        assert result[0] == "Visitantes: "
        assert result[5] == "Desenvolvedores"
        assert result[7] == "Links Importantes"

    @patch("frontend.callbacks.visitor_callbacks.t")
    def test_none_lang_defaults_to_en(self, mock_t):
        """When lang is None/falsy, should default to 'en'."""
        mock_t.side_effect = lambda lang, section, key, default="": default
        result = self._get_fn()(None)
        # The function defaults lang to "en" and then calls t
        assert len(result) == 8
        mock_t.assert_called()
        # Check the first call used "en"
        first_call_lang = mock_t.call_args_list[0][0][0]
        assert first_call_lang == "en"

    @patch("frontend.callbacks.visitor_callbacks.t")
    def test_empty_string_lang_defaults_to_en(self, mock_t):
        mock_t.side_effect = lambda lang, section, key, default="": default
        self._get_fn()("")
        first_call_lang = mock_t.call_args_list[0][0][0]
        assert first_call_lang == "en"

    @patch("frontend.callbacks.visitor_callbacks.t")
    def test_all_return_values_are_strings(self, mock_t):
        mock_t.side_effect = lambda lang, section, key, default="": default
        result = self._get_fn()("en")
        for item in result:
            assert isinstance(item, str)
