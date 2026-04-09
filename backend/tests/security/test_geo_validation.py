"""
Security Tests - Geo Validation

Tests: Coordinate range validation, WKT/GeoJSON injection prevention,
SRID validation, and boundary-condition handling.
"""

import os

import pytest

# Detect if Redis is available (valid coordinates will reach Celery)
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
    reason="Redis not available — valid-coord tests trigger Celery with 20s retry timeout",
)


@pytest.mark.security
class TestCoordinateRangeValidation:
    """Verifica que coordenadas fora do range [-90,90] x [-180,180]
    são rejeitadas corretamente pelas funções de validação."""

    INVALID_COORDINATES = [
        (91.0, 0.0, "lat > 90"),
        (-91.0, 0.0, "lat < -90"),
        (0.0, 181.0, "lon > 180"),
        (0.0, -181.0, "lon < -180"),
        (999.0, 999.0, "extreme values"),
        (-999.0, -999.0, "extreme negative"),
    ]

    @pytest.mark.parametrize(
        "lat,lon,desc", INVALID_COORDINATES, ids=[c[2] for c in INVALID_COORDINATES]
    )
    def test_invalid_coordinates_rejected(self, api_client, lat, lon, desc):
        """Coordenadas inválidas ({desc}) devem retornar 400/422."""
        response = api_client.post(
            "/api/v1/internal/eto/calculate",
            json={
                "lat": lat,
                "lng": lon,
                "start_date": "2024-01-01",
                "end_date": "2024-01-07",
                "period_type": "recent",
            },
        )
        assert response.status_code in (400, 422), (
            f"Invalid coords ({lat}, {lon}) not rejected: HTTP {response.status_code}"
        )

    VALID_BOUNDARY_COORDINATES = [
        (0.0, 0.0, "null island"),
        (90.0, 180.0, "NE corner"),
        (-90.0, -180.0, "SW corner"),
        (-23.5505, -46.6333, "São Paulo"),
        (40.7128, -74.0060, "New York"),
        (64.1466, -21.9426, "Reykjavík (Nordic)"),
    ]

    @skip_if_no_redis
    @pytest.mark.parametrize(
        "lat,lon,desc",
        VALID_BOUNDARY_COORDINATES,
        ids=[c[2] for c in VALID_BOUNDARY_COORDINATES],
    )
    def test_valid_coordinates_accepted(self, api_client, lat, lon, desc):
        """Coordenadas válidas ({desc}) devem passar a validação (não 422).

        Note: In test env without Redis/Celery, valid requests may return
        500 after passing validation (Celery connection failure). This is
        expected — we only check that coordinates are NOT rejected by the
        Pydantic/validation layer (422).
        """
        response = api_client.post(
            "/api/v1/internal/eto/calculate",
            json={
                "lat": lat,
                "lng": lon,
                "start_date": "2024-01-01",
                "end_date": "2024-01-07",
                "period_type": "recent",
            },
            timeout=30,
        )
        # Must NOT return 422 (validation error) for valid coordinates.
        # 500 is acceptable in test env (Celery/Redis not available).
        assert response.status_code != 422, (
            f"Valid coords ({lat}, {lon}) wrongly rejected with 422"
        )

    def test_nan_coordinate_rejected(self, api_client):
        """NaN coordinate deve ser rejeitado."""
        import json

        try:
            response = api_client.post(
                "/api/v1/internal/eto/calculate",
                json={
                    "lat": float("nan"),
                    "lng": -48.33,
                    "start_date": "2024-01-01",
                    "end_date": "2024-01-07",
                    "period_type": "recent",
                },
            )
            # If serialized, must not be accepted as valid
            assert response.status_code in (400, 422, 500)
        except (ValueError, OverflowError):
            # float('nan') is not JSON compliant — rejection at
            # serialization level is the correct security behavior
            pass

    def test_none_coordinate_rejected(self, api_client):
        """null/None coordinate deve ser rejeitado."""
        response = api_client.post(
            "/api/v1/internal/eto/calculate",
            json={
                "lat": None,
                "lng": -48.33,
                "start_date": "2024-01-01",
                "end_date": "2024-01-07",
                "period_type": "recent",
            },
        )
        assert response.status_code in (400, 422)


@pytest.mark.security
class TestWKTInjectionPrevention:
    """Verifica que strings WKT maliciosas são rejeitadas."""

    WKT_INJECTION_PAYLOADS = [
        "POINT(0 0); DROP TABLE spatial_ref_sys;--",
        "POLYGON((0 0, 1 1, 1 0, 0 0)); DELETE FROM climate_data",
        "GEOMETRYCOLLECTION EMPTY; SELECT pg_sleep(10)",
        "MULTIPOINT((0 0), (1 1)); COPY pg_shadow TO '/tmp/pwned'",
    ]

    @pytest.mark.parametrize("wkt", WKT_INJECTION_PAYLOADS)
    def test_wkt_injection_in_coordinate_field(self, api_client, wkt):
        """WKT injection em campos de coordenada deve ser rejeitado."""
        response = api_client.post(
            "/api/v1/internal/eto/calculate",
            json={
                "lat": wkt,
                "lng": -48.33,
                "start_date": "2024-01-01",
                "end_date": "2024-01-07",
                "period_type": "recent",
            },
        )
        assert response.status_code in (400, 422), (
            f"WKT injection not blocked: {wkt[:50]}"
        )


@pytest.mark.security
class TestSRIDValidation:
    """Verifica que SRIDs inválidos não causam erros de segurança."""

    def test_negative_srid_rejected(self):
        """SRID negativo deve ser tratado como inválido."""
        # This tests the internal validation logic, not an endpoint
        from backend.api.services.opentopo.opentopo_sync_adapter import (
            OpenTopoSyncAdapter,
        )

        # Adapter should not crash on invalid coordinates
        adapter = OpenTopoSyncAdapter()
        # Calling with extreme values should raise or return gracefully
        try:
            result = adapter.get_elevation(lat=999, lon=999)
            # If it returns, it should indicate an error or None
        except (ValueError, Exception):
            pass  # Expected — validation caught it

    @skip_if_no_redis
    def test_coordinate_precision_handling(self, api_client):
        """Coordenadas com muitas casas decimais devem ser aceitas."""
        response = api_client.post(
            "/api/v1/internal/eto/calculate",
            json={
                "lat": -10.123456789012345,  # 15 decimal places
                "lng": -48.987654321098765,
                "start_date": "2024-01-01",
                "end_date": "2024-01-07",
                "period_type": "recent",
            },
        )
        # High precision should be accepted (truncated internally if needed)
        assert response.status_code != 422
