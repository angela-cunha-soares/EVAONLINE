"""
Tests for NASA Power Adapter - Using pytest-mock

Demonstra uso de pytest-mock para mocking simplificado.
"""

import pytest


@pytest.mark.unit
class TestNASAPowerAdapterWithMock:
    """Testa adapter NASA Power usando pytest-mock."""

    def test_successful_request_with_mocker(self, mocker):
        """
        Testa request bem-sucedido usando mocker fixture.
        """
        # Mock da resposta HTTP
        mock_response = mocker.Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "header": {"title": "NASA/POWER", "api_version": "v2.5.4"},
            "parameters": {
                "T2M_MAX": {"20250701": 32.5},
                "T2M_MIN": {"20250701": 18.2},
            },
            "geometry": {"type": "Point", "coordinates": [-48.5, -22.25]},
        }

        # Mock do httpx.get
        mock_get = mocker.patch("httpx.get", return_value=mock_response)

        # Simular chamada ao adapter
        import httpx

        response = httpx.get("https://power.larc.nasa.gov/api/...")

        # Validações
        assert response.status_code == 200
        data = response.json()
        assert data["parameters"]["T2M_MAX"]["20250701"] == 32.5
        mock_get.assert_called_once()

    def test_timeout_error_with_mocker(self, mocker):
        """Testa timeout usando mocker.patch."""
        import httpx

        # Mock que lança exceção
        mocker.patch(
            "httpx.get", side_effect=httpx.TimeoutException("Request timeout")
        )

        # Verificar que exceção é lançada
        with pytest.raises(httpx.TimeoutException):
            httpx.get("https://power.larc.nasa.gov/api/...")

    def test_spy_on_custom_object(self, mocker):
        """
        Testa spy - permite chamar função real e verificar chamadas.

        Diferente de mock, spy não substitui a função.
        Nota: Spy não funciona com tipos built-in imutáveis como dict.
        """

        # Criar classe customizada para demonstrar spy
        class DataProcessor:
            def process(self, data):
                return data.upper()

        processor = DataProcessor()

        # Criar spy (não bloqueia chamada real)
        spy = mocker.spy(processor, "process")

        # Usar função real
        result = processor.process("hello")

        # Verificar que foi chamada E retornou valor correto
        spy.assert_called_once_with("hello")
        assert result == "HELLO"

    def test_mock_multiple_calls(self, mocker):
        """Testa múltiplas chamadas com side_effect."""
        mock_get = mocker.patch("httpx.get")

        # Primeira chamada: timeout
        # Segunda chamada: sucesso
        mock_get.side_effect = [
            Exception("Timeout"),
            mocker.Mock(status_code=200, json=lambda: {"data": "ok"}),
        ]

        # Primeira chamada falha
        with pytest.raises(Exception, match="Timeout"):
            import httpx

            httpx.get("https://api.com")

        # Segunda chamada sucede
        response = httpx.get("https://api.com")
        assert response.status_code == 200

    def test_mock_with_return_value_chain(self, mocker):
        """Testa mock com cadeia de return_value."""
        mock_client = mocker.Mock()
        mock_client.get_data.return_value.json.return_value = {
            "temperature": 25.0
        }

        # Uso
        result = mock_client.get_data().json()
        assert result["temperature"] == 25.0


@pytest.mark.unit
class TestFactoryBoyIntegration:
    """Demonstra uso de factory_boy com pytest-mock."""

    def test_climate_data_factory_with_faker(self):
        """Testa factory_boy com Faker integrado."""
        from backend.tests.fixtures.factories.climate_data_factory import (
            ClimateDataFactory,
        )

        # Criar dados aleatórios
        data = ClimateDataFactory.create()

        # Validações
        assert -90 <= data["latitude"] <= 90
        assert -180 <= data["longitude"] <= 180
        assert 10 <= data["temperature_min"] <= 25
        assert 20 <= data["temperature_max"] <= 40
        assert data["temperature_max"] >= data["temperature_min"]

    def test_batch_creation_with_factory_boy(self):
        """Testa criação em batch."""
        from backend.tests.fixtures.factories.climate_data_factory import (
            create_batch_with_sequence,
        )

        # Criar 10 registros de uma vez
        batch = create_batch_with_sequence(size=10)

        assert len(batch) == 10
        # Datas são sequenciais
        for i in range(1, len(batch)):
            days_diff = (batch[i]["date"] - batch[i - 1]["date"]).days
            assert days_diff == 1

    def test_preset_scenarios_with_factory_boy(self):
        """Testa cenários pré-definidos."""
        from backend.tests.fixtures.factories.climate_data_factory import (
            SummerDayFactory,
            WinterDayFactory,
            RainyDayFactory,
        )

        # Dia de verão
        summer = SummerDayFactory()
        assert summer["temperature_max"] == 32.5
        assert summer["temperature_min"] == 18.2

        # Dia de inverno
        winter = WinterDayFactory()
        assert winter["temperature_max"] == 22.0
        assert winter["humidity"] == 80.0

        # Dia chuvoso
        rainy = RainyDayFactory()
        assert rainy["precipitation"] >= 10.0
