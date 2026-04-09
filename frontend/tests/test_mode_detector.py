"""Tests for frontend.utils.mode_detector module."""

import pytest
from datetime import date, datetime, timedelta
from unittest.mock import patch, MagicMock


# ============================================================================
# Tests for parse_date_from_ui
# ============================================================================
class TestParseDateFromUi:
    """Tests for parse_date_from_ui function."""

    def setup_method(self):
        from frontend.utils.mode_detector import parse_date_from_ui
        self.parse = parse_date_from_ui

    def test_none_input(self):
        assert self.parse(None) is None

    def test_empty_string(self):
        assert self.parse("") is None

    def test_whitespace_string(self):
        assert self.parse("   ") is None

    def test_date_object_passthrough(self):
        d = date(2024, 6, 15)
        assert self.parse(d) == d

    def test_datetime_object_extracts_date(self):
        dt = datetime(2024, 6, 15, 10, 30, 0)
        # datetime is subclass of date, so isinstance(dt, date) is True
        # Function returns the datetime as-is; check it represents the right date
        result = self.parse(dt)
        assert result.year == 2024
        assert result.month == 6
        assert result.day == 15

    def test_iso_format(self):
        assert self.parse("2024-06-15") == date(2024, 6, 15)

    def test_iso_format_with_time(self):
        assert self.parse("2024-06-15T10:30:00") == date(2024, 6, 15)

    def test_brazilian_format(self):
        assert self.parse("15/06/2024") == date(2024, 6, 15)

    def test_invalid_string(self):
        assert self.parse("not-a-date") is None

    def test_numeric_input(self):
        # str(123) = "123" which can't be parsed
        assert self.parse(123) is None


# ============================================================================
# Tests for format_date_for_display
# ============================================================================
class TestFormatDateForDisplay:
    """Tests for format_date_for_display function."""

    def setup_method(self):
        from frontend.utils.mode_detector import format_date_for_display
        self.fmt = format_date_for_display

    def test_basic_format(self):
        assert self.fmt(date(2024, 1, 5)) == "05/01/2024"

    def test_end_of_year(self):
        assert self.fmt(date(2024, 12, 31)) == "31/12/2024"

    def test_leap_day(self):
        assert self.fmt(date(2024, 2, 29)) == "29/02/2024"


# ============================================================================
# Tests for get_timezone_for_location
# ============================================================================
class TestGetTimezoneForLocation:
    """Tests for get_timezone_for_location function."""

    def setup_method(self):
        from frontend.utils.mode_detector import get_timezone_for_location
        self.get_tz = get_timezone_for_location

    def test_sao_paulo(self):
        tz = self.get_tz(-23.55, -46.63)
        assert "Sao_Paulo" in str(tz) or "America" in str(tz)

    def test_london(self):
        tz = self.get_tz(51.5, -0.12)
        assert "London" in str(tz) or "Europe" in str(tz)

    def test_tokyo(self):
        tz = self.get_tz(35.68, 139.69)
        assert "Tokyo" in str(tz) or "Asia" in str(tz)

    def test_ocean_fallback(self):
        """Ocean point should use longitude-based fallback."""
        # Middle of the Pacific
        tz = self.get_tz(0.0, -170.0)
        # Should return some timezone (either found or fallback)
        assert tz is not None

    def test_returns_pytz_timezone(self):
        import pytz
        tz = self.get_tz(-15.79, -47.88)
        assert isinstance(tz, pytz.BaseTzInfo)


# ============================================================================
# Tests for get_today_for_location
# ============================================================================
class TestGetTodayForLocation:
    """Tests for get_today_for_location function."""

    def setup_method(self):
        from frontend.utils.mode_detector import get_today_for_location
        self.get_today = get_today_for_location

    def test_returns_date(self):
        result = self.get_today(-23.55, -46.63)
        assert isinstance(result, date)

    def test_nearby_to_utc(self):
        """Date should be close to UTC date (within 1 day)."""
        from datetime import timezone
        utc_date = datetime.now(timezone.utc).date()
        result = self.get_today(-23.55, -46.63)
        diff = abs((result - utc_date).days)
        assert diff <= 1


