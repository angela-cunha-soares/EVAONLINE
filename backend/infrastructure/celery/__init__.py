"""
Configuração do Celery.
"""

from backend.infrastructure.celery.celery_config import celery_app

__all__ = ["celery_app"]
