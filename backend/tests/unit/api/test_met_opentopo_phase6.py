"""
Phase 6 – MET Norway client & OpenTopo client tests.

Covers get_daily_forecast, _parse_daily_response, cache logic,
retry/error handling for MET Norway, and get_elevation/get_elevations_batch
for OpenTopo.
"""

import asyncio
from datetime import datetime, timedelta
from unittest.mock import MagicMock, AsyncMock, patch

import httpx
import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def _make_httpx_response(status_code=200, json_data=None, headers=None):
    """Build a fake httpx.Response."""
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.headers = headers or {}
    resp.json.return_value = json_data or {}
    resp.raise_for_status = MagicMock()
    if status_code >= 400:
        resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Error", request=MagicMock(), response=resp
        )
    resp.request = MagicMock()
    return resp


# ===================================================================
# MET Norway client
# ===================================================================

class TestMETNorwayClientInit:
    """Tests for MET Norway client initialization and static methods."""

    def _make_client(self):
        from backend.api.services.met_norway.met_norway_client import METNorwayClient
        return METNorwayClient()

    def test_init_default_config(self):
        client = self._make_client()
        assert client.config is not None
        assert "api.met.no" in client.config.base_url

    def test_round_coordinates(self):
        from backend.api.services.met_norway.met_norway_client import METNorwayClient
        lat, lon = METNorwayClient._round_coordinates(-23.550123456, -46.633098765)
        assert lat == -23.5501
        assert lon == -46.6331

    def test_is_in_nordic_region_true(self):
        from backend.api.services.met_norway.met_norway_client import METNorwayClient
        assert METNorwayClient.is_in_nordic_region(60.0, 10.0) is True  # Oslo area

    def test_is_in_nordic_region_false(self):
        from backend.api.services.met_norway.met_norway_client import METNorwayClient
        assert METNorwayClient.is_in_nordic_region(-23.55, -46.63) is False  # São Paulo

    def test_get_recommended_variables_nordic(self):
        from backend.api.services.met_norway.met_norway_client import METNorwayClient
        vars_ = METNorwayClient.get_recommended_variables(60.0, 10.0)
        assert "precipitation_sum" in vars_  # Nordic includes precipitation

    def test_get_recommended_variables_global(self):
        from backend.api.services.met_norway.met_norway_client import METNorwayClient
        vars_ = METNorwayClient.get_recommended_variables(-23.55, -46.63)
        assert "precipitation_sum" not in vars_  # Global skips precipitation

    def test_get_attribution(self):
        client = self._make_client()
        attr = client.get_attribution()
        assert "MET Norway" in attr
        assert "CC BY" in attr

    def test_get_coverage_info(self):
        client = self._make_client()
        info = client.get_coverage_info()
        assert info["region"] == "GLOBAL"
        assert "nordic" in info["quality_tiers"]

    def test_get_data_availability_info(self):
        from backend.api.services.met_norway.met_norway_client import METNorwayClient
        info = METNorwayClient.get_data_availability_info()
        assert info["forecast_horizon_days"] == 5

    def test_factory_function(self):
        from backend.api.services.met_norway.met_norway_client import create_met_norway_client
        client = create_met_norway_client()
        assert client is not None


