"""
Aplicação Dash do ETo Calculator (integrada ao Backend FastAPI).

Exports:
- initialize_dash_app(): Factory para criar instância Dash
- app, server: Instâncias globais para montagem no backend

Integração:
- Montada pelo backend/main.py via mount_dash()
- Backend roda em http://localhost:8000
- Dash frontend em http://localhost:8000/
- API em http://localhost:8000/api/v1/...
"""

import os
import sys
from pathlib import Path

# Garantir que o projeto raiz está no path (necessário para imports absolutos)
_project_root = Path(__file__).parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from frontend.core.dash_app_config import create_dash_app
from frontend.core.base_layout import create_base_layout
from frontend.callbacks.registry import register_all_callbacks
from config.logging_config import setup_logging, get_logger

# Setup logging (Loguru com rotação, compressão, retenção)
setup_logging(log_level="INFO", log_dir="logs", json_logs=False)
logger = get_logger()


def initialize_dash_app(standalone=False):
    """
    Inicializa a aplicação Dash com layout e callbacks.

    Called by:
        - backend/main.py → mount_dash() (modo integrado, standalone=False)
        - __main__ (modo standalone para desenvolvimento, standalone=True)

    Args:
        standalone: Se True, configura Flask para servir assets diretamente

    Returns:
        tuple: (app, server) - Instâncias Dash e Flask
    """
    try:
        logger.info("🚀 Initializing Dash Frontend...")

        # Criar instância Dash + Flask server
        app, server = create_dash_app(standalone=standalone)

        # Configurar layout base (navbar, stores, footer, page-content)
        app.layout = create_base_layout()

        # Registrar todos os callbacks (home, eto, navigation, session, etc.)
        register_all_callbacks(app)

        mode = "standalone" if standalone else "integrado (FastAPI)"
        logger.info(
            f"✅ Dash Frontend initialized successfully (modo: {mode})"
        )

        return app, server

    except Exception as e:
        logger.error(f"❌ Falha ao inicializar Dash Frontend: {e}")
        raise


# =============================================================================
# Instância global - criada quando o módulo é importado
# Usado por: backend/main.py → mount_dash() → from frontend.app import app
# =============================================================================
standalone_mode = os.getenv("EVA_FRONTEND_STANDALONE") == "1"
app, server = initialize_dash_app(standalone=standalone_mode)


if __name__ == "__main__":
    # Modo standalone para desenvolvimento (sem FastAPI)
    logger.info("=" * 60)
    logger.info("🌦️  Starting EVAonline Frontend (Standalone Mode)")
    logger.info("=" * 60)
    logger.info("Frontend: http://localhost:8050")
    logger.info("API Backend: http://localhost:8000 (deve estar rodando)")
    logger.info("=" * 60)

    # Re-inicializar com configuração standalone (serve assets via Flask)
    app, server = initialize_dash_app(standalone=True)

    server.run(host="0.0.0.0", port=8050, debug=False, threaded=True)
