"""
Serviço para gerenciar geolocalização de usuários.
Armazena coordenadas e metadados dos visitantes no PostgreSQL.
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Optional
from uuid import uuid4

from backend.database.models.visitor_stats import Visitor
from backend.database.connection import get_db_context

logger = logging.getLogger(__name__)


class GeolocationService:
    """
    Gerencia geolocalização e rastreamento de visitantes.

    Features:
    - Armazena coordenadas do navegador
    - Detecta dispositivo/browser/OS
    - Associa sessões com cálculos ETo
    - Mantém histórico de visitas
    """

    @staticmethod
    def create_or_update_visitor(
        visitor_id: str,
        session_id: str,
        geolocation: Optional[Dict[str, float]] = None,
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None,
        country: Optional[str] = None,
        city: Optional[str] = None,
    ) -> Visitor:
        """
        Cria ou atualiza visitante com geolocalização.

        Args:
            visitor_id: UUID único do visitante
            session_id: ID da sessão
            geolocation: Dict com 'latitude', 'longitude', 'accuracy'
            user_agent: String do User-Agent
            ip_address: IP do visitante (opcional)
            country: País detectado (opcional)
            city: Cidade detectada (opcional)

        Returns:
            Visitor: Objeto do visitante atualizado

        Example:
            >>> service = GeolocationService()
            >>> visitor = service.create_or_update_visitor(
            ...     visitor_id="visitor_abc123",
            ...     session_id="sess_xyz789",
            ...     geolocation={
            ...         'latitude': -15.7939,
            ...         'longitude': -47.8828,
            ...         'accuracy': 50
            ...     },
            ...     user_agent="Mozilla/5.0...",
            ...     country="Brazil",
            ...     city="Brasília"
            ... )
        """
        # Detectar região climática se geolocalização fornecida
        climate_region = None
        if geolocation:
            lat = geolocation.get("latitude")
            lon = geolocation.get("longitude")
            if lat is not None and lon is not None:
                climate_region = GeolocationService._detect_climate_region(
                    lat, lon
                )

        with get_db_context() as db:
            # Buscar visitante existente
            visitor = (
                db.query(Visitor)
                .filter(Visitor.visitor_id == visitor_id)
                .first()
            )

            if visitor:
                # Atualizar visitante existente
                visitor.session_id = session_id  # type: ignore[assignment]
                visitor.last_visit = datetime.now(timezone.utc)
                visitor.visit_count += 1

                # Atualizar geolocalização se fornecida
                if geolocation:
                    lat = geolocation.get("latitude")
                    lon = geolocation.get("longitude")
                    acc = geolocation.get("accuracy")
                    visitor.last_latitude = lat  # type: ignore[assignment]
                    visitor.last_longitude = lon  # type: ignore[assignment]
                    visitor.geolocation_accuracy = acc  # type: ignore

                # Atualizar metadados
                if country:
                    visitor.country = country  # type: ignore[assignment]
                if city:
                    visitor.city = city  # type: ignore[assignment]

                # Atualizar região climática
                if climate_region:
                    visitor.climate_region = climate_region  # type: ignore

                logger.info(
                    f"✅ Visitante atualizado: {visitor_id} "
                    f"(visita #{visitor.visit_count}, "
                    f"região: {climate_region})"
                )
            else:
                # Criar novo visitante
                device_info = GeolocationService._parse_user_agent(
                    user_agent or "Unknown"
                )

                visitor = Visitor(
                    visitor_id=visitor_id,
                    session_id=session_id,
                    user_agent=user_agent or "Unknown",
                    ip_address=ip_address,
                    first_visit=datetime.now(timezone.utc),
                    last_visit=datetime.now(timezone.utc),
                    visit_count=1,
                    last_latitude=(
                        geolocation.get("latitude") if geolocation else None
                    ),
                    last_longitude=(
                        geolocation.get("longitude") if geolocation else None
                    ),
                    geolocation_accuracy=(
                        geolocation.get("accuracy") if geolocation else None
                    ),
                    country=country,
                    city=city,
                    climate_region=climate_region,
                    device_type=device_info.get("device_type"),
                    browser=device_info.get("browser"),
                    os=device_info.get("os"),
                )
                db.add(visitor)
                logger.info(
                    f"✅ Novo visitante criado: {visitor_id} "
                    f"(região: {climate_region})"
                )

            db.commit()
            db.refresh(visitor)
            return visitor

    @staticmethod
    def get_visitor_by_id(visitor_id: str) -> Optional[Visitor]:
        """
        Busca visitante por ID.

        Args:
            visitor_id: UUID do visitante

        Returns:
            Visitor ou None se não encontrado
        """
        with get_db_context() as db:
            return (
                db.query(Visitor)
                .filter(Visitor.visitor_id == visitor_id)
                .first()
            )

    @staticmethod
    def get_visitor_by_session(session_id: str) -> Optional[Visitor]:
        """
        Busca visitante por sessão.

        Args:
            session_id: ID da sessão

        Returns:
            Visitor ou None se não encontrado
        """
        with get_db_context() as db:
            return (
                db.query(Visitor)
                .filter(Visitor.session_id == session_id)
                .first()
            )

    @staticmethod
    def update_geolocation(
        visitor_id: str,
        latitude: float,
        longitude: float,
        accuracy: Optional[float] = None,
    ) -> bool:
        """
        Atualiza geolocalização do visitante.

        Args:
            visitor_id: UUID do visitante
            latitude: Latitude
            longitude: Longitude
            accuracy: Precisão em metros (opcional)

        Returns:
            True se atualizado com sucesso, False caso contrário
        """
        with get_db_context() as db:
            visitor = (
                db.query(Visitor)
                .filter(Visitor.visitor_id == visitor_id)
                .first()
            )

            if visitor:
                visitor.last_latitude = latitude  # type: ignore[assignment]
                visitor.last_longitude = longitude  # type: ignore[assignment]
                visitor.geolocation_accuracy = accuracy  # type: ignore
                visitor.last_visit = datetime.now(timezone.utc)
                db.commit()
                logger.info(f"✅ Geolocalização atualizada: {visitor_id}")
                return True
            else:
                logger.warning(f"⚠️ Visitante não encontrado: {visitor_id}")
                return False

    @staticmethod
    def _detect_climate_region(latitude: float, longitude: float) -> str:
        """
        Detecta região climática (USA, Nordic, ou global).

        Args:
            latitude: Latitude da localização
            longitude: Longitude da localização

        Returns:
            String: "usa", "nordic" ou "global"
        """
        # Bounding boxes para detecção geográfica
        # USA Continental: (-125, 24, -66, 49) = (W, S, E, N)
        # Nordic: (4, 54, 32, 71.5) = (W, S, E, N) — MEPS domain

        # Verificar se está nos EUA
        if -125.0 <= longitude <= -66.0 and 24.0 <= latitude <= 49.0:
            return "usa"

        # Verificar se está na região Nórdica
        if 4.0 <= longitude <= 32.0 and 54.0 <= latitude <= 71.5:
            return "nordic"

        # Global para todas as outras regiões
        return "global"

    @staticmethod
    def _parse_user_agent(user_agent: str) -> Dict[str, Optional[str]]:
        """
        Extrai informações do User-Agent.

        Args:
            user_agent: String do User-Agent

        Returns:
            Dict com device_type, browser, os
        """
        # Detectar tipo de dispositivo
        if "Mobile" in user_agent or "Android" in user_agent:
            device_type = "mobile"
        elif "Tablet" in user_agent or "iPad" in user_agent:
            device_type = "tablet"
        else:
            device_type = "desktop"

        # Detectar navegador
        if "Chrome" in user_agent and "Edg" not in user_agent:
            browser = "chrome"
        elif "Firefox" in user_agent:
            browser = "firefox"
        elif "Safari" in user_agent and "Chrome" not in user_agent:
            browser = "safari"
        elif "Edg" in user_agent:
            browser = "edge"
        else:
            browser = "other"

        # Detectar OS
        if "Windows" in user_agent:
            os_type = "windows"
        elif "Mac" in user_agent:
            os_type = "macos"
        elif "Linux" in user_agent:
            os_type = "linux"
        elif "Android" in user_agent:
            os_type = "android"
        elif "iOS" in user_agent or "iPhone" in user_agent:
            os_type = "ios"
        else:
            os_type = "other"

        return {"device_type": device_type, "browser": browser, "os": os_type}

    @staticmethod
    def generate_visitor_id() -> str:
        """
        Gera ID único para visitante.

        Returns:
            String no formato 'visitor_<uuid>'
        """
        return f"visitor_{uuid4().hex[:12]}"

    @staticmethod
    def generate_session_id() -> str:
        """
        Gera ID único para sessão.

        Returns:
            String no formato 'sess_<uuid>'
        """
        return f"sess_{uuid4().hex[:16]}"
