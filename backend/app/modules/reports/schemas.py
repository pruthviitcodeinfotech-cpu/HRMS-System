"""Reports Management — Pydantic request/response schemas (DTOs).

Defines serialization, validation, and structure rules for operational, compliance,
and audit reports across all HRMS modules.
"""

from __future__ import annotations

import datetime
from decimal import Decimal
from typing import Generic, TypeVar

from pydantic import Field, field_validator, model_validator

from app.shared.base.schema import BaseSchema
from app.shared.schemas.pagination import PaginationMeta, PaginationRequest
from app.shared.utils.datetime import utcnow

T = TypeVar("T")

# ===========================================================================
# 1. Base / Common Reports DTOs
# ===========================================================================


class ReportQueryRequest(PaginationRequest):
    """Inbound query and filter parameters for generating operational reports."""

    date_from: datetime.date | None = Field(
        default=None,
        description="Filter records starting from this date (YYYY-MM-DD).",
    )
    date_to: datetime.date | None = Field(
        default=None,
        description="Filter records up to this date (YYYY-MM-DD).",
    )
    period: str | None = Field(
        default=None,
        description="Preset time window filters: 'today', 'week', 'month', 'quarter', 'year'.",
    )
    month: str | None = Field(
        default=None,
        description="Filter records by a specific month (format: YYYY-MM).",
    )
    branch_id: int | None = Field(
        default=None,
        description="Filter records by branch identifier.",
    )
    dept_id: int | None = Field(
        default=None,
        description="Filter records by department identifier.",
    )
    designation_id: int | None = Field(
        default=None,
        description="Filter records by designation identifier.",
    )
    employee_id: int | None = Field(
        default=None,
        description="Filter records by employee identifier.",
    )
    status: str | None = Field(
        default=None,
        description="Filter records by status value.",
    )
    format: str = Field(
        default="json",
        description="Format of the report: 'json', 'csv', 'excel', or 'pdf'.",
    )
    sort_by: str | None = Field(
        default=None,
        description="Field name by which to sort results.",
    )
    sort_dir: str = Field(
        default="asc",
        description="Sort direction: 'asc' or 'desc'.",
    )

    @field_validator("period")
    @classmethod
    def _validate_period(cls, v: str | None) -> str | None:
        if v is not None:
            allowed = ("today", "week", "month", "quarter", "year")
            if v not in allowed:
                raise ValueError(f"period must be one of: {', '.join(allowed)}")
        return v

    @field_validator("format")
    @classmethod
    def _validate_format(cls, v: str) -> str:
        allowed = ("json", "csv", "excel", "pdf")
        if v not in allowed:
            raise ValueError(f"format must be one of: {', '.join(allowed)}")
        return v

    @field_validator("sort_dir")
    @classmethod
    def _validate_sort_dir(cls, v: str) -> str:
        allowed = ("asc", "desc")
        if v not in allowed:
            raise ValueError(f"sort_dir must be one of: {', '.join(allowed)}")
        return v

    @model_validator(mode="after")
    def _validate_date_range(self) -> ReportQueryRequest:
        if self.date_from and self.date_to:
            if self.date_from > self.date_to:
                raise ValueError("date_from cannot be after date_to")
            # Enforce max 12 months range (366 days)
            delta = self.date_to - self.date_from
            if delta.days > 366:
                raise ValueError("Date range exceeds the maximum allowed span of 12 months.")
        return self


class ReportPaginatedResponse(BaseSchema, Generic[T]):
    """Generic envelope wrapping a paginated list of report rows and calculation metadata."""

    items: list[T] = Field(..., description="Tabular rows of the report page.")
    pagination: PaginationMeta = Field(..., description="Pagination markers.")
    generated_at: datetime.datetime = Field(
        default_factory=utcnow,
        description="Timestamp indicating when the report query was executed.",
    )

    @classmethod
    def build(
        cls,
        *,
        items: list[T],
        page: int,
        page_size: int,
        total_records: int,
    ) -> ReportPaginatedResponse[T]:
        return cls(
            items=items,
            pagination=PaginationMeta.build(
                page=page, page_size=page_size, total_records=total_records
            ),
        )


class ExportJobStatusResponse(BaseSchema):
    """Tracks state and download details of an asynchronous report export job."""

    export_job_id: str = Field(..., description="Unique job tracking identifier.")
    status: str = Field(
        ...,
        description=(
            "Operational status of the export: 'pending', 'processing', 'completed', or 'failed'."
        ),
    )
    download_url: str | None = Field(
        default=None,
        description=("Direct download link to the compiled spreadsheet/PDF file once completed."),
    )
    expires_at: datetime.datetime | None = Field(
        default=None,
        description="Expiration timestamp after which the cached export file is deleted.",
    )

    @field_validator("status")
    @classmethod
    def _validate_status(cls, v: str) -> str:
        allowed = ("pending", "processing", "completed", "failed")
        if v not in allowed:
            raise ValueError(f"status must be one of: {', '.join(allowed)}")
        return v


