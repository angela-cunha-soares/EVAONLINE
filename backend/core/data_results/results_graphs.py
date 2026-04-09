import numpy as np
import pandas as pd
import plotly.graph_objects as go
from loguru import logger

from shared_utils.get_translations import get_translations

# ── Shared academic chart style constants ──
_FONT_FAMILY = "Segoe UI, Roboto, Arial, sans-serif"
_TITLE_SIZE = 26
_AXIS_TITLE_SIZE = 22
_TICK_SIZE = 18
_LEGEND_SIZE = 20
_ANNOTATION_SIZE = 17
_BAR_TEXT_SIZE = 17
_CHART_HEIGHT = 550
_HEATMAP_HEIGHT = 550
_BRAND_BLUE = "#005B99"
_TEMPLATE = "plotly_white"
_GRID_Y_COLOR = "rgba(0,0,0,0.15)"
_GRID_X_COLOR = "rgba(0,0,0,0.12)"
_DATE_FORMAT = "%d/%m/%Y"


def _bold(text: str) -> str:
    """Wrap text in HTML bold tags for Plotly axis titles."""
    return f"<b>{text}</b>"

# ── Heatmap custom colorscale (pomegranate → cream → teal) ──
_HEATMAP_COLORSCALE = [
    [0.0, "#9B2335"],
    [0.25, "#E8927C"],
    [0.5, "#FDF5E6"],
    [0.75, "#5DADE2"],
    [1.0, "#14505C"],
]

# Map API column names → translation keys in data_variables
_COLUMN_TO_VAR_KEY = {
    "T2M_MAX": "temp_max",
    "T2M_MIN": "temp_min",
    "T2M": "temp_mean",
    "RH2M": "humidity",
    "WS2M": "wind_speed",
    "ALLSKY_SFC_SW_DWN": "radiation",
    "PRECTOTCORR": "precipitation",
    "eto_evaonline": "eto_evaonline",
    "ETo EVAonline (mm/day)": "eto_evaonline",
    "ETo Open-Meteo (mm/day)": "eto_openmeteo",
    "eto_openmeteo": "eto_openmeteo",
}


def _base_layout(**overrides):
    """Return a base layout dict for consistent academic styling.

    NOTE: xaxis/yaxis are NOT included here because each chart
    defines its own axis configuration.  Including them would cause
    'got multiple values for keyword argument' when unpacked together
    with per-chart xaxis/yaxis kwargs in update_layout().
    """
    layout = dict(
        font=dict(family=_FONT_FAMILY, size=_TICK_SIZE),
        title_font=dict(size=_TITLE_SIZE, family=_FONT_FAMILY),
        template=_TEMPLATE,
        height=_CHART_HEIGHT,
        hoverlabel=dict(font_size=17, font_family=_FONT_FAMILY),
    )
    layout.update(overrides)
    return layout


