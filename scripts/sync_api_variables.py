"""
Script UNIFICADO para sincronizar tabela api_variables com raw_data padronizado.

Este script:
1. Remove mapeamentos antigos/desatualizados
2. Insere/atualiza mapeamentos corretos para todas as 6 APIs
3. Usa nomes de colunas CORRETOS (source_api, standard_name)
4. Reflete a padronização implementada nos clients

APIs suportadas:
- NASA POWER
- Open-Meteo Archive
- Open-Meteo Forecast
- NWS Forecast
- NWS Stations
- MET Norway

Usage:
    uv run python scripts/sync_api_variables.py
"""

import sys
from pathlib import Path

# Adicionar raiz do projeto ao path (ANTES de imports do backend)
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from backend.database.connection import get_db_context  # noqa: E402
from sqlalchemy import text  # noqa: E402


def sync_api_variables():
    """Sincroniza tabela api_variables com raw_data padronizado."""

    print("\n" + "=" * 80)
    print("🔄 SINCRONIZANDO API_VARIABLES COM RAW_DATA PADRONIZADO")
    print("=" * 80)

    # Mapeamentos CORRETOS baseados no raw_data atual
    variables = [
        # ==================================================
        # NASA POWER
        # ==================================================
        {
            "source_api": "nasa_power",
            "variable_name": "date",
            "standard_name": "date",
            "unit": "",
            "description": "Data do registro",
        },
        {
            "source_api": "nasa_power",
            "variable_name": "source",
            "standard_name": "source",
            "unit": "",
            "description": "Nome da API fonte",
        },
        {
            "source_api": "nasa_power",
            "variable_name": "temp_max",
            "standard_name": "temp_max",
            "unit": "°C",
            "description": "Temperatura máxima diária",
        },
        {
            "source_api": "nasa_power",
            "variable_name": "temp_min",
            "standard_name": "temp_min",
            "unit": "°C",
            "description": "Temperatura mínima diária",
        },
        {
            "source_api": "nasa_power",
            "variable_name": "temp_mean",
            "standard_name": "temp_mean",
            "unit": "°C",
            "description": "Temperatura média diária",
        },
        {
            "source_api": "nasa_power",
            "variable_name": "relative_humidity_mean",
            "standard_name": "relative_humidity_mean",
            "unit": "%",
            "description": "Umidade relativa média",
        },
        {
            "source_api": "nasa_power",
            "variable_name": "wind_speed_2m_mean",
            "standard_name": "wind_speed_2m_mean",
            "unit": "m/s",
            "description": "Velocidade do vento a 2m (nativo)",
        },
        {
            "source_api": "nasa_power",
            "variable_name": "solar_radiation",
            "standard_name": "solar_radiation",
            "unit": "MJ/m²/dia",
            "description": "Radiação solar",
        },
        {
            "source_api": "nasa_power",
            "variable_name": "precipitation_sum_mm",
            "standard_name": "precipitation_sum_mm",
            "unit": "mm",
            "description": "Precipitação total diária",
        },
        # ==================================================
        # OPEN-METEO ARCHIVE
        # ==================================================
        {
            "source_api": "openmeteo_archive",
            "variable_name": "date",
            "standard_name": "date",
            "unit": "",
            "description": "Data do registro",
        },
        {
            "source_api": "openmeteo_archive",
            "variable_name": "source",
            "standard_name": "source",
            "unit": "",
            "description": "Nome da API fonte",
        },
        {
            "source_api": "openmeteo_archive",
            "variable_name": "temp_max",
            "standard_name": "temp_max",
            "unit": "°C",
            "description": "Temperatura máxima diária",
        },
        {
            "source_api": "openmeteo_archive",
            "variable_name": "temp_min",
            "standard_name": "temp_min",
            "unit": "°C",
            "description": "Temperatura mínima diária",
        },
        {
            "source_api": "openmeteo_archive",
            "variable_name": "temp_mean",
            "standard_name": "temp_mean",
            "unit": "°C",
            "description": "Temperatura média diária",
        },
        {
            "source_api": "openmeteo_archive",
            "variable_name": "relative_humidity_max",
            "standard_name": "relative_humidity_max",
            "unit": "%",
            "description": "Umidade relativa máxima",
        },
        {
            "source_api": "openmeteo_archive",
            "variable_name": "relative_humidity_min",
            "standard_name": "relative_humidity_min",
            "unit": "%",
            "description": "Umidade relativa mínima",
        },
        {
            "source_api": "openmeteo_archive",
            "variable_name": "relative_humidity_mean",
            "standard_name": "relative_humidity_mean",
            "unit": "%",
            "description": "Umidade relativa média",
        },
        {
            "source_api": "openmeteo_archive",
            "variable_name": "wind_speed_2m_mean",
            "standard_name": "wind_speed_2m_mean",
            "unit": "m/s",
            "description": "Velocidade do vento a 2m (convertido)",
        },
        {
            "source_api": "openmeteo_archive",
            "variable_name": "solar_radiation",
            "standard_name": "solar_radiation",
            "unit": "MJ/m²",
            "description": "Radiação solar",
        },
        {
            "source_api": "openmeteo_archive",
            "variable_name": "precipitation_sum_mm",
            "standard_name": "precipitation_sum_mm",
            "unit": "mm",
            "description": "Precipitação total",
        },
        {
            "source_api": "openmeteo_archive",
            "variable_name": "et0_fao_evapotranspiration",
            "standard_name": "et0_fao_evapotranspiration",
            "unit": "mm/dia",
            "description": "ETo FAO-56",
        },
        # ==================================================
        # OPEN-METEO FORECAST
        # ==================================================
        {
            "source_api": "openmeteo_forecast",
            "variable_name": "date",
            "standard_name": "date",
            "unit": "",
            "description": "Data do registro",
        },
        {
            "source_api": "openmeteo_forecast",
            "variable_name": "source",
            "standard_name": "source",
            "unit": "",
            "description": "Nome da API fonte",
        },
        {
            "source_api": "openmeteo_forecast",
            "variable_name": "temp_max",
            "standard_name": "temp_max",
            "unit": "°C",
            "description": "Temperatura máxima prevista",
        },
        {
            "source_api": "openmeteo_forecast",
            "variable_name": "temp_min",
            "standard_name": "temp_min",
            "unit": "°C",
            "description": "Temperatura mínima prevista",
        },
        {
            "source_api": "openmeteo_forecast",
            "variable_name": "temp_mean",
            "standard_name": "temp_mean",
            "unit": "°C",
            "description": "Temperatura média prevista",
        },
        {
            "source_api": "openmeteo_forecast",
            "variable_name": "relative_humidity_max",
            "standard_name": "relative_humidity_max",
            "unit": "%",
            "description": "Umidade relativa máxima prevista",
        },
        {
            "source_api": "openmeteo_forecast",
            "variable_name": "relative_humidity_min",
            "standard_name": "relative_humidity_min",
            "unit": "%",
            "description": "Umidade relativa mínima prevista",
        },
        {
            "source_api": "openmeteo_forecast",
            "variable_name": "relative_humidity_mean",
            "standard_name": "relative_humidity_mean",
            "unit": "%",
            "description": "Umidade relativa média prevista",
        },
        {
            "source_api": "openmeteo_forecast",
            "variable_name": "wind_speed_2m_mean",
            "standard_name": "wind_speed_2m_mean",
            "unit": "m/s",
            "description": "Velocidade do vento a 2m prevista",
        },
        {
            "source_api": "openmeteo_forecast",
            "variable_name": "solar_radiation",
            "standard_name": "solar_radiation",
            "unit": "W/m²",
            "description": "Radiação solar prevista",
        },
        {
            "source_api": "openmeteo_forecast",
            "variable_name": "precipitation_sum_mm",
            "standard_name": "precipitation_sum_mm",
            "unit": "mm",
            "description": "Precipitação prevista",
        },
        {
            "source_api": "openmeteo_forecast",
            "variable_name": "et0_fao_evapotranspiration",
            "standard_name": "et0_fao_evapotranspiration",
            "unit": "mm/dia",
            "description": "ETo FAO-56 previsto",
        },
        # ==================================================
        # MET NORWAY
        # ==================================================
        {
            "source_api": "met_norway",
            "variable_name": "date",
            "standard_name": "date",
            "unit": "",
            "description": "Data do registro",
        },
        {
            "source_api": "met_norway",
            "variable_name": "source",
            "standard_name": "source",
            "unit": "",
            "description": "Nome da API fonte",
        },
        {
            "source_api": "met_norway",
            "variable_name": "temp_max",
            "standard_name": "temp_max",
            "unit": "°C",
            "description": "Temperatura máxima prevista",
        },
        {
            "source_api": "met_norway",
            "variable_name": "temp_min",
            "standard_name": "temp_min",
            "unit": "°C",
            "description": "Temperatura mínima prevista",
        },
        {
            "source_api": "met_norway",
            "variable_name": "temp_mean",
            "standard_name": "temp_mean",
            "unit": "°C",
            "description": "Temperatura média prevista",
        },
        {
            "source_api": "met_norway",
            "variable_name": "relative_humidity_mean",
            "standard_name": "relative_humidity_mean",
            "unit": "%",
            "description": "Umidade relativa média prevista",
        },
        {
            "source_api": "met_norway",
            "variable_name": "wind_speed_2m_mean",
            "standard_name": "wind_speed_2m_mean",
            "unit": "m/s",
            "description": "Velocidade do vento a 2m (convertido FAO-56)",
        },
        {
            "source_api": "met_norway",
            "variable_name": "precipitation_sum_mm",
            "standard_name": "precipitation_sum_mm",
            "unit": "mm",
            "description": "Precipitação prevista",
        },
        # ==================================================
        # NWS FORECAST
        # ==================================================
        {
            "source_api": "nws_forecast",
            "variable_name": "date",
            "standard_name": "date",
            "unit": "",
            "description": "Data do registro",
        },
        {
            "source_api": "nws_forecast",
            "variable_name": "source",
            "standard_name": "source",
            "unit": "",
            "description": "Nome da API fonte",
        },
        {
            "source_api": "nws_forecast",
            "variable_name": "temp_max",
            "standard_name": "temp_max",
            "unit": "°C",
            "description": "Temperatura máxima prevista",
        },
        {
            "source_api": "nws_forecast",
            "variable_name": "temp_min",
            "standard_name": "temp_min",
            "unit": "°C",
            "description": "Temperatura mínima prevista",
        },
        {
            "source_api": "nws_forecast",
            "variable_name": "temp_mean",
            "standard_name": "temp_mean",
            "unit": "°C",
            "description": "Temperatura média prevista",
        },
        {
            "source_api": "nws_forecast",
            "variable_name": "relative_humidity_mean",
            "standard_name": "relative_humidity_mean",
            "unit": "%",
            "description": "Umidade relativa média prevista",
        },
        {
            "source_api": "nws_forecast",
            "variable_name": "wind_speed_2m_mean",
            "standard_name": "wind_speed_2m_mean",
            "unit": "m/s",
            "description": "Velocidade do vento prevista",
        },
        {
            "source_api": "nws_forecast",
            "variable_name": "precipitation_sum_mm",
            "standard_name": "precipitation_sum_mm",
            "unit": "mm",
            "description": "Precipitação prevista",
        },
        {
            "source_api": "nws_forecast",
            "variable_name": "probability_precip_mean_percent",
            "standard_name": "probability_precip_mean_percent",
            "unit": "%",
            "description": "Probabilidade de precipitação",
        },
        {
            "source_api": "nws_forecast",
            "variable_name": "short_forecast",
            "standard_name": "short_forecast",
            "unit": "",
            "description": "Descrição curta da previsão",
        },
        {
            "source_api": "nws_forecast",
            "variable_name": "hourly_data",
            "standard_name": "hourly_data",
            "unit": "",
            "description": "Dados horários detalhados",
        },
        # ==================================================
        # NWS STATIONS
        # ==================================================
        {
            "source_api": "nws_stations",
            "variable_name": "date",
            "standard_name": "date",
            "unit": "",
            "description": "Data da observação (YYYY-MM-DD)",
        },
        {
            "source_api": "nws_stations",
            "variable_name": "source",
            "standard_name": "source",
            "unit": "",
            "description": "Nome da API fonte",
        },
        {
            "source_api": "nws_stations",
            "variable_name": "timestamp",
            "standard_name": "timestamp",
            "unit": "",
            "description": "Timestamp da observação",
        },
        {
            "source_api": "nws_stations",
            "variable_name": "station_id",
            "standard_name": "station_id",
            "unit": "",
            "description": "ID da estação meteorológica",
        },
        {
            "source_api": "nws_stations",
            "variable_name": "temp_current",
            "standard_name": "temp_current",
            "unit": "°C",
            "description": "Temperatura atual",
        },
        {
            "source_api": "nws_stations",
            "variable_name": "temp_max",
            "standard_name": "temp_max",
            "unit": "°C",
            "description": "Temperatura máxima (24h)",
        },
        {
            "source_api": "nws_stations",
            "variable_name": "temp_min",
            "standard_name": "temp_min",
            "unit": "°C",
            "description": "Temperatura mínima (24h)",
        },
        {
            "source_api": "nws_stations",
            "variable_name": "dewpoint",
            "standard_name": "dewpoint",
            "unit": "°C",
            "description": "Ponto de orvalho",
        },
        {
            "source_api": "nws_stations",
            "variable_name": "relative_humidity_mean",
            "standard_name": "relative_humidity_mean",
            "unit": "%",
            "description": "Umidade relativa",
        },
        {
            "source_api": "nws_stations",
            "variable_name": "wind_speed_2m_mean",
            "standard_name": "wind_speed_2m_mean",
            "unit": "m/s",
            "description": "Velocidade do vento a 2m (convertido FAO-56)",
        },
        {
            "source_api": "nws_stations",
            "variable_name": "precipitation_sum_mm",
            "standard_name": "precipitation_sum_mm",
            "unit": "mm",
            "description": "Precipitação (1h)",
        },
    ]

    with get_db_context() as db:
        # Limpar registros antigos
        print("\n🧹 Limpando registros antigos...")
        result = db.execute(text("DELETE FROM api_variables"))
        deleted = result.rowcount
        print(f"   Removidos {deleted} registros antigos")

        # Inserir novos mapeamentos
        print("\n📝 Inserindo novos mapeamentos...")
        inserted = 0

        for var in variables:
            try:
                db.execute(
                    text(
                        """
                        INSERT INTO api_variables 
                        (source_api, variable_name, standard_name, unit, 
                         description, is_required_for_eto)
                        VALUES 
                        (:source_api, :variable_name, :standard_name, :unit, 
                         :description, false)
                    """
                    ),
                    var,
                )
                inserted += 1
                print(
                    f"  ✅ {var['source_api']:20s} | "
                    f"{var['variable_name']:30s} → {var['standard_name']}"
                )

            except Exception as e:
                print(f"  ❌ {var['source_api']}.{var['variable_name']}: {e}")

        db.commit()

    print("\n" + "=" * 80)
    print("✅ SINCRONIZAÇÃO CONCLUÍDA!")
    print(f"   🗑️  Removidos: {deleted} registros antigos")
    print(f"   ➕ Inseridos: {inserted} novos mapeamentos")
    print("=" * 80)

    # Mostrar resumo por API
    print("\n📋 RESUMO POR API:")
    print("-" * 80)

    with get_db_context() as db:
        result = db.execute(
            text(
                """
                SELECT source_api, COUNT(*) as total
                FROM api_variables
                GROUP BY source_api
                ORDER BY source_api
            """
            )
        )

        for row in result:
            print(f"  📡 {row.source_api:25s} → {row.total:2d} variáveis")

    print("-" * 80 + "\n")


if __name__ == "__main__":
    try:
        sync_api_variables()
    except Exception as e:
        print(f"\n❌ ERRO: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
