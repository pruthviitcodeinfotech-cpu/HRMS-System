"""Unit tests for ``ShiftService`` business logic (repositories mocked).

Covers shift CRUD, shift assignment (supersession + validation), shift rotation
(roster generation), shift resolution, weekly-off configuration, search/pagination,
and the conflict / not-found / validation failure paths. All data access is mocked,
so these exercise the service logic in isolation.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.core.exceptions.base import (
    ConflictException,
    NotFoundException,
    ValidationException,
)
from app.modules.shift.schemas import (
    ShiftAssignRequest,
    ShiftAssignmentQuery,
    ShiftCreateRequest,
    ShiftDayTimingInput,
    ShiftResolveQuery,
    ShiftRotationRequest,
    ShiftUpdateRequest,
    WeeklyOffQuery,
    WeeklyOffUpdateRequest,
)

_NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------


def _shift(**overrides: object) -> SimpleNamespace:
    base: dict[str, object] = {
        "shift_id": 1,
        "org_id": 1,
        "shift_name": "Morning",
        "shift_type": "fixed",
        "is_open_shift": False,
        "is_default": False,
        "is_uniform_time": True,
        "has_break_time": False,
        "shift_color": "#fff",
        "remark": None,
        "is_advanced_mode": False,
        "is_deleted": False,
        "created_by": 1,
        "created_at": _NOW,
        "updated_at": _NOW,
        "day_timings": [],
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def _employee(**overrides: object) -> SimpleNamespace:
    base: dict[str, object] = {
        "employee_id": 5,
        "org_id": 1,
        "employee_name": "Jane Doe",
        "date_of_joining": date(2026, 1, 1),
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def _assignment(**overrides: object) -> SimpleNamespace:
    base: dict[str, object] = {
        "assignment_id": 1,
        "org_id": 1,
        "employee_id": 5,
        "shift_id": 1,
        "effective_from": date(2026, 2, 1),
        "effective_to": None,
        "assigned_by": 9,
        "created_at": _NOW,
        "updated_at": _NOW,
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def _weekoff(**overrides: object) -> SimpleNamespace:
    base: dict[str, object] = {
        "weekoff_id": 1,
        "employee_id": 5,
        "day_of_week": 0,
        "weekoff_type": "week_off",
        "occurrence_1st": True,
        "occurrence_2nd": True,
        "occurrence_3rd": True,
        "occurrence_4th": True,
        "occurrence_5th": True,
        "effective_from": None,
        "effective_to": None,
        "updated_by": 9,
        "updated_at": _NOW,
        "created_at": _NOW,
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def _roster(**overrides: object) -> SimpleNamespace:
    base: dict[str, object] = {
        "roster_id": 1,
        "org_id": 1,
        "employee_id": 5,
        "roster_date": date(2026, 2, 1),
        "shift_id": 1,
        "is_week_off": False,
        "created_by": 9,
        "updated_by": 9,
        "created_at": _NOW,
        "updated_at": _NOW,
    }
    base.update(overrides)
    return SimpleNamespace(**base)


@pytest.fixture
def shift_service():
    """A real :class:`ShiftService` with every repository replaced by an ``AsyncMock``."""
    from app.modules.shift.service import ShiftService

    svc = ShiftService(AsyncMock())
    for attr in (
        "shifts",
        "day_timings",
        "assignments",
        "rosters",
        "weekoffs",
        "employees",
        "branches",
        "departments",
        "users",
        "audit",
    ):
        setattr(svc, attr, AsyncMock())
    # Sensible defaults.
    svc.shifts.name_exists.return_value = False
    svc.shifts.get_active_by_id.return_value = _shift()
    svc.shifts.get_detail.return_value = _shift()
    svc.shifts.has_open_assignments.return_value = False
    svc.shifts.exists_in_org.return_value = True
    svc.shifts.create.return_value = _shift()
    svc.shifts.search.return_value = []
    svc.shifts.search_count.return_value = 0
    svc.assignments.exists_on_effective_from.return_value = False
    svc.assignments.get_open_for_employee.return_value = None
    svc.assignments.resolve_for_date.return_value = None
    svc.assignments.create.return_value = _assignment()
    svc.employees.get_active_by_id.return_value = _employee()
    svc.branches.exists_active.return_value = True
    svc.departments.exists_active.return_value = True
    svc.weekoffs.get_active_for_day.return_value = None
    svc.weekoffs.create.return_value = _weekoff()
    svc.weekoffs.list_for_employee.return_value = []
    svc.weekoffs.list_for_employees.return_value = []
    svc.weekoffs.active_for_day_by_employees.return_value = []
    svc.weekoffs.close_by_ids.return_value = 0
    svc.weekoffs.bulk_create.return_value = [_weekoff()]
    svc.rosters.bulk_create.return_value = [_roster(), _roster(roster_id=2)]
    svc.users.get_active_by_id.return_value = SimpleNamespace(name="Admin")
    return svc


def _create_payload(**overrides: object) -> ShiftCreateRequest:
    base: dict[str, object] = {"shift_name": "Morning"}
    base.update(overrides)
    return ShiftCreateRequest(**base)


# ===========================================================================
# Shift CRUD
# ===========================================================================
async def test_create_shift_success(shift_service) -> None:
    result = await shift_service.create_shift(
        org_id=1, actor_id=9, data=_create_payload()
    )
    assert result.shift_name == "Morning"
    shift_service.shifts.create.assert_awaited_once()
    shift_service.audit.record.assert_awaited_once()


async def test_create_shift_duplicate_name(shift_service) -> None:
    shift_service.shifts.name_exists.return_value = True
    with pytest.raises(ConflictException) as exc:
        await shift_service.create_shift(org_id=1, actor_id=9, data=_create_payload())
    assert exc.value.code == "duplicate_shift_name"


async def test_create_shift_persists_day_timings(shift_service) -> None:
    data = _create_payload(
        day_timings=[ShiftDayTimingInput(start_time="09:00", end_time="18:00")]
    )
    await shift_service.create_shift(org_id=1, actor_id=9, data=data)
    shift_service.day_timings.create.assert_awaited_once()


async def test_update_shift_success(shift_service) -> None:
    result = await shift_service.update_shift(
        org_id=1, actor_id=9, shift_id=1, data=ShiftUpdateRequest(shift_name="Evening")
    )
    assert result.shift_id == 1
    shift_service.shifts.update.assert_awaited_once()


async def test_update_shift_not_found(shift_service) -> None:
    shift_service.shifts.get_active_by_id.return_value = None
    with pytest.raises(NotFoundException) as exc:
        await shift_service.update_shift(
            org_id=1, actor_id=9, shift_id=404, data=ShiftUpdateRequest(shift_name="X")
        )
    assert exc.value.code == "not_found"


async def test_update_shift_duplicate_name(shift_service) -> None:
    shift_service.shifts.get_active_by_id.return_value = _shift(shift_name="Old")
    shift_service.shifts.name_exists.return_value = True
    with pytest.raises(ConflictException) as exc:
        await shift_service.update_shift(
            org_id=1, actor_id=9, shift_id=1, data=ShiftUpdateRequest(shift_name="New")
        )
    assert exc.value.code == "duplicate_shift_name"


async def test_update_shift_replaces_day_timings(shift_service) -> None:
    data = ShiftUpdateRequest(day_timings=[ShiftDayTimingInput(start_time="09:00", end_time="17:00")])
    await shift_service.update_shift(org_id=1, actor_id=9, shift_id=1, data=data)
    shift_service.day_timings.delete_all_for_shift.assert_awaited_once()
    shift_service.day_timings.create.assert_awaited_once()


async def test_get_shift_not_found(shift_service) -> None:
    shift_service.shifts.get_detail.return_value = None
    with pytest.raises(NotFoundException):
        await shift_service.get_shift(org_id=1, shift_id=404)


async def test_delete_shift_success(shift_service) -> None:
    await shift_service.delete_shift(org_id=1, actor_id=9, shift_id=1)
    shift_service.shifts.soft_delete.assert_awaited_once()
    shift_service.audit.record.assert_awaited_once()


async def test_delete_shift_in_use(shift_service) -> None:
    shift_service.shifts.has_open_assignments.return_value = True
    with pytest.raises(ConflictException) as exc:
        await shift_service.delete_shift(org_id=1, actor_id=9, shift_id=1)
    assert exc.value.code == "shift_in_use"


# ===========================================================================
# Search / pagination
# ===========================================================================
async def test_list_shifts_pagination(shift_service) -> None:
    shift_service.shifts.search.return_value = [_shift()]
    shift_service.shifts.search_count.return_value = 1
    result = await shift_service.list_shifts(
        org_id=1, search="morn", shift_type="fixed", page=2, page_size=10
    )
    assert result.pagination.page == 2
    assert result.pagination.total_records == 1
    assert len(result.items) == 1
    kwargs = shift_service.shifts.search.await_args.kwargs
    assert kwargs["search"] == "morn"
    assert kwargs["shift_type"] == "fixed"


# ===========================================================================
# Shift assignment
# ===========================================================================
async def test_assign_shift_success(shift_service) -> None:
    data = ShiftAssignRequest(employee_id=5, effective_from=date(2026, 2, 1))
    result = await shift_service.assign_shift(org_id=1, actor_id=9, shift_id=1, data=data)
    assert result.assignment_id == 1
    shift_service.assignments.create.assert_awaited_once()
    shift_service.audit.record.assert_awaited_once()


async def test_assign_shift_shift_not_found(shift_service) -> None:
    shift_service.shifts.get_active_by_id.return_value = None
    data = ShiftAssignRequest(employee_id=5, effective_from=date(2026, 2, 1))
    with pytest.raises(NotFoundException):
        await shift_service.assign_shift(org_id=1, actor_id=9, shift_id=404, data=data)


async def test_assign_shift_employee_not_found(shift_service) -> None:
    shift_service.employees.get_active_by_id.return_value = None
    data = ShiftAssignRequest(employee_id=404, effective_from=date(2026, 2, 1))
    with pytest.raises(NotFoundException):
        await shift_service.assign_shift(org_id=1, actor_id=9, shift_id=1, data=data)


async def test_assign_shift_before_joining_date(shift_service) -> None:
    shift_service.employees.get_active_by_id.return_value = _employee(
        date_of_joining=date(2026, 3, 1)
    )
    data = ShiftAssignRequest(employee_id=5, effective_from=date(2026, 2, 1))
    with pytest.raises(ValidationException) as exc:
        await shift_service.assign_shift(org_id=1, actor_id=9, shift_id=1, data=data)
    assert exc.value.code == "invalid_assignment_date"


async def test_assign_shift_duplicate_same_date(shift_service) -> None:
    shift_service.assignments.exists_on_effective_from.return_value = True
    data = ShiftAssignRequest(employee_id=5, effective_from=date(2026, 2, 1))
    with pytest.raises(ConflictException) as exc:
        await shift_service.assign_shift(org_id=1, actor_id=9, shift_id=1, data=data)
    assert exc.value.code == "duplicate_assignment"


async def test_assign_shift_supersedes_prior(shift_service) -> None:
    """The prior open assignment is closed the day before the new one begins."""
    shift_service.assignments.get_open_for_employee.return_value = _assignment(
        assignment_id=99, effective_from=date(2026, 1, 1)
    )
    data = ShiftAssignRequest(employee_id=5, effective_from=date(2026, 2, 1))
    await shift_service.assign_shift(org_id=1, actor_id=9, shift_id=1, data=data)
    prior_update = shift_service.assignments.update.await_args
    assert prior_update.args[1]["effective_to"] == date(2026, 1, 31)


async def test_list_assignments_requires_employee_id(shift_service) -> None:
    with pytest.raises(ValidationException) as exc:
        await shift_service.list_assignments(org_id=1, query=ShiftAssignmentQuery())
    assert exc.value.code == "validation_error"


async def test_list_assignments_timeline(shift_service) -> None:
    shift_service.assignments.list_for_employee.return_value = [_assignment()]
    shift_service.assignments.count_for_employee.return_value = 1
    result = await shift_service.list_assignments(
        org_id=1, query=ShiftAssignmentQuery(employee_id=5)
    )
    assert result.pagination.total_records == 1
    assert len(result.items) == 1


async def test_list_assignments_resolved_for_date(shift_service) -> None:
    shift_service.assignments.resolve_for_date.return_value = _assignment()
    query = ShiftAssignmentQuery(employee_id=5, on_date=date(2026, 2, 15))
    result = await shift_service.list_assignments(org_id=1, query=query)
    assert len(result.items) == 1
    shift_service.assignments.resolve_for_date.assert_awaited_once()


# ===========================================================================
# Shift resolution
# ===========================================================================
async def test_resolve_shift_working_day(shift_service) -> None:
    shift_service.assignments.resolve_for_date.return_value = _assignment()
    shift_service.weekoffs.get_active_for_day.return_value = None
    result = await shift_service.resolve_shift(
        org_id=1, query=ShiftResolveQuery(employee_id=5, on_date=date(2026, 3, 2))
    )
    assert result.shift is not None
    assert result.is_weekly_off is False
    assert result.is_working_day is True


async def test_resolve_shift_non_working_timing(shift_service) -> None:
    """Max fidelity: a shift day-timing marking the weekday non-working sets is_working_day=False."""
    # 2026-03-02 is a Monday -> weekday ordinal 1.
    shift_service.assignments.resolve_for_date.return_value = _assignment()
    shift_service.shifts.get_detail.return_value = _shift(
        day_timings=[SimpleNamespace(day_of_week=1, is_working_day=False)]
    )
    shift_service.weekoffs.get_active_for_day.return_value = None
    result = await shift_service.resolve_shift(
        org_id=1, query=ShiftResolveQuery(employee_id=5, on_date=date(2026, 3, 2))
    )
    assert result.is_weekly_off is False
    assert result.is_working_day is False


async def test_resolve_shift_weekly_off(shift_service) -> None:
    shift_service.assignments.resolve_for_date.return_value = None
    shift_service.weekoffs.get_active_for_day.return_value = _weekoff(weekoff_type="week_off")
    result = await shift_service.resolve_shift(
        org_id=1, query=ShiftResolveQuery(employee_id=5, on_date=date(2026, 3, 1))
    )
    assert result.is_weekly_off is True
    assert result.is_working_day is False
    assert result.shift is None


async def test_resolve_shift_occasional_weekoff_second_sunday(shift_service) -> None:
    """2026-03-08 is the 2nd Sunday; occurrence_2nd=True → it is a week-off."""
    shift_service.assignments.resolve_for_date.return_value = None
    shift_service.weekoffs.get_active_for_day.return_value = _weekoff(
        weekoff_type="occasional_week_off",
        occurrence_1st=False,
        occurrence_2nd=True,
        occurrence_3rd=False,
        occurrence_4th=False,
        occurrence_5th=False,
    )
    result = await shift_service.resolve_shift(
        org_id=1, query=ShiftResolveQuery(employee_id=5, on_date=date(2026, 3, 8))
    )
    assert result.is_weekly_off is True


async def test_resolve_shift_employee_not_found(shift_service) -> None:
    shift_service.employees.get_active_by_id.return_value = None
    with pytest.raises(NotFoundException):
        await shift_service.resolve_shift(
            org_id=1, query=ShiftResolveQuery(employee_id=404, on_date=date(2026, 3, 1))
        )


# ===========================================================================
# Shift rotation
# ===========================================================================
async def test_generate_rotation_success(shift_service) -> None:
    data = ShiftRotationRequest(
        name="Rot",
        cadence="daily",
        shift_sequence=[1, 2],
        start_date=date(2026, 2, 1),
        horizon_days=3,
        group_scope={"employee_ids": [5]},
    )
    result = await shift_service.generate_rotation(org_id=1, actor_id=9, data=data)
    assert result.generated_count == 2
    assert len(result.generated_assignments) == 2
    shift_service.rosters.bulk_create.assert_awaited_once()
    shift_service.audit.record.assert_awaited_once()


async def test_generate_rotation_respects_weekly_off(shift_service) -> None:
    """A rotation date on the employee's active week-off is marked off with no shift."""
    # 2026-02-01 is a Sunday -> weekday ordinal 0; configure that day as a week-off.
    shift_service.weekoffs.list_for_employees.return_value = [
        _weekoff(employee_id=5, day_of_week=0, weekoff_type="week_off")
    ]
    data = ShiftRotationRequest(
        name="Rot",
        cadence="daily",
        shift_sequence=[1, 2],
        start_date=date(2026, 2, 1),
        horizon_days=3,
        group_scope={"employee_ids": [5]},
    )
    await shift_service.generate_rotation(org_id=1, actor_id=9, data=data)
    rows = shift_service.rosters.bulk_create.await_args.args[0]
    sunday_row = next(r for r in rows if r["roster_date"] == date(2026, 2, 1))
    assert sunday_row["is_week_off"] is True
    assert sunday_row["shift_id"] is None
    # A non-week-off day still gets a shift.
    monday_row = next(r for r in rows if r["roster_date"] == date(2026, 2, 2))
    assert monday_row["is_week_off"] is False
    assert monday_row["shift_id"] is not None