# ===========================================================================
# 2. Employee Reports DTOs
# ===========================================================================


class EmployeeMasterReportItemSchema(BaseSchema):
    """Row representation of the Employee Master Report."""

    code: str = Field(..., description="Unique payroll code of the employee.")
    name: str = Field(..., description="Full name of the employee.")
    mobile: str | None = Field(default=None, description="Contact phone number.")
    email: str | None = Field(default=None, description="Corporate email address.")
    branch: str = Field(..., description="Name of the branch location.")
    department: str = Field(..., description="Name of the department.")
    designation: str = Field(..., description="Name of the job role/designation.")
    employee_type: str = Field(..., description="Employment type (e.g. full-time, intern).")
    date_of_joining: datetime.date = Field(..., description="Date when the employee joined.")
    status: str = Field(..., description="Employment status (e.g. active, suspended, terminated).")


class EmployeeMasterReportResponse(ReportPaginatedResponse[EmployeeMasterReportItemSchema]):
    """Response payload containing paginated Employee Master list."""


class EmployeeJoiningReportItemSchema(BaseSchema):
    """Details of joiners per period."""

    code: str = Field(..., description="Unique payroll code.")
    name: str = Field(..., description="Full name.")
    branch: str = Field(..., description="Name of branch.")
    department: str = Field(..., description="Name of department.")
    designation: str = Field(..., description="Name of designation.")
    date_of_joining: datetime.date = Field(..., description="Employee joining date.")


class EmployeeJoiningReportResponse(ReportPaginatedResponse[EmployeeJoiningReportItemSchema]):
    """Response containing joiners list for a specific range."""


class EmployeeStatusTransitionSchema(BaseSchema):
    """Details of a single employment status history record."""

    previous_status: str | None = Field(default=None, description="Status prior to change.")
    new_status: str = Field(..., description="Status after change.")
    changed_at: datetime.datetime = Field(..., description="Timestamp of the change.")
    changed_by_name: str | None = Field(default=None, description="Name of the editor.")


class EmployeeStatusReportItemSchema(BaseSchema):
    """Status roster showing current status and transition history."""

    code: str = Field(..., description="Employee code.")
    name: str = Field(..., description="Employee full name.")
    current_status: str = Field(..., description="Current status of the employee.")
    transition_history: list[EmployeeStatusTransitionSchema] = Field(
        default_factory=list, description="Historical timeline of status changes."
    )


class EmployeeStatusReportResponse(ReportPaginatedResponse[EmployeeStatusReportItemSchema]):
    """Response containing employment status changes list."""


class EmployeesByDepartmentReportItemSchema(BaseSchema):
    """Rooster item representing headcount metrics and roster for a department."""

    department_name: str = Field(..., description="Name of the department.")
    manager_name: str | None = Field(default=None, description="Department manager's name.")
    employee_count: int = Field(0, description="Total headcount within department.")
    roster: list[EmployeeMasterReportItemSchema] = Field(
        default_factory=list, description="List of employees belonging to the department."
    )


class EmployeesByDepartmentReportResponse(
    ReportPaginatedResponse[EmployeesByDepartmentReportItemSchema]
):
    """Response payload containing departments report."""


class EmployeesByDesignationReportItemSchema(BaseSchema):
    """Rooster item representing headcount metrics and roster for a designation."""

    designation_name: str = Field(..., description="Name of the designation.")
    employee_count: int = Field(0, description="Total headcount with this designation.")
    roster: list[EmployeeMasterReportItemSchema] = Field(
        default_factory=list, description="List of employees holding this designation."
    )


class EmployeesByDesignationReportResponse(
    ReportPaginatedResponse[EmployeesByDesignationReportItemSchema]
):
    """Response payload containing designations report."""


class EmployeesByBranchReportItemSchema(BaseSchema):
    """Rooster item representing headcount metrics and roster for a branch."""

    branch_name: str = Field(..., description="Name of the branch.")
    employee_count: int = Field(0, description="Total headcount at this branch.")
    roster: list[EmployeeMasterReportItemSchema] = Field(
        default_factory=list, description="List of employees assigned to this branch."
    )


class EmployeesByBranchReportResponse(ReportPaginatedResponse[EmployeesByBranchReportItemSchema]):
    """Response payload containing branch report."""


