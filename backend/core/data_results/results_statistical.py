import dash_bootstrap_components as dbc
import numpy as np
import pandas as pd
import plotly.express as px
from dash import dcc, html
from loguru import logger
from scipy import stats
from statsmodels.tsa.stattools import adfuller

from backend.core.data_results.results_tables import (
    display_results_table,
    format_number,
)
from shared_utils.get_translations import get_translations


def display_daily_data(df: pd.DataFrame, lang: str = "pt") -> html.Div:
    """
    Exibe os dados climáticos diários em uma tabela formatada.

    Parâmetros:
    - df: DataFrame com os dados (espera colunas 'date', 'T2M_MAX', 'T2M_MIN',
    - 'RH2M', 'WS2M', 'ALLSKY_SFC_SW_DWN', 'PRECTOTCORR', 'ETo').
    - lang: Idioma para traduções ('pt' ou 'en').

    Retorna:
    - html.Div contendo a tabela formatada.
    """
    try:
        return display_results_table(df, lang=lang)
    except Exception as e:
        logger.error(f"Erro ao exibir dados diários: {str(e)}")
        t = get_translations(lang)
        return html.Div(f"{t.get('results', {}).get('error', 'Erro')}: {str(e)}")


def display_descriptive_stats(df: pd.DataFrame, lang: str = "pt", mode: str = "") -> html.Div:
    """
    Exibe estatísticas descritivas para as variáveis numéricas.

    Parâmetros:
    - df: DataFrame com os dados.
    - lang: Idioma para traduções ('pt' ou 'en').
    - mode: Modo de operação. Se 'DASHBOARD_FORECAST', oculta CV,
            Skewness e Kurtosis (amostra insuficiente).

    Retorna:
    - html.Div contendo a tabela de estatísticas.
    """
    try:
        if df is None or df.empty:
            logger.warning(
                "DataFrame vazio ou None fornecido para "
                "display_descriptive_stats"
            )
            return html.Div(get_translations(lang).get("results", {}).get("no_data", "Sem dados disponíveis"))

        t = get_translations(lang)
        dv = t.get("data_variables", {})
        st = t.get("statistics", {})

        # Mapeamento de nomes de colunas para nomes formatados
        column_display_names = {
            "T2M_MAX": dv.get("temp_max", "Temperatura Máxima (°C)"),
            "T2M_MIN": dv.get("temp_min", "Temperatura Mínima (°C)"),
            "T2M": dv.get("temp_mean", "Temperatura Média (°C)"),
            "RH2M": dv.get("humidity", "Umidade Relativa (%)"),
            "WS2M": dv.get("wind_speed", "Velocidade do Vento (m/s)"),
            "ALLSKY_SFC_SW_DWN": dv.get(
                "radiation", "Radiação Solar (MJ/m²/dia)"
            ),
            "PRECTOTCORR": dv.get("precipitation", "Precipitação Total (mm)"),
            "ETo": dv.get("eto", "ETo (mm/dia)"),
            "eto_evaonline": dv.get("eto_evaonline", "ETo EVAonline (mm/dia)"),
            "eto_openmeteo": dv.get("eto_openmeteo", "ETo Open-Meteo (mm/dia)"),
        }

        expected_columns = [
            "T2M_MAX",
            "T2M_MIN",
            "RH2M",
            "WS2M",
            "ALLSKY_SFC_SW_DWN",
            "PRECTOTCORR",
            "ETo",
            "eto_evaonline",
        ]
        numeric_cols = [col for col in expected_columns if col in df.columns]
        if not numeric_cols:
            logger.error("Nenhuma coluna numérica válida encontrada")
            raise ValueError("Nenhuma coluna numérica válida encontrada")

        stats_data = {
            st.get("mean", "Média"): df[numeric_cols].mean().round(2),
            st.get("max", "Máximo"): df[numeric_cols].max().round(2),
            st.get("min", "Mínimo"): df[numeric_cols].min().round(2),
            st.get("median", "Mediana"): df[numeric_cols].median().round(2),
            st.get("std_dev", "Desvio Padrão"): df[numeric_cols].std().round(2),
            st.get("percentile_25", "Percentil 25%"): df[numeric_cols].quantile(0.25).round(2),
            st.get("percentile_75", "Percentil 75%"): df[numeric_cols].quantile(0.75).round(2),
        }

        # CV, Skewness e Kurtosis só para amostras >= 30 dias
        n_days = len(df)
        has_enough_samples = n_days >= 30 and mode != "DASHBOARD_FORECAST"
        if has_enough_samples:
            stats_data[st.get("coef_variation", "CV (%)")] = (
                (df[numeric_cols].std() / df[numeric_cols].mean()) * 100
            ).round(2)
            stats_data[st.get("skewness", "Assimetria")] = df[numeric_cols] \
                .apply(lambda x: stats.skew(x.dropna())).round(2)
            stats_data[st.get("kurtosis", "Curtose")] = df[numeric_cols] \
                .apply(lambda x: stats.kurtosis(x.dropna())).round(2)
        stats_df = pd.DataFrame(stats_data).T
        stats_df.insert(0, st.get("statistic", "Estatística"), stats_df.index)

        # Renomear colunas com nomes formatados
        stats_df = stats_df.rename(columns=column_display_names)

        # Formatar valores numéricos com ponto decimal
        statistic_col = st.get("statistic", "Estatística")
        for col in stats_df.columns:
            if col != statistic_col:
                stats_df[col] = stats_df[col].apply(
                    lambda x: format_number(x, 2)
                )

        # Criar tabela com estilo profissional
        table = dbc.Table(
            [
                html.Thead(
                    html.Tr(
                        [
                            html.Th(
                                col,
                                className="text-center bg-primary text-white",
                            )
                            for col in stats_df.columns
                        ]
                    )
                )
            ]
            + [
                html.Tbody(
                    [
                        html.Tr(
                            [
                                html.Td(
                                    stats_df.iloc[i][col],
                                    className="text-center",
                                )
                                for col in stats_df.columns
                            ]
                        )
                        for i in range(len(stats_df))
                    ]
                )
            ],
            striped=True,
            bordered=True,
            hover=True,
            responsive=True,
            className="table table-sm shadow-sm",
        )
        logger.info("Tabela de estatísticas descritivas gerada com sucesso")
        return html.Div([table], className="mb-4")  # Espaçamento inferior

    except Exception as e:
        logger.error(f"Erro ao gerar estatísticas descritivas: {str(e)}")
        rs = get_translations(lang).get("results", {})
        return html.Div(f"{rs.get('error', 'Erro')}: {str(e)}")


