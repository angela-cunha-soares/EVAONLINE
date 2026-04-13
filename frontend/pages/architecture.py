# filepath: frontend/pages/architecture.py
"""
Página Architecture do EVAonline — Documentação técnica detalhada de implementação.
Inclui: API clients, data pipeline, Kalman filters, database, Celery e endpoint WebSocket.

Suporta tradução dinâmica PT/EN via shared_utils.get_translations.
"""

import logging

import dash_bootstrap_components as dbc
from dash import html

from shared_utils.get_translations import t

logger = logging.getLogger(__name__)


# =============================================================================
# HELPER: Tradução com fallback
# =============================================================================
def _t(lang, *keys, default=""):
    """Wrapper para tradução com prefixo 'architecture' automático."""
    return t(lang, "architecture", *keys, default=default)


# =============================================================================
# HELPER: Diagrama de fluxo visual (ASCII → HTML)
# =============================================================================
def _create_flow_diagram(lang="en"):
    """Diagrama end-to-end do fluxo de dados."""
    steps = [
        ("👤", _t(lang, "flow", "step1_title", default="User clicks map"),
         _t(lang, "flow", "step1_desc", default="lat/lon → Frontend (Dash callback)"), "primary"),
        ("📡", _t(lang, "flow", "step2_title", default="POST /api/v1/internal/eto/calculate"),
         _t(lang, "flow", "step2_desc", default="FastAPI validates → Celery .delay()"), "info"),
        ("⚙️", _t(lang, "flow", "step3_title", default="Celery Worker"),
         _t(lang, "flow", "step3_desc", default="Source selection → Download → Preprocess → Fusion → ETo"), "warning"),
        ("📊", _t(lang, "flow", "step4_title", default="Kalman Filter"),
         _t(lang, "flow", "step4_desc", default="Adaptive filter on precipitation + ETo"), "success"),
        ("📈", _t(lang, "flow", "step5_title", default="Results"),
         _t(lang, "flow", "step5_desc", default="Redis task-status polling (2s) / WebSocket endpoint → Tables + Plotly charts"), "primary"),
        ("💾", _t(lang, "flow", "step6_title", default="Persistence"),
         _t(lang, "flow", "step6_desc", default="PostgreSQL (JSONB) + Redis cache"), "secondary"),
    ]

    flow_items = []
    for i, (icon, title_text, desc, color) in enumerate(steps):
        flow_items.append(
            html.Div(
                [
                    html.Div(
                        [
                            html.Div(
                                [
                                    html.Span(icon, style={"fontSize": "1.5rem"}),
                                    dbc.Badge(
                                        str(i + 1), color=color,
                                        className="ms-2",
                                        pill=True,
                                    ),
                                ],
                                className="d-flex align-items-center mb-1",
                            ),
                            html.Strong(title_text, className="d-block"),
                            html.Small(desc, className="text-muted"),
                        ],
                        className="p-3 border rounded bg-light",
                    ),
                    # Arrow between steps
                    *(
                        [html.Div(
                            html.I(className="bi bi-arrow-down fs-4 text-muted"),
                            className="text-center my-1",
                        )]
                        if i < len(steps) - 1
                        else []
                    ),
                ]
            )
        )

    return html.Div(flow_items, className="d-flex flex-column align-items-center")


# =============================================================================
# SECTION 1: API Clients
# =============================================================================
def _create_api_clients_section(lang="en"):
    """Seção com tabela detalhada dos 7 API clients."""

    # Mapeamento de tipo para chave de tradução
    type_keys = {
        "Historical": "type_historical",
        "Recent + Forecast": "type_recent_forecast",
        "Forecast": "type_forecast",
        "Forecast (USA)": "type_forecast_usa",
        "Real-time observations": "type_realtime",
        "Elevation": "type_elevation",
    }

    api_data = [
        {
            "name": "NASA POWER",
            "file": "nasa_power_client.py",
            "coverage": "Global (0.5° x 0.625°)",
            "time_range": "1990 → today - 2d",
            "type": "Historical",
            "variables": "T2M_MAX, T2M_MIN, T2M, RH2M, WS2M, ALLSKY_SFC_SW_DWN, PRECTOTCORR",
            "icon": "bi-globe-americas",
            "color": "primary",
            "key_method": "get_daily_data(lat, lon, start, end)",
        },
        {
            "name": "Open-Meteo Archive",
            "file": "openmeteo_archive_client.py",
            "coverage": "Global (0.1° x 0.1° ERA5-Land)",
            "time_range": "1990 → today - 2d",
            "type": "Historical",
            "variables": "temperature_2m_{mean,max,min}, precipitation_sum, et0_fao, shortwave_radiation, RH, wind_10m",
            "icon": "bi-cloud-sun",
            "color": "success",
            "key_method": "get_climate_data(lat, lng, start, end)",
        },
        {
            "name": "Open-Meteo Forecast",
            "file": "openmeteo_forecast_client.py",
            "coverage": "Global",
            "time_range": "today - 29d → today + 5d",
            "type": "Recent + Forecast",
            "variables": "Same 10 as Archive",
            "icon": "bi-cloud-lightning",
            "color": "info",
            "key_method": "get_climate_data(lat, lng, start, end)",
        },
        {
            "name": "MET Norway",
            "file": "met_norway_client.py",
            "coverage": "Global (9km) / Nordic (2.5km)",
            "time_range": "today → today + 5d",
            "type": "Forecast",
            "variables": "air_temperature, relative_humidity, wind_speed, precipitation_amount",
            "icon": "bi-snow2",
            "color": "info",
            "key_method": "get_forecast_data(lat, lon)",
        },
        {
            "name": "NWS Forecast",
            "file": "nws_forecast_client.py",
            "coverage": "USA Continental (24-49°N)",
            "time_range": "today → today + 5d",
            "type": "Forecast (USA)",
            "variables": "temperature, humidity, windSpeed, skyCover, precipitation, dewpoint",
            "icon": "bi-flag",
            "color": "danger",
            "key_method": "get_forecast(lat, lon)",
        },
        {
            "name": "NWS Stations",
            "file": "nws_stations_client.py",
            "coverage": "USA Continental (stations)",
            "time_range": "today - 2d → today",
            "type": "Real-time observations",
            "variables": "temperature, dewpoint, humidity, wind (10m→2m FAO-56)",
            "icon": "bi-broadcast",
            "color": "danger",
            "key_method": "_get_grid(lat, lon)",
        },
        {
            "name": "OpenTopoData",
            "file": "opentopo_client.py",
            "coverage": "Global (SRTM30m + ASTER)",
            "time_range": "Static (elevation)",
            "type": "Elevation",
            "variables": "elevation_m (for atmospheric pressure, γ)",
            "icon": "bi-triangle",
            "color": "secondary",
            "key_method": "get_elevation(lat, lon)",
        },
    ]

    rows = []
    for api in api_data:
        type_key = type_keys.get(api["type"], "type_historical")
        type_label = _t(lang, "api_clients", type_key, default=api["type"])

        rows.append(
            html.Tr(
                [
                    html.Td(
                        [
                            html.I(className=f"bi {api['icon']} me-2"),
                            html.Strong(api["name"]),
                        ]
                    ),
                    html.Td(
                        dbc.Badge(type_label, color=api["color"], pill=True)
                    ),
                    html.Td(html.Small(api["coverage"])),
                    html.Td(html.Small(api["time_range"])),
                    html.Td(
                        html.Code(api["key_method"], className="small")
                    ),
                    html.Td(
                        html.Small(
                            api["variables"],
                            className="text-muted",
                            style={"fontSize": "0.75rem"},
                        )
                    ),
                ]
            )
        )

    return dbc.Row(
        dbc.Col(
            [
                html.H2(
                    [
                        html.I(className="bi bi-cloud-download me-2"),
                        _t(lang, "api_clients", "title", default="API Clients (Climate Data Sources)"),
                    ],
                    id="api-clients",
                    className="mb-4 doc-section-title",
                ),
                dbc.Card(
                    dbc.CardBody(
                        [
                            html.P(
                                [
                                    _t(lang, "api_clients", "description_prefix", default="EVAonline integrates "),
                                    html.Strong(_t(lang, "api_clients", "description_sources", default="7 data sources (6 climate + 1 elevation)")),
                                    _t(lang, "api_clients", "description_location", default=" located in "),
                                    html.Code("backend/api/services/"),
                                    _t(lang, "api_clients", "description_suffix_each", default=". Each client has a "),
                                    html.Code("*_client.py"),
                                    _t(lang, "api_clients", "description_suffix_async", default=" (async) and a "),
                                    html.Code("*_sync_adapter.py"),
                                    _t(lang, "api_clients", "description_suffix_sync", default=" (sync wrapper for Celery)."),
                                ],
                                className="text-muted mb-3",
                            ),
                            dbc.Table(
                                [
                                    html.Thead(
                                        html.Tr(
                                            [
                                                html.Th(_t(lang, "api_clients", "th_source", default="Source")),
                                                html.Th(_t(lang, "api_clients", "th_type", default="Type")),
                                                html.Th(_t(lang, "api_clients", "th_coverage", default="Coverage")),
                                                html.Th(_t(lang, "api_clients", "th_time_range", default="Time Range")),
                                                html.Th(_t(lang, "api_clients", "th_key_method", default="Key Method")),
                                                html.Th(_t(lang, "api_clients", "th_variables", default="Variables")),
                                            ]
                                        )
                                    ),
                                    html.Tbody(rows),
                                ],
                                bordered=True,
                                hover=True,
                                responsive=True,
                                size="sm",
                                className="mb-0",
                            ),
                        ]
                    ),
                    className="mb-4 shadow-sm",
                ),
            ],
            width=12,
        )
    )


