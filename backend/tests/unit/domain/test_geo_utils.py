"""
Unit Tests - geo_utils (core utilities)

Tests Haversine distance, vectorized distance, geographic region detection,
hemisphere detection, and bounding box calculation.

Reference: Article Section 2.2 (Geographic Processing)
"""


import numpy as np
import pytest

from backend.core.utils.geo_utils import (
    haversine_distance,
    haversine_distance_vectorized,
    detect_geographic_region,
    is_same_hemisphere,
    calculate_bounding_box,
)


# ============================================================================
# Haversine Distance
# ============================================================================


@pytest.mark.unit
class TestHaversineDistance:
    """Scalar Haversine distance tests."""

    def test_same_point_is_zero(self):
        assert haversine_distance(-23.55, -46.63, -23.55, -46.63) == 0.0

    def test_nyc_to_london(self):
        """NYC to London ≈ 5570 km."""
        d = haversine_distance(40.71, -74.01, 51.51, -0.13)
        assert 5500 < d < 5650

    def test_sao_paulo_to_jau(self):
        """São Paulo to Jaú ≈ 296 km."""
        d = haversine_distance(-23.55, -46.63, -22.30, -48.56)
        assert 200 < d < 400

    def test_antipodal_points(self):
        """0,0 to 0,180 ≈ half circumference ≈ 20015 km."""
        d = haversine_distance(0, 0, 0, 180)
        assert 20000 < d < 20100

    def test_result_is_float(self):
        d = haversine_distance(0, 0, 1, 1)
        assert isinstance(d, float)

    def test_symmetry(self):
        d1 = haversine_distance(10, 20, 30, 40)
        d2 = haversine_distance(30, 40, 10, 20)
        assert abs(d1 - d2) < 0.01


@pytest.mark.unit
class TestHaversineVectorized:
    """Vectorized Haversine tests."""

    def test_scalar_inputs(self):
        d = haversine_distance_vectorized(40.71, -74.01, 51.51, -0.13)
        assert 5500 < float(d) < 5650

    def test_array_inputs(self):
        lats = np.array([40.71, -23.55])
        lons = np.array([-74.01, -46.63])
        d = haversine_distance_vectorized(lats, lons, 51.51, -0.13)
        assert len(d) == 2
        assert all(di > 0 for di in d)

    def test_matches_scalar(self):
        """Vectorized single-element matches scalar."""
        d_scalar = haversine_distance(40.71, -74.01, 51.51, -0.13)
        d_vec = haversine_distance_vectorized(40.71, -74.01, 51.51, -0.13)
        assert abs(float(d_vec) - d_scalar) < 1.0


# ============================================================================
# Region Detection
# ============================================================================


@pytest.mark.unit
class TestDetectGeographicRegion:
    """Geographic region detection."""

    def test_brazil(self):
        region = detect_geographic_region(-23.55, -46.63)
        assert "bra" in region.lower() or region.lower() == "south_america"

    def test_usa(self):
        region = detect_geographic_region(39.74, -104.99)
        assert "usa" in region.lower() or "america" in region.lower()

    def test_europe_or_nordic(self):
        region = detect_geographic_region(60.17, 24.94)
        assert region.lower() in ("europe", "nordic", "scandinavia", "global")

    def test_returns_string(self):
        region = detect_geographic_region(0, 0)
        assert isinstance(region, str)
        assert len(region) > 0


# ============================================================================
# Hemisphere Detection
# ============================================================================


@pytest.mark.unit
class TestIsSameHemisphere:
    """Hemisphere check."""

    def test_both_north(self):
        assert is_same_hemisphere(30.0, 50.0) is True

    def test_both_south(self):
        assert is_same_hemisphere(-10.0, -40.0) is True

    def test_different_hemispheres(self):
        assert is_same_hemisphere(30.0, -30.0) is False

    def test_near_equator_within_tolerance(self):
        """Points near equator on opposite sides but within tolerance."""
        assert is_same_hemisphere(2.0, -2.0, tolerance=5.0) is True

    def test_equator_same_hemisphere(self):
        assert is_same_hemisphere(0.0, 0.0) is True


# ============================================================================
# Bounding Box
# ============================================================================


@pytest.mark.unit
class TestCalculateBoundingBox:
    """Bounding box around a point."""

    def test_returns_four_values(self):
        result = calculate_bounding_box(-23.55, -46.63, 100)
        assert len(result) == 4

    def test_min_less_than_max(self):
        min_lat, max_lat, min_lon, max_lon = calculate_bounding_box(0, 0, 100)
        assert min_lat < max_lat
        assert min_lon < max_lon

    def test_center_inside_box(self):
        min_lat, max_lat, min_lon, max_lon = calculate_bounding_box(-23.55, -46.63, 50)
        assert min_lat <= -23.55 <= max_lat
        assert min_lon <= -46.63 <= max_lon

    def test_larger_distance_wider_box(self):
        box_small = calculate_bounding_box(0, 0, 10)
        box_large = calculate_bounding_box(0, 0, 100)
        small_span = box_small[1] - box_small[0]
        large_span = box_large[1] - box_large[0]
        assert large_span > small_span

    def test_equator_symmetry(self):
        """At equator, lat and lon deltas should be similar."""
        min_lat, max_lat, min_lon, max_lon = calculate_bounding_box(0, 0, 100)
        lat_span = max_lat - min_lat
        lon_span = max_lon - min_lon
        assert abs(lat_span - lon_span) / lat_span < 0.1  # Within 10%
