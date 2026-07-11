"""Unit tests for ``PayrollService`` business logic (repositories mocked)."""

from __future__ import annotations

from datetime import date, datetime, time, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.exceptions.base import ConflictException, NotFoundException, ValidationException
from app.modules.payroll.constants import (
    PaymentStatus,
    WorkingHourType,
    AttendanceMode,
    PayrollType,
    PayrollSalaryType,
    AdjustedStatus,
    AdjustmentSource,
)
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
        "attendance_mode": AttendanceMode.CONSIDER_ALL_PUNCH.value,
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
        "original_status": AdjustedStatus.ABSENT.value,
        "adjusted_status": AdjustedStatus.FULL_DAY.value,
        "is_forced_overwrite": False,
        "has_punch_error": False,
        "adjustment_source": AdjustmentSource.SPREADSHEET.value,
        "adjusted_by": 9,
        "adjusted_at": _NOW,
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def _attendance_day(day: int, status: str = "present", **overrides: object) -> SimpleNamespace:
    base: dict[str, object] = {
        "attendance_date": date(2026, 1, day),
        "status": status,
        "total_working_minutes": 480,
        "overtime_minutes": 0,
        "late_minutes": 0,
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def _loan(**overrides: object) -> SimpleNamespace:
    base: dict[str, object] = {
        "id": 1,
        "employee_id": 5,
        "monthly_installment": Decimal("100.00"),
        "outstanding_amount": Decimal("500.00"),
        "status": "active",
        "type": "loan",
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def _result(scalars_all: list | None = None, scalar_one: object = None) -> MagicMock:
    """A stand-in for the SQLAlchemy ``Result`` that ``await session.execute()`` returns.

    ``Result`` is synchronous — ``.scalars().all()`` and ``.scalar_one_or_none()`` return
    values directly. Modelling it with an ``AsyncMock`` hands back coroutines, which the
    service then treats as truthy data.
    """
    result = MagicMock()
    result.scalars.return_value.all.return_value = scalars_all if scalars_all is not None else []
    result.scalar_one_or_none.return_value = scalar_one
    return result


# ``_calculate_employee_payroll`` issues exactly four queries per employee, in this order.
def _per_employee_results(
    att_days: list | None = None,
    leaves: list | None = None,
    loans: list | None = None,
    arrears: object = None,
) -> list[MagicMock]:
    return [
        _result(att_days),  # attendance days
        _result(leaves),  # approved leave requests
        _result(loans),  # active loans / advances
        _result(scalar_one=arrears),  # arrears record
    ]


# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------


@pytest.fixture
def payroll_service():
    """A real PayrollService with every repository replaced by AsyncMock."""
    from app.modules.payroll.service import PayrollService

    svc = PayrollService(AsyncMock())
    # `await session.execute(...)` yields a synchronous Result (.scalars()/.first()).
    svc.session.execute = AsyncMock(return_value=MagicMock())
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
        "notifications",
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

    # Collections read by ``_calculate_employee_payroll``; default to "nothing recorded".
    svc.adjustments.search.return_value = []
    svc.penalties.get_penalties.return_value = []
    svc.extra_hours.get_extra_hours_range.return_value = []

    # Finalization notifications: employee 5 resolves to linked user 42 by default.
    svc.notifications.resolve_user_ids_for_employees.return_value = [42]

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
    payload = PayrollGroupCreateSchema(
        name="New Group", payroll_type=PayrollType.MONTHLY_WITHOUT_COMPLIANCE
    )
    payroll_service.groups.create.return_value = _group(name="New Group")
    res = await payroll_service.create_group(org_id=1, payload=payload, user_id=9)
    assert res.name == "New Group"
    payroll_service.groups.name_exists.assert_awaited_once_with(1, "New Group")


async def test_create_group_name_exists(payroll_service) -> None:
    payroll_service.groups.name_exists.return_value = True
    payload = PayrollGroupCreateSchema(
        name="Existing Group", payroll_type=PayrollType.MONTHLY_WITHOUT_COMPLIANCE
    )
    with pytest.raises(PayrollGroupNameExistsException):
        await payroll_service.create_group(org_id=1, payload=payload, user_id=9)


async def test_delete_group_success(payroll_service) -> None:
    # Set queries to mock group not in use
    payroll_service.session.execute = AsyncMock(return_value=MagicMock())
    payroll_service.session.execute.return_value.first.return_value = None

    await payroll_service.delete_group(org_id=1, group_id=2, user_id=9)
    payroll_service.groups.update.assert_awaited_once()


async def test_delete_group_in_use(payroll_service) -> None:
    # Mock group in use by employee
    payroll_service.session.execute = AsyncMock(return_value=MagicMock())
    payroll_service.session.execute.return_value.first.return_value = (5,)

    with pytest.raises(PayrollGroupInUseException):
        await payroll_service.delete_group(org_id=1, group_id=2, user_id=9)


async def test_assign_group(payroll_service) -> None:
    payload = EmployeeGroupAssignRequestSchema(
        payroll_group_id=2, salary_type=PayrollSalaryType.MONTHLY
    )
    payroll_service.assignments.create.return_value = _assignment()
    await payroll_service.assign_group(org_id=1, employee_id=5, payload=payload, user_id=9)
    payroll_service.assignments.get_by_employee.assert_awaited_once_with(5)
    payroll_service.employees.update.assert_awaited_once()


async def test_replace_columns(payroll_service) -> None:
    payload = PayrollColumnSettingsReplaceSchema(
        columns=[
            PayrollColumnSettingInputSchema(
                column_key="basic", column_label="Basic Pay", is_visible=True, display_order=1
            )
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

# A ₹3100 monthly salary over a 31-day cycle gives an exact ₹100.00 daily wage, so the
# expected gross is not obscured by the rounding of ``daily_wage`` to two places.
_FULL_MONTH = [_attendance_day(d) for d in range(1, 32)]


async def test_preview_payroll(payroll_service) -> None:
    payload = PayrollProcessRequestSchema(
        payroll_group_id=2,
        cycle_from=date(2026, 1, 1),
        cycle_to=date(2026, 1, 31),
        employee_ids=[5],
    )
    employee = _employee(monthly_salary=Decimal("3100.00"))
    payroll_service.session.execute = AsyncMock(
        side_effect=[_result([employee]), *_per_employee_results(att_days=_FULL_MONTH)]
    )

    res = await payroll_service.preview_payroll(org_id=1, payload=payload)

    assert len(res) == 1
    row = res[0]
    assert row.employee_id == 5
    assert row.total_days == 31
    assert row.full_day_count == 31
    assert row.paid_day_count == Decimal("31")
    assert row.unpaid_day_count == Decimal("0.0")
    assert row.daily_wage == Decimal("100.00")
    assert row.gross_wages == Decimal("3100.00")
    assert row.gross_earnings == Decimal("3100.00")
    assert row.to_pay == Decimal("3100.00")
    # Preview must not persist anything.
    payroll_service.computed_rows.create.assert_not_awaited()


async def test_preview_payroll_unpaid_days_reduce_gross(payroll_service) -> None:
    """Twenty present days out of a 31-day cycle pays twenty daily wages, not the full month."""
    payload = PayrollProcessRequestSchema(
        payroll_group_id=2,
        cycle_from=date(2026, 1, 1),
        cycle_to=date(2026, 1, 31),
        employee_ids=[5],
    )
    employee = _employee(monthly_salary=Decimal("3100.00"))
    att = [_attendance_day(d) for d in range(1, 21)]
    payroll_service.session.execute = AsyncMock(
        side_effect=[_result([employee]), *_per_employee_results(att_days=att)]
    )

    res = await payroll_service.preview_payroll(org_id=1, payload=payload)

    assert res[0].full_day_count == 20
    assert res[0].paid_day_count == Decimal("20")
    assert res[0].unpaid_day_count == Decimal("11")
    assert res[0].gross_wages == Decimal("2000.00")


async def test_generate_payroll(payroll_service) -> None:
    payload = PayrollProcessRequestSchema(
        payroll_group_id=2,
        cycle_from=date(2026, 1, 1),
        cycle_to=date(2026, 1, 31),
        employee_ids=[5],
    )
    employee = _employee(monthly_salary=Decimal("3100.00"))
    payroll_service.computed_rows.get_row.return_value = None
    payroll_service.session.execute = AsyncMock(
        side_effect=[_result([employee]), *_per_employee_results(att_days=_FULL_MONTH)]
    )

    res = await payroll_service.generate_payroll(org_id=1, payload=payload, user_id=9)

    assert res.results[0].success is True
    assert res.results[0].employee_id == 5
    payroll_service.computed_rows.create.assert_awaited_once()
    persisted = payroll_service.computed_rows.create.await_args.args[0]
    assert persisted["gross_wages"] == Decimal("3100.00")
    assert persisted["is_finalized"] is False
    assert persisted["computed_by"] == 9
    payroll_service.audit.record.assert_awaited_once()


async def test_generate_payroll_skips_finalized_employee(payroll_service) -> None:
    """An already-finalized employee is reported as a failure, not recomputed."""
    payload = PayrollProcessRequestSchema(
        payroll_group_id=2,
        cycle_from=date(2026, 1, 1),
        cycle_to=date(2026, 1, 31),
        employee_ids=[5],
    )
    payroll_service.computed_rows.get_row.return_value = _computed_row(is_finalized=True)
    payroll_service.session.execute = AsyncMock(side_effect=[_result([_employee()])])

    res = await payroll_service.generate_payroll(org_id=1, payload=payload, user_id=9)

    assert res.results[0].success is False
    assert res.results[0].error_code == "PAYROLL_ALREADY_FINALIZED"
    payroll_service.computed_rows.create.assert_not_awaited()


async def test_finalize_payroll_success(payroll_service) -> None:
    payload = PayrollProcessRequestSchema(
        payroll_group_id=2, cycle_from=date(2026, 1, 1), cycle_to=date(2026, 1, 31)
    )
    payroll_service.runs.create.return_value = _run()
    payroll_service.session.execute = AsyncMock(
        side_effect=[
            _result(scalar_one=None),  # no existing finalized run
            _result([_computed_row(is_finalized=False)]),  # computed rows to lock
        ]
    )

    res = await payroll_service.finalize_payroll(org_id=1, payload=payload, user_id=9)

    assert res.finalized_amount == Decimal("3000.00")
    payroll_service.runs.create.assert_awaited_once()
    assert payroll_service.runs.create.await_args.args[0]["finalized_amount"] == Decimal("3000.00")
    payroll_service.computed_rows.update.assert_awaited_once()
    locked = payroll_service.computed_rows.update.await_args.args[1]
    assert locked == {"is_finalized": True, "finalized_run_id": 4}


async def test_finalize_payroll_notifies_affected_employees(payroll_service) -> None:
    """Finalizing emits ONE multi-recipient notification for all affected employees."""
    payload = PayrollProcessRequestSchema(
        payroll_group_id=2, cycle_from=date(2026, 1, 1), cycle_to=date(2026, 1, 31)
    )
    payroll_service.runs.create.return_value = _run()
    payroll_service.session.execute = AsyncMock(
        side_effect=[
            _result(scalar_one=None),  # no existing finalized run
            _result(
                [
                    _computed_row(is_finalized=False, employee_id=5),
                    _computed_row(id=11, is_finalized=False, employee_id=6),
                ]
            ),
        ]
    )
    payroll_service.notifications.resolve_user_ids_for_employees.return_value = [42, 43]

    await payroll_service.finalize_payroll(org_id=1, payload=payload, user_id=9)

    # Users resolved once, for the distinct affected employee ids.
    payroll_service.notifications.resolve_user_ids_for_employees.assert_awaited_once_with(
        1, [5, 6]
    )
    payroll_service.notifications.emit_system_notification.assert_awaited_once()
    kwargs = payroll_service.notifications.emit_system_notification.await_args.kwargs
    assert kwargs["recipient_user_ids"] == [42, 43]
    assert kwargs["notification_type"] == "payroll"
    assert kwargs["source_module"] == "payroll"
    assert kwargs["source_entity_id"] == 4
    assert "finalized" in kwargs["message"]


async def test_finalize_payroll_settles_loan_deduction(payroll_service) -> None:
    """Finalizing debits the employee's active loan and writes a ledger transaction."""
    payload = PayrollProcessRequestSchema(
        payroll_group_id=2, cycle_from=date(2026, 1, 1), cycle_to=date(2026, 1, 31)
    )
    row = _computed_row(
        is_finalized=False,
        loan_advance_deduction=Decimal("100.00"),
        arrears_amount=Decimal("0.00"),
        to_pay=Decimal("2900.00"),
    )
    loan = _loan()
    payroll_service.runs.create.return_value = _run(finalized_amount=Decimal("2900.00"))
    payroll_service.session.add = MagicMock()
    payroll_service.session.execute = AsyncMock(
        side_effect=[
            _result(scalar_one=None),  # no existing finalized run
            _result([row]),  # computed rows
            _result([loan]),  # active loans, ordered by id
            _result(),  # re-load the loan into the session
        ]
    )

    res = await payroll_service.finalize_payroll(org_id=1, payload=payload, user_id=9)

    assert res.finalized_amount == Decimal("2900.00")
    assert loan.outstanding_amount == Decimal("400.00")
    assert loan.status == "active"
    payroll_service.session.add.assert_called_once()
    tx = payroll_service.session.add.call_args.args[0]
    assert tx.amount == Decimal("100.00")
    assert tx.loan_advance_id == loan.id
    assert tx.payroll_run_id == 4


async def test_finalize_payroll_no_rows_conflicts(payroll_service) -> None:
    payload = PayrollProcessRequestSchema(
        payroll_group_id=2, cycle_from=date(2026, 1, 1), cycle_to=date(2026, 1, 31)
    )
    payroll_service.session.execute = AsyncMock(side_effect=[_result(scalar_one=None), _result([])])
    with pytest.raises(ConflictException):
        await payroll_service.finalize_payroll(org_id=1, payload=payload, user_id=9)


async def test_finalize_payroll_existing_run_conflicts(payroll_service) -> None:
    payload = PayrollProcessRequestSchema(
        payroll_group_id=2, cycle_from=date(2026, 1, 1), cycle_to=date(2026, 1, 31)
    )
    payroll_service.session.execute = AsyncMock(side_effect=[_result(scalar_one=_run())])
    with pytest.raises(PayrollAlreadyFinalizedException):
        await payroll_service.finalize_payroll(org_id=1, payload=payload, user_id=9)


async def test_definalize_payroll(payroll_service) -> None:
    payroll_service.runs.get_by_id_in_org.return_value = _run(is_definalized=False)
    payroll_service.runs.update.return_value = _run(is_definalized=True)
    mock_exec = MagicMock()
    mock_exec.scalars.return_value.all.side_effect = [
        [],  # loans tx
        [],  # arrears tx
        [_computed_row(is_finalized=True)],  # comp rows
    ]
    payroll_service.session.execute = AsyncMock(return_value=mock_exec)

    res = await payroll_service.definalize_payroll(org_id=1, run_id=4, user_id=9)
    assert res.is_definalized is True
    payroll_service.runs.update.assert_awaited_once()


async def test_record_payment(payroll_service) -> None:
    payload = RecordPaymentRequestSchema(
        paid_amount=Decimal("3000.00"), payment_status=PaymentStatus.PAID
    )
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
        employee_id=5, attendance_date=date(2026, 1, 15), adjusted_status=AdjustedStatus.FULL_DAY
    )
    # mock unfinalized period check
    payroll_service.session.execute = AsyncMock(return_value=MagicMock())
    payroll_service.session.execute.return_value.first.return_value = None

    await payroll_service.add_adjustment(org_id=1, payload=payload, user_id=9)
    payroll_service.adjustments.create.assert_awaited_once()


async def test_add_penalty(payroll_service) -> None:
    payload = AttendanceAdjustmentPenaltyCreateSchema(
        employee_id=5, attendance_date=date(2026, 1, 15), penalty_amount=Decimal("50.00")
    )
    payroll_service.session.execute = AsyncMock(return_value=MagicMock())
    payroll_service.session.execute.return_value.first.return_value = None

    await payroll_service.add_penalty(org_id=1, payload=payload, user_id=9)
    payroll_service.penalties.create.assert_awaited_once()


async def test_add_extra_hours(payroll_service) -> None:
    payload = AttendanceAdjustmentExtraHoursCreateSchema(
        employee_id=5, attendance_date=date(2026, 1, 15), extra_hours=Decimal("2.5")
    )
    payroll_service.session.execute = AsyncMock(return_value=MagicMock())
    payroll_service.session.execute.return_value.first.return_value = None
    payroll_service.extra_hours.get_extra_hours.return_value = None

    await payroll_service.add_extra_hours(org_id=1, payload=payload, user_id=9)
    payroll_service.extra_hours.create.assert_awaited_once()
