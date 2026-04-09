"""
Tests for Refactored Factories with factory_boy

Valida ClimateDataFactory, PointFactory, MeteorologicalStationFactory.
"""

import pytest


@pytest.mark.unit
class TestClimateDataFactoryRefactored:
    """Testa ClimateDataFactory refatorado com factory_boy."""

    def test_create_single_data(self):
        """Testa criação de dado climático único."""
        from backend.tests.fixtures.factories.climate_data_factory import (
            ClimateDataFactory,
        )

        data = ClimateDataFactory()

        assert "latitude" in data
        assert "longitude" in data
        assert "temperature_max" in data
        assert "temperature_min" in data
        assert "temperature_avg" in data
        assert data["temperature_avg"] == round(
            (data["temperature_max"] + data["temperature_min"]) / 2, 1
        )

    def test_summer_winter_rainy_factories(self):
        """Testa factories especializadas."""
        from backend.tests.fixtures.factories.climate_data_factory import (
            SummerDayFactory,
            WinterDayFactory,
            RainyDayFactory,
        )

        summer = SummerDayFactory()
        assert summer["temperature_max"] == 32.5

        winter = WinterDayFactory()
        assert winter["temperature_max"] == 22.0

        rainy = RainyDayFactory()
        assert rainy["precipitation"] >= 10.0


@pytest.mark.unit
class TestGeometryFactoryRefactored:
    """Testa GeometryFactory refatorado com factory_boy."""

    def test_point_factory(self):
        """Testa PointFactory."""
        from backend.tests.fixtures.factories.geometry_factory import (
            PointFactory,
        )

        point = PointFactory()

        assert "wkt" in point
        assert "ewkt" in point
        assert "POINT" in point["wkt"]
        assert "SRID=" in point["ewkt"]

    def test_random_point_factory(self):
        """Testa RandomPointFactory com coordenadas aleatórias."""
        from backend.tests.fixtures.factories.geometry_factory import (
            RandomPointFactory,
        )

        point1 = RandomPointFactory()
        point2 = RandomPointFactory()

        # Coordenadas devem ser diferentes (aleatórias)
        assert (
            point1["latitude"] != point2["latitude"]
            or point1["longitude"] != point2["longitude"]
        )

    def test_legacy_geometry_factory(self):
        """Testa compatibilidade com GeometryFactory antigo."""
        from backend.tests.fixtures.factories.geometry_factory import (
            GeometryFactory,
        )

        wkt = GeometryFactory.create_point(-22.25, -48.5)
        assert wkt == "POINT(-48.5 -22.25)"

        ewkt = GeometryFactory.create_point_ewkt(-22.25, -48.5)
        assert ewkt == "SRID=4326;POINT(-48.5 -22.25)"


@pytest.mark.unit
class TestStationFactoryRefactored:
    """Testa StationFactory refatorado com factory_boy."""

    def test_meteorological_station_factory(self):
        """Testa MeteorologicalStationFactory."""
        from backend.tests.fixtures.factories.station_factory import (
            MeteorologicalStationFactory,
        )

        station = MeteorologicalStationFactory()

        assert "station_id" in station
        assert "name" in station
        assert "latitude" in station
        assert "longitude" in station
        assert "elevation" in station
        assert station["country"] == "BR"

    def test_brazil_station_factory(self):
        """Testa BrazilStationFactory com coordenadas válidas."""
        from backend.tests.fixtures.factories.station_factory import (
            BrazilStationFactory,
        )

        station = BrazilStationFactory()

        # Coordenadas dentro do Brasil
        assert -33.0 <= station["latitude"] <= 5.0
        assert -73.0 <= station["longitude"] <= -34.0

    def test_station_id_sequence(self):
        """Testa sequência de IDs."""
        from backend.tests.fixtures.factories.station_factory import (
            MeteorologicalStationFactory,
        )

        stations = [MeteorologicalStationFactory() for _ in range(3)]

        # IDs devem ser sequenciais
        assert "TEST" in stations[0]["station_id"]
        assert stations[0]["station_id"] != stations[1]["station_id"]

    def test_legacy_station_factory(self):
        """Testa compatibilidade com StationFactory antigo."""
        from backend.tests.fixtures.factories.station_factory import (
            StationFactory,
        )

        station = StationFactory.create_station()
        assert station["station_id"] == "TEST001"
        assert station["name"] == "Estação Teste"

        brazil_stations = StationFactory.create_brazil_stations()
        assert len(brazil_stations) == 3
        assert brazil_stations[0]["station_id"] == "SP001"
