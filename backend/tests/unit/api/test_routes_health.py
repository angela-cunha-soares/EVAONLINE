"""
Unit Tests - Health & Metrics Endpoints

Testa endpoints de saúde e métricas do sistema.
"""

import pytest


@pytest.mark.unit
class TestHealthEndpoint:
    """Testa endpoint /health."""

    def test_health_returns_200(self, api_client):
        """Testa que /health retorna 200 OK."""
        response = api_client.get("/api/v1/health")

        assert response.status_code == 200

    def test_health_returns_json(self, api_client):
        """Testa que /health retorna JSON válido."""
        response = api_client.get("/api/v1/health")

        assert response.headers["content-type"] == "application/json"
        data = response.json()
        assert isinstance(data, dict)

    def test_health_has_status_key(self, api_client):
        """Testa que resposta contém chave 'status'."""
        response = api_client.get("/api/v1/health")
        data = response.json()

        assert "status" in data
        assert data["status"] in ["ok", "healthy", "up"]

    def test_health_has_timestamp(self, api_client):
        """Testa que resposta contém timestamp."""
        response = api_client.get("/api/v1/health")
        data = response.json()

        # Pode ser 'timestamp', 'time', ou similar
        assert any(
            key in data for key in ["timestamp", "time", "datetime"]
        ), "Response should contain a timestamp field"


@pytest.mark.unit
class TestMetricsEndpoint:
    """Testa endpoint /metrics (Prometheus)."""

    def test_metrics_returns_200(self, api_client):
        """Testa que /metrics retorna 200 OK."""
        response = api_client.get("/metrics")

        assert response.status_code == 200

    def test_metrics_returns_prometheus_format(self, api_client):
        """Testa que /metrics retorna formato Prometheus."""
        response = api_client.get("/metrics")

        # Prometheus retorna text/plain
        assert "text/plain" in response.headers.get("content-type", "")

        # Deve conter métricas válidas
        content = response.text
        assert "# TYPE" in content or "# HELP" in content

    @pytest.mark.parametrize(
        "expected_metric",
        [
            "http_requests_total",
            "http_request_duration_seconds",
            "api_requests_total",
        ],
    )
    def test_metrics_contains_standard_metrics(
        self, api_client, expected_metric
    ):
        """Testa que métricas padrão Prometheus existem."""
        response = api_client.get("/metrics")
        content = response.text

        assert (
            expected_metric in content
        ), f"Metric '{expected_metric}' not found in /metrics"


@pytest.mark.unit
class TestRootEndpoint:
    """Testa endpoint raiz /."""

    def test_root_returns_200_or_redirect(self, api_client):
        """Testa que raiz retorna 200 ou redirect."""
        response = api_client.get("/", follow_redirects=False)

        # Pode retornar 200 (docs) ou 307/308 (redirect)
        assert response.status_code in [200, 307, 308]

    def test_docs_endpoint_accessible(self, api_client):
        """Testa que /docs é acessível."""
        response = api_client.get("/api/v1/docs")

        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")

    def test_openapi_json_accessible(self, api_client):
        """Testa que schema OpenAPI está acessível."""
        response = api_client.get("/api/v1/openapi.json")

        assert response.status_code == 200
        data = response.json()

        # Validar estrutura OpenAPI
        assert "openapi" in data
        assert "info" in data
        assert "paths" in data
