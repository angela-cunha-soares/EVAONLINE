"""
Tasks Celery para pre-carregamento de dados climáticos populares.

Estratégia de pre-fetch:
- Cidades mundiais populares: 50 cidades, execução diária 03:00 BRT
- Dados dos últimos 30 dias para cada localização

Benefits:
- Cache aquecido para requisições futuras
- Reduz latência para usuários
- Otimiza uso de APIs externas
- Distribui carga ao longo do tempo
"""

import asyncio
from datetime import datetime, timedelta

from celery import shared_task
from loguru import logger

# Cidades mundiais mais populares (top 50)
POPULAR_WORLD_CITIES = [
    {"name": "Paris", "lat": 48.8566, "lon": 2.3522, "country": "França"},
    {
        "name": "London",
        "lat": 51.5074,
        "lon": -0.1278,
        "country": "Reino Unido",
    },
    {"name": "New York", "lat": 40.7128, "lon": -74.0060, "country": "EUA"},
    {"name": "Tokyo", "lat": 35.6762, "lon": 139.6503, "country": "Japão"},
    {
        "name": "São Paulo",
        "lat": -23.5505,
        "lon": -46.6333,
        "country": "Brasil",
    },
    {
        "name": "Los Angeles",
        "lat": 34.0522,
        "lon": -118.2437,
        "country": "EUA",
    },
    {"name": "Shanghai", "lat": 31.2304, "lon": 121.4737, "country": "China"},
    {"name": "Mumbai", "lat": 19.0760, "lon": 72.8777, "country": "Índia"},
    {"name": "Beijing", "lat": 39.9042, "lon": 116.4074, "country": "China"},
    {
        "name": "Mexico City",
        "lat": 19.4326,
        "lon": -99.1332,
        "country": "México",
    },
    {"name": "Moscow", "lat": 55.7558, "lon": 37.6173, "country": "Rússia"},
    {"name": "Dubai", "lat": 25.2048, "lon": 55.2708, "country": "EAU"},
    {
        "name": "Singapore",
        "lat": 1.3521,
        "lon": 103.8198,
        "country": "Cingapura",
    },
    {
        "name": "Sydney",
        "lat": -33.8688,
        "lon": 151.2093,
        "country": "Austrália",
    },
    {"name": "Berlin", "lat": 52.5200, "lon": 13.4050, "country": "Alemanha"},
    {"name": "Madrid", "lat": 40.4168, "lon": -3.7038, "country": "Espanha"},
    {"name": "Rome", "lat": 41.9028, "lon": 12.4964, "country": "Itália"},
    {"name": "Toronto", "lat": 43.6532, "lon": -79.3832, "country": "Canadá"},
    {"name": "Istanbul", "lat": 41.0082, "lon": 28.9784, "country": "Turquia"},
    {
        "name": "Bangkok",
        "lat": 13.7563,
        "lon": 100.5018,
        "country": "Tailândia",
    },
    {
        "name": "Buenos Aires",
        "lat": -34.6037,
        "lon": -58.3816,
        "country": "Argentina",
    },
    {
        "name": "Rio de Janeiro",
        "lat": -22.9068,
        "lon": -43.1729,
        "country": "Brasil",
    },
    {"name": "Seoul", "lat": 37.5665, "lon": 126.9780, "country": "Coreia"},
    {"name": "Amsterdam", "lat": 52.3676, "lon": 4.9041, "country": "Holanda"},
    {"name": "Vienna", "lat": 48.2082, "lon": 16.3738, "country": "Áustria"},
    {"name": "Barcelona", "lat": 41.3851, "lon": 2.1734, "country": "Espanha"},
    {"name": "Lisbon", "lat": 38.7223, "lon": -9.1393, "country": "Portugal"},
    {"name": "Cairo", "lat": 30.0444, "lon": 31.2357, "country": "Egito"},
    {
        "name": "Cape Town",
        "lat": -33.9249,
        "lon": 18.4241,
        "country": "África do Sul",
    },
    {
        "name": "Melbourne",
        "lat": -37.8136,
        "lon": 144.9631,
        "country": "Austrália",
    },
    {"name": "Hong Kong", "lat": 22.3193, "lon": 114.1694, "country": "China"},
    {
        "name": "San Francisco",
        "lat": 37.7749,
        "lon": -122.4194,
        "country": "EUA",
    },
    {"name": "Chicago", "lat": 41.8781, "lon": -87.6298, "country": "EUA"},
    {"name": "Miami", "lat": 25.7617, "lon": -80.1918, "country": "EUA"},
    {
        "name": "Brasília",
        "lat": -15.7939,
        "lon": -47.8828,
        "country": "Brasil",
    },
    {"name": "Bogotá", "lat": 4.7110, "lon": -74.0721, "country": "Colômbia"},
    {"name": "Lima", "lat": -12.0464, "lon": -77.0428, "country": "Peru"},
    {"name": "Santiago", "lat": -33.4489, "lon": -70.6693, "country": "Chile"},
    {
        "name": "Johannesburg",
        "lat": -26.2041,
        "lon": 28.0473,
        "country": "África do Sul",
    },
    {"name": "Lagos", "lat": 6.5244, "lon": 3.3792, "country": "Nigéria"},
    {"name": "Nairobi", "lat": -1.2864, "lon": 36.8172, "country": "Quênia"},
    {"name": "Tel Aviv", "lat": 32.0853, "lon": 34.7818, "country": "Israel"},
    {"name": "Athens", "lat": 37.9838, "lon": 23.7275, "country": "Grécia"},
    {"name": "Stockholm", "lat": 59.3293, "lon": 18.0686, "country": "Suécia"},
    {
        "name": "Copenhagen",
        "lat": 55.6761,
        "lon": 12.5683,
        "country": "Dinamarca",
    },
    {"name": "Oslo", "lat": 59.9139, "lon": 10.7522, "country": "Noruega"},
    {
        "name": "Helsinki",
        "lat": 60.1695,
        "lon": 24.9354,
        "country": "Finlândia",
    },
    {"name": "Warsaw", "lat": 52.2297, "lon": 21.0122, "country": "Polônia"},
    {"name": "Prague", "lat": 50.0755, "lon": 14.4378, "country": "Tchéquia"},
    {"name": "Budapest", "lat": 47.4979, "lon": 19.0402, "country": "Hungria"},
]

