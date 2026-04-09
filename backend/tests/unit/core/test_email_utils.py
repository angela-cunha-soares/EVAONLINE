"""
Unit Tests – backend.core.utils.email_utils

Tests validate_email (pure regex) and send functions (mocked SMTP).
"""

import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest


# ===================================================================
# validate_email (pure logic — no I/O)
# ===================================================================

class TestValidateEmail:
    """Tests for email_utils.validate_email"""

    def test_valid_simple(self):
        from backend.core.utils.email_utils import validate_email
        assert validate_email("user@example.com") is True

    def test_valid_with_dots(self):
        from backend.core.utils.email_utils import validate_email
        assert validate_email("first.last@company.org") is True

    def test_valid_with_plus(self):
        from backend.core.utils.email_utils import validate_email
        assert validate_email("user+tag@gmail.com") is True

    def test_valid_with_numbers(self):
        from backend.core.utils.email_utils import validate_email
        assert validate_email("user123@test456.co.uk") is True

    def test_invalid_no_at(self):
        from backend.core.utils.email_utils import validate_email
        assert validate_email("invalid.email") is False

    def test_invalid_no_domain(self):
        from backend.core.utils.email_utils import validate_email
        assert validate_email("user@") is False

    def test_invalid_no_tld(self):
        from backend.core.utils.email_utils import validate_email
        assert validate_email("user@domain") is False

    def test_empty_string(self):
        from backend.core.utils.email_utils import validate_email
        assert validate_email("") is False

    def test_none_input(self):
        from backend.core.utils.email_utils import validate_email
        assert validate_email(None) is False

    def test_integer_input(self):
        from backend.core.utils.email_utils import validate_email
        assert validate_email(42) is False

    def test_spaces(self):
        from backend.core.utils.email_utils import validate_email
        assert validate_email("user @example.com") is False

    def test_double_at(self):
        from backend.core.utils.email_utils import validate_email
        assert validate_email("user@@example.com") is False


# ===================================================================
# send_email (mocked SMTP)
# ===================================================================

class TestSendEmail:
    """Tests for email_utils.send_email with mocked SMTP"""

    def test_invalid_email_returns_false(self):
        from backend.core.utils.email_utils import send_email
        assert send_email("bad-email", "subject", "body") is False

    @patch.dict(os.environ, {"SMTP_USER": "", "SMTP_PASSWORD": ""})
    def test_no_smtp_config_simulates(self):
        """Without SMTP credentials, email is simulated → returns True"""
        # Re-import to pick up env changes
        import importlib
        import backend.core.utils.email_utils as mod
        importlib.reload(mod)
        result = mod.send_email("user@example.com", "Test Subject", "Test Body")
        assert result is True

    @patch("backend.core.utils.email_utils.smtplib.SMTP")
    def test_smtp_success(self, mock_smtp_class):
        """Successful SMTP send returns True"""
        import importlib
        import backend.core.utils.email_utils as mod

        # Simulate configured SMTP
        with patch.object(mod, "SMTP_USER", "testuser"):
            with patch.object(mod, "SMTP_PASSWORD", "testpass"):
                mock_server = MagicMock()
                mock_smtp_class.return_value.__enter__ = MagicMock(return_value=mock_server)
                mock_smtp_class.return_value.__exit__ = MagicMock(return_value=False)
                result = mod.send_email("user@example.com", "Subject", "Body")
                assert result is True


# ===================================================================
# send_email_with_attachment
# ===================================================================

class TestSendEmailWithAttachment:
    """Tests for email_utils.send_email_with_attachment"""

    def test_invalid_email_returns_false(self):
        from backend.core.utils.email_utils import send_email_with_attachment
        assert send_email_with_attachment("bad", "subj", "body", "/tmp/f.csv") is False

    def test_missing_file_raises(self):
        from backend.core.utils.email_utils import send_email_with_attachment
        with pytest.raises(FileNotFoundError):
            send_email_with_attachment(
                "user@example.com", "subj", "body",
                "/nonexistent/path/file.csv"
            )

    @patch.dict(os.environ, {"SMTP_USER": "", "SMTP_PASSWORD": ""})
    def test_no_smtp_simulates_with_attachment(self):
        import importlib
        import backend.core.utils.email_utils as mod
        importlib.reload(mod)

        # Create a temp file to use as attachment
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
            f.write(b"col1,col2\n1,2\n")
            tmp_path = f.name
        try:
            result = mod.send_email_with_attachment(
                "user@example.com", "Subject", "Body", tmp_path
            )
            assert result is True
        finally:
            os.unlink(tmp_path)


# ===================================================================
# send_html_email
# ===================================================================

class TestSendHtmlEmail:
    """Tests for email_utils.send_html_email"""

    def test_invalid_email_returns_false(self):
        from backend.core.utils.email_utils import send_html_email
        assert send_html_email("bad", "subj", "<h1>Hi</h1>") is False


# ===================================================================
# send_html_email_with_attachment
# ===================================================================

class TestSendHtmlEmailWithAttachment:
    """Tests for email_utils.send_html_email_with_attachment"""

    def test_invalid_email_returns_false(self):
        from backend.core.utils.email_utils import send_html_email_with_attachment
        assert send_html_email_with_attachment(
            "bad", "subj", "<h1>Hi</h1>", "/tmp/f.csv"
        ) is False

    def test_missing_file_raises(self):
        from backend.core.utils.email_utils import send_html_email_with_attachment
        with pytest.raises(FileNotFoundError):
            send_html_email_with_attachment(
                "user@example.com", "subj", "<h1>Hi</h1>",
                "/nonexistent/path/file.csv"
            )
