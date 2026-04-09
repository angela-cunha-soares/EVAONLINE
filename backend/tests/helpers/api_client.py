"""
API Client Helper

Helper for making HTTP requests in tests.
"""

from typing import Optional


class APIClientHelper:
    """Helper para testes de API."""

    def __init__(self, client):
        """
        Initialize helper with FastAPI TestClient.

        Args:
            client: TestClient or AsyncClient
        """
        self.client = client

    def get_climate_data(
        self,
        latitude: float,
        longitude: float,
        start_date: str,
        end_date: Optional[str] = None,
    ):
        """
        Makes a request to the climate data endpoint.

        Args:
            latitude: Latitude in decimal degrees
            longitude: Longitude in decimal degrees
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD), optional

        Returns:
            Response object
        """
        params = {
            "lat": latitude,
            "lon": longitude,
            "start_date": start_date,
        }
        if end_date:
            params["end_date"] = end_date

        return self.client.get("/api/climate/data", params=params)

    def calculate_eto(
        self, latitude: float, longitude: float, climate_data: list[dict]
    ):
        """
        Makes a request to the ETO calculation endpoint.

        Args:
            latitude: Latitude in decimal degrees
            longitude: Longitude in decimal degrees
            climate_data: List of climate data dictionaries

        Returns:
            Response object
        """
        payload = {
            "latitude": latitude,
            "longitude": longitude,
            "climate_data": climate_data,
        }
        return self.client.post("/api/eto/calculate", json=payload)

    def assert_success(self, response, expected_status: int = 200):
        """
        Assert that the response was successful.

        Args:
            response: Response object
            expected_status: Expected status code
        """
        assert (
            response.status_code == expected_status
        ), f"Expected {expected_status}, got {response.status_code}: {response.text}"

    def assert_error(
        self,
        response,
        expected_status: int,
        expected_message: Optional[str] = None,
    ):
        """
        Assert that the response returned the expected error.

        Args:
            response: Response object
            expected_status: Expected error status code
            expected_message: Expected error message (optional)
        """
        assert response.status_code == expected_status
        if expected_message:
            assert expected_message in response.text
