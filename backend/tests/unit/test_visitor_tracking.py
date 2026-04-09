"""Tests for backend/infrastructure/visitor_tracking.py."""

import pytest
from unittest.mock import MagicMock, patch


class TestVisitorTracker:
    def _make_tracker(self, redis_mock=None):
        from backend.infrastructure.visitor_tracking import VisitorTracker

        r = redis_mock or MagicMock()
        return VisitorTracker(r), r

    def test_init(self):
        tracker, r = self._make_tracker()
        assert tracker.redis is r
        assert tracker.redis_key == "visitors:total"
        assert tracker.sync_threshold == 100
        assert tracker.sync_interval == 3600

    @pytest.mark.asyncio
    async def test_increment_visitor_basic(self):
        tracker, r = self._make_tracker()
        r.incr.return_value = 1
        result = await tracker.increment_visitor()
        assert result == 1
        r.incr.assert_called_once_with("visitors:total")

    @pytest.mark.asyncio
    async def test_increment_visitor_with_session(self):
        tracker, r = self._make_tracker()
        r.incr.return_value = 5
        result = await tracker.increment_visitor(session_id="sess_abc")
        assert result == 5
        r.sadd.assert_called_once_with("visitors:session", "sess_abc")

    @pytest.mark.asyncio
    async def test_increment_without_session_no_sadd(self):
        tracker, r = self._make_tracker()
        r.incr.return_value = 3
        await tracker.increment_visitor(session_id=None)
        r.sadd.assert_not_called()

    @pytest.mark.asyncio
    @patch("backend.infrastructure.visitor_tracking.get_db")
    async def test_sync_to_database_updates_existing(self, mock_get_db):
        tracker, r = self._make_tracker()
        mock_db = MagicMock()
        mock_stats = MagicMock()
        mock_db.query.return_value.first.return_value = mock_stats
        await tracker._sync_to_database(200, db=mock_db)
        assert mock_stats.total_visitors == 200
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    @patch("backend.infrastructure.visitor_tracking.get_db")
    async def test_sync_to_database_creates_new(self, mock_get_db):
        tracker, r = self._make_tracker()
        mock_db = MagicMock()
        mock_db.query.return_value.first.return_value = None
        await tracker._sync_to_database(50, db=mock_db)
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    @patch("backend.infrastructure.visitor_tracking.get_db")
    async def test_sync_to_database_rollback_on_error(self, mock_get_db):
        tracker, r = self._make_tracker()
        mock_db = MagicMock()
        mock_db.query.side_effect = Exception("DB error")
        await tracker._sync_to_database(100, db=mock_db)
        mock_db.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_total_visitors_from_redis(self):
        tracker, r = self._make_tracker()
        r.get.return_value = b"42"
        result = await tracker.get_total_visitors()
        assert result == 42

    @pytest.mark.asyncio
    @patch("backend.infrastructure.visitor_tracking.get_db")
    async def test_get_total_visitors_fallback_to_db(self, mock_get_db):
        tracker, r = self._make_tracker()
        r.get.return_value = None  # Redis empty
        mock_db = MagicMock()
        mock_stats = MagicMock()
        mock_stats.total_visitors = 99
        mock_db.query.return_value.first.return_value = mock_stats
        mock_get_db.return_value = iter([mock_db])
        result = await tracker.get_total_visitors()
        assert result == 99
        r.set.assert_called_once_with("visitors:total", 99)

    def test_get_unique_sessions_today(self):
        tracker, r = self._make_tracker()
        r.scard.return_value = 15
        assert tracker.get_unique_sessions_today() == 15
        r.scard.assert_called_once_with("visitors:session")
