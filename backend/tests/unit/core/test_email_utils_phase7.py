"""
Phase 7 – email_utils.py comprehensive tests.

Covers functions NOT yet tested in phase4:
- _send_via_resend      (Resend API path)
- _send_via_smtp         (SMTP HTML path with/without attachment)
- send_html_email        (auto-selects Resend vs SMTP)
- send_html_email_with_attachment
- Additional error paths for send_email / send_email_with_attachment
"""

import smtplib
from unittest.mock import MagicMock, mock_open, patch

import pytest

# Patch module-level constants BEFORE import
_EMAIL_PATCHES = {
    "SMTP_USER": "testuser@gmail.com",
    "SMTP_PASSWORD": "secret123",
    "SMTP_HOST": "smtp.gmail.com",
    "SMTP_PORT": 587,
    "SMTP_FROM": "testuser@gmail.com",
    "SMTP_USE_TLS": True,
    "RESEND_API_KEY": "",
    "RESEND_FROM": "test@resend.dev",
}


# ═══════════════════════════════════════════════════════════════
# send_email – additional error paths
# ═══════════════════════════════════════════════════════════════


class TestSendEmailErrors:
    @patch.multiple("backend.core.utils.email_utils", **_EMAIL_PATCHES)
    @patch("backend.core.utils.email_utils.smtplib.SMTP")
    def test_smtp_generic_exception(self, mock_smtp_cls):
        from backend.core.utils.email_utils import send_email

        mock_smtp_cls.side_effect = Exception("Connection reset")
        result = send_email("user@example.com", "Test", "Body")
        assert result is False

    @patch.multiple("backend.core.utils.email_utils", **_EMAIL_PATCHES)
    @patch("backend.core.utils.email_utils.smtplib.SMTP")
    def test_smtp_exception_returns_false(self, mock_smtp_cls):
        from backend.core.utils.email_utils import send_email

        mock_smtp_cls.side_effect = smtplib.SMTPException("Server error")
        result = send_email("user@example.com", "Test", "Body")
        assert result is False

    @patch.multiple("backend.core.utils.email_utils", **_EMAIL_PATCHES)
    @patch("backend.core.utils.email_utils.smtplib.SMTP")
    def test_custom_from_email(self, mock_smtp_cls):
        from backend.core.utils.email_utils import send_email

        mock_server = MagicMock()
        mock_smtp_cls.return_value.__enter__ = MagicMock(return_value=mock_server)
        mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)
        result = send_email(
            "user@example.com", "Test", "Body", from_email="custom@example.com"
        )
        assert result is True


# ═══════════════════════════════════════════════════════════════
# send_email_with_attachment – additional paths
# ═══════════════════════════════════════════════════════════════


