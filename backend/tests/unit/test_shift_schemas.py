"""Unit tests for the Shift-Management request-schema validation.

Exercises the Pydantic v2 validators independently of the service: shift-time
rules (crosses-midnight / breaks), required fields, assignment date range, the
weekly-off exactly-one-target rule, rotation bounds, and query aliases.
"""

from __future__ import annotations

from datetime import date

import pytest
from pydantic import ValidationError

from app.modules.shift.schemas import (
    ShiftAssignmentQuery,
    ShiftAssignRequest,
    ShiftCreateRequest,
    ShiftDayTimingInput,
    ShiftResolveQuery,
    ShiftRotationRequest,
    WeeklyOffQuery,
    WeeklyOffUpdateRequest,
)


# --- Shift day timing ------------------------------------------------------
def test_day_timing_end_before_start_rejected() -> None:
    with pytest.raises(ValidationError):
        ShiftDayTimingInput(start_time="22:00", end_time="06:00")


def test_day_timing_overnight_allowed_with_flag() -> None:
    timing = ShiftDayTimingInput(start_time="22:00", end_time="06:00", crosses_midnight=True)
    assert timing.crosses_midnight is True


def test_day_timing_bad_break_rejected() -> None:
    with pytest.raises(ValidationError):
        ShiftDayTimingInput(break_start_time="13:00", break_end_time="12:00")


# --- Shift create ----------------------------------------------------------
def test_shift_create_trims_name() -> None:
    req = ShiftCreateRequest(shift_name="  Morning  ")
    assert req.shift_name == "Morning"


def test_shift_create_missing_name_rejected() -> None:
    with pytest.raises(ValidationError):
        ShiftCreateRequest()


def test_shift_create_default_type_is_fixed() -> None:
    assert ShiftCreateRequest(shift_name="X").shift_type.value == "fixed"


# --- Shift assignment ------------------------------------------------------
def test_assign_effective_to_before_from_rejected() -> None:
    with pytest.raises(ValidationError):
        ShiftAssignRequest(
            employee_id=1, effective_from=date(2026, 2, 1), effective_to=date(2026, 1, 1)
        )


def test_assign_valid() -> None:
    req = ShiftAssignRequest(employee_id=1, effective_from=date(2026, 2, 1))
    assert req.effective_to is None


# --- Weekly off ------------------------------------------------------------
def test_weekly_off_update_both_targets_rejected() -> None:
    with pytest.raises(ValidationError):
        WeeklyOffUpdateRequest(employee_id=1, department_id=2, day_of_week=0)


def test_weekly_off_update_neither_target_rejected() -> None:
    with pytest.raises(ValidationError):
        WeeklyOffUpdateRequest(day_of_week=0)


def test_weekly_off_update_valid() -> None:
    req = WeeklyOffUpdateRequest(employee_id=1, day_of_week=6, weekoff_type="week_off")
    assert int(req.day_of_week) == 6
    assert req.weekoff_type.value == "week_off"


def test_weekly_off_query_exactly_one() -> None:
    with pytest.raises(ValidationError):
        WeeklyOffQuery(employee_id=1, department_id=2)
    assert WeeklyOffQuery(employee_id=1).employee_id == 1


# --- Rotation --------------------------------------------------------------
def test_rotation_empty_sequence_rejected() -> None:
    with pytest.raises(ValidationError):
        ShiftRotationRequest(
            name="R",
            cadence="daily",
            shift_sequence=[],
            start_date=date(2026, 1, 1),
            horizon_days=7,
        )


def test_rotation_horizon_bounds() -> None:
    for bad in (0, 367):
        with pytest.raises(ValidationError):
            ShiftRotationRequest(
                name="R",
                cadence="daily",
                shift_sequence=[1],
                start_date=date(2026, 1, 1),
                horizon_days=bad,
            )


def test_rotation_valid() -> None:
    req = ShiftRotationRequest(
        name="Rot",
        cadence="weekly",
        shift_sequence=[1, 2],
        start_date=date(2026, 1, 1),
        horizon_days=14,
        group_scope={"branch_ids": [3]},
    )
    assert req.group_scope.branch_ids == [3]


# --- Query aliases ---------------------------------------------------------
def test_resolve_query_date_alias() -> None:
    query = ShiftResolveQuery(employee_id=1, **{"date": "2026-03-01"})
    assert query.on_date == date(2026, 3, 1)


def test_assignment_query_defaults_and_alias() -> None:
    query = ShiftAssignmentQuery(employee_id=1, **{"date": "2026-03-01"})
    assert query.page == 1
    assert query.on_date == date(2026, 3, 1)
