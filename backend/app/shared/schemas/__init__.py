"""Shared response and pagination schemas + response builders."""

from app.shared.schemas.pagination import (
    PaginatedResponse,
    PaginationMeta,
    PaginationRequest,
)
from app.shared.schemas.response import (
    APIMessage,
    ErrorDetail,
    ErrorInfo,
    ErrorResponse,
    ResponseMeta,
    SuccessResponse,
    ValidationErrorResponse,
    error_response,
    paginated_response,
    success_response,
)

__all__ = [
    "APIMessage",
    "SuccessResponse",
    "ErrorResponse",
    "ErrorDetail",
    "ErrorInfo",
    "ResponseMeta",
    "ValidationErrorResponse",
    "success_response",
    "error_response",
    "paginated_response",
    "PaginationRequest",
    "PaginationMeta",
    "PaginatedResponse",
]