# Cidades USA mais populares (para NWS Forecast e Stations)
POPULAR_USA_CITIES = [
    {"name": "New York", "lat": 40.7128, "lon": -74.0060, "state": "NY"},
    {"name": "Los Angeles", "lat": 34.0522, "lon": -118.2437, "state": "CA"},
    {"name": "Chicago", "lat": 41.8781, "lon": -87.6298, "state": "IL"},
    {"name": "Houston", "lat": 29.7604, "lon": -95.3698, "state": "TX"},
    {"name": "Phoenix", "lat": 33.4484, "lon": -112.0740, "state": "AZ"},
    {"name": "Philadelphia", "lat": 39.9526, "lon": -75.1652, "state": "PA"},
    {"name": "San Antonio", "lat": 29.4241, "lon": -98.4936, "state": "TX"},
    {"name": "San Diego", "lat": 32.7157, "lon": -117.1611, "state": "CA"},
    {"name": "Dallas", "lat": 32.7767, "lon": -96.7970, "state": "TX"},
    {"name": "San Jose", "lat": 37.3382, "lon": -121.8863, "state": "CA"},
    {"name": "Austin", "lat": 30.2672, "lon": -97.7431, "state": "TX"},
    {"name": "Jacksonville", "lat": 30.3322, "lon": -81.6557, "state": "FL"},
    {"name": "San Francisco", "lat": 37.7749, "lon": -122.4194, "state": "CA"},
    {"name": "Columbus", "lat": 39.9612, "lon": -82.9988, "state": "OH"},
    {"name": "Fort Worth", "lat": 32.7555, "lon": -97.3308, "state": "TX"},
    {"name": "Indianapolis", "lat": 39.7684, "lon": -86.1581, "state": "IN"},
    {"name": "Charlotte", "lat": 35.2271, "lon": -80.8431, "state": "NC"},
    {"name": "Seattle", "lat": 47.6062, "lon": -122.3321, "state": "WA"},
    {"name": "Denver", "lat": 39.7392, "lon": -104.9903, "state": "CO"},
    {"name": "Washington", "lat": 38.9072, "lon": -77.0369, "state": "DC"},
    {"name": "Boston", "lat": 42.3601, "lon": -71.0589, "state": "MA"},
    {"name": "Nashville", "lat": 36.1627, "lon": -86.7816, "state": "TN"},
    {"name": "Detroit", "lat": 42.3314, "lon": -83.0458, "state": "MI"},
    {"name": "Portland", "lat": 45.5152, "lon": -122.6784, "state": "OR"},
    {"name": "Las Vegas", "lat": 36.1699, "lon": -115.1398, "state": "NV"},
    {"name": "Miami", "lat": 25.7617, "lon": -80.1918, "state": "FL"},
    {"name": "Atlanta", "lat": 33.7490, "lon": -84.3880, "state": "GA"},
    {"name": "Minneapolis", "lat": 44.9778, "lon": -93.2650, "state": "MN"},
    {"name": "Tampa", "lat": 27.9506, "lon": -82.4572, "state": "FL"},
    {"name": "Orlando", "lat": 28.5383, "lon": -81.3792, "state": "FL"},
]

