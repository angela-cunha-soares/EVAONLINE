"""
Callbacks para página ETo.

Integração com 6 fontes climaticas do backend:
- Open-Meteo Archive: Historico (1990 -> hoje-2d)
- Open-Meteo Forecast: Previsao/Recent (hoje-29d -> hoje+5d)
- NASA POWER: Historico global (1990 -> hoje-2d)
- MET Norway: Previsao global (hoje -> hoje+5d)
- NWS Forecast: Previsao USA (hoje -> hoje+5d)
- NWS Stations: Observacoes USA (hoje-2d -> hoje)

Validacoes (api_limits.py):
- Historico: 1990-01-01 (padrao EVA), min 1 dia e max 90 dias
- Real-time: min 7 dias e max 30 dias
- Forecast: ate +5 dias
"""

import logging
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs

import pytz

import dash_bootstrap_components as dbc
from dash import Input, Output, State, callback, dcc, html, no_update
from shared_utils.get_translations import t

logger = logging.getLogger(__name__)

# Importar OperationModeDetector
from frontend.utils.mode_detector import (
    OperationModeDetector,
    get_timezone_for_location,
    get_today_for_location,
    is_land_point,
    parse_date_from_ui,
)

# Importar helper do backend para fontes disponíveis
try:
    from backend.api.services.climate_source_selector import (
        get_available_sources_for_frontend,
    )
except ImportError:
    logger.warning(
        "⚠️ Não foi possível importar get_available_sources_for_frontend"
    )
    get_available_sources_for_frontend = None


def decimal_to_dms(decimal_coord, is_latitude=True):
    """
    Converte coordenada decimal para formato DMS (Degrees-Minutes-Seconds).

    Args:
        decimal_coord: Coordenada em decimal (-90 a 90 para lat, -180 a 180 para lon)
        is_latitude: True se for latitude, False se for longitude

    Returns:
        String formatada: "45°30'15.25"N" ou "120°15'30.50"W"
    """
    direction = ""
    if is_latitude:
        direction = "N" if decimal_coord >= 0 else "S"
    else:
        direction = "E" if decimal_coord >= 0 else "W"

    abs_coord = abs(decimal_coord)
    degrees = int(abs_coord)
    minutes = int((abs_coord - degrees) * 60)
    seconds = ((abs_coord - degrees) * 60 - minutes) * 60

    return f"{degrees}°{minutes}'{seconds:.2f}\"{direction}"


@callback(
    [
        Output("location-display", "children"),
        Output("parsed-coordinates", "data"),
    ],
    Input("navigation-coordinates", "data"),
)
def update_location_from_store(coords_data):
    """
    Atualiza exibição da localização com coordenadas do Store GLOBAL.

    Recebe: {"lat": float, "lon": float} do sessionStorage
    """
    # Log para debug
    logger.info(
        f"🔍 update_location_from_store chamado com coords_data: {coords_data}"
    )

    if not coords_data:
        logger.warning("⚠️ coords_data está vazio")
        return (
            html.Div(
                [
                    html.I(
                        className="bi bi-exclamation-circle me-2",
                        style={"color": "#856404"},
                    ),
                    html.Span(
                        "Nenhuma localização selecionada. ",
                        style={"color": "#856404"},
                    ),
                    dbc.Button(
                        [
                            html.I(className="bi bi-arrow-left me-2"),
                            "Voltar ao mapa",
                        ],
                        href="/",
                        color="warning",
                        size="sm",
                        outline=True,
                        className="ms-2",
                    ),
                ],
                className="d-flex align-items-center",
            ),
            None,
        )

    try:
        lat = coords_data.get("lat")
        lon = coords_data.get("lon")

        logger.info(f"🎯 lat={lat}, lon={lon}")

        if lat and lon:
            lat_f = float(lat)
            lon_f = float(lon)

            logger.info(f"✅ Coordenadas válidas: {lat_f}, {lon_f}")

            # Converter para DMS usando helper
            lat_dms = decimal_to_dms(lat_f, is_latitude=True)
            lon_dms = decimal_to_dms(lon_f, is_latitude=False)

            display = html.Div(
                [
                    html.Div(
                        [
                            html.I(
                                className="bi bi-geo-alt-fill me-2",
                                style={"fontSize": "1.2rem"},
                            ),
                            html.Div(
                                [
                                    html.Strong(
                                        "Coordenadas Selecionadas:",
                                        className="d-block",
                                    ),
                                    html.Span(
                                        f"Lat: {lat_dms} | Lon: {lon_dms}",
                                        className="d-block text-muted small",
                                    ),
                                    html.Span(
                                        f"Decimal: {lat_f:.6f}, {lon_f:.6f}",
                                        className="text-muted small",
                                    ),
                                ],
                                className="flex-grow-1",
                            ),
                        ],
                        className="d-flex align-items-start",
                    ),
                    dbc.Button(
                        [html.I(className="bi bi-pencil me-2"), "Alterar"],
                        href="/",
                        color="secondary",
                        size="sm",
                        outline=True,
                        className="ms-auto",
                    ),
                ],
                className="d-flex align-items-center justify-content-between w-100",
            )

            # Retornar display E coordenadas no Store
            return display, {"lat": lat_f, "lon": lon_f}
        else:
            logger.warning(
                f"⚠️ Coordenadas ausentes ou inválidas: lat={lat}, lon={lon}"
            )
            return (
                html.Div(
                    [
                        html.I(
                            className="bi bi-exclamation-circle me-2",
                            style={"color": "#856404"},
                        ),
                        html.Span(
                            "Coordenadas não encontradas na URL. ",
                            style={"color": "#856404"},
                        ),
                        dbc.Button(
                            [
                                html.I(className="bi bi-arrow-left me-2"),
                                "Voltar ao mapa",
                            ],
                            href="/",
                            color="warning",
                            size="sm",
                            outline=True,
                            className="ms-2",
                        ),
                    ],
                    className="d-flex align-items-center",
                ),
                None,
            )

    except Exception as e:
        logger.error(f"❌ Erro ao parsear URL params: {e}", exc_info=True)
        return (
            html.Div(
                [
                    html.I(
                        className="bi bi-exclamation-triangle me-2",
                        style={"color": "#721c24"},
                    ),
                    html.Span(
                        f"Erro ao processar coordenadas: {str(e)}",
                        style={"color": "#721c24"},
                    ),
                    dbc.Button(
                        [
                            html.I(className="bi bi-arrow-left me-2"),
                            "Voltar ao mapa",
                        ],
                        href="/",
                        color="danger",
                        size="sm",
                        outline=True,
                        className="ms-2",
                    ),
                ],
                className="d-flex align-items-center",
            ),
            None,
        )


@callback(
    Output("location-input-container", "children"),
    [
        Input("location-mode-radio", "value"),
        Input("url", "search"),
    ],
)
def render_location_input(mode, search):
    """
    Renderiza interface de entrada de coordenadas baseado no modo selecionado.

    - map: Exibe coordenadas recebidas via URL (ou alerta se não houver)
    - manual: Campos de entrada para lat/lon + botão validar
    """
    if mode == "map":
        # Modo mapa: mostra coordenadas da URL ou alerta
        if not search:
            return dbc.Alert(
                [
                    html.I(className="bi bi-info-circle me-2"),
                    html.Span(
                        "Clique no mapa da página inicial para selecionar uma localização."
                    ),
                ],
                color="info",
                className="mb-0",
            )

        # Parse URL params
        try:
            params = parse_qs(search.lstrip("?"))
            lat = float(params.get("lat", [None])[0])
            lon = float(params.get("lon", [None])[0])

            # Converter para DMS
            lat_dms = decimal_to_dms(lat, is_latitude=True)
            lon_dms = decimal_to_dms(lon, is_latitude=False)

            return html.Div(
                [
                    dbc.Row(
                        [
                            dbc.Col(
                                [
                                    html.Strong("Latitude:"),
                                    html.Br(),
                                    html.Span(f"{lat_dms} ({lat:.6f}°)"),
                                ],
                                width=6,
                            ),
                            dbc.Col(
                                [
                                    html.Strong("Longitude:"),
                                    html.Br(),
                                    html.Span(f"{lon_dms} ({lon:.6f}°)"),
                                ],
                                width=6,
                            ),
                        ],
                        className="mb-3",
                    ),
                    dbc.Button(
                        [
                            html.I(className="bi bi-arrow-left me-2"),
                            "Alterar no Mapa",
                        ],
                        href="/",
                        color="primary",
                        size="sm",
                        outline=True,
                    ),
                ],
            )
        except (ValueError, TypeError, KeyError):
            return dbc.Alert(
                [
                    html.I(className="bi bi-exclamation-triangle me-2"),
                    html.Span(
                        "Coordenadas inválidas. Clique no mapa para selecionar uma localização."
                    ),
                    html.Br(),
                    dbc.Button(
                        [
                            html.I(className="bi bi-arrow-left me-2"),
                            "Ir ao Mapa",
                        ],
                        href="/",
                        color="warning",
                        size="sm",
                        outline=True,
                        className="mt-2",
                    ),
                ],
                color="warning",
                className="mb-0",
            )

    else:  # mode == "manual"
        return html.Div(
            [
                dbc.Row(
                    [
                        dbc.Col(
                            [
                                dbc.Label(
                                    "Latitude (°):",
                                    html_for="manual-lat-input",
                                ),
                                dbc.Input(
                                    id="manual-lat-input",
                                    type="number",
                                    placeholder="-90.0 a 90.0",
                                    min=-90,
                                    max=90,
                                    step=0.000001,
                                    className="mb-2",
                                ),
                                html.Small(
                                    "Valores negativos = Sul",
                                    className="text-muted",
                                ),
                            ],
                            md=6,
                        ),
                        dbc.Col(
                            [
                                dbc.Label(
                                    "Longitude (°):",
                                    html_for="manual-lon-input",
                                ),
                                dbc.Input(
                                    id="manual-lon-input",
                                    type="number",
                                    placeholder="-180.0 a 180.0",
                                    min=-180,
                                    max=180,
                                    step=0.000001,
                                    className="mb-2",
                                ),
                                html.Small(
                                    "Valores negativos = Oeste",
                                    className="text-muted",
                                ),
                            ],
                            md=6,
                        ),
                    ],
                    className="mb-3",
                ),
                dbc.Button(
                    [
                        html.I(className="bi bi-check-circle me-2"),
                        "Validar Coordenadas",
                    ],
                    id="validate-coords-button",
                    color="success",
                    outline=True,
                    className="w-100",
                ),
                html.Div(id="coord-validation-feedback", className="mt-2"),
            ]
        )


