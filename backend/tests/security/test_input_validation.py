"""
Security Tests - Input Validation

Tests against SQL injection, XSS, path traversal, oversized payloads,
and malformed coordinate / date inputs.
"""

import os

import pytest

# Detect if Redis is available (valid-looking requests reach Celery)
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
    reason="Redis not available — these tests trigger Celery with 20s retry timeout",
)


@pytest.mark.security
class TestSQLInjectionPrevention:
    """Verifica que SQL injection é bloqueado pela validação Pydantic."""

    SQL_PAYLOADS = [
        "1'; DROP TABLE climate_data;--",
        "1 OR 1=1",
        "0 UNION SELECT * FROM information_schema.tables",
        "'; EXEC xp_cmdshell('whoami');--",
        "1; UPDATE users SET role='admin' WHERE 1=1;--",
    ]

    @pytest.mark.parametrize("payload", SQL_PAYLOADS)
    def test_sql_in_latitude(self, api_client, payload):
        """Latitude com SQL injection deve retornar 422."""
        response = api_client.post(
            "/api/v1/internal/eto/calculate",
            json={
                "lat": payload,
                "lng": -48.5,
                "start_date": "2024-01-01",
                "end_date": "2024-01-07",
                "period_type": "recent",
            },
        )
        assert response.status_code in (400, 422), (
            f"SQL injection not blocked in lat: {payload}"
        )

    @pytest.mark.parametrize("payload", SQL_PAYLOADS)
    def test_sql_in_longitude(self, api_client, payload):
        """Longitude com SQL injection deve retornar 422."""
        response = api_client.post(
            "/api/v1/internal/eto/calculate",
            json={
                "lat": -10.95,
                "lng": payload,
                "start_date": "2024-01-01",
                "end_date": "2024-01-07",
                "period_type": "recent",
            },
        )
        assert response.status_code in (400, 422), (
            f"SQL injection not blocked in lng: {payload}"
        )

    def test_sql_in_date_field(self, api_client):
        """Datas com SQL injection devem ser rejeitadas."""
        response = api_client.post(
            "/api/v1/internal/eto/calculate",
            json={
                "lat": -10.95,
                "lng": -48.33,
                "start_date": "2024-01-01'; DROP TABLE climate_data;--",
                "end_date": "2024-01-07",
                "period_type": "recent",
            },
        )
        assert response.status_code in (400, 422)


@pytest.mark.security
class TestXSSPrevention:
    """Verifica que payloads XSS não são refletidos nas respostas."""

    XSS_PAYLOADS = [
        "<script>alert('xss')</script>",
        "<img src=x onerror=alert(1)>",
        "javascript:alert(document.cookie)",
        "<svg onload=alert(1)>",
        "'\"><script>alert(1)</script>",
    ]

    @pytest.mark.parametrize("payload", XSS_PAYLOADS)
    def test_xss_not_reflected_in_health(self, api_client, payload):
        """XSS payloads não devem ser refletidos nas respostas."""
        response = api_client.get(
            "/api/v1/health",
            params={"test": payload},
        )
        if response.status_code == 200:
            assert payload not in response.text, (
                f"XSS payload reflected in response: {payload}"
            )

    @skip_if_no_redis
    @pytest.mark.parametrize("payload", XSS_PAYLOADS)
    def test_xss_in_email_field(self, api_client, payload):
        """XSS em campo de email must not be reflected in API response.

        The async API accepts the request (200 + task_id) and the Celery
        worker later rejects the invalid email.  The security invariant
        is that XSS payloads are NEVER reflected back to the caller.
        """
        response = api_client.post(
            "/api/v1/internal/eto/calculate",
            json={
                "lat": -10.95,
                "lng": -48.33,
                "start_date": "2024-01-01",
                "end_date": "2024-01-07",
                "period_type": "historical_email",
                "email": payload,
            },
        )
        # For an async API the request may be accepted (200/202) and
        # processed by a background worker.  The critical check is that
        # the XSS payload is never reflected in the response body.
        if response.status_code in (200, 201, 202):
            assert payload not in response.text, (
                f"XSS payload reflected in response body: {payload}"
            )
        # Non-2xx is also acceptable (payload rejected early).