# Cidades nórdicas (para MET Norway Locationforecast)
# Região com alta qualidade: 1km MET Nordic + radar + bias-correction
POPULAR_NORDIC_CITIES = [
    # Noruega
    {"name": "Oslo", "lat": 59.9139, "lon": 10.7522, "country": "Noruega"},
    {"name": "Bergen", "lat": 60.3913, "lon": 5.3221, "country": "Noruega"},
    {
        "name": "Trondheim",
        "lat": 63.4305,
        "lon": 10.3951,
        "country": "Noruega",
    },
    {
        "name": "Stavanger",
        "lat": 58.9700,
        "lon": 5.7331,
        "country": "Noruega",
    },
    {"name": "Tromsø", "lat": 69.6492, "lon": 18.9553, "country": "Noruega"},
    # Suécia
    {
        "name": "Stockholm",
        "lat": 59.3293,
        "lon": 18.0686,
        "country": "Suécia",
    },
    {
        "name": "Gothenburg",
        "lat": 57.7089,
        "lon": 11.9746,
        "country": "Suécia",
    },
    {"name": "Malmö", "lat": 55.6050, "lon": 13.0038, "country": "Suécia"},
    {"name": "Uppsala", "lat": 59.8586, "lon": 17.6389, "country": "Suécia"},
    # Finlândia
    {
        "name": "Helsinki",
        "lat": 60.1699,
        "lon": 24.9384,
        "country": "Finlândia",
    },
    {"name": "Espoo", "lat": 60.2055, "lon": 24.6559, "country": "Finlândia"},
    {
        "name": "Tampere",
        "lat": 61.4978,
        "lon": 23.7610,
        "country": "Finlândia",
    },
    {"name": "Oulu", "lat": 65.0121, "lon": 25.4651, "country": "Finlândia"},
    # Dinamarca
    {
        "name": "Copenhagen",
        "lat": 55.6761,
        "lon": 12.5683,
        "country": "Dinamarca",
    },
    {"name": "Aarhus", "lat": 56.1629, "lon": 10.2039, "country": "Dinamarca"},
    {"name": "Odense", "lat": 55.4038, "lon": 10.4024, "country": "Dinamarca"},
    # Islândia
    {
        "name": "Reykjavik",
        "lat": 64.1466,
        "lon": -21.9426,
        "country": "Islândia",
    },
    # Países Bálticos
    {"name": "Tallinn", "lat": 59.4370, "lon": 24.7536, "country": "Estônia"},
    {"name": "Riga", "lat": 56.9496, "lon": 24.1052, "country": "Letônia"},
    {"name": "Vilnius", "lat": 54.6872, "lon": 25.2797, "country": "Lituânia"},
]


