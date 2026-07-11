"""Global FastAPI exception handlers → standard error envelope.

``register_exception_handlers(app)`` maps every error class to the standard error
response shape (see :mod:`app.shared.schemas.response`):

    * :class:`~app.core.exceptions.base.AppException` — domain/infra errors.
    * ``RequestValidationError`` / pydantic ``ValidationError`` — 422 with field details.
    * ``IntegrityError`` — a database constraint the service's pre-check lost a race to.
    * ``StarletteHTTPException`` — framework HTTP errors (404 routing, etc.).
    * ``Exception`` — last-resort 500 (message is generic; details are logged only).
"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.exceptions.base import AppException
from app.core.logging.config import get_logger
from app.core.middleware.request_context import get_request_id
from app.shared.schemas.response import ErrorDetail, error_response

_logger = get_logger("errors")

# PostgreSQL SQLSTATE codes for the integrity violations a request can legitimately
# provoke. Services pre-check uniqueness ("does this name exist?") before inserting,
# but that check and the insert are not atomic: two concurrent identical requests both
# pass the check and one loses at the database. Without this mapping the loser gets a
# 500 — which is what a double-clicked submit button or two admins acting at once
# actually produced (measured: 9 of 10 concurrent creates returned 500).
_INTEGRITY_MAP: dict[str, tuple[int, str, str]] = {
    "23505": (409, "CONFLICT", "This record already exists."),
    "23503": (409, "CONFLICT", "A referenced record does not exist or is still in use."),
    "23502": (422, "VALIDATION_ERROR", "A required field was missing."),
    "23514": (422, "VALIDATION_ERROR", "A field value is not allowed."),
}


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
            # Optional response headers set by the raiser (e.g. ``Retry-After`` on a
            # 429 RATE_LIMITED); absent on virtually every other AppException.
            headers=getattr(exc, "headers", None),
        )

    @app.exception_handler(IntegrityError)
    async def _handle_integrity_error(_request: Request, exc: IntegrityError) -> JSONResponse:
        """Map a database constraint violation to the right HTTP status.

        The database is the last line of defence for uniqueness and referential
        integrity, and under concurrency it is the *only* one that holds. A violation
        here is a legitimate client-visible conflict, not a server fault — the driver
        message is logged but never returned (it can carry SQL and column values).
        """
        sqlstate = getattr(getattr(exc, "orig", None), "sqlstate", None) or getattr(
            getattr(exc, "orig", None), "pgcode", None
        )
        status_code, code, message = _INTEGRITY_MAP.get(
            str(sqlstate), (409, "CONFLICT", "The request conflicts with the current state.")
        )
        _logger.warning(
            "integrity_error",
            sqlstate=str(sqlstate),
            constraint=getattr(getattr(exc, "orig", None), "constraint_name", None),
        )
        return JSONResponse(
            status_code=status_code,
            content=error_response(code=code, message=message, request_id=get_request_id()),
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
