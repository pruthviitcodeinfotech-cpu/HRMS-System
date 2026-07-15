"""Dashboard Management — HTTP routes (thin controllers).

Maps every endpoint in the approved Dashboard API Contract onto FastAPI
handlers. Controllers resolve dependencies, call DashboardService, and return
standard SuccessResponse envelopes. No business logic lives here.
"""

from __future__ import annotations

import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, status

from app.core.constants.enums import PermissionAction as A
from app.core.dependencies.auth import (
    CurrentUser,
    get_current_active_user,
    require_permission,
)
from app.core.exceptions.base import AppException
from app.core.middleware.request_context import get_request_id
from app.modules.dashboard.dependencies import DashboardServiceDep
from app.modules.dashboard.schemas import (
    ApprovalDashboardResponse,
    AttendanceDashboardResponse,
    ChartResponseSchema,
    DashboardKPIsResponse,
    DashboardStatisticsResponse,
    DashboardSummaryResponse,
    EmployeeDashboardResponse,
    HardwareDashboardResponse,
    LeaveDashboardResponse,
    NotificationDashboardResponse,
    PayrollDashboardResponse,
    SettlementDashboardResponse,
    WidgetsMetadataResponse,
    ShiftSummaryResponse,
    PendingBiometricsResponse,
)
from app.shared.schemas.response import SuccessResponse, success_response

router = APIRouter(prefix="/dashboard", tags=["Dashboard Management"])

_FEATURE_KEY = "dashboard"


# =========================================================================
# Common Dependencies & Helpers
# =========================================================================


def get_org_id(current_user: Annotated[CurrentUser, Depends(get_current_active_user)]) -> int:
    """Return the caller's tenant organization ID, or raise TENANT_UNRESOLVED if absent."""
    if current_user.org_id is None:
        exc = AppException("Organization context is required.", code="TENANT_UNRESOLVED")
        exc.status_code = status.HTTP_400_BAD_REQUEST
        raise exc
    return current_user.org_id


OrgIdDep = Annotated[int, Depends(get_org_id)]
CurrentUserDep = Annotated[CurrentUser, Depends(get_current_active_user)]


def _ok(data: Any, message: str = "OK") -> dict[str, Any]:
    """Helper to wrap controller responses in the standard SuccessResponse envelope."""
    return success_response(data=data, message=message, request_id=get_request_id())


# =========================================================================
# 1. Main Summary, Widgets, KPIs & Statistics
# =========================================================================


@router.get(
    "/summary",
    response_model=SuccessResponse[DashboardSummaryResponse],
    summary="Dashboard Summary",
    description="Headline KPIs across all permitted modules.",
    dependencies=[Depends(require_permission(_FEATURE_KEY, A.READ))],
)
async def get_summary(
    service: DashboardServiceDep,
    org_id: OrgIdDep,
    current_user: CurrentUserDep,
    date: Annotated[
        datetime.date | None,
        Query(description="Target date for the summary metrics. Defaults to today."),
    ] = None,
) -> dict[str, Any]:
    """Retrieve summarized dashboard metrics across all modules."""
    res = await service.get_summary(org_id=org_id, user=current_user, target_date=date)
    return _ok(res)


@router.get(
    "/widgets",
    response_model=SuccessResponse[WidgetsMetadataResponse],
    summary="Dashboard Widgets",
    description="Metadata: which widgets the caller can see.",
    dependencies=[Depends(require_permission(_FEATURE_KEY, A.READ))],
)
async def get_widgets(
    service: DashboardServiceDep,
    org_id: OrgIdDep,
    current_user: CurrentUserDep,
) -> dict[str, Any]:
    """Retrieve metadata configuration indicating widgets accessibility."""
    res = service.get_widgets_metadata(org_id=org_id, user=current_user)
    return _ok(res)


@router.get(
    "/kpis",
    response_model=SuccessResponse[DashboardKPIsResponse],
    summary="Dashboard KPIs",
    description="The flat headline KPI number set.",
    dependencies=[Depends(require_permission(_FEATURE_KEY, A.READ))],
)
async def get_kpis(
    service: DashboardServiceDep,
    org_id: OrgIdDep,
    current_user: CurrentUserDep,
    date: Annotated[
        datetime.date | None, Query(description="Target date for the KPIs. Defaults to today.")
    ] = None,
) -> dict[str, Any]:
    """Retrieve flat metrics set across all modules."""
    res = await service.get_kpis(org_id=org_id, user=current_user, target_date=date)
    return _ok(res)


