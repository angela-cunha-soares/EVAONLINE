"""
Operation Mode Auto-Detection
Detecta automaticamente o modo operacional baseado nas datas selecionadas.

Mapeia interface do usuário → modos do backend:
- Frontend: "historical", "recent", "forecast"
- Backend: "HISTORICAL_EMAIL", "DASHBOARD_CURRENT", "DASHBOARD_FORECAST"
"""

from datetime import date, datetime, timedelta
from functools import lru_cache
from typing import Tuple, Optional
import logging
import pytz
from timezonefinderL import TimezoneFinder

logger = logging.getLogger(__name__)

# Cache do TimezoneFinder para melhor performance
_tf = None


def _get_timezone_finder() -> TimezoneFinder:
    """Retorna instância singleton do TimezoneFinder."""
    global _tf
    if _tf is None:
        _tf = TimezoneFinder()
    return _tf


def get_timezone_for_location(lat: float, lng: float) -> pytz.BaseTzInfo:
    """
    Detecta o timezone baseado nas coordenadas.

    Args:
        lat: Latitude
        lng: Longitude

    Returns:
        Timezone pytz para a localização
    """
    tf = _get_timezone_finder()
    tz_name = tf.timezone_at(lat=lat, lng=lng)

    if tz_name:
        logger.debug(f"🌍 Timezone detectado para ({lat}, {lng}): {tz_name}")
        return pytz.timezone(tz_name)

    # Fallback: estimate timezone from longitude (for ocean/remote areas)
    # Each 15° of longitude = 1 hour offset from UTC
    utc_offset_hours = round(lng / 15)
    utc_offset_hours = max(
        -12, min(14, utc_offset_hours)
    )  # Clamp to valid range

    # Create timezone name like "Etc/GMT-9" (note: Etc/GMT signs are inverted)
    # UTC+9 is Etc/GMT-9
    if utc_offset_hours >= 0:
        tz_name = (
            f"Etc/GMT-{utc_offset_hours}" if utc_offset_hours > 0 else "UTC"
        )
    else:
        tz_name = f"Etc/GMT+{abs(utc_offset_hours)}"

    logger.warning(
        f"⚠️ Timezone não detectado para ({lat}, {lng}), "
        f"usando estimativa baseada na longitude: {tz_name} (UTC{'+' if utc_offset_hours >= 0 else ''}{utc_offset_hours})"
    )
    return pytz.timezone(tz_name)


def get_today_for_location(lat: float, lng: float) -> date:
    """
    Retorna a data de hoje no timezone da localização especificada.

    Args:
        lat: Latitude
        lng: Longitude

    Returns:
        Data atual na localização
    """
    tz = get_timezone_for_location(lat, lng)
    return datetime.now(tz).date()


def get_today_local() -> date:
    """
    Retorna a data de hoje no timezone de São Paulo (fallback).
    Use get_today_for_location() quando tiver coordenadas.
    """
    return datetime.now(pytz.timezone("America/Sao_Paulo")).date()


def is_land_point(lat: float, lng: float) -> bool:
    """
    Verifica se um ponto está em terra firme (detecção em 3 camadas).
    Resultados são cacheados (LRU, 512 entradas) para evitar
    chamadas repetidas à API OpenTopoData.

    Camada 1 - timezonefinderL (instantâneo, offline):
        Retorna timezone IANA para terra, None para oceano.
        Rápido mas impreciso: polígonos simplificados estendem-se
        sobre o oceano perto de ilhas (ex: Marquesas, Hawaii).

    Camada 2 - OpenTopoData ETOPO1 (batimetria global, ~1-3s):
        ETOPO1 tem cobertura global incluindo profundidade do oceano.
        elevation < 0 → oceano/mar (batimetria)
        elevation >= 0 → terra ou nível do mar
        Resolve falsos positivos do timezonefinderL em áreas costeiras.

    Camada 3 - OpenTopoData SRTM/ASTER (datasets terrestres, ~1-3s):
        Usada quando camada 1 diz "oceano" (timezone=None).
        SRTM/ASTER retornam null para oceano.
        Se retorna elevação válida → é terra (timezonefinderL errou).
        Captura ilhas sem timezone IANA no dataset simplificado.

    Args:
        lat: Latitude
        lng: Longitude

    Returns:
        True se o ponto está em terra, False se oceano
    """
    # Arredondar para 4 casas (~11m) para eficiência do cache
    return _is_land_cached(round(lat, 4), round(lng, 4))


