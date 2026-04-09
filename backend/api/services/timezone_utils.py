"""
Timezone utilities for location-based date calculations.

Uses timezonefinderL to detect timezone based on coordinates,
ensuring consistent date handling across different server timezones.
"""

from datetime import date, datetime
from typing import Optional
import pytz
from timezonefinderL import TimezoneFinder
from loguru import logger

# Singleton TimezoneFinder instance for performance
_tf: Optional[TimezoneFinder] = None


def _get_timezone_finder() -> TimezoneFinder:
    """Returns singleton TimezoneFinder instance."""
    global _tf
    if _tf is None:
        _tf = TimezoneFinder()
    return _tf


def get_timezone_for_location(lat: float, lng: float) -> pytz.BaseTzInfo:
    """
    Detect timezone based on coordinates.

    Args:
        lat: Latitude (-90 to 90)
        lng: Longitude (-180 to 180)

    Returns:
        pytz timezone for the location
    """
    tf = _get_timezone_finder()
    tz_name = tf.timezone_at(lat=lat, lng=lng)

    if tz_name:
        logger.debug(f"🌍 Timezone detected for ({lat}, {lng}): {tz_name}")
        return pytz.timezone(tz_name)

    # Fallback to UTC if timezone cannot be detected
    logger.warning(
        f"⚠️ Could not detect timezone for ({lat}, {lng}), using UTC"
    )
    return pytz.UTC


def get_today_for_location(lat: float, lng: float) -> date:
    """
    Get today's date in the timezone of the specified location.

    Args:
        lat: Latitude
        lng: Longitude

    Returns:
        Current date at the location
    """
    tz = get_timezone_for_location(lat, lng)
    return datetime.now(tz).date()


def get_today_utc() -> date:
    """Get today's date in UTC."""
    return datetime.now(pytz.UTC).date()
