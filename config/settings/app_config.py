"""
===========================================
SETTINGS CONFIGURATION - EVAonline
===========================================
Configurações centralizadas usando Pydantic Settings.
"""

from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseSettings):
    """Configurações do banco de dados PostgreSQL."""

    model_config = SettingsConfigDict(env_prefix="POSTGRES_")

    HOST: str = Field(default="localhost", description="PostgreSQL host")
    PORT: int = Field(default=5432, description="PostgreSQL port")
    DB: str = Field(default="evaonline", description="Database name")
    USER: str = Field(default="postgres", description="Database user")
    PASSWORD: str = Field(default="", description="Database password")

    # Pool de conexões
    POOL_SIZE: int = Field(default=20, description="Connection pool size")
    MAX_OVERFLOW: int = Field(
        default=0, description="Max overflow connections"
    )
    POOL_TIMEOUT: int = Field(
        default=30, description="Pool timeout in seconds"
    )
    POOL_RECYCLE: int = Field(
        default=3600, description="Connection recycle time in seconds"
    )

    @property
    def database_url(self) -> str:
        """Retorna a URL de conexão ao banco de dados."""
        return (
            f"postgresql://{self.USER}:{self.PASSWORD}"
            f"@{self.HOST}:{self.PORT}/{self.DB}"
        )

    @property
    def async_database_url(self) -> str:
        """Retorna a URL de conexão assíncrona ao banco de dados."""
        return (
            f"postgresql+asyncpg://{self.USER}:"
            f"{self.PASSWORD}@{self.HOST}:"
            f"{self.PORT}/{self.DB}"
        )


class RedisSettings(BaseSettings):
    """Configurações do Redis."""

    model_config = SettingsConfigDict(env_prefix="REDIS_")

    HOST: str = Field(default="localhost", description="Redis host")
    PORT: int = Field(default=6379, description="Redis port")
    DB: int = Field(default=0, description="Redis database number")
    PASSWORD: Optional[str] = Field(default=None, description="Redis password")
    MAX_CONNECTIONS: int = Field(
        default=50, description="Max Redis connections"
    )
    SOCKET_TIMEOUT: int = Field(
        default=5, description="Socket timeout in seconds"
    )
    SOCKET_CONNECT_TIMEOUT: int = Field(
        default=5, description="Socket connect timeout in seconds"
    )

    @property
    def redis_url(self) -> str:
        """Retorna a URL de conexão ao Redis."""
        if self.PASSWORD:
            return (
                f"redis://:{self.PASSWORD}@{self.HOST}:"
                f"{self.PORT}/{self.DB}"
            )
        return f"redis://{self.HOST}:{self.PORT}/{self.DB}"


class CelerySettings(BaseSettings):
    """Configurações do Celery."""

    model_config = SettingsConfigDict(env_prefix="CELERY_")

    BROKER_URL: Optional[str] = Field(default=None, description="Broker URL")
    RESULT_BACKEND: Optional[str] = Field(
        default=None, description="Result backend URL"
    )
    TASK_SERIALIZER: str = Field(default="json", description="Task serializer")
    RESULT_SERIALIZER: str = Field(
        default="json", description="Result serializer"
    )
    ACCEPT_CONTENT: List[str] = Field(
        default=["json"], description="Accepted content types"
    )
    TIMEZONE: str = Field(default="America/Sao_Paulo", description="Timezone")
    ENABLE_UTC: bool = Field(default=True, description="Enable UTC")
    TASK_TRACK_STARTED: bool = Field(
        default=True, description="Track task started state"
    )
    TASK_TIME_LIMIT: int = Field(
        default=3600, description="Task time limit in seconds"
    )
    TASK_SOFT_TIME_LIMIT: int = Field(
        default=3300, description="Task soft time limit in seconds"
    )


