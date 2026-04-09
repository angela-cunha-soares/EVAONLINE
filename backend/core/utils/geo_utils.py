"""
Geographic utilities for distance and coordinate calculations.

Provides optimized Haversine distance calculations for both scalar and
vectorized (NumPy array) operations.
"""

import json
import math
from functools import lru_cache
from pathlib import Path
from typing import Tuple, Union

import numpy as np
from shapely.geometry import Point, shape
from shapely.ops import unary_union
from shapely.prepared import prep


def haversine_distance(
    lat1: float, lon1: float, lat2: float, lon2: float
) -> float:
    """
    Calculate distance between two points using Haversine formula.

    Args:
        lat1, lon1: First coordinate (degrees)
        lat2, lon2: Second coordinate (degrees)

    Returns:
        Distance in kilometers
    """
    R = 6371.0  # Earth radius in km

    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)

    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad

    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c


def haversine_distance_vectorized(
    lat1: Union[np.ndarray, float],
    lon1: Union[np.ndarray, float],
    lat2: Union[np.ndarray, float],
    lon2: Union[np.ndarray, float],
) -> Union[np.ndarray, float]:
    """
    Vectorized Haversine for multiple pairs (fast for large arrays).

    Args:
        lat1, lon1, lat2, lon2: NumPy arrays or floats of lat/lon (degrees).

    Returns:
        Array of distances in km (or float if inputs are floats).
    """
    # Convert to radians
    lat1_rad = np.radians(lat1)
    lon1_rad = np.radians(lon1)
    lat2_rad = np.radians(lat2)
    lon2_rad = np.radians(lon2)

    # Differences
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad

    # Haversine formula
    a = (
        np.sin(dlat / 2) ** 2
        + np.cos(lat1_rad) * np.cos(lat2_rad) * np.sin(dlon / 2) ** 2
    )
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))

    # Earth radius in km
    R = 6371.0

    return R * c


@lru_cache(maxsize=1)
def _load_brazil_geometry():
    """Load and merge all UF polygons into a single prepared geometry."""
    geojson_path = (
        Path(__file__).resolve().parent.parent.parent.parent
        / "data"
        / "geojson"
        / "BR_UF_2024.geojson"
    )
    with open(geojson_path, encoding="utf-8") as f:
        data = json.load(f)
    polygons = [shape(feat["geometry"]) for feat in data["features"]]
    brazil = unary_union(polygons)
    return prep(brazil)


def _is_inside_brazil(lat: float, lon: float) -> bool:
    """Check if coordinates fall inside Brazil using official IBGE shapefile."""
    # Fast bounding-box reject
    if lat > 5.3 or lat < -33.8 or lon > -34.7 or lon < -74.0:
        return False
    brazil = _load_brazil_geometry()
    return brazil.contains(Point(lon, lat))


def detect_geographic_region(lat: float, lon: float) -> str:
    """
    Detect geographic region based on coordinates.

    Only three regions matter for the platform's fusion logic:
    - **brasil**: Kalman filter uses Brazilian climatological priors
      (detected via IBGE official shapefile)
    - **usa**: NWS forecast sources available, +30% weight bonus
    - **nordic**: MET Norway high-resolution (1 km) data, +50% weight bonus
    - **global**: default for all other locations

    Returns one of: brasil, usa, nordic, global
    """
    if _is_inside_brazil(lat, lon):
        return "brasil"
    # USA Continental (NWS coverage: 48 contiguous states)
    if 24 <= lat <= 49 and -125 <= lon <= -66:
        return "usa"
    # Nordic Europe (MET Norway MEPS 1km domain)
    if 54 <= lat <= 71.5 and 4 <= lon <= 32:
        return "nordic"
    return "global"


def is_same_hemisphere(
    lat1: float, lat2: float, tolerance: float = 5.0
) -> bool:
    """
    Check if two latitudes are in the same hemisphere.

    Args:
        lat1, lat2: Latitudes in degrees
        tolerance: Degrees near equator to consider as "same hemisphere"

    Returns:
        True if both are in the same hemisphere
    """
    # Same sign means same hemisphere
    if lat1 * lat2 > 0:
        return True

    # Near equator is considered compatible with both hemispheres
    if abs(lat1) < tolerance and abs(lat2) < tolerance:
        return True

    return False


def calculate_bounding_box(
    lat: float, lon: float, distance_km: float
) -> Tuple[float, float, float, float]:
    """
    Calculate a bounding box around a point.

    Args:
        lat, lon: Center coordinates (degrees)
        distance_km: Distance from center to edge (km)

    Returns:
        Tuple of (min_lat, max_lat, min_lon, max_lon)
    """
    # Approximate degrees per km
    lat_delta = distance_km / 111.0  # ~111 km per degree latitude
    lon_delta = distance_km / (111.0 * math.cos(math.radians(lat)))

    return (
        lat - lat_delta,
        lat + lat_delta,
        lon - lon_delta,
        lon + lon_delta,
    )
