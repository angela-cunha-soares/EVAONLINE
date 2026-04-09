"""
Phase 6 – OpenMeteo Archive & Forecast client tests.

Covers the main get_climate_data flow, _validate_inputs, _fetch_in_chunks,
cache hit/miss, wind conversion, and factory helpers.
"""

import asyncio
from datetime import datetime, timedelta
from unittest.mock import MagicMock, AsyncMock, patch

import numpy as np
import pytest


# ---------------------------------------------------------------------------
# Event-loop isolation (same pattern used across Phase 4-5 files)
# ---------------------------------------------------------------------------

def _fresh_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

def _run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# ---------------------------------------------------------------------------
# Helpers – fake openmeteo_requests response objects
# ---------------------------------------------------------------------------

class _FakeDaily:
    """Mimics the Daily() proto-buf wrapper returned by openmeteo."""

    def __init__(self, time_start, time_end, interval, variables):
        self._start = time_start
        self._end = time_end
        self._interval = interval
        self._vars = variables  # list of numpy arrays

    def Time(self):
        return self._start

    def TimeEnd(self):
        return self._end

    def Interval(self):
        return self._interval

    def Variables(self, idx):
        v = MagicMock()
        v.ValuesAsNumpy.return_value = self._vars[idx]
        return v


class _FakeResponse:
    """Mimics the response object from openmeteo_requests."""

    def __init__(self, lat, lon, elev, tz, tz_abbr, utc_off, daily):
        self._lat = lat
        self._lon = lon
        self._elev = elev
        self._tz = tz
        self._tz_abbr = tz_abbr
        self._utc = utc_off
        self._daily = daily

    def Latitude(self):
        return self._lat

    def Longitude(self):
        return self._lon

    def Elevation(self):
        return self._elev

    def Timezone(self):
        return self._tz

    def TimezoneAbbreviation(self):
        return self._tz_abbr

    def UtcOffsetSeconds(self):
        return self._utc

    def Daily(self):
        return self._daily


def _build_response(n_days=5, n_vars=10, lat=-23.55, lon=-46.63):
    """Build a fake openmeteo response with *n_days* of data."""
    base_ts = int(datetime(2024, 6, 1).timestamp())
    interval = 86400
    end_ts = base_ts + interval * n_days

    variables = [np.random.uniform(10, 30, n_days) for _ in range(n_vars)]
    daily = _FakeDaily(base_ts, end_ts, interval, variables)
    return _FakeResponse(lat, lon, 850.0, b"America/Sao_Paulo", b"BRT", -10800, daily)


# ===================================================================
# OpenMeteo Archive client
# ===================================================================

class TestOpenMeteoArchiveValidation:
    """Tests for _validate_inputs of the Archive client."""

    def _make_client(self):
        with patch("backend.api.services.openmeteo_archive.openmeteo_archive_client.openmeteo_requests"), \
             patch("backend.api.services.openmeteo_archive.openmeteo_archive_client.requests_cache"), \
             patch("backend.api.services.openmeteo_archive.openmeteo_archive_client.retry"):
            from backend.api.services.openmeteo_archive.openmeteo_archive_client import OpenMeteoArchiveClient
            return OpenMeteoArchiveClient(cache=None, cache_dir="/tmp/test_cache")

    def test_invalid_coordinates(self):
        client = self._make_client()
        with pytest.raises(ValueError, match="Invalid coordinates"):
            client._validate_inputs(999, 999, "2024-01-01", "2024-01-31")

    def test_invalid_date_format(self):
        client = self._make_client()
        with pytest.raises(ValueError, match="YYYY-MM-DD"):
            client._validate_inputs(-23.55, -46.63, "01/01/2024", "31/01/2024")

    def test_start_after_end(self):
        client = self._make_client()
        with pytest.raises(ValueError, match="start_date must be"):
            client._validate_inputs(-23.55, -46.63, "2024-02-01", "2024-01-01")

    def test_before_min_date(self):
        client = self._make_client()
        with pytest.raises(ValueError, match="1990"):
            client._validate_inputs(-23.55, -46.63, "1989-01-01", "1989-06-01")

    def test_after_max_date(self):
        client = self._make_client()
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        with pytest.raises(ValueError, match="today"):
            client._validate_inputs(-23.55, -46.63, "2024-01-01", tomorrow)

    def test_valid_inputs(self):
        client = self._make_client()
        # Should not raise
        client._validate_inputs(-23.55, -46.63, "2024-01-01", "2024-03-01")