async def test_generate_rotation_invalid_shift(shift_service) -> None:
    shift_service.shifts.exists_in_org.return_value = False
    data = ShiftRotationRequest(
        name="Rot",
        cadence="daily",
        shift_sequence=[999],
        start_date=date(2026, 2, 1),
        horizon_days=3,
        group_scope={"employee_ids": [5]},
    )
    with pytest.raises(ValidationException) as exc:
        await shift_service.generate_rotation(org_id=1, actor_id=9, data=data)
    assert exc.value.code == "invalid_shift"


async def test_generate_rotation_empty_scope(shift_service) -> None:
    data = ShiftRotationRequest(
        name="Rot",
        cadence="daily",
        shift_sequence=[1],
        start_date=date(2026, 2, 1),
        horizon_days=3,
        group_scope={},
    )
    with pytest.raises(ValidationException) as exc:
        await shift_service.generate_rotation(org_id=1, actor_id=9, data=data)
    assert exc.value.code == "empty_rotation_scope"


# ===========================================================================
# Weekly offs
# ===========================================================================
async def test_get_weekly_offs_for_employee(shift_service) -> None:
    shift_service.weekoffs.list_for_employee.return_value = [_weekoff()]
    result = await shift_service.get_weekly_offs(
        org_id=1, query=WeeklyOffQuery(employee_id=5)
    )
    assert len(result.items) == 1