class TestMETNorwayGetDailyForecast:
    """Tests for get_daily_forecast method."""

    def _make_client_with_mock(self, cache=None):
        from backend.api.services.met_norway.met_norway_client import METNorwayClient
        client = METNorwayClient(cache=cache)
        client.client = AsyncMock(spec=httpx.AsyncClient)
        return client

    def _sample_met_response(self):
        """Build a realistic MET Norway API response."""
        base_time = datetime.now()
        timeseries = []
        for h in range(48):  # 48 hours = 2 days
            ts = base_time + timedelta(hours=h)
            timeseries.append({
                "time": ts.isoformat() + "Z",
                "data": {
                    "instant": {
                        "details": {
                            "air_temperature": 20.0 + h * 0.1,
                            "relative_humidity": 65.0,
                            "wind_speed": 3.5,
                        }
                    },
                    "next_1_hours": {
                        "details": {
                            "precipitation_amount": 0.5
                        }
                    },
                    "next_6_hours": {
                        "details": {
                            "air_temperature_max": 25.0,
                            "air_temperature_min": 15.0,
                            "precipitation_amount": 2.0,
                        }
                    },
                },
            })

        return {
            "geometry": {"coordinates": [-46.63, -23.55, 850]},
            "properties": {"timeseries": timeseries},
        }

    def test_get_daily_forecast_success(self):
        """Full flow: API call → parse → return daily data."""
        client = self._make_client_with_mock()

        mock_resp = _make_httpx_response(
            status_code=200,
            json_data=self._sample_met_response(),
            headers={
                "Last-Modified": "Fri, 01 Jan 2024 00:00:00 GMT",
                "Expires": "Fri, 01 Jan 2099 00:00:00 GMT",
            },
        )
        client.client.get = AsyncMock(return_value=mock_resp)

        result = _run(client.get_daily_forecast(-23.55, -46.63))
        assert isinstance(result, list)

    def test_get_daily_forecast_start_after_end(self):
        """start_date > end_date raises ValueError."""
        client = self._make_client_with_mock()
        start = datetime.now() + timedelta(days=3)
        end = datetime.now()
        with pytest.raises(ValueError, match="start_date must be"):
            _run(client.get_daily_forecast(-23.55, -46.63, start_date=start, end_date=end))

    def test_get_daily_forecast_clamps_to_5_days(self):
        """Period > 5 days is clamped."""
        client = self._make_client_with_mock()

        mock_resp = _make_httpx_response(
            status_code=200,
            json_data=self._sample_met_response(),
            headers={},
        )
        client.client.get = AsyncMock(return_value=mock_resp)

        start = datetime.now()
        end = start + timedelta(days=10)  # Too long

        result = _run(client.get_daily_forecast(-23.55, -46.63, start_date=start, end_date=end))
        # Should not raise, just clamp

    def test_get_daily_forecast_304_not_modified(self):
        """304 response returns cached data."""
        mock_cache = AsyncMock()
        from backend.api.services.met_norway.met_norway_client import METNorwayCacheMetadata, METNorwayDailyData
        cached_data = METNorwayCacheMetadata(
            last_modified="Fri, 01 Jan 2024 00:00:00 GMT",
            expires=datetime.now() + timedelta(hours=1),
            data=[METNorwayDailyData(date=datetime.now(), source="met_norway")],
        )
        # First call: expired cache → return metadata with last_modified
        # Second call after 304: return the updated metadata
        mock_cache.get = AsyncMock(return_value=cached_data.to_json())

        client = self._make_client_with_mock(cache=mock_cache)

        resp_304 = _make_httpx_response(status_code=304, headers={"Expires": "Fri, 01 Jan 2099 00:00:00 GMT"})
        resp_304.raise_for_status = MagicMock()  # 304 doesn't raise
        client.client.get = AsyncMock(return_value=resp_304)

        result = _run(client.get_daily_forecast(-23.55, -46.63))
        assert isinstance(result, list)

    def test_get_daily_forecast_429_rate_limit(self):
        """429 response raises without retry."""
        client = self._make_client_with_mock()

        resp_429 = _make_httpx_response(status_code=429, headers={"Retry-After": "60"})
        client.client.get = AsyncMock(return_value=resp_429)

        with pytest.raises(httpx.HTTPStatusError):
            _run(client.get_daily_forecast(-23.55, -46.63))

    def test_get_daily_forecast_retry_on_error(self):
        """Retries on transient HTTP errors."""
        client = self._make_client_with_mock()
        client.config.retry_attempts = 2
        client.config.retry_delay = 0.01

        resp_500 = _make_httpx_response(status_code=500)
        client.client.get = AsyncMock(return_value=resp_500)

        with pytest.raises(httpx.HTTPStatusError):
            _run(client.get_daily_forecast(-23.55, -46.63))

        assert client.client.get.await_count == 2

    def test_get_daily_forecast_empty_timeseries(self):
        """Empty timeseries returns empty list."""
        client = self._make_client_with_mock()

        data = {"geometry": {"coordinates": [-46.63, -23.55]}, "properties": {"timeseries": []}}
        mock_resp = _make_httpx_response(status_code=200, json_data=data, headers={})
        client.client.get = AsyncMock(return_value=mock_resp)

        result = _run(client.get_daily_forecast(-23.55, -46.63))
        assert result == []

    def test_get_daily_forecast_cache_save(self):
        """Saves to cache when data is fetched."""
        mock_cache = AsyncMock()
        mock_cache.get = AsyncMock(return_value=None)
        client = self._make_client_with_mock(cache=mock_cache)

        mock_resp = _make_httpx_response(
            status_code=200,
            json_data=self._sample_met_response(),
            headers={"Last-Modified": "Fri, 01 Jan 2024 00:00:00 GMT", "Expires": "Fri, 01 Jan 2099 00:00:00 GMT"},
        )
        client.client.get = AsyncMock(return_value=mock_resp)

        _run(client.get_daily_forecast(-23.55, -46.63))
        # cache.set should have been called
        assert mock_cache.set.await_count >= 1


