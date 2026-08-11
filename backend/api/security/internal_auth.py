"""
Shared-secret authentication for the internal calculation endpoint.

The `/api/v1/internal/*` routes are meant to be called ONLY by the Dash
server (server-side callback, via loopback). Nginx already blocks external
access to `/internal/`; this token is defense-in-depth so that even a caller
inside the Docker network cannot drive the calculation endpoint without the
secret.

Enforced only in production (so tests and local dev are unaffected).
"""

import hashlib
import hmac

from fastapi import Header, HTTPException, status
from loguru import logger

from config.settings.app_config import get_settings

INTERNAL_TOKEN_HEADER = "X-Internal-Token"


def get_internal_token() -> str:
    """
    Return the shared internal token.

    Uses INTERNAL_API_TOKEN if set, otherwise derives a stable token from
    SECRET_KEY so both the Dash server and the API agree without extra config.
    """
    settings = get_settings()
    token = (settings.INTERNAL_API_TOKEN or "").strip()
    if token:
        return token
    digest = hashlib.sha256(
        f"evaonline-internal:{settings.SECRET_KEY}".encode("utf-8")
    ).hexdigest()
    return digest


def _enforced() -> bool:
    """Only enforce in production (avoid breaking tests/local dev)."""
    return get_settings().ENVIRONMENT == "production"


def verify_internal_token(
    x_internal_token: str = Header(default=""),
) -> None:
    """
    FastAPI dependency: reject internal calls without the correct token.

    No-op outside production.
    """
    if not _enforced():
        return
    expected = get_internal_token()
    provided = (x_internal_token or "").strip()
    if not provided or not hmac.compare_digest(provided, expected):
        logger.warning("🚫 Internal endpoint called without a valid token")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden",
        )
