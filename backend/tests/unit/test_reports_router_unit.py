"""Unit tests for ReportsService — all report types, RBAC, scoping, exports.

Repository is mocked; no DB connection required.
"""

from __future__ import annotations

import datetime
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest
from pydantic import ValidationError

from app.core.dependencies.auth import CurrentUser
from app.core.exceptions.base import AuthorizationException, NotFoundException
from app.core.security.permissions import build_effective_permissions
from app.modules.reports.schemas import (
    AttendanceSummaryReportResponse,
    DailyAttendanceReportResponse,
    EmployeeJoiningReportResponse,
    EmployeeMasterReportResponse,
    EmployeesByBranchReportResponse,
    EmployeesByDepartmentReportResponse,
    EmployeesByDesignationReportResponse,
    EmployeeStatusReportResponse,
    ExportJobStatusResponse,
    LeaveBalanceReportResponse,
    LeaveRequestReportResponse,
    LeaveSummaryReportResponse,
    MonthlyAttendanceReportResponse,
    OvertimeReportResponse,
    PayrollRegisterReportResponse,
    PayrollSummaryReportResponse,
    PendingApprovalReportResponse,
    ReportQueryRequest,
    SalaryRegisterReportResponse,
    SettlementLedgerReportResponse,
    SettlementSummaryReportResponse,
)
from app.modules.reports.service import ReportsService

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _principal(
    *,
    is_super_admin: bool = False,
    org_id: int = 1,
    branch_ids=(),
    department_ids=(),
    perms=None,
) -> CurrentUser:
    permissions = build_effective_permissions(
        is_super_admin=is_super_admin,
        feature_rows=perms or [],
        branch_ids=list(branch_ids),
        department_ids=list(department_ids),
    )
    return CurrentUser(
        user_id=1,
        org_id=org_id,
        is_super_admin=is_super_admin,
        is_active=True,
        permissions=permissions,
    )


def _perm(feature_key: str, **flags: bool) -> dict:
    base = {
        "feature_key": feature_key,
        "can_create": False,
        "can_read": False,
        "can_edit": False,
        "can_delete": False,
    }
    base.update(flags)
    return base


def _full_perms(*feature_keys: str) -> list[dict]:
    """Build read-enabled permissions for reports + given feature keys."""
    return [_perm("reports", can_read=True)] + [_perm(k, can_read=True) for k in feature_keys]


@pytest.fixture
def mock_cache():
    with (
        patch("app.modules.reports.service.cache_get_json", new_callable=AsyncMock) as mg,
        patch("app.modules.reports.service.cache_set_json", new_callable=AsyncMock) as ms,
    ):
        mg.return_value = None
        yield mg, ms


@pytest.fixture
def svc():
    session = AsyncMock()
    service = ReportsService(session)
    service.repo = AsyncMock()
    return service


@pytest.fixture
def super_admin():
    return _principal(is_super_admin=True)


# ===========================================================================
# 1. Authorization
# ===========================================================================


@pytest.mark.asyncio
async def test_missing_reports_read_permission(svc) -> None:
    user = _principal(perms=[_perm("employee", can_read=True)])
    with pytest.raises(AuthorizationException, match="reports:read"):
        await svc.get_employee_master_report(org_id=1, user=user, query=ReportQueryRequest())


@pytest.mark.asyncio
async def test_missing_source_module_permission(svc) -> None:
    user = _principal(perms=[_perm("reports", can_read=True)])
    with pytest.raises(AuthorizationException, match="employee:read"):
        await svc.get_employee_master_report(org_id=1, user=user, query=ReportQueryRequest())


@pytest.mark.asyncio
async def test_payroll_report_needs_payroll_permission(svc) -> None:
    user = _principal(perms=[_perm("reports", can_read=True)])
    svc.repo.get_payroll_register_report.return_value = ([], 0)
    with pytest.raises(AuthorizationException):
        await svc.get_payroll_register_report(org_id=1, user=user, query=ReportQueryRequest())


