"""Unit tests for ``PayrollService`` business logic (repositories mocked)."""

from __future__ import annotations

from datetime import UTC, date, datetime, time
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.exceptions.base import ConflictException
from app.modules.payroll.constants import (
    AdjustedStatus,
    AdjustmentSource,
    AttendanceMode,
    PaymentStatus,
    PayrollSalaryType,
    PayrollType,
    WorkingHourType,
)
from app.modules.payroll.exceptions import (
    CycleExistsException,
    CycleFinalizedException,
    PayrollAlreadyFinalizedException,
    PayrollGroupInUseException,
    PayrollGroupNameExistsException,
)
from app.modules.payroll.schemas import (
    AttendanceAdjustmentCreateSchema,
    AttendanceAdjustmentExtraHoursCreateSchema,
    AttendanceAdjustmentPenaltyCreateSchema,
    EmployeeGroupAssignRequestSchema,
    PayrollColumnSettingInputSchema,
    PayrollColumnSettingsReplaceSchema,
    PayrollCycleCreateSchema,
    PayrollCycleUpdateSchema,
    PayrollGroupCreateSchema,
    PayrollProcessRequestSchema,
    PayrollSettingUpdateSchema,
    RecordPaymentRequestSchema,
)

_NOW = datetime(2026, 1, 1, tzinfo=UTC)


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
        "employee_id": 5,
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


# Payroll batches are computed by bulk-prefetching every input ONCE for the whole employee
# set, then calculating purely in memory. ``_prefetch_batch_inputs`` issues exactly these
# four ``session.execute`` queries, in this order, no matter how many employees are in the
# run — the other four inputs (assignments, adjustments, penalties, extra hours) come from
# the repositories, which the fixture mocks directly.
def _batch_results(
    att_days: list | None = None,
    leaves: list | None = None,
    loans: list | None = None,
    arrears: list | None = None,
) -> list[MagicMock]:
    return [
        _result(att_days),  # attendance days for the whole cycle
        _result(leaves),  # approved leave requests overlapping the cycle
        _result(loans),  # active loans / advances
        _result(arrears),  # arrears records
    ]


# Every data-access call ``generate_payroll`` can make, so a test can count DB round-trips.
_DB_CALLS: dict[str, tuple[str, ...]] = {
    "assignments": ("get_by_employees", "get_by_employee"),
    "adjustments": ("get_adjustments_for_employees", "search"),
    "penalties": ("get_penalties_for_employees", "get_penalties"),
    "extra_hours": ("get_extra_hours_for_employees", "get_extra_hours_range"),
    "computed_rows": (
        "get_rows_for_cycle",
        "get_row",
        "create",
        "update",
        "bulk_insert_rows",
        "bulk_update_rows",
    ),
}


def _db_round_trips(svc) -> int:
    """Total DB round-trips a run made: raw ``session.execute`` calls + repository calls."""
    total = svc.session.execute.await_count
    for repo_name, methods in _DB_CALLS.items():
        repo = getattr(svc, repo_name)
        total += sum(getattr(repo, method).await_count for method in methods)
    return total


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

    # Collections bulk-prefetched by ``_prefetch_batch_inputs``; default to "nothing recorded".
    svc.assignments.get_by_employees.return_value = [_assignment()]
    svc.adjustments.get_adjustments_for_employees.return_value = []
    svc.penalties.get_penalties_for_employees.return_value = []
    svc.extra_hours.get_extra_hours_for_employees.return_value = []
    svc.computed_rows.get_rows_for_cycle.return_value = []

    # Single-employee reads still used elsewhere in the service.
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
        side_effect=[_result([employee]), *_batch_results(att_days=_FULL_MONTH)]
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
        side_effect=[_result([employee]), *_batch_results(att_days=att)]
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
    payroll_service.computed_rows.get_rows_for_cycle.return_value = []
    payroll_service.session.execute = AsyncMock(
        side_effect=[_result([employee]), *_batch_results(att_days=_FULL_MONTH)]
    )

    res = await payroll_service.generate_payroll(org_id=1, payload=payload, user_id=9)

    assert res.results[0].success is True
    assert res.results[0].employee_id == 5
    # New rows are written with ONE bulk insert carrying every employee's row.
    payroll_service.computed_rows.bulk_insert_rows.assert_awaited_once()
    inserted = payroll_service.computed_rows.bulk_insert_rows.await_args.args[0]
    assert len(inserted) == 1
    persisted = inserted[0]
    assert persisted["gross_wages"] == Decimal("3100.00")
    assert persisted["is_finalized"] is False
    assert persisted["computed_by"] == 9
    payroll_service.audit.record.assert_awaited_once()