@lru_cache(maxsize=512)
def _is_land_cached(lat: float, lng: float) -> bool:
    """Implementação cacheada da detecção terra/oceano."""
    import os
    import httpx

    base_url = os.getenv("OPENTOPO_URL", "https://api.opentopodata.org/v1")

    # === Camada 1: timezonefinderL (offline, < 1ms) ===
    tf = _get_timezone_finder()
    tz_name = tf.timezone_at(lat=lat, lng=lng)

    if tz_name is not None:
        # timezonefinderL diz "terra", mas pode ser falso positivo
        # perto de ilhas/costa. Verificar com ETOPO1 (batimetria).
        # === Camada 2: ETOPO1 para confirmar (negativo = oceano) ===
        try:
            resp = httpx.get(
                f"{base_url}/etopo1",
                params={"locations": f"{lat},{lng}"},
                timeout=10,
            )
            if resp.status_code == 200:
                data = resp.json()
                if data.get("status") == "OK":
                    results = data.get("results", [])
                    if results:
                        elev = results[0].get("elevation")
                        if elev is not None and elev < 0:
                            logger.warning(
                                f"🌊 ETOPO1 detectou OCEANO em "
                                f"({lat}, {lng}): {elev}m "
                                f"(timezonefinderL dizia '{tz_name}')"
                            )
                            return False
            # ETOPO1 diz terra (elev >= 0) ou falhou → confiar
            logger.debug(
                f"✅ Terra confirmada em ({lat}, {lng}) " f"timezone={tz_name}"
            )
            return True
        except Exception as e:
            logger.warning(
                f"⚠️ ETOPO1 check falhou: {e}. "
                f"Confiando no timezonefinderL ({tz_name})"
            )
            return True

    # === timezonefinderL diz "oceano" (timezone=None) ===
    # === Camada 3: SRTM/ASTER para ilhas sem timezone ===
    try:
        resp = httpx.get(
            f"{base_url}/srtm30m,aster30m",
            params={"locations": f"{lat},{lng}"},
            timeout=10,
        )
        if resp.status_code == 200:
            data = resp.json()
            if data.get("status") == "OK":
                results = data.get("results", [])
                if results and results[0].get("elevation") is not None:
                    elev = results[0]["elevation"]
                    if elev > 0:
                        logger.info(
                            f"🏝️ SRTM detectou TERRA em ({lat}, {lng}) "
                            f"elevação={elev}m "
                            f"(timezonefinderL não reconheceu)"
                        )
                        return True

        logger.info(f"🌊 Todas as camadas confirmam OCEANO em ({lat}, {lng})")
    except Exception as e:
        logger.warning(
            f"⚠️ Verificação SRTM falhou: {e}. "
            f"Confiando apenas no timezonefinderL."
        )

    return False


