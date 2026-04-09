#!/bin/bash

# Script de health check para diferentes serviços EVAonline
# Adaptado para cada tipo de serviço (api, worker, beat, flower)

SERVICE=${SERVICE:-api}
REDIS_HOST=${REDIS_HOST:-redis}
REDIS_PORT=${REDIS_PORT:-6379}

case "$SERVICE" in
    "api")
        # Health check para API: verifica endpoint HTTP
        curl -f http://localhost:8000/api/v1/health || exit 1
        ;;
    "worker"|"worker-dev"|"worker-eto")
        # Health check para Celery Worker: verifica conexão com Redis
        nc -z $REDIS_HOST $REDIS_PORT || exit 1
        ;;
    "beat")
        # Health check para Celery Beat: verifica conexão com Redis
        nc -z $REDIS_HOST $REDIS_PORT || exit 1
        ;;
    "flower")
        # Health check para Flower: verifica porta 5555
        curl -f http://localhost:5555/api/workers || exit 1
        ;;
    *)
        # Default: healthcheck da API
        curl -f http://localhost:8000/api/v1/health || exit 1
        ;;
esac
