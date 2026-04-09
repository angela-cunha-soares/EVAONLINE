"""
Custom Assertions

Custom assertions for more expressive tests.
"""

import pandas as pd


class CustomAssertions:
    """Custom assertions para testes."""

    @staticmethod
    def assert_coordinates_valid(latitude: float, longitude: float):
        """Assert that coordinates are valid."""
        assert (
            -90 <= latitude <= 90
        ), f"Latitude {latitude} outside the range [-90, 90]"
        assert (
            -180 <= longitude <= 180
        ), f"Longitude {longitude} outside the range [-180, 180]"

    @staticmethod
    def assert_temperature_valid(
        temperature: float, min_temp: float = -100, max_temp: float = 100
    ):
        """Assert that temperature is valid."""
        assert (
            min_temp <= temperature <= max_temp
        ), f"Temperature {temperature} outside the range [{min_temp}, {max_temp}]"

    @staticmethod
    def assert_dict_contains_keys(data: dict, required_keys: list[str]):
        """Assert that dictionary contains required keys."""
        missing_keys = [key for key in required_keys if key not in data]
        assert not missing_keys, f"Missing keys: {missing_keys}"

    @staticmethod
    def assert_climate_data_valid(data: dict):
        """Assert that climate data is valid."""
        required_keys = [
            "latitude",
            "longitude",
            "date",
            "temperature_max",
            "temperature_min",
        ]
        CustomAssertions.assert_dict_contains_keys(data, required_keys)
        CustomAssertions.assert_coordinates_valid(
            data["latitude"], data["longitude"]
        )
        CustomAssertions.assert_temperature_valid(data["temperature_max"])
        CustomAssertions.assert_temperature_valid(data["temperature_min"])
        assert (
            data["temperature_max"] >= data["temperature_min"]
        ), "Tmax deve ser >= Tmin"

    @staticmethod
    def assert_eto_value_valid(eto: float):
        """Assert that the ETO value is valid (0-20 mm/dia)."""
        assert 0 <= eto <= 20, f"ETO {eto} outside the range [0, 20] mm/dia"

    @staticmethod
    def assert_fao56_result_valid(result: dict):
        """Assert that the FAO-56 result is valid."""
        assert result is not None, "FAO-56 result is None"
        CustomAssertions.assert_dict_contains_keys(
            result, ["et0_mm_day", "quality", "method"]
        )
        assert result["method"] == "pm_fao56"
        if "error" not in result:
            CustomAssertions.assert_eto_value_valid(result["et0_mm_day"])
            assert result["quality"] in ("high", "medium", "low")

    @staticmethod
    def assert_fusion_output_valid(df: pd.DataFrame, expected_vars: list[str] = None):
        """Assert that the fusion DataFrame is valid."""
        assert isinstance(df, pd.DataFrame), "Fusion output must be DataFrame"
        assert len(df) > 0, "Fusion output is empty"
        if expected_vars is None:
            expected_vars = [
                "T2M_MAX", "T2M_MIN", "T2M", "RH2M",
                "WS2M", "ALLSKY_SFC_SW_DWN", "PRECTOTCORR",
            ]
        for var in expected_vars:
            assert var in df.columns, f"Missing variable: {var}"

    @staticmethod
    def assert_api_accepted(response, expected_mode: str = None):
        """Assert that API returned accepted (Celery task dispatched)."""
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data["status"] == "accepted"
        assert "task_id" in data
        assert "websocket_url" in data
        if expected_mode:
            assert data.get("operation_mode") == expected_mode

    @staticmethod
    def assert_api_error(response, expected_status: int = 422, msg_contains: str = None):
        """Helper for making HTTP requests in tests."""
        assert response.status_code == expected_status, (
            f"Expected {expected_status}, got {response.status_code}"
        )
        if msg_contains:
            assert msg_contains.lower() in response.text.lower()