# =============================================================================
# SECTION 2: Data Processing Pipeline
# =============================================================================
def _create_pipeline_section(lang="en"):
    """Pipeline de processamento de dados."""

    pipeline_steps = [
        {
            "step_key": "step1_name",
            "step_default": "1. Orchestrator",
            "file": "data_download.py",
            "func": "download_weather_data()",
            "desc_key": "step1_desc",
            "desc_default": "Coordinate validation → Date validation → Mode detection → Source selection → Parallel fetch",
            "icon": "bi-diagram-3",
            "lines": "701 lines",
        },
        {
            "step_key": "step2_name",
            "step_default": "2. Preprocessing",
            "file": "data_preprocessing.py",
            "func": "preprocessing(weather_df, latitude, region)",
            "desc_key": "step2_desc",
            "desc_default": "Physical limits (WMO/Xavier) → IQR outlier detection (max 5%) → Linear interpolation → Fill → Mean",
            "icon": "bi-funnel",
            "lines": "635 lines",
        },
        {
            "step_key": "step3_name",
            "step_default": "3. Climate Fusion (3 modes)",
            "file": "climate_fusion.py",
            "func": "ClimateFusion.fuse_multi_source()",
            "desc_key": "step3_desc",
            "desc_default": "Historical: per-variable NASA/OM weights (validated). Recent: primary+fallback sources with HIST_WEIGHTS. Forecast: region weights (USA → NWS 50%/OM 30%/MET 20%; Nordic → MET 80%/OM 20%; Global → OM 70%/MET 30%)",
            "icon": "bi-intersect",
            "lines": "403 lines",
        },
        {
            "step_key": "step4_name",
            "step_default": "4. Kalman Filters (2-stage)",
            "file": "kalman_filters.py",
            "func": "KalmanApplier.apply_eto_filter()",
            "desc_key": "step4_desc",
            "desc_default": "Stage 1: Adaptive Kalman on precipitation (outlier detection via monthly P01/P99 percentiles, R×500 penalty). Stage 2: Final adaptive Kalman on calculated ETo (monthly bias correction + continuous filter using 1991–2020 climatology)",
            "icon": "bi-gpu-card",
            "lines": "~400 lines",
        },
        {
            "step_key": "step5_name",
            "step_default": "5. Ensemble Orchestrator",
            "file": "climate_ensemble.py",
            "func": "ClimateKalmanEnsemble.process()",
            "desc_key": "step5_desc",
            "desc_default": "Fusion (step 3) → Load 30-year monthly normals (1991-2020) → Kalman precipitation filter (step 4a) → FAO-56 ETo calculation → Kalman ETo correction (step 4b) → Set fusion_mode",
            "icon": "bi-layers",
            "lines": "55 lines",
        },
    ]

    cards = []
    for p in pipeline_steps:
        cards.append(
            dbc.Card(
                [
                    dbc.CardBody(
                        [
                            html.Div(
                                [
                                    html.I(
                                        className=f"bi {p['icon']} me-2 text-primary",
                                        style={"fontSize": "1.3rem"},
                                    ),
                                    html.Strong(_t(lang, "pipeline", p["step_key"], default=p["step_default"])),
                                    dbc.Badge(
                                        p["lines"],
                                        color="light",
                                        text_color="dark",
                                        className="ms-2",
                                    ),
                                ],
                                className="mb-2",
                            ),
                            html.Div(
                                [
                                    html.Code(
                                        p["file"],
                                        className="me-2 text-info",
                                    ),
                                    html.Code(
                                        p["func"],
                                        className="text-success",
                                        style={"fontSize": "0.8rem"},
                                    ),
                                ],
                                className="mb-2",
                            ),
                            html.P(
                                _t(lang, "pipeline", p["desc_key"], default=p["desc_default"]),
                                className="small text-muted mb-0",
                            ),
                        ]
                    )
                ],
                className="mb-2 border-start border-primary border-3",
            )
        )

    return dbc.Row(
        dbc.Col(
            [
                html.H2(
                    [
                        html.I(className="bi bi-gear me-2"),
                        _t(lang, "pipeline", "title", default="Data Processing Pipeline"),
                    ],
                    id="pipeline",
                    className="mb-4 doc-section-title",
                ),
                dbc.Card(
                    dbc.CardBody(
                        [
                            html.P(
                                [
                                    _t(lang, "pipeline", "description_prefix", default="All processing modules reside in "),
                                    html.Code("backend/core/data_processing/"),
                                    _t(lang, "pipeline", "description_suffix", default=". The pipeline is executed by Celery workers asynchronously."),
                                ],
                                className="text-muted mb-3",
                            ),
                            *cards,
                        ]
                    ),
                    className="mb-4 shadow-sm",
                ),
            ],
            width=12,
        )
    )


