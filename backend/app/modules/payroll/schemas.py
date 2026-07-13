"""Payroll Management — Pydantic request/response schemas (DTOs).

Defines validation and serialization rules for payroll settings, payroll groups,
employee assignments, salary cycles, column settings, computed runs/rows,
payslips, and bulk adjustments (penalties, extra hours).
"""

from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal

from pydantic import Field, field_validator, model_validator

from app.modules.payroll.constants import (
    AdjustedStatus,
    AdjustmentSource,
    AttendanceMode,
    PaymentStatus,
    PayrollSalaryType,
    PayrollType,
    WorkingHourType,
)
from app.shared.base.schema import BaseSchema
from app.shared.schemas.pagination import PaginatedResponse

# ===========================================================================
# 1. Payroll Configuration
# ===========================================================================

class PayrollSettingResponseSchema(BaseSchema):
    """Response schema for representing organization-level payroll settings."""

    id: int = Field(..., description="Unique setting ID.")
    org_id: int = Field(..., description="Organization ID.")
    working_hour_type: WorkingHourType = Field(..., description="Working hour type context.")
    full_day_working_hours: time = Field(..., description="Full day working hours boundary.")
    half_day_working_hours: time = Field(..., description="Half day working hours boundary.")
    attendance_mode: AttendanceMode = Field(..., description="Mode of attendance calculation.")
    off_day_compensation: str = Field(..., description="Type of off-day compensation.")
    off_day_wage_multiplier: Decimal = Field(..., description="Off-day wage multiplier.")
    daily_wage_formula: str = Field(..., description="Formula for daily wage.")
    overtime_type: str = Field(..., description="Overtime calculation type.")
    overtime_hourly_multiplier: Decimal = Field(..., description="Hourly multiplier for overtime.")
    overtime_buffer_period: time = Field(..., description="Buffer period before overtime starts.")
    overtime_period_interval: str | None = Field(default=None, description="Interval for overtime periods.")
    full_day_penalty_enabled: bool = Field(..., description="Whether full day penalty is enabled.")
    half_day_penalty_enabled: bool = Field(..., description="Whether half day penalty is enabled.")
    late_coming_penalty_enabled: bool = Field(..., description="Whether late coming penalty is enabled.")
    grace_time: time = Field(..., description="Late coming grace time.")
    updated_by: int | None = Field(default=None, description="User ID of last updater.")
    created_at: datetime = Field(..., description="Creation timestamp.")
    updated_at: datetime = Field(..., description="Last update timestamp.")


class PayrollSettingUpdateSchema(BaseSchema):
    """Payload for updating organization-level payroll settings."""

    working_hour_type: WorkingHourType | None = Field(default=None, description="Working hour type.")
    full_day_working_hours: time | None = Field(default=None, description="Full day working hours.")
    half_day_working_hours: time | None = Field(default=None, description="Half day working hours.")
    attendance_mode: AttendanceMode | None = Field(default=None, description="Attendance calculation mode.")
    off_day_compensation: str | None = Field(default=None, max_length=30, description="Off-day compensation type.")
    off_day_wage_multiplier: Decimal | None = Field(default=None, description="Off-day wage multiplier.")
    daily_wage_formula: str | None = Field(default=None, max_length=50, description="Daily wage formula.")
    overtime_type: str | None = Field(default=None, max_length=30, description="Overtime pay type.")
    overtime_hourly_multiplier: Decimal | None = Field(default=None, description="Overtime hourly multiplier.")
    overtime_buffer_period: time | None = Field(default=None, description="Overtime buffer period.")
    overtime_period_interval: str | None = Field(default=None, max_length=10, description="Overtime period interval.")
    full_day_penalty_enabled: bool | None = Field(default=None, description="Enable full-day penalties.")
    half_day_penalty_enabled: bool | None = Field(default=None, description="Enable half-day penalties.")
    late_coming_penalty_enabled: bool | None = Field(default=None, description="Enable late coming penalties.")
    grace_time: time | None = Field(default=None, description="Grace time.")

    @model_validator(mode="after")
    def validate_multipliers(self) -> PayrollSettingUpdateSchema:
        if self.off_day_wage_multiplier is not None and self.off_day_wage_multiplier < Decimal("0"):
            raise ValueError("off_day_wage_multiplier must be greater than or equal to 0.")
        if self.overtime_hourly_multiplier is not None and self.overtime_hourly_multiplier < Decimal("0"):
            raise ValueError("overtime_hourly_multiplier must be greater than or equal to 0.")
        return self


