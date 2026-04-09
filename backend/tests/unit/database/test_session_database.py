"""
Tests for backend/database/session_database.py.

Covers:
- get_db generator (yields session, closes on exit)
- Re-exported symbols
"""

from unittest.mock import MagicMock, patch



class TestGetDb:
    """Test the FastAPI dependency generator `get_db`."""

    @patch("backend.database.session_database.SessionLocal")
    def test_yields_session(self, mock_session_cls):
        from backend.database.session_database import get_db

        mock_db = MagicMock()
        mock_session_cls.return_value = mock_db

        gen = get_db()
        session = next(gen)
        assert session is mock_db

    @patch("backend.database.session_database.SessionLocal")
    def test_closes_session_on_exit(self, mock_session_cls):
        from backend.database.session_database import get_db

        mock_db = MagicMock()
        mock_session_cls.return_value = mock_db

        gen = get_db()
        next(gen)
        # Trigger finally block
        try:
            next(gen)
        except StopIteration:
            pass
        mock_db.close.assert_called_once()

    @patch("backend.database.session_database.SessionLocal")
    def test_closes_session_on_exception(self, mock_session_cls):
        from backend.database.session_database import get_db

        mock_db = MagicMock()
        mock_session_cls.return_value = mock_db

        gen = get_db()
        next(gen)
        # Simulate exception during request
        try:
            gen.throw(RuntimeError("request failed"))
        except RuntimeError:
            pass
        mock_db.close.assert_called_once()


class TestReExports:
    """Verify that the module re-exports expected symbols."""

    def test_base_exported(self):
        from backend.database.session_database import Base
        assert Base is not None

    def test_session_local_exported(self):
        from backend.database.session_database import SessionLocal
        assert SessionLocal is not None

    def test_engine_exported(self):
        from backend.database.session_database import engine
        assert engine is not None

    def test_get_db_context_exported(self):
        from backend.database.session_database import get_db_context
        assert callable(get_db_context)
