# Weather API Technical Specifications

## Introduction

This document describes the technical specifications of the six public weather APIs integrated into the system. The information was validated in **November 2025** and represents the current state of the services.

---

## 🌍 Weather APIs Overview

### Summary Table

| API | Coverage | Resolution | Data Type | Period Available |
|-----|----------|------------|-----------|------------------|
| **MET Norway** | Global (quality tiers) | Hourly → Daily | Forecast | Today + 5 days |
| **NASA POWER** | Global | Daily | Historical + Recent | 1990-01-01 to today − 2d (2-day delay) |
| **NWS Forecast** | USA only | Hourly → Daily | Forecast | Today + 5 days |
| **NWS Stations** | USA only (~1800 stations) | Hourly → Daily | Real-time observations | today − 2d to today |
| **Open-Meteo Archive** | Global | Daily | Historical | 1990-01-01 to (today - 2 days) |
| **Open-Meteo Forecast** | Global | Daily | Recent + Forecast | (today − 29 days) to (today + 5 days) |

---

## 📊 EVAonline Application Limits (Nov 2025)

### Request Type Validation

| Request Type | Context | Period Options | End Date Constraint | Use Case |
|--------------|---------|----------------|---------------------|----------|
| **Historical (Email)** | Background processing | 1-90 days (free choice) | end ≤ (today - 30 days) | CSV or Excel report via email |
| **Dashboard (Web)** | Real-time visualization | 7, 14, 21, or 30 days (dropdown) | end = today (fixed) | Interactive tables + charts |
| **Forecast (Web)** | Future predictions | 5 days (fixed) | start = today, end = today + 5d | Short-term planning |

### Examples of Valid Periods (ref: 14/11/2025)

```python
from datetime import datetime, timedelta

today = datetime(2025, 11, 14).date()

# ✅ VALID - Historical (fim ≤ hoje-30 dias)
start = datetime(2025, 7, 18).date()  # 18/07/2025
end = datetime(2025, 10, 15).date()    # 15/10/2025 (hoje-30 dias)
period = (end - start).days + 1        # 90 dias
context = "historical"
assert end <= today - timedelta(days=30)  # ✅ 15/10 ≤ 15/10

# ✅ VALID - Historical (qualquer ano desde 1990)
start = datetime(2013, 5, 1).date()   # 01/05/2013
end = datetime(2013, 7, 29).date()    # 29/07/2013
period = (end - start).days + 1       # 90 dias
context = "historical"
assert end <= today - timedelta(days=30)  # ✅ Muito antigo

# ✅ VALID - Dashboard 30 dias (fim SEMPRE hoje)
start = today - timedelta(days=29)    # 16/10/2025 (hoje-29d)
end = today                            # 14/11/2025 (hoje)
period = (end - start).days + 1       # 30 dias
context = "dashboard"
assert end == today  # ✅ Fim é hoje
assert period in [7, 14, 21, 30]  # ✅ Dropdown options

# ✅ VALID - Dashboard 7 dias (mínimo)
start = today - timedelta(days=6)     # 08/11/2025 (hoje-6d)
end = today                           # 14/11/2025 (hoje)
period = (end - start).days + 1       # 7 dias
context = "dashboard"
assert period == 7  # ✅ Exatamente 7 dias

# ✅ VALID - Forecast (fixo 5 dias)
start = today                         # 14/11/2025
end = today + timedelta(days=5)       # 19/11/2025 (14+5=19)
period = (end - start).days + 1       # 6 dias totais
context = "forecast"
assert start == today and end == today + timedelta(days=5)  # ✅ Fixo

# ❌ INVALID - Historical muito recente
start = datetime(2025, 11, 1).date()  # 01/11/2025
end = datetime(2025, 11, 13).date()   # 13/11/2025
context = "historical"
assert end <= today - timedelta(days=30)  # ❌ 13/11 > 15/10 (hoje-30d)
# ERROR: End date too recent for historical!

# ❌ INVALID - Dashboard fim não é hoje
start = datetime(2025, 10, 1).date()
end = datetime(2025, 10, 31).date()   # Não é hoje!
context = "dashboard"
# ERROR: Dashboard end must be today!

# ❌ INVALID - Historical período > 90 dias
start = datetime(2025, 1, 1).date()
end = datetime(2025, 5, 1).date()     # 121 dias
context = "historical"
# ERROR: Period 121 days > max 90 days!
```