# =============================================================================
# SECTION 3: ETo Calculation (FAO-56)
# =============================================================================
def _create_eto_calculation_section(lang="en"):
    """Detalhes do cálculo FAO-56 Penman-Monteith."""
    return dbc.Row(
        dbc.Col(
            [
                html.H2(
                    [
                        html.I(className="bi bi-calculator me-2"),
                        _t(lang, "eto_calc", "title", default="ETo Calculation (FAO-56 Penman-Monteith)"),
                    ],
                    id="eto-calc",
                    className="mb-4 doc-section-title",
                ),
                dbc.Card(
                    dbc.CardBody(
                        [
                            # Two services
                            dbc.Row(
                                [
                                    dbc.Col(
                                        dbc.Card(
                                            dbc.CardBody(
                                                [
                                                    html.H5(
                                                        [
                                                            html.I(className="bi bi-calculator me-2 text-primary"),
                                                            _t(lang, "eto_calc", "service1_name", default="EToCalculationService"),
                                                        ],
                                                        className="mb-3",
                                                    ),
                                                    html.P(
                                                        [
                                                            html.Code("eto_services.py"),
                                                            _t(lang, "eto_calc", "service1_desc", default=" — Pure FAO-56 PM calculation"),
                                                        ],
                                                        className="small text-muted",
                                                    ),
                                                    html.H6(
                                                        _t(lang, "eto_calc", "required_inputs", default="Required Inputs:"),
                                                        className="mt-3 mb-2",
                                                    ),
                                                    html.Ul(
                                                        [
                                                            html.Li(html.Code("T2M_MAX, T2M_MIN, T2M (°C)")),
                                                            html.Li(html.Code("RH2M (%)")),
                                                            html.Li(html.Code("WS2M (m/s at 2m)")),
                                                            html.Li(html.Code("ALLSKY_SFC_SW_DWN (MJ/m²/day)")),
                                                            html.Li(html.Code("latitude, longitude, date, elevation_m")),
                                                        ],
                                                        className="small",
                                                    ),
                                                    html.H6(
                                                        _t(lang, "eto_calc", "internal_calcs", default="Internal Calculations:"),
                                                        className="mt-3 mb-2",
                                                    ),
                                                    html.Ul(
                                                        [
                                                            html.Li(_t(lang, "eto_calc", "calc_es", default="Saturation vapor pressure (eₛ) — Tetens formula")),
                                                            html.Li(_t(lang, "eto_calc", "calc_ea", default="Actual vapor pressure (eₐ) from RH")),
                                                            html.Li(_t(lang, "eto_calc", "calc_vpd", default="VPD = eₛ − eₐ")),
                                                            html.Li(_t(lang, "eto_calc", "calc_slope", default="Slope of vapor pressure curve (Δ)")),
                                                            html.Li(_t(lang, "eto_calc", "calc_gamma", default="Psychrometric constant (γ) from elevation")),
                                                            html.Li(_t(lang, "eto_calc", "calc_ra", default="Extraterrestrial radiation (Rₐ)")),
                                                            html.Li(_t(lang, "eto_calc", "calc_rn", default="Net radiation (Rₙ)")),
                                                        ],
                                                        className="small",
                                                    ),
                                                ]
                                            ),
                                            className="h-100",
                                        ),
                                        md=6,
                                    ),
                                    dbc.Col(
                                        dbc.Card(
                                            dbc.CardBody(
                                                [
                                                    html.H5(
                                                        [
                                                            html.I(className="bi bi-diagram-3 me-2 text-success"),
                                                            _t(lang, "eto_calc", "service2_name", default="EToProcessingService"),
                                                        ],
                                                        className="mb-3",
                                                    ),
                                                    html.P(
                                                        [
                                                            html.Code("eto_services.py"),
                                                            _t(lang, "eto_calc", "service2_desc", default=" — Full processing orchestrator"),
                                                        ],
                                                        className="small text-muted",
                                                    ),
                                                    html.H6(
                                                        _t(lang, "eto_calc", "full_pipeline", default="Full Pipeline:"),
                                                        className="mt-3 mb-2",
                                                    ),
                                                    html.Ol(
                                                        [
                                                            html.Li(_t(lang, "eto_calc", "pipe1", default="Get elevation (OpenTopo API or user)")),
                                                            html.Li(_t(lang, "eto_calc", "pipe2", default="Download weather (multi-source)")),
                                                            html.Li(_t(lang, "eto_calc", "pipe3", default="Preprocess (validate + outliers + impute)")),
                                                            html.Li(_t(lang, "eto_calc", "pipe4", default="Kalman fusion (if enabled)")),
                                                            html.Li(_t(lang, "eto_calc", "pipe5", default="Calculate raw ETo per row")),
                                                            html.Li(_t(lang, "eto_calc", "pipe6", default="Apply Kalman on ETo & precipitation")),
                                                            html.Li(_t(lang, "eto_calc", "pipe7", default="Filter to requested period")),
                                                            html.Li(_t(lang, "eto_calc", "pipe8", default="Build final response")),
                                                        ],
                                                        className="small",
                                                    ),
                                                    html.H6(
                                                        _t(lang, "eto_calc", "output_title", default="Output:"),
                                                        className="mt-3 mb-2",
                                                    ),
                                                    html.Ul(
                                                        [
                                                            html.Li(_t(lang, "eto_calc", "out1", default="et0_series (daily records)")),
                                                            html.Li(_t(lang, "eto_calc", "out2", default="summary (total/mean/max/min)")),
                                                            html.Li(_t(lang, "eto_calc", "out3", default="recommendations (irrigation)")),
                                                            html.Li(_t(lang, "eto_calc", "out4", default="fusion_mode, elevation, warnings")),
                                                        ],
                                                        className="small",
                                                    ),
                                                ]
                                            ),
                                            className="h-100",
                                        ),
                                        md=6,
                                    ),
                                ]
                            ),
                            # Equation
                            dbc.Alert(
                                [
                                    html.H6(
                                        _t(lang, "eto_calc", "equation_label", default="FAO-56 Penman-Monteith Equation:"),
                                        className="mb-2 text-dark fw-semibold",
                                    ),
                                    html.Div(
                                        "ET₀ = [0.408·Δ·(Rₙ − G) + γ·(900/(T+273))·u₂·(eₛ − eₐ)] / [Δ + γ·(1 + 0.34·u₂)]",
                                        className="font-monospace text-center",
                                        style={"fontSize": "1rem", "letterSpacing": "0.5px"},
                                    ),
                                ],
                                color="light",
                                className="mt-3 border",
                            ),
                        ]
                    ),
                    className="mb-4 shadow-sm",
                ),
            ],
            width=12,
        )
    )


