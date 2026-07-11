"""Unit tests for ``ShiftService`` business logic (repositories mocked).

Covers shift CRUD, shift assignment (supersession + validation), shift rotation
(roster generation), shift resolution, weekly-off configuration, search/pagination,
and the conflict / not-found / validation failure paths. All data access is mocked,
so these exercise the service logic in isolation.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.core.exceptions.base import (
    ConflictException,
    NotFoundException,
    ValidationException,
)
from app.modules.shift.exceptions import (
    AssignmentNotFoundException,
    AssignmentOverlapException,
    RosterNotFoundException,
    ShiftNotDeletedException,
    TimingDayDuplicateException,
    WeekoffDayExistsException,
)
from app.modules.shift.schemas import (
    RosterUpsertRequest,
    ShiftAssignmentBulkRequest,
    ShiftAssignmentQuery,
    ShiftAssignmentUpdateRequest,
    ShiftAssignRequest,
    ShiftCreateRequest,
    ShiftDayTimingInput,
    ShiftResolveQuery,
    ShiftRotationRequest,
    ShiftTimingsReplaceRequest,
    ShiftUpdateRequest,
    WeeklyOffQuery,
    WeeklyOffUpdateRequest,
    WeekoffConfigureRequest,
)

_NOW = datetime(2026, 1, 1, tzinfo=UTC)


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


def _timing(**overrides: object) -> SimpleNamespace:
    base: dict[str, object] = {
        "timing_id": 1,
        "shift_id": 1,
        "day_of_week": None,
        "start_time": None,
        "end_time": None,
        "break_start_time": None,
        "break_end_time": None,
        "duration_minutes": None,
        "is_working_day": True,
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
        "org_settings",
    ):
        setattr(svc, attr, AsyncMock())
    # Sensible defaults.
    svc.shifts.name_exists.return_value = False
    svc.shifts.get_active_by_id.return_value = _shift()
    svc.shifts.get_any_by_id.return_value = _shift(is_deleted=True)
    svc.shifts.get_detail.return_value = _shift()
    svc.shifts.has_open_assignments.return_value = False
    svc.shifts.exists_in_org.return_value = True
    svc.shifts.create.return_value = _shift()
    svc.shifts.search.return_value = []
    svc.shifts.search_count.return_value = 0
    svc.day_timings.get_for_shift.return_value = _timing()
    svc.day_timings.list_for_shift.return_value = []
    svc.day_timings.exists_for_day.return_value = False
    svc.assignments.exists_on_effective_from.return_value = False
    svc.assignments.get_open_for_employee.return_value = None
    svc.assignments.resolve_for_date.return_value = None
    svc.assignments.create.return_value = _assignment()
    svc.assignments.get_by_id_in_org.return_value = _assignment()
    svc.assignments.overlap_exists.return_value = False
    svc.assignments.search.return_value = []
    svc.assignments.search_count.return_value = 0
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
    svc.weekoffs.get_by_id_for_employee.return_value = _weekoff()
    svc.weekoffs.exists_active_for_day.return_value = False
    svc.rosters.bulk_create.return_value = [_roster(), _roster(roster_id=2)]
    svc.rosters.exists_for_shift_on_or_after.return_value = False
    svc.rosters.get_for_employee_date.return_value = None
    svc.rosters.get_by_id_in_org.return_value = _roster()
    svc.rosters.create.return_value = _roster()
    svc.rosters.update.return_value = _roster()
    svc.rosters.search_range.return_value = []
    svc.rosters.search_range_count.return_value = 0
    svc.rosters.list_for_employee_range.return_value = []
    svc.users.get_active_by_id.return_value = SimpleNamespace(name="Admin")
    svc.org_settings.get_by_org_id.return_value = SimpleNamespace(advance_shift_enabled=True)
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
    data = ShiftUpdateRequest(
        day_timings=[ShiftDayTimingInput(start_time="09:00", end_time="17:00")]
    )
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


async def test_list_assignments_date_resolve_requires_employee_id(shift_service) -> None:
    """The single-effective-assignment resolve (``date``) needs an employee scope."""
    query = ShiftAssignmentQuery(**{"date": "2026-02-15"})
    with pytest.raises(ValidationException) as exc:
        await shift_service.list_assignments(org_id=1, query=query)
    assert exc.value.code == "validation_error"


async def test_list_assignments_timeline(shift_service) -> None:
    shift_service.assignments.search.return_value = [_assignment()]
    shift_service.assignments.search_count.return_value = 1
    result = await shift_service.list_assignments(
        org_id=1, query=ShiftAssignmentQuery(employee_id=5)
    )
    assert result.pagination.total_records == 1
    assert len(result.items) == 1
    kwargs = shift_service.assignments.search.await_args.kwargs
    assert kwargs["employee_id"] == 5


async def test_list_assignments_org_wide_with_filters(shift_service) -> None:
    """Contract #16: org-wide list with shift_id / active_on filters."""
    shift_service.assignments.search.return_value = [_assignment()]
    shift_service.assignments.search_count.return_value = 1
    query = ShiftAssignmentQuery(shift_id=1, active_on=date(2026, 2, 15))
    result = await shift_service.list_assignments(org_id=1, query=query)
    assert len(result.items) == 1
    kwargs = shift_service.assignments.search.await_args.kwargs
    assert kwargs["shift_id"] == 1
    assert kwargs["active_on"] == date(2026, 2, 15)


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
    """Max fidelity: a timing marking the weekday non-working sets is_working_day=False."""
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