@shared_task(
    bind=True, max_retries=3, name="climate.prefetch_nasa_popular_cities"
)
def prefetch_nasa_popular_cities(self):
    """
    Pre-carrega dados NASA POWER para 50 cidades mais populares.

    Execução: Diariamente às 03:00 BRT via Celery Beat
    Período: Últimos 30 dias
    Fontes: NASA POWER (domínio público)

    Returns:
        dict: Status e estatísticas do pre-fetch
    """
    try:
        logger.info("🚀 Iniciando pre-fetch NASA POWER (50 cidades)")

        # Importa dentro da task para evitar circular imports
        from backend.api.services.nasa_power_client import NASAPowerClient
        from backend.infrastructure.cache.climate_cache import (
            create_climate_cache,
        )

        # Período: últimos 30 dias
        end = datetime.now()
        start = end - timedelta(days=30)

        # Cria cache e cliente
        cache = create_climate_cache("nasa")
        client = NASAPowerClient(cache=cache)

        success_count = 0
        failed_cities = []

        # Pre-fetch cada cidade
        for idx, city in enumerate(POPULAR_WORLD_CITIES, 1):
            try:
                # Usa asyncio para chamar método async
                loop = asyncio.get_event_loop()
                data = loop.run_until_complete(
                    client.get_daily_data(
                        lat=city["lat"],
                        lon=city["lon"],
                        start_date=start,
                        end_date=end,
                    )
                )

                if data:
                    success_count += 1
                    logger.info(
                        f"✅ [{idx}/{len(POPULAR_WORLD_CITIES)}] "
                        f"{city['name']}, {city['country']}"
                    )
                else:
                    failed_cities.append(city["name"])
                    logger.warning(f"⚠️ Sem dados para {city['name']}")

            except Exception as e:
                failed_cities.append(city["name"])
                logger.error(f"❌ Erro em {city['name']}: {str(e)[:100]}")

        # Estatísticas finais
        total = len(POPULAR_WORLD_CITIES)
        success_rate = (success_count / total) * 100

        result = {
            "status": "success" if success_count > 0 else "failed",
            "total_cities": total,
            "success": success_count,
            "failed": len(failed_cities),
            "success_rate": f"{success_rate:.1f}%",
            "failed_cities": failed_cities[:10],  # Primeiras 10
            "period": f"{start.date()} to {end.date()}",
        }

        logger.info(
            f"🎯 Pre-fetch NASA POWER completo: "
            f"{success_count}/{total} cidades ({success_rate:.1f}%)"
        )

        # Fecha conexões
        loop.run_until_complete(cache.close())
        loop.run_until_complete(client.close())

        return result

    except Exception as e:
        logger.error(f"💥 Erro crítico no pre-fetch NASA: {e}")
        # Retry com exponential backoff
        raise self.retry(exc=e, countdown=300)  # 5 minutos


@shared_task(name="climate.cleanup_old_cache")
def cleanup_old_cache():
    """
    Remove entradas de cache expiradas antigas.

    Execução: Diariamente às 02:00 BRT via Celery Beat
    Remove: Chaves com padrão 'climate:*' expiradas há mais de 7 dias

    Returns:
        dict: Estatísticas de limpeza
    """
    try:
        from redis.asyncio import Redis

        from config.settings import get_settings

        settings = get_settings()

        logger.info("🧹 Iniciando limpeza de cache climático antigo")

        loop = asyncio.get_event_loop()
        redis = Redis.from_url(
            settings.redis.redis_url, decode_responses=False
        )

        # Busca todas as chaves 'climate:*'
        keys = loop.run_until_complete(redis.keys("climate:*"))

        removed_count = 0
        kept_count = 0

        for key in keys:
            ttl = loop.run_until_complete(redis.ttl(key))

            # Remove se TTL expirado (< 0) ou muito baixo (< 1 hora)
            if ttl < 0 or ttl < 3600:
                loop.run_until_complete(redis.delete(key))
                removed_count += 1
            else:
                kept_count += 1

        logger.info(
            f"✅ Limpeza completa: {removed_count} removidas, "
            f"{kept_count} mantidas"
        )

        loop.run_until_complete(redis.close())

        return {
            "status": "success",
            "removed": removed_count,
            "kept": kept_count,
            "total_scanned": len(keys),
        }

    except Exception as e:
        logger.error(f"❌ Erro na limpeza de cache: {e}")
        return {"status": "error", "message": str(e)}


@shared_task(name="climate.generate_cache_stats")
def generate_cache_stats():
    """
    Gera estatísticas de uso do cache.

    Execução: A cada hora via Celery Beat
    Métricas: Hit rate, dados populares, tamanho do cache

    Returns:
        dict: Estatísticas de cache
    """
    try:
        from redis.asyncio import Redis

        from config.settings import get_settings

        settings = get_settings()
        loop = asyncio.get_event_loop()
        redis = Redis.from_url(
            settings.redis.redis_url, decode_responses=False
        )

        # Conta chaves por fonte
        sources = ["nasa", "met", "nws", "openmeteo"]
        stats = {}

        for source in sources:
            keys = loop.run_until_complete(redis.keys(f"climate:{source}:*"))
            stats[source] = {
                "total_keys": len(keys),
                "memory_mb": 0,
            }  # TODO: calcular tamanho real

        # Total geral
        total_keys = loop.run_until_complete(redis.dbsize())

        result = {
            "timestamp": datetime.now().isoformat(),
            "sources": stats,
            "total_keys_db": total_keys,
        }

        logger.info(f"📊 Cache stats: {result}")

        loop.run_until_complete(redis.close())

        return result

    except Exception as e:
        logger.error(f"❌ Erro ao gerar stats: {e}")
        return {"status": "error", "message": str(e)}


