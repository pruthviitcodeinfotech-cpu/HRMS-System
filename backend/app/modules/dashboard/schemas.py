"""Dashboard Management — Pydantic request/response schemas (DTOs).

Defines serialization, validation, and structure rules for the main dashboard
summary, KPIs list, widgets configurations, per-module dashboards, and chart trends.
"""

from __future__ import annotations

import datetime
from decimal import Decimal

from pydantic import Field

from app.shared.base.schema import BaseSchema
from app.shared.utils.datetime import utcnow
from app.shared.schemas.pagination import PaginatedResponse

# ===========================================================================
# 1. Base / Common Dashboard DTOs
# ===========================================================================


class ChartSeriesPointSchema(BaseSchema):
    """Represent a single series named list of data points for chart projections."""

    name: str = Field(..., description="Name of the data series (e.g. 'Present', 'Absent').")
    points: list[float] = Field(..., description="Chronological sequence of data values.")


class ChartResponseSchema(BaseSchema):
    """Generic response structure for chart data."""

    labels: list[str] = Field(
        ..., description="X-axis category labels (e.g. dates, months, department names)."
    )
    series: list[ChartSeriesPointSchema] = Field(
        ..., description="Series data containing points for plotting."
    )
    generated_at: datetime.datetime = Field(
        default_factory=utcnow,
        description="Timestamp indicating when the chart data was computed.",
    )


class WidgetMetadataSchema(BaseSchema):
    """Metadata representing a dashboard widget configuration for client render."""

    widget_key: str = Field(..., description="Unique key identifier of the widget.")
    title: str = Field(..., description="Display title of the widget.")
    permitted: bool = Field(
        ..., description="Whether the current caller is authorized to view this widget's data."
    )
    source_module: str = Field(
        ..., description="Backend domain module supplying data for this widget."
    )


class WidgetsMetadataResponse(BaseSchema):
    """Response DTO containing metadata of all widgets."""

    widgets: list[WidgetMetadataSchema] = Field(
        ..., description="List of widgets metadata for the caller."
    )


# ===========================================================================
# 2. Combined Summary Dashboard DTOs
# ===========================================================================


class EmployeeSummarySchema(BaseSchema):
    """Summarized metrics from the Employee module."""

    total_employees: int = Field(..., description="Total headcount registered in the system.")
    active_employees: int = Field(..., description="Count of currently active employees.")
    new_employees: int = Field(..., description="Count of newly hired employees in the period.")


class AttendanceSummarySchema(BaseSchema):
    """Summarized metrics from the Attendance module."""

    present_today: int = Field(..., description="Number of employees present today.")
    absent_today: int = Field(..., description="Number of employees absent today.")
    half_day_today: int = Field(default=0, description="Number of half day employees today.")
    late_arrivals: int = Field(..., description="Number of employees who arrived late today.")
    early_exits: int = Field(..., description="Number of employees who left early today.")
    on_leave_today: int = Field(..., description="Number of employees currently on leave today.")
    on_break_today: int = Field(default=0, description="Number of employees currently on break today.")
    pending_biometrics: int = Field(default=0, description="Number of employees whose biometric enrollment/status is pending.")



class LeaveSummarySchema(BaseSchema):
    """Summarized metrics from the Leave module."""

    total_requests: int = Field(..., description="Total leave requests in current period.")
    pending_leaves: int = Field(..., description="Number of leave requests awaiting approval.")


class ApprovalSummarySchema(BaseSchema):
    """Summarized metrics from the Approval module."""

    pending_approvals: int = Field(
        ..., description="Number of approval requests awaiting user decision."
    )


class PayrollSummarySchema(BaseSchema):
    """Summarized metrics from the Payroll module."""

    current_payroll_status: str = Field(
        ..., description="Status of the current salary cycle (e.g. 'draft', 'finalized')."
    )


class SettlementSummarySchema(BaseSchema):
    """Summarized metrics from the Settlement module."""

    total_outstanding_loans_advances: Decimal = Field(
        ..., description="Sum of outstanding loans and advances."
    )
    total_outstanding_arrears: Decimal = Field(..., description="Sum of outstanding arrears.")


class HardwareSummarySchema(BaseSchema):
    """Summarized metrics from the Hardware/Biometric module."""

    online_devices: int = Field(..., description="Number of biometric devices currently online.")
    offline_devices: int = Field(..., description="Number of biometric devices currently offline.")


