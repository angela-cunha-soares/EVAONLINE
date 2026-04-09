"""
Middleware para monitoramento de requisições.
"""

import time
from collections.abc import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from backend.api.middleware.prometheus_metrics import (
    API_ACTIVE_REQUESTS,
    API_REQUEST_DURATION,
    API_REQUESTS,
)


class PrometheusMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        method = request.method
        path = request.url.path

        # Incrementar contador de requisições ativas
        API_ACTIVE_REQUESTS.labels(method=method, endpoint=path).inc()

        # Medir tempo de resposta
        start_time = time.time()

        try:
            response = await call_next(request)

            # Registrar métricas
            API_REQUESTS.labels(
                method=method, endpoint=path, status_code=response.status_code
            ).inc()

            API_REQUEST_DURATION.labels(method=method, endpoint=path).observe(
                time.time() - start_time
            )

            return response

        finally:
            # Decrementar contador de requisições ativas
            API_ACTIVE_REQUESTS.labels(method=method, endpoint=path).dec()
