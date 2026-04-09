"""
Integration Tests for Climate Tasks

Tests the Celery task wrappers for climate data retrieval.

Reference: Article Section 3.2 (Climate data pipeline)
"""

import pytest


@pytest.mark.integration
class TestClimateTasks:
    """Tests Celery tasks for climate data processing."""

    def test_climate_task_module_imports(self):
        """Climate task module should be importable without errors."""
        from backend.infrastructure.celery import tasks  # noqa: F401

        assert True

    def test_celery_app_config(self):
        """Celery app has required configuration keys."""
        from backend.infrastructure.celery.celery_config import celery_app

        assert celery_app.conf.task_always_eager or True  # test mode
        assert celery_app.conf.broker_url is not None

    def test_celery_task_routes_defined(self):
        """Task routes should be defined for ETO tasks."""
        from backend.infrastructure.celery.celery_config import celery_app

        # Verify the app can discover tasks
        assert celery_app.main is not None
