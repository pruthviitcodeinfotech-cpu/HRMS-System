"""Leave & Holiday Management — Pydantic request/response schemas (DTOs).

Defines validation and serialization rules for leave types, settings, balances,
adjustments, allocations, requests, templates, items, and assignments.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import Field, model_validator

from app.modules.leave.constants import (
    AdjustmentType,
    AllocationFrequency,
    AllocationSource,
    CarryForwardFrequency,
    EncashmentFrequency,
    LeaveCycle,
    LeaveRequestStatus,
)
from app.shared.base.schema import BaseSchema, TimestampSchema
from app.shared.schemas.pagination import PaginatedResponse

# ===========================================================================
# 1. Leave Type Schemas
# ===========================================================================


class LeaveTypeCreateRequest(BaseSchema):
    """Request schema for creating a leave type."""

    name: str = Field(..., max_length=100, description="Name of the leave type.")
    alias: str = Field(..., max_length=50, description="Short code/alias unique per org.")
    description: str | None = Field(default=None, description="Optional description.")
    auto_allocation_count: Decimal = Field(..., ge=0, description="Count of auto-allocated days.")
    allocation_frequency: AllocationFrequency = Field(
        default=AllocationFrequency.MONTHLY,
        description="Frequency of allocation (monthly, yearly)."
    )
    carry_forward_count: Decimal = Field(
        default=Decimal("0.00"), ge=0, description="Limit for carry forward."
    )
    carry_forward_frequency: CarryForwardFrequency = Field(
        default=CarryForwardFrequency.MONTHLY,
        description="Frequency of carry forward (monthly, yearly)."
    )
    encashment_enabled: bool = Field(default=False, description="Whether encashment is enabled.")
    encashment_limit: Decimal | None = Field(default=None, ge=0, description="Encashment limit.")
    encashment_frequency: EncashmentFrequency | None = Field(
        default=None, description="Frequency of encashment (monthly, yearly)."
    )
    is_active: bool = Field(default=True, description="Whether the leave type is active.")

    @model_validator(mode="after")
    def _validate_encashment(self) -> LeaveTypeCreateRequest:
        """Enforce that encashment_limit is required when encashment is enabled."""
        if self.encashment_enabled and self.encashment_limit is None:
            raise ValueError("encashment_limit is required when encashment is enabled")
        return self


class LeaveTypeUpdateRequest(BaseSchema):
    """Request schema for updating a leave type."""

    name: str | None = Field(default=None, max_length=100, description="Name of the leave type.")
    alias: str | None = Field(default=None, max_length=50, description="Short code/alias unique per org.")
    description: str | None = Field(default=None, description="Optional description.")
    auto_allocation_count: Decimal | None = Field(default=None, ge=0, description="Count of auto-allocated days.")
    allocation_frequency: AllocationFrequency | None = Field(
        default=None, description="Frequency of allocation (monthly, yearly)."
    )
    carry_forward_count: Decimal | None = Field(
        default=None, ge=0, description="Limit for carry forward."
    )
    carry_forward_frequency: CarryForwardFrequency | None = Field(
        default=None, description="Frequency of carry forward (monthly, yearly)."
    )
    encashment_enabled: bool | None = Field(default=None, description="Whether encashment is enabled.")
    encashment_limit: Decimal | None = Field(default=None, ge=0, description="Encashment limit.")
    encashment_frequency: EncashmentFrequency | None = Field(
        default=None, description="Frequency of encashment (monthly, yearly)."
    )
    is_active: bool | None = Field(default=None, description="Whether the leave type is active.")

    @model_validator(mode="after")
    def _validate_encashment(self) -> LeaveTypeUpdateRequest:
        """Enforce that encashment_limit is required when encashment is enabled."""
        enabled = self.encashment_enabled
        limit = self.encashment_limit
        if enabled is True and limit is None:
            raise ValueError("encashment_limit is required when encashment is enabled")
        return self


class LeaveTypeSchema(TimestampSchema):
    """Response schema for representing a leave type."""

    id: int = Field(..., description="Unique leave type ID.")
    org_id: int = Field(..., description="Organization ID.")
    name: str = Field(..., description="Name of the leave type.")
    alias: str = Field(..., description="Short code/alias unique per org.")
    description: str | None = Field(default=None, description="Description of the leave type.")
    auto_allocation_count: Decimal = Field(..., description="Auto allocated days count.")
    allocation_frequency: AllocationFrequency = Field(..., description="Allocation frequency.")
    carry_forward_count: Decimal = Field(..., description="Carry forward count limit.")
    carry_forward_frequency: CarryForwardFrequency = Field(..., description="Carry forward frequency.")
    encashment_enabled: bool = Field(..., description="Whether encashment is enabled.")
    encashment_limit: Decimal | None = Field(default=None, description="Encashment limit.")
    encashment_frequency: EncashmentFrequency | None = Field(default=None, description="Encashment frequency.")
    is_active: bool = Field(..., description="Active status.")
    is_deleted: bool = Field(..., description="Deleted status.")
    created_by: int | None = Field(default=None, description="Creator user ID.")
    updated_by: int | None = Field(default=None, description="Updater user ID.")


class LeaveTypeListResponse(PaginatedResponse[LeaveTypeSchema]):
    """Paginated list response for leave types."""


# ===========================================================================
# 2. Leave Settings / Cycle Configuration Schemas
# ===========================================================================


class LeaveSettingsUpdateRequest(BaseSchema):
    """Request schema for updating organization leave settings."""

    leave_cycle: LeaveCycle = Field(
        default=LeaveCycle.CALENDAR_YEAR,
        description="Type of leave cycle (calendar_year, financial_year)."
    )
    cycle_start_month: int = Field(
        default=1, ge=1, le=12, description="Start month of the leave cycle (1-12)."
    )


class LeaveSettingsSchema(TimestampSchema):
    """Response schema for representing organization leave settings."""

    id: int = Field(..., description="Unique settings ID.")
    org_id: int = Field(..., description="Organization ID.")
    leave_cycle: LeaveCycle = Field(..., description="Type of leave cycle.")
    cycle_start_month: int = Field(..., description="Start month of the leave cycle.")
    created_by: int | None = Field(default=None, description="Creator user ID.")
    updated_by: int | None = Field(default=None, description="Updater user ID.")


# ===========================================================================
# 3. Leave Balances, Allocations & Adjustments Schemas
# ===========================================================================


class EmployeeLeaveBalanceSchema(BaseSchema):
    """Response schema representing an employee's leave balance."""

    id: int = Field(..., description="Unique balance record ID.")
    employee_id: int = Field(..., description="Employee ID.")
    leave_type_id: int = Field(..., description="Leave type ID.")
    cycle_year: int = Field(..., description="Target cycle year.")
    opening_balance: Decimal = Field(..., description="Opening balance.")
    allocated: Decimal = Field(..., description="Allocated leaves.")
    used: Decimal = Field(..., description="Used leaves.")
    carried_forward: Decimal = Field(..., description="Carried forward leaves.")
    encashed: Decimal = Field(..., description="Encashed leaves.")
    adjusted: Decimal = Field(..., description="Adjusted leaves.")
    closing_balance: Decimal = Field(..., description="Closing balance.")
    updated_at: datetime = Field(..., description="Last updated timestamp.")
    updated_by: int | None = Field(default=None, description="Updater user ID.")
    leave_type: LeaveTypeSchema | None = Field(default=None, description="Nested leave type details.")


