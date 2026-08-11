"""
Abuse monitoring and alerting.

Counts rate-limit blocks per identifier per day. When a single identifier
crosses ABUSE_ALERT_THRESHOLD blocks in a day, an alert is emitted once
(deduped) to the logs and, if configured, to a webhook (Discord/Slack).

All operations are best-effort and never raise into the request path.
"""

from datetime import datetime, timezone

from loguru import logger
from redis import Redis

from config.settings.app_config import get_settings


def _redis() -> Redis:
    return Redis.from_url(get_settings().redis.redis_url, decode_responses=True)


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _send_webhook(message: str) -> None:
    url = (get_settings().ALERT_WEBHOOK_URL or "").strip()
    if not url:
        return
    try:
        import requests

        # Discord expects {"content": ...}; Slack accepts {"text": ...}.
        requests.post(
            url, json={"content": message, "text": message}, timeout=5
        )
    except Exception as exc:  # pragma: no cover - network best-effort
        logger.debug(f"Abuse webhook failed: {exc}")


def record_block(
    identifier_type: str,
    identifier: str,
    mode: str,
    reason: str = "rate_limit",
) -> None:
    """
    Record a blocked/denied request and alert once per day if the same
    identifier crosses the configured threshold.
    """
    try:
        settings = get_settings()
        redis = _redis()
        day = _today()
        key = f"abuse:{identifier_type}:{identifier}:{day}"
        count = int(redis.incr(key))
        redis.expire(key, 86400 * 2)

        logger.warning(
            f"⚠️ Abuse block: {identifier_type}={identifier} mode={mode} "
            f"reason={reason} count_today={count}"
        )

        if count == settings.ABUSE_ALERT_THRESHOLD:
            alert_key = f"abuse_alert:{identifier_type}:{identifier}:{day}"
            # Only alert once per identifier per day.
            if redis.set(alert_key, "1", nx=True, ex=86400 * 2):
                msg = (
                    f"🚨 EVAonline abuse alert: {identifier_type}="
                    f"{identifier} reached {count} blocked requests today "
                    f"(mode={mode}, reason={reason})."
                )
                logger.error(msg)
                _send_webhook(msg)
    except Exception as exc:  # pragma: no cover - never break the request path
        logger.debug(f"record_block error: {exc}")