---

## 📊 Dashboard Coverage Strategy (Gap Filling)

### Problem: Open-Meteo Archive 2-day delay

**Timeline for 30-day Dashboard (ref: 14/11/2025):**

```
Período solicitado: 16/10/2025 → 14/11/2025 (30 dias)

┌────────────────────────────────────────────┬─────────┬─────────┐
│         NASA POWER (completo)              │         │         │
│ 16/10 ────────────────────────────► 14/11  │         │         │
└────────────────────────────────────────────┴─────────┴─────────┘
  ✅ Cobertura: 30 dias SEM gap (até hoje)

┌────────────────────────────────────────────┬─────────┬─────────┐
│    Open-Meteo Archive (delay 2 dias)       │   GAP   │         │
│ 16/10 ────────────────────────► 12/11      │ 13/11   │ 14/11   │
└────────────────────────────────────────────┴─────────┴─────────┘
  ⚠️  Faltam: 13/11 e 14/11 (2 dias)

┌────────────────────────────────────────────┬─────────┬─────────┐
│                                            │ OM Fcst │         │
│                                            │ 13/11   │ 14/11   │
└────────────────────────────────────────────┴─────────┴─────────┘
  ✅ Open-Meteo Forecast preenche os 2 dias faltantes
```

### Solution: Multi-API Strategy

| API | Start | End | Purpose |
|-----|-------|-----|---------|
| **NASA POWER** | hoje-29d (16/10) | hoje (14/11) | Fonte primária completa - 30 dias |
| **Open-Meteo Archive** | hoje-29d (16/10) | hoje-2d (12/11) | Fonte histórica - 28 dias |
| **Open-Meteo Forecast** | hoje-1d (13/11) | hoje (14/11) | Preenche gap Archive - 2 dias |

**Implementation:**
```python
from datetime import datetime, timedelta

today = datetime(2025, 11, 14).date()

# Dashboard: últimos 30 dias (opção dropdown)
dashboard_start = today - timedelta(days=29)  # 16/10/2025
dashboard_end = today                          # 14/11/2025

# APIs a consultar (para 30 dias)
apis = {
    "nasa_power": {
        "start": dashboard_start,      # 16/10/2025
        "end": dashboard_end,           # 14/11/2025 ✅ SEM gap
        "coverage_days": 30
    },
    "openmeteo_archive": {
        "start": dashboard_start,      # 16/10/2025
        "end": today - timedelta(days=2),  # 12/11/2025 ⚠️ Gap de 2d
        "coverage_days": 28
    },
    "openmeteo_forecast": {
        "start": today - timedelta(days=1),  # 13/11/2025
        "end": dashboard_end,                # 14/11/2025 ✅ Preenche gap
        "coverage_days": 2,
        "purpose": "Fill Archive gap"
    }
}

# Fusão Kalman combina as 3 fontes
# Resultado: 30 dias completos sem gaps
```

---

## 🔧 API-Specific Details

### 1. MET Norway Locationforecast API

- **Documentation**: https://api.met.no/weatherapi/locationforecast/2.0/documentation
- **Data Model**: https://docs.api.met.no/doc/locationforecast/datamodel
- **Coverage**: **Global** (with quality tiers)
- **Resolution**: Hourly (aggregated to daily)
- **Period**: **5-day forecast** (today + 5 days)
- **License**: CC-BY 4.0 (attribution required)

#### Quality Tiers (Regional Strategy)

| Region | Resolution | Model | Variables | Precipitation Quality |
|--------|------------|-------|-----------|----------------------|
| **Nordic** (NO/SE/FI/DK/Baltics) | 1 km | MEPS 2.5km + downscaling | temp, humidity, wind, **precipitation** | ⭐⭐⭐⭐⭐ Very High (radar + bias correction) |
| **Global** (Rest of World) | 9 km | ECMWF IFS | **temp, humidity only** | ❌ Excluded (wind has different model, precipitation use Open-Meteo) |

**Nordic Bounding Box:**
- Longitude: 4.0°E to 31.0°E
- Latitude: 54.0°N to 71.5°N

#### Extracted Variables