# =============================================================================
# SECTION 4: API Endpoints
# =============================================================================
def _create_api_endpoints_section(lang="en"):
    """Tabela de endpoints da API REST."""

    endpoints = [
        ("GET", "/health", "desc_health", "Basic status + version", "Health"),
        ("GET", "/health/detailed", "desc_health_detailed", "PostgreSQL + Redis + Celery health", "Health"),
        ("GET", "/ready", "desc_ready", "Docker readiness probe", "Health"),
        ("POST", "/internal/eto/calculate", "desc_eto_calc", "Async ETo calculation → task_id + status metadata (includes websocket_url)", "ETo"),
        ("POST", "/internal/eto/location-info", "desc_eto_location", "Timezone + elevation for coordinates", "ETo"),
        ("GET", "/climate/sources/available", "desc_climate_sources", "Available sources (optional ?lat=&lon=)", "Climate"),
        ("POST", "/visitors/increment", "desc_visitors_inc", "Increment visitor counter", "Visitors"),
        ("GET", "/visitors/stats", "desc_visitors_stats", "Real-time stats (Redis)", "Visitors"),
    ]

    rows = []
    method_colors = {"GET": "success", "POST": "primary", "WS": "warning"}
    for method, path, desc_key, desc_default, group in endpoints:
        rows.append(
            html.Tr(
                [
                    html.Td(
                        dbc.Badge(method, color=method_colors.get(method, "secondary"))
                    ),
                    html.Td(html.Code(f"/api/v1{path}", className="small")),
                    html.Td(html.Small(
                        _t(lang, "endpoints", desc_key, default=desc_default),
                        className="text-muted",
                    )),
                    html.Td(
                        dbc.Badge(group, color="light", text_color="dark", pill=True)
                    ),
                ]
            )
        )

    return dbc.Row(
        dbc.Col(
            [
                html.H2(
                    [
                        html.I(className="bi bi-hdd-network me-2"),
                        _t(lang, "endpoints", "title", default="API Endpoints"),
                    ],
                    id="api-endpoints",
                    className="mb-4 doc-section-title",
                ),
                dbc.Card(
                    dbc.CardBody(
                        [
                            html.P(
                                [
                                    _t(lang, "endpoints", "description_prefix", default="All API routes are prefixed with "),
                                    html.Code("/api/v1"),
                                    _t(lang, "endpoints", "description_middle", default=" and documented at "),
                                    html.Code("/api/v1/docs"),
                                    _t(lang, "endpoints", "description_suffix", default=" (Swagger UI)."),
                                ],
                                className="text-muted mb-3",
                            ),
                            dbc.Table(
                                [
                                    html.Thead(
                                        html.Tr(
                                            [
                                                html.Th(_t(lang, "endpoints", "th_method", default="Method")),
                                                html.Th(_t(lang, "endpoints", "th_endpoint", default="Endpoint")),
                                                html.Th(_t(lang, "endpoints", "th_description", default="Description")),
                                                html.Th(_t(lang, "endpoints", "th_group", default="Group")),
                                            ]
                                        )
                                    ),
                                    html.Tbody(rows),
                                ],
                                bordered=True,
                                hover=True,
                                responsive=True,
                                size="sm",
                            ),
                        ]
                    ),
                    className="mb-4 shadow-sm",
                ),
            ],
            width=12,
        )
    )


# =============================================================================
# SECTION 5: Database Models
# =============================================================================
def _create_database_section(lang="en"):
    """Modelos do banco de dados."""

    models = [
        {
            "table": "climate_data",
            "model": "ClimateData",
            "key_cols": "source_api, lat, lon, elevation, timezone, date, raw_data (JSONB), harmonized_data (JSONB), eto_mm_day, quality_flags (JSONB)",
            "strategy_key": "strategy_climate",
            "strategy_default": "JSONB storage for flexible multi-source data in single table",
        },
        {
            "table": "api_variables",
            "model": "APIVariables",
            "key_cols": "source_api, variable_name, standard_name, unit, is_required_for_eto",
            "strategy_key": "strategy_api_vars",
            "strategy_default": "Maps each API's variable names to standardized internal names",
        },
        {
            "table": "visitors",
            "model": "Visitor",
            "key_cols": "visitor_id (UUID), session_id, ip_address, first_visit, last_visit, visit_count, country, device_type",
            "strategy_key": "strategy_visitors",
            "strategy_default": "Session-based deduplication with geo enrichment",
        },
        {
            "table": "user_session_cache",
            "model": "UserSessionCache",
            "key_cols": "session_id (UUID), user_agent, created_at, last_access, cache_size_mb",
            "strategy_key": "strategy_cache",
            "strategy_default": "Per-session cache tracking",
        },
        {
            "table": "admin_users",
            "model": "AdminUser",
            "key_cols": "username, email, password_hash (bcrypt), role (SUPER_ADMIN/ADMIN/DEVELOPER), api_token",
            "strategy_key": "strategy_admin",
            "strategy_default": "Role-based access control",
        },
    ]

    rows = []
    for m in models:
        rows.append(
            html.Tr(
                [
                    html.Td(html.Code(m["table"])),
                    html.Td(html.Code(m["model"], className="text-primary")),
                    html.Td(html.Small(m["key_cols"], style={"fontSize": "0.75rem"})),
                    html.Td(html.Small(
                        _t(lang, "database", m["strategy_key"], default=m["strategy_default"]),
                        className="text-muted",
                    )),
                ]
            )
        )

    return dbc.Row(
        dbc.Col(
            [
                html.H2(
                    [
                        html.I(className="bi bi-database me-2"),
                        _t(lang, "database", "title", default="Database Models (PostgreSQL)"),
                    ],
                    id="database",
                    className="mb-4 doc-section-title",
                ),
                dbc.Card(
                    dbc.CardBody(
                        [
                            html.P(
                                _t(lang, "database", "description", default="5 tables managed via SQLAlchemy + Alembic migrations. Connection pooling: 20 pool, 30 overflow, 3600s recycle."),
                                className="text-muted mb-3",
                            ),
                            dbc.Table(
                                [
                                    html.Thead(
                                        html.Tr(
                                            [
                                                html.Th(_t(lang, "database", "th_table", default="Table")),
                                                html.Th(_t(lang, "database", "th_model", default="Model")),
                                                html.Th(_t(lang, "database", "th_key_columns", default="Key Columns")),
                                                html.Th(_t(lang, "database", "th_strategy", default="Strategy")),
                                            ]
                                        )
                                    ),
                                    html.Tbody(rows),
                                ],
                                bordered=True,
                                hover=True,
                                responsive=True,
                                size="sm",
                            ),
                        ]
                    ),
                    className="mb-4 shadow-sm",
                ),
            ],
            width=12,
        )
    )