def display_normality_test(df: pd.DataFrame, lang: str = "pt", mode: str = "") -> html.Div:
    """
    Exibe o teste de normalidade Shapiro-Wilk.

    Parâmetros:
    - df: DataFrame com os dados.
    - lang: Idioma para traduções ('pt' ou 'en').
    - mode: Modo de operação. Se 'DASHBOARD_FORECAST', exibe aviso
            informando que a amostra é insuficiente.

    Retorna:
    - html.Div com a tabela e nota explicativa.
    """
    try:
        if df is None or df.empty:
            logger.warning(
                "DataFrame vazio ou None fornecido para display_normality_test"
            )
            return html.Div(get_translations(lang).get("results", {}).get("no_data", "Sem dados disponíveis"))

        # Amostra insuficiente para Shapiro-Wilk (forecast ou < 30 dias)
        n_days = len(df)
        if mode == "DASHBOARD_FORECAST" or n_days < 30:
            t_fc = get_translations(lang)
            st_fc = t_fc.get("statistics", {})
            if mode == "DASHBOARD_FORECAST":
                msg = st_fc.get(
                    "forecast_sample_insufficient",
                    "Test not performed: insufficient sample size for forecast mode (6 days)."
                    if lang == "en" else
                    "Teste não realizado: amostra insuficiente para o modo previsão (6 dias)."
                )
            else:
                msg = st_fc.get(
                    "sample_insufficient",
                    "Not calculated: at least 30 days required. Currently: {days} days."
                ).format(days=n_days)
            return html.Div(
                dbc.Alert(msg, color="info", className="mt-2"),
                className="mb-4",
            )

        t = get_translations(lang)
        dv = t.get("data_variables", {})
        st = t.get("statistics", {})

        # Mapeamento de nomes de colunas para nomes formatados
        column_display_names = {
            "T2M_MAX": dv.get("temp_max", "Temperatura Máxima (°C)"),
            "T2M_MIN": dv.get("temp_min", "Temperatura Mínima (°C)"),
            "T2M": dv.get("temp_mean", "Temperatura Média (°C)"),
            "RH2M": dv.get("humidity", "Umidade Relativa (%)"),
            "WS2M": dv.get("wind_speed", "Velocidade do Vento (m/s)"),
            "ALLSKY_SFC_SW_DWN": dv.get(
                "radiation", "Radiação Solar (MJ/m²/dia)"
            ),
            "PRECTOTCORR": dv.get("precipitation", "Precipitação Total (mm)"),
            "ETo": dv.get("eto", "ETo (mm/dia)"),
            "eto_evaonline": dv.get("eto_evaonline", "ETo EVAonline (mm/dia)"),
            "eto_openmeteo": dv.get("eto_openmeteo", "ETo Open-Meteo (mm/dia)"),
        }

        # Support both old 'ETo' and new 'eto_evaonline' column names
        eto_col = "eto_evaonline" if "eto_evaonline" in df.columns else "ETo"
        expected_columns = [
            "T2M_MAX",
            "T2M_MIN",
            "RH2M",
            "WS2M",
            "ALLSKY_SFC_SW_DWN",
            "PRECTOTCORR",
            eto_col,
        ]
        numeric_cols = [col for col in expected_columns if col in df.columns]
        if not numeric_cols:
            logger.error("Nenhuma coluna numérica válida encontrada")
            raise ValueError("Nenhuma coluna numérica válida encontrada")

        normality_tests = {}
        for col in numeric_cols:
            stat, p_value = stats.shapiro(df[col].dropna())
            # Usar nome formatado da coluna
            display_name = column_display_names.get(col, col)
            normality_tests[display_name] = {
                st.get("statistic", "Estatística"): format_number(stat, 2),
                st.get("p_value", "P-Valor"): format_number(p_value, 4),
            }
        normality_df = pd.DataFrame(normality_tests).T
        normality_df.insert(0, st.get("variable", "Variável"), normality_df.index)

        # Criar tabela com estilo profissional
        table = dbc.Table(
            [
                html.Thead(
                    html.Tr(
                        [
                            html.Th(
                                col,
                                className="text-center bg-primary text-white",
                            )
                            for col in normality_df.columns
                        ]
                    )
                )
            ]
            + [
                html.Tbody(
                    [
                        html.Tr(
                            [
                                html.Td(
                                    normality_df.iloc[i][col],
                                    className="text-center",
                                )
                                for col in normality_df.columns
                            ]
                        )
                        for i in range(len(normality_df))
                    ]
                )
            ],
            striped=True,
            bordered=True,
            hover=True,
            responsive=True,
            className="table table-sm shadow-sm",
        )
        logger.info("Tabela de teste de normalidade gerada com sucesso")
        return html.Div(
            [
                table,
                html.P(st.get("normality_note", ""), className="text-muted small mt-2"),
            ],
            className="mb-4",
        )

    except Exception as e:
        logger.error(f"Erro ao gerar teste de normalidade: {str(e)}")
        rs = get_translations(lang).get("results", {})
        return html.Div(f"{rs.get('error', 'Erro')}: {str(e)}")


