"""
Tests for shared_utils/websocket_client.py.

Covers:
- MessageType enum
- WebSocketMessage (init, to_dict, from_json)
- WebSocketClient (init, get_status, _dispatch_message, _run_callback, disconnect)
- DashWebSocketManager (create_connection, get_connection, remove_connection)
"""

import asyncio
import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from shared_utils.websocket_client import (
    DashWebSocketManager,
    MessageType,
    WebSocketClient,
    WebSocketMessage,
)


# ---------------------------------------------------------------------------
# MessageType
# ---------------------------------------------------------------------------
class TestMessageType:
    def test_progress_value(self):
        assert MessageType.PROGRESS.value == "PROGRESS"

    def test_success_value(self):
        assert MessageType.SUCCESS.value == "SUCCESS"

    def test_error_value(self):
        assert MessageType.ERROR.value == "ERROR"

    def test_timeout_value(self):
        assert MessageType.TIMEOUT.value == "TIMEOUT"

    def test_invalid_value(self):
        assert MessageType.INVALID.value == "INVALID"

    def test_all_members(self):
        members = {m.value for m in MessageType}
        assert members == {"PROGRESS", "SUCCESS", "ERROR", "TIMEOUT", "INVALID"}


# ---------------------------------------------------------------------------
# WebSocketMessage
# ---------------------------------------------------------------------------
class TestWebSocketMessage:
    def test_init(self):
        msg = WebSocketMessage("PROGRESS", {"percent": 50})
        assert msg.type == "PROGRESS"
        assert msg.data == {"percent": 50}
        assert msg.timestamp is not None

    def test_to_dict(self):
        msg = WebSocketMessage("SUCCESS", {"result": "ok"})
        d = msg.to_dict()
        assert d["type"] == "SUCCESS"
        assert d["data"] == {"result": "ok"}
        assert "timestamp" in d

    def test_from_json_valid(self):
        payload = json.dumps({"type": "ERROR", "data": {"error": "fail"}})
        msg = WebSocketMessage.from_json(payload)
        assert msg is not None
        assert msg.type == "ERROR"
        assert msg.data == {"error": "fail"}

    def test_from_json_missing_type(self):
        payload = json.dumps({"data": {"info": "test"}})
        msg = WebSocketMessage.from_json(payload)
        assert msg is not None
        assert msg.type == MessageType.INVALID.value

    def test_from_json_missing_data(self):
        payload = json.dumps({"type": "SUCCESS"})
        msg = WebSocketMessage.from_json(payload)
        assert msg is not None
        assert msg.data == {}

    def test_from_json_invalid_json(self):
        msg = WebSocketMessage.from_json("not-json{{")
        assert msg is None

    def test_from_json_empty_string(self):
        msg = WebSocketMessage.from_json("")
        assert msg is None

    def test_timestamp_is_isoformat(self):
        msg = WebSocketMessage("PROGRESS", {})
        # Should not raise
        datetime.fromisoformat(msg.timestamp)


# ---------------------------------------------------------------------------
# WebSocketClient — init & get_status
# ---------------------------------------------------------------------------
class TestWebSocketClientInit:
    def test_default_init(self):
        client = WebSocketClient(task_id="abc-123")
        assert client.task_id == "abc-123"
        assert client.is_connected is False
        assert client.retry_count == 0
        assert client.message_count == 0
        assert "abc-123" in client.ws_url

    def test_custom_url(self):
        client = WebSocketClient(
            task_id="t1",
            base_url="ws://example.com:9000",
            endpoint="/ws",
        )
        assert client.ws_url == "ws://example.com:9000/ws/t1"

    def test_get_status(self):
        client = WebSocketClient(task_id="t2")
        status = client.get_status()
        assert status["task_id"] == "t2"
        assert status["is_connected"] is False
        assert status["retry_count"] == 0
        assert status["message_count"] == 0
        assert status["last_error"] is None

    def test_callbacks_stored(self):
        on_p = MagicMock()
        on_s = MagicMock()
        client = WebSocketClient(
            task_id="t3",
            on_progress=on_p,
            on_success=on_s,
        )
        assert client.on_progress is on_p
        assert client.on_success is on_s

    def test_class_constants(self):
        assert WebSocketClient.MAX_RETRIES == 5
        assert WebSocketClient.TIMEOUT == 30
        assert WebSocketClient.INITIAL_RETRY_DELAY == 1
        assert WebSocketClient.MAX_RETRY_DELAY == 30