async def test_generate_payroll_updates_existing_row_in_bulk(payroll_service) -> None:
    """An existing unfinalized row is refreshed via the bulk UPDATE path, keyed by its id."""
    payload = PayrollProcessRequestSchema(
        payroll_group_id=2,
        cycle_from=date(2026, 1, 1),
        cycle_to=date(2026, 1, 31),
        employee_ids=[5],
    )
    employee = _employee(monthly_salary=Decimal("3100.00"))
    payroll_service.computed_rows.get_rows_for_cycle.return_value = [
        _computed_row(id=10, employee_id=5, is_finalized=False)
    ]
    payroll_service.session.execute = AsyncMock(
        side_effect=[_result([employee]), *_batch_results(att_days=_FULL_MONTH)]
    )

    res = await payroll_service.generate_payroll(org_id=1, payload=payload, user_id=9)

    assert res.results[0].success is True
    payroll_service.computed_rows.bulk_insert_rows.assert_awaited_once_with([])
    payroll_service.computed_rows.bulk_update_rows.assert_awaited_once()
    updated = payroll_service.computed_rows.bulk_update_rows.await_args.args[0]
    assert len(updated) == 1
    assert updated[0]["id"] == 10
    assert updated[0]["gross_wages"] == Decimal("3100.00")


async def test_generate_payroll_skips_finalized_employee(payroll_service) -> None:
    """An already-finalized employee is reported as a failure, not recomputed."""
    payload = PayrollProcessRequestSchema(
        payroll_group_id=2,
        cycle_from=date(2026, 1, 1),
        cycle_to=date(2026, 1, 31),
        employee_ids=[5],
    )
    payroll_service.computed_rows.get_rows_for_cycle.return_value = [
        _computed_row(is_finalized=True)
    ]
    payroll_service.session.execute = AsyncMock(
        side_effect=[_result([_employee()]), *_batch_results()]
    )

    res = await payroll_service.generate_payroll(org_id=1, payload=payload, user_id=9)

    assert res.results[0].success is False
    assert res.results[0].error_code == "PAYROLL_ALREADY_FINALIZED"
    # Nothing persisted: the finalized employee reaches neither the insert nor the update batch.
    payroll_service.computed_rows.create.assert_not_awaited()
    payroll_service.computed_rows.bulk_insert_rows.assert_awaited_once_with([])
    payroll_service.computed_rows.bulk_update_rows.assert_awaited_once_with([])


async def test_recalculate_payroll_raises_when_any_row_finalized(payroll_service) -> None:
    """A finalized row anywhere in the target period aborts the whole recalculation."""
    payload = PayrollProcessRequestSchema(
        payroll_group_id=2,
        cycle_from=date(2026, 1, 1),
        cycle_to=date(2026, 1, 31),
        employee_ids=[5],
    )
    payroll_service.computed_rows.get_rows_for_cycle.return_value = [
        _computed_row(is_finalized=True)
    ]
    payroll_service.session.execute = AsyncMock(
        side_effect=[_result([_employee()]), *_batch_results()]
    )

    with pytest.raises(PayrollAlreadyFinalizedException):
        await payroll_service.recalculate_payroll(org_id=1, payload=payload, user_id=9)

    payroll_service.computed_rows.bulk_insert_rows.assert_not_awaited()
    payroll_service.computed_rows.bulk_update_rows.assert_not_awaited()


async def test_recalculate_payroll_reads_existing_rows_once(payroll_service) -> None:
    """The cycle's existing rows are fetched ONCE.

    The old code read each employee's row twice: once in the finalized-check loop and
    again in the compute loop.
    """
    payload = PayrollProcessRequestSchema(
        payroll_group_id=2,
        cycle_from=date(2026, 1, 1),
        cycle_to=date(2026, 1, 31),
        employee_ids=[5],
    )
    employee = _employee(monthly_salary=Decimal("3100.00"))
    payroll_service.computed_rows.get_rows_for_cycle.return_value = [
        _computed_row(id=10, employee_id=5, is_finalized=False)
    ]
    payroll_service.session.execute = AsyncMock(
        side_effect=[_result([employee]), *_batch_results(att_days=_FULL_MONTH)]
    )

    res = await payroll_service.recalculate_payroll(org_id=1, payload=payload, user_id=9)

    assert res.results[0].success is True
    payroll_service.computed_rows.get_rows_for_cycle.assert_awaited_once()
    payroll_service.computed_rows.get_row.assert_not_awaited()
    updated = payroll_service.computed_rows.bulk_update_rows.await_args.args[0]
    assert updated[0]["gross_wages"] == Decimal("3100.00")