class NotificationSummarySchema(BaseSchema):
    """Summarized metrics from the Notification module."""

    unread_notifications: int = Field(..., description="Count of unread notifications.")


class DashboardSummaryResponse(BaseSchema):
    """Response DTO combining all summaries authorized for the caller."""

    employees: EmployeeSummarySchema | None = Field(
        default=None, description="Employee summary metrics if authorized."
    )
    attendance: AttendanceSummarySchema | None = Field(
        default=None, description="Attendance summary metrics if authorized."
    )
    leave: LeaveSummarySchema | None = Field(
        default=None, description="Leave summary metrics if authorized."
    )
    approvals: ApprovalSummarySchema | None = Field(
        default=None, description="Approval summary metrics if authorized."
    )
    payroll: PayrollSummarySchema | None = Field(
        default=None, description="Payroll summary metrics if authorized."
    )
    devices: HardwareSummarySchema | None = Field(
        default=None, description="Biometric devices summary metrics if authorized."
    )
    notifications: NotificationSummarySchema | None = Field(
        default=None, description="Notifications summary metrics if authorized."
    )
    generated_at: datetime.datetime = Field(
        default_factory=utcnow,
        description="Timestamp indicating when the summary was aggregated.",
    )


# ===========================================================================
# 3. Flat KPIs & Statistics DTOs
# ===========================================================================


class DashboardKPIsResponse(BaseSchema):
    """Headline flat KPI map aggregated across all modules."""

    total_employees: int = Field(..., description="Total employees count.")
    active_employees: int = Field(..., description="Active employees count.")
    new_employees: int = Field(..., description="New hires count in the current period.")
    present_today: int = Field(..., description="Present today count.")
    absent_today: int = Field(..., description="Absent today count.")
    half_day_today: int = Field(default=0, description="Half day today count.")
    late_arrivals: int = Field(..., description="Late arrivals today count.")
    early_exits: int = Field(..., description="Early exits today count.")
    on_leave_today: int = Field(..., description="On leave today count.")
    on_break_today: int = Field(default=0, description="On break today count.")
    pending_biometrics: int = Field(default=0, description="Pending biometrics count.")
    pending_leaves: int = Field(..., description="Pending leave requests count.")
    pending_approvals: int = Field(..., description="Pending approvals count.")
    current_payroll_status: str = Field(..., description="Status of the current payroll cycle.")
    total_outstanding_loans_advances: Decimal = Field(
        ..., description="Total outstanding loans and advances."
    )
    total_outstanding_arrears: Decimal = Field(..., description="Total outstanding arrears.")
    online_devices: int = Field(..., description="Online biometric devices count.")
    offline_devices: int = Field(..., description="Offline biometric devices count.")
    unread_notifications: int = Field(..., description="Unread notifications count.")
    generated_at: datetime.datetime = Field(
        default_factory=utcnow,
        description="Timestamp indicating when the KPIs were computed.",
    )



class DashboardStatisticsResponse(BaseSchema):
    """Extended statistics and ratios representing organization metrics."""

    employee_turnover_rate: float | None = Field(
        None, description="Turnover rate for the current period."
    )
    attendance_rate_today: float | None = Field(
        None, description="Percentage of active employees present today."
    )
    leave_approval_rate: float | None = Field(
        None, description="Percentage of leave requests that are approved."
    )
    device_uptime_rate: float | None = Field(
        None, description="Percentage of biometric devices that are online."
    )
    generated_at: datetime.datetime = Field(
        default_factory=utcnow,
        description="Timestamp indicating when stats were computed.",
    )


# ===========================================================================
# 4. Individual Per-Module Dashboard DTOs
# ===========================================================================


class EmployeeDistributionItem(BaseSchema):
    """General key-value count model for category distributions."""

    name: str = Field(..., description="Name of the category classification (e.g. 'Engineering').")
    count: int = Field(..., description="Count of employees in this category classification.")


class EmployeeDashboardResponse(BaseSchema):
    """Metrics for the dedicated Employee Dashboard."""

    total_employees: int = Field(..., description="Total employee headcount.")
    active_employees: int = Field(..., description="Currently active employee count.")
    inactive_employees: int = Field(..., description="Count of inactive or terminated employees.")
    new_employees: int = Field(..., description="Count of joined employees in period.")
    distribution: dict[str, list[EmployeeDistributionItem]] = Field(
        ...,
        description="Headcount breakdowns grouped by dept, branch, designation, and status.",
    )
    generated_at: datetime.datetime = Field(
        default_factory=utcnow,
        description="Timestamp indicating when the dashboard was generated.",
    )