@callback(
    Output("fusion-info-card", "children"),
    [
        Input("data-type-radio", "value"),
        Input("navigation-coordinates", "data"),
    ],
    State("language-store", "data"),
    prevent_initial_call=True,
)
def update_fusion_info(data_type, coords_data, lang):
    """
    Atualiza info de fusão automática baseado no modo selecionado.
    Exibe cards visuais abaixo do mapa com info de período e fontes.

    Fontes por modo:
    - historical: NASA POWER + Open-Meteo Archive
    - recent: NASA POWER + Open-Meteo Archive + Open-Meteo Forecast
    - forecast: Open-Meteo Forecast + MET Norway (+ NWS se EUA)
    """
    if not data_type:
        return None  # No card shown until user selects a data type

    if not lang:
        lang = "en"

    # Verificar se está nos EUA
    in_usa = False
    if coords_data:
        lat = coords_data.get("lat", 0)
        lon = coords_data.get("lon", 0)
        in_usa = -125 <= lon <= -65 and 25 <= lat <= 50

    # Configuração por modo — com tradução
    mode_config = {
        "historical": {
            "title": t(lang, "mode_info", "historical_title", default="Historical Data"),
            "description": t(
                lang, "mode_info", "historical_desc",
                default="ETo calculated from satellite and reanalysis data with multi-source Kalman fusion.",
            ),
            "period_icon": "bi-hourglass-split",
            "period": t(
                lang, "mode_info", "historical_period",
                default="Custom range: 1990 \u2192 yesterday (max 90 days)",
            ),
            "source_icon": "bi-broadcast-pin",
            "sources": ["NASA POWER", "Open-Meteo Archive"],
            "gradient": ("linear-gradient(135deg, #1976d2, #0d47a1)"),
            "header_icon": "bi-hourglass-split",
            "accent": "#0d47a1",
        },
        "recent": {
            "title": t(lang, "mode_info", "recent_title", default="Recent Data"),
            "description": t(
                lang, "mode_info", "recent_desc",
                default="ETo from recent observations and forecasts combined for optimal coverage.",
            ),
            "period_icon": "bi-calendar-check",
            "period": t(
                lang, "mode_info", "recent_period",
                default="Last 7, 14, 21 or 30 days (EVAonline standard)",
            ),
            "source_icon": "bi-broadcast-pin",
            "sources": [
                "NASA POWER",
                "Open-Meteo Archive",
                "Open-Meteo Forecast",
            ],
            "gradient": ("linear-gradient(135deg, #2e7d32, #1b5e20)"),
            "header_icon": "bi-clock-history",
            "accent": "#1b5e20",
        },
        "forecast": {
            "title": t(lang, "mode_info", "forecast_title", default="Forecast \u2014 5 days"),
            "description": t(
                lang, "mode_info", "forecast_desc",
                default="ETo predicted from multi-model ensemble weather forecasts.",
            ),
            "period_icon": "bi-calendar-plus",
            "period": t(
                lang, "mode_info", "forecast_period",
                default="Today \u2192 today + 5 days (fixed)",
            ),
            "source_icon": "bi-broadcast-pin",
            "sources": (
                ["Open-Meteo Forecast", "MET Norway"]
                + (["NWS (USA)"] if in_usa else [])
            ),
            "gradient": ("linear-gradient(135deg, #7b1fa2, #4a148c)"),
            "header_icon": "bi-cloud-sun-fill",
            "accent": "#4a148c",
        },
    }

    config = mode_config.get(data_type, mode_config["recent"])

    # === Card principal com gradiente ===
    main_card = html.Div(
        [
            # Título com ícone
            html.Div(
                [
                    html.I(
                        className=(f"bi {config['header_icon']} me-2"),
                        style={"fontSize": "1.3rem"},
                    ),
                    html.Strong(
                        config["title"],
                        style={"fontSize": "1.1rem"},
                    ),
                ],
                className="mb-2 d-flex align-items-center",
            ),
            # Descrição
            html.P(
                config["description"],
                className="mb-0",
                style={
                    "fontSize": "0.9rem",
                    "opacity": "0.9",
                    "lineHeight": "1.4",
                },
            ),
        ],
        style={
            "background": config["gradient"],
            "color": "white",
            "borderRadius": "10px",
            "padding": "16px 18px",
            "boxShadow": "0 3px 12px rgba(0,0,0,0.15)",
        },
    )

    # === Detalhes: período e fontes ===
    detail_row_style = {
        "display": "flex",
        "alignItems": "center",
        "gap": "8px",
    }
    detail_icon_style = {
        "fontSize": "1rem",
        "color": "#6c757d",
        "width": "18px",
        "textAlign": "center",
    }
    detail_text_style = {
        "fontSize": "1rem",
        "color": "#495057",
    }

    details = html.Div(
        [
            # Período
            html.Div(
                [
                    html.I(
                        className=(f"bi {config['period_icon']}"),
                        style=detail_icon_style,
                    ),
                    html.Span(
                        [
                            html.Span(
                                t(lang, "mode_info", "period_label", default="Period: "),
                                style={
                                    "color": "#6c757d",
                                    "fontWeight": "normal",
                                },
                            ),
                            html.Span(
                                config["period"],
                                style={"fontWeight": "500"},
                            ),
                        ],
                        style=detail_text_style,
                    ),
                ],
                style=detail_row_style,
                className="mb-1",
            ),
            # Fontes
            html.Div(
                [
                    html.I(
                        className=(f"bi {config['source_icon']}"),
                        style=detail_icon_style,
                    ),
                    html.Span(
                        [
                            html.Span(
                                t(lang, "mode_info", "sources_label", default="Sources: "),
                                style={
                                    "color": "#6c757d",
                                    "fontWeight": "normal",
                                },
                            ),
                            html.Span(
                                ", ".join(config["sources"]),
                                style={
                                    "fontWeight": "600",
                                    "color": config["accent"],
                                },
                            ),
                        ],
                        style=detail_text_style,
                    ),
                ],
                style=detail_row_style,
            ),
        ],
        style={
            "padding": "10px 6px 4px 6px",
        },
    )

    return html.Div([main_card, details])


# ============================================================================
# CALLBACKS DE COMPATIBILIDADE (mantidos para não quebrar referências)
# ============================================================================


@callback(
    [
        Output("source-selection-info", "children", allow_duplicate=True),
    ],
    Input("validate-coords-button", "n_clicks"),
    [
        State("manual-lat-input", "value"),
        State("manual-lon-input", "value"),
    ],
    prevent_initial_call=True,
)
def validate_manual_coordinates(n_clicks, lat, lon):
    """
    Valida coordenadas inseridas manualmente.
    SIMPLIFICADO: Não precisa mais popular dropdown de fontes.
    """
    if not n_clicks:
        return [""]

    # Validar entrada básica
    if lat is None or lon is None:
        return [""]

    if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
        return [""]

    return [""]  # Fusão automática, não precisa popular dropdown


@callback(
    [
        Output("source-selection-info", "children", allow_duplicate=True),
    ],
    Input("parsed-coordinates", "data"),
    prevent_initial_call="initial_duplicate",
)
def populate_sources_from_url(coords_data):
    """
    SIMPLIFICADO: Não precisa mais popular dropdown.
    Fusão é automática.
    """
    return [""]


@callback(
    Output("source-description", "children"),
    Input("data-type-radio", "value"),
)
def update_source_description(data_type):
    """
    SIMPLIFICADO: Fusão automática, não precisa descrição de fonte individual.
    """
    return ""


# ============================================================================
# CALLBACKS REMOVIDOS - Fusão Automática
# ============================================================================
# O callback filter_sources_by_mode foi REMOVIDO.
# A fusão é agora SEMPRE automática baseada no modo selecionado.
# As fontes são determinadas pelo backend em get_available_sources_by_mode()
# ============================================================================


# ============================================================================
# CALLBACK - HABILITAR BOTÃO CALCULAR
# ============================================================================
@callback(
    Output("calculate-eto-btn", "disabled", allow_duplicate=True),
    [
        Input("navigation-coordinates", "data"),
        Input("data-type-radio", "value"),
    ],
    prevent_initial_call=True,
)
def enable_calculate_button(coords_data, data_type):
    """
    Habilita o botão Calculate ETO apenas quando:
    1. Coordenadas estão selecionadas (clicou no mapa)
    2. Data Type está selecionado (historical, recent ou forecast)
    """
    has_coords = (
        coords_data is not None
        and "lat" in coords_data
        and "lon" in coords_data
    )
    has_data_type = data_type is not None and data_type in [
        "historical",
        "recent",
        "forecast",
    ]

    # Retorna True (disabled) se qualquer condição não for atendida
    # Retorna False (enabled) se ambas condições forem atendidas
    return not (has_coords and has_data_type)


# ============================================================================
# CALLBACK - NOVA CONSULTA (RESET)
# ============================================================================
@callback(
    [
        Output("eto-results-container", "children", allow_duplicate=True),
        Output("validation-alert", "children", allow_duplicate=True),
        Output("operation-mode-indicator", "children", allow_duplicate=True),
        Output("data-type-radio", "value"),
        Output("selected-location-data", "data", allow_duplicate=True),
        Output("navigation-coordinates", "data", allow_duplicate=True),
        Output("marker-layer", "children", allow_duplicate=True),
        Output("calculate-eto-btn", "disabled", allow_duplicate=True),
        Output("selected-coords-display", "children", allow_duplicate=True),
        Output("sidebar-location-display", "children", allow_duplicate=True),
        Output("calculation-success-status", "children", allow_duplicate=True),
        Output("fusion-info-card", "children", allow_duplicate=True),
    ],
    [
        Input("btn-new-query", "n_clicks"),
        Input("btn-new-query-sidebar", "n_clicks"),
    ],
    State("language-store", "data"),
    prevent_initial_call=True,
)
def reset_for_new_query(n_clicks_main, n_clicks_sidebar, lang):
    """
    Reseta a interface para uma nova consulta quando o usuário
    clica em 'Nova Consulta' ou 'Selecionar Outro Ponto'.
    """
    from dash.exceptions import PreventUpdate

    # Check if any button was actually clicked
    if not n_clicks_main and not n_clicks_sidebar:
        raise PreventUpdate

    if not lang:
        lang = "en"

    click_map_text = t(lang, "sidebar", "click_map", default="Click on the map to select a point")

    # Default message for sidebar location
    default_sidebar_location = dbc.Alert(
        [
            html.I(className="bi bi-hand-index-thumb me-2"),
            click_map_text,
        ],
        color="secondary",
        className="mb-0 small py-2",
    )

    # Default message for coords display
    default_coords_display = html.Div(
        click_map_text,
        className="alert alert-info small",
    )

    # Return empty/reset values
    return (
        None,  # Clear results container
        None,  # Clear validation alert
        None,  # Clear mode indicator
        None,  # Reset data-type-radio to no selection
        None,  # Clear selected-location-data
        None,  # Clear navigation-coordinates
        [],  # Clear marker-layer
        True,  # Disable calculate button
        default_coords_display,  # Reset coords display
        default_sidebar_location,  # Reset sidebar location
        None,  # Clear calculation success status
        None,  # Clear fusion info card
    )


@callback(
    Output("conditional-form", "children"),
    Input("data-type-radio", "value"),
    State("language-store", "data"),
)
def render_conditional_form(data_type, lang):
    """
    Renderiza formulário condicional baseado no tipo de dados.

    - Histórico: date range (1990 → ontem)
    - Atual: últimos N dias (1-7)
    """
    if not lang:
        lang = "en"

    if data_type == "historical":
        # Date format depends on language
        date_format = "MM/DD/YYYY" if lang == "en" else "DD/MM/YYYY"
 
        return html.Div(
            [
                html.Label(
                    t(lang, "form", "analysis_period", default="Analysis Period:"),
                    className="fw-bold mb-3",
                    style={"fontSize": "1.1rem"},
                ),
                # Data Inicial
                html.Div(
                    [
                        html.Label(
                            t(lang, "form", "start_date_label", default="Start Date (MM/DD/YYYY):"),
                            className="mb-2",
                        ),
                        dcc.DatePickerSingle(
                            id="start-date-historical",
                            min_date_allowed=datetime(1990, 1, 1),
                            max_date_allowed=datetime.now()
                            - timedelta(days=1),
                            initial_visible_month=datetime.now()
                            - timedelta(days=30),
                            date=None,
                            display_format=date_format,
                            placeholder=t(lang, "form", "date_placeholder", default="MM/DD/YYYY"),
                            className="w-100",
                        ),
                    ],
                    className="mb-3",
                ),
                # Data Final
                html.Div(
                    [
                        html.Label(
                            t(lang, "form", "end_date_label", default="End Date (MM/DD/YYYY):"),
                            className="mb-2",
                        ),
                        dcc.DatePickerSingle(
                            id="end-date-historical",
                            min_date_allowed=datetime(1990, 1, 1),
                            max_date_allowed=datetime.now()
                            - timedelta(days=1),
                            initial_visible_month=datetime.now(),
                            date=None,
                            display_format=date_format,
                            placeholder=t(lang, "form", "date_placeholder", default="MM/DD/YYYY"),
                            className="w-100",
                        ),
                    ],
                    className="mb-3",
                ),
                # MANDATORY Email field for historical data
                html.Div(
                    [
                        html.Label(
                            [
                                t(lang, "form", "email_label", default="E-mail"),
                                " ",
                                html.Span("*", style={"color": "red"}),
                            ],
                            className="mb-2 fw-bold",
                        ),
                        dbc.Input(
                            id="email-historical",
                            type="email",
                            placeholder=t(lang, "form", "email_placeholder", default="your.email@example.com"),
                            className="w-100",
                            required=True,
                        ),
                        dbc.FormFeedback(
                            t(lang, "form", "email_invalid", default="Please enter a valid e-mail"),
                            type="invalid",
                        ),
                        html.Small(
                            t(lang, "form", "email_required", default="Required for report delivery"),
                            className="text-info d-block mt-1",
                        ),
                    ],
                    className="mb-3",
                ),
                # File format selection
                html.Div(
                    [
                        html.Label(
                            t(lang, "form", "file_format", default="File format"),
                            className="mb-2 fw-bold",
                        ),
                        dbc.RadioItems(
                            id="file-format-historical",
                            options=[
                                {
                                    "label": " Excel (.xlsx)",
                                    "value": "excel",
                                },
                                {
                                    "label": " CSV (.csv)",
                                    "value": "csv",
                                },
                            ],
                            value=None,
                            inline=False,
                            className="mb-2",
                        ),
                        html.Small(
                            t(lang, "form", "format_email_desc", default="Format of data sent by email"),
                            className="text-muted d-block",
                        ),
                    ],
                    className="mb-3",
                ),
                html.Small(
                    t(lang, "form", "historical_range", default="Historical data: 01/01/1990 to yesterday"),
                    className="text-muted d-block",
                ),
                html.Small(
                    t(lang, "form", "historical_limit", default="Limit: 90 days per request"),
                    className="text-warning d-block",
                ),
                # Hidden field for callback compatibility
                dbc.Input(
                    id="days-current",
                    value="7",
                    type="hidden",
                    style={"display": "none"},
                ),
            ]
        )

    # ========================================================================
    # MODO 2: RECENT
    # ========================================================================
    elif data_type == "recent":
        return html.Div(
            [
                html.Label(
                    t(lang, "form", "analysis_period", default="Analysis Period:"),
                    className="fw-bold mb-3",
                    style={"fontSize": "1.1rem"},
                ),
                dbc.Row(
                    [
                        dbc.Col(
                            [
                                # html.Label("Últimos dias:", className="mb-2"),
                                dbc.Select(
                                    id="days-current",
                                    options=[
                                        {
                                            "label": t(lang, "form", "last_7_days", default="Last 7 days"),
                                            "value": "7",
                                        },
                                        {
                                            "label": t(lang, "form", "last_14_days", default="Last 14 days"),
                                            "value": "14",
                                        },
                                        {
                                            "label": t(lang, "form", "last_21_days", default="Last 21 days"),
                                            "value": "21",
                                        },
                                        {
                                            "label": t(lang, "form", "last_30_days", default="Last 30 days"),
                                            "value": "30",
                                        },
                                    ],
                                    value=None,
                                    placeholder=t(lang, "form", "select_period", default="Select period"),
                                    className="w-100",
                                ),
                            ],
                            md=6,
                        ),
                    ],
                    className="mb-3",
                ),
                html.Div(id="recent-period-feedback"),
                # Hidden fields for callback compatibility
                dbc.Input(
                    id="start-date-historical",
                    type="hidden",
                    style={"display": "none"},
                ),
                dbc.Input(
                    id="end-date-historical",
                    type="hidden",
                    style={"display": "none"},
                ),
                dbc.Input(
                    id="email-historical",
                    type="hidden",
                    style={"display": "none"},
                ),
                dbc.Input(
                    id="file-format-historical",
                    value="excel",
                    type="hidden",
                    style={"display": "none"},
                ),
            ]
        )

    # ========================================================================
    # MODO 3: FORECAST
    # ========================================================================
    else:  # forecast
        return html.Div(
            [
                # Hidden fields for callback compatibility
                dbc.Input(
                    id="days-current",
                    value="6",
                    type="hidden",
                    style={"display": "none"},
                ),
                dbc.Input(
                    id="start-date-historical",
                    type="hidden",
                    style={"display": "none"},
                ),
                dbc.Input(
                    id="end-date-historical",
                    type="hidden",
                    style={"display": "none"},
                ),
                dbc.Input(
                    id="email-historical",
                    type="hidden",
                    style={"display": "none"},
                ),
                dbc.Input(
                    id="file-format-historical",
                    value="csv",
                    type="hidden",
                    style={"display": "none"},
                ),
            ]
        )


