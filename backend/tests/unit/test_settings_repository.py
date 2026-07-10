"""Unit tests for Settings Management Repository layer."""

from __future__ import annotations

import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.modules.settings.repository import (
    OrgSalarySlipSettingsRepository,
    OrgSettingsRepository,
    SettingsCrossModuleRepository,
)

_ORG_ID = 10
_NOW = datetime.datetime(2026, 7, 10, 10, 0, 0, tzinfo=datetime.timezone.utc)  # noqa: UP017


def _mock_scalar(value) -> MagicMock:
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    return result


def _mock_session() -> AsyncMock:
    """An ``AsyncSession`` double whose synchronous methods stay synchronous.

    ``AsyncSession.add`` is not a coroutine; leaving it as an ``AsyncMock`` child makes
    the repository schedule a coroutine it never awaits.
    """
    session = AsyncMock()
    session.add = MagicMock()
    return session


# ===========================================================================
# 1. OrgSettingsRepository
# ===========================================================================


@pytest.mark.asyncio
async def test_org_settings_get_by_org_id_found() -> None:
    session = _mock_session()
    from app.modules.settings.models import OrgSettings

    row = OrgSettings(id=1, org_id=_ORG_ID)
    session.execute.return_value = _mock_scalar(row)

    repo = OrgSettingsRepository(session)
    result = await repo.get_by_org_id(_ORG_ID)

    assert result == row
    session.execute.assert_called_once()


@pytest.mark.asyncio
async def test_org_settings_get_by_org_id_not_found() -> None:
    session = _mock_session()
    session.execute.return_value = _mock_scalar(None)

    repo = OrgSettingsRepository(session)
    result = await repo.get_by_org_id(_ORG_ID)

    assert result is None


@pytest.mark.asyncio
async def test_org_settings_exists_in_org_true() -> None:
    session = _mock_session()
    mock_result = MagicMock()
    mock_result.first.return_value = (1,)
    session.execute.return_value = mock_result

    repo = OrgSettingsRepository(session)
    result = await repo.exists_in_org(_ORG_ID)

    assert result is True


@pytest.mark.asyncio
async def test_org_settings_exists_in_org_false() -> None:
    session = _mock_session()
    mock_result = MagicMock()
    mock_result.first.return_value = None
    session.execute.return_value = mock_result

    repo = OrgSettingsRepository(session)
    result = await repo.exists_in_org(_ORG_ID)

    assert result is False


@pytest.mark.asyncio
async def test_org_settings_search_applies_filters() -> None:
    session = _mock_session()
    from app.modules.settings.models import OrgSettings

    row = OrgSettings(id=1, org_id=_ORG_ID, advance_shift_enabled=True)
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [row]
    session.execute.return_value = mock_result

    repo = OrgSettingsRepository(session)
    results = await repo.search(_ORG_ID, advance_shift_enabled=True)

    assert results == [row]
    session.execute.assert_called_once()


@pytest.mark.asyncio
async def test_org_settings_reset_to_defaults_row_exists() -> None:
    session = _mock_session()
    from app.modules.settings.models import OrgSettings

    row = OrgSettings(
        id=1,
        org_id=_ORG_ID,
        advance_shift_enabled=True,
        enable_regularization=True,
        enable_photo_punch=True,
        device_sync_time=datetime.time(9, 0, 0),
        sync_code="OLD",
        pass_code="OLD",
    )
    # First call (get_by_org_id inside reset_to_defaults) returns the row
    mock_result = _mock_scalar(row)
    session.execute.return_value = mock_result
    # flush and refresh are noops
    session.flush = AsyncMock()
    session.refresh = AsyncMock()

    repo = OrgSettingsRepository(session)
    result = await repo.reset_to_defaults(_ORG_ID, updated_by=99)

    assert result is not None
    assert result.advance_shift_enabled is False
    assert result.enable_regularization is False
    assert result.device_sync_time == datetime.time(16, 51, 0)
    # Sensitive codes untouched
    assert result.sync_code == "OLD"
    assert result.pass_code == "OLD"


@pytest.mark.asyncio
async def test_org_settings_reset_to_defaults_row_missing() -> None:
    session = _mock_session()
    session.execute.return_value = _mock_scalar(None)

    repo = OrgSettingsRepository(session)
    result = await repo.reset_to_defaults(_ORG_ID, updated_by=99)

    assert result is None


# ===========================================================================
# 2. OrgSalarySlipSettingsRepository
# ===========================================================================


