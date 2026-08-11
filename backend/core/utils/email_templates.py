"""
Templates HTML para emails do EVAonline.
Bilingual support: English (en) and Portuguese (pt).

Similar ao fluxo do BDMEP/INMET:
1. Email de confirmação: Solicitação recebida, processamento iniciado
2. Email final: Dados processados com link de download (48h)
"""

from datetime import datetime
from typing import Optional


# ============================================================================
# TRANSLATION DICTIONARIES
# ============================================================================

_EMAIL_TRANSLATIONS = {
    # Header / Footer
    "header_subtitle": {
        "en": "Web-based global reference EVApotranspiration estimate",
        "pt": "Web-based global reference EVApotranspiration estimate",
    },
    "footer_method": {
        "en": "FAO-56 Penman-Monteith method | This is an automated email.",
        "pt": "FAO-56 Penman-Monteith method | Este é um email automático.",
    },

    # Common labels
    "location": {"en": "Location", "pt": "Localização"},
    "period": {"en": "Period", "pt": "Período"},
    "requested_period": {"en": "Requested Period", "pt": "Período Solicitado"},
    "file_format": {"en": "File Format", "pt": "Formato do Arquivo"},
    "request_datetime": {
        "en": "Request Date/Time",
        "pt": "Data/Hora da Solicitação",
    },
    "request_details": {
        "en": "Request Details",
        "pt": "Detalhes da Solicitação",
    },
    "days": {"en": "days", "pt": "dias"},
    "day": {"en": "day", "pt": "dia"},
    "to": {"en": "to", "pt": "a"},
    "at": {"en": "at", "pt": "às"},
    "format_excel": {"en": "Excel (.xlsx)", "pt": "Excel (.xlsx)"},
    "format_csv": {"en": "CSV (.csv)", "pt": "CSV (.csv)"},
    "elevation": {"en": "Elevation", "pt": "Elevação"},
    "elevation_auto": {
        "en": "Obtained automatically",
        "pt": "Obtida automaticamente",
    },

    # Processing started email
    "started_subject": {
        "en": "📊 EVAonline - Request Received | Processing Started",
        "pt": "📊 EVAonline - Solicitação Recebida | Processamento Iniciado",
    },
    "started_title": {
        "en": "✅ Request Received Successfully!",
        "pt": "✅ Solicitação Recebida com Sucesso!",
    },
    "started_body": {
        "en": (
            "Your request for reference evapotranspiration (ETo) data has been "
            "received and is being processed by <strong>EVAonline</strong>."
        ),
        "pt": (
            "Sua solicitação de dados de evapotranspiração de referência (ETo) foi "
            "recebida e está sendo processada pelo <strong>EVAonline</strong>."
        ),
    },
    "started_next_steps_title": {
        "en": "⏳ Next steps:",
        "pt": "⏳ Próximos passos:",
    },
    "started_next_steps_body": {
        "en": (
            "You will receive another email with a download link once "
            "processing is complete. The estimated time is 1 to 5 minutes, "
            "depending on the requested period."
        ),
        "pt": (
            "Você receberá outro email com um link de download assim que o "
            "processamento for concluído. O tempo estimado é de 1 a 5 minutos, "
            "dependendo do período solicitado."
        ),
    },
    "started_spam_notice": {
        "en": (
            "If you do not receive the email with data within 15 minutes, "
            "check your spam folder or try again."
        ),
        "pt": (
            "Caso não receba o email com os dados em até 15 minutos, verifique "
            "sua pasta de spam ou tente novamente."
        ),
    },

    # Data ready email
    "ready_subject": {
        "en": "📊 EVAonline - Your Data is Ready! | Download Available",
        "pt": "📊 EVAonline - Seus Dados Estão Prontos! | Download Disponível",
    },
    "ready_title": {
        "en": "🎉 Your Data is Ready!",
        "pt": "🎉 Seus Dados Estão Prontos!",
    },
    "ready_body": {
        "en": (
            "The processing of your reference evapotranspiration (ETo) data "
            "has been completed successfully. Use the download button below "
            "to get your file (link valid for 48 hours)."
        ),
        "pt": (
            "O processamento dos seus dados de evapotranspiração de referência (ETo) "
            "foi concluído com sucesso. Use o botão de download abaixo para "
            "obter o arquivo (link válido por 48 horas)."
        ),
    },
    "ready_success": {
        "en": "✅ Processing Completed Successfully!",
        "pt": "✅ Processamento Concluído com Sucesso!",
    },
    "ready_days_processed": {
        "en": "{days} days processed in {seconds:.1f} seconds",
        "pt": "{days} dias processados em {seconds:.1f} segundos",
    },
    "processing_info": {
        "en": "Processing Information",
        "pt": "Informações do Processamento",
    },
    "days_processed": {
        "en": "Days Processed",
        "pt": "Dias Processados",
    },
    "data_sources": {
        "en": "Data Sources",
        "pt": "Fontes de Dados",
    },
    "multiple_sources": {
        "en": "Multiple sources",
        "pt": "Múltiplas fontes",
    },
    "stats_title": {
        "en": "📈 Statistical Summary",
        "pt": "📈 Resumo Estatístico",
    },
    "eto_mean": {"en": "Mean ETo:", "pt": "ETo Médio:"},
    "eto_max": {"en": "Max ETo:", "pt": "ETo Máximo:"},
    "eto_min": {"en": "Min ETo:", "pt": "ETo Mínimo:"},
    "eto_total": {"en": "Total ETo:", "pt": "ETo Total:"},
    "columns_title": {
        "en": "📁 Available Columns in the File:",
        "pt": "📁 Colunas Disponíveis no Arquivo:",
    },
    "col_date": {
        "en": "<strong>date</strong> - Observation date",
        "pt": "<strong>date</strong> - Data da observação",
    },
    "col_temp": {
        "en": "<strong>tmax_c, tmin_c, tmed_c</strong> - Maximum, minimum and mean temperatures (°C)",
        "pt": "<strong>tmax_c, tmin_c, tmed_c</strong> - Temperaturas máxima, mínima e média (°C)",
    },
    "col_humidity": {
        "en": "<strong>humidity_pct</strong> - Mean relative humidity (%)",
        "pt": "<strong>humidity_pct</strong> - Umidade relativa média (%)",
    },
    "col_wind": {
        "en": "<strong>wind_ms</strong> - Wind speed at 2m (m/s)",
        "pt": "<strong>wind_ms</strong> - Velocidade do vento a 2m (m/s)",
    },
    "col_radiation": {
        "en": "<strong>radiation_mj_m2</strong> - Global solar radiation (MJ/m²/day)",
        "pt": "<strong>radiation_mj_m2</strong> - Radiação solar global (MJ/m²/dia)",
    },
    "col_precip": {
        "en": "<strong>precip_mm</strong> - Accumulated precipitation (mm)",
        "pt": "<strong>precip_mm</strong> - Precipitação acumulada (mm)",
    },
    "col_eto": {
        "en": "<strong>et0_mm_day</strong> - Reference evapotranspiration (mm/day)",
        "pt": "<strong>et0_mm_day</strong> - Evapotranspiração de referência (mm/dia)",
    },

    # Error email
    "error_subject": {
        "en": "⚠️ EVAonline - Processing Error | Please Try Again",
        "pt": "⚠️ EVAonline - Erro no Processamento | Tente Novamente",
    },
    "error_title": {
        "en": "⚠️ Processing Error",
        "pt": "⚠️ Erro no Processamento",
    },
    "error_body": {
        "en": (
            "Dear user, unfortunately an error occurred while processing "
            "your data request."
        ),
        "pt": (
            "Caro(a) usuário(a), infelizmente ocorreu um erro ao processar "
            "sua solicitação de dados."
        ),
    },
    "error_details": {
        "en": "❌ Error Details",
        "pt": "❌ Detalhes do Erro",
    },
    "request_id": {
        "en": "Request ID",
        "pt": "ID da Solicitação",
    },
    "suggestions_title": {
        "en": "💡 Suggestions:",
        "pt": "💡 Sugestões:",
    },
    "suggestion_1": {
        "en": "Try reducing the requested period",
        "pt": "Tente reduzir o período solicitado",
    },
    "suggestion_2": {
        "en": "Verify the coordinates are correct",
        "pt": "Verifique se as coordenadas estão corretas",
    },
    "suggestion_3": {
        "en": "Wait a few minutes and try again",
        "pt": "Aguarde alguns minutos e tente novamente",
    },
    "suggestion_4": {
        "en": "If the problem persists, contact us",
        "pt": "Se o problema persistir, entre em contato conosco",
    },
}


