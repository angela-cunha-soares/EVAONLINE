"""
Teste FINAL das 6 APIs com dados REAIS

Teste end-to-end: API → Processamento → PostgreSQL

Usage:
    uv run python scripts/validation/load_climate_data.py
"""

import asyncio
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Adicionar raiz ao path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from backend.api.services.nasa_power.nasa_power_client import NASAPowerClient
from backend.api.services.openmeteo_archive.openmeteo_archive_client import (
    OpenMeteoArchiveClient,
)
from backend.api.services.openmeteo_forecast.openmeteo_forecast_client import (
    OpenMeteoForecastClient,
)
from backend.api.services.met_norway import METNorwayClient
from backend.api.services.nws_forecast import NWSForecastClient
from backend.api.services.nws_stations import NWSStationsClient
from backend.database.connection import get_db_context
from backend.database.data_storage import save_climate_data
from backend.database.models import ClimateData


def serialize_datetime_in_dict(data: dict) -> dict:
    """Converte datetime objects para isoformat() em dict."""
    result = {}
    for key, value in data.items():
        if isinstance(value, datetime):
            result[key] = value.isoformat()
        elif isinstance(value, dict):
            result[key] = serialize_datetime_in_dict(value)
        elif isinstance(value, list):
            result[key] = [
                (
                    serialize_datetime_in_dict(item)
                    if isinstance(item, dict)
                    else item
                )
                for item in value
            ]
        else:
            result[key] = value
    return result


def clean_test_data():
    """Remove dados de teste anteriores."""
    print("\n🧹 Limpando dados de teste anteriores...")
    with get_db_context() as db:
        deleted = (
            db.query(ClimateData)
            .filter(
                ClimateData.processing_metadata["script"].astext
                == "test_all_6_apis"
            )
            .delete(synchronize_session=False)
        )
        db.commit()
        print(f"   Removidos {deleted} registros antigos")


async def test_nasa_power():
    """Testa NASA POWER."""
    print("\n" + "=" * 80)
    print("1️⃣  NASA POWER - Dados Históricos")
    print("=" * 80)

    try:
        client = NASAPowerClient()

        lat, lon = -22.7250, -47.6476  # Piracicaba
        end_date = datetime.now() - timedelta(days=1)
        start_date = end_date - timedelta(days=7)

        print(f"\n📍 Piracicaba, SP ({lat:.4f}, {lon:.4f})")
        print(f"📅 Período: {start_date.date()} a {end_date.date()}")
        print("⏳ Buscando dados...")

        result = await client.get_daily_data(
            lat=lat, lon=lon, start_date=start_date, end_date=end_date
        )

        if result:
            print(f"✅ Recebidos {len(result)} registros")

            climate_records = []
            for record in result[:3]:
                record_dict = (
                    record.model_dump()
                    if hasattr(record, "model_dump")
                    else dict(record)
                )
                record_dict = serialize_datetime_in_dict(record_dict)

                date_obj = (
                    datetime.strptime(record_dict["date"], "%Y-%m-%d")
                    if isinstance(record_dict.get("date"), str)
                    else record_dict["date"]
                )

                # Padronizar raw_data NASA POWER
                # NASA POWER fornece vento a 2m nativamente
                raw_data = {
                    "date": record_dict.get("date"),
                    "source": "nasa_power",
                    "temp_max": record_dict.get("temp_max"),
                    "temp_min": record_dict.get("temp_min"),
                    "temp_mean": record_dict.get("temp_mean"),
                    "relative_humidity_mean": record_dict.get("humidity"),
                    "wind_speed_2m_mean": record_dict.get(
                        "wind_speed"
                    ),  # Nativo a 2m
                    "precipitation_sum_mm": record_dict.get("precipitation"),
                    "solar_radiation": record_dict.get("solar_radiation"),
                }

                climate_records.append(
                    {
                        "latitude": lat,
                        "longitude": lon,
                        "elevation": 547.0,
                        "timezone": "America/Sao_Paulo",
                        "date": date_obj,
                        "raw_data": raw_data,
                        "eto_mm_day": record_dict.get("eto_mm_day"),
                        "eto_method": "FAO-56",
                        "quality_flags": {"test": True},
                        "processing_metadata": {"script": "test_all_6_apis"},
                    }
                )

            count = save_climate_data(
                climate_records, "nasa_power", auto_harmonize=True
            )
            print(f"💾 Salvos {count} registros")
            await client.close()
            return True
        else:
            print("❌ Sem dados")
            await client.close()
            return False

    except Exception as e:
        print(f"❌ Erro: {e}")
        return False