@callback(
    [
        Output("eto-results-container", "children"),
        Output("operation-mode-indicator", "children"),
        Output("validation-alert", "children"),
        Output("current-task-id", "data"),
        Output("progress-interval", "disabled"),
        Output("current-operation-mode", "data"),
        Output("eto-progress-container", "children", allow_duplicate=True),
    ],
    Input("calculate-eto-btn", "n_clicks"),
    [
        State("navigation-coordinates", "data"),
        State("data-type-radio", "value"),
        State("start-date-historical", "date"),
        State("end-date-historical", "date"),
        State("email-historical", "value"),
        State("file-format-historical", "value"),
        State("days-current", "value"),
        State("app-session-id", "data"),
        State("manual-elevation", "data"),
        State("language-store", "data"),
    ],
    prevent_initial_call=True,
)
def calculate_eto(
    n_clicks,
    coords_data,
    data_type,
    start_date_hist,
    end_date_hist,
    email_hist,
    file_format_hist,
    days_current,
    session_id,
    manual_elevation=None,
    lang=None,
):
    """
    Calcula ETo com detecção automática de modo operacional.

    Usa OperationModeDetector para validar e preparar requisição.

    Mapeamento UI → Backend:
    - "historical" → HISTORICAL_EMAIL (1-90 days, requires email)
    - "recent" → DASHBOARD_CURRENT (7/14/21/30 days)
    - "forecast" → DASHBOARD_FORECAST (6 days fixed)

    Args:
        session_id: ID único da sessão do usuário (gerado automaticamente)

    Returns:
        Tuple (results_container, mode_indicator, validation_alert)
    """
    import uuid

    logger.info("🧮 calculate_eto callback triggered")

    # Default language
    if not lang:
        lang = "en"

    if n_clicks is None or n_clicks == 0:
        logger.warning("⚠️ Aborting - n_clicks empty or zero")
        return None, None, None, None, True, None, None

    # Garantir session_id único para esta sessão
    if not session_id:
        session_id = f"sess_{uuid.uuid4().hex}"
        logger.info(f"🆕 Nova sessão gerada: {session_id}")
    else:
        logger.info(f"🔑 Sessão existente: {session_id}")

    logger.info("✅ Proceeding with validation...")

    # ========================================================================
    # 1. VALIDATE COORDINATES (from Store)
    # ========================================================================
    if not coords_data:
        logger.error("❌ coords_data empty")
        error_alert = dbc.Alert(
            [
                html.I(className="bi bi-exclamation-triangle me-2"),
                html.Strong(t(lang, "validation", "error_label", default="Error: ")),
                t(lang, "validation", "coords_not_found", default="Coordinates not found."),
            ],
            color="danger",
        )
        return None, None, error_alert, None, True, None, None

    try:
        lat = float(coords_data.get("lat"))
        lon = float(coords_data.get("lon"))

        if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
            logger.error(f"❌ Invalid coords: lat={lat}, lon={lon}")
            error_alert = dbc.Alert(
                [
                    html.I(className="bi bi-exclamation-triangle me-2"),
                    html.Strong(t(lang, "validation", "error_label", default="Error: ")),
                    t(lang, "validation", "invalid_coords", default="Invalid coordinates."),
                ],
                color="danger",
            )
            return None, None, error_alert, None, True, None, None

    except (ValueError, TypeError, KeyError) as e:
        logger.error(f"❌ Error parsing coordinates: {e}")
        error_alert = dbc.Alert(
            [
                html.I(className="bi bi-exclamation-triangle me-2"),
                html.Strong(t(lang, "validation", "error_label", default="Error: ")),
                t(lang, "validation", "coords_parse_error", default="Failed to process coordinates."),
            ],
            color="danger",
        )
        return None, None, error_alert, None, True, None, None

    # Pre-check: Is this a land point?
    if not is_land_point(lat, lon):
        logger.warning(f"🌊 Ocean point detected: ({lat}, {lon})")
        error_alert = dbc.Alert(
            [
                html.I(
                    className="bi bi-water me-2",
                    style={"fontSize": "1.3rem"},
                ),
                html.Strong(t(lang, "validation", "ocean_point_title", default="Point over the ocean")),
                html.Br(),
                html.Span(
                    [
                        "As coordenadas selecionadas (",
                        html.Code(f"{lat:.4f}°, {lon:.4f}°"),
                        ") ", t(lang, "results", "over_ocean", default="are over the ocean or water body."), " ",
                        t(lang, "results", "eto_land_only", default="Evapotranspiration (ETo) is calculated only for"), " ",
                        html.Strong(t(lang, "results", "land_areas", default="land areas")),
                        ".",
                    ]
                ),
                html.Br(),
                html.Small(
                    t(lang, "results", "ocean_click_tip", default="Tip: Click on a point over land on the map."),
                    className="text-muted mt-1 d-block",
                ),
            ],
            color="info",
            className="mt-2",
        )
        return None, None, error_alert, None, True, None, None

    # ========================================================================
    # 2. DETECT OPERATION MODE & VALIDATE
    # ========================================================================
    try:
        # UI selection agora vem diretamente do data_type radio
        ui_selection = data_type  # "historical", "recent", ou "forecast"
        logger.info(f"🎯 UI Selection: {ui_selection}")

        # Validate data_type is selected
        if not ui_selection:
            error_alert = dbc.Alert(
                [
                    html.I(className="bi bi-hand-index me-2"),
                    html.Strong(t(lang, "validation", "data_type_not_selected", default="Data type not selected: ")),
                    t(lang, "validation", "data_type_not_selected_desc", default="Select Historical, Recent or Forecast before calculating."),
                ],
                color="warning",
            )
            return None, None, error_alert, None, True, None, None

        # Parse dates
        start_date = None
        end_date = None
        period_days = None

        if ui_selection == "historical":
            # Validate email for historical mode
            if not email_hist or "@" not in email_hist:
                error_alert = dbc.Alert(
                    [
                        html.I(className="bi bi-exclamation-triangle me-2"),
                        html.Strong(t(lang, "validation", "error_label", default="Error: ")),
                        t(lang, "validation", "email_required", default="Valid e-mail required for historical data."),
                    ],
                    color="warning",
                )
                return None, None, error_alert, None, True, None, None

            # Parse historical dates
            start_date = parse_date_from_ui(start_date_hist)
            end_date = parse_date_from_ui(end_date_hist)
            logger.info(f"📅 Historical: {start_date} → {end_date}")

            # Validar datas (DatePickerSingle retorna None para datas fora do range)
            if not start_date or not end_date:
                error_alert = dbc.Alert(
                    [
                        html.I(className="bi bi-calendar-x me-2"),
                        html.Strong(t(lang, "validation", "select_dates_title", default="Select dates: ")),
                        html.Br(),
                        t(lang, "validation", "select_dates_desc", default="Please select the "),
                        html.Strong(t(lang, "validation", "select_dates_start", default="Start Date")),
                        " ",
                        t(lang, "validation", "select_dates_end", default="End Date") if lang == "en" else "",
                        " " if lang == "en" else " e a ",
                        html.Strong(t(lang, "validation", "select_dates_end", default="End Date")) if lang == "en" else html.Strong(t(lang, "validation", "select_dates_end", default="Data Final")),
                        t(lang, "validation", "select_dates_for_hist", default=" for historical mode. "),
                        html.Br(),
                        html.Small(
                            t(lang, "validation", "select_dates_range", default="Valid dates: between 01/01/1990 and yesterday."),
                            className="mt-1 d-block",
                        ),
                    ],
                    color="warning",
                )
                return None, None, error_alert, None, True, None, None

            # Validar formato de arquivo
            if not file_format_hist:
                error_alert = dbc.Alert(
                    [
                        html.I(className="bi bi-file-earmark-x me-2"),
                        html.Strong(t(lang, "validation", "format_required_title", default="Format required: ")),
                        t(lang, "validation", "format_required_desc", default="Please select the file format (Excel or CSV)."),
                    ],
                    color="warning",
                )
                return None, None, error_alert, None, True, None, None

            # Validar que data inicial não é maior que data final
            if start_date > end_date:
                error_alert = dbc.Alert(
                    [
                        html.I(className="bi bi-calendar-x me-2"),
                        html.Strong(t(lang, "validation", "period_error_title", default="Period error: ")),
                        t(lang, "validation", "period_error_desc", default="The start date cannot be after the end date. "),
                        t(lang, "validation", "period_error_selected", default=f"You selected: {start_date} to {end_date}.").format(start=start_date, end=end_date) if "{start}" in t(lang, "validation", "period_error_selected", default="") else f"{start_date} → {end_date}.",
                    ],
                    color="danger",
                )
                return None, None, error_alert, None, True, None, None

            # Validar que datas não são anteriores a 1990
            from datetime import date as dt_date

            min_date = dt_date(1990, 1, 1)
            today = dt_date.today()

            if start_date < min_date or end_date < min_date:
                invalid_date = (
                    start_date if start_date < min_date else end_date
                )
                error_alert = dbc.Alert(
                    [
                        html.I(className="bi bi-database-x me-2"),
                        html.Strong(t(lang, "validation", "period_unavailable_title", default="Period not available: ")),
                        html.Br(),
                        t(lang, "validation", "period_unavailable_desc", default="EVAonline historical data is available from "),
                        html.Strong("01/01/1990"),
                        t(lang, "validation", "period_unavailable_before", default=f". The selected date ({invalid_date.strftime('%d/%m/%Y')}) is before this limit.").format(date=invalid_date.strftime('%d/%m/%Y')),
                        html.Br(),
                        html.Small(
                            t(lang, "validation", "period_unavailable_tip", default="Adjust the dates to the range: 01/01/1990 to yesterday."),
                            className="text-muted mt-1 d-block",
                        ),
                    ],
                    color="warning",
                )
                return None, None, error_alert, None, True, None, None

            # Validar que datas não são futuras
            if start_date > today or end_date > today:
                error_alert = dbc.Alert(
                    [
                        html.I(className="bi bi-calendar-x me-2"),
                        html.Strong(t(lang, "validation", "future_date_title", default="Future date not allowed: ")),
                        html.Br(),
                        t(lang, "validation", "future_date_desc", default="Historical mode works with past data. "),
                        t(lang, "validation", "future_date_max", default=f"The maximum allowed date is yesterday ({(today - dt_date.resolution).strftime('%d/%m/%Y')}).").format(date=(today - dt_date.resolution).strftime('%d/%m/%Y')),
                    ],
                    color="warning",
                )
                return None, None, error_alert, None, True, None, None

            # Validar que período não excede 90 dias
            period_days_hist = (end_date - start_date).days + 1
            if period_days_hist > 90:
                error_alert = dbc.Alert(
                    [
                        html.I(className="bi bi-exclamation-triangle me-2"),
                        html.Strong(t(lang, "validation", "period_exceeds_title", default="Period exceeds the limit: ")),
                        html.Br(),
                        t(lang, "validation", "period_exceeds_desc", default=f"You selected {period_days_hist} days ({start_date.strftime('%d/%m/%Y')} to {end_date.strftime('%d/%m/%Y')}). ").format(days=period_days_hist, start=start_date.strftime('%d/%m/%Y'), end=end_date.strftime('%d/%m/%Y')),
                        html.Br(),
                        t(lang, "validation", "period_exceeds_max", default="The maximum limit per request is "),
                        html.Strong("90 " + t(lang, "email", "days_label", default="days")),
                        t(lang, "validation", "period_exceeds_reduce", default=". Reduce the date range."),
                    ],
                    color="warning",
                )
                return None, None, error_alert, None, True, None, None

        elif ui_selection == "recent":
            # Parse period from dropdown
            if not days_current:
                error_alert = dbc.Alert(
                    [
                        html.I(className="bi bi-calendar-event me-2"),
                        html.Strong(t(lang, "validation", "period_not_selected", default="Period not selected: ")),
                        t(lang, "validation", "period_select", default="Select the period"),
                    ],
                    color="warning",
                )
                return None, None, error_alert, None, True, None, None
            period_days = int(days_current)
            logger.info(f"📅 Recent: last {period_days} days")

        else:  # forecast
            logger.info("📅 Forecast: next 6 days (fixed)")

        # Use OperationModeDetector to prepare request
        payload = OperationModeDetector.prepare_api_request(
            ui_selection=ui_selection,
            latitude=lat,
            longitude=lon,
            start_date=start_date,
            end_date=end_date,
            period_days=period_days,
            email=email_hist if ui_selection == "historical" else None,
        )

        # Adicionar formato de arquivo para modo historical
        if ui_selection == "historical" and file_format_hist:
            payload["file_format"] = file_format_hist
            logger.info(f"📎 File format: {file_format_hist}")

        # Passar elevação manual se fornecida pelo usuário
        if manual_elevation is not None:
            payload["elevation"] = float(manual_elevation)
            logger.info(f"📐 Manual elevation: {manual_elevation}m")

        # Detect mode for visual indicator
        backend_mode, mode_config = OperationModeDetector.detect_mode(
            ui_selection, start_date, end_date, period_days
        )

        logger.info(f"✅ Mode detected: {backend_mode}")
        logger.info(f"📦 Payload: {payload}")

        # Create user-friendly mode indicator card
        mode_names = {
            "historical": t(lang, "sidebar", "mode_historical", default="Historical"),
            "recent": t(lang, "sidebar", "mode_recent", default="Recent"),
            "forecast": t(lang, "sidebar", "mode_forecast", default="Forecast"),
        }
        mode_icons = {
            "historical": "bi-hourglass-split",
            "recent": "bi-clock-history",
            "forecast": "bi-cloud-sun-fill",
        }
        mode_colors = {
            "historical": "#006699",  # Blue
            "recent": "#28a745",  # Green
            "forecast": "#fd7e14",  # Orange
        }

        # Build period description
        date_to = t(lang, "results", "date_to", default="to")
        if ui_selection == "historical":
            period_text = f"{start_date.strftime('%d/%m/%Y')} {date_to} {end_date.strftime('%d/%m/%Y')}"
            period_days_calc = (end_date - start_date).days + 1
            n_days_text = t(lang, "results", "n_days", default="{n} days").replace("{n}", str(period_days_calc))
            period_extra = f"({n_days_text})"
        elif ui_selection == "recent":
            period_text = t(lang, "results", "last_n_days", default="Last {n} days").replace("{n}", str(period_days))
            period_extra = t(lang, "results", "recent_data", default="(recent data)")
        else:  # forecast
            from datetime import timedelta

            location_today = get_today_for_location(lat, lon)
            forecast_end = location_today + timedelta(days=5)
            period_text = f"{location_today.strftime('%d/%m/%Y')} {date_to} {forecast_end.strftime('%d/%m/%Y')}"
            period_extra = t(lang, "results", "forecast_days", default="(forecast 5 days)")

        # Get timezone for location
        try:
            location_tz = get_timezone_for_location(lat, lon)
            tz_name = str(location_tz)
            # Simplify timezone name for display
            if tz_name.startswith("Etc/GMT"):
                # Etc/GMT convention is inverted: Etc/GMT+9 = UTC-9
                # Convert to more intuitive display
                if "+" in tz_name:
                    offset_val = tz_name.split("+")[1]
                    tz_display = f"UTC-{offset_val}"
                elif "-" in tz_name and tz_name != "Etc/GMT":
                    offset_val = tz_name.split("-")[1]
                    tz_display = f"UTC+{offset_val}"
                else:
                    tz_display = "UTC"
            elif "/" in tz_name:
                tz_display = tz_name.split("/")[-1].replace("_", " ")
            else:
                tz_display = tz_name
        except Exception:
            tz_display = "UTC"
            tz_name = "UTC"

        mode_indicator = html.Div(
            [
                html.Div(
                    [
                        html.I(
                            className=f"bi {mode_icons.get(ui_selection, 'bi-info-circle')} me-2"
                        ),
                        html.Strong(
                            f"{t(lang, 'results', 'mode_label', default='Mode')}: {mode_names.get(ui_selection, ui_selection)}"
                        ),
                    ],
                    style={
                        "display": "flex",
                        "alignItems": "center",
                        "marginBottom": "8px",
                    },
                ),
                html.Div(
                    [
                        html.I(className="bi bi-geo-alt me-2 text-muted"),
                        html.Span(
                            f"{t(lang, 'results', 'location_label', default='Location')}: {lat:.4f}°, {lon:.4f}°",
                            className="text-muted",
                        ),
                    ],
                    style={"marginBottom": "4px", "fontSize": "0.9rem"},
                ),
                html.Div(
                    [
                        html.I(className="bi bi-clock me-2 text-muted"),
                        html.Span(
                            f"{t(lang, 'results', 'timezone_label', default='Timezone')}: {tz_display}",
                            className="text-muted",
                        ),
                        html.Small(
                            f" ({tz_name})",
                            className="text-secondary",
                            style={"fontSize": "0.95rem"},
                        ),
                    ],
                    style={"marginBottom": "4px", "fontSize": "1rem"},
                ),
                html.Div(
                    [
                        html.I(
                            className="bi bi-calendar-range me-2 text-muted"
                        ),
                        html.Span(
                            f"{t(lang, 'results', 'period_label', default='Period')}: {period_text} ", className="text-muted"
                        ),
                        html.Small(period_extra, className="text-secondary"),
                    ],
                    style={"fontSize": "0.9rem"},
                ),
            ],
            style={
                "background": f"linear-gradient(135deg, {mode_colors.get(ui_selection, '#6c757d')}15, {mode_colors.get(ui_selection, '#6c757d')}05)",
                "border": f"1px solid {mode_colors.get(ui_selection, '#6c757d')}40",
                "borderLeft": f"4px solid {mode_colors.get(ui_selection, '#6c757d')}",
                "borderRadius": "8px",
                "padding": "12px 16px",
                "marginBottom": "12px",
            },
        )

    except ValueError as e:
        logger.error(f"❌ Validation error: {e}")
        # Parse structured error codes from backend
        error_str = str(e)
        # Check for structured error codes (e.g. "END_DATE_FUTURE|...")
        if "End date must be <=" in error_str and "yesterday" in error_str:
            error_alert = dbc.Alert(
                [
                    html.I(className="bi bi-calendar-x me-2"),
                    html.Strong(t(lang, "validation", "future_date_title", default="Future date not allowed: ")),
                    html.Br(),
                    t(lang, "validation", "future_date_desc", default="Historical mode works with past data. "),
                    t(lang, "validation", "future_date_max", default="The maximum allowed date is yesterday."),
                ],
                color="warning",
            )
        elif "Period must be" in error_str:
            error_alert = dbc.Alert(
                [
                    html.I(className="bi bi-exclamation-triangle me-2"),
                    html.Strong(t(lang, "validation", "period_exceeds_title", default="Period exceeds the limit: ")),
                    html.Br(),
                    t(lang, "validation", "period_exceeds_max", default="The maximum limit per request is "),
                    html.Strong("90 " + t(lang, "email", "days_label", default="days")),
                    t(lang, "validation", "period_exceeds_reduce", default=". Reduce the date range."),
                ],
                color="warning",
            )
        else:
            error_alert = dbc.Alert(
                [
                    html.I(className="bi bi-exclamation-triangle me-2"),
                    html.Strong(t(lang, "validation", "error_label", default="Error: ")),
                    error_str,
                ],
                color="danger",
            )
        return None, None, error_alert, None, True, None, None

    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        error_alert = dbc.Alert(
            [
                html.I(className="bi bi-exclamation-octagon-fill me-2"),
                html.Strong(t(lang, "validation", "error_label", default="Error: ")),
                str(e),
            ],
            color="danger",
        )
        return None, None, error_alert, None, True, None, None

    # ========================================================================
    # 3. CALL BACKEND API
    # ========================================================================
    import requests

    try:
        logger.info("🔄 Sending request to backend...")

        # 🔀 FUSÃO AUTOMÁTICA: Não enviar "sources", backend decide automaticamente
        # O backend irá selecionar as melhores fontes baseado no period_type
        # Ver: climate_source_manager.get_available_sources_by_mode()

        # Adicionar session_id para identificação única do usuário
        payload["session_id"] = session_id
        payload["visitor_id"] = session_id  # Para compatibilidade
        payload["lang"] = lang or "en"  # Idioma para emails

        logger.info(f"📦 Final payload (auto-fusion): {payload}")

        # Make POST request
        response = requests.post(
            "http://localhost:8000/api/v1/internal/eto/calculate",
            json=payload,
            timeout=30,
        )

        # Check status
        if response.status_code == 200:
            logger.info("✅ Task submitted to backend!")
            task_response = response.json()

            # Backend retorna task_id, não resultado direto
            if task_response.get("status") == "accepted":
                task_id = task_response.get("task_id")
                logger.info(f"📋 Task ID: {task_id}")

                # Iniciar monitoramento via interval callback
                # Retornar: results=None, mode_indicator, alert=None,
                #          task_id, interval_disabled=False, operation_mode, progress_spinner
                immediate_spinner = html.Div(
                    [
                        html.Div(
                            [
                                dbc.Spinner(
                                    color="success",
                                    type="grow",
                                    size="sm",
                                    spinner_class_name="me-2",
                                ),
                                html.Span(
                                    t(lang, "progress_ui", "downloading_calculating", default="Downloading data and calculating ETo..."),
                                    className="text-success fw-semibold",
                                ),
                            ],
                            className="d-flex align-items-center",
                        ),
                    ],
                    className="p-3 bg-light rounded-3 border",
                )
                return (
                    None,
                    mode_indicator,
                    None,
                    task_id,
                    False,  # Habilitar interval
                    backend_mode,  # Salvar o modo de operação
                    immediate_spinner,  # Spinner imediato
                )

            # Se não foi aceito
            error_alert = dbc.Alert(
                [
                    html.I(className="bi bi-exclamation-triangle me-2"),
                    html.Strong("Erro: "),
                    f"Task não foi aceita: {task_response}",
                ],
                color="danger",
            )
            return None, mode_indicator, error_alert, None, True, None, None

        elif response.status_code == 429:
            # Rate limit exceeded - show friendly message
            logger.warning(f"🚫 Rate limit: {response.text[:200]}")
            try:
                detail = response.json().get("detail", "")
            except Exception:
                detail = response.text[:200]

            rate_msg = {
                "en": "Daily calculation limit reached. Please try again tomorrow.",
                "pt": "Limite diário de cálculos atingido. Tente novamente amanhã.",
            }.get(lang, detail or "Rate limit exceeded.")

            error_alert = dbc.Alert(
                [
                    html.I(className="bi bi-hourglass-split me-2"),
                    html.Strong("Limit: " if lang == "en" else "Limite: "),
                    rate_msg,
                ],
                color="warning",
            )
            return None, mode_indicator, error_alert, None, True, None, None

        else:
            logger.error(f"❌ Backend error {response.status_code}")
            error_alert = dbc.Alert(
                [
                    html.I(className="bi bi-exclamation-triangle me-2"),
                    html.Strong(f"Erro {response.status_code}: "),
                    response.text[:200],
                ],
                color="danger",
            )
            return None, mode_indicator, error_alert, None, True, None, None

    except requests.Timeout:
        logger.error("⏱️ Request timeout")
        error_alert = dbc.Alert(
            [
                html.I(className="bi bi-clock-fill me-2"),
                html.Strong("Timeout: "),
                "Backend demorou muito (>30s).",
            ],
            color="warning",
        )
        return None, mode_indicator, error_alert, None, True, None, None

    except requests.ConnectionError:
        logger.error("🔌 Connection error")
        error_alert = dbc.Alert(
            [
                html.I(className="bi bi-plug-fill me-2"),
                html.Strong("Erro de conexão: "),
                "Não foi possível conectar ao backend.",
            ],
            color="danger",
        )
        return None, mode_indicator, error_alert, None, True, None, None

    except Exception as e:
        logger.error(f"💥 Unexpected error: {str(e)}")
        error_alert = dbc.Alert(
            [
                html.I(className="bi bi-exclamation-octagon-fill me-2"),
                html.Strong("Erro inesperado: "),
                str(e),
            ],
            color="danger",
        )
        return None, mode_indicator, error_alert, None, True, None, None