def plot_eto_vs_temperature(df: pd.DataFrame, lang: str = "pt") -> go.Figure:
    """
    Gera um gráfico de barras para ETo e linhas para temperaturas
    máxima e mínima.

    Parâmetros:
    - df: DataFrame com os dados (espera colunas 'date', 'T2M_MAX',
          'T2M_MIN', 'ETo').
    - lang: Idioma para traduções ('pt' ou 'en').

    Retorna:
    - Objeto go.Figure com o gráfico.
    """
    try:
        if df is None or df.empty:
            logger.warning(
                "DataFrame vazio ou None fornecido para "
                "plot_eto_vs_temperature"
            )
            return go.Figure()

        # Obter traduções
        t = get_translations(lang)
        dv = t.get("data_variables", {})
        ch = t.get("charts", {})

        # Support both old 'ETo' and new 'eto_evaonline' column names
        eto_col = "eto_evaonline" if "eto_evaonline" in df.columns else "ETo"
        expected_columns = ["date", "T2M_MAX", "T2M_MIN", eto_col]
        missing_columns = [
            col for col in expected_columns if col not in df.columns
        ]
        if missing_columns:
            logger.error(f"Colunas ausentes no DataFrame: {missing_columns}")
            return go.Figure()  # Return empty figure instead of raising

        fig = go.Figure()
        fig.add_trace(
            go.Bar(
                x=df["date"],
                y=df[eto_col],
                name=dv.get("eto", "ETo (mm/dia)"),
                marker_color=_BRAND_BLUE,
                text=df[eto_col].round(2),
                textposition="outside",
                textfont={"size": _BAR_TEXT_SIZE},
            )
        )
        fig.add_trace(
            go.Scatter(
                x=df["date"],
                y=df["T2M_MAX"],
                mode="lines+markers",
                name=dv.get("temp_max", "Temperatura Máxima (°C)"),
                line={"color": "#C0392B", "width": 2.5},
                marker={"size": 5},
            )
        )
        fig.add_trace(
            go.Scatter(
                x=df["date"],
                y=df["T2M_MIN"],
                mode="lines+markers",
                name=dv.get("temp_min", "Temperatura Mínima (°C)"),
                line={"color": "#27AE60", "width": 2.5},
                marker={"size": 5},
            )
        )
        fig.update_layout(
            **_base_layout(),
            yaxis={"title": {"text": _bold(ch.get("temperature", "Temperatura (°C)")), "font": {"size": _AXIS_TITLE_SIZE}},
                   "showgrid": True, "gridcolor": _GRID_Y_COLOR, "tickfont": {"size": _TICK_SIZE}},
            xaxis={"tickangle": -45, "title": {"text": _bold(ch.get("date_label", "Date")), "font": {"size": _AXIS_TITLE_SIZE}},
                   "tickfont": {"size": _TICK_SIZE}, "showgrid": True, "gridcolor": _GRID_X_COLOR,
                   "tickformat": _DATE_FORMAT},
            legend_title={"text": ch.get("legend", "Legenda"), "font": {"size": _LEGEND_SIZE}},
            barmode="group",
            legend={
                "x": 0.5,
                "y": -0.25,
                "xanchor": "center",
                "yanchor": "top",
                "orientation": "h",
                "font": {"size": _LEGEND_SIZE},
            },
            margin={"b": 120, "t": 40, "l": 70, "r": 30},
        )
        logger.info("Gráfico ET₀ vs. Temperatura gerado com sucesso")
        return fig

    except Exception as e:
        logger.error(f"Erro ao gerar gráfico ET₀ vs. Temperatura: {str(e)}")
        return go.Figure()