@shared_task(
    bind=True,
    max_retries=3,
    name="climate.prefetch_nws_forecast_usa_cities",
)
def prefetch_nws_forecast_usa_cities(self):
    """
    Pre-carrega previsões NWS (5 dias) para 30 cidades USA.

    Execução: A cada 6 horas via Celery Beat
    Período: Próximos 5 dias (forecast)
    Fonte: NWS API (dados públicos NOAA)
    Coverage: USA continental, Alaska, Hawaii

    Returns:
        dict: Status e estatísticas do pre-fetch
    """
    try:
        logger.info("🚀 Iniciando pre-fetch NWS Forecast (30 cidades USA)")

        # Importa dentro da task para evitar circular imports
        from backend.api.services.nws_forecast_sync_adapter import (
            NWSDailyForecastSyncAdapter,
        )

        # Período: próximos 5 dias
        start = datetime.now()
        end = start + timedelta(days=5)

        # Cria adapter (cache já configurado internamente)
        adapter = NWSDailyForecastSyncAdapter()

        success_count = 0
        failed_cities = []

        # Pre-fetch cada cidade USA
        for idx, city in enumerate(POPULAR_USA_CITIES, 1):
            try:
                data = adapter.get_daily_data_sync(
                    lat=city["lat"],
                    lon=city["lon"],
                    start_date=start,
                    end_date=end,
                )

                if data:
                    success_count += 1
                    logger.info(
                        f"✅ [{idx}/{len(POPULAR_USA_CITIES)}] "
                        f"{city['name']}, {city['state']} - "
                        f"{len(data)} dias"
                    )
                else:
                    failed_cities.append(city["name"])
                    logger.warning(f"⚠️ Sem dados para {city['name']}")

            except Exception as e:
                failed_cities.append(city["name"])
                logger.error(f"❌ Erro em {city['name']}: {str(e)[:100]}")

        # Estatísticas finais
        total = len(POPULAR_USA_CITIES)
        success_rate = (success_count / total) * 100

        result = {
            "status": "success" if success_count > 0 else "failed",
            "total_cities": total,
            "success": success_count,
            "failed": len(failed_cities),
            "success_rate": f"{success_rate:.1f}%",
            "failed_cities": failed_cities[:10],
            "period": f"{start.date()} to {end.date()}",
            "forecast_days": 5,
        }

        logger.info(
            f"🎯 Pre-fetch NWS Forecast completo: "
            f"{success_count}/{total} cidades ({success_rate:.1f}%)"
        )

        return result

    except Exception as e:
        logger.error(f"💥 Erro crítico no pre-fetch NWS Forecast: {e}")
        # Retry com exponential backoff
        raise self.retry(exc=e, countdown=300)  # 5 minutos


