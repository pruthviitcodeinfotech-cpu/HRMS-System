"""Integration tests for the Reports Management router.

The ReportsService is mocked at the dependency level so tests exercise the
full FastAPI routing layer (auth, permission guard, response mapping) without
hitting the database or Redis.
"""

from __future__ import annotations

import datetime
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.modules.reports.dependencies import get_reports_service
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
    SalaryRegisterReportResponse,
    SettlementLedgerReportResponse,
    SettlementSummaryReportResponse,
)
from tests.conftest import API_PREFIX

BASE = f"{API_PREFIX}/reports"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_svc() -> AsyncMock:
    return AsyncMock()


@pytest_asyncio.fixture
async def rc(app, mock_svc: AsyncMock):
    """Reports client with mocked service and raise_app_exceptions=False
    so that 202 status codes set on the Response object are preserved."""
    from app.modules.reports.router import router as reports_router

    prefix = f"{API_PREFIX}/reports"
    already = any(getattr(r, "path", "").startswith(prefix) for r in app.routes)
    if not already:
        app.include_router(reports_router, prefix=API_PREFIX)

    app.dependency_overrides[get_reports_service] = lambda: mock_svc
    # raise_app_exceptions=False: lets us inspect 202 / 4xx without exception
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


def _empty_paginated(cls):
    """Build an empty paginated report response."""
    return cls.build(items=[], page=1, page_size=25, total_records=0)


def _job(status: str = "pending") -> ExportJobStatusResponse:
    return ExportJobStatusResponse(
        export_job_id="job_test",
        status=status,
        download_url=None if status == "pending" else "/api/v1/reports/exports/job_test/download",
        expires_at=datetime.datetime.now(datetime.UTC) + datetime.timedelta(hours=1),
    )


def _file_response(fmt: str = "csv") -> dict:
    media = {
        "csv": "text/csv",
        "excel": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "pdf": "application/pdf",
    }[fmt]
    return {
        "file_bytes": b"mock_file_content",
        "filename": f"report.{fmt}",
        "media_type": media,
    }


# ===========================================================================
# 1. Unauthenticated request
# ===========================================================================


@pytest.mark.asyncio
async def test_unauthenticated_request_returns_401(rc: AsyncClient) -> None:
    resp = await rc.get(f"{BASE}/employees/master")
    assert resp.status_code == 401


# ===========================================================================
# 2. Employee Reports
# ===========================================================================


@pytest.mark.asyncio
async def test_employee_master_json(
    rc: AsyncClient, mock_svc: AsyncMock, super_admin_headers: dict
) -> None:
    mock_svc.get_employee_master_report.return_value = _empty_paginated(
        EmployeeMasterReportResponse
    )
    resp = await rc.get(f"{BASE}/employees/master", headers=super_admin_headers)
    assert resp.status_code == 200
    assert resp.json()["data"]["items"] == []
    mock_svc.get_employee_master_report.assert_called_once()


@pytest.mark.asyncio
async def test_employee_master_csv_sync(
    rc: AsyncClient, mock_svc: AsyncMock, super_admin_headers: dict
) -> None:
    mock_svc.get_employee_master_report.return_value = _file_response("csv")
    resp = await rc.get(
        f"{BASE}/employees/master", params={"format": "csv"}, headers=super_admin_headers
    )
    assert resp.status_code == 200
    assert "attachment" in resp.headers.get("content-disposition", "")
    assert resp.content == b"mock_file_content"


@pytest.mark.asyncio
async def test_employee_master_async_job(
    rc: AsyncClient, mock_svc: AsyncMock, super_admin_headers: dict
) -> None:
    mock_svc.get_employee_master_report.return_value = _job("pending")
    resp = await rc.get(
        f"{BASE}/employees/master", params={"format": "csv"}, headers=super_admin_headers
    )
    assert resp.status_code == 202
    assert resp.json()["data"]["export_job_id"] == "job_test"