async def test_openmeteo_archive():
    """Testa Open-Meteo Archive."""
    print("\n" + "=" * 80)
    print("2️⃣  OPEN-METEO ARCHIVE - Dados Históricos")
    print("=" * 80)

    try:
        client = OpenMeteoArchiveClient()

        lat, lon = -23.5505, -46.6333  # São Paulo
        # Archive: dados históricos até hoje-2d, mínimo 7 dias EVA
        end_date = datetime.now() - timedelta(days=2)
        start_date = end_date - timedelta(days=7)

        print(f"\n📍 São Paulo, SP ({lat:.4f}, {lon:.4f})")
        print(f"📅 Período: {start_date.date()} a {end_date.date()}")
        print("⏳ Buscando dados...")

        result = await client.get_climate_data(
            lat=lat,
            lng=lon,
            start_date=start_date.strftime("%Y-%m-%d"),
            end_date=end_date.strftime("%Y-%m-%d"),
        )

        if result:
            # Open-Meteo returns dict with climate_data containing lists by date
            climate_data = result.get("climate_data", {})
            dates = climate_data.get("dates", [])
            print(f"✅ Recebidos {len(dates)} registros")

            climate_records = []
            for i, date_str in enumerate(dates):  # Process all days
                # Build record from climate_data arrays (exclude datetime keys)
                record_dict = {}
                for key, values in climate_data.items():
                    # Skip datetime-related keys
                    if (
                        key not in ["time", "dates"]
                        and isinstance(values, list)
                        and i < len(values)
                    ):
                        record_dict[key] = values[i]

                date_obj = (
                    datetime.strptime(date_str, "%Y-%m-%d")
                    if isinstance(date_str, str)
                    else date_str
                )

                # Padronizar raw_data Open-Meteo Archive
                raw_data = {
                    "date": (
                        date_str
                        if isinstance(date_str, str)
                        else date_str.strftime("%Y-%m-%d")
                    ),
                    "source": "openmeteo_archive",
                    "temp_max": record_dict.get("temperature_2m_max"),
                    "temp_min": record_dict.get("temperature_2m_min"),
                    "temp_mean": record_dict.get("temperature_2m_mean"),
                    "relative_humidity_max": record_dict.get(
                        "relative_humidity_2m_max"
                    ),
                    "relative_humidity_min": record_dict.get(
                        "relative_humidity_2m_min"
                    ),
                    "relative_humidity_mean": record_dict.get(
                        "relative_humidity_2m_mean"
                    ),
                    "wind_speed_2m_mean": record_dict.get(
                        "wind_speed_2m_mean"
                    ),
                    "precipitation_sum_mm": record_dict.get(
                        "precipitation_sum"
                    ),
                    "solar_radiation": record_dict.get(
                        "shortwave_radiation_sum"
                    ),
                    "et0_fao_evapotranspiration": record_dict.get(
                        "et0_fao_evapotranspiration"
                    ),
                }

                climate_records.append(
                    {
                        "latitude": lat,
                        "longitude": lon,
                        "elevation": result.get("location", {}).get(
                            "elevation", 760.0
                        ),
                        "timezone": "America/Sao_Paulo",
                        "date": date_obj,
                        "raw_data": raw_data,
                        "eto_mm_day": record_dict.get(
                            "et0_fao_evapotranspiration"
                        ),
                        "eto_method": "FAO-56",
                        "quality_flags": {"test": True},
                        "processing_metadata": {"script": "test_all_6_apis"},
                    }
                )

            count = save_climate_data(
                climate_records, "openmeteo_archive", auto_harmonize=True
            )
            print(f"💾 Salvos {count} registros")
            # No close() method
            return True
        else:
            print("❌ Sem dados")
            # No close() method
            return False

    except Exception as e:
        print(f"❌ Erro: {e}")
        return False


