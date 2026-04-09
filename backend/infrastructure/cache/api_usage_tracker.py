"""
API Usage Tracker - Monitor daily API consumption.

Rastreia consumo diário de cada API climática e alerta
quando próximo dos limites.

Usage:
    from backend.infrastructure.cache.api_usage_tracker import (
        track_api_call,
        get_api_usage,
        check_api_quota,
    )

    # Registrar chamada
    track_api_call("nasa_power", requests_count=1)

    # Verificar uso atual
    usage = get_api_usage("nasa_power")

    # Verificar se tem quota disponível
    if not check_api_quota("nasa_power"):
        logger.warning("NASA POWER quota exceeded!")
"""

from datetime import datetime

from loguru import logger
from redis import Redis

from config.settings.app_config import get_settings

settings = get_settings()

# API Limits (requests per day)
API_LIMITS = {
    "nasa_power": 1000,  # NASA POWER: 1000 req/dia
    "nws_forecast": None,  # NWS: sem limite documentado
    "nws_stations": None,  # NWS: sem limite documentado
    "openmeteo_forecast": 10000,  # Open-Meteo: 10k/dia free tier
    "openmeteo_archive": 10000,  # Open-Meteo: 10k/dia free tier
    "met_norway": None,  # MET Norway: fair use (sem limite rígido)
    "opentopo": 1000,  # OpenTopoData: 1000 req/dia
    "resend": 100,  # Resend: 100 emails/dia (free tier)
}

# Warning thresholds (% of limit)
WARNING_THRESHOLD = 0.80  # 80%
CRITICAL_THRESHOLD = 0.95  # 95%


def _get_redis() -> Redis:
    """Get Redis connection."""
    return Redis.from_url(settings.redis.redis_url, decode_responses=True)


def _get_usage_key(api_name: str, date: str | None = None) -> str:
    """Get Redis key for API usage tracking."""
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")
    return f"api_usage:{api_name}:{date}"


def track_api_call(api_name: str, requests_count: int = 1) -> int:
    """
    Track API call and return current daily usage.

    Args:
        api_name: Nome da API ("nasa_power", "nws_forecast", etc.)
        requests_count: Número de requests feitos (padrão: 1)

    Returns:
        Número total de requests hoje para essa API

    Example:
        >>> usage = track_api_call("nasa_power")
        >>> print(f"NASA POWER usage today: {usage}/1000")
    """
    redis = _get_redis()
    key = _get_usage_key(api_name)

    # Incrementar contador
    current_usage_raw = redis.incr(key, requests_count)
    current_usage = int(current_usage_raw) if current_usage_raw else 0

    # Definir TTL de 48h (manter histórico 2 dias)
    redis.expire(key, 86400 * 2)

    # Verificar e alertar se próximo do limite
    limit = API_LIMITS.get(api_name)
    if limit is not None:
        usage_percent = current_usage / limit

        if usage_percent >= CRITICAL_THRESHOLD:
            logger.critical(
                f"🚨 {api_name.upper()} CRITICAL: {current_usage}/{limit} "
                f"requests ({usage_percent:.1%}) - NEAR LIMIT!"
            )
        elif usage_percent >= WARNING_THRESHOLD:
            logger.warning(
                f"⚠️ {api_name.upper()} WARNING: {current_usage}/{limit} "
                f"requests ({usage_percent:.1%})"
            )

    return current_usage


def get_api_usage(
    api_name: str,
    date: str | None = None,
) -> dict[str, int | float | None]:
    """
    Get current usage for an API.

    Args:
        api_name: Nome da API
        date: Data no formato YYYY-MM-DD (default: hoje)

    Returns:
        Dict com usage stats:
        {
            "requests_today": 245,
            "limit": 1000,
            "usage_percent": 24.5,
            "remaining": 755,
        }

    Example:
        >>> stats = get_api_usage("nasa_power")
        >>> print(f"Used: {stats['usage_percent']:.1f}%")
    """
    redis = _get_redis()
    key = _get_usage_key(api_name, date)

    # Get current usage
    usage_str = redis.get(key)
    current_usage = int(usage_str) if usage_str else 0

    # Get limit
    limit = API_LIMITS.get(api_name)

    # Calculate stats
    if limit is not None:
        usage_percent = (current_usage / limit) * 100
        remaining = limit - current_usage
    else:
        usage_percent = None
        remaining = None

    return {
        "requests_today": current_usage,
        "limit": limit,
        "usage_percent": usage_percent,
        "remaining": remaining,
    }


def check_api_quota(api_name: str, required_requests: int = 1) -> bool:
    """
    Check if API has enough quota for required requests.

    Args:
        api_name: Nome da API
        required_requests: Número de requests necessários

    Returns:
        True se tem quota disponível, False caso contrário

    Example:
        >>> if check_api_quota("nasa_power", required_requests=5):
        ...     data = fetch_from_nasa_power()
        ... else:
        ...     data = fetch_from_openmeteo()  # Fallback
    """
    limit = API_LIMITS.get(api_name)

    # Se não tem limite, sempre tem quota
    if limit is None:
        return True

    # Verificar uso atual
    stats = get_api_usage(api_name)
    current_usage = stats["requests_today"] or 0

    # Verificar se tem espaço
    return (current_usage + required_requests) <= limit


def get_all_api_usage() -> dict[str, dict]:
    """
    Get usage stats for all APIs.

    Returns:
        Dict com stats de todas APIs:
        {
            "nasa_power": {"requests_today": 245, "limit": 1000, ...},
            "nws_forecast": {...},
            ...
        }

    Example:
        >>> stats = get_all_api_usage()
        >>> for api_name, api_stats in stats.items():
        ...     print(f"{api_name}: {api_stats['requests_today']} requests")
    """
    return {
        api_name: get_api_usage(api_name) for api_name in API_LIMITS.keys()
    }


def reset_api_usage(api_name: str, date: str | None = None) -> None:
    """
    Reset usage counter for an API (admin/testing only).

    Args:
        api_name: Nome da API
        date: Data no formato YYYY-MM-DD (default: hoje)

    Example:
        >>> reset_api_usage("nasa_power")  # Reset today's counter
    """
    redis = _get_redis()
    key = _get_usage_key(api_name, date)
    redis.delete(key)
    logger.info(f"🔄 Reset usage counter for {api_name}")


# Exemplo de uso em clientes de API:
"""
# Em nasa_power_client.py, adicionar:

from backend.infrastructure.cache.api_usage_tracker import (
    track_api_call,
    check_api_quota,
)

async def get_daily_data(...):
    # Verificar quota antes de chamar API
    if not check_api_quota("nasa_power"):
        raise APIQuotaExceeded(
            "NASA POWER daily limit reached. Try again tomorrow."
        )
    
    # Chamar API
    response = await client.get(url)
    
    # Registrar chamada
    track_api_call("nasa_power")
    
    return process_response(response)
"""