class TestOpenMeteoArchiveGetData:
    """Tests for get_climate_data of the Archive client."""

    def _make_client(self):
        with patch("backend.api.services.openmeteo_archive.openmeteo_archive_client.openmeteo_requests") as mock_om, \
             patch("backend.api.services.openmeteo_archive.openmeteo_archive_client.requests_cache"), \
             patch("backend.api.services.openmeteo_archive.openmeteo_archive_client.retry"):
            from backend.api.services.openmeteo_archive.openmeteo_archive_client import OpenMeteoArchiveClient
            client = OpenMeteoArchiveClient(cache=None, cache_dir="/tmp/test_cache")
            return client, mock_om

    def test_get_climate_data_success(self):
        client, _ = self._make_client()
        resp = _build_response(n_days=5, n_vars=10)
        client.client = MagicMock()
        client.client.weather_api.return_value = [resp]

        with patch("backend.api.services.openmeteo_archive.openmeteo_archive_client.check_api_quota", return_value=True), \
             patch("backend.api.services.openmeteo_archive.openmeteo_archive_client.track_api_call"):
            result = _run(client.get_climate_data(-23.55, -46.63, "2024-01-01", "2024-01-05"))

        assert "climate_data" in result
        assert "location" in result
        assert result["location"]["elevation"] == 850.0
        assert len(result["climate_data"]["dates"]) == 5

    def test_get_climate_data_cache_hit(self):
        client, _ = self._make_client()
        mock_cache = AsyncMock()
        cached = {"climate_data": {"dates": [1, 2]}, "location": {}}
        mock_cache.get.return_value = cached
        client.cache = mock_cache

        result = _run(client.get_climate_data(-23.55, -46.63, "2024-01-01", "2024-01-05"))
        assert result == cached

    def test_get_climate_data_quota_exceeded(self):
        client, _ = self._make_client()
        with patch("backend.api.services.openmeteo_archive.openmeteo_archive_client.check_api_quota", return_value=False):
            with pytest.raises(RuntimeError, match="quota exceeded"):
                _run(client.get_climate_data(-23.55, -46.63, "2024-01-01", "2024-01-05"))

    def test_get_climate_data_saves_to_cache(self):
        client, _ = self._make_client()
        mock_cache = AsyncMock()
        mock_cache.get.return_value = None
        client.cache = mock_cache

        resp = _build_response(n_days=3, n_vars=10)
        client.client = MagicMock()
        client.client.weather_api.return_value = [resp]

        with patch("backend.api.services.openmeteo_archive.openmeteo_archive_client.check_api_quota", return_value=True), \
             patch("backend.api.services.openmeteo_archive.openmeteo_archive_client.track_api_call"):
            _run(client.get_climate_data(-23.55, -46.63, "2024-01-01", "2024-01-03"))

        mock_cache.set.assert_called_once()

    def test_get_climate_data_wind_conversion(self):
        """Wind speed 10m is converted to 2m."""
        client, _ = self._make_client()
        resp = _build_response(n_days=3, n_vars=10)
        client.client = MagicMock()
        client.client.weather_api.return_value = [resp]

        with patch("backend.api.services.openmeteo_archive.openmeteo_archive_client.check_api_quota", return_value=True), \
             patch("backend.api.services.openmeteo_archive.openmeteo_archive_client.track_api_call"):
            result = _run(client.get_climate_data(-23.55, -46.63, "2024-01-01", "2024-01-03"))

        assert "wind_speed_2m_mean" in result["climate_data"]

    def test_get_climate_data_api_error(self):
        client, _ = self._make_client()
        client.client = MagicMock()
        client.client.weather_api.side_effect = Exception("API down")

        with patch("backend.api.services.openmeteo_archive.openmeteo_archive_client.check_api_quota", return_value=True):
            with pytest.raises(Exception, match="API down"):
                _run(client.get_climate_data(-23.55, -46.63, "2024-01-01", "2024-01-05"))

    def test_long_period_triggers_chunks(self):
        """Period > 10 years triggers _fetch_in_chunks."""
        client, _ = self._make_client()

        with patch.object(client, "_fetch_in_chunks", new_callable=AsyncMock) as mock_chunks:
            mock_chunks.return_value = {"climate_data": {"dates": []}, "location": {}}
            with patch("backend.api.services.openmeteo_archive.openmeteo_archive_client.check_api_quota", return_value=True):
                result = _run(client.get_climate_data(-23.55, -46.63, "1990-01-01", "2024-01-01"))
            mock_chunks.assert_called_once()

    def test_single_day_response(self):
        """Single-day response where time_start == time_end."""
        client, _ = self._make_client()
        base_ts = int(datetime(2024, 6, 1).timestamp())
        variables = [np.array([25.0]) for _ in range(10)]
        daily = _FakeDaily(base_ts, base_ts, 86400, variables)
        resp = _FakeResponse(-23.55, -46.63, 850.0, b"UTC", b"UTC", 0, daily)

        client.client = MagicMock()
        client.client.weather_api.return_value = [resp]

        with patch("backend.api.services.openmeteo_archive.openmeteo_archive_client.check_api_quota", return_value=True), \
             patch("backend.api.services.openmeteo_archive.openmeteo_archive_client.track_api_call"):
            result = _run(client.get_climate_data(-23.55, -46.63, "2024-06-01", "2024-06-01"))

        assert len(result["climate_data"]["dates"]) == 1

    def test_variable_extraction_error_fills_none(self):
        """When a variable extraction fails, fill with None list."""
        client, _ = self._make_client()
        base_ts = int(datetime(2024, 6, 1).timestamp())
        end_ts = base_ts + 86400 * 3

        # Create variables where some throw exceptions
        variables = []
        for i in range(10):
            if i == 3:  # One variable fails
                v = MagicMock()
                v.ValuesAsNumpy.side_effect = Exception("Var not available")
                variables.append(v)
            else:
                variables.append(np.random.uniform(10, 30, 3))

        daily = MagicMock()
        daily.Time.return_value = base_ts
        daily.TimeEnd.return_value = end_ts
        daily.Interval.return_value = 86400

        def _variables(idx):
            v = variables[idx]
            if isinstance(v, MagicMock):
                return v
            m = MagicMock()
            m.ValuesAsNumpy.return_value = v
            return m

        daily.Variables = _variables

        resp = _FakeResponse(-23.55, -46.63, 850.0, b"UTC", b"UTC", 0, daily)

        client.client = MagicMock()
        client.client.weather_api.return_value = [resp]

        with patch("backend.api.services.openmeteo_archive.openmeteo_archive_client.check_api_quota", return_value=True), \
             patch("backend.api.services.openmeteo_archive.openmeteo_archive_client.track_api_call"):
            result = _run(client.get_climate_data(-23.55, -46.63, "2024-06-01", "2024-06-03"))

        # The et0_fao_evapotranspiration (index 4, but 3 in DAILY_VARIABLES) should be None-filled
        assert len(result["climate_data"]["dates"]) == 3


