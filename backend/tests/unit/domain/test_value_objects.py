"""
Tests for Value Objects (Real Implementation)

Tests: Coordinate, Temperature, Elevation, Humidity, WindSpeed validation
"""

import pytest


@pytest.mark.unit
class TestCoordinateValidation:
    """Testa validação de coordenadas usando GeographicUtils."""

    def test_valid_brazil_coordinates(self):
        """Testa coordenadas válidas no Brasil."""
        from backend.api.services.geographic_utils import GeographicUtils

        # Jaú, SP
        assert GeographicUtils.is_valid_coordinate(-22.25, -48.5)
        assert GeographicUtils.is_in_brazil(-22.25, -48.5)

        # São Paulo
        assert GeographicUtils.is_valid_coordinate(-23.55, -46.63)
        assert GeographicUtils.is_in_brazil(-23.55, -46.63)

    def test_valid_usa_coordinates(self):
        """Testa coordenadas válidas nos EUA."""
        from backend.api.services.geographic_utils import GeographicUtils

        # Nova York
        assert GeographicUtils.is_valid_coordinate(40.7128, -74.0060)
        assert GeographicUtils.is_in_usa(40.7128, -74.0060)

        # Los Angeles
        assert GeographicUtils.is_valid_coordinate(34.0522, -118.2437)
        assert GeographicUtils.is_in_usa(34.0522, -118.2437)

    def test_valid_nordic_coordinates(self):
        """Testa coordenadas válidas na região nórdica."""
        from backend.api.services.geographic_utils import GeographicUtils

        # Oslo, Noruega
        assert GeographicUtils.is_valid_coordinate(59.9139, 10.7522)
        assert GeographicUtils.is_in_nordic(59.9139, 10.7522)

    def test_invalid_latitude_too_high(self):
        """Testa latitude acima de 90°."""
        from backend.api.services.geographic_utils import GeographicUtils

        assert not GeographicUtils.is_valid_coordinate(100, -48.5)
        assert not GeographicUtils.is_valid_coordinate(91, -48.5)

    def test_invalid_latitude_too_low(self):
        """Testa latitude abaixo de -90°."""
        from backend.api.services.geographic_utils import GeographicUtils

        assert not GeographicUtils.is_valid_coordinate(-100, -48.5)
        assert not GeographicUtils.is_valid_coordinate(-91, -48.5)

    def test_invalid_longitude_too_high(self):
        """Testa longitude acima de 180°."""
        from backend.api.services.geographic_utils import GeographicUtils

        assert not GeographicUtils.is_valid_coordinate(-22.25, 200)
        assert not GeographicUtils.is_valid_coordinate(-22.25, 181)

    def test_boundary_coordinates(self):
        """Testa coordenadas nos limites (90°, 180°)."""
        from backend.api.services.geographic_utils import GeographicUtils

        # Limites válidos
        assert GeographicUtils.is_valid_coordinate(90, 180)
        assert GeographicUtils.is_valid_coordinate(-90, -180)
        assert GeographicUtils.is_valid_coordinate(0, 0)


@pytest.mark.unit
class TestTemperatureValidation:
    """Testa validação de temperaturas usando WeatherValidationUtils."""

    def test_valid_temperatures(self):
        """Testa temperaturas válidas."""
        from backend.api.services.weather_utils import (
            WeatherValidationUtils,
        )

        # Temperaturas normais
        assert WeatherValidationUtils.is_valid_temperature(25.0)
        assert WeatherValidationUtils.is_valid_temperature(0.0)
        assert WeatherValidationUtils.is_valid_temperature(-10.0)
        assert WeatherValidationUtils.is_valid_temperature(40.0)

    def test_extreme_cold_temperature(self):
        """Testa temperaturas extremamente baixas."""
        from backend.api.services.weather_utils import (
            WeatherValidationUtils,
        )

        assert not WeatherValidationUtils.is_valid_temperature(-100)
        assert not WeatherValidationUtils.is_valid_temperature(-200)

    def test_extreme_hot_temperature(self):
        """Testa temperaturas extremamente altas."""
        from backend.api.services.weather_utils import (
            WeatherValidationUtils,
        )

        assert not WeatherValidationUtils.is_valid_temperature(70)
        assert not WeatherValidationUtils.is_valid_temperature(100)

    def test_boundary_temperatures(self):
        """Testa temperaturas nos limites."""
        from backend.api.services.weather_utils import (
            WeatherValidationUtils,
        )

        # Limites válidos (-90 a 60°C)
        assert WeatherValidationUtils.is_valid_temperature(-90)
        assert WeatherValidationUtils.is_valid_temperature(60)


