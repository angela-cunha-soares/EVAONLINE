"""
Pending historical requests (hybrid confirmation flow).

When a historical request arrives with an *unverified* email, the fully
resolved Celery task kwargs are stashed here, keyed by the same token used in
the confirmation email. When the user clicks the link, the request is consumed
and enqueued — so the click both verifies the email (30 days) and starts that
specific job. Short TTL (matches the verification token).
"""

import json
from typing import Optional

from loguru import logger
from redis import Redis

from config.settings.app_config import get_settings

_KEY_PREFIX = "pending_req:"
DEFAULT_TTL = 86400  # 24h - janela confortavel para o usuario clicar no link


def _redis() -> Redis:
    return Redis.from_url(get_settings().redis.redis_url, decode_responses=True)


def save(token: str, params: dict, ttl: int = DEFAULT_TTL) -> bool:
    """Store the pending request params under a token."""
    try:
        _redis().set(_KEY_PREFIX + token, json.dumps(params), ex=ttl)
        return True
    except Exception as exc:
        logger.error(f"pending_request.save error: {exc}")
        return False


def consume(token: str) -> Optional[dict]:
    """Return and delete the pending request for a token (one-time use)."""
    if not token:
        return None
    try:
        redis = _redis()
        # GETDEL e atomico (Redis 6.2+): elimina a corrida de dois cliques
        # simultaneos no link enfileirarem o mesmo job duas vezes.
        raw = redis.getdel(_KEY_PREFIX + token)
        if not raw:
            return None
        return json.loads(raw)
    except Exception as exc:
        logger.error(f"pending_request.consume error: {exc}")
        return None