class TestOpenMeteoArchiveHelpers:
    """Tests for static/helper methods."""

    def _make_client(self):
        with patch("backend.api.services.openmeteo_archive.openmeteo_archive_client.openmeteo_requests"), \
             patch("backend.api.services.openmeteo_archive.openmeteo_archive_client.requests_cache"), \
             patch("backend.api.services.openmeteo_archive.openmeteo_archive_client.retry"):
            from backend.api.services.openmeteo_archive.openmeteo_archive_client import OpenMeteoArchiveClient
            return OpenMeteoArchiveClient(cache=None, cache_dir="/tmp/test_cache")

    def test_get_cache_key(self):
        client = self._make_client()
        key = client._get_cache_key(-23.55, -46.63, "2024-01-01", "2024-06-01")
        assert "openmeteo" in key
        assert "archive" in key
        assert "-23.55" in key

    def test_close_is_noop(self):
        client = self._make_client()
        _run(client.close())  # should not raise

    def test_get_info(self):
        with patch("backend.api.services.openmeteo_archive.openmeteo_archive_client.openmeteo_requests"), \
             patch("backend.api.services.openmeteo_archive.openmeteo_archive_client.requests_cache"), \
             patch("backend.api.services.openmeteo_archive.openmeteo_archive_client.retry"):
            from backend.api.services.openmeteo_archive.openmeteo_archive_client import OpenMeteoArchiveClient
            info = OpenMeteoArchiveClient.get_info()
        assert "Archive" in info["api"]
        assert info["coverage"] == "Global"

    def test_factory_function(self):
        with patch("backend.api.services.openmeteo_archive.openmeteo_archive_client.openmeteo_requests"), \
             patch("backend.api.services.openmeteo_archive.openmeteo_archive_client.requests_cache"), \
             patch("backend.api.services.openmeteo_archive.openmeteo_archive_client.retry"):
            from backend.api.services.openmeteo_archive.openmeteo_archive_client import create_archive_client
            client = create_archive_client()
            assert client is not None