def _t(lang: str, key: str) -> str:
    """Get translation for a key."""
    entry = _EMAIL_TRANSLATIONS.get(key, {})
    return entry.get(lang, entry.get("en", key))


# ============================================================================
# HEADER / FOOTER
# ============================================================================


def get_email_header(lang: str = "en") -> str:
    """Retorna o cabeçalho padrão dos emails."""
    return f"""
    <div style="background: linear-gradient(135deg, #1a5f2a 0%, #2d8f4e 100%); 
                padding: 30px 20px; text-align: center; border-radius: 8px 8px 0 0;">
        <h1 style="color: white; margin: 0; font-family: Arial, sans-serif; font-size: 28px;">
            🌱 EVAonline
        </h1>
        <p style="color: #e8f5e9; margin: 10px 0 0 0; font-size: 14px;">
            {_t(lang, "header_subtitle")}
        </p>
    </div>
    """


def get_email_footer(lang: str = "en") -> str:
    """Retorna o rodapé padrão dos emails."""
    return f"""
    <div style="background: #333; color: #999; padding: 20px; text-align: center; 
                border-radius: 0 0 8px 8px; font-family: Arial, sans-serif; font-size: 12px;">
        <p style="margin: 0 0 10px 0;">
            <strong>EVAonline</strong> - {_t(lang, "header_subtitle")}
        </p>
        <p style="margin: 0 0 10px 0; color: #666;">
            {_t(lang, "footer_method")}
        </p>
        <p style="margin: 0; color: #666;">
            © 2024-2026 EVAonline | 
            <a href="https://github.com/evaonlineplatform/EVAONLINE" 
               style="color: #4CAF50; text-decoration: none;">GitHub</a>
        </p>
    </div>
    """


