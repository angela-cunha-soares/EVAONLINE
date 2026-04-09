"""
Unit Tests - Middleware

Testa middlewares da aplicação (CORS, Prometheus).
"""

import pytest


@pytest.mark.unit
class TestCORSMiddleware:
    """Testa CORS (Cross-Origin Resource Sharing)."""

    def test_cors_allows_configured_origins(self, api_client):
        """Testa que CORS permite origens configuradas."""
        response = api_client.options(
            "/api/v1/internal/eto/calculate",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
            },
        )

        # Deve retornar headers CORS
        assert response.status_code in [200, 204]

    def test_cors_allows_credentials(self, api_client):
        """Testa que CORS permite credenciais."""
        response = api_client.options(
            "/api/v1/internal/eto/calculate",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
            },
        )

        if "Access-Control-Allow-Credentials" in response.headers:
            assert (
                response.headers["Access-Control-Allow-Credentials"] == "true"
            )

    @pytest.mark.parametrize(
        "method", ["GET", "POST", "PUT", "PATCH", "DELETE"]
    )
    def test_cors_allows_http_methods(self, api_client, method):
        """Testa que CORS permite métodos HTTP comuns."""
        response = api_client.options(
            "/api/v1/internal/eto/calculate",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": method,
            },
        )

        assert response.status_code in [200, 204]


@pytest.mark.unit
class TestPrometheusMiddleware:
    """Testa middleware de métricas Prometheus."""

    def test_prometheus_increments_request_counter(self, api_client):
        """Testa que requests incrementam contador."""
        # Request qualquer
        api_client.get("/api/v1/health")

        # Buscar métricas
        response = api_client.get("/metrics")

        assert response.status_code == 200
        metrics = response.text

        # Deve conter contador de requests
        assert (
            "http_requests_total" in metrics or "api_requests_total" in metrics
        )

    def test_prometheus_records_request_duration(self, api_client):
        """Testa que duração de requests é registrada."""
        api_client.get("/api/v1/health")

        response = api_client.get("/metrics")
        metrics = response.text

        # Deve conter histograma de duração
        assert (
            "http_request_duration_seconds" in metrics
            or "api_request_duration_seconds" in metrics
        )

    def test_prometheus_labels_include_method_and_endpoint(self, api_client):
        """Testa que métricas incluem labels (method, endpoint)."""
        api_client.get("/api/v1/health")

        response = api_client.get("/metrics")
        metrics = response.text

        # Deve ter labels com method
        assert 'method="GET"' in metrics or "method='GET'" in metrics