# =============================================================================
# SECTION 6: Celery Workers & Tasks
# =============================================================================
def _create_celery_section(lang="en"):
    """Celery workers e tasks."""

    task_steps = [
        ("0%", "step0", "Send initial email (if historical_email mode)", "secondary"),
        ("5%", "step1", "Validate coordinates, dates; auto-detect mode", "info"),
        ("10%", "step2", "Select best sources via ClimateSourceManager", "info"),
        ("20%", "step3", "Process via EToProcessingService.process_location()", "primary"),
        ("60–90%", "step4", "FAO-56 Penman-Monteith + Kalman fusion", "warning"),
        ("95%", "step5", "Generate output file (CSV/Excel); email if applicable", "success"),
        ("100%", "step6", "Return result dict to Redis backend", "success"),
    ]

    timeline = []
    for pct, key, default_desc, color in task_steps:
        timeline.append(
            html.Div(
                [
                    dbc.Badge(pct, color=color, className="me-2", style={"minWidth": "60px"}),
                    html.Small(_t(lang, "celery", key, default=default_desc)),
                ],
                className="d-flex align-items-center mb-2",
            )
        )

    return dbc.Row(
        dbc.Col(
            [
                html.H2(
                    [
                        html.I(className="bi bi-cpu me-2"),
                        _t(lang, "celery", "title", default="Celery Workers & Async Tasks"),
                    ],
                    id="celery",
                    className="mb-4 doc-section-title",
                ),
                dbc.Card(
                    dbc.CardBody(
                        [
                            html.P(
                                [
                                    _t(lang, "celery", "description_broker", default="Broker: "),
                                    html.Code("Redis"),
                                    _t(lang, "celery", "description_backend", default=" | Backend: "),
                                    html.Code("Redis"),
                                    _t(lang, "celery", "description_base", default=" | Base class: "),
                                    html.Code("MonitoredProgressTask"),
                                    _t(lang, "celery", "description_suffix", default=" (supports Redis pub/sub for WebSocket and Redis result backend consumed by frontend polling)."),
                                ],
                                className="text-muted mb-3",
                            ),
                            dbc.Row(
                                [
                                    # Tasks table
                                    dbc.Col(
                                        [
                                            html.H5(
                                                _t(lang, "celery", "registered_tasks", default="Registered Tasks"),
                                                className="mb-3",
                                            ),
                                            dbc.Table(
                                                [
                                                    html.Thead(
                                                        html.Tr(
                                                            [
                                                                html.Th(_t(lang, "celery", "th_task", default="Task")),
                                                                html.Th(_t(lang, "celery", "th_trigger", default="Trigger")),
                                                                html.Th(_t(lang, "celery", "th_purpose", default="Purpose")),
                                                            ]
                                                        )
                                                    ),
                                                    html.Tbody(
                                                        [
                                                            html.Tr(
                                                                [
                                                                    html.Td(html.Code("calculate_eto_task")),
                                                                    html.Td(html.Small(
                                                                        _t(lang, "celery", "task1_trigger", default="POST /eto/calculate")
                                                                    )),
                                                                    html.Td(html.Small(
                                                                        _t(lang, "celery", "task1_purpose", default="Full ETo pipeline + CSV/Excel + email")
                                                                    )),
                                                                ]
                                                            ),
                                                            html.Tr(
                                                                [
                                                                    html.Td(html.Code("process_historical_download")),
                                                                    html.Td(html.Small(
                                                                        _t(lang, "celery", "task2_trigger", default="Legacy/auxiliary historical batch flow")
                                                                    )),
                                                                    html.Td(html.Small(
                                                                        _t(lang, "celery", "task2_purpose", default="Download → ETo → email attachment")
                                                                    )),
                                                                ]
                                                            ),
                                                            html.Tr(
                                                                [
                                                                    html.Td(html.Code("sync_visitor_data")),
                                                                    html.Td(html.Small(
                                                                        _t(lang, "celery", "task3_trigger", default="Celery Beat (30 min)")
                                                                    )),
                                                                    html.Td(html.Small(
                                                                        _t(lang, "celery", "task3_purpose", default="Redis → PostgreSQL sync")
                                                                    )),
                                                                ]
                                                            ),
                                                        ]
                                                    ),
                                                ],
                                                bordered=True,
                                                hover=True,
                                                size="sm",
                                            ),
                                        ],
                                        md=7,
                                    ),
                                    # Task progress timeline
                                    dbc.Col(
                                        [
                                            html.H5(
                                                _t(lang, "celery", "task_flow_title", default="calculate_eto_task Flow"),
                                                className="mb-3",
                                            ),
                                            html.Div(timeline),
                                            html.Small(
                                                _t(lang, "celery", "auto_retries", default="Auto-retries: calculate_eto_task up to 2× (network/API errors); historical batch task up to 3×"),
                                                className="text-muted mt-2 d-block",
                                            ),
                                        ],
                                        md=5,
                                    ),
                                ]
                            ),
                        ]
                    ),
                    className="mb-4 shadow-sm",
                ),
            ],
            width=12,
        )
    )


# =============================================================================
# SECTION 7: WebSocket Real-time Communication
# =============================================================================
def _create_websocket_section(lang="en"):
    """WebSocket para comunicação em tempo real."""
    return dbc.Row(
        dbc.Col(
            [
                html.H2(
                    [
                        html.I(className="bi bi-broadcast-pin me-2"),
                            _t(lang, "websocket", "title", default="WebSocket Endpoint (Available Channel)"),
                    ],
                    id="websocket",
                    className="mb-4 doc-section-title",
                ),
                dbc.Card(
                    dbc.CardBody(
                        [
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [
                                            html.H5(
                                                [
                                                    html.I(className="bi bi-server me-2"),
                                                    _t(lang, "websocket", "server_side", default="Server-side"),
                                                ],
                                                className="mb-3",
                                            ),
                                            html.Ul(
                                                [
                                                    html.Li(
                                                        [
                                                            html.Strong(_t(lang, "websocket", "endpoint_label", default="Endpoint: ")),
                                                            html.Code("ws://host/ws/task_status/{task_id}"),
                                                        ]
                                                    ),
                                                    html.Li(
                                                        [
                                                            html.Strong(_t(lang, "websocket", "file_label", default="File: ")),
                                                            html.Code("websocket_service.py"),
                                                        ]
                                                    ),
                                                    html.Li(_t(lang, "websocket", "server_connect", default="Client connects with Celery task_id")),
                                                    html.Li(_t(lang, "websocket", "server_subscribe", default="Server subscribes to Redis pub/sub channel")),
                                                    html.Li(_t(lang, "websocket", "server_coroutines", default="Two coroutines: Redis listener + Celery poller")),
                                                    html.Li(_t(lang, "websocket", "server_timeout", default="Auto-timeout: 30 minutes")),
                                                ],
                                                className="small",
                                            ),
                                        ],
                                        md=6,
                                    ),
                                    dbc.Col(
                                        [
                                            html.H5(
                                                [
                                                    html.I(className="bi bi-laptop me-2"),
                                                    _t(lang, "websocket", "client_side", default="Client-side"),
                                                ],
                                                className="mb-3",
                                            ),
                                            html.Ul(
                                                [
                                                    html.Li(
                                                        [
                                                            html.Strong(_t(lang, "websocket", "file_label", default="File: ")),
                                                            html.Code("websocket_client.py"),
                                                        ]
                                                    ),
                                                    html.Li(_t(lang, "websocket", "client_current", default="Current frontend path uses dcc.Interval polling of Redis task metadata every 2s (eto_callbacks.py)")),
                                                    html.Li(
                                                        [
                                                            html.Strong(_t(lang, "websocket", "message_type_label", default="MessageType: ")),
                                                            html.Code("PROGRESS | SUCCESS | ERROR | TIMEOUT"),
                                                        ]
                                                    ),
                                                    html.Li(_t(lang, "websocket", "client_reconnect", default="WebSocket client module supports auto-reconnection with exponential backoff")),
                                                    html.Li(_t(lang, "websocket", "client_callbacks", default="WebSocket module exposes callbacks: on_progress, on_success, on_error")),
                                                ],
                                                className="small",
                                            ),
                                            html.H6(
                                                _t(lang, "websocket", "message_format", default="Message Format:"),
                                                className="mt-3 mb-2",
                                            ),
                                            html.Pre(
                                                '{\n  "status": "PROGRESS",\n  "info": {"progress": 50,\n           "message": "Kalman Fusion..."},\n  "timestamp": "2025-01-01T12:00:00"\n}',
                                                className="bg-dark text-light p-3 rounded small",
                                            ),
                                        ],
                                        md=6,
                                    ),
                                ]
                            ),
                        ]
                    ),
                    className="mb-4 shadow-sm",
                ),
            ],
            width=12,
        )
    )


