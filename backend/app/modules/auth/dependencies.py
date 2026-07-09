"""Authentication module — module-scoped FastAPI dependencies.

Only genuinely auth-specific wiring lives here. Everything generic is **reused**
from the shared foundation and deliberately not duplicated:

    * DB session ............. ``app.core.dependencies.db.get_db``
    * Current principal ...... ``app.core.dependencies.auth.get_current_user`` /
                               ``get_current_active_user``
    * Permission / role guards ``require_permission`` / ``require_role``
    * Pagination ............. ``app.core.dependencies.pagination``
    * JWT / password utils ... ``app.core.security.*``

This module adds the pieces that are specific to the auth endpoints: constructing
the :class:`~app.modules.auth.service.AuthService`, resolving the tenant for the
unauthenticated login route, and extracting the current session id from the
access-token principal.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Header, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies.auth import CurrentUser, get_current_active_user
from app.core.dependencies.db import get_db
from app.core.exceptions.base import AppException
from app.modules.auth.service import AuthService


async def get_auth_service(db: Annotated[AsyncSession, Depends(get_db)]) -> AuthService:
    """Provide an :class:`AuthService` bound to the request-scoped DB session."""
    return AuthService(db)


async def resolve_org_id(
    request: Request,
    x_org_id: Annotated[int | None, Header(alias="X-Org-ID")] = None,
) -> int:
    """Resolve the tenant (``org_id``) for unauthenticated requests (e.g. login).

    Prefers the value bound by the tenant middleware, falling back to the
    ``X-Org-ID`` header. Raises ``TENANT_UNRESOLVED`` (400) when neither is
    present. (The precise tenant-resolution strategy is a contract open question.)
    """
    org_id = getattr(request.state, "org_id", None) or x_org_id
    if org_id is None:
        exc = AppException(
            "Organization context could not be resolved.", code="TENANT_UNRESOLVED"
        )
        exc.status_code = status.HTTP_400_BAD_REQUEST
        raise exc
    return int(org_id)


def get_current_session_id(
    current_user: Annotated[CurrentUser, Depends(get_current_active_user)],
) -> int | None:
    """Extract the numeric session id from the access-token ``sid`` claim."""
    return int(current_user.session_id) if current_user.session_id is not None else None


# --- Convenience annotated dependency aliases (for thin controllers) ---------
AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
CurrentUserDep = Annotated[CurrentUser, Depends(get_current_active_user)]
OrgIdDep = Annotated[int, Depends(resolve_org_id)]
CurrentSessionIdDep = Annotated[int | None, Depends(get_current_session_id)]

__all__ = [
    "get_auth_service",
    "resolve_org_id",
    "get_current_session_id",
    "AuthServiceDep",
    "CurrentUserDep",
    "OrgIdDep",
    "CurrentSessionIdDep",
]
