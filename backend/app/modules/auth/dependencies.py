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
unauthenticated login route, extracting the current session id from the
access-token principal, and the brute-force throttles applied to the two
unauthenticated routes (``login`` / ``refresh``, contract §7).
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Header, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config.settings import settings
from app.core.dependencies.auth import CurrentUser, get_current_active_user
from app.core.dependencies.db import get_db
from app.core.dependencies.rate_limit import client_ip, rate_limit, read_body_field
from app.core.exceptions.base import AppException, RateLimitException
from app.core.logging.config import get_logger
from app.modules.auth.service import AuthService
from app.modules.auth.org_membership_service import OrganizationMembershipService
from app.modules.auth.org_switch_service import OrganizationSwitchService

_logger = get_logger("auth.rate_limit")


async def get_auth_service(db: Annotated[AsyncSession, Depends(get_db)]) -> AuthService:
    """Provide an :class:`AuthService` bound to the request-scoped DB session."""
    return AuthService(db)


async def get_org_membership_service(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> OrganizationMembershipService:
    """Provide an :class:`OrganizationMembershipService` bound to the request-scoped DB session."""
    return OrganizationMembershipService(db)


async def get_org_switch_service(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> OrganizationSwitchService:
    """Provide an :class:`OrganizationSwitchService` bound to the request-scoped DB session."""
    return OrganizationSwitchService(db)


async def resolve_org_id(
    request: Request,
    x_org_id: Annotated[int | None, Header(alias="X-Org-ID")] = None,
) -> int:
    """Resolve the tenant (``org_id``) for unauthenticated requests (e.g. login).

    Prefers the value bound by the tenant middleware, falling back to the
    ``X-Org-ID`` header, and defaulting to 1 (default organization).
    """
    org_id = getattr(request.state, "org_id", None) or x_org_id or 1
    return int(org_id)


# ---------------------------------------------------------------------------
# Rate limiting (contract §7: `login` and `refresh` must be rate-limited)
# ---------------------------------------------------------------------------
# Login is throttled per client IP *and* per submitted email (two independent
# counters). Refresh is throttled per IP only: its sole body field is the refresh
# token, which is a secret — it is never used as a rate-limit key, hashed or not.
_login_throttle = rate_limit(
    "login",
    settings.login_rate_limit_attempts,
    settings.login_rate_limit_window_seconds,
    identifier_field="email",
)
_refresh_throttle = rate_limit(
    "refresh",
    settings.refresh_rate_limit_attempts,
    settings.refresh_rate_limit_window_seconds,
)


def _best_effort_org_id(request: Request) -> int | None:
    """Resolve the tenant without raising (the throttle runs before validation)."""
    raw = getattr(request.state, "org_id", None) or request.headers.get("X-Org-ID")
    try:
        return int(raw) if raw is not None else None
    except (TypeError, ValueError):
        return None


async def _audit_rate_limit_trip(
    service: AuthService, request: Request, *, scope: str, identifier: str | None
) -> None:
    """Best-effort audit row for a rate-limit trip; never masks the 429."""
    org_id = _best_effort_org_id(request)
    if org_id is None:
        # `activity_logs.org_id` is NOT NULL and FK-checked; with no tenant (a
        # refresh call carries none) the event can only be logged, not audited.
        _logger.warning("rate_limit_trip_unaudited", scope=scope, reason="tenant_unresolved")
        return
    try:
        await service.record_rate_limit_event(
            org_id=org_id,
            scope=scope,
            ip_address=client_ip(request),
            identifier=identifier,
        )
    except Exception as exc:  # noqa: BLE001 - auditing must not turn a 429 into a 500
        _logger.error("rate_limit_audit_failed", scope=scope, error=str(exc))


async def enforce_login_rate_limit(
    request: Request,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> None:
    """Throttle ``POST /auth/login`` and audit the breach (``429 RATE_LIMITED``)."""
    try:
        await _login_throttle(request)
    except RateLimitException:
        identifier = await read_body_field(request, "email")
        await _audit_rate_limit_trip(service, request, scope="login", identifier=identifier)
        raise


async def enforce_refresh_rate_limit(
    request: Request,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> None:
    """Throttle ``POST /auth/refresh`` and audit the breach (``429 RATE_LIMITED``)."""
    try:
        await _refresh_throttle(request)
    except RateLimitException:
        # The refresh token is never recorded — only the offending IP.
        await _audit_rate_limit_trip(service, request, scope="refresh", identifier=None)
        raise


def get_current_session_id(
    current_user: Annotated[CurrentUser, Depends(get_current_active_user)],
) -> int | None:
    """Extract the numeric session id from the access-token ``sid`` claim."""
    return int(current_user.session_id) if current_user.session_id is not None else None


# --- Convenience annotated dependency aliases (for thin controllers) ---------
AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
OrgMembershipServiceDep = Annotated[OrganizationMembershipService, Depends(get_org_membership_service)]
OrgSwitchServiceDep = Annotated[OrganizationSwitchService, Depends(get_org_switch_service)]
CurrentUserDep = Annotated[CurrentUser, Depends(get_current_active_user)]
OrgIdDep = Annotated[int, Depends(resolve_org_id)]
CurrentSessionIdDep = Annotated[int | None, Depends(get_current_session_id)]

__all__ = [
    "get_auth_service",
    "get_org_membership_service",
    "get_org_switch_service",
    "resolve_org_id",
    "get_current_session_id",
    "enforce_login_rate_limit",
    "enforce_refresh_rate_limit",
    "AuthServiceDep",
    "OrgMembershipServiceDep",
    "OrgSwitchServiceDep",
    "CurrentUserDep",
    "OrgIdDep",
    "CurrentSessionIdDep",
]