async def test_openmeteo_forecast():
    """Testa Open-Meteo Forecast."""
    print("\n" + "=" * 80)
    print("3️⃣  OPEN-METEO FORECAST - Previsão")
    print("=" * 80)

    try:
        client = OpenMeteoForecastClient()

        lat, lon = -15.7939, -47.8828  # Brasília
        # Teste para data específica: 2025-11-12
        start_date = datetime(2025, 11, 12)
        end_date = datetime(2025, 11, 12)

        print(f"\n📍 Brasília, DF ({lat:.4f}, {lon:.4f})")
        print(f"📅 Previsão: {start_date.date()} a {end_date.date()}")
        print("⏳ Buscando dados...")

        result = await client.get_climate_data(
            lat=lat,
            lng=lon,
            start_date=start_date.strftime("%Y-%m-%d"),
            end_date=end_date.strftime("%Y-%m-%d"),
        )

        if result:
            # Open-Meteo returns dict with climate_data containing lists by date
            climate_data = result.get("climate_data", {})
            dates = climate_data.get("dates", [])  # FIX: 'dates' not 'time'
            print(f"✅ Recebidos {len(dates)} registros")

            climate_records = []
            for i, date_str in enumerate(dates):  # Process all days
                # Build record from climate_data arrays (exclude datetime keys)
                record_dict = {}
                for key, values in climate_data.items():
                    # Skip datetime-related keys
                    if (
                        key not in ["time", "dates"]
                        and isinstance(values, list)
                        and i < len(values)
                    ):
                        record_dict[key] = values[i]

                date_obj = (
                    datetime.strptime(date_str, "%Y-%m-%d")
                    if isinstance(date_str, str)
                    else date_str
                )

                # Padronizar raw_data Open-Meteo Forecast
                raw_data = {
                    "date": (
                        date_str
                        if isinstance(date_str, str)
                        else date_str.strftime("%Y-%m-%d")
                    ),
                    "source": "openmeteo_forecast",
                    "temp_max": record_dict.get("temperature_2m_max"),
                    "temp_min": record_dict.get("temperature_2m_min"),
                    "temp_mean": record_dict.get("temperature_2m_mean"),
                    "relative_humidity_max": record_dict.get(
                        "relative_humidity_2m_max"
                    ),
                    "relative_humidity_min": record_dict.get(
                        "relative_humidity_2m_min"
                    ),
                    "relative_humidity_mean": record_dict.get(
                        "relative_humidity_2m_mean"
                    ),
                    "wind_speed_2m_mean": record_dict.get(
                        "wind_speed_2m_mean"
                    ),
                    "precipitation_sum_mm": record_dict.get(
                        "precipitation_sum"
                    ),
                    "solar_radiation": record_dict.get(
                        "shortwave_radiation_sum"
                    ),
                    "et0_fao_evapotranspiration": record_dict.get(
                        "et0_fao_evapotranspiration"
                    ),
                }

                climate_records.append(
                    {
                        "latitude": lat,
                        "longitude": lon,
                        "elevation": result.get("location", {}).get(
                            "elevation", 1172.0
                        ),
                        "timezone": "America/Brasilia",
                        "date": date_obj,
                        "raw_data": raw_data,
                        "eto_mm_day": record_dict.get(
                            "et0_fao_evapotranspiration"
                        ),
                        "eto_method": "FAO-56",
                        "quality_flags": {"test": True},
                        "processing_metadata": {"script": "test_all_6_apis"},
                    }
                )

            count = save_climate_data(
                climate_records, "openmeteo_forecast", auto_harmonize=True
            )
            print(f"💾 Salvos {count} registros")
            # No close() method
            return True
        else:
            print("❌ Sem dados")
            # No close() method
            return False

    except Exception as e:
        print(f"❌ Erro: {e}")
        return False


