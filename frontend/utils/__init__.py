"""
Utils package for ETO Calculator application.

Timezone functions are in mode_detector.py (fast, offline via timezonefinderL).
"""

from .user_geolocation import (
    calculate_geolocation_accuracy,
    get_fallback_location,
    is_valid_coordinate_range,
    validate_geolocation_permission,
)

__all__ = [
    # user_geolocation
    "validate_geolocation_permission",
    "calculate_geolocation_accuracy",
    "get_fallback_location",
    "is_valid_coordinate_range",
]