@callback(
    [
        Output("eto-progress-container", "children", allow_duplicate=True),
        Output("eto-results-container", "children", allow_duplicate=True),
        Output("progress-interval", "disabled", allow_duplicate=True),
        Output("current-task-id", "data", allow_duplicate=True),
        Output("calculation-success-status", "children"),
        Output("eto-results-data", "data"),  # Store para dados de download
        Output(
            "fusion-info-card", "children", allow_duplicate=True
        ),  # Para modo histórico
    ],
    Input("progress-interval", "n_intervals"),
    [
        State("current-task-id", "data"),
        State("current-operation-mode", "data"),
        State("language-store", "data"),
    ],
    prevent_initial_call=True,
)
def update_progress(n_intervals, task_id, operation_mode, lang=None):
    """Atualiza indicador de progresso consultando status da task no Redis.

    Para modo HISTORICAL_EMAIL: Não exibe dados na interface, apenas confirmação.
    Para outros modos (DASHBOARD_CURRENT, DASHBOARD_FORECAST): Exibe dados normalmente.
    """
    if not lang:
        lang = "en"

    if not task_id:
        return None, no_update, True, None, no_update, no_update, no_update

    try:
        import redis
        import json
        import os

        # Usar variável de ambiente ou padrão para Docker
        redis_host = os.getenv("REDIS_HOST", "redis")
        redis_port = int(os.getenv("REDIS_PORT", "6379"))
        redis_password = os.getenv("REDIS_PASSWORD", None)

        r = redis.Redis(
            host=redis_host,
            port=redis_port,
            db=0,
            password=redis_password,
            decode_responses=True,
        )

        result_key = f"celery-task-meta-{task_id}"
        result_data = r.get(result_key)

        logger.info(f"🔍 Checking task {task_id}, mode: {operation_mode}")

        if not result_data:
            # Task ainda não iniciou ou não tem dados - mostrar spinner elegante
            progress_indicator = html.Div(
                [
                    html.Div(
                        [
                            dbc.Spinner(
                                color="success",
                                type="grow",
                                size="sm",
                                spinner_class_name="me-2",
                            ),
                            html.Span(
                                t(lang, "progress_ui", "downloading_calculating", default="Downloading data and calculating ETo..."),
                                className="text-success fw-semibold",
                            ),
                        ],
                        className="d-flex align-items-center",
                    ),
                ],
                className="p-3 bg-light rounded-3 border",
            )
            return (
                progress_indicator,
                no_update,
                False,
                task_id,
                no_update,
                no_update,
                no_update,  # fusion-info-card
            )

        result = json.loads(result_data)
        status = result.get("status")
        logger.info(f"📊 Task status: {status}")

        if status == "SUCCESS":
            task_result = result.get("result", {})

            # Check if task returned an error in the result
            task_error = task_result.get("error")
            if task_error:
                logger.error(
                    f"❌ Task SUCCESS mas com erro no resultado: {task_error}"
                )
                error_content = html.Div(
                    [
                        dbc.Alert(
                            [
                                html.I(
                                    className="bi bi-exclamation-triangle me-2",
                                    style={"fontSize": "1.2rem"},
                                ),
                                html.Strong("Erro ao processar dados"),
                            ],
                            color="danger",
                            className="mb-3",
                        ),
                        html.Div(
                            [
                                html.P(
                                    [
                                        html.I(
                                            className="bi bi-info-circle me-2"
                                        ),
                                        html.Small(
                                            str(task_error),
                                            className="text-muted font-monospace",
                                        ),
                                    ],
                                    className="mb-2",
                                ),
                                html.P(
                                    [
                                        html.I(
                                            className="bi bi-lightbulb me-2 text-warning"
                                        ),
                                        html.Small(
                                            "Isso pode ser um problema temporário. "
                                            "Tente novamente ou selecione outro ponto.",
                                            className="text-muted",
                                        ),
                                    ],
                                    className="mb-0",
                                ),
                            ],
                            className="px-2",
                        ),
                        html.Hr(),
                        dbc.Button(
                            [
                                html.I(className="bi bi-geo-alt me-2"),
                                t(lang, "results", "select_another", default="Select Another Point"),
                            ],
                            id="btn-new-query",
                            color="primary",
                            className="w-100",
                        ),
                    ]
                )
                sidebar_error = html.Div(
                    [
                        dbc.Alert(
                            [
                                html.I(
                                    className="bi bi-exclamation-triangle me-2"
                                ),
                                t(lang, "results", "error_processing", default="Processing error"),
                            ],
                            color="danger",
                            className="py-2 px-3 mb-2 small",
                        ),
                        dbc.Button(
                            [
                                html.I(className="bi bi-geo-alt me-2"),
                                t(lang, "results", "select_another", default="Select Another Point"),
                            ],
                            id="btn-new-query-sidebar",
                            color="primary",
                            outline=True,
                            size="sm",
                            className="w-100",
                        ),
                    ]
                )
                return (
                    None,
                    error_content,
                    True,
                    None,
                    sidebar_error,
                    None,
                    no_update,
                )

            days_calculated = len(task_result.get("et0_series", []))
            logger.info(
                f"✅ Task SUCCESS - {days_calculated} days, mode: {operation_mode}"
            )

            # ================================================================
            # MODO HISTORICAL_EMAIL: Apenas confirmação, sem exibir dados
            # ================================================================
            if operation_mode == "HISTORICAL_EMAIL":
                logger.info("📧 Modo HISTORICAL_EMAIL - exibindo confirmação")
                email_sent = task_result.get("email_sent", True)

                if email_sent:
                    proc_time = task_result.get(
                        "processing_time_seconds", "N/A"
                    )
                    success_content = html.Div(
                        [
                            # --- Header com gradiente azul acadêmico ---
                            html.Div(
                                html.Div(
                                    [
                                        html.Div(
                                            html.I(
                                                className="bi bi-envelope-check",
                                                style={"fontSize": "2rem"},
                                            ),
                                            style={
                                                "width": "56px",
                                                "height": "56px",
                                                "borderRadius": "50%",
                                                "background": "rgba(255,255,255,0.2)",
                                                "display": "flex",
                                                "alignItems": "center",
                                                "justifyContent": "center",
                                                "flexShrink": "0",
                                            },
                                        ),
                                        html.Div(
                                            [
                                                html.H5(
                                                    t(lang, "email", "sent_success", default="Data Sent by Email"),
                                                    className="mb-0 fw-bold",
                                                ),
                                                html.Small(
                                                    t(lang, "email", "sent_description", default="Historical processing completed"),
                                                    style={"opacity": "0.85"},
                                                ),
                                            ]
                                        ),
                                    ],
                                    className="d-flex align-items-center gap-3",
                                ),
                                style={
                                    "background": "linear-gradient(135deg, #006699 0%, #0088aa 100%)",
                                    "color": "white",
                                    "padding": "20px 24px",
                                    "borderRadius": "12px 12px 0 0",
                                },
                            ),
                            # --- Corpo ---
                            html.Div(
                                [
                                    # Badge de sucesso
                                    html.Div(
                                        html.Div(
                                            [
                                                html.I(
                                                    className="bi bi-check-circle-fill me-2",
                                                    style={
                                                        "fontSize": "1.1rem"
                                                    },
                                                ),
                                                html.Span(
                                                    t(lang, "email", "completed", default="Completed successfully"),
                                                    className="fw-semibold",
                                                ),
                                            ],
                                            className="d-inline-flex align-items-center",
                                            style={
                                                "background": "linear-gradient(135deg, #e8f5e9, #c8e6c9)",
                                                "color": "#2e7d32",
                                                "padding": "10px 20px",
                                                "borderRadius": "8px",
                                                "fontSize": "0.95rem",
                                            },
                                        ),
                                        className="mb-3",
                                    ),
                                    # Info items
                                    html.Div(
                                        [
                                            # Período processado
                                            html.Div(
                                                [
                                                    html.Div(
                                                        html.I(
                                                            className="bi bi-calendar-check",
                                                            style={
                                                                "fontSize": "1.2rem",
                                                                "color": "#006699",
                                                            },
                                                        ),
                                                        style={
                                                            "width": "40px",
                                                            "height": "40px",
                                                            "borderRadius": "8px",
                                                            "background": "#e8f4f8",
                                                            "display": "flex",
                                                            "alignItems": "center",
                                                            "justifyContent": "center",
                                                            "flexShrink": "0",
                                                        },
                                                    ),
                                                    html.Div(
                                                        [
                                                            html.Div(
                                                                t(lang, "email", "processed_period", default="Processed period"),
                                                                className="text-muted",
                                                                style={
                                                                    "fontSize": "1rem"
                                                                },
                                                            ),
                                                            html.Div(
                                                                f"{days_calculated} {t(lang, 'email', 'days_label', default='days')}",
                                                                className="fw-semibold",
                                                                style={
                                                                    "fontSize": "0.95rem"
                                                                },
                                                            ),
                                                        ]
                                                    ),
                                                ],
                                                className="d-flex align-items-center gap-3 mb-3",
                                            ),
                                            # Email enviado
                                            html.Div(
                                                [
                                                    html.Div(
                                                        html.I(
                                                            className="bi bi-envelope-paper",
                                                            style={
                                                                "fontSize": "1.2rem",
                                                                "color": "#006699",
                                                            },
                                                        ),
                                                        style={
                                                            "width": "40px",
                                                            "height": "40px",
                                                            "borderRadius": "8px",
                                                            "background": "#e8f4f8",
                                                            "display": "flex",
                                                            "alignItems": "center",
                                                            "justifyContent": "center",
                                                            "flexShrink": "0",
                                                        },
                                                    ),
                                                    html.Div(
                                                        [
                                                            html.Div(
                                                                t(lang, "email", "email_delivery", default="Email delivery"),
                                                                className="text-muted",
                                                                style={
                                                                    "fontSize": "1rem"
                                                                },
                                                            ),
                                                            html.Div(
                                                                t(lang, "email", "data_sent_success", default="Data sent successfully"),
                                                                className="fw-semibold",
                                                                style={
                                                                    "fontSize": "0.95rem"
                                                                },
                                                            ),
                                                        ]
                                                    ),
                                                ],
                                                className="d-flex align-items-center gap-3 mb-3",
                                            ),
                                            # Tempo de processamento
                                            html.Div(
                                                [
                                                    html.Div(
                                                        html.I(
                                                            className="bi bi-stopwatch",
                                                            style={
                                                                "fontSize": "1.2rem",
                                                                "color": "#006699",
                                                            },
                                                        ),
                                                        style={
                                                            "width": "40px",
                                                            "height": "40px",
                                                            "borderRadius": "8px",
                                                            "background": "#e8f4f8",
                                                            "display": "flex",
                                                            "alignItems": "center",
                                                            "justifyContent": "center",
                                                            "flexShrink": "0",
                                                        },
                                                    ),
                                                    html.Div(
                                                        [
                                                            html.Div(
                                                                t(lang, "email", "processing_time", default="Processing time"),
                                                                className="text-muted",
                                                                style={
                                                                    "fontSize": "1rem"
                                                                },
                                                            ),
                                                            html.Div(
                                                                f"{proc_time}s",
                                                                className="fw-semibold",
                                                                style={
                                                                    "fontSize": "0.95rem"
                                                                },
                                                            ),
                                                        ]
                                                    ),
                                                ],
                                                className="d-flex align-items-center gap-3",
                                            ),
                                        ],
                                        style={
                                            "background": "#f8f9fa",
                                            "borderRadius": "10px",
                                            "padding": "16px 20px",
                                        },
                                    ),
                                    # Aviso discreto
                                    html.Div(
                                        [
                                            html.I(
                                                className="bi bi-info-circle me-2",
                                                style={"color": "#006699"},
                                            ),
                                            html.Small(
                                                t(lang, "results", "check_inbox", default="Check your inbox and spam folder. The file is attached in the requested format."),
                                                className="text-muted",
                                            ),
                                        ],
                                        className="d-flex align-items-start mt-3",
                                        style={"fontSize": "1rem"},
                                    ),
                                    # Botão Nova Consulta
                                    html.Div(
                                        dbc.Button(
                                            [
                                                html.I(
                                                    className="bi bi-arrow-repeat me-2"
                                                ),
                                                t(lang, "results", "new_query", default="New Query"),
                                            ],
                                            id="btn-new-query",
                                            color="primary",
                                            className="w-100 mt-3",
                                        ),
                                    ),
                                ],
                                style={"padding": "20px 24px"},
                            ),
                        ],
                        style={
                            "borderRadius": "12px",
                            "border": "1px solid #e0e0e0",
                            "boxShadow": "0 4px 20px rgba(0, 0, 0, 0.08)",
                            "overflow": "hidden",
                            "marginTop": "1rem",
                            "background": "white",
                        },
                    )
                else:
                    success_content = dbc.Alert(
                        [
                            html.I(
                                className="bi bi-exclamation-triangle me-2"
                            ),
                            html.Strong(t(lang, "validation", "processing_done_email_fail", default="Processing completed, ")),
                            t(lang, "validation", "processing_done_email_fail_desc", default="but there was a problem sending the email. Check SMTP settings."),
                        ],
                        color="warning",
                        className="mt-3",
                    )

                # Success status for sidebar with New Query button
                sidebar_success = html.Div(
                    [
                        dbc.Alert(
                            [
                                html.I(
                                    className="bi bi-check-circle-fill me-2"
                                ),
                                html.Strong(
                                    f"✅ {days_calculated} {t(lang, 'results', 'days_processed', default='days processed')}"
                                ),
                            ],
                            color="success",
                            className="py-2 px-3 mb-2",
                        ),
                        dbc.Button(
                            [
                                html.I(className="bi bi-geo-alt me-2"),
                                t(lang, "results", "select_another", default="Select Another Point"),
                            ],
                            id="btn-new-query-sidebar",
                            color="primary",
                            outline=True,
                            size="sm",
                            className="w-100",
                        ),
                    ]
                )

                # Colocar resultado no fusion-info-card (coluna do mapa), não no eto-results-container
                return (
                    None,
                    None,
                    True,
                    None,
                    sidebar_success,
                    None,
                    success_content,
                )

            # ================================================================
            # OUTROS MODOS (DASHBOARD_CURRENT, DASHBOARD_FORECAST):
            # Exibir dados na interface normalmente
            # ================================================================
            logger.info(
                f"📊 Modo {operation_mode} - exibindo dados na interface"
            )

            import pandas as pd
            from backend.core.data_results.results_layout import (
                create_results_tabs,
            )

            # Convert result to DataFrame
            et0_data = task_result.get("et0_series", [])
            logger.info(f"📈 Dados recebidos: {len(et0_data)} registros")

            if not et0_data:
                error_content = html.Div(
                    [
                        dbc.Alert(
                            [
                                html.I(
                                    className="bi bi-water me-2",
                                    style={"fontSize": "1.2rem"},
                                ),
                                html.Strong(t(lang, "results", "no_data_location", default="No data for this location")),
                            ],
                            color="info",
                            className="mb-3",
                        ),
                        html.Div(
                            [
                                html.P(
                                    [
                                        html.I(
                                            className="bi bi-info-circle me-2"
                                        ),
                                        t(lang, "results", "eto_land_only", default="Evapotranspiration (ETo) is calculated only for"),
                                        " ",
                                        html.Strong(t(lang, "results", "land_areas", default="land areas")),
                                        ".",
                                    ],
                                    className="mb-2",
                                ),
                                html.P(
                                    [
                                        t(lang, "results", "possible_causes", default="Possible causes:"),
                                    ],
                                    className="mb-1 fw-semibold small",
                                ),
                                html.Ul(
                                    [
                                        html.Li(
                                            t(lang, "results", "cause_ocean", default="Point selected over ocean, lake, or water body"),
                                            className="small",
                                        ),
                                        html.Li(
                                            t(lang, "results", "cause_remote", default="Remote region without data source coverage"),
                                            className="small",
                                        ),
                                        html.Li(
                                            t(lang, "results", "cause_unavailable", default="Data source temporarily unavailable"),
                                            className="small",
                                        ),
                                    ],
                                    className="mb-3 ps-3",
                                ),
                                html.P(
                                    [
                                        html.I(
                                            className="bi bi-lightbulb me-2 text-warning"
                                        ),
                                        html.Small(
                                            t(lang, "results", "ocean_tip", default="Tip: Select a point on land to obtain ETo data."),
                                            className="text-muted",
                                        ),
                                    ],
                                    className="mb-0",
                                ),
                            ],
                            className="px-2",
                        ),
                        html.Hr(),
                        dbc.Button(
                            [
                                html.I(className="bi bi-geo-alt me-2"),
                                t(lang, "results", "select_another", default="Select Another Point"),
                            ],
                            id="btn-new-query",
                            color="primary",
                            className="w-100",
                        ),
                    ]
                )
                # Sidebar with retry button
                sidebar_error = html.Div(
                    [
                        dbc.Alert(
                            [
                                html.I(className="bi bi-water me-2"),
                                t(lang, "results", "ocean_warning", default="No data (ocean/remote area)"),
                            ],
                            color="info",
                            className="py-2 px-3 mb-2 small",
                        ),
                        dbc.Button(
                            [
                                html.I(className="bi bi-geo-alt me-2"),
                                t(lang, "results", "select_another", default="Select Another Point"),
                            ],
                            id="btn-new-query-sidebar",
                            color="primary",
                            outline=True,
                            size="sm",
                            className="w-100",
                        ),
                    ]
                )
                return (
                    None,
                    error_content,
                    True,
                    None,
                    sidebar_error,
                    None,
                    no_update,
                )

            # Create DataFrame with standardized column names
            df_records = []
            for record in et0_data:
                df_records.append(
                    {
                        "date": pd.to_datetime(record.get("date")),
                        "T2M_MAX": record.get("tmax_c", 0),
                        "T2M_MIN": record.get("tmin_c", 0),
                        "T2M": record.get("tmed_c", 0),
                        "RH2M": record.get("humidity_pct", 0),
                        "WS2M": record.get("wind_ms", 0),
                        "ALLSKY_SFC_SW_DWN": record.get("radiation_mj_m2", 0),
                        "PRECTOTCORR": record.get("precip_mm", 0),
                        "eto_evaonline": record.get("et0_mm_day", 0),
                        "eto_openmeteo": record.get(
                            "eto_openmeteo", record.get("et0_mm_day", 0)
                        ),  # Fallback se não houver
                    }
                )

            df = pd.DataFrame(df_records)

            # Get sources used
            sources_used = task_result.get("sources_used", [])

            # Create results with new tab system
            try:
                # Preparar dados para download (armazenar no Store)
                download_data = {
                    "records": et0_data,
                    "sources_used": sources_used,
                    "mode": operation_mode,
                    "days": days_calculated,
                    "lang": lang,
                }

                # Download buttons moved to individual tables
                download_buttons = None

                # 🌊 Ocean warning banner (if backend detected no elevation data)
                ocean_warning_banner = None
                if task_result.get("ocean_warning"):
                    ocean_warning_banner = dbc.Alert(
                        [
                            html.I(
                                className="bi bi-exclamation-triangle me-2",
                                style={"fontSize": "1.1rem"},
                            ),
                            html.Strong(t(lang, "results", "warning_label", default="Warning:") + " "),
                            t(lang, "results", "ocean_elevation_warning", default="The elevation service (SRTM/ASTER) did not return data for this point. It may be over a water body or uncovered area. Elevation was assumed as 0 m (sea level)."),
                        ],
                        color="warning",
                        className="mb-3",
                    )

                # 📡 Card da estação NWS (USA only)
                nws_station_card = None
                nws_station = task_result.get("nws_station")
                if nws_station:
                    obs = nws_station.get("latest_observation")
                    obs_content = []
                    if obs:
                        # Convert UTC timestamp to station local time
                        obs_ts_raw = obs.get("timestamp", "")
                        station_tz_name = nws_station.get("timezone", "")
                        obs_time_display = ""
                        obs_relative = ""
                        try:
                            # Parse ISO timestamp
                            obs_dt = datetime.fromisoformat(
                                obs_ts_raw.replace("Z", "+00:00")
                            )
                            if not obs_dt.tzinfo:
                                obs_dt = obs_dt.replace(tzinfo=timezone.utc)
                            # Convert to station local timezone
                            if station_tz_name:
                                local_tz = pytz.timezone(station_tz_name)
                                obs_local = obs_dt.astimezone(local_tz)
                                tz_abbr = obs_local.strftime("%Z")
                                obs_time_display = (
                                    f"{obs_local.strftime('%d/%m/%Y %H:%M')} "
                                    f"({tz_abbr})"
                                )
                            else:
                                obs_time_display = (
                                    obs_ts_raw[:16].replace("T", " ") + " UTC"
                                )
                            # Calculate relative time
                            now_utc = datetime.now(timezone.utc)
                            delta = now_utc - obs_dt
                            minutes_ago = int(delta.total_seconds() / 60)
                            if minutes_ago < 1:
                                obs_relative = t(lang, "nws_card", "time_now", default="now")
                            elif minutes_ago < 60:
                                obs_relative = t(lang, "nws_card", "time_minutes_ago", default="{minutes} min ago").format(minutes=minutes_ago)
                            elif minutes_ago < 1440:
                                hours = minutes_ago // 60
                                obs_relative = t(lang, "nws_card", "time_hours_ago", default="{hours}h{minutes:02d}min ago").format(hours=hours, minutes=minutes_ago % 60)
                            else:
                                days = minutes_ago // 1440
                                obs_relative = t(lang, "nws_card", "time_days_ago", default="{days} day(s) ago").format(days=days)
                        except Exception:
                            obs_time_display = (
                                obs_ts_raw[:16].replace("T", " ") + " UTC"
                            )

                        temp = obs.get("temperature_c")
                        humidity = obs.get("humidity_pct")
                        wind = obs.get("wind_speed_2m_ms") or obs.get(
                            "wind_speed_ms"
                        )

                        # Build observation time label
                        time_label = f"{t(lang, 'nws_card', 'last_reading', default='Last reading: ')}{obs_time_display}"
                        if obs_relative:
                            time_label += f" — {obs_relative}"

                        obs_content = [
                            html.Div(
                                [
                                    html.I(className="bi bi-clock me-1"),
                                    html.Small(time_label),
                                ],
                                className="mb-2 text-muted",
                                title=t(lang, "nws_card", "reading_tooltip", default="Time of the most recent sensor reading from this station. The data below corresponds to that moment."),
                            ),
                            html.Div(
                                [
                                    html.Span(
                                        [
                                            html.I(
                                                className="bi bi-thermometer-half me-1"
                                            ),
                                            f"{temp:.1f}°C" if temp else "N/A",
                                        ],
                                        className="me-3",
                                    ),
                                    html.Span(
                                        [
                                            html.I(
                                                className="bi bi-droplet me-1"
                                            ),
                                            (
                                                f"{humidity:.0f}%"
                                                if humidity
                                                else "N/A"
                                            ),
                                        ],
                                        className="me-3",
                                    ),
                                    html.Span(
                                        [
                                            html.I(
                                                className="bi bi-wind me-1"
                                            ),
                                            (
                                                f"{wind:.1f} m/s"
                                                if wind
                                                else "N/A"
                                            ),
                                        ]
                                    ),
                                ],
                                className="mb-0",
                            ),
                        ]

                    nws_station_card = dbc.Card(
                        [
                            dbc.CardHeader(
                                [
                                    html.I(
                                        className="bi bi-broadcast-pin me-2"
                                    ),
                                    html.Strong(
                                        t(lang, "nws_card", "title", default="📡 Nearest Weather Station")
                                    ),
                                    dbc.Badge(
                                        "USA",
                                        color="primary",
                                        className="ms-2",
                                    ),
                                ],
                                className="bg-info bg-opacity-10",
                            ),
                            dbc.CardBody(
                                [
                                    html.Div(
                                        [
                                            html.H5(
                                                [
                                                    html.I(
                                                        className="bi bi-building me-2"
                                                    ),
                                                    nws_station.get(
                                                        "station_name",
                                                        "Unknown",
                                                    ),
                                                    html.Small(
                                                        f" ({nws_station.get('station_id', '')})",
                                                        className="text-muted",
                                                    ),
                                                ],
                                                className="mb-3",
                                            ),
                                            html.Div(
                                                [
                                                    html.Span(
                                                        [
                                                            html.I(
                                                                className="bi bi-geo-alt me-1"
                                                            ),
                                                            html.Strong(
                                                                t(lang, "nws_card", "distance", default="Distance: ")
                                                            ),
                                                            f"{nws_station.get('distance_km', 0):.1f} km",
                                                        ],
                                                        className="me-3",
                                                        title=t(lang, "nws_card", "distance_tooltip", default="Distance between the selected point and the weather station"),
                                                    ),
                                                    html.Span(
                                                        [
                                                            html.I(
                                                                className="bi bi-arrow-up me-1"
                                                            ),
                                                            html.Strong(
                                                                t(lang, "nws_card", "elevation", default="Elevation: ")
                                                            ),
                                                            f"{nws_station.get('elevation_m', 'N/A')} m",
                                                        ]
                                                    ),
                                                ],
                                                className="mb-3",
                                            ),
                                            html.Hr(className="my-2"),
                                            (
                                                html.Div(obs_content)
                                                if obs_content
                                                else html.Em(
                                                    t(lang, "nws_card", "obs_unavailable", default="Observation not available at this time"),
                                                    className="text-muted",
                                                )
                                            ),
                                        ]
                                    ),
                                    html.Hr(className="my-3"),
                                    html.Small(
                                        [
                                            html.I(
                                                className="bi bi-info-circle me-1"
                                            ),
                                            t(lang, "nws_card", "nws_info", default="Real data from NWS/NOAA station. Official page: "),
                                            html.A(
                                                "weather.gov",
                                                href="https://www.weather.gov/",
                                                target="_blank",
                                                rel="noopener noreferrer",
                                                className="text-info",
                                            ),
                                        ],
                                        className="text-muted",
                                    ),
                                ]
                            ),
                        ],
                        className="mb-3 border-info",
                    )

                results_content = html.Div(
                    [
                        # Header with New Query button
                        html.Div(
                            [
                                dbc.Button(
                                    [
                                        html.I(
                                            className="bi bi-arrow-repeat me-2"
                                        ),
                                        t(lang, "results", "new_query", default="New Query"),
                                    ],
                                    id="btn-new-query",
                                    color="outline-primary",
                                    size="sm",
                                    className="mb-3",
                                ),
                            ],
                            className="d-flex justify-content-end",
                        ),
                        # 🌊 Ocean Warning (if elevation unavailable)
                        ocean_warning_banner,
                        # 📡 NWS Station Card (USA only)
                        nws_station_card,
                        # Tabs with results (success message moved to sidebar)
                        create_results_tabs(
                            df, sources=sources_used, lang=lang,
                            mode=operation_mode,
                        ),
                        # Download buttons
                        download_buttons,
                    ],
                    className="results-container",
                )

                # Success status for sidebar with New Query button
                sidebar_success = html.Div(
                    [
                        dbc.Alert(
                            [
                                html.I(
                                    className="bi bi-check-circle-fill me-2"
                                ),
                                html.Strong(
                                    f"✅ {t(lang, 'results', 'success_message', default='Success!')} {days_calculated} {t(lang, 'results', 'success_days', default='days calculated')}"
                                ),
                            ],
                            color="success",
                            className="py-2 px-3 mb-2",
                        ),
                        dbc.Button(
                            [
                                html.I(className="bi bi-geo-alt me-2"),
                                t(lang, "results", "select_another", default="Select Another Point"),
                            ],
                            id="btn-new-query-sidebar",
                            color="primary",
                            outline=True,
                            size="sm",
                            className="w-100",
                        ),
                    ]
                )

                # Desabilitar interval e limpar task_id
                return (
                    None,
                    results_content,
                    True,
                    None,
                    sidebar_success,
                    download_data,
                    no_update,  # fusion-info-card (não usa no modo dashboard)
                )

            except Exception as e:
                logger.error(f"Error creating results tabs: {e}")
                # Fallback to simple table
                error_card = dbc.Alert(
                    [
                        html.I(className="bi bi-exclamation-triangle me-2"),
                        f"Erro ao criar visualização: {str(e)}",
                    ],
                    color="warning",
                )
                return None, error_card, True, None, no_update, None, no_update

        elif status == "FAILURE":
            # Handle FAILURE status
            error_msg = result.get("result", "Erro desconhecido")
            warnings = []

            error_card = dbc.Card(
                [
                    dbc.CardHeader(
                        [
                            html.I(
                                className="bi bi-exclamation-triangle me-2"
                            ),
                            html.Strong("❌ Erro no cálculo"),
                        ],
                        className="bg-danger text-white",
                    ),
                    dbc.CardBody(
                        [
                            html.P(
                                [
                                    html.Strong("Erro: "),
                                    html.Span(str(error_msg)),
                                ]
                            ),
                            html.Hr() if warnings else None,
                            (
                                html.Div(
                                    [
                                        html.H6("⚠️ Avisos:"),
                                        html.Ul(
                                            [
                                                html.Li(warning)
                                                for warning in warnings[
                                                    :5
                                                ]  # Max 5 warnings
                                            ]
                                        ),
                                    ]
                                )
                                if warnings
                                else None
                            ),
                            html.Hr(),
                            html.P(
                                t(lang, "results", "please_try_again", default="Please try again or contact support."),
                                className="mb-0 text-muted",
                            ),
                        ]
                    ),
                ],
                className="mt-3",
            )
            return None, error_card, True, None, no_update, None, no_update

        elif status == "PENDING" or status == "STARTED" or status == "RETRY":
            # Task em execução ou tentando novamente
            elapsed = n_intervals * 2  # 2 segundos por intervalo

            # Timeout: se passou muito tempo em RETRY, mostrar erro
            if status == "RETRY" and elapsed > 180:
                # After 180 seconds of retrying, show error
                # (retry countdown=60*(n+1), so need time for retries to execute)
                logger.warning(
                    f"⏱️ Task em RETRY por muito tempo ({elapsed}s), abortando"
                )
                error_content = html.Div(
                    [
                        dbc.Alert(
                            [
                                html.I(
                                    className="bi bi-exclamation-triangle me-2",
                                    style={"fontSize": "1.2rem"},
                                ),
                                html.Strong(
                                    t(lang, "results", "could_not_get_data", default="Could not get data for this location")
                                ),
                            ],
                            color="warning",
                            className="mb-3",
                        ),
                        html.Div(
                            [
                                html.P(
                                    t(lang, "results", "possible_causes", default="Possible causes:"),
                                    className="mb-1 fw-semibold small",
                                ),
                                html.Ul(
                                    [
                                        html.Li(
                                            t(lang, "results", "cause_ocean", default="Point selected over ocean, lake, or water body"),
                                            className="small",
                                        ),
                                        html.Li(
                                            t(lang, "results", "cause_climate_unavailable", default="Climate data sources temporarily unavailable"),
                                            className="small",
                                        ),
                                        html.Li(
                                            t(lang, "results", "cause_remote", default="Remote region without data source coverage"),
                                            className="small",
                                        ),
                                        html.Li(
                                            t(lang, "results", "cause_server_overloaded", default="Server overloaded — try again in a few minutes"),
                                            className="small",
                                        ),
                                    ],
                                    className="mb-3 ps-3",
                                ),
                                html.P(
                                    [
                                        html.I(
                                            className="bi bi-lightbulb me-2 text-warning"
                                        ),
                                        html.Small(
                                            t(lang, "results", "retry_tip", default="Tip: Try again or select another point."),
                                            className="text-muted",
                                        ),
                                    ],
                                    className="mb-0",
                                ),
                            ],
                            className="px-2",
                        ),
                        html.Hr(),
                        dbc.Button(
                            [
                                html.I(className="bi bi-geo-alt me-2"),
                                t(lang, "results", "select_another", default="Select Another Point"),
                            ],
                            id="btn-new-query",
                            color="primary",
                            className="w-100",
                        ),
                    ]
                )
                sidebar_error = html.Div(
                    [
                        dbc.Alert(
                            [
                                html.I(
                                    className="bi bi-exclamation-triangle me-2"
                                ),
                                t(lang, "results", "error_fetching", default="Error fetching data"),
                            ],
                            color="warning",
                            className="py-2 px-3 mb-2 small",
                        ),
                        dbc.Button(
                            [
                                html.I(className="bi bi-geo-alt me-2"),
                                t(lang, "results", "select_another", default="Select Another Point"),
                            ],
                            id="btn-new-query-sidebar",
                            color="primary",
                            outline=True,
                            size="sm",
                            className="w-100",
                        ),
                    ]
                )
                return (
                    None,
                    error_content,
                    True,
                    None,
                    sidebar_error,
                    None,
                    no_update,
                )

            # Progress: use 180s for RETRY, 60s for normal
            max_time = 180 if status == "RETRY" else 60
            estimated_progress = min(95, 10 + (elapsed / max_time) * 85)

            # Mensagem diferente para RETRY
            if status == "RETRY":
                progress_msg = t(lang, "progress_ui", "retrying", default="Trying to get data...")
                time_remaining = t(lang, "progress_ui", "please_wait", default="Please wait... ({seconds}s)").format(seconds=elapsed)
            else:
                progress_msg = t(lang, "progress_ui", "downloading_calculating", default="Downloading data and calculating ETo...")
                time_remaining = t(lang, "progress_ui", "time_estimated", default="Estimated time: {seconds}s").format(seconds=max(1, 30 - elapsed))

            progress_indicator = html.Div(
                [
                    # Linha com spinner e mensagem
                    html.Div(
                        [
                            dbc.Spinner(
                                color=(
                                    "success"
                                    if status != "RETRY"
                                    else "warning"
                                ),
                                type="border",
                                size="sm",
                                spinner_class_name="me-3",
                            ),
                            html.Div(
                                [
                                    html.Span(
                                        progress_msg,
                                        className="fw-semibold text-dark",
                                    ),
                                    html.Br(),
                                    html.Small(
                                        time_remaining,
                                        className="text-muted",
                                    ),
                                ],
                            ),
                            html.Div(
                                html.Span(
                                    f"{int(estimated_progress)}%",
                                    className="fw-bold text-success fs-5",
                                ),
                                className="ms-auto",
                            ),
                        ],
                        className="d-flex align-items-center mb-3",
                    ),
                    # Barra de progresso fina e elegante
                    dbc.Progress(
                        value=estimated_progress,
                        color="success" if status != "RETRY" else "warning",
                        className="mb-0",
                        style={"height": "8px", "borderRadius": "4px"},
                    ),
                ],
                className="p-3 bg-light rounded-3 border",
            )

            return (
                progress_indicator,
                no_update,
                False,
                task_id,
                no_update,
                no_update,
                no_update,  # fusion-info-card
            )

        else:
            # Status desconhecido - manter consultando por tempo limitado
            elapsed = n_intervals * 2
            if elapsed > 120:
                logger.error(f"⏱️ Task timeout com status: {status}")
                return (
                    None,
                    no_update,
                    True,
                    None,
                    no_update,
                    no_update,
                    no_update,
                )
            logger.warning(f"⚠️ Status desconhecido: {status}")
            return (
                None,
                no_update,
                False,
                task_id,
                no_update,
                no_update,
                no_update,
            )

    except Exception as e:
        logger.error(f"Erro ao atualizar progresso: {e}")
        return None, no_update, False, task_id, no_update, no_update, no_update