class AttendanceDailyTrendPoint(BaseSchema):
    """Daily record point representing attendance state."""

    date: datetime.date = Field(..., description="Specific calendar date.")
    present: int = Field(..., description="Present count on this date.")
    absent: int = Field(..., description="Absent count on this date.")
    late: int = Field(..., description="Late arrivals count on this date.")


class AttendanceDashboardResponse(BaseSchema):
    """Metrics for the dedicated Attendance Dashboard."""

    present_today: int = Field(..., description="Present today count.")
    absent_today: int = Field(..., description="Absent today count.")
    half_day_today: int = Field(..., description="Half day today count.")
    on_leave_today: int = Field(..., description="On leave today count.")
    on_break_today: int = Field(default=0, description="On break today count.")
    pending_biometrics: int = Field(default=0, description="Pending biometrics count.")
    late_arrivals: int = Field(..., description="Late arrivals today count.")
    early_exits: int = Field(..., description="Early exits today count.")
    not_marked: int = Field(..., description="Active employees with unmarked attendance today.")
    trend: list[AttendanceDailyTrendPoint] = Field(
        ..., description="Chronological sequence of daily attendance counts."
    )
    generated_at: datetime.datetime = Field(
        default_factory=utcnow,
        description="Timestamp indicating when the metrics were computed.",
    )


class ShiftSummaryItemSchema(BaseSchema):
    """Shift summary counts representation."""

    shift_id: int = Field(..., description="ID of the shift.")
    shift_name: str = Field(..., description="Name of the shift.")
    total_employees: int = Field(default=0, description="Total active employees assigned to this shift.")
    present: int = Field(default=0, description="Number of employees present today.")
    late: int = Field(default=0, description="Number of late arrivals today.")
    absent: int = Field(default=0, description="Number of absent employees today.")
    on_leave: int = Field(default=0, description="Number of employees on leave today.")


class ShiftSummaryResponse(BaseSchema):
    """Metrics for the Dashboard Shift Summary widget."""

    shifts: list[ShiftSummaryItemSchema] = Field(..., description="Daily summary grouped by shift.")
    generated_at: datetime.datetime = Field(
        default_factory=utcnow,
        description="Timestamp indicating when the metrics were computed.",
    )




class LeaveTypeBreakdownItem(BaseSchema):
    """Leave category count mapping."""

    leave_type: str = Field(..., description="Name of the leave type category (e.g. 'Sick Leave').")
    count: int = Field(..., description="Number of requests associated with this leave type.")


class LeaveDashboardResponse(BaseSchema):
    """Metrics for the dedicated Leave Dashboard."""

    total_requests: int = Field(..., description="Total requests processed.")
    pending: int = Field(..., description="Awaiting approval count.")
    approved: int = Field(..., description="Approved requests count.")
    rejected: int = Field(..., description="Rejected requests count.")
    by_type: list[LeaveTypeBreakdownItem] = Field(
        ..., description="Requests breakdown by leave types."
    )
    generated_at: datetime.datetime = Field(
        default_factory=utcnow,
        description="Timestamp indicating when metrics were aggregated.",
    )


class ApprovalRequestBriefSchema(BaseSchema):
    """A brief summary representing a single approval request."""

    id: int = Field(..., description="Primary key of the approval request.")
    request_type: str = Field(
        ..., description="Category of request (e.g. 'leave', 'attendance_regularization')."
    )
    status: str = Field(..., description="Current request status.")
    requester_name: str = Field(..., description="Name of the employee making the request.")
    submitted_at: datetime.datetime = Field(..., description="Submission date and time.")


class ApprovalDashboardResponse(BaseSchema):
    """Metrics for the dedicated Approval Dashboard."""

    pending_approvals: int = Field(..., description="Pending approval count.")
    by_request_type: dict[str, int] = Field(
        ..., description="Grouped count of pending approvals by request type."
    )
    approved_recent: int = Field(..., description="Count of requests approved recently.")
    rejected_recent: int = Field(..., description="Count of requests rejected recently.")
    recent: list[ApprovalRequestBriefSchema] = Field(
        ..., description="List of most recent approval requests."
    )
    generated_at: datetime.datetime = Field(
        default_factory=utcnow,
        description="Timestamp indicating when the dashboard was generated.",
    )


