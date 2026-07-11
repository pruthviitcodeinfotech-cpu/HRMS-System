"""Authentication module — service layer (business rules & orchestration).

Implements the behaviour of the Authentication API Contract: login, refresh,
logout, current-user (``/me``), and session administration. All persistence goes
through the module repositories; all cryptography goes through the shared security
utilities. The service owns the transaction boundary (via
:class:`app.shared.base.service.BaseService`) and never issues SQL directly.

Scope note — the approved Authentication API Contract intentionally does **not**
include some flows shown as generic examples:

    * **Change Password** — deferred to the User Management & RBAC module.
    * **Forgot / Reset Password / email verification** — no supporting schema
      (reset-token/OTP tables do not exist); listed as contract Open Questions.
    * **Token Validation** — an *internal* mechanism (the ``get_current_user``
      dependency), exposed here as :meth:`validate_access_token` for reuse, not as
      a public endpoint.

These are therefore not implemented here (doing so would require schema this build
does not have, or would cross the contract's module boundary).
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config.settings import settings
from app.core.dependencies.rate_limit import (
    hash_identifier,
    safe_counter_incr,
    safe_delete,
    safe_flag_set,
    safe_flag_ttl,
)
from app.core.exceptions.base import (
    AuthenticationException,
    AuthorizationException,
    NotFoundException,
    RateLimitException,
)
from app.core.security.jwt import (
    ACCESS_TOKEN_TYPE,
    TokenError,
    create_access_token,
    verify_token,
)
from app.core.security.password import verify_password
from app.modules.audit.constants import ActionType
from app.modules.audit.service import AuditService
from app.modules.auth.repository import AuthUserRepository, UserSessionRepository
from app.modules.auth.schemas import (
    AccessTokenResponse,
    AuthUserSchema,
    CurrentUserSchema,
    DataScopeSchema,
    FeaturePermissionSchema,
    LoginResponse,
    RevokeAllSessionsResponse,
    SessionListResponse,
    SessionSchema,
    TokenClaims,
)
from app.shared.base.service import BaseService
from app.shared.utils.datetime import utcnow
from app.shared.utils.ids import random_token

_INVALID_CREDENTIALS = "Invalid email or password."

#: ``activity_logs.performed_by_name`` is NOT NULL, but a throttled / locked-out
#: caller has no authenticated principal — record the attempt under this label.
_ANONYMOUS = "Unauthenticated"


def _failure_key(org_id: int, email: str) -> str:
    """Redis key holding the consecutive-failed-login count for one account."""
    return f"auth:login:failures:{org_id}:{hash_identifier(email)}"


def _lockout_key(org_id: int, email: str) -> str:
    """Redis key holding the active lockout flag for one account."""
    return f"auth:login:lockout:{org_id}:{hash_identifier(email)}"


def _account_locked_error(retry_after: int) -> RateLimitException:
    """Build the ``429 RATE_LIMITED`` raised while an account is locked out."""
    exc = RateLimitException(
        "This account is temporarily locked after repeated failed login attempts. "
        f"Please try again in {retry_after} second(s)."
    )
    exc.headers = {"Retry-After": str(retry_after)}  # type: ignore[attr-defined]
    return exc


class AuthService(BaseService):
    """Authentication business logic (login, refresh, logout, sessions, /me)."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)
        self.users = AuthUserRepository(session)
        self.sessions = UserSessionRepository(session)
        self.audit = AuditService(session)

    # =====================================================================
    # Audit helper
    # =====================================================================
    async def _audit(
        self,
        *,
        user: Any,
        action_type: ActionType,
        title: str,
        description: str,
        sub_module: str | None = None,
    ) -> None:
        """Write one ``module="auth"`` audit row inside the active transaction.

        The security/access report (``reports.repository`` security-events query)
        selects on ``module="auth"``, so these rows surface there. Descriptions never
        contain passwords, tokens, or session tokens.
        """
        await self.audit.record(
            org_id=user.org_id,
            module="auth",
            sub_module=sub_module,
            action_type=action_type,
            title=title,
            description=description,
            performed_by_user_id=user.id,
            performed_by_name=user.name,
        )

    # =====================================================================
    # Login
    # =====================================================================
    async def login(
        self,
        *,
        org_id: int,
        email: str,
        password: str,
        device_info: str | None = None,
        ip_address: str | None = None,
    ) -> LoginResponse:
        """Verify credentials, open a session, and issue an access + refresh token.

        ``org_id`` is the resolved tenant (the router supplies it from tenant
        context). Unknown user, wrong password, inactive, or soft-deleted accounts
        all fail with the same non-disclosing ``AUTH_INVALID_CREDENTIALS`` error.

        Brute-force protection (distinct from, and in addition to, the per-IP request
        throttle on the route): after ``LOGIN_MAX_FAILED_ATTEMPTS`` consecutive failed
        attempts within ``LOGIN_FAILURE_WINDOW_SECONDS`` the account is locked for
        ``LOGIN_LOCKOUT_SECONDS``. While locked, **even a correct password is
        rejected** (``429 RATE_LIMITED``). A successful login clears the counter.
        The lockout state lives in Redis because the approved ``users`` schema has no
        ``failed_login_attempts`` / ``locked_until`` columns (contract §7, §9 Q7) —
        no schema change is introduced here.
        """
        locked_for = await safe_flag_ttl(_lockout_key(org_id, email))
        if locked_for > 0:
            raise _account_locked_error(locked_for)

        user = await self.users.get_by_email(org_id, email)
        if (
            user is None
            or not user.password_hash
            or not verify_password(password, user.password_hash)
            or not user.is_active
        ):
            await self._register_failed_login(org_id=org_id, email=email, user=user)
            raise AuthenticationException(_INVALID_CREDENTIALS, code="AUTH_INVALID_CREDENTIALS")

        # Successful authentication — the consecutive-failure streak is broken.
        await safe_delete(_failure_key(org_id, email), _lockout_key(org_id, email))

        now = utcnow()
        refresh_token = random_token()
        expires_at = now + timedelta(seconds=settings.refresh_token_ttl)

        async with self.transaction():
            session_row = await self.sessions.create_session(
                user_id=user.id,
                session_token=refresh_token,
                expires_at=expires_at,
                device_info=device_info,
                ip_address=ip_address,
            )
            await self.users.update_last_login(user, now)
            await self._audit(
                user=user,
                action_type=ActionType.INSERT,
                sub_module="session",
                title="User logged in",
                description=f"User '{user.name}' logged in (session #{session_row.id})",
            )

        merged, branch_ids, department_ids = await self._resolve_authz(user.id)
        access_token = self._issue_access_token(
            user=user,
            session_id=session_row.id,
            merged=merged,
            branch_ids=branch_ids,
            department_ids=department_ids,
        )
        return LoginResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=settings.access_token_ttl,
            user=AuthUserSchema.model_validate(user),
        )

    # =====================================================================
    # Brute-force protection (account lockout + security-event auditing)
    # =====================================================================
    async def _register_failed_login(
        self, *, org_id: int, email: str, user: Any | None
    ) -> None:
        """Count one failed attempt for ``email``; lock the account at the threshold.

        Unknown emails are counted too — otherwise the lockout would tell an attacker
        which addresses exist. Every Redis call here fails open (see
        :mod:`app.core.dependencies.rate_limit`): if the backend is down the counter
        simply does not advance and the caller still gets ``AUTH_INVALID_CREDENTIALS``.
        """
        count, _ttl = await safe_counter_incr(
            _failure_key(org_id, email),
            window_seconds=settings.login_failure_window_seconds,
        )
        if count < settings.login_max_failed_attempts:
            return

        await safe_flag_set(
            _lockout_key(org_id, email), ttl_seconds=settings.login_lockout_seconds
        )
        await safe_delete(_failure_key(org_id, email))
        await self._audit_lockout(org_id=org_id, email=email, user=user, attempts=count)

    async def _audit_lockout(
        self, *, org_id: int, email: str, user: Any | None, attempts: int
    ) -> None:
        """Write the ``module="auth"`` audit row for an account lockout."""
        description = (
            f"Account '{email}' locked for {settings.login_lockout_seconds}s after "
            f"{attempts} consecutive failed login attempts"
        )
        async with self.transaction():
            if user is not None:
                await self._audit(
                    user=user,
                    action_type=ActionType.UPDATE,
                    sub_module="lockout",
                    title="Account locked",
                    description=description,
                )
            else:
                # No such user — still record the attempt against the tenant so the
                # security report sees credential-stuffing on unknown addresses.
                await self.audit.record(
                    org_id=org_id,
                    module="auth",
                    sub_module="lockout",
                    action_type=ActionType.UPDATE,
                    title="Account locked",
                    description=f"{description} (no such user)",
                    performed_by_user_id=None,
                    performed_by_name=_ANONYMOUS,
                )

    async def record_rate_limit_event(
        self,
        *,
        org_id: int,
        scope: str,
        ip_address: str | None = None,
        identifier: str | None = None,
    ) -> None:
        """Audit a rate-limit trip on an auth endpoint (``429 RATE_LIMITED``).

        Called from the route dependency, which has no authenticated principal — the
        row is attributed to the tenant and the offending IP. Never contains the
        submitted password or any token.
        """
        target = f" for '{identifier}'" if identifier else ""
        async with self.transaction():
            await self.audit.record(
                org_id=org_id,
                module="auth",
                sub_module="rate_limit",
                action_type=ActionType.INSERT,
                title="Rate limit exceeded",
                description=(
                    f"Rate limit exceeded on '{scope}'{target} "
                    f"from IP {ip_address or 'unknown'}"
                ),
                performed_by_user_id=None,
                performed_by_name=_ANONYMOUS,
            )

    # =====================================================================
    # Refresh
    # =====================================================================
    async def refresh_token(self, *, refresh_token: str) -> AccessTokenResponse:
        """Exchange a valid refresh token for a fresh access token.

        Refresh-token rotation is a contract open question; the current token is
        retained (``refresh_token`` is not re-issued).
        """
        now = utcnow()
        session_row = await self.sessions.get_valid_by_token(refresh_token, now=now)
        if session_row is None:
            raise AuthenticationException(
                "Invalid or expired refresh token.", code="AUTH_REFRESH_INVALID"
            )

        user = await self.users.get_active_by_id(session_row.user_id)
        if user is None:
            raise AuthenticationException(
                "Invalid or expired refresh token.", code="AUTH_REFRESH_INVALID"
            )
        if not user.is_active:
            raise AuthorizationException("This account is inactive.", code="AUTH_USER_INACTIVE")

        merged, branch_ids, department_ids = await self._resolve_authz(user.id)
        access_token = self._issue_access_token(
            user=user,
            session_id=session_row.id,
            merged=merged,
            branch_ids=branch_ids,
            department_ids=department_ids,
        )
        return AccessTokenResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=settings.access_token_ttl,
            refresh_token=None,
        )

    # =====================================================================
    # Logout
    # =====================================================================
    async def logout(
        self,
        *,
        user_id: int,
        session_id: int | None,
        refresh_token: str | None = None,
    ) -> None:
        """Revoke a session.

        When ``refresh_token`` is provided, revoke that specific session (it must
        belong to the caller); otherwise revoke the session referenced by the
        caller's access token (``session_id``).
        """
        now = utcnow()
        if refresh_token is not None:
            session_row = await self.sessions.get_by_token(refresh_token)
            if session_row is None or session_row.user_id != user_id:
                raise NotFoundException(
                    "Session not found.", code="AUTH_SESSION_NOT_FOUND"
                )
        elif session_id is not None:
            session_row = await self.sessions.get_for_user(session_id, user_id)
            if session_row is None:
                raise NotFoundException(
                    "Session not found.", code="AUTH_SESSION_NOT_FOUND"
                )
        else:
            # No session reference on the token and no token supplied — nothing to do.
            return

        user = await self.users.get_active_by_id(user_id)
        async with self.transaction():
            await self.sessions.revoke(session_row, when=now)
            if user is not None:
                await self._audit(
                    user=user,
                    action_type=ActionType.DELETE,
                    sub_module="session",
                    title="User logged out",
                    description=f"User '{user.name}' logged out (session #{session_row.id})",
                )

    # =====================================================================
    # Current user (/me)
    # =====================================================================
    async def get_current_user(self, *, user_id: int) -> CurrentUserSchema:
        """Return the authenticated user's profile plus effective authorization."""
        user = await self.users.get_active_by_id(user_id)
        if user is None:
            raise NotFoundException("User not found.", code="USER_NOT_FOUND")
        if not user.is_active:
            raise AuthorizationException("This account is inactive.", code="AUTH_USER_INACTIVE")

        merged, branch_ids, department_ids = await self._resolve_authz(user.id)
        permissions = [
            FeaturePermissionSchema(feature_key=key, **flags) for key, flags in merged.items()
        ]
        return CurrentUserSchema(
            **AuthUserSchema.model_validate(user).model_dump(),
            permissions=permissions,
            data_scope=DataScopeSchema(branch_ids=branch_ids, department_ids=department_ids),
        )

    # =====================================================================
    # Session administration
    # =====================================================================
    async def list_sessions(
        self,
        *,
        user_id: int,
        current_session_id: int | None,
        active_only: bool = True,
        page: int = 1,
        page_size: int = 25,
    ) -> SessionListResponse:
        """Return a paginated list of the caller's own sessions."""
        rows = await self.sessions.list_for_user(
            user_id, active_only=active_only, page=page, page_size=page_size
        )
        total = await self.sessions.count_for_user(user_id, active_only=active_only)
        items = [
            SessionSchema.model_validate(row).model_copy(
                update={"is_current": row.id == current_session_id}
            )
            for row in rows
        ]
        return SessionListResponse.build(
            items=items, page=page, page_size=page_size, total_records=total
        )

    async def revoke_session(self, *, user_id: int, session_id: int) -> None:
        """Revoke one of the caller's sessions by id (idempotent)."""
        session_row = await self.sessions.get_for_user(session_id, user_id)
        if session_row is None:
            raise NotFoundException("Session not found.", code="AUTH_SESSION_NOT_FOUND")
        user = await self.users.get_active_by_id(user_id)
        async with self.transaction():
            await self.sessions.revoke(session_row, when=utcnow())
            if user is not None:
                await self._audit(
                    user=user,
                    action_type=ActionType.DELETE,
                    sub_module="session",
                    title="Session revoked",
                    description=f"User '{user.name}' revoked session #{session_id}",
                )

    async def revoke_all_other_sessions(
        self, *, user_id: int, current_session_id: int | None
    ) -> RevokeAllSessionsResponse:
        """Revoke all of the caller's sessions except the current one."""
        user = await self.users.get_active_by_id(user_id)
        async with self.transaction():
            revoked = await self.sessions.revoke_all_for_user(
                user_id, when=utcnow(), exclude_session_id=current_session_id
            )
            if user is not None:
                await self._audit(
                    user=user,
                    action_type=ActionType.DELETE,
                    sub_module="session",
                    title="All other sessions revoked",
                    description=(
                        f"User '{user.name}' revoked {revoked} other session(s)"
                    ),
                )
        return RevokeAllSessionsResponse(revoked_count=revoked)

    # =====================================================================
    # Token validation (internal mechanism)
    # =====================================================================
    def validate_access_token(self, token: str) -> TokenClaims:
        """Decode and verify an access token, returning its claims.

        Internal helper mirroring the ``get_current_user`` dependency's check; not
        a public endpoint. Raises :class:`AuthenticationException` on any failure.
        """
        try:
            claims = verify_token(token, ACCESS_TOKEN_TYPE)
        except TokenError as exc:
            raise AuthenticationException(
                "Invalid or expired access token.", code="AUTH_TOKEN_INVALID"
            ) from exc
        return TokenClaims.model_validate(claims)

    # =====================================================================
    # Internal helpers
    # =====================================================================
    async def _resolve_authz(
        self, user_id: int
    ) -> tuple[dict[str, dict[str, bool]], list[int], list[int]]:
        """Resolve effective permissions (template ⊕ custom) and data scope."""
        template_rows = await self.users.get_template_permissions(user_id)
        custom_rows = await self.users.get_custom_permissions(user_id)
        merged = self._merge_permissions(template_rows, custom_rows)
        branch_ids = await self.users.get_branch_ids(user_id)
        department_ids = await self.users.get_department_ids(user_id)
        return merged, branch_ids, department_ids

    @staticmethod
    def _merge_permissions(
        template_rows: list[Any], custom_rows: list[Any]
    ) -> dict[str, dict[str, bool]]:
        """Merge template permissions with per-user overrides (custom wins)."""
        merged: dict[str, dict[str, bool]] = {}
        for row in [*template_rows, *custom_rows]:
            merged[row.feature_key] = {
                "can_create": bool(row.can_create),
                "can_read": bool(row.can_read),
                "can_edit": bool(row.can_edit),
                "can_delete": bool(row.can_delete),
            }
        return merged

    @staticmethod
    def _issue_access_token(
        *,
        user: Any,
        session_id: int,
        merged: dict[str, dict[str, bool]],
        branch_ids: list[int],
        department_ids: list[int],
    ) -> str:
        """Build a self-contained access token carrying identity + authorization."""
        permissions = [{"feature_key": key, **flags} for key, flags in merged.items()]
        extra_claims: dict[str, Any] = {
            "org_id": user.org_id,
            "is_super_admin": user.is_super_admin,
            "is_active": user.is_active,
            "sid": str(session_id),
            "roles": ["super_admin"] if user.is_super_admin else [],
            "permissions": permissions,
            "branch_ids": branch_ids,
            "department_ids": department_ids,
        }
        return create_access_token(user.id, extra_claims=extra_claims)