@pytest.mark.asyncio
async def test_leave_report_needs_leave_permission(svc) -> None:
    user = _principal(perms=[_perm("reports", can_read=True)])
    with pytest.raises(AuthorizationException):
        await svc.get_leave_balance_report(org_id=1, user=user, query=ReportQueryRequest())


@pytest.mark.asyncio
async def test_attendance_report_needs_attendance_permission(svc) -> None:
    user = _principal(perms=[_perm("reports", can_read=True)])
    with pytest.raises(AuthorizationException):
        await svc.get_daily_attendance_report(org_id=1, user=user, query=ReportQueryRequest())


@pytest.mark.asyncio
async def test_settlement_report_needs_settlement_permission(svc) -> None:
    user = _principal(perms=[_perm("reports", can_read=True)])
    with pytest.raises(AuthorizationException):
        await svc.get_settlement_ledger_report(org_id=1, user=user, query=ReportQueryRequest())


# ===========================================================================
# 2. Scope Isolation
# ===========================================================================


@pytest.mark.asyncio
async def test_super_admin_has_unrestricted_scope(svc, super_admin) -> None:
    svc.repo.get_employee_master_report.return_value = ([], 0)
    res = await svc.get_employee_master_report(
        org_id=1, user=super_admin, query=ReportQueryRequest()
    )
    assert isinstance(res, EmployeeMasterReportResponse)
    call_kwargs = svc.repo.get_employee_master_report.call_args.kwargs
    assert call_kwargs["branch_ids"] is None
    assert call_kwargs["dept_ids"] is None


@pytest.mark.asyncio
async def test_scoped_user_branch_dept_forwarded(svc) -> None:
    user = _principal(
        perms=_full_perms("employee"),
        branch_ids=(10, 20),
        department_ids=(30,),
    )
    svc.repo.get_employee_master_report.return_value = ([], 0)
    await svc.get_employee_master_report(org_id=1, user=user, query=ReportQueryRequest())
    call_kwargs = svc.repo.get_employee_master_report.call_args.kwargs
    assert call_kwargs["branch_ids"] == [10, 20]
    assert call_kwargs["dept_ids"] == [30]


@pytest.mark.asyncio
async def test_scope_violation_for_branch(svc) -> None:
    user = _principal(perms=_full_perms("employee"), branch_ids=(10,))
    query = ReportQueryRequest(branch_id=99)
    with pytest.raises(AuthorizationException, match="Missing branch access permission"):
        await svc.get_employee_master_report(org_id=1, user=user, query=query)


# ===========================================================================
# 3. Employee Reports — JSON
# ===========================================================================


@pytest.mark.asyncio
async def test_employee_master_json(svc, super_admin) -> None:
    svc.repo.get_employee_master_report.return_value = ([], 0)
    res = await svc.get_employee_master_report(
        org_id=1, user=super_admin, query=ReportQueryRequest()
    )
    assert isinstance(res, EmployeeMasterReportResponse)
    assert res.pagination.total_records == 0


@pytest.mark.asyncio
async def test_employee_joining_json(svc, super_admin) -> None:
    svc.repo.get_employee_joining_report.return_value = ([], 0)
    res = await svc.get_employee_joining_report(
        org_id=1, user=super_admin, query=ReportQueryRequest()
    )
    assert isinstance(res, EmployeeJoiningReportResponse)


@pytest.mark.asyncio
async def test_employee_status_json(svc, super_admin) -> None:
    svc.repo.get_employee_status_report.return_value = ([], 0)
    res = await svc.get_employee_status_report(
        org_id=1, user=super_admin, query=ReportQueryRequest()
    )
    assert isinstance(res, EmployeeStatusReportResponse)


@pytest.mark.asyncio
async def test_department_headcount_json(svc, super_admin) -> None:
    svc.repo.get_department_headcount_report.return_value = ([], 0)
    res = await svc.get_department_headcount_report(
        org_id=1, user=super_admin, query=ReportQueryRequest()
    )
    assert isinstance(res, EmployeesByDepartmentReportResponse)


@pytest.mark.asyncio
async def test_designation_headcount_json(svc, super_admin) -> None:
    svc.repo.get_designation_headcount_report.return_value = ([], 0)
    res = await svc.get_designation_headcount_report(
        org_id=1, user=super_admin, query=ReportQueryRequest()
    )
    assert isinstance(res, EmployeesByDesignationReportResponse)


