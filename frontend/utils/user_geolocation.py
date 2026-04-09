"""
Utilitários para geolocalização do usuário.

Features:
- Validação de permissões de localização
- Fallbacks para quando a geolocalização falha
- Cálculo de precisão de coordenadas
"""

import logging
from typing import Dict, Tuple

logger = logging.getLogger(__name__)


def validate_geolocation_permission() -> bool:
    """
    Simula validação de permissão de geolocalização.
    Returns:
        bool: True se a geolocalização está disponível
    """
    # Em uma aplicação real, isso verificaria as permissões do navegador
    # Por enquanto, sempre retorna True (assume que está disponível)
    logger.debug("🔍 Validando permissão de geolocalização")
    return True


def calculate_geolocation_accuracy(position: Dict) -> str:
    """
    Calcula a precisão da geolocalização baseado nos dados fornecidos.
    Args:
        position: Dados de posição do navegador
    Returns:
        str: Descrição da precisão
    """
    try:
        accuracy = position.get("accuracy", 0)
        if accuracy < 10:
            return "alta precisão"
        elif accuracy < 50:
            return "precisão moderada"
        elif accuracy < 100:
            return "precisão baixa"
        else:
            return "precisão muito baixa"
    except Exception as e:
        logger.warning(f"⚠️ Erro ao calcular precisão: {e}")
        return "precisão desconhecida"


def get_fallback_location() -> Tuple[float, float]:
    """
    Retorna uma localização de fallback quando a geolocalização falha.
    Returns:
        tuple: (lat, lon) - Centro do Brasil como fallback
    """
    logger.info("🔄 Usando localização de fallback (Centro do Brasil)")
    return -15.793889, -47.882778  # Brasília, DF


def is_valid_coordinate_range(lat: float, lon: float) -> bool:
    """
    Valida se as coordenadas estão dentro de ranges válidos.
    Args:
        lat: Latitude
        lon: Longitude
    Returns:
        bool: True se as coordenadas são válidas
    """
    valid_lat = -90 <= lat <= 90
    valid_lon = -180 <= lon <= 180
    if not valid_lat or not valid_lon:
        logger.warning(f"❌ Coordenadas fora do range válido: ({lat}, {lon})")
        return False
    return True


logger.info("✅ Utilitários de geolocalização carregados com sucesso")