# ===========================================================================
# 3. Attendance Reports DTOs
# ===========================================================================


class DailyAttendanceReportItemSchema(BaseSchema):
    """Roster row representing daily attendance details."""

    employee_code: str = Field(..., description="Payroll code.")
    employee_name: str = Field(..., description="Full name.")
    attendance_date: datetime.date = Field(..., description="Date of attendance.")
    status: str = Field(..., description="Status (Present, Absent, Half Day, Leave, etc.).")
    first_punch_in: datetime.datetime | None = Field(default=None, description="First IN punch.")
    last_punch_out: datetime.datetime | None = Field(default=None, description="Last OUT punch.")
    work_hours: float = Field(0.0, description="Total calculated working hours.")
    late_minutes: int = Field(0, description="Late arrival duration in minutes.")
    early_leaving_minutes: int = Field(0, description="Early departure duration in minutes.")


class DailyAttendanceReportResponse(ReportPaginatedResponse[DailyAttendanceReportItemSchema]):
    """Daily attendance report page."""


class MonthlyAttendanceReportItemSchema(BaseSchema):
    """Aggregated attendance summary for an employee across a calendar month."""

    employee_code: str = Field(..., description="Payroll code.")
    employee_name: str = Field(..., description="Full name.")
    month: str = Field(..., description="Target month in YYYY-MM format.")
    present_days: float = Field(0.0, description="Number of present days.")
    absent_days: float = Field(0.0, description="Number of absent days.")
    half_days: int = Field(0, description="Number of half days.")
    leave_days: float = Field(0.0, description="Number of days on leave.")
    late_days: int = Field(0, description="Number of days arrived late.")
    total_work_hours: float = Field(0.0, description="Sum of working hours for the month.")
    day_status_map: dict[str, str] = Field(
        default_factory=dict,
        description="Key-value mapping of day of month (e.g. '01', '02') to attendance status.",
    )


class MonthlyAttendanceReportResponse(ReportPaginatedResponse[MonthlyAttendanceReportItemSchema]):
    """Monthly attendance calendar report page."""


class EmployeeAttendanceReportItemSchema(BaseSchema):
    """Attendance log for a single employee on a specific date."""

    attendance_date: datetime.date = Field(..., description="Date.")
    status: str = Field(..., description="Status.")
    first_punch_in: datetime.datetime | None = None
    last_punch_out: datetime.datetime | None = None
    work_hours: float = Field(0.0, description="Calculated work hours.")
    late_minutes: int = Field(0, description="Late minutes.")
    early_leaving_minutes: int = Field(0, description="Early minutes.")
    overtime_minutes: int = Field(0, description="Overtime minutes.")


class EmployeeAttendanceReportResponse(ReportPaginatedResponse[EmployeeAttendanceReportItemSchema]):
    """Individual employee range report."""


class LateComingReportItemSchema(BaseSchema):
    """Report detailing late arrival instances."""

    employee_code: str = Field(..., description="Employee code.")
    employee_name: str = Field(..., description="Employee name.")
    attendance_date: datetime.date = Field(..., description="Date of late occurrence.")
    first_punch_in: datetime.datetime = Field(..., description="Actual punch in timestamp.")
    expected_in: datetime.datetime = Field(..., description="Scheduled start time.")
    late_minutes: int = Field(..., description="Minutes late.")


class LateComingReportResponse(ReportPaginatedResponse[LateComingReportItemSchema]):
    """Roster of late arrival logs."""


class EarlyGoingReportItemSchema(BaseSchema):
    """Report detailing early departure instances."""

    employee_code: str = Field(..., description="Employee code.")
    employee_name: str = Field(..., description="Employee name.")
    attendance_date: datetime.date = Field(..., description="Date of occurrence.")
    last_punch_out: datetime.datetime = Field(..., description="Actual checkout timestamp.")
    expected_out: datetime.datetime = Field(..., description="Scheduled shift end time.")
    early_leaving_minutes: int = Field(..., description="Minutes early.")


class EarlyGoingReportResponse(ReportPaginatedResponse[EarlyGoingReportItemSchema]):
    """Roster of early departure logs."""


class MissingPunchReportItemSchema(BaseSchema):
    """Report detailing attendance records with anomalous/missing punches."""

    employee_code: str = Field(..., description="Employee code.")
    employee_name: str = Field(..., description="Employee name.")
    attendance_date: datetime.date = Field(..., description="Date of anomaly.")
    first_punch_in: datetime.datetime | None = Field(default=None, description="Punch in.")
    last_punch_out: datetime.datetime | None = Field(default=None, description="Punch out.")
    punch_count: int = Field(..., description="Total punches recorded for the day.")
    issue_type: str = Field(
        ...,
        description="Type of anomaly detected: 'missing_out_punch', 'odd_punch_count', etc.",
    )


