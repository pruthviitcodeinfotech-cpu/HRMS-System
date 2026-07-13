"""Attendance Management — Pydantic v2 request/response DTOs.

Wire contract for the Attendance Management API (section 11 of the HRMS Complete
API Contract): live attendance feed, daily grid, monthly calendar, raw logs,
manual attendance entries, correction requests, approvals, missing punches,
attendance locking, and on-demand recomputation.

Reconciliation notes (the SQLAlchemy models are the source of truth):
* Field names mirror the ``attendance_days``, ``attendance_punches``, and
  ``attendance_penalties`` table columns. Where the API contract specifies
  different names (e.g. ``first_in``, ``last_out``, ``worked_minutes``), Pydantic's
  validation and serialization aliases are used to map between DB and wire formats
  without duplicating field configurations.
* Reuses the shared foundation (:class:`app.shared.base.schema.BaseSchema`).
  ORM-backed response schemas use ``from_attributes=True`` (inherited from
  ``BaseSchema``) to automatically build from SQLAlchemy model instances.
"""

from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal

from pydantic import Field, field_validator, model_validator

from app.modules.attendance.constants import (
    ApprovalStatus,
    AttendanceDayStatus,
    AttendanceSource,
    LockScope,
    PenaltyStatus,
    PenaltyType,
    PenaltyUnit,
    PunchSource,
    PunchType,
)
from app.shared.base.schema import BaseSchema
from app.shared.schemas.pagination import PaginatedResponse, PaginationRequest

# Several schemas below expose a field literally named ``date``. Under
# ``from __future__ import annotations`` the class attribute shadows the imported
# ``date`` type when Pydantic resolves the annotation, so those fields reference
# this alias instead.
DateType = date


# ===========================================================================
# Validation helpers
# ===========================================================================


def _validate_non_negative_minutes(value: int, field_name: str) -> int:
    """Validate that minutes are non-negative."""
    if value < 0:
        raise ValueError(f"{field_name} must be greater than or equal to 0")
    return value


# ===========================================================================
# Attendance — request schemas (DTOs)
# ===========================================================================


class AttendanceLiveQuery(BaseSchema):
    """Query parameters for ``WS/GET /attendance/live`` (live feed)."""

    branch_id: int | None = Field(default=None, description="Scope the feed to a specific branch.")


class AttendanceDailyQuery(PaginationRequest):
    """Query parameters for ``GET /attendance/daily`` (daily grid)."""

    date: DateType = Field(..., description="Target calendar date.")
    branch_id: int | None = Field(default=None, description="Filter employees by branch.")
    department_id: int | None = Field(default=None, description="Filter employees by department.")


class AttendanceMonthlyQuery(BaseSchema):
    """Query parameters for ``GET /attendance/monthly/{employee_id}``."""

    month: int = Field(..., ge=1, le=12, description="Target calendar month (1-12).")
    year: int = Field(..., ge=1900, le=2100, description="Target calendar year.")


class AttendanceLogsQuery(PaginationRequest):
    """Query parameters for ``GET /attendance/logs`` (raw punch list)."""

    employee_id: int | None = Field(default=None, description="Filter by employee.")
    device_id: int | None = Field(default=None, description="Filter by biometric device.")
    from_date: date = Field(
        ...,
        validation_alias="from",
        serialization_alias="from",
        description="Start date of the log window.",
    )
    to_date: date = Field(
        ...,
        validation_alias="to",
        serialization_alias="to",
        description="End date of the log window.",
    )


class AttendanceManualCreateRequest(BaseSchema):
    """Body for ``POST /attendance/manual`` (onboard a manual entry)."""

    employee_id: int = Field(..., description="ID of the employee.")
    date: DateType = Field(..., description="Date of the attendance.")
    in_time: datetime = Field(..., description="Punch-in timestamp (ISO format).")
    out_time: datetime = Field(..., description="Punch-out timestamp (ISO format).")
    reason: str = Field(..., min_length=3, max_length=500, description="Reason for manual entry.")

    @model_validator(mode="after")
    def _validate_times(self) -> AttendanceManualCreateRequest:
        """Validate that punch out occurs strictly after punch in."""
        if self.out_time <= self.in_time:
            raise ValueError("out_time must be chronologically after in_time")
        return self


class AttendanceCorrectionCreateRequest(BaseSchema):
    """Body for ``POST /attendance/corrections`` (request regularization)."""

    employee_id: int = Field(..., description="ID of the employee.")
    date: DateType = Field(..., description="Date of the attendance day to correct.")
    requested_in: datetime = Field(..., description="Requested punch-in timestamp.")
    requested_out: datetime = Field(..., description="Requested punch-out timestamp.")
    reason: str = Field(..., min_length=3, max_length=500, description="Reason for correction.")

    @model_validator(mode="after")
    def _validate_times(self) -> AttendanceCorrectionCreateRequest:
        """Validate that requested out occurs strictly after requested in."""
        if self.requested_out <= self.requested_in:
            raise ValueError("requested_out must be chronologically after requested_in")
        return self