def display_correlation_matrix(df: pd.DataFrame, lang: str = "pt") -> html.Div:
    """
    Exibe a matriz de correlação entre as variáveis.

    Parâmetros:
    - df: DataFrame com os dados.
    - lang: Idioma para traduções ('pt' ou 'en').

    Retorna:
    - html.Div com a tabela de correlação.
    """
    try:
        if df is None or df.empty:
            logger.warning(
                "DataFrame vazio ou None fornecido para "
                "display_correlation_matrix"
            )
            return html.Div(get_translations(lang).get("results", {}).get("no_data", "Sem dados disponíveis"))

        t = get_translations(lang)
        dv = t.get("data_variables", {})
        # Support both old 'ETo' and new 'eto_evaonline' column names
        eto_col = "eto_evaonline" if "eto_evaonline" in df.columns else "ETo"
        expected_columns = [
            "T2M_MAX",
            "T2M_MIN",
            "RH2M",
            "WS2M",
            "ALLSKY_SFC_SW_DWN",
            "PRECTOTCORR",
            eto_col,
        ]
        numeric_cols = [col for col in expected_columns if col in df.columns]
        if not numeric_cols:
            logger.error("Nenhuma coluna numérica válida encontrada")
            raise ValueError("Nenhuma coluna numérica válida encontrada")

        corr_df = df[numeric_cols].corr().round(2)
        corr_df = corr_df.rename(
            columns=lambda x: dv.get(x.lower(), x),
            index=lambda x: dv.get(x.lower(), x),
        )

        # Criar tabela manualmente
        table = dbc.Table(
            [html.Thead(html.Tr([html.Th(col) for col in corr_df.columns]))]
            + [
                html.Tbody(
                    [
                        html.Tr(
                            [
                                html.Td(corr_df.iloc[i][col])
                                for col in corr_df.columns
                            ]
                        )
                        for i in range(len(corr_df))
                    ]
                )
            ],
            striped=True,
            bordered=True,
            hover=True,
            responsive=True,
            className="table table-sm",
        )
        logger.info("Matriz de correlação gerada com sucesso")
        return html.Div([table])  # Title added by layout

    except Exception as e:
        logger.error(f"Erro ao gerar matriz de correlação: {str(e)}")
        rs = get_translations(lang).get("results", {})
        return html.Div(f"{rs.get('error', 'Erro')}: {str(e)}")