class TestSendEmailWithAttachmentExtra:
    @patch.multiple("backend.core.utils.email_utils", **_EMAIL_PATCHES)
    @patch("backend.core.utils.email_utils.smtplib.SMTP")
    @patch("backend.core.utils.email_utils.Path")
    @patch("builtins.open", mock_open(read_data=b"file_content"))
    def test_success_with_attachment(self, mock_path_cls, mock_smtp_cls):
        from backend.core.utils.email_utils import send_email_with_attachment

        mock_path_inst = MagicMock()
        mock_path_inst.exists.return_value = True
        mock_path_inst.name = "data.csv"
        mock_path_cls.return_value = mock_path_inst

        mock_server = MagicMock()
        mock_smtp_cls.return_value.__enter__ = MagicMock(return_value=mock_server)
        mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)

        result = send_email_with_attachment(
            "user@example.com", "Report", "See attached", "/tmp/data.csv"
        )
        assert result is True

    @patch.multiple("backend.core.utils.email_utils", **_EMAIL_PATCHES)
    @patch("backend.core.utils.email_utils.smtplib.SMTP")
    @patch("backend.core.utils.email_utils.Path")
    @patch("builtins.open", mock_open(read_data=b"file_content"))
    def test_smtp_exception_with_attachment(self, mock_path_cls, mock_smtp_cls):
        from backend.core.utils.email_utils import send_email_with_attachment

        mock_path_inst = MagicMock()
        mock_path_inst.exists.return_value = True
        mock_path_inst.name = "data.csv"
        mock_path_cls.return_value = mock_path_inst

        mock_smtp_cls.side_effect = smtplib.SMTPException("Error")

        result = send_email_with_attachment(
            "user@example.com", "Report", "See attached", "/tmp/data.csv"
        )
        assert result is False

    @patch.multiple("backend.core.utils.email_utils", **_EMAIL_PATCHES)
    @patch("backend.core.utils.email_utils.smtplib.SMTP")
    @patch("backend.core.utils.email_utils.Path")
    @patch("builtins.open", mock_open(read_data=b"file_content"))
    def test_generic_exception_with_attachment(self, mock_path_cls, mock_smtp_cls):
        from backend.core.utils.email_utils import send_email_with_attachment

        mock_path_inst = MagicMock()
        mock_path_inst.exists.return_value = True
        mock_path_inst.name = "data.csv"
        mock_path_cls.return_value = mock_path_inst

        mock_smtp_cls.side_effect = Exception("Unexpected")

        result = send_email_with_attachment(
            "user@example.com", "Report", "See attached", "/tmp/data.csv"
        )
        assert result is False


# ═══════════════════════════════════════════════════════════════
# _send_via_resend
# ═══════════════════════════════════════════════════════════════


class TestSendViaResend:
    @patch("backend.core.utils.email_utils.RESEND_API_KEY", "re_test_key")
    @patch("backend.core.utils.email_utils.RESEND_FROM", "test@resend.dev")
    @patch("backend.infrastructure.cache.api_usage_tracker.track_api_call")
    @patch(
        "backend.infrastructure.cache.api_usage_tracker.check_api_quota",
        return_value=True,
    )
    def test_success(self, mock_quota, mock_track):
        import sys

        mock_resend = MagicMock()
        mock_resend.Emails.send.return_value = {"id": "abc123"}
        sys.modules["resend"] = mock_resend

        try:
            from backend.core.utils.email_utils import _send_via_resend

            result = _send_via_resend(
                "user@example.com", "Test", "<h1>Hello</h1>"
            )
            assert result is True
            mock_resend.Emails.send.assert_called_once()
        finally:
            sys.modules.pop("resend", None)

    @patch("backend.core.utils.email_utils.RESEND_API_KEY", "re_test_key")
    @patch(
        "backend.infrastructure.cache.api_usage_tracker.check_api_quota",
        return_value=False,
    )
    def test_quota_exceeded(self, mock_quota):
        import sys

        sys.modules["resend"] = MagicMock()
        try:
            from backend.core.utils.email_utils import _send_via_resend

            result = _send_via_resend(
                "user@example.com", "Test", "<h1>Hello</h1>"
            )
            assert result is False
        finally:
            sys.modules.pop("resend", None)

    @patch("backend.core.utils.email_utils.RESEND_API_KEY", "re_test_key")
    @patch("backend.infrastructure.cache.api_usage_tracker.track_api_call")
    @patch(
        "backend.infrastructure.cache.api_usage_tracker.check_api_quota",
        return_value=True,
    )
    def test_with_attachment(self, mock_quota, mock_track):
        import sys

        mock_resend = MagicMock()
        mock_resend.Emails.send.return_value = {"id": "xyz"}
        sys.modules["resend"] = mock_resend

        try:
            with patch(
                "backend.core.utils.email_utils.Path"
            ) as mock_path, patch(
                "builtins.open", mock_open(read_data=b"csv_data")
            ):
                from backend.core.utils.email_utils import _send_via_resend

                mock_path_inst = MagicMock()
                mock_path_inst.exists.return_value = True
                mock_path_inst.name = "report.csv"
                mock_path.return_value = mock_path_inst

                result = _send_via_resend(
                    "user@example.com", "Report", "<table>", "/tmp/report.csv"
                )
                assert result is True
        finally:
            sys.modules.pop("resend", None)

    @patch("backend.core.utils.email_utils.RESEND_API_KEY", "re_test_key")
    @patch(
        "backend.infrastructure.cache.api_usage_tracker.check_api_quota",
        return_value=True,
    )
    def test_attachment_not_found(self, mock_quota):
        import sys

        sys.modules["resend"] = MagicMock()
        try:
            with patch(
                "backend.core.utils.email_utils.Path"
            ) as mock_path:
                from backend.core.utils.email_utils import _send_via_resend

                mock_path_inst = MagicMock()
                mock_path_inst.exists.return_value = False
                mock_path.return_value = mock_path_inst

                # FileNotFoundError is raised but caught by the broad
                # except block in _send_via_resend → returns False
                result = _send_via_resend(
                    "user@example.com", "Report", "<table>",
                    "/tmp/missing.csv",
                )
                assert result is False
        finally:
            sys.modules.pop("resend", None)

    @patch("backend.core.utils.email_utils.RESEND_API_KEY", "re_test_key")
    @patch("backend.infrastructure.cache.api_usage_tracker.track_api_call")
    @patch(
        "backend.infrastructure.cache.api_usage_tracker.check_api_quota",
        return_value=True,
    )
    def test_api_exception(self, mock_quota, mock_track):
        import sys

        mock_resend = MagicMock()
        mock_resend.Emails.send.side_effect = Exception("API error")
        sys.modules["resend"] = mock_resend

        try:
            from backend.core.utils.email_utils import _send_via_resend

            result = _send_via_resend(
                "user@example.com", "Test", "<h1>Hello</h1>"
            )
            assert result is False
        finally:
            sys.modules.pop("resend", None)