@router.get(
    "/statistics",
    response_model=SuccessResponse[DashboardStatisticsResponse],
    summary="Dashboard Statistics",
    description="Broader per-module statistic ratios.",
    dependencies=[Depends(require_permission(_FEATURE_KEY, A.READ))],
)
async def get_statistics(
    service: DashboardServiceDep,
    org_id: OrgIdDep,
    current_user: CurrentUserDep,
    date: Annotated[
        datetime.date | None, Query(description="Target date for ratios. Defaults to today.")
    ] = None,
) -> dict[str, Any]:
    """Retrieve computed ratios for employee turnover, attendance, and device uptime."""
    res = await service.get_statistics(org_id=org_id, user=current_user, target_date=date)
    return _ok(res)


# =========================================================================
# 2. Individual Per-Module Dashboards
# =========================================================================


@router.get(
    "/employees",
    response_model=SuccessResponse[EmployeeDashboardResponse],
    summary="Employee Dashboard",
    description="Detailed metrics and distributions for employees.",
    dependencies=[Depends(require_permission(_FEATURE_KEY, A.READ))],
)
async def get_employee_dashboard(
    service: DashboardServiceDep,
    org_id: OrgIdDep,
    current_user: CurrentUserDep,
    date: Annotated[
        datetime.date | None, Query(description="Target date for employee snapshot.")
    ] = None,
) -> dict[str, Any]:
    """Retrieve employee counts and breakdown distributions (dept, branch, status)."""
    res = await service.get_employee_dashboard(org_id=org_id, user=current_user, target_date=date)
    return _ok(res)


@router.get(
    "/attendance",
    response_model=SuccessResponse[AttendanceDashboardResponse],
    summary="Attendance Dashboard",
    description="Detailed metrics and trend for attendance.",
    dependencies=[Depends(require_permission(_FEATURE_KEY, A.READ))],
)
async def get_attendance_dashboard(
    service: DashboardServiceDep,
    org_id: OrgIdDep,
    current_user: CurrentUserDep,
    date: Annotated[
        datetime.date | None,
        Query(description="Target date for attendance metrics. Defaults to today."),
    ] = None,
) -> dict[str, Any]:
    """Retrieve daily attendance statuses plus historical daily trend logs."""
    res = await service.get_attendance_dashboard(org_id=org_id, user=current_user, target_date=date)
    return _ok(res)


@router.get(
    "/shifts",
    response_model=SuccessResponse[ShiftSummaryResponse],
    summary="Dashboard Shift Summary",
    description="Today's attendance counts grouped by shift.",
    dependencies=[Depends(require_permission(_FEATURE_KEY, A.READ))],
)
async def get_shift_summary(
    service: DashboardServiceDep,
    org_id: OrgIdDep,
    current_user: CurrentUserDep,
    date: Annotated[
        datetime.date | None,
        Query(description="Target date for shift attendance metrics. Defaults to today."),
    ] = None,
) -> dict[str, Any]:
    """Retrieve daily attendance metrics grouped by shift."""
    res = await service.get_shift_summary(org_id=org_id, user=current_user, target_date=date)
    return _ok(res)


@router.get(
    "/biometrics/pending",
    response_model=SuccessResponse[PendingBiometricsResponse],
    summary="Dashboard Pending Biometrics Employees",
    description="List of employees whose biometric enrollment is pending.",
    dependencies=[Depends(require_permission(_FEATURE_KEY, A.READ))],
)
async def get_pending_biometrics_employees(
    service: DashboardServiceDep,
    org_id: OrgIdDep,
    current_user: CurrentUserDep,
    search: Annotated[
        str | None,
        Query(description="Search by employee name or code"),
    ] = None,
    page: Annotated[
        int,
        Query(ge=1, description="1-based page number"),
    ] = 1,
    page_size: Annotated[
        int,
        Query(ge=1, le=100, description="Items per page"),
    ] = 20,
) -> dict[str, Any]:
    """Retrieve daily attendance metrics grouped by shift."""
    res = await service.get_pending_biometrics_employees(
        org_id=org_id,
        user=current_user,
        search=search,
        page=page,
        page_size=page_size,
    )
    return _ok(res)




