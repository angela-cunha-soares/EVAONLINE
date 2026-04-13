import os
import sys

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from backend.api.routes import api_router
from backend.api.websocket.websocket_service import router as websocket_router
from config.logging_config import get_logger, setup_logging

from config.settings.app_config import get_legacy_settings
from math import radians, sin, cos, sqrt, atan2

# Configurar logging avançado
def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculates the approximate distance between two points (Haversine).

    Args:
        lat1: Latitude of point 1
        lon1: Longitude of point 1
        lat2: Latitude of point 2
        lon2: Longitude of point 2

    Returns:
        Distance in meters
    """

    R = 6371000  # Earth's radius in meters
    
    lat1_rad = radians(lat1)
    lat2_rad = radians(lat2)
    delta_lat = radians(lat2 - lat1)
    delta_lon = radians(lon2 - lon1)
    
    a = sin(delta_lat / 2) ** 2 + cos(lat1_rad) * cos(lat2_rad) * sin(delta_lon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    
    return R * c
setup_logging(log_level="INFO", log_dir="logs", json_logs=False)
logger = get_logger()

# Load settings
settings = get_legacy_settings()


# ============================================================================
# PRODUCTION SECRET VALIDATION
# ============================================================================
_FORBIDDEN_PATTERNS = [
    "CHANGE_THIS",
    "change-this",
    "your_password",
    "your-password",
    "your_secret",
    "your-secret",
    "changeme",
    "admin123",
    "password123",
]


def _validate_production_secrets():
    """
    Reject default/insecure secrets in production.

    Prevents accidental deployment with template placeholder credentials.
    Only enforced when ENVIRONMENT=production.
    """
    env = os.getenv("ENVIRONMENT", "development")
    if env != "production":
        return

    critical_vars = {
        "SECRET_KEY": os.getenv("SECRET_KEY", ""),
        "POSTGRES_PASSWORD": os.getenv("POSTGRES_PASSWORD", ""),
        "REDIS_PASSWORD": os.getenv("REDIS_PASSWORD", ""),
    }

    for var_name, value in critical_vars.items():
        if not value or len(value) < 16:
            logger.critical(
                f"FATAL: {var_name} is empty or too short (min 16 chars). "
                f"Generate a secure secret: python -c "
                f"\"import secrets; print(secrets.token_urlsafe(32))\""
            )
            sys.exit(1)

        for pattern in _FORBIDDEN_PATTERNS:
            if pattern.lower() in value.lower():
                logger.critical(
                    f"FATAL: {var_name} contains default placeholder "
                    f"'{pattern}'. Replace with a secure generated value "
                    f"before deploying to production."
                )
                sys.exit(1)

    logger.info("Production secret validation passed")


_validate_production_secrets()


def create_application() -> FastAPI:
    app = FastAPI(
        title="EVAonline",
        version="1.0.0",
        openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
        docs_url=f"{settings.API_V1_PREFIX}/docs",
        redoc_url=f"{settings.API_V1_PREFIX}/redoc",
    )

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.BACKEND_CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Add Prometheus middleware
    from backend.api.middleware.prometheus import PrometheusMiddleware

    app.add_middleware(PrometheusMiddleware)

    # Create routes
    app.include_router(api_router, prefix=settings.API_V1_PREFIX)
    app.include_router(websocket_router)

    # Configure Prometheus metrics
    Instrumentator().instrument(app).expose(app, endpoint="/metrics")

    # Serving static files from the frontend
    from fastapi.staticfiles import StaticFiles
    from pathlib import Path

    assets_dir = Path("assets")
    if assets_dir.exists():
        app.mount(
            "/frontend/assets", StaticFiles(directory="assets"), name="assets"
        )

    # Note: Root endpoint will be handled by Dash frontend
    # API docs available at /api/v1/docs

    return app


def mount_dash(app: FastAPI) -> FastAPI:
    """Mount Dash application into FastAPI."""
    try:
        from frontend.app import app as dash_app
        from fastapi.middleware.wsgi import WSGIMiddleware

        logger.info("Mounting Dash frontend into FastAPI...")

        # Mount Dash app at root path
        app.mount("/", WSGIMiddleware(dash_app.server))

        logger.info("Dash frontend mounted successfully at /")
        return app
    except Exception as e:
        logger.error(f"Failed to mount Dash: {e}")
        logger.info("Dash will run separately on port 8050")
        return app


# First, create a FastAPI application
app = create_application()

# Install Dash last (after all API routes have been registered)
app = mount_dash(app)

if __name__ == "__main__":
    import uvicorn

    # uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=settings.DEBUG)
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
