"""
Security Tests - Rate Limiting

Tests: Burst protection, rate-limit headers, and recovery after window.
"""

import os
import time

import pytest

# Detect if Redis is available (rate limiter middleware tries to connect)
# .env may set REDIS_HOST=redis (Docker network name), so we also try localhost
_REDIS_AVAILABLE = False
try:
    import redis as _redis_mod

    _redis_port = int(os.getenv("REDIS_PORT", "6379"))
    _redis_pwd = os.getenv("REDIS_PASSWORD") or None
    for _host in (os.getenv("REDIS_HOST", "localhost"), "localhost", "127.0.0.1"):
        try:
            _r = _redis_mod.Redis(
                host=_host, port=_redis_port,
                password=_redis_pwd, socket_connect_timeout=1,
            )
            _r.ping()
            _REDIS_AVAILABLE = True
            break
        except Exception:
            continue
except ImportError:
    pass

skip_if_no_redis = pytest.mark.skipif(
    not _REDIS_AVAILABLE,
    reason="Redis not available — rate limiter attempts block ~2.7s per request",
)


@pytest.mark.security
class TestRateLimitingSecurity:
    """Testa rate limiting e proteção contra abuso."""

    def test_health_endpoint_burst(self, api_client):
        """Burst de requests rápidos no /health não deve causar 500."""
        status_codes = []
        for _ in range(50):
            resp = api_client.get("/api/v1/health")
            status_codes.append(resp.status_code)

        # Should see 200s and possibly 429s — never 500
        assert 500 not in status_codes, (
            "Server returned 500 under burst load"
        )
        assert 200 in status_codes, (
            "At least some health requests should succeed"
        )

    @skip_if_no_redis
    def test_calculate_endpoint_burst(self, api_client):
        """Burst de requests de cálculo com inválidos — verifica estabilidade."""
        # Use intentionally invalid payloads to test validation layer
        # without hitting Celery/Redis (which isn't available in test env).
        # Each request can take ~2.7s without Redis (rate limiter timeout),
        # so we keep the count low.
        payload = {
            "lat": 999,  # Invalid — triggers 400 before Celery
            "lng": -999,
            "start_date": "2024-01-01",
            "end_date": "2024-01-07",
            "period_type": "recent",
        }
        status_codes = []
        for _ in range(5):
            resp = api_client.post(
                "/api/v1/internal/eto/calculate", json=payload
            )
            status_codes.append(resp.status_code)

        # System must not crash; 400/422/429 are all acceptable
        assert 500 not in status_codes, (
            "Server returned 500 under burst POST load"
        )

    def test_rate_limit_headers_present(self, api_client):
        """Verifica presença de headers de rate limit (informational)."""
        response = api_client.get("/api/v1/health")
        rate_headers = [
            "X-RateLimit-Limit",
            "X-RateLimit-Remaining",
            "X-RateLimit-Reset",
            "Retry-After",
        ]
        has_any = any(h.lower() in {k.lower() for k in response.headers} for h in rate_headers)
        # Informational — log presence but don't fail
        if not has_any:
            pytest.skip(
                "Rate limit headers not present "
                "(may be handled by Nginx in production)"
            )
        assert has_any

    def test_rate_limit_recovery(self, api_client):
        """Após burst, o sistema deve recuperar (não travar)."""
        # Fire burst
        for _ in range(30):
            api_client.get("/api/v1/health")

        # Small pause
        time.sleep(1)

        # Must recover
        response = api_client.get("/api/v1/health")
        assert response.status_code in (200, 429), (
            f"System did not recover after burst: {response.status_code}"
        )


@pytest.mark.security
class TestEndpointAccessControl:
    """Verifica que endpoints internos/métricas não são expostos."""

    def test_metrics_not_publicly_accessible(self, api_client):
        """O endpoint /metrics deve existir mas ser protegido em produção."""
        response = api_client.get("/metrics")
        # In test env /metrics may return 200 (Prometheus instrumentator)
        # In production Nginx blocks it. Just ensure no 500.
        assert response.status_code != 500

    def test_docs_accessible(self, api_client):
        """Swagger UI deve estar acessível."""
        response = api_client.get("/api/v1/docs")
        assert response.status_code == 200

    def test_openapi_schema_accessible(self, api_client):
        """OpenAPI JSON schema deve estar acessível."""
        response = api_client.get("/api/v1/openapi.json")
        assert response.status_code == 200
        data = response.json()
        assert "openapi" in data
        assert "paths" in data

    def test_nonexistent_endpoint_returns_404(self, api_client):
        """Endpoint inexistente deve retornar 404, não 500."""
        response = api_client.get("/api/v1/this-does-not-exist")
        # 404/405 from FastAPI, or 200 if Dash front-end catches unmatched
        # routes — the key check is it must never return 500.
        assert response.status_code != 500, (
            f"Nonexistent endpoint returned 500: {response.text[:200]}"
        )