# ===========================================================================
# 2. Payroll Groups ("Salary Structures")
# ===========================================================================

class PayrollGroupResponseSchema(BaseSchema):
    """Response schema representing a payroll group (Salary Structure)."""

    id: int = Field(..., description="Unique payroll group ID.")
    org_id: int = Field(..., description="Organization ID.")
    name: str = Field(..., description="Name of the payroll group.")
    payroll_type: PayrollType = Field(..., description="Payroll type configuration.")
    is_default: bool = Field(..., description="True if group is default for organization.")
    is_deleted: bool = Field(..., description="True if group is soft-deleted.")
    created_by: int | None = Field(default=None, description="User ID of creator.")
    updated_by: int | None = Field(default=None, description="User ID of last updater.")
    created_at: datetime = Field(..., description="Creation timestamp.")
    updated_at: datetime = Field(..., description="Last update timestamp.")


class PayrollGroupCreateSchema(BaseSchema):
    """Payload for creating a new payroll group."""

    name: str = Field(..., min_length=1, max_length=150, description="Name of the payroll group.")
    payroll_type: PayrollType = Field(..., description="Type of payroll computation.")
    is_default: bool = Field(default=False, description="Set as default group.")

    @field_validator("name")
    @classmethod
    def validate_name_not_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("name must not be empty or whitespace.")
        return value.strip()