@router.get(
    "/leave",
    response_model=SuccessResponse[LeaveDashboardResponse],
    summary="Leave Dashboard",
    description="Detailed metrics and leave type breakdown.",
    dependencies=[Depends(require_permission(_FEATURE_KEY, A.READ))],
)
async def get_leave_dashboard(
    service: DashboardServiceDep,
    org_id: OrgIdDep,
    current_user: CurrentUserDep,
    date: Annotated[
        datetime.date | None,
        Query(description="Target date for leave requests filter. Defaults to today."),
    ] = None,
) -> dict[str, Any]:
    """Retrieve leave requests totals, statuses, and category type breakdowns."""
    res = await service.get_leave_dashboard(org_id=org_id, user=current_user, target_date=date)
    return _ok(res)


@router.get(
    "/approvals",
    response_model=SuccessResponse[ApprovalDashboardResponse],
    summary="Approval Dashboard",
    description="Pending approval requests count, types, and recent decisions list.",
    dependencies=[Depends(require_permission(_FEATURE_KEY, A.READ))],
)
async def get_approval_dashboard(
    service: DashboardServiceDep,
    org_id: OrgIdDep,
    current_user: CurrentUserDep,
) -> dict[str, Any]:
    """Retrieve pending approvals mapping and recent approval log brief items."""
    res = await service.get_approval_dashboard(org_id=org_id, user=current_user)
    return _ok(res)


@router.get(
    "/payroll",
    response_model=SuccessResponse[PayrollDashboardResponse],
    summary="Payroll Dashboard",
    description="Latest payroll cycles, finalization amount, and headcounts.",
    dependencies=[Depends(require_permission(_FEATURE_KEY, A.READ))],
)
async def get_payroll_dashboard(
    service: DashboardServiceDep,
    org_id: OrgIdDep,
    current_user: CurrentUserDep,
) -> dict[str, Any]:
    """Retrieve current payroll cycle status, payment state breakdown, and finalized metrics."""
    res = await service.get_payroll_dashboard(org_id=org_id, user=current_user)
    return _ok(res)


@router.get(
    "/settlements",
    response_model=SuccessResponse[SettlementDashboardResponse],
    summary="Settlement Dashboard",
    description="Loans/advances statuses and outstanding arrears sum.",
    dependencies=[Depends(require_permission(_FEATURE_KEY, A.READ))],
)
async def get_settlement_dashboard(
    service: DashboardServiceDep,
    org_id: OrgIdDep,
    current_user: CurrentUserDep,
) -> dict[str, Any]:
    """Retrieve active loans/advances metrics and outstanding arrears balances."""
    res = await service.get_settlement_dashboard(org_id=org_id, user=current_user)
    return _ok(res)


@router.get(
    "/devices",
    response_model=SuccessResponse[HardwareDashboardResponse],
    summary="Hardware Dashboard",
    description="Biometric hardware devices status and sync metadata.",
    dependencies=[Depends(require_permission(_FEATURE_KEY, A.READ))],
)
async def get_hardware_dashboard(
    service: DashboardServiceDep,
    org_id: OrgIdDep,
    current_user: CurrentUserDep,
) -> dict[str, Any]:
    """Retrieve online/offline biometric device aggregates and sync timestamps."""
    res = await service.get_hardware_dashboard(org_id=org_id, user=current_user)
    return _ok(res)


@router.get(
    "/notifications",
    response_model=SuccessResponse[NotificationDashboardResponse],
    summary="Notification Dashboard Summary",
    description="Unread notifications count and recent notification alerts.",
    dependencies=[Depends(require_permission(_FEATURE_KEY, A.READ))],
)
async def get_notification_dashboard(
    service: DashboardServiceDep,
    org_id: OrgIdDep,
    current_user: CurrentUserDep,
    limit: Annotated[
        int, Query(description="Maximum notification logs to retrieve in list.", ge=1)
    ] = 5,
) -> dict[str, Any]:
    """Retrieve active notification count and recent inbox items for the caller."""
    res = await service.get_notification_dashboard(org_id=org_id, user=current_user, limit=limit)
    return _ok(res)


@router.get(
    "/recent-activity",
    response_model=SuccessResponse[list[dict[str, Any]]],
    summary="Recent Activity Feed",
    description="Recent chronological action audit logs.",
    dependencies=[Depends(require_permission(_FEATURE_KEY, A.READ))],
)
async def get_recent_activity(
    service: DashboardServiceDep,
    org_id: OrgIdDep,
    current_user: CurrentUserDep,
    limit: Annotated[int, Query(description="Maximum activity audit logs to retrieve.", ge=1)] = 10,
) -> dict[str, Any]:
    """Retrieve recent tenant audit log activities."""
    res = await service.get_recent_activity(org_id=org_id, user=current_user, limit=limit)
    return _ok(res)


# =========================================================================
# 3. Chart Projections
# =========================================================================