**Instant Values (hourly snapshots):**
- `air_temperature`: Air temperature (°C)
- `relative_humidity`: Relative humidity (%)
- `wind_speed`: Wind speed at 10m (m/s)

**Next 1 hour:**
- `precipitation_amount`: Hourly precipitation (mm) - **Nordic only**

**Next 6 hours:**
- `air_temperature_max`: Maximum temperature (°C)
- `air_temperature_min`: Minimum temperature (°C)
- `precipitation_amount`: 6-hour precipitation (mm) - **Nordic only**

#### Request Limits

| Period | Limit | Action on Excess |
|--------|-------|------------------|
| **Per Second** | 20 requests/second | HTTP 429 (throttled) |
| **Per Minute** | <100 req/min (fair use) | Blocked temporarily |
| **Per Hour/Day/Month** | Fair use (monitor `Expires` headers) | Permanent ban if abused |

**Mandatory Requirements:**
- ✅ User-Agent: `"EVAonline/1.0 (contact@evaonline.com)"`
- ✅ HTTPS only
- ✅ Cache responses (honor `Expires` header)

**EVAonline Implementation:**
```python
from backend.api.services.met_norway import METNorwayClient

# Automatic region detection
client = METNorwayClient()
is_nordic = client.is_in_nordic_region(lat=59.9, lon=10.75)  # Oslo = True

# Variables automatically filtered by region
data = await client.get_daily_forecast(
    lat=59.9, lon=10.75, 
    start_date=datetime.today(),
    end_date=datetime.today() + timedelta(days=5),
    variables=None  # Auto-selects based on region
)
```

---

### 2. NASA POWER API

- **Website**: https://power.larc.nasa.gov/
- **Documentation**: https://power.larc.nasa.gov/docs/services/api/
- **Citation**: https://power.larc.nasa.gov/docs/referencing/
- **License**: Free use (Public Domain)
- **Version**: Daily 2.x.x
- **Community**: `AG` (Agronomy) - mandatory for agroclimatic data
- **Coverage**: **Global**
- **Resolution**: Daily
- **Period**: **1990-01-01 to today (no delay)**

#### Mandatory Attribution
> "Data obtained from NASA Langley Research Center POWER Project funded through the NASA Earth Science Directorate Applied Science Program."

#### Variables and Spatial Resolution

| Variable | Description | Spatial Resolution | Source |
|----------|-------------|-------------------|--------|
| `ALLSKY_SFC_SW_DWN` | All Sky Surface Shortwave Downward Irradiance (MJ/m²/day) | 1° × 1° | CERES SYN1deg |
| `T2M` | Temperature at 2 Meters (°C) | 0.5° × 0.625° | MERRA-2 |
| `T2M_MAX` | Temperature at 2 Meters Maximum (°C) | 0.5° × 0.625° | MERRA-2 |
| `T2M_MIN` | Temperature at 2 Meters Minimum (°C) | 0.5° × 0.625° | MERRA-2 |
| `RH2M` | Relative Humidity at 2 Meters (%) | 0.5° × 0.625° | MERRA-2 |
| `WS2M` | Wind Speed at 2 Meters (m/s) | 0.5° × 0.625° | MERRA-2 |
| `PRECTOTCORR` | Precipitation Corrected (mm/day) | 0.5° × 0.625° | MERRA-2 |

#### Request Limits

| Period | Limit | Notes |
|--------|-------|-------|
| **Per Second** | <1 req/s (recommended) | Fair use; typical response: 1-5 seconds |
| **Per Request** | Max 20 parameters (single point) | For regions: 1 parameter/request |
| **Per Day/Month** | No numerical limits | Monitor excessive use; avoid <0.5° resolution |

**EVAonline Implementation:**
```python
from backend.api.services.nasa_power import NASAPowerClient

client = NASAPowerClient()

# Historical data
data = await client.get_daily_data(
    lat=-15.8, lon=-47.9,  # Brasília
    start_date=datetime(2024, 1, 1),
    end_date=datetime(2024, 12, 31),
    variables=["T2M_MAX", "T2M_MIN", "PRECTOTCORR", "ALLSKY_SFC_SW_DWN"]
)
```

---

### 3. NWS Forecast API (NOAA)