async def test_get_weekly_offs_employee_not_found(shift_service) -> None:
    shift_service.employees.get_active_by_id.return_value = None
    with pytest.raises(NotFoundException):
        await shift_service.get_weekly_offs(org_id=1, query=WeeklyOffQuery(employee_id=404))


async def test_set_weekly_off_for_employee(shift_service) -> None:
    data = WeeklyOffUpdateRequest(employee_id=5, day_of_week=0, weekoff_type="week_off")
    result = await shift_service.set_weekly_off(org_id=1, actor_id=9, data=data)
    assert result.weekoff_id == 1
    shift_service.weekoffs.create.assert_awaited_once()
    shift_service.audit.record.assert_awaited_once()


async def test_set_weekly_off_closes_existing(shift_service) -> None:
    shift_service.weekoffs.get_active_for_day.return_value = _weekoff()
    data = WeeklyOffUpdateRequest(
        employee_id=5, day_of_week=0, weekoff_type="week_off", effective_from=date(2026, 3, 1)
    )
    await shift_service.set_weekly_off(org_id=1, actor_id=9, data=data)
    closed = shift_service.weekoffs.update.await_args
    assert closed.args[1]["effective_to"] == date(2026, 2, 28)


async def test_set_weekly_off_department_bulk(shift_service) -> None:
    """Department bulk uses batched read + bulk close + bulk insert (no N+1)."""
    shift_service.employees.search.return_value = [_employee(employee_id=5), _employee(employee_id=6)]
    shift_service.weekoffs.bulk_create.return_value = [_weekoff(), _weekoff(weekoff_id=2)]
    data = WeeklyOffUpdateRequest(department_id=3, day_of_week=0, weekoff_type="week_off")
    await shift_service.set_weekly_off(org_id=1, actor_id=9, data=data)
    # One batched read, one bulk insert — not one create per employee.
    shift_service.weekoffs.bulk_create.assert_awaited_once()
    shift_service.weekoffs.active_for_day_by_employees.assert_awaited_once()
    assert shift_service.weekoffs.create.await_count == 0
    rows = shift_service.weekoffs.bulk_create.await_args.args[0]
    assert len(rows) == 2


async def test_set_weekly_off_department_no_employees(shift_service) -> None:
    shift_service.employees.search.return_value = []
    data = WeeklyOffUpdateRequest(department_id=3, day_of_week=0, weekoff_type="week_off")
    with pytest.raises(NotFoundException) as exc:
        await shift_service.set_weekly_off(org_id=1, actor_id=9, data=data)
    assert exc.value.code == "not_found"
