"""
API Response Builder
"""

from datetime import datetime


class APIResponseBuilder:
    """Builder for creating responses from external APIs."""

    @staticmethod
    def build_nasa_power_response(
        latitude: float = -22.25,
        longitude: float = -48.5,
        start_date: str = "20250701",
        end_date: str = "20250928",
    ) -> dict:
        """
        Creates a NASA Power API response.

        Args:
            latitude: Requested latitude
            longitude: Requested longitude
            start_date: Start date (YYYYMMDD)
            end_date: End date (YYYYMMDD)

        Returns:
            Dictionary simulating a NASA Power response
        """
        return {
            "header": {
                "title": "NASA/POWER CERES/MERRA2 Native Resolution Daily Data",
                "api_version": "v2.5.4",
                "fill_value": -999.0,
            },
            "messages": [],
            "parameters": {
                "T2M_MAX": {
                    "20250701": 32.5,
                    "20250702": 33.1,
                    "20250703": 31.8,
                },
                "T2M_MIN": {
                    "20250701": 18.2,
                    "20250702": 19.1,
                    "20250703": 17.5,
                },
                "RH2M": {
                    "20250701": 65.0,
                    "20250702": 68.5,
                    "20250703": 62.3,
                },
                "WS2M": {
                    "20250701": 2.5,
                    "20250702": 3.1,
                    "20250703": 2.2,
                },
                "ALLSKY_SFC_SW_DWN": {
                    "20250701": 20.5,
                    "20250702": 19.8,
                    "20250703": 21.2,
                },
                "PRECTOTCORR": {
                    "20250701": 0.0,
                    "20250702": 5.2,
                    "20250703": 0.0,
                },
            },
            "geometry": {
                "type": "Point",
                "coordinates": [longitude, latitude],
            },
        }

    @staticmethod
    def build_met_norway_response(
        latitude: float = -22.25, longitude: float = -48.5
    ) -> dict:
        """
        Creates a response from the Met Norway API.

        Args:
            latitude: Requested latitude
            longitude: Requested longitude

        Returns:
            Dictionary simulating a response from Met Norway
        """
        return {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [longitude, latitude, 580],
            },
            "properties": {
                "meta": {
                    "updated_at": datetime.now().isoformat(),
                    "units": {
                        "air_temperature": "celsius",
                        "precipitation_amount": "mm",
                        "wind_speed": "m/s",
                    },
                },
                "timeseries": [
                    {
                        "time": "2025-07-01T00:00:00Z",
                        "data": {
                            "instant": {
                                "details": {
                                    "air_temperature": 25.4,
                                    "relative_humidity": 65.0,
                                    "wind_speed": 2.5,
                                }
                            },
                            "next_6_hours": {
                                "summary": {"symbol_code": "partlycloudy_day"},
                                "details": {"precipitation_amount": 0.0},
                            },
                        },
                    }
                ],
            },
        }

    @staticmethod
    def build_opentopo_response(elevation: float = 580.0) -> dict:
        """
        Creates an OpenTopo API response.

        Args:
            elevation: Elevation in meters

        Returns:
            Dictionary simulating an OpenTopo response
        """
        return {
            "status": "OK",
            "results": [
                {
                    "elevation": elevation,
                    "location": {"lat": -22.25, "lng": -48.5},
                }
            ],
        }