- **Documentation**: https://www.weather.gov/documentation/services-web-api
- **FAQ**: https://weather-gov.github.io/api/general-faqs
- **License**: Public Domain (US Government)
- **Coverage**: **USA only** (Continental + Alaska + Hawaii)
  - Longitude: -125°W to -66°W
  - Latitude: 18°N to 71°N (includes Alaska)
- **Resolution**: Hourly → Daily
- **Period**: **5-day forecast** (120 hours ahead)

#### Technical Characteristics
- **User-Agent**: Mandatory (e.g., `"EVAonline/1.0 (contact@evaonline.com)"`)
- **Rate Limit**: ≈5 requests/second
- **Automatic Conversion**: °F → °C, mph → m/s
- **Aggregation**: Mean (temp/humidity/wind), Sum (precip), Max/Min (temp)

#### Request Limits

| Period | Limit | Action on Excess |
|--------|-------|------------------|
| **Per Second** | ≈5 req/s | HTTP 429 (retry after 5s) |
| **Per Day** | <1000 req/day (fair use) | Abuse review |

**Known Issues (2025):**
- ⚠️ API may return past data (automatically filtered by EVAonline)
- ⚠️ Minimum temperature has greater variation (nocturnal microclimate)
- ⚠️ Precipitation uses `quantitativePrecipitation` when available

**EVAonline Implementation:**
```python
from backend.api.services.nws_forecast import NWSForecastClient

client = NWSForecastClient()

# USA only
data = await client.get_daily_forecast(
    lat=38.9, lon=-77.0,  # Washington DC
    start_date=datetime.today(),
    end_date=datetime.today() + timedelta(days=5)
)
```

---

### 4. NWS Stations API (NOAA)

- **Documentation**: Same as NWS Forecast API
- **License**: Public Domain
- **Coverage**: **≈1800 stations in USA**
- **EVAonline period**: **1990-01-01 to today (real-time)**
- **Resolution**: Hourly → Daily

#### Typical Workflow
```python
from backend.api.services.nws_stations import NWSStationsClient

client = NWSStationsClient()

# 1. Find nearest stations
stations = await client.find_nearest_stations(lat=38.9, lon=-77.0, limit=5)

# 2. Get observations from best station
station_id = stations[0]['stationIdentifier']
data = await client.get_station_observations(
    station_id=station_id,
    start_date=datetime(2024, 1, 1),
    end_date=datetime(2024, 1, 31)
)

# 3. Aggregate to daily
daily_data = client.aggregate_to_daily(data)
```

#### Request Limits

| Period | Limit | Notes |
|--------|-------|-------|
| **Per Second** | ≈5 req/s | HTTP 429 on excess |
| **Per Day** | <1000 req/day (fair use) | Monitored for abuse |

**Known Issues (2025):**
- ⚠️ Observations may have up to 20-minute delay (MADIS)
- ⚠️ Null values in max/min temperature outside CST
- ⚠️ Precipitation <0.4" may be reported as 0 (rounding)

---

### 5. Open-Meteo Archive API

- **Endpoint**: https://archive-api.open-meteo.com/v1/archive
- **Documentation**: https://open-meteo.com/en/docs
- **Source Code**: https://github.com/open-meteo/open-meteo (AGPLv3)
- **License**: CC BY 4.0 + AGPLv3
- **Coverage**: **Global**
- **Resolution**: Daily
- **EVAonline period**: **1990-01-01 to (today - 2 days)**

#### Available Variables (10)

| Variable | Description | Unit |
|----------|-------------|------|
| `temperature_2m_max` | Daily maximum temperature | °C |
| `temperature_2m_min` | Daily minimum temperature | °C |
| `temperature_2m_mean` | Daily mean temperature | °C |
| `relative_humidity_2m_max` | Daily maximum relative humidity | % |
| `relative_humidity_2m_min` | Daily minimum relative humidity | % |
| `relative_humidity_2m_mean` | Daily mean relative humidity | % |
| `wind_speed_10m_mean` | Daily mean wind speed at 10m | m/s |
| `shortwave_radiation_sum` | Daily solar radiation | MJ/m² |
| `precipitation_sum` | Daily precipitation | mm |
| `et0_fao_evapotranspiration` | Daily reference evapotranspiration | mm |

#### Request Limits

