"""Application exception hierarchy.

Every domain/infrastructure error raised inside the app inherits from
:class:`AppException`. Each carries a stable machine-readable ``code``, an HTTP
``status_code``, a safe human ``message``, and optional structured ``details``
(e.g. field-level validation errors). The global exception handlers
(:mod:`app.core.exceptions.handlers`) render these into the standard envelope.
"""

from __future__ import annotations

from typing import Any


class AppException(Exception):
    """Base class for all application errors.

    Attributes:
        code: stable, machine-readable error code (e.g. ``NOT_FOUND``).
        status_code: HTTP status to return.
        message: safe, human-readable message (no secrets/SQL/tokens).
        details: optional structured payload (e.g. field errors).
    """

    code: str = "APP_ERROR"
    status_code: int = 500
    message: str = "An unexpected error occurred."

    def __init__(
        self,
        message: str | None = None,
        *,
        code: str | None = None,
        details: Any | None = None,
    ) -> None:
        self.message = message or self.message
        self.code = code or self.code
        self.details = details
        super().__init__(self.message)


class ValidationException(AppException):
    """Request payload / parameter failed validation."""

    code = "VALIDATION_ERROR"
    status_code = 422
    message = "The request could not be validated."


class AuthenticationException(AppException):
    """Missing, invalid, or expired credentials."""

    code = "AUTH_NOT_AUTHENTICATED"
    status_code = 401
    message = "Authentication is required."


class AuthorizationException(AppException):
    """Authenticated but not permitted (feature permission or data scope)."""

    code = "AUTH_FORBIDDEN"
    status_code = 403
    message = "You do not have permission to perform this action."


class NotFoundException(AppException):
    """A referenced resource does not exist within the caller's scope."""

    code = "NOT_FOUND"
    status_code = 404
    message = "The requested resource was not found."


class ConflictException(AppException):
    """The request conflicts with current state (uniqueness, invalid transition)."""

    code = "CONFLICT"
    status_code = 409
    message = "The request conflicts with the current state of the resource."


class DatabaseException(AppException):
    """An unexpected database/persistence error."""

    code = "DATABASE_ERROR"
    status_code = 500
    message = "A database error occurred."


class RateLimitException(AppException):
    """Too many requests for a rate-limited operation."""

    code = "RATE_LIMITED"
    status_code = 429
    message = "Too many requests. Please try again later."