def display_eto_summary(df: pd.DataFrame, lang: str = "pt") -> html.Div:
    """
    Exibe tabela de balanço hídrico diário (apenas a tabela).

    Parâmetros:
    - df: DataFrame com os dados (espera colunas 'date', 'PRECTOTCORR', 'ETo').
    - lang: Idioma para traduções ('pt' ou 'en').

    Retorna:
    - html.Div com a tabela de balanço hídrico.
    """
    try:
        if df is None or df.empty:
            logger.warning(
                "DataFrame vazio ou None fornecido para display_eto_summary"
            )
            return html.Div(get_translations(lang).get("results", {}).get("no_data", "Sem dados disponíveis"))

        t = get_translations(lang)
        dv = t.get("data_variables", {})
        st = t.get("statistics", {})

        # Support both old 'ETo' and new 'eto_evaonline' column names
        eto_col = "eto_evaonline" if "eto_evaonline" in df.columns else "ETo"
        expected_columns = ["date", "PRECTOTCORR", eto_col]
        missing_columns = [
            col for col in expected_columns if col not in df.columns
        ]
        if missing_columns:
            logger.error(f"Colunas ausentes no DataFrame: {missing_columns}")
            return html.Div(t.get("results", {}).get("no_data", "Sem dados disponíveis"))

        df_display = df[["date", "PRECTOTCORR", eto_col]].copy()
        df_display["date"] = pd.to_datetime(df_display["date"]).dt.strftime(
            "%d/%m/%Y"
        )

        # Calcular déficit hídrico
        deficit_col = st.get("water_deficit", "Déficit Hídrico (mm)")
        df_display[deficit_col] = (
            df_display["PRECTOTCORR"] - df_display[eto_col]
        )

        # Formatar valores numéricos com ponto decimal
        for col in [c for c in df_display.columns if c != "date"]:
            df_display[col] = df_display[col].apply(
                lambda x: format_number(x, 2)
            )

        # Renomear colunas para exibição
        eto_display_name = dv.get("eto_evaonline", "ETo EVAonline (mm/dia)")
        df_renamed = df_display.rename(
            columns={
                "date": dv.get("date", "Data"),
                "PRECTOTCORR": dv.get("precipitation", "Precipitação Total (mm)"),
                eto_col: eto_display_name,
            }
        )

        # Criar tabela com cores condicionais para déficit
        # Cabeçalho
        header = html.Thead(
            html.Tr(
                [
                    html.Th(col, className="text-center bg-primary text-white")
                    for col in df_renamed.columns
                ]
            )
        )

        # Corpo com cores condicionais na coluna de déficit
        rows = []
        for i in range(len(df_renamed)):
            cells = []
            for col in df_renamed.columns:
                value = df_renamed.iloc[i][col]
                # Aplicar cor condicional apenas na coluna de déficit
                if col == deficit_col:
                    # Converter para float para comparação
                    try:
                        num_value = float(value)
                    except (ValueError, TypeError):
                        num_value = 0

                    if num_value < 0:
                        # Déficit (falta de água) - vermelho
                        cell = html.Td(
                            value,
                            className="text-center",
                            style={
                                "backgroundColor": "#ffcccc",
                                "color": "#c00000",
                                "fontWeight": "bold",
                            },
                        )
                    elif num_value > 0:
                        # Excesso (água disponível) - verde
                        cell = html.Td(
                            value,
                            className="text-center",
                            style={
                                "backgroundColor": "#ccffcc",
                                "color": "#008000",
                                "fontWeight": "bold",
                            },
                        )
                    else:
                        cell = html.Td(value, className="text-center")
                else:
                    cell = html.Td(value, className="text-center")
                cells.append(cell)
            rows.append(html.Tr(cells))

        body = html.Tbody(rows)

        table = dbc.Table(
            [header, body],
            striped=True,
            bordered=True,
            hover=True,
            responsive=True,
            className="table table-sm shadow-sm",
        )

        logger.info("Tabela de balanço hídrico gerada com sucesso")
        return html.Div([table], className="mb-4")

    except Exception as e:
        logger.error(f"Erro ao gerar resumo de ETo: {str(e)}")
        rs = get_translations(lang).get("results", {})
        return html.Div(f"{rs.get('error', 'Erro')}: {str(e)}")