class TestMETNorwayParseResponse:
    """Tests for _parse_daily_response."""

    def _make_client(self):
        from backend.api.services.met_norway.met_norway_client import METNorwayClient
        return METNorwayClient()

    def test_parse_valid_response(self):
        client = self._make_client()
        start = datetime.now()
        end = start + timedelta(days=2)

        timeseries = []
        for h in range(48):
            ts = start + timedelta(hours=h)
            timeseries.append({
                "time": ts.isoformat() + "Z",
                "data": {
                    "instant": {
                        "details": {
                            "air_temperature": 22.0,
                            "relative_humidity": 60.0,
                            "wind_speed": 4.0,
                        }
                    },
                    "next_1_hours": {"details": {"precipitation_amount": 0.2}},
                    "next_6_hours": {
                        "details": {
                            "air_temperature_max": 28.0,
                            "air_temperature_min": 16.0,
                        }
                    },
                },
            })

        data = {
            "geometry": {"coordinates": [-46.63, -23.55, 850]},
            "properties": {"timeseries": timeseries},
        }

        result = client._parse_daily_response(data, ["air_temperature_max"], start, end)
        assert isinstance(result, list)

    def test_parse_no_geometry(self):
        """Missing geometry still works."""
        client = self._make_client()
        start = datetime.now()
        end = start + timedelta(days=1)

        data = {"geometry": {}, "properties": {"timeseries": []}}
        result = client._parse_daily_response(data, [], start, end)
        assert result == []

    def test_parse_invalid_data_returns_empty(self):
        """Completely invalid timeseries data returns empty list (handled gracefully)."""
        client = self._make_client()
        start = datetime.now()
        end = start + timedelta(days=1)

        data = {"geometry": {"coordinates": [-46, -23]}, "properties": {"timeseries": "not_a_list"}}
        result = client._parse_daily_response(data, [], start, end)
        assert result == []


class TestMETNorwayHealthCheck:
    """Tests for health_check method."""

    def test_health_check_success(self):
        from backend.api.services.met_norway.met_norway_client import METNorwayClient
        client = METNorwayClient()
        client.client = AsyncMock()
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        client.client.get = AsyncMock(return_value=mock_resp)

        result = _run(client.health_check())
        assert result is True

    def test_health_check_failure(self):
        from backend.api.services.met_norway.met_norway_client import METNorwayClient
        client = METNorwayClient()
        client.client = AsyncMock()
        client.client.get = AsyncMock(side_effect=Exception("Connection refused"))

        result = _run(client.health_check())
        assert result is False


# ===================================================================
# OpenTopo client
# ===================================================================

