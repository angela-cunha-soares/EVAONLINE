# 🏗️ EVAonline — Architecture Documentation

**Last updated:** 2025-02-23  
**Status:** Production-ready

---

## 📋 Table of Contents

1. [System Overview](#system-overview)
2. [High-Level Architecture](#high-level-architecture)
3. [Service Architecture (Docker)](#service-architecture-docker)
4. [Backend Architecture](#backend-architecture)
5. [Frontend Architecture](#frontend-architecture)
6. [Data Flow](#data-flow)
7. [Climate Data Sources](#climate-data-sources)
8. [ETo Calculation (FAO-56)](#eto-calculation-fao-56)
9. [WebSocket Progress System](#websocket-progress-system)
10. [Download System](#download-system)
11. [Directory Structure](#directory-structure)

---

## System Overview

EVAonline is a comprehensive web application for calculating reference evapotranspiration (ET₀) using the **FAO-56 Penman-Monteith** method. It integrates real-time meteorological data from **multiple global sources** using a **Kalman-filter data fusion** approach.

### Key Features
- **5 Climate Data Sources**: NASA POWER, Open-Meteo, MET Norway, NWS Forecast, NWS Stations
- **3 Calculation Modes**: Recent (7–30 days), Historical (custom range), Forecast (today + 5 days)
- **Kalman Filter Fusion**: Optimal merging of multi-source data with quality weighting
- **Real-time Progress**: WebSocket-based progress tracking for long calculations
- **Per-table/chart Downloads**: CSV, Excel, PNG for each result component
- **Bilingual Interface**: Full EN/PT support with runtime switching
- **Water Deficit Analysis**: Irrigation requirement calculations
- **Interactive Maps**: Click-to-select location with Leaflet.js

### Technology Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | Dash 2.x + Plotly + dash-leaflet |
| **Backend API** | FastAPI 0.100+ + Uvicorn |
| **Task Queue** | Celery 5.x + Redis broker |
| **Database** | PostgreSQL 16 + SQLAlchemy 2.0 |
| **Cache** | Redis 7.x |
| **Reverse Proxy** | Nginx (single entry point) |
| **Monitoring** | Prometheus + Grafana + Flower |
| **Container** | Docker Compose (13 services) |

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        NGINX (port 80/443)                       │
│              Single public entry point + SSL termination          │
├──────────┬──────────────┬───────────────┬────────────────────────┤
│   /      │  /api/v1/*   │  /grafana/*   │  /flower/*             │
│  Dash UI │  FastAPI     │  Grafana      │  Flower                │
└────┬─────┴──────┬───────┴───────┬───────┴──────────┬─────────────┘
     │            │               │                  │
     ▼            ▼               ▼                  ▼
┌─────────┐ ┌──────────┐  ┌──────────┐        ┌──────────┐
│  Dash   │ │ FastAPI  │  │ Grafana  │        │  Flower  │
│ Frontend│ │ Backend  │  │ (3000)   │        │  (5555)  │
│ (8050)  │ │ (8000)   │  └────┬─────┘        └────┬─────┘
└────┬────┘ └────┬─────┘       │                    │
     │           │              │                    │
     │     ┌─────┴──────┐      │              ┌─────┴──────┐
     │     │  WebSocket  │      │              │   Celery   │
     │     │  /ws/eto/   │      │              │  Workers   │
     │     └─────┬───────┘      │              └─────┬──────┘
     │           │              │                    │
     ▼           ▼              ▼                    ▼
┌────────────────────────────────────────────────────────────┐
│                    Docker Internal Network                   │
│                    (evaonline-network)                        │
├──────────────┬──────────────┬────────────────────────────────┤
│  PostgreSQL  │    Redis     │         Prometheus             │
│   (5432)     │   (6379)     │          (9090)                │
│              │  broker +    │   scrapes /metrics             │
│              │  cache       │   from API + Flower            │
└──────────────┴──────────────┴────────────────────────────────┘
```

---

## Service Architecture (Docker)

The application runs as **13 Docker services** defined in `docker-compose.yml`:

### Core Services

| Service | Image | Port | Role |
|---------|-------|------|------|
| `postgres` | postgres:16-alpine | 5432 (internal) | Primary database |
| `redis` | redis:7-alpine | 6379 (internal) | Celery broker + result cache |
| `api` | evaonline (custom) | 8000 (internal) | FastAPI backend + WebSocket |
| `dash` | evaonline (custom) | 8050 (internal) | Dash frontend application |
| `celery-worker` | evaonline (custom) | — | Async ETo calculation tasks |
| `celery-beat` | evaonline (custom) | — | Periodic task scheduler |
| `nginx` | nginx:1.25-alpine | **80 (public)** | Reverse proxy, rate limiting |

### Monitoring Services

| Service | Image | Port | Role |
|---------|-------|------|------|
| `prometheus` | prom/prometheus | 9090 (internal) | Metrics collection |
| `grafana` | grafana/grafana | 3000 (internal) | Dashboards & visualization |
| `flower` | mher/flower | 5555 (internal) | Celery task monitoring |

### Database Init Services

| Service | Role |
|---------|------|
| `db-init` | Creates initial schema + extensions |
| `db-migrate` | Runs Alembic migrations |
| `db-seed` | Seeds reference data |

### Key Design Decisions

1. **Only port 80/443 is public** — all other services use Docker internal network
2. **Nginx handles**: routing, rate limiting, security headers, static caching, gzip
3. **Health checks** on all services with restart policies
4. **Named volumes** for data persistence (postgres-data, redis-data, grafana-data)

---

## Backend Architecture

### Module Structure

```
└── 📁backend
    └── 📁api
        └── 📁middleware
            ├── __init__.py
            ├── prometheus_metrics.py
            ├── prometheus.py
            ├── rate_limiter.py
        └── 📁routes
            ├── __init__.py
            ├── climate_sources.py
            ├── eto_routes.py
            ├── geolocation_routes.py
            ├── health.py
            ├── visitor_routes.py
        └── 📁services
            └── 📁met_norway
                ├── __init__.py
                ├── met_norway_client.py
                ├── met_norway_sync_adapter.py
            └── 📁nasa_power
                ├── __init__.py
                ├── nasa_power_client.py
                ├── nasa_power_sync_adapter.py
            └── 📁nws_forecast
                ├── __init__.py
                ├── nws_forecast_client.py
                ├── nws_forecast_sync_adapter.py
            └── 📁nws_stations
                ├── __init__.py
                ├── nws_stations_client.py
                ├── nws_stations_sync_adapter.py
            └── 📁openmeteo_archive
                ├── __init__.py
                ├── openmeteo_archive_client.py
                ├── openmeteo_archive_sync_adapter.py
            └── 📁openmeteo_forecast
                ├── __init__.py
                ├── openmeteo_forecast_client.py
                ├── openmeteo_forecast_sync_adapter.py
            └── 📁opentopo
                ├── __init__.py
                ├── opentopo_client.py
                ├── opentopo_sync_adapter.py
            ├── __init__.py
            ├── climate_factory.py
            ├── climate_source_availability.py
            ├── climate_source_manager.py
            ├── climate_source_selector.py
            ├── climate_validation.py
            ├── data_download.py
            ├── eto_variable_validator.py
            ├── geographic_utils.py
            ├── README.md
            ├── timezone_utils.py
            ├── weather_utils.py
        └── 📁websocket
            ├── __init__.py
            ├── websocket_service.py
    └── 📁core
        └── 📁analytics
            ├── __init__.py
            ├── geolocation_service.py
            ├── visitor_counter_service.py
        └── 📁data_processing
            ├── __init__.py
            ├── climate_ensemble.py
            ├── climate_fusion.py
            ├── climate_limits.py
            ├── data_preprocessing.py
            ├── historical_loader.py
            ├── kalman_filters.py
        └── 📁data_results
            ├── __init__.py
            ├── results_graphs.py
            ├── results_layout.py
            ├── results_statistical.py
            ├── results_tables.py
        └── 📁eto_calculation
            ├── __init__.py
            ├── eto_services.py
        └── 📁utils
            ├── __init__.py
            ├── email_templates.py
            ├── email_utils.py
            ├── geo_utils.py
        ├── __init__.py
    └── 📁database
        └── 📁models
            ├── __init__.py
            ├── admin_user.py
            ├── api_variables.py
            ├── climate_data.py
            ├── user_cache.py
            ├── visitor_stats.py
        ├── __init__.py
        ├── connection.py
        ├── data_storage.py
        ├── health_checks.py
        ├── redis_pool.py
        ├── session_database.py
    └── 📁infrastructure
        └── 📁cache
            ├── __init__.py
            ├── api_usage_tracker.py
            ├── cache_manager.py
            ├── celery_tasks.py
            ├── climate_cache.py
            ├── climate_tasks.py
            ├── redis_manager.py
        └── 📁celery
            └── 📁tasks
                ├── __init__.py
                ├── data_download.py
                ├── eto_calculation.py
                ├── visitor_sync.py
            ├── __init__.py
            ├── celery_config.py
        └── 📁loaders
            ├── climate_history_loader.py
        ├── __init__.py
        ├── visitor_tracking.py
    └── 📁logs
    └── 📁tests
        └── 📁e2e
            └── 📁celery
                ├── test_async_climate_download.py
            ├── __init__.py
            ├── test_api_fallback_scenarios.py
            ├── test_historical_email.py
            ├── test_spatial_analysis.py
        └── 📁fixtures
            └── 📁builders
                ├── __init__.py
                ├── api_response_builder.py
                ├── climate_data_builder.py
            └── 📁factories
                ├── __init__.py
                ├── climate_data_factory.py
                ├── geometry_factory.py
                ├── station_factory.py
            └── 📁mocks
                ├── __init__.py
                ├── met_norway_mock.py
                ├── nasa_power_mock.py
                ├── opentopo_mock.py
            ├── __init__.py
        └── 📁helpers
            ├── __init__.py
            ├── api_client.py
            ├── assertions.py
            ├── database_utils.py
            ├── spatial_helpers.py
        └── 📁integration
            └── 📁api
                └── 📁test_middleware
                    ├── __init__.py
                    ├── test_cors.py
                    ├── test_rate_limiting.py
                └── 📁test_rest
                    ├── __init__.py
                    ├── test_climate_endpoints.py
                    ├── test_eto_endpoints.py
                    ├── test_spatial_endpoints.py
                ├── __init__.py
                ├── test_climate_sources.py
                ├── test_eto_calculation.py
                ├── test_schemathesis_contract.py
            └── 📁celery
                ├── __init__.py
                ├── test_climate_tasks.py
                ├── test_eto_tasks.py
                ├── test_worker_config.py
            └── 📁database
                └── 📁test_migrations
                    ├── __init__.py
                    ├── test_alembic_migrations.py
                └── 📁test_repositories
                    ├── __init__.py
                    ├── test_climate_repository_integration.py
                    ├── test_spatial_repository.py
                └── 📁test_spatial
                    ├── __init__.py
                    ├── test_geo_operations.py
                    ├── test_postgis_geometries.py
                    ├── test_spatial_indexes.py
                ├── __init__.py
                ├── test_cache_invalidation.py
                ├── test_climate_data_storage.py
                ├── test_transaction_rollback.py
            └── 📁infrastructure
                ├── test_celery_tasks.py
                ├── test_climate_cache_flow.py
            ├── __init__.py
            ├── conftest.py
            ├── test_frontend_backend_eto_flow.py
        └── 📁performance
            ├── __init__.py
            ├── test_api_response_times.py
            ├── test_critical_queries.py
            ├── test_eto_performance.py
            ├── test_spatial_operations.py
        └── 📁security
            ├── __init__.py
            ├── test_geo_validation.py
            ├── test_input_validation.py
            ├── test_rate_limiting.py
        └── 📁unit
            └── 📁api
                ├── test_api_clients_comprehensive.py
                ├── test_climate_source_manager_comprehensive.py
                ├── test_climate_sources_route.py
                ├── test_data_download_phase5.py
                ├── test_geolocation_routes.py
                ├── test_health_routes.py
                ├── test_met_opentopo_phase6.py
                ├── test_middleware.py
                ├── test_nws_clients_phase7.py
                ├── test_nws_forecast_comprehensive.py
                ├── test_openmeteo_clients_phase6.py
                ├── test_opentopo_sync_adapter.py
                ├── test_pure_functions_phase4.py
                ├── test_rate_limiter_comprehensive.py
                ├── test_routes_climate.py
                ├── test_routes_eto.py
                ├── test_routes_health.py
                ├── test_services_comprehensive.py
                ├── test_sync_adapters_phase4.py
                ├── test_visitor_routes.py
                ├── test_websocket_endpoint.py
                ├── test_websocket_service_expanded.py
                ├── test_websocket_service.py
            └── 📁application
                └── 📁test_queries
                    ├── __init__.py
                    ├── test_historical_data.py
                    ├── test_spatial_queries.py
                └── 📁test_use_cases
                    ├── __init__.py
                    ├── test_calculate_eto.py
                    ├── test_climate_factory.py
                    ├── test_climate_source_availability.py
                    ├── test_climate_source_manager.py
                    ├── test_climate_source_selector.py
                    ├── test_climate_validation.py
                    ├── test_eto_variable_validator.py
                    ├── test_geographic_utils.py
                    ├── test_get_climate_data.py
                    ├── test_historical_data.py
                    ├── test_kalman_ensemble.py
                    ├── test_timezone_utils.py
                    ├── test_weather_utils_comprehensive.py
                    ├── test_weather_utils.py
                ├── __init__.py
            └── 📁core
                ├── test_api_stats_layout_comprehensive.py
                ├── test_climate_fusion_deep.py
                ├── test_climate_fusion_phase5.py
                ├── test_data_download_eto_comprehensive.py
                ├── test_data_preprocessing_phase7.py
                ├── test_data_results_comprehensive.py
                ├── test_email_comprehensive.py
                ├── test_email_templates_comprehensive.py
                ├── test_email_utils_phase4.py
                ├── test_email_utils_phase7.py
                ├── test_email_utils.py
                ├── test_eto_calc_service_phase7.py
                ├── test_eto_calculation_service.py
                ├── test_eto_services_phase5.py
                ├── test_geolocation_service.py
                ├── test_historical_loader_phase5.py
                ├── test_infra_tasks_phase6.py
                ├── test_pipeline_support_phase5.py
                ├── test_remaining_coverage_comprehensive.py
                ├── test_results_graphs_phase7.py
                ├── test_results_statistical_phase7.py
            └── 📁data_processing
                ├── test_kalman_ensemble.py
            └── 📁database
                ├── test_cache_manager.py
                ├── test_climate_data_storage.py
                ├── test_connection.py
                ├── test_health_checks.py
                ├── test_models.py
                ├── test_redis_pool.py
                ├── test_session_database.py
            └── 📁domain
                ├── __init__.py
                ├── test_climate_fusion_comprehensive.py
                ├── test_climate_fusion.py
                ├── test_data_preprocessing_comprehensive.py
                ├── test_data_preprocessing.py
                ├── test_data_results_functions.py
                ├── test_data_results_init.py
                ├── test_domain_services.py
                ├── test_entities.py
                ├── test_geo_utils.py
                ├── test_results_graphs.py
                ├── test_results_tables.py
                ├── test_value_objects.py
            └── 📁fixtures
                ├── test_factories_refactored.py
            └── 📁infra
                ├── test_cache_infra_phase7.py
                ├── test_climate_tasks_phase7.py
                ├── test_eto_calculation_task_phase7.py
            └── 📁infrastructure
                └── 📁test_adapters
                    ├── __init__.py
                    ├── test_met_norway_adapter.py
                    ├── test_nasa_power_adapter.py
                    ├── test_nws_forecast_adapter.py
                    ├── test_nws_stations_adapter.py
                    ├── test_openmeteo_archive_adapter.py
                    ├── test_openmeteo_forecast_adapter.py
                    ├── test_opentopo_adapter.py
                └── 📁test_repositories
                    ├── __init__.py
                    ├── test_cache_repository.py
                    ├── test_climate_repository.py
                ├── __init__.py
                ├── test_cache_comprehensive.py
                ├── test_cache_manager.py
                ├── test_climate_tasks_comprehensive.py
                ├── test_climate_tasks_phase4.py
                ├── test_eto_calculation_task_phase4.py
                ├── test_visitor_tracking.py
            ├── __init__.py
            ├── conftest.py
            ├── test_admin_user.py
            ├── test_database_init.py
            ├── test_logging_config.py
            ├── test_services_init.py
            ├── test_visitor_tracking.py
        ├── __init__.py
        ├── conftest.py
    ├── __init__.py
    └── main.py
```

### Request Processing Flow

```
HTTP Request → Nginx → FastAPI Router → Service Layer → Data Sources
                                            │                │
                                            ▼                ▼
                                       Kalman Fusion ← API Responses
                                            │
                                            ▼
                                     ETo Calculator
                                            │
                                            ▼
                                    PostgreSQL + Redis Cache
                                            │
                                            ▼
                                     HTTP Response (JSON)
```

### Async Task Processing (Celery)

For long-running ETo calculations:

```
1. Client sends POST /api/v1/eto/calculate
2. FastAPI creates Celery task → returns task_id
3. Client connects WebSocket /ws/eto/{task_id}
4. Celery worker executes:
   a. Fetch data from 5 climate APIs (parallel)
   b. Apply Kalman filter fusion
   c. Calculate ETo for each day
   d. Store results in PostgreSQL
   e. Send progress updates via WebSocket
5. Client receives real-time progress + final results
```

---

## Frontend Architecture

### Module Structure

```
└── 📁frontend
    └── 📁assets
        └── 📁css
            ├── custom.css
        └── 📁images
            ├── Flag_of_Brazil.svg
            ├── Flag_of_the_United_States.svg
            ├── github.svg
            ├── logo_c4ai.svg
            ├── logo_esalq.svg
            ├── logo_evaonline.svg
            ├── logo_fapesp.svg
            ├── logo_ibm.svg
            ├── logo_leb.svg
            ├── logo_usp.svg
            ├── ORCID_iD.svg
        └── 📁js
            ├── chart_download.js
            ├── datepicker_locale.js
        ├── favicon.ico
    └── 📁callbacks
        ├── __init__.py
        ├── cache_callbacks.py
        ├── eto_callbacks.py
        ├── home_callbacks.py
        ├── navbar_callbacks.py
        ├── navigation_callbacks.py
        ├── registry.py
        ├── visitor_callbacks.py
    └── 📁components
        ├── __init__.py
        ├── footer.py
        ├── info_cards.py
        ├── navbar.py
        ├── world_map_leaflet.py
    └── 📁core
        ├── __init__.py
        ├── base_layout.py
        ├── dash_app_config.py
    └── 📁pages
        ├── __init__.py
        ├── about.py
        ├── architecture.py
        ├── documentation.py
        ├── home.py
    └── 📁services
        ├── __init__.py
    └── 📁tests
        ├── __init__.py
        ├── test_documentation.py
        ├── test_eto_callbacks_expanded.py
        ├── test_eto_callbacks.py
        ├── test_get_translations.py
        ├── test_home_callbacks_layer_control.py
        ├── test_home_callbacks.py
        ├── test_info_cards.py
        ├── test_mode_detector.py
        ├── test_navbar_callbacks.py
        ├── test_navigation_cache_callbacks.py
        ├── test_setup_docker.py
        ├── test_user_geolocation.py
        ├── test_visitor_callbacks.py
        ├── test_websocket_client.py
        ├── test_world_map_leaflet.py
    └── 📁utils
        ├── __init__.py
        ├── mode_detector.py
        ├── user_geolocation.py
    ├── __init__.py
    └── app.py
```

### Multi-Page Navigation

| Route | Page | Description |
|-------|------|-------------|
| `/` | Dashboard | Main ETo calculator with map |
| `/documentation` | Documentation | User guide, methodology, downloads |
| `/architecture` | Architecture | System architecture diagrams |
| `/about` | About | Project info, team, publications |

### Download System

Each results section has individual download buttons:

```
Results Panel
├── Summary Table         → [CSV] [Excel] [PNG]
├── Daily ETo Chart       → [PNG] [CSV]
├── Monthly Summary       → [CSV] [Excel] [PNG]
├── Data Sources Table    → [CSV] [Excel]
├── Water Deficit Chart   → [PNG] [CSV]
└── Full Report           → [Excel] (all sheets)
```

---

## Data Flow

### Complete ETo Calculation Pipeline

```
┌──────────────────────────────────────────────────────────────────┐
│ STEP 1: User Input                                                │
│ • Latitude/Longitude (map click or manual)                        │
│ • Mode: Recent | Historical | Forecast                            │
│ • Date range (historical only)                                    │
│ • Language: EN | PT                                               │
└──────────┬───────────────────────────────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────────────────────────────┐
│ STEP 2: Elevation Retrieval                                       │
│ • Source: Open-Elevation API (open-elevation.com)                 │
│ • Fallback: Estimate from latitude                                │
│ • Cache: Redis (24h TTL)                                          │
└──────────┬───────────────────────────────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────────────────────────────┐
│ STEP 3: Multi-Source Climate Data Fetch (parallel)                │
│                                                                    │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐              │
│  │  NASA POWER   │ │  Open-Meteo  │ │ MET Norway   │              │
│  │  (Global)     │ │  (Global)    │ │ (Nordic opt.) │              │
│  │  Daily/hourly │ │  Archive +   │ │ Forecast      │              │
│  │  1990-present │ │  Forecast    │ │ today + 5d    │              │
│  └──────┬───────┘ └──────┬───────┘ └──────┬───────┘              │
│         │                │                │                       │
│  ┌──────┴───────┐ ┌──────┴───────┐                               │
│  │ NWS Forecast │ │ NWS Stations │                                │
│  │  (US only)   │ │  (US only)   │                                │
│  │ today + 5d   │ │ Observations │                                │
│  └──────┬───────┘ └──────┬───────┘                               │
│         │                │                                        │
│         ▼                ▼                                        │
│  Each source returns standardized DataFrame:                      │
│  [date, temp_max, temp_min, temp_mean, humidity, wind_speed,      │
│   solar_radiation, pressure, precipitation, ...]                  │
└──────────┬───────────────────────────────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────────────────────────────┐
│ STEP 4: Data Quality Assessment                                   │
│ • Completeness check (% non-null per variable)                    │
│ • Physical range validation (e.g., temp -50 to +60°C)            │
│ • Temporal consistency (no future dates, sorted)                  │
│ • Source reliability scoring (NASA=0.9, OpenMeteo=0.85, etc.)     │
└──────────┬───────────────────────────────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────────────────────────────┐
│ STEP 5: Kalman Filter Data Fusion                                 │
│ • State vector: [T_max, T_min, T_mean, RH, u₂, R_s, P]         │
│ • Process noise Q: estimated from source variability              │
│ • Measurement noise R: per-source, per-variable                   │
│ • Innovation sequence: detects outliers                           │
│ • Output: optimal fused estimate + uncertainty                    │
│ (See "Kalman Filter Data Fusion" section for details)             │
└──────────┬───────────────────────────────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────────────────────────────┐
│ STEP 6: Wind Height Correction                                    │
│ • Convert wind speed to 2m reference height                       │
│ • Formula: u₂ = uz × [4.87 / ln(67.8z - 5.42)]                  │
│ • NASA POWER: z=10m, Open-Meteo: z=10m, others vary              │
└──────────┬───────────────────────────────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────────────────────────────┐
│ STEP 7: FAO-56 Penman-Monteith ETo Calculation                   │
│                                                                    │
│        0.408 Δ(Rn - G) + γ [900/(T+273)] u₂ (es - ea)           │
│ ETo = ─────────────────────────────────────────────────           │
│                     Δ + γ(1 + 0.34 u₂)                           │
│                                                                    │
│ Where:                                                             │
│   Rn = net radiation (from Rs, latitude, day of year)             │
│   G  = soil heat flux (≈0 for daily)                              │
│   Δ  = slope of vapor pressure curve                              │
│   γ  = psychrometric constant (from altitude/pressure)            │
│   es = saturation vapor pressure (from Tmax, Tmin)                │
│   ea = actual vapor pressure (from humidity or Tmin)              │
│   u₂ = wind speed at 2m height                                   │
└──────────┬───────────────────────────────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────────────────────────────┐
│ STEP 8: Water Deficit Analysis                                    │
│ • ETc = ETo × Kc (crop coefficient, user-defined or default)     │
│ • Water deficit = ETc - Effective Precipitation                   │
│ • Irrigation requirement = max(0, deficit)                        │
│ • Cumulative deficit over period                                  │
└──────────┬───────────────────────────────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────────────────────────────┐
│ STEP 9: Results & Storage                                         │
│ • Store in PostgreSQL (eto_calculations table)                    │
│ • Cache in Redis (TTL based on mode)                              │
│ • Return JSON via API / WebSocket                                 │
│ • Frontend renders: tables, charts, download buttons              │
└──────────────────────────────────────────────────────────────────┘
```

---

## Climate Data Sources

### Source Specifications

| Source | Coverage | Variables | Update Freq. | Latency |
|--------|----------|-----------|-------------|---------|
| **NASA POWER** | Global | T, RH, Wind, Rs, P, Precip | Daily | ~3-7 days |
| **Open-Meteo** | Global | T, RH, Wind, Rs, P, Precip | Hourly | Real-time |
| **MET Norway** | Global (forecast) | T, RH, Wind, Precip, Pressure | 6-hourly | Real-time |
| **NWS Forecast** | US only | T, RH, Wind, Precip | 12-hourly | Real-time |
| **NWS Stations** | US only | T, RH, Wind, Precip, Pressure | Hourly | ~1 hour |

---

## ETo Calculation (FAO-56)

### Implementation (`backend/core/eto_calculator.py`)

The FAO-56 Penman-Monteith equation:

$$
ET_0 = \frac{0.408 \Delta (R_n - G) + \gamma \frac{900}{T+273} u_2 (e_s - e_a)}{\Delta + \gamma (1 + 0.34 u_2)}
$$

### Intermediate Calculations

1. **Psychrometric constant** (γ):
   $$\gamma = \frac{c_p \cdot P}{\epsilon \cdot \lambda} = 0.665 \times 10^{-3} P$$

2. **Saturation vapor pressure** (es):
   $$e_s = \frac{e°(T_{max}) + e°(T_{min})}{2}$$
   where $e°(T) = 0.6108 \exp\left[\frac{17.27T}{T+237.3}\right]$

3. **Actual vapor pressure** (ea):
   $$e_a = \frac{RH_{mean}}{100} \cdot e_s$$

4. **Slope of vapor pressure curve** (Δ):
   $$\Delta = \frac{4098 \cdot e°(T_{mean})}{(T_{mean} + 237.3)^2}$$

5. **Net radiation** (Rn):
   - Net shortwave: $R_{ns} = (1 - \alpha) R_s$ where α = 0.23
   - Net longwave: $R_{nl} = \sigma \left[\frac{T_{max,K}^4 + T_{min,K}^4}{2}\right](0.34 - 0.14\sqrt{e_a})\left(1.35\frac{R_s}{R_{so}} - 0.35\right)$
   - Net radiation: $R_n = R_{ns} - R_{nl}$

6. **Extraterrestrial radiation** (Ra):
   - Computed from latitude and day of year
   - Used for clear-sky radiation: $R_{so} = (0.75 + 2 \times 10^{-5} z) R_a$

### Wind Height Correction

Wind speed must be adjusted to 2m reference height:

$$u_2 = u_z \cdot \frac{4.87}{\ln(67.8z - 5.42)}$$

---

## WebSocket Progress System

### Architecture

```
Frontend (Dash)                    Backend (FastAPI)
     │                                    │
     │  1. POST /api/v1/eto/calculate     │
     │ ──────────────────────────────────► │
     │  ◄── { task_id: "abc-123" }        │
     │                                    │
     │  2. WS /ws/eto/abc-123             │
     │ ◄═══════════════════════════════►  │
     │                                    │
     │  3. Progress messages:             │
     │  ◄── { progress: 10, step: "Fetching NASA POWER..." }
     │  ◄── { progress: 30, step: "Fetching Open-Meteo..." }
     │  ◄── { progress: 60, step: "Applying Kalman fusion..." }
     │  ◄── { progress: 90, step: "Calculating ETo..." }
     │  ◄── { progress: 100, step: "Complete", data: {...} }
     │                                    │
     │  4. Connection closed              │
     │ ════════════════════════════════╝   │
```

### WebSocket Message Format

```json
{
    "type": "progress",
    "task_id": "abc-123",
    "progress": 60,
    "step": "Applying Kalman filter fusion...",
    "details": {
        "sources_completed": 3,
        "sources_total": 5,
        "current_source": "MET Norway"
    }
}
```

### Frontend Integration

The Dash frontend uses `DashWebSocketManager` (from `shared_utils/websocket_client.py`) to:
1. Connect to the WebSocket endpoint
2. Display progress bar with step description
3. Handle reconnection on connection loss
4. Parse final results and render charts/tables

---

## Download System

### Per-Component Downloads

Each results section generates downloads independently:

backend\api\services\data_download.py:
1. COORDINATE VALIDATION
2. DATE FORMAT VALIDATION
3. MODE DETECTION (using official module)
4. MODE AND PERIOD VALIDATION
5. INTELLIGENT SOURCE SELECTION (using ClimateSourceManager)
6. Normalize data_source input
7. Use specific method for data_download
8. Consolidate data (Kalman fusion will be done in eto_services.py)
9. If multiple sources, concatenate ALL measurements: Kalman fusion in eto_services.py will apply intelligent weights
10. Physical validation will be done in data_preprocessing.py

### Available Downloads

| Section | CSV | Excel | PNG |
|---------|-----|-------|-----|
| Daily ETo Table | ✅ | ✅ | — |
| Daily ETo Chart | — | — | ✅ |
| Monthly Summary | ✅ | ✅ | — |
| Source Comparison | ✅ | ✅ | — |
| Water Deficit Chart | — | — | ✅ |
| Full Report | — | ✅ (multi-sheet) | — |

---

### Redis Caching Strategy

| Key Pattern | TTL | Content |
|-------------|-----|---------|
| `elevation:{lat}:{lon}` | 24h | Elevation in meters |
| `climate:{source}:{lat}:{lon}:{date}` | 6h | Raw climate data |
| `eto:{lat}:{lon}:{start}:{end}:{mode}` | 1h | Calculated ETo results |
| `task:{task_id}` | 24h | Celery task status |

---

### Documentation

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/docs` | Swagger UI |
| GET | `/api/v1/openapi.json` | OpenAPI schema |

---

### Authentication

- **Grafana**: Username/password (configured in `.env`)
- **Flower**: HTTP Basic Auth (configured in `.env`)
- **API**: Currently open (designed for public use)

### Secrets Management

- All secrets in `.env` file (not committed to git)
- `.env.example` provides template with placeholder values
- Docker Compose reads secrets from `.env` at build/run time

---

## Directory Structure

```
EVAONLINE/
├── alembic/                   
│   ├── versions/               
│   └── env.py              
├── backend/                
│   ├── api/                
│   ├── core/               
│   ├── database/           
│   ├── infrastructure/         
│   └── tests/                  
├── config/                     
│   ├── settings/               
│   ├── translations/           
│   └── logging_config.py      
├── data/                      
├── database/                   
├── docker/                     
│   ├── monitoring/            
│   │   ├── prometheus.yml   
│   │   └── grafana/          
│   └── nginx/                
│       ├── nginx.conf         
│       └── ssl/               
├── docs/                      
├── frontend/                  
│   ├── callbacks/              
│   ├── components/             
│   ├── layouts/               
│   ├── pages/                 
│   └── assets/               
├── init-db/                    
├── scripts/                    
├── shared_utils/               
├── docker-compose.yml      
├── Dockerfile                  
├── pyproject.toml              
├── requirements.txt            
└── README.md                   
---

**Last updated:** 2025-02-23  
**Maintained by:** EVAonline Development Team
