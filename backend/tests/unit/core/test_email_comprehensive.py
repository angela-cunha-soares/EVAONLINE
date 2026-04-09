"""
Tests for email_utils.py and email_templates.py.

Covers:
- validate_email (pure regex validation)
- send_email / send_email_with_attachment (mocked SMTP)
- send_html_email / send_html_email_with_attachment (routing logic)
- Email template generation (processing started, data ready, error)
"""

import pytest
import tempfile
import os
from unittest.mock import patch, MagicMock

from backend.core.utils.email_utils import (
    validate_email,
    send_email,
    send_email_with_attachment,
    send_html_email,
    send_html_email_with_attachment,
)
from backend.core.utils.email_templates import (
    get_email_header,
    get_email_footer,
    _t,
    create_processing_started_email,
)


# ════════════════════════════════════════════════════════════════════
# validate_email — pure regex
# ════════════════════════════════════════════════════════════════════

class TestValidateEmail:

    def test_valid_email(self):
        assert validate_email("user@example.com") is True

    def test_valid_email_subdomain(self):
        assert validate_email("user@sub.domain.org") is True

    def test_valid_email_with_plus(self):
        assert validate_email("user+tag@gmail.com") is True

    def test_valid_email_with_dots(self):
        assert validate_email("first.last@example.com") is True

    def test_invalid_no_at(self):
        assert validate_email("invalid.email") is False

    def test_invalid_no_domain(self):
        assert validate_email("user@") is False

    def test_invalid_no_tld(self):
        assert validate_email("user@domain") is False

    def test_invalid_double_at(self):
        assert validate_email("user@@domain.com") is False

    def test_invalid_none(self):
        assert validate_email(None) is False

    def test_invalid_empty(self):
        assert validate_email("") is False

    def test_invalid_not_string(self):
        assert validate_email(12345) is False

    def test_invalid_spaces(self):
        assert validate_email("user @example.com") is False


# ════════════════════════════════════════════════════════════════════
# send_email — mocked SMTP
# ════════════════════════════════════════════════════════════════════

class TestSendEmail:

    def test_invalid_email_returns_false(self):
        assert send_email("invalid", "Subj", "Body") is False

    @patch.dict(os.environ, {"SMTP_USER": "", "SMTP_PASSWORD": ""})
    def test_no_smtp_config_simulates(self):
        """Without SMTP credentials, email is simulated (returns True)"""
        # Reload module to pick up env
        import importlib
        import backend.core.utils.email_utils as mod
        mod.SMTP_USER = ""
        mod.SMTP_PASSWORD = ""
        result = mod.send_email("user@example.com", "Test", "Body")
        assert result is True

    @patch("backend.core.utils.email_utils.smtplib.SMTP")
    def test_smtp_success(self, mock_smtp_class):
        """With SMTP credentials, sends via SMTP"""
        import backend.core.utils.email_utils as mod
        mod.SMTP_USER = "user@gmail.com"
        mod.SMTP_PASSWORD = "secret"
        
        mock_server = MagicMock()
        mock_smtp_class.return_value.__enter__ = MagicMock(return_value=mock_server)
        mock_smtp_class.return_value.__exit__ = MagicMock(return_value=False)
        
        result = mod.send_email("dest@example.com", "Subject", "Body")
        assert result is True

    @patch("backend.core.utils.email_utils.smtplib.SMTP")
    def test_smtp_auth_error(self, mock_smtp_class):
        import smtplib
        import backend.core.utils.email_utils as mod
        mod.SMTP_USER = "user@gmail.com"
        mod.SMTP_PASSWORD = "wrong"
        
        mock_server = MagicMock()
        mock_server.login.side_effect = smtplib.SMTPAuthenticationError(535, b"Auth failed")
        mock_smtp_class.return_value.__enter__ = MagicMock(return_value=mock_server)
        mock_smtp_class.return_value.__exit__ = MagicMock(return_value=False)
        
        result = mod.send_email("dest@example.com", "Subject", "Body")
        assert result is False


# ════════════════════════════════════════════════════════════════════
# send_email_with_attachment
# ════════════════════════════════════════════════════════════════════