@pytest.mark.asyncio
async def test_employee_joining_json(
    rc: AsyncClient, mock_svc: AsyncMock, super_admin_headers: dict
) -> None:
    mock_svc.get_employee_joining_report.return_value = _empty_paginated(
        EmployeeJoiningReportResponse
    )
    resp = await rc.get(f"{BASE}/employees/joining", headers=super_admin_headers)
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_employee_status_json(
    rc: AsyncClient, mock_svc: AsyncMock, super_admin_headers: dict
) -> None:
    mock_svc.get_employee_status_report.return_value = _empty_paginated(
        EmployeeStatusReportResponse
    )
    resp = await rc.get(f"{BASE}/employees/status", headers=super_admin_headers)
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_employee_by_department_json(
    rc: AsyncClient, mock_svc: AsyncMock, super_admin_headers: dict
) -> None:
    mock_svc.get_department_headcount_report.return_value = _empty_paginated(
        EmployeesByDepartmentReportResponse
    )
    resp = await rc.get(f"{BASE}/employees/by-department", headers=super_admin_headers)
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_employee_by_designation_json(
    rc: AsyncClient, mock_svc: AsyncMock, super_admin_headers: dict
) -> None:
    mock_svc.get_designation_headcount_report.return_value = _empty_paginated(
        EmployeesByDesignationReportResponse
    )
    resp = await rc.get(f"{BASE}/employees/by-designation", headers=super_admin_headers)
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_employee_by_branch_json(
    rc: AsyncClient, mock_svc: AsyncMock, super_admin_headers: dict
) -> None:
    mock_svc.get_branch_headcount_report.return_value = _empty_paginated(
        EmployeesByBranchReportResponse
    )
    resp = await rc.get(f"{BASE}/employees/by-branch", headers=super_admin_headers)
    assert resp.status_code == 200


# ===========================================================================
# 3. Attendance Reports
# ===========================================================================


@pytest.mark.asyncio
async def test_attendance_daily_json(
    rc: AsyncClient, mock_svc: AsyncMock, super_admin_headers: dict
) -> None:
    mock_svc.get_daily_attendance_report.return_value = _empty_paginated(
        DailyAttendanceReportResponse
    )
    resp = await rc.get(f"{BASE}/attendance/daily", headers=super_admin_headers)
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_attendance_monthly_json(
    rc: AsyncClient, mock_svc: AsyncMock, super_admin_headers: dict
) -> None:
    mock_svc.get_monthly_attendance_report.return_value = _empty_paginated(
        MonthlyAttendanceReportResponse
    )
    resp = await rc.get(f"{BASE}/attendance/monthly", headers=super_admin_headers)
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_attendance_overtime_json(
    rc: AsyncClient, mock_svc: AsyncMock, super_admin_headers: dict
) -> None:
    mock_svc.get_overtime_report.return_value = _empty_paginated(OvertimeReportResponse)
    resp = await rc.get(f"{BASE}/attendance/overtime", headers=super_admin_headers)
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_attendance_summary_json(
    rc: AsyncClient, mock_svc: AsyncMock, super_admin_headers: dict
) -> None:
    mock_svc.get_attendance_summary_report.return_value = AttendanceSummaryReportResponse(
        total_records=10,
        present_count=8,
        absent_count=2,
        late_count=1,
        early_count=0,
        working_minutes_sum=4800,
        overtime_minutes_sum=30,
        status_counts=[],
    )
    resp = await rc.get(f"{BASE}/attendance/summary", headers=super_admin_headers)
    assert resp.status_code == 200
    assert resp.json()["data"]["present_count"] == 8


@pytest.mark.asyncio
async def test_attendance_csv_download(
    rc: AsyncClient, mock_svc: AsyncMock, super_admin_headers: dict
) -> None:
    mock_svc.get_daily_attendance_report.return_value = _file_response("csv")
    resp = await rc.get(
        f"{BASE}/attendance/daily", params={"format": "csv"}, headers=super_admin_headers
    )
    assert resp.status_code == 200
    assert "attachment" in resp.headers.get("content-disposition", "")


# ===========================================================================
# 4. Leave Reports
# ===========================================================================


