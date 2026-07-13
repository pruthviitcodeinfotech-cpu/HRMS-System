"""Authentication module — domain-specific exceptions.

All exceptions here inherit from the shared :class:`app.core.exceptions.base.AppException`
hierarchy so the global handler renders them into the standard error envelope with
the correct HTTP status code and machine-readable code.

Phase 3 additions
─────────────────
:class:`OrgMembershipNotFoundException` — raised when a user attempts to switch
    to an organization they are not a member of (or whose membership is inactive).
:class:`OrgInactiveException` — raised when the target organization itself is
    inactive or soft-deleted.
:class:`OrgSwitchNotAllowedException` — raised for any other condition that
    prevents an org switch (e.g. user's own account is inactive in the context
    of a switch request).
"""

from __future__ import annotations

from app.core.exceptions.base import AuthorizationException, NotFoundException


class OrgMembershipNotFoundException(NotFoundException):
    """The user has no active membership in the requested organization."""

    code = "ORG_MEMBERSHIP_NOT_FOUND"
    status_code = 404
    message = "You do not have an active membership in the requested organization."


class OrgInactiveException(NotFoundException):
    """The target organization is inactive or has been deleted."""

    code = "ORG_INACTIVE"
    status_code = 404
    message = "The requested organization is inactive or does not exist."


class OrgSwitchNotAllowedException(AuthorizationException):
    """Org switch cannot proceed due to the user's account state."""

    code = "ORG_SWITCH_NOT_ALLOWED"
    status_code = 403
    message = "Organization switching is not allowed for this account."


__all__ = [
    "OrgMembershipNotFoundException",
    "OrgInactiveException",
    "OrgSwitchNotAllowedException",
]
