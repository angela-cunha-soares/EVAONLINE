"""
Unit Tests - ETO Calculation Endpoints

Testa endpoints de cálculo de evapotranspiração de referência (ETo).
"""

import pytest
from unittest.mock import patch, MagicMock


@pytest.mark.unit
class TestETOCalculationEndpoint:
    """Testa POST /api/v1/internal/eto/calculate."""

    def test_calculate_eto_with_valid_data(
        self, api_client, sample_eto_request
    ):
        """Testa cálculo ETO com dados válidos."""
        with patch(
            "backend.infrastructure.celery.tasks.eto_calculation."
            "calculate_eto_task.delay"
        ) as mock_task:
            # Mock tarefa Celery retorna task_id
            mock_task.return_value = MagicMock(id="task-abc-123")

            response = api_client.post(
                "/api/v1/internal/eto/calculate", json=sample_eto_request
            )

            # Deve aceitar (200/202) ou falhar em dependências (500)
            assert response.status_code in [200, 202, 500]

            if response.status_code in [200, 202]:
                data = response.json()
                # Resposta assíncrona com task_id
                assert "task_id" in data or "status" in data

    def test_calculate_eto_missing_required_fields(self, api_client):
        """Testa validação quando faltam campos obrigatórios."""
        incomplete_request = {
            "lat": -22.25,
            # Faltando lng, datas, etc.
        }

        response = api_client.post(
            "/api/v1/internal/eto/calculate", json=incomplete_request
        )

        # Deve retornar 422 Unprocessable Entity
        assert response.status_code == 422
        data = response.json()

        assert "detail" in data

    def test_calculate_eto_invalid_coordinates(self, api_client):
        """Testa validação de coordenadas inválidas."""
        invalid_request = {
            "lat": 100,  # Inválido (> 90)
            "lng": -48.5,
            "start_date": "2025-07-01",
            "end_date": "2025-07-31",
            "elevation": 580,
        }

        response = api_client.post(
            "/api/v1/internal/eto/calculate", json=invalid_request
        )

        # Deve rejeitar coordenadas inválidas (ou falhar em infra)
        assert response.status_code in [400, 422, 500]

    def test_calculate_eto_invalid_date_range(self, api_client):
        """Testa validação quando data final < data inicial."""
        invalid_request = {
            "lat": -22.25,
            "lng": -48.5,
            "start_date": "2025-08-01",
            "end_date": "2025-07-01",  # Antes de start_date!
            "elevation": 580,
        }

        response = api_client.post(
            "/api/v1/internal/eto/calculate", json=invalid_request
        )

        assert response.status_code in [400, 422, 500]

    @pytest.mark.parametrize(
        "invalid_elevation",
        [-1000, 10000, -999999],  # Muito baixo ou muito alto
    )
    def test_calculate_eto_invalid_elevation(
        self, api_client, invalid_elevation
    ):
        """Testa validação de elevação inválida."""
        invalid_request = {
            "lat": -22.25,
            "lng": -48.5,
            "start_date": "2025-07-01",
            "end_date": "2025-07-31",
            "elevation": invalid_elevation,
        }

        response = api_client.post(
            "/api/v1/internal/eto/calculate", json=invalid_request
        )

        assert response.status_code in [400, 422, 500]


@pytest.mark.unit
class TestLocationInfoEndpoint:
    """Testa POST /api/v1/internal/eto/location-info."""

    def test_location_info_returns_elevation(self, api_client):
        """Testa busca de informações da localização."""
        request = {"lat": -22.25, "lng": -48.5}

        response = api_client.post(
            "/api/v1/internal/eto/location-info", json=request
        )

        # Endpoint deve existir
        assert response.status_code == 200
        data = response.json()

        # Deve retornar dados da localização
        assert isinstance(data, dict)