# ============================================================================
# Tests for get_today_local
# ============================================================================
class TestGetTodayLocal:
    """Tests for get_today_local (São Paulo fallback)."""

    def setup_method(self):
        from frontend.utils.mode_detector import get_today_local
        self.get_today = get_today_local

    def test_returns_date(self):
        assert isinstance(self.get_today(), date)

    def test_close_to_utc(self):
        from datetime import timezone
        utc_date = datetime.now(timezone.utc).date()
        result = self.get_today()
        diff = abs((result - utc_date).days)
        assert diff <= 1


# ============================================================================
# Tests for is_land_point
# ============================================================================
class TestIsLandPoint:
    """Tests for is_land_point function (mocked HTTP)."""

    def setup_method(self):
        from frontend.utils.mode_detector import is_land_point, _is_land_cached
        self.is_land = is_land_point
        # Clear the cache before each test
        _is_land_cached.cache_clear()

    @patch("httpx.get")
    def test_definite_land_with_timezone_and_positive_elevation(self, mock_get):
        """Point with timezone + positive elevation = land."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "status": "OK",
            "results": [{"elevation": 800}],
        }
        mock_get.return_value = mock_resp

        assert self.is_land(-15.79, -47.88) is True

    @patch("httpx.get")
    def test_ocean_point_negative_elevation(self, mock_get):
        """Point with timezone but negative elevation = ocean."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "status": "OK",
            "results": [{"elevation": -500}],
        }
        mock_get.return_value = mock_resp

        from frontend.utils.mode_detector import _is_land_cached
        _is_land_cached.cache_clear()
        assert self.is_land(-15.79, -47.88) is False

    @patch("httpx.get")
    def test_api_failure_trusts_timezone(self, mock_get):
        """If API fails but timezone exists, trust timezone = land."""
        mock_get.side_effect = Exception("Network error")

        from frontend.utils.mode_detector import _is_land_cached
        _is_land_cached.cache_clear()
        # Brasilia has a timezone, so should return True despite API failure
        assert self.is_land(-15.79, -47.88) is True


