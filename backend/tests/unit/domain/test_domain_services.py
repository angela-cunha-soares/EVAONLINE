"""
Tests for Domain Services (Real Implementation)

Tests: EToCalculationService - FAO-56 Penman-Monteith
"""

import pytest


@pytest.mark.unit
class TestETOCalculationService:
    """Testa serviço de cálculo de ETo (FAO-56 Penman-Monteith)."""

    def test_calculate_et0_with_valid_data(self):
        """Testa cálculo de ETo com dados válidos."""
        from backend.core.eto_calculation.eto_services import (
            EToCalculationService,
        )

        service = EToCalculationService()

        # Dados climáticos válidos (Jaú, SP - dia de verão típico)
        measurements = {
            "T2M_MAX": 32.5,  # Temperatura máxima (°C)
            "T2M_MIN": 18.2,  # Temperatura mínima (°C)
            "T2M": 25.4,  # Temperatura média (°C)
            "RH2M": 65.0,  # Umidade relativa (%)
            "WS2M": 2.5,  # Velocidade do vento (m/s)
            "PRECTOTCORR": 0.0,  # Precipitação (mm)
            "ALLSKY_SFC_SW_DWN": 20.5,  # Radiação solar (MJ/m²/dia)
            "latitude": -22.25,
            "longitude": -48.5,
            "date": "2025-07-01",
            "elevation_m": 580,
        }

        result = service.calculate_et0(measurements)

        # Validações
        assert result is not None, "Service returned None"
        assert "et0_mm_day" in result
        assert result["et0_mm_day"] is not None

        # ETo deve estar em range razoável (0 a 15 mm/dia para Brasil)
        et0_value = result["et0_mm_day"]
        assert (
            0 < et0_value < 15
        ), f"ETo {et0_value} fora do range esperado (0-15 mm/dia)"

    def test_calculate_et0_validates_temperature_range(self):
        """Testa que ETo valida range de temperaturas."""
        from backend.core.eto_calculation.eto_services import (
            EToCalculationService,
        )

        service = EToCalculationService()

        # Tmax < Tmin (inválido)
        measurements = {
            "T2M_MAX": 15.0,  # Menor que Tmin!
            "T2M_MIN": 25.0,
            "T2M": 20.0,
            "RH2M": 65.0,
            "WS2M": 2.5,
            "PRECTOTCORR": 0.0,
            "ALLSKY_SFC_SW_DWN": 20.5,
            "latitude": -22.25,
            "longitude": -48.5,
            "date": "2025-07-01",
            "elevation_m": 580,
        }

        # Service retorna dict com 'error' em caso de erro
        result = service.calculate_et0(measurements)
        assert result is not None, "Service should not return None"
        assert "error" in result, "Should have error key"
        assert "T2M_MAX" in result["error"], "Error should mention T2M_MAX"
        assert result["et0_mm_day"] == 0, "ET0 should be 0 on error"
        assert result["quality"] == "low", "Quality should be low on error"

    def test_calculate_et0_validates_coordinates(self):
        """Testa que ETo valida coordenadas."""
        from backend.core.eto_calculation.eto_services import (
            EToCalculationService,
        )

        service = EToCalculationService()

        # Coordenadas inválidas (lat > 90)
        measurements = {
            "T2M_MAX": 32.5,
            "T2M_MIN": 18.2,
            "T2M": 25.4,
            "RH2M": 65.0,
            "WS2M": 2.5,
            "PRECTOTCORR": 0.0,
            "ALLSKY_SFC_SW_DWN": 20.5,
            "latitude": 100,  # Inválido!
            "longitude": -48.5,
            "date": "2025-07-01",
            "elevation_m": 580,
        }

        # Service retorna dict com 'error' em caso de erro
        result = service.calculate_et0(measurements)
        assert result is not None, "Service should not return None"
        assert "error" in result, "Should have error key"
        assert "Coordenadas inválidas" in result["error"]
        assert result["et0_mm_day"] == 0, "ET0 should be 0 on error"
        assert result["quality"] == "low", "Quality should be low on error"

    def test_calculate_et0_requires_all_variables(self):
        """Testa que ETo exige todas as variáveis obrigatórias."""
        from backend.core.eto_calculation.eto_services import (
            EToCalculationService,
        )

        service = EToCalculationService()

        # Faltando RH2M (umidade)
        measurements = {
            "T2M_MAX": 32.5,
            "T2M_MIN": 18.2,
            "T2M": 25.4,
            # "RH2M": 65.0,  # FALTANDO
            "WS2M": 2.5,
            "PRECTOTCORR": 0.0,
            "ALLSKY_SFC_SW_DWN": 20.5,
            "latitude": -22.25,
            "longitude": -48.5,
            "date": "2025-07-01",
            "elevation_m": 580,
        }

        # Service retorna dict com 'error' em caso de erro
        result = service.calculate_et0(measurements)
        assert result is not None, "Service should not return None"
        assert "error" in result, "Should have error key"
        assert "Variáveis ausentes" in result["error"]
        assert "RH2M" in result["error"], "Error should mention RH2M"
        assert result["et0_mm_day"] == 0, "ET0 should be 0 on error"
        assert result["quality"] == "low", "Quality should be low on error"

    def test_calculate_et0_winter_day(self):
        """Testa cálculo de ETo em dia de inverno."""
        from backend.core.eto_calculation.eto_services import (
            EToCalculationService,
        )

        service = EToCalculationService()

        # Dia de inverno (temperaturas menores, menos radiação)
        measurements = {
            "T2M_MAX": 22.0,
            "T2M_MIN": 10.0,
            "T2M": 16.0,
            "RH2M": 80.0,  # Mais úmido
            "WS2M": 1.5,  # Menos vento
            "PRECTOTCORR": 0.0,
            "ALLSKY_SFC_SW_DWN": 15.0,  # Menos radiação
            "latitude": -22.25,
            "longitude": -48.5,
            "date": "2025-07-01",
            "elevation_m": 580,
        }

        result = service.calculate_et0(measurements)

        # ETo de inverno deve ser menor que verão
        assert result is not None, "Service returned None"
        et0_winter = result["et0_mm_day"]
        assert 0 < et0_winter < 8, f"ETo inverno {et0_winter} fora do esperado"

    def test_calculate_et0_high_elevation(self):
        """Testa cálculo de ETo em alta elevação."""
        from backend.core.eto_calculation.eto_services import (
            EToCalculationService,
        )

        service = EToCalculationService()

        # Alta elevação (2000m)
        measurements = {
            "T2M_MAX": 25.0,
            "T2M_MIN": 12.0,
            "T2M": 18.5,
            "RH2M": 60.0,
            "WS2M": 3.0,
            "PRECTOTCORR": 0.0,
            "ALLSKY_SFC_SW_DWN": 22.0,
            "latitude": -22.25,
            "longitude": -48.5,
            "date": "2025-07-01",
            "elevation_m": 2000,  # Alta elevação
        }

        result = service.calculate_et0(measurements)

        # Deve calcular com pressão atmosférica ajustada
        assert result is not None, "Service returned None"
        assert result["et0_mm_day"] > 0


