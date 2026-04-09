import dash_bootstrap_components as dbc
import pandas as pd
from dash import html
from loguru import logger

from shared_utils.get_translations import get_translations


def format_number(value, decimals: int = 2) -> str:
    """
    Formata número com ponto como separador decimal (padrão internacional).

    Args:
        value: Valor numérico a formatar
        decimals: Número de casas decimais

    Returns:
        String formatada com ponto decimal
    """
    if pd.isna(value):
        return "-"
    try:
        return f"{float(value):.{decimals}f}"
    except (ValueError, TypeError):
        return str(value)


def display_results_table(df: pd.DataFrame, lang: str = "pt") -> html.Div:
    """
    Prepara e retorna uma tabela formatada de resultados de ET₀ para
    exibição no Dash.

    Parâmetros:
    - df: DataFrame com os resultados do cálculo de ETo.
    - lang: Idioma para tradução das colunas ('pt' ou 'en').

    Retorna:
    - html.Div contendo a tabela formatada com dbc.Table.
    """
    try:
        # Validar DataFrame
        if df is None or df.empty:
            logger.warning(
                "DataFrame vazio ou None fornecido para display_results_table"
            )
            return html.Div("Nenhum dado disponível para exibição")

        # Criar uma cópia do DataFrame
        df_display = df.copy()

        # Colunas a exibir (simplificado - sem comparações)
        expected_columns = [
            "date",
            "T2M_MAX",
            "T2M_MIN",
            "RH2M",
            "WS2M",
            "ALLSKY_SFC_SW_DWN",
            "PRECTOTCORR",
            "eto_evaonline",  # ETo EVAonline (nossa)
            "ETo",  # Retrocompatibilidade
        ]

        # Selecionar apenas colunas disponíveis
        available_columns = [
            col for col in expected_columns if col in df_display.columns
        ]

        # Garantir que ao menos date e uma ETo existam
        if "date" not in available_columns:
            logger.error("Coluna 'date' ausente no DataFrame")
            raise ValueError("Coluna 'date' é obrigatória")

        has_eto = any(
            col in available_columns
            for col in ["eto_evaonline", "eto_openmeteo", "ETo"]
        )
        if not has_eto:
            logger.error("Nenhuma coluna ETo encontrada")
            raise ValueError("Ao menos uma coluna ETo é necessária")

        # Selecionar colunas relevantes
        df_display = df_display[available_columns]

        # Obter traduções (translations already include units)
        t = get_translations(lang)
        dv = t.get("data_variables", {})
        column_names = {
            "date": dv.get("date", "Data"),
            "T2M_MAX": dv.get("temp_max", "Temperatura Máxima (°C)"),
            "T2M_MIN": dv.get("temp_min", "Temperatura Mínima (°C)"),
            "RH2M": dv.get("humidity", "Umidade Relativa (%)"),
            "WS2M": dv.get("wind_speed", "Velocidade do Vento (m/s)"),
            "ALLSKY_SFC_SW_DWN": dv.get("radiation", "Radiação Solar (MJ/m²/dia)"),
            "PRECTOTCORR": dv.get("precipitation", "Precipitação Total (mm)"),
            "ETo": dv.get("eto", "ETo (mm/dia)"),
            "eto_evaonline": dv.get("eto_evaonline", "ETo EVAonline (mm/dia)"),
        }

        # Formatar a coluna de data ANTES de renomear
        df_display["date"] = pd.to_datetime(df_display["date"]).dt.strftime(
            "%d/%m/%Y"
        )

        # Renomear colunas
        df_display = df_display.rename(columns=column_names)

        # Formatar valores numéricos com ponto decimal (padrão internacional)
        date_col_name = column_names.get("date", "Data")
        for col in df_display.columns:
            if col != date_col_name:
                df_display[col] = df_display[col].apply(
                    lambda x: format_number(x, 2)
                )

        # Criar tabela com Dash Bootstrap Components - Design profissional
        table = dbc.Table(
            # Cabeçalho com estilo profissional
            [
                html.Thead(
                    html.Tr(
                        [
                            html.Th(
                                col,
                                className="text-center bg-primary text-white",
                            )
                            for col in df_display.columns
                        ]
                    ),
                    className="sticky-top",
                )
            ]
            # Corpo
            + [
                html.Tbody(
                    [
                        html.Tr(
                            [
                                html.Td(
                                    df_display.iloc[i][col],
                                    className="text-center",
                                )
                                for col in df_display.columns
                            ]
                        )
                        for i in range(len(df_display))
                    ]
                )
            ],
            striped=True,
            bordered=True,
            hover=True,
            responsive=True,
            className="table table-sm shadow-sm",
        )

        logger.info("Tabela de resultados formatada com sucesso")
        return html.Div([table])

    except Exception as e:
        logger.error(f"Erro ao formatar tabela de resultados: {str(e)}")
        return html.Div(f"Erro ao exibir tabela: {str(e)}")
