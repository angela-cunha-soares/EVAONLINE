"""
Celery tasks para EVAonline.

Tasks disponíveis:
- eto_calculation: Cálculo ETo com progresso em tempo real
- data_download: Download histórico + envio por email
"""

from .eto_calculation import calculate_eto_task
from .data_download import process_historical_download
from .download_cleanup import cleanup_expired_downloads

__all__ = [
    "calculate_eto_task",
    "process_historical_download",
    "cleanup_expired_downloads",
]
