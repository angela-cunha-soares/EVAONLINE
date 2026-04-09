"""
Climate Data Builder

Builder Pattern for creating complex ClimateData objects.
"""

from datetime import datetime, timedelta


class ClimateDataBuilder:
    """Builder for creating complex ClimateData objects."""

    def __init__(self):
        self._latitude: float = -22.25
        self._longitude: float = -48.5
        self._date: datetime = datetime.now().date()
        self._temperature_max: float = 32.5
        self._temperature_min: float = 18.2
        self._humidity: float = 65.0
        self._wind_speed: float = 2.5
        self._solar_radiation: float = 20.5
        self._precipitation: float = 0.0
        self._source: str = "NASA_POWER"

    def with_location(self, latitude: float, longitude: float):
        """Define location."""
        self._latitude = latitude
        self._longitude = longitude
        return self

    def with_date(self, date: datetime):
        """Define data."""
        self._date = date
        return self

    def with_temperature(self, max_temp: float, min_temp: float):
        """Define temperatures."""
        self._temperature_max = max_temp
        self._temperature_min = min_temp
        return self

    def with_humidity(self, humidity: float):
        """Define humidity."""
        self._humidity = humidity
        return self

    def with_precipitation(self, precipitation: float):
        """Define precipitation."""
        self._precipitation = precipitation
        return self

    def with_source(self, source: str):
        """Define data source."""
        self._source = source
        return self

    def build(self) -> dict:
        """Build the final dictionary."""
        return {
            "latitude": self._latitude,
            "longitude": self._longitude,
            "date": self._date,
            "temperature_max": self._temperature_max,
            "temperature_min": self._temperature_min,
            "temperature_avg": (self._temperature_max + self._temperature_min)
            / 2,
            "humidity": self._humidity,
            "wind_speed": self._wind_speed,
            "solar_radiation": self._solar_radiation,
            "precipitation": self._precipitation,
            "source": self._source,
        }

    def build_series(self, days: int = 90) -> list[dict]:
        """Build a temporal series."""
        base_date = self._date
        series = []

        for i in range(days):
            self.with_date(base_date + timedelta(days=i))
            series.append(self.build())

        return series
