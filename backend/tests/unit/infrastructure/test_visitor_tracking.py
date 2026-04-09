"""
Unit Tests – backend.infrastructure.visitor_tracking.VisitorTracker
and backend.core.analytics.visitor_counter_service.VisitorCounterService

All Redis and DB dependencies are mocked with fakeredis / MagicMock.
"""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

try:
    import fakeredis
    HAS_FAKEREDIS = True
except ImportError:
    HAS_FAKEREDIS = False


# ===================================================================
# VisitorTracker tests
# ===================================================================

class TestVisitorTracker:
    """Tests for VisitorTracker (async increments, sync, get_total)"""

    def _make_tracker(self):
        """Create a VisitorTracker with a mock Redis client."""
        from backend.infrastructure.visitor_tracking import VisitorTracker
        mock_redis = MagicMock()
        mock_redis.incr.return_value = 1
        mock_redis.sadd.return_value = 1
        mock_redis.get.return_value = "42"
        mock_redis.scard.return_value = 5
        return VisitorTracker(redis_client=mock_redis), mock_redis

    @pytest.mark.asyncio
    async def test_increment_visitor_returns_count(self):
        tracker, mock_redis = self._make_tracker()
        mock_redis.incr.return_value = 7
        count = await tracker.increment_visitor(session_id="sess_abc")
        assert count == 7
        mock_redis.incr.assert_called_once_with("visitors:total")

    @pytest.mark.asyncio
    async def test_increment_without_session_id(self):
        tracker, mock_redis = self._make_tracker()
        mock_redis.incr.return_value = 1
        count = await tracker.increment_visitor()
        assert count == 1
        mock_redis.sadd.assert_not_called()

    @pytest.mark.asyncio
    async def test_increment_with_session_adds_to_set(self):
        tracker, mock_redis = self._make_tracker()
        await tracker.increment_visitor(session_id="sess_xyz")
        mock_redis.sadd.assert_called_once_with("visitors:session", "sess_xyz")

    @pytest.mark.asyncio
    async def test_get_total_visitors_from_redis(self):
        tracker, mock_redis = self._make_tracker()
        mock_redis.get.return_value = "100"
        total = await tracker.get_total_visitors()
        assert total == 100

    @pytest.mark.asyncio
    @patch("backend.infrastructure.visitor_tracking.get_db")
    async def test_get_total_visitors_fallback_to_db(self, mock_get_db):
        tracker, mock_redis = self._make_tracker()
        mock_redis.get.return_value = "0"  # Redis empty

        mock_stats = MagicMock()
        mock_stats.total_visitors = 500
        mock_session = MagicMock()
        mock_session.query.return_value.first.return_value = mock_stats
        mock_get_db.return_value = iter([mock_session])

        total = await tracker.get_total_visitors()
        assert total == 500
        mock_redis.set.assert_called_once_with("visitors:total", 500)

    def test_get_unique_sessions_today(self):
        tracker, mock_redis = self._make_tracker()
        mock_redis.scard.return_value = 15
        assert tracker.get_unique_sessions_today() == 15


# ===================================================================
# VisitorCounterService tests
# ===================================================================

class TestVisitorCounterService:
    """Tests for VisitorCounterService with mocked Redis + DB session"""

    def _make_service(self):
        from backend.core.analytics.visitor_counter_service import VisitorCounterService
        mock_redis = MagicMock()
        mock_db = MagicMock()

        # Default mock returns
        mock_redis.sismember.return_value = False  # new visitor
        mock_redis.incr.return_value = 1
        mock_redis.get.return_value = "10"
        mock_redis.scard.return_value = 3

        return VisitorCounterService(mock_redis, mock_db), mock_redis, mock_db

    def test_increment_new_visitor(self):
        svc, mock_redis, _ = self._make_service()
        mock_redis.sismember.return_value = False
        mock_redis.get.return_value = "11"
        mock_redis.scard.return_value = 4

        result = svc.increment_visitor(session_id="sess_123")
        assert result["is_new_visitor"] is True
        assert result["total_visitors"] == 11
        mock_redis.incr.assert_called()

    def test_increment_returning_visitor(self):
        svc, mock_redis, _ = self._make_service()
        mock_redis.sismember.return_value = True  # already seen
        mock_redis.get.return_value = "10"
        mock_redis.scard.return_value = 3

        result = svc.increment_visitor(session_id="sess_123")
        assert result["is_new_visitor"] is False
        assert result["total_visitors"] == 10

    def test_increment_no_identifier_returns_stats(self):
        svc, mock_redis, _ = self._make_service()
        mock_redis.get.return_value = "10"

        result = svc.increment_visitor()  # No session_id or ip
        assert "total_visitors" in result

    def test_get_stats(self):
        svc, mock_redis, _ = self._make_service()
        mock_redis.get.side_effect = lambda key: {
            "visitors:count": "42",
        }.get(key, None)

        result = svc.get_stats()
        assert "total_visitors" in result
        assert "current_hour" in result
        assert "timestamp" in result

    def test_get_stats_handles_exception(self):
        svc, mock_redis, _ = self._make_service()
        mock_redis.get.side_effect = Exception("Redis down")

        result = svc.get_stats()
        assert "error" in result

    def test_sync_to_database_creates_new(self):
        svc, mock_redis, mock_db = self._make_service()
        mock_redis.get.return_value = "50"
        mock_db.query.return_value.first.return_value = None  # No existing stats

        result = svc.sync_to_database()
        assert result["status"] == "synced"
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    def test_sync_to_database_updates_existing(self):
        svc, mock_redis, mock_db = self._make_service()
        mock_redis.get.return_value = "75"
        existing_stats = MagicMock()
        mock_db.query.return_value.first.return_value = existing_stats

        result = svc.sync_to_database()
        assert result["status"] == "synced"
        assert existing_stats.total_visitors == 75
        mock_db.commit.assert_called_once()

    def test_sync_to_database_handles_error(self):
        svc, mock_redis, mock_db = self._make_service()
        mock_redis.get.return_value = "50"
        mock_db.query.side_effect = Exception("DB error")

        result = svc.sync_to_database()
        assert "error" in result
        mock_db.rollback.assert_called_once()

    def test_get_database_stats_returns_data(self):
        svc, _, mock_db = self._make_service()
        mock_stats = MagicMock()
        mock_stats.total_visitors = 200
        mock_stats.unique_visitors_today = 30
        mock_stats.peak_hour = "14:00"
        mock_stats.last_sync = datetime(2024, 1, 1, 12, 0)
        mock_stats.created_at = datetime(2024, 1, 1, 0, 0)
        mock_db.query.return_value.first.return_value = mock_stats

        result = svc.get_database_stats()
        assert result["total_visitors"] == 200
        assert result["peak_hour"] == "14:00"

    def test_get_database_stats_returns_none_when_empty(self):
        svc, _, mock_db = self._make_service()
        mock_db.query.return_value.first.return_value = None
        assert svc.get_database_stats() is None

    def test_get_database_stats_handles_error(self):
        svc, _, mock_db = self._make_service()
        mock_db.query.side_effect = Exception("DB gone")
        result = svc.get_database_stats()
        assert "error" in result
