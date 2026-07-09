"""Standard API response envelope and response-builder helpers.

Every endpoint returns one of two shapes so clients can rely on a single format::

    success: { "success": true,  "message": "...", "data": {...}, "meta": {...} }
    error:   { "success": false, "message": "...", "error": {...}, "meta": {...} }

Use the builder helpers (:func:`success_response`, :func:`error_response`,
:func:`paginated_response`) rather than constructing dicts by hand.
"""

from __future__ import annotations

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

from app.shared.schemas.pagination import PaginationMeta

T = TypeVar("T")


class APIMessage(BaseModel):
    """A bare message payload (e.g. for 200s with no resource body)."""

    message: str


class ResponseMeta(BaseModel):
    """Envelope metadata: correlation id and optional pagination block."""

    request_id: str | None = None
    pagination: PaginationMeta | None = None


class SuccessResponse(BaseModel, Generic[T]):
    """Standard success envelope."""

    success: bool = True
    message: str = "OK"
    data: T | None = None
    meta: ResponseMeta | None = None


class ErrorDetail(BaseModel):
    """A single field/param-level error."""

    field: str | None = None
    message: str
    code: str | None = None


class ErrorInfo(BaseModel):
    """The ``error`` block of an error envelope."""

    code: str
    message: str
    details: list[ErrorDetail] | None = None


class ErrorResponse(BaseModel):
    """Standard error envelope."""

    success: bool = False
    message: str
    error: ErrorInfo
    meta: ResponseMeta | None = None


class ValidationErrorResponse(ErrorResponse):
    """Error envelope specialised for validation failures (422)."""

    error: ErrorInfo = Field(
        default_factory=lambda: ErrorInfo(code="VALIDATION_ERROR", message="Validation failed.")
    )


# --- Builder helpers ---------------------------------------------------------


def success_response(
    data: Any = None,
    *,
    message: str = "OK",
    request_id: str | None = None,
    pagination: PaginationMeta | None = None,
) -> dict[str, Any]:
    """Build a success envelope as a plain dict (ready to return from a route)."""
    meta = ResponseMeta(request_id=request_id, pagination=pagination)
    return SuccessResponse(message=message, data=data, meta=meta).model_dump()


def paginated_response(
    items: list[Any],
    *,
    page: int,
    page_size: int,
    total_records: int,
    message: str = "OK",
    request_id: str | None = None,
) -> dict[str, Any]:
    """Build a success envelope whose ``data`` is a list plus pagination meta."""
    pagination = PaginationMeta.build(
        page=page, page_size=page_size, total_records=total_records
    )
    return success_response(
        {"items": items},
        message=message,
        request_id=request_id,
        pagination=pagination,
    )


def error_response(
    *,
    code: str,
    message: str,
    details: list[ErrorDetail] | None = None,
    request_id: str | None = None,
) -> dict[str, Any]:
    """Build an error envelope as a plain dict."""
    return ErrorResponse(
        message=message,
        error=ErrorInfo(code=code, message=message, details=details),
        meta=ResponseMeta(request_id=request_id),
    ).model_dump()
