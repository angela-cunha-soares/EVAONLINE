"""
Seed inicial para tabela api_variables.

Mapeia variáveis de todas as 6 fontes de dados para nomes padronizados.
Este seed deve ser executado após a criação da tabela api_variables.

Uso:
    python database/seeds/api_variables_seed.py
"""

from typing import Any, Dict, List

# Dados do seed
API_VARIABLES_DATA: List[Dict[str, Any]] = [
    # =========================================================================
    # NASA POWER (1981+ | Histórico Global)
    # =========================================================================
    {
        "source_api": "nasa_power",
        "variable_name": "T2M_MAX",
        "standard_name": "temp_max_c",
        "unit": "°C",
        "description": "Temperatura máxima a 2 metros",
        "is_required_for_eto": True,
    },
    {
        "source_api": "nasa_power",
        "variable_name": "T2M_MIN",
        "standard_name": "temp_min_c",
        "unit": "°C",
        "description": "Temperatura mínima a 2 metros",
        "is_required_for_eto": True,
    },
    {
        "source_api": "nasa_power",
        "variable_name": "T2M",
        "standard_name": "temp_mean_c",
        "unit": "°C",
        "description": "Temperatura média a 2 metros",
        "is_required_for_eto": False,
    },
    {
        "source_api": "nasa_power",
        "variable_name": "RH2M",
        "standard_name": "humidity_percent",
        "unit": "%",
        "description": "Umidade relativa a 2 metros",
        "is_required_for_eto": True,
    },
    {
        "source_api": "nasa_power",
        "variable_name": "WS2M",
        "standard_name": "wind_speed_ms",
        "unit": "m/s",
        "description": "Velocidade do vento a 2 metros",
        "is_required_for_eto": True,
    },
    {
        "source_api": "nasa_power",
        "variable_name": "ALLSKY_SFC_SW_DWN",
        "standard_name": "solar_radiation_mjm2",
        "unit": "MJ/m²/d",
        "description": "Radiação solar de onda curta descendente",
        "is_required_for_eto": True,
    },
    {
        "source_api": "nasa_power",
        "variable_name": "PRECTOTCORR",
        "standard_name": "precipitation_mm",
        "unit": "mm/d",
        "description": "Precipitação total corrigida",
        "is_required_for_eto": False,
    },
    # =========================================================================
    # Open-Meteo Archive (1940+ | Histórico Global)
    # =========================================================================
    {
        "source_api": "openmeteo_archive",
        "variable_name": "temperature_2m_max",
        "standard_name": "temp_max_c",
        "unit": "°C",
        "description": "Temperatura máxima a 2 metros",
        "is_required_for_eto": True,
    },
    {
        "source_api": "openmeteo_archive",
        "variable_name": "temperature_2m_min",
        "standard_name": "temp_min_c",
        "unit": "°C",
        "description": "Temperatura mínima a 2 metros",
        "is_required_for_eto": True,
    },
    {
        "source_api": "openmeteo_archive",
        "variable_name": "temperature_2m_mean",
        "standard_name": "temp_mean_c",
        "unit": "°C",
        "description": "Temperatura média a 2 metros",
        "is_required_for_eto": False,
    },
    {
        "source_api": "openmeteo_archive",
        "variable_name": "relative_humidity_2m_mean",
        "standard_name": "humidity_percent",
        "unit": "%",
        "description": "Umidade relativa média a 2 metros",
        "is_required_for_eto": True,
    },
    {
        "source_api": "openmeteo_archive",
        "variable_name": "wind_speed_10m_max",
        "standard_name": "wind_speed_ms",
        "unit": "m/s",
        "description": "Velocidade máxima do vento a 10 metros",
        "is_required_for_eto": True,
    },
    {
        "source_api": "openmeteo_archive",
        "variable_name": "shortwave_radiation_sum",
        "standard_name": "solar_radiation_mjm2",
        "unit": "MJ/m²/d",
        "description": "Soma de radiação de onda curta",
        "is_required_for_eto": True,
    },
    {
        "source_api": "openmeteo_archive",
        "variable_name": "precipitation_sum",
        "standard_name": "precipitation_mm",
        "unit": "mm/d",
        "description": "Precipitação total diária",
        "is_required_for_eto": False,
    },
    {
        "source_api": "openmeteo_archive",
        "variable_name": "et0_fao_evapotranspiration",
        "standard_name": "eto_fao_mm",
        "unit": "mm/d",
        "description": "ETo FAO-56 pré-calculado pela API",
        "is_required_for_eto": False,
    },
    # =========================================================================
    # Open-Meteo Forecast (-30d a +16d | Híbrido Global)
    # =========================================================================
    {
        "source_api": "openmeteo_forecast",
        "variable_name": "temperature_2m_max",
        "standard_name": "temp_max_c",
        "unit": "°C",
        "description": "Temperatura máxima a 2 metros (previsão)",
        "is_required_for_eto": True,
    },
    {
        "source_api": "openmeteo_forecast",
        "variable_name": "temperature_2m_min",
        "standard_name": "temp_min_c",
        "unit": "°C",
        "description": "Temperatura mínima a 2 metros (previsão)",
        "is_required_for_eto": True,
    },
    {
        "source_api": "openmeteo_forecast",
        "variable_name": "relative_humidity_2m_mean",
        "standard_name": "humidity_percent",
        "unit": "%",
        "description": "Umidade relativa média (previsão)",
        "is_required_for_eto": True,
    },
    {
        "source_api": "openmeteo_forecast",
        "variable_name": "wind_speed_10m_max",
        "standard_name": "wind_speed_ms",
        "unit": "m/s",
        "description": "Velocidade máxima do vento (previsão)",
        "is_required_for_eto": True,
    },
    {
        "source_api": "openmeteo_forecast",
        "variable_name": "shortwave_radiation_sum",
        "standard_name": "solar_radiation_mjm2",
        "unit": "MJ/m²/d",
        "description": "Radiação solar (previsão)",
        "is_required_for_eto": True,
    },
    {
        "source_api": "openmeteo_forecast",
        "variable_name": "precipitation_sum",
        "standard_name": "precipitation_mm",
        "unit": "mm/d",
        "description": "Precipitação prevista",
        "is_required_for_eto": False,
    },
    {
        "source_api": "openmeteo_forecast",
        "variable_name": "et0_fao_evapotranspiration",
        "standard_name": "eto_fao_mm",
        "unit": "mm/d",
        "description": "ETo FAO-56 previsto pela API",
        "is_required_for_eto": False,
    },
    # =========================================================================
    # MET Norway (hoje a +5d | Forecast Nórdico)
    # =========================================================================
    {
        "source_api": "met_norway",
        "variable_name": "air_temperature_max",
        "standard_name": "temp_max_c",
        "unit": "°C",
        "description": "Temperatura máxima do ar",
        "is_required_for_eto": True,
    },
    {
        "source_api": "met_norway",
        "variable_name": "air_temperature_min",
        "standard_name": "temp_min_c",
        "unit": "°C",
        "description": "Temperatura mínima do ar",
        "is_required_for_eto": True,
    },
    {
        "source_api": "met_norway",
        "variable_name": "relative_humidity",
        "standard_name": "humidity_percent",
        "unit": "%",
        "description": "Umidade relativa",
        "is_required_for_eto": True,
    },
    {
        "source_api": "met_norway",
        "variable_name": "wind_speed",
        "standard_name": "wind_speed_ms",
        "unit": "m/s",
        "description": "Velocidade do vento",
        "is_required_for_eto": True,
    },
    {
        "source_api": "met_norway",
        "variable_name": "shortwave_radiation",
        "standard_name": "solar_radiation_mjm2",
        "unit": "MJ/m²/d",
        "description": "Radiação de onda curta",
        "is_required_for_eto": True,
    },
    {
        "source_api": "met_norway",
        "variable_name": "precipitation_amount",
        "standard_name": "precipitation_mm",
        "unit": "mm",
        "description": "Quantidade de precipitação",
        "is_required_for_eto": False,
    },
    # =========================================================================
    # NWS Forecast (hoje a +7d | Forecast USA)
    # =========================================================================
    {
        "source_api": "nws_forecast",
        "variable_name": "temperature",
        "standard_name": "temp_mean_c",
        "unit": "°C",
        "description": "Temperatura prevista",
        "is_required_for_eto": True,
    },
    {
        "source_api": "nws_forecast",
        "variable_name": "dewpoint",
        "standard_name": "dewpoint_c",
        "unit": "°C",
        "description": "Ponto de orvalho (para calcular umidade)",
        "is_required_for_eto": True,
    },
    {
        "source_api": "nws_forecast",
        "variable_name": "windSpeed",
        "standard_name": "wind_speed_ms",
        "unit": "m/s",
        "description": "Velocidade do vento",
        "is_required_for_eto": True,
    },
    {
        "source_api": "nws_forecast",
        "variable_name": "probabilityOfPrecipitation",
        "standard_name": "precipitation_probability",
        "unit": "%",
        "description": "Probabilidade de precipitação",
        "is_required_for_eto": False,
    },
    # =========================================================================
    # NWS Stations (hoje-1d a hoje | Real-time USA)
    # =========================================================================
    {
        "source_api": "nws_stations",
        "variable_name": "temperature",
        "standard_name": "temp_c",
        "unit": "°C",
        "description": "Temperatura observada",
        "is_required_for_eto": True,
    },
    {
        "source_api": "nws_stations",
        "variable_name": "dewpoint",
        "standard_name": "dewpoint_c",
        "unit": "°C",
        "description": "Ponto de orvalho observado",
        "is_required_for_eto": True,
    },
    {
        "source_api": "nws_stations",
        "variable_name": "windSpeed",
        "standard_name": "wind_speed_ms",
        "unit": "m/s",
        "description": "Velocidade do vento observada",
        "is_required_for_eto": True,
    },
    {
        "source_api": "nws_stations",
        "variable_name": "relativeHumidity",
        "standard_name": "humidity_percent",
        "unit": "%",
        "description": "Umidade relativa observada",
        "is_required_for_eto": True,
    },
    {
        "source_api": "nws_stations",
        "variable_name": "barometricPressure",
        "standard_name": "pressure_pa",
        "unit": "Pa",
        "description": "Pressão barométrica",
        "is_required_for_eto": False,
    },
]