class MissingPunchReportResponse(ReportPaginatedResponse[MissingPunchReportItemSchema]):
    """Roster of missing punch logs."""


class OvertimeReportItemSchema(BaseSchema):
    """Report showing overtime metrics per employee-day."""

    employee_code: str = Field(..., description="Employee code.")
    employee_name: str = Field(..., description="Employee name.")
    attendance_date: datetime.date = Field(..., description="Date.")
    work_hours: float = Field(0.0, description="Base work hours.")
    overtime_minutes: int = Field(..., description="Calculated raw overtime minutes.")
    approved_overtime_minutes: int = Field(..., description="Overtime minutes approved for pay.")


class OvertimeReportResponse(ReportPaginatedResponse[OvertimeReportItemSchema]):
    """Overtime report page."""


class AttendanceStatusSummarySchema(BaseSchema):
    """Aggregated count for a status classification."""

    status: str = Field(..., description="Attendance status label.")
    count: int = Field(..., description="Number of instances.")


class AttendanceSummaryReportResponse(BaseSchema):
    """Comprehensive aggregates of attendance over a target timeframe."""

    total_records: int = Field(0, description="Total days processed.")
    present_count: int = Field(0, description="Total present days.")
    absent_count: int = Field(0, description="Total absent days.")
    late_count: int = Field(0, description="Total late arrivals.")
    early_count: int = Field(0, description="Total early departures.")
    working_minutes_sum: int = Field(0, description="Total working minutes accumulated.")
    overtime_minutes_sum: int = Field(0, description="Total overtime minutes accumulated.")
    status_counts: list[AttendanceStatusSummarySchema] = Field(
        default_factory=list, description="Count aggregates grouped by attendance status."
    )
    generated_at: datetime.datetime = Field(
        default_factory=utcnow,
        description="Timestamp indicating when summary report was generated.",
    )


# ===========================================================================
# 4. Leave Reports DTOs
# ===========================================================================


class LeaveBalanceReportItemSchema(BaseSchema):
    """Aggregated allocation and utilization balances per employee-leave type."""

    employee_code: str = Field(..., description="Employee code.")
    employee_name: str = Field(..., description="Employee name.")
    leave_type_name: str = Field(..., description="Leave category name.")
    opening_balance: float = Field(0.0, description="Initial balance for cycle.")
    allocated: float = Field(0.0, description="Accrued/allocated leaves.")
    used: float = Field(0.0, description="Utilized leaves.")
    adjusted: float = Field(0.0, description="Manual balance adjustments.")
    closing_balance: float = Field(0.0, description="Remaining leave balance.")


class LeaveBalanceReportResponse(ReportPaginatedResponse[LeaveBalanceReportItemSchema]):
    """Leave balances report page."""


class LeaveRequestReportItemSchema(BaseSchema):
    """Roster row representing leave requests."""

    employee_code: str = Field(..., description="Employee code.")
    employee_name: str = Field(..., description="Employee name.")
    leave_type_name: str = Field(..., description="Leave category name.")
    start_date: datetime.date = Field(..., description="Start date of leave.")
    end_date: datetime.date = Field(..., description="End date of leave.")
    total_days: float = Field(..., description="Calculated total leave duration in days.")
    status: str = Field(..., description="Request state (pending, approved, rejected).")
    applied_on: datetime.date = Field(..., description="Date leave was submitted.")
    reason: str | None = Field(default=None, description="Employee rationale.")


class LeaveRequestReportResponse(ReportPaginatedResponse[LeaveRequestReportItemSchema]):
    """Leave requests roster page."""


class LeaveApprovalReportItemSchema(BaseSchema):
    """Roster row for audited leave approval histories."""

    employee_code: str = Field(..., description="Employee code.")
    employee_name: str = Field(..., description="Employee name.")
    leave_type_name: str = Field(..., description="Leave type.")
    start_date: datetime.date = Field(..., description="Start date.")
    end_date: datetime.date = Field(..., description="End date.")
    total_days: float = Field(..., description="Leave days.")
    status: str = Field(..., description="Final decision status.")
    applied_on: datetime.date = Field(..., description="Date submitted.")
    reviewed_by_name: str | None = Field(default=None, description="Name of the decider.")
    reviewed_at: datetime.datetime | None = Field(default=None, description="Time of review.")
    comments: str | None = Field(default=None, description="Review remarks.")


class LeaveApprovalReportResponse(ReportPaginatedResponse[LeaveApprovalReportItemSchema]):
    """Roster of resolved leave request decisions."""


