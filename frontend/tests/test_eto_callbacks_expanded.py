"""
Tests adicionais para frontend/callbacks/eto_callbacks.py — calculate_eto + download tables.

Foco nas branches de validação do calculate_eto (o maior bloco sem cobertura)
e nas funções download_table_* que exportam dados.
"""

from datetime import date, timedelta
from unittest.mock import MagicMock, patch

from dash import no_update


# ---------------------------------------------------------------------------
# calculate_eto  — validation branches
# ---------------------------------------------------------------------------
class TestCalculateEto:
    """Testa todas as validações do calculate_eto (branches ~1083-1750)."""

    def _get_fn(self):
        from frontend.callbacks.eto_callbacks import calculate_eto
        return calculate_eto

    # -- Gate checks --
    def test_none_n_clicks(self):
        result = self._get_fn()(
            None, {"lat": -23, "lon": -46},
            "recent", None, None, None, None, "7", "sess1", None, "en",
        )
        assert result == (None, None, None, None, True, None, None)

    def test_zero_n_clicks(self):
        result = self._get_fn()(
            0, {"lat": -23, "lon": -46},
            "recent", None, None, None, None, "7", "sess1", None, "en",
        )
        assert result == (None, None, None, None, True, None, None)

    # -- Coord validations --
    def test_no_coords_data(self):
        result = self._get_fn()(
            1, None,
            "recent", None, None, None, None, "7", "sess1", None, "en",
        )
        assert result[0] is None
        assert result[2] is not None
        assert result[4] is True

    def test_invalid_coords_range(self):
        result = self._get_fn()(
            1, {"lat": 100, "lon": -46},
            "recent", None, None, None, None, "7", "sess1", None, "en",
        )
        assert result[0] is None
        assert result[2] is not None

    def test_coords_parse_error(self):
        result = self._get_fn()(
            1, {"lat": "abc", "lon": -46},
            "recent", None, None, None, None, "7", "sess1", None, "en",
        )
        assert result[0] is None
        assert result[2] is not None

    # -- Ocean point --
    @patch("frontend.callbacks.eto_callbacks.is_land_point", return_value=False)
    def test_ocean_point(self, mock_land):
        result = self._get_fn()(
            1, {"lat": 0, "lon": 0},
            "recent", None, None, None, None, "7", "sess1", None, "en",
        )
        assert result[0] is None
        assert result[2] is not None

    # -- Data type not selected --
    @patch("frontend.callbacks.eto_callbacks.is_land_point", return_value=True)
    def test_no_data_type(self, mock_land):
        result = self._get_fn()(
            1, {"lat": -23, "lon": -46},
            None, None, None, None, None, "7", "sess1", None, "en",
        )
        assert result[2] is not None

    # -- Historical: missing email --
    @patch("frontend.callbacks.eto_callbacks.is_land_point", return_value=True)
    def test_historical_no_email(self, mock_land):
        result = self._get_fn()(
            1, {"lat": -23, "lon": -46},
            "historical", "2024-01-01", "2024-01-15",
            None, "csv", None, "sess1", None, "en",
        )
        assert result[2] is not None

    @patch("frontend.callbacks.eto_callbacks.is_land_point", return_value=True)
    def test_historical_invalid_email(self, mock_land):
        result = self._get_fn()(
            1, {"lat": -23, "lon": -46},
            "historical", "2024-01-01", "2024-01-15",
            "not-an-email", "csv", None, "sess1", None, "en",
        )
        assert result[2] is not None

    # -- Historical: missing dates → parse_date_from_ui returns None --
    @patch("frontend.callbacks.eto_callbacks.is_land_point", return_value=True)
    @patch("frontend.callbacks.eto_callbacks.parse_date_from_ui", return_value=None)
    def test_historical_no_dates(self, mock_parse, mock_land):
        result = self._get_fn()(
            1, {"lat": -23, "lon": -46},
            "historical", None, None,
            "user@test.com", "csv", None, "sess1", None, "en",
        )
        assert result[2] is not None

    # -- Historical: no file format --
    @patch("frontend.callbacks.eto_callbacks.is_land_point", return_value=True)
    @patch("frontend.callbacks.eto_callbacks.parse_date_from_ui")
    def test_historical_no_file_format(self, mock_parse, mock_land):
        mock_parse.side_effect = [date(2024, 1, 1), date(2024, 1, 15)]
        result = self._get_fn()(
            1, {"lat": -23, "lon": -46},
            "historical", "2024-01-01", "2024-01-15",
            "user@test.com", None, None, "sess1", None, "en",
        )
        assert result[2] is not None

    # -- Historical: start > end --
    @patch("frontend.callbacks.eto_callbacks.is_land_point", return_value=True)
    @patch("frontend.callbacks.eto_callbacks.parse_date_from_ui")
    def test_historical_start_after_end(self, mock_parse, mock_land):
        mock_parse.side_effect = [date(2024, 3, 15), date(2024, 1, 1)]
        result = self._get_fn()(
            1, {"lat": -23, "lon": -46},
            "historical", "2024-03-15", "2024-01-01",
            "user@test.com", "csv", None, "sess1", None, "en",
        )
        assert result[2] is not None

    # -- Historical: dates before 1990 --
    @patch("frontend.callbacks.eto_callbacks.is_land_point", return_value=True)
    @patch("frontend.callbacks.eto_callbacks.parse_date_from_ui")
    def test_historical_before_1990(self, mock_parse, mock_land):
        mock_parse.side_effect = [date(1989, 1, 1), date(1989, 2, 1)]
        result = self._get_fn()(
            1, {"lat": -23, "lon": -46},
            "historical", "1989-01-01", "1989-02-01",
            "user@test.com", "csv", None, "sess1", None, "en",
        )
        assert result[2] is not None

    # -- Historical: future dates --
    @patch("frontend.callbacks.eto_callbacks.is_land_point", return_value=True)
    @patch("frontend.callbacks.eto_callbacks.parse_date_from_ui")
    def test_historical_future_dates(self, mock_parse, mock_land):
        future = date.today() + timedelta(days=30)
        mock_parse.side_effect = [date.today(), future]
        result = self._get_fn()(
            1, {"lat": -23, "lon": -46},
            "historical", str(date.today()), str(future),
            "user@test.com", "csv", None, "sess1", None, "en",
        )
        assert result[2] is not None

    # -- Historical: period > 90 days --
    @patch("frontend.callbacks.eto_callbacks.is_land_point", return_value=True)
    @patch("frontend.callbacks.eto_callbacks.parse_date_from_ui")
    def test_historical_over_90_days(self, mock_parse, mock_land):
        mock_parse.side_effect = [date(2024, 1, 1), date(2024, 6, 1)]
        result = self._get_fn()(
            1, {"lat": -23, "lon": -46},
            "historical", "2024-01-01", "2024-06-01",
            "user@test.com", "csv", None, "sess1", None, "en",
        )
        assert result[2] is not None

    # -- Recent: no period selected --
    @patch("frontend.callbacks.eto_callbacks.is_land_point", return_value=True)
    def test_recent_no_period(self, mock_land):
        result = self._get_fn()(
            1, {"lat": -23, "lon": -46},
            "recent", None, None, None, None,
            None, "sess1", None, "en",
        )
        assert result[2] is not None

    # -- Recent: valid → calls backend (API returns accepted) --
    @patch("frontend.callbacks.eto_callbacks.get_timezone_for_location")
    @patch("requests.post")
    @patch("frontend.callbacks.eto_callbacks.OperationModeDetector")
    @patch("frontend.callbacks.eto_callbacks.is_land_point", return_value=True)
    def test_recent_valid_calls_backend(self, mock_land, mock_detector, mock_post, mock_tz):
        mock_tz.return_value = "America/Sao_Paulo"
        mock_detector.prepare_api_request.return_value = {
            "latitude": -23, "longitude": -46, "period_type": "recent",
        }
        mock_detector.detect_mode.return_value = ("DASHBOARD_CURRENT", {})
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "accepted", "task_id": "task_123",
        }
        mock_post.return_value = mock_response

        result = self._get_fn()(
            1, {"lat": -23, "lon": -46},
            "recent", None, None, None, None, "7", "sess1", None, "en",
        )
        assert result[3] == "task_123"
        assert result[4] is False

    # -- Backend returns 429 (rate limit) --
    @patch("frontend.callbacks.eto_callbacks.get_timezone_for_location")
    @patch("requests.post")
    @patch("frontend.callbacks.eto_callbacks.OperationModeDetector")
    @patch("frontend.callbacks.eto_callbacks.is_land_point", return_value=True)
    def test_rate_limit_429(self, mock_land, mock_detector, mock_post, mock_tz):
        mock_tz.return_value = "UTC"
        mock_detector.prepare_api_request.return_value = {
            "latitude": -23, "longitude": -46, "period_type": "recent",
        }
        mock_detector.detect_mode.return_value = ("DASHBOARD_CURRENT", {})
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.json.return_value = {"detail": "Rate limit exceeded"}
        mock_response.text = "Rate limit exceeded"
        mock_post.return_value = mock_response

        result = self._get_fn()(
            1, {"lat": -23, "lon": -46},
            "recent", None, None, None, None, "7", "sess1", None, "en",
        )
        assert result[2] is not None
        assert result[4] is True

    # -- Backend returns 500 --
    @patch("frontend.callbacks.eto_callbacks.get_timezone_for_location")
    @patch("requests.post")
    @patch("frontend.callbacks.eto_callbacks.OperationModeDetector")
    @patch("frontend.callbacks.eto_callbacks.is_land_point", return_value=True)
    def test_backend_error_500(self, mock_land, mock_detector, mock_post, mock_tz):
        mock_tz.return_value = "UTC"
        mock_detector.prepare_api_request.return_value = {
            "latitude": -23, "longitude": -46, "period_type": "recent",
        }
        mock_detector.detect_mode.return_value = ("DASHBOARD_CURRENT", {})
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_post.return_value = mock_response

        result = self._get_fn()(
            1, {"lat": -23, "lon": -46},
            "recent", None, None, None, None, "7", "sess1", None, "en",
        )
        assert result[2] is not None

    # -- Backend timeout --
    @patch("frontend.callbacks.eto_callbacks.get_timezone_for_location")
    @patch("requests.post")
    @patch("frontend.callbacks.eto_callbacks.OperationModeDetector")
    @patch("frontend.callbacks.eto_callbacks.is_land_point", return_value=True)
    def test_backend_timeout(self, mock_land, mock_detector, mock_post, mock_tz):
        import requests as real_requests
        mock_tz.return_value = "UTC"
        mock_detector.prepare_api_request.return_value = {
            "latitude": -23, "longitude": -46, "period_type": "recent",
        }
        mock_detector.detect_mode.return_value = ("DASHBOARD_CURRENT", {})
        mock_post.side_effect = real_requests.Timeout()

        result = self._get_fn()(
            1, {"lat": -23, "lon": -46},
            "recent", None, None, None, None, "7", "sess1", None, "en",
        )
        assert result[2] is not None

    # -- Backend connection error --
    @patch("frontend.callbacks.eto_callbacks.get_timezone_for_location")
    @patch("requests.post")
    @patch("frontend.callbacks.eto_callbacks.OperationModeDetector")
    @patch("frontend.callbacks.eto_callbacks.is_land_point", return_value=True)
    def test_backend_connection_error(self, mock_land, mock_detector, mock_post, mock_tz):
        import requests as real_requests
        mock_tz.return_value = "UTC"
        mock_detector.prepare_api_request.return_value = {
            "latitude": -23, "longitude": -46, "period_type": "recent",
        }
        mock_detector.detect_mode.return_value = ("DASHBOARD_CURRENT", {})
        mock_post.side_effect = real_requests.ConnectionError()

        result = self._get_fn()(
            1, {"lat": -23, "lon": -46},
            "recent", None, None, None, None, "7", "sess1", None, "en",
        )
        assert result[2] is not None

    # -- Forecast mode → calls backend --
    @patch("frontend.callbacks.eto_callbacks.get_today_for_location", return_value=date.today())
    @patch("frontend.callbacks.eto_callbacks.get_timezone_for_location")
    @patch("requests.post")
    @patch("frontend.callbacks.eto_callbacks.OperationModeDetector")
    @patch("frontend.callbacks.eto_callbacks.is_land_point", return_value=True)
    def test_forecast_mode_valid(self, mock_land, mock_detector, mock_post, mock_tz, mock_today):
        mock_tz.return_value = "UTC"
        mock_detector.prepare_api_request.return_value = {
            "latitude": -23, "longitude": -46, "period_type": "forecast",
        }
        mock_detector.detect_mode.return_value = ("DASHBOARD_FORECAST", {})
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "accepted", "task_id": "task_fc",
        }
        mock_post.return_value = mock_response

        result = self._get_fn()(
            1, {"lat": -23, "lon": -46},
            "forecast", None, None, None, None, "6", "sess1", None, "en",
        )
        assert result[3] == "task_fc"

    # -- Session ID auto-generated --
    @patch("frontend.callbacks.eto_callbacks.get_timezone_for_location")
    @patch("requests.post")
    @patch("frontend.callbacks.eto_callbacks.OperationModeDetector")
    @patch("frontend.callbacks.eto_callbacks.is_land_point", return_value=True)
    def test_auto_generates_session_id(self, mock_land, mock_detector, mock_post, mock_tz):
        mock_tz.return_value = "UTC"
        mock_detector.prepare_api_request.return_value = {
            "latitude": -23, "longitude": -46,
        }
        mock_detector.detect_mode.return_value = ("DASHBOARD_CURRENT", {})
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "accepted", "task_id": "t1"}
        mock_post.return_value = mock_response

        result = self._get_fn()(
            1, {"lat": -23, "lon": -46},
            "recent", None, None, None, None, "7",
            None, None, "en",
        )
        assert result[3] == "t1"

    # -- ValueError from OperationModeDetector: "End date must be <= yesterday" --
    @patch("frontend.callbacks.eto_callbacks.is_land_point", return_value=True)
    @patch("frontend.callbacks.eto_callbacks.parse_date_from_ui")
    def test_value_error_end_date_yesterday(self, mock_parse, mock_land):
        mock_parse.side_effect = [date(2024, 1, 1), date(2024, 1, 15)]
        with patch(
            "frontend.callbacks.eto_callbacks.OperationModeDetector"
        ) as mock_det:
            mock_det.prepare_api_request.side_effect = ValueError(
                "End date must be <= yesterday"
            )
            result = self._get_fn()(
                1, {"lat": -23, "lon": -46},
                "historical", "2024-01-01", "2024-01-15",
                "user@test.com", "csv", None, "sess1", None, "en",
            )
        assert result[2] is not None

    # -- ValueError: "Period must be" --
    @patch("frontend.callbacks.eto_callbacks.is_land_point", return_value=True)
    @patch("frontend.callbacks.eto_callbacks.parse_date_from_ui")
    def test_value_error_period_limit(self, mock_parse, mock_land):
        mock_parse.side_effect = [date(2024, 1, 1), date(2024, 1, 15)]
        with patch(
            "frontend.callbacks.eto_callbacks.OperationModeDetector"
        ) as mock_det:
            mock_det.prepare_api_request.side_effect = ValueError(
                "Period must be <= 90 days"
            )
            result = self._get_fn()(
                1, {"lat": -23, "lon": -46},
                "historical", "2024-01-01", "2024-01-15",
                "user@test.com", "csv", None, "sess1", None, "en",
            )
        assert result[2] is not None

    # -- General ValueError --
    @patch("frontend.callbacks.eto_callbacks.is_land_point", return_value=True)
    @patch("frontend.callbacks.eto_callbacks.parse_date_from_ui")
    def test_general_value_error(self, mock_parse, mock_land):
        mock_parse.side_effect = [date(2024, 1, 1), date(2024, 1, 15)]
        with patch(
            "frontend.callbacks.eto_callbacks.OperationModeDetector"
        ) as mock_det:
            mock_det.prepare_api_request.side_effect = ValueError("Some other error")
            result = self._get_fn()(
                1, {"lat": -23, "lon": -46},
                "historical", "2024-01-01", "2024-01-15",
                "user@test.com", "csv", None, "sess1", None, "en",
            )
        assert result[2] is not None

    # -- General Exception in mode detection --
    @patch("frontend.callbacks.eto_callbacks.is_land_point", return_value=True)
    @patch("frontend.callbacks.eto_callbacks.parse_date_from_ui")
    def test_general_exception_in_mode(self, mock_parse, mock_land):
        mock_parse.side_effect = [date(2024, 1, 1), date(2024, 1, 15)]
        with patch(
            "frontend.callbacks.eto_callbacks.OperationModeDetector"
        ) as mock_det:
            mock_det.prepare_api_request.side_effect = RuntimeError("Crash!")
            result = self._get_fn()(
                1, {"lat": -23, "lon": -46},
                "historical", "2024-01-01", "2024-01-15",
                "user@test.com", "csv", None, "sess1", None, "en",
            )
        assert result[2] is not None

    # -- None lang defaults --
    def test_none_lang_defaults(self):
        result = self._get_fn()(
            1, None,
            "recent", None, None, None, None, "7", "sess1", None, None,
        )
        assert result[2] is not None

    # -- Historical: valid request → API accepted --
    @patch("frontend.callbacks.eto_callbacks.get_timezone_for_location")
    @patch("requests.post")
    @patch("frontend.callbacks.eto_callbacks.OperationModeDetector")
    @patch("frontend.callbacks.eto_callbacks.is_land_point", return_value=True)
    @patch("frontend.callbacks.eto_callbacks.parse_date_from_ui")
    def test_historical_valid_accepted(self, mock_parse, mock_land, mock_detector, mock_post, mock_tz):
        mock_tz.return_value = "America/Sao_Paulo"
        mock_parse.side_effect = [date(2024, 1, 1), date(2024, 1, 15)]
        mock_detector.prepare_api_request.return_value = {
            "latitude": -23, "longitude": -46, "period_type": "historical",
        }
        mock_detector.detect_mode.return_value = ("HISTORICAL_EMAIL", {})
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "accepted", "task_id": "hist_1"}
        mock_post.return_value = mock_response

        result = self._get_fn()(
            1, {"lat": -23, "lon": -46},
            "historical", "2024-01-01", "2024-01-15",
            "user@test.com", "csv", None, "sess1", None, "en",
        )
        assert result[3] == "hist_1"

    # -- Backend 200 but NOT accepted (unexpected JSON) --
    @patch("frontend.callbacks.eto_callbacks.get_timezone_for_location")
    @patch("requests.post")
    @patch("frontend.callbacks.eto_callbacks.OperationModeDetector")
    @patch("frontend.callbacks.eto_callbacks.is_land_point", return_value=True)
    def test_backend_200_not_accepted(self, mock_land, mock_detector, mock_post, mock_tz):
        mock_tz.return_value = "UTC"
        mock_detector.prepare_api_request.return_value = {
            "latitude": -23, "longitude": -46, "period_type": "recent",
        }
        mock_detector.detect_mode.return_value = ("DASHBOARD_CURRENT", {})
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "failed", "error": "no data"}
        mock_post.return_value = mock_response

        result = self._get_fn()(
            1, {"lat": -23, "lon": -46},
            "recent", None, None, None, None, "7", "sess1", None, "en",
        )
        assert result is not None

    # -- General exception in requests.post --
    @patch("frontend.callbacks.eto_callbacks.get_timezone_for_location")
    @patch("requests.post")
    @patch("frontend.callbacks.eto_callbacks.OperationModeDetector")
    @patch("frontend.callbacks.eto_callbacks.is_land_point", return_value=True)
    def test_general_exception_in_request(self, mock_land, mock_detector, mock_post, mock_tz):
        mock_tz.return_value = "UTC"
        mock_detector.prepare_api_request.return_value = {
            "latitude": -23, "longitude": -46, "period_type": "recent",
        }
        mock_detector.detect_mode.return_value = ("DASHBOARD_CURRENT", {})
        mock_post.side_effect = Exception("Unexpected crash")

        result = self._get_fn()(
            1, {"lat": -23, "lon": -46},
            "recent", None, None, None, None, "7", "sess1", None, "en",
        )
        assert result[2] is not None

    # -- manual_elevation is passed to payload --
    @patch("frontend.callbacks.eto_callbacks.get_timezone_for_location")
    @patch("requests.post")
    @patch("frontend.callbacks.eto_callbacks.OperationModeDetector")
    @patch("frontend.callbacks.eto_callbacks.is_land_point", return_value=True)
    def test_manual_elevation_passed(self, mock_land, mock_detector, mock_post, mock_tz):
        mock_tz.return_value = "UTC"
        mock_detector.prepare_api_request.return_value = {
            "latitude": -23, "longitude": -46, "period_type": "recent",
        }
        mock_detector.detect_mode.return_value = ("DASHBOARD_CURRENT", {})
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "accepted", "task_id": "elev1"}
        mock_post.return_value = mock_response

        result = self._get_fn()(
            1, {"lat": -23, "lon": -46},
            "recent", None, None, None, None, "7", "sess1",
            850, "en",
        )
        assert result[3] == "elev1"
        call_kwargs = mock_post.call_args
        payload_sent = call_kwargs[1]["json"] if "json" in call_kwargs[1] else call_kwargs[0][1]
        assert payload_sent.get("elevation") == 850.0


