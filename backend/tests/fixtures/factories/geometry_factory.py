"""
Geometry Factory

Factory for creating test geometries.
"""

import factory  # type: ignore
from factory import Faker, LazyAttribute  # type: ignore
import math


class PointFactory(factory.Factory):  # type: ignore
    """Factory for creating POINT geometries using factory_boy."""

    class Meta:
        model = dict

    # Coordinates (default settings for Jaú, SP)
    latitude = -22.25
    longitude = -48.5
    srid = 4326

    @LazyAttribute  # type: ignore
    def wkt(self) -> str:
        """Gera WKT do POINT."""
        return f"POINT({self.longitude} {self.latitude})"

    @LazyAttribute  # type: ignore
    def ewkt(self) -> str:
        """Gera EWKT (Extended WKT) com SRID."""
        return f"SRID={self.srid};POINT({self.longitude} {self.latitude})"


class RandomPointFactory(PointFactory):  # type: ignore
    """Factory for creating POINT geometries with random coordinates."""

    latitude = Faker("latitude")
    longitude = Faker("longitude")


# =============================================================================
# HELPER FUNCTIONS (backward compatibility)
# =============================================================================


def create_point(latitude: float = -22.25, longitude: float = -48.5) -> str:
    """
    Cria WKT de POINT (compatibilidade).

    Args:
        latitude: Latitude in decimal degrees
        longitude: Longitude in decimal degrees

    Returns:
        String WKT do POINT
    """
    return f"POINT({longitude} {latitude})"


def create_point_ewkt(
    latitude: float = -22.25, longitude: float = -48.5, srid: int = 4326
) -> str:
    """
    Cria EWKT (Extended WKT) de POINT com SRID.

    Args:
        latitude: Latitude in decimal degrees
        longitude: Longitude in decimal degrees
        srid: Spatial reference system (default: 4326 - WGS84)

    Returns:
        String EWKT do POINT
    """
    return f"SRID={srid};POINT({longitude} {latitude})"


def create_polygon_brazil() -> str:
    """
    Creates a WKT from a POLYGON representing an area in Brazil.

    Returns:
        String WKT do POLYGON
    """
    return (
        "POLYGON(("
        "-48.6 -22.3, "
        "-48.4 -22.3, "
        "-48.4 -22.2, "
        "-48.6 -22.2, "
        "-48.6 -22.3"
        "))"
    )


def create_circle_wkt(
    center_lat: float, center_lon: float, radius_meters: float
) -> str:
    """
    Creates an approximation of a circle using a POLYGON (32 points).

    Args:
        center_lat: Latitude of the center
        center_lon: Longitude of the center
        radius_meters: Radius in meters

    Returns:
        String WKT do POLYGON circular
    """
    # 1 grau ≈ 111km
    radius_degrees = radius_meters / 111000

    points = []
    for i in range(33):  # 32 points + close the polygon
        angle = (i * 360 / 32) * math.pi / 180
        lat = center_lat + (radius_degrees * math.sin(angle))
        lon = center_lon + (radius_degrees * math.cos(angle))
        points.append(f"{lon} {lat}")

    return f"POLYGON(({', '.join(points)}))"


# Alias GeometryFactory para compatibilidade
class GeometryFactory:
    """Classe legacy para compatibilidade."""

    create_point = staticmethod(create_point)
    create_point_ewkt = staticmethod(create_point_ewkt)
    create_polygon_brazil = staticmethod(create_polygon_brazil)
    create_circle_wkt = staticmethod(create_circle_wkt)