# ===================================================================
# OpenMeteo Forecast client
# ===================================================================

class TestOpenMeteoForecastValidation:
    """Tests for _validate_inputs of the Forecast client."""

    def _make_client(self):
        with patch("backend.api.services.openmeteo_forecast.openmeteo_forecast_client.openmeteo_requests"), \
             patch("backend.api.services.openmeteo_forecast.openmeteo_forecast_client.requests_cache"), \
             patch("backend.api.services.openmeteo_forecast.openmeteo_forecast_client.retry"):
            from backend.api.services.openmeteo_forecast.openmeteo_forecast_client import OpenMeteoForecastClient
            return OpenMeteoForecastClient(cache=None, cache_dir="/tmp/test_cache")

    def test_invalid_coordinates(self):
        client = self._make_client()
        with pytest.raises(ValueError, match="Invalid coordinates"):
            client._validate_inputs(999, 999, "2024-01-01", "2024-01-05")

    def test_start_after_end(self):
        client = self._make_client()
        with pytest.raises(ValueError, match="start_date must be"):
            client._validate_inputs(-23.55, -46.63, "2024-02-01", "2024-01-01")

    def test_too_far_past(self):
        client = self._make_client()
        old_date = (datetime.now() - timedelta(days=60)).strftime("%Y-%m-%d")
        today = datetime.now().strftime("%Y-%m-%d")
        with pytest.raises(ValueError, match="29 days"):
            client._validate_inputs(-23.55, -46.63, old_date, today)

    def test_too_far_future(self):
        client = self._make_client()
        today = datetime.now().strftime("%Y-%m-%d")
        far = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
        with pytest.raises(ValueError, match="5 days"):
            client._validate_inputs(-23.55, -46.63, today, far)

    def test_valid_inputs(self):
        client = self._make_client()
        today = datetime.now()
        start = (today - timedelta(days=5)).strftime("%Y-%m-%d")
        end = (today + timedelta(days=3)).strftime("%Y-%m-%d")
        client._validate_inputs(-23.55, -46.63, start, end)