class AttendanceCorrectionApproveRequest(BaseSchema):
    """Body for ``PUT /attendance/corrections/{id}/approve``."""

    decision: ApprovalStatus = Field(..., description="Approval decision: approved or rejected.")
    comment: str | None = Field(default=None, max_length=500, description="Approver's remarks.")


class AttendanceMissingPunchesQuery(PaginationRequest):
    """Query parameters for ``GET /attendance/missing-punches``."""

    from_date: date = Field(
        ...,
        validation_alias="from",
        serialization_alias="from",
        description="Start date of analysis.",
    )
    to_date: date = Field(
        ...,
        validation_alias="to",
        serialization_alias="to",
        description="End date of analysis.",
    )
    branch_id: int | None = Field(default=None, description="Filter by branch.")


class AttendanceLockRequest(BaseSchema):
    """Body for ``POST /attendance/lock`` (freeze attendance period)."""

    period_start: date = Field(..., description="Start of the freeze range.")
    period_end: date = Field(..., description="End of the freeze range.")
    scope: LockScope = Field(..., description="Lock scope: company or branch.")
    branch_id: int | None = Field(
        default=None, description="Branch ID (required if scope is branch)."
    )
    reason: str | None = Field(default=None, max_length=500, description="Reason for freeze.")

    @model_validator(mode="after")
    def _validate_period(self) -> AttendanceLockRequest:
        """Validate that period end does not precede period start, and scope matches."""
        if self.period_end < self.period_start:
            raise ValueError("period_end must be on or after period_start")
        if self.scope == LockScope.BRANCH and self.branch_id is None:
            raise ValueError("branch_id is required when scope is branch")
        return self


class AttendanceUnlockRequest(BaseSchema):
    """Body for ``POST /attendance/unlock`` (unfreeze attendance period).body"""

    period_start: date = Field(..., description="Start of the freeze range to unlock.")
    period_end: date = Field(..., description="End of the freeze range to unlock.")
    scope: LockScope = Field(..., description="Lock scope: company or branch.")
    branch_id: int | None = Field(
        default=None, description="Branch ID (required if scope is branch)."
    )
    reason: str | None = Field(default=None, max_length=500, description="Reason for unfreeze.")

    @model_validator(mode="after")
    def _validate_period(self) -> AttendanceUnlockRequest:
        """Validate that period end does not precede period start, and scope matches."""
        if self.period_end < self.period_start:
            raise ValueError("period_end must be on or after period_start")
        if self.scope == LockScope.BRANCH and self.branch_id is None:
            raise ValueError("branch_id is required when scope is branch")
        return self



class AttendanceRecomputeRequest(BaseSchema):
    """Body for ``POST /attendance/{employee_id}/recompute``."""

    date: DateType = Field(..., description="Target date for recalculation.")


# ===========================================================================
# Attendance — response schemas (DTOs)
# ===========================================================================


class AttendanceLiveMessageSchema(BaseSchema):
    """Websocket realtime event payload (contract §18.5)."""

    employee_id: int = Field(..., description="ID of the employee who punched.")
    employee_name: str = Field(..., description="Name of the employee.")
    punch_time: datetime = Field(..., description="Timestamp of the punch.")
    punch_type: PunchType = Field(..., description="Punch type: in, out, etc.")
    branch_id: int = Field(..., description="Branch where the punch was recorded.")
    device_id: int | None = Field(default=None, description="Source device ID (if biometric).")


class AttendanceDailySchema(BaseSchema):
    """Daily attendance summary representation (contract §11 / daily grid)."""

    employee_id: int = Field(..., description="ID of the employee.")
    status: AttendanceDayStatus = Field(..., description="Operational status for the day.")
    first_in: datetime | None = Field(
        default=None,
        validation_alias="first_punch_in",
        description="First check-in timestamp.",
    )
    last_out: datetime | None = Field(
        default=None,
        validation_alias="last_punch_out",
        description="Last check-out timestamp.",
    )
    worked_minutes: int = Field(
        default=0,
        validation_alias="total_working_minutes",
        description="Calculated total working minutes.",
    )
    late_minutes: int = Field(
        default=0,
        description="Minutes late relative to shift.",
    )
    overtime_minutes: int = Field(
        default=0,
        description="Approved overtime minutes.",
    )
    is_locked: bool = Field(
        default=False,
        description="Whether this day is locked from mutations (post-payroll).",
    )

    @field_validator("worked_minutes")
    @classmethod
    def _validate_worked_minutes(cls, value: int) -> int:
        return _validate_non_negative_minutes(value, "worked_minutes")

    @field_validator("late_minutes")
    @classmethod
    def _validate_late_minutes(cls, value: int) -> int:
        return _validate_non_negative_minutes(value, "late_minutes")

    @field_validator("overtime_minutes")
    @classmethod
    def _validate_overtime_minutes(cls, value: int) -> int:
        return _validate_non_negative_minutes(value, "overtime_minutes")