# ============================================================================
# Tests for OperationModeDetector
# ============================================================================
class TestOperationModeDetector:
    """Tests for OperationModeDetector class."""

    def setup_method(self):
        from frontend.utils.mode_detector import OperationModeDetector
        self.detector = OperationModeDetector

    # --- detect_mode ---
    def test_detect_mode_historical(self):
        mode, config = self.detector.detect_mode("historical")
        assert mode == "HISTORICAL_EMAIL"
        assert config["requires_email"] is True

    def test_detect_mode_recent(self):
        mode, config = self.detector.detect_mode("recent")
        assert mode == "DASHBOARD_CURRENT"
        assert config["requires_email"] is False

    def test_detect_mode_forecast(self):
        mode, config = self.detector.detect_mode("forecast")
        assert mode == "DASHBOARD_FORECAST"
        assert config["requires_email"] is False

    def test_detect_mode_invalid(self):
        with pytest.raises(ValueError, match="Unknown operation mode"):
            self.detector.detect_mode("invalid_mode")

    # --- validate_dates ---
    def test_validate_historical_valid(self):
        start = date(2024, 1, 1)
        end = date(2024, 1, 30)
        valid, msg = self.detector.validate_dates(
            "HISTORICAL_EMAIL", start, end
        )
        assert valid is True
        assert "30 days" in msg

    def test_validate_historical_before_1990(self):
        start = date(1989, 12, 31)
        end = date(1990, 1, 15)
        valid, msg = self.detector.validate_dates(
            "HISTORICAL_EMAIL", start, end
        )
        assert valid is False
        assert "1990" in msg

    def test_validate_historical_too_long(self):
        start = date(2024, 1, 1)
        end = date(2024, 6, 1)  # >90 days
        valid, msg = self.detector.validate_dates(
            "HISTORICAL_EMAIL", start, end
        )
        assert valid is False
        assert "90" in msg

    def test_validate_historical_future_end(self):
        start = date(2024, 1, 1)
        end = date.today() + timedelta(days=10)
        valid, msg = self.detector.validate_dates(
            "HISTORICAL_EMAIL", start, end
        )
        assert valid is False

    def test_validate_current_valid(self):
        today = date.today()
        start = today - timedelta(days=6)  # 7-day period
        valid, msg = self.detector.validate_dates(
            "DASHBOARD_CURRENT", start, today
        )
        assert valid is True

    def test_validate_current_bad_period(self):
        today = date.today()
        start = today - timedelta(days=4)  # 5-day period (not allowed)
        valid, msg = self.detector.validate_dates(
            "DASHBOARD_CURRENT", start, today
        )
        assert valid is False

    def test_validate_current_not_ending_today(self):
        yesterday = date.today() - timedelta(days=1)
        start = yesterday - timedelta(days=6)
        valid, msg = self.detector.validate_dates(
            "DASHBOARD_CURRENT", start, yesterday
        )
        assert valid is False
        assert "today" in msg

    def test_validate_forecast_valid(self):
        today = date.today()
        end = today + timedelta(days=5)
        valid, msg = self.detector.validate_dates(
            "DASHBOARD_FORECAST", today, end
        )
        assert valid is True

    def test_validate_forecast_wrong_period(self):
        today = date.today()
        end = today + timedelta(days=10)
        valid, msg = self.detector.validate_dates(
            "DASHBOARD_FORECAST", today, end
        )
        assert valid is False

    def test_validate_unknown_mode(self):
        valid, msg = self.detector.validate_dates(
            "UNKNOWN_MODE", date.today(), date.today()
        )
        assert valid is False

    # --- get_mode_info ---
    def test_get_mode_info_valid(self):
        info = self.detector.get_mode_info("HISTORICAL_EMAIL")
        assert "description" in info
        assert "sources" in info

    def test_get_mode_info_invalid(self):
        assert self.detector.get_mode_info("NONEXISTENT") == {}

    # --- get_available_sources ---
    def test_get_sources_historical(self):
        sources = self.detector.get_available_sources("HISTORICAL_EMAIL")
        assert "nasa_power" in sources

    def test_get_sources_forecast(self):
        sources = self.detector.get_available_sources("DASHBOARD_FORECAST")
        assert "openmeteo_forecast" in sources

    def test_get_sources_invalid(self):
        assert self.detector.get_available_sources("NONEXISTENT") == []

    # --- prepare_api_request ---
    def test_prepare_request_historical(self):
        start = date(2024, 1, 1)
        end = date(2024, 1, 15)
        payload = self.detector.prepare_api_request(
            ui_selection="historical",
            latitude=-15.79,
            longitude=-47.88,
            start_date=start,
            end_date=end,
            email="user@example.com",
        )
        assert payload["lat"] == -15.79
        assert payload["lng"] == -47.88
        assert payload["period_type"] == "historical_email"
        assert payload["email"] == "user@example.com"

    def test_prepare_request_recent(self):
        payload = self.detector.prepare_api_request(
            ui_selection="recent",
            latitude=-23.55,
            longitude=-46.63,
            period_days=7,
        )
        assert payload["period_type"] == "dashboard_current"
        assert payload["email"] is None

    def test_prepare_request_forecast(self):
        payload = self.detector.prepare_api_request(
            ui_selection="forecast",
            latitude=35.68,
            longitude=139.69,
        )
        assert payload["period_type"] == "dashboard_forecast"

    def test_prepare_request_historical_no_dates(self):
        with pytest.raises(ValueError, match="requires start_date"):
            self.detector.prepare_api_request(
                ui_selection="historical",
                latitude=-15.79,
                longitude=-47.88,
            )

    def test_prepare_request_recent_no_period(self):
        with pytest.raises(ValueError, match="requires period_days"):
            self.detector.prepare_api_request(
                ui_selection="recent",
                latitude=-15.79,
                longitude=-47.88,
            )

    def test_prepare_request_invalid_selection(self):
        with pytest.raises(ValueError, match="Unknown operation mode"):
            self.detector.prepare_api_request(
                ui_selection="invalid",
                latitude=-15.79,
                longitude=-47.88,
            )

    # --- MODE_MAPPING ---
    def test_mode_mapping_coverage(self):
        assert "historical" in self.detector.MODE_MAPPING
        assert "recent" in self.detector.MODE_MAPPING
        assert "forecast" in self.detector.MODE_MAPPING


# ============================================================================
# Tests for _get_timezone_finder singleton
# ============================================================================
class TestGetTimezoneFinder:
    """Test the singleton TimezoneFinder helper."""

    def test_returns_same_instance(self):
        from frontend.utils.mode_detector import _get_timezone_finder
        tf1 = _get_timezone_finder()
        tf2 = _get_timezone_finder()
        assert tf1 is tf2
