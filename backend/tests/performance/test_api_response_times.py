"""
Performance Tests - API Response Times

Benchmarks the FastAPI endpoint response times.
Target: < 500 ms (p95) for /api/v1/internal/eto/calculate

Reference: Article Section 4 (Performance evaluation)
"""

import pytest
import time
import numpy as np
from datetime import date, timedelta
from unittest.mock import patch, MagicMock

from fastapi.testclient import TestClient

from backend.main import app


@pytest.mark.performance
class TestAPIResponseTimes:
    """Benchmarks for API endpoint latency."""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    @pytest.fixture
    def mock_celery(self):
        with patch(
            "backend.api.routes.eto_routes.calculate_eto_task"
        ) as mock_task:
            mock_result = MagicMock()
            mock_result.id = "perf-test-task-001"
            mock_task.delay.return_value = mock_result
            yield mock_task

    def test_health_endpoint_under_50ms(self, client):
        """GET /api/v1/health should respond in < 50 ms."""
        # Warm up
        for _ in range(5):
            client.get("/api/v1/health")

        times = []
        for _ in range(50):
            start = time.perf_counter()
            response = client.get("/api/v1/health")
            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)

        p95 = np.percentile(times, 95)
        assert response.status_code == 200
        assert p95 < 50.0, f"Health p95={p95:.1f}ms exceeds 50ms"

    def test_eto_calculate_under_500ms(self, client, mock_celery):
        """POST /eto/calculate should respond in < 500 ms (p95)."""
        today = date.today()
        start_date = str(today - timedelta(days=6))  # 7 days inclusive
        end_date = str(today)

        payload = {
            "lat": -22.2926,
            "lng": -48.5841,
            "start_date": start_date,
            "end_date": end_date,
            "period_type": "dashboard_current",
        }

        # Mock rate limiter to avoid slow Redis calls in benchmark
        with patch(
            "backend.api.routes.eto_routes.check_calculation_limit",
            return_value=(True, ""),
        ), patch(
            "backend.api.routes.eto_routes.track_calculation",
        ):
            # Warm up
            for _ in range(3):
                client.post("/api/v1/internal/eto/calculate", json=payload)

            times = []
            for _ in range(30):
                start = time.perf_counter()
                response = client.post(
                    "/api/v1/internal/eto/calculate", json=payload
                )
                elapsed = (time.perf_counter() - start) * 1000
                times.append(elapsed)

        p95 = np.percentile(times, 95)
        assert response.status_code == 200
        assert p95 < 500.0, f"ETo endpoint p95={p95:.1f}ms exceeds 500ms"

    def test_validation_error_is_fast(self, client):
        """422 validation errors should be faster than successful requests."""
        payload = {"start_date": "2025-01-01"}  # Missing lat/lng

        times = []
        for _ in range(20):
            start = time.perf_counter()
            response = client.post(
                "/api/v1/internal/eto/calculate", json=payload
            )
            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)

        p95 = np.percentile(times, 95)
        assert response.status_code == 422
        assert p95 < 100.0, f"Validation error p95={p95:.1f}ms exceeds 100ms"
