"""Unit tests for Enterprise Settings & Policy Management."""

from __future__ import annotations

import datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.modules.settings.schemas import (
    AttendancePolicyUpdateRequest,
    NotificationPolicyUpdateRequest,
    SecurityPolicyUpdateRequest,
)
from app.modules.settings.service import SettingsService

_ORG_ID = 10
_USER_ID = 42


def _make_policy(**overrides) -> SimpleNamespace:
    defaults = dict(
        id=1,
        org_id=_ORG_ID,
        branch_id=None,
        grace_period_minutes=15,
        late_penalty_enabled=False,
        overtime_buffer_minutes=30,
        overtime_multiplier=Decimal("1.50"),
        password_min_length=8,
        password_require_special=True,
        session_timeout_minutes=60,
        max_failed_login_attempts=5,
        lockout_duration_minutes=15,
        email_enabled=True,
        sms_enabled=False,
        push_enabled=True,
        sender_email="noreply@hrms.com",
        updated_by=None,
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def _make_service() -> SettingsService:
    session = AsyncMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    svc = SettingsService(session)
    svc.policy_settings = AsyncMock()
    svc.audit = AsyncMock()
    return svc


@pytest.mark.asyncio
async def test_get_and_update_attendance_policy() -> None:
    """GET and PATCH /settings/attendance-policy."""
    svc = _make_service()
    mock_pol = _make_policy()
    svc.policy_settings.get_by_org_id.return_value = mock_pol

    # Get default policy
    get_res = await svc.get_attendance_policy(org_id=_ORG_ID)
    assert get_res.grace_period_minutes == 15
    assert get_res.overtime_multiplier == 1.5

    # Update policy
    update_data = AttendancePolicyUpdateRequest(
        grace_period_minutes=20,
        overtime_multiplier=2.0,
    )
    patch_res = await svc.update_attendance_policy(
        org_id=_ORG_ID, data=update_data, updated_by=_USER_ID
    )
    assert mock_pol.grace_period_minutes == 20
    assert mock_pol.overtime_multiplier == Decimal("2.0")
    svc.audit.record.assert_called_once()


@pytest.mark.asyncio
async def test_get_and_update_security_policy() -> None:
    """GET and PATCH /settings/security-policy."""
    svc = _make_service()
    mock_pol = _make_policy()
    svc.policy_settings.get_by_org_id.return_value = mock_pol

    get_res = await svc.get_security_policy(org_id=_ORG_ID)
    assert get_res.password_min_length == 8
    assert get_res.session_timeout_minutes == 60

    update_data = SecurityPolicyUpdateRequest(
        password_min_length=12,
        session_timeout_minutes=30,
    )
    patch_res = await svc.update_security_policy(
        org_id=_ORG_ID, data=update_data, updated_by=_USER_ID
    )
    assert mock_pol.password_min_length == 12
    assert mock_pol.session_timeout_minutes == 30
    svc.audit.record.assert_called_once()


@pytest.mark.asyncio
async def test_get_and_update_notification_policy() -> None:
    """GET and PATCH /settings/notification-policy."""
    svc = _make_service()
    mock_pol = _make_policy()
    svc.policy_settings.get_by_org_id.return_value = mock_pol

    get_res = await svc.get_notification_policy(org_id=_ORG_ID)
    assert get_res.email_enabled is True
    assert get_res.sms_enabled is False

    update_data = NotificationPolicyUpdateRequest(
        sms_enabled=True,
        sender_email="hr@codeinfotech.com",
    )
    patch_res = await svc.update_notification_policy(
        org_id=_ORG_ID, data=update_data, updated_by=_USER_ID
    )
    assert mock_pol.sms_enabled is True
    assert mock_pol.sender_email == "hr@codeinfotech.com"
    svc.audit.record.assert_called_once()