class LeaveSummaryReportResponse(BaseSchema):
    """Leave metrics aggregates over a timeframe."""

    total_requests: int = Field(0, description="Total requests.")
    pending_count: int = Field(0, description="Pending requests.")
    approved_count: int = Field(0, description="Approved requests.")
    rejected_count: int = Field(0, description="Rejected requests.")
    total_leave_days: float = Field(0.0, description="Sum of approved leave days.")
    by_type: dict[str, int] = Field(
        default_factory=dict, description="Request count grouped by leave category name."
    )
    generated_at: datetime.datetime = Field(
        default_factory=utcnow,
        description="Timestamp indicating when summary report was generated.",
    )


# ===========================================================================
# 5. Approval Reports DTOs
# ===========================================================================


class PendingApprovalReportItemSchema(BaseSchema):
    """Roster row showing item awaiting resolution."""

    request_id: int = Field(..., description="Database ID of the approval request.")
    request_type: str = Field(..., description="Type of request: 'leave', 'attendance', etc.")
    employee_name: str = Field(..., description="Submitting employee name.")
    submitted_at: datetime.datetime = Field(..., description="Timestamp of submission.")
    details_summary: str = Field(..., description="Summarized details of the request.")


class PendingApprovalReportResponse(ReportPaginatedResponse[PendingApprovalReportItemSchema]):
    """Roster of pending decisions."""


class ApprovalHistoryReportItemSchema(BaseSchema):
    """Roster row showing resolved approval requests."""

    request_id: int = Field(..., description="Approval request ID.")
    request_type: str = Field(..., description="Type of request.")
    employee_name: str = Field(..., description="Submitting employee.")
    status: str = Field(..., description="Outcome: 'approved' or 'rejected'.")
    submitted_at: datetime.datetime = Field(..., description="Timestamp of submission.")
    decided_at: datetime.datetime = Field(..., description="Timestamp of decision.")
    decided_by_name: str = Field(..., description="Name of the resolving officer.")
    comments: str | None = Field(default=None, description="Decision remarks.")


class ApprovalHistoryReportResponse(ReportPaginatedResponse[ApprovalHistoryReportItemSchema]):
    """Roster of past decisions."""


class ApprovalPerformanceReportItemSchema(BaseSchema):
    """Manager performance metric measuring review efficiency."""

    approver_name: str = Field(..., description="Full name of the approver.")
    total_decisions: int = Field(..., description="Total decisions processed.")
    approved_count: int = Field(..., description="Total approvals given.")
    rejected_count: int = Field(..., description="Total rejections given.")
    avg_decision_time_seconds: float = Field(
        ..., description="Average seconds elapsed between submission and decision."
    )
    throughput_per_day: float = Field(..., description="Average decisions completed per day.")


class ApprovalPerformanceReportResponse(
    ReportPaginatedResponse[ApprovalPerformanceReportItemSchema]
):
    """Roster of approvers performance benchmarks."""


# ===========================================================================
# 6. Payroll Reports DTOs
# ===========================================================================


class PayrollRegisterComponentSchema(BaseSchema):
    """A single earning or deduction row item for a payroll slip."""

    component_name: str = Field(..., description="Name of payroll component.")
    component_type: str = Field(..., description="Type: 'earning' or 'deduction'.")
    amount: Decimal = Field(..., description="Valued monetary amount.")


class PayrollRegisterReportItemSchema(BaseSchema):
    """Row representing full payroll register details."""

    employee_code: str = Field(..., description="Employee code.")
    employee_name: str = Field(..., description="Employee name.")
    payroll_group_name: str = Field(..., description="Owning payroll group.")
    salary_cycle_name: str = Field(..., description="Salary cycle identifier.")
    gross_earnings: Decimal = Field(..., description="Gross earnings sum.")
    total_deductions: Decimal = Field(..., description="Total deductions sum.")
    net_payable: Decimal = Field(..., description="Gross minus deductions.")
    components: list[PayrollRegisterComponentSchema] = Field(
        default_factory=list, description="List of computed salary rows."
    )


class PayrollRegisterReportResponse(ReportPaginatedResponse[PayrollRegisterReportItemSchema]):
    """Payroll register page."""


class SalaryRegisterReportItemSchema(BaseSchema):
    """Row item representing salary breakdown details."""

    employee_code: str = Field(..., description="Employee code.")
    employee_name: str = Field(..., description="Employee name.")
    basic_salary: Decimal = Field(..., description="Employee base basic salary.")
    allowances: Decimal = Field(..., description="Total allowances component sum.")
    deductions: Decimal = Field(..., description="Total statutory/other deductions sum.")
    gross_salary: Decimal = Field(..., description="Total gross earnings.")
    net_salary: Decimal = Field(..., description="Net payout amount.")
    payment_status: str = Field(..., description="Status (paid, processing, unpaid).")