# ═══════════════════════════════════════════════════════════════
# _send_via_smtp (HTML path)
# ═══════════════════════════════════════════════════════════════


class TestSendViaSMTP:
    @patch.multiple("backend.core.utils.email_utils", **_EMAIL_PATCHES)
    @patch("backend.core.utils.email_utils.smtplib.SMTP")
    def test_html_no_attachment(self, mock_smtp_cls):
        from backend.core.utils.email_utils import _send_via_smtp

        mock_server = MagicMock()
        mock_smtp_cls.return_value.__enter__ = MagicMock(return_value=mock_server)
        mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)

        result = _send_via_smtp("user@example.com", "Test", "<h1>Hello</h1>")
        assert result is True

    @patch.multiple("backend.core.utils.email_utils", **_EMAIL_PATCHES)
    @patch("backend.core.utils.email_utils.smtplib.SMTP")
    @patch("backend.core.utils.email_utils.Path")
    @patch("builtins.open", mock_open(read_data=b"attachment_bytes"))
    def test_html_with_attachment(self, mock_path_cls, mock_smtp_cls):
        from backend.core.utils.email_utils import _send_via_smtp

        mock_path_inst = MagicMock()
        mock_path_inst.exists.return_value = True
        mock_path_inst.name = "report.xlsx"
        mock_path_cls.return_value = mock_path_inst

        mock_server = MagicMock()
        mock_smtp_cls.return_value.__enter__ = MagicMock(return_value=mock_server)
        mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)

        result = _send_via_smtp(
            "user@example.com", "Report", "<table>", "/tmp/report.xlsx"
        )
        assert result is True

    @patch(
        "backend.core.utils.email_utils.SMTP_USER", ""
    )
    @patch(
        "backend.core.utils.email_utils.SMTP_PASSWORD", ""
    )
    def test_no_smtp_config_simulates(self):
        from backend.core.utils.email_utils import _send_via_smtp

        result = _send_via_smtp("user@example.com", "Test", "<h1>Hello</h1>")
        assert result is True  # Simulated

    @patch.multiple("backend.core.utils.email_utils", **_EMAIL_PATCHES)
    @patch("backend.core.utils.email_utils.smtplib.SMTP")
    def test_exception_returns_false(self, mock_smtp_cls):
        from backend.core.utils.email_utils import _send_via_smtp

        mock_smtp_cls.side_effect = Exception("Connection failed")
        result = _send_via_smtp("user@example.com", "Test", "<h1>Hello</h1>")
        assert result is False