async def test_generate_rotation_blocked_when_advance_shift_disabled(shift_service) -> None:
    """org_settings.advance_shift_enabled=False -> 409 before any validation or writes."""
    shift_service.org_settings.get_by_org_id.return_value = SimpleNamespace(
        advance_shift_enabled=False
    )
    data = ShiftRotationRequest(
        name="Rot",
        cadence="daily",
        shift_sequence=[1],
        start_date=date(2026, 2, 1),
        horizon_days=3,
        group_scope={"employee_ids": [5]},
    )
    with pytest.raises(ConflictException) as exc:
        await shift_service.generate_rotation(org_id=1, actor_id=9, data=data)
    assert exc.value.code == "ADVANCE_SHIFT_DISABLED"
    shift_service.rosters.bulk_create.assert_not_awaited()


async def test_generate_rotation_blocked_without_settings_row(shift_service) -> None:
    """An org with no org_settings row keeps the schema default (off) -> 409."""
    shift_service.org_settings.get_by_org_id.return_value = None
    data = ShiftRotationRequest(
        name="Rot",
        cadence="daily",
        shift_sequence=[1],
        start_date=date(2026, 2, 1),
        horizon_days=3,
        group_scope={"employee_ids": [5]},
    )
    with pytest.raises(ConflictException) as exc:
        await shift_service.generate_rotation(org_id=1, actor_id=9, data=data)
    assert exc.value.code == "ADVANCE_SHIFT_DISABLED"


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
    shift_service.employees.search.return_value = [
        _employee(employee_id=5),
        _employee(employee_id=6),
    ]
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


# ===========================================================================
# Shift restore (contract #6)
# ===========================================================================
async def test_restore_shift_success(shift_service) -> None:
    shift_service.shifts.get_any_by_id.return_value = _shift(is_deleted=True)
    result = await shift_service.restore_shift(org_id=1, actor_id=9, shift_id=1)
    assert result.shift_id == 1
    updated = shift_service.shifts.update.await_args
    assert updated.args[1] == {"is_deleted": False}
    shift_service.audit.record.assert_awaited_once()


async def test_restore_shift_not_deleted_409(shift_service) -> None:
    shift_service.shifts.get_any_by_id.return_value = _shift(is_deleted=False)
    with pytest.raises(ShiftNotDeletedException) as exc:
        await shift_service.restore_shift(org_id=1, actor_id=9, shift_id=1)
    assert exc.value.code == "SHIFT_NOT_DELETED"


async def test_restore_shift_not_found(shift_service) -> None:
    shift_service.shifts.get_any_by_id.return_value = None
    with pytest.raises(NotFoundException) as exc:
        await shift_service.restore_shift(org_id=1, actor_id=9, shift_id=404)
    assert exc.value.code == "SHIFT_NOT_FOUND"