# ---------------------------------------------------------------------------
# download_table_climate
# ---------------------------------------------------------------------------
class TestDownloadTableClimate:
    def _get_fn(self):
        from frontend.callbacks.eto_callbacks import download_table_climate
        return download_table_climate

    def test_no_data_returns_no_update(self):
        assert self._get_fn()(1, 0, None, "en") is no_update

    def test_no_clicks_returns_no_update(self):
        assert self._get_fn()(None, None, {"records": [{"a": 1}]}, "en") is no_update

    def test_empty_records_returns_no_update(self):
        assert self._get_fn()(1, 0, {"records": []}, "en") is no_update

    @patch("frontend.callbacks.eto_callbacks._is_excel_trigger", return_value=False)
    def test_valid_csv_download(self, mock_trigger):
        records = [
            {"tmax_c": 35, "tmin_c": 20, "humidity_pct": 60,
             "wind_ms": 2, "radiation_mj_m2": 18, "precip_mm": 0,
             "et0_mm_day": 5.1, "date": "2024-01-01"},
        ]
        result = self._get_fn()(1, 0, {"records": records}, "en")
        assert result is not no_update

    @patch("frontend.callbacks.eto_callbacks._is_excel_trigger", return_value=True)
    def test_valid_excel_download(self, mock_trigger):
        records = [
            {"tmax_c": 35, "tmin_c": 20, "humidity_pct": 60,
             "wind_ms": 2, "radiation_mj_m2": 18, "precip_mm": 0,
             "et0_mm_day": 5.1, "date": "2024-01-01"},
        ]
        result = self._get_fn()(0, 1, {"records": records}, "pt")
        assert result is not no_update