class AttendanceMonthlyDaySchema(BaseSchema):
    """Compact daily representation in monthly calendar (contract §11)."""

    attendance_date: date = Field(..., description="Date.")
    status: AttendanceDayStatus = Field(..., description="Day status.")
    first_in: datetime | None = Field(
        default=None,
        validation_alias="first_punch_in",
        description="First check-in timestamp.",
    )
    last_out: datetime | None = Field(
        default=None,
        validation_alias="last_punch_out",
        description="Last check-out timestamp.",
    )
    worked_minutes: int = Field(
        default=0,
        validation_alias="total_working_minutes",
        description="Worked minutes.",
    )
    is_locked: bool = Field(
        default=False,
        description="Whether this day falls in a locked period.",
    )
    leave_id: int | None = Field(
        default=None,
        description="Associated leave request ID (if on leave).",
    )
    is_regularized: bool = Field(
        default=False,
        description="True if manually corrected/regularized.",
    )
    remarks: str | None = Field(default=None, description="Optional admin remarks.")


class AttendancePunchSchema(BaseSchema):
    """Raw, append-only punch record representation (attendance_punches)."""

    id: int = Field(..., description="Primary key.")
    org_id: int = Field(..., description="Tenant organization.")
    employee_id: int = Field(..., description="ID of the employee.")
    attendance_day_id: int = Field(..., description="Associated daily summary ID.")
    punch_type: PunchType = Field(..., description="Punch event type.")
    punch_time: datetime = Field(..., description="Punch event timestamp.")
    sequence_no: int = Field(..., description="Day-local chronological sequence number.")
    punch_source: PunchSource = Field(..., description="How the punch was ingested.")
    device_id: int | None = Field(default=None, description="Biometric device ID (if biometric).")
    latitude: Decimal | None = Field(
        default=None,
        ge=-90,
        le=90,
        max_digits=9,
        decimal_places=6,
        description="GPS Latitude.",
    )
    longitude: Decimal | None = Field(
        default=None,
        ge=-180,
        le=180,
        max_digits=9,
        decimal_places=6,
        description="GPS Longitude.",
    )
    is_valid: bool = Field(default=True, description="Whether this punch is valid/considered.")
    created_at: datetime = Field(..., description="Log creation timestamp.")


class AttendancePenaltySchema(BaseSchema):
    """Attendance penalty representation (attendance_penalties)."""

    id: int = Field(..., description="Primary key.")
    org_id: int = Field(..., description="Tenant organization.")
    employee_id: int = Field(..., description="ID of the employee.")
    attendance_day_id: int = Field(..., description="Associated daily summary ID.")
    penalty_type: PenaltyType = Field(..., description="Type of penalty.")
    penalty_unit: PenaltyUnit = Field(..., description="Unit of deduction.")
    penalty_value: Decimal = Field(
        ..., ge=0, max_digits=10, decimal_places=2, description="Deduction value."
    )
    status: PenaltyStatus = Field(..., description="Status: active or waived.")
    applied_by: int = Field(..., description="ID of the user who applied the penalty.")
    payroll_reference_id: int | None = Field(
        default=None, description="Deferred reference to payroll line item."
    )
    remarks: str | None = Field(default=None, description="Remarks / justification.")
    created_at: datetime = Field(..., description="Created timestamp.")
    updated_at: datetime = Field(..., description="Updated timestamp.")
    is_deleted: bool = Field(default=False, description="Soft-delete flag.")