class APISettings(BaseSettings):
    """Configurações da API FastAPI."""

    model_config = SettingsConfigDict(env_prefix="API_")

    # Server
    HOST: str = Field(default="0.0.0.0", description="FastAPI host")
    PORT: int = Field(default=8000, description="FastAPI port")
    WORKERS: int = Field(default=4, description="Number of workers")
    RELOAD: bool = Field(default=False, description="Enable auto-reload")

    # API
    V1_PREFIX: str = Field(default="/api/v1", description="API v1 prefix")
    TITLE: str = Field(default="EVAonline API", description="API title")
    DESCRIPTION: str = Field(
        default="API para cálculo de Evapotranspiração",
        description="API description",
    )
    VERSION: str = Field(default="1.0.0", description="API version")

    # CORS
    CORS_ORIGINS: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8050"],
        description="Allowed CORS origins",
    )
    CORS_ALLOW_CREDENTIALS: bool = Field(
        default=True, description="Allow credentials in CORS"
    )
    CORS_ALLOW_METHODS: List[str] = Field(
        default=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        description="Allowed methods",
    )
    CORS_ALLOW_HEADERS: List[str] = Field(
        default=["*"], description="Allowed headers"
    )

    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = Field(
        default=True, description="Enable rate limiting"
    )
    RATE_LIMIT_PER_MINUTE: int = Field(
        default=60, description="Requests per minute limit"
    )


class DashSettings(BaseSettings):
    """Configurações do Dashboard Dash."""

    model_config = SettingsConfigDict(env_prefix="DASH_")

    HOST: str = Field(default="0.0.0.0", description="Dash host")
    PORT: int = Field(default=8050, description="Dash port")
    DEBUG: bool = Field(default=False, description="Enable debug mode")
    DEV_TOOLS_HOT_RELOAD: bool = Field(
        default=False, description="Enable hot reload"
    )


class ClimateAPISettings(BaseSettings):
    """Configurações de APIs de clima."""

    model_config = SettingsConfigDict(env_prefix="CLIMATE_")

    # NASA POWER
    NASA_POWER_BASE_URL: str = Field(
        default="https://power.larc.nasa.gov/api/temporal/daily/point",
        description="NASA POWER API base URL",
    )
    NASA_POWER_TIMEOUT: int = Field(
        default=30, description="Request timeout in seconds"
    )

    # MET Norway
    MET_NORWAY_BASE_URL: str = Field(
        default="https://api.met.no/weatherapi/locationforecast/2.0/",
        description="MET Norway API base URL",
    )
    MET_NORWAY_USER_AGENT: str = Field(
        default="EVAonline/1.0",
        description="User agent",
    )

    # Open-Meteo
    OPENMETEO_BASE_URL: str = Field(
        default="https://api.open-meteo.com/v1/",
        description="Open-Meteo API base URL",
    )

    # NWS (National Weather Service)
    NWS_BASE_URL: str = Field(
        default="https://api.weather.gov/", description="NWS API base URL"
    )

    # Cache
    CACHE_ENABLED: bool = Field(default=True, description="Enable API cache")
    CACHE_EXPIRE: int = Field(
        default=3600, description="Cache expiration in seconds"
    )


class LoggingSettings(BaseSettings):
    """Configurações de logging."""

    model_config = SettingsConfigDict(env_prefix="LOG_")

    LEVEL: str = Field(default="INFO", description="Logging level")
    DIR: str = Field(default="logs", description="Logs directory")
    JSON: bool = Field(default=False, description="Use JSON format")
    ROTATION: str = Field(default="00:00", description="Log rotation time")
    RETENTION: str = Field(
        default="30 days", description="Log retention period"
    )
    COMPRESSION: str = Field(
        default="zip", description="Log compression format"
    )

    @field_validator("LEVEL")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Valida o nível de log."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(
                f"LOG_LEVEL deve ser um de: {', '.join(valid_levels)}"
            )
        return v.upper()


