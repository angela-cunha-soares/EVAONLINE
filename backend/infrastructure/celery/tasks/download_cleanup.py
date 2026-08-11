"""
Periodic cleanup of expired result-download files.

Redis expires the download metadata automatically after DOWNLOAD_TTL_HOURS;
this task removes the leftover files on disk whose metadata is gone.
Scheduled hourly via Celery Beat.
"""

from loguru import logger

from backend.infrastructure.celery.celery_config import celery_app


@celery_app.task(name="storage.cleanup_expired_downloads")
def cleanup_expired_downloads() -> int:
    """Delete orphaned (expired) result files. Returns count removed."""
    from backend.infrastructure.storage.result_files import cleanup_expired

    removed = cleanup_expired()
    logger.info(f"🧹 cleanup_expired_downloads removed {removed} file(s)")
    return removed
