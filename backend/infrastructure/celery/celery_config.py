"""
Configuração do Celery para tarefas assíncronas do EVAonline.
Centraliza todas as configurações do Celery para a aplicação.
"""

import json
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from celery import Celery
from celery.schedules import crontab
from dotenv import load_dotenv
from kombu import Queue
from redis import Redis

from backend.api.middleware.prometheus_metrics import (
    CELERY_TASK_DURATION,
    CELERY_TASKS_TOTAL,
)

# from config.settings import get_settings
from config.settings.app_config import (
    get_celery_broker_url,
    get_celery_result_backend,
    get_legacy_settings,
)

# Carregar .env explicitamente para garantir que variáveis estejam disponíveis
import os

env_path = Path(__file__).resolve().parents[3] / ".env"
if env_path.exists():
    load_dotenv(env_path, override=True)  # override=True força recarregar
    print(f"✅ .env carregado: {env_path}")

    # DEBUG: Printar variáveis críticas do Redis
    pwd_set = bool(os.getenv("REDIS_PASSWORD"))
    broker_set = bool(os.getenv("CELERY_BROKER_URL"))
    print(f"🔍 REDIS_PASSWORD definido: {pwd_set}")
    print(f"🔍 CELERY_BROKER_URL definido: {broker_set}")

# Carregar configurações (compatibilidade/URLs do Celery)
# Priorizar CELERY_BROKER_URL do .env diretamente
broker_url = os.getenv("CELERY_BROKER_URL") or get_celery_broker_url()
result_backend = (
    os.getenv("CELERY_RESULT_BACKEND") or get_celery_result_backend()
)
print(f"🔍 DEBUG Celery - broker_url: {broker_url[:50]}...")
print(f"🔍 DEBUG Celery - result_backend: {result_backend[:50]}...")
legacy_settings = get_legacy_settings()

# Inicializar Celery
celery_app = Celery(
    "evaonline",
    broker=broker_url,
    backend=result_backend,
)

# Métricas Prometheus
# As métricas são importadas do main.py para evitar duplicação


# Classe base para tarefas com monitoramento e progresso
class MonitoredProgressTask(celery_app.Task):
    def publish_progress(self, task_id, progress, status="PROGRESS"):
        """Publica progresso no canal Redis para WebSocket."""
        try:
            # Usar broker_url configurado (compatibilidade)
            redis_client = Redis.from_url(broker_url, decode_responses=True)
            redis_client.publish(
                f"task_status:{task_id}",
                json.dumps(
                    {
                        "status": status,
                        "info": progress,
                        "timestamp": datetime.now().isoformat(),
                    }
                ),
            )
            redis_client.close()
        except Exception as e:
            # Não bloqueia a task se falhar publicação de progresso
            import logging

            logging.warning(f"Falha ao publicar progresso: {e}")

    def __call__(self, *args, **kwargs):
        """Rastreia duração e status da tarefa para Prometheus."""
        import time

        start_time = time.time()
        try:
            result = super().__call__(*args, **kwargs)
            CELERY_TASKS_TOTAL.labels(
                task_name=self.name, status="SUCCESS"
            ).inc()
            return result
        except Exception:
            CELERY_TASKS_TOTAL.labels(
                task_name=self.name, status="FAILURE"
            ).inc()
            raise
        finally:
            CELERY_TASK_DURATION.labels(task_name=self.name).observe(
                time.time() - start_time
            )


# Definir classe base para todas as tarefas
celery_app.Task = MonitoredProgressTask