@pytest.mark.parametrize("headcount", [1, 5, 50])
async def test_generate_payroll_query_count_does_not_scale_with_headcount(
    payroll_service, headcount: int
) -> None:
    """Payroll generation must cost a BOUNDED number of DB round-trips.

    The old implementation issued ~11 queries *per employee* (2,206 for a 200-employee
    run). Inputs are now bulk-prefetched once and the computed rows are written with two
    bulk statements, so the total is constant. This test fails loudly if a per-employee
    query ever creeps back into the loop.
    """
    employees = [
        _employee(employee_id=i, monthly_salary=Decimal("3100.00"))
        for i in range(1, headcount + 1)
    ]
    payload = PayrollProcessRequestSchema(
        payroll_group_id=2,
        cycle_from=date(2026, 1, 1),
        cycle_to=date(2026, 1, 31),
        employee_ids=[e.employee_id for e in employees],
    )
    # Every employee has an assignment and a full month of attendance, so each one takes
    # the full compute path rather than short-circuiting on missing data.
    payroll_service.assignments.get_by_employees.return_value = [
        _assignment(id=e.employee_id, employee_id=e.employee_id) for e in employees
    ]
    attendance = [
        _attendance_day(d, employee_id=e.employee_id)
        for e in employees
        for d in range(1, 32)
    ]
    payroll_service.computed_rows.get_rows_for_cycle.return_value = []
    payroll_service.session.execute = AsyncMock(
        side_effect=[_result(employees), *_batch_results(att_days=attendance)]
    )

    res = await payroll_service.generate_payroll(org_id=1, payload=payload, user_id=9)

    # Every employee was computed, and computed correctly.
    assert len(res.results) == headcount
    assert all(item.success for item in res.results)
    inserted = payroll_service.computed_rows.bulk_insert_rows.await_args.args[0]
    assert len(inserted) == headcount
    assert all(row["gross_wages"] == Decimal("3100.00") for row in inserted)

    # ... at a fixed cost: 1 employee select + 8 bulk prefetches + 1 existing-rows read
    # + 2 bulk writes. Bounded, and identical for 1 employee and for 50.
    assert _db_round_trips(payroll_service) == 12


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


# ===========================================================================
# 7. Preview & Serialization tests
# ===========================================================================

async def test_preview_payroll_schema_serialization_null_id(payroll_service) -> None:
    """Verify that a transient preview row (with id=None) serializes correctly using schemas."""
    from app.modules.payroll.schemas import PayrollPreviewResponseSchema, PayrollComputedRowSchema
    from app.modules.payroll.models.run import PayrollComputedRow

    payload = PayrollProcessRequestSchema(
        payroll_group_id=2,
        cycle_from=date(2026, 1, 1),
        cycle_to=date(2026, 1, 31),
        employee_ids=[5],
    )
    employee = _employee(monthly_salary=Decimal("3100.00"))
    payroll_service.session.execute = AsyncMock(
        side_effect=[_result([employee]), *_batch_results(att_days=_FULL_MONTH)]
    )

    rows = await payroll_service.preview_payroll(org_id=1, payload=payload)
    assert len(rows) == 1
    assert rows[0].id is None

    # Validate with Pydantic schema
    schema_row = PayrollComputedRowSchema.model_validate(rows[0])
    assert schema_row.id is None
    assert schema_row.employee_id == 5

    preview_schema = PayrollPreviewResponseSchema(items=rows)
    serialized = preview_schema.model_dump()
    assert len(serialized["items"]) == 1
    assert serialized["items"][0]["id"] is None
    assert serialized["items"][0]["employee_id"] == 5


async def test_preview_payroll_empty(payroll_service) -> None:
    """Verify that previewing payroll with no employees returns an empty list."""
    payload = PayrollProcessRequestSchema(
        payroll_group_id=2,
        cycle_from=date(2026, 1, 1),
        cycle_to=date(2026, 1, 31),
        employee_ids=[],
    )
    # Return no employees matching the group
    payroll_service.session.execute = AsyncMock(
        side_effect=[_result([]), *_batch_results()]
    )

    rows = await payroll_service.preview_payroll(org_id=1, payload=payload)
    assert len(rows) == 0


