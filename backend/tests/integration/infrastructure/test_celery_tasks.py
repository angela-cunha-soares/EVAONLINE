"""
Integration Tests - Infrastructure Celery Tasks

Tests the Celery infrastructure layer: app config, worker setup,
task serialization, and eager-mode execution.

Reference: Article Section 3.3 (Asynchronous processing architecture)
"""

import pytest
from backend.infrastructure.celery.celery_config import celery_app


@pytest.mark.integration
class TestCeleryAppConfiguration:
    """Tests Celery application configuration."""

    def test_celery_app_exists(self):
        """Celery app should be properly instantiated."""
        assert celery_app is not None
        assert celery_app.main is not None

    def test_broker_url_configured(self):
        """Broker URL must be configured (Redis)."""
        broker = celery_app.conf.broker_url
        assert broker is not None
        assert "redis" in broker.lower()

    def test_result_backend_configured(self):
        """Result backend must be configured."""
        backend = celery_app.conf.result_backend
        assert backend is not None

    def test_task_serializer_json(self):
        """Tasks should use JSON serialization."""
        serializer = celery_app.conf.task_serializer
        assert serializer == "json"

    def test_task_always_eager_in_testing(self):
        """In testing env, task_always_eager should be True."""
        assert celery_app.conf.task_always_eager is True


@pytest.mark.integration
class TestCeleryTaskDiscovery:
    """Tests that all required tasks are discoverable."""

    def test_eto_task_registered(self):
        """calculate_eto_task must be importable."""
        from backend.infrastructure.celery.tasks.eto_calculation import (
            calculate_eto_task,
        )

        assert calculate_eto_task is not None
        assert callable(calculate_eto_task)

    def test_task_has_correct_attributes(self):
        """Task should have standard Celery attributes."""
        from backend.infrastructure.celery.tasks.eto_calculation import (
            calculate_eto_task,
        )

        assert hasattr(calculate_eto_task, "delay")
        assert hasattr(calculate_eto_task, "apply_async")
        assert hasattr(calculate_eto_task, "apply")
        assert hasattr(calculate_eto_task, "name")