def create_deficit_chart_section(
    df: pd.DataFrame, lang: str = "pt"
) -> html.Div:
    """
    Cria seção com gráfico de déficit hídrico e estatísticas.

    Parâmetros:
    - df: DataFrame com os dados.
    - lang: Idioma para traduções.

    Retorna:
    - html.Div com gráfico e estatísticas de déficit.
    """
    try:
        if df is None or df.empty:
            return html.Div("No data available")

        t = get_translations(lang)
        dv = t.get("data_variables", {})
        st = t.get("statistics", {})
        ch = t.get("charts", {})

        # Support both old 'ETo' and new 'eto_evaonline' column names
        eto_col = "eto_evaonline" if "eto_evaonline" in df.columns else "ETo"

        df_display = df[["date", "PRECTOTCORR", eto_col]].copy()
        df_display["date"] = pd.to_datetime(df_display["date"]).dt.strftime(
            "%d/%m/%Y"
        )

        # Calcular déficit hídrico
        deficit_col = st.get("water_deficit", "Déficit Hídrico (mm)")
        df_display[deficit_col] = (
            df_display["PRECTOTCORR"] - df_display[eto_col]
        ).round(2)

        # Estatísticas
        deficit_mean = round(df_display[deficit_col].mean(), 2)
        deficit_total = round(df_display[deficit_col].sum(), 2)
        days_with_deficit = len(df_display[df_display[deficit_col] < 0])
        days_with_excess = len(df_display[df_display[deficit_col] > 0])

        # Preparar dados para gráfico
        deficiency_label = st.get("deficiency", "Deficiency")
        surplus_label = st.get("surplus", "Surplus")
        df_display[deficiency_label] = df_display[deficit_col].apply(
            lambda x: min(0, x) if x < 0 else 0
        )
        df_display[surplus_label] = df_display[deficit_col].apply(
            lambda x: max(0, x) if x > 0 else 0
        )

        # Criar gráfico de déficit
        fig_deficit = px.area(
            df_display,
            x="date",
            y=[deficiency_label, surplus_label],
            title=st.get("daily_water_deficit", "Daily Water Deficit"),
            labels={"value": st.get("mm_day_unit", "mm/day"), "variable": "Component"},
            color_discrete_map={
                deficiency_label: "#dc3545",
                surplus_label: "#27AE60",
            },
        )
        fig_deficit.update_layout(
            font=dict(family="Segoe UI, Roboto, Arial, sans-serif", size=18),
            title_font=dict(size=26, family="Segoe UI, Roboto, Arial, sans-serif"),
            yaxis_title=dict(text=f"<b>{st.get('water_deficit_mm_day', 'Water Deficit (mm/day)')}</b>", font=dict(size=22)),
            xaxis_title=dict(text=f"<b>{ch.get('date_label', 'Date')}</b>", font=dict(size=22)),
            xaxis=dict(tickfont=dict(size=18), showgrid=True, gridcolor="rgba(0,0,0,0.12)"),
            yaxis=dict(tickfont=dict(size=18), showgrid=True, gridcolor="rgba(0,0,0,0.15)"),
            legend_title=dict(text=ch.get("legend", "Legend"), font=dict(size=20)),
            template="plotly_white",
            height=500,
            margin={"b": 80, "t": 60, "l": 70, "r": 30},
            hoverlabel=dict(font_size=17),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="center",
                x=0.5,
                font=dict(size=20),
            ),
        )

        return html.Div(
            [
                # Estatísticas em cards
                dbc.Row(
                    [
                        dbc.Col(
                            dbc.Card(
                                dbc.CardBody(
                                    [
                                        html.H6(
                                            st.get("deficit_mean", "Mean Deficit"),
                                            className="text-muted mb-1",
                                        ),
                                        html.H4(
                                            f"{deficit_mean} {st.get('mm_day_unit', 'mm/day')}",
                                            className="text-danger mb-0",
                                        ),
                                    ]
                                ),
                                className="text-center shadow-sm",
                            ),
                            md=3,
                            className="mb-3",
                        ),
                        dbc.Col(
                            dbc.Card(
                                dbc.CardBody(
                                    [
                                        html.H6(
                                            st.get("deficit_total", "Total Deficit"),
                                            className="text-muted mb-1",
                                        ),
                                        html.H4(
                                            f"{deficit_total} {st.get('mm_unit', 'mm')}",
                                            className="text-danger mb-0",
                                        ),
                                    ]
                                ),
                                className="text-center shadow-sm",
                            ),
                            md=3,
                            className="mb-3",
                        ),
                        dbc.Col(
                            dbc.Card(
                                dbc.CardBody(
                                    [
                                        html.H6(
                                            st.get("days_with_deficit", "Days with Deficit"),
                                            className="text-muted mb-1",
                                        ),
                                        html.H4(
                                            f"{days_with_deficit} {st.get('days_unit', 'days')}",
                                            className="text-warning mb-0",
                                        ),
                                    ]
                                ),
                                className="text-center shadow-sm",
                            ),
                            md=3,
                            className="mb-3",
                        ),
                        dbc.Col(
                            dbc.Card(
                                dbc.CardBody(
                                    [
                                        html.H6(
                                            st.get("days_with_excess", "Days with Excess"),
                                            className="text-muted mb-1",
                                        ),
                                        html.H4(
                                            f"{days_with_excess} {st.get('days_unit', 'days')}",
                                            className="text-success mb-0",
                                        ),
                                    ]
                                ),
                                className="text-center shadow-sm",
                            ),
                            md=3,
                            className="mb-3",
                        ),
                    ],
                    className="mb-3",
                ),
                # Gráfico
                dcc.Graph(
                    id="chart-deficit",
                    figure=fig_deficit,
                    config={"displayModeBar": False},
                    style={"height": "400px"},
                ),
                # Nota explicativa
                html.P(
                    st.get("deficit_note", ""),
                    className="text-muted small fst-italic mt-2",
                ),
            ]
        )

    except Exception as e:
        logger.error(f"Erro ao criar seção de déficit: {str(e)}")
        return html.Div(f"Erro: {str(e)}")