class AttendanceDayDetailSchema(BaseSchema):
    """Detailed daily attendance summary with nested punches and penalties."""

    id: int = Field(..., description="Primary key.")
    org_id: int = Field(..., description="Tenant organization ID.")
    employee_id: int = Field(..., description="Employee ID.")
    attendance_date: date = Field(..., description="Date.")
    shift_id: int | None = Field(default=None, description="Assigned shift ID.")
    expected_start_time: time | None = Field(default=None, description="Shift start.")
    expected_end_time: time | None = Field(default=None, description="Shift end.")
    status: AttendanceDayStatus = Field(..., description="Day summary status.")
    first_punch_in: datetime | None = Field(default=None, description="First check-in.")
    last_punch_out: datetime | None = Field(default=None, description="Last check-out.")
    total_working_minutes: int = Field(default=0, description="Working duration.")
    total_break_minutes: int = Field(default=0, description="Break duration.")
    overtime_minutes: int = Field(default=0, description="Overtime duration.")
    late_minutes: int = Field(default=0, description="Late arrival duration.")
    early_leaving_minutes: int = Field(default=0, description="Early departure duration.")
    leave_id: int | None = Field(default=None, description="Associated leave ID.")
    is_regularized: bool = Field(default=False, description="Regularization flag.")
    source: AttendanceSource = Field(..., description="Data source.")
    marked_by: int | None = Field(default=None, description="User who marked this record.")
    remarks: str | None = Field(default=None, description="Remarks.")
    created_at: datetime = Field(..., description="Created at.")
    updated_at: datetime = Field(..., description="Updated at.")
    created_by: int | None = Field(default=None, description="Created by user ID.")
    updated_by: int | None = Field(default=None, description="Updated by user ID.")

    punches: list[AttendancePunchSchema] = Field(
        default_factory=list, description="Punch timeline logs for the day."
    )
    penalties: list[AttendancePenaltySchema] = Field(
        default_factory=list, description="Penalties triggered by attendance issues."
    )


class AttendanceCorrectionSchema(BaseSchema):
    """Representation of an attendance correction (regularization) request."""

    id: int = Field(..., description="Primary key.")
    employee_id: int = Field(..., description="ID of the employee.")
    attendance_date: date = Field(
        ...,
        validation_alias="attendance_date",
        serialization_alias="date",
        description="Date of attendance day corrected.",
    )
    old_punch_time: str | None = Field(default=None, description="Original punch time string.")
    new_punch_time: str = Field(..., description="New requested punch time string.")
    employee_reason: str | None = Field(default=None, description="Reason for request.")
    applied_on: datetime = Field(..., description="Submission timestamp.")
    status: ApprovalStatus = Field(..., description="Status: pending, approved, or rejected.")
    created_at: datetime = Field(..., description="Log creation timestamp.")
    updated_at: datetime = Field(..., description="Log update timestamp.")


class AttendanceMissingPunchSchema(BaseSchema):
    """Schema for a flagged missing punch record (contract §11)."""

    employee_id: int = Field(..., description="ID of the employee.")
    employee_code: str = Field(..., description="UI display code of the employee.")
    employee_name: str = Field(..., description="Full name of the employee.")
    attendance_date: date = Field(..., description="Date of missing punch.")
    punch_time: datetime | None = Field(
        default=None, description="The single punch timestamp that exists."
    )
    punch_type: PunchType | None = Field(
        default=None, description="The type of the single punch that exists."
    )
    missing_type: PunchType = Field(
        ..., description="The type of punch that is missing (in or out)."
    )


# ===========================================================================
# Paginated list responses (reuse the shared paged envelope)
# ===========================================================================


class AttendanceDailyListResponse(PaginatedResponse[AttendanceDailySchema]):
    """Paginated daily attendance list response."""


class AttendanceLogsResponse(PaginatedResponse[AttendancePunchSchema]):
    """Paginated raw punch logs list response."""


class AttendanceMissingPunchesResponse(PaginatedResponse[AttendanceMissingPunchSchema]):
    """Paginated missing punches list response."""


class AttendanceLockSchema(BaseSchema):
    """Response schema representing an attendance lock record."""

    id: int
    org_id: int
    lock_month: int
    lock_year: int
    lock_type: str
    branch_id: int | None
    status: str
    locked_by: int
    locked_at: datetime
    reason: str | None
    created_at: datetime
    updated_at: datetime


__all__ = [
    # requests/queries
    "AttendanceLiveQuery",
    "AttendanceDailyQuery",
    "AttendanceMonthlyQuery",
    "AttendanceLogsQuery",
    "AttendanceManualCreateRequest",
    "AttendanceCorrectionCreateRequest",
    "AttendanceCorrectionApproveRequest",
    "AttendanceMissingPunchesQuery",
    "AttendanceLockRequest",
    "AttendanceUnlockRequest",
    "AttendanceRecomputeRequest",
    # responses/DTOs
    "AttendanceLiveMessageSchema",
    "AttendanceDailySchema",
    "AttendanceMonthlyDaySchema",
    "AttendancePunchSchema",
    "AttendancePenaltySchema",
    "AttendanceDayDetailSchema",
    "AttendanceCorrectionSchema",
    "AttendanceMissingPunchSchema",
    "AttendanceLockSchema",
    # paginated envelopes
    "AttendanceDailyListResponse",
    "AttendanceLogsResponse",
    "AttendanceMissingPunchesResponse",
]