@pytest.mark.unit
class TestElevationUtils:
    """Testa utilitários de elevação."""

    def test_get_elevation_correction_factor(self):
        """Testa cálculo de fatores de correção por elevação."""
        from backend.api.services.weather_utils import ElevationUtils

        # Nível do mar
        factors_sea = ElevationUtils.get_elevation_correction_factor(0)
        assert factors_sea["pressure"] > 100  # ~101.3 kPa
        assert factors_sea["gamma"] > 0  # Constante psicrométrica

        # Jaú, SP (580m)
        factors_jau = ElevationUtils.get_elevation_correction_factor(580)
        assert factors_jau["pressure"] < factors_sea["pressure"]

        # Alta elevação (2000m)
        factors_high = ElevationUtils.get_elevation_correction_factor(2000)
        assert factors_high["pressure"] < factors_jau["pressure"]


@pytest.mark.unit
class TestGeographicRegionDetection:
    """Testa detecção de regiões geográficas."""

    def test_detect_brazil_region(self):
        """Testa detecção de coordenadas no Brasil."""
        from backend.api.services.geographic_utils import GeographicUtils

        # Jaú, SP
        assert GeographicUtils.is_in_brazil(-22.25, -48.5)

        # Manaus, AM
        assert GeographicUtils.is_in_brazil(-3.119, -60.021)

        # Fora do Brasil (Buenos Aires)
        assert not GeographicUtils.is_in_brazil(-34.6037, -58.3816)

    def test_detect_usa_region(self):
        """Testa detecção de coordenadas nos EUA."""
        from backend.api.services.geographic_utils import GeographicUtils

        # Nova York
        assert GeographicUtils.is_in_usa(40.7128, -74.0060)

        # Fora dos EUA (Cidade do México)
        assert not GeographicUtils.is_in_usa(19.4326, -99.1332)

    def test_detect_nordic_region(self):
        """Testa detecção de coordenadas na região nórdica."""
        from backend.api.services.geographic_utils import GeographicUtils

        # Oslo, Noruega
        assert GeographicUtils.is_in_nordic(59.9139, 10.7522)

        # Estocolmo, Suécia
        assert GeographicUtils.is_in_nordic(59.3293, 18.0686)

        # Fora da região (Londres)
        assert not GeographicUtils.is_in_nordic(51.5074, -0.1278)
