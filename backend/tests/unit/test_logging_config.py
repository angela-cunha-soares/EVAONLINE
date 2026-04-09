"""Tests for config/logging_config.py."""

import os
import tempfile
from pathlib import Path

from config.logging_config import LoggingConfig, LogContext


class TestLoggingConfig:
    def test_init_defaults(self):
        cfg = LoggingConfig()
        assert cfg.log_level == "INFO"
        assert cfg.rotation == "00:00"
        assert cfg.retention == "30 days"
        assert cfg.compression == "zip"
        assert cfg.json_logs is False

    def test_init_custom(self):
        cfg = LoggingConfig(
            log_level="DEBUG",
            log_dir="custom_logs",
            json_logs=True,
        )
        assert cfg.log_level == "DEBUG"
        assert cfg.json_logs is True

    def test_creates_log_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            log_dir = os.path.join(tmp, "test_logs")
            cfg = LoggingConfig(log_dir=log_dir)
            assert Path(log_dir).exists()

    def test_setup_text_format(self, tmp_path):
        log_dir = str(tmp_path / "logs_text")
        cfg = LoggingConfig(log_dir=log_dir, json_logs=False)
        cfg.setup()  # Should not raise

    def test_setup_json_format(self, tmp_path):
        log_dir = str(tmp_path / "logs_json")
        cfg = LoggingConfig(log_dir=log_dir, json_logs=True)
        cfg.setup()  # Should not raise

    def test_get_colored_format(self):
        fmt = LoggingConfig._get_colored_format()
        assert isinstance(fmt, str)
        assert "level" in fmt

    def test_get_json_format(self):
        fmt = LoggingConfig._get_json_format()
        assert isinstance(fmt, str)
        assert "timestamp" in fmt
        assert "message" in fmt


class TestLogContext:
    def test_api_request_context(self):
        ctx = LogContext.api_request("GET", "/api/test")
        assert ctx is not None

    def test_api_request_with_user(self):
        ctx = LogContext.api_request("POST", "/api/eto", user_id="u123", request_id="r456")
        assert ctx is not None

    def test_celery_task_context(self):
        ctx = LogContext.celery_task("calc_eto", "task-123")
        assert ctx is not None

    def test_celery_task_with_args(self):
        ctx = LogContext.celery_task("calc_eto", "task-123", args={"lat": -23})
        assert ctx is not None

    def test_database_operation_context(self):
        ctx = LogContext.database_operation("INSERT", "eto_results")
        assert ctx is not None

    def test_database_operation_with_duration(self):
        ctx = LogContext.database_operation("SELECT", "visitors", duration_ms=15.5)
        assert ctx is not None
