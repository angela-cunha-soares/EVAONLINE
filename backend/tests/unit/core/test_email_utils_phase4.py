"""
Phase 4 Tests: Email Utilities.

Tests email sending functions with mocked SMTP/Resend:
- validate_email (pure)
- send_email (mocked SMTP)
- send_email_with_attachment (mocked SMTP)
- send_html_email (routing logic)
- send_html_email_with_attachment (routing logic)
- _send_via_smtp (mocked SMTP)
- _send_via_resend (mocked resend API)
"""

import os
import sys
import tempfile
from unittest.mock import MagicMock, patch

import pytest


class TestValidateEmail:
    """Tests for validate_email pure function."""

    def test_valid_email(self):
        from backend.core.utils.email_utils import validate_email
        assert validate_email("user@example.com") is True

    def test_valid_email_with_dots(self):
        from backend.core.utils.email_utils import validate_email
        assert validate_email("first.last@example.com") is True

    def test_valid_email_with_plus(self):
        from backend.core.utils.email_utils import validate_email
        assert validate_email("user+tag@example.com") is True

    def test_valid_email_with_subdomain(self):
        from backend.core.utils.email_utils import validate_email
        assert validate_email("user@mail.example.com") is True

    def test_invalid_email_no_at(self):
        from backend.core.utils.email_utils import validate_email
        assert validate_email("invalid.email") is False

    def test_invalid_email_no_domain(self):
        from backend.core.utils.email_utils import validate_email
        assert validate_email("user@") is False

    def test_invalid_email_no_tld(self):
        from backend.core.utils.email_utils import validate_email
        assert validate_email("user@domain") is False

    def test_invalid_email_empty(self):
        from backend.core.utils.email_utils import validate_email
        assert validate_email("") is False

    def test_invalid_email_none(self):
        from backend.core.utils.email_utils import validate_email
        assert validate_email(None) is False

    def test_invalid_email_number(self):
        from backend.core.utils.email_utils import validate_email
        assert validate_email(123) is False

    def test_invalid_email_spaces(self):
        from backend.core.utils.email_utils import validate_email
        assert validate_email("user @example.com") is False


class TestSendEmail:
    """Tests for send_email with mocked SMTP."""

    def test_send_email_invalid_recipient(self):
        from backend.core.utils.email_utils import send_email
        result = send_email("invalid", "Subject", "Body")
        assert result is False

    @patch.dict(
        os.environ,
        {"SMTP_USER": "", "SMTP_PASSWORD": ""},
        clear=False,
    )
    def test_send_email_no_smtp_config_simulates(self):
        """When no SMTP config, email is simulated (returns True)."""
        # Need to reimport to pick up new env
        import importlib
        import backend.core.utils.email_utils as eu
        original_user = eu.SMTP_USER
        original_pw = eu.SMTP_PASSWORD
        eu.SMTP_USER = ""
        eu.SMTP_PASSWORD = ""
        try:
            result = eu.send_email("user@example.com", "Test", "Body")
            assert result is True
        finally:
            eu.SMTP_USER = original_user
            eu.SMTP_PASSWORD = original_pw

    @patch("backend.core.utils.email_utils.smtplib.SMTP")
    def test_send_email_success(self, mock_smtp):
        import backend.core.utils.email_utils as eu
        original_user = eu.SMTP_USER
        original_pw = eu.SMTP_PASSWORD
        eu.SMTP_USER = "test@gmail.com"
        eu.SMTP_PASSWORD = "testpassword"
        try:
            mock_server = MagicMock()
            mock_smtp.return_value.__enter__ = MagicMock(return_value=mock_server)
            mock_smtp.return_value.__exit__ = MagicMock(return_value=False)
            result = eu.send_email("user@example.com", "Test", "Body")
            assert result is True
        finally:
            eu.SMTP_USER = original_user
            eu.SMTP_PASSWORD = original_pw

    @patch("backend.core.utils.email_utils.smtplib.SMTP")
    def test_send_email_smtp_auth_error(self, mock_smtp):
        import smtplib
        import backend.core.utils.email_utils as eu
        original_user = eu.SMTP_USER
        original_pw = eu.SMTP_PASSWORD
        eu.SMTP_USER = "test@gmail.com"
        eu.SMTP_PASSWORD = "wrongpassword"
        try:
            mock_smtp.return_value.__enter__ = MagicMock(
                side_effect=smtplib.SMTPAuthenticationError(535, b"Auth failed")
            )
            mock_smtp.return_value.__exit__ = MagicMock(return_value=False)
            result = eu.send_email("user@example.com", "Test", "Body")
            assert result is False
        finally:
            eu.SMTP_USER = original_user
            eu.SMTP_PASSWORD = original_pw