# ============================================================================
# CALLBACKS DE DOWNLOAD CSV E EXCEL
# ============================================================================


@callback(
    Output("download-csv", "data"),
    Input("btn-download-csv", "n_clicks"),
    State("eto-results-data", "data"),
    prevent_initial_call=True,
)
def download_csv(n_clicks, results_data):
    """Gera download de arquivo CSV."""
    if not n_clicks or not results_data:
        return no_update

    import pandas as pd
    from datetime import datetime

    records = results_data.get("records", [])
    if not records:
        return no_update

    # Criar DataFrame
    df = pd.DataFrame(records)

    # Formatar nome do arquivo
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"EVAonline_ETo_{timestamp}.csv"

    return dcc.send_data_frame(df.to_csv, filename, index=False)


@callback(
    Output("download-excel", "data"),
    Input("btn-download-excel", "n_clicks"),
    State("eto-results-data", "data"),
    prevent_initial_call=True,
)
def download_excel(n_clicks, results_data):
    """Gera download de arquivo Excel."""
    if not n_clicks or not results_data:
        return no_update

    import pandas as pd
    from datetime import datetime
    import io

    records = results_data.get("records", [])
    if not records:
        return no_update

    # Criar DataFrame
    df = pd.DataFrame(records)

    # Formatar nome do arquivo
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"EVAonline_ETo_{timestamp}.xlsx"

    # Criar buffer Excel
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="ETo_Data")
    output.seek(0)

    return dcc.send_bytes(output.getvalue(), filename)