class SalaryRegisterReportResponse(ReportPaginatedResponse[SalaryRegisterReportItemSchema]):
    """Salary register page."""


class PayrollSummaryReportResponse(BaseSchema):
    """Aggregated metrics across a whole payroll cycle run."""

    gross_sum: Decimal = Field(..., description="Sum of gross payouts.")
    deductions_sum: Decimal = Field(..., description="Sum of deduction amounts.")
    net_payable_sum: Decimal = Field(..., description="Sum of net cash paid.")
    total_headcount: int = Field(..., description="Number of employees paid.")
    generated_at: datetime.datetime = Field(
        default_factory=utcnow,
        description="Timestamp indicating when summary report was generated.",
    )


class PayslipReportItemSchema(BaseSchema):
    """Roster row representing computed payslip files."""

    employee_code: str = Field(..., description="Employee code.")
    employee_name: str = Field(..., description="Employee name.")
    payslip_id: int = Field(..., description="Database ID of the payslip.")
    salary_cycle_name: str = Field(..., description="Salary cycle name.")
    pdf_url: str = Field(..., description="Download link to the PDF document.")


class PayslipReportResponse(ReportPaginatedResponse[PayslipReportItemSchema]):
    """Payslip documents list page."""


# ===========================================================================
# 7. Settlement Reports DTOs
# ===========================================================================


class SettlementLedgerReportItemSchema(BaseSchema):
    """Roster row tracing loan transactions and arrears adjustments."""

    employee_code: str = Field(..., description="Employee code.")
    employee_name: str = Field(..., description="Employee name.")
    type: str = Field(..., description="Type of settlement: 'loan', 'advance', or 'arrears'.")
    reference_id: int = Field(..., description="ID of corresponding model.")
    transaction_date: datetime.date = Field(..., description="Date transaction was executed.")
    transaction_type: str = Field(..., description="Type: 'credit' or 'debit'.")
    amount: Decimal = Field(..., description="Value of transaction.")
    outstanding_balance: Decimal = Field(..., description="Remaining balance after transaction.")
    comment: str | None = Field(default=None, description="Reason or auditor note.")


class SettlementLedgerReportResponse(ReportPaginatedResponse[SettlementLedgerReportItemSchema]):
    """Settlements ledger page."""


class SettlementSummaryReportResponse(BaseSchema):
    """Aggregated outstanding loan liabilities and arrears totals."""

    active_loans_count: int = Field(..., description="Number of active loans/advances.")
    closed_loans_count: int = Field(..., description="Number of closed loans/advances.")
    total_principal_amount: Decimal = Field(..., description="Sum of principal loans granted.")
    total_outstanding_loans: Decimal = Field(..., description="Outstanding principal balance.")
    total_outstanding_arrears: Decimal = Field(..., description="Outstanding arrears balances.")
    generated_at: datetime.datetime = Field(
        default_factory=utcnow,
        description="Timestamp indicating when summary report was generated.",
    )


# ===========================================================================
# 8. Hardware Reports DTOs
# ===========================================================================


class DeviceStatusReportItemSchema(BaseSchema):
    """Device connection logs."""

    device_id: int = Field(..., description="Database ID.")
    name: str = Field(..., description="Device name.")
    status: str = Field(..., description="Status (online, offline, maintenance).")
    branch_name: str = Field(..., description="Branch location name.")
    last_seen_at: datetime.datetime | None = Field(default=None, description="Last ping time.")


class DeviceStatusReportResponse(ReportPaginatedResponse[DeviceStatusReportItemSchema]):
    """Device status list page."""


class DeviceHealthReportItemSchema(BaseSchema):
    """Health metrics for devices."""

    device_id: int = Field(..., description="Database ID.")
    name: str = Field(..., description="Device name.")
    status: str = Field(..., description="Uptime state.")
    firmware_version: str | None = Field(default=None, description="Firmware version.")
    software_version: str | None = Field(default=None, description="Software client version.")
    uptime_percentage: float = Field(0.0, description="Uptime ratio.")
    last_sync_at: datetime.datetime | None = Field(
        default=None, description="Last database sync time."
    )


class DeviceHealthReportResponse(ReportPaginatedResponse[DeviceHealthReportItemSchema]):
    """Device health list page."""


class DeviceSyncReportItemSchema(BaseSchema):
    """Audit of device synchronization freshness."""

    device_id: int = Field(..., description="Database ID.")
    name: str = Field(..., description="Device name.")
    last_sync_at: datetime.datetime | None = Field(
        default=None, description="Last sync execution time."
    )
    status_label: str = Field(..., description="Freshness assessment (e.g. 'synced', 'delayed').")


