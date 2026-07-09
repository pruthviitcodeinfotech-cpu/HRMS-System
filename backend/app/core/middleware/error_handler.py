"""Top-level error-boundary middleware.

FastAPI's registered exception handlers (:mod:`app.core.exceptions.handlers`) are
the primary mechanism for rendering errors. This middleware is a thin safety net
that guarantees any exception escaping the handler stack (e.g. raised in another
middleware) still becomes the standard error envelope instead of a bare ASGI 500.
"""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core.exceptions.base import AppException
from app.core.logging.config import get_logger
from app.core.middleware.request_context import get_request_id
from app.shared.schemas.response import error_response

_logger = get_logger("error_boundary")


class ExceptionHandlingMiddleware(BaseHTTPMiddleware):
    """Convert unhandled exceptions into the standard error envelope."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        try:
            return await call_next(request)
        except AppException as exc:
            return JSONResponse(
                status_code=exc.status_code,
                content=error_response(
                    code=exc.code,
                    message=exc.message,
                    details=exc.details if isinstance(exc.details, list) else None,
                    request_id=get_request_id(),
                ),
            )
        except Exception as exc:  # noqa: BLE001 - last-resort boundary
            _logger.exception("unhandled_exception_in_middleware", error=str(exc))
            return JSONResponse(
                status_code=500,
                content=error_response(
                    code="INTERNAL_ERROR",
                    message="An unexpected error occurred.",
                    request_id=get_request_id(),
                ),
            )