# ---------------------------------------------------------------------------
# download_table_stats
# ---------------------------------------------------------------------------
class TestDownloadTableStats:
    def _get_fn(self):
        from frontend.callbacks.eto_callbacks import download_table_stats
        return download_table_stats

    def test_no_data_returns_no_update(self):
        assert self._get_fn()(1, 0, None, "en") is no_update

    def test_no_clicks_returns_no_update(self):
        assert self._get_fn()(None, None, {"records": [{"a": 1}]}, "en") is no_update

    def test_empty_records_returns_no_update(self):
        assert self._get_fn()(1, 0, {"records": []}, "en") is no_update

    @patch("frontend.callbacks.eto_callbacks._is_excel_trigger", return_value=False)
    def test_valid_stats_csv(self, mock_trigger):
        records = [
            {"tmax_c": 35, "tmin_c": 20, "humidity_pct": 60,
             "wind_ms": 2, "radiation_mj_m2": 18, "precip_mm": 0.5,
             "et0_mm_day": 5.1},
            {"tmax_c": 32, "tmin_c": 18, "humidity_pct": 55,
             "wind_ms": 3, "radiation_mj_m2": 20, "precip_mm": 1.0,
             "et0_mm_day": 4.8},
        ]
        result = self._get_fn()(1, 0, {"records": records, "mode": "DASHBOARD_CURRENT"}, "pt")
        assert result is not no_update

    @patch("frontend.callbacks.eto_callbacks._is_excel_trigger", return_value=False)
    def test_forecast_mode_stats(self, mock_trigger):
        records = [
            {"tmax_c": 35, "tmin_c": 20, "et0_mm_day": 5.1},
            {"tmax_c": 32, "tmin_c": 18, "et0_mm_day": 4.8},
        ]
        result = self._get_fn()(1, 0, {"records": records, "mode": "DASHBOARD_FORECAST"}, "en")
        assert result is not no_update

    def test_no_numeric_columns_returns_no_update(self):
        records = [{"date": "2024-01-01", "name": "test"}]
        assert self._get_fn()(1, 0, {"records": records}, "en") is no_update


