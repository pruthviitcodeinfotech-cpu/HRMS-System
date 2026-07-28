"""Unit tests for Enterprise User Profile & Account Management."""

from __future__ import annotations

import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.modules.profile.schemas import (
    EmergencyContactUpdateRequest,
    PreferencesUpdateRequest,
)
from app.modules.profile.service import ProfileService

_ORG_ID = 10
_USER_ID = 42
_NOW = datetime.datetime(2026, 7, 28, 12, 0, 0, tzinfo=datetime.timezone.utc)


def _make_user(**overrides) -> SimpleNamespace:
    defaults = dict(
        id=_USER_ID,
        name="Pruthvi",
        email="pruthvi@codeinfotech.com",
        mobile_country_code="+91",
        mobile_number="9876543210",
        is_super_admin=False,
        is_active=True,
        employee_id=None,
        signature_url=None,
        emergency_contact_name=None,
        emergency_contact_phone=None,
        emergency_contact_relationship=None,
        language="en",
        timezone="Asia/Kolkata",
        theme="system",
        is_2fa_enabled=False,
        totp_secret=None,
        notification_preferences=None,
        last_login_at=_NOW,
        created_at=_NOW,
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def _make_org() -> SimpleNamespace:
    return SimpleNamespace(
        org_id=_ORG_ID,
        org_code="CIT",
        org_name="CodeInfotech",
        contact_phone=None,
        contact_email=None,
        is_active=True,
    )


def _make_service() -> ProfileService:
    session = AsyncMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    svc = ProfileService(session)
    svc.profile.get_role_name = AsyncMock(return_value="Employee")
    svc.profile.get_organization = AsyncMock(return_value=_make_org())
    svc.profile.get_employee = AsyncMock(return_value=None)
    svc.profile.update_user = AsyncMock()
    svc.audit.record = AsyncMock()
    return svc


@pytest.mark.asyncio
async def test_update_emergency_contact() -> None:
    """PUT /profile/emergency-contact updates the three emergency contact fields."""
    svc = _make_service()
    mock_user = _make_user()
    svc.profile.get_user = AsyncMock(return_value=mock_user)

    payload = EmergencyContactUpdateRequest(
        name="Emergency Contact",
        phone="+919876543211",
        relationship="Spouse",
    )

    res = await svc.update_emergency_contact(user_id=_USER_ID, org_id=_ORG_ID, data=payload)
    assert res.user_id == _USER_ID

    # update_user should have been called with the correct dict
    call_args = svc.profile.update_user.call_args_list[0][0]
    update_dict = svc.profile.update_user.call_args_list[0][0][1]
    assert update_dict["emergency_contact_name"] == "Emergency Contact"
    assert update_dict["emergency_contact_relationship"] == "Spouse"

    # audit should have been fired once
    svc.audit.record.assert_called_once()


@pytest.mark.asyncio
async def test_update_preferences_theme_language_timezone() -> None:
    """PUT /profile/preferences stores language/timezone/theme."""
    svc = _make_service()
    mock_user = _make_user(theme="dark")
    svc.profile.get_user = AsyncMock(return_value=mock_user)

    payload = PreferencesUpdateRequest(
        theme="dark",
        language="hi",
        timezone="UTC",
        notification_preferences={"email": True, "in_app": True},
    )

    res = await svc.update_preferences(user_id=_USER_ID, org_id=_ORG_ID, data=payload)
    assert res.user_id == _USER_ID
    svc.profile.update_user.assert_called_once()

    update_dict = svc.profile.update_user.call_args_list[0][0][1]
    assert update_dict["theme"] == "dark"
    assert update_dict["language"] == "hi"
    assert update_dict["timezone"] == "UTC"
    # notification prefs are JSON-serialized
    assert "notification_preferences" in update_dict


@pytest.mark.asyncio
async def test_setup_2fa_returns_valid_uri() -> None:
    """POST /profile/2fa/setup returns TOTP provisioning URI."""
    svc = _make_service()
    mock_user = _make_user()
    svc.profile.get_user = AsyncMock(return_value=mock_user)

    setup_res = await svc.setup_2fa(user_id=_USER_ID, org_id=_ORG_ID)

    assert setup_res.totp_secret is not None
    assert len(setup_res.totp_secret) >= 10
    assert setup_res.provisioning_uri.startswith("otpauth://totp/")
    assert "secret=" in setup_res.provisioning_uri
    assert "issuer=" in setup_res.provisioning_uri

    # Secret should have been stored
    svc.profile.update_user.assert_called_once()
    stored = svc.profile.update_user.call_args_list[0][0][1]
    assert stored["totp_secret"] == setup_res.totp_secret


@pytest.mark.asyncio
async def test_enable_2fa_accepts_valid_code() -> None:
    """POST /profile/2fa/enable accepts a valid TOTP code and enables 2FA."""
    import base64
    import hmac
    import hashlib
    import time
    import struct

    # Generate a secret
    import secrets as _secrets
    raw_secret = base64.b32encode(_secrets.token_bytes(10)).decode("utf-8").rstrip("=")

    svc = _make_service()
    mock_user = _make_user(totp_secret=raw_secret, is_2fa_enabled=False)
    svc.profile.get_user = AsyncMock(return_value=mock_user)

    # Compute current valid TOTP code
    sec = raw_secret.upper()
    if len(sec) % 8:
        sec += "=" * (8 - len(sec) % 8)
    key = base64.b32decode(sec)
    counter = int(time.time() // 30)
    msg = struct.pack(">Q", counter)
    h = hmac.new(key, msg, hashlib.sha1).digest()
    offset = h[-1] & 0x0F
    code_int = struct.unpack(">I", h[offset : offset + 4])[0] & 0x7FFFFFFF
    valid_code = str(code_int % 1000000).zfill(6)

    await svc.enable_2fa(user_id=_USER_ID, org_id=_ORG_ID, code=valid_code)

    # 2FA flag should have been set to True
    svc.profile.update_user.assert_called_once_with(mock_user, {"is_2fa_enabled": True})
    svc.audit.record.assert_called_once()


@pytest.mark.asyncio
async def test_enable_2fa_rejects_invalid_code() -> None:
    """POST /profile/2fa/enable raises ValidationException for wrong code."""
    import base64
    import secrets as _secrets

    raw_secret = base64.b32encode(_secrets.token_bytes(10)).decode("utf-8").rstrip("=")
    svc = _make_service()
    mock_user = _make_user(totp_secret=raw_secret, is_2fa_enabled=False)
    svc.profile.get_user = AsyncMock(return_value=mock_user)

    from app.core.exceptions.base import ValidationException

    with pytest.raises(ValidationException):
        await svc.enable_2fa(user_id=_USER_ID, org_id=_ORG_ID, code="000000")


@pytest.mark.asyncio
async def test_disable_2fa_clears_secret() -> None:
    """POST /profile/2fa/disable clears TOTP secret and disables flag."""
    svc = _make_service()
    mock_user = _make_user(totp_secret="SOMESECRET", is_2fa_enabled=True)
    svc.profile.get_user = AsyncMock(return_value=mock_user)

    await svc.disable_2fa(user_id=_USER_ID, org_id=_ORG_ID)

    svc.profile.update_user.assert_called_once_with(
        mock_user, {"is_2fa_enabled": False, "totp_secret": None}
    )
    svc.audit.record.assert_called_once()


@pytest.mark.asyncio
async def test_get_active_sessions_marks_current() -> None:
    """GET /profile/sessions marks the calling session as is_current=True."""
    import datetime
    svc = _make_service()
    mock_user = _make_user()
    svc.profile.get_user = AsyncMock(return_value=mock_user)

    from types import SimpleNamespace
    s1 = SimpleNamespace(id=1, device_info="Chrome", ip_address="127.0.0.1",
                          created_at=_NOW, expires_at=None, is_active=True)
    s2 = SimpleNamespace(id=2, device_info="Firefox", ip_address="192.168.1.1",
                          created_at=_NOW, expires_at=None, is_active=True)

    # Mock the DB query result
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [s1, s2]
    svc.session.execute = AsyncMock(return_value=mock_result)

    sessions = await svc.get_active_sessions(user_id=_USER_ID, org_id=_ORG_ID, current_session_id=1)
    assert len(sessions) == 2
    assert sessions[0].is_current is True
    assert sessions[1].is_current is False


@pytest.mark.asyncio
async def test_revoke_all_other_sessions() -> None:
    """POST /profile/sessions/revoke-others calls revoke_user_sessions correctly."""
    svc = _make_service()
    mock_user = _make_user()
    svc.profile.get_user = AsyncMock(return_value=mock_user)
    svc.sessions.revoke_user_sessions = AsyncMock(return_value=3)

    count = await svc.revoke_all_other_sessions(
        user_id=_USER_ID, org_id=_ORG_ID, current_session_id=1
    )
    assert count == 3
    svc.sessions.revoke_user_sessions.assert_called_once_with(mock_user.id, exclude_session_id=1)
    svc.audit.record.assert_called_once()
