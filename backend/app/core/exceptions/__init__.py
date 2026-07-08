"""Application exceptions and global handler registration."""

from app.core.exceptions.base import (
    AppException,
    AuthenticationException,
    AuthorizationException,
    ConflictException,
    DatabaseException,
    NotFoundException,
    RateLimitException,
    ValidationException,
)
from app.core.exceptions.handlers import register_exception_handlers

__all__ = [
    "AppException",
    "AuthenticationException",
    "AuthorizationException",
    "ConflictException",
    "DatabaseException",
    "NotFoundException",
    "RateLimitException",
    "ValidationException",
    "register_exception_handlers",
]