def display_trend_analysis(df: pd.DataFrame, lang: str = "pt") -> html.Div:
    """
    Exibe a tendência temporal da ETo.

    Parâmetros:
    - df: DataFrame com os dados (espera colunas 'date', 'ETo').
    - lang: Idioma para traduções ('pt' ou 'en').

    Retorna:
    - html.Div com a tendência.
    """
    try:
        if df is None or df.empty:
            logger.warning(
                "DataFrame vazio ou None fornecido para display_trend_analysis"
            )
            return html.Div(get_translations(lang).get("results", {}).get("no_data", "Sem dados disponíveis"))

        t = get_translations(lang)
        st = t.get("statistics", {})
        if "date" not in df.columns or "ETo" not in df.columns:
            logger.error("Colunas 'date' ou 'ETo' ausentes no DataFrame")
            raise ValueError("Colunas 'date' ou 'ETo' ausentes no DataFrame")

        dates_numeric = pd.to_numeric(
            pd.to_datetime(df["date"]).map(lambda x: x.toordinal())
        )
        slope, intercept = np.polyfit(dates_numeric, df["ETo"], 1)
        logger.info("Análise de tendência gerada com sucesso")
        return html.Div(
            [
                html.H5(st.get("trend_analysis", "Análise de Tendência")),
                html.P(
                    f"{st.get('eto_trend', 'Tendência da ETo')}: {slope.round(4)} mm/dia {st.get('per_day', 'por dia')}"
                ),
            ]
        )

    except Exception as e:
        logger.error(f"Erro ao gerar análise de tendência: {str(e)}")
        rs = get_translations(lang).get("results", {})
        return html.Div(f"{rs.get('error', 'Erro')}: {str(e)}")