# ---------------------------------------------------------------------------
# WebSocketClient — _run_callback
# ---------------------------------------------------------------------------
class TestRunCallback:
    @pytest.mark.asyncio
    async def test_sync_callback_with_data(self):
        client = WebSocketClient(task_id="t1")
        cb = MagicMock()
        await client._run_callback(cb, {"key": "val"})
        cb.assert_called_once_with({"key": "val"})

    @pytest.mark.asyncio
    async def test_sync_callback_no_data(self):
        client = WebSocketClient(task_id="t1")
        cb = MagicMock()
        await client._run_callback(cb)
        cb.assert_called_once_with()

    @pytest.mark.asyncio
    async def test_async_callback_with_data(self):
        client = WebSocketClient(task_id="t1")
        cb = AsyncMock()
        await client._run_callback(cb, {"key": "val"})
        cb.assert_awaited_once_with({"key": "val"})

    @pytest.mark.asyncio
    async def test_async_callback_no_data(self):
        client = WebSocketClient(task_id="t1")
        cb = AsyncMock()
        await client._run_callback(cb)
        cb.assert_awaited_once_with()

    @pytest.mark.asyncio
    async def test_callback_exception_does_not_raise(self):
        client = WebSocketClient(task_id="t1")
        cb = MagicMock(side_effect=RuntimeError("boom"))
        # Should not raise
        await client._run_callback(cb, {"x": 1})


# ---------------------------------------------------------------------------
# WebSocketClient — _dispatch_message
# ---------------------------------------------------------------------------
class TestDispatchMessage:
    @pytest.mark.asyncio
    async def test_progress_dispatch(self):
        on_p = AsyncMock()
        client = WebSocketClient(task_id="t1", on_progress=on_p)
        msg = WebSocketMessage(MessageType.PROGRESS.value, {"pct": 50})
        await client._dispatch_message(msg)
        on_p.assert_awaited_once_with({"pct": 50})

    @pytest.mark.asyncio
    async def test_success_dispatch(self):
        on_s = AsyncMock()
        client = WebSocketClient(task_id="t1", on_success=on_s)
        msg = WebSocketMessage(MessageType.SUCCESS.value, {"ok": True})
        await client._dispatch_message(msg)
        on_s.assert_awaited_once()
        assert client.is_connected is False

    @pytest.mark.asyncio
    async def test_error_dispatch(self):
        on_e = AsyncMock()
        client = WebSocketClient(task_id="t1", on_error=on_e)
        msg = WebSocketMessage(MessageType.ERROR.value, {"err": "x"})
        await client._dispatch_message(msg)
        on_e.assert_awaited_once()
        assert client.is_connected is False

    @pytest.mark.asyncio
    async def test_timeout_dispatch(self):
        on_t = AsyncMock()
        client = WebSocketClient(task_id="t1", on_timeout=on_t)
        msg = WebSocketMessage(MessageType.TIMEOUT.value, {"err": "timeout"})
        await client._dispatch_message(msg)
        on_t.assert_awaited_once()
        assert client.is_connected is False

    @pytest.mark.asyncio
    async def test_dispatch_no_callback(self):
        """No callback registered — should not raise."""
        client = WebSocketClient(task_id="t1")
        msg = WebSocketMessage(MessageType.PROGRESS.value, {})
        await client._dispatch_message(msg)  # no error

    @pytest.mark.asyncio
    async def test_dispatch_callback_exception(self):
        on_p = AsyncMock(side_effect=RuntimeError("callback error"))
        client = WebSocketClient(task_id="t1", on_progress=on_p)
        msg = WebSocketMessage(MessageType.PROGRESS.value, {})
        await client._dispatch_message(msg)  # should not raise


# ---------------------------------------------------------------------------
# WebSocketClient — disconnect
# ---------------------------------------------------------------------------
class TestDisconnect:
    @pytest.mark.asyncio
    async def test_disconnect_open_ws(self):
        client = WebSocketClient(task_id="t1")
        mock_ws = AsyncMock()
        mock_ws.closed = False
        client.ws = mock_ws
        client.is_connected = True

        await client.disconnect()
        mock_ws.close.assert_awaited_once()
        assert client.is_connected is False

    @pytest.mark.asyncio
    async def test_disconnect_already_closed(self):
        client = WebSocketClient(task_id="t1")
        mock_ws = AsyncMock()
        mock_ws.closed = True
        client.ws = mock_ws
        client.is_connected = True

        await client.disconnect()
        mock_ws.close.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_disconnect_no_ws(self):
        client = WebSocketClient(task_id="t1")
        await client.disconnect()  # should not raise

    @pytest.mark.asyncio
    async def test_disconnect_fires_callback(self):
        on_disc = AsyncMock()
        client = WebSocketClient(task_id="t1", on_disconnected=on_disc)
        mock_ws = AsyncMock()
        mock_ws.closed = False
        client.ws = mock_ws
        client.is_connected = True

        await client.disconnect()
        on_disc.assert_awaited_once()