@pytest.mark.asyncio
async def test_branch_headcount_json(svc, super_admin) -> None:
    svc.repo.get_branch_headcount_report.return_value = ([], 0)
    res = await svc.get_branch_headcount_report(
        org_id=1, user=super_admin, query=ReportQueryRequest()
    )
    assert isinstance(res, EmployeesByBranchReportResponse)


# ===========================================================================
# 4. Attendance Reports
# ===========================================================================


@pytest.mark.asyncio
async def test_daily_attendance_json(svc, super_admin) -> None:
    svc.repo.get_daily_attendance_report.return_value = ([], 0)
    res = await svc.get_daily_attendance_report(
        org_id=1, user=super_admin, query=ReportQueryRequest()
    )
    assert isinstance(res, DailyAttendanceReportResponse)


@pytest.mark.asyncio
async def test_monthly_attendance_json(svc, super_admin) -> None:
    svc.repo.get_monthly_attendance_report.return_value = ([], 0)
    res = await svc.get_monthly_attendance_report(
        org_id=1, user=super_admin, query=ReportQueryRequest()
    )
    assert isinstance(res, MonthlyAttendanceReportResponse)


@pytest.mark.asyncio
async def test_overtime_json(svc, super_admin) -> None:
    svc.repo.get_overtime_report.return_value = ([], 0)
    res = await svc.get_overtime_report(org_id=1, user=super_admin, query=ReportQueryRequest())
    assert isinstance(res, OvertimeReportResponse)


@pytest.mark.asyncio
async def test_attendance_summary_json(svc, super_admin) -> None:
    svc.repo.get_attendance_summary_report.return_value = {
        "total_records": 10,
        "present_count": 8,
        "absent_count": 2,
        "late_count": 1,
        "early_count": 0,
        "working_minutes_sum": 4800,
        "overtime_minutes_sum": 30,
        "status_counts": [],
    }
    res = await svc.get_attendance_summary_report(
        org_id=1, user=super_admin, query=ReportQueryRequest()
    )
    assert isinstance(res, AttendanceSummaryReportResponse)
    assert res.present_count == 8


# ===========================================================================
# 5. Leave Reports
# ===========================================================================


@pytest.mark.asyncio
async def test_leave_balance_json(svc, super_admin) -> None:
    svc.repo.get_leave_balance_report.return_value = ([], 0)
    res = await svc.get_leave_balance_report(org_id=1, user=super_admin, query=ReportQueryRequest())
    assert isinstance(res, LeaveBalanceReportResponse)


@pytest.mark.asyncio
async def test_leave_requests_json(svc, super_admin) -> None:
    svc.repo.get_leave_requests_report.return_value = ([], 0)
    res = await svc.get_leave_requests_report(
        org_id=1, user=super_admin, query=ReportQueryRequest()
    )
    assert isinstance(res, LeaveRequestReportResponse)


@pytest.mark.asyncio
async def test_leave_summary_json(svc, super_admin) -> None:
    svc.repo.get_leave_summary_report.return_value = {
        "total_requests": 5,
        "pending_count": 1,
        "approved_count": 3,
        "rejected_count": 1,
        "total_leave_days": 7.0,
        "by_type": {},
    }
    res = await svc.get_leave_summary_report(org_id=1, user=super_admin, query=ReportQueryRequest())
    assert isinstance(res, LeaveSummaryReportResponse)
    assert res.approved_count == 3


# ===========================================================================
# 6. Payroll Reports
# ===========================================================================


@pytest.mark.asyncio
async def test_payroll_register_json(svc, super_admin) -> None:
    svc.repo.get_payroll_register_report.return_value = ([], 0)
    res = await svc.get_payroll_register_report(
        org_id=1, user=super_admin, query=ReportQueryRequest()
    )
    assert isinstance(res, PayrollRegisterReportResponse)