class OperationModeDetector:
    """Detecta e valida modos operacionais do EVAonline"""

    # Mapeamento Frontend → Backend
    MODE_MAPPING = {
        "historical": "HISTORICAL_EMAIL",
        "recent": "DASHBOARD_CURRENT",
        "forecast": "DASHBOARD_FORECAST",
    }

    # Configurações de cada modo backend
    BACKEND_MODES = {
        "HISTORICAL_EMAIL": {
            "description": "1-90 days historical data with email report",
            "min_date": date(1990, 1, 1),
            "max_date_offset": -1,  # today - 1 day (yesterday)
            "min_period": 1,
            "max_period": 90,
            "sources": ["nasa_power", "openmeteo_archive", "openmeteo_forecast"],
            "requires_email": True,
        },
        "DASHBOARD_CURRENT": {
            "description": "Last 7/14/21/30 days dashboard view",
            "min_date_offset": -29,  # today - 29 days
            "max_date_offset": 0,  # today
            "allowed_periods": [7, 14, 21, 30],
            "sources": [
                "nasa_power",
                "openmeteo_archive",
                "openmeteo_forecast",
            ],
            "requires_email": False,
        },
        "DASHBOARD_FORECAST": {
            "description": "Next 6 days forecast (today → today+5)",
            "min_date_offset": 0,  # today
            "max_date_offset": 5,  # today + 5 days
            "fixed_period": 6,
            "sources": ["openmeteo_forecast", "met_norway", "nws_forecast"],
            "usa_station_option": True,  # NWS Stations available in USA
            "requires_email": False,
        },
    }

    @classmethod
    def detect_mode(
        cls,
        ui_selection: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        period_days: Optional[int] = None,
    ) -> Tuple[str, dict]:
        """
        Detecta o modo backend apropriado baseado na seleção do usuário.

        Args:
            ui_selection: Seleção da UI ("historical", "recent", "forecast")
            start_date: Data inicial (para modo historical)
            end_date: Data final (para modo historical)
            period_days: Número de dias (para modo recent)

        Returns:
            Tuple (backend_mode: str, config: dict)

        Example:
            >>> mode, config = OperationModeDetector.detect_mode(
            ...     "recent",
            ...     period_days=30
            ... )
            >>> print(mode)  # "DASHBOARD_CURRENT"
        """
        backend_mode = cls.MODE_MAPPING.get(ui_selection)

        if not backend_mode:
            logger.error(f"Invalid UI selection: {ui_selection}")
            raise ValueError(f"Unknown operation mode: {ui_selection}")

        config = cls.BACKEND_MODES[backend_mode].copy()
        config["ui_selection"] = ui_selection

        logger.info(
            f"🎯 Detected mode: {backend_mode} (from UI: {ui_selection})"
        )

        return backend_mode, config

    @classmethod
    def validate_dates(
        cls,
        mode: str,
        start_date: date,
        end_date: date,
        lat: Optional[float] = None,
        lng: Optional[float] = None,
    ) -> Tuple[bool, str]:
        """
        Valida se as datas são válidas para o modo.

        Args:
            mode: Modo backend ("HISTORICAL_EMAIL", "DASHBOARD_CURRENT", etc)
            start_date: Data inicial
            end_date: Data final
            lat: Latitude (optional, para timezone correto)
            lng: Longitude (optional, para timezone correto)

        Returns:
            Tuple (is_valid: bool, message: str)
        """
        if mode not in cls.BACKEND_MODES:
            return False, f"Invalid mode: {mode}"

        config = cls.BACKEND_MODES[mode]
        # Use location-based timezone when coordinates available
        if lat is not None and lng is not None:
            today = get_today_for_location(lat, lng)
        else:
            today = get_today_local()
        period_days = (end_date - start_date).days + 1

        if mode == "HISTORICAL_EMAIL":
            # Validar data mínima
            min_date = config["min_date"]
            if start_date < min_date:
                return False, f"Start date must be >= {min_date.isoformat()}"

            # Validar data máxima (hoje - 2 dias)
            max_date = today + timedelta(days=config["max_date_offset"])
            if end_date > max_date:
                return (
                    False,
                    f"End date must be <= {max_date.isoformat()} (yesterday)",
                )

            # Validar período
            if not (
                config["min_period"] <= period_days <= config["max_period"]
            ):
                return (
                    False,
                    f"Period must be {config['min_period']}-{config['max_period']} days",
                )

            return True, f"Valid historical period ({period_days} days)"

        elif mode == "DASHBOARD_CURRENT":
            # End date deve ser hoje
            if end_date != today:
                return (
                    False,
                    f"Dashboard current requires end_date = today ({today.isoformat()})",
                )

            # Período deve ser um dos permitidos
            if period_days not in config["allowed_periods"]:
                allowed = ", ".join(map(str, config["allowed_periods"]))
                return False, f"Period must be one of: {allowed} days"

            # Start date calculado deve estar dentro do range
            min_date = today + timedelta(days=config["min_date_offset"])
            if start_date < min_date:
                return False, f"Start date must be >= {min_date.isoformat()}"

            return (
                True,
                f"Valid dashboard period ({period_days} days ending today)",
            )

        elif mode == "DASHBOARD_FORECAST":
            # Deve começar hoje
            expected_start = today + timedelta(days=config["min_date_offset"])
            if abs((start_date - expected_start).days) > 1:
                return (
                    False,
                    f"Forecast must start today ({today.isoformat()})",
                )

            # Deve terminar em today+5
            expected_end = today + timedelta(days=config["max_date_offset"])
            if abs((end_date - expected_end).days) > 1:
                return (
                    False,
                    f"Forecast must end {expected_end.isoformat()} (today+5d)",
                )

            # Período deve ser 6 dias
            if period_days != config["fixed_period"]:
                return (
                    False,
                    f"Forecast period must be exactly {config['fixed_period']} days",
                )

            return True, "Valid 6-day forecast period"

        return False, "Unknown validation error"

    @classmethod
    def prepare_api_request(
        cls,
        ui_selection: str,
        latitude: float,
        longitude: float,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        period_days: Optional[int] = None,
        email: Optional[str] = None,
        usa_forecast_source: str = "fusion",
    ) -> dict:
        """
        Prepara payload para requisição à API do backend.

        Args:
            ui_selection: Seleção da UI
            latitude: Latitude
            longitude: Longitude
            start_date: Data inicial (para historical)
            end_date: Data final (para historical)
            period_days: Número de dias (para recent/forecast)
            email: Email do usuário (para historical)
            usa_forecast_source: "fusion" ou "stations" (para forecast nos EUA)

        Returns:
            dict com payload formatado para API
        """
        # Detectar modo
        backend_mode, config = cls.detect_mode(
            ui_selection, start_date, end_date, period_days
        )

        # Usar timezone baseado na localização selecionada
        today = get_today_for_location(latitude, longitude)
        logger.info(
            f"📅 Data local para ({latitude}, {longitude}): {today.isoformat()}"
        )

        # Calcular datas baseado no modo
        if ui_selection == "historical":
            # Modo 1: Usar datas fornecidas
            if not (start_date and end_date):
                raise ValueError(
                    "Historical mode requires start_date and end_date"
                )
            request_start = start_date
            request_end = end_date

        elif ui_selection == "recent":
            # Modo 2: Calcular datas do período
            if not period_days:
                raise ValueError("Recent mode requires period_days")
            request_end = today
            request_start = today - timedelta(days=period_days - 1)

        elif ui_selection == "forecast":
            # Modo 3: Período fixo
            request_start = today
            request_end = today + timedelta(days=5)

            # Se USA e selecionou stations, usar modo especial
            if usa_forecast_source == "stations":
                backend_mode = "DASHBOARD_FORECAST_STATIONS"
        else:
            raise ValueError(f"Unknown UI selection: {ui_selection}")

        # Validar datas (usando timezone da localização)
        is_valid, message = cls.validate_dates(
            backend_mode,
            request_start,
            request_end,
            lat=latitude,
            lng=longitude,
        )
        if not is_valid:
            raise ValueError(
                f"Invalid dates for mode {backend_mode}: {message}"
            )

        # Mapear backend_mode → period_type do backend (lowercase com _)
        # Backend espera: "historical_email", "dashboard_current", "dashboard_forecast"
        period_type_map = {
            "HISTORICAL_EMAIL": "historical_email",
            "DASHBOARD_CURRENT": "dashboard_current",
            "DASHBOARD_FORECAST": "dashboard_forecast",
        }
        period_type = period_type_map.get(backend_mode, "dashboard_current")

        # Montar payload para o backend
        payload = {
            "lat": latitude,  # Backend espera "lat", não "latitude"
            "lng": longitude,  # Backend espera "lng", não "longitude"
            "start_date": request_start.isoformat(),
            "end_date": request_end.isoformat(),
            "period_type": period_type,
            "email": email if config["requires_email"] else None,
        }

        logger.info(f"📦 API request payload prepared: {payload}")

        return payload

    @classmethod
    def get_mode_info(cls, backend_mode: str) -> dict:
        """
        Retorna informações sobre um modo backend.

        Args:
            backend_mode: Nome do modo backend

        Returns:
            dict com configuração do modo
        """
        return cls.BACKEND_MODES.get(backend_mode, {})

    @classmethod
    def get_available_sources(cls, backend_mode: str) -> list:
        """
        Retorna fontes de dados disponíveis para um modo.

        Args:
            backend_mode: Nome do modo backend

        Returns:
            list de fontes disponíveis
        """
        config = cls.BACKEND_MODES.get(backend_mode, {})
        return config.get("sources", [])


def format_date_for_display(date_obj: date) -> str:
    """
    Formata data para exibição na UI.

    Args:
        date_obj: Objeto date

    Returns:
        String formatada (DD/MM/YYYY)
    """
    return date_obj.strftime("%d/%m/%Y")


def parse_date_from_ui(date_input) -> Optional[date]:
    """
    Parse data vinda da UI (formato ISO, DD/MM/YYYY, ou objeto date).

    Args:
        date_input: String de data, objeto date/datetime, ou None

    Returns:
        Objeto date ou None se não conseguir parsear
    """
    if date_input is None:
        return None

    # Se já é um objeto date, retorna diretamente
    if isinstance(date_input, date):
        return date_input

    # Se é datetime, extrai date
    if isinstance(date_input, datetime):
        return date_input.date()

    # Converter para string se necessário
    date_str = str(date_input).strip()
    if not date_str:
        return None

    # Tentar formato ISO primeiro (YYYY-MM-DD)
    try:
        return datetime.fromisoformat(date_str).date()
    except (ValueError, AttributeError):
        pass

    # Tentar formato brasileiro (DD/MM/YYYY)
    try:
        return datetime.strptime(date_str, "%d/%m/%Y").date()
    except ValueError:
        pass

    return None