def plot_eto_vs_radiation(df: pd.DataFrame, lang: str = "pt") -> go.Figure:
    """
    Gera um gráfico de linhas para ETo e radiação solar com eixos Y
    duplos.

    Parâmetros:
    - df: DataFrame com os dados (espera colunas 'date',
          'ALLSKY_SFC_SW_DWN', 'ETo').
    - lang: Idioma para traduções ('pt' ou 'en').

    Retorna:
    - Objeto go.Figure com o gráfico.
    """
    try:
        if df is None or df.empty:
            logger.warning(
                "DataFrame vazio ou None fornecido para "
                "plot_eto_vs_radiation"
            )
            return go.Figure()

        t = get_translations(lang)
        dv = t.get("data_variables", {})
        ch = t.get("charts", {})

        # Support both old 'ETo' and new 'eto_evaonline' column names
        eto_col = "eto_evaonline" if "eto_evaonline" in df.columns else "ETo"
        expected_columns = ["date", "ALLSKY_SFC_SW_DWN", eto_col]
        missing_columns = [
            col for col in expected_columns if col not in df.columns
        ]
        if missing_columns:
            logger.error(f"Colunas ausentes no DataFrame: {missing_columns}")
            return go.Figure()  # Return empty figure instead of raising

        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=df["date"],
                y=df[eto_col],
                mode="lines+markers",
                name=dv.get("eto", "ETo (mm/dia)"),
                yaxis="y1",
                line={"color": _BRAND_BLUE, "width": 2.5},
                marker={"size": 5},
            )
        )
        fig.add_trace(
            go.Scatter(
                x=df["date"],
                y=df["ALLSKY_SFC_SW_DWN"],
                mode="lines+markers",
                name=dv.get("radiation", "Radiação Solar (MJ/m²/dia)"),
                yaxis="y2",
                line={"color": "#E67E22", "width": 2.5},
                marker={"size": 5},
            )
        )
        fig.update_layout(
            **_base_layout(),
            yaxis={"title": {"text": _bold(dv.get("eto", "ETo (mm/dia)")), "font": {"size": _AXIS_TITLE_SIZE}},
                   "showgrid": True, "gridcolor": _GRID_Y_COLOR, "tickfont": {"size": _TICK_SIZE}},
            yaxis2={
                "title": {"text": _bold(dv.get("radiation", "Radiação Solar (MJ/m²/dia)")), "font": {"size": _AXIS_TITLE_SIZE}},
                "overlaying": "y",
                "side": "right",
                "tickfont": {"size": _TICK_SIZE},
                "showgrid": False,
            },
            xaxis={"title": {"text": _bold(ch.get("date_label", "Date")), "font": {"size": _AXIS_TITLE_SIZE}},
                   "tickfont": {"size": _TICK_SIZE}, "showgrid": True, "gridcolor": _GRID_X_COLOR,
                   "tickformat": _DATE_FORMAT},
            legend_title={"text": ch.get("legend", "Legenda"), "font": {"size": _LEGEND_SIZE}},
            legend={
                "x": 0.5,
                "y": -0.2,
                "xanchor": "center",
                "yanchor": "top",
                "orientation": "h",
                "font": {"size": _LEGEND_SIZE},
            },
            margin={"b": 110, "t": 40, "l": 70, "r": 80},
        )
        logger.info("Gráfico ET₀ vs. Radiação gerado com sucesso")
        return fig

    except Exception as e:
        logger.error(f"Erro ao gerar gráfico ET₀ vs. Radiação: {str(e)}")
        return go.Figure()


