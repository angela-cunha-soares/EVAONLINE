"""
Per-User Rate Limiter for ETo Calculations.

Limita o número de cálculos por usuário por dia usando Redis.
Identifica usuários por IP + visitor_id (localStorage do navegador).
Protege contra abuso e uso excessivo das APIs externas.

Dual identification:
- IP: protege contra abuso em nível de rede
- visitor_id: granularidade por navegador (ex: vários alunos no mesmo IP)
- Ambos são verificados; o mais restritivo prevalece

Limits:
- Dashboard modes (current/forecast): 30/day per user
- Historical mode (email): 10/day per user
- Global: 50/day per user across all modes
"""

from datetime import datetime
from typing import Optional

from loguru import logger
from redis import Redis

from config.settings.app_config import get_settings

settings = get_settings()

# Per-IP daily limits
CALC_LIMITS = {
    "dashboard_current": 30,   # Dashboard: 30 cálculos/dia por IP
    "dashboard_forecast": 30,  # Dashboard: 30 cálculos/dia por IP
    "historical_email": 10,    # Histórico (email): 10/dia por IP
    "global": 50,              # Total geral: 50/dia por IP
}


def _get_redis() -> Redis:
    """Get Redis connection."""
    return Redis.from_url(settings.redis.redis_url, decode_responses=True)


def _get_key(identifier: str, mode: str) -> str:
    """Build Redis key for rate limiting."""
    today = datetime.now().strftime("%Y-%m-%d")
    return f"calc_limit:{identifier}:{mode}:{today}"


def _check_identifier_limit(
    redis: Redis,
    identifier: str,
    identifier_type: str,
    mode: str,
) -> tuple[bool, Optional[str]]:
    """
    Check limits for a single identifier (IP or visitor_id).

    Returns:
        (allowed, error_message)
    """
    # 1. Check mode-specific limit
    mode_key = _get_key(identifier, mode)
    mode_usage_raw = redis.get(mode_key)
    mode_usage = int(mode_usage_raw) if mode_usage_raw else 0
    mode_limit = CALC_LIMITS.get(mode, 30)

    if mode_usage >= mode_limit:
        logger.warning(
            f"🚫 Rate limit exceeded: {identifier_type}={identifier} "
            f"mode={mode} usage={mode_usage}/{mode_limit}"
        )
        return False, (
            f"Daily limit reached for this mode ({mode_limit} calculations/day). "
            f"Try again tomorrow."
        )

    # 2. Check global limit
    global_key = _get_key(identifier, "global")
    global_usage_raw = redis.get(global_key)
    global_usage = int(global_usage_raw) if global_usage_raw else 0
    global_limit = CALC_LIMITS["global"]

    if global_usage >= global_limit:
        logger.warning(
            f"🚫 Global rate limit exceeded: {identifier_type}={identifier} "
            f"usage={global_usage}/{global_limit}"
        )
        return False, (
            f"Daily calculation limit reached ({global_limit}/day). "
            f"Try again tomorrow."
        )

    return True, None


def check_calculation_limit(
    client_ip: str,
    mode: str = "dashboard_current",
    visitor_id: Optional[str] = None,
) -> tuple[bool, Optional[str]]:
    """
    Check if user has remaining calculation quota.

    Uses dual identification: IP + visitor_id.
    Both are checked; the most restrictive one prevails.
    This provides:
    - IP: network-level abuse protection
    - visitor_id: per-browser granularity (e.g. university lab)

    Args:
        client_ip: IP address of the client
        mode: Operation mode
        visitor_id: Unique browser identifier (from localStorage)

    Returns:
        (allowed, error_message) - True if allowed, False with message if blocked
    """
    try:
        redis = _get_redis()

        # 1. Check IP-based limits
        allowed, msg = _check_identifier_limit(redis, client_ip, "IP", mode)
        if not allowed:
            return False, msg

        # 2. Check visitor_id-based limits (if provided)
        if visitor_id:
            vid_key = f"vid:{visitor_id}"  # Prefix to distinguish from IPs
            allowed, msg = _check_identifier_limit(
                redis, vid_key, "visitor_id", mode
            )
            if not allowed:
                return False, msg

        return True, None

    except Exception as e:
        # If Redis fails, allow the request (fail open)
        logger.error(f"Rate limiter error: {e}")
        return True, None


def track_calculation(
    client_ip: str,
    mode: str = "dashboard_current",
    visitor_id: Optional[str] = None,
) -> int:
    """
    Increment calculation counter for IP and visitor_id.

    Call this AFTER successfully dispatching the Celery task.

    Args:
        client_ip: IP address of the client
        mode: Operation mode
        visitor_id: Unique browser identifier

    Returns:
        Current global usage count for this IP today
    """
    try:
        redis = _get_redis()
        ttl = 86400 * 2  # 48h TTL

        # Track IP
        mode_key = _get_key(client_ip, mode)
        redis.incr(mode_key)
        redis.expire(mode_key, ttl)

        global_key = _get_key(client_ip, "global")
        global_usage = int(redis.incr(global_key))
        redis.expire(global_key, ttl)

        # Track visitor_id (if provided)
        if visitor_id:
            vid_key = f"vid:{visitor_id}"
            vid_mode_key = _get_key(vid_key, mode)
            redis.incr(vid_mode_key)
            redis.expire(vid_mode_key, ttl)

            vid_global_key = _get_key(vid_key, "global")
            redis.incr(vid_global_key)
            redis.expire(vid_global_key, ttl)

        logger.info(
            f"📊 Calc tracked: IP={client_ip} visitor={visitor_id or 'N/A'} "
            f"mode={mode} global_usage={global_usage}/{CALC_LIMITS['global']}"
        )

        return global_usage

    except Exception as e:
        logger.error(f"Track calculation error: {e}")
        return 0


def get_remaining_calculations(
    client_ip: str,
    mode: str = "dashboard_current",
) -> dict:
    """
    Get remaining calculation quota for an IP.

    Returns:
        Dict with remaining quotas
    """
    try:
        redis = _get_redis()

        mode_key = _get_key(client_ip, mode)
        mode_usage_raw = redis.get(mode_key)
        mode_usage = int(mode_usage_raw) if mode_usage_raw else 0
        mode_limit = CALC_LIMITS.get(mode, 30)

        global_key = _get_key(client_ip, "global")
        global_usage_raw = redis.get(global_key)
        global_usage = int(global_usage_raw) if global_usage_raw else 0

        return {
            "mode": mode,
            "mode_used": mode_usage,
            "mode_limit": mode_limit,
            "mode_remaining": max(0, mode_limit - mode_usage),
            "global_used": global_usage,
            "global_limit": CALC_LIMITS["global"],
            "global_remaining": max(0, CALC_LIMITS["global"] - global_usage),
        }

    except Exception as e:
        logger.error(f"Get remaining error: {e}")
        return {
            "mode": mode,
            "mode_remaining": -1,
            "global_remaining": -1,
        }
