"""
Middlewares da aplicação FastAPI.
"""

from backend.api.middleware.prometheus import PrometheusMiddleware

__all__ = ["PrometheusMiddleware"]
