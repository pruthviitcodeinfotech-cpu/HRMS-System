"""Reusable authentication / authorization FastAPI dependencies.

These are the shared building blocks every protected endpoint composes:

    * :func:`get_current_user` — decode + verify the Bearer access token into a
      :class:`CurrentUser` principal (from token claims).
    * :func:`get_current_active_user` — additionally require an active principal.
    * :func:`require_permission` — RBAC feature-permission guard factory.
    * :func:`require_role` — role/super-admin guard factory.

The principal is built from access-token claims so the foundation stays decoupled
from the ``users`` ORM model. The auth module issues tokens carrying ``org_id``,
``is_super_admin``, ``is_active``, ``roles`` and the resolved ``permissions`` so
these guards work without a per-request DB read. Modules may layer DB-backed
revocation checks on top.
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

from app.core.constants.enums import PermissionAction
from app.core.exceptions.base import AuthenticationException, AuthorizationException
from app.core.middleware.request_context import (
    set_current_org_id,
    set_current_user_id,
)
from app.core.security.jwt import ACCESS_TOKEN_TYPE, TokenError, verify_token
from app.core.security.permissions import EffectivePermissions, build_effective_permissions

_bearer_scheme = HTTPBearer(auto_error=False)


class CurrentUser(BaseModel):
    """The authenticated principal resolved from an access token."""

    user_id: int
    org_id: int | None = None
    is_super_admin: bool = False
    is_active: bool = True
    session_id: str | None = None
    roles: frozenset[str] = frozenset()
    permissions: EffectivePermissions = Field(default_factory=EffectivePermissions)

    model_config = {"arbitrary_types_allowed": True}

    def require(self, feature_key: str, action: PermissionAction) -> None:
        """Raise :class:`AuthorizationException` unless the action is permitted."""
        if not self.permissions.has_permission(feature_key, action):
            raise AuthorizationException(
                f"Missing permission '{feature_key}:{action.value}'."
            )


def _principal_from_claims(claims: dict[str, Any]) -> CurrentUser:
    try:
        user_id = int(claims["sub"])
    except (KeyError, ValueError, TypeError) as exc:
        raise AuthenticationException("Malformed access token.") from exc

    is_super_admin = bool(claims.get("is_super_admin", False))
    permissions = build_effective_permissions(
        is_super_admin=is_super_admin,
        feature_rows=claims.get("permissions"),
        branch_ids=claims.get("branch_ids"),
        department_ids=claims.get("department_ids"),
    )
    org_id = claims.get("org_id")
    return CurrentUser(
        user_id=user_id,
        org_id=int(org_id) if org_id is not None else None,
        is_super_admin=is_super_admin,
        is_active=bool(claims.get("is_active", True)),
        session_id=claims.get("sid"),
        roles=frozenset(claims.get("roles", [])),
        permissions=permissions,
    )


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)],
) -> CurrentUser:
    """Resolve the current principal from the ``Authorization: Bearer`` token."""
    if credentials is None or not credentials.credentials:
        raise AuthenticationException("Authentication credentials were not provided.")
    try:
        claims = verify_token(credentials.credentials, ACCESS_TOKEN_TYPE)
    except TokenError as exc:
        raise AuthenticationException("Invalid or expired access token.") from exc

    user = _principal_from_claims(claims)
    set_current_user_id(user.user_id)
    if user.org_id is not None:
        set_current_org_id(user.org_id)
    return user


async def get_current_active_user(
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> CurrentUser:
    """Require the principal to be active (rejects deactivated accounts)."""
    if not user.is_active:
        raise AuthorizationException("This account is inactive.")
    return user


def require_permission(feature_key: str, action: PermissionAction):
    """Return a dependency that enforces ``feature_key:action`` on the caller.

    Usage::

        @router.get(..., dependencies=[Depends(require_permission("employee", PermissionAction.READ))])
    """

    async def _guard(
        user: Annotated[CurrentUser, Depends(get_current_active_user)],
    ) -> CurrentUser:
        user.require(feature_key, action)
        return user

    return _guard


def require_role(*roles: str):
    """Return a dependency that requires the caller to hold one of ``roles``.

    Super admins always pass. Role names are matched against the token's ``roles``
    claim (in this project a user's single rights-template name, plus any
    system roles).
    """
    required = frozenset(roles)

    async def _guard(
        user: Annotated[CurrentUser, Depends(get_current_active_user)],
    ) -> CurrentUser:
        if user.is_super_admin or (user.roles & required):
            return user
        raise AuthorizationException("You do not have the required role.")

    return _guard
