"""
Climate Data Factory - Using factory_boy with Faker

Factory for creating ClimateData objects for testing.
Uses factory_boy for DRY factories and Faker for realistic data.
"""
from factory import Factory, Faker, LazyAttribute  # type: ignore
from datetime import datetime, timedelta


class ClimateDataFactory(Factory):
    """
    Factory for creating climate data objects for testing using factory_boy.

    Basic usage:
        data = ClimateDataFactory()
        batch = ClimateDataFactory.build_batch(90)
        custom = ClimateDataFactory(latitude=-15.0, temperature_max=35.0)
    """

    class Meta:
        model = dict

    # Location (defaults to Jaú, SP)
    latitude = -22.25
    longitude = -48.5
    elevation = 580

    # Data
    date = Faker("date_this_year")

    # Temperatures (°C) - Faker generates realistic values
    temperature_max = Faker(
        "pyfloat", min_value=20.0, max_value=40.0, right_digits=1
    )
    temperature_min = Faker(
        "pyfloat", min_value=10.0, max_value=25.0, right_digits=1
    )

    @LazyAttribute
    def temperature_avg(self):
        """Calculates average temperature automatically."""
        return round((self.temperature_max + self.temperature_min) / 2, 1)

    # Humidity (%)
    humidity = Faker("pyfloat", min_value=40.0, max_value=90.0, right_digits=1)

    # Wind Speed (m/s)
    wind_speed = Faker("pyfloat", min_value=0.5, max_value=8.0, right_digits=1)

    # Solar Radiation (MJ/m²/dia)
    solar_radiation = Faker(
        "pyfloat", min_value=15.0, max_value=30.0, right_digits=1
    )

    # Precipitation (mm)
    precipitation = Faker(
        "pyfloat", min_value=0.0, max_value=50.0, right_digits=1
    )

    # Data Source
    source = "NASA_POWER"


class SummerDayFactory(ClimateDataFactory):
    """Factory for typical summer days."""

    temperature_max = 32.5
    temperature_min = 18.2
    humidity = 65.0
    wind_speed = 2.5
    solar_radiation = 20.5
    precipitation = 0.0

    @LazyAttribute
    def temperature_avg(self):
        return 25.4


class WinterDayFactory(ClimateDataFactory):
    """Factory for typical winter days."""

    temperature_max = 22.0
    temperature_min = 10.0
    humidity = 80.0
    wind_speed = 1.5
    solar_radiation = 15.0
    precipitation = 0.0

    @LazyAttribute
    def temperature_avg(self):
        return 16.0


class RainyDayFactory(ClimateDataFactory):
    """Factory for rainy days."""

    temperature_max = 25.0
    temperature_min = 16.0
    humidity = 85.0
    wind_speed = 3.5
    solar_radiation = 12.0
    precipitation = Faker(
        "pyfloat", min_value=10.0, max_value=80.0, right_digits=1
    )

    @LazyAttribute
    def temperature_avg(self):
        return 20.5


# =============================================================================
# HELPER FUNCTIONS (compatibility with old code)
# =============================================================================


def create_sample_data(**kwargs):
    """
    Creates sample climate data (for compatibility with older code).

    Args:
        **kwargs: Parameters to override

    Returns:
        dict: Climate data
    """
    return ClimateDataFactory(**kwargs)


def create_90_day_series(start_date=None, **kwargs):
    """
    Creates a 90-day series of climate data.

    Args:
        start_date: Initial date (default: 2025-07-01)
        **kwargs: Additional parameters

    Returns:
        list[dict]: List with 90 dictionaries of climate data
    """
    if start_date is None:
        start_date = datetime(2025, 7, 1).date()

    return [
        ClimateDataFactory(date=start_date + timedelta(days=i), **kwargs)
        for i in range(90)
    ]


def create_batch_with_sequence(size=10, start_date=None, **kwargs):
    """
    Creates a batch with sequential dates.

    Args:
        size: Number of records
        start_date: Initial date
        **kwargs: Additional parameters

    Returns:
        list[dict]: List of dictionaries
    """
    if start_date is None:
        start_date = datetime(2025, 7, 1).date()

    return [
        ClimateDataFactory(date=start_date + timedelta(days=i), **kwargs)
        for i in range(size)
    ]
