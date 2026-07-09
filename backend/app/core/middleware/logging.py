"""Access + timing logging middleware.

Logs one structured line per request with method, path, status code, execution
time (ms), client, and the correlation id (added by
:class:`~app.core.middleware.request_context.RequestContextMiddleware`).
Unhandled exceptions are logged with a traceback and re-raised so the registered
exception handlers can render the error envelope.
"""

from __future__ import annotations

import time

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.core.logging.config import get_logger

_logger = get_logger("http")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Emit a structured access log with timing for every request."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        start = time.perf_counter()
        method = request.method
        path = request.url.path
        client = request.client.host if request.client else None
        try:
            response = await call_next(request)
        except Exception:
            duration_ms = round((time.perf_counter() - start) * 1000, 2)
            _logger.exception(
                "request_failed",
                method=method,
                path=path,
                client=client,
                duration_ms=duration_ms,
            )
            raise
        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        _logger.info(
            "request_completed",
            method=method,
            path=path,
            status_code=response.status_code,
            client=client,
            duration_ms=duration_ms,
        )
        response.headers["X-Response-Time-ms"] = str(duration_ms)
        return response