class TestSendEmailWithAttachment:
    """Tests for send_email_with_attachment."""

    def test_send_with_attachment_invalid_email(self):
        from backend.core.utils.email_utils import send_email_with_attachment
        result = send_email_with_attachment("invalid", "Subject", "Body", "/tmp/f.csv")
        assert result is False

    def test_send_with_attachment_file_not_found(self):
        from backend.core.utils.email_utils import send_email_with_attachment
        with pytest.raises(FileNotFoundError):
            send_email_with_attachment(
                "user@example.com", "Subject", "Body", "/nonexistent/file.csv"
            )

    def test_send_with_attachment_no_smtp_simulates(self):
        import backend.core.utils.email_utils as eu
        original_user = eu.SMTP_USER
        original_pw = eu.SMTP_PASSWORD
        eu.SMTP_USER = ""
        eu.SMTP_PASSWORD = ""
        try:
            with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
                f.write(b"col1,col2\n1,2\n")
                tmp_path = f.name
            try:
                result = eu.send_email_with_attachment(
                    "user@example.com", "Test", "Body", tmp_path
                )
                assert result is True
            finally:
                os.unlink(tmp_path)
        finally:
            eu.SMTP_USER = original_user
            eu.SMTP_PASSWORD = original_pw

    @patch("backend.core.utils.email_utils.smtplib.SMTP")
    def test_send_with_attachment_success(self, mock_smtp):
        import backend.core.utils.email_utils as eu
        original_user = eu.SMTP_USER
        original_pw = eu.SMTP_PASSWORD
        eu.SMTP_USER = "test@gmail.com"
        eu.SMTP_PASSWORD = "testpassword"
        try:
            mock_server = MagicMock()
            mock_smtp.return_value.__enter__ = MagicMock(return_value=mock_server)
            mock_smtp.return_value.__exit__ = MagicMock(return_value=False)

            with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
                f.write(b"test data")
                tmp_path = f.name
            try:
                result = eu.send_email_with_attachment(
                    "user@example.com", "Test", "Body", tmp_path
                )
                assert result is True
            finally:
                os.unlink(tmp_path)
        finally:
            eu.SMTP_USER = original_user
            eu.SMTP_PASSWORD = original_pw


class TestSendViaSmtp:
    """Tests for _send_via_smtp."""

    def test_send_via_smtp_no_config_simulates(self):
        import backend.core.utils.email_utils as eu
        original_user = eu.SMTP_USER
        original_pw = eu.SMTP_PASSWORD
        eu.SMTP_USER = ""
        eu.SMTP_PASSWORD = ""
        try:
            result = eu._send_via_smtp("user@example.com", "Test", "<h1>Hi</h1>")
            assert result is True
        finally:
            eu.SMTP_USER = original_user
            eu.SMTP_PASSWORD = original_pw

    @patch("backend.core.utils.email_utils.smtplib.SMTP")
    def test_send_via_smtp_html_no_attachment(self, mock_smtp):
        import backend.core.utils.email_utils as eu
        original_user = eu.SMTP_USER
        original_pw = eu.SMTP_PASSWORD
        eu.SMTP_USER = "test@gmail.com"
        eu.SMTP_PASSWORD = "testpw"
        try:
            mock_server = MagicMock()
            mock_smtp.return_value.__enter__ = MagicMock(return_value=mock_server)
            mock_smtp.return_value.__exit__ = MagicMock(return_value=False)
            result = eu._send_via_smtp(
                "user@example.com", "Test", "<h1>Hello</h1>"
            )
            assert result is True
        finally:
            eu.SMTP_USER = original_user
            eu.SMTP_PASSWORD = original_pw

    @patch("backend.core.utils.email_utils.smtplib.SMTP")
    def test_send_via_smtp_with_attachment(self, mock_smtp):
        import backend.core.utils.email_utils as eu
        original_user = eu.SMTP_USER
        original_pw = eu.SMTP_PASSWORD
        eu.SMTP_USER = "test@gmail.com"
        eu.SMTP_PASSWORD = "testpw"
        try:
            mock_server = MagicMock()
            mock_smtp.return_value.__enter__ = MagicMock(return_value=mock_server)
            mock_smtp.return_value.__exit__ = MagicMock(return_value=False)

            with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
                f.write(b"data")
                tmp_path = f.name
            try:
                result = eu._send_via_smtp(
                    "user@example.com", "Test", "<h1>Hi</h1>", tmp_path
                )
                assert result is True
            finally:
                os.unlink(tmp_path)
        finally:
            eu.SMTP_USER = original_user
            eu.SMTP_PASSWORD = original_pw

    @patch("backend.core.utils.email_utils.smtplib.SMTP")
    def test_send_via_smtp_error(self, mock_smtp):
        import backend.core.utils.email_utils as eu
        original_user = eu.SMTP_USER
        original_pw = eu.SMTP_PASSWORD
        eu.SMTP_USER = "test@gmail.com"
        eu.SMTP_PASSWORD = "testpw"
        try:
            mock_smtp.return_value.__enter__ = MagicMock(
                side_effect=Exception("SMTP error")
            )
            mock_smtp.return_value.__exit__ = MagicMock(return_value=False)
            result = eu._send_via_smtp(
                "user@example.com", "Test", "<h1>Hi</h1>"
            )
            assert result is False
        finally:
            eu.SMTP_USER = original_user
            eu.SMTP_PASSWORD = original_pw