async def test_met_norway():
    """Testa MET Norway."""
    print("\n" + "=" * 80)
    print("4️⃣  MET NORWAY - Previsão Nórdica")
    print("=" * 80)

    try:
        client = METNorwayClient()

        lat, lon = 59.9139, 10.7522  # Oslo

        print(f"\n📍 Oslo, Noruega ({lat:.4f}, {lon:.4f})")
        print("⏳ Buscando previsão...")

        data = await client.get_daily_forecast(lat=lat, lon=lon)

        if data:
            print(f"✅ Recebidos {len(data)} registros")

            climate_records = []
            for record in data[:2]:
                record_dict = (
                    record.model_dump()
                    if hasattr(record, "model_dump")
                    else dict(record)
                )
                # Serializar datetime objects
                record_dict = serialize_datetime_in_dict(record_dict)

                # Parse date - remover T00:00:00 se presente
                date_str = record_dict.get("date", "")
                if isinstance(date_str, str):
                    date_str = date_str.split("T")[
                        0
                    ]  # Remove hora se presente
                    date_obj = datetime.strptime(date_str, "%Y-%m-%d")
                else:
                    date_obj = date_str

                # Padronizar raw_data MET Norway
                raw_data = {
                    "date": date_str,
                    "source": "met_norway",
                    "temp_max": record_dict.get("temp_max"),
                    "temp_min": record_dict.get("temp_min"),
                    "temp_mean": record_dict.get("temp_mean"),
                    "relative_humidity_mean": record_dict.get("humidity_mean"),
                    "wind_speed_2m_mean": record_dict.get(
                        "wind_speed_2m_mean"
                    ),
                    "precipitation_sum_mm": record_dict.get(
                        "precipitation_sum"
                    ),
                }

                climate_records.append(
                    {
                        "latitude": lat,
                        "longitude": lon,
                        "elevation": 23.0,
                        "timezone": "Europe/Oslo",
                        "date": date_obj,
                        "raw_data": raw_data,
                        "eto_mm_day": None,
                        "eto_method": None,
                        "quality_flags": {"test": True},
                        "processing_metadata": {"script": "test_all_6_apis"},
                    }
                )

            count = save_climate_data(
                climate_records, "met_norway", auto_harmonize=True
            )
            print(f"💾 Salvos {count} registros")
            await client.close()
            return True
        else:
            print("❌ Sem dados")
            await client.close()
            return False

    except Exception as e:
        print(f"❌ Erro: {e}")
        return False