class TestOpenTopoGetElevation:
    """Tests for get_elevation method."""

    def _make_client(self, cache=None):
        from backend.api.services.opentopo.opentopo_client import OpenTopoClient
        client = OpenTopoClient(cache=cache)
        client.client = AsyncMock(spec=httpx.AsyncClient)
        return client

    def test_get_elevation_success(self):
        client = self._make_client()
        resp = _make_httpx_response(
            status_code=200,
            json_data={
                "status": "OK",
                "results": [
                    {"elevation": 1172.0, "location": {"lat": -15.78, "lng": -47.93}, "dataset": "srtm30m"}
                ],
            },
        )
        client.client.get = AsyncMock(return_value=resp)

        with patch("backend.api.services.opentopo.opentopo_client.check_api_quota", return_value=True), \
             patch("backend.api.services.opentopo.opentopo_client.track_api_call"):
            result = _run(client.get_elevation(-15.78, -47.93))

        assert result is not None
        assert result.elevation == 1172.0
        assert result.dataset == "srtm30m"

    def test_get_elevation_invalid_coordinates(self):
        client = self._make_client()
        result = _run(client.get_elevation(999, 999))
        assert result is None

    def test_get_elevation_api_error_status(self):
        client = self._make_client()
        resp = _make_httpx_response(
            status_code=200,
            json_data={"status": "ERROR", "error": "Something went wrong"},
        )
        client.client.get = AsyncMock(return_value=resp)

        with patch("backend.api.services.opentopo.opentopo_client.check_api_quota", return_value=True), \
             patch("backend.api.services.opentopo.opentopo_client.track_api_call"):
            result = _run(client.get_elevation(-15.78, -47.93))

        assert result is None

    def test_get_elevation_no_results(self):
        client = self._make_client()
        resp = _make_httpx_response(
            status_code=200,
            json_data={"status": "OK", "results": []},
        )
        client.client.get = AsyncMock(return_value=resp)

        with patch("backend.api.services.opentopo.opentopo_client.check_api_quota", return_value=True), \
             patch("backend.api.services.opentopo.opentopo_client.track_api_call"):
            result = _run(client.get_elevation(-15.78, -47.93))

        assert result is None

    def test_get_elevation_null_elevation(self):
        client = self._make_client()
        resp = _make_httpx_response(
            status_code=200,
            json_data={
                "status": "OK",
                "results": [{"elevation": None, "location": {"lat": -15.78, "lng": -47.93}}],
            },
        )
        client.client.get = AsyncMock(return_value=resp)

        with patch("backend.api.services.opentopo.opentopo_client.check_api_quota", return_value=True), \
             patch("backend.api.services.opentopo.opentopo_client.track_api_call"):
            result = _run(client.get_elevation(-15.78, -47.93))

        assert result is None

    def test_get_elevation_cache_hit(self):
        mock_cache = AsyncMock()
        mock_cache.get = AsyncMock(return_value={"elevation": 1200.0})
        client = self._make_client(cache=mock_cache)

        with patch("backend.api.services.opentopo.opentopo_client.check_api_quota", return_value=True):
            result = _run(client.get_elevation(-15.78, -47.93))

        assert result == {"elevation": 1200.0}

    def test_get_elevation_saves_to_cache(self):
        mock_cache = AsyncMock()
        mock_cache.get = AsyncMock(return_value=None)
        client = self._make_client(cache=mock_cache)

        resp = _make_httpx_response(
            status_code=200,
            json_data={
                "status": "OK",
                "results": [{"elevation": 850.0, "location": {"lat": -23.55, "lng": -46.63}, "dataset": "aster30m"}],
            },
        )
        client.client.get = AsyncMock(return_value=resp)

        with patch("backend.api.services.opentopo.opentopo_client.check_api_quota", return_value=True), \
             patch("backend.api.services.opentopo.opentopo_client.track_api_call"):
            result = _run(client.get_elevation(-23.55, -46.63))

        assert result is not None
        mock_cache.set.assert_called_once()

    def test_get_elevation_quota_exceeded(self):
        client = self._make_client()
        with patch("backend.api.services.opentopo.opentopo_client.check_api_quota", return_value=False):
            result = _run(client.get_elevation(-15.78, -47.93))
        assert result is None

    def test_get_elevation_rate_limit_429(self):
        client = self._make_client()
        resp = _make_httpx_response(status_code=429)
        client.client.get = AsyncMock(return_value=resp)

        with patch("backend.api.services.opentopo.opentopo_client.check_api_quota", return_value=True), \
             patch("backend.api.services.opentopo.opentopo_client.track_api_call"):
            result = _run(client.get_elevation(-15.78, -47.93))

        assert result is None

    def test_get_elevation_unexpected_error(self):
        client = self._make_client()
        client.client.get = AsyncMock(side_effect=Exception("Network error"))

        with patch("backend.api.services.opentopo.opentopo_client.check_api_quota", return_value=True):
            result = _run(client.get_elevation(-15.78, -47.93))

        assert result is None

    def test_get_elevation_cache_read_error(self):
        """Cache read error doesn't block API call."""
        mock_cache = AsyncMock()
        mock_cache.get = AsyncMock(side_effect=Exception("Redis down"))
        mock_cache.set = AsyncMock()
        client = self._make_client(cache=mock_cache)

        resp = _make_httpx_response(
            status_code=200,
            json_data={
                "status": "OK",
                "results": [{"elevation": 500.0, "location": {"lat": -23.55, "lng": -46.63}, "dataset": "srtm30m"}],
            },
        )
        client.client.get = AsyncMock(return_value=resp)

        with patch("backend.api.services.opentopo.opentopo_client.check_api_quota", return_value=True), \
             patch("backend.api.services.opentopo.opentopo_client.track_api_call"):
            result = _run(client.get_elevation(-23.55, -46.63))

        assert result is not None
        assert result.elevation == 500.0


