"""
⚠️ DEPRECATED: Use config.logging_config instead.

This module is kept for backward compatibility only.
New code should use:
    from config.logging_config import setup_logging, get_logger
"""
import os
import sys

from loguru import logger


def configure_logging(log_file: str = "logs/app.log", level: str = "INFO"):
    """
    Configura o logging com Loguru para a aplicação EVAonline.

    Parâmetros:
    - log_file: Caminho para o arquivo de log (padrão: logs/app.log)
    - level: Nível de logging (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    # Criar diretório de logs, se não existir
    # Esta linha é robusta e garante que o caminho do log seja válido.
    os.makedirs(os.path.dirname(log_file), exist_ok=True)

    # Remover o handler padrão do Loguru (console) para evitar duplicação de logs.
    # Esta é uma prática recomendada para ter controle total sobre os handlers.
    logger.remove()

    # Configurar logging para o console (stdout) com um formato limpo.
    # Ideal para desenvolvimento e para ver logs em tempo real em contêineres Docker.
    logger.add(
        sys.stdout,
        level=level,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    )

    # Configurar logging para arquivo com rotação, retenção e compressão.
    logger.add(
        log_file,
        level=level,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        rotation="10 MB",  # Rotaciona o arquivo quando atingir 10 MB
        retention="7 days",  # Mantém logs dos últimos 7 dias
        compression="zip",  # Comprime os arquivos de log antigos para economizar espaço
    )

    logger.info("Logging configurado com sucesso")
