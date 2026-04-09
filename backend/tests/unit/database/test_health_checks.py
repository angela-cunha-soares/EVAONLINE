"""
Unit Tests – backend.database.health_checks

All external dependencies (SessionLocal, engine, get_redis_client) are mocked
so tests run without Docker services.
"""

from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.exc import SQLAlchemyError


# ===================================================================
# check_database_connection
# ===================================================================

class TestCheckDatabaseConnection:
    """Tests for health_checks.check_database_connection"""

    @patch("backend.database.health_checks.SessionLocal")
    def test_healthy(self, mock_session_local):
        from backend.database.health_checks import check_database_connection

        mock_session = MagicMock()
        mock_session.execute.return_value.fetchone.return_value = (1,)
        mock_session_local.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_session_local.return_value.__exit__ = MagicMock(return_value=False)

        result = check_database_connection()
        assert result["status"] == "healthy"
        assert "response_time" in result
        assert result["database"] == "postgresql"

    @patch("backend.database.health_checks.SessionLocal")
    def test_unhealthy_wrong_result(self, mock_session_local):
        from backend.database.health_checks import check_database_connection

        mock_session = MagicMock()
        mock_session.execute.return_value.fetchone.return_value = (99,)
        mock_session_local.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_session_local.return_value.__exit__ = MagicMock(return_value=False)

        result = check_database_connection()
        assert result["status"] == "unhealthy"

    @patch("backend.database.health_checks.SessionLocal")
    def test_unhealthy_exception(self, mock_session_local):
        from backend.database.health_checks import check_database_connection

        mock_session_local.return_value.__enter__ = MagicMock(
            side_effect=SQLAlchemyError("connection refused")
        )
        mock_session_local.return_value.__exit__ = MagicMock(return_value=False)

        result = check_database_connection()
        assert result["status"] == "unhealthy"
        assert "connection refused" in result["message"]


# ===================================================================
# check_redis_connection
# ===================================================================

class TestCheckRedisConnection:
    """Tests for health_checks.check_redis_connection"""

    @patch("backend.database.health_checks.get_redis_client")
    def test_healthy(self, mock_get_redis):
        from backend.database.health_checks import check_redis_connection

        mock_redis = MagicMock()
        mock_redis.ping.return_value = True
        mock_redis.info.return_value = {
            "used_memory_human": "1.5M",
            "connected_clients": 3,
        }
        mock_get_redis.return_value = mock_redis

        result = check_redis_connection()
        assert result["status"] == "healthy"
        assert result["cache"] == "redis"
        assert result["memory_used"] == "1.5M"
        assert result["connected_clients"] == 3

    @patch("backend.database.health_checks.get_redis_client")
    def test_unhealthy_exception(self, mock_get_redis):
        from backend.database.health_checks import check_redis_connection

        mock_get_redis.side_effect = Exception("Redis offline")

        result = check_redis_connection()
        assert result["status"] == "unhealthy"
        assert "Redis offline" in result["message"]


# ===================================================================
# get_database_metrics
# ===================================================================

class TestGetDatabaseMetrics:
    """Tests for health_checks.get_database_metrics"""

    @patch("backend.database.health_checks.engine")
    @patch("backend.database.health_checks.SessionLocal")
    def test_returns_metrics(self, mock_session_local, mock_engine):
        from backend.database.health_checks import get_database_metrics

        mock_session = MagicMock()
        # First query: active_connections
        mock_session.execute.return_value.fetchone.side_effect = [
            (5,),       # active_connections
            ("128 MB",),  # db_size
            (12,),      # table_count
        ]
        mock_session_local.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_session_local.return_value.__exit__ = MagicMock(return_value=False)

        mock_pool = MagicMock()
        mock_pool.size.return_value = 10
        mock_pool.checkedout.return_value = 2
        mock_pool.overflow.return_value = 0
        mock_engine.pool = mock_pool

        result = get_database_metrics()
        assert result["active_connections"] == 5
        assert result["database_size"] == "128 MB"
        assert result["table_count"] == 12

    @patch("backend.database.health_checks.SessionLocal")
    def test_error_returns_dict(self, mock_session_local):
        from backend.database.health_checks import get_database_metrics

        mock_session_local.return_value.__enter__ = MagicMock(
            side_effect=SQLAlchemyError("query failed")
        )
        mock_session_local.return_value.__exit__ = MagicMock(return_value=False)

        result = get_database_metrics()
        assert "error" in result


# ===================================================================
# perform_full_health_check
# ===================================================================

class TestPerformFullHealthCheck:
    """Tests for health_checks.perform_full_health_check"""

    @patch("backend.database.health_checks.get_database_metrics")
    @patch("backend.database.health_checks.check_redis_connection")
    @patch("backend.database.health_checks.check_database_connection")
    def test_all_healthy(self, mock_db, mock_redis, mock_metrics):
        from backend.database.health_checks import perform_full_health_check

        mock_db.return_value = {"status": "healthy", "response_time": 1.0, "database": "postgresql", "message": "ok"}
        mock_redis.return_value = {"status": "healthy", "response_time": 0.5, "cache": "redis", "message": "ok"}
        mock_metrics.return_value = {"active_connections": 5}

        result = perform_full_health_check()
        assert result["overall_status"] == "healthy"
        assert "database" in result["checks"]
        assert "redis" in result["checks"]
        assert "metrics" in result

    @patch("backend.database.health_checks.get_database_metrics")
    @patch("backend.database.health_checks.check_redis_connection")
    @patch("backend.database.health_checks.check_database_connection")
    def test_db_unhealthy(self, mock_db, mock_redis, mock_metrics):
        from backend.database.health_checks import perform_full_health_check

        mock_db.return_value = {"status": "unhealthy", "response_time": 5.0, "database": "postgresql", "message": "down"}
        mock_redis.return_value = {"status": "healthy", "response_time": 0.5, "cache": "redis", "message": "ok"}

        result = perform_full_health_check()
        assert result["overall_status"] == "unhealthy"

    @patch("backend.database.health_checks.get_database_metrics")
    @patch("backend.database.health_checks.check_redis_connection")
    @patch("backend.database.health_checks.check_database_connection")
    def test_redis_unhealthy(self, mock_db, mock_redis, mock_metrics):
        from backend.database.health_checks import perform_full_health_check

        mock_db.return_value = {"status": "healthy", "response_time": 1.0, "database": "postgresql", "message": "ok"}
        mock_redis.return_value = {"status": "unhealthy", "response_time": 5.0, "cache": "redis", "message": "down"}
        mock_metrics.return_value = {"active_connections": 5}

        result = perform_full_health_check()
        assert result["overall_status"] == "unhealthy"


# ===================================================================
# database_monitoring_context
# ===================================================================

class TestDatabaseMonitoringContext:
    """Tests for health_checks.database_monitoring_context"""

    def test_context_manager_success(self):
        from backend.database.health_checks import database_monitoring_context

        with database_monitoring_context("test_op"):
            pass  # no exception → logged as success

    def test_context_manager_exception_propagates(self):
        from backend.database.health_checks import database_monitoring_context

        with pytest.raises(ValueError, match="boom"):
            with database_monitoring_context("test_op"):
                raise ValueError("boom")
