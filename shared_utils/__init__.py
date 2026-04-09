from .logging import configure_logging
from .websocket_client import DashWebSocketManager, MessageType, WebSocketClient, WebSocketMessage

configure_logging()  # Configura o logging automaticamente

__all__ = [
    "configure_logging",
    "WebSocketClient",
    "WebSocketMessage",
    "MessageType",
    "DashWebSocketManager",
]
