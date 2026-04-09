"""
Tests for backend/api/websocket/websocket_service.py.

All external dependencies (redis, celery AsyncResult, websocket) are mocked.
"""

import json
from unittest.mock import AsyncMock, patch

import pytest


# ---------------------------------------------------------------------------
# broadcast_to_task_subscribers
# ---------------------------------------------------------------------------
class TestBroadcastToTaskSubscribers:
    @pytest.mark.asyncio
    @patch("backend.api.websocket.websocket_service.redis_client")
    async def test_publishes_message(self, mock_redis):
        from backend.api.websocket.websocket_service import (
            broadcast_to_task_subscribers,
        )

        message = {"status": "PROGRESS", "info": {"percent": 50}}
        await broadcast_to_task_subscribers("task-123", message)

        mock_redis.publish.assert_called_once_with(
            "task_status:task-123",
            json.dumps(message),
        )

    @pytest.mark.asyncio
    @patch("backend.api.websocket.websocket_service.redis_client")
    async def test_channel_format(self, mock_redis):
        from backend.api.websocket.websocket_service import (
            broadcast_to_task_subscribers,
        )

        await broadcast_to_task_subscribers("abc-def", {"x": 1})
        channel = mock_redis.publish.call_args[0][0]
        assert channel == "task_status:abc-def"


# ---------------------------------------------------------------------------
# monitor_task_timeout
# ---------------------------------------------------------------------------
class TestMonitorTaskTimeout:
    @pytest.mark.asyncio
    async def test_sends_timeout_and_closes(self):
        from backend.api.websocket.websocket_service import (
            monitor_task_timeout,
        )

        ws = AsyncMock()

        # Patch asyncio.sleep to not actually wait
        with patch("backend.api.websocket.websocket_service.asyncio.sleep", new_callable=AsyncMock):
            await monitor_task_timeout(ws, "task-1", timeout_minutes=0)

        ws.send_json.assert_called_once()
        call_data = ws.send_json.call_args[0][0]
        assert call_data["status"] == "TIMEOUT"
        ws.close.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_exception_handling(self):
        from backend.api.websocket.websocket_service import (
            monitor_task_timeout,
        )

        ws = AsyncMock()
        ws.send_json.side_effect = RuntimeError("closed")

        with patch("backend.api.websocket.websocket_service.asyncio.sleep", new_callable=AsyncMock):
            # Should not raise
            await monitor_task_timeout(ws, "task-2", timeout_minutes=0)


# ---------------------------------------------------------------------------
# Module-level config
# ---------------------------------------------------------------------------
class TestWebSocketServiceConfig:
    def test_redis_url_defined(self):
        from backend.api.websocket.websocket_service import REDIS_URL
        assert isinstance(REDIS_URL, str)
        assert "redis" in REDIS_URL.lower()

    def test_router_exists(self):
        from backend.api.websocket.websocket_service import router
        assert router is not None
