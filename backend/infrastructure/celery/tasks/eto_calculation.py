"""
Task Celery para cálculo ETo com progresso em tempo real.

Integra:
- ClimateSourceManager: Seleção de fontes por localização
- EToProcessingService: Pipeline completo de ETo
- WebSocket: Broadcasting de progresso
"""

from celery.utils.log import get_task_logger
from datetime import datetime
from typing import Any

logger = get_task_logger(__name__)

# Importar celery_app para garantir conexão correta
from backend.infrastructure.celery.celery_config import celery_app


@celery_app.task(
    bind=True,
    name="backend.infrastructure.celery.tasks.calculate_eto_task",
    max_retries=2,
    rate_limit="10/m",  # Max 10 calculations/minute globally
    retry_backoff=True,
    retry_backoff_max=60,  # Max 1 minuto entre retries
    retry_jitter=True,
    ignore_result=False,  # Garantir que resultado seja salvo no Redis
    track_started=True,  # Track status STARTED
)
def calculate_eto_task(
    self,
    lat: float,
    lon: float,
    start_date: str,
    end_date: str,
    sources: list[str] | None = None,
    elevation: float | None = None,
    mode: str | None = None,
    email: str | None = None,
    visitor_id: str | None = None,
    session_id: str | None = None,
    file_format: str = "csv",  # csv (padrão) ou excel
    enable_fusion: bool = False,  # 🔀 Flag para fusão Kalman
    lang: str = "en",  # Language for email templates (en/pt)
) -> dict[str, Any]:
    """
    Calcula ETo para localização com progresso em tempo real.

    Args:
        self: Contexto Celery (bind=True)
        lat, lon: Coordenadas
        start_date, end_date: Período (YYYY-MM-DD)
        sources: Fontes climáticas (None = auto-select)
        elevation: Elevação em metros (None = buscar via OpenTopo)
        mode: Modo de operação (None = auto-detect)
        enable_fusion: Se True, aplica fusão Kalman (Smart Fusion)

    Returns:
        Dict com resultado completo:
        {
            "summary": {...},
            "et0_series": [...],
            "quality_metrics": {...},
            "sources_used": [...],
            "task_id": "abc-123",
            "processing_time_seconds": 12.5
        }

    Raises:
        ValidationError: Se parâmetros inválidos
        APIError: Se todas as fontes falharem
    """
    import asyncio

    import nest_asyncio
    from backend.core.eto_calculation.eto_services import EToProcessingService
    from backend.api.services.climate_validation import (
        ClimateValidationService,
    )
    from backend.api.services.climate_source_manager import (
        ClimateSourceManager,
    )
    from backend.api.services.climate_source_availability import (
        OperationMode,
    )

    def run_async_safely(coro):
        """Run async coroutine safely in Celery worker (handles closed loops)."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_closed():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        nest_asyncio.apply(loop)
        return loop.run_until_complete(coro)

    task_id = self.request.id
    start_time = datetime.now()

    try:
        # ========== STEP 0: EMAIL INICIAL (modo historical_email) ==========
        if mode and "email" in mode.lower() and email:
            from backend.core.utils.email_utils import (
                send_html_email,
                validate_email,
            )
            from backend.core.utils.email_templates import (
                create_processing_started_email,
            )

            if validate_email(email):
                # Criar email HTML profissional (estilo INMET/BDMEP)
                subject, html_body = create_processing_started_email(
                    task_id=task_id,
                    latitude=lat,
                    longitude=lon,
                    start_date=start_date,
                    end_date=end_date,
                    started_at=start_time,
                    file_format=file_format,
                    lang=lang,
                )

                send_html_email(
                    to=email,
                    subject=subject,
                    html_body=html_body,
                )
                logger.info(f"📧 Email inicial HTML enviado para {email}")

        # ========== STEP 1: VALIDAÇÃO (5%) ==========
        logger.info(f"⏳ [5%] Validando parâmetros...")

        # Validar coordenadas
        if not ClimateValidationService.validate_coordinates(lat, lon)[0]:
            raise ValueError(f"Coordenadas inválidas: ({lat}, {lon})")

        # Converter datas
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")

        # Auto-detectar modo se não fornecido
        if mode is None:
            detected_mode, error = (
                ClimateValidationService.detect_mode_from_dates(
                    start_date, end_date
                )
            )
            if detected_mode:
                mode = detected_mode
                logger.info(f"✅ Modo auto-detectado: {mode}")
            else:
                mode = OperationMode.DASHBOARD_CURRENT.value
                logger.warning(f"⚠️  Modo não detectado, usando padrão: {mode}")

        logger.info(
            f"📍 Task {task_id}: ETo para ({lat}, {lon}) "
            f"de {start_date} a {end_date} - Modo: {mode}"
        )

        # ========== STEP 2: SELEÇÃO DE FONTES (10%) ==========
        logger.info("[10%] Selecionando melhores fontes climáticas...")

        manager = ClimateSourceManager()
        source_info = manager.get_sources_for_data_download(
            lat=lat,
            lon=lon,
            start_date=start_dt,
            end_date=end_dt,
            mode=mode,
            preferred_sources=sources,
        )

        selected_sources = source_info["sources"]
        region = source_info["location_info"]["region"]

        logger.info(
            f"🔍 Fontes selecionadas para {region}: {selected_sources}"
        )

        # ========== STEP 3: PROCESSAMENTO ETo (20-90%) ==========
        logger.info(
            f"[20%] Processando dados de {len(selected_sources)} fontes "
            f"({region})..."
        )

        # Inicializar serviço de processamento
        service = EToProcessingService()

        # ========== STEP 4: CÁLCULO ETo (60-90%) ==========
        logger.info("[60%] Calculando ETo (FAO-56 Penman-Monteith)...")

        # O process_location já faz download + processamento completo
        result = run_async_safely(
            service.process_location(
                latitude=lat,
                longitude=lon,
                start_date=start_date,
                end_date=end_date,
                sources=selected_sources,
                elevation=elevation,
                enable_fusion=enable_fusion,  # 🔀 Passar flag de fusão
                mode=mode,  # 🔀 Operational mode for fusion strategy
            )
        )

        # ========== STEP 4.4: VERIFICAR SINAL DE OCEANO ==========
        # Se SRTM/ASTER retornaram null (source=padrão, no_data=True),
        # o ponto pode estar sobre oceano/corpo d'água
        elev_info = result.get("elevation", {})
        if isinstance(elev_info, dict) and elev_info.get("no_data"):
            logger.warning(
                f"🌊 Elevação indisponível via SRTM/ASTER para ({lat}, {lon}) "
                f"- possível ponto sobre oceano/corpo d'água"
            )
            result["ocean_warning"] = True

        # ========== STEP 4.5: ESTAÇÃO NWS (USA only) ==========
        # Se está nos EUA e modo recent/forecast, buscar estação mais próxima
        nws_station_info = None
        is_usa = "usa" in region.lower() if region else False
        is_forecast_mode = mode and (
            "forecast" in mode.lower() or "current" in mode.lower()
        )

        logger.info(
            f"🔍 Region check: {region} | is_usa={is_usa} | mode={mode}"
        )

        if is_usa and is_forecast_mode:
            logger.info(
                "[75%] Buscando estação meteorológica NWS mais próxima..."
            )
            try:
                import httpx as _httpx

                NWS_BASE = "https://api.weather.gov"
                NWS_HEADERS = {
                    "User-Agent": "EVAonline (+https://github.com/evaonlineplatform/EVAONLINE)",
                    "Accept": "application/geo+json",
                }

                # 1) Buscar grid point → estações próximas
                grid_resp = _httpx.get(
                    f"{NWS_BASE}/points/{lat:.4f},{lon:.4f}",
                    headers=NWS_HEADERS,
                    timeout=15,
                )
                grid_resp.raise_for_status()
                grid_props = grid_resp.json()["properties"]
                wfo = grid_props["gridId"]
                grid_x = grid_props["gridX"]
                grid_y = grid_props["gridY"]

                # 2) Buscar estações do grid
                stations_resp = _httpx.get(
                    f"{NWS_BASE}/gridpoints/{wfo}/{grid_x},{grid_y}/stations?limit=3",
                    headers=NWS_HEADERS,
                    timeout=15,
                )
                stations_resp.raise_for_status()
                features = stations_resp.json().get("features", [])

                if features:
                    first = features[0]
                    props = first["properties"]
                    geom = first["geometry"]["coordinates"]  # [lon, lat]
                    st_lat, st_lon = geom[1], geom[0]

                    # Calcular distância
                    import geopy.distance

                    dist_km = round(
                        geopy.distance.distance(
                            (lat, lon), (st_lat, st_lon)
                        ).km,
                        1,
                    )

                    station_id = props["stationIdentifier"]
                    station_name = props.get("name", "Unknown")
                    elev_data = props.get("elevation", {})
                    elev_m = elev_data.get("value") if elev_data else None

                    nws_station_info = {
                        "station_id": station_id,
                        "station_name": station_name,
                        "latitude": st_lat,
                        "longitude": st_lon,
                        "elevation_m": elev_m,
                        "distance_km": dist_km,
                        "is_active": True,
                        "timezone": grid_props.get("timeZone"),
                        "data_source": "NWS/NOAA Weather Stations",
                        "latest_observation": None,
                    }

                    # 3) Buscar última observação da estação
                    try:
                        obs_resp = _httpx.get(
                            f"{NWS_BASE}/stations/{station_id}/observations/latest",
                            headers=NWS_HEADERS,
                            timeout=15,
                        )
                        if obs_resp.status_code == 200:
                            obs_p = obs_resp.json()["properties"]
                            ts = obs_p.get("timestamp", "")

                            def _nws_val(d):
                                if not d or d.get("value") is None:
                                    return None
                                return float(d["value"])

                            temp_c = _nws_val(obs_p.get("temperature"))
                            humidity = _nws_val(obs_p.get("relativeHumidity"))
                            wind_kmh = _nws_val(obs_p.get("windSpeed"))
                            wind_ms = (
                                round(wind_kmh / 3.6, 1) if wind_kmh else None
                            )

                            nws_station_info["latest_observation"] = {
                                "timestamp": ts,
                                "temperature_c": temp_c,
                                "humidity_pct": humidity,
                                "wind_speed_ms": wind_ms,
                                "wind_speed_2m_ms": (
                                    round(wind_ms * 0.748, 1)
                                    if wind_ms
                                    else None
                                ),
                                "is_delayed": False,
                            }
                    except Exception as obs_err:
                        logger.warning(f"⚠️ Obs error: {obs_err}")

                    logger.info(
                        f"📡 Estação NWS encontrada: {station_name} "
                        f"({station_id}) - {dist_km} km"
                    )

            except Exception as nws_error:
                logger.warning(f"⚠️ Erro ao buscar estação NWS: {nws_error}")

        # ========== STEP 5: SALVAR NO BANCO (80-90%) ==========
        logger.info("[80%] Salvando dados no banco...")

        # Salvar dados climáticos com ETo no banco
        from backend.database.data_storage import save_climate_data
        from backend.database.connection import get_db

        try:
            db = next(get_db())
            # Preparar dados para salvar
            climate_records = []
            if "et0_series" in result:
                for record in result["et0_series"]:
                    climate_records.append(
                        {
                            "latitude": lat,
                            "longitude": lon,
                            "elevation": result.get("elevation", {}).get(
                                "value", elevation
                            ),
                            "date": record.get("date"),
                            "raw_data": record,
                            "eto_mm_day": record.get("et0_mm_day"),
                            "eto_method": "penman_monteith_fao56",
                        }
                    )

            if climate_records:
                saved_count = save_climate_data(
                    data=climate_records,
                    source_api=(
                        selected_sources[0] if selected_sources else "fusion"
                    ),
                )
                logger.info(f"💾 Salvos {saved_count} registros no banco")
        except Exception as save_error:
            logger.warning(f"⚠️ Erro ao salvar no banco: {save_error}")
        finally:
            db.close()

        # ========== STEP 6: ENVIO DE EMAIL (modo historical_email) ==========
        email_sent = False
        if mode and "email" in mode.lower() and email:
            logger.info("[90%] Gerando arquivo e enviando por email...")

            try:
                import pandas as pd
                from backend.core.utils.email_utils import (
                    send_html_email,
                    validate_email,
                )
                from backend.core.utils.email_templates import (
                    create_data_ready_email,
                )
                from backend.infrastructure.storage import result_files
                from config.settings.app_config import get_settings

                # Validar email fornecido
                if not validate_email(email):
                    logger.warning(f"⚠️ Email inválido: {email}")
                else:
                    # Usar visitor_id ou session_id existente, ou gerar novo
                    if visitor_id:
                        user_identifier = visitor_id.replace("visitor_", "")[
                            :8
                        ]
                    elif session_id:
                        user_identifier = session_id.replace("sess_", "")[:8]
                    else:
                        # Fallback: gerar ID baseado no email
                        import hashlib

                        user_identifier = hashlib.md5(
                            email.encode()
                        ).hexdigest()[:8]

                    logger.info(
                        f"📋 ID usuário: {user_identifier} "
                        f"(visitor: {bool(visitor_id)}, "
                        f"session: {bool(session_id)})"
                    )

                    # Determinar extensão do arquivo
                    file_ext = "xlsx" if file_format == "excel" else "csv"

                    # Gerar arquivo com nome simplificado:
                    # EVAonline_<lat>_<lon>_<start>_<end>.<ext>
                    lat_str = f"{abs(lat):.4f}{'N' if lat >= 0 else 'S'}"
                    lon_str = f"{abs(lon):.4f}{'E' if lon >= 0 else 'W'}"
                    filename = (
                        f"EVAonline_{lat_str}_{lon_str}_"
                        f"{start_date}_{end_date}.{file_ext}"
                    )

                    # Converter et0_series para DataFrame
                    et0_series = result.get("et0_series", [])
                    df_result = pd.DataFrame(et0_series)

                    # Salvar no formato escolhido (em memória)
                    if not df_result.empty:
                        import io

                        buffer = io.BytesIO()
                        if file_format == "excel":
                            df_result.to_excel(buffer, index=False)
                        else:
                            df_result.to_csv(buffer, index=False)
                        file_bytes = buffer.getvalue()
                        logger.info(
                            f"📊 Arquivo {file_format.upper()} gerado em "
                            f"memória ({len(file_bytes)} bytes)"
                        )

                        # Guardar arquivo e gerar link de download que expira
                        settings = get_settings()
                        token = result_files.save_result(
                            file_bytes, filename, email
                        )
                        base = settings.PUBLIC_BASE_URL.rstrip("/")
                        download_url = f"{base}/api/v1/download/{token}"
                        logger.info(
                            f"🔗 Link de download gerado (expira em "
                            f"{settings.DOWNLOAD_TTL_HOURS}h): "
                            f"{download_url}"
                        )

                        # Calcular tempo de processamento
                        processing_time = (
                            datetime.now() - start_time
                        ).total_seconds()

                        # Calcular estatísticas resumidas
                        eto_values = [
                            r.get("et0_mm_day", 0)
                            for r in et0_series
                            if r.get("et0_mm_day") is not None
                        ]
                        summary_stats = None
                        if eto_values:
                            summary_stats = {
                                "eto_mean": sum(eto_values) / len(eto_values),
                                "eto_max": max(eto_values),
                                "eto_min": min(eto_values),
                                "eto_total": sum(eto_values),
                            }

                        # Criar email HTML com o LINK de download (sem anexo)
                        subject, html_body = create_data_ready_email(
                            task_id=task_id,
                            latitude=lat,
                            longitude=lon,
                            start_date=start_date,
                            end_date=end_date,
                            days_processed=len(et0_series),
                            processing_time_seconds=processing_time,
                            sources_used=selected_sources,
                            file_format=file_format,
                            elevation=result.get("elevation", {}).get("value"),
                            summary_stats=summary_stats,
                            lang=lang,
                            download_url=download_url,
                            expiry_hours=settings.DOWNLOAD_TTL_HOURS,
                        )

                        # Enviar email HTML com o link (3º e-mail: resultados)
                        email_sent = send_html_email(
                            to=email,
                            subject=subject,
                            html_body=html_body,
                        )

                        if email_sent:
                            logger.info(
                                f"✅ E-mail de resultados (link) enviado "
                                f"para {email}"
                            )
                        else:
                            logger.warning(
                                f"⚠️ Falha ao enviar email para {email}"
                            )
                    else:
                        logger.warning("⚠️ Nenhum dado para enviar")

            except Exception as email_error:
                logger.error(
                    f"❌ Erro ao gerar arquivo/enviar email: {email_error}",
                    exc_info=True,
                )

        # ========== STEP 7: FINALIZAÇÃO (95-100%) ==========
        logger.info("[95%] Preparando resultado final...")

        processing_time = (datetime.now() - start_time).total_seconds()

        final_result = {
            **result,  # Usar todo o resultado do service
            "task_id": task_id,
            "processing_time_seconds": round(processing_time, 2),
            "mode": mode,
            "email_sent": email_sent,  # Indicar se email foi enviado
            "nws_station": nws_station_info,  # 📡 Estação NWS (USA only)
        }

        logger.info(
            f"✅ [100%] Task {task_id} completed in {processing_time:.2f}s "
            f"for ({lat}, {lon})"
        )

        return final_result

    except Exception as e:
        logger.error(f"❌ Task {task_id} failed: {e}", exc_info=True)

        # Enviar email de erro se possível
        if mode and "email" in mode.lower() and email:
            try:
                from backend.core.utils.email_utils import (
                    send_html_email,
                    validate_email,
                )
                from backend.core.utils.email_templates import (
                    create_processing_error_email,
                )

                if validate_email(email):
                    subject, html_body = create_processing_error_email(
                        task_id=task_id,
                        latitude=lat,
                        longitude=lon,
                        start_date=start_date,
                        end_date=end_date,
                        error_message=str(e),
                        lang=lang,
                    )
                    send_html_email(
                        to=email, subject=subject, html_body=html_body
                    )
                    logger.info(f"📧 Email de erro enviado para {email}")
            except Exception as email_err:
                logger.error(f"Falha ao enviar email de erro: {email_err}")

        # Retry apenas para erros de rede/API, não para validação
        if isinstance(e, (ValueError, TypeError)):
            # Erros de validação: falhar imediatamente sem retry
            return {
                "error": str(e),
                "task_id": task_id,
                "mode": mode,
                "processing_time_seconds": round(
                    (datetime.now() - start_time).total_seconds(), 2
                ),
            }

        # Erros de rede/API: retry com backoff (max 2 tentativas)
        if self.request.retries < self.max_retries:
            raise self.retry(
                exc=e, countdown=30 * (self.request.retries + 1)
            )

        # Esgotou retries: retornar erro
        return {
            "error": str(e),
            "task_id": task_id,
            "mode": mode,
            "processing_time_seconds": round(
                (datetime.now() - start_time).total_seconds(), 2
            ),
        }
