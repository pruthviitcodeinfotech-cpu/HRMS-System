"""Global FastAPI exception handlers → standard error envelope.

``register_exception_handlers(app)`` maps every error class to the standard error
response shape (see :mod:`app.shared.schemas.response`):

    * :class:`~app.core.exceptions.base.AppException` — domain/infra errors.
    * ``RequestValidationError`` / pydantic ``ValidationError`` — 422 with field details.
    * ``StarletteHTTPException`` — framework HTTP errors (404 routing, etc.).
    * ``Exception`` — last-resort 500 (message is generic; details are logged only).
"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.exceptions.base import AppException
from app.core.logging.config import get_logger
from app.core.middleware.request_context import get_request_id
from app.shared.schemas.response import ErrorDetail, error_response

_logger = get_logger("errors")


def _details_from_validation(exc: RequestValidationError | ValidationError) -> list[ErrorDetail]:
    details: list[ErrorDetail] = []
    for err in exc.errors():
        loc = ".".join(str(p) for p in err.get("loc", ()) if p not in ("body", "query", "path"))
        details.append(
            ErrorDetail(field=loc or None, message=err.get("msg", "invalid"), code=err.get("type"))
        )
    return details


def register_exception_handlers(app: FastAPI) -> None:
    """Register all global exception handlers on ``app``."""

    @app.exception_handler(AppException)
    async def _handle_app_exception(_request: Request, exc: AppException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=error_response(
                code=exc.code,
                message=exc.message,
                details=exc.details if isinstance(exc.details, list) else None,
                request_id=get_request_id(),
            ),
        )

    @app.exception_handler(RequestValidationError)
    async def _handle_request_validation(
        _request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content=error_response(
                code="VALIDATION_ERROR",
                message="The request could not be validated.",
                details=_details_from_validation(exc),
                request_id=get_request_id(),
            ),
        )

    @app.exception_handler(ValidationError)
    async def _handle_pydantic_validation(
        _request: Request, exc: ValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content=error_response(
                code="VALIDATION_ERROR",
                message="The request could not be validated.",
                details=_details_from_validation(exc),
                request_id=get_request_id(),
            ),
        )

    @app.exception_handler(StarletteHTTPException)
    async def _handle_http_exception(
        _request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        message = exc.detail if isinstance(exc.detail, str) else "HTTP error."
        return JSONResponse(
            status_code=exc.status_code,
            content=error_response(
                code=f"HTTP_{exc.status_code}",
                message=message,
                request_id=get_request_id(),
            ),
            headers=getattr(exc, "headers", None),
        )

    @app.exception_handler(Exception)
    async def _handle_unexpected(_request: Request, exc: Exception) -> JSONResponse:
        _logger.exception("unhandled_exception", error=str(exc))
        return JSONResponse(
            status_code=500,
            content=error_response(
                code="INTERNAL_ERROR",
                message="An unexpected error occurred.",
                request_id=get_request_id(),
            ),
        )