@pytest.mark.asyncio
async def test_salary_register_json(svc, super_admin) -> None:
    svc.repo.get_salary_register_report.return_value = ([], 0)
    res = await svc.get_salary_register_report(
        org_id=1, user=super_admin, query=ReportQueryRequest()
    )
    assert isinstance(res, SalaryRegisterReportResponse)


@pytest.mark.asyncio
async def test_payroll_summary_json(svc, super_admin) -> None:
    svc.repo.get_payroll_summary_report.return_value = {
        "gross_sum": Decimal("100000"),
        "deductions_sum": Decimal("10000"),
        "net_payable_sum": Decimal("90000"),
        "total_headcount": 5,
    }
    res = await svc.get_payroll_summary_report(
        org_id=1, user=super_admin, query=ReportQueryRequest()
    )
    assert isinstance(res, PayrollSummaryReportResponse)
    assert res.total_headcount == 5


# ===========================================================================
# 7. Settlement Reports
# ===========================================================================


@pytest.mark.asyncio
async def test_settlement_ledger_json(svc, super_admin) -> None:
    svc.repo.get_settlement_ledger_report.return_value = ([], 0)
    res = await svc.get_settlement_ledger_report(
        org_id=1, user=super_admin, query=ReportQueryRequest()
    )
    assert isinstance(res, SettlementLedgerReportResponse)


@pytest.mark.asyncio
async def test_settlement_summary_json(svc, super_admin) -> None:
    svc.repo.get_settlement_summary_report.return_value = {
        "active_loans_count": 3,
        "closed_loans_count": 2,
        "total_principal_amount": Decimal("50000"),
        "total_outstanding_loans": Decimal("30000"),
        "total_outstanding_arrears": Decimal("2000"),
    }
    res = await svc.get_settlement_summary_report(
        org_id=1, user=super_admin, query=ReportQueryRequest()
    )
    assert isinstance(res, SettlementSummaryReportResponse)
    assert res.active_loans_count == 3


# ===========================================================================
# 8. Approval Reports
# ===========================================================================


@pytest.mark.asyncio
async def test_pending_approvals_json(svc, super_admin) -> None:
    svc.repo.get_pending_approvals_report.return_value = ([], 0)
    res = await svc.get_pending_approvals_report(
        org_id=1, user=super_admin, query=ReportQueryRequest()
    )
    assert isinstance(res, PendingApprovalReportResponse)


# ===========================================================================
# 9. CSV Export — synchronous (small result)
# ===========================================================================


@pytest.mark.asyncio
async def test_sync_csv_export_returns_file_bytes(svc, super_admin) -> None:
    row = {
        "code": "EMP01",
        "name": "John Doe",
        "mobile": None,
        "email": None,
        "branch": "HQ",
        "department": "IT",
        "designation": "Engineer",
        "employee_type": "full-time",
        "date_of_joining": "2022-01-01",
        "status": "active",
    }
    svc.repo.get_employee_master_report.return_value = ([row], 1)
    res = await svc.get_employee_master_report(
        org_id=1, user=super_admin, query=ReportQueryRequest(format="csv")
    )
    assert isinstance(res, dict)
    assert "file_bytes" in res
    assert res["media_type"] == "text/csv"
    assert b"EMP01" in res["file_bytes"]


@pytest.mark.asyncio
async def test_sync_excel_export_returns_file_bytes(svc, super_admin) -> None:
    svc.repo.get_employee_master_report.return_value = ([], 0)
    res = await svc.get_employee_master_report(
        org_id=1, user=super_admin, query=ReportQueryRequest(format="excel")
    )
    assert isinstance(res, dict)
    assert "application/vnd" in res["media_type"]


@pytest.mark.asyncio
async def test_sync_pdf_export_returns_file_bytes(svc, super_admin) -> None:
    svc.repo.get_employee_master_report.return_value = ([], 0)
    res = await svc.get_employee_master_report(
        org_id=1, user=super_admin, query=ReportQueryRequest(format="pdf")
    )
    assert isinstance(res, dict)
    assert res["media_type"] == "application/pdf"


# ===========================================================================
# 10. Async Export — large result (>1000 rows)
# ===========================================================================


