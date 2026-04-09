"""
===========================================
LOGGING CONFIGURATION - EVAonline
===========================================
Configuração centralizada de logging usando Loguru.
"""

import sys
from pathlib import Path
from typing import Any, Dict, Optional

from loguru import logger


class LoggingConfig:
    """Configuração centralizada de logging para a aplicação."""

    def __init__(
        self,
        log_level: str = "INFO",
        log_dir: str = "logs",
        rotation: str = "00:00",
        retention: str = "30 days",
        compression: str = "zip",
        json_logs: bool = False,
    ) -> None:
        """
        Inicializa a configuração de logging.

        Args:
            log_level: Nível de log (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            log_dir: Diretório onde os logs serão salvos
            rotation: Quando rotacionar os logs (ex: "00:00", "500 MB")
            retention: Quanto tempo manter logs antigos
            compression: Formato de compressão para logs antigos
            json_logs: Se True, gera logs em formato JSON
        """
        self.log_level = log_level
        self.log_dir = Path(log_dir)
        self.rotation = rotation
        self.retention = retention
        self.compression = compression
        self.json_logs = json_logs

        # Criar diretório de logs se não existir
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def setup(self) -> None:
        """Configura o logger com as definições especificadas."""
        # Remover handlers padrão
        logger.remove()

        # Configurar formato de log
        if self.json_logs:
            log_format = self._get_json_format()
        else:
            log_format = self._get_colored_format()

        # Handler para console (stderr)
        logger.add(
            sys.stderr,
            format=log_format,
            level=self.log_level,
            colorize=not self.json_logs,
            backtrace=True,
            diagnose=True,
        )

        # Handler para arquivo geral
        logger.add(
            self.log_dir / "app_{time:YYYY-MM-DD}.log",
            format=log_format,
            level=self.log_level,
            rotation=self.rotation,
            retention=self.retention,
            compression=self.compression,
            backtrace=True,
            diagnose=True,
            enqueue=True,  # Thread-safe
        )

        # Handler para erros (separado)
        logger.add(
            self.log_dir / "error_{time:YYYY-MM-DD}.log",
            format=log_format,
            level="ERROR",
            rotation=self.rotation,
            retention=self.retention,
            compression=self.compression,
            backtrace=True,
            diagnose=True,
            enqueue=True,
        )

        # Handler para API requests (opcional)
        logger.add(
            self.log_dir / "api_{time:YYYY-MM-DD}.log",
            format=log_format,
            level="INFO",
            rotation=self.rotation,
            retention=self.retention,
            compression=self.compression,
            filter=lambda record: "api" in record["extra"],
            enqueue=True,
        )

        # Handler para Celery tasks (opcional)
        logger.add(
            self.log_dir / "celery_{time:YYYY-MM-DD}.log",
            format=log_format,
            level="INFO",
            rotation=self.rotation,
            retention=self.retention,
            compression=self.compression,
            filter=lambda record: "celery" in record["extra"],
            enqueue=True,
        )

        logger.info(f"Logging configurado - Nível: {self.log_level}, Diretório: {self.log_dir}")

    @staticmethod
    def _get_colored_format() -> str:
        """Retorna formato colorido para logs em console."""
        return (
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "<level>{message}</level>"
        )

    @staticmethod
    def _get_json_format() -> str:
        """Retorna formato JSON para logs estruturados."""
        return (
            '{{"timestamp": "{time:YYYY-MM-DD HH:mm:ss.SSS}", '
            '"level": "{level}", '
            '"module": "{name}", '
            '"function": "{function}", '
            '"line": {line}, '
            '"message": "{message}"}}'
        )


# ===========================================
# Contextualizadores para logging estruturado
# ===========================================


class LogContext:
    """Context managers para adicionar contexto aos logs."""

    @staticmethod
    def api_request(
        method: str,
        path: str,
        user_id: Optional[str] = None,
        request_id: Optional[str] = None,
    ) -> Any:
        """
        Contexto para requisições de API.

        Example:
            with LogContext.api_request("GET", "/api/eto", user_id="123"):
                logger.info("Processando requisição ETo")
        """
        return logger.contextualize(
            api=True,
            method=method,
            path=path,
            user_id=user_id,
            request_id=request_id,
        )

    @staticmethod
    def celery_task(task_name: str, task_id: str, args: Optional[Dict] = None) -> Any:
        """
        Contexto para tarefas Celery.

        Example:
            with LogContext.celery_task("calculate_eto", "abc-123"):
                logger.info("Executando cálculo ETo")
        """
        return logger.contextualize(
            celery=True,
            task_name=task_name,
            task_id=task_id,
            task_args=args,
        )

    @staticmethod
    def database_operation(operation: str, table: str, duration_ms: Optional[float] = None) -> Any:
        """
        Contexto para operações de banco de dados.

        Example:
            with LogContext.database_operation("INSERT", "eto_results"):
                logger.info("Inserindo resultado ETo")
        """
        return logger.contextualize(
            database=True,
            operation=operation,
            table=table,
            duration_ms=duration_ms,
        )


# ===========================================
# Funções auxiliares
# ===========================================


def setup_logging(
    log_level: str = "INFO",
    log_dir: str = "logs",
    json_logs: bool = False,
) -> None:
    """
    Configura o logging da aplicação.

    Args:
        log_level: Nível de log
        log_dir: Diretório de logs
        json_logs: Usar formato JSON
    """
    config = LoggingConfig(
        log_level=log_level,
        log_dir=log_dir,
        json_logs=json_logs,
    )
    config.setup()


def get_logger() -> Any:
    """Retorna a instância do logger."""
    return logger


# ===========================================
# Decoradores para logging automático
# ===========================================


def log_execution_time(func: Any) -> Any:
    """
    Decorator para logar tempo de execução de funções.

    Example:
        @log_execution_time
        def calculate_something():
            pass
    """
    import functools
    import time

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            duration = (time.time() - start_time) * 1000
            logger.info(f"{func.__name__} executado em {duration:.2f}ms")
            return result
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            logger.error(f"{func.__name__} falhou após {duration:.2f}ms: {e}")
            raise

    return wrapper


def log_async_execution_time(func: Any) -> Any:
    """
    Decorator para logar tempo de execução de funções assíncronas.

    Example:
        @log_async_execution_time
        async def fetch_data():
            pass
    """
    import functools
    import time

    @functools.wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        start_time = time.time()
        try:
            result = await func(*args, **kwargs)
            duration = (time.time() - start_time) * 1000
            logger.info(f"{func.__name__} executado em {duration:.2f}ms")
            return result
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            logger.error(f"{func.__name__} falhou após {duration:.2f}ms: {e}")
            raise

    return wrapper
