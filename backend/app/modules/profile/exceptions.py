"""User Profile — module-specific exceptions.

Each type specialises a shared :mod:`app.core.exceptions.base` exception so the
registered handlers map it to the right HTTP status and a stable machine-readable
``code`` without any router-level ``HTTPException``.
"""

from __future__ import annotations

from app.core.exceptions.base import AuthenticationException, ConflictException, NotFoundException


class ProfileNotFoundException(NotFoundException):
    """The caller's user (or its organization) could not be resolved."""

    code = "PROFILE_NOT_FOUND"
    message = "Your profile could not be found."


class MobileNumberExistsException(ConflictException):
    """The requested mobile number is already registered to another user in this org."""

    code = "MOBILE_NUMBER_EXISTS"
    message = "This mobile number is already in use by another account."


class IncorrectCurrentPasswordException(AuthenticationException):
    """The supplied ``current_password`` does not match the stored hash."""

    code = "CURRENT_PASSWORD_INCORRECT"
    message = "The current password you entered is incorrect."


class NoEmployeeLinkedException(ConflictException):
    """The user account has no linked employee record to store a profile photo on."""

    code = "NO_EMPLOYEE_LINKED"
    message = "Your account is not linked to an employee record; a profile photo cannot be stored."


__all__ = [
    "ProfileNotFoundException",
    "MobileNumberExistsException",
    "IncorrectCurrentPasswordException",
    "NoEmployeeLinkedException",
]