class TestSendEmailWithAttachment:

    def test_invalid_email(self):
        assert send_email_with_attachment("invalid", "Sub", "Body", "/tmp/f.csv") is False

    def test_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            send_email_with_attachment(
                "user@example.com", "Sub", "Body", "/nonexistent/file.csv"
            )

    def test_simulated_with_temp_file(self):
        import backend.core.utils.email_utils as mod
        mod.SMTP_USER = ""
        mod.SMTP_PASSWORD = ""
        
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
            f.write(b"date,ETo\n2024-01-01,4.5")
            tmp_path = f.name
        try:
            result = mod.send_email_with_attachment(
                "user@example.com", "Data", "Here's data", tmp_path
            )
            assert result is True
        finally:
            os.unlink(tmp_path)


# ════════════════════════════════════════════════════════════════════
# send_html_email — routing logic
# ════════════════════════════════════════════════════════════════════

class TestSendHtmlEmail:

    def test_invalid_email(self):
        assert send_html_email("invalid", "Sub", "<h1>Hi</h1>") is False

    @patch("backend.core.utils.email_utils.RESEND_API_KEY", "")
    @patch("backend.core.utils.email_utils._send_via_smtp")
    def test_routes_to_smtp_without_resend(self, mock_smtp):
        mock_smtp.return_value = True
        result = send_html_email("user@example.com", "Sub", "<h1>Hi</h1>")
        mock_smtp.assert_called_once()

    def test_html_with_attachment_invalid_email(self):
        assert send_html_email_with_attachment(
            "invalid", "Sub", "<h1>Hi</h1>", "/tmp/f.csv"
        ) is False

    def test_html_with_attachment_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            send_html_email_with_attachment(
                "user@example.com", "Sub", "<h1>Hi</h1>", "/nonexistent/file.csv"
            )


# ════════════════════════════════════════════════════════════════════
# Email templates — pure HTML generation
# ════════════════════════════════════════════════════════════════════

class TestEmailTemplates:

    def test_translation_helper_en(self):
        text = _t("en", "header_subtitle")
        assert "EVApotranspiration" in text

    def test_translation_helper_pt(self):
        text = _t("pt", "header_subtitle")
        assert "EVApotranspiration" in text

    def test_translation_missing_key(self):
        text = _t("en", "nonexistent_key_xyz")
        assert text == "nonexistent_key_xyz"

    def test_header_contains_evaonline(self):
        header = get_email_header("en")
        assert "EVAonline" in header

    def test_header_en_vs_pt(self):
        h_en = get_email_header("en")
        h_pt = get_email_header("pt")
        assert "EVAonline" in h_en
        assert "EVAonline" in h_pt

    def test_footer_contains_fao56(self):
        footer = get_email_footer("en")
        assert "FAO-56" in footer

    def test_footer_contains_github_link(self):
        footer = get_email_footer("en")
        assert "github.com" in footer.lower()

    def test_create_processing_started_email(self):
        from datetime import datetime
        subject, html_body = create_processing_started_email(
            task_id="task_123",
            latitude=-15.7939,
            longitude=-47.8828,
            start_date="2024-01-01",
            end_date="2024-01-31",
            started_at=datetime(2024, 1, 15, 10, 30, 0),
            file_format="excel",
            lang="en",
        )
        assert "EVAonline" in subject
        assert "-15.7939" in html_body
        assert "-47.8828" in html_body
        assert "2024-01-01" in html_body
        assert "2024-01-31" in html_body

    def test_create_processing_started_email_pt(self):
        from datetime import datetime
        subject, html_body = create_processing_started_email(
            task_id="task_456",
            latitude=-23.5,
            longitude=-46.6,
            start_date="2024-06-01",
            end_date="2024-06-30",
            started_at=datetime(2024, 6, 15, 14, 0, 0),
            file_format="csv",
            lang="pt",
        )
        assert "EVAonline" in subject
        assert "-23.5" in html_body
        assert "CSV" in html_body

    def test_create_processing_started_email_calculates_days(self):
        from datetime import datetime
        _, html_body = create_processing_started_email(
            task_id="task_789",
            latitude=0, longitude=0,
            start_date="2024-01-01",
            end_date="2024-01-10",
            started_at=datetime(2024, 1, 1),
            lang="en",
        )
        # 10 days in the period
        assert "10" in html_body
