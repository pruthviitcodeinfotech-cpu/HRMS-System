"""Shift Management — Pydantic v2 request/response DTOs.

Wire contract for the Shift-Management API (section 10 of the HRMS Complete API
Contract): shift definitions + per-day timings, shift assignment, the shift-resolve
lookup, shift rotations (roster generation), and weekly-off configuration.

Reconciliation notes (the SQLAlchemy models are the source of truth):

* Field names mirror the ``shifts`` / ``shift_day_timings`` / ``shift_assignments``
  / ``employee_weekoffs`` / ``roster`` columns exactly (``shift_name``,
  ``shift_type``, ``day_of_week``, ``effective_from``, ...). The API contract uses
  generic illustrative names (``name``, ``type``, ``weekday``); those map onto the
  concrete columns. This follows the convention established in
  :mod:`app.modules.employee.schemas` — "field shapes mirror the tables; validation
  follows the API contract".
* A shift's timings live in ``shift_day_timings`` (one uniform row with
  ``day_of_week = NULL``, or one row per weekday). The contract's flat
  ``{start_time, end_time}`` therefore maps to a single uniform
  :class:`ShiftDayTimingInput`.
* ``crosses_midnight`` is a transport-only validation flag (no column): it gates
  the contract rule "422 if end ≤ start unless crosses_midnight". ``grace_minutes``
  / ``overtime_buffer_minutes`` have **no shift column** — they are Attendance-Engine
  thresholds owned by the **Settings** contract (``/settings/attendance``) and are
  intentionally not modelled here.
* ``working_hours_config`` (models live in this package) is surfaced by the
  **Settings** API (``GET/PUT /settings/attendance``), not by Shift Management §10,
  so its DTOs belong to the Settings module and are intentionally out of scope here.
* Shift rotations have **no table**: ``POST /shift-rotations`` is a compute command
  that materialises ``roster`` rows, so :class:`ShiftRotationRequest` is a pure
  command DTO and the response returns generated :class:`RosterEntrySchema` rows.

Reuses the shared foundation (:class:`app.shared.base.schema.BaseSchema`, the paged
envelope, and :class:`PaginationRequest`). ORM-backed response schemas use
``from_attributes`` so they build directly from model instances.
"""

from __future__ import annotations

from datetime import date, datetime, time

from pydantic import Field, field_validator, model_validator

from app.modules.shift.constants import (
    DayOfWeek,
    ShiftType,
    WeekoffType,
)
from app.shared.base.schema import BaseSchema
from app.shared.schemas.pagination import PaginatedResponse, PaginationRequest

# ===========================================================================
# Shift day timings (nested in shift create / detail)
# ===========================================================================


class ShiftDayTimingInput(BaseSchema):
    """A single ``shift_day_timings`` row supplied on shift create/update.

    ``day_of_week`` is ``None`` for a uniform timing; a per-day shift supplies one
    entry per weekday. ``crosses_midnight`` is a transport-only flag (no column)
    that permits an ``end_time`` at/earlier than ``start_time`` (overnight shift).
    ``duration_minutes`` is normally derived server-side and may be omitted.
    """

    day_of_week: DayOfWeek | None = Field(default=None, description="0=Sunday … 6=Saturday.")
    start_time: time | None = None
    end_time: time | None = None
    break_start_time: time | None = None
    break_end_time: time | None = None
    duration_minutes: int | None = Field(default=None, ge=0)
    is_working_day: bool = True
    crosses_midnight: bool = Field(
        default=False, description="Transport-only: allow end_time ≤ start_time (overnight shift)."
    )

    @model_validator(mode="after")
    def _validate_times(self) -> ShiftDayTimingInput:
        """Enforce the contract's shift-time rules (422 on violation)."""
        if self.start_time is not None and self.end_time is not None:
            if self.end_time <= self.start_time and not self.crosses_midnight:
                raise ValueError(
                    "end_time must be after start_time unless crosses_midnight is true"
                )
        if (
            self.break_start_time is not None
            and self.break_end_time is not None
            and self.break_end_time <= self.break_start_time
        ):
            raise ValueError("break_end_time must be after break_start_time")
        return self