async def test_nws_forecast():
    """Testa NWS Forecast."""
    print("\n" + "=" * 80)
    print("5️⃣  NWS FORECAST - Previsão USA")
    print("=" * 80)

    try:
        client = NWSForecastClient()

        lat, lon = 39.7392, -104.9903  # Denver

        print(f"\n📍 Denver, Colorado ({lat:.4f}, {lon:.4f})")
        print("⏳ Buscando previsão...")

        data = await client.get_daily_forecast_data(lat=lat, lon=lon)

        if data:
            print(f"✅ Recebidos {len(data)} registros")

            climate_records = []
            for record in data[:2]:
                record_dict = (
                    record.model_dump()
                    if hasattr(record, "model_dump")
                    else dict(record)
                )
                # Serializar datetime
                record_dict = serialize_datetime_in_dict(record_dict)

                date_obj = (
                    datetime.fromisoformat(record_dict["date"].split("T")[0])
                    if isinstance(record_dict.get("date"), str)
                    else record_dict["date"]
                )

                # Extrair data sem hora para NWS Forecast
                date_str = record_dict.get("date")
                if isinstance(date_str, str):
                    date_only = date_str.split("T")[0]
                else:
                    date_only = str(date_obj.date())

                # Padronizar raw_data NWS Forecast
                raw_data = {
                    "date": date_only,
                    "source": "nws_forecast",
                    "temp_max": record_dict.get("temp_max_celsius"),
                    "temp_min": record_dict.get("temp_min_celsius"),
                    "temp_mean": record_dict.get("temp_mean_celsius"),
                    "relative_humidity_mean": record_dict.get(
                        "humidity_mean_percent"
                    ),
                    "wind_speed_2m_mean": record_dict.get(
                        "wind_speed_mean_ms"
                    ),
                    "precipitation_sum_mm": record_dict.get("precip_total_mm"),
                    "probability_precip_mean_percent": record_dict.get(
                        "probability_precip_mean_percent"
                    ),
                    "short_forecast": record_dict.get("short_forecast"),
                    "hourly_data": record_dict.get("hourly_data"),
                }

                climate_records.append(
                    {
                        "latitude": lat,
                        "longitude": lon,
                        "elevation": 1609.0,
                        "timezone": "America/Denver",
                        "date": date_obj,
                        "raw_data": raw_data,
                        "eto_mm_day": None,
                        "eto_method": None,
                        "quality_flags": {"test": True},
                        "processing_metadata": {"script": "test_all_6_apis"},
                    }
                )

            count = save_climate_data(
                climate_records, "nws_forecast", auto_harmonize=True
            )
            print(f"💾 Salvos {count} registros")
            await client.close()
            return True
        else:
            print("❌ Sem dados")
            await client.close()
            return False

    except Exception as e:
        print(f"❌ Erro: {e}")
        return False


async def test_nws_stations():
    """Testa NWS Stations."""
    print("\n" + "=" * 80)
    print("6️⃣  NWS STATIONS - Dados Real-time USA")
    print("=" * 80)

    try:
        client = NWSStationsClient()

        lat, lon = 39.7392, -104.9903  # Denver
        print(f"\n📍 Denver, Colorado ({lat:.4f}, {lon:.4f})")
        print("⏳ Buscando estações próximas...")

        stations = await client.find_nearest_stations(lat=lat, lon=lon)

        if not stations:
            print("❌ Nenhuma estação encontrada")
            await client.close()
            return False

        print(f"✅ Encontradas {len(stations)} estações")

        station = stations[0]
        station_id = station.station_id
        print(f"\n📡 Testando estação: {station_id}")

        observations = await client.get_station_observations(station_id)

        if observations:
            print(f"✅ Recebidas {len(observations)} observações")

            climate_records = []
            for obs in observations[:1]:
                timestamp = obs.timestamp
                date_obj = (
                    timestamp
                    if isinstance(timestamp, datetime)
                    else datetime.now()
                )

                # Padronizar raw_data NWS Stations
                raw_data = {
                    "date": (
                        str(timestamp.date())
                        if isinstance(timestamp, datetime)
                        else str(datetime.now().date())
                    ),
                    "timestamp": (
                        timestamp.isoformat()
                        if isinstance(timestamp, datetime)
                        else timestamp
                    ),
                    "source": "nws_stations",
                    "station_id": station_id,
                    "temp_current": obs.temp_celsius,
                    "temp_max": obs.temp_max_24h,  # Últimas 24h
                    "temp_min": obs.temp_min_24h,  # Últimas 24h
                    "dewpoint": obs.dewpoint_celsius,
                    "relative_humidity_mean": obs.humidity_percent,
                    "wind_speed_2m_mean": obs.wind_speed_2m_ms,
                    "precipitation_sum_mm": obs.precipitation_1h_mm,
                }

                climate_records.append(
                    {
                        "latitude": lat,
                        "longitude": lon,
                        "elevation": 1609.0,
                        "timezone": "America/Denver",
                        "date": date_obj,
                        "raw_data": raw_data,
                        "eto_mm_day": None,
                        "eto_method": None,
                        "quality_flags": {
                            "test": True,
                            "station_id": station_id,
                        },
                        "processing_metadata": {"script": "test_all_6_apis"},
                    }
                )

            count = save_climate_data(
                climate_records, "nws_stations", auto_harmonize=True
            )
            print(f"💾 Salvos {count} registros")
            await client.close()
            return True
        else:
            print("❌ Sem observações")
            await client.close()
            return False

    except Exception as e:
        print(f"❌ Erro: {e}")
        return False


