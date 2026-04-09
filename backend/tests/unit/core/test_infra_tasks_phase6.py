"""
Phase 6 – Infrastructure Celery tasks tests.

Covers:
- process_historical_download (data_download.py) – full pipeline mock
- sync_visitor_data (visitor_sync.py) – Redis→PostgreSQL sync
"""

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest


# ===================================================================
# process_historical_download
# ===================================================================

class TestProcessHistoricalDownload:
    """Tests for the process_historical_download Celery task."""

    # Module path for module-level imports
    _MOD = "backend.infrastructure.celery.tasks.data_download"
    # Source modules for lazy imports inside function body
    _EMAIL = "backend.core.utils.email_utils"
    _DL = "backend.api.services.data_download"
    _PP = "backend.core.data_processing.data_preprocessing"
    # calculate_eto was removed from eto_services → need create=True
    _ETO = "backend.core.eto_calculation.eto_services"

    @pytest.fixture(autouse=True)
    def _patch_metrics(self):
        """Patch Prometheus metrics imported at module level."""
        with patch(f"{self._MOD}.CELERY_TASK_DURATION") as mock_dur, \
             patch(f"{self._MOD}.CELERY_TASKS_TOTAL") as mock_total:
            self.mock_duration = mock_dur
            self.mock_total = mock_total
            yield

    def _get_task_func(self):
        """Get the raw function, bypassing Celery PromiseProxy."""
        from backend.infrastructure.celery.tasks.data_download import (
            process_historical_download,
        )
        return process_historical_download

    def _make_self_mock(self, retries=0):
        """Create a mock for `self` (Celery bind=True context)."""
        ctx = MagicMock()
        ctx.request.retries = retries
        ctx.retry.side_effect = Exception("Retried")
        return ctx

    def test_success_csv(self, tmp_path):
        """Full pipeline success with CSV output."""
        task = self._get_task_func()
        ctx = self._make_self_mock()

        weather_df = pd.DataFrame({
            "date": pd.date_range("2024-01-01", periods=30),
            "T2M_MAX": [30.0] * 30,
            "T2M_MIN": [20.0] * 30,
        })
        processed_df = weather_df.copy()
        # MagicMock avoids real file I/O (to_csv / to_excel)
        mock_eto = MagicMock()
        mock_eto.__len__ = MagicMock(return_value=30)

        with patch(f"{self._EMAIL}.send_email") as mock_send, \
             patch(f"{self._EMAIL}.send_email_with_attachment") as mock_attach, \
             patch(f"{self._DL}.download_weather_data", new=MagicMock(return_value=(weather_df, ["warn1"]))), \
             patch(f"{self._PP}.preprocessing", return_value=(processed_df, [])), \
             patch(f"{self._ETO}.calculate_eto", create=True, return_value=(mock_eto, [])):

            result = task.run.__func__(
                ctx,
                email="user@test.com",
                lat=-23.55,
                lon=-46.63,
                source="nasa_power",
                start_date="2024-01-01",
                end_date="2024-01-30",
                file_format="csv",
            )

        assert result["status"] == "success"
        assert result["rows"] == 30
        assert mock_send.called  # initial confirmation email
        assert mock_attach.called  # email with attachment

    def test_success_excel(self, tmp_path):
        """Excel format output."""
        task = self._get_task_func()
        ctx = self._make_self_mock()

        df = pd.DataFrame({
            "date": pd.date_range("2024-01-01", periods=5),
            "T2M_MAX": [28.0] * 5,
        })

        mock_eto = MagicMock()
        mock_eto.__len__ = MagicMock(return_value=5)

        with patch(f"{self._EMAIL}.send_email"), \
             patch(f"{self._EMAIL}.send_email_with_attachment"), \
             patch(f"{self._DL}.download_weather_data", new=MagicMock(return_value=(df, []))), \
             patch(f"{self._PP}.preprocessing", return_value=(df, [])), \
             patch(f"{self._ETO}.calculate_eto", create=True, return_value=(mock_eto, [])):

            result = task.run.__func__(
                ctx,
                email="user@test.com",
                lat=-23.55,
                lon=-46.63,
                source="data fusion",
                start_date="2024-01-01",
                end_date="2024-01-05",
                file_format="excel",
            )

        assert result["status"] == "success"

    def test_empty_data_raises_valueerror(self):
        """Empty download raises ValueError → no retry."""
        task = self._get_task_func()
        ctx = self._make_self_mock()

        with patch(f"{self._EMAIL}.send_email"), \
             patch(f"{self._EMAIL}.send_email_with_attachment"), \
             patch(f"{self._DL}.download_weather_data", new=MagicMock(return_value=(pd.DataFrame(), []))):

            with pytest.raises(ValueError, match="Nenhum dado"):
                task.run.__func__(
                    ctx,
                    email="user@test.com",
                    lat=-23.55,
                    lon=-46.63,
                    source="nasa_power",
                    start_date="2024-01-01",
                    end_date="2024-01-30",
                )

    def test_none_data_raises_valueerror(self):
        """None download raises ValueError."""
        task = self._get_task_func()
        ctx = self._make_self_mock()

        with patch(f"{self._EMAIL}.send_email"), \
             patch(f"{self._EMAIL}.send_email_with_attachment"), \
             patch(f"{self._DL}.download_weather_data", new=MagicMock(return_value=(None, []))):

            with pytest.raises(ValueError, match="Nenhum dado"):
                task.run.__func__(
                    ctx,
                    email="user@test.com",
                    lat=-23.55,
                    lon=-46.63,
                    source="nasa_power",
                    start_date="2024-01-01",
                    end_date="2024-01-30",
                )

    def test_processing_error_sends_error_email_and_retries(self):
        """Non-ValueError errors send error email and trigger retry."""
        task = self._get_task_func()
        ctx = self._make_self_mock()

        df = pd.DataFrame({
            "date": pd.date_range("2024-01-01", periods=5),
            "T2M_MAX": [28.0] * 5,
        })

        with patch(f"{self._EMAIL}.send_email") as mock_email, \
             patch(f"{self._EMAIL}.send_email_with_attachment"), \
             patch(f"{self._DL}.download_weather_data", new=MagicMock(return_value=(df, []))), \
             patch(f"{self._PP}.preprocessing", side_effect=RuntimeError("Processing failed")):

            with pytest.raises(Exception):
                task.run.__func__(
                    ctx,
                    email="user@test.com",
                    lat=-23.55,
                    lon=-46.63,
                    source="nasa_power",
                    start_date="2024-01-01",
                    end_date="2024-01-05",
                )

        # Error email was sent
        assert mock_email.call_count >= 2  # initial + error email

    def test_metrics_recorded_on_success(self):
        """Prometheus metrics are recorded."""
        task = self._get_task_func()
        ctx = self._make_self_mock()

        df = pd.DataFrame({"date": pd.date_range("2024-01-01", periods=3), "val": [1, 2, 3]})
        mock_eto = MagicMock()
        mock_eto.__len__ = MagicMock(return_value=3)

        with patch(f"{self._EMAIL}.send_email"), \
             patch(f"{self._EMAIL}.send_email_with_attachment"), \
             patch(f"{self._DL}.download_weather_data", new=MagicMock(return_value=(df, []))), \
             patch(f"{self._PP}.preprocessing", return_value=(df, [])), \
             patch(f"{self._ETO}.calculate_eto", create=True, return_value=(mock_eto, [])):

            task.run.__func__(
                ctx,
                email="user@test.com",
                lat=-23.55,
                lon=-46.63,
                source="nasa_power",
                start_date="2024-01-01",
                end_date="2024-01-03",
            )

        self.mock_total.labels.assert_called_with(
            task_name="process_historical_download", status="SUCCESS"
        )


