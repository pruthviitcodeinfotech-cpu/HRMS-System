"""Integration tests for the Authentication router.

Exercises the real FastAPI app + the real auth/permission dependencies + the
standard response envelope, with only :class:`AuthService` mocked (so no database
is required). Covers login, refresh, logout, session revocation, validation
errors, unauthorized access, and token expiration — and asserts that
password-change/reset endpoints are *not* part of the auth module (they are
deferred/unsupported per the approved contract).
"""

from __future__ import annotations

from unittest.mock import AsyncMock

from httpx import ASGITransport, AsyncClient

from app.core.config.settings import settings
from app.modules.auth.schemas import (
    AccessTokenResponse,
    AuthUserSchema,
    CurrentUserSchema,
    DataScopeSchema,
    LoginResponse,
    OrganizationSummarySchema,
    RevokeAllSessionsResponse,
)
from tests.conftest import API_PREFIX

ORG_HEADER = {"X-Org-ID": "1"}


def _auth_user() -> AuthUserSchema:
    return AuthUserSchema(
        id=1,
        org_id=1,
        name="Test User",
        email="user@example.com",
        mobile_country_code="+91",
        mobile_number="9876543210",
        is_super_admin=False,
        is_active=True,
        employee_id=None,
        last_login_at=None,
    )