class DeviceSyncReportResponse(ReportPaginatedResponse[DeviceSyncReportItemSchema]):
    """Device sync logs list page."""


# ===========================================================================
# 9. Notification Reports DTOs
# ===========================================================================


class NotificationDeliveryReportItemSchema(BaseSchema):
    """Auditing notification deliveries."""

    notification_title: str = Field(..., description="Title.")
    recipient_name: str = Field(..., description="Recipient full name.")
    sent_at: datetime.datetime = Field(..., description="Timestamp sent.")
    delivered_at: datetime.datetime | None = Field(default=None, description="Timestamp received.")
    delivery_status: str = Field(..., description="Status (delivered, failed, pending).")


class NotificationDeliveryReportResponse(
    ReportPaginatedResponse[NotificationDeliveryReportItemSchema]
):
    """Notification delivery roster page."""


class NotificationReadReportItemSchema(BaseSchema):
    """Auditing notification read status."""

    notification_title: str = Field(..., description="Title.")
    recipient_name: str = Field(..., description="Recipient.")
    sent_at: datetime.datetime = Field(..., description="Timestamp sent.")
    read_at: datetime.datetime | None = Field(default=None, description="Timestamp read.")
    read_status: str = Field(..., description="Status (read, unread).")


class NotificationReadReportResponse(ReportPaginatedResponse[NotificationReadReportItemSchema]):
    """Notification read status page."""


class NotificationSummaryReportResponse(BaseSchema):
    """Delivery efficiency summary metrics."""

    total_sent: int = Field(0, description="Total notifications dispatched.")
    total_delivered: int = Field(0, description="Total notifications received.")
    total_read: int = Field(0, description="Total notifications marked read.")
    delivery_rate: float = Field(0.0, description="Uptime/delivery ratio.")
    read_rate: float = Field(0.0, description="Read/opened ratio.")
    generated_at: datetime.datetime = Field(
        default_factory=utcnow,
        description="Timestamp indicating when summary report was generated.",
    )


# ===========================================================================
# 10. Activity Log / Audit Reports DTOs
# ===========================================================================


class UserActivityReportItemSchema(BaseSchema):
    """Operational audit track records."""

    performed_by_name: str = Field(..., description="User executing mutation.")
    action: str = Field(..., description="Action tag (e.g. create, update, delete).")
    module: str = Field(..., description="Subject module domain.")
    details: str = Field(..., description="Human-readable execution log.")
    logged_at: datetime.datetime = Field(..., description="Timestamp of execution.")
    ip_address: str | None = Field(default=None, description="Execution client IP address.")


class UserActivityReportResponse(ReportPaginatedResponse[UserActivityReportItemSchema]):
    """User activities list page."""


class AuditTrailReportItemSchema(BaseSchema):
    """Auditing data-change history."""

    logged_at: datetime.datetime = Field(..., description="Timestamp.")
    performed_by_name: str = Field(..., description="User.")
    action: str = Field(..., description="Action.")
    module: str = Field(..., description="Domain module.")
    entity_type: str = Field(..., description="Affected database model class name.")
    entity_id: int = Field(..., description="Database row primary key ID.")
    changes_summary: str = Field(..., description="Payload diff description.")


class AuditTrailReportResponse(ReportPaginatedResponse[AuditTrailReportItemSchema]):
    """Audit trails list page."""


class SecurityEventReportItemSchema(BaseSchema):
    """Sensitive security operations event logs."""

    logged_at: datetime.datetime = Field(..., description="Timestamp.")
    performed_by_name: str = Field(..., description="Actor user.")
    action: str = Field(..., description="Action tag.")
    module: str = Field(..., description="Domain module.")
    severity: str = Field(..., description="Warning level (warning, critical).")
    details: str = Field(..., description="Security event description.")


class SecurityEventReportResponse(ReportPaginatedResponse[SecurityEventReportItemSchema]):
    """Security events list page."""


# ===========================================================================
# 11. Organization Reports DTOs
# ===========================================================================


class BranchSummaryReportItemSchema(BaseSchema):
    """Aggregate stats per branch."""

    branch_name: str = Field(..., description="Branch location name.")
    total_employees: int = Field(..., description="Headcount.")
    active_employees: int = Field(..., description="Active headcount.")
    department_count: int = Field(..., description="Total active departments mapped.")


class BranchSummaryReportResponse(ReportPaginatedResponse[BranchSummaryReportItemSchema]):
    """Branches summary page."""


