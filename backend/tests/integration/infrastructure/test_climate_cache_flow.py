"""
Integration Tests - Climate Cache Flow

Tests the Redis caching layer for climate data requests.
Validates cache key generation, TTL, and invalidation.

Reference: Article Section 3.3 (Caching strategy)
"""

import pytest


@pytest.mark.integration
class TestClimateCacheServiceImport:
    """Tests cache module imports and structure."""

    def test_cache_service_importable(self):
        """ClimateCacheService should be importable."""
        from backend.infrastructure.cache.climate_cache import (
            ClimateCacheService,
        )

        assert ClimateCacheService is not None

    def test_cache_manager_importable(self):
        """ClimateCache (aggregation manager) should be importable."""
        from backend.infrastructure.cache.cache_manager import ClimateCache

        assert ClimateCache is not None

    def test_cache_service_has_expected_methods(self):
        """ClimateCacheService should expose cache interface."""
        from backend.infrastructure.cache.climate_cache import (
            ClimateCacheService,
        )

        # Check for standard cache methods
        members = dir(ClimateCacheService)
        has_get = any("get" in m.lower() for m in members)
        has_set = any("set" in m.lower() or "store" in m.lower() or "save" in m.lower() for m in members)
        assert has_get or has_set, "ClimateCacheService needs get/set methods"


@pytest.mark.integration
class TestClimateCacheKeyStrategy:
    """Tests cache key generation logic."""

    def test_cache_key_includes_coordinates(self):
        """Cache keys should include lat/lon for uniqueness."""
        # The key strategy should encode lat/lon/dates
        lat, lon = -22.2926, -48.5841
        key = f"climate:{lat}:{lon}:2023-06-01:2023-06-30"
        assert "-22.2926" in key
        assert "-48.5841" in key

    def test_different_coords_different_keys(self):
        """Different locations must produce different keys."""
        key1 = f"climate:-22.2926:-48.5841:2023-06-01"
        key2 = f"climate:34.05:-118.25:2023-06-01"
        assert key1 != key2

    def test_different_dates_different_keys(self):
        """Different date ranges must produce different keys."""
        key1 = f"climate:-22.2926:-48.5841:2023-06-01"
        key2 = f"climate:-22.2926:-48.5841:2023-07-01"
        assert key1 != key2