class ShiftDayTimingSchema(BaseSchema):
    """A persisted ``shift_day_timings`` row."""

    timing_id: int
    day_of_week: DayOfWeek | None = None
    start_time: time | None = None
    end_time: time | None = None
    break_start_time: time | None = None
    break_end_time: time | None = None
    duration_minutes: int | None = None
    is_working_day: bool = True


class ShiftTimingsReplaceRequest(BaseSchema):
    """Body for ``PUT /shifts/{shift_id}/timings`` — replaces the full timing set."""

    timings: list[ShiftDayTimingInput] = Field(..., min_length=1)


class ShiftDayTimingUpdateRequest(BaseSchema):
    """Body for ``PATCH /shifts/{shift_id}/timings/{timing_id}`` (partial update).

    ``crosses_midnight`` is transport-only (no column): it permits an ``end_time``
    at/earlier than ``start_time`` when both are supplied in the same patch.
    """

    day_of_week: DayOfWeek | None = None
    start_time: time | None = None
    end_time: time | None = None
    break_start_time: time | None = None
    break_end_time: time | None = None
    duration_minutes: int | None = Field(default=None, ge=0)
    is_working_day: bool | None = None
    crosses_midnight: bool = Field(
        default=False, description="Transport-only: allow end_time ≤ start_time (overnight shift)."
    )

    @model_validator(mode="after")
    def _validate_times(self) -> ShiftDayTimingUpdateRequest:
        """Enforce the contract's shift-time rules when both ends are patched together."""
        if self.start_time is not None and self.end_time is not None:
            if self.end_time <= self.start_time and not self.crosses_midnight:
                raise ValueError(
                    "end_time must be after start_time unless crosses_midnight is true"
                )
        if (
            self.break_start_time is not None
            and self.break_end_time is not None
            and self.break_end_time <= self.break_start_time
        ):
            raise ValueError("break_end_time must be after break_start_time")
        return self


# ===========================================================================
# Shift — requests
# ===========================================================================


class ShiftCreateRequest(BaseSchema):
    """Body for ``POST /shifts`` (define a shift).

    Provide ``day_timings`` as one uniform entry (``day_of_week=None``) when
    ``is_uniform_time`` is true, or one entry per weekday for an advanced shift.
    """

    shift_name: str = Field(..., min_length=1, max_length=150)
    shift_type: ShiftType = ShiftType.FIXED
    is_open_shift: bool = False
    is_default: bool = False
    is_uniform_time: bool = True
    has_break_time: bool = False
    shift_color: str | None = Field(default=None, max_length=30)
    remark: str | None = None
    is_advanced_mode: bool = False
    day_timings: list[ShiftDayTimingInput] = Field(default_factory=list)

    @field_validator("shift_name")
    @classmethod
    def _trim_name(cls, value: str) -> str:
        return value.strip()