# =============================================================================
# SECTION 8: End-to-End Flow Diagram
# =============================================================================
def _create_e2e_flow_section(lang="en"):
    """Diagrama visual end-to-end."""
    return dbc.Row(
        dbc.Col(
            [
                html.H2(
                    [
                        html.I(className="bi bi-arrow-repeat me-2"),
                        _t(lang, "flow", "title", default="End-to-End Data Flow"),
                    ],
                    id="e2e-flow",
                    className="mb-4 doc-section-title",
                ),
                dbc.Card(
                    dbc.CardBody(
                        [
                            _create_flow_diagram(lang),
                            html.Hr(),
                            dbc.Alert(
                                [
                                    html.I(className="bi bi-info-circle me-2"),
                                    html.Strong(_t(lang, "flow", "architecture_label", default="Architecture: ")),
                                    _t(lang, "flow", "architecture_desc", default="Clean Hexagonal DDD (Clean + Hexagonal + Domain-Driven Design). Layers: Presentation (Dash) → Application (FastAPI) → Domain (ETo, Kalman) → Infrastructure (APIs, DB, Redis, Celery)."),
                                ],
                                color="info",
                                className="mb-0 mt-3",
                            ),
                        ]
                    ),
                    className="mb-4 shadow-sm",
                ),
            ],
            width=12,
        )
    )


# =============================================================================
# SECTION 9: Tech Stack
# =============================================================================
def _create_tech_stack_section(lang="en"):
    """Stack tecnológica completa."""
    categories = [
        {
            "title_key": "frontend",
            "title_default": "🎨 Frontend",
            "color": "primary",
            "items": [
                ("Dash", "dash_desc", "Interactive dashboards"),
                ("Dash Bootstrap", "dash_bootstrap_desc", "Responsive UI"),
                ("dash-leaflet", "dash_leaflet_desc", "Interactive maps + GeoJSON"),
                ("Plotly", "plotly_desc", "Statistical charts"),
            ],
        },
        {
            "title_key": "backend",
            "title_default": "🚀 Backend",
            "color": "success",
            "items": [
                ("FastAPI", "fastapi_desc", "REST API + WebSocket"),
                ("Celery", "celery_desc", "Async task processing"),
                ("Redis", "redis_desc", "Cache + message broker"),
                ("SQLAlchemy", "sqlalchemy_desc", "ORM + Alembic migrations"),
            ],
        },
        {
            "title_key": "database_cat",
            "title_default": "💾 Database",
            "color": "warning",
            "items": [
                ("PostgreSQL", "postgresql_desc", "Primary database"),
                ("Redis", "redis_session_desc", "Session + queue + pub/sub"),
                ("JSONB", "jsonb_desc", "Flexible climate data storage"),
            ],
        },
        {
            "title_key": "infrastructure",
            "title_default": "🐳 Infrastructure",
            "color": "danger",
            "items": [
                ("Docker", "docker_desc", "Multi-stage containerization"),
                ("Nginx", "nginx_desc", "Reverse proxy + gzip"),
                ("Prometheus", "prometheus_desc", "Metrics collection"),
                ("Loguru", "loguru_desc", "Structured logging"),
            ],
        },
    ]

    cols = []
    for cat in categories:
        items = [
            html.Div(
                [
                    html.I(className="bi bi-check-circle-fill text-success me-2"),
                    html.Strong(name),
                    html.Small(
                        f" — {_t(lang, 'tech_stack', desc_key, default=desc_default)}",
                        className="text-muted",
                    ),
                ],
                className="mb-2",
            )
            for name, desc_key, desc_default in cat["items"]
        ]
        cols.append(
            dbc.Col(
                dbc.Card(
                    [
                        dbc.CardHeader(
                            html.Strong(_t(lang, "tech_stack", cat["title_key"], default=cat["title_default"])),
                            className=f"bg-{cat['color']} text-white",
                        ),
                        dbc.CardBody(items),
                    ],
                    className="h-100",
                ),
                md=3,
                className="mb-3",
            )
        )

    return dbc.Row(
        dbc.Col(
            [
                html.H2(
                    [
                        html.I(className="bi bi-stack me-2"),
                        _t(lang, "tech_stack", "title", default="Technology Stack"),
                    ],
                    id="tech-stack",
                    className="mb-4 doc-section-title",
                ),
                dbc.Row(cols),
            ],
            width=12,
        )
    )


