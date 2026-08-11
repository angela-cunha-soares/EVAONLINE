"""
Result-file storage with expiring, tokenized download links.

Historical-mode results are saved to disk and served through a random,
unguessable token. Metadata (token -> file info) lives in Redis with a TTL
equal to the download window (default 48h), so links expire on their own.
A periodic cleanup removes orphaned files whose metadata has expired.

Design notes:
- The file on disk is named ``<token><ext>`` so the token is recoverable
  from the filename during cleanup.
- ``resolve()`` returns metadata only while the Redis key is alive AND the
  file still exists; otherwise the link is treated as expired/invalid.
"""

import json
import os
import secrets
import time
from typing import Optional

from loguru import logger
from redis import Redis

from config.settings.app_config import get_settings

_KEY_PREFIX = "download:"


def _redis() -> Redis:
    return Redis.from_url(get_settings().redis.redis_url, decode_responses=True)


def _storage_dir() -> str:
    d = get_settings().RESULTS_STORAGE_DIR
    os.makedirs(d, exist_ok=True)
    return d


def _ttl_seconds() -> int:
    return int(get_settings().DOWNLOAD_TTL_HOURS) * 3600


def _safe_ext(filename: str) -> str:
    """Return a safe extension (e.g. '.csv', '.xlsx') from a filename."""
    ext = os.path.splitext(filename or "")[1].lower()
    if ext and all(c.isalnum() or c == "." for c in ext) and len(ext) <= 8:
        return ext
    return ".dat"


def save_result(
    data: bytes,
    filename: str,
    email: str,
    ttl_seconds: Optional[int] = None,
) -> str:
    """
    Persist ``data`` and register a download token.

    Args:
        data: file content (bytes)
        filename: original filename (used for the download name + extension)
        email: requester email (for optional binding / auditing)
        ttl_seconds: override the default TTL

    Returns:
        The download token (opaque, URL-safe).
    """
    ttl = ttl_seconds if ttl_seconds is not None else _ttl_seconds()
    token = secrets.token_urlsafe(32)
    ext = _safe_ext(filename)
    path = os.path.join(_storage_dir(), f"{token}{ext}")

    with open(path, "wb") as fh:
        fh.write(data)

    meta = {
        "path": path,
        "filename": filename or f"result{ext}",
        "email": (email or "").strip().lower(),
        "size": len(data),
        "created_at": int(time.time()),
        "expires_at": int(time.time()) + ttl,
    }
    redis = _redis()
    redis.set(_KEY_PREFIX + token, json.dumps(meta), ex=ttl)
    logger.info(
        f"💾 Result stored: token={token[:8]}… size={len(data)}B "
        f"ttl={ttl}s file={os.path.basename(path)}"
    )
    return token


def resolve(token: str) -> Optional[dict]:
    """Return metadata for a live token, or None if expired/invalid."""
    if not token:
        return None
    try:
        raw = _redis().get(_KEY_PREFIX + token)
        if not raw:
            return None
        meta = json.loads(raw)
        if not os.path.exists(meta.get("path", "")):
            return None
        return meta
    except Exception as exc:
        logger.error(f"resolve token error: {exc}")
        return None


def delete(token: str) -> bool:
    """Remove a token's file and metadata."""
    try:
        redis = _redis()
        raw = redis.get(_KEY_PREFIX + token)
        if raw:
            meta = json.loads(raw)
            p = meta.get("path")
            if p and os.path.exists(p):
                os.remove(p)
        redis.delete(_KEY_PREFIX + token)
        return True
    except Exception as exc:
        logger.error(f"delete token error: {exc}")
        return False


def cleanup_expired() -> int:
    """
    Remove orphaned files whose metadata has expired.

    Redis expires the metadata automatically; this deletes the leftover files
    on disk that no longer have a live token. Returns the number removed.
    """
    removed = 0
    try:
        redis = _redis()
        directory = _storage_dir()
        for name in os.listdir(directory):
            path = os.path.join(directory, name)
            if not os.path.isfile(path):
                continue
            token = os.path.splitext(name)[0]
            if not redis.exists(_KEY_PREFIX + token):
                try:
                    os.remove(path)
                    removed += 1
                except OSError as exc:  # pragma: no cover
                    logger.debug(f"cleanup could not remove {name}: {exc}")
        if removed:
            logger.info(f"🧹 Cleanup removed {removed} expired result file(s)")
    except Exception as exc:  # pragma: no cover
        logger.error(f"cleanup_expired error: {exc}")
    return removed