class ShiftUpdateRequest(BaseSchema):
    """Body for ``PUT /shifts/{id}`` (partial update; all fields optional).

    When ``day_timings`` is supplied it replaces the shift's timings wholesale.
    """

    shift_name: str | None = Field(default=None, min_length=1, max_length=150)
    shift_type: ShiftType | None = None
    is_open_shift: bool | None = None
    is_default: bool | None = None
    is_uniform_time: bool | None = None
    has_break_time: bool | None = None
    shift_color: str | None = Field(default=None, max_length=30)
    remark: str | None = None
    is_advanced_mode: bool | None = None
    day_timings: list[ShiftDayTimingInput] | None = None

    @field_validator("shift_name")
    @classmethod
    def _trim_name(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else None


# ===========================================================================
# Shift — responses
# ===========================================================================


class ShiftSummarySchema(BaseSchema):
    """Compact shift row for the list endpoint."""

    shift_id: int
    org_id: int
    shift_name: str
    shift_type: ShiftType
    is_open_shift: bool = False
    is_default: bool = False
    is_uniform_time: bool = True
    has_break_time: bool = False
    shift_color: str | None = None
    is_advanced_mode: bool = False
    created_at: datetime


class ShiftSchema(ShiftSummarySchema):
    """Full flat projection of a ``shifts`` row."""

    remark: str | None = None
    is_deleted: bool = False
    created_by: int | None = None
    updated_at: datetime


class ShiftDetailSchema(ShiftSchema):
    """Response for ``GET /shifts/{id}`` — the shift plus its day timings."""

    day_timings: list[ShiftDayTimingSchema] = Field(default_factory=list)


# ===========================================================================
# Shift assignment
# ===========================================================================


class ShiftAssignRequest(BaseSchema):
    """Body for ``POST /shifts/{id}/assign`` (assign a shift to an employee).

    Supersedes the employee's prior assignment (the service closes its
    ``effective_to``). ``effective_to`` may be supplied to bound this assignment.
    """

    employee_id: int
    effective_from: date
    effective_to: date | None = None

    @model_validator(mode="after")
    def _validate_range(self) -> ShiftAssignRequest:
        """``effective_to`` (when given) must not precede ``effective_from``."""
        if self.effective_to is not None and self.effective_to < self.effective_from:
            raise ValueError("effective_to must be on or after effective_from")
        return self


class ShiftAssignmentSchema(BaseSchema):
    """A persisted ``shift_assignments`` row."""

    assignment_id: int
    org_id: int
    employee_id: int
    shift_id: int
    effective_from: date
    effective_to: date | None = None
    assigned_by: int | None = None
    created_at: datetime
    updated_at: datetime


class ShiftAssignmentQuery(PaginationRequest):
    """Query parameters for ``GET /shift-assignments`` (contract §7 #16)."""

    employee_id: int | None = Field(default=None, description="Filter by employee.")
    shift_id: int | None = Field(default=None, description="Filter by shift.")
    active_on: date | None = Field(
        default=None, description="Return assignments whose effective range covers this date."
    )
    on_date: date | None = Field(
        default=None, alias="date", description="Resolve the assignment effective on this date."
    )


class ShiftAssignmentCreateRequest(ShiftAssignRequest):
    """Body for ``POST /shift-assignments`` (contract #14 — ``shift_id`` in the body)."""

    shift_id: int


class ShiftAssignmentBulkRequest(BaseSchema):
    """Body for ``POST /shift-assignments/bulk`` (contract #15)."""

    employee_ids: list[int] = Field(..., min_length=1)
    shift_id: int
    effective_from: date
    effective_to: date | None = None

    @model_validator(mode="after")
    def _validate_range(self) -> ShiftAssignmentBulkRequest:
        """``effective_to`` (when given) must not precede ``effective_from``."""
        if self.effective_to is not None and self.effective_to < self.effective_from:
            raise ValueError("effective_to must be on or after effective_from")
        return self


class ShiftAssignmentUpdateRequest(BaseSchema):
    """Body for ``PATCH /shift-assignments/{assignment_id}`` (contract #17)."""

    shift_id: int | None = None
    effective_from: date | None = None
    effective_to: date | None = None


class ShiftAssignmentBulkItemResult(BaseSchema):
    """Per-employee outcome of a bulk assignment (contract #15)."""

    employee_id: int
    status: str = Field(..., description="'created' or 'skipped'.")
    reason: str | None = None
    assignment_id: int | None = None


class ShiftAssignmentBulkResponse(BaseSchema):
    """Response for ``POST /shift-assignments/bulk`` — per-item results."""

    created_count: int = 0
    skipped_count: int = 0
    results: list[ShiftAssignmentBulkItemResult] = Field(default_factory=list)


# ===========================================================================
# Shift resolve (the Attendance Engine's shift-of-the-day lookup)
# ===========================================================================


class ShiftResolveQuery(BaseSchema):
    """Query parameters for ``GET /shifts/resolve``."""

    employee_id: int
    on_date: date = Field(alias="date", description="The date to resolve the shift for.")


class ShiftResolveResponse(BaseSchema):
    """Response for ``GET /shifts/resolve`` — the resolved shift + day flags."""

    shift: ShiftSchema | None = Field(
        default=None, description="The effective shift, or null on a non-working day."
    )
    is_weekly_off: bool = False
    is_working_day: bool = True


# ===========================================================================
# Roster + shift rotations
# ===========================================================================


class RosterEntrySchema(BaseSchema):
    """A persisted ``roster`` row (one employee's shift for one date)."""

    roster_id: int
    org_id: int
    employee_id: int
    roster_date: date
    shift_id: int | None = None
    is_week_off: bool = False
    created_by: int | None = None
    updated_by: int | None = None
    created_at: datetime
    updated_at: datetime


class RosterRangeQuery(PaginationRequest):
    """Date-range selector shared by the roster calendar reads (contract #20/#21).

    Exactly one range form is required: ``month`` (``YYYY-MM``) **or** the
    ``date_from`` + ``date_to`` pair.
    """

    date_from: date | None = None
    date_to: date | None = None
    month: str | None = Field(
        default=None, pattern=r"^\d{4}-(0[1-9]|1[0-2])$", description="Calendar month (YYYY-MM)."
    )

    @model_validator(mode="after")
    def _one_range_form(self) -> RosterRangeQuery:
        """Require ``month`` XOR (``date_from`` + ``date_to``), with a valid order."""
        has_pair = self.date_from is not None and self.date_to is not None
        has_partial_pair = (self.date_from is None) != (self.date_to is None)
        if self.month is not None and (self.date_from is not None or self.date_to is not None):
            raise ValueError("supply either month or date_from/date_to, not both")
        if self.month is None and (has_partial_pair or not has_pair):
            raise ValueError("supply month (YYYY-MM) or both date_from and date_to")
        if has_pair and self.date_to < self.date_from:
            raise ValueError("date_to must be on or after date_from")
        return self


class RosterQuery(RosterRangeQuery):
    """Query parameters for ``GET /roster`` (org shift calendar, contract #20)."""

    branch_id: int | None = None
    department_id: int | None = None
    employee_id: int | None = None
    shift_id: int | None = None


class RosterUpsertRequest(BaseSchema):
    """Body for ``PUT /roster`` (contract #22) and each item of ``POST /roster/bulk``."""

    employee_id: int
    roster_date: date
    shift_id: int | None = None
    is_week_off: bool = False

    @model_validator(mode="after")
    def _weekoff_excludes_shift(self) -> RosterUpsertRequest:
        """A week-off entry must not also carry a shift (contract §8)."""
        if self.is_week_off and self.shift_id is not None:
            raise ValueError("a week-off roster entry cannot carry a shift_id")
        return self


class RosterBulkRequest(BaseSchema):
    """Body for ``POST /roster/bulk`` (contract #23)."""

    entries: list[RosterUpsertRequest] = Field(..., min_length=1)


class RosterUpdateRequest(BaseSchema):
    """Body for ``PATCH /roster/{roster_id}`` (contract #24)."""

    shift_id: int | None = None
    is_week_off: bool | None = None


class RosterUpsertResult(BaseSchema):
    """Result of a roster upsert: the entry plus whether it was created or updated."""

    created: bool
    entry: RosterEntrySchema


class RosterBulkItemResult(BaseSchema):
    """Per-entry outcome of ``POST /roster/bulk``."""

    employee_id: int
    roster_date: date
    status: str = Field(..., description="'created', 'updated' or 'skipped'.")
    reason: str | None = None
    roster_id: int | None = None


class RosterBulkResponse(BaseSchema):
    """Response for ``POST /roster/bulk`` — per-item results."""

    created_count: int = 0
    updated_count: int = 0
    skipped_count: int = 0
    results: list[RosterBulkItemResult] = Field(default_factory=list)


class ShiftRotationScope(BaseSchema):
    """The ``group_scope`` a rotation applies to (branch / department / employees)."""

    branch_ids: list[int] = Field(default_factory=list)
    department_ids: list[int] = Field(default_factory=list)
    employee_ids: list[int] = Field(default_factory=list)


class ShiftRotationRequest(BaseSchema):
    """Body for ``POST /shift-rotations`` (generate a rotating roster).

    A rotation cycles ``shift_sequence`` (ordered shift ids) across the target
    employees over ``horizon_days`` starting at ``start_date``, materialising
    ``roster`` rows. There is no rotation table — this is a compute command.
    """

    name: str = Field(..., min_length=1, max_length=150)
    cadence: str = Field(
        ..., min_length=1, max_length=50, description="Rotation cadence, e.g. 'daily' or 'weekly'."
    )
    shift_sequence: list[int] = Field(
        ..., min_length=1, description="Ordered shift ids to rotate through."
    )
    start_date: date
    horizon_days: int = Field(..., ge=1, le=366, description="How many days to generate (bounded).")
    group_scope: ShiftRotationScope = Field(default_factory=ShiftRotationScope)

    @field_validator("name")
    @classmethod
    def _trim(cls, value: str) -> str:
        return value.strip()


class ShiftRotationResponse(BaseSchema):
    """Response for ``POST /shift-rotations`` (202 Accepted) — generated roster rows."""

    generated_count: int = 0
    generated_assignments: list[RosterEntrySchema] = Field(default_factory=list)


# ===========================================================================
# Weekly offs (employee_weekoffs)
# ===========================================================================


class WeeklyOffUpdateRequest(BaseSchema):
    """Body for ``PUT /weekly-offs`` (set a weekday's week-off configuration).

    Exactly one of ``employee_id`` / ``department_id`` must be supplied (422
    otherwise). ``day_of_week`` is the contract's ``weekday``. The five
    ``occurrence_*`` flags select which occurrences of that weekday in a month the
    rule applies to (used for occasional week-offs).
    """

    employee_id: int | None = None
    department_id: int | None = Field(
        default=None, description="Bulk-apply to every employee in the department."
    )
    day_of_week: DayOfWeek = Field(..., description="0=Sunday … 6=Saturday (contract 'weekday').")
    weekoff_type: WeekoffType = WeekoffType.WORKING
    occurrence_1st: bool = True
    occurrence_2nd: bool = True
    occurrence_3rd: bool = True
    occurrence_4th: bool = True
    occurrence_5th: bool = True
    effective_from: date | None = None
    effective_to: date | None = None

    @model_validator(mode="after")
    def _exactly_one_target(self) -> WeeklyOffUpdateRequest:
        """Require exactly one of ``employee_id`` / ``department_id``."""
        if (self.employee_id is None) == (self.department_id is None):
            raise ValueError("exactly one of employee_id or department_id is required")
        return self


class WeeklyOffQuery(BaseSchema):
    """Query parameters for ``GET /weekly-offs`` (employee OR department)."""

    employee_id: int | None = None
    department_id: int | None = None

    @model_validator(mode="after")
    def _exactly_one_target(self) -> WeeklyOffQuery:
        """Require exactly one of ``employee_id`` / ``department_id``."""
        if (self.employee_id is None) == (self.department_id is None):
            raise ValueError("exactly one of employee_id or department_id is required")
        return self


class WeekoffItemInput(BaseSchema):
    """One weekday's configuration inside ``PUT /employees/{id}/weekoffs`` (contract #12)."""

    day_of_week: DayOfWeek = Field(..., description="0=Sunday … 6=Saturday.")
    weekoff_type: WeekoffType = WeekoffType.WORKING
    occurrence_1st: bool = True
    occurrence_2nd: bool = True
    occurrence_3rd: bool = True
    occurrence_4th: bool = True
    occurrence_5th: bool = True
    effective_from: date | None = None
    effective_to: date | None = None

    @model_validator(mode="after")
    def _validate_range(self) -> WeekoffItemInput:
        """``effective_to`` (when given) must not precede ``effective_from``."""
        if (
            self.effective_from is not None
            and self.effective_to is not None
            and self.effective_to < self.effective_from
        ):
            raise ValueError("effective_to must be on or after effective_from")
        return self


class WeekoffConfigureRequest(BaseSchema):
    """Body for ``PUT /employees/{employee_id}/weekoffs`` (contract #12 — bulk replace)."""

    weekoffs: list[WeekoffItemInput] = Field(..., min_length=1)


class WeekoffPatchRequest(BaseSchema):
    """Body for ``PATCH /employees/{employee_id}/weekoffs/{weekoff_id}`` (contract #13).

    Patches a single weekday's ``weekoff_type`` / occurrence flags / ``effective_to``.
    """

    weekoff_type: WeekoffType | None = None
    occurrence_1st: bool | None = None
    occurrence_2nd: bool | None = None
    occurrence_3rd: bool | None = None
    occurrence_4th: bool | None = None
    occurrence_5th: bool | None = None
    effective_to: date | None = None


class WeeklyOffSchema(BaseSchema):
    """A persisted ``employee_weekoffs`` row."""

    weekoff_id: int
    employee_id: int
    day_of_week: DayOfWeek
    weekoff_type: WeekoffType
    occurrence_1st: bool = True
    occurrence_2nd: bool = True
    occurrence_3rd: bool = True
    occurrence_4th: bool = True
    occurrence_5th: bool = True
    effective_from: date | None = None
    effective_to: date | None = None
    updated_by: int | None = None
    updated_at: datetime
    created_at: datetime


# ===========================================================================
# Paginated list responses (reuse the shared paged envelope)
# ===========================================================================


class ShiftListResponse(PaginatedResponse[ShiftSummarySchema]):
    """Paginated ``GET /shifts`` result."""


class ShiftAssignmentListResponse(PaginatedResponse[ShiftAssignmentSchema]):
    """Paginated ``GET /shift-assignments`` result (assignment timeline)."""


class WeeklyOffListResponse(PaginatedResponse[WeeklyOffSchema]):
    """Paginated weekly-off configuration result (``GET /employees/{id}/weekoffs``)."""


class RosterListResponse(PaginatedResponse[RosterEntrySchema]):
    """Paginated roster calendar result (``GET /roster``, ``GET /employees/{id}/roster``)."""


__all__ = [
    # day timings
    "ShiftDayTimingInput",
    "ShiftDayTimingSchema",
    "ShiftTimingsReplaceRequest",
    "ShiftDayTimingUpdateRequest",
    # shift requests
    "ShiftCreateRequest",
    "ShiftUpdateRequest",
    # shift responses
    "ShiftSummarySchema",
    "ShiftSchema",
    "ShiftDetailSchema",
    # assignment
    "ShiftAssignRequest",
    "ShiftAssignmentCreateRequest",
    "ShiftAssignmentBulkRequest",
    "ShiftAssignmentUpdateRequest",
    "ShiftAssignmentBulkItemResult",
    "ShiftAssignmentBulkResponse",
    "ShiftAssignmentSchema",
    "ShiftAssignmentQuery",
    # resolve
    "ShiftResolveQuery",
    "ShiftResolveResponse",
    # roster / rotation
    "RosterEntrySchema",
    "RosterRangeQuery",
    "RosterQuery",
    "RosterUpsertRequest",
    "RosterBulkRequest",
    "RosterUpdateRequest",
    "RosterUpsertResult",
    "RosterBulkItemResult",
    "RosterBulkResponse",
    "ShiftRotationScope",
    "ShiftRotationRequest",
    "ShiftRotationResponse",
    # weekly offs
    "WeekoffItemInput",
    "WeekoffConfigureRequest",
    "WeekoffPatchRequest",
    "WeeklyOffUpdateRequest",
    "WeeklyOffQuery",
    "WeeklyOffSchema",
    # paginated list responses
    "ShiftListResponse",
    "ShiftAssignmentListResponse",
    "WeeklyOffListResponse",
    "RosterListResponse",
]