# ===========================================================================
# Shift timings (contract §5)
# ===========================================================================
async def test_replace_timings_uniform_success(shift_service) -> None:
    shift_service.shifts.get_active_by_id.return_value = _shift(is_uniform_time=True)
    shift_service.day_timings.list_for_shift.return_value = [
        _timing(start_time=None, end_time=None)
    ]
    data = ShiftTimingsReplaceRequest(
        timings=[ShiftDayTimingInput(start_time="09:00", end_time="18:00")]
    )
    result = await shift_service.replace_timings(
        org_id=1, actor_id=9, shift_id=1, data=data
    )
    assert len(result) == 1
    shift_service.day_timings.delete_all_for_shift.assert_awaited_once_with(1)
    shift_service.day_timings.create.assert_awaited_once()
    shift_service.audit.record.assert_awaited_once()


async def test_replace_timings_uniform_requires_single_null_day(shift_service) -> None:
    shift_service.shifts.get_active_by_id.return_value = _shift(is_uniform_time=True)
    data = ShiftTimingsReplaceRequest(
        timings=[
            ShiftDayTimingInput(day_of_week=1, start_time="09:00", end_time="18:00"),
            ShiftDayTimingInput(day_of_week=2, start_time="09:00", end_time="18:00"),
        ]
    )
    with pytest.raises(ValidationException):
        await shift_service.replace_timings(org_id=1, actor_id=9, shift_id=1, data=data)
    shift_service.day_timings.delete_all_for_shift.assert_not_awaited()


async def test_replace_timings_duplicate_day_409(shift_service) -> None:
    shift_service.shifts.get_active_by_id.return_value = _shift(is_uniform_time=False)
    data = ShiftTimingsReplaceRequest(
        timings=[
            ShiftDayTimingInput(day_of_week=1, start_time="09:00", end_time="18:00"),
            ShiftDayTimingInput(day_of_week=1, start_time="10:00", end_time="19:00"),
        ]
    )
    with pytest.raises(TimingDayDuplicateException) as exc:
        await shift_service.replace_timings(org_id=1, actor_id=9, shift_id=1, data=data)
    assert exc.value.code == "TIMING_DAY_DUPLICATE"


# ===========================================================================
# Assignment update / delete / bulk (contract #15, #17, #18)
# ===========================================================================
async def test_update_assignment_overlap_409(shift_service) -> None:
    shift_service.assignments.overlap_exists.return_value = True
    data = ShiftAssignmentUpdateRequest(effective_to=date(2026, 3, 1))
    with pytest.raises(AssignmentOverlapException) as exc:
        await shift_service.update_assignment(
            org_id=1, actor_id=9, assignment_id=1, data=data
        )
    assert exc.value.code == "ASSIGNMENT_OVERLAP"


async def test_delete_assignment_success(shift_service) -> None:
    await shift_service.delete_assignment(org_id=1, actor_id=9, assignment_id=1)
    shift_service.assignments.delete.assert_awaited_once()
    shift_service.audit.record.assert_awaited_once()


async def test_delete_assignment_not_found(shift_service) -> None:
    shift_service.assignments.get_by_id_in_org.return_value = None
    with pytest.raises(AssignmentNotFoundException) as exc:
        await shift_service.delete_assignment(org_id=1, actor_id=9, assignment_id=404)
    assert exc.value.code == "ASSIGNMENT_NOT_FOUND"


async def test_bulk_assign_reports_per_item_results(shift_service) -> None:
    """A missing employee is skipped with a reason; the valid one is created."""

    async def _employee_lookup(employee_id: int, org_id: int):
        return _employee(employee_id=employee_id) if employee_id == 5 else None

    shift_service.employees.get_active_by_id.side_effect = _employee_lookup
    data = ShiftAssignmentBulkRequest(
        employee_ids=[5, 404], shift_id=1, effective_from=date(2026, 2, 1)
    )
    result = await shift_service.bulk_assign_shift(org_id=1, actor_id=9, data=data)
    assert result.created_count == 1
    assert result.skipped_count == 1
    statuses = {item.employee_id: item.status for item in result.results}
    assert statuses == {5: "created", 404: "skipped"}
    shift_service.audit.record.assert_awaited_once()