# ============================================================================
# TEMPLATE 1: PROCESSING STARTED
# ============================================================================


def create_processing_started_email(
    task_id: str,
    latitude: float,
    longitude: float,
    start_date: str,
    end_date: str,
    started_at: datetime,
    file_format: str = "excel",
    lang: str = "en",
) -> tuple[str, str]:
    """
    Cria email de confirmação de que o processamento foi iniciado.

    Returns:
        tuple: (subject, html_body)
    """
    subject = _t(lang, "started_subject")

    format_label = (
        _t(lang, "format_excel")
        if file_format == "excel"
        else _t(lang, "format_csv")
    )

    # Calcular número de dias
    from datetime import datetime as dt

    start_dt = dt.strptime(start_date, "%Y-%m-%d")
    end_dt = dt.strptime(end_date, "%Y-%m-%d")
    days = (end_dt - start_dt).days + 1

    # Date/time formatting based on language
    if lang == "pt":
        datetime_str = (
            f"{started_at.strftime('%d/%m/%Y')} "
            f"{_t(lang, 'at')} {started_at.strftime('%H:%M:%S')} (UTC-3)"
        )
    else:
        datetime_str = (
            f"{started_at.strftime('%Y-%m-%d')} "
            f"{_t(lang, 'at')} {started_at.strftime('%H:%M:%S')} (UTC-3)"
        )

    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
    </head>
    <body style="margin: 0; padding: 0; background-color: #f5f5f5; font-family: Arial, sans-serif;">
        <div style="max-width: 600px; margin: 20px auto; background: white; border-radius: 8px; 
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
            
            {get_email_header(lang)}
            
            <div style="padding: 30px;">
                <h2 style="color: #1a5f2a; margin-top: 0;">
                    {_t(lang, "started_title")}
                </h2>
                
                <p style="color: #333; line-height: 1.6;">
                    {_t(lang, "started_body")}
                </p>
                
                <div style="background: #e8f5e9; border-left: 4px solid #4CAF50; 
                            padding: 15px; margin: 20px 0; border-radius: 0 4px 4px 0;">
                    <p style="margin: 0; color: #2e7d32; font-weight: bold;">
                        📋 {_t(lang, "request_details")}
                    </p>
                </div>
                
                <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
                    <tr style="background: #f9f9f9;">
                        <td style="padding: 12px; border: 1px solid #ddd; font-weight: bold; width: 40%;">
                            📍 {_t(lang, "location")}
                        </td>
                        <td style="padding: 12px; border: 1px solid #ddd;">
                            Lat: {latitude:.4f}° | Lon: {longitude:.4f}°
                        </td>
                    </tr>
                    <tr>
                        <td style="padding: 12px; border: 1px solid #ddd; font-weight: bold;">
                            📅 {_t(lang, "requested_period")}
                        </td>
                        <td style="padding: 12px; border: 1px solid #ddd;">
                            {start_date} {_t(lang, "to")} {end_date} ({days} {_t(lang, "days")})
                        </td>
                    </tr>
                    <tr style="background: #f9f9f9;">
                        <td style="padding: 12px; border: 1px solid #ddd; font-weight: bold;">
                            📎 {_t(lang, "file_format")}
                        </td>
                        <td style="padding: 12px; border: 1px solid #ddd;">
                            {format_label}
                        </td>
                    </tr>
                    <tr>
                        <td style="padding: 12px; border: 1px solid #ddd; font-weight: bold;">
                            ⏰ {_t(lang, "request_datetime")}
                        </td>
                        <td style="padding: 12px; border: 1px solid #ddd;">
                            {datetime_str}
                        </td>
                    </tr>
                </table>
                
                <div style="background: #fff3e0; border-left: 4px solid #ff9800; 
                            padding: 15px; margin: 20px 0; border-radius: 0 4px 4px 0;">
                    <p style="margin: 0; color: #e65100;">
                        <strong>{_t(lang, "started_next_steps_title")}</strong><br>
                        {_t(lang, "started_next_steps_body")}
                    </p>
                </div>
                
                <p style="color: #666; font-size: 13px; margin-top: 30px;">
                    {_t(lang, "started_spam_notice")}
                </p>
            </div>
            
            {get_email_footer(lang)}
        </div>
    </body>
    </html>
    """

    return subject, html_body


# ============================================================================
# TEMPLATE 2: DATA READY
# ============================================================================


def create_data_ready_email(
    task_id: str,
    latitude: float,
    longitude: float,
    start_date: str,
    end_date: str,
    days_processed: int,
    processing_time_seconds: float,
    sources_used: list[str],
    file_format: str = "excel",
    elevation: Optional[float] = None,
    summary_stats: Optional[dict] = None,
    lang: str = "en",
    download_url: Optional[str] = None,
    expiry_hours: int = 48,
) -> tuple[str, str]:
    """
    Cria email informando que os dados estão prontos.

    Se ``download_url`` for fornecido, inclui um botão de download (link que
    expira em ``expiry_hours``) em vez de depender de anexo.

    Returns:
        tuple: (subject, html_body)
    """
    subject = _t(lang, "ready_subject")

    # Bloco do botão de download (link que expira)
    _is_pt = str(lang).lower().startswith("pt")
    download_html = ""
    if download_url:
        _btn = "⬇ Baixar resultados" if _is_pt else "⬇ Download results"
        _exp = (
            f"O link expira em {expiry_hours} horas. Após esse período o "
            f"arquivo é removido automaticamente."
            if _is_pt
            else f"This link expires in {expiry_hours} hours. After that the "
            f"file is removed automatically."
        )
        download_html = f"""
        <div style="text-align:center;margin:24px 0;">
            <a href="{download_url}" style="display:inline-block;background:#1a5f2a;
               color:#ffffff;text-decoration:none;padding:14px 28px;border-radius:8px;
               font-weight:bold;font-size:16px;">{_btn}</a>
            <p style="color:#888;font-size:13px;margin:12px 0 0;">{_exp}</p>
        </div>
        """

    format_label = (
        _t(lang, "format_excel")
        if file_format == "excel"
        else _t(lang, "format_csv")
    )

    # Mapear nomes das fontes para nomes mais amigáveis
    source_names = {
        "nasa_power": "NASA POWER",
        "openmeteo_archive": "Open-Meteo Archive",
        "openmeteo_forecast": "Open-Meteo Forecast",
        "met_norway": "MET Norway",
    }
    sources_friendly = [source_names.get(s, s) for s in sources_used]
    sources_str = (
        ", ".join(sources_friendly)
        if sources_friendly
        else _t(lang, "multiple_sources")
    )

    # Estatísticas resumidas
    stats_html = ""
    if summary_stats:
        eto_mean = summary_stats.get("eto_mean", 0)
        eto_max = summary_stats.get("eto_max", 0)
        eto_min = summary_stats.get("eto_min", 0)
        eto_total = summary_stats.get("eto_total", 0)

        day_abbr = _t(lang, "day")

        stats_html = f"""
        <div style="background: #e3f2fd; border-left: 4px solid #2196F3; 
                    padding: 15px; margin: 20px 0; border-radius: 0 4px 4px 0;">
            <p style="margin: 0 0 10px 0; color: #1565c0; font-weight: bold;">
                {_t(lang, "stats_title")}
            </p>
            <table style="width: 100%; font-size: 14px;">
                <tr>
                    <td style="padding: 5px 0;"><strong>{_t(lang, "eto_mean")}</strong></td>
                    <td style="padding: 5px 0;">{eto_mean:.2f} mm/{day_abbr}</td>
                    <td style="padding: 5px 0;"><strong>{_t(lang, "eto_max")}</strong></td>
                    <td style="padding: 5px 0;">{eto_max:.2f} mm/{day_abbr}</td>
                </tr>
                <tr>
                    <td style="padding: 5px 0;"><strong>{_t(lang, "eto_min")}</strong></td>
                    <td style="padding: 5px 0;">{eto_min:.2f} mm/{day_abbr}</td>
                    <td style="padding: 5px 0;"><strong>{_t(lang, "eto_total")}</strong></td>
                    <td style="padding: 5px 0;">{eto_total:.2f} mm</td>
                </tr>
            </table>
        </div>
        """

    elevation_str = (
        f"{elevation:.1f} m" if elevation else _t(lang, "elevation_auto")
    )

    days_processed_text = _t(lang, "ready_days_processed").format(
        days=days_processed, seconds=processing_time_seconds
    )

    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
    </head>
    <body style="margin: 0; padding: 0; background-color: #f5f5f5; font-family: Arial, sans-serif;">
        <div style="max-width: 600px; margin: 20px auto; background: white; border-radius: 8px; 
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
            
            {get_email_header(lang)}
            
            <div style="padding: 30px;">
                <h2 style="color: #1a5f2a; margin-top: 0;">
                    {_t(lang, "ready_title")}
                </h2>
                
                <p style="color: #333; line-height: 1.6;">
                    {_t(lang, "ready_body")}
                </p>
                
                <div style="background: #e8f5e9; border-left: 4px solid #4CAF50; 
                            padding: 15px; margin: 20px 0; border-radius: 0 4px 4px 0;">
                    <p style="margin: 0; color: #2e7d32; font-weight: bold; font-size: 16px;">
                        {_t(lang, "ready_success")}
                    </p>
                    <p style="margin: 10px 0 0 0; color: #2e7d32;">
                        {days_processed_text}
                    </p>
                </div>
                {download_html}
                <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
                    <tr style="background: #1a5f2a; color: white;">
                        <td colspan="2" style="padding: 12px; font-weight: bold;">
                            📋 {_t(lang, "processing_info")}
                        </td>
                    </tr>
                    <tr style="background: #f9f9f9;">
                        <td style="padding: 12px; border: 1px solid #ddd; font-weight: bold; width: 40%;">
                            📍 {_t(lang, "location")}
                        </td>
                        <td style="padding: 12px; border: 1px solid #ddd;">
                            Lat: {latitude:.4f}° | Lon: {longitude:.4f}°
                        </td>
                    </tr>
                    <tr>
                        <td style="padding: 12px; border: 1px solid #ddd; font-weight: bold;">
                            🏔️ {_t(lang, "elevation")}
                        </td>
                        <td style="padding: 12px; border: 1px solid #ddd;">
                            {elevation_str}
                        </td>
                    </tr>
                    <tr style="background: #f9f9f9;">
                        <td style="padding: 12px; border: 1px solid #ddd; font-weight: bold;">
                            📅 {_t(lang, "period")}
                        </td>
                        <td style="padding: 12px; border: 1px solid #ddd;">
                            {start_date} {_t(lang, "to")} {end_date}
                        </td>
                    </tr>
                    <tr>
                        <td style="padding: 12px; border: 1px solid #ddd; font-weight: bold;">
                            📊 {_t(lang, "days_processed")}
                        </td>
                        <td style="padding: 12px; border: 1px solid #ddd;">
                            {days_processed} {_t(lang, "days")}
                        </td>
                    </tr>
                    <tr style="background: #f9f9f9;">
                        <td style="padding: 12px; border: 1px solid #ddd; font-weight: bold;">
                            🌐 {_t(lang, "data_sources")}
                        </td>
                        <td style="padding: 12px; border: 1px solid #ddd;">
                            {sources_str}
                        </td>
                    </tr>
                    <tr>
                        <td style="padding: 12px; border: 1px solid #ddd; font-weight: bold;">
                            📎 {_t(lang, "file_format")}
                        </td>
                        <td style="padding: 12px; border: 1px solid #ddd;">
                            {format_label}
                        </td>
                    </tr>
                </table>
                
                {stats_html}
                
                <div style="background: #f5f5f5; padding: 15px; margin: 20px 0; 
                            border-radius: 4px; border: 1px solid #ddd;">
                    <p style="margin: 0 0 10px 0; font-weight: bold; color: #333;">
                        {_t(lang, "columns_title")}
                    </p>
                    <ul style="margin: 0; padding-left: 20px; color: #666; font-size: 13px;">
                        <li>{_t(lang, "col_date")}</li>
                        <li>{_t(lang, "col_temp")}</li>
                        <li>{_t(lang, "col_humidity")}</li>
                        <li>{_t(lang, "col_wind")}</li>
                        <li>{_t(lang, "col_radiation")}</li>
                        <li>{_t(lang, "col_precip")}</li>
                        <li>{_t(lang, "col_eto")}</li>
                    </ul>
                </div>
            </div>
            
            {get_email_footer(lang)}
        </div>
    </body>
    </html>
    """

    return subject, html_body