@pytest.mark.asyncio
async def test_salary_slip_get_by_org_id_found() -> None:
    session = _mock_session()
    from app.modules.settings.models import OrgSalarySlipSettings

    row = OrgSalarySlipSettings(id=2, org_id=_ORG_ID, company_name="ACME")
    session.execute.return_value = _mock_scalar(row)

    repo = OrgSalarySlipSettingsRepository(session)
    result = await repo.get_by_org_id(_ORG_ID)

    assert result == row


@pytest.mark.asyncio
async def test_salary_slip_get_by_org_id_not_found() -> None:
    session = _mock_session()
    session.execute.return_value = _mock_scalar(None)

    repo = OrgSalarySlipSettingsRepository(session)
    result = await repo.get_by_org_id(_ORG_ID)

    assert result is None


@pytest.mark.asyncio
async def test_salary_slip_exists_in_org_true() -> None:
    session = _mock_session()
    mock_result = MagicMock()
    mock_result.first.return_value = (1,)
    session.execute.return_value = mock_result

    repo = OrgSalarySlipSettingsRepository(session)
    result = await repo.exists_in_org(_ORG_ID)

    assert result is True


@pytest.mark.asyncio
async def test_salary_slip_exists_in_org_false() -> None:
    session = _mock_session()
    mock_result = MagicMock()
    mock_result.first.return_value = None
    session.execute.return_value = mock_result

    repo = OrgSalarySlipSettingsRepository(session)
    result = await repo.exists_in_org(_ORG_ID)

    assert result is False


# ===========================================================================
# 3. SettingsCrossModuleRepository
# ===========================================================================


@pytest.mark.asyncio
async def test_cross_module_exists_true() -> None:
    session = _mock_session()
    mock_result = MagicMock()
    mock_result.first.return_value = (1,)
    session.execute.return_value = mock_result

    repo = SettingsCrossModuleRepository(session)
    result = await repo.cross_module_exists("payroll_settings", _ORG_ID)

    assert result is True


@pytest.mark.asyncio
async def test_cross_module_exists_false() -> None:
    session = _mock_session()
    mock_result = MagicMock()
    mock_result.first.return_value = None
    session.execute.return_value = mock_result

    repo = SettingsCrossModuleRepository(session)
    result = await repo.cross_module_exists("leave_settings", _ORG_ID)

    assert result is False


@pytest.mark.asyncio
async def test_attendance_settings_exists_delegates() -> None:
    session = _mock_session()
    mock_result = MagicMock()
    mock_result.first.return_value = (1,)
    session.execute.return_value = mock_result

    repo = SettingsCrossModuleRepository(session)
    result = await repo.attendance_settings_exists(_ORG_ID)

    assert result is True
    # Verify the SQL text contained the correct table
    stmt_text = str(session.execute.call_args[0][0])
    assert "org_attendance_settings" in stmt_text


@pytest.mark.asyncio
async def test_payroll_settings_exists_delegates() -> None:
    session = _mock_session()
    mock_result = MagicMock()
    mock_result.first.return_value = None
    session.execute.return_value = mock_result

    repo = SettingsCrossModuleRepository(session)
    result = await repo.payroll_settings_exists(_ORG_ID)

    assert result is False
    stmt_text = str(session.execute.call_args[0][0])
    assert "payroll_settings" in stmt_text


@pytest.mark.asyncio
async def test_leave_settings_exists_delegates() -> None:
    session = _mock_session()
    mock_result = MagicMock()
    mock_result.first.return_value = (1,)
    session.execute.return_value = mock_result

    repo = SettingsCrossModuleRepository(session)
    result = await repo.leave_settings_exists(_ORG_ID)

    assert result is True
    stmt_text = str(session.execute.call_args[0][0])
    assert "leave_settings" in stmt_text


@pytest.mark.asyncio
async def test_get_settings_history_paginated() -> None:
    session = _mock_session()
    from app.modules.audit.models import ActivityLog

    log = ActivityLog(
        id=1,
        org_id=_ORG_ID,
        module="settings",
        title="Settings Updated",
        description="Some change",
        action_type="Update",
        performed_by_name="Admin",
        log_date=_NOW.date(),
        log_time=_NOW.time(),
    )
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [log]
    session.execute.return_value = mock_result

    repo = SettingsCrossModuleRepository(session)
    results = await repo.get_settings_history(_ORG_ID, page=1, page_size=10)

    assert results == [log]


@pytest.mark.asyncio
async def test_get_settings_history_count() -> None:
    session = _mock_session()
    mock_result = MagicMock()
    mock_result.scalar_one.return_value = 5
    session.execute.return_value = mock_result

    repo = SettingsCrossModuleRepository(session)
    count = await repo.get_settings_history_count(_ORG_ID)

    assert count == 5
