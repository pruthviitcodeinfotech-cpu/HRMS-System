"""Settings module-specific exception types.

Maps to the error codes defined in the approved Settings Management API Contract.
"""

from __future__ import annotations

from app.core.exceptions.base import NotFoundException, ValidationException


class SettingsNotFoundException(NotFoundException):
    """Raised when an org_settings or salary-slip settings row is not found."""

    code = "SETTINGS_NOT_FOUND"
    message = "Settings not found."


class UnknownFeatureException(NotFoundException):
    """Raised when a feature_key does not map to a known fixed toggle."""

    code = "UNKNOWN_FEATURE"
    message = "The specified feature key is not recognized."


class SettingsValidationException(ValidationException):
    """Raised when request payload or business-rule validation fails."""

    code = "VALIDATION_ERROR"
    message = "Settings validation error."