@pytest.mark.asyncio
async def test_leave_balance_json(
    rc: AsyncClient, mock_svc: AsyncMock, super_admin_headers: dict
) -> None:
    mock_svc.get_leave_balance_report.return_value = _empty_paginated(LeaveBalanceReportResponse)
    resp = await rc.get(f"{BASE}/leave/balance", headers=super_admin_headers)
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_leave_requests_json(
    rc: AsyncClient, mock_svc: AsyncMock, super_admin_headers: dict
) -> None:
    mock_svc.get_leave_requests_report.return_value = _empty_paginated(LeaveRequestReportResponse)
    resp = await rc.get(f"{BASE}/leave/requests", headers=super_admin_headers)
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_leave_summary_json(
    rc: AsyncClient, mock_svc: AsyncMock, super_admin_headers: dict
) -> None:
    mock_svc.get_leave_summary_report.return_value = LeaveSummaryReportResponse(
        total_requests=3,
        pending_count=0,
        approved_count=3,
        rejected_count=0,
        total_leave_days=6.0,
        by_type={},
    )
    resp = await rc.get(f"{BASE}/leave/summary", headers=super_admin_headers)
    assert resp.status_code == 200
    assert resp.json()["data"]["approved_count"] == 3


# ===========================================================================
# 5. Payroll Reports
# ===========================================================================


@pytest.mark.asyncio
async def test_payroll_register_json(
    rc: AsyncClient, mock_svc: AsyncMock, super_admin_headers: dict
) -> None:
    mock_svc.get_payroll_register_report.return_value = _empty_paginated(
        PayrollRegisterReportResponse
    )
    resp = await rc.get(f"{BASE}/payroll/register", headers=super_admin_headers)
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_payroll_salary_register_json(
    rc: AsyncClient, mock_svc: AsyncMock, super_admin_headers: dict
) -> None:
    mock_svc.get_salary_register_report.return_value = _empty_paginated(
        SalaryRegisterReportResponse
    )
    resp = await rc.get(f"{BASE}/payroll/salary-register", headers=super_admin_headers)
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_payroll_summary_json(
    rc: AsyncClient, mock_svc: AsyncMock, super_admin_headers: dict
) -> None:
    mock_svc.get_payroll_summary_report.return_value = PayrollSummaryReportResponse(
        gross_sum=Decimal("100000"),
        deductions_sum=Decimal("10000"),
        net_payable_sum=Decimal("90000"),
        total_headcount=10,
    )
    resp = await rc.get(f"{BASE}/payroll/summary", headers=super_admin_headers)
    assert resp.status_code == 200
    assert resp.json()["data"]["total_headcount"] == 10


@pytest.mark.asyncio
async def test_payroll_register_with_filters(
    rc: AsyncClient, mock_svc: AsyncMock, super_admin_headers: dict
) -> None:
    mock_svc.get_payroll_register_report.return_value = _empty_paginated(
        PayrollRegisterReportResponse
    )
    resp = await rc.get(
        f"{BASE}/payroll/register",
        params={"payroll_group_id": 1, "salary_cycle_id": 2},
        headers=super_admin_headers,
    )
    assert resp.status_code == 200
    call_kwargs = mock_svc.get_payroll_register_report.call_args.kwargs
    assert call_kwargs["payroll_group_id"] == 1
    assert call_kwargs["salary_cycle_id"] == 2


# ===========================================================================
# 6. Settlement Reports
# ===========================================================================


@pytest.mark.asyncio
async def test_settlement_ledger_json(
    rc: AsyncClient, mock_svc: AsyncMock, super_admin_headers: dict
) -> None:
    mock_svc.get_settlement_ledger_report.return_value = _empty_paginated(
        SettlementLedgerReportResponse
    )
    resp = await rc.get(f"{BASE}/settlements/ledger", headers=super_admin_headers)
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_settlement_summary_json(
    rc: AsyncClient, mock_svc: AsyncMock, super_admin_headers: dict
) -> None:
    mock_svc.get_settlement_summary_report.return_value = SettlementSummaryReportResponse(
        active_loans_count=2,
        closed_loans_count=5,
        total_principal_amount=Decimal("100000"),
        total_outstanding_loans=Decimal("60000"),
        total_outstanding_arrears=Decimal("5000"),
    )
    resp = await rc.get(f"{BASE}/settlements/summary", headers=super_admin_headers)
    assert resp.status_code == 200
    assert resp.json()["data"]["active_loans_count"] == 2


# ===========================================================================
# 7. Approval Reports
# ===========================================================================