@pytest.mark.security
class TestCoordinateValidation:
    """Verifica rejeição de coordenadas fora do range válido."""

    def test_latitude_above_max(self, api_client):
        """lat > 90 deve ser rejeitado."""
        response = api_client.post(
            "/api/v1/internal/eto/calculate",
            json={
                "lat": 91.0,
                "lng": -48.33,
                "start_date": "2024-01-01",
                "end_date": "2024-01-07",
                "period_type": "recent",
            },
        )
        assert response.status_code in (400, 422)

    def test_latitude_below_min(self, api_client):
        """lat < -90 deve ser rejeitado."""
        response = api_client.post(
            "/api/v1/internal/eto/calculate",
            json={
                "lat": -91.0,
                "lng": -48.33,
                "start_date": "2024-01-01",
                "end_date": "2024-01-07",
                "period_type": "recent",
            },
        )
        assert response.status_code in (400, 422)

    def test_longitude_above_max(self, api_client):
        """lon > 180 deve ser rejeitado."""
        response = api_client.post(
            "/api/v1/internal/eto/calculate",
            json={
                "lat": -10.95,
                "lng": 181.0,
                "start_date": "2024-01-01",
                "end_date": "2024-01-07",
                "period_type": "recent",
            },
        )
        assert response.status_code in (400, 422)

    def test_longitude_below_min(self, api_client):
        """lon < -180 deve ser rejeitado."""
        response = api_client.post(
            "/api/v1/internal/eto/calculate",
            json={
                "lat": -10.95,
                "lng": -181.0,
                "start_date": "2024-01-01",
                "end_date": "2024-01-07",
                "period_type": "recent",
            },
        )
        assert response.status_code in (400, 422)

    def test_extreme_coordinate_value(self, api_client):
        """Valores extremos (999) devem ser rejeitados."""
        response = api_client.post(
            "/api/v1/internal/eto/calculate",
            json={
                "lat": 999,
                "lng": -999,
                "start_date": "2024-01-01",
                "end_date": "2024-01-07",
                "period_type": "recent",
            },
        )
        assert response.status_code in (400, 422)


@pytest.mark.security
class TestPayloadValidation:
    """Verifica rejeição de payloads malformados ou oversized."""

    def test_empty_body_rejected(self, api_client):
        """Body vazio deve retornar erro."""
        response = api_client.post(
            "/api/v1/internal/eto/calculate",
            json={},
        )
        assert response.status_code in (400, 422)

    def test_missing_required_fields(self, api_client):
        """Campos obrigatórios faltando devem retornar 422."""
        response = api_client.post(
            "/api/v1/internal/eto/calculate",
            json={"lat": -10.95},
        )
        assert response.status_code in (400, 422)

    def test_invalid_date_format(self, api_client):
        """Formato de data inválido deve ser rejeitado."""
        response = api_client.post(
            "/api/v1/internal/eto/calculate",
            json={
                "lat": -10.95,
                "lng": -48.33,
                "start_date": "01/01/2024",  # wrong format
                "end_date": "07-Jan-2024",  # wrong format
                "period_type": "recent",
            },
        )
        assert response.status_code in (400, 422)

    def test_start_after_end_date(self, api_client):
        """start_date > end_date deve ser rejeitado."""
        response = api_client.post(
            "/api/v1/internal/eto/calculate",
            json={
                "lat": -10.95,
                "lng": -48.33,
                "start_date": "2024-12-31",
                "end_date": "2024-01-01",
                "period_type": "recent",
            },
        )
        assert response.status_code in (400, 422)

    @skip_if_no_redis
    def test_oversized_json_body(self, api_client):
        """Payload muito grande deve ser rejeitado ou não causar crash."""
        huge_payload = {
            "lat": -10.95,
            "lng": -48.33,
            "start_date": "2024-01-01",
            "end_date": "2024-01-07",
            "period_type": "recent",
            "extra_data": "X" * (1024 * 1024),  # 1 MB of junk
        }
        response = api_client.post(
            "/api/v1/internal/eto/calculate",
            json=huge_payload,
        )
        # Should not crash the server (200-level would be ok if field is
        # ignored; 413/422 if rejected — anything except 500)
        assert response.status_code != 500, "Server crash on oversized payload"

    def test_invalid_period_type(self, api_client):
        """period_type inválido deve ser rejeitado."""
        response = api_client.post(
            "/api/v1/internal/eto/calculate",
            json={
                "lat": -10.95,
                "lng": -48.33,
                "start_date": "2024-01-01",
                "end_date": "2024-01-07",
                "period_type": "INVALID_TYPE",
            },
        )
        assert response.status_code in (400, 422)