class LeaveBalanceListResponse(PaginatedResponse[EmployeeLeaveBalanceSchema]):
    """Paginated list response for leave balances."""


class LeaveCreditDebitRequest(BaseSchema):
    """Request schema for crediting or debiting a leave balance manually."""

    leave_type_id: int = Field(..., description="Target leave type ID.")
    cycle_year: int = Field(..., description="Target cycle year.")
    days: Decimal = Field(..., gt=0, description="Number of days to credit or debit.")
    adjustment_type: AdjustmentType = Field(
        default=AdjustmentType.MANUAL,
        description="Type of adjustment (manual, bulk_adjust, bulk_update).",
    )
    remarks: str | None = Field(default=None, max_length=500, description="Optional reason.")


class LeaveBalanceAdjustRequest(BaseSchema):
    """Request schema for adjusting a leave balance manually."""

    leave_type_id: int = Field(..., description="Target leave type ID.")
    cycle_year: int = Field(..., description="Target cycle year.")
    new_balance: Decimal = Field(..., ge=0, description="The absolute target balance to set.")
    adjustment_type: AdjustmentType = Field(
        default=AdjustmentType.MANUAL,
        description="Type of adjustment (manual, bulk_adjust, bulk_update)."
    )
    remarks: str | None = Field(default=None, max_length=500, description="Optional reason.")