# Configurações principais
celery_app.conf.update(
    # Serialização
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    # Resultados - CRÍTICO para frontend ler via Redis
    result_extended=True,  # Salva metadados extras (status, result, etc)
    result_expires=3600,  # Expira em 1 hora
    task_track_started=True,  # Track quando task inicia
    task_ignore_result=False,  # NÃO ignorar resultados
    # Timezone
    timezone="America/Sao_Paulo",
    enable_utc=True,
    # Rotas e filas
    task_default_queue="general",
    task_routes={
        "backend.infrastructure.celery.tasks.calculate_eto_task": {
            "queue": "eto"
        },
        "backend.core.eto_calculation.*": {"queue": "eto_processing"},
        "backend.api.services.data_download.*": {"queue": "data_download"},
        "backend.api.services.openmeteo.*": {"queue": "elevation"},
        # REMOVIDO: backend.core.data_processing.data_fusion.*
        # (arquivo deletado em FASE 1-2)
    },
    task_queues=(
        Queue("general"),
        Queue("eto", routing_key="eto.#"),
        Queue("eto_processing"),
        Queue("data_download"),
        Queue("data_processing"),
        Queue("elevation"),
    ),
)

# Configuração de tarefas periódicas
celery_app.conf.beat_schedule = {
    # Limpeza de cache antigo (02:00 BRT)
    "cleanup-old-climate-cache": {
        "task": "climate.cleanup_old_cache",
        "schedule": crontab(hour=2, minute=0),
    },
    # Pre-fetch cidades mundiais populares (03:00 BRT)
    "prefetch-nasa-popular-cities": {
        "task": "climate.prefetch_nasa_popular_cities",
        "schedule": crontab(hour=3, minute=0),
    },
    # Pre-fetch NWS Forecast USA (a cada 6 horas)
    "prefetch-nws-forecast-usa": {
        "task": "climate.prefetch_nws_forecast_usa_cities",
        # 00:00, 06:00, 12:00, 18:00
        "schedule": crontab(hour="*/6", minute=0),
    },
    # Pre-fetch NWS Stations USA (04:00 BRT diariamente)
    "prefetch-nws-stations-usa": {
        "task": "climate.prefetch_nws_stations_usa_cities",
        "schedule": crontab(hour=4, minute=0),
    },
    # Pre-fetch Open-Meteo Forecast (05:00 BRT diariamente)
    "prefetch-openmeteo-forecast": {
        "task": "climate.prefetch_openmeteo_forecast_popular_cities",
        "schedule": crontab(hour=5, minute=0),
    },
    # Pre-fetch Open-Meteo Archive (06:00 BRT aos domingos)
    "prefetch-openmeteo-archive": {
        "task": "climate.prefetch_openmeteo_archive_popular_cities",
        "schedule": crontab(hour=6, minute=0, day_of_week=0),  # Domingo
    },
    # Pre-fetch MET Norway Nordic (07:00 BRT diariamente)
    "prefetch-met-norway-nordic": {
        "task": "climate.prefetch_met_norway_nordic_cities",
        "schedule": crontab(hour=7, minute=0),  # Diário (Fair use)
    },
    # Estatísticas de cache (a cada hora)
    "generate-cache-stats": {
        "task": "climate.generate_cache_stats",
        "schedule": crontab(minute=0),  # Todo início de hora
    },
    # Sincronização de dados de visitantes (a cada hora)
    "sync-visitor-data": {
        "task": "backend.infrastructure.celery.tasks.sync_visitor_data",
        "schedule": crontab(minute=30),  # A cada 30 minutos
    },
    # Tasks legadas
    "cleanup-expired-data": {
        "task": (
            "backend.infrastructure.cache.celery_tasks.cleanup_expired_data"
        ),
        "schedule": crontab(hour=0, minute=0),  # 00:00 diariamente
    },
    "update-popular-ranking": {
        "task": (
            "backend.infrastructure.cache.celery_tasks.update_popular_ranking"
        ),
        "schedule": crontab(minute="*/10"),  # A cada 10 minutos
    },
}

# Descoberta automática de tarefas
celery_app.autodiscover_tasks(
    [
        "backend.infrastructure.cache.celery_tasks",
        "backend.infrastructure.cache.climate_tasks",
        "backend.infrastructure.celery.tasks",
        "backend.core.eto_calculation",
        "backend.api.services.data_download",
        "backend.api.services.openmeteo",
    ]
)
