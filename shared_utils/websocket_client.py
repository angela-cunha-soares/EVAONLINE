"""
WebSocket Client para comunicação em tempo real com o backend.

Funcionalidades:
- Conexão a endpoints WebSocket com suporte a task_id
- Tratamento de mensagens (PROGRESS, SUCCESS, ERROR, TIMEOUT)
- Reconexão automática com backoff exponencial
- Gerenciamento de estado da conexão
- Callbacks para diferentes tipos de eventos

"""

import asyncio
import json
import logging
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, Optional

import websockets

logger = logging.getLogger(__name__)


class MessageType(Enum):
    """Tipos de mensagens possíveis do servidor WebSocket."""

    PROGRESS = "PROGRESS"
    SUCCESS = "SUCCESS"
    ERROR = "ERROR"
    TIMEOUT = "TIMEOUT"
    INVALID = "INVALID"


class WebSocketMessage:
    """Classe para representar e serializar mensagens WebSocket."""

    def __init__(self, message_type: str, data: Dict[str, Any]):
        """
        Inicializa uma mensagem WebSocket.

        Args:
            message_type: Tipo da mensagem (PROGRESS, SUCCESS, ERROR, TIMEOUT)
            data: Dados da mensagem
        """
        self.type = message_type
        self.data = data
        self.timestamp = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """Converte a mensagem para dicionário."""
        return {
            "type": self.type,
            "data": self.data,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_json(cls, json_str: str) -> "WebSocketMessage":
        """
        Cria uma mensagem a partir de string JSON.

        Args:
            json_str: String JSON com a mensagem

        Returns:
            WebSocketMessage ou None se inválido
        """
        try:
            data = json.loads(json_str)
            return cls(
                message_type=data.get("type", MessageType.INVALID.value),
                data=data.get("data", {}),
            )
        except json.JSONDecodeError as e:
            logger.error(f"Erro ao decodificar mensagem JSON: {e}")
            return None


class WebSocketClient:
    """
    Cliente WebSocket para conexão com backend em tempo real.

    Exemplo de uso:
    ```python
    async def on_progress(msg):
        print(f"Progress: {msg.data}")

    client = WebSocketClient(
        task_id="123-456",
        on_progress=on_progress
    )

    await client.connect()
    # Envia updates em tempo real via callbacks
    ```
    """

    # Configurações de reconexão
    INITIAL_RETRY_DELAY = 1  # 1 segundo
    MAX_RETRY_DELAY = 30  # 30 segundos
    MAX_RETRIES = 5  # Máximo de tentativas
    TIMEOUT = 30  # Timeout em segundos

    def __init__(
        self,
        task_id: str,
        base_url: str = "ws://localhost:8000",
        endpoint: str = "/task_status",
        on_progress: Optional[Callable] = None,
        on_success: Optional[Callable] = None,
        on_error: Optional[Callable] = None,
        on_timeout: Optional[Callable] = None,
        on_connected: Optional[Callable] = None,
        on_disconnected: Optional[Callable] = None,
    ):
        """
        Inicializa o cliente WebSocket.

        Args:
            task_id: ID da tarefa a monitorar
            base_url: URL base do servidor (ex: ws://localhost:8000)
            endpoint: Endpoint WebSocket (ex: /task_status)
            on_progress: Callback para mensagens de progresso
            on_success: Callback para conclusão com sucesso
            on_error: Callback para erros
            on_timeout: Callback para timeout
            on_connected: Callback quando conectado
            on_disconnected: Callback quando desconectado
        """
        self.task_id = task_id
        self.base_url = base_url
        self.endpoint = endpoint
        self.ws_url = f"{base_url}{endpoint}/{task_id}"

        # Callbacks
        self.on_progress = on_progress
        self.on_success = on_success
        self.on_error = on_error
        self.on_timeout = on_timeout
        self.on_connected = on_connected
        self.on_disconnected = on_disconnected

        # Estado
        self.is_connected = False
        self.ws: Optional[Any] = None
        self.retry_count = 0
        self.last_error: Optional[str] = None
        self.message_count = 0

    async def connect(self) -> bool:
        """
        Conecta ao servidor WebSocket com reconexão automática.

        Returns:
            bool: True se conectado com sucesso, False caso contrário
        """
        retry_delay = self.INITIAL_RETRY_DELAY

        while self.retry_count < self.MAX_RETRIES:
            try:
                logger.info(
                    f"Conectando ao WebSocket: {self.ws_url} "
                    f"(tentativa {self.retry_count + 1}/{self.MAX_RETRIES})"
                )

                async with websockets.connect(
                    self.ws_url,
                    ping_interval=20,
                    ping_timeout=10,
                    close_timeout=10,
                ) as ws:
                    self.ws = ws
                    self.is_connected = True
                    self.retry_count = 0
                    self.last_error = None

                    logger.info(f"✅ Conectado ao WebSocket: {self.task_id}")

                    if self.on_connected:
                        await self._run_callback(self.on_connected)

                    # Aguarda mensagens
                    await self._listen()

            except websockets.exceptions.WebSocketException as e:
                self.is_connected = False
                self.last_error = str(e)
                self.retry_count += 1

                logger.warning(
                    f"Erro WebSocket para {self.task_id}: {e}. "
                    f"Tentando reconectar em {retry_delay}s..."
                )

                if self.on_error:
                    await self._run_callback(
                        self.on_error,
                        {"error": str(e), "retry_in": retry_delay},
                    )

                if self.retry_count < self.MAX_RETRIES:
                    await asyncio.sleep(retry_delay)
                    retry_delay = min(retry_delay * 2, self.MAX_RETRY_DELAY)
                else:
                    logger.error(
                        f"❌ Limite de tentativas atingido para {self.task_id}"
                    )
                    break

            except asyncio.TimeoutError:
                self.is_connected = False
                self.last_error = "Timeout"
                logger.error(f"Timeout ao conectar em {self.task_id}")

                if self.on_timeout:
                    await self._run_callback(
                        self.on_timeout, {"error": "Connection timeout"}
                    )
                break

            except Exception as e:
                self.is_connected = False
                self.last_error = str(e)
                logger.error(f"Erro inesperado ao conectar: {e}")

                if self.on_error:
                    await self._run_callback(self.on_error, {"error": str(e)})
                break

        if self.on_disconnected and not self.is_connected:
            await self._run_callback(self.on_disconnected)

        return self.is_connected

    async def _listen(self) -> None:
        """
        Aguarda e processa mensagens do servidor WebSocket.
        Executa até que a conexão seja fechada ou erro ocorra.
        """
        try:
            async for message_text in self.ws:
                self.message_count += 1

                # Parse mensagem JSON
                msg = WebSocketMessage.from_json(message_text)

                if not msg:
                    logger.warning(
                        f"Mensagem inválida recebida: {message_text}"
                    )
                    continue

                logger.debug(
                    f"Mensagem recebida ({self.task_id}): tipo={msg.type}, dados={msg.data}"
                )

                # Dispatch para callbacks apropriados
                await self._dispatch_message(msg)

        except websockets.exceptions.ConnectionClosed as e:
            logger.info(f"Conexão WebSocket fechada: {e}")
            self.is_connected = False

        except Exception as e:
            logger.error(f"Erro ao escutar WebSocket: {e}")
            self.is_connected = False
            self.last_error = str(e)

    async def _dispatch_message(self, msg: WebSocketMessage) -> None:
        """
        Dispara callbacks apropriados baseado no tipo de mensagem.

        Args:
            msg: Mensagem WebSocket recebida
        """
        try:
            if msg.type == MessageType.PROGRESS.value and self.on_progress:
                await self._run_callback(self.on_progress, msg.data)

            elif msg.type == MessageType.SUCCESS.value and self.on_success:
                await self._run_callback(self.on_success, msg.data)
                # Fechar conexão após sucesso
                self.is_connected = False

            elif msg.type == MessageType.ERROR.value and self.on_error:
                await self._run_callback(self.on_error, msg.data)
                # Fechar conexão após erro
                self.is_connected = False

            elif msg.type == MessageType.TIMEOUT.value and self.on_timeout:
                await self._run_callback(self.on_timeout, msg.data)
                # Fechar conexão após timeout
                self.is_connected = False

        except Exception as e:
            logger.error(f"Erro ao disparar callback ({msg.type}): {e}")

    async def _run_callback(
        self, callback: Callable, data: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Executa callback de forma segura, suportando sync e async.

        Args:
            callback: Função a executar
            data: Dados para passar ao callback
        """
        try:
            if asyncio.iscoroutinefunction(callback):
                if data:
                    await callback(data)
                else:
                    await callback()
            else:
                if data:
                    callback(data)
                else:
                    callback()
        except Exception as e:
            logger.error(f"Erro ao executar callback: {e}")

    async def disconnect(self) -> None:
        """Desconecta do servidor WebSocket."""
        try:
            if self.ws and not self.ws.closed:
                await self.ws.close()
                self.is_connected = False
                logger.info(f"Desconectado do WebSocket: {self.task_id}")

                if self.on_disconnected:
                    await self._run_callback(self.on_disconnected)
        except Exception as e:
            logger.error(f"Erro ao desconectar: {e}")

    def get_status(self) -> Dict[str, Any]:
        """
        Retorna status atual da conexão.

        Returns:
            Dict com informações de status
        """
        return {
            "task_id": self.task_id,
            "is_connected": self.is_connected,
            "retry_count": self.retry_count,
            "message_count": self.message_count,
            "last_error": self.last_error,
            "ws_url": self.ws_url,
        }


# ============================================================================
# HELPERS PARA USO EM DASH
# ============================================================================


class DashWebSocketManager:
    """
    Gerenciador de conexões WebSocket para Dash.

    Gerencia múltiplas conexões WebSocket simultâneas e coordena
    callbacks Dash para atualização de UI em tempo real.
    """

    _connections: Dict[str, WebSocketClient] = {}
    _event_loop: Optional[asyncio.AbstractEventLoop] = None

    @classmethod
    def get_event_loop(cls) -> asyncio.AbstractEventLoop:
        """Obtém ou cria event loop para async operations."""
        if cls._event_loop is None or cls._event_loop.is_closed():
            try:
                cls._event_loop = asyncio.get_event_loop()
            except RuntimeError:
                cls._event_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(cls._event_loop)
        return cls._event_loop

    @classmethod
    def create_connection(
        cls, task_id: str, base_url: str = "ws://localhost:8000", **kwargs
    ) -> WebSocketClient:
        """
        Cria nova conexão WebSocket.

        Args:
            task_id: ID da tarefa a monitorar
            base_url: URL base do servidor
            **kwargs: Argumentos adicionais para WebSocketClient

        Returns:
            WebSocketClient: Objeto de conexão criado
        """
        if task_id in cls._connections:
            logger.warning(f"Conexão para {task_id} já existe")
            return cls._connections[task_id]

        client = WebSocketClient(task_id, base_url=base_url, **kwargs)
        cls._connections[task_id] = client
        return client

    @classmethod
    def get_connection(cls, task_id: str) -> Optional[WebSocketClient]:
        """Obtém conexão existente."""
        return cls._connections.get(task_id)

    @classmethod
    def remove_connection(cls, task_id: str) -> None:
        """Remove conexão."""
        if task_id in cls._connections:
            del cls._connections[task_id]

    @classmethod
    async def connect_async(cls, task_id: str) -> bool:
        """
        Conecta um cliente WebSocket de forma assíncrona.

        Args:
            task_id: ID da tarefa

        Returns:
            bool: True se conectado com sucesso
        """
        client = cls.get_connection(task_id)
        if not client:
            logger.error(f"Conexão não encontrada para {task_id}")
            return False

        return await client.connect()

    @classmethod
    def connect_sync(cls, task_id: str) -> bool:
        """
        Conecta um cliente WebSocket de forma síncrona (wrapper para Dash).

        Args:
            task_id: ID da tarefa

        Returns:
            bool: True se conectado com sucesso
        """
        try:
            loop = cls.get_event_loop()
            if loop.is_running():
                # Se loop já está rodando, fazer não-bloqueante
                future = asyncio.ensure_future(
                    cls.connect_async(task_id), loop=loop
                )
                return future
            else:
                # Se não está rodando, usar run_until_complete
                return loop.run_until_complete(cls.connect_async(task_id))
        except Exception as e:
            logger.error(f"Erro ao conectar sincronamente: {e}")
            return False


__all__ = [
    "WebSocketClient",
    "WebSocketMessage",
    "MessageType",
    "DashWebSocketManager",
]
