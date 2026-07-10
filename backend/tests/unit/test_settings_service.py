"""Unit tests for the Settings Management Service layer."""

from __future__ import annotations

import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.modules.settings.exceptions import (
    SettingsNotFoundException,
    SettingsValidationException,
    UnknownFeatureException,
)
from app.modules.settings.service import SettingsService

_ORG_ID = 10
_USER_ID = 99
_CALLER_NAME = "Admin User"

_NOW = datetime.datetime(2026, 7, 10, 10, 0, 0, tzinfo=datetime.timezone.utc)  # noqa: UP017


def _make_org_settings(**overrides) -> SimpleNamespace:
    base = {
        "id": 1,
        "org_id": _ORG_ID,
        "advance_shift_enabled": False,
        "enable_regularization": False,
        "enable_photo_punch": False,
        "device_sync_time": datetime.time(16, 51, 0),
        "sync_code": "SYNC001",
        "pass_code": "PASS01",
        "updated_by": None,
        "created_at": _NOW,
        "updated_at": _NOW,
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def _make_slip_settings(**overrides) -> SimpleNamespace:
    base = {
        "id": 2,
        "org_id": _ORG_ID,
        "company_logo_url": None,
        "company_name": "ACME Corp",
        "company_address": "123 Main St",
        "company_contact": "9876543210",
        "company_website_email": None,
        "auto_release_payslip": True,
        "branch_wise_payslip": False,
        "updated_by": None,
        "created_at": _NOW,
        "updated_at": _NOW,
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def _make_service() -> SettingsService:
    svc = SettingsService(AsyncMock())
    svc.org_settings = AsyncMock()
    svc.salary_slip = AsyncMock()
    svc.cross_module = AsyncMock()
    svc.users = AsyncMock()
    svc.audit = AsyncMock()
    svc.audit.record = AsyncMock()
    return svc


# ===========================================================================
# 1. get_configuration_view
# ===========================================================================


@pytest.mark.asyncio
async def test_get_configuration_view_returns_dict() -> None:
    svc = _make_service()
    svc.org_settings.get_by_org_id = AsyncMock(return_value=_make_org_settings())
    svc.salary_slip.get_by_org_id = AsyncMock(return_value=_make_slip_settings())

    result = await svc.get_configuration_view(_ORG_ID)

    assert "organization" in result
    assert "salary_slip" in result
    assert "cross_module_pointers" in result
    assert result["organization"].org_id == _ORG_ID


@pytest.mark.asyncio
async def test_get_configuration_view_none_rows() -> None:
    svc = _make_service()
    svc.org_settings.get_by_org_id = AsyncMock(return_value=None)
    svc.salary_slip.get_by_org_id = AsyncMock(return_value=None)

    result = await svc.get_configuration_view(_ORG_ID)

    assert result["organization"] is None
    assert result["salary_slip"] is None
    assert "leave" in result["cross_module_pointers"]


# ===========================================================================
# 2. get_org_settings
# ===========================================================================


@pytest.mark.asyncio
async def test_get_org_settings_found() -> None:
    svc = _make_service()
    svc.org_settings.get_by_org_id = AsyncMock(return_value=_make_org_settings())

    result = await svc.get_org_settings(_ORG_ID)
    assert result.org_id == _ORG_ID


@pytest.mark.asyncio
async def test_get_org_settings_not_found() -> None:
    svc = _make_service()
    svc.org_settings.get_by_org_id = AsyncMock(return_value=None)

    with pytest.raises(SettingsNotFoundException):
        await svc.get_org_settings(_ORG_ID)


# ===========================================================================
# 3. update_org_settings
# ===========================================================================


@pytest.mark.asyncio
async def test_update_org_settings_patch_existing() -> None:
    svc = _make_service()
    existing = _make_org_settings()
    updated = _make_org_settings(advance_shift_enabled=True)
    svc.org_settings.get_by_org_id = AsyncMock(return_value=existing)
    svc.org_settings.update = AsyncMock(return_value=updated)

    result = await svc.update_org_settings(
        _ORG_ID, _USER_ID, _CALLER_NAME, advance_shift_enabled=True
    )

    assert result.advance_shift_enabled is True
    svc.org_settings.update.assert_called_once()
    svc.audit.record.assert_called_once()


@pytest.mark.asyncio
async def test_update_org_settings_upsert_creates_row() -> None:
    svc = _make_service()
    new_row = _make_org_settings()
    svc.org_settings.get_by_org_id = AsyncMock(return_value=None)
    svc.org_settings.create = AsyncMock(return_value=new_row)

    result = await svc.update_org_settings(
        _ORG_ID,
        _USER_ID,
        _CALLER_NAME,
        sync_code="CODE1",
        pass_code="PASS1",
    )

    svc.org_settings.create.assert_called_once()
    assert result.org_id == _ORG_ID


@pytest.mark.asyncio
async def test_update_org_settings_upsert_missing_sync_code() -> None:
    svc = _make_service()
    svc.org_settings.get_by_org_id = AsyncMock(return_value=None)

    with pytest.raises(SettingsValidationException, match="sync_code"):
        await svc.update_org_settings(_ORG_ID, _USER_ID, _CALLER_NAME, pass_code="PASS1")


@pytest.mark.asyncio
async def test_update_org_settings_upsert_missing_pass_code() -> None:
    svc = _make_service()
    svc.org_settings.get_by_org_id = AsyncMock(return_value=None)

    with pytest.raises(SettingsValidationException, match="pass_code"):
        await svc.update_org_settings(_ORG_ID, _USER_ID, _CALLER_NAME, sync_code="CODE1")


@pytest.mark.asyncio
async def test_update_org_settings_sync_code_too_long() -> None:
    svc = _make_service()
    svc.org_settings.get_by_org_id = AsyncMock(return_value=_make_org_settings())

    with pytest.raises(SettingsValidationException, match="sync_code"):
        await svc.update_org_settings(_ORG_ID, _USER_ID, _CALLER_NAME, sync_code="X" * 51)


@pytest.mark.asyncio
async def test_update_org_settings_pass_code_too_long() -> None:
    svc = _make_service()
    svc.org_settings.get_by_org_id = AsyncMock(return_value=_make_org_settings())

    with pytest.raises(SettingsValidationException, match="pass_code"):
        await svc.update_org_settings(_ORG_ID, _USER_ID, _CALLER_NAME, pass_code="Y" * 21)


@pytest.mark.asyncio
async def test_update_org_settings_writes_audit_log() -> None:
    svc = _make_service()
    svc.org_settings.get_by_org_id = AsyncMock(return_value=_make_org_settings())
    svc.org_settings.update = AsyncMock(return_value=_make_org_settings())

    await svc.update_org_settings(_ORG_ID, _USER_ID, _CALLER_NAME, enable_photo_punch=True)

    svc.audit.record.assert_called_once()
    call_kwargs = svc.audit.record.call_args.kwargs
    assert call_kwargs["module"] == "settings"
    assert call_kwargs["sub_module"] == "organization"
    assert call_kwargs["performed_by_user_id"] == _USER_ID


# ===========================================================================
# 4. reset_org_settings
# ===========================================================================


@pytest.mark.asyncio
async def test_reset_org_settings_success() -> None:
    svc = _make_service()
    reset_row = _make_org_settings()
    svc.org_settings.get_by_org_id = AsyncMock(return_value=_make_org_settings())
    svc.org_settings.reset_to_defaults = AsyncMock(return_value=reset_row)

    result = await svc.reset_org_settings(_ORG_ID, _USER_ID, _CALLER_NAME)

    svc.org_settings.reset_to_defaults.assert_called_once_with(_ORG_ID, updated_by=_USER_ID)
    svc.audit.record.assert_called_once()
    assert result == reset_row


@pytest.mark.asyncio
async def test_reset_org_settings_not_found() -> None:
    svc = _make_service()
    svc.org_settings.get_by_org_id = AsyncMock(return_value=None)

    with pytest.raises(SettingsNotFoundException):
        await svc.reset_org_settings(_ORG_ID, _USER_ID, _CALLER_NAME)


# ===========================================================================
# 5. get_salary_slip_settings
# ===========================================================================


@pytest.mark.asyncio
async def test_get_salary_slip_settings_found() -> None:
    svc = _make_service()
    svc.salary_slip.get_by_org_id = AsyncMock(return_value=_make_slip_settings())

    result = await svc.get_salary_slip_settings(_ORG_ID)
    assert result.company_name == "ACME Corp"


@pytest.mark.asyncio
async def test_get_salary_slip_settings_not_found() -> None:
    svc = _make_service()
    svc.salary_slip.get_by_org_id = AsyncMock(return_value=None)

    with pytest.raises(SettingsNotFoundException):
        await svc.get_salary_slip_settings(_ORG_ID)


# ===========================================================================
# 6. update_salary_slip_settings
# ===========================================================================


@pytest.mark.asyncio
async def test_update_salary_slip_patch_existing() -> None:
    svc = _make_service()
    existing = _make_slip_settings()
    updated = _make_slip_settings(company_name="New Corp")
    svc.salary_slip.get_by_org_id = AsyncMock(return_value=existing)
    svc.salary_slip.update = AsyncMock(return_value=updated)

    result = await svc.update_salary_slip_settings(
        _ORG_ID, _USER_ID, _CALLER_NAME, company_name="New Corp"
    )

    assert result.company_name == "New Corp"
    svc.salary_slip.update.assert_called_once()
    svc.audit.record.assert_called_once()


@pytest.mark.asyncio
async def test_update_salary_slip_upsert_creates_row() -> None:
    svc = _make_service()
    new_row = _make_slip_settings()
    svc.salary_slip.get_by_org_id = AsyncMock(return_value=None)
    svc.salary_slip.create = AsyncMock(return_value=new_row)

    result = await svc.update_salary_slip_settings(
        _ORG_ID,
        _USER_ID,
        _CALLER_NAME,
        company_name="ACME Corp",
        company_address="123 Main St",
        company_contact="9876543210",
    )

    svc.salary_slip.create.assert_called_once()
    assert result.company_name == "ACME Corp"


@pytest.mark.asyncio
async def test_update_salary_slip_upsert_missing_required_field() -> None:
    svc = _make_service()
    svc.salary_slip.get_by_org_id = AsyncMock(return_value=None)

    with pytest.raises(SettingsValidationException, match="company_name"):
        await svc.update_salary_slip_settings(
            _ORG_ID,
            _USER_ID,
            _CALLER_NAME,
            company_address="123 Main St",
            company_contact="9876543210",
        )


@pytest.mark.asyncio
async def test_update_salary_slip_blank_company_name() -> None:
    svc = _make_service()
    svc.salary_slip.get_by_org_id = AsyncMock(return_value=_make_slip_settings())

    with pytest.raises(SettingsValidationException, match="company_name"):
        await svc.update_salary_slip_settings(_ORG_ID, _USER_ID, _CALLER_NAME, company_name="   ")


@pytest.mark.asyncio
async def test_update_salary_slip_company_name_too_long() -> None:
    svc = _make_service()
    svc.salary_slip.get_by_org_id = AsyncMock(return_value=_make_slip_settings())

    with pytest.raises(SettingsValidationException, match="company_name"):
        await svc.update_salary_slip_settings(
            _ORG_ID, _USER_ID, _CALLER_NAME, company_name="A" * 201
        )


@pytest.mark.asyncio
async def test_update_salary_slip_invalid_email() -> None:
    svc = _make_service()
    svc.salary_slip.get_by_org_id = AsyncMock(return_value=_make_slip_settings())

    with patch(
        "app.shared.utils.validators.is_valid_email", return_value=False
    ):
        with pytest.raises(SettingsValidationException, match="email"):
            await svc.update_salary_slip_settings(
                _ORG_ID,
                _USER_ID,
                _CALLER_NAME,
                company_website_email="not@@valid.com",
            )


@pytest.mark.asyncio
async def test_update_salary_slip_valid_email_normalized() -> None:
    svc = _make_service()
    existing = _make_slip_settings()
    updated = _make_slip_settings(company_website_email="info@acme.com")
    svc.salary_slip.get_by_org_id = AsyncMock(return_value=existing)
    svc.salary_slip.update = AsyncMock(return_value=updated)

    with patch(
        "app.shared.utils.validators.is_valid_email", return_value=True
    ):
        await svc.update_salary_slip_settings(
            _ORG_ID,
            _USER_ID,
            _CALLER_NAME,
            company_website_email="INFO@ACME.COM",
        )

    call_data = svc.salary_slip.update.call_args[0][1]
    assert call_data["company_website_email"] == "info@acme.com"


@pytest.mark.asyncio
async def test_update_salary_slip_writes_audit_log() -> None:
    svc = _make_service()
    svc.salary_slip.get_by_org_id = AsyncMock(return_value=_make_slip_settings())
    svc.salary_slip.update = AsyncMock(return_value=_make_slip_settings())

    await svc.update_salary_slip_settings(
        _ORG_ID, _USER_ID, _CALLER_NAME, auto_release_payslip=False
    )

    svc.audit.record.assert_called_once()
    kw = svc.audit.record.call_args.kwargs
    assert kw["sub_module"] == "salary_slip"


# ===========================================================================
# 7. get_features
# ===========================================================================


@pytest.mark.asyncio
async def test_get_features_both_rows_present() -> None:
    svc = _make_service()
    svc.org_settings.get_by_org_id = AsyncMock(
        return_value=_make_org_settings(advance_shift_enabled=True, enable_regularization=True)
    )
    svc.salary_slip.get_by_org_id = AsyncMock(
        return_value=_make_slip_settings(auto_release_payslip=False, branch_wise_payslip=True)
    )

    features = await svc.get_features(_ORG_ID)

    assert features["advance_shift_enabled"] is True
    assert features["enable_regularization"] is True
    assert features["enable_photo_punch"] is False
    assert features["auto_release_payslip"] is False
    assert features["branch_wise_payslip"] is True


@pytest.mark.asyncio
async def test_get_features_absent_rows_default_false() -> None:
    svc = _make_service()
    svc.org_settings.get_by_org_id = AsyncMock(return_value=None)
    svc.salary_slip.get_by_org_id = AsyncMock(return_value=None)

    features = await svc.get_features(_ORG_ID)

    assert features["advance_shift_enabled"] is False
    assert features["auto_release_payslip"] is True  # getattr default True


# ===========================================================================
# 8. set_feature
# ===========================================================================


@pytest.mark.asyncio
async def test_set_feature_org_settings_key() -> None:
    svc = _make_service()
    org_row = _make_org_settings()
    updated_org = _make_org_settings(advance_shift_enabled=True)
    slip_row = _make_slip_settings()

    # get_by_org_id is called twice: inside set_feature then inside get_features
    svc.org_settings.get_by_org_id = AsyncMock(
        side_effect=[org_row, updated_org]
    )
    svc.org_settings.update = AsyncMock(return_value=updated_org)
    svc.salary_slip.get_by_org_id = AsyncMock(return_value=slip_row)

    result = await svc.set_feature(_ORG_ID, _USER_ID, _CALLER_NAME, "advance_shift_enabled", True)

    svc.org_settings.update.assert_called_once()
    svc.audit.record.assert_called_once()
    assert result["advance_shift_enabled"] is True


@pytest.mark.asyncio
async def test_set_feature_salary_slip_key() -> None:
    svc = _make_service()
    org_row = _make_org_settings()
    slip_row = _make_slip_settings()
    updated_slip = _make_slip_settings(branch_wise_payslip=True)

    svc.org_settings.get_by_org_id = AsyncMock(return_value=org_row)
    svc.salary_slip.get_by_org_id = AsyncMock(return_value=slip_row)
    svc.salary_slip.update = AsyncMock(return_value=updated_slip)

    await svc.set_feature(_ORG_ID, _USER_ID, _CALLER_NAME, "branch_wise_payslip", True)

    svc.salary_slip.update.assert_called_once()
    svc.audit.record.assert_called_once()


@pytest.mark.asyncio
async def test_set_feature_unknown_key_raises() -> None:
    svc = _make_service()

    with pytest.raises(UnknownFeatureException, match="unknown_key"):
        await svc.set_feature(_ORG_ID, _USER_ID, _CALLER_NAME, "unknown_key", True)


@pytest.mark.asyncio
async def test_set_feature_org_row_missing_raises() -> None:
    svc = _make_service()
    svc.org_settings.get_by_org_id = AsyncMock(return_value=None)

    with pytest.raises(SettingsNotFoundException):
        await svc.set_feature(_ORG_ID, _USER_ID, _CALLER_NAME, "advance_shift_enabled", True)


@pytest.mark.asyncio
async def test_set_feature_slip_row_missing_raises() -> None:
    svc = _make_service()
    svc.salary_slip.get_by_org_id = AsyncMock(return_value=None)

    with pytest.raises(SettingsNotFoundException):
        await svc.set_feature(_ORG_ID, _USER_ID, _CALLER_NAME, "branch_wise_payslip", False)


@pytest.mark.asyncio
async def test_set_feature_audit_title_reflects_state() -> None:
    svc = _make_service()
    svc.org_settings.get_by_org_id = AsyncMock(return_value=_make_org_settings())
    svc.org_settings.update = AsyncMock(return_value=_make_org_settings())
    svc.salary_slip.get_by_org_id = AsyncMock(return_value=_make_slip_settings())

    await svc.set_feature(_ORG_ID, _USER_ID, _CALLER_NAME, "enable_regularization", False)

    title = svc.audit.record.call_args.kwargs["title"]
    assert "Disabled" in title


# ===========================================================================
# 9. get_settings_history
# ===========================================================================


@pytest.mark.asyncio
async def test_get_settings_history_returns_paginated() -> None:
    svc = _make_service()
    fake_log = SimpleNamespace(id=1, module="settings", title="Updated")
    svc.cross_module.get_settings_history = AsyncMock(return_value=[fake_log])
    svc.cross_module.get_settings_history_count = AsyncMock(return_value=1)

    result = await svc.get_settings_history(_ORG_ID, page=1, page_size=10)

    assert result["total"] == 1
    assert result["items"] == [fake_log]
    assert result["page"] == 1
    assert result["page_size"] == 10


# ===========================================================================
# 10. cross_module_settings_present
# ===========================================================================


@pytest.mark.asyncio
async def test_cross_module_settings_present() -> None:
    svc = _make_service()
    svc.cross_module.attendance_settings_exists = AsyncMock(return_value=True)
    svc.cross_module.payroll_settings_exists = AsyncMock(return_value=False)
    svc.cross_module.leave_settings_exists = AsyncMock(return_value=True)

    result = await svc.cross_module_settings_present(_ORG_ID)

    assert result["attendance"] is True
    assert result["payroll"] is False
    assert result["leave"] is True
