"""
Performance Tests - Spatial Operations

Tests: Benchmark of geospatial operations (Python/Shapely)
"""

import pytest


@pytest.mark.performance
class TestSpatialOperations:
    """Test performance of geospatial operations."""

    def test_region_detection_performance(self):
        """Test performance of region detection."""
        import time
        from backend.core.utils.geo_utils import detect_geographic_region

        start = time.perf_counter()
        for _ in range(1000):
            detect_geographic_region(-22.9, -43.2)
        elapsed = time.perf_counter() - start
        # 1000 detections should take < 1 second
        assert elapsed < 1.0

    def test_reference_lookup_performance(self):
        """Test performance of reference lookup."""
        import time
        from backend.core.data_processing.historical_loader import (
            HistoricalDataLoader,
        )

        loader = HistoricalDataLoader()
        start = time.perf_counter()
        for _ in range(100):
            loader.get_reference_for_location(-22.72, -47.64)
        elapsed = time.perf_counter() - start
        # 100 lookups should take < 2 seconds
        assert elapsed < 2.0