class TestOpenTopoBatch:
    """Tests for get_elevations_batch."""

    def _make_client(self):
        from backend.api.services.opentopo.opentopo_client import OpenTopoClient
        client = OpenTopoClient()
        client.client = AsyncMock(spec=httpx.AsyncClient)
        return client

    def test_batch_empty_list(self):
        client = self._make_client()
        result = _run(client.get_elevations_batch([]))
        assert result == []

    def test_batch_invalid_coordinates(self):
        client = self._make_client()
        result = _run(client.get_elevations_batch([(999, 999)]))
        assert result == []

    def test_batch_success(self):
        client = self._make_client()
        resp = _make_httpx_response(
            status_code=200,
            json_data={
                "status": "OK",
                "results": [
                    {"elevation": 1172.0, "location": {"lat": -15.78, "lng": -47.93}, "dataset": "srtm30m"},
                    {"elevation": 850.0, "location": {"lat": -23.55, "lng": -46.63}, "dataset": "aster30m"},
                ],
            },
        )
        client.client.get = AsyncMock(return_value=resp)

        locations = [(-15.78, -47.93), (-23.55, -46.63)]
        result = _run(client.get_elevations_batch(locations))
        assert len(result) == 2
        assert result[0].elevation == 1172.0

    def test_batch_skips_null_elevation(self):
        client = self._make_client()
        resp = _make_httpx_response(
            status_code=200,
            json_data={
                "status": "OK",
                "results": [
                    {"elevation": None, "location": {"lat": -15.78, "lng": -47.93}},
                    {"elevation": 850.0, "location": {"lat": -23.55, "lng": -46.63}, "dataset": "srtm30m"},
                ],
            },
        )
        client.client.get = AsyncMock(return_value=resp)

        locations = [(-15.78, -47.93), (-23.55, -46.63)]
        result = _run(client.get_elevations_batch(locations))
        assert len(result) == 1  # Only the one with elevation

    def test_batch_api_error(self):
        client = self._make_client()
        client.client.get = AsyncMock(side_effect=Exception("API error"))

        result = _run(client.get_elevations_batch([(-15.78, -47.93)]))
        assert result == []

    def test_batch_error_status(self):
        client = self._make_client()
        resp = _make_httpx_response(
            status_code=200,
            json_data={"status": "ERROR", "error": "Quota exceeded"},
        )
        client.client.get = AsyncMock(return_value=resp)

        result = _run(client.get_elevations_batch([(-15.78, -47.93)]))
        assert result == []


class TestOpenTopoClose:
    """Test close method."""

    def test_close(self):
        from backend.api.services.opentopo.opentopo_client import OpenTopoClient
        client = OpenTopoClient()
        client.client = AsyncMock()
        _run(client.close())
        client.client.aclose.assert_called_once()