# --- Login -----------------------------------------------------------------
async def test_login_success(client: AsyncClient, mock_auth_service: AsyncMock) -> None:
    mock_auth_service.login.return_value = LoginResponse(
        access_token="access-abc",
        refresh_token="refresh-xyz",
        token_type="bearer",
        expires_in=900,
        user=_auth_user(),
    )
    resp = await client.post(
        f"{API_PREFIX}/auth/login",
        json={"email": "user@example.com", "password": "Secret123"},
        headers=ORG_HEADER,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["data"]["access_token"] == "access-abc"
    assert body["data"]["user"]["email"] == "user@example.com"


async def test_login_invalid_email_returns_422(client: AsyncClient) -> None:
    resp = await client.post(
        f"{API_PREFIX}/auth/login",
        json={"email": "not-an-email", "password": "Secret123"},
        headers=ORG_HEADER,
    )
    assert resp.status_code == 422
    body = resp.json()
    assert body["success"] is False
    assert body["error"]["code"] == "VALIDATION_ERROR"


async def test_login_missing_password_returns_422(client: AsyncClient) -> None:
    resp = await client.post(
        f"{API_PREFIX}/auth/login",
        json={"email": "user@example.com"},
        headers=ORG_HEADER,
    )
    assert resp.status_code == 422


async def test_login_missing_tenant_returns_400(client: AsyncClient) -> None:
    resp = await client.post(
        f"{API_PREFIX}/auth/login",
        json={"email": "user@example.com", "password": "Secret123"},
    )
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "TENANT_UNRESOLVED"


async def test_login_invalid_credentials_returns_401(
    client: AsyncClient, mock_auth_service: AsyncMock
) -> None:
    from app.core.exceptions.base import AuthenticationException

    mock_auth_service.login.side_effect = AuthenticationException(
        "Invalid email or password.", code="AUTH_INVALID_CREDENTIALS"
    )
    resp = await client.post(
        f"{API_PREFIX}/auth/login",
        json={"email": "user@example.com", "password": "wrong"},
        headers=ORG_HEADER,
    )
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "AUTH_INVALID_CREDENTIALS"


# --- Refresh ---------------------------------------------------------------
async def test_refresh_success(client: AsyncClient, mock_auth_service: AsyncMock) -> None:
    mock_auth_service.refresh_token.return_value = AccessTokenResponse(
        access_token="new-access", token_type="bearer", expires_in=900
    )
    resp = await client.post(f"{API_PREFIX}/auth/refresh", json={"refresh_token": "r"})
    assert resp.status_code == 200
    assert resp.json()["data"]["access_token"] == "new-access"


async def test_refresh_invalid_returns_401(
    client: AsyncClient, mock_auth_service: AsyncMock
) -> None:
    from app.core.exceptions.base import AuthenticationException

    mock_auth_service.refresh_token.side_effect = AuthenticationException(
        "Invalid or expired refresh token.", code="AUTH_REFRESH_INVALID"
    )
    resp = await client.post(f"{API_PREFIX}/auth/refresh", json={"refresh_token": "bad"})
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "AUTH_REFRESH_INVALID"


# --- Rate limiting (contract §7) -------------------------------------------
async def _login(client: AsyncClient, mock_auth_service: AsyncMock, email: str):
    mock_auth_service.login.return_value = LoginResponse(
        access_token="access-abc",
        refresh_token="refresh-xyz",
        token_type="bearer",
        expires_in=900,
        user=_auth_user(),
    )
    return await client.post(
        f"{API_PREFIX}/auth/login",
        json={"email": email, "password": "Secret123"},
        headers=ORG_HEADER,
    )


async def test_login_rate_limit_returns_429(
    client: AsyncClient, mock_auth_service: AsyncMock
) -> None:
    """The (attempts + 1)-th login from the same IP is rejected with 429 RATE_LIMITED."""
    limit = settings.login_rate_limit_attempts
    for _ in range(limit):
        assert (await _login(client, mock_auth_service, "user@example.com")).status_code == 200

    resp = await _login(client, mock_auth_service, "user@example.com")
    assert resp.status_code == 429
    body = resp.json()
    assert body["success"] is False
    assert body["error"]["code"] == "RATE_LIMITED"
    # Retry-After is advertised so clients back off for the rest of the window.
    assert 0 < int(resp.headers["retry-after"]) <= settings.login_rate_limit_window_seconds


async def test_login_rate_limit_trip_is_audited(
    client: AsyncClient, mock_auth_service: AsyncMock
) -> None:
    """A throttled login writes one `module="auth"` security-event audit row."""
    for _ in range(settings.login_rate_limit_attempts + 1):
        await _login(client, mock_auth_service, "user@example.com")

    mock_auth_service.record_rate_limit_event.assert_awaited_once()
    kwargs = mock_auth_service.record_rate_limit_event.await_args.kwargs
    assert kwargs["org_id"] == 1
    assert kwargs["scope"] == "login"
    assert kwargs["identifier"] == "user@example.com"
    assert kwargs["ip_address"]


async def test_login_rate_limit_does_not_lock_out_other_users(
    app, client: AsyncClient, mock_auth_service: AsyncMock
) -> None:
    """One flooding IP+email must not exhaust another user's budget.

    The two counters are independent, so a victim logging in from a different IP is
    unaffected by an attacker who has burned through their own IP/email buckets.
    """
    for _ in range(settings.login_rate_limit_attempts + 1):
        await _login(client, mock_auth_service, "attacker@example.com")

    transport = ASGITransport(app=app, client=("10.0.0.9", 5555))
    async with AsyncClient(transport=transport, base_url="http://test") as victim_client:
        resp = await _login(victim_client, mock_auth_service, "victim@example.com")
    assert resp.status_code == 200


async def test_refresh_rate_limit_returns_429(
    client: AsyncClient, mock_auth_service: AsyncMock
) -> None:
    mock_auth_service.refresh_token.return_value = AccessTokenResponse(
        access_token="new-access", token_type="bearer", expires_in=900
    )
    for _ in range(settings.refresh_rate_limit_attempts):
        resp = await client.post(f"{API_PREFIX}/auth/refresh", json={"refresh_token": "r"})
        assert resp.status_code == 200

    resp = await client.post(f"{API_PREFIX}/auth/refresh", json={"refresh_token": "r"})
    assert resp.status_code == 429
    assert resp.json()["error"]["code"] == "RATE_LIMITED"


# --- Unauthorized access ---------------------------------------------------
async def test_me_without_token_returns_401(client: AsyncClient) -> None:
    resp = await client.get(f"{API_PREFIX}/auth/me")
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "AUTH_NOT_AUTHENTICATED"


async def test_me_invalid_token_returns_401(client: AsyncClient) -> None:
    resp = await client.get(
        f"{API_PREFIX}/auth/me", headers={"Authorization": "Bearer not.a.jwt"}
    )
    assert resp.status_code == 401


# --- Token expiration ------------------------------------------------------
async def test_me_expired_token_returns_401(client: AsyncClient, expired_token: str) -> None:
    resp = await client.get(
        f"{API_PREFIX}/auth/me", headers={"Authorization": f"Bearer {expired_token}"}
    )
    assert resp.status_code == 401


# --- Authenticated endpoints ----------------------------------------------
async def test_me_success(
    client: AsyncClient, mock_auth_service: AsyncMock, auth_headers: dict[str, str]
) -> None:
    mock_auth_service.get_current_user.return_value = CurrentUserSchema(
        **_auth_user().model_dump(), permissions=[], data_scope=DataScopeSchema()
    )
    resp = await client.get(f"{API_PREFIX}/auth/me", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["data"]["email"] == "user@example.com"


async def test_logout_returns_204(
    client: AsyncClient, mock_auth_service: AsyncMock, auth_headers: dict[str, str]
) -> None:
    mock_auth_service.logout.return_value = None
    resp = await client.post(f"{API_PREFIX}/auth/logout", headers=auth_headers)
    assert resp.status_code == 204
    mock_auth_service.logout.assert_awaited_once()


async def test_revoke_session_returns_204(
    client: AsyncClient, mock_auth_service: AsyncMock, auth_headers: dict[str, str]
) -> None:
    mock_auth_service.revoke_session.return_value = None
    resp = await client.delete(f"{API_PREFIX}/auth/sessions/5", headers=auth_headers)
    assert resp.status_code == 204


async def test_revoke_all_returns_200(
    client: AsyncClient, mock_auth_service: AsyncMock, auth_headers: dict[str, str]
) -> None:
    mock_auth_service.revoke_all_other_sessions.return_value = RevokeAllSessionsResponse(
        revoked_count=2
    )
    resp = await client.post(f"{API_PREFIX}/auth/sessions/revoke-all", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["data"]["revoked_count"] == 2


# --- Password change / reset are NOT part of the auth module ---------------
async def test_change_password_not_in_auth(client: AsyncClient) -> None:
    """Change Password is deferred to the User Management module (contract)."""
    resp = await client.post(
        f"{API_PREFIX}/auth/change-password", json={"old": "x", "new": "y"}
    )
    assert resp.status_code == 404


async def test_reset_password_not_in_auth(client: AsyncClient) -> None:
    """Forgot/Reset Password has no supporting schema (contract Open Question)."""
    forgot = await client.post(f"{API_PREFIX}/auth/forgot-password", json={"email": "u@e.com"})
    reset = await client.post(f"{API_PREFIX}/auth/reset-password", json={"token": "t"})
    assert forgot.status_code == 404
    assert reset.status_code == 404


# --- Multi-Organization Switching Endpoints (Phase 4) ----------------------
async def test_get_my_organizations_returns_list(
    client: AsyncClient,
    mock_org_membership_service: AsyncMock,
    auth_headers: dict[str, str],
) -> None:
    expected = [
        OrganizationSummarySchema(
            org_id=10, org_code="ACME", org_name="Acme Corp", is_primary=True, is_active=True
        )
    ]
    mock_org_membership_service.list_organizations.return_value = expected

    resp = await client.get(f"{API_PREFIX}/auth/my-organizations", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert len(body["data"]) == 1
    assert body["data"][0]["org_id"] == 10
    assert body["data"][0]["org_code"] == "ACME"
    mock_org_membership_service.list_organizations.assert_awaited_once_with(user_id=1)


async def test_get_my_organizations_unauthorized(client: AsyncClient) -> None:
    resp = await client.get(f"{API_PREFIX}/auth/my-organizations")
    assert resp.status_code == 401


async def test_switch_organization_success(
    client: AsyncClient,
    mock_org_switch_service: AsyncMock,
    auth_headers: dict[str, str],
) -> None:
    mock_org_switch_service.switch_organization.return_value = AccessTokenResponse(
        access_token="new-access-token",
        token_type="bearer",
        expires_in=900,
        refresh_token=None,
    )

    resp = await client.post(
        f"{API_PREFIX}/auth/switch-organization",
        json={"org_id": 20},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["data"]["access_token"] == "new-access-token"
    # Note: session_id is "10" by default in auth_headers/make_access_token fixture
    mock_org_switch_service.switch_organization.assert_awaited_once_with(
        user_id=1, target_org_id=20, session_id=10
    )


async def test_switch_organization_unauthorized(client: AsyncClient) -> None:
    resp = await client.post(
        f"{API_PREFIX}/auth/switch-organization",
        json={"org_id": 20},
    )
    assert resp.status_code == 401


async def test_switch_organization_validation_error(
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    resp = await client.post(
        f"{API_PREFIX}/auth/switch-organization",
        json={"org_id": "not-an-int"},
        headers=auth_headers,
    )
    assert resp.status_code == 422