class TestSendViaResend:
    """Tests for _send_via_resend with mocked resend API."""

    @pytest.fixture(autouse=True)
    def mock_resend_module(self):
        """Inject a fake 'resend' module so _send_via_resend can import it."""
        import types
        fake_resend = types.ModuleType("resend")
        fake_resend.Emails = MagicMock()
        fake_resend.api_key = None
        sys.modules["resend"] = fake_resend
        self._fake_resend = fake_resend
        yield fake_resend
        sys.modules.pop("resend", None)

    @patch("backend.infrastructure.cache.api_usage_tracker.check_api_quota", return_value=False)
    def test_send_via_resend_quota_exceeded(self, mock_quota):
        import backend.core.utils.email_utils as eu
        original_key = eu.RESEND_API_KEY
        eu.RESEND_API_KEY = "re_test_key"
        try:
            result = eu._send_via_resend(
                "user@example.com", "Test", "<h1>Hi</h1>"
            )
            assert result is False
        finally:
            eu.RESEND_API_KEY = original_key

    @patch("backend.infrastructure.cache.api_usage_tracker.track_api_call")
    @patch("backend.infrastructure.cache.api_usage_tracker.check_api_quota", return_value=True)
    def test_send_via_resend_success(self, mock_quota, mock_track):
        import backend.core.utils.email_utils as eu
        original_key = eu.RESEND_API_KEY
        eu.RESEND_API_KEY = "re_test_key"
        try:
            self._fake_resend.Emails.send.return_value = {"id": "test-id-123"}
            result = eu._send_via_resend(
                "user@example.com", "Test", "<h1>Hello</h1>"
            )
            assert result is True
            mock_track.assert_called_once_with("resend")
        finally:
            eu.RESEND_API_KEY = original_key

    @patch("backend.infrastructure.cache.api_usage_tracker.track_api_call")
    @patch("backend.infrastructure.cache.api_usage_tracker.check_api_quota", return_value=True)
    def test_send_via_resend_with_attachment(self, mock_quota, mock_track):
        import backend.core.utils.email_utils as eu
        original_key = eu.RESEND_API_KEY
        eu.RESEND_API_KEY = "re_test_key"
        try:
            self._fake_resend.Emails.send.return_value = {"id": "test-id-456"}
            with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
                f.write(b"col1\nval1\n")
                tmp_path = f.name
            try:
                result = eu._send_via_resend(
                    "user@example.com", "Test", "<h1>Hi</h1>", tmp_path
                )
                assert result is True
            finally:
                os.unlink(tmp_path)
        finally:
            eu.RESEND_API_KEY = original_key

    @patch("backend.infrastructure.cache.api_usage_tracker.check_api_quota", return_value=True)
    def test_send_via_resend_file_not_found(self, mock_quota):
        import backend.core.utils.email_utils as eu
        original_key = eu.RESEND_API_KEY
        eu.RESEND_API_KEY = "re_test_key"
        try:
            result = eu._send_via_resend(
                "user@example.com", "Test", "<h1>Hi</h1>",
                "/nonexistent/file.csv"
            )
            # FileNotFoundError is caught internally → returns False
            assert result is False
        finally:
            eu.RESEND_API_KEY = original_key

    @patch("backend.infrastructure.cache.api_usage_tracker.check_api_quota", return_value=True)
    def test_send_via_resend_api_error(self, mock_quota):
        import backend.core.utils.email_utils as eu
        original_key = eu.RESEND_API_KEY
        eu.RESEND_API_KEY = "re_test_key"
        try:
            self._fake_resend.Emails.send.side_effect = Exception("Resend API error")
            result = eu._send_via_resend(
                "user@example.com", "Test", "<h1>Hi</h1>"
            )
            assert result is False
        finally:
            eu.RESEND_API_KEY = original_key