# =============================================================================
# SECTION 10: Validation & Scientific Methodology
# =============================================================================
def _create_validation_section(lang="en"):
    """Seção detalhada da validação científica e metodologia de fusão."""

    # --- Fusion weights table ---
    fusion_weights = [
        ("T2M_MAX", "Max temperature", "0.58", "0.42"),
        ("T2M_MIN", "Min temperature", "0.52", "0.48"),
        ("T2M", "Mean temperature", "0.60", "0.40"),
        ("RH2M", "Relative humidity", "0.35", "0.65"),
        ("WS2M", "Wind speed at 2m", "0.20", "0.80"),
        ("ALLSKY_SFC_SW_DWN", "Solar radiation", "0.92", "0.08"),
        ("PRECTOTCORR", "Precipitation", "0.50", "0.50"),
    ]

    weights_rows = []
    for var, desc_default, w_nasa, w_om in fusion_weights:
        weights_rows.append(
            html.Tr([
                html.Td(html.Code(var)),
                html.Td(html.Small(
                    _t(lang, "validation", f"var_{var}", default=desc_default)
                )),
                html.Td(html.Strong(w_nasa, className="text-primary")),
                html.Td(html.Strong(w_om, className="text-success")),
            ])
        )

    # --- Validation results table ---
    results_data = [
        ("NASA POWER (FAO-56)", "0.740", "0.411", "-0.363", "0.845", "1.117", "+15.78"),
        ("Open-Meteo Archive (ERA5-Land)", "0.636", "0.432", "-0.547", "0.859", "1.097", "+13.02"),
        ("Open-Meteo API (ERA5)", "0.649", "0.584", "0.216", "0.690", "0.860", "+8.27"),
    ]
    fusion_result = ("EVAonline Fusion", "0.694", "0.814", "0.676", "0.423", "0.566", "+0.71")

    results_rows = []
    for name, r2, kge, nse, mae, rmse, pbias in results_data:
        results_rows.append(
            html.Tr([
                html.Td(name),
                html.Td(r2), html.Td(kge), html.Td(nse),
                html.Td(mae), html.Td(rmse), html.Td(pbias),
            ])
        )
    # Fusion row (bold)
    fn, fr2, fkge, fnse, fmae, frmse, fpbias = fusion_result
    results_rows.append(
        html.Tr([
            html.Td(html.Strong(fn, className="text-success")),
            html.Td(html.Strong(fr2)),
            html.Td(html.Strong(fkge, className="text-success")),
            html.Td(html.Strong(fnse)),
            html.Td(html.Strong(fmae)),
            html.Td(html.Strong(frmse)),
            html.Td(html.Strong(fpbias, className="text-success")),
        ], className="table-success")
    )

    # --- Pipeline steps (validation methodology) ---
    pipeline_steps = [
        ("1", "bi-download", "val_step1", "Data Acquisition",
         "val_step1_desc",
         "Download raw data from NASA POWER (7 variables at 2m) and Open-Meteo Archive (7 variables, wind at 10m). Period: 1991-2020, 17 MATOPIBA cities + Piracicaba/SP."),
        ("2", "bi-funnel", "val_step2", "Preprocessing & QC",
         "val_step2_desc",
         "Apply physical limits (Xavier et al., 2016). IQR outlier detection (max 5%). Linear interpolation for gaps. Wind conversion: Open-Meteo 10m \u2192 2m via FAO-56 Eq. 47."),
        ("3", "bi-intersect", "val_step3", "Weighted Fusion",
         "val_step3_desc",
         "Per-variable weighted average: each variable has a NASA weight and an Open-Meteo weight (see table). Precipitation: simple average (0.50/0.50) + Adaptive Kalman filter for outlier detection."),
        ("4", "bi-calculator", "val_step4", "FAO-56 Penman-Monteith",
         "val_step4_desc",
         "Complete FAO-56 PM calculation on the fused data: saturation/actual vapor pressure, extraterrestrial radiation (Eqs. 21-25), net radiation, psychrometric constant with altitude correction."),
        ("5", "bi-gpu-card", "val_step5", "Final Kalman ETo Correction",
         "val_step5_desc",
         "3-step adaptive Kalman on calculated ETo: (a) monthly bias correction using 30-year climatology, (b) continuous Kalman filter (no monthly reset) with dynamic P01/P99 bounds, (c) anomaly detection."),
        ("6", "bi-clipboard-check", "val_step6", "Validation vs Xavier BR-DWGD",
         "val_step6_desc",
         "Compare EVAonline ETo against Xavier et al. (2022) gridded reference dataset (gold standard for Brazil). Calculate R\u00b2, KGE, NSE, MAE, RMSE, PBIAS across all 17 sites."),
    ]

    step_items = []
    for num, icon, key, default_title, desc_key, desc_default in pipeline_steps:
        step_items.append(
            html.Div([
                html.Div([
                    dbc.Badge(num, color="primary", pill=True, className="me-2",
                              style={"minWidth": "28px", "fontSize": "0.85rem"}),
                    html.I(className=f"bi {icon} me-2 text-primary",
                           style={"fontSize": "1.1rem"}),
                    html.Strong(
                        _t(lang, "validation", key, default=default_title),
                    ),
                ], className="d-flex align-items-center mb-1"),
                html.P(
                    _t(lang, "validation", desc_key, default=desc_default),
                    className="small text-muted mb-0 ms-5",
                ),
            ], className="mb-3 p-2 border-start border-primary border-2 bg-light rounded")
        )

    return dbc.Row(
        dbc.Col([
            html.H2([
                html.I(className="bi bi-check2-square me-2"),
                _t(lang, "validation", "title",
                   default="Validation & Scientific Methodology"),
            ], id="validation", className="mb-4 doc-section-title"),

            # --- Card 1: Overview ---
            dbc.Card(dbc.CardBody([
                html.H5([
                    html.I(className="bi bi-info-circle me-2 text-info"),
                    _t(lang, "validation", "overview_title",
                       default="Overview"),
                ], className="mb-3"),
                html.P(
                    _t(lang, "validation", "overview_text",
                       default="EVAonline was validated against the Brazilian Daily Weather Gridded Data (BR-DWGD) by Xavier et al. (2016, 2022), the gold-standard reference ETo dataset for Brazil. The validation covers 17 sites (16 in the MATOPIBA agricultural frontier + Piracicaba/SP), 30 years of daily data (1991-2020, 10,958 days per site), and compares 4 ETo estimation methods against the BR-DWGD reference."),
                    className="text-muted",
                ),
                dbc.Alert([
                    html.I(className="bi bi-trophy me-2"),
                    html.Strong(
                        _t(lang, "validation", "highlight_label",
                           default="Key result: ")),
                    _t(lang, "validation", "highlight_text",
                       default="EVAonline Fusion achieved KGE = 0.814, reducing RMSE by 49% vs NASA POWER and by 34% vs the best single source (Open-Meteo API)."),
                ], color="success", className="mb-0"),
            ]), className="mb-3 shadow-sm"),

            # --- Card 2: Step-by-step Pipeline ---
            dbc.Card(dbc.CardBody([
                html.H5([
                    html.I(className="bi bi-list-ol me-2 text-primary"),
                    _t(lang, "validation", "pipeline_title",
                       default="Validation Pipeline (Step by Step)"),
                ], className="mb-3"),
                html.Div(step_items),
            ]), className="mb-3 shadow-sm"),

            # --- Card 3: Fusion Weights ---
            dbc.Card(dbc.CardBody([
                html.H5([
                    html.I(className="bi bi-sliders me-2 text-warning"),
                    _t(lang, "validation", "weights_title",
                       default="Historical Fusion Weights (Validated)"),
                ], className="mb-3"),
                html.P(
                    _t(lang, "validation", "weights_desc",
                       default="In historical mode, each meteorological variable is fused as a weighted average of NASA POWER and Open-Meteo Archive. These weights were optimized to minimize error against Xavier BR-DWGD and are identical in both the validation scripts and the production backend."),
                    className="small text-muted mb-3",
                ),
                dbc.Table([
                    html.Thead(html.Tr([
                        html.Th(_t(lang, "validation", "th_variable", default="Variable")),
                        html.Th(_t(lang, "validation", "th_description", default="Description")),
                        html.Th(
                            _t(lang, "validation", "th_nasa_weight", default="NASA Weight"),
                            className="text-center",
                        ),
                        html.Th(
                            _t(lang, "validation", "th_om_weight", default="Open-Meteo Weight"),
                            className="text-center",
                        ),
                    ])),
                    html.Tbody(weights_rows),
                ], bordered=True, hover=True, responsive=True, size="sm"),
                html.Small(
                    _t(lang, "validation", "weights_note",
                       default="Precipitation uses simple average (0.50/0.50) followed by Adaptive Kalman filter for outlier detection using monthly percentile bounds."),
                    className="text-muted fst-italic",
                ),
            ]), className="mb-3 shadow-sm"),

            # --- Card 4: Validation Results ---
            dbc.Card(dbc.CardBody([
                html.H5([
                    html.I(className="bi bi-bar-chart me-2 text-success"),
                    _t(lang, "validation", "results_title",
                       default="Validation Results (17 sites, 1991-2020)"),
                ], className="mb-3"),
                html.P(
                    _t(lang, "validation", "results_desc",
                       default="Mean metrics across 17 sites comparing 4 ETo estimation methods against Xavier BR-DWGD reference:"),
                    className="small text-muted mb-3",
                ),
                dbc.Table([
                    html.Thead(html.Tr([
                        html.Th(
                            _t(lang, "validation", "th_method", default="Method")),
                        html.Th("R\u00b2"), html.Th("KGE"), html.Th("NSE"),
                        html.Th("MAE (mm/d)"), html.Th("RMSE (mm/d)"),
                        html.Th("PBIAS (%)"),
                    ])),
                    html.Tbody(results_rows),
                ], bordered=True, hover=True, responsive=True, size="sm",
                   className="mb-3"),
                # Improvement callout
                dbc.Alert([
                    html.Strong(
                        _t(lang, "validation", "improvement_label",
                           default="Improvement vs best individual source (Open-Meteo API):")),
                    html.Br(),
                    html.Small(
                        _t(lang, "validation", "improvement_text",
                           default="\u0394KGE: +39% | \u0394MAE: -39% | \u0394RMSE: -34% | \u0394PBIAS: -91.5%")),
                ], color="info", className="mb-0 py-2"),
            ]), className="mb-3 shadow-sm"),

            # --- Card 5: Three Operational Modes ---
            dbc.Card(dbc.CardBody([
                html.H5([
                    html.I(className="bi bi-toggles me-2 text-info"),
                    _t(lang, "validation", "modes_title",
                       default="Three Operational Modes"),
                ], className="mb-3"),
                dbc.Row([
                    dbc.Col(dbc.Card([
                        dbc.CardHeader(
                            html.Strong(
                                _t(lang, "validation", "mode_hist_title",
                                   default="Historical")),
                            className="bg-primary text-white py-2",
                        ),
                        dbc.CardBody([
                            html.Small(
                                _t(lang, "validation", "mode_hist_sources",
                                   default="Sources: NASA POWER + Open-Meteo Archive"),
                                className="d-block mb-1",
                            ),
                            html.Small(
                                _t(lang, "validation", "mode_hist_fusion",
                                   default="Fusion: Per-variable HIST_WEIGHTS (validated)"),
                                className="d-block mb-1",
                            ),
                            html.Small(
                                _t(lang, "validation", "mode_hist_period",
                                   default="Period: 1990 \u2192 today \u2212 2 days"),
                                className="d-block text-muted",
                            ),
                        ], className="py-2"),
                    ], className="h-100"), md=4, className="mb-2"),
                    dbc.Col(dbc.Card([
                        dbc.CardHeader(
                            html.Strong(
                                _t(lang, "validation", "mode_recent_title",
                                   default="Recent")),
                            className="bg-warning text-dark py-2",
                        ),
                        dbc.CardBody([
                            html.Small(
                                _t(lang, "validation", "mode_recent_sources",
                                   default="Sources: OM Forecast (primary) + fallback pair"),
                                className="d-block mb-1",
                            ),
                            html.Small(
                                _t(lang, "validation", "mode_recent_fusion",
                                   default="Fusion: HIST_WEIGHTS when both primary sources available; OM Forecast fills gaps"),
                                className="d-block mb-1",
                            ),
                            html.Small(
                                _t(lang, "validation", "mode_recent_period",
                                   default="Period: today \u2212 29 days \u2192 today"),
                                className="d-block text-muted",
                            ),
                        ], className="py-2"),
                    ], className="h-100"), md=4, className="mb-2"),
                    dbc.Col(dbc.Card([
                        dbc.CardHeader(
                            html.Strong(
                                _t(lang, "validation", "mode_forecast_title",
                                   default="Forecast")),
                            className="bg-info text-white py-2",
                        ),
                        dbc.CardBody([
                            html.Small(
                                _t(lang, "validation", "mode_forecast_sources",
                                   default="Sources: Region-dependent (OM, MET, NWS)"),
                                className="d-block mb-1",
                            ),
                            html.Small(
                                _t(lang, "validation", "mode_forecast_fusion",
                                   default="Fusion: Region weights \u2014 USA: NWS 50%/OM 30%/MET 20%; Nordic: MET 80%/OM 20%; Global: OM 70%/MET 30%"),
                                className="d-block mb-1",
                            ),
                            html.Small(
                                _t(lang, "validation", "mode_forecast_period",
                                   default="Period: today \u2192 today + 5 days"),
                                className="d-block text-muted",
                            ),
                        ], className="py-2"),
                    ], className="h-100"), md=4, className="mb-2"),
                ]),
            ]), className="mb-4 shadow-sm"),
        ], width=12)
    )


