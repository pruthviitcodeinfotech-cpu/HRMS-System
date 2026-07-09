"""Unit tests for ``PayrollService`` business logic (repositories mocked)."""

from __future__ import annotations

from datetime import date, datetime, time, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.core.exceptions.base import ConflictException, NotFoundException, ValidationException
from app.modules.payroll.constants import PaymentStatus, WorkingHourType, AttendanceMode, PayrollType, PayrollSalaryType, AdjustedStatus, AdjustmentSource
from app.modules.payroll.exceptions import (
    PayrollGroupNotFoundException,
    PayrollGroupNameExistsException,
    PayrollGroupInUseException,
    CycleNotFoundException,
    CycleExistsException,
    CycleFinalizedException,
    ComputedRowNotFoundException,
    FinalizedRunNotFoundException,
    PayrollAlreadyFinalizedException,
    PayrollNotFinalizedException,
    AdjustmentNotFoundException,
    AdjustmentExistsException,
    EmployeeNotFoundException,
)
from app.modules.payroll.schemas import (
    PayrollSettingUpdateSchema,
    PayrollGroupCreateSchema,
    PayrollGroupUpdateSchema,
    EmployeeGroupAssignRequestSchema,
    PayrollColumnSettingsReplaceSchema,
    PayrollColumnSettingInputSchema,
    PayrollCycleCreateSchema,
    PayrollCycleUpdateSchema,
    PayrollProcessRequestSchema,
    RecordPaymentRequestSchema,
    AttendanceAdjustmentCreateSchema,
    AttendanceAdjustmentUpdateSchema,
    AttendanceAdjustmentPenaltyCreateSchema,
    AttendanceAdjustmentExtraHoursCreateSchema,
)

_NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------