# ---------------------------------------------------------------------------
# DashWebSocketManager
# ---------------------------------------------------------------------------
class TestDashWebSocketManager:
    def setup_method(self):
        """Reset class state between tests."""
        DashWebSocketManager._connections = {}
        DashWebSocketManager._event_loop = None

    def test_create_connection(self):
        client = DashWebSocketManager.create_connection(task_id="task-1")
        assert isinstance(client, WebSocketClient)
        assert client.task_id == "task-1"

    def test_get_connection(self):
        DashWebSocketManager.create_connection(task_id="task-2")
        client = DashWebSocketManager.get_connection("task-2")
        assert client is not None
        assert client.task_id == "task-2"

    def test_get_connection_missing(self):
        client = DashWebSocketManager.get_connection("nonexistent")
        assert client is None

    def test_remove_connection(self):
        DashWebSocketManager.create_connection(task_id="task-3")
        DashWebSocketManager.remove_connection("task-3")
        assert DashWebSocketManager.get_connection("task-3") is None

    def test_remove_nonexistent(self):
        # Should not raise
        DashWebSocketManager.remove_connection("ghost")

    def test_create_with_custom_callbacks(self):
        cb = MagicMock()
        client = DashWebSocketManager.create_connection(
            task_id="task-4",
            on_progress=cb,
        )
        assert client.on_progress is cb

    def test_get_event_loop(self):
        loop = DashWebSocketManager.get_event_loop()
        assert loop is not None
        assert isinstance(loop, asyncio.AbstractEventLoop)


# ---------------------------------------------------------------------------
# WebSocketClient.connect
# ---------------------------------------------------------------------------
class TestConnect:
    """Tests for connect() with mocked websockets."""

    @pytest.mark.asyncio
    async def test_successful_connect_and_listen(self):
        """Simulate a successful connection that receives messages then closes."""
        import websockets.exceptions

        client = WebSocketClient(task_id="test-conn")
        on_connected = AsyncMock()
        on_disconnected = AsyncMock()
        client.on_connected = on_connected
        client.on_disconnected = on_disconnected

        mock_ws = AsyncMock()
        # Simulate receiving one message then connection closes
        msg = json.dumps({"type": "PROGRESS", "data": {"percent": 50}})

        async def mock_connect(*args, **kwargs):
            """Context manager that yields mock_ws."""
            class _CM:
                async def __aenter__(self_cm):
                    return mock_ws
                async def __aexit__(self_cm, *exc):
                    pass
            return _CM()

        # Make mock_ws iterable (for `async for message_text in self.ws:`)
        mock_ws.__aiter__ = MagicMock(return_value=iter([msg]))
        # After iterating, _listen should finish -> connection exits context -> loop ends

        with patch("shared_utils.websocket_client.websockets") as mock_websockets:
            # Make websockets.connect return our context manager
            async def ws_connect(*args, **kwargs):
                return mock_ws

            mock_websockets.connect = MagicMock()
            mock_ws_ctx = AsyncMock()
            mock_ws_ctx.__aenter__ = AsyncMock(return_value=mock_ws)
            mock_ws_ctx.__aexit__ = AsyncMock(return_value=False)
            mock_websockets.connect.return_value = mock_ws_ctx

            # Simulate ConnectionClosed at the end of _listen
            mock_ws.__aiter__ = MagicMock(return_value=iter([msg]))
            mock_websockets.exceptions.WebSocketException = websockets.exceptions.WebSocketException

            # Run connect - it should process the message and exit
            result = await client.connect()

    @pytest.mark.asyncio
    async def test_connect_timeout(self):
        """Simulate a timeout during connection."""
        import websockets.exceptions

        client = WebSocketClient(task_id="test-timeout")
        on_timeout = AsyncMock()
        client.on_timeout = on_timeout

        with patch("shared_utils.websocket_client.websockets") as mock_ws:
            mock_ws.connect.side_effect = asyncio.TimeoutError()
            mock_ws.exceptions.WebSocketException = websockets.exceptions.WebSocketException

            result = await client.connect()
            assert result is False
            assert client.last_error == "Timeout"

    @pytest.mark.asyncio
    async def test_connect_unexpected_error(self):
        """Simulate an unexpected error during connection."""
        import websockets.exceptions

        client = WebSocketClient(task_id="test-error")
        on_error = AsyncMock()
        client.on_error = on_error

        with patch("shared_utils.websocket_client.websockets") as mock_ws:
            mock_ws.connect.side_effect = RuntimeError("unexpected")
            mock_ws.exceptions.WebSocketException = websockets.exceptions.WebSocketException

            result = await client.connect()
            assert result is False
            assert "unexpected" in client.last_error

    @pytest.mark.asyncio
    async def test_connect_calls_on_disconnected(self):
        """On failure, on_disconnected callback should fire."""
        import websockets.exceptions

        client = WebSocketClient(task_id="test-disc")
        on_disconnected = AsyncMock()
        client.on_disconnected = on_disconnected

        with patch("shared_utils.websocket_client.websockets") as mock_ws:
            mock_ws.connect.side_effect = asyncio.TimeoutError()
            mock_ws.exceptions.WebSocketException = websockets.exceptions.WebSocketException

            await client.connect()
            on_disconnected.assert_awaited_once()