# ============================================================================
# CALLBACKS DE DOWNLOAD POR TABELA
# ============================================================================


def _send_table(df_export, base_name, excel_clicked, sheet_name="Data", lang="pt"):
    """Helper: send a DataFrame as CSV or Excel.

    Args:
        excel_clicked: True when the Excel button was the trigger.
        lang: Interface language — controls decimal/separator formatting.
              'pt' → decimal=',' sep=';'  |  'en' → decimal='.' sep=','
    """
    import io
    import pandas as pd
    from datetime import datetime as _dt

    timestamp = _dt.now().strftime("%Y%m%d_%H%M%S")

    # Round all numeric columns to 2 decimal places for clean export.
    # This also prevents Portuguese Excel from misinterpreting 3-digit
    # decimal values (e.g. 29.885) as thousands-separated integers.
    num_cols = df_export.select_dtypes(include="number").columns
    df_export = df_export.copy()
    df_export[num_cols] = df_export[num_cols].round(2)

    if excel_clicked:
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as w:
            df_export.to_excel(w, index=False, sheet_name=sheet_name)
            # Apply 2-decimal number format for consistent display
            ws = w.sheets[sheet_name]
            for row in ws.iter_rows(min_row=2, min_col=1):
                for cell in row:
                    if isinstance(cell.value, (int, float)):
                        cell.number_format = "0.00"
        buf.seek(0)
        return dcc.send_bytes(buf.getvalue(), f"EVAonline_{base_name}_{timestamp}.xlsx")

    # CSV: locale-aware formatting
    if lang == "pt":
        csv_sep, csv_dec = ";", ","
    else:
        csv_sep, csv_dec = ",", "."

    return dcc.send_data_frame(
        df_export.to_csv,
        f"EVAonline_{base_name}_{timestamp}.csv",
        index=False,
        sep=csv_sep,
        decimal=csv_dec,
    )


