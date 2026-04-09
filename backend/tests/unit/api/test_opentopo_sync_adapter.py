"""
Tests for OpenTopoSyncAdapter — covers all sync wrappers, async internals,
health check branches, and coverage info.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.api.services.opentopo.opentopo_client import (
    OpenTopoConfig,
    OpenTopoLocation,
)
from backend.api.services.opentopo.opentopo_sync_adapter import (
    OpenTopoSyncAdapter,
)

MODULE = "backend.api.services.opentopo.opentopo_sync_adapter"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def adapter():
    """Adapter without cache."""
    return OpenTopoSyncAdapter()


@pytest.fixture
def adapter_with_cache():
    """Adapter with a mock Redis cache."""
    return OpenTopoSyncAdapter(cache=MagicMock())


@pytest.fixture
def sample_location():
    return OpenTopoLocation(lat=-15.78, lon=-47.93, elevation=1172.0, dataset="srtm30m")


def _mock_loop(running=False):
    """Create a fake event loop that is NOT closed."""
    loop = MagicMock()
    loop.is_running.return_value = running
    loop.is_closed.return_value = False
    return loop


def _close_coro_and_return(return_value):
    """Side-effect that closes the coroutine arg to avoid 'was never awaited' warnings."""
    def _side_effect(coro):
        if hasattr(coro, "close"):
            coro.close()
        return return_value
    return _side_effect


# ---------------------------------------------------------------------------
# __init__
# ---------------------------------------------------------------------------

class TestInit:
    def test_default_config(self, adapter):
        assert isinstance(adapter.config, OpenTopoConfig)
        assert adapter.cache is None

    def test_custom_config_and_cache(self):
        cfg = OpenTopoConfig(timeout=5)
        cache = MagicMock()
        a = OpenTopoSyncAdapter(config=cfg, cache=cache)
        assert a.config.timeout == 5
        assert a.cache is cache


# ---------------------------------------------------------------------------
# get_elevation_sync — all 3 event-loop branches
# ---------------------------------------------------------------------------

class TestGetElevationSync:
    """Cover: loop not running, loop.is_running(), RuntimeError (no loop)."""

    def test_no_running_loop(self, adapter, sample_location):
        """Branch: loop exists, NOT running → run_until_complete."""
        loop = _mock_loop(running=False)
        loop.run_until_complete.side_effect = _close_coro_and_return(sample_location)

        with patch(f"{MODULE}.asyncio.get_event_loop", return_value=loop):
            result = adapter.get_elevation_sync(-15.78, -47.93)

        assert result.elevation == 1172.0
        loop.run_until_complete.assert_called_once()

    def test_running_loop_uses_executor(self, adapter, sample_location):
        """Branch: loop IS running → ThreadPoolExecutor + asyncio.run."""
        loop = _mock_loop(running=True)

        with patch(f"{MODULE}.asyncio.get_event_loop", return_value=loop), \
             patch(f"{MODULE}.asyncio.run", side_effect=_close_coro_and_return(sample_location)):
            result = adapter.get_elevation_sync(-15.78, -47.93)

        assert result.elevation == 1172.0

    def test_no_loop_fallback(self, adapter, sample_location):
        """Branch: no event loop → asyncio.run()."""
        with patch(f"{MODULE}.asyncio.get_event_loop",
                   side_effect=RuntimeError("no current event loop")), \
             patch(f"{MODULE}.asyncio.run", side_effect=_close_coro_and_return(sample_location)):
            result = adapter.get_elevation_sync(-15.78, -47.93)

        assert result.elevation == 1172.0


# ---------------------------------------------------------------------------
# get_elevations_batch_sync — all 3 event-loop branches
# ---------------------------------------------------------------------------

class TestGetElevationsBatchSync:

    def test_no_running_loop(self, adapter, sample_location):
        loop = _mock_loop(running=False)
        loop.run_until_complete.side_effect = _close_coro_and_return([sample_location])

        with patch(f"{MODULE}.asyncio.get_event_loop", return_value=loop):
            result = adapter.get_elevations_batch_sync([(-15.78, -47.93)])

        assert len(result) == 1
        assert result[0].elevation == 1172.0

    def test_running_loop_uses_executor(self, adapter, sample_location):
        loop = _mock_loop(running=True)

        with patch(f"{MODULE}.asyncio.get_event_loop", return_value=loop), \
             patch(f"{MODULE}.asyncio.run", side_effect=_close_coro_and_return([sample_location])):
            result = adapter.get_elevations_batch_sync([(-15.78, -47.93)])

        assert len(result) == 1

    def test_no_loop_fallback(self, adapter, sample_location):
        with patch(f"{MODULE}.asyncio.get_event_loop",
                   side_effect=RuntimeError("no current event loop")), \
             patch(f"{MODULE}.asyncio.run", side_effect=_close_coro_and_return([sample_location])):
            result = adapter.get_elevations_batch_sync([(-15.78, -47.93)])

        assert len(result) == 1


# ---------------------------------------------------------------------------
# health_check_sync — all 3 event-loop branches
# ---------------------------------------------------------------------------

class TestHealthCheckSync:

    def test_no_running_loop(self, adapter):
        loop = _mock_loop(running=False)
        loop.run_until_complete.side_effect = _close_coro_and_return(True)

        with patch(f"{MODULE}.asyncio.get_event_loop", return_value=loop):
            assert adapter.health_check_sync() is True

    def test_running_loop_uses_executor(self, adapter):
        loop = _mock_loop(running=True)

        with patch(f"{MODULE}.asyncio.get_event_loop", return_value=loop), \
             patch(f"{MODULE}.asyncio.run", side_effect=_close_coro_and_return(True)):
            assert adapter.health_check_sync() is True

    def test_no_loop_fallback(self, adapter):
        with patch(f"{MODULE}.asyncio.get_event_loop",
                   side_effect=RuntimeError("no current event loop")), \
             patch(f"{MODULE}.asyncio.run", side_effect=_close_coro_and_return(False)):
            assert adapter.health_check_sync() is False


# ---------------------------------------------------------------------------
# _async_health_check — internal branches
# ---------------------------------------------------------------------------

class TestAsyncHealthCheck:

    @pytest.mark.asyncio
    @patch("backend.api.services.opentopo.opentopo_sync_adapter.OpenTopoClient")
    async def test_health_ok(self, MockClient, adapter, sample_location):
        """Location returned with elevation → True."""
        instance = AsyncMock()
        instance.get_elevation = AsyncMock(return_value=sample_location)
        instance.close = AsyncMock()
        MockClient.return_value = instance

        result = await adapter._async_health_check()
        assert result is True
        instance.close.assert_awaited_once()

    @pytest.mark.asyncio
    @patch("backend.api.services.opentopo.opentopo_sync_adapter.OpenTopoClient")
    async def test_health_no_data(self, MockClient, adapter):
        """Location is None → False."""
        instance = AsyncMock()
        instance.get_elevation = AsyncMock(return_value=None)
        instance.close = AsyncMock()
        MockClient.return_value = instance

        result = await adapter._async_health_check()
        assert result is False

    @pytest.mark.asyncio
    @patch("backend.api.services.opentopo.opentopo_sync_adapter.OpenTopoClient")
    async def test_health_zero_elevation(self, MockClient, adapter):
        """Location with elevation=0 (falsy) → False."""
        loc = OpenTopoLocation(lat=-15.78, lon=-47.93, elevation=0.0, dataset="srtm30m")
        instance = AsyncMock()
        instance.get_elevation = AsyncMock(return_value=loc)
        instance.close = AsyncMock()
        MockClient.return_value = instance

        result = await adapter._async_health_check()
        assert result is False

    @pytest.mark.asyncio
    @patch("backend.api.services.opentopo.opentopo_sync_adapter.OpenTopoClient")
    async def test_health_exception(self, MockClient, adapter):
        """Exception in get_elevation → False."""
        instance = AsyncMock()
        instance.get_elevation = AsyncMock(side_effect=Exception("timeout"))
        instance.close = AsyncMock()
        MockClient.return_value = instance

        result = await adapter._async_health_check()
        assert result is False
        instance.close.assert_awaited_once()


# ---------------------------------------------------------------------------
# _async_get_elevation / _async_get_elevations_batch
# ---------------------------------------------------------------------------

class TestAsyncInternals:

    @pytest.mark.asyncio
    @patch("backend.api.services.opentopo.opentopo_sync_adapter.OpenTopoClient")
    async def test_async_get_elevation(self, MockClient, adapter, sample_location):
        instance = AsyncMock()
        instance.get_elevation = AsyncMock(return_value=sample_location)
        instance.close = AsyncMock()
        MockClient.return_value = instance

        result = await adapter._async_get_elevation(-15.78, -47.93)
        assert result.elevation == 1172.0
        instance.close.assert_awaited_once()

    @pytest.mark.asyncio
    @patch("backend.api.services.opentopo.opentopo_sync_adapter.OpenTopoClient")
    async def test_async_get_elevation_with_dataset(self, MockClient, adapter, sample_location):
        instance = AsyncMock()
        instance.get_elevation = AsyncMock(return_value=sample_location)
        instance.close = AsyncMock()
        MockClient.return_value = instance

        result = await adapter._async_get_elevation(-15.78, -47.93, "etopo1")
        instance.get_elevation.assert_awaited_once_with(-15.78, -47.93, "etopo1")

    @pytest.mark.asyncio
    @patch("backend.api.services.opentopo.opentopo_sync_adapter.OpenTopoClient")
    async def test_async_get_elevations_batch(self, MockClient, adapter, sample_location):
        instance = AsyncMock()
        instance.get_elevations_batch = AsyncMock(return_value=[sample_location])
        instance.close = AsyncMock()
        MockClient.return_value = instance

        locs = [(-15.78, -47.93)]
        result = await adapter._async_get_elevations_batch(locs)
        assert len(result) == 1
        instance.close.assert_awaited_once()


# ---------------------------------------------------------------------------
# _async_is_in_coverage
# ---------------------------------------------------------------------------

class TestAsyncIsInCoverage:

    @pytest.mark.asyncio
    async def test_valid_coordinate(self, adapter):
        result = await adapter._async_is_in_coverage(-15.78, -47.93)
        assert result is True

    @pytest.mark.asyncio
    async def test_invalid_coordinate(self, adapter):
        result = await adapter._async_is_in_coverage(999.0, -47.93)
        assert result is False

    @pytest.mark.asyncio
    async def test_edge_coordinate(self, adapter):
        result = await adapter._async_is_in_coverage(90.0, 180.0)
        assert result is True


# ---------------------------------------------------------------------------
# get_coverage_info
# ---------------------------------------------------------------------------

class TestGetCoverageInfo:

    def test_returns_dict(self, adapter):
        info = adapter.get_coverage_info()
        assert isinstance(info, dict)
        assert info["adapter"] == "OpenTopoSyncAdapter"

    def test_datasets_present(self, adapter):
        info = adapter.get_coverage_info()
        datasets = info["datasets"]
        assert "srtm30m" in datasets
        assert "aster30m" in datasets
        assert "mapzen" in datasets
        assert "etopo1" in datasets

    def test_default_dataset_matches_config(self, adapter):
        info = adapter.get_coverage_info()
        assert info["default_dataset"] == adapter.config.default_dataset

    def test_rate_limits(self, adapter):
        info = adapter.get_coverage_info()
        rl = info["rate_limits"]
        assert rl["requests_per_second"] == 1
        assert rl["locations_per_request"] == 100

    def test_fao56_info(self, adapter):
        info = adapter.get_coverage_info()
        assert "fao56_calculations" in info
        assert "atmospheric_pressure" in info["fao56_calculations"]