@shared_task(
    bind=True,
    max_retries=3,
    name="climate.prefetch_nws_stations_usa_cities",
)
def prefetch_nws_stations_usa_cities(self):
    """
    Pre-carrega observações NWS (histórico 7 dias) para 30 cidades USA.

    Execução: Diariamente às 04:00 BRT via Celery Beat
    Período: Últimos 7 dias (observações horárias agregadas)
    Fonte: NWS Stations API (dados públicos NOAA)
    Coverage: ~1800 estações USA

    Known Issues Monitored:
    - MADIS delays: até 20 minutos (normal)
    - CST timezone nulls: max/min podem ser null
    - Precip rounding: <0.4" pode arredondar para 0

    Returns:
        dict: Status e estatísticas do pre-fetch
    """
    try:
        logger.info("🚀 Iniciando pre-fetch NWS Stations (30 cidades USA)")

        # Importa dentro da task para evitar circular imports
        from backend.api.services.nws_stations_sync_adapter import (
            NWSStationsSyncAdapter,
        )

        # Período: últimos 7 dias
        end = datetime.now()
        start = end - timedelta(days=7)

        # Cria adapter (SEM filtrar atrasadas para histórico)
        # Cache já configurado internamente no client
        adapter = NWSStationsSyncAdapter(filter_delayed=False)

        success_count = 0
        failed_cities = []
        total_observations = 0

        # Pre-fetch cada cidade USA
        for idx, city in enumerate(POPULAR_USA_CITIES, 1):
            try:
                data = adapter.get_daily_data_sync(
                    lat=city["lat"],
                    lon=city["lon"],
                    start_date=start,
                    end_date=end,
                )

                if data:
                    success_count += 1
                    total_observations += len(data)
                    logger.info(
                        f"✅ [{idx}/{len(POPULAR_USA_CITIES)}] "
                        f"{city['name']}, {city['state']} - "
                        f"{len(data)} dias"
                    )
                else:
                    failed_cities.append(city["name"])
                    logger.warning(f"⚠️ Sem dados para {city['name']}")

            except Exception as e:
                failed_cities.append(city["name"])
                logger.error(f"❌ Erro em {city['name']}: {str(e)[:100]}")

        # Estatísticas finais
        total = len(POPULAR_USA_CITIES)
        success_rate = (success_count / total) * 100

        result = {
            "status": "success" if success_count > 0 else "failed",
            "total_cities": total,
            "success": success_count,
            "failed": len(failed_cities),
            "success_rate": f"{success_rate:.1f}%",
            "failed_cities": failed_cities[:10],
            "period": f"{start.date()} to {end.date()}",
            "historical_days": 7,
            "total_daily_records": total_observations,
        }

        logger.info(
            f"🎯 Pre-fetch NWS Stations completo: "
            f"{success_count}/{total} cidades ({success_rate:.1f}%), "
            f"{total_observations} dias agregados"
        )

        return result

    except Exception as e:
        logger.error(f"💥 Erro crítico no pre-fetch NWS Stations: {e}")
        # Retry com exponential backoff
        raise self.retry(exc=e, countdown=300)  # 5 minutos


@shared_task(
    bind=True,
    max_retries=3,
    name="climate.prefetch_openmeteo_forecast_popular_cities",
)
def prefetch_openmeteo_forecast_popular_cities(self):
    """
    Pre-carrega dados Open-Meteo Forecast para 50 cidades mais populares.

    Execução: Diariamente às 05:00 BRT via Celery Beat
    Período: Últimos 5 dias + próximos 5 dias
    Fonte: Open-Meteo Forecast API (global, 10k req/dia)

    Returns:
        dict: Status e estatísticas do pre-fetch
    """
    try:
        logger.info("🚀 Iniciando pre-fetch Open-Meteo Forecast (50 cidades)")

        # Importa dentro da task para evitar circular imports
        from backend.api.services.openmeteo_forecast_sync_adapter import (
            OpenMeteoForecastSyncAdapter,
        )
        from backend.infrastructure.cache.climate_cache import (
            create_climate_cache,
        )

        # Período: últimos 5 dias + próximos 5 dias (10 dias total)
        today = datetime.now()
        start = today - timedelta(days=5)
        end = today + timedelta(days=5)

        # Cria cache e adapter
        cache = create_climate_cache("openmeteo")
        adapter = OpenMeteoForecastSyncAdapter(cache=cache)

        success_count = 0
        failed_cities = []
        total_days = 0

        # Pre-fetch cada cidade
        for idx, city in enumerate(POPULAR_WORLD_CITIES, 1):
            try:
                data = adapter.get_data_sync(
                    lat=city["lat"],
                    lon=city["lon"],
                    start_date=start,
                    end_date=end,
                )

                if data:
                    success_count += 1
                    total_days += len(data)
                    logger.info(
                        f"✅ [{idx}/{len(POPULAR_WORLD_CITIES)}] "
                        f"{city['name']}, {city['country']} - {len(data)} dias"
                    )
                else:
                    failed_cities.append(city["name"])
                    logger.warning(f"⚠️ Sem dados para {city['name']}")

            except Exception as e:
                failed_cities.append(city["name"])
                logger.error(f"❌ Erro em {city['name']}: {str(e)[:100]}")

        # Estatísticas finais
        total = len(POPULAR_WORLD_CITIES)
        success_rate = (success_count / total) * 100

        result = {
            "status": "success" if success_count > 0 else "failed",
            "total_cities": total,
            "success": success_count,
            "failed": len(failed_cities),
            "success_rate": f"{success_rate:.1f}%",
            "failed_cities": failed_cities[:10],  # Primeiras 10
            "period": f"{start.date()} to {end.date()}",
            "total_days": total_days,
        }

        logger.info(
            f"🎯 Pre-fetch Open-Meteo Forecast completo: "
            f"{success_count}/{total} cidades ({success_rate:.1f}%), "
            f"{total_days} dias"
        )

        # Fecha cache
        import asyncio

        loop = asyncio.get_event_loop()
        loop.run_until_complete(cache.close())

        return result

    except Exception as e:
        logger.error(f"💥 Erro crítico no pre-fetch Open-Meteo: {e}")
        # Retry com exponential backoff
        raise self.retry(exc=e, countdown=300)  # 5 minutos