# ---------------------------------------------------------------------------
# download_table_eto_summary
# ---------------------------------------------------------------------------
class TestDownloadTableEtoSummary:
    def _get_fn(self):
        from frontend.callbacks.eto_callbacks import download_table_eto_summary
        return download_table_eto_summary

    def test_no_data_returns_no_update(self):
        assert self._get_fn()(1, 0, None, "en") is no_update

    def test_empty_records(self):
        assert self._get_fn()(1, 0, {"records": []}, "en") is no_update

    def test_missing_required_cols(self):
        records = [{"tmax_c": 35}]
        assert self._get_fn()(1, 0, {"records": records}, "en") is no_update

    @patch("frontend.callbacks.eto_callbacks._is_excel_trigger", return_value=False)
    def test_valid_eto_summary(self, mock_trigger):
        records = [
            {"date": "2024-01-01", "precip_mm": 2.0, "et0_mm_day": 5.1},
            {"date": "2024-01-02", "precip_mm": 0.0, "et0_mm_day": 4.8},
        ]
        result = self._get_fn()(1, 0, {"records": records}, "pt")
        assert result is not no_update


# ---------------------------------------------------------------------------
# download_table_normality
# ---------------------------------------------------------------------------
class TestDownloadTableNormality:
    def _get_fn(self):
        from frontend.callbacks.eto_callbacks import download_table_normality
        return download_table_normality

    def test_no_data_returns_no_update(self):
        assert self._get_fn()(1, 0, None, "en") is no_update

    def test_forecast_mode_returns_no_update(self):
        data = {"records": [{"tmax_c": 35}], "mode": "DASHBOARD_FORECAST"}
        assert self._get_fn()(1, 0, data, "en") is no_update

    def test_empty_records(self):
        assert self._get_fn()(1, 0, {"records": []}, "en") is no_update

    @patch("frontend.callbacks.eto_callbacks._is_excel_trigger", return_value=False)
    def test_valid_normality(self, mock_trigger):
        records = [
            {"tmax_c": 30 + i * 0.5, "tmin_c": 18 + i * 0.3, "et0_mm_day": 4 + i * 0.1}
            for i in range(10)
        ]
        result = self._get_fn()(1, 0, {"records": records, "mode": "DASHBOARD_CURRENT"}, "en")
        assert result is not no_update

    def test_no_numeric_columns_returns_no_update(self):
        records = [{"date": "2024-01-01", "name": "test"}]
        assert self._get_fn()(1, 0, {"records": records, "mode": "DASHBOARD_CURRENT"}, "en") is no_update