class LeaveBalanceAdjustmentSchema(BaseSchema):
    """Response schema representing a single manual leave balance adjustment."""

    id: int = Field(..., description="Unique adjustment ID.")
    employee_id: int = Field(..., description="Employee ID.")
    leave_type_id: int = Field(..., description="Leave type ID.")
    adjustment_type: AdjustmentType = Field(..., description="Type of adjustment.")
    delta: Decimal = Field(..., description="The signed adjustment delta value.")
    new_balance: Decimal = Field(..., description="The final balance reached.")
    remarks: str | None = Field(default=None, description="Reason for adjustment.")
    cycle_year: int = Field(..., description="Target cycle year.")
    adjusted_at: datetime = Field(..., description="Adjustment timestamp.")
    adjusted_by: int = Field(..., description="User ID of the adjuster.")
    leave_type: LeaveTypeSchema | None = Field(default=None, description="Nested leave type details.")


class EmployeeLeaveAllocationSchema(BaseSchema):
    """Response schema representing a single leave allocation event."""

    id: int = Field(..., description="Unique allocation ID.")
    employee_id: int = Field(..., description="Employee ID.")
    leave_type_id: int = Field(..., description="Leave type ID.")
    cycle_year: int = Field(..., description="Target cycle year.")
    cycle_period: str | None = Field(default=None, description="Target cycle period.")
    allocated_days: Decimal = Field(..., description="Days allocated.")
    allocation_date: date = Field(..., description="Date of allocation.")
    allocation_source: AllocationSource = Field(..., description="Allocation source (auto, manual).")
    created_at: datetime = Field(..., description="Creation timestamp.")
    created_by: int | None = Field(default=None, description="User ID of creator.")
    leave_type: LeaveTypeSchema | None = Field(default=None, description="Nested leave type details.")


# ===========================================================================
# 4. Leave Request Schemas
# ===========================================================================


class LeaveRequestCreateRequest(BaseSchema):
    """Request schema for applying for a leave."""

    employee_id: int | None = Field(
        default=None,
        description="Employee ID. Required for admin creation; omitted/defaults to self in self-service."
    )
    leave_type_id: int = Field(..., description="Leave type ID.")
    start_date: date = Field(..., description="Start date of leave.")
    end_date: date = Field(..., description="End date of leave.")
    duration_days: Decimal = Field(..., gt=0, description="Duration in days (e.g. 0.5, 1.0, 5.0).")
    reason: str | None = Field(default=None, max_length=1000, description="Reason for leave.")

    @model_validator(mode="after")
    def _validate_dates(self) -> LeaveRequestCreateRequest:
        """Enforce end_date >= start_date."""
        if self.end_date < self.start_date:
            raise ValueError("end_date must be greater than or equal to start_date")
        return self


class LeaveRequestUpdateRequest(BaseSchema):
    """Request schema for editing an existing leave request."""

    leave_type_id: int | None = Field(default=None, description="Leave type ID.")
    start_date: date | None = Field(default=None, description="Start date of leave.")
    end_date: date | None = Field(default=None, description="End date of leave.")
    duration_days: Decimal | None = Field(default=None, gt=0, description="Duration in days.")
    reason: str | None = Field(default=None, max_length=1000, description="Reason for leave.")

    @model_validator(mode="after")
    def _validate_dates(self) -> LeaveRequestUpdateRequest:
        """Enforce end_date >= start_date if both are updated."""
        start = self.start_date
        end = self.end_date
        if start is not None and end is not None:
            if end < start:
                raise ValueError("end_date must be greater than or equal to start_date")
        return self


class LeaveRequestSchema(TimestampSchema):
    """Response schema representing a leave request."""

    id: int = Field(..., description="Unique leave request ID.")
    employee_id: int = Field(..., description="Employee ID.")
    leave_type_id: int = Field(..., description="Leave type ID.")
    start_date: date = Field(..., description="Start date.")
    end_date: date = Field(..., description="End date.")
    duration_days: Decimal = Field(..., description="Duration in days.")
    reason: str | None = Field(default=None, description="Reason for leave.")
    status: LeaveRequestStatus = Field(..., description="Current status of request.")
    applied_on: datetime = Field(..., description="Timestamp when applied.")
    reviewed_at: datetime | None = Field(default=None, description="Review timestamp.")
    reviewed_by: int | None = Field(default=None, description="User ID of reviewer.")
    rejection_reason: str | None = Field(default=None, description="Optional rejection reason.")
    leave_type: LeaveTypeSchema | None = Field(default=None, description="Nested leave type details.")


class LeaveRequestListResponse(PaginatedResponse[LeaveRequestSchema]):
    """Paginated list response for leave requests."""


# ===========================================================================
# 5. Holiday Management Schemas
# ===========================================================================