| Period | Limit | Notes |
|--------|-------|-------|
| **Per Second** | <10 req/s (recommended) | Throttling on excess |
| **Per Day** | ≈10,000 req/day (free plan) | Paid plans for >1M req/month |

**Cache Strategy (Nov 2025):**
- Primary: Redis via ClimateCache (24h TTL)
- Fallback: `requests_cache` local (24h TTL)
- Historical data is stable (rarely changes)

**EVAonline Implementation:**
```python
from backend.api.services.openmeteo_archive import OpenMeteoArchiveClient

client = OpenMeteoArchiveClient()

# Historical data (global coverage)
data = await client.get_daily_data(
    lat=41.9, lon=12.45,  # Rome
    start_date=datetime(2024, 1, 1),
    end_date=datetime(2024, 12, 31)
)
```

---

### 6. Open-Meteo Forecast API

- **Endpoint**: https://api.open-meteo.com/v1/forecast
- **Documentation**: https://open-meteo.com/en/docs
- **Source Code**: https://github.com/open-meteo/open-meteo (AGPLv3)
- **License**: CC BY 4.0 + AGPLv3
- **Coverage**: **Global**
- **Resolution**: Daily
- **Period**: **(today - 30 days) to (today + 5 days)** = 36 days total

#### Variables
Identical to Open-Meteo Archive (see above)

#### Request Limits

| Period | Limit | Notes |
|--------|-------|-------|
| **Per Second** | <10 req/s (recommended) | Throttling on excess |
| **Per Day** | ≈10,000 req/day (free plan) | Paid plans for >1M req/month |

**Cache Strategy (Nov 2025):**
- Primary: Redis via ClimateCache (dynamic TTL)
- Fallback: `requests_cache` local
- **Dynamic TTL:**
  - Forecast (future): 1h
  - Recent (past): 6h

**EVAonline Implementation:**
```python
from backend.api.services.openmeteo_forecast import OpenMeteoForecastClient

client = OpenMeteoForecastClient()

# Recent + Forecast
data = await client.get_daily_data(
    lat=41.9, lon=12.45,  # Rome
    start_date=datetime.today() - timedelta(days=30),  # 30 days ago
    end_date=datetime.today() + timedelta(days=10)     # 10 days ahead
)
```

---

## 🔄 Data Aggregation Methods

### Hourly → Daily Conversion

| Variable | Aggregation Method |
|----------|-------------------|
| Temperature | Arithmetic mean |
| Humidity | Arithmetic mean |
| Wind Speed | Arithmetic mean |
| Precipitation | Cumulative sum |
| Solar Radiation | Cumulative sum |
| Max Temperature | Maximum value |
| Min Temperature | Minimum value |

### Example Code
```python
# Internal aggregation (automated)
hourly_temps = [15.2, 16.3, 17.8, 18.2, 17.5, 16.1]
daily_mean_temp = sum(hourly_temps) / len(hourly_temps)  # 16.85°C

hourly_precip = [0.5, 1.2, 0.0, 0.3, 0.0, 0.0]
daily_total_precip = sum(hourly_precip)  # 2.0 mm
```

---

## 🛡️ Request Management Best Practices

### Cache System (Two-Layer)

```python
from backend.infrastructure.cache import ClimateCache

# Primary: Redis (shared across workers)
cache = ClimateCache()
await cache.set(key="climate_data_rome_2024-01", data=data, ttl=86400)

# Fallback: Local requests_cache (per worker)
import requests_cache
session = requests_cache.CachedSession('climate_cache', expire_after=86400)
```

### Retry Strategy (Exponential Backoff)

```python
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10)
)
async def fetch_with_retry(url: str):
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.json()
```

### User-Agent Configuration

```python
# Mandatory for MET Norway and NWS
USER_AGENT = "EVAonline/1.0 (contact@evaonline.com)"

headers = {
    "User-Agent": USER_AGENT,
    "Accept": "application/json"
}
```

---

## 📞 API Support Contacts

| API | Contact Email |
|-----|---------------|
| **MET Norway** | support@met.no |
| **NASA POWER** | larc-power-project@mail.nasa.gov |
| **NWS (NOAA)** | api-support@noaa.gov |
| **Open-Meteo** | support@open-meteo.com |

---