# ═══════════════════════════════════════════════════════════════
# send_html_email (auto-selects)
# ═══════════════════════════════════════════════════════════════


class TestSendHtmlEmail:
    def test_invalid_email(self):
        from backend.core.utils.email_utils import send_html_email

        result = send_html_email("not-an-email", "Test", "<h1>Hello</h1>")
        assert result is False

    @patch("backend.core.utils.email_utils.RESEND_API_KEY", "re_test_key")
    @patch("backend.core.utils.email_utils._send_via_resend", return_value=True)
    def test_uses_resend_when_configured(self, mock_resend):
        from backend.core.utils.email_utils import send_html_email

        result = send_html_email(
            "user@example.com", "Test", "<h1>Hello</h1>"
        )
        assert result is True
        mock_resend.assert_called_once()

    @patch("backend.core.utils.email_utils.RESEND_API_KEY", "")
    @patch("backend.core.utils.email_utils._send_via_smtp", return_value=True)
    def test_falls_back_to_smtp(self, mock_smtp):
        from backend.core.utils.email_utils import send_html_email

        result = send_html_email(
            "user@example.com", "Test", "<h1>Hello</h1>"
        )
        assert result is True
        mock_smtp.assert_called_once()


# ═══════════════════════════════════════════════════════════════
# send_html_email_with_attachment
# ═══════════════════════════════════════════════════════════════


class TestSendHtmlEmailWithAttachment:
    def test_invalid_email(self):
        from backend.core.utils.email_utils import send_html_email_with_attachment

        result = send_html_email_with_attachment(
            "bad", "Test", "<h1>Hi</h1>", "/tmp/f.csv"
        )
        assert result is False

    @patch("backend.core.utils.email_utils.Path")
    def test_file_not_found(self, mock_path_cls):
        from backend.core.utils.email_utils import send_html_email_with_attachment

        mock_path_inst = MagicMock()
        mock_path_inst.exists.return_value = False
        mock_path_cls.return_value = mock_path_inst

        with pytest.raises(FileNotFoundError):
            send_html_email_with_attachment(
                "user@example.com", "Test", "<h1>Hi</h1>", "/tmp/missing.csv"
            )

    @patch("backend.core.utils.email_utils.RESEND_API_KEY", "re_test_key")
    @patch("backend.core.utils.email_utils._send_via_resend", return_value=True)
    @patch("backend.core.utils.email_utils.Path")
    def test_uses_resend(self, mock_path_cls, mock_resend):
        from backend.core.utils.email_utils import send_html_email_with_attachment

        mock_path_inst = MagicMock()
        mock_path_inst.exists.return_value = True
        mock_path_cls.return_value = mock_path_inst

        result = send_html_email_with_attachment(
            "user@example.com", "Report", "<table>", "/tmp/data.csv"
        )
        assert result is True

    @patch("backend.core.utils.email_utils.RESEND_API_KEY", "")
    @patch("backend.core.utils.email_utils._send_via_smtp", return_value=True)
    @patch("backend.core.utils.email_utils.Path")
    def test_falls_back_to_smtp(self, mock_path_cls, mock_smtp):
        from backend.core.utils.email_utils import send_html_email_with_attachment

        mock_path_inst = MagicMock()
        mock_path_inst.exists.return_value = True
        mock_path_cls.return_value = mock_path_inst

        result = send_html_email_with_attachment(
            "user@example.com", "Report", "<table>", "/tmp/data.csv"
        )
        assert result is True