@pytest.mark.asyncio
async def test_pending_approvals_json(
    rc: AsyncClient, mock_svc: AsyncMock, super_admin_headers: dict
) -> None:
    mock_svc.get_pending_approvals_report.return_value = _empty_paginated(
        PendingApprovalReportResponse
    )
    resp = await rc.get(f"{BASE}/approvals/pending", headers=super_admin_headers)
    assert resp.status_code == 200


# ===========================================================================
# 8. Export Job endpoints
# ===========================================================================


@pytest.mark.asyncio
async def test_export_job_status_endpoint(
    rc: AsyncClient, mock_svc: AsyncMock, super_admin_headers: dict
) -> None:
    mock_svc.get_export_job_status.return_value = _job("completed")
    resp = await rc.get(f"{BASE}/exports/job_test", headers=super_admin_headers)
    assert resp.status_code == 200
    assert resp.json()["data"]["status"] == "completed"
    mock_svc.get_export_job_status.assert_called_once_with(org_id=1, job_id="job_test")


@pytest.mark.asyncio
async def test_export_file_download_endpoint(
    rc: AsyncClient, mock_svc: AsyncMock, super_admin_headers: dict
) -> None:
    mock_svc.get_export_file.return_value = _file_response("csv")
    resp = await rc.get(f"{BASE}/exports/job_test/download", headers=super_admin_headers)
    assert resp.status_code == 200
    assert resp.content == b"mock_file_content"
    assert "attachment" in resp.headers.get("content-disposition", "")
    mock_svc.get_export_file.assert_called_once_with(org_id=1, job_id="job_test")


@pytest.mark.asyncio
async def test_export_pdf_download_endpoint(
    rc: AsyncClient, mock_svc: AsyncMock, super_admin_headers: dict
) -> None:
    mock_svc.get_export_file.return_value = _file_response("pdf")
    resp = await rc.get(f"{BASE}/exports/job_test/download", headers=super_admin_headers)
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"


# ===========================================================================
# 9. Dynamic Filters forwarding
# ===========================================================================


@pytest.mark.asyncio
async def test_query_filters_forwarded(
    rc: AsyncClient, mock_svc: AsyncMock, super_admin_headers: dict
) -> None:
    mock_svc.get_employee_master_report.return_value = _empty_paginated(
        EmployeeMasterReportResponse
    )
    resp = await rc.get(
        f"{BASE}/employees/master",
        params={
            "page": 2,
            "page_size": 10,
            "branch_id": 5,
            "dept_id": 3,
            "status": "active",
            "sort_by": "name",
            "sort_dir": "desc",
        },
        headers=super_admin_headers,
    )
    assert resp.status_code == 200
    call_kwargs = mock_svc.get_employee_master_report.call_args.kwargs
    query = call_kwargs["query"]
    assert query.page == 2
    assert query.page_size == 10
    assert query.branch_id == 5
    assert query.dept_id == 3
    assert query.status == "active"
    assert query.sort_by == "name"
    assert query.sort_dir == "desc"


@pytest.mark.asyncio
async def test_date_range_filter_forwarded(
    rc: AsyncClient, mock_svc: AsyncMock, super_admin_headers: dict
) -> None:
    mock_svc.get_daily_attendance_report.return_value = _empty_paginated(
        DailyAttendanceReportResponse
    )
    resp = await rc.get(
        f"{BASE}/attendance/daily",
        params={"date_from": "2026-01-01", "date_to": "2026-01-31"},
        headers=super_admin_headers,
    )
    assert resp.status_code == 200
    q = mock_svc.get_daily_attendance_report.call_args.kwargs["query"]
    assert str(q.date_from) == "2026-01-01"
    assert str(q.date_to) == "2026-01-31"


@pytest.mark.asyncio
async def test_invalid_format_returns_422(rc: AsyncClient, super_admin_headers: dict) -> None:
    resp = await rc.get(
        f"{BASE}/employees/master",
        params={"format": "xml"},
        headers=super_admin_headers,
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_invalid_sort_dir_returns_422(rc: AsyncClient, super_admin_headers: dict) -> None:
    resp = await rc.get(
        f"{BASE}/employees/master",
        params={"sort_dir": "random"},
        headers=super_admin_headers,
    )
    assert resp.status_code == 422