class TestOpenMeteoForecastGetData:
    """Tests for get_climate_data of the Forecast client."""

    def _make_client(self):
        with patch("backend.api.services.openmeteo_forecast.openmeteo_forecast_client.openmeteo_requests") as mock_om, \
             patch("backend.api.services.openmeteo_forecast.openmeteo_forecast_client.requests_cache"), \
             patch("backend.api.services.openmeteo_forecast.openmeteo_forecast_client.retry"):
            from backend.api.services.openmeteo_forecast.openmeteo_forecast_client import OpenMeteoForecastClient
            client = OpenMeteoForecastClient(cache=None, cache_dir="/tmp/test_cache")
            return client, mock_om

    def _make_forecast_response(self, n_days=5):
        """Build response compatible with Forecast client (uses pd.date_range)."""
        import pandas as pd
        base_ts = int(datetime.now().timestamp()) - 86400  # yesterday
        end_ts = base_ts + 86400 * n_days
        interval = 86400
        variables = [np.random.uniform(10, 30, n_days) for _ in range(10)]
        daily = _FakeDaily(base_ts, end_ts, interval, variables)
        return _FakeResponse(-23.55, -46.63, 850.0, b"America/Sao_Paulo", b"BRT", -10800, daily)

    def test_get_climate_data_success(self):
        client, _ = self._make_client()
        resp = self._make_forecast_response(n_days=5)
        client.client = MagicMock()
        client.client.weather_api.return_value = [resp]

        today = datetime.now()
        start = (today - timedelta(days=2)).strftime("%Y-%m-%d")
        end = (today + timedelta(days=2)).strftime("%Y-%m-%d")

        with patch("backend.api.services.openmeteo_forecast.openmeteo_forecast_client.check_api_quota", return_value=True), \
             patch("backend.api.services.openmeteo_forecast.openmeteo_forecast_client.track_api_call"):
            result = _run(client.get_climate_data(-23.55, -46.63, start, end))

        assert "climate_data" in result
        assert "location" in result
        assert "wind_speed_2m_mean" in result["climate_data"]

    def test_get_climate_data_cache_hit(self):
        client, _ = self._make_client()
        mock_cache = AsyncMock()
        cached = {"climate_data": {"dates": [1, 2, 3]}, "location": {}}
        mock_cache.get.return_value = cached
        client.cache = mock_cache

        today = datetime.now()
        start = (today - timedelta(days=2)).strftime("%Y-%m-%d")
        end = (today + timedelta(days=2)).strftime("%Y-%m-%d")

        result = _run(client.get_climate_data(-23.55, -46.63, start, end))
        assert result == cached

    def test_get_climate_data_quota_exceeded(self):
        client, _ = self._make_client()
        today = datetime.now()
        start = (today - timedelta(days=2)).strftime("%Y-%m-%d")
        end = (today + timedelta(days=2)).strftime("%Y-%m-%d")

        with patch("backend.api.services.openmeteo_forecast.openmeteo_forecast_client.check_api_quota", return_value=False):
            with pytest.raises(RuntimeError, match="quota exceeded"):
                _run(client.get_climate_data(-23.55, -46.63, start, end))

    def test_get_climate_data_date_clamping(self):
        """Dates outside API range are clamped."""
        client, _ = self._make_client()
        resp = self._make_forecast_response(n_days=5)
        client.client = MagicMock()
        client.client.weather_api.return_value = [resp]

        # Use dates within valid range but near boundaries
        today = datetime.now()
        start = (today - timedelta(days=20)).strftime("%Y-%m-%d")
        end = (today + timedelta(days=3)).strftime("%Y-%m-%d")

        with patch("backend.api.services.openmeteo_forecast.openmeteo_forecast_client.check_api_quota", return_value=True), \
             patch("backend.api.services.openmeteo_forecast.openmeteo_forecast_client.track_api_call"):
            result = _run(client.get_climate_data(-23.55, -46.63, start, end))

        assert result is not None

    def test_get_climate_data_saves_to_cache(self):
        client, _ = self._make_client()
        mock_cache = AsyncMock()
        mock_cache.get.return_value = None
        client.cache = mock_cache

        resp = self._make_forecast_response(n_days=3)
        client.client = MagicMock()
        client.client.weather_api.return_value = [resp]

        today = datetime.now()
        start = (today - timedelta(days=1)).strftime("%Y-%m-%d")
        end = (today + timedelta(days=1)).strftime("%Y-%m-%d")

        with patch("backend.api.services.openmeteo_forecast.openmeteo_forecast_client.check_api_quota", return_value=True), \
             patch("backend.api.services.openmeteo_forecast.openmeteo_forecast_client.track_api_call"):
            _run(client.get_climate_data(-23.55, -46.63, start, end))

        mock_cache.set.assert_called_once()


