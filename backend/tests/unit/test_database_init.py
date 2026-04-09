"""Tests for backend/database/__init__.py."""

from unittest.mock import patch, MagicMock


class TestInitDb:
    @patch("backend.database.engine")
    @patch("backend.database.Base")
    def test_init_db_success(self, mock_base, mock_engine):
        from backend.database import init_db
        init_db()
        mock_base.metadata.create_all.assert_called_once_with(bind=mock_engine)

    @patch("backend.database.engine")
    @patch("backend.database.Base")
    def test_init_db_raises_on_error(self, mock_base, mock_engine):
        import pytest
        mock_base.metadata.create_all.side_effect = Exception("DB error")
        from backend.database import init_db
        with pytest.raises(Exception, match="DB error"):
            init_db()