@pytest.mark.asyncio
async def test_async_export_trigger_on_large_result(svc, super_admin, mock_cache) -> None:
    mock_get, mock_set = mock_cache
    svc.repo.get_employee_master_report.return_value = ([], 2000)

    res = await svc.get_employee_master_report(
        org_id=1, user=super_admin, query=ReportQueryRequest(format="csv")
    )
    assert isinstance(res, ExportJobStatusResponse)
    assert res.status == "pending"
    assert res.export_job_id is not None
    mock_set.assert_called()


# ===========================================================================
# 11. Export Job Status
# ===========================================================================


@pytest.mark.asyncio
async def test_get_export_job_status_not_found(svc, mock_cache) -> None:
    mock_get, _ = mock_cache
    mock_get.return_value = None
    with pytest.raises(NotFoundException):
        await svc.get_export_job_status(org_id=1, job_id="nonexistent")


@pytest.mark.asyncio
async def test_get_export_job_status_success(svc, mock_cache) -> None:
    mock_get, _ = mock_cache
    mock_get.return_value = {
        "export_job_id": "job_abc",
        "status": "completed",
        "download_url": "/api/v1/reports/exports/job_abc/download",
        "expires_at": "2026-07-11T10:00:00",
    }
    res = await svc.get_export_job_status(org_id=1, job_id="job_abc")
    assert isinstance(res, ExportJobStatusResponse)
    assert res.status == "completed"


# ===========================================================================
# 12. Validation — ReportQueryRequest
# ===========================================================================


def test_query_invalid_format_rejected() -> None:
    with pytest.raises(ValidationError):
        ReportQueryRequest(format="xml")


def test_query_invalid_period_rejected() -> None:
    with pytest.raises(ValidationError):
        ReportQueryRequest(period="biweekly")


def test_query_invalid_sort_dir_rejected() -> None:
    with pytest.raises(ValidationError):
        ReportQueryRequest(sort_dir="random")


def test_query_date_range_inversion_rejected() -> None:
    with pytest.raises(ValidationError):
        ReportQueryRequest(
            date_from=datetime.date(2026, 6, 1),
            date_to=datetime.date(2026, 1, 1),
        )


def test_query_date_range_exceeds_12_months() -> None:
    with pytest.raises(ValidationError):
        ReportQueryRequest(
            date_from=datetime.date(2024, 1, 1),
            date_to=datetime.date(2026, 6, 1),
        )


def test_query_valid_all_formats() -> None:
    for fmt in ("json", "csv", "excel", "pdf"):
        q = ReportQueryRequest(format=fmt)
        assert q.format == fmt


def test_query_valid_periods() -> None:
    for period in ("today", "week", "month", "quarter", "year"):
        q = ReportQueryRequest(period=period)
        assert q.period == period


def test_query_defaults() -> None:
    q = ReportQueryRequest()
    assert q.format == "json"
    assert q.sort_dir == "asc"
    assert q.page == 1
    assert q.page_size == 25


# ===========================================================================
# 13. Pagination
# ===========================================================================


@pytest.mark.asyncio
async def test_pagination_forwarded_to_repo(svc, super_admin) -> None:
    svc.repo.get_employee_master_report.return_value = ([], 0)
    query = ReportQueryRequest(page=3, page_size=10)
    await svc.get_employee_master_report(org_id=1, user=super_admin, query=query)
    call_kwargs = svc.repo.get_employee_master_report.call_args.kwargs
    assert call_kwargs["page"] == 3
    assert call_kwargs["page_size"] == 10


@pytest.mark.asyncio
async def test_filters_forwarded_to_repo(svc, super_admin) -> None:
    svc.repo.get_employee_master_report.return_value = ([], 0)
    query = ReportQueryRequest(
        branch_id=5,
        dept_id=7,
        designation_id=2,
        status="active",
        sort_by="name",
        sort_dir="desc",
    )
    await svc.get_employee_master_report(org_id=1, user=super_admin, query=query)
    kw = svc.repo.get_employee_master_report.call_args.kwargs
    assert kw.get("status") == "active"
    assert kw.get("sort_by") == "name"
    assert kw.get("sort_dir") == "desc"
