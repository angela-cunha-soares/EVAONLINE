"""
Climate Sources Routes
"""

from typing import Any, Dict, Optional
from fastapi import APIRouter, Query
from loguru import logger

from backend.api.services.climate_source_manager import ClimateSourceManager
from backend.api.services.climate_source_selector import ClimateSourceSelector
from backend.api.services.eto_variable_validator import EToVariableValidator

router = APIRouter(prefix="/climate/sources", tags=["Climate"])

# Inicializar gerenciador e seletor globalmente
_manager = ClimateSourceManager()
_selector = ClimateSourceSelector()
_eto_validator = EToVariableValidator()


# ============================================================================
# ENDPOINTS
# ============================================================================


@router.get("")
@router.get("/")
async def list_sources(
    lat: Optional[float] = Query(None, description="Latitude"),
    lon: Optional[float] = Query(None, description="Longitude"),
) -> Dict[str, Any]:
    """
    List available climate data sources.

    Alias for /available — resolves GET /api/v1/climate/sources.
    """
    return await get_available_sources(lat=lat, lon=lon)


@router.get("/available")
async def get_available_sources(
    lat: Optional[float] = Query(None, description="Latitude"),
    lon: Optional[float] = Query(None, description="Longitude"),
) -> Dict[str, Any]:
    """
    ✅ Descobrir fontes de dados climáticos disponíveis.

    Args:
        lat: Latitude (opcional - se fornecida, retorna fontes regionais)
        lon: Longitude (opcional)

    Returns:
        Dict com fontes disponíveis (global + regional se lat/lon fornecidos)
    """
    try:
        # Se lat/lon não fornecidos, retornar todas as fontes
        if lat is None or lon is None:
            sources = []
            for source_id, config in _manager.SOURCES_CONFIG.items():
                # Obter informações de variáveis ETo
                eto_info = _eto_validator.get_source_description(source_id)

                sources.append(
                    {
                        "id": source_id,
                        "name": config.get("name", source_id),
                        "type": config.get("coverage", "unknown"),
                        "coverage": config.get("coverage", "unknown"),
                        "license": config.get("license", "unknown"),
                        "temporal_range": config.get("temporal_range", ""),
                        "data_types": config.get("variables", []),
                        "realtime": config.get("realtime", False),
                        "priority": config.get("priority", 0),
                        "has_complete_eto": eto_info["has_complete_eto"],
                        "eto_status": eto_info["description"],
                        "missing_variables": eto_info["missing_variables"],
                    }
                )

            return {
                "status": "success",
                "sources": sources,
                "total_sources": len(sources),
                "location": None,
                "geographic_context": None,
            }

        # Com lat/lon: obter fontes formatadas do seletor
        from backend.api.services.climate_source_selector import (
            get_available_sources_for_frontend,
        )

        frontend_data = get_available_sources_for_frontend(lat, lon)

        # Extrair contexto geográfico
        location_info = frontend_data.get("location_info", {})
        region = location_info.get("region", "Global")

        geographic_context = "global"
        if location_info.get("in_usa"):
            geographic_context = "usa"
        elif location_info.get("in_nordic"):
            geographic_context = "nordic"

        # Transformar formato do seletor para formato da API
        sources_list = frontend_data.get("sources", [])
        sources = []

        for source in sources_list:
            source_id = source.get("value")
            if source_id and source_id in _manager.SOURCES_CONFIG:
                config = _manager.SOURCES_CONFIG[source_id]
                source_name = source.get(
                    "label", config.get("name", source_id)
                )

                # Obter informações de variáveis ETo
                eto_info = _eto_validator.get_source_description(source_id)

                sources.append(
                    {
                        "id": source_id,
                        "name": source_name,
                        "type": config.get("coverage", "unknown"),
                        "coverage": config.get("coverage", "unknown"),
                        "license": config.get("license", "unknown"),
                        "temporal_range": config.get("temporal_range", ""),
                        "data_types": config.get("variables", []),
                        "realtime": config.get("realtime", False),
                        "priority": config.get("priority", 0),
                        "description": source.get("description", ""),
                        "has_complete_eto": eto_info["has_complete_eto"],
                        "eto_status": eto_info["description"],
                        "missing_variables": eto_info["missing_variables"],
                    }
                )

        logger.info(
            f"Available sources for ({lat}, {lon}) [{geographic_context}]: "
            f"{[s['id'] for s in sources]}"
        )

        return {
            "status": "success",
            "sources": sources,
            "total_sources": len(sources),
            "recommended": frontend_data.get("recommended"),
            "location": {"lat": lat, "lon": lon},
            "geographic_context": geographic_context,
            "region": region,
        }

    except Exception as e:
        logger.error(f"Error getting available sources: {e}")
        return {
            "status": "error",
            "error": str(e),
            "sources": [],
            "total_sources": 0,
        }
