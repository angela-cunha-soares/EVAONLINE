"""
Met Norway API Mock

Mock responses para Met Norway API.
"""

from unittest.mock import Mock


class MetNorwayMock:
    """Mock para Met Norway API."""

    @staticmethod
    def mock_successful_response():
        """Create a mock successful response."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [-48.5, -22.25, 580]},
            "properties": {
                "timeseries": [
                    {
                        "time": "2025-07-01T00:00:00Z",
                        "data": {
                            "instant": {
                                "details": {
                                    "air_temperature": 25.4,
                                    "relative_humidity": 65.0,
                                }
                            }
                        },
                    }
                ]
            },
        }
        return mock_response