@shared_task(
    bind=True,
    max_retries=3,
    name="climate.prefetch_openmeteo_archive_popular_cities",
)
def prefetch_openmeteo_archive_popular_cities(self):
    """
    Pre-carrega dados Open-Meteo Archive para 50 cidades mais populares.

    Execução: Semanalmente aos domingos às 06:00 BRT via Celery Beat
    Período: Último ano completo (365 dias históricos)
    Fonte: Open-Meteo Archive API (1940-hoje, dados estáveis)
    TTL: 24 horas (dados históricos podem ter correções)

    Diferença do Forecast:
    - Archive: Dados históricos (1940 até 2 dias atrás)
    - Forecast: Dados recentes + previsão (-30d até +5d)

    Returns:
        dict: Status e estatísticas do pre-fetch
    """
    try:
        logger.info("🚀 Iniciando pre-fetch Open-Meteo Archive (50 cidades)")

        # Importa dentro da task para evitar circular imports
        from backend.api.services.openmeteo_archive_sync_adapter import (
            OpenMeteoArchiveSyncAdapter,
        )
        from backend.infrastructure.cache.climate_cache import (
            create_climate_cache,
        )

        # Período: último ano completo (365 dias)
        # Archive tem dados até hoje-2 dias (buffer de processamento)
        today = datetime.now()
        end = today - timedelta(days=2)
        start = end - timedelta(days=365)

        # Cria cache e adapter
        cache = create_climate_cache("openmeteo")
        adapter = OpenMeteoArchiveSyncAdapter(cache=cache)

        success_count = 0
        failed_cities = []
        total_days = 0

        # Pre-fetch cada cidade
        for idx, city in enumerate(POPULAR_WORLD_CITIES, 1):
            try:
                data = adapter.get_data_sync(
                    lat=city["lat"],
                    lon=city["lon"],
                    start_date=start,
                    end_date=end,
                )

                if data:
                    success_count += 1
                    total_days += len(data)
                    logger.info(
                        f"✅ [{idx}/{len(POPULAR_WORLD_CITIES)}] "
                        f"{city['name']}, {city['country']} - "
                        f"{len(data)} dias históricos"
                    )
                else:
                    failed_cities.append(city["name"])
                    logger.warning(
                        f"⚠️ Sem dados históricos para {city['name']}"
                    )

            except Exception as e:
                failed_cities.append(city["name"])
                logger.error(f"❌ Erro em {city['name']}: {str(e)[:100]}")

        # Estatísticas finais
        total = len(POPULAR_WORLD_CITIES)
        success_rate = (success_count / total) * 100

        result = {
            "status": "success" if success_count > 0 else "failed",
            "total_cities": total,
            "success": success_count,
            "failed": len(failed_cities),
            "success_rate": f"{success_rate:.1f}%",
            "failed_cities": failed_cities[:10],  # Primeiras 10
            "period": f"{start.date()} to {end.date()}",
            "total_days": total_days,
            "avg_days_per_city": (
                total_days / success_count if success_count > 0 else 0
            ),
        }

        logger.info(
            f"🎯 Pre-fetch Open-Meteo Archive completo: "
            f"{success_count}/{total} cidades ({success_rate:.1f}%), "
            f"{total_days} dias históricos"
        )

        # Fecha cache
        import asyncio

        loop = asyncio.get_event_loop()
        loop.run_until_complete(cache.close())

        return result

    except Exception as e:
        logger.error(f"💥 Erro crítico no pre-fetch Archive: {e}")
        # Retry com exponential backoff
        raise self.retry(exc=e, countdown=300)  # 5 minutos


