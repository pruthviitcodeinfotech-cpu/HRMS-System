"""Unit tests for ``AuthService`` business logic (repositories mocked).

Covers login (success + failure modes), refresh (incl. inactive user), logout,
session revocation, and the ``/me`` authorization assembly. All data access is
stubbed via the ``service`` fixture, so these tests exercise only the service's
rules and orchestration.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.core.exceptions.base import (
    AuthenticationException,
    AuthorizationException,
    NotFoundException,
)
from app.modules.auth.schemas import (
    AccessTokenResponse,
    CurrentUserSchema,
    LoginResponse,
    RevokeAllSessionsResponse,
)
from tests.conftest import TEST_PASSWORD


# --- Login -----------------------------------------------------------------
async def test_login_success(service, fake_user) -> None:
    service.users.get_by_email.return_value = fake_user
    service.sessions.create_session.return_value = SimpleNamespace(id=10)

    result = await service.login(
        org_id=1, email=fake_user.email, password=TEST_PASSWORD, device_info="pytest"
    )

    assert isinstance(result, LoginResponse)
    assert result.access_token and result.refresh_token
    assert result.token_type == "bearer"
    assert result.expires_in >= 1
    assert result.user.email == fake_user.email
    service.sessions.create_session.assert_awaited_once()
    service.users.update_last_login.assert_awaited_once()
    service.audit.record.assert_awaited_once()


async def test_login_wrong_password(service, fake_user) -> None:
    service.users.get_by_email.return_value = fake_user
    with pytest.raises(AuthenticationException) as exc:
        await service.login(org_id=1, email=fake_user.email, password="wrong")
    assert exc.value.code == "AUTH_INVALID_CREDENTIALS"


async def test_login_unknown_user(service) -> None:
    service.users.get_by_email.return_value = None
    with pytest.raises(AuthenticationException) as exc:
        await service.login(org_id=1, email="nobody@example.com", password="x")
    assert exc.value.code == "AUTH_INVALID_CREDENTIALS"


async def test_login_inactive_user(service, fake_user) -> None:
    fake_user.is_active = False
    service.users.get_by_email.return_value = fake_user
    with pytest.raises(AuthenticationException) as exc:
        await service.login(org_id=1, email=fake_user.email, password=TEST_PASSWORD)
    assert exc.value.code == "AUTH_INVALID_CREDENTIALS"


# --- Refresh ---------------------------------------------------------------
async def test_refresh_success(service, fake_user) -> None:
    service.sessions.get_valid_by_token.return_value = SimpleNamespace(id=10, user_id=1)
    service.users.get_active_by_id.return_value = fake_user

    result = await service.refresh_token(refresh_token="valid-token")

    assert isinstance(result, AccessTokenResponse)
    assert result.access_token
    assert result.refresh_token is None  # rotation off by default


async def test_refresh_invalid_token(service) -> None:
    service.sessions.get_valid_by_token.return_value = None
    with pytest.raises(AuthenticationException) as exc:
        await service.refresh_token(refresh_token="bad")
    assert exc.value.code == "AUTH_REFRESH_INVALID"


async def test_refresh_inactive_user(service, fake_user) -> None:
    fake_user.is_active = False
    service.sessions.get_valid_by_token.return_value = SimpleNamespace(id=10, user_id=1)
    service.users.get_active_by_id.return_value = fake_user
    with pytest.raises(AuthorizationException) as exc:
        await service.refresh_token(refresh_token="valid")
    assert exc.value.code == "AUTH_USER_INACTIVE"


# --- Logout / revoke -------------------------------------------------------
async def test_logout_by_refresh_token(service) -> None:
    session_row = SimpleNamespace(id=10, user_id=1)
    service.sessions.get_by_token.return_value = session_row

    await service.logout(user_id=1, session_id=None, refresh_token="tok")

    service.sessions.revoke.assert_awaited_once()


async def test_logout_session_not_found(service) -> None:
    service.sessions.get_by_token.return_value = None
    with pytest.raises(NotFoundException) as exc:
        await service.logout(user_id=1, session_id=None, refresh_token="ghost")
    assert exc.value.code == "AUTH_SESSION_NOT_FOUND"


async def test_logout_foreign_session_rejected(service) -> None:
    service.sessions.get_by_token.return_value = SimpleNamespace(id=10, user_id=999)
    with pytest.raises(NotFoundException):
        await service.logout(user_id=1, session_id=None, refresh_token="tok")


async def test_revoke_all_other_sessions(service) -> None:
    service.sessions.revoke_all_for_user.return_value = 3
    result = await service.revoke_all_other_sessions(user_id=1, current_session_id=10)
    assert isinstance(result, RevokeAllSessionsResponse)
    assert result.revoked_count == 3
    service.sessions.revoke_all_for_user.assert_awaited_once()


# --- Current user (/me) ----------------------------------------------------
async def test_get_current_user(service, fake_user) -> None:
    service.users.get_active_by_id.return_value = fake_user
    result = await service.get_current_user(user_id=1)
    assert isinstance(result, CurrentUserSchema)
    assert result.email == fake_user.email
    assert result.permissions == []
    assert result.data_scope.branch_ids == []


async def test_get_current_user_missing(service) -> None:
    service.users.get_active_by_id.return_value = None
    with pytest.raises(NotFoundException):
        await service.get_current_user(user_id=1)