def _setting(**overrides: object) -> SimpleNamespace:
    base: dict[str, object] = {
        "id": 1,
        "org_id": 1,
        "working_hour_type": WorkingHourType.FIXED.value,
        "full_day_working_hours": time(9, 0),
        "half_day_working_hours": time(4, 30),
        "attendance_mode": AttendanceMode.BIOMETRIC.value,
        "off_day_compensation": "paid",
        "off_day_wage_multiplier": Decimal("1.0"),
        "daily_wage_formula": "calendar_days",
        "overtime_type": "multiplier",
        "overtime_hourly_multiplier": Decimal("1.5"),
        "overtime_buffer_period": time(0, 30),
        "overtime_period_interval": "daily",
        "full_day_penalty_enabled": False,
        "half_day_penalty_enabled": False,
        "late_coming_penalty_enabled": False,
        "grace_time": time(0, 15),
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def _group(**overrides: object) -> SimpleNamespace:
    base: dict[str, object] = {
        "id": 2,
        "org_id": 1,
        "name": "Standard Structure",
        "payroll_type": PayrollType.MONTHLY_WITHOUT_COMPLIANCE.value,
        "is_default": False,
        "is_deleted": False,
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def _employee(**overrides: object) -> SimpleNamespace:
    base: dict[str, object] = {
        "employee_id": 5,
        "org_id": 1,
        "employee_name": "Alice Smith",
        "employee_code": "EMP005",
        "monthly_salary": Decimal("3000.00"),
        "salary_type": "Monthly",
        "payroll_group_id": 2,
        "is_deleted": False,
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def _assignment(**overrides: object) -> SimpleNamespace:
    base: dict[str, object] = {
        "id": 1,
        "employee_id": 5,
        "payroll_group_id": 2,
        "salary_type": PayrollSalaryType.MONTHLY.value,
        "previous_group_id": None,
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def _cycle(**overrides: object) -> SimpleNamespace:
    base: dict[str, object] = {
        "id": 3,
        "payroll_group_id": 2,
        "cycle_date": date(2026, 1, 31),
        "is_finalized": False,
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def _computed_row(**overrides: object) -> SimpleNamespace:
    base: dict[str, object] = {
        "id": 10,
        "payroll_group_id": 2,
        "employee_id": 5,
        "cycle_from": date(2026, 1, 1),
        "cycle_to": date(2026, 1, 31),
        "total_days": 31,
        "full_day_count": 20,
        "half_day_count": 0,
        "off_day_count": 8,
        "paid_leave_count": Decimal("3.0"),
        "paid_day_count": Decimal("31.0"),
        "unpaid_day_count": Decimal("0.0"),
        "daily_wage": Decimal("96.77"),
        "gross_wages": Decimal("3000.00"),
        "overtime_amount": Decimal("0.00"),
        "penalties_amount": Decimal("0.00"),
        "extras_amount": Decimal("0.00"),
        "gross_earnings": Decimal("3000.00"),
        "loan_advance_deduction": Decimal("0.00"),
        "arrears_amount": Decimal("0.00"),
        "to_pay": Decimal("3000.00"),
        "balance_arrears": Decimal("0.00"),
        "payment_method": "bank_transfer",
        "is_finalized": False,
        "finalized_run_id": None,
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def _run(**overrides: object) -> SimpleNamespace:
    base: dict[str, object] = {
        "id": 4,
        "org_id": 1,
        "payroll_group_id": 2,
        "cycle_from": date(2026, 1, 1),
        "cycle_to": date(2026, 1, 31),
        "payroll_module": "core_payroll",
        "finalized_amount": Decimal("3000.00"),
        "finalized_at": _NOW,
        "finalized_by": 9,
        "payment_status": PaymentStatus.PENDING.value,
        "is_definalized": False,
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def _adjustment(**overrides: object) -> SimpleNamespace:
    base: dict[str, object] = {
        "id": 12,
        "org_id": 1,
        "employee_id": 5,
        "attendance_date": date(2026, 1, 15),
        "original_status": AdjustedStatus.A.value,
        "adjusted_status": AdjustedStatus.FD.value,
        "is_forced_overwrite": False,
        "has_punch_error": False,
        "adjustment_source": AdjustmentSource.SPREADSHEET.value,
        "adjusted_by": 9,
        "adjusted_at": _NOW,
    }
    base.update(overrides)
    return SimpleNamespace(**base)


# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------

@pytest.fixture
def payroll_service():
    """A real PayrollService with every repository replaced by AsyncMock."""
    from app.modules.payroll.service import PayrollService

    svc = PayrollService(AsyncMock())
    for attr in (
        "settings",
        "groups",
        "assignments",
        "cycles",
        "columns",
        "runs",
        "computed_rows",
        "adjustments",
        "penalties",
        "extra_hours",
        "employees",
        "users",
        "audit",
    ):
        setattr(svc, attr, AsyncMock())

    # Default mock behavior
    svc.settings.get_by_org.return_value = _setting()
    svc.groups.get_by_id_in_org.return_value = _group()
    svc.groups.name_exists.return_value = False
    svc.employees.get_by_id.return_value = _employee()
    svc.assignments.get_by_employee.return_value = _assignment()
    svc.cycles.get_cycle.return_value = _cycle()
    svc.cycles.get_by_id.return_value = _cycle()
    svc.runs.get_by_id_in_org.return_value = _run()
    svc.computed_rows.get_by_id.return_value = _computed_row()
    svc.adjustments.get_by_id.return_value = _adjustment()
    svc.adjustments.get_adjustment.return_value = None

    return svc


# ===========================================================================
# 1. Configuration tests
# ===========================================================================

async def test_get_settings_existing(payroll_service) -> None:
    res = await payroll_service.get_settings(org_id=1)
    assert res.org_id == 1
    payroll_service.settings.get_by_org.assert_awaited_once_with(1)


async def test_get_settings_create_default(payroll_service) -> None:
    payroll_service.settings.get_by_org.return_value = None
    payroll_service.settings.create.return_value = _setting(org_id=2)
    res = await payroll_service.get_settings(org_id=2)
    assert res.org_id == 2
    payroll_service.settings.create.assert_awaited_once()


async def test_update_settings(payroll_service) -> None:
    payload = PayrollSettingUpdateSchema(full_day_working_hours=time(8, 0))
    await payroll_service.update_settings(org_id=1, payload=payload, user_id=9)
    payroll_service.settings.update.assert_awaited_once()
    payroll_service.audit.record.assert_awaited_once()


# ===========================================================================
# 2. Groups & Column settings tests
# ===========================================================================

async def test_create_group_success(payroll_service) -> None:
    payload = PayrollGroupCreateSchema(name="New Group", payroll_type=PayrollType.MONTHLY_WITHOUT_COMPLIANCE)
    payroll_service.groups.create.return_value = _group(name="New Group")
    res = await payroll_service.create_group(org_id=1, payload=payload, user_id=9)
    assert res.name == "New Group"
    payroll_service.groups.name_exists.assert_awaited_once_with(1, "New Group")


async def test_create_group_name_exists(payroll_service) -> None:
    payroll_service.groups.name_exists.return_value = True
    payload = PayrollGroupCreateSchema(name="Existing Group", payroll_type=PayrollType.MONTHLY_WITHOUT_COMPLIANCE)
    with pytest.raises(PayrollGroupNameExistsException):
        await payroll_service.create_group(org_id=1, payload=payload, user_id=9)


async def test_delete_group_success(payroll_service) -> None:
    # Set queries to mock group not in use
    payroll_service.session.execute = AsyncMock()
    payroll_service.session.execute.return_value.first.return_value = None

    await payroll_service.delete_group(org_id=1, group_id=2, user_id=9)
    payroll_service.groups.update.assert_awaited_once()


async def test_delete_group_in_use(payroll_service) -> None:
    # Mock group in use by employee
    payroll_service.session.execute = AsyncMock()
    payroll_service.session.execute.return_value.first.return_value = (5,)

    with pytest.raises(PayrollGroupInUseException):
        await payroll_service.delete_group(org_id=1, group_id=2, user_id=9)


async def test_assign_group(payroll_service) -> None:
    payload = EmployeeGroupAssignRequestSchema(payroll_group_id=2, salary_type=PayrollSalaryType.MONTHLY)
    payroll_service.assignments.create.return_value = _assignment()
    await payroll_service.assign_group(org_id=1, employee_id=5, payload=payload, user_id=9)
    payroll_service.assignments.get_by_employee.assert_awaited_once_with(5)
    payroll_service.employees.update.assert_awaited_once()


async def test_replace_columns(payroll_service) -> None:
    payload = PayrollColumnSettingsReplaceSchema(
        columns=[
            PayrollColumnSettingInputSchema(column_key="basic", column_label="Basic Pay", is_visible=True, display_order=1)
        ]
    )
    await payroll_service.replace_columns(org_id=1, group_id=2, payload=payload, user_id=9)
    payroll_service.columns.replace_columns.assert_awaited_once()


# ===========================================================================
# 3. Cycles tests
# ===========================================================================

async def test_create_cycle_success(payroll_service) -> None:
    payload = PayrollCycleCreateSchema(payroll_group_id=2, cycle_date=date(2026, 2, 28))
    payroll_service.cycles.get_cycle.return_value = None
    await payroll_service.create_cycle(org_id=1, payload=payload, user_id=9)
    payroll_service.cycles.create.assert_awaited_once()


async def test_create_cycle_exists(payroll_service) -> None:
    payload = PayrollCycleCreateSchema(payroll_group_id=2, cycle_date=date(2026, 1, 31))
    with pytest.raises(CycleExistsException):
        await payroll_service.create_cycle(org_id=1, payload=payload, user_id=9)


async def test_update_cycle_finalized(payroll_service) -> None:
    payroll_service.cycles.get_by_id.return_value = _cycle(is_finalized=True)
    payload = PayrollCycleUpdateSchema(cycle_date=date(2026, 2, 28))
    with pytest.raises(CycleFinalizedException):
        await payroll_service.update_cycle(org_id=1, cycle_id=3, payload=payload, user_id=9)


# ===========================================================================
# 4. Computation, Generate, Finalize & Payments tests
# ===========================================================================

async def test_preview_payroll(payroll_service) -> None:
    payload = PayrollProcessRequestSchema(
        payroll_group_id=2, cycle_from=date(2026, 1, 1), cycle_to=date(2026, 1, 31), employee_ids=[5]
    )
    # Mock sub-repos/session executions
    payroll_service.session.execute = AsyncMock()
    payroll_service.session.execute.return_value.scalars.return_value.all.return_value = []

    res = await payroll_service.preview_payroll(org_id=1, payload=payload)
    assert len(res) == 1
    assert res[0].employee_id == 5
    assert res[0].gross_wages == Decimal("3000.00")


async def test_generate_payroll(payroll_service) -> None:
    payload = PayrollProcessRequestSchema(
        payroll_group_id=2, cycle_from=date(2026, 1, 1), cycle_to=date(2026, 1, 31), employee_ids=[5]
    )
    payroll_service.computed_rows.get_row.return_value = None
    payroll_service.session.execute = AsyncMock()
    payroll_service.session.execute.return_value.scalars.return_value.all.return_value = []

    res = await payroll_service.generate_payroll(org_id=1, payload=payload, user_id=9)
    assert res.results[0].success is True
    payroll_service.computed_rows.create.assert_awaited_once()


async def test_finalize_payroll_success(payroll_service) -> None:
    payload = PayrollProcessRequestSchema(
        payroll_group_id=2, cycle_from=date(2026, 1, 1), cycle_to=date(2026, 1, 31)
    )
    payroll_service.runs.create.return_value = _run()
    payroll_service.computed_rows.get_row.return_value = None

    # mock session execute returns
    mock_exec = AsyncMock()
    mock_exec.scalar_one_or_none.return_value = None
    # comp_rows returns list of unfinalized rows
    mock_exec.scalars.return_value.all.side_effect = [
        [_computed_row(is_finalized=False)], # comp_rows
        [], # loans
    ]
    payroll_service.session.execute = AsyncMock(return_value=mock_exec)

    res = await payroll_service.finalize_payroll(org_id=1, payload=payload, user_id=9)
    assert res.finalized_amount == Decimal("3000.00")
    payroll_service.runs.create.assert_awaited_once()
    payroll_service.computed_rows.update.assert_awaited_once()


async def test_definalize_payroll(payroll_service) -> None:
    payroll_service.runs.get_by_id_in_org.return_value = _run(is_definalized=False)
    mock_exec = AsyncMock()
    mock_exec.scalars.return_value.all.side_effect = [
        [], # loans tx
        [], # arrears tx
        [_computed_row(is_finalized=True)], # comp rows
    ]
    payroll_service.session.execute = AsyncMock(return_value=mock_exec)

    res = await payroll_service.definalize_payroll(org_id=1, run_id=4, user_id=9)
    assert res.is_definalized is True
    payroll_service.runs.update.assert_awaited_once()


async def test_record_payment(payroll_service) -> None:
    payload = RecordPaymentRequestSchema(paid_amount=Decimal("3000.00"), payment_status=PaymentStatus.PAID)
    await payroll_service.record_payment(org_id=1, run_id=4, payload=payload, user_id=9)
    payroll_service.runs.update.assert_awaited_once()


# ===========================================================================
# 5. Payslips & History tests
# ===========================================================================

async def test_view_payslip(payroll_service) -> None:
    res = await payroll_service.view_payslip(org_id=1, row_id=10)
    assert res.row_id == 10
    assert res.net_pay == Decimal("3000.00")


async def test_download_payslip_pdf_finalized(payroll_service) -> None:
    payroll_service.computed_rows.get_by_id.return_value = _computed_row(is_finalized=True)
    res = await payroll_service.download_payslip_pdf(org_id=1, row_id=10)
    assert b"%PDF" in res


async def test_download_payslip_pdf_unfinalized_raises(payroll_service) -> None:
    payroll_service.computed_rows.get_by_id.return_value = _computed_row(is_finalized=False)
    with pytest.raises(ConflictException):
        await payroll_service.download_payslip_pdf(org_id=1, row_id=10)


# ===========================================================================
# 6. Adjustments tests
# ===========================================================================

async def test_add_adjustment(payroll_service) -> None:
    payload = AttendanceAdjustmentCreateSchema(
        employee_id=5, attendance_date=date(2026, 1, 15), adjusted_status=AdjustedStatus.FD
    )
    # mock unfinalized period check
    payroll_service.session.execute = AsyncMock()
    payroll_service.session.execute.return_value.first.return_value = None

    await payroll_service.add_adjustment(org_id=1, payload=payload, user_id=9)
    payroll_service.adjustments.create.assert_awaited_once()


async def test_add_penalty(payroll_service) -> None:
    payload = AttendanceAdjustmentPenaltyCreateSchema(
        employee_id=5, attendance_date=date(2026, 1, 15), penalty_amount=Decimal("50.00")
    )
    payroll_service.session.execute = AsyncMock()
    payroll_service.session.execute.return_value.first.return_value = None

    await payroll_service.add_penalty(org_id=1, payload=payload, user_id=9)
    payroll_service.penalties.create.assert_awaited_once()


async def test_add_extra_hours(payroll_service) -> None:
    payload = AttendanceAdjustmentExtraHoursCreateSchema(
        employee_id=5, attendance_date=date(2026, 1, 15), extra_hours=Decimal("2.5")
    )
    payroll_service.session.execute = AsyncMock()
    payroll_service.session.execute.return_value.first.return_value = None
    payroll_service.extra_hours.get_extra_hours.return_value = None

    await payroll_service.add_extra_hours(org_id=1, payload=payload, user_id=9)
    payroll_service.extra_hours.create.assert_awaited_once()