class HolidayTemplateCreateRequest(BaseSchema):
    """Request schema for creating a holiday template with its items atomically."""

    name: str = Field(..., max_length=150, description="Name of the holiday group.")
    items: list["HolidayTemplateItemCreateRequest"] = Field(
        default_factory=list,
        description="Holiday items to create atomically with the template.",
    )


class HolidayTemplateUpdateRequest(BaseSchema):
    """Request schema for updating a holiday template."""

    name: str = Field(..., max_length=150, description="Name of the holiday group.")


class HolidayTemplateItemCreateRequest(BaseSchema):
    """Request schema for adding a holiday item to a group."""

    name: str = Field(..., max_length=150, description="Name of the holiday (e.g. Christmas).")
    start_date: date = Field(..., description="Start date of the holiday.")
    end_date: date = Field(..., description="End date of the holiday.")
    day_of_week: str | None = Field(default=None, max_length=15, description="Day of week (e.g. Monday).")
    duration_days: int = Field(default=1, ge=1, description="Holiday duration in days.")

    @model_validator(mode="after")
    def _validate_dates(self) -> HolidayTemplateItemCreateRequest:
        """Enforce end_date >= start_date."""
        if self.end_date < self.start_date:
            raise ValueError("end_date must be greater than or equal to start_date")
        return self


class HolidayTemplateItemUpdateRequest(BaseSchema):
    """Request schema for updating a holiday item in a group."""

    name: str | None = Field(default=None, max_length=150, description="Name of the holiday.")
    start_date: date | None = Field(default=None, description="Start date.")
    end_date: date | None = Field(default=None, description="End date.")
    day_of_week: str | None = Field(default=None, max_length=15, description="Day of week.")
    duration_days: int | None = Field(default=None, ge=1, description="Holiday duration in days.")

    @model_validator(mode="after")
    def _validate_dates(self) -> HolidayTemplateItemUpdateRequest:
        """Enforce end_date >= start_date if both are updated."""
        start = self.start_date
        end = self.end_date
        if start is not None and end is not None:
            if end < start:
                raise ValueError("end_date must be greater than or equal to start_date")
        return self


class HolidayTemplateItemSchema(TimestampSchema):
    """Response schema representing a holiday item within a template."""

    id: int = Field(..., description="Unique holiday item ID.")
    template_id: int = Field(..., description="Template ID.")
    name: str = Field(..., description="Name of the holiday.")
    start_date: date = Field(..., description="Start date.")
    end_date: date = Field(..., description="End date.")
    day_of_week: str | None = Field(default=None, description="Day of the week.")
    duration_days: int = Field(..., description="Holiday duration in days.")
    is_deleted: bool = Field(..., description="Deleted status.")
    created_by: int | None = Field(default=None, description="Creator user ID.")


class HolidayTemplateSchema(TimestampSchema):
    """Response schema representing a holiday template/group."""

    id: int = Field(..., description="Unique template ID.")
    org_id: int = Field(..., description="Organization ID.")
    name: str = Field(..., description="Name of the holiday group.")
    holiday_count: int = Field(..., description="Number of holidays in this group.")
    is_deleted: bool = Field(..., description="Deleted status.")
    created_by: int | None = Field(default=None, description="Creator user ID.")
    updated_by: int | None = Field(default=None, description="Updater user ID.")
    items: list[HolidayTemplateItemSchema] | None = Field(
        default=None, description="Nested holiday item list."
    )


class HolidayTemplateAssignRequest(BaseSchema):
    """Request schema for assigning a holiday template to an employee."""

    template_id: int = Field(..., description="Target holiday template ID.")


class EmployeeHolidayAssignmentSchema(BaseSchema):
    """Response schema representing an employee's holiday group assignment."""

    id: int = Field(..., description="Unique assignment ID.")
    employee_id: int = Field(..., description="Employee ID.")
    template_id: int | None = Field(..., description="Assigned holiday template ID.")
    assigned_at: datetime = Field(..., description="Assignment timestamp.")
    assigned_by: int = Field(..., description="User ID of assigning manager.")
    previous_template_id: int | None = Field(default=None, description="Previous template ID.")


class EmployeeHolidayCalendarSchema(BaseSchema):
    """Response schema representing a holiday in the employee's calendar."""

    id: int = Field(..., description="Unique holiday item ID.")
    name: str = Field(..., description="Name of the holiday.")
    start_date: date = Field(..., description="Start date.")
    end_date: date = Field(..., description="End date.")
    day_of_week: str | None = Field(default=None, description="Day of the week.")
    duration_days: int = Field(..., description="Duration in days.")