# ===================================================================
# sync_visitor_data
# ===================================================================

class TestSyncVisitorData:
    """Tests for the sync_visitor_data Celery task."""

    _MOD = "backend.infrastructure.celery.tasks.visitor_sync"

    @pytest.fixture(autouse=True)
    def _patch_imports(self):
        """Patch heavy imports: celery_app, get_db, module-level settings."""
        mock_settings = MagicMock()
        mock_settings.REDIS_URL = "redis://localhost:6379/0"

        with patch(f"{self._MOD}.get_db") as mock_db, \
             patch(f"{self._MOD}.settings", mock_settings), \
             patch(f"{self._MOD}.VisitorCounterService") as mock_svc_cls:
            self.mock_db = mock_db
            self.mock_settings = mock_settings
            self.mock_svc_cls = mock_svc_cls

            # get_db returns a generator that yields a session
            mock_session = MagicMock()
            mock_db.return_value = iter([mock_session])

            yield

    def _get_task_func(self):
        """Import the task function. Module-level imports are already patched."""
        from backend.infrastructure.celery.tasks.visitor_sync import (
            sync_visitor_data,
        )
        return sync_visitor_data

    def test_success(self):
        """Successful sync returns result dict."""
        self.mock_svc_cls.return_value.sync_to_database.return_value = {
            "total_visitors": 42,
        }

        with patch("redis.from_url", return_value=MagicMock()):
            task = self._get_task_func()
            result = task()

        assert result["total_visitors"] == 42

    def test_sync_error_in_result(self):
        """Service returns error dict."""
        self.mock_svc_cls.return_value.sync_to_database.return_value = {
            "error": "Redis connection failed",
        }

        with patch("redis.from_url", return_value=MagicMock()):
            task = self._get_task_func()
            result = task()

        assert "error" in result

    def test_exception_returns_error_dict(self):
        """Exception during sync returns error dict."""
        self.mock_svc_cls.side_effect = Exception("Service creation failed")

        with patch("redis.from_url", return_value=MagicMock()):
            task = self._get_task_func()
            result = task()

        assert "error" in result
        assert "Service creation failed" in result["error"]