class DepartmentSummaryReportItemSchema(BaseSchema):
    """Aggregate stats per department."""

    department_name: str = Field(..., description="Department name.")
    total_employees: int = Field(..., description="Headcount.")
    active_employees: int = Field(..., description="Active headcount.")
    manager_name: str | None = Field(default=None, description="Manager name.")


class DepartmentSummaryReportResponse(ReportPaginatedResponse[DepartmentSummaryReportItemSchema]):
    """Departments summary page."""


class WorkforceSummaryReportResponse(BaseSchema):
    """Operational workforce distribution metrics."""

    total_headcount: int = Field(..., description="Total global headcount.")
    status_breakdown: dict[str, int] = Field(
        default_factory=dict, description="Count mapped by employment status."
    )
    type_breakdown: dict[str, int] = Field(
        default_factory=dict, description="Count mapped by employment type."
    )
    branch_breakdown: dict[str, int] = Field(
        default_factory=dict, description="Count mapped by branch."
    )
    department_breakdown: dict[str, int] = Field(
        default_factory=dict, description="Count mapped by department."
    )
    generated_at: datetime.datetime = Field(
        default_factory=utcnow,
        description="Timestamp indicating when summary report was generated.",
    )


__all__ = [
    "ReportQueryRequest",
    "ReportPaginatedResponse",
    "ExportJobStatusResponse",
    "EmployeeMasterReportItemSchema",
    "EmployeeMasterReportResponse",
    "EmployeeJoiningReportItemSchema",
    "EmployeeJoiningReportResponse",
    "EmployeeStatusTransitionSchema",
    "EmployeeStatusReportItemSchema",
    "EmployeeStatusReportResponse",
    "EmployeesByDepartmentReportItemSchema",
    "EmployeesByDepartmentReportResponse",
    "EmployeesByDesignationReportItemSchema",
    "EmployeesByDesignationReportResponse",
    "EmployeesByBranchReportItemSchema",
    "EmployeesByBranchReportResponse",
    "DailyAttendanceReportItemSchema",
    "DailyAttendanceReportResponse",
    "MonthlyAttendanceReportItemSchema",
    "MonthlyAttendanceReportResponse",
    "EmployeeAttendanceReportItemSchema",
    "EmployeeAttendanceReportResponse",
    "LateComingReportItemSchema",
    "LateComingReportResponse",
    "EarlyGoingReportItemSchema",
    "EarlyGoingReportResponse",
    "MissingPunchReportItemSchema",
    "MissingPunchReportResponse",
    "OvertimeReportItemSchema",
    "OvertimeReportResponse",
    "AttendanceStatusSummarySchema",
    "AttendanceSummaryReportResponse",
    "LeaveBalanceReportItemSchema",
    "LeaveBalanceReportResponse",
    "LeaveRequestReportItemSchema",
    "LeaveRequestReportResponse",
    "LeaveApprovalReportItemSchema",
    "LeaveApprovalReportResponse",
    "LeaveSummaryReportResponse",
    "PendingApprovalReportItemSchema",
    "PendingApprovalReportResponse",
    "ApprovalHistoryReportItemSchema",
    "ApprovalHistoryReportResponse",
    "ApprovalPerformanceReportItemSchema",
    "ApprovalPerformanceReportResponse",
    "PayrollRegisterComponentSchema",
    "PayrollRegisterReportItemSchema",
    "PayrollRegisterReportResponse",
    "SalaryRegisterReportItemSchema",
    "SalaryRegisterReportResponse",
    "PayrollSummaryReportResponse",
    "PayslipReportItemSchema",
    "PayslipReportResponse",
    "SettlementLedgerReportItemSchema",
    "SettlementLedgerReportResponse",
    "SettlementSummaryReportResponse",
    "DeviceStatusReportItemSchema",
    "DeviceStatusReportResponse",
    "DeviceHealthReportItemSchema",
    "DeviceHealthReportResponse",
    "DeviceSyncReportItemSchema",
    "DeviceSyncReportResponse",
    "NotificationDeliveryReportItemSchema",
    "NotificationDeliveryReportResponse",
    "NotificationReadReportItemSchema",
    "NotificationReadReportResponse",
    "NotificationSummaryReportResponse",
    "UserActivityReportItemSchema",
    "UserActivityReportResponse",
    "AuditTrailReportItemSchema",
    "AuditTrailReportResponse",
    "SecurityEventReportItemSchema",
    "SecurityEventReportResponse",
    "BranchSummaryReportItemSchema",
    "BranchSummaryReportResponse",
    "DepartmentSummaryReportItemSchema",
    "DepartmentSummaryReportResponse",
    "WorkforceSummaryReportResponse",
]