class TestSendHtmlEmail:
    """Tests for send_html_email routing logic."""

    def test_send_html_email_invalid(self):
        from backend.core.utils.email_utils import send_html_email
        result = send_html_email("invalid", "Test", "<h1>Hi</h1>")
        assert result is False

    def test_send_html_email_routes_to_resend(self):
        import backend.core.utils.email_utils as eu
        original_key = eu.RESEND_API_KEY
        eu.RESEND_API_KEY = "re_test_key"
        try:
            with patch.object(eu, "_send_via_resend", return_value=True) as mock_resend:
                result = eu.send_html_email(
                    "user@example.com", "Test", "<h1>Hi</h1>"
                )
                assert result is True
                mock_resend.assert_called_once()
        finally:
            eu.RESEND_API_KEY = original_key

    def test_send_html_email_routes_to_smtp(self):
        import backend.core.utils.email_utils as eu
        original_key = eu.RESEND_API_KEY
        eu.RESEND_API_KEY = ""
        try:
            with patch.object(eu, "_send_via_smtp", return_value=True) as mock_smtp:
                result = eu.send_html_email(
                    "user@example.com", "Test", "<h1>Hi</h1>"
                )
                assert result is True
                mock_smtp.assert_called_once()
        finally:
            eu.RESEND_API_KEY = original_key


class TestSendHtmlEmailWithAttachment:
    """Tests for send_html_email_with_attachment."""

    def test_send_html_attachment_invalid_email(self):
        from backend.core.utils.email_utils import send_html_email_with_attachment
        result = send_html_email_with_attachment(
            "invalid", "Test", "<h1>Hi</h1>", "/tmp/f.csv"
        )
        assert result is False

    def test_send_html_attachment_file_not_found(self):
        from backend.core.utils.email_utils import send_html_email_with_attachment
        with pytest.raises(FileNotFoundError):
            send_html_email_with_attachment(
                "user@example.com", "Test", "<h1>Hi</h1>", "/nonexist.csv"
            )

    def test_send_html_attachment_routes_to_resend(self):
        import backend.core.utils.email_utils as eu
        original_key = eu.RESEND_API_KEY
        eu.RESEND_API_KEY = "re_test_key"
        try:
            with patch.object(eu, "_send_via_resend", return_value=True) as mock_resend:
                with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
                    f.write(b"data")
                    tmp_path = f.name
                try:
                    result = eu.send_html_email_with_attachment(
                        "user@example.com", "Test", "<h1>Hi</h1>", tmp_path
                    )
                    assert result is True
                    mock_resend.assert_called_once()
                finally:
                    os.unlink(tmp_path)
        finally:
            eu.RESEND_API_KEY = original_key

    def test_send_html_attachment_routes_to_smtp(self):
        import backend.core.utils.email_utils as eu
        original_key = eu.RESEND_API_KEY
        eu.RESEND_API_KEY = ""
        try:
            with patch.object(eu, "_send_via_smtp", return_value=True) as mock_smtp:
                with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
                    f.write(b"data")
                    tmp_path = f.name
                try:
                    result = eu.send_html_email_with_attachment(
                        "user@example.com", "Test", "<h1>Hi</h1>", tmp_path
                    )
                    assert result is True
                    mock_smtp.assert_called_once()
                finally:
                    os.unlink(tmp_path)
        finally:
            eu.RESEND_API_KEY = original_key
