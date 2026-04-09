"""
Tests for backend/api/websocket/websocket_service.py — websocket_endpoint.

Covers the main WebSocket endpoint that monitors Celery task status
via Redis pubsub, including disconnect, error, and task-completion flows.
"""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import WebSocketDisconnect


def _fake_create_task(coro):
    """Mock asyncio.create_task that closes the coroutine to avoid 'was never awaited' warnings."""
    coro.close()
    return MagicMock()


class TestWebsocketEndpoint:
    """Tests for the websocket_endpoint async function."""

    def _get_fn(self):
        from backend.api.websocket.websocket_service import websocket_endpoint
        return websocket_endpoint

    @pytest.mark.asyncio
    @patch("backend.api.websocket.websocket_service.AsyncResult")
    @patch("backend.api.websocket.websocket_service.redis_client")
    @patch("backend.api.websocket.websocket_service.asyncio")
    @patch("backend.api.websocket.websocket_service.broadcast_to_task_subscribers", new_callable=AsyncMock)
    async def test_initial_state_sent(self, mock_broadcast, mock_asyncio, mock_redis, mock_async_result):
        """Should accept websocket, subscribe to Redis, and send initial state."""
        fn = self._get_fn()
        ws = AsyncMock()

        task = MagicMock()
        task.state = "PENDING"
        task.info = {}
        mock_async_result.return_value = task

        mock_pubsub = MagicMock()
        mock_redis.pubsub.return_value = mock_pubsub

        mock_asyncio.create_task.side_effect = _fake_create_task
        mock_asyncio.sleep = AsyncMock()

        async def fake_gather(*coros):
            for c in coros:
                c.close()
        mock_asyncio.gather = fake_gather
        mock_asyncio.CancelledError = asyncio.CancelledError

        await fn(ws, "task-123")

        ws.accept.assert_awaited_once()
        mock_pubsub.subscribe.assert_called_once_with("task_status:task-123")
        ws.send_json.assert_awaited()

    @pytest.mark.asyncio
    @patch("backend.api.websocket.websocket_service.AsyncResult")
    @patch("backend.api.websocket.websocket_service.redis_client")
    @patch("backend.api.websocket.websocket_service.asyncio.create_task")
    @patch("backend.api.websocket.websocket_service.asyncio.sleep", new_callable=AsyncMock)
    @patch("backend.api.websocket.websocket_service.broadcast_to_task_subscribers", new_callable=AsyncMock)
    async def test_websocket_disconnect(self, mock_broadcast, mock_sleep, mock_create_task, mock_redis, mock_async_result):
        """Should handle WebSocketDisconnect gracefully."""
        mock_create_task.side_effect = _fake_create_task
        fn = self._get_fn()
        ws = AsyncMock()
        # Make send_json raise WebSocketDisconnect to simulate disconnect
        ws.send_json.side_effect = WebSocketDisconnect()

        task = MagicMock()
        task.state = "PENDING"
        task.info = {}
        mock_async_result.return_value = task

        mock_pubsub = MagicMock()
        mock_redis.pubsub.return_value = mock_pubsub

        # Should not raise
        await fn(ws, "task-456")

        # Cleanup should still happen
        mock_pubsub.close.assert_called_once()

    @pytest.mark.asyncio
    @patch("backend.api.websocket.websocket_service.AsyncResult")
    @patch("backend.api.websocket.websocket_service.redis_client")
    @patch("backend.api.websocket.websocket_service.asyncio.create_task")
    @patch("backend.api.websocket.websocket_service.asyncio.sleep", new_callable=AsyncMock)
    @patch("backend.api.websocket.websocket_service.broadcast_to_task_subscribers", new_callable=AsyncMock)
    async def test_general_exception_sends_error(self, mock_broadcast, mock_sleep, mock_create_task, mock_redis, mock_async_result):
        """On general exception, should try to send error JSON to client."""
        mock_create_task.side_effect = _fake_create_task
        fn = self._get_fn()
        ws = AsyncMock()

        # Make AsyncResult raise a generic error
        mock_async_result.side_effect = RuntimeError("celery down")

        mock_pubsub = MagicMock()
        mock_redis.pubsub.return_value = mock_pubsub

        await fn(ws, "task-789")

        # Should have attempted to send error message
        error_calls = [c for c in ws.send_json.call_args_list
                       if c[0][0].get("status") == "ERROR"]
        assert len(error_calls) >= 1
        assert "celery down" in error_calls[0][0][0]["error"]

        # Cleanup
        mock_pubsub.close.assert_called_once()

    @pytest.mark.asyncio
    @patch("backend.api.websocket.websocket_service.AsyncResult")
    @patch("backend.api.websocket.websocket_service.redis_client")
    @patch("backend.api.websocket.websocket_service.asyncio.create_task")
    @patch("backend.api.websocket.websocket_service.asyncio.sleep", new_callable=AsyncMock)
    @patch("backend.api.websocket.websocket_service.broadcast_to_task_subscribers", new_callable=AsyncMock)
    async def test_error_send_fails_silently(self, mock_broadcast, mock_sleep, mock_create_task, mock_redis, mock_async_result):
        """If sending error message also fails, should not raise."""
        mock_create_task.side_effect = _fake_create_task
        fn = self._get_fn()
        ws = AsyncMock()

        mock_async_result.side_effect = RuntimeError("celery down")
        # send_json always fails
        ws.send_json.side_effect = RuntimeError("already closed")

        mock_pubsub = MagicMock()
        mock_redis.pubsub.return_value = mock_pubsub

        # Should not raise
        await fn(ws, "task-err")
        mock_pubsub.close.assert_called_once()

    @pytest.mark.asyncio
    @patch("backend.api.websocket.websocket_service.AsyncResult")
    @patch("backend.api.websocket.websocket_service.redis_client")
    @patch("backend.api.websocket.websocket_service.asyncio")
    @patch("backend.api.websocket.websocket_service.broadcast_to_task_subscribers", new_callable=AsyncMock)
    async def test_task_failure_broadcasts_failure(self, mock_broadcast, mock_asyncio, mock_redis, mock_async_result):
        """When task fails, should broadcast FAILURE status."""
        fn = self._get_fn()
        ws = AsyncMock()

        task = MagicMock()
        task.state = "STARTED"
        task.ready.side_effect = [False, True]
        task.failed.return_value = True
        task.info = ValueError("computation failed")
        mock_async_result.return_value = task

        mock_pubsub = MagicMock()
        mock_redis.pubsub.return_value = mock_pubsub

        mock_asyncio.create_task.side_effect = _fake_create_task
        mock_asyncio.sleep = AsyncMock()

        # Make asyncio.gather run only monitor_task (second arg)
        async def fake_gather(*coros):
            coros_list = list(coros)
            # Run monitor_task (second coroutine), skip listen_redis
            if len(coros_list) >= 2:
                # Cancel listen_redis
                coros_list[0].close()
                await coros_list[1]
        mock_asyncio.gather = fake_gather
        mock_asyncio.CancelledError = asyncio.CancelledError

        await fn(ws, "fail-task")

        # Check broadcast was called with FAILURE
        failure_calls = [c for c in mock_broadcast.call_args_list
                        if isinstance(c[0][1], dict) and c[0][1].get("status") == "FAILURE"]
        assert len(failure_calls) >= 1

    @pytest.mark.asyncio
    @patch("backend.api.websocket.websocket_service.AsyncResult")
    @patch("backend.api.websocket.websocket_service.redis_client")
    @patch("backend.api.websocket.websocket_service.asyncio")
    @patch("backend.api.websocket.websocket_service.broadcast_to_task_subscribers", new_callable=AsyncMock)
    async def test_task_success_broadcasts_result(self, mock_broadcast, mock_asyncio, mock_redis, mock_async_result):
        """When task succeeds, should broadcast SUCCESS with result."""
        fn = self._get_fn()
        ws = AsyncMock()

        task = MagicMock()
        task.state = "STARTED"
        task.info = {}
        task.ready.side_effect = [False, True]
        task.failed.return_value = False

        result_data = MagicMock()
        result_data.to_dict.return_value = {"eto": 5.2}
        task.get.return_value = (result_data, ["warning1"])
        mock_async_result.return_value = task

        mock_pubsub = MagicMock()
        mock_redis.pubsub.return_value = mock_pubsub

        mock_asyncio.create_task.side_effect = _fake_create_task
        mock_asyncio.sleep = AsyncMock()

        async def fake_gather(*coros):
            coros_list = list(coros)
            if len(coros_list) >= 2:
                coros_list[0].close()
                await coros_list[1]
        mock_asyncio.gather = fake_gather
        mock_asyncio.CancelledError = asyncio.CancelledError

        await fn(ws, "success-task")

        success_calls = [c for c in mock_broadcast.call_args_list
                        if isinstance(c[0][1], dict) and c[0][1].get("status") == "SUCCESS"]
        assert len(success_calls) >= 1
        assert success_calls[0][0][1]["result"] == {"eto": 5.2}

    @pytest.mark.asyncio
    @patch("backend.api.websocket.websocket_service.AsyncResult")
    @patch("backend.api.websocket.websocket_service.redis_client")
    @patch("backend.api.websocket.websocket_service.asyncio")
    @patch("backend.api.websocket.websocket_service.broadcast_to_task_subscribers", new_callable=AsyncMock)
    async def test_redis_message_forwarded(self, mock_broadcast, mock_asyncio, mock_redis, mock_async_result):
        """Redis pubsub messages should be forwarded to WebSocket client."""
        fn = self._get_fn()
        ws = AsyncMock()

        task = MagicMock()
        task.state = "PROGRESS"
        task.info = {"percent": 50}

        redis_msg = {"status": "PROGRESS", "info": {"percent": 75}}

        mock_pubsub = MagicMock()
        mock_pubsub.get_message.side_effect = [
            {"type": "message", "data": json.dumps(redis_msg)},
            None,
        ]
        mock_redis.pubsub.return_value = mock_pubsub

        task.ready.side_effect = [False, True]
        task.failed.return_value = False
        task.get.return_value = ({"ok": True}, None)
        mock_async_result.return_value = task

        mock_timeout_task = MagicMock()
        mock_asyncio.create_task.side_effect = _fake_create_task
        mock_asyncio.sleep = AsyncMock()

        async def fake_gather(*coros):
            coros_list = list(coros)
            if len(coros_list) >= 2:
                # Run listen_redis just once to forward the message
                # get_message will return our redis_msg, then None (StopIteration on 3rd)
                coros_list[1].close()
                # Manually simulate what listen_redis does for one iteration
                message = mock_pubsub.get_message(timeout=1.0)
                if message and message["type"] == "message":
                    await ws.send_json(json.loads(message["data"]))
        mock_asyncio.gather = fake_gather
        mock_asyncio.CancelledError = asyncio.CancelledError

        await fn(ws, "redis-task")

        sent_messages = [c[0][0] for c in ws.send_json.call_args_list]
        forwarded = [m for m in sent_messages if isinstance(m, dict) and m.get("info", {}).get("percent") == 75]
        assert len(forwarded) >= 1

    @pytest.mark.asyncio
    @patch("backend.api.websocket.websocket_service.AsyncResult")
    @patch("backend.api.websocket.websocket_service.redis_client")
    @patch("backend.api.websocket.websocket_service.asyncio")
    @patch("backend.api.websocket.websocket_service.broadcast_to_task_subscribers", new_callable=AsyncMock)
    async def test_progress_state_broadcast(self, mock_broadcast, mock_asyncio, mock_redis, mock_async_result):
        """When task is in PROGRESS state, should broadcast progress info."""
        fn = self._get_fn()
        ws = AsyncMock()

        task = MagicMock()
        task.state = "PROGRESS"
        task.info = {"percent": 30}
        task.ready.side_effect = [False, True]
        task.failed.return_value = False
        task.get.return_value = (None, None)
        mock_async_result.return_value = task

        mock_pubsub = MagicMock()
        mock_pubsub.get_message.return_value = None
        mock_redis.pubsub.return_value = mock_pubsub

        mock_asyncio.create_task.side_effect = _fake_create_task
        mock_asyncio.sleep = AsyncMock()

        async def fake_gather(*coros):
            coros_list = list(coros)
            if len(coros_list) >= 2:
                coros_list[0].close()
                await coros_list[1]
        mock_asyncio.gather = fake_gather
        mock_asyncio.CancelledError = asyncio.CancelledError

        await fn(ws, "progress-task")
        progress_calls = [c for c in mock_broadcast.call_args_list
                         if isinstance(c[0][1], dict) and c[0][1].get("status") == "PROGRESS"]
        assert len(progress_calls) >= 1
