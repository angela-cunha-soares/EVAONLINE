"""
Unit Tests – backend.database.redis_pool

All external Redis connections are mocked.
"""

from unittest.mock import MagicMock, patch

import pytest


class TestInitializeRedisPool:
    """Tests for redis_pool.initialize_redis_pool"""

    @patch("backend.database.redis_pool.redis.Redis")
    @patch("backend.database.redis_pool.redis.ConnectionPool")
    def test_creates_pool_and_client(self, mock_pool_cls, mock_redis_cls):
        import backend.database.redis_pool as mod

        # Reset module-level globals
        mod._redis_pool = None
        mod._redis_client = None

        mock_pool = MagicMock()
        mock_pool_cls.return_value = mock_pool

        mock_client = MagicMock()
        mock_client.ping.return_value = True
        mock_redis_cls.return_value = mock_client

        result = mod.initialize_redis_pool()
        assert result is mock_client
        mock_pool_cls.assert_called_once()
        mock_redis_cls.assert_called_once_with(connection_pool=mock_pool)

    @patch("backend.database.redis_pool.redis.Redis")
    @patch("backend.database.redis_pool.redis.ConnectionPool")
    def test_returns_existing_client_if_already_initialized(self, mock_pool_cls, mock_redis_cls):
        import backend.database.redis_pool as mod

        existing = MagicMock()
        mod._redis_client = existing

        result = mod.initialize_redis_pool()
        assert result is existing
        mock_pool_cls.assert_not_called()

        # Cleanup
        mod._redis_client = None
        mod._redis_pool = None

    @patch("backend.database.redis_pool.redis.Redis")
    @patch("backend.database.redis_pool.redis.ConnectionPool")
    def test_raises_on_connection_failure(self, mock_pool_cls, mock_redis_cls):
        import backend.database.redis_pool as mod

        mod._redis_pool = None
        mod._redis_client = None

        mock_client = MagicMock()
        mock_client.ping.side_effect = Exception("Connection refused")
        mock_redis_cls.return_value = mock_client

        with pytest.raises(Exception, match="Connection refused"):
            mod.initialize_redis_pool()

        # Cleanup
        mod._redis_client = None
        mod._redis_pool = None


class TestGetRedisClient:
    """Tests for redis_pool.get_redis_client"""

    def test_returns_existing_client(self):
        import backend.database.redis_pool as mod

        existing = MagicMock()
        mod._redis_client = existing

        result = mod.get_redis_client()
        assert result is existing

        mod._redis_client = None
        mod._redis_pool = None

    @patch("backend.database.redis_pool.initialize_redis_pool")
    def test_initializes_if_none(self, mock_init):
        import backend.database.redis_pool as mod

        mod._redis_client = None
        mock_client = MagicMock()
        mock_init.return_value = mock_client

        result = mod.get_redis_client()
        mock_init.assert_called_once()

        mod._redis_client = None
        mod._redis_pool = None


class TestCloseRedis:
    """Tests for redis_pool.close_redis"""

    def test_close_clears_globals(self):
        import backend.database.redis_pool as mod

        mock_client = MagicMock()
        mod._redis_client = mock_client
        mod._redis_pool = MagicMock()

        mod.close_redis()

        assert mod._redis_client is None
        assert mod._redis_pool is None
        mock_client.close.assert_called_once()

    def test_close_when_already_none(self):
        import backend.database.redis_pool as mod

        mod._redis_client = None
        mod._redis_pool = None

        # Should not raise
        mod.close_redis()
        assert mod._redis_client is None