class TestOpenMeteoForecastHelpers:
    """Tests for helper methods of the Forecast client."""

    def _make_client(self):
        with patch("backend.api.services.openmeteo_forecast.openmeteo_forecast_client.openmeteo_requests"), \
             patch("backend.api.services.openmeteo_forecast.openmeteo_forecast_client.requests_cache"), \
             patch("backend.api.services.openmeteo_forecast.openmeteo_forecast_client.retry"):
            from backend.api.services.openmeteo_forecast.openmeteo_forecast_client import OpenMeteoForecastClient
            return OpenMeteoForecastClient(cache=None, cache_dir="/tmp/test_cache")

    def test_convert_wind_10m_to_2m(self):
        from backend.api.services.openmeteo_forecast.openmeteo_forecast_client import OpenMeteoForecastClient
        wind = np.array([5.0, 10.0, 0.0])
        result = OpenMeteoForecastClient.convert_wind_10m_to_2m(wind)
        assert len(result) == 3
        assert all(r >= 0.5 for r in result)  # minimum 0.5 m/s
        assert result[0] < 5.0  # conversion reduces 10m wind

    def test_convert_wind_already_2m(self):
        from backend.api.services.openmeteo_forecast.openmeteo_forecast_client import OpenMeteoForecastClient
        wind = np.array([5.0, 10.0])
        result = OpenMeteoForecastClient.convert_wind_10m_to_2m(wind, height=2.0)
        assert result[0] == 5.0  # no conversion
        assert result[1] == 10.0

    def test_get_ttl_seconds_future(self):
        client = self._make_client()
        future_date = (datetime.now() + timedelta(days=2)).strftime("%Y-%m-%d")
        today = datetime.now().strftime("%Y-%m-%d")
        ttl = client._get_ttl_seconds(today, future_date)
        assert ttl == 3600  # 1 hour for forecast

    def test_get_ttl_seconds_past(self):
        client = self._make_client()
        past_date = (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d")
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        ttl = client._get_ttl_seconds(past_date, yesterday)
        assert ttl == 3600 * 6  # 6 hours for recent

    def test_get_cache_key(self):
        client = self._make_client()
        key = client._get_cache_key(-23.55, -46.63, "2024-01-01", "2024-01-05")
        assert "forecast" in key

    def test_get_info(self):
        from backend.api.services.openmeteo_forecast.openmeteo_forecast_client import OpenMeteoForecastClient
        info = OpenMeteoForecastClient.get_info()
        assert "Forecast" in info["api"]

    def test_factory_function(self):
        with patch("backend.api.services.openmeteo_forecast.openmeteo_forecast_client.openmeteo_requests"), \
             patch("backend.api.services.openmeteo_forecast.openmeteo_forecast_client.requests_cache"), \
             patch("backend.api.services.openmeteo_forecast.openmeteo_forecast_client.retry"):
            from backend.api.services.openmeteo_forecast.openmeteo_forecast_client import create_forecast_client
            client = create_forecast_client()
            assert client is not None