# ---------------------------------------------------------------------------
# update_progress
# ---------------------------------------------------------------------------
class TestUpdateProgress:
    def _get_fn(self):
        from frontend.callbacks.eto_callbacks import update_progress
        return update_progress

    def test_no_task_id(self):
        result = self._get_fn()(1, None, "DASHBOARD_CURRENT", "en")
        assert result[0] is None
        assert result[2] is True

    def test_no_task_id_none_lang(self):
        result = self._get_fn()(1, None, "DASHBOARD_CURRENT", None)
        assert result[0] is None

    @patch("redis.Redis")
    def test_task_pending_shows_spinner(self, mock_redis_cls):
        mock_r = MagicMock()
        mock_r.get.return_value = None
        mock_redis_cls.return_value = mock_r
        result = self._get_fn()(1, "task_abc", "DASHBOARD_CURRENT", "en")
        assert result[0] is not None
        assert result[2] is False

    @patch("redis.Redis")
    def test_task_success_with_data(self, mock_redis_cls):
        import json
        task_result = {
            "status": "SUCCESS",
            "result": {
                "records": [{"tmax_c": 35, "et0_mm_day": 5.0}],
                "metadata": {"mode": "DASHBOARD_CURRENT"},
            },
        }
        mock_r = MagicMock()
        mock_r.get.return_value = json.dumps(task_result)
        mock_redis_cls.return_value = mock_r
        result = self._get_fn()(1, "task_ok", "DASHBOARD_CURRENT", "en")
        assert result[2] is True

    @patch("redis.Redis")
    def test_task_failure(self, mock_redis_cls):
        import json
        task_result = {
            "status": "FAILURE",
            "result": "Something went wrong",
            "traceback": "...",
        }
        mock_r = MagicMock()
        mock_r.get.return_value = json.dumps(task_result)
        mock_redis_cls.return_value = mock_r
        result = self._get_fn()(1, "task_fail", "DASHBOARD_CURRENT", "en")
        assert result[2] is True

    @patch("redis.Redis")
    def test_redis_connection_error(self, mock_redis_cls):
        mock_redis_cls.side_effect = Exception("Connection refused")
        result = self._get_fn()(1, "task_x", "DASHBOARD_CURRENT", "en")
        # Exception keeps interval running (False) to retry
        assert result[2] is False