# Map from serialized (store) column names to internal column names
_STORE_TO_INTERNAL = {
    "tmax_c": "T2M_MAX",
    "tmin_c": "T2M_MIN",
    "tmed_c": "T2M",
    "humidity_pct": "RH2M",
    "wind_ms": "WS2M",
    "radiation_mj_m2": "ALLSKY_SFC_SW_DWN",
    "precip_mm": "PRECTOTCORR",
    "et0_mm_day": "eto_evaonline",
}


def _df_from_store(results_data):
    """Build a DataFrame from store records, remapping column names."""
    import pandas as pd
    records = results_data.get("records", [])
    if not records:
        return None
    df = pd.DataFrame(records)
    # Remap serialised names → internal names used by display functions
    df = df.rename(columns=_STORE_TO_INTERNAL)
    return df


def _is_excel_trigger():
    """Return True if the callback was triggered by an Excel button."""
    from dash import callback_context
    triggered = callback_context.triggered
    if triggered:
        return triggered[0]["prop_id"].split(".")[0].endswith("-excel")
    return False


@callback(
    Output("download-table-climate", "data"),
    Input("btn-dl-climate-csv", "n_clicks"),
    Input("btn-dl-climate-excel", "n_clicks"),
    State("eto-results-data", "data"),
    State("language-store", "data"),
    prevent_initial_call=True,
)
def download_table_climate(csv_n, excel_n, results_data, lang_data):
    """Download da tabela Daily Climate Data."""
    if not results_data or not (csv_n or excel_n):
        return no_update

    import pandas as pd
    from shared_utils.get_translations import get_translations

    lang = lang_data if isinstance(lang_data, str) else "pt"
    df = _df_from_store(results_data)
    if df is None:
        return no_update

    t_dict = get_translations(lang)
    dv = t_dict.get("data_variables", {})

    eto_col = "eto_evaonline" if "eto_evaonline" in df.columns else "ETo"
    cols = ["date", "T2M_MAX", "T2M_MIN", "RH2M", "WS2M", "ALLSKY_SFC_SW_DWN", "PRECTOTCORR", eto_col]
    df_export = df[[c for c in cols if c in df.columns]].copy()
    df_export = df_export.rename(columns={
        "date": dv.get("date", "Date"),
        "T2M_MAX": dv.get("temp_max", "Max Temp (°C)"),
        "T2M_MIN": dv.get("temp_min", "Min Temp (°C)"),
        "RH2M": dv.get("humidity", "Humidity (%)"),
        "WS2M": dv.get("wind_speed", "Wind Speed (m/s)"),
        "ALLSKY_SFC_SW_DWN": dv.get("radiation", "Solar Radiation"),
        "PRECTOTCORR": dv.get("precipitation", "Precipitation (mm)"),
        eto_col: dv.get("eto_evaonline", "ETo EVAonline (mm/day)"),
    })

    return _send_table(df_export, "Climate", _is_excel_trigger(), "Climate_Data", lang=lang)