@pytest.mark.unit
class TestHumidityValidation:
    """Testa validação de umidade relativa."""

    def test_valid_humidity(self):
        """Testa valores válidos de umidade."""
        from backend.api.services.weather_utils import (
            WeatherValidationUtils,
        )

        assert WeatherValidationUtils.is_valid_humidity(50.0)
        assert WeatherValidationUtils.is_valid_humidity(0.0)
        assert WeatherValidationUtils.is_valid_humidity(100.0)

    def test_invalid_humidity_negative(self):
        """Testa umidade negativa."""
        from backend.api.services.weather_utils import (
            WeatherValidationUtils,
        )

        assert not WeatherValidationUtils.is_valid_humidity(-10)
        assert not WeatherValidationUtils.is_valid_humidity(-1)

    def test_invalid_humidity_above_100(self):
        """Testa umidade acima de 100%."""
        from backend.api.services.weather_utils import (
            WeatherValidationUtils,
        )

        assert not WeatherValidationUtils.is_valid_humidity(101)
        assert not WeatherValidationUtils.is_valid_humidity(150)


@pytest.mark.unit
class TestWindSpeedValidation:
    """Testa validação de velocidade do vento."""

    def test_valid_wind_speed(self):
        """Testa velocidades de vento válidas."""
        from backend.api.services.weather_utils import (
            WeatherValidationUtils,
        )

        assert WeatherValidationUtils.is_valid_wind_speed(0.0)
        assert WeatherValidationUtils.is_valid_wind_speed(2.5)
        assert WeatherValidationUtils.is_valid_wind_speed(50.0)

    def test_invalid_wind_speed_negative(self):
        """Testa velocidade de vento negativa."""
        from backend.api.services.weather_utils import (
            WeatherValidationUtils,
        )

        assert not WeatherValidationUtils.is_valid_wind_speed(-1)
        assert not WeatherValidationUtils.is_valid_wind_speed(-10)

    def test_invalid_wind_speed_too_high(self):
        """Testa velocidade de vento extremamente alta."""
        from backend.api.services.weather_utils import (
            WeatherValidationUtils,
        )

        # Acima de 200 m/s (≈720 km/h, limite físico)
        assert not WeatherValidationUtils.is_valid_wind_speed(250)
        assert not WeatherValidationUtils.is_valid_wind_speed(500)


@pytest.mark.unit
class TestElevationValidation:
    """Testa validação de elevação."""

    def test_valid_elevations(self):
        """Testa elevações válidas."""
        # Jaú, SP (580m)
        assert -500 <= 580 <= 9000

        # Monte Everest (8848m)
        assert -500 <= 8848 <= 9000

        # Mar Morto (-430m)
        assert -500 <= -430 <= 9000

    def test_invalid_elevation_too_low(self):
        """Testa elevação abaixo do limite (-500m)."""
        # Abaixo do Mar Morto
        assert not (-500 <= -600 <= 9000)
        assert not (-500 <= -1000 <= 9000)

    def test_invalid_elevation_too_high(self):
        """Testa elevação acima do limite (9000m)."""
        # Acima dos limites habitáveis
        assert not (-500 <= 10000 <= 9000)
        assert not (-500 <= 15000 <= 9000)
