"""
Registro centralizado de todos callbacks.

Ordem de registro é importante:
1. home_callbacks: Mapa, clique, seleção de coordenadas
2. layer_control_callbacks: Camadas do mapa, sidebar, input manual
3. navigation_callbacks: Roteamento entre páginas
4. navbar_callbacks: Tradução PT/EN, links ativos
5. cache_callbacks: Session ID (DEVE vir ANTES de eto e visitor)
6. eto_callbacks: Cálculo de ETo (usa session_id)
7. visitor_callbacks: Contador de visitantes (usa session_id)
"""

import logging

logger = logging.getLogger(__name__)


def register_all_callbacks(app):
    """Registra todos callbacks ativos na ordem correta de dependências."""
    try:
        # ① Callback principal da home (mapa leaflet + coordenadas)
        from .home_callbacks import (
            register_home_callbacks,
            register_layer_control_callbacks,
        )

        register_home_callbacks(app)
        register_layer_control_callbacks(app)

        # ② Callbacks de navegação (rotas entre páginas)
        from .navigation_callbacks import register_navigation_callbacks

        register_navigation_callbacks(app)

        # ③ Callbacks da navbar (tradução PT/EN, links ativos)
        from . import navbar_callbacks  # noqa: F401

        # ④ Callbacks de sessão (gera app-session-id)
        # DEVE ser registrado ANTES de eto_callbacks e visitor_callbacks
        from .cache_callbacks import register_cache_callbacks

        register_cache_callbacks(app)

        # ⑤ Callbacks da página ETo (usa app-session-id)
        from . import eto_callbacks  # noqa: F401

        # ⑥ Callbacks do contador de visitantes (usa app-session-id)
        from . import visitor_callbacks  # noqa: F401

        logger.info("✅ Todos os 6 módulos de callbacks registrados!")

    except Exception as e:
        logger.error(f"❌ Erro ao registrar callbacks: {e}")
        raise
