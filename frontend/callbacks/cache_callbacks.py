"""
Callbacks para gerenciamento de sessão de usuários anônimos.

Cada aba/janela do navegador recebe um session_id único via sessionStorage.
O backend usa esse ID para:
- Rastrear tarefas Celery por usuário
- Isolar resultados em ambientes multi-usuário
- Associar dados de cache Redis à sessão

NOTA: O cache de dados climáticos é gerenciado pelo Redis no backend
(ClimateCacheService). O frontend NÃO precisa cachear dados climáticos.
"""

import logging
import uuid

from dash import Input, Output, State
from dash.exceptions import PreventUpdate

logger = logging.getLogger(__name__)


def register_cache_callbacks(app):
    """Registra callbacks de gerenciamento de sessão."""

    @app.callback(
        Output("app-session-id", "data"),
        Input("url", "pathname"),
        State("app-session-id", "data"),
    )
    def initialize_session_id(pathname, existing_session_id):
        """
        Inicializa session ID único para este usuário/aba.

        Cada aba do navegador terá um ID único (sessionStorage).
        Isso permite identificar cada usuário anônimo no backend.

        Formato: "sess_<uuid_hex>" (ex: "sess_a1b2c3d4e5f6...")
        """
        if existing_session_id:
            return existing_session_id

        new_session_id = f"sess_{uuid.uuid4().hex}"
        logger.info(f"🆕 Nova sessão iniciada: {new_session_id}")
        return new_session_id