def plot_temp_rad_prec(df: pd.DataFrame, lang: str = "pt") -> go.Figure:
    """
    Gera um gráfico combinado de barras (ETo, precipitação) e linha
    (temp. máx.).

    Parâmetros:
    - df: DataFrame com os dados (espera colunas 'date', 'T2M_MAX',
          'PRECTOTCORR', 'eto_evaonline').
    - lang: Idioma para traduções ('pt' ou 'en').

    Retorna:
    - Objeto go.Figure com o gráfico.
    """
    try:
        if df is None or df.empty:
            logger.warning(
                "DataFrame vazio ou None fornecido para " "plot_temp_rad_prec"
            )
            return go.Figure()

        t = get_translations(lang)
        dv = t.get("data_variables", {})
        ch = t.get("charts", {})

        # Support both old 'ETo' and new 'eto_evaonline' column names
        eto_col = "eto_evaonline" if "eto_evaonline" in df.columns else "ETo"
        expected_columns = [
            "date",
            "T2M_MAX",
            "PRECTOTCORR",
            eto_col,
        ]
        missing_columns = [
            col for col in expected_columns if col not in df.columns
        ]
        if missing_columns:
            logger.error(f"Colunas ausentes no DataFrame: {missing_columns}")
            return go.Figure()  # Return empty figure instead of raising

        fig = go.Figure()
        fig.add_trace(
            go.Bar(
                x=df["date"],
                y=df[eto_col],
                name=dv.get("eto", "ETo (mm/dia)"),
                marker_color=_BRAND_BLUE,
                text=df[eto_col].round(2),
                textposition="outside",
                textfont={"size": _BAR_TEXT_SIZE},
            )
        )
        fig.add_trace(
            go.Scatter(
                x=df["date"],
                y=df["T2M_MAX"],
                mode="lines+markers",
                name=dv.get("temp_max", "Temperatura Máxima (°C)"),
                line={"color": "#C0392B", "width": 2.5},
                marker={"size": 5},
                yaxis="y2",
            )
        )
        fig.add_trace(
            go.Bar(
                x=df["date"],
                y=df["PRECTOTCORR"],
                name=dv.get("precipitation", "Precipitação Total (mm)"),
                marker_color="#8E44AD",
                text=df["PRECTOTCORR"].round(2),
                textposition="outside",
                textfont={"size": _BAR_TEXT_SIZE},
            )
        )

        temp_max = df["T2M_MAX"].max()
        temp_max_range = temp_max * 1.2 if temp_max > 0 else 10

        eto_max = df[eto_col].max()
        precip_max = df["PRECTOTCORR"].max()
        bar_max = (
            max(eto_max, precip_max) * 1.5
            if max(eto_max, precip_max) > 0
            else 10
        )

        fig.update_layout(
            **_base_layout(),
            xaxis={"title": {"text": _bold(ch.get("date_label", "Date")), "font": {"size": _AXIS_TITLE_SIZE}},
                   "tickangle": -45, "tickfont": {"size": _TICK_SIZE},
                   "showgrid": True, "gridcolor": _GRID_X_COLOR,
                   "tickformat": _DATE_FORMAT},
            yaxis={
                "title": {"text": _bold(f"{dv.get('eto', 'ETo (mm/dia)')}/{dv.get('precipitation', 'Precipitação Total (mm)')}"),
                         "font": {"size": _AXIS_TITLE_SIZE}},
                "side": "left",
                "range": [0, bar_max],
                "tickfont": {"size": _TICK_SIZE},
                "showgrid": True, "gridcolor": _GRID_Y_COLOR,
            },
            yaxis2={
                "title": {"text": _bold(dv.get("temp_max", "Temperatura Máxima (°C)")), "font": {"size": _AXIS_TITLE_SIZE}},
                "overlaying": "y",
                "side": "right",
                "range": [0, temp_max_range],
                "tickfont": {"size": _TICK_SIZE},
                "showgrid": False,
            },
            legend={
                "x": 0.5,
                "y": -0.25,
                "xanchor": "center",
                "yanchor": "top",
                "orientation": "h",
                "font": {"size": _LEGEND_SIZE},
            },
            barmode="group",
            margin={"b": 120, "t": 40, "l": 80, "r": 80},
        )
        logger.info("Gráfico combinado gerado com sucesso")
        return fig

    except Exception as e:
        logger.error(f"Erro ao gerar gráfico Temp/Rad/Prec: {str(e)}")
        return go.Figure()


def plot_heatmap(df: pd.DataFrame, lang: str = "pt") -> go.Figure:
    """
    Gera um mapa de calor para a matriz de correlação.

    Parâmetros:
    - df: DataFrame com os dados (espera colunas numéricas, exceto
          'date' e 'PRECTOTCORR').
    - lang: Idioma para traduções ('pt' ou 'en').

    Retorna:
    - Objeto go.Figure com o gráfico.
    """
    try:
        if df is None or df.empty:
            logger.warning(
                "DataFrame vazio ou None fornecido para plot_heatmap"
            )
            return go.Figure()

        t = get_translations(lang)
        dv = t.get("data_variables", {})
        st = t.get("statistics", {})
        columns_to_exclude = [
            "date", "PRECTOTCORR",
            "ETo Open-Meteo (mm/day)", "eto_openmeteo",
        ]
        corr_columns = [
            col for col in df.columns if col not in columns_to_exclude
        ]
        if not corr_columns:
            logger.error("Nenhuma coluna válida para calcular correlação")
            raise ValueError("Nenhuma coluna válida para calcular correlação")

        corr_matrix = df[corr_columns].corr().round(2)
        # Renomear colunas usando mapeamento API → chave de tradução
        translated_columns = {
            col: dv.get(_COLUMN_TO_VAR_KEY.get(col, ""), col)
            for col in corr_matrix.columns
        }
        corr_matrix = corr_matrix.rename(
            columns=translated_columns, index=translated_columns
        )

        fig = go.Figure()
        fig.add_heatmap(
            z=corr_matrix.values,
            x=corr_matrix.columns,
            y=corr_matrix.index,
            colorscale=_HEATMAP_COLORSCALE,
            zmin=-1,
            zmax=1,
            text=corr_matrix.values,
            texttemplate="%{text}",
            textfont={"size": _ANNOTATION_SIZE},
        )
        fig.update_layout(
            **_base_layout(height=_HEATMAP_HEIGHT),
            xaxis={"tickfont": {"size": _TICK_SIZE, "family": _FONT_FAMILY}, "tickangle": -30},
            yaxis={"tickfont": {"size": _TICK_SIZE, "family": _FONT_FAMILY}, "autorange": "reversed"},
            margin={"b": 120, "t": 40, "l": 160, "r": 30},
        )
        logger.info("Mapa de calor gerado com sucesso")
        return fig

    except Exception as e:
        logger.error(f"Erro ao gerar mapa de calor: {str(e)}")
        return go.Figure()