# =============================================================================
# QUICK NAV
# =============================================================================
def _create_arch_nav(lang="en"):
    """Quick navigation for architecture page."""
    nav_items = [
        ("1", "bi-arrow-repeat", _t(lang, "nav", "flow", default="Flow"), "#e2e-flow"),
        ("2", "bi-cloud-download", _t(lang, "nav", "apis", default="APIs"), "#api-clients"),
        ("3", "bi-gear", _t(lang, "nav", "pipeline", default="Pipeline"), "#pipeline"),
        ("4", "bi-calculator", _t(lang, "nav", "eto", default="ETo"), "#eto-calc"),
        ("5", "bi-check2-square", _t(lang, "nav", "validation", default="Validation"), "#validation"),
        ("6", "bi-hdd-network", _t(lang, "nav", "endpoints", default="Endpoints"), "#api-endpoints"),
        ("7", "bi-database", _t(lang, "nav", "database", default="Database"), "#database"),
        ("8", "bi-cpu", _t(lang, "nav", "celery", default="Celery"), "#celery"),
        ("9", "bi-broadcast-pin", _t(lang, "nav", "websocket", default="WebSocket"), "#websocket"),
        ("10", "bi-stack", _t(lang, "nav", "tech_stack", default="Tech Stack"), "#tech-stack"),
    ]

    links = []
    for num, icon, label, href in nav_items:
        links.append(
            html.A(
                [
                    html.Span(num, className="doc-nav-number"),
                    html.I(className=f"bi {icon} me-1"),
                    label,
                ],
                href=href,
                className="doc-nav-link",
            )
        )

    return dbc.Card(
        dbc.CardBody(
            html.Div(links, className="doc-nav-container"),
            className="py-2 px-3",
        ),
        className="mb-4 shadow-sm doc-nav-card",
    )


# =============================================================================
# MAIN LAYOUT FACTORY
# =============================================================================
def create_architecture_layout(lang="en"):
    """
    Gera o layout da página Architecture com traduções.

    Args:
        lang: Código do idioma ("en" ou "pt")

    Returns:
        html.Div: Layout completo da página
    """
    return html.Div(
        [
            dbc.Container(
                [
                    # Page title
                    html.Div(
                        [
                            html.H1(
                                [
                                    html.I(className="bi bi-diagram-3 me-3"),
                                    _t(lang, "page_title", default="System Architecture"),
                                ],
                                className="text-center mb-2",
                                style={"color": "#2c3e50", "fontWeight": "bold"},
                            ),
                            html.P(
                                _t(lang, "page_subtitle", default="Detailed technical implementation of EVAonline"),
                                className="text-center lead text-muted mb-4",
                            ),
                            html.Hr(className="my-4"),
                        ]
                    ),
                    # Quick navigation
                    _create_arch_nav(lang),
                    # Sections
                    _create_e2e_flow_section(lang),
                    _create_api_clients_section(lang),
                    _create_pipeline_section(lang),
                    _create_eto_calculation_section(lang),
                    _create_validation_section(lang),
                    _create_api_endpoints_section(lang),
                    _create_database_section(lang),
                    _create_celery_section(lang),
                    _create_websocket_section(lang),
                    _create_tech_stack_section(lang),
                ],
                fluid=False,
                className="py-4",
            )
        ],
        className="doc-page-container",
    )


# Layout padrão (EN) — usado como fallback e import inicial
architecture_layout = create_architecture_layout("en")

logger.info("✅ Architecture page loaded successfully")
