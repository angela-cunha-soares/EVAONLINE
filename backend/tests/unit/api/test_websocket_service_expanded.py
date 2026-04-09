"""Tests for backend/api/websocket/websocket_service.py."""

import json
import pytest
from unittest.mock import patch, AsyncMock

from backend.api.websocket.websocket_service import (
    broadcast_to_task_subscribers,
    monitor_task_timeout,
)


class TestBroadcastToTaskSubscribers:
    @pytest.mark.asyncio
    @patch("backend.api.websocket.websocket_service.redis_client")
    async def test_publishes_to_redis(self, mock_redis):
        message = {"status": "PROGRESS", "percent": 50}
        await broadcast_to_task_subscribers("task-123", message)
        mock_redis.publish.assert_called_once_with(
            "task_status:task-123",
            json.dumps(message),
        )


class TestMonitorTaskTimeout:
    @pytest.mark.asyncio
    @patch("backend.api.websocket.websocket_service.asyncio.sleep", new_callable=AsyncMock)
    async def test_sends_timeout_message(self, mock_sleep):
        mock_ws = AsyncMock()
        await monitor_task_timeout(mock_ws, "task-123", timeout_minutes=1)
        mock_sleep.assert_awaited_once_with(60)
        mock_ws.send_json.assert_awaited_once()
        msg = mock_ws.send_json.call_args[0][0]
        assert msg["status"] == "TIMEOUT"
        mock_ws.close.assert_awaited_once()

    @pytest.mark.asyncio
    @patch("backend.api.websocket.websocket_service.asyncio.sleep", new_callable=AsyncMock)
    async def test_handles_exception(self, mock_sleep):
        mock_ws = AsyncMock()
        mock_sleep.side_effect = Exception("cancelled")
        # Should not raise
        await monitor_task_timeout(mock_ws, "task-456")