class PayrollDashboardResponse(BaseSchema):
    """Metrics for the dedicated Payroll Dashboard."""

    current_cycle_id: int | None = Field(
        None, description="Primary key identifier of the current payroll cycle."
    )
    current_cycle_name: str | None = Field(
        None, description="Human readable name of the current cycle."
    )
    is_finalized: bool = Field(..., description="Whether the current cycle is finalized.")
    status: str = Field(
        ..., description="Detailed salary status of current cycle (e.g. 'processing', 'approved')."
    )
    finalized_amount: Decimal = Field(
        ..., description="Aggregate monetary cost for the finalized run."
    )
    payment_status_breakdown: dict[str, int] = Field(
        ..., description="Count of employees grouped by payment execution state."
    )
    headcount: int = Field(
        ..., description="Total count of employees processed in the payroll cycle."
    )
    generated_at: datetime.datetime = Field(
        default_factory=utcnow,
        description="Timestamp indicating when payroll stats were computed.",
    )


class SettlementDashboardResponse(BaseSchema):
    """Metrics for the dedicated Settlement (Loans, Advances, Arrears) Dashboard."""

    active_loans_advances: int = Field(..., description="Count of active loans and advances.")
    closed_loans_advances: int = Field(..., description="Count of closed loans and advances.")
    total_outstanding_loans_advances: Decimal = Field(
        ..., description="Monetary sum of outstanding loan and advance balances."
    )
    total_outstanding_arrears: Decimal = Field(
        ..., description="Monetary sum of outstanding arrears balances."
    )
    generated_at: datetime.datetime = Field(
        default_factory=utcnow,
        description="Timestamp indicating when the statistics were generated.",
    )


class HardwareDashboardResponse(BaseSchema):
    """Metrics for the dedicated Hardware Biometric Dashboard."""

    online_devices: int = Field(..., description="Biometric devices online count.")
    offline_devices: int = Field(..., description="Biometric devices offline count.")
    disabled_devices: int = Field(..., description="Biometric devices disabled count.")
    maintenance_devices: int = Field(..., description="Biometric devices in maintenance count.")
    last_device_sync: datetime.datetime | None = Field(
        None, description="Timestamp of the most recent device synchronization."
    )
    generated_at: datetime.datetime = Field(
        default_factory=utcnow,
        description="Timestamp indicating when device state was aggregated.",
    )


class NotificationBriefSchema(BaseSchema):
    """A brief summary representing a single notification."""

    id: int = Field(..., description="Primary key of the notification.")
    title: str = Field(..., description="Title of the notification.")
    notification_type: str = Field(..., description="Category classification of notification.")
    priority: str = Field(..., description="Urgency priority level (e.g. 'high', 'normal').")
    created_at: datetime.datetime = Field(..., description="Creation date and time.")


class NotificationDashboardResponse(BaseSchema):
    """Metrics for the dedicated Notification Dashboard."""

    unread_count: int = Field(..., description="Total unread notifications count for caller.")
    recent: list[NotificationBriefSchema] = Field(
        ..., description="Most recent notifications matching the caller."
    )
    generated_at: datetime.datetime = Field(
        default_factory=utcnow,
        description="Timestamp indicating when the dashboard was generated.",
    )


class PendingBiometricEmployeeSchema(BaseSchema):
    """Schema representing an employee with pending biometric enrollment."""

    employee_id: int = Field(..., description="ID of the employee.")
    employee_code: str = Field(..., description="Unique employee code.")
    employee_name: str = Field(..., description="Name of the employee.")
    department: str | None = Field(default=None, description="Department name.")
    designation: str | None = Field(default=None, description="Designation name.")
    branch: str | None = Field(default=None, description="Branch name.")
    biometric_status: str = Field(default="pending", description="Biometric status.")
    enrollment_status: str = Field(default="pending", description="Biometric enrollment status.")
    created_at: datetime.datetime | None = Field(default=None, description="Created timestamp.")


class PendingBiometricsResponse(PaginatedResponse[PendingBiometricEmployeeSchema]):
    """Paginated list of employees with pending biometric enrollment."""
    pass