async def test_preview_payroll_multiple(payroll_service) -> None:
    """Verify that previewing payroll with multiple employees computes correctly for all."""
    payload = PayrollProcessRequestSchema(
        payroll_group_id=2,
        cycle_from=date(2026, 1, 1),
        cycle_to=date(2026, 1, 31),
        employee_ids=[5, 6],
    )
    employee1 = _employee(employee_id=5, monthly_salary=Decimal("3100.00"))
    employee2 = _employee(employee_id=6, monthly_salary=Decimal("6200.00"))
    
    # Mock assignments for both employees
    payroll_service.assignments.get_by_employees.return_value = [
        _assignment(employee_id=5),
        _assignment(employee_id=6),
    ]

    # Mock attendance for both employees
    att_days = (
        [_attendance_day(d, employee_id=5) for d in range(1, 32)] +
        [_attendance_day(d, employee_id=6) for d in range(1, 32)]
    )

    payroll_service.session.execute = AsyncMock(
        side_effect=[
            _result([employee1, employee2]),
            *_batch_results(att_days=att_days)
        ]
    )

    rows = await payroll_service.preview_payroll(org_id=1, payload=payload)
    assert len(rows) == 2
    assert {row.employee_id for row in rows} == {5, 6}
    
    # Check individual computations
    row5 = next(r for r in rows if r.employee_id == 5)
    row6 = next(r for r in rows if r.employee_id == 6)
    
    assert row5.id is None
    assert row5.gross_wages == Decimal("3100.00")
    
    assert row6.id is None
    assert row6.gross_wages == Decimal("6200.00")


async def test_preview_payroll_validation_errors(payroll_service) -> None:
    """Verify that validation errors are handled correctly for preview."""
    from pydantic import ValidationError
    from app.core.exceptions.base import ValidationException

    # 1. Pydantic level validation error (cycle_to before cycle_from)
    with pytest.raises(ValidationError):
        PayrollProcessRequestSchema(
            payroll_group_id=2,
            cycle_from=date(2026, 1, 31),
            cycle_to=date(2026, 1, 1),
            employee_ids=[5],
        )

    # 2. Service level validation (e.g. employee not assigned to payroll group)
    payload = PayrollProcessRequestSchema(
        payroll_group_id=2,
        cycle_from=date(2026, 1, 1),
        cycle_to=date(2026, 1, 31),
        employee_ids=[5],
    )
    employee = _employee(monthly_salary=Decimal("3100.00"))
    
    # Return empty assignment list so _calculate_employee_payroll raises ValidationException
    payroll_service.assignments.get_by_employees.return_value = []
    
    payroll_service.session.execute = AsyncMock(
        side_effect=[_result([employee]), *_batch_results(att_days=_FULL_MONTH)]
    )

    rows = await payroll_service.preview_payroll(org_id=1, payload=payload)
    # The employee should be skipped due to the ValidationException
    assert len(rows) == 0



async def test_finalized_payroll_schema_serialization_id(payroll_service) -> None:
    """Verify that finalized payroll rows (with non-null id) serialize correctly."""
    from app.modules.payroll.schemas import PayrollComputedRowSchema
    from app.modules.payroll.models.run import PayrollComputedRow

    # Create a mock or real DB model instance of a finalized row
    finalized_row = PayrollComputedRow(
        id=123,
        payroll_group_id=2,
        employee_id=5,
        cycle_from=date(2026, 1, 1),
        cycle_to=date(2026, 1, 31),
        total_days=31,
        full_day_count=31,
        half_day_count=0,
        off_day_count=0,
        paid_leave_count=Decimal("0"),
        paid_day_count=Decimal("31"),
        unpaid_day_count=Decimal("0"),
        daily_wage=Decimal("100.00"),
        gross_wages=Decimal("3100.00"),
        overtime_amount=Decimal("0.00"),
        penalties_amount=Decimal("0.00"),
        extras_amount=Decimal("0.00"),
        gross_earnings=Decimal("3100.00"),
        loan_advance_deduction=Decimal("0.00"),
        arrears_amount=Decimal("0.00"),
        to_pay=Decimal("3100.00"),
        balance_arrears=Decimal("0.00"),
        payment_method="bank_transfer",
        is_finalized=True,
        finalized_run_id=45,
        computed_by=9,
        computed_at=datetime.now()
    )

    schema_row = PayrollComputedRowSchema.model_validate(finalized_row)
    assert schema_row.id == 123
    assert schema_row.employee_id == 5
    assert schema_row.is_finalized is True
    assert schema_row.finalized_run_id == 45