def plot_correlation(
    df: pd.DataFrame, x_var: str, lang: str = "pt"
) -> go.Figure:
    """
    Gera um gráfico de dispersão com linha de tendência para uma
    variável vs. ETo.

    Parâmetros:
    - df: DataFrame com os dados (espera colunas 'ETo' e x_var).
    - x_var: Nome da coluna para o eixo X.
    - lang: Idioma para traduções ('pt' ou 'en').

    Retorna:
    - Objeto go.Figure com o gráfico.
    """
    try:
        if df is None or df.empty:
            logger.warning(
                "DataFrame vazio ou None fornecido para plot_correlation"
            )
            return go.Figure()

        t = get_translations(lang)
        dv = t.get("data_variables", {})
        ch = t.get("charts", {})
        if x_var not in df.columns or "ETo" not in df.columns:
            logger.error(
                f"Colunas inválidas para correlação: x_var={x_var}, ETo"
            )
            raise ValueError(
                f"Colunas inválidas para correlação: x_var={x_var}, ETo"
            )

        x_var_translated = dv.get(_COLUMN_TO_VAR_KEY.get(x_var, ""), x_var)
        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=df[x_var],
                y=df["ETo"],
                mode="markers",
                name=f"{x_var_translated} vs. {dv.get('eto', 'ETo (mm/dia)')}",
                marker={"color": _BRAND_BLUE, "size": 8, "opacity": 0.7},
            )
        )
        slope, intercept = np.polyfit(df[x_var], df["ETo"], 1)
        line = slope * df[x_var] + intercept

        fig.add_trace(
            go.Scatter(
                x=df[x_var],
                y=line,
                mode="lines",
                name=ch.get("trend_line", "Linha de Tendência"),
                line={"color": "#C0392B", "dash": "dash", "width": 2},
            )
        )

        fig.update_layout(
            **_base_layout(),
            xaxis={"title": {"text": _bold(x_var_translated), "font": {"size": _AXIS_TITLE_SIZE}},
                   "tickfont": {"size": _TICK_SIZE}, "showgrid": True, "gridcolor": _GRID_X_COLOR},
            yaxis={"title": {"text": _bold(dv.get("eto", "ETo (mm/dia)")), "font": {"size": _AXIS_TITLE_SIZE}},
                   "tickfont": {"size": _TICK_SIZE}, "showgrid": True, "gridcolor": _GRID_Y_COLOR},
            legend={
                "x": 0.5,
                "y": -0.2,
                "xanchor": "center",
                "yanchor": "top",
                "orientation": "h",
                "font": {"size": _LEGEND_SIZE},
            },
            margin={"b": 100, "t": 40, "l": 70, "r": 30},
        )
        logger.info(
            f"Gráfico de correlação gerado com sucesso: {x_var} vs. ETo"
        )
        return fig

    except Exception as e:
        logger.error(f"Erro ao gerar gráfico de correlação: {str(e)}")
        return go.Figure()
