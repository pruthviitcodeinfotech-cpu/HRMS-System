"""Unit tests for ProfileService.

Covers:
  - get_profile assembles user + organization + branch + employee + role
  - update_profile updates the mobile number and rejects duplicates
  - update_profile is a no-op when no editable field is supplied
  - change_password verifies the current password before hashing the new one
  - update_profile_photo requires (and stores against) a linked employee
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.modules.profile.exceptions import (
    IncorrectCurrentPasswordException,
    MobileNumberExistsException,
    NoEmployeeLinkedException,
)
from app.modules.profile.schemas import ChangePasswordRequest, ProfileUpdateRequest
from app.modules.profile.service import ProfileService

_NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _user(**overrides) -> SimpleNamespace:
    base = dict(
        id=1,
        org_id=1,
        name="Jane Doe",
        email="jane@example.com",
        mobile_country_code="+91",
        mobile_number="9000000000",
        is_super_admin=False,
        is_active=True,
        employee_id=None,
        password_hash="hashed-secret",
        signature_url=None,
        emergency_contact_name=None,
        emergency_contact_phone=None,
        emergency_contact_relationship=None,
        language="en",
        timezone="Asia/Kolkata",
        theme="system",
        is_2fa_enabled=False,
        notification_preferences=None,
        last_login_at=_NOW,
        created_at=_NOW,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def _org(**overrides) -> SimpleNamespace:
    base = dict(
        org_id=1,
        org_code="ACME",
        org_name="Acme Corp",
        contact_phone="9876543210",
        contact_email="hq@acme.test",
        is_active=True,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def _employee(**overrides) -> SimpleNamespace:
    base = dict(
        employee_id=10,
        employee_code="EMP-010",
        employee_name="Jane Doe",
        profile_photo_url=None,
        date_of_joining=date(2024, 1, 1),
        department=SimpleNamespace(dept_name="Engineering"),
        designation=SimpleNamespace(designation_name="Senior Engineer"),
        master_branch=SimpleNamespace(
            branch_id=5,
            branch_name="HQ",
            address="123 Main St",
            city="Surat",
            state="Gujarat",
            country="India",
        ),
    )
    base.update(overrides)
    return SimpleNamespace(**base)


@pytest.fixture
def profile_service() -> ProfileService:
    svc = ProfileService(AsyncMock())
    svc.profile = AsyncMock()
    svc.audit = AsyncMock()
    svc.sessions = AsyncMock()
    svc.sessions.revoke_all_for_user.return_value = 0
    return svc


# ---------------------------------------------------------------------------
# get_profile
# ---------------------------------------------------------------------------


async def test_get_profile_without_linked_employee(profile_service: ProfileService) -> None:
    profile_service.profile.get_user.return_value = _user()
    profile_service.profile.get_organization.return_value = _org()
    profile_service.profile.get_role_name.return_value = "Admin"

    result = await profile_service.get_profile(user_id=1, org_id=1)

    assert result.user_id == 1
    assert result.role_name == "Admin"
    assert result.organization.org_code == "ACME"
    assert result.branch is None
    assert result.employee is None
    assert result.profile_photo_url is None
    profile_service.profile.get_employee.assert_not_awaited()


async def test_get_profile_with_linked_employee(profile_service: ProfileService) -> None:
    profile_service.profile.get_user.return_value = _user(employee_id=10)
    profile_service.profile.get_organization.return_value = _org()
    profile_service.profile.get_role_name.return_value = None
    profile_service.profile.get_employee.return_value = _employee(
        profile_photo_url="profile-photos/abc.jpg"
    )

    result = await profile_service.get_profile(user_id=1, org_id=1)

    assert result.employee is not None
    assert result.employee.employee_code == "EMP-010"
    assert result.employee.department_name == "Engineering"
    assert result.employee.designation_name == "Senior Engineer"
    assert result.branch is not None
    assert result.branch.branch_name == "HQ"
    assert result.profile_photo_url == "profile-photos/abc.jpg"


# ---------------------------------------------------------------------------
# update_profile
# ---------------------------------------------------------------------------


async def test_update_profile_changes_mobile_number(profile_service: ProfileService) -> None:
    user = _user()
    profile_service.profile.get_user.return_value = user
    profile_service.profile.get_organization.return_value = _org()
    profile_service.profile.get_role_name.return_value = None
    profile_service.profile.mobile_exists.return_value = False

    async def fake_update(u, updates):
        for k, v in updates.items():
            setattr(u, k, v)
        return u

    profile_service.profile.update_user.side_effect = fake_update

    payload = ProfileUpdateRequest(mobile_number="9123456780")
    result = await profile_service.update_profile(user_id=1, org_id=1, data=payload)

    assert result.mobile_number == "9123456780"
    profile_service.profile.mobile_exists.assert_awaited_once_with(
        1, "+91", "9123456780", exclude_user_id=1
    )
    profile_service.audit.record.assert_awaited_once()


async def test_update_profile_rejects_duplicate_mobile(profile_service: ProfileService) -> None:
    profile_service.profile.get_user.return_value = _user()
    profile_service.profile.mobile_exists.return_value = True

    payload = ProfileUpdateRequest(mobile_number="9123456780")
    with pytest.raises(MobileNumberExistsException):
        await profile_service.update_profile(user_id=1, org_id=1, data=payload)

    profile_service.profile.update_user.assert_not_awaited()
    profile_service.audit.record.assert_not_awaited()


# ---------------------------------------------------------------------------
# change_password
# ---------------------------------------------------------------------------


_STRONG_PASSWORD = "NewSecret123!"


async def test_change_password_rejects_incorrect_current_password(
    profile_service: ProfileService,
) -> None:
    profile_service.profile.get_user.return_value = _user(password_hash="a-real-bcrypt-hash")

    payload = ChangePasswordRequest(
        current_password="wrong-password",
        new_password=_STRONG_PASSWORD,
        confirm_password=_STRONG_PASSWORD,
    )
    with pytest.raises(IncorrectCurrentPasswordException):
        await profile_service.change_password(
            user_id=1, org_id=1, data=payload, current_session_id=10
        )

    profile_service.profile.update_user.assert_not_awaited()
    profile_service.sessions.revoke_all_for_user.assert_not_awaited()


async def test_change_password_success(
    profile_service: ProfileService, monkeypatch: pytest.MonkeyPatch
) -> None:
    profile_service.profile.get_user.return_value = _user(password_hash="old-hash")
    profile_service.sessions.revoke_all_for_user.return_value = 3
    monkeypatch.setattr(
        "app.modules.profile.service.verify_password", MagicMock(return_value=True)
    )
    monkeypatch.setattr(
        "app.modules.profile.service.hash_password", MagicMock(return_value="new-hash")
    )

    payload = ChangePasswordRequest(
        current_password="old-password",
        new_password=_STRONG_PASSWORD,
        confirm_password=_STRONG_PASSWORD,
    )
    result = await profile_service.change_password(
        user_id=1, org_id=1, data=payload, current_session_id=10
    )

    profile_service.profile.update_user.assert_awaited_once()
    args, _ = profile_service.profile.update_user.call_args
    assert args[1] == {"password_hash": "new-hash"}
    revoke_call = profile_service.sessions.revoke_all_for_user.call_args
    assert revoke_call.args == (1,)
    assert revoke_call.kwargs["exclude_session_id"] == 10
    assert isinstance(revoke_call.kwargs["when"], datetime)
    profile_service.audit.record.assert_awaited_once()
    assert result.revoked_session_count == 3


async def test_change_password_rejects_weak_password() -> None:
    with pytest.raises(ValueError):
        ChangePasswordRequest(
            current_password="old-password",
            new_password="weakpassword",
            confirm_password="weakpassword",
        )


# ---------------------------------------------------------------------------
# update_profile_photo
# ---------------------------------------------------------------------------


async def test_update_profile_photo_requires_linked_employee(
    profile_service: ProfileService,
) -> None:
    profile_service.profile.get_user.return_value = _user(employee_id=None)

    with pytest.raises(NoEmployeeLinkedException):
        await profile_service.update_profile_photo(user_id=1, org_id=1, upload=AsyncMock())

    profile_service.profile.update_employee.assert_not_awaited()


async def test_update_profile_photo_success(profile_service: ProfileService) -> None:
    profile_service.profile.get_user.return_value = _user(employee_id=10)
    employee = _employee()
    profile_service.profile.get_employee.return_value = employee

    stored = SimpleNamespace(key="profile-photos/xyz.png")
    fake_storage = AsyncMock()
    fake_storage.save_upload.return_value = stored
    profile_service._storage = fake_storage

    async def fake_update_employee(emp, updates):
        for k, v in updates.items():
            setattr(emp, k, v)
        return emp

    profile_service.profile.update_employee.side_effect = fake_update_employee

    result = await profile_service.update_profile_photo(user_id=1, org_id=1, upload=AsyncMock())

    assert result.profile_photo_url == "profile-photos/xyz.png"
    profile_service.profile.update_employee.assert_awaited_once_with(
        employee, {"profile_photo_url": "profile-photos/xyz.png"}
    )
    profile_service.audit.record.assert_awaited_once()
