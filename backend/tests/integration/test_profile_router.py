from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.core.dependencies.auth import assert_session_live
from app.modules.profile.dependencies import get_profile_service
from app.modules.profile.exceptions import (
    IncorrectCurrentPasswordException,
    MobileNumberExistsException,
    NoEmployeeLinkedException,
)
from app.modules.profile.schemas import (
    ChangePasswordResponse,
    OrganizationSummary,
    ProfilePhotoResponse,
    ProfileSchema,
)
from tests.conftest import API_PREFIX

_NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)
_STRONG_PASSWORD = "NewSecret123!"


@pytest.fixture
def mock_profile_service() -> AsyncMock:
    return AsyncMock()


@pytest_asyncio.fixture
async def profile_client(app, mock_profile_service: AsyncMock):
    app.dependency_overrides[assert_session_live] = lambda: None
    app.dependency_overrides[get_profile_service] = lambda: mock_profile_service
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as http_client:
        yield http_client
    app.dependency_overrides.clear()


def _profile(mobile_number: str = "9000000000") -> ProfileSchema:
    return ProfileSchema(
        user_id=1,
        name="Jane Doe",
        email="jane@example.com",
        mobile_country_code="+91",
        mobile_number=mobile_number,
        is_super_admin=False,
        is_active=True,
        role_name="Admin",
        profile_photo_url=None,
        last_login_at=_NOW,
        created_at=_NOW,
        organization=OrganizationSummary(
            org_id=1, org_code="ACME", org_name="Acme Corp", is_active=True
        ),
        branch=None,
        employee=None,
    )


async def test_get_profile_200(
    profile_client: AsyncClient, mock_profile_service: AsyncMock, auth_headers
) -> None:
    mock_profile_service.get_profile.return_value = _profile()
    resp = await profile_client.get(f"{API_PREFIX}/profile", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["data"]["user_id"] == 1
    mock_profile_service.get_profile.assert_awaited_once_with(user_id=1, org_id=1)


async def test_get_profile_requires_auth(profile_client: AsyncClient) -> None:
    resp = await profile_client.get(f"{API_PREFIX}/profile")
    assert resp.status_code == 401


async def test_update_profile_200(
    profile_client: AsyncClient, mock_profile_service: AsyncMock, auth_headers
) -> None:
    mock_profile_service.update_profile.return_value = _profile("9123456780")
    resp = await profile_client.put(
        f"{API_PREFIX}/profile",
        json={"mobile_number": "9123456780"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["mobile_number"] == "9123456780"


async def test_update_profile_duplicate_mobile_409(
    profile_client: AsyncClient, mock_profile_service: AsyncMock, auth_headers
) -> None:
    mock_profile_service.update_profile.side_effect = MobileNumberExistsException()
    resp = await profile_client.put(
        f"{API_PREFIX}/profile",
        json={"mobile_number": "9123456780"},
        headers=auth_headers,
    )
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "MOBILE_NUMBER_EXISTS"


async def test_update_profile_rejects_empty_payload_422(
    profile_client: AsyncClient, auth_headers
) -> None:
    resp = await profile_client.put(f"{API_PREFIX}/profile", json={}, headers=auth_headers)
    assert resp.status_code == 422


async def test_change_password_200(
    profile_client: AsyncClient, mock_profile_service: AsyncMock, auth_headers
) -> None:
    mock_profile_service.change_password.return_value = ChangePasswordResponse(
        revoked_session_count=2
    )
    resp = await profile_client.put(
        f"{API_PREFIX}/profile/change-password",
        json={
            "current_password": "OldSecret123!",
            "new_password": _STRONG_PASSWORD,
            "confirm_password": _STRONG_PASSWORD,
        },
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["revoked_session_count"] == 2
    call = mock_profile_service.change_password.call_args
    assert call.kwargs["user_id"] == 1
    assert call.kwargs["org_id"] == 1
    assert call.kwargs["current_session_id"] == 10


async def test_change_password_incorrect_current_401(
    profile_client: AsyncClient, mock_profile_service: AsyncMock, auth_headers
) -> None:
    mock_profile_service.change_password.side_effect = IncorrectCurrentPasswordException()
    resp = await profile_client.put(
        f"{API_PREFIX}/profile/change-password",
        json={
            "current_password": "WrongSecret123!",
            "new_password": _STRONG_PASSWORD,
            "confirm_password": _STRONG_PASSWORD,
        },
        headers=auth_headers,
    )
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "CURRENT_PASSWORD_INCORRECT"


async def test_change_password_mismatched_confirmation_422(
    profile_client: AsyncClient, auth_headers
) -> None:
    resp = await profile_client.put(
        f"{API_PREFIX}/profile/change-password",
        json={
            "current_password": "OldSecret123!",
            "new_password": _STRONG_PASSWORD,
            "confirm_password": "Different123!",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 422


async def test_change_password_rejects_weak_password_422(
    profile_client: AsyncClient, auth_headers
) -> None:
    resp = await profile_client.put(
        f"{API_PREFIX}/profile/change-password",
        json={
            "current_password": "OldSecret123!",
            "new_password": "alllowercase1",
            "confirm_password": "alllowercase1",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "VALIDATION_ERROR"


async def test_update_profile_photo_no_employee_409(
    profile_client: AsyncClient, mock_profile_service: AsyncMock, auth_headers
) -> None:
    mock_profile_service.update_profile_photo.side_effect = NoEmployeeLinkedException()
    resp = await profile_client.put(
        f"{API_PREFIX}/profile/photo",
        files={"file": ("photo.png", b"fake-bytes", "image/png")},
        headers=auth_headers,
    )
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "NO_EMPLOYEE_LINKED"


async def test_update_profile_photo_200(
    profile_client: AsyncClient, mock_profile_service: AsyncMock, auth_headers
) -> None:
    mock_profile_service.update_profile_photo.return_value = ProfilePhotoResponse(
        profile_photo_url="profile-photos/abc.png"
    )
    resp = await profile_client.put(
        f"{API_PREFIX}/profile/photo",
        files={"file": ("photo.png", b"fake-bytes", "image/png")},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["profile_photo_url"] == "profile-photos/abc.png"