@callback(
    Output("download-table-stats", "data"),
    Input("btn-dl-stats-csv", "n_clicks"),
    Input("btn-dl-stats-excel", "n_clicks"),
    State("eto-results-data", "data"),
    State("language-store", "data"),
    prevent_initial_call=True,
)
def download_table_stats(csv_n, excel_n, results_data, lang_data):
    """Download da tabela Descriptive Statistics."""
    if not results_data or not (csv_n or excel_n):
        return no_update

    import pandas as pd
    from scipy import stats as sp_stats
    from shared_utils.get_translations import get_translations

    lang = lang_data if isinstance(lang_data, str) else "pt"
    mode = results_data.get("mode", "")
    df = _df_from_store(results_data)
    if df is None:
        return no_update
    t_dict = get_translations(lang)
    dv = t_dict.get("data_variables", {})
    st = t_dict.get("statistics", {})

    col_names = {
        "T2M_MAX": dv.get("temp_max", "Max Temp"),
        "T2M_MIN": dv.get("temp_min", "Min Temp"),
        "RH2M": dv.get("humidity", "Humidity"),
        "WS2M": dv.get("wind_speed", "Wind Speed"),
        "ALLSKY_SFC_SW_DWN": dv.get("radiation", "Solar Radiation"),
        "PRECTOTCORR": dv.get("precipitation", "Precipitation"),
        "ETo": dv.get("eto", "ETo"),
        "eto_evaonline": dv.get("eto_evaonline", "ETo EVAonline"),
    }
    expected = ["T2M_MAX", "T2M_MIN", "RH2M", "WS2M", "ALLSKY_SFC_SW_DWN", "PRECTOTCORR", "ETo", "eto_evaonline"]
    num_cols = [c for c in expected if c in df.columns]
    if not num_cols:
        return no_update

    data = {
        st.get("mean", "Mean"): df[num_cols].mean().round(2),
        st.get("max", "Max"): df[num_cols].max().round(2),
        st.get("min", "Min"): df[num_cols].min().round(2),
        st.get("median", "Median"): df[num_cols].median().round(2),
        st.get("std_dev", "Std Dev"): df[num_cols].std().round(2),
        st.get("percentile_25", "P25"): df[num_cols].quantile(0.25).round(2),
        st.get("percentile_75", "P75"): df[num_cols].quantile(0.75).round(2),
    }
    if mode != "DASHBOARD_FORECAST":
        data[st.get("coef_variation", "CV (%)")] = (
            (df[num_cols].std() / df[num_cols].mean()) * 100
        ).round(2)
        data[st.get("skewness", "Skewness")] = df[num_cols].apply(
            lambda x: sp_stats.skew(x.dropna())
        ).round(2)
        data[st.get("kurtosis", "Kurtosis")] = df[num_cols].apply(
            lambda x: sp_stats.kurtosis(x.dropna())
        ).round(2)

    stats_df = pd.DataFrame(data).T
    stats_df.insert(0, st.get("statistic", "Statistic"), stats_df.index)
    stats_df = stats_df.rename(columns=col_names)

    return _send_table(stats_df, "Statistics", _is_excel_trigger(), "Descriptive_Stats", lang=lang)


@callback(
    Output("download-table-eto-summary", "data"),
    Input("btn-dl-eto-summary-csv", "n_clicks"),
    Input("btn-dl-eto-summary-excel", "n_clicks"),
    State("eto-results-data", "data"),
    State("language-store", "data"),
    prevent_initial_call=True,
)
def download_table_eto_summary(csv_n, excel_n, results_data, lang_data):
    """Download da tabela ETo Summary / Water Balance."""
    if not results_data or not (csv_n or excel_n):
        return no_update

    import pandas as pd
    from shared_utils.get_translations import get_translations

    lang = lang_data if isinstance(lang_data, str) else "pt"
    df = _df_from_store(results_data)
    if df is None:
        return no_update

    t_dict = get_translations(lang)
    dv = t_dict.get("data_variables", {})
    st = t_dict.get("statistics", {})

    eto_col = "eto_evaonline" if "eto_evaonline" in df.columns else "ETo"
    if "date" not in df.columns or "PRECTOTCORR" not in df.columns or eto_col not in df.columns:
        return no_update

    df_exp = df[["date", "PRECTOTCORR", eto_col]].copy()
    df_exp["date"] = pd.to_datetime(df_exp["date"]).dt.strftime("%d/%m/%Y")
    deficit_label = st.get("water_deficit", "Water Deficit (mm)")
    df_exp[deficit_label] = (df_exp["PRECTOTCORR"] - df_exp[eto_col]).round(2)

    for col in [c for c in df_exp.columns if c != "date"]:
        df_exp[col] = df_exp[col].round(2)

    df_exp = df_exp.rename(columns={
        "date": dv.get("date", "Date"),
        "PRECTOTCORR": dv.get("precipitation", "Precipitation (mm)"),
        eto_col: dv.get("eto_evaonline", "ETo EVAonline (mm/day)"),
    })

    return _send_table(df_exp, "WaterBalance", _is_excel_trigger(), "Water_Balance", lang=lang)


@callback(
    Output("download-table-normality", "data"),
    Input("btn-dl-normality-csv", "n_clicks"),
    Input("btn-dl-normality-excel", "n_clicks"),
    State("eto-results-data", "data"),
    State("language-store", "data"),
    prevent_initial_call=True,
)
def download_table_normality(csv_n, excel_n, results_data, lang_data):
    """Download da tabela Normality Test (Shapiro-Wilk)."""
    if not results_data or not (csv_n or excel_n):
        return no_update

    import pandas as pd
    from scipy import stats as sp_stats
    from shared_utils.get_translations import get_translations

    lang = lang_data if isinstance(lang_data, str) else "pt"
    mode = results_data.get("mode", "")
    if mode == "DASHBOARD_FORECAST":
        return no_update

    df = _df_from_store(results_data)
    if df is None:
        return no_update

    t_dict = get_translations(lang)
    dv = t_dict.get("data_variables", {})
    st = t_dict.get("statistics", {})

    col_names = {
        "T2M_MAX": dv.get("temp_max", "Max Temp"),
        "T2M_MIN": dv.get("temp_min", "Min Temp"),
        "RH2M": dv.get("humidity", "Humidity"),
        "WS2M": dv.get("wind_speed", "Wind Speed"),
        "ALLSKY_SFC_SW_DWN": dv.get("radiation", "Solar Radiation"),
        "PRECTOTCORR": dv.get("precipitation", "Precipitation"),
        "ETo": dv.get("eto", "ETo"),
        "eto_evaonline": dv.get("eto_evaonline", "ETo EVAonline"),
    }
    eto_col = "eto_evaonline" if "eto_evaonline" in df.columns else "ETo"
    expected = ["T2M_MAX", "T2M_MIN", "RH2M", "WS2M", "ALLSKY_SFC_SW_DWN", "PRECTOTCORR", eto_col]
    num_cols = [c for c in expected if c in df.columns]
    if not num_cols:
        return no_update

    rows = {}
    for col in num_cols:
        stat_val, p_val = sp_stats.shapiro(df[col].dropna())
        display = col_names.get(col, col)
        rows[display] = {
            st.get("statistic", "Statistic"): round(stat_val, 4),
            st.get("p_value", "P-Value"): round(p_val, 4),
        }

    norm_df = pd.DataFrame(rows).T
    norm_df.insert(0, st.get("variable", "Variable"), norm_df.index)

    return _send_table(norm_df, "Normality", _is_excel_trigger(), "Shapiro_Wilk", lang=lang)


# ============================================================================
# CLIENTSIDE CALLBACKS - Chart Image Downloads (PNG / JPG)
# ============================================================================
# Each chart has two buttons: PNG and JPG.
# Downloads run entirely in the browser via Plotly.downloadImage().
# ============================================================================

from dash import clientside_callback

# Chart definitions: (chart_id, graph_component_id, default_filename)
_CHARTS = [
    ("deficit",       "chart-deficit",       "EVAonline_WaterDeficit"),
    ("eto-temp",      "chart-eto-temp",      "EVAonline_ETo_vs_Temp"),
    ("eto-rad",       "chart-eto-rad",       "EVAonline_ETo_vs_Radiation"),
    ("temp-rad-prec", "chart-temp-rad-prec", "EVAonline_Temp_Prec"),
    ("heatmap",       "chart-heatmap",       "EVAonline_Heatmap"),
]

for _cid, _gid, _fname in _CHARTS:
    for _fmt, _plotly_fmt in [("png", "png"), ("jpg", "jpeg")]:
        clientside_callback(
            f"""
            function(n_clicks) {{
                if (!n_clicks) {{
                    return window.dash_clientside.no_update;
                }}
                var wrapper = document.getElementById("{_gid}");
                if (!wrapper) {{
                    return window.dash_clientside.no_update;
                }}
                // dcc.Graph wraps the Plotly div; find the actual plot element
                var graphDiv = wrapper.querySelector(".js-plotly-plot") || wrapper;
                Plotly.downloadImage(graphDiv, {{
                    format: "{_plotly_fmt}",
                    width: 1920,
                    height: 1080,
                    scale: 2,
                    filename: "{_fname}"
                }});
                return "";
            }}
            """,
            Output(f"btn-dl-chart-{_cid}-{_fmt}", "title"),
            Input(f"btn-dl-chart-{_cid}-{_fmt}", "n_clicks"),
            prevent_initial_call=True,
        )


logger.info("✅ Página ETo carregada com sucesso")
