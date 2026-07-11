"""Reusable authentication / authorization FastAPI dependencies.

These are the shared building blocks every protected endpoint composes:

    * :func:`get_current_user` — decode + verify the Bearer access token into a
      :class:`CurrentUser` principal (from token claims).
    * :func:`get_current_active_user` — additionally require an active principal.
    * :func:`require_permission` — RBAC feature-permission guard factory.
    * :func:`require_role` — role/super-admin guard factory.

The principal is built from access-token claims, but the claims alone are **not**
trusted to decide whether the caller may still act: :func:`assert_session_live`
re-validates the token's session (and the owning user) against the database on
every request, so logout, force-logout, deactivation and deletion take effect
immediately instead of at token expiry.
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants.enums import PermissionAction
from app.core.dependencies.db import get_db
from app.core.exceptions.base import AuthenticationException, AuthorizationException
from app.core.middleware.request_context import (
    set_current_org_id,
    set_current_user_id,
)
from app.core.security.jwt import ACCESS_TOKEN_TYPE, TokenError, verify_token
from app.core.security.permissions import EffectivePermissions, build_effective_permissions
from app.shared.utils.datetime import utcnow

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


async def assert_session_live(
    user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Re-validate the token's session and its owner against the database.

    An access token is a bearer credential that stays cryptographically valid until it
    expires. Trusting its claims alone would mean logout, admin force-logout, user
    deactivation and user deletion do not take effect until expiry — a terminated
    employee would keep API access for the remainder of the token's lifetime.

    This runs on every authenticated request and **fails closed**: the session named by
    the ``sid`` claim must still exist, be active, be unrevoked and unexpired, and the
    owning user must still be active and not soft-deleted. It is a single primary-key
    lookup joined to ``users``.

    Tokens issued without a ``sid`` are rejected: an unrevocable token is not acceptable.
    """
    # Imported here: app.core must not import a business module at module scope.
    from app.modules.rbac.models.user import User, UserSession

    if user.session_id is None:
        raise AuthenticationException("Access token is not bound to a session.")
    try:
        session_id = int(user.session_id)
    except (TypeError, ValueError) as exc:
        raise AuthenticationException("Access token carries a malformed session id.") from exc

    stmt = (
        select(UserSession.expires_at, User.is_active, User.deleted_at)
        .join(User, User.id == UserSession.user_id)
        .where(
            UserSession.id == session_id,
            UserSession.user_id == user.user_id,
            UserSession.is_active.is_(True),
            UserSession.revoked_at.is_(None),
        )
    )
    row = (await db.execute(stmt.limit(1))).first()
    if row is None:
        raise AuthenticationException("This session has been revoked or has expired.")

    expires_at, user_is_active, user_deleted_at = row
    if expires_at is not None and expires_at <= utcnow():
        raise AuthenticationException("This session has been revoked or has expired.")
    if not user_is_active or user_deleted_at is not None:
        raise AuthorizationException("This account is inactive.")


async def get_current_active_user(
    user: Annotated[CurrentUser, Depends(get_current_user)],
    _session_live: Annotated[None, Depends(assert_session_live)],
) -> CurrentUser:
    """Require an active principal whose session is still live in the database."""
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