# ============================================================================
# TEMPLATE 3: PROCESSING ERROR
# ============================================================================


def create_processing_error_email(
    task_id: str,
    latitude: float,
    longitude: float,
    start_date: str,
    end_date: str,
    error_message: str,
    lang: str = "en",
) -> tuple[str, str]:
    """
    Cria email informando erro no processamento.

    Returns:
        tuple: (subject, html_body)
    """
    subject = _t(lang, "error_subject")

    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
    </head>
    <body style="margin: 0; padding: 0; background-color: #f5f5f5; font-family: Arial, sans-serif;">
        <div style="max-width: 600px; margin: 20px auto; background: white; border-radius: 8px; 
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
            
            {get_email_header(lang)}
            
            <div style="padding: 30px;">
                <h2 style="color: #c62828; margin-top: 0;">
                    {_t(lang, "error_title")}
                </h2>
                
                <p style="color: #333; line-height: 1.6;">
                    {_t(lang, "error_body")}
                </p>
                
                <div style="background: #ffebee; border-left: 4px solid #f44336; 
                            padding: 15px; margin: 20px 0; border-radius: 0 4px 4px 0;">
                    <p style="margin: 0; color: #c62828; font-weight: bold;">
                        {_t(lang, "error_details")}
                    </p>
                    <p style="margin: 10px 0 0 0; color: #c62828; font-family: monospace; 
                              font-size: 13px; word-break: break-all;">
                        {error_message[:500]}
                    </p>
                </div>
                
                <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
                    <tr style="background: #f9f9f9;">
                        <td style="padding: 12px; border: 1px solid #ddd; font-weight: bold; width: 40%;">
                            🆔 {_t(lang, "request_id")}
                        </td>
                        <td style="padding: 12px; border: 1px solid #ddd; font-family: monospace;">
                            {task_id[:8]}...
                        </td>
                    </tr>
                    <tr>
                        <td style="padding: 12px; border: 1px solid #ddd; font-weight: bold;">
                            📍 {_t(lang, "location")}
                        </td>
                        <td style="padding: 12px; border: 1px solid #ddd;">
                            Lat: {latitude:.4f}° | Lon: {longitude:.4f}°
                        </td>
                    </tr>
                    <tr style="background: #f9f9f9;">
                        <td style="padding: 12px; border: 1px solid #ddd; font-weight: bold;">
                            📅 {_t(lang, "requested_period")}
                        </td>
                        <td style="padding: 12px; border: 1px solid #ddd;">
                            {start_date} {_t(lang, "to")} {end_date}
                        </td>
                    </tr>
                </table>
                
                <div style="background: #e3f2fd; border-left: 4px solid #2196F3; 
                            padding: 15px; margin: 20px 0; border-radius: 0 4px 4px 0;">
                    <p style="margin: 0; color: #1565c0;">
                        <strong>{_t(lang, "suggestions_title")}</strong><br>
                        • {_t(lang, "suggestion_1")}<br>
                        • {_t(lang, "suggestion_2")}<br>
                        • {_t(lang, "suggestion_3")}<br>
                        • {_t(lang, "suggestion_4")}
                    </p>
                </div>
            </div>
            
            {get_email_footer(lang)}
        </div>
    </body>
    </html>
    """

    return subject, html_body