def get_seed_data() -> List[Dict[str, Any]]:
    """
    Retorna dados do seed para inserção no banco.

    Returns:
        Lista de dicionários com dados das variáveis de todas as APIs
    """
    return API_VARIABLES_DATA


def seed_api_variables(session):
    """
    Insere dados iniciais na tabela api_variables.

    Args:
        session: Sessão SQLAlchemy ativa

    Example:
        from backend.database.connection import get_db
        from backend.database.models.api_variables import APIVariables

        with get_db() as session:
            seed_api_variables(session)
    """
    from backend.database.models.api_variables import APIVariables

    print("🌱 Iniciando seed de api_variables...")

    # Verifica se já existem dados
    existing_count = session.query(APIVariables).count()
    if existing_count > 0:
        print(f"⚠️  Tabela já contém {existing_count} registros.")
        response = input("Deseja limpar e reinserir? (s/N): ")
        if response.lower() == "s":
            session.query(APIVariables).delete()
            session.commit()
            print("🗑️  Registros anteriores removidos.")
        else:
            print("❌ Seed cancelado.")
            return

    # Insere dados
    inserted = 0
    for var_data in API_VARIABLES_DATA:
        var = APIVariables(**var_data)
        session.add(var)
        inserted += 1

    session.commit()
    print(f"✅ {inserted} variáveis inseridas com sucesso!")

    # Estatísticas
    print("\n📊 Estatísticas por API:")
    from sqlalchemy import func, Integer

    stats = (
        session.query(
            APIVariables.source_api,
            func.count(APIVariables.id).label("count"),
            func.sum(
                func.cast(APIVariables.is_required_for_eto, Integer)
            ).label("required_eto"),
        )
        .group_by(APIVariables.source_api)
        .all()
    )

    for stat in stats:
        print(
            f"  - {stat.source_api}: {stat.count} variáveis "
            f"({stat.required_eto} essenciais para ETo)"
        )


if __name__ == "__main__":
    """
    Executa seed diretamente via CLI.

    Uso:
        python database/seeds/api_variables_seed.py
    """
    import sys
    from pathlib import Path

    # Adiciona backend ao path
    backend_path = Path(__file__).parent.parent.parent / "backend"
    sys.path.insert(0, str(backend_path))

    from backend.database.connection import get_db_context
    from sqlalchemy import Integer

    print("🚀 EVA Online - Seed API Variables")
    print("=" * 50)

    with get_db_context() as session:
        seed_api_variables(session)

    print("\n✅ Seed concluído com sucesso!")