class PayrollGroupUpdateSchema(BaseSchema):
    """Payload for patching an existing payroll group."""

    name: str | None = Field(default=None, min_length=1, max_length=150, description="Name of the payroll group.")
    payroll_type: PayrollType | None = Field(default=None, description="Type of payroll computation.")
    is_default: bool | None = Field(default=None, description="Set as default group.")

    @field_validator("name")
    @classmethod
    def validate_name_not_empty(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("name must not be empty or whitespace.")
        return value.strip() if value is not None else None


class PayrollGroupListResponse(PaginatedResponse[PayrollGroupResponseSchema]):
    """Paginated response containing list of payroll groups."""


# ===========================================================================
# 3. Employee Group Assignment
# ===========================================================================

class EmployeeGroupAssignRequestSchema(BaseSchema):
    """Payload for assigning an employee to a payroll group."""

    payroll_group_id: int = Field(..., description="Payroll group ID to assign.")
    salary_type: PayrollSalaryType = Field(..., description="Salary type context.")


class EmployeeGroupAssignmentResponseSchema(BaseSchema):
    """Response schema for representing an employee's group assignment."""

    id: int = Field(..., description="Unique assignment ID.")
    employee_id: int = Field(..., description="Employee ID.")
    payroll_group_id: int = Field(..., description="Assigned payroll group ID.")
    salary_type: PayrollSalaryType = Field(..., description="Salary type: monthly, hourly.")
    previous_group_id: int | None = Field(default=None, description="ID of previous group if any.")
    assigned_by: int = Field(..., description="User ID who assigned the group.")
    assigned_at: datetime = Field(..., description="Timestamp of assignment.")
    created_at: datetime = Field(..., description="Record creation timestamp.")
    updated_at: datetime = Field(..., description="Record update timestamp.")


# ===========================================================================
# 4. Column Settings
# ===========================================================================

class PayrollColumnSettingSchema(BaseSchema):
    """Response schema for a single column setting configuration."""

    id: int = Field(..., description="Column setting ID.")
    payroll_group_id: int = Field(..., description="Associated payroll group ID.")
    column_key: str = Field(..., description="Technical identifier key for the column.")
    column_label: str = Field(..., description="User-friendly label/header.")
    is_visible: bool = Field(..., description="Visibility status on payslip/records.")
    display_order: int = Field(..., description="Ordering rank (lower is shown first).")
    updated_by: int | None = Field(default=None, description="User ID of last updater.")
    updated_at: datetime = Field(..., description="Last update timestamp.")


class PayrollColumnSettingsResponseSchema(BaseSchema):
    """Response schema enclosing all column settings for a group."""

    columns: list[PayrollColumnSettingSchema] = Field(..., description="List of column settings.")


class PayrollColumnSettingInputSchema(BaseSchema):
    """Payload representing a single column setting replacement entry."""

    column_key: str = Field(..., min_length=1, max_length=50, description="Technical identifier key.")
    column_label: str = Field(..., min_length=1, max_length=100, description="User-facing label.")
    is_visible: bool = Field(default=True, description="Visibility status.")
    display_order: int = Field(..., ge=0, description="Sequence display order.")


class PayrollColumnSettingsReplaceSchema(BaseSchema):
    """Payload for replacing all column settings for a payroll group."""

    columns: list[PayrollColumnSettingInputSchema] = Field(..., description="Full list of column settings to replace.")


# ===========================================================================
# 5. Payroll Cycles
# ===========================================================================

class PayrollCycleResponseSchema(BaseSchema):
    """Response schema representing a payroll salary cycle."""

    id: int = Field(..., description="Unique cycle ID.")
    payroll_group_id: int = Field(..., description="Payroll group ID.")
    cycle_date: date = Field(..., description="Target date of the cycle.")
    is_finalized: bool = Field(..., description="True if cycle is finalized/locked.")
    created_by: int | None = Field(default=None, description="User ID of creator.")
    created_at: datetime = Field(..., description="Creation timestamp.")


class PayrollCycleCreateSchema(BaseSchema):
    """Payload for defining a new payroll cycle."""

    payroll_group_id: int = Field(..., description="Target payroll group ID.")
    cycle_date: date = Field(..., description="Target date of the cycle (YYYY-MM-DD).")


class PayrollCycleUpdateSchema(BaseSchema):
    """Payload for updating a payroll cycle's date (only allowed when unfinalized)."""

    cycle_date: date = Field(..., description="New target date of the cycle (YYYY-MM-DD).")


class PayrollCycleListResponse(PaginatedResponse[PayrollCycleResponseSchema]):
    """Paginated response containing list of payroll salary cycles."""


# ===========================================================================
# 6. Payroll Processing & Finalization
# ===========================================================================

class PayrollProcessRequestSchema(BaseSchema):
    """Payload for generating, recalculating, previewing, or locking payroll runs."""

    payroll_group_id: int = Field(..., description="Target payroll group ID.")
    cycle_from: date = Field(..., description="Cycle start date (inclusive).")
    cycle_to: date = Field(..., description="Cycle end date (inclusive).")
    employee_ids: list[int] | None = Field(default=None, description="Optional subset of employees to calculate.")

    @model_validator(mode="after")
    def validate_date_range(self) -> PayrollProcessRequestSchema:
        if self.cycle_to < self.cycle_from:
            raise ValueError("cycle_to must be on or after cycle_from.")
        return self


class PayrollProcessItemResultSchema(BaseSchema):
    """Outcome status for an individual employee's payroll computation."""

    employee_id: int = Field(..., description="Subject employee ID.")
    success: bool = Field(..., description="True if compute succeeded, False otherwise.")
    error_code: str | None = Field(default=None, description="Stable error code if failed.")
    error_message: str | None = Field(default=None, description="Readable message detail if failed.")


class PayrollProcessResponseSchema(BaseSchema):
    """Response containing execution results of a payroll run computation."""

    results: list[PayrollProcessItemResultSchema] = Field(..., description="Individual calculation status outcomes.")


class FinalizedPayrollRunResponseSchema(BaseSchema):
    """Response schema representing a finalized payroll lock run."""

    id: int = Field(..., description="Unique run ID.")
    org_id: int = Field(..., description="Organization ID.")
    payroll_group_id: int = Field(..., description="Payroll group ID.")
    cycle_from: date = Field(..., description="Locked period start date.")
    cycle_to: date = Field(..., description="Locked period end date.")
    payroll_module: str = Field(..., description="Calculated module designation.")
    finalized_amount: Decimal = Field(..., description="Total finalized payment amount.")
    finalized_at: datetime = Field(..., description="Timestamp of locking.")
    finalized_by: int = Field(..., description="User ID of finalizer.")
    paid_amount: Decimal | None = Field(default=None, description="Amount recorded as paid.")
    paid_at: datetime | None = Field(default=None, description="Timestamp when paid.")
    payment_status: PaymentStatus = Field(..., description="Status: pending, paid, partial.")
    is_definalized: bool = Field(..., description="True if run has been unlocked.")
    definalized_at: datetime | None = Field(default=None, description="Timestamp of unlocking.")
    definalized_by: int | None = Field(default=None, description="User ID who unlocked.")
    created_at: datetime = Field(..., description="Creation timestamp.")
    updated_at: datetime = Field(..., description="Last update timestamp.")


class RecordPaymentRequestSchema(BaseSchema):
    """Payload for recording payment details against a finalized run."""

    paid_amount: Decimal = Field(..., ge=0, description="Amount paid.")
    payment_status: PaymentStatus = Field(..., description="Status: paid, partial, pending.")
    paid_at: datetime | None = Field(default=None, description="Timestamp of payment (defaults to now).")


class FinalizedPayrollRunListResponse(PaginatedResponse[FinalizedPayrollRunResponseSchema]):
    """Paginated response containing list of finalized payroll runs."""


# ===========================================================================
# 7. Payroll Computed Records
# ===========================================================================

class PayrollComputedRowSchema(BaseSchema):
    """Response schema for a single employee's computed payroll metrics row."""

    id: int | None = Field(default=None, description="Unique row ID.")
    payroll_group_id: int = Field(..., description="Associated payroll group ID.")
    employee_id: int = Field(..., description="Employee ID.")
    cycle_from: date = Field(..., description="Calculated period start.")
    cycle_to: date = Field(..., description="Calculated period end.")
    total_days: int = Field(..., description="Total days in target calendar range.")
    full_day_count: int = Field(..., description="Count of full attendance days.")
    half_day_count: int = Field(..., description="Count of half attendance days.")
    off_day_count: int = Field(..., description="Count of off-days / week-offs.")
    paid_leave_count: Decimal = Field(..., description="Count of paid leaves approved.")
    paid_day_count: Decimal = Field(..., description="Total days eligible for payment.")
    unpaid_day_count: Decimal = Field(..., description="Days absent / unpaid.")
    daily_wage: Decimal = Field(..., description="Derived daily wage rate.")
    gross_wages: Decimal = Field(..., description="Basic gross wages computed.")
    overtime_amount: Decimal = Field(..., description="Calculated overtime earnings.")
    penalties_amount: Decimal = Field(..., description="Total penalties deducted.")
    extras_amount: Decimal = Field(..., description="Extra hour additions or adjustments.")
    gross_earnings: Decimal = Field(..., description="Gross earnings before deductions.")
    loan_advance_deduction: Decimal = Field(..., description="Settlement deductions (loans/advances).")
    arrears_amount: Decimal = Field(..., description="Settlement additions (arrears).")
    to_pay: Decimal = Field(..., description="Net payout amount (gross_earnings - deductions).")
    balance_arrears: Decimal = Field(..., description="Unresolved residual balance.")
    payment_method: str | None = Field(default=None, description="Method of payment.")
    is_finalized: bool = Field(..., description="True if locked under a finalized run.")
    finalized_run_id: int | None = Field(default=None, description="Locking run ID reference.")
    computed_by: int | None = Field(default=None, description="User ID of computer.")
    computed_at: datetime = Field(..., description="Computation timestamp.")


class PayrollRecordListResponse(PaginatedResponse[PayrollComputedRowSchema]):
    """Paginated response containing list of computed payroll rows."""


class PayrollPreviewResponseSchema(BaseSchema):
    """Response containing preview list of computed rows without DB persistence."""

    items: list[PayrollComputedRowSchema] = Field(..., description="Calculated computed rows preview.")


class PayrollSummaryResponseSchema(BaseSchema):
    """Response schema summarizing aggregate metrics for a cycle range."""

    headcount: int = Field(..., description="Total employees calculated.")
    total_gross_earnings: Decimal = Field(..., description="Aggregated gross earnings.")
    total_to_pay: Decimal = Field(..., description="Aggregated net payout.")
    total_overtime: Decimal = Field(..., description="Aggregated overtime.")
    total_penalties: Decimal = Field(..., description="Aggregated penalties.")
    total_deductions: Decimal = Field(..., description="Aggregated loan/advance deductions.")


# ===========================================================================
# 8. Payslips
# ===========================================================================

class PayslipSectionItemSchema(BaseSchema):
    """A key-value descriptor detailing a single entry line on a payslip."""

    key: str = Field(..., description="Identifier key.")
    label: str = Field(..., description="User-facing display label.")
    value: Decimal | str = Field(..., description="Calculated value or textual description.")


class PayslipResponseSchema(BaseSchema):
    """Response schema for showing on-demand rendered payslip breakdown details."""

    row_id: int = Field(..., description="Associated computed row ID.")
    employee_id: int = Field(..., description="Subject employee ID.")
    employee_name: str | None = Field(default=None, description="Subject employee name (resolved).")
    employee_code: str | None = Field(default=None, description="Subject employee code (resolved).")
    cycle_from: date = Field(..., description="Payslip start date.")
    cycle_to: date = Field(..., description="Payslip end date.")
    earnings: list[PayslipSectionItemSchema] = Field(..., description="List of earning line items.")
    deductions: list[PayslipSectionItemSchema] = Field(..., description="List of deduction line items.")
    net_pay: Decimal = Field(..., description="Earning total minus deduction total.")
    payment_method: str | None = Field(default=None, description="Determined payment method.")
    is_finalized: bool = Field(..., description="True if row is finalized/locked.")


# ===========================================================================
# 9. Attendance Adjustments
# ===========================================================================

class AttendanceAdjustmentResponseSchema(BaseSchema):
    """Response schema representing a bulk attendance adjustment record."""

    id: int = Field(..., description="Adjustment record ID.")
    org_id: int = Field(..., description="Organization ID.")
    employee_id: int = Field(..., description="Subject employee ID.")
    attendance_date: date = Field(..., description="Adjusted attendance date.")
    original_status: AdjustedStatus | None = Field(default=None, description="Original status code.")
    adjusted_status: AdjustedStatus = Field(..., description="New adjusted status code (FD, HD, A, WO, LWP).")
    is_forced_overwrite: bool = Field(..., description="Forced overwrite switch.")
    has_punch_error: bool = Field(..., description="Whether record had punch errors.")
    adjustment_source: AdjustmentSource = Field(..., description="Source: spreadsheet or quick_action.")
    adjusted_by: int = Field(..., description="User ID of adjuster.")
    adjusted_at: datetime = Field(..., description="Timestamp of adjustment.")


class AttendanceAdjustmentCreateSchema(BaseSchema):
    """Payload for creating / upserting an attendance adjustment."""

    employee_id: int = Field(..., description="Subject employee ID.")
    attendance_date: date = Field(..., description="Adjustment target date.")
    adjusted_status: AdjustedStatus = Field(..., description="Target status (FD, HD, A, WO, LWP).")
    original_status: AdjustedStatus | None = Field(default=None, description="Optional original status.")
    adjustment_source: AdjustmentSource = Field(default=AdjustmentSource.SPREADSHEET, description="Source of action.")
    is_forced_overwrite: bool = Field(default=False, description="Overwrite status regardless of lock checks.")
    has_punch_error: bool = Field(default=False, description="Flag punch error indicator.")


class AttendanceAdjustmentUpdateSchema(BaseSchema):
    """Payload for updating an existing attendance adjustment."""

    adjusted_status: AdjustedStatus | None = Field(default=None, description="Target status (FD, HD, A, WO, LWP).")
    original_status: AdjustedStatus | None = Field(default=None, description="Optional original status.")
    is_forced_overwrite: bool | None = Field(default=None, description="Overwrite switch.")
    has_punch_error: bool | None = Field(default=None, description="Flag punch error indicator.")


class AttendanceAdjustmentListResponse(PaginatedResponse[AttendanceAdjustmentResponseSchema]):
    """Paginated response containing list of attendance adjustments."""


class AttendanceAdjustmentPenaltyCreateSchema(BaseSchema):
    """Payload for creating a penalty adjustment entry."""

    employee_id: int = Field(..., description="Subject employee ID.")
    attendance_date: date = Field(..., description="Target attendance date.")
    penalty_amount: Decimal = Field(..., gt=0, description="Amount of penalty.")
    remark: str | None = Field(default=None, max_length=500, description="Optional remark comments.")

    @field_validator("remark")
    @classmethod
    def validate_remark_not_empty(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("remark must not be empty or whitespace.")
        return value.strip() if value is not None else None


class AttendanceAdjustmentPenaltyResponseSchema(BaseSchema):
    """Response schema representing an attendance penalty entry."""

    id: int = Field(..., description="Penalty record ID.")
    employee_id: int = Field(..., description="Employee ID.")
    attendance_date: date = Field(..., description="Attendance date.")
    penalty_amount: Decimal = Field(..., description="Calculated penalty amount.")
    remark: str | None = Field(default=None, description="Remark description.")
    is_removed: bool = Field(..., description="True if removed / marked inactive.")
    created_by: int = Field(..., description="User ID of creator.")
    created_at: datetime = Field(..., description="Creation timestamp.")
    updated_at: datetime = Field(..., description="Last update timestamp.")


class AttendanceAdjustmentExtraHoursCreateSchema(BaseSchema):
    """Payload for creating an extra hours adjustment entry."""

    employee_id: int = Field(..., description="Subject employee ID.")
    attendance_date: date = Field(..., description="Target attendance date.")
    extra_hours: Decimal = Field(..., gt=0, le=24, description="Count of extra hours.")
    remark: str | None = Field(default=None, max_length=500, description="Optional remark details.")

    @field_validator("remark")
    @classmethod
    def validate_remark_not_empty(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("remark must not be empty or whitespace.")
        return value.strip() if value is not None else None


class AttendanceAdjustmentExtraHoursResponseSchema(BaseSchema):
    """Response schema representing an extra hours entry."""

    id: int = Field(..., description="Extra hours record ID.")
    employee_id: int = Field(..., description="Employee ID.")
    attendance_date: date = Field(..., description="Attendance date.")
    extra_hours: Decimal = Field(..., description="Recorded extra hours.")
    remark: str | None = Field(default=None, description="Remarks context.")
    created_by: int = Field(..., description="User ID of creator.")
    created_at: datetime = Field(..., description="Creation timestamp.")


# ===========================================================================
# Module exports
# ===========================================================================

__all__ = [
    # Settings
    "PayrollSettingResponseSchema",
    "PayrollSettingUpdateSchema",
    # Groups
    "PayrollGroupResponseSchema",
    "PayrollGroupCreateSchema",
    "PayrollGroupUpdateSchema",
    "PayrollGroupListResponse",
    # Assignments
    "EmployeeGroupAssignRequestSchema",
    "EmployeeGroupAssignmentResponseSchema",
    # Columns
    "PayrollColumnSettingSchema",
    "PayrollColumnSettingsResponseSchema",
    "PayrollColumnSettingInputSchema",
    "PayrollColumnSettingsReplaceSchema",
    # Cycles
    "PayrollCycleResponseSchema",
    "PayrollCycleCreateSchema",
    "PayrollCycleUpdateSchema",
    "PayrollCycleListResponse",
    # Processing
    "PayrollProcessRequestSchema",
    "PayrollProcessItemResultSchema",
    "PayrollProcessResponseSchema",
    "FinalizedPayrollRunResponseSchema",
    "RecordPaymentRequestSchema",
    "FinalizedPayrollRunListResponse",
    # Records
    "PayrollComputedRowSchema",
    "PayrollRecordListResponse",
    "PayrollPreviewResponseSchema",
    "PayrollSummaryResponseSchema",
    # Payslips
    "PayslipSectionItemSchema",
    "PayslipResponseSchema",
    # Adjustments
    "AttendanceAdjustmentResponseSchema",
    "AttendanceAdjustmentCreateSchema",
    "AttendanceAdjustmentUpdateSchema",
    "AttendanceAdjustmentListResponse",
    "AttendanceAdjustmentPenaltyCreateSchema",
    "AttendanceAdjustmentPenaltyResponseSchema",
    "AttendanceAdjustmentExtraHoursCreateSchema",
    "AttendanceAdjustmentExtraHoursResponseSchema",
]