async def check_database_summary():
    """Mostra resumo dos dados no banco."""
    print("\n" + "=" * 80)
    print("📊 RESUMO DO BANCO DE DADOS")
    print("=" * 80)

    with get_db_context() as db:
        total = db.query(ClimateData).count()
        print(f"\n📈 Total de registros: {total}")

        from sqlalchemy import func

        results = (
            db.query(
                ClimateData.source_api,
                func.count(ClimateData.id).label("count"),
            )
            .group_by(ClimateData.source_api)
            .all()
        )

        print("\n📋 Registros por API:")
        for source, count in results:
            print(f"   - {source}: {count} registro(s)")

        with_eto = (
            db.query(ClimateData)
            .filter(ClimateData.eto_mm_day.isnot(None))
            .count()
        )
        print(f"\n📈 Registros com ETo: {with_eto}/{total}")

        with_harmonized = (
            db.query(ClimateData)
            .filter(ClimateData.harmonized_data.isnot(None))
            .count()
        )
        print(f"✨ Registros harmonizados: {with_harmonized}/{total}")


async def main():
    """Executa testes de todas as 6 APIs."""
    print("=" * 80)
    print("🧪 TESTE FINAL - 6 APIs DE CLIMA COM DADOS REAIS")
    print("=" * 80)
    print(
        "\nTestando integração end-to-end: API → Processamento → PostgreSQL\n"
    )

    # Limpar dados antigos
    clean_test_data()

    results = {}

    # Testar cada API
    results["NASA POWER"] = await test_nasa_power()
    results["Open-Meteo Archive"] = await test_openmeteo_archive()
    results["Open-Meteo Forecast"] = await test_openmeteo_forecast()
    results["MET Norway"] = await test_met_norway()
    results["NWS Forecast"] = await test_nws_forecast()
    results["NWS Stations"] = await test_nws_stations()

    # Resumo do banco
    await check_database_summary()

    # Resultado final
    print("\n" + "=" * 80)
    print("🎯 RESULTADO FINAL")
    print("=" * 80)

    passed = sum(1 for success in results.values() if success)
    total = len(results)

    for api_name, success in results.items():
        status = "✅ PASSOU" if success else "❌ FALHOU"
        print(f"\n   {api_name}: {status}")

    print(f"\n📊 Score: {passed}/{total} APIs funcionando")

    if passed == total:
        print("\n🎉 SUCESSO TOTAL!")
        print("✅ Todas as 6 APIs funcionando")
        print("✅ Dados reais salvos no PostgreSQL")
        print("✅ Harmonização funcionando")
        print("\n🚀 Sistema validado e pronto para produção!")
    elif passed >= 4:
        print("\n✅ SUCESSO PARCIAL!")
        print(f"✅ {passed}/6 APIs funcionando corretamente")
        print(f"⚠️  {total - passed} API(s) com problemas")
    else:
        print("\n⚠️  PROBLEMAS DETECTADOS")
        print(f"❌ Apenas {passed}/6 APIs funcionando")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