## 🔍 Request Limits Summary Table

| API | Per Second | Per Minute | Per Day | Special Policies |
|-----|------------|------------|---------|------------------|
| **MET Norway** | 20 req/s | <100 req/min | Fair use | User-Agent mandatory; HTTPS only; Cache required |
| **NASA POWER** | <1 req/s (rec.) | Fair use | No limit | Max 20 params/request; Avoid <0.5° resolution |
| **NWS Forecast** | ≈5 req/s | Fair use | <1000 req/day | User-Agent mandatory; HTTPS only |
| **NWS Stations** | ≈5 req/s | Fair use | <1000 req/day | User-Agent mandatory; HTTPS only |
| **Open-Meteo Archive** | <10 req/s (rec.) | Fair use | ≈10,000 req/day | Cache mandatory; API key optional |
| **Open-Meteo Forecast** | <10 req/s (rec.) | Fair use | ≈10,000 req/day | Cache mandatory; API key optional |

---

## 📅 Last Updated
**November 14, 2025** - All limits and specifications were validated against official API documentation and EVAonline business rules.

---

## 📋 Quick Reference: EVAonline Date Constraints

### Context Summary Table

| Context | APIs Used | Start Date | End Date | Period Options | Example (ref: 14/11/2025) |
|---------|-----------|------------|----------|----------------|---------------------------|
| **Historical** | NASA POWER + Open-Meteo Archive | User choice (≥ 1990) | User choice (≤ hoje-30d) | 1-90 days (free) | 18/07/2025 → 15/10/2025 (90d) |
| **Dashboard** | NASA POWER + Archive + Forecast | hoje-[29,20,13,6]d | hoje (fixed) | 7, 14, 21, 30 days (dropdown) | 16/10/2025 → 14/11/2025 (30d) |
| **Forecast** | Forecast + MET Norway + NWS | hoje (fixed) | hoje+5d (fixed) | 5 days (fixed) | 14/11/2025 → 19/11/2025 (5d) |

### API Capabilities Matrix

| API | Data Type | Start Limit | End Limit | EVAonline Use Cases |
|-----|-----------|-------------|-----------|---------------------|
| **NASA POWER** | Historical + Recent | 1990-01-01 | hoje | Historical + Dashboard |
| **Open-Meteo Archive** | Historical | 1990-01-01 | hoje-2d | Historical + Dashboard (até hoje-2d) |
| **Open-Meteo Forecast** | Recent + Forecast | hoje-30d | hoje+5d | Dashboard (gap fill) + Forecast |
| **MET Norway** | Forecast | hoje | hoje+5d | Forecast (global) |
| **NWS Forecast** | Forecast | hoje | hoje+5d | Forecast (USA only) |
| **NWS Stations** | Real-time | 1990-01-01 | hoje | Real-time observations (USA only) |

### Validation Rules

```python
# Historical Mode
def validate_historical(start: date, end: date, today: date) -> bool:
    """
    - Start: >= 1990-01-01
    - End: <= today - 30 days
    - Period: 1-90 days
    - Free date selection within constraints
    """
    period = (end - start).days + 1
    return (
        start >= date(1990, 1, 1) and
        end <= today - timedelta(days=30) and
        1 <= period <= 90
    )

# Dashboard Mode
def validate_dashboard(start: date, end: date, today: date) -> bool:
    """
    - Start: calculated from period choice
    - End: today (FIXED)
    - Period: 7, 14, 21, or 30 days (dropdown options)
    """
    period = (end - start).days + 1
    return (
        end == today and
        period in [7, 14, 21, 30]  # Dropdown options
    )

# Forecast Mode
def validate_forecast(start: date, end: date, today: date) -> bool:
    """
    - Start: today (FIXED)
    - End: today + 5 days (FIXED)
    - Period: 6 days total (today + next 5 days)
    """
    period = (end - start).days + 1
    return (
        start == today and
        end == today + timedelta(days=5) and
        period == 6  # 14/11 to 19/11 = 6 days
    )
```

---

## 📖 Additional Resources

- [EVAonline Climate Services Documentation](../README.md)
- [API Client Implementation Guide](./climate_factory.py)
- [Cache Strategy Documentation](../../infrastructure/cache/README.md)
- [Testing Guide](../../tests/README.md)