@shared_task(
    bind=True,
    max_retries=3,
    name="climate.prefetch_met_norway_nordic_cities",
)
def prefetch_met_norway_nordic_cities(self):
    """
    Pre-carrega dados MET Norway Locationforecast para cidades nórdicas.

    Execução: Diariamente às 07:00 BRT via Celery Beat
    Período: Últimos 3 dias + próximos 7 dias (10 dias forecast)
    Fonte: MET Norway Locationforecast 2.0 (CC-BY 4.0)
    Região: Nordic (NO/SE/FI/DK/IS/Baltics) - Alta qualidade
    Qualidade: 1km MET Nordic + radar + bias-correction

    Diferença das outras APIs:
    - MET Norway: Melhor qualidade em região Nordic (1km + radar)
    - Open-Meteo: Boa qualidade global (9-11km ECMWF)
    - NASA POWER: Dados históricos globais (50km satellite)

    IMPORTANTE - FAIR USE POLICY:
    - Respeita Expires headers (não requisita antes de expirar)
    - Schedule espaçado (1x dia vs 4x dia do NWS)
    - Apenas 20 cidades (vs 50 Open-Meteo)
    - Região limitada (alta qualidade > volume)

    Returns:
        dict: Status e estatísticas do pre-fetch
    """
    try:
        logger.info("🚀 Iniciando pre-fetch MET Norway (20 cidades Nordic)")

        # Importa dentro da task para evitar circular imports
        from backend.api.services.met_norway_locationforecast_sync_adapter import (  # noqa: E501
            METNorwayLocationForecastSyncAdapter,
        )
        from backend.infrastructure.cache.climate_cache import (
            create_climate_cache,
        )

        # Período: últimos 3 dias + próximos 7 dias (10 dias forecast)
        today = datetime.now()
        start = today - timedelta(days=3)
        end = today + timedelta(days=7)

        # Cria cache e adapter
        cache = create_climate_cache("met_norway")
        adapter = METNorwayLocationForecastSyncAdapter(cache=cache)

        success_count = 0
        failed_cities = []
        total_days = 0
        nordic_count = 0

        # Pre-fetch cada cidade
        for idx, city in enumerate(POPULAR_NORDIC_CITIES, 1):
            try:
                data = adapter.get_daily_data_sync(
                    lat=city["lat"],
                    lon=city["lon"],
                    start_date=start,
                    end_date=end,
                )

                if data:
                    success_count += 1
                    total_days += len(data)
                    # Conta quantas são região Nordic (alta qualidade)
                    from backend.api.services.met_norway.met_norway_client import (
                        METNorwayClient,
                    )

                    is_nordic = METNorwayClient.is_in_nordic_region(
                        city["lat"], city["lon"]
                    )
                    if is_nordic:
                        nordic_count += 1

                    quality = "1km+radar" if is_nordic else "9km ECMWF"
                    logger.info(
                        f"✅ [{idx}/{len(POPULAR_NORDIC_CITIES)}] "
                        f"{city['name']}, {city['country']} - "
                        f"{len(data)} dias ({quality})"
                    )
                else:
                    failed_cities.append(city["name"])
                    logger.warning(f"⚠️ Sem dados forecast para {city['name']}")

            except Exception as e:
                failed_cities.append(city["name"])
                logger.error(f"❌ Erro em {city['name']}: {str(e)[:100]}")

        # Estatísticas finais
        total = len(POPULAR_NORDIC_CITIES)
        success_rate = (success_count / total) * 100

        result = {
            "status": "success" if success_count > 0 else "failed",
            "total_cities": total,
            "success": success_count,
            "failed": len(failed_cities),
            "success_rate": f"{success_rate:.1f}%",
            "failed_cities": failed_cities[:10],  # Primeiras 10
            "period": f"{start.date()} to {end.date()}",
            "total_days": total_days,
            "nordic_region_count": nordic_count,
            "avg_days_per_city": (
                total_days / success_count if success_count > 0 else 0
            ),
        }

        logger.info(
            f"🎯 Pre-fetch MET Norway completo: "
            f"{success_count}/{total} cidades ({success_rate:.1f}%), "
            f"{total_days} dias forecast, "
            f"{nordic_count} cidades Nordic (alta qualidade)"
        )

        # Fecha cache
        import asyncio

        loop = asyncio.get_event_loop()
        loop.run_until_complete(cache.close())

        return result

    except Exception as e:
        logger.error(f"💥 Erro crítico no pre-fetch MET Norway: {e}")
        # Retry com exponential backoff
        raise self.retry(exc=e, countdown=300)  # 5 minutos