# ---------------------------------------------------------------------------
# WebSocketClient._listen
# ---------------------------------------------------------------------------
class TestListen:
    """Tests for _listen() method."""

    @pytest.mark.asyncio
    async def test_listen_processes_messages(self):
        """_listen should process valid JSON messages."""
        client = WebSocketClient(task_id="test-listen")
        on_progress = AsyncMock()
        client.on_progress = on_progress

        msg = json.dumps({"type": "PROGRESS", "data": {"percent": 75}})
        mock_ws = AsyncMock()

        # Create an async iterator
        async def aiter_msgs():
            yield msg

        mock_ws.__aiter__ = lambda self: aiter_msgs()
        client.ws = mock_ws

        await client._listen()
        assert client.message_count == 1

    @pytest.mark.asyncio
    async def test_listen_handles_invalid_json(self):
        """_listen should skip invalid JSON messages."""
        client = WebSocketClient(task_id="test-invalid")

        mock_ws = AsyncMock()

        async def aiter_msgs():
            yield "not valid json {"

        mock_ws.__aiter__ = lambda self: aiter_msgs()
        client.ws = mock_ws

        await client._listen()
        assert client.message_count == 1

    @pytest.mark.asyncio
    async def test_listen_connection_closed(self):
        """_listen should handle ConnectionClosed gracefully."""
        import websockets.exceptions

        client = WebSocketClient(task_id="test-closed")
        mock_ws = AsyncMock()

        async def aiter_msgs():
            raise websockets.exceptions.ConnectionClosed(None, None)
            yield  # Make it a generator

        mock_ws.__aiter__ = lambda self: aiter_msgs()
        client.ws = mock_ws

        await client._listen()
        assert client.is_connected is False

    @pytest.mark.asyncio
    async def test_listen_unexpected_error(self):
        """_listen should handle unexpected errors."""
        client = WebSocketClient(task_id="test-err")
        mock_ws = AsyncMock()

        async def aiter_msgs():
            raise RuntimeError("boom")
            yield

        mock_ws.__aiter__ = lambda self: aiter_msgs()
        client.ws = mock_ws

        await client._listen()
        assert client.is_connected is False
        assert client.last_error == "boom"


# ---------------------------------------------------------------------------
# WebSocketClient.get_status
# ---------------------------------------------------------------------------
class TestGetStatus:
    """Tests for get_status method."""

    def test_status_fields(self):
        client = WebSocketClient(task_id="test-status")
        status = client.get_status()
        assert status["task_id"] == "test-status"
        assert "is_connected" in status
        assert "retry_count" in status
        assert "message_count" in status
        assert "last_error" in status

    def test_status_after_error(self):
        client = WebSocketClient(task_id="test-status-err")
        client.last_error = "test error"
        client.retry_count = 3
        status = client.get_status()
        assert status["last_error"] == "test error"
        assert status["retry_count"] == 3