def display_seasonality_test(df: pd.DataFrame, lang: str = "pt") -> html.Div:
    """
    Exibe o teste de estacionalidade (ADF) para ETo.

    Parâmetros:
    - df: DataFrame com os dados (espera coluna 'ETo').
    - lang: Idioma para traduções ('pt' ou 'en').

    Retorna:
    - html.Div com o resultado do teste.
    """
    try:
        if df is None or df.empty:
            logger.warning(
                "DataFrame vazio ou None fornecido para "
                "display_seasonality_test"
            )
            return html.Div(get_translations(lang).get("results", {}).get("no_data", "Sem dados disponíveis"))

        t = get_translations(lang)
        st = t.get("statistics", {})
        if "ETo" not in df.columns:
            logger.error("Coluna 'ETo' ausente no DataFrame")
            raise ValueError("Coluna 'ETo' ausente no DataFrame")

        result = adfuller(df["ETo"].dropna())
        p_value = float(result[1])
        logger.info(
            f"Teste de estacionalidade (ADF) gerado com sucesso: "
            f"p-valor = {p_value:.4f}"
        )
        return html.Div(
            [
                html.H5(st.get("seasonality_test", "Teste de Estacionalidade")),
                html.P(f"{st.get('adf_test', 'Teste ADF')}: p-valor = {p_value:.4f}"),
            ]
        )

    except Exception as e:
        logger.error(f"Erro ao gerar teste de estacionalidade: {str(e)}")
        rs = get_translations(lang).get("results", {})
        return html.Div(f"{rs.get('error', 'Erro')}: {str(e)}")


def display_cumulative_distribution(
    df: pd.DataFrame, lang: str = "pt"
) -> html.Div:
    """
    Exibe a distribuição acumulada de ETo e precipitação.

    Parâmetros:
    - df: DataFrame com os dados (espera colunas 'date', 'PRECTOTCORR', 'ETo').
    - lang: Idioma para traduções ('pt' ou 'en').

    Retorna:
    - html.Div com a tabela de distribuição acumulada.
    """
    try:
        if df is None or df.empty:
            logger.warning(
                "DataFrame vazio ou None fornecido para "
                "display_cumulative_distribution"
            )
            return html.Div(get_translations(lang).get("results", {}).get("no_data", "Sem dados disponíveis"))

        t = get_translations(lang)
        dv = t.get("data_variables", {})
        st = t.get("statistics", {})

        # Support both old 'ETo' and new 'eto_evaonline' column names
        eto_col = "eto_evaonline" if "eto_evaonline" in df.columns else "ETo"
        expected_columns = ["date", "PRECTOTCORR", eto_col]
        missing_columns = [
            col for col in expected_columns if col not in df.columns
        ]
        if missing_columns:
            logger.error(f"Colunas ausentes no DataFrame: {missing_columns}")
            return html.Div(t.get("results", {}).get("no_data", "Sem dados disponíveis"))

        df_display = df[["date", "PRECTOTCORR", eto_col]].copy()
        df_display["date"] = pd.to_datetime(df_display["date"]).dt.strftime(
            "%d/%m/%Y"
        )
        df_display[st.get("cumulative_eto", "ETo Acumulada (mm)")] = df_display[eto_col].cumsum().round(2)
        df_display[st.get("cumulative_precipitation", "Precipitação Acumulada (mm)")] = (
            df_display["PRECTOTCORR"].cumsum().round(2)
        )

        # Renomear colunas para exibição
        df_renamed = df_display.rename(
            columns={
                "date": dv.get("date", "Data"),
                "PRECTOTCORR": dv.get("precipitation", "Precipitação Total (mm)"),
                eto_col: dv.get("eto", "ETo (mm/dia)"),
            }
        )

        # Criar tabela manualmente
        table = dbc.Table(
            [html.Thead(html.Tr([html.Th(col) for col in df_renamed.columns]))]
            + [
                html.Tbody(
                    [
                        html.Tr(
                            [
                                html.Td(df_renamed.iloc[i][col])
                                for col in df_renamed.columns
                            ]
                        )
                        for i in range(len(df_renamed))
                    ]
                )
            ],
            striped=True,
            bordered=True,
            hover=True,
            responsive=True,
            className="table table-sm",
        )
        logger.info("Tabela de distribuição acumulada gerada com sucesso")
        return html.Div([html.H5(st.get("cumulative_distribution", "Distribuição Acumulada")), table])

    except Exception as e:
        logger.error(f"Erro ao gerar distribuição acumulada: {str(e)}")
        rs = get_translations(lang).get("results", {})
        return html.Div(f"{rs.get('error', 'Erro')}: {str(e)}")