@router.get(
    "/charts/attendance-trend",
    response_model=SuccessResponse[ChartResponseSchema],
    summary="Attendance Trend Chart",
    description="Attendance status series points grouped by date.",
    dependencies=[Depends(require_permission(_FEATURE_KEY, A.READ))],
)
async def get_attendance_trend_chart(
    service: DashboardServiceDep,
    org_id: OrgIdDep,
    current_user: CurrentUserDep,
    days: Annotated[
        int, Query(description="Number of days to group trend metrics over.", ge=1)
    ] = 30,
) -> dict[str, Any]:
    """Retrieve attendance status chart points over time."""
    res = await service.get_attendance_trend_chart(org_id=org_id, user=current_user, days=days)
    return _ok(res)


@router.get(
    "/charts/employee-growth",
    response_model=SuccessResponse[ChartResponseSchema],
    summary="Employee Growth Chart",
    description="Employee count cumulative progression series.",
    dependencies=[Depends(require_permission(_FEATURE_KEY, A.READ))],
)
async def get_employee_growth_chart(
    service: DashboardServiceDep,
    org_id: OrgIdDep,
    current_user: CurrentUserDep,
    months: Annotated[
        int, Query(description="Number of historical months to project growth over.", ge=1)
    ] = 6,
) -> dict[str, Any]:
    """Retrieve cumulative employee growth trend data points."""
    res = await service.get_employee_growth_chart(org_id=org_id, user=current_user, months=months)
    return _ok(res)


@router.get(
    "/charts/leave-trend",
    response_model=SuccessResponse[ChartResponseSchema],
    summary="Leave Trend Chart",
    description="Leave request status points grouped by month.",
    dependencies=[Depends(require_permission(_FEATURE_KEY, A.READ))],
)
async def get_leave_trend_chart(
    service: DashboardServiceDep,
    org_id: OrgIdDep,
    current_user: CurrentUserDep,
    months: Annotated[
        int, Query(description="Number of months to group leave trend over.", ge=1)
    ] = 6,
) -> dict[str, Any]:
    """Retrieve leave status series points over time."""
    res = await service.get_leave_trend_chart(org_id=org_id, user=current_user, months=months)
    return _ok(res)


@router.get(
    "/charts/payroll-trend",
    response_model=SuccessResponse[ChartResponseSchema],
    summary="Payroll Cost Trend Chart",
    description="Payroll cost series points grouped by salary cycles.",
    dependencies=[Depends(require_permission(_FEATURE_KEY, A.READ))],
)
async def get_payroll_trend_chart(
    service: DashboardServiceDep,
    org_id: OrgIdDep,
    current_user: CurrentUserDep,
    limit: Annotated[
        int, Query(description="Maximum number of historical payroll cycles to include.", ge=1)
    ] = 6,
) -> dict[str, Any]:
    """Retrieve historical payroll monetary runs cost series points."""
    res = await service.get_payroll_trend_chart(org_id=org_id, user=current_user, limit=limit)
    return _ok(res)


@router.get(
    "/charts/department-attendance",
    response_model=SuccessResponse[ChartResponseSchema],
    summary="Department Attendance Chart",
    description="Attendance status series points grouped by department.",
    dependencies=[Depends(require_permission(_FEATURE_KEY, A.READ))],
)
async def get_dept_attendance_chart(
    service: DashboardServiceDep,
    org_id: OrgIdDep,
    current_user: CurrentUserDep,
    date: Annotated[
        datetime.date | None,
        Query(description="Target date for department statistics. Defaults to today."),
    ] = None,
) -> dict[str, Any]:
    """Retrieve department attendance series metrics."""
    res = await service.get_dept_attendance_chart(
        org_id=org_id, user=current_user, target_date=date
    )
    return _ok(res)


@router.get(
    "/charts/branch-attendance",
    response_model=SuccessResponse[ChartResponseSchema],
    summary="Branch Attendance Chart",
    description="Attendance status series points grouped by branch.",
    dependencies=[Depends(require_permission(_FEATURE_KEY, A.READ))],
)
async def get_branch_attendance_chart(
    service: DashboardServiceDep,
    org_id: OrgIdDep,
    current_user: CurrentUserDep,
    date: Annotated[
        datetime.date | None,
        Query(description="Target date for branch statistics. Defaults to today."),
    ] = None,
) -> dict[str, Any]:
    """Retrieve branch attendance series metrics."""
    res = await service.get_branch_attendance_chart(
        org_id=org_id, user=current_user, target_date=date
    )
    return _ok(res)
