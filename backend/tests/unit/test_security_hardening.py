"""Security regression tests for the Phase 3 hardening.

Each test pins a vulnerability that was live in the codebase. They are written to fail
loudly if the control is ever removed, so the fix cannot silently regress.
"""

from __future__ import annotations

from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.dependencies.auth import CurrentUser, assert_session_live
from app.core.exceptions.base import AuthenticationException, AuthorizationException
from app.modules.rbac.schemas import UserUpdateRequest
from app.modules.settings.repository import SettingsCrossModuleRepository
from app.shared.utils.datetime import utcnow


def _db_returning(row: object | None) -> AsyncMock:
    """A session whose `await execute(...)` yields a synchronous Result."""
    result = MagicMock()
    result.first.return_value = row
    db = AsyncMock()
    db.execute = AsyncMock(return_value=result)
    return db


def _principal(session_id: str | None = "10") -> CurrentUser:
    return CurrentUser(user_id=1, org_id=1, is_active=True, session_id=session_id)


# ===========================================================================
# Token revocation — the access token must not outlive its session
# ===========================================================================


async def test_live_session_is_accepted() -> None:
    """A session that is active, unrevoked and unexpired passes."""
    row = (utcnow() + timedelta(minutes=10), True, None)  # expires_at, is_active, deleted_at
    await assert_session_live(_principal(), _db_returning(row))


async def test_revoked_session_rejects_a_cryptographically_valid_token() -> None:
    """After logout / force-logout the session row no longer matches -> 401.

    This is the whole point of the control: the JWT is still perfectly valid and
    unexpired, but the bearer must no longer be able to act.
    """
    with pytest.raises(AuthenticationException):
        await assert_session_live(_principal(), _db_returning(None))


async def test_expired_session_is_rejected() -> None:
    row = (utcnow() - timedelta(seconds=1), True, None)
    with pytest.raises(AuthenticationException):
        await assert_session_live(_principal(), _db_returning(row))


async def test_deactivated_user_cannot_use_a_live_token() -> None:
    """Deactivating a user must lock them out immediately, not at token expiry."""
    row = (utcnow() + timedelta(minutes=10), False, None)
    with pytest.raises(AuthorizationException):
        await assert_session_live(_principal(), _db_returning(row))


async def test_soft_deleted_user_cannot_use_a_live_token() -> None:
    row = (utcnow() + timedelta(minutes=10), True, utcnow())
    with pytest.raises(AuthorizationException):
        await assert_session_live(_principal(), _db_returning(row))


async def test_token_without_a_session_id_is_rejected() -> None:
    """An unrevocable token is not acceptable — fail closed."""
    with pytest.raises(AuthenticationException):
        await assert_session_live(_principal(session_id=None), _db_returning(None))


async def test_token_with_malformed_session_id_is_rejected() -> None:
    with pytest.raises(AuthenticationException):
        await assert_session_live(_principal(session_id="not-an-int"), _db_returning(None))


# ===========================================================================
# Privilege manipulation — super-admin revocation must be gated too
# ===========================================================================


async def test_non_super_admin_cannot_revoke_super_admin(rbac_service) -> None:
    """Gating only the *grant* let any user-editor strip another user's super-admin.

    That is privilege manipulation, and a route to locking an org out of its own admin.
    """
    target = SimpleNamespace(id=2, org_id=1, is_super_admin=True, email="a@b.c",
                             mobile_number="900", mobile_country_code="+91")
    rbac_service.users.get_active_by_id.return_value = target

    with pytest.raises(AuthorizationException):
        await rbac_service.update_user(
            org_id=1,
            actor_is_super_admin=False,
            user_id=2,
            data=UserUpdateRequest(is_super_admin=False),
        )
    rbac_service.users.update.assert_not_awaited()


async def test_non_super_admin_cannot_grant_super_admin(rbac_service) -> None:
    target = SimpleNamespace(id=2, org_id=1, is_super_admin=False, email="a@b.c",
                             mobile_number="900", mobile_country_code="+91")
    rbac_service.users.get_active_by_id.return_value = target

    with pytest.raises(AuthorizationException):
        await rbac_service.update_user(
            org_id=1,
            actor_is_super_admin=False,
            user_id=2,
            data=UserUpdateRequest(is_super_admin=True),
        )
    rbac_service.users.update.assert_not_awaited()


# ===========================================================================
# SQL injection — the table name is interpolated, so it must be allowlisted
# ===========================================================================


async def test_cross_module_table_name_is_allowlisted() -> None:
    repo = SettingsCrossModuleRepository(AsyncMock())
    with pytest.raises(ValueError):
        await repo.cross_module_exists("users; DROP TABLE users --", org_id=1)
    with pytest.raises(ValueError):
        await repo.cross_module_exists("users", org_id=1)


async def test_cross_module_allows_the_three_real_tables() -> None:
    repo = SettingsCrossModuleRepository(_db_returning((1,)))
    for table in ("org_attendance_settings", "payroll_settings", "leave_settings"):
        assert await repo.cross_module_exists(table, org_id=1) is True