class Settings(BaseSettings):
    """Configurações principais da aplicação."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # Environment
    ENVIRONMENT: str = Field(
        default="development",
        description="Environment (development, staging, production)",
    )
    DEBUG: bool = Field(default=False, description="Debug mode")
    SECRET_KEY: str = Field(
        default="your-secret-key-change-this-in-production",
        description="Secret key for sessions",
    )

    # Timezone
    TIMEZONE: str = Field(
        default="America/Sao_Paulo", description="Application timezone"
    )

    # Paths
    BASE_DIR: Path = Field(
        default_factory=lambda: Path(__file__).parent.parent.parent,
        description="Base directory",
    )
    DATA_DIR: Path = Field(default=Path("data"), description="Data directory")
    TEMP_DIR: Path = Field(
        default=Path("temp"), description="Temporary directory"
    )

    # Sub-configurações
    database: DatabaseSettings = DatabaseSettings()
    redis: RedisSettings = RedisSettings()
    celery: CelerySettings = CelerySettings()
    api: APISettings = APISettings()
    dash: DashSettings = DashSettings()
    climate_apis: ClimateAPISettings = ClimateAPISettings()
    logging: LoggingSettings = LoggingSettings()

    def __init__(self, **kwargs: Any) -> None:
        """Inicializa as configurações."""
        super().__init__(**kwargs)

        # Criar diretórios necessários
        self.DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.TEMP_DIR.mkdir(parents=True, exist_ok=True)

        # Configurar Celery se não definido
        if not self.celery.BROKER_URL:
            self.celery.BROKER_URL = self.redis.redis_url
        if not self.celery.RESULT_BACKEND:
            self.celery.RESULT_BACKEND = self.redis.redis_url

    @field_validator("ENVIRONMENT")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        """Valida o ambiente."""
        valid_envs = ["development", "staging", "production", "testing"]
        if v.lower() not in valid_envs:
            raise ValueError(
                f"ENVIRONMENT deve ser um de: {', '.join(valid_envs)}"
            )
        return v.lower()

    @property
    def is_production(self) -> bool:
        """Verifica se está em produção."""
        return self.ENVIRONMENT == "production"

    @property
    def is_development(self) -> bool:
        """Verifica se está em desenvolvimento."""
        return self.ENVIRONMENT == "development"

    @property
    def is_staging(self) -> bool:
        """Verifica se está em staging."""
        return self.ENVIRONMENT == "staging"

    @property
    def is_testing(self) -> bool:
        """Verifica se está em testing."""
        return self.ENVIRONMENT == "testing"


@lru_cache
def get_settings() -> Settings:
    """
    Retorna a instância singleton das configurações.

    Returns:
        Settings: Instância das configurações
    """
    return Settings()


# ===========================================
# ADAPTADOR DE COMPATIBILIDADE
# ===========================================


class LegacySettingsAdapter:
    """
    Adaptador que mantém compatibilidade com a API antiga das configurações.
    """

    def __init__(self, settings: Settings):
        self._settings = settings

    # ===========================================
    # PROPRIEDADES DIRETAS (compatibilidade)
    # ===========================================

    @property
    def PROJECT_NAME(self) -> str:
        return "EVAonline"

    @property
    def VERSION(self) -> str:
        return "1.0.0"

    @property
    def DEBUG(self) -> bool:
        return self._settings.DEBUG

    @property
    def ENVIRONMENT(self) -> str:
        return self._settings.ENVIRONMENT

    @property
    def SECRET_KEY(self) -> str:
        return self._settings.SECRET_KEY

    @property
    def API_V1_PREFIX(self) -> str:
        return self._settings.api.V1_PREFIX

    @property
    def BACKEND_CORS_ORIGINS(self) -> List[str]:
        return self._settings.api.CORS_ORIGINS

    # ===========================================
    # DASH CONFIGURAÇÕES
    # ===========================================

    @property
    def DASH_URL_BASE_PATHNAME(self) -> str:
        return "/"

    @property
    def DASH_ASSETS_FOLDER(self) -> str:
        return "frontend/assets"

    @property
    def DASH_ROUTES(self) -> Dict[str, str]:
        return {
            "home": "/",
            "eto_calculator": "/eto_calculator",
            "about": "/about",
            "documentation": "/documentation",
        }

    # ===========================================
    # BANCO DE DADOS
    # ===========================================

    @property
    def POSTGRES_SERVER(self) -> str:
        return self._settings.database.HOST

    @property
    def POSTGRES_HOST(self) -> str:
        return self._settings.database.HOST

    @property
    def POSTGRES_USER(self) -> str:
        return self._settings.database.USER

    @property
    def POSTGRES_PASSWORD(self) -> str:
        return self._settings.database.PASSWORD

    @property
    def POSTGRES_DB(self) -> str:
        return self._settings.database.DB

    @property
    def POSTGRES_PORT(self) -> int:
        return self._settings.database.PORT

    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        return self._settings.database.database_url

    @property
    def SQLALCHEMY_DATABASE_URI_ASYNC(self) -> str:
        return self._settings.database.async_database_url

    # Pool de conexões
    @property
    def DB_POOL_SIZE(self) -> int:
        return self._settings.database.POOL_SIZE

    @property
    def DB_MAX_OVERFLOW(self) -> int:
        return self._settings.database.MAX_OVERFLOW

    @property
    def DB_POOL_RECYCLE(self) -> int:
        return self._settings.database.POOL_RECYCLE

    @property
    def DB_POOL_TIMEOUT(self) -> int:
        return self._settings.database.POOL_TIMEOUT

    # ===========================================
    # REDIS
    # ===========================================

    @property
    def REDIS_HOST(self) -> str:
        return self._settings.redis.HOST

    @property
    def REDIS_PORT(self) -> int:
        return self._settings.redis.PORT

    @property
    def REDIS_DB(self) -> int:
        return self._settings.redis.DB

    @property
    def REDIS_PASSWORD(self) -> Optional[str]:
        return self._settings.redis.PASSWORD

    @property
    def REDIS_MAX_CONNECTIONS(self) -> int:
        return self._settings.redis.MAX_CONNECTIONS

    @property
    def REDIS_SOCKET_TIMEOUT(self) -> int:
        return self._settings.redis.SOCKET_TIMEOUT

    @property
    def REDIS_SOCKET_CONNECT_TIMEOUT(self) -> int:
        return self._settings.redis.SOCKET_CONNECT_TIMEOUT

    @property
    def REDIS_URL(self) -> str:
        return self._settings.redis.redis_url

    # ===========================================
    # CELERY
    # ===========================================

    @property
    def CELERY_BROKER_URL(self) -> str:
        return (
            self._settings.celery.BROKER_URL or self._settings.redis.redis_url
        )

    @property
    def CELERY_RESULT_BACKEND(self) -> str:
        return (
            self._settings.celery.RESULT_BACKEND
            or self._settings.redis.redis_url
        )

    @property
    def CELERY_WORKER_CONCURRENCY(self) -> int:
        return 4

    @property
    def CELERY_WORKER_PREFETCH_MULTIPLIER(self) -> int:
        return 4

    @property
    def CELERY_TASK_SOFT_TIME_LIMIT(self) -> int:
        return self._settings.celery.TASK_SOFT_TIME_LIMIT

    @property
    def CELERY_TASK_TIME_LIMIT(self) -> int:
        return self._settings.celery.TASK_TIME_LIMIT

    @property
    def CELERY_TASK_ACKS_LATE(self) -> bool:
        return True

    @property
    def CELERY_WORKER_SEND_TASK_EVENTS(self) -> bool:
        return True

    @property
    def CELERY_TASK_SEND_SENT_EVENT(self) -> bool:
        return True

    # ===========================================
    # CACHE
    # ===========================================

    @property
    def CACHE_TTL(self) -> int:
        return 60 * 60 * 24  # 24 horas

    @property
    def CACHE_SHORT_TTL(self) -> int:
        return 60 * 15  # 15 minutos

    @property
    def CACHE_LONG_TTL(self) -> int:
        return 60 * 60 * 24 * 7  # 7 dias

    @property
    def CACHE_ENABLED(self) -> bool:
        return True

    @property
    def CACHE_COMPRESSION(self) -> bool:
        return True

    @property
    def CACHE_KEY_PREFIX(self) -> str:
        return "evaonline"

    # ===========================================
    # APIs EXTERNAS
    # ===========================================

    @property
    def OPEN_METEO_ELEVATION_URL(self) -> str:
        return self._settings.climate_apis.OPENMETEO_BASE_URL

    @property
    def OPEN_METEO_TIMEOUT(self) -> int:
        return self._settings.climate_apis.NASA_POWER_TIMEOUT

    @property
    def OPEN_METEO_MAX_RETRIES(self) -> int:
        return 3

    @property
    def NASA_POWER_URL(self) -> str:
        return self._settings.climate_apis.NASA_POWER_BASE_URL

    @property
    def NASA_POWER_TIMEOUT(self) -> int:
        return self._settings.climate_apis.NASA_POWER_TIMEOUT

    @property
    def EXTERNAL_API_RATE_LIMIT(self) -> int:
        return 100

    # ===========================================
    # MONITORAMENTO
    # ===========================================

    @property
    def PROMETHEUS_ENABLED(self) -> bool:
        return True

    @property
    def PROMETHEUS_PORT(self) -> int:
        return 8001

    @property
    def ADMIN_DASHBOARDS(self) -> Dict[str, str]:
        return {
            "grafana": "http://localhost:3000",
            "prometheus": "http://localhost:9090",
        }

    @property
    def LOG_LEVEL(self) -> str:
        return self._settings.logging.LEVEL

    @property
    def LOG_FORMAT(self) -> str:
        return "json" if self._settings.logging.JSON else "console"

    # ===========================================
    # SEGURANÇA
    # ===========================================

    @property
    def HEALTH_CHECK_ENDPOINT(self) -> str:
        return "/health"

    @property
    def READINESS_ENDPOINT(self) -> str:
        return "/ready"

    @property
    def CORS_ALLOW_CREDENTIALS(self) -> bool:
        return self._settings.api.CORS_ALLOW_CREDENTIALS

    @property
    def CORS_ALLOW_METHODS(self) -> List[str]:
        return self._settings.api.CORS_ALLOW_METHODS

    @property
    def CORS_ALLOW_HEADERS(self) -> List[str]:
        return self._settings.api.CORS_ALLOW_HEADERS

    @property
    def RATE_LIMIT_ENABLED(self) -> bool:
        return self._settings.api.RATE_LIMIT_ENABLED

    @property
    def RATE_LIMIT_REQUESTS(self) -> int:
        return self._settings.api.RATE_LIMIT_PER_MINUTE

    @property
    def RATE_LIMIT_WINDOW(self) -> int:
        return 60


@lru_cache
def get_legacy_settings() -> LegacySettingsAdapter:
    """
    Retorna adaptador compatível com a API antiga.

    Returns:
        LegacySettingsAdapter: Instância compatível com API antiga
    """
    settings = get_settings()
    return LegacySettingsAdapter(settings)


# ===========================================
# Funções auxiliares para uso direto
# ===========================================


def get_database_url() -> str:
    """Retorna a URL do banco de dados."""
    settings = get_settings()
    return settings.database.database_url


def get_async_database_url() -> str:
    """Retorna a URL assíncrona do banco de dados."""
    settings = get_settings()
    return settings.database.async_database_url


def get_redis_url() -> str:
    """Retorna a URL do Redis."""
    settings = get_settings()
    return settings.redis.redis_url


def get_celery_broker_url() -> str:
    """Retorna a URL do broker do Celery."""
    settings = get_settings()
    return settings.celery.BROKER_URL or settings.redis.redis_url


def get_celery_result_backend() -> str:
    """Retorna a URL do backend de resultados do Celery."""
    settings = get_settings()
    return settings.celery.RESULT_BACKEND or settings.redis.redis_url


# Alias para compatibilidade
config = get_settings()
legacy_config = get_legacy_settings()
