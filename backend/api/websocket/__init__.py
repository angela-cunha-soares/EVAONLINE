"""
WebSocket Module - EVAonline

Este módulo contém funcionalidades WebSocket para comunicação em tempo real
na aplicação EVAonline, principalmente para monitoramento de tarefas Celery.

COMPONENTS:
==========

WebSocket Services:
├── websocket_service - Serviço principal de WebSocket
│   ├── Task monitoring endpoints
│   ├── Redis pub/sub integration
│   ├── Timeout handling
│   └── Error management

FEATURES:
========

Real-time Task Monitoring:
- Monitoramento de tarefas Celery via WebSocket
- Atualizações em tempo real do progresso
- Notificações de conclusão/sucesso/falha
- Timeout automático (30 minutos padrão)

Redis Integration:
- Publicação de mensagens via Redis pub/sub
- Canal dedicado por task_id
- Escalabilidade horizontal

Error Handling:
- Tratamento robusto de desconexões
- Logging detalhado de eventos
- Recuperação graciosa de falhas

USAGE EXAMPLES:
==============

# Include WebSocket router in FastAPI app
from backend.api.websocket.websocket_service import router as ws_router

app = FastAPI()
app.include_router(ws_router)

# WebSocket endpoint: ws://localhost:8000/task_status/{task_id}
# Client can connect and receive real-time updates about Celery tasks

PERFORMANCE:
===========

- Conexões assíncronas não-bloqueantes
- Monitoramento paralelo de Redis e tarefas
- Gerenciamento eficiente de memória
- Limitação automática de timeout

SECURITY:
========

- Validação de task_id
- Proteção contra conexões maliciosas
- Logging de todas as conexões
- Timeout para prevenir resource exhaustion

Author: EVAonline Development Team
Date: October 2025
Version: 1.0.0
"""

from .websocket_service import router

__all__ = ["router"]

# Version info
__version__ = "1.0.0"
__author__ = "EVAonline Development Team"
__date__ = "October 2025"
