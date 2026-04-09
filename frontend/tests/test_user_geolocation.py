"""Tests for frontend.utils.user_geolocation module."""

from frontend.utils.user_geolocation import (
    validate_geolocation_permission,
    calculate_geolocation_accuracy,
    get_fallback_location,
    is_valid_coordinate_range,
)


class TestValidateGeolocationPermission:
    def test_returns_true(self):
        assert validate_geolocation_permission() is True


class TestCalculateGeolocationAccuracy:
    def test_high_precision(self):
        assert calculate_geolocation_accuracy({"accuracy": 5}) == "alta precisão"

    def test_moderate_precision(self):
        assert calculate_geolocation_accuracy({"accuracy": 30}) == "precisão moderada"

    def test_low_precision(self):
        assert calculate_geolocation_accuracy({"accuracy": 80}) == "precisão baixa"

    def test_very_low_precision(self):
        assert calculate_geolocation_accuracy({"accuracy": 200}) == "precisão muito baixa"

    def test_zero_accuracy(self):
        assert calculate_geolocation_accuracy({"accuracy": 0}) == "alta precisão"

    def test_missing_accuracy_key(self):
        assert calculate_geolocation_accuracy({}) == "alta precisão"

    def test_none_input_returns_unknown(self):
        # None.get() raises AttributeError → "precisão desconhecida"
        assert calculate_geolocation_accuracy(None) == "precisão desconhecida"

    def test_boundary_10(self):
        assert calculate_geolocation_accuracy({"accuracy": 10}) == "precisão moderada"

    def test_boundary_50(self):
        assert calculate_geolocation_accuracy({"accuracy": 50}) == "precisão baixa"

    def test_boundary_100(self):
        assert calculate_geolocation_accuracy({"accuracy": 100}) == "precisão muito baixa"


class TestGetFallbackLocation:
    def test_returns_brasilia(self):
        lat, lon = get_fallback_location()
        assert lat == -15.793889
        assert lon == -47.882778

    def test_returns_tuple(self):
        result = get_fallback_location()
        assert isinstance(result, tuple)
        assert len(result) == 2


class TestIsValidCoordinateRange:
    def test_valid_coords(self):
        assert is_valid_coordinate_range(0.0, 0.0) is True

    def test_valid_extremes(self):
        assert is_valid_coordinate_range(90, 180) is True
        assert is_valid_coordinate_range(-90, -180) is True

    def test_invalid_lat_too_high(self):
        assert is_valid_coordinate_range(91, 0) is False

    def test_invalid_lat_too_low(self):
        assert is_valid_coordinate_range(-91, 0) is False

    def test_invalid_lon_too_high(self):
        assert is_valid_coordinate_range(0, 181) is False

    def test_invalid_lon_too_low(self):
        assert is_valid_coordinate_range(0, -181) is False

    def test_brasilia_coordinates(self):
        assert is_valid_coordinate_range(-15.79, -47.88) is True