# ===========================================================================
# Weekly offs — contract paths (#11-#13)
# ===========================================================================
async def test_configure_weekoffs_closes_prior_current_rows(shift_service) -> None:
    """PUT replaces the current config: re-specified weekdays are effective-dated."""
    shift_service.weekoffs.list_for_employee.return_value = [
        _weekoff(weekoff_id=7, day_of_week=0),
        _weekoff(weekoff_id=8, day_of_week=3),
    ]
    data = WeekoffConfigureRequest(
        weekoffs=[
            {
                "day_of_week": 0,
                "weekoff_type": "week_off",
                "effective_from": date(2026, 3, 1).isoformat(),
            }
        ]
    )
    result = await shift_service.configure_weekoffs(
        org_id=1, actor_id=9, employee_id=5, data=data
    )
    assert len(result.items) == 1
    # The re-specified weekday's current row is closed the day before.
    closed = shift_service.weekoffs.update.await_args
    assert closed.args[1] == {"effective_to": date(2026, 2, 28)}
    # The dropped weekday (day 3) is closed via the batched close.
    close_ids = shift_service.weekoffs.close_by_ids.await_args.args[0]
    assert close_ids == [8]
    shift_service.weekoffs.create.assert_awaited_once()


async def test_configure_weekoffs_duplicate_day_409(shift_service) -> None:
    data = WeekoffConfigureRequest(
        weekoffs=[
            {"day_of_week": 0, "weekoff_type": "week_off"},
            {"day_of_week": 0, "weekoff_type": "working"},
        ]
    )
    with pytest.raises(WeekoffDayExistsException) as exc:
        await shift_service.configure_weekoffs(org_id=1, actor_id=9, employee_id=5, data=data)
    assert exc.value.code == "WEEKOFF_DAY_EXISTS"


# ===========================================================================
# Roster (contract §8)
# ===========================================================================
async def test_upsert_roster_creates_when_absent(shift_service) -> None:
    shift_service.rosters.get_for_employee_date.return_value = None
    data = RosterUpsertRequest(employee_id=5, roster_date=date(2026, 2, 1), shift_id=1)
    result = await shift_service.upsert_roster_entry(org_id=1, actor_id=9, data=data)
    assert result.created is True
    shift_service.rosters.create.assert_awaited_once()
    shift_service.rosters.update.assert_not_awaited()


async def test_upsert_roster_uniqueness_updates_existing(shift_service) -> None:
    """One row per (employee, date): a second upsert updates instead of duplicating."""
    existing = _roster(roster_id=42, shift_id=2)
    shift_service.rosters.get_for_employee_date.return_value = existing
    data = RosterUpsertRequest(employee_id=5, roster_date=date(2026, 2, 1), shift_id=1)
    result = await shift_service.upsert_roster_entry(org_id=1, actor_id=9, data=data)
    assert result.created is False
    shift_service.rosters.create.assert_not_awaited()
    updated = shift_service.rosters.update.await_args
    assert updated.args[0] is existing
    assert updated.args[1]["shift_id"] == 1


async def test_update_roster_entry_weekoff_clears_shift(shift_service) -> None:
    from app.modules.shift.schemas import RosterUpdateRequest

    shift_service.rosters.get_by_id_in_org.return_value = _roster(shift_id=1)
    result = await shift_service.update_roster_entry(
        org_id=1, actor_id=9, roster_id=1, data=RosterUpdateRequest(is_week_off=True)
    )
    updated = shift_service.rosters.update.await_args
    assert updated.args[1]["is_week_off"] is True
    assert updated.args[1]["shift_id"] is None
    assert result.roster_id == 1


async def test_delete_roster_entry_not_found(shift_service) -> None:
    shift_service.rosters.get_by_id_in_org.return_value = None
    with pytest.raises(RosterNotFoundException) as exc:
        await shift_service.delete_roster_entry(org_id=1, actor_id=9, roster_id=404)
    assert exc.value.code == "ROSTER_NOT_FOUND"
