"""
ETo Variable Validator

Validates if a data source has all required variables for FAO-56 ETo calculation.
"""

from typing import Dict, List, Set
from loguru import logger


class EToVariableValidator:
    """Validates if climate sources have required variables for ETo calculation."""

    # Variáveis obrigatórias para cálculo de ETo FAO-56
    # Baseado em: Allen et al., 1998 - FAO Irrigation and Drainage Paper 56
    REQUIRED_VARIABLES = {
        "temperature_max",  # Temperatura máxima do ar (°C)
        "temperature_min",  # Temperatura mínima do ar (°C)
        "temperature_mean",  # Temperatura média do ar (°C)
        "relative_humidity",  # Umidade relativa média (%)
        "wind_speed",  # Velocidade do vento a 2m (m/s)
        "solar_radiation",  # Radiação solar (MJ/m²/dia)
    }

    # Mapeamento de variáveis por fonte de dados
    # Mapeia as variáveis disponíveis em cada API para as variáveis padrão
    SOURCE_VARIABLES: Dict[str, Set[str]] = {
        "nasa_power": {
            "temperature_max",
            "temperature_min",
            "temperature_mean",
            "relative_humidity",
            "wind_speed",
            "solar_radiation",
            "precipitation",
        },
        "openmeteo_archive": {
            "temperature_max",
            "temperature_min",
            "temperature_mean",
            "relative_humidity",
            "wind_speed",
            "solar_radiation",
            "precipitation",
        },
        "openmeteo_forecast": {
            "temperature_max",
            "temperature_min",
            "temperature_mean",
            "relative_humidity",
            "wind_speed",
            "solar_radiation",
            "precipitation",
        },
        "met_norway": {
            "temperature_max",
            "temperature_min",
            "temperature_mean",
            "relative_humidity",
            # Nota: MET Norway NÃO fornece wind_speed e solar_radiation globalmente
            # Apenas temperatura e umidade são confiáveis
        },
        "nws_forecast": {
            "temperature_max",
            "temperature_min",
            "temperature_mean",
            "relative_humidity",
            "wind_speed",
            # Nota: NWS NÃO fornece solar_radiation diretamente
        },
        "nws_stations": {
            "temperature",
            "relative_humidity",
            "wind_speed",
            # Nota: NWS Stations são observações pontuais, não ideais para ETo
        },
    }

    @classmethod
    def has_all_eto_variables(cls, source_id: str) -> bool:
        """
        Verifica se uma fonte tem todas as variáveis necessárias para ETo.

        Args:
            source_id: ID da fonte (ex: "nasa_power", "openmeteo_forecast")

        Returns:
            True se a fonte tem todas as variáveis, False caso contrário
        """
        if source_id not in cls.SOURCE_VARIABLES:
            logger.warning(f"Fonte desconhecida: {source_id}")
            return False

        available_vars = cls.SOURCE_VARIABLES[source_id]
        has_all = cls.REQUIRED_VARIABLES.issubset(available_vars)

        if not has_all:
            missing = cls.REQUIRED_VARIABLES - available_vars
            logger.debug(
                f"Fonte {source_id} não tem todas variáveis ETo. "
                f"Faltam: {missing}"
            )

        return has_all

    @classmethod
    def get_missing_variables(cls, source_id: str) -> Set[str]:
        """
        Retorna as variáveis faltantes para cálculo de ETo.

        Args:
            source_id: ID da fonte

        Returns:
            Set com as variáveis faltantes
        """
        if source_id not in cls.SOURCE_VARIABLES:
            return cls.REQUIRED_VARIABLES

        available_vars = cls.SOURCE_VARIABLES[source_id]
        return cls.REQUIRED_VARIABLES - available_vars

    @classmethod
    def get_available_variables(cls, source_id: str) -> Set[str]:
        """
        Retorna as variáveis disponíveis em uma fonte.

        Args:
            source_id: ID da fonte

        Returns:
            Set com as variáveis disponíveis
        """
        return cls.SOURCE_VARIABLES.get(source_id, set())

    @classmethod
    def get_sources_with_complete_eto(cls) -> List[str]:
        """
        Retorna lista de fontes que têm todas as variáveis para ETo.

        Returns:
            Lista de source_ids que podem calcular ETo completo
        """
        return [
            source_id
            for source_id in cls.SOURCE_VARIABLES
            if cls.has_all_eto_variables(source_id)
        ]

    @classmethod
    def get_source_description(cls, source_id: str) -> Dict[str, any]:
        """
        Retorna descrição completa de uma fonte para o dropdown.

        Args:
            source_id: ID da fonte

        Returns:
            Dict com: name, has_eto, missing_vars, description
        """
        source_names = {
            "nasa_power": "NASA POWER",
            "openmeteo_archive": "Open-Meteo Archive",
            "openmeteo_forecast": "Open-Meteo Forecast",
            "met_norway": "MET Norway",
            "nws_forecast": "NWS Forecast (USA)",
            "nws_stations": "NWS Stations (USA)",
        }

        has_eto = cls.has_all_eto_variables(source_id)
        missing = cls.get_missing_variables(source_id)

        # Descrição detalhada
        if has_eto:
            description = "✓ Complete - All variables for ETo calculation"
        else:
            missing_list = ", ".join(sorted(missing))
            description = f"⚠ Incomplete - Missing: {missing_list}"

        return {
            "id": source_id,
            "name": source_names.get(source_id, source_id),
            "has_complete_eto": has_eto,
            "missing_variables": list(missing),
            "description": description,
        }
