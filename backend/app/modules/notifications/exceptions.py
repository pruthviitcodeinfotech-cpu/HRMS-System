"""Notifications module-specific exception types.

Maps to the error codes defined in the approved Notification Management API Contract.
"""

from __future__ import annotations

from app.core.exceptions.base import ConflictException, NotFoundException, ValidationException


class NotificationNotFoundException(NotFoundException):
    """Raised when a notification definition is not found."""

    code = "NOTIFICATION_NOT_FOUND"
    message = "Notification not found."


class RecipientNotFoundException(NotFoundException):
    """Raised when a user recipient association is not found."""

    code = "RECIPIENT_NOT_FOUND"
    message = "Notification recipient not found."


class UserNotFoundException(NotFoundException):
    """Raised when a targeted user is not found."""

    code = "USER_NOT_FOUND"
    message = "User not found."


class AlreadyAssignedException(ConflictException):
    """Raised when assigning a user who is already a recipient."""

    code = "ALREADY_ASSIGNED"
    message = "User is already assigned to this notification."


class NotificationValidationException(ValidationException):
    """Raised when request payload or action validations fail."""

    code = "VALIDATION_ERROR"
    message = "Notification validation error."
