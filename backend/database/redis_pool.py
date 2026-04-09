"""
Pool centralizado de conexões Redis com gerenciamento de ciclo de vida.

Benefício: Reutiliza conexões, evita esgotamento de recursos.
"""

import os

import redis
from loguru import logger

_redis_pool: redis.ConnectionPool | None = None
_redis_client: redis.Redis | None = None


def initialize_redis_pool() -> redis.Redis:
    """
    Inicializa pool de conexões Redis.

    Usa REDIS_URL da variável de ambiente ou configurações seguras.

    Returns:
        Cliente Redis com pool
    """
    global _redis_pool, _redis_client

    if _redis_client is not None:
        return _redis_client

    # Configurações seguras do Redis
    redis_host = os.getenv("REDIS_HOST", "redis")
    redis_port = int(os.getenv("REDIS_PORT", "6379"))
    redis_password = os.getenv("REDIS_PASSWORD")
    redis_db = int(os.getenv("REDIS_DB", "0"))

    # Configurações de pool otimizadas
    max_connections = int(os.getenv("REDIS_MAX_CONNECTIONS", "50"))
    socket_timeout = int(os.getenv("REDIS_SOCKET_TIMEOUT", "10"))
    socket_connect_timeout = int(os.getenv("REDIS_SOCKET_CONNECT_TIMEOUT", "5"))

    try:
        _redis_pool = redis.ConnectionPool(
            host=redis_host,
            port=redis_port,
            password=redis_password,
            db=redis_db,
            max_connections=max_connections,
            socket_timeout=socket_timeout,
            socket_connect_timeout=socket_connect_timeout,
            retry_on_timeout=True,
            health_check_interval=30,
            decode_responses=True,  # Retorna strings em vez de bytes
        )

        _redis_client = redis.Redis(connection_pool=_redis_pool)

        # Teste de conexão
        _redis_client.ping()
        logger.info("✅ Redis pool initialized and connected")

        return _redis_client

    except Exception as e:
        logger.error(f"❌ Redis connection failed: {e}")
        raise


def get_redis_client() -> redis.Redis:
    """
    Obtém cliente Redis com pool compartilhado.

    Inicializa se ainda não foi inicializado.

    Returns:
        Cliente Redis

    Raises:
        Exception: Se conexão falhar
    """
    global _redis_client

    if _redis_client is None:
        return initialize_redis_pool()

    return _redis_client


def close_redis() -> None:
    """Fecha pool de Redis e libera recursos."""
    global _redis_pool, _redis_client

    if _redis_client:
        try:
            _redis_client.close()
            logger.info("✅ Redis pool closed")
        except Exception as e:
            logger.warning(f"Error closing Redis: {e}")

    _redis_pool = None
    _redis_client = None
