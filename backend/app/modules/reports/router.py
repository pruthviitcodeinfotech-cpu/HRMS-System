"""Reports Management — HTTP routes (thin controllers).

Maps every endpoint in the approved Reports API Contract onto FastAPI handlers.
Controllers resolve dependencies, call ReportsService, and return standard
SuccessResponse envelopes or synchronous file streams.
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, Response, status

from app.core.constants.enums import PermissionAction as A
from app.core.dependencies.auth import (
    CurrentUser,
    get_current_active_user,
    require_permission,
)
from app.core.exceptions.base import AppException
from app.core.middleware.request_context import get_request_id
from app.modules.reports.dependencies import ReportsServiceDep
from app.modules.reports.schemas import (
    ExportJobStatusResponse,
    ReportQueryRequest,
)
from app.shared.schemas.response import SuccessResponse, success_response

router = APIRouter(prefix="/reports", tags=["Reports Management"])

_FEATURE_KEY = "reports"


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
ReportQueryDep = Annotated[ReportQueryRequest, Depends()]


async def _map_report_result(
    res: Any,
    response: Response,
    success_msg: str = "Report generated successfully.",
) -> Any:
    """Helper to map service report output to the correct HTTP response."""
    if isinstance(res, dict) and "file_bytes" in res:
        return Response(
            content=res["file_bytes"],
            media_type=res["media_type"],
            headers={"Content-Disposition": f'attachment; filename="{res["filename"]}"'},
        )

    if isinstance(res, ExportJobStatusResponse):
        response.status_code = status.HTTP_202_ACCEPTED
        return success_response(
            data=res,
            message="Report export job initiated.",
            request_id=get_request_id(),
        )

    from pydantic import BaseModel
    if isinstance(res, BaseModel) and hasattr(res, "data"):
        return success_response(
            data=res.data,
            message=success_msg,
            request_id=get_request_id(),
        )

    return success_response(
        data=res,
        message=success_msg,
        request_id=get_request_id(),
    )


# =========================================================================
# 1. Employee Reports
# =========================================================================


@router.get(
    "/employees/master",
    response_model=None,
    responses={
        202: {
            "model": SuccessResponse[ExportJobStatusResponse],
            "description": "Large export job accepted.",
        },
        200: {"description": "JSON report data or synchronous file download (CSV/Excel/PDF)."},
    },
    summary="Employee Master Report",
    description="Fetch employee master roster.",
    dependencies=[Depends(require_permission(_FEATURE_KEY, A.READ))],
)
async def get_employee_master_report(
    service: ReportsServiceDep,
    org_id: OrgIdDep,
    current_user: CurrentUserDep,
    response: Response,
    query: ReportQueryDep,
) -> Any:
    """Retrieve filtered and paginated employee master list."""
    res = await service.get_employee_master_report(org_id=org_id, user=current_user, query=query)
    return await _map_report_result(res, response)


@router.get(
    "/employees/joining",
    response_model=None,
    responses={
        202: {
            "model": SuccessResponse[ExportJobStatusResponse],
            "description": "Large export job accepted.",
        },
        200: {"description": "JSON report data or synchronous file download (CSV/Excel/PDF)."},
    },
    summary="Employee Joining Report",
    description="Fetch roster of employees who joined within the period.",
    dependencies=[Depends(require_permission(_FEATURE_KEY, A.READ))],
)
async def get_employee_joining_report(
    service: ReportsServiceDep,
    org_id: OrgIdDep,
    current_user: CurrentUserDep,
    response: Response,
    query: ReportQueryDep,
) -> Any:
    """Retrieve filtered and paginated employee joining roster."""
    res = await service.get_employee_joining_report(org_id=org_id, user=current_user, query=query)
    return await _map_report_result(res, response)


@router.get(
    "/employees/status",
    response_model=None,
    responses={
        202: {
            "model": SuccessResponse[ExportJobStatusResponse],
            "description": "Large export job accepted.",
        },
        200: {"description": "JSON report data or synchronous file download (CSV/Excel/PDF)."},
    },
    summary="Employee Status Report",
    description="Fetch employee status transition logs.",
    dependencies=[Depends(require_permission(_FEATURE_KEY, A.READ))],
)
async def get_employee_status_report(
    service: ReportsServiceDep,
    org_id: OrgIdDep,
    current_user: CurrentUserDep,
    response: Response,
    query: ReportQueryDep,
) -> Any:
    """Retrieve filtered and paginated employee status history roster."""
    res = await service.get_employee_status_report(org_id=org_id, user=current_user, query=query)
    return await _map_report_result(res, response)


@router.get(
    "/employees/by-department",
    response_model=None,
    responses={
        202: {
            "model": SuccessResponse[ExportJobStatusResponse],
            "description": "Large export job accepted.",
        },
        200: {"description": "JSON report data or synchronous file download (CSV/Excel/PDF)."},
    },
    summary="Department Headcount Report",
    description="Fetch employee headcount grouped by department.",
    dependencies=[Depends(require_permission(_FEATURE_KEY, A.READ))],
)
async def get_department_headcount_report(
    service: ReportsServiceDep,
    org_id: OrgIdDep,
    current_user: CurrentUserDep,
    response: Response,
    query: ReportQueryDep,
) -> Any:
    """Retrieve paginated department headcount report."""
    res = await service.get_department_headcount_report(
        org_id=org_id, user=current_user, query=query
    )
    return await _map_report_result(res, response)


@router.get(
    "/employees/by-designation",
    response_model=None,
    responses={
        202: {
            "model": SuccessResponse[ExportJobStatusResponse],
            "description": "Large export job accepted.",
        },
        200: {"description": "JSON report data or synchronous file download (CSV/Excel/PDF)."},
    },
    summary="Designation Headcount Report",
    description="Fetch employee headcount grouped by designation.",
    dependencies=[Depends(require_permission(_FEATURE_KEY, A.READ))],
)
async def get_designation_headcount_report(
    service: ReportsServiceDep,
    org_id: OrgIdDep,
    current_user: CurrentUserDep,
    response: Response,
    query: ReportQueryDep,
) -> Any:
    """Retrieve paginated designation headcount report."""
    res = await service.get_designation_headcount_report(
        org_id=org_id, user=current_user, query=query
    )
    return await _map_report_result(res, response)


@router.get(
    "/employees/by-branch",
    response_model=None,
    responses={
        202: {
            "model": SuccessResponse[ExportJobStatusResponse],
            "description": "Large export job accepted.",
        },
        200: {"description": "JSON report data or synchronous file download (CSV/Excel/PDF)."},
    },
    summary="Branch Headcount Report",
    description="Fetch employee headcount grouped by branch.",
    dependencies=[Depends(require_permission(_FEATURE_KEY, A.READ))],
)
async def get_branch_headcount_report(
    service: ReportsServiceDep,
    org_id: OrgIdDep,
    current_user: CurrentUserDep,
    response: Response,
    query: ReportQueryDep,
) -> Any:
    """Retrieve paginated branch headcount report."""
    res = await service.get_branch_headcount_report(org_id=org_id, user=current_user, query=query)
    return await _map_report_result(res, response)


# =========================================================================
# 2. Attendance Reports
# =========================================================================


@router.get(
    "/attendance/daily",
    response_model=None,
    responses={
        202: {
            "model": SuccessResponse[ExportJobStatusResponse],
            "description": "Large export job accepted.",
        },
        200: {"description": "JSON report data or synchronous file download (CSV/Excel/PDF)."},
    },
    summary="Daily Attendance Report",
    description="Fetch daily attendance records roster.",
    dependencies=[Depends(require_permission(_FEATURE_KEY, A.READ))],
)
async def get_daily_attendance_report(
    service: ReportsServiceDep,
    org_id: OrgIdDep,
    current_user: CurrentUserDep,
    response: Response,
    query: ReportQueryDep,
) -> Any:
    """Retrieve filtered and paginated daily attendance roster."""
    res = await service.get_daily_attendance_report(org_id=org_id, user=current_user, query=query)
    return await _map_report_result(res, response)


@router.get(
    "/attendance/daily-punch",
    response_model=None,
    responses={
        202: {
            "model": SuccessResponse[ExportJobStatusResponse],
            "description": "Large export job accepted.",
        },
        200: {"description": "JSON report data or synchronous file download (CSV/Excel/PDF)."},
    },
    summary="Daily Punch Matrix Report",
    description="Fetch multi-day daily punch matrix report grouped by employee.",
    dependencies=[Depends(require_permission(_FEATURE_KEY, A.READ))],
)
async def get_daily_punch_matrix_report(
    service: ReportsServiceDep,
    org_id: OrgIdDep,
    current_user: CurrentUserDep,
    response: Response,
    query: ReportQueryDep,
) -> Any:
    """Retrieve filtered and paginated daily punch matrix report."""
    res = await service.get_daily_punch_matrix_report(org_id=org_id, user=current_user, query=query)
    return await _map_report_result(res, response)


@router.get(
    "/attendance/working-hours",
    response_model=None,
    responses={
        202: {
            "model": SuccessResponse[ExportJobStatusResponse],
            "description": "Large export job accepted.",
        },
        200: {"description": "JSON report data or synchronous file download (CSV/Excel/PDF)."},
    },
    summary="Working Hours Matrix Report",
    description="Fetch multi-day working hours matrix report grouped by employee.",
    dependencies=[Depends(require_permission(_FEATURE_KEY, A.READ))],
)
async def get_working_hours_matrix_report(
    service: ReportsServiceDep,
    org_id: OrgIdDep,
    current_user: CurrentUserDep,
    response: Response,
    query: ReportQueryDep,
) -> Any:
    """Retrieve filtered and paginated working hours matrix report."""
    res = await service.get_working_hours_matrix_report(org_id=org_id, user=current_user, query=query)
    return await _map_report_result(res, response)


@router.get(
    "/attendance/branch-wise-punch",
    response_model=None,
    responses={
        202: {
            "model": SuccessResponse[ExportJobStatusResponse],
            "description": "Large export job accepted.",
        },
        200: {"description": "JSON report data or synchronous file download (CSV/Excel/PDF)."},
    },
    summary="Branch Wise Punch Report",
    description="Fetch multi-day branch wise punch matrix report grouped by employee.",
    dependencies=[Depends(require_permission(_FEATURE_KEY, A.READ))],
)
async def get_branch_wise_punch_report(
    service: ReportsServiceDep,
    org_id: OrgIdDep,
    current_user: CurrentUserDep,
    response: Response,
    query: ReportQueryDep,
) -> Any:
    """Retrieve filtered and paginated branch wise punch report."""
    res = await service.get_branch_wise_punch_report(org_id=org_id, user=current_user, query=query)
    return await _map_report_result(res, response)


@router.get(
    "/attendance/muster",
    response_model=None,
    responses={
        202: {
            "model": SuccessResponse[ExportJobStatusResponse],
            "description": "Large export job accepted.",
        },
        200: {"description": "JSON report data or synchronous file download (CSV/Excel/PDF)."},
    },
    summary="Muster Roll Report",
    description="Fetch multi-day muster roll report grouped by employee.",
    dependencies=[Depends(require_permission(_FEATURE_KEY, A.READ))],
)
async def get_muster_report(
    service: ReportsServiceDep,
    org_id: OrgIdDep,
    current_user: CurrentUserDep,
    response: Response,
    query: ReportQueryDep,
) -> Any:
    """Retrieve filtered and paginated muster roll report."""
    res = await service.get_muster_report(org_id=org_id, user=current_user, query=query)
    return await _map_report_result(res, response)


@router.get(
    "/attendance/employee-day-wise-master",
    response_model=None,
    responses={
        202: {
            "model": SuccessResponse[ExportJobStatusResponse],
            "description": "Large export job accepted.",
        },
        200: {"description": "JSON report data or synchronous file download (CSV/Excel/PDF)."},
    },
    summary="Employee Day Wise Master Report",
    description="Fetch multi-day day-wise master report grouped by employee.",
    dependencies=[Depends(require_permission(_FEATURE_KEY, A.READ))],
)
async def get_employee_day_wise_master_report(
    service: ReportsServiceDep,
    org_id: OrgIdDep,
    current_user: CurrentUserDep,
    response: Response,
    query: ReportQueryDep,
    department_id: int | None = Query(None, description="Filter by department id."),
    designation_id: int | None = Query(None, description="Filter by designation id."),
) -> Any:
    """Retrieve filtered and paginated employee day-wise master report."""
    if department_id is not None:
        query.dept_id = department_id
    if designation_id is not None:
        query.designation_id = designation_id
    res = await service.get_employee_day_wise_master_report(org_id=org_id, user=current_user, query=query)
    return await _map_report_result(res, response)


@router.get(
    "/attendance/monthly",
    response_model=None,
    responses={
        202: {
            "model": SuccessResponse[ExportJobStatusResponse],
            "description": "Large export job accepted.",
        },
        200: {"description": "JSON report data or synchronous file download (CSV/Excel/PDF)."},
    },
    summary="Monthly Attendance Report",
    description="Fetch monthly calendar grid attendance summary.",
    dependencies=[Depends(require_permission(_FEATURE_KEY, A.READ))],
)
async def get_monthly_attendance_report(
    service: ReportsServiceDep,
    org_id: OrgIdDep,
    current_user: CurrentUserDep,
    response: Response,
    query: ReportQueryDep,
) -> Any:
    """Retrieve filtered and paginated monthly attendance grid."""
    res = await service.get_monthly_attendance_report(org_id=org_id, user=current_user, query=query)
    return await _map_report_result(res, response)


@router.get(
    "/attendance/shift-wise",
    response_model=None,
    responses={
        202: {
            "model": SuccessResponse[ExportJobStatusResponse],
            "description": "Large export job accepted.",
        },
        200: {"description": "JSON report data or synchronous file download (CSV/Excel/PDF)."},
    },
    summary="Shift Wise Attendance Report",
    description="Fetch attendance logs grouped by employee assigned shifts.",
    dependencies=[Depends(require_permission(_FEATURE_KEY, A.READ))],
)
async def get_shift_wise_report(
    service: ReportsServiceDep,
    org_id: OrgIdDep,
    current_user: CurrentUserDep,
    response: Response,
    query: ReportQueryDep,
) -> Any:
    """Retrieve filtered and paginated shift-wise attendance report."""
    res = await service.get_daily_attendance_report(org_id=org_id, user=current_user, query=query)
    return await _map_report_result(res, response)


@router.get(
    "/attendance/employee",
    response_model=None,
    responses={
        202: {
            "model": SuccessResponse[ExportJobStatusResponse],
            "description": "Large export job accepted.",
        },
        200: {"description": "JSON report data or synchronous file download (CSV/Excel/PDF)."},
    },
    summary="Employee Attendance Report",
    description="Fetch attendance logs for a specific employee.",
    dependencies=[Depends(require_permission(_FEATURE_KEY, A.READ))],
)
async def get_employee_attendance_report(
    service: ReportsServiceDep,
    org_id: OrgIdDep,
    current_user: CurrentUserDep,
    response: Response,
    query: ReportQueryDep,
) -> Any:
    """Retrieve filtered and paginated attendance records for a specific employee."""
    res = await service.get_employee_attendance_report(
        org_id=org_id, user=current_user, query=query
    )
    return await _map_report_result(res, response)


@router.get(
    "/attendance/late-coming",
    response_model=None,
    responses={
        202: {
            "model": SuccessResponse[ExportJobStatusResponse],
            "description": "Large export job accepted.",
        },
        200: {"description": "JSON report data or synchronous file download (CSV/Excel/PDF)."},
    },
    summary="Late Coming Report",
    description="Fetch late arrival logs.",
    dependencies=[Depends(require_permission(_FEATURE_KEY, A.READ))],
)
async def get_late_coming_report(
    service: ReportsServiceDep,
    org_id: OrgIdDep,
    current_user: CurrentUserDep,
    response: Response,
    query: ReportQueryDep,
) -> Any:
    """Retrieve filtered and paginated late coming roster."""
    res = await service.get_late_coming_report(org_id=org_id, user=current_user, query=query)
    return await _map_report_result(res, response)


@router.get(
    "/attendance/early-going",
    response_model=None,
    responses={
        202: {
            "model": SuccessResponse[ExportJobStatusResponse],
            "description": "Large export job accepted.",
        },
        200: {"description": "JSON report data or synchronous file download (CSV/Excel/PDF)."},
    },
    summary="Early Going Report",
    description="Fetch early departure logs.",
    dependencies=[Depends(require_permission(_FEATURE_KEY, A.READ))],
)
async def get_early_going_report(
    service: ReportsServiceDep,
    org_id: OrgIdDep,
    current_user: CurrentUserDep,
    response: Response,
    query: ReportQueryDep,
) -> Any:
    """Retrieve filtered and paginated early going roster."""
    res = await service.get_early_going_report(org_id=org_id, user=current_user, query=query)
    return await _map_report_result(res, response)


@router.get(
    "/attendance/missing-punch",
    response_model=None,
    responses={
        202: {
            "model": SuccessResponse[ExportJobStatusResponse],
            "description": "Large export job accepted.",
        },
        200: {"description": "JSON report data or synchronous file download (CSV/Excel/PDF)."},
    },
    summary="Missing Punch Report",
    description="Fetch missing check-in/out anomaly logs.",
    dependencies=[Depends(require_permission(_FEATURE_KEY, A.READ))],
)
async def get_missing_punch_report(
    service: ReportsServiceDep,
    org_id: OrgIdDep,
    current_user: CurrentUserDep,
    response: Response,
    query: ReportQueryDep,
) -> Any:
    """Retrieve filtered and paginated missing punch roster."""
    res = await service.get_missing_punch_report(org_id=org_id, user=current_user, query=query)
    return await _map_report_result(res, response)


@router.get(
    "/attendance/overtime",
    response_model=None,
    responses={
        202: {
            "model": SuccessResponse[ExportJobStatusResponse],
            "description": "Large export job accepted.",
        },
        200: {"description": "JSON report data or synchronous file download (CSV/Excel/PDF)."},
    },
    summary="Overtime Report",
    description="Fetch overtime hours logs.",
    dependencies=[Depends(require_permission(_FEATURE_KEY, A.READ))],
)
async def get_overtime_report(
    service: ReportsServiceDep,
    org_id: OrgIdDep,
    current_user: CurrentUserDep,
    response: Response,
    query: ReportQueryDep,
) -> Any:
    """Retrieve filtered and paginated overtime roster."""
    res = await service.get_overtime_report(org_id=org_id, user=current_user, query=query)
    return await _map_report_result(res, response)


@router.get(
    "/attendance/summary",
    response_model=None,
    responses={
        202: {
            "model": SuccessResponse[ExportJobStatusResponse],
            "description": "Large export job accepted.",
        },
        200: {"description": "JSON summary data or synchronous file download (CSV/Excel/PDF)."},
    },
    summary="Attendance Summary Report",
    description="Fetch summarized aggregates for attendance.",
    dependencies=[Depends(require_permission(_FEATURE_KEY, A.READ))],
)
async def get_attendance_summary_report(
    service: ReportsServiceDep,
    org_id: OrgIdDep,
    current_user: CurrentUserDep,
    response: Response,
    query: ReportQueryDep,
) -> Any:
    """Retrieve summarized attendance report."""
    res = await service.get_attendance_summary_report(org_id=org_id, user=current_user, query=query)
    return await _map_report_result(res, response)


# =========================================================================
# 3. Leave Reports
# =========================================================================


@router.get(
    "/leave/balance",
    response_model=None,
    responses={
        202: {
            "model": SuccessResponse[ExportJobStatusResponse],
            "description": "Large export job accepted.",
        },
        200: {"description": "JSON report data or synchronous file download (CSV/Excel/PDF)."},
    },
    summary="Leave Balance Report",
    description="Fetch leave allocations and balance rosters.",
    dependencies=[Depends(require_permission(_FEATURE_KEY, A.READ))],
)
async def get_leave_balance_report(
    service: ReportsServiceDep,
    org_id: OrgIdDep,
    current_user: CurrentUserDep,
    response: Response,
    query: ReportQueryDep,
) -> Any:
    """Retrieve filtered and paginated leave balance roster."""
    res = await service.get_leave_balance_report(org_id=org_id, user=current_user, query=query)
    return await _map_report_result(res, response)


@router.get(
    "/leave/requests",
    response_model=None,
    responses={
        202: {
            "model": SuccessResponse[ExportJobStatusResponse],
            "description": "Large export job accepted.",
        },
        200: {"description": "JSON report data or synchronous file download (CSV/Excel/PDF)."},
    },
    summary="Leave Request Report",
    description="Fetch rosters of leave requests.",
    dependencies=[Depends(require_permission(_FEATURE_KEY, A.READ))],
)
async def get_leave_requests_report(
    service: ReportsServiceDep,
    org_id: OrgIdDep,
    current_user: CurrentUserDep,
    response: Response,
    query: ReportQueryDep,
) -> Any:
    """Retrieve filtered and paginated leave requests roster."""
    res = await service.get_leave_requests_report(org_id=org_id, user=current_user, query=query)
    return await _map_report_result(res, response)


@router.get(
    "/leave/approvals",
    response_model=None,
    responses={
        202: {
            "model": SuccessResponse[ExportJobStatusResponse],
            "description": "Large export job accepted.",
        },
        200: {"description": "JSON report data or synchronous file download (CSV/Excel/PDF)."},
    },
    summary="Leave Approval Report",
    description="Fetch roster of decisions on leave requests.",
    dependencies=[Depends(require_permission(_FEATURE_KEY, A.READ))],
)
async def get_leave_approvals_report(
    service: ReportsServiceDep,
    org_id: OrgIdDep,
    current_user: CurrentUserDep,
    response: Response,
    query: ReportQueryDep,
) -> Any:
    """Retrieve filtered and paginated leave approvals roster."""
    res = await service.get_leave_approvals_report(org_id=org_id, user=current_user, query=query)
    return await _map_report_result(res, response)


@router.get(
    "/leave/summary",
    response_model=None,
    responses={
        202: {
            "model": SuccessResponse[ExportJobStatusResponse],
            "description": "Large export job accepted.",
        },
        200: {"description": "JSON summary data or synchronous file download (CSV/Excel/PDF)."},
    },
    summary="Leave Summary Report",
    description="Fetch leave type breakdowns and decision aggregates.",
    dependencies=[Depends(require_permission(_FEATURE_KEY, A.READ))],
)
async def get_leave_summary_report(
    service: ReportsServiceDep,
    org_id: OrgIdDep,
    current_user: CurrentUserDep,
    response: Response,
    query: ReportQueryDep,
) -> Any:
    """Retrieve leave summary report."""
    res = await service.get_leave_summary_report(org_id=org_id, user=current_user, query=query)
    return await _map_report_result(res, response)


@router.get(
    "/leave/taken",
    response_model=None,
    responses={
        202: {
            "model": SuccessResponse[ExportJobStatusResponse],
            "description": "Large export job accepted.",
        },
        200: {"description": "JSON matrix data or synchronous file download (CSV/Excel/PDF)."},
    },
    summary="Leave Taken Report",
    description="Fetch leave taken matrix grouped by employee.",
    dependencies=[Depends(require_permission(_FEATURE_KEY, A.READ))],
)
async def get_leave_taken_report(
    service: ReportsServiceDep,
    org_id: OrgIdDep,
    current_user: CurrentUserDep,
    response: Response,
    query: ReportQueryDep,
    department_id: int | None = Query(None, description="Filter by department id."),
) -> Any:
    """Retrieve filtered and paginated leave taken report."""
    if department_id is not None:
        query.dept_id = department_id
    res = await service.get_leave_taken_report(org_id=org_id, user=current_user, query=query)
    return await _map_report_result(res, response)


# =========================================================================
# 4. Approval Reports
# =========================================================================


@router.get(
    "/approvals/pending",
    response_model=None,
    responses={
        202: {
            "model": SuccessResponse[ExportJobStatusResponse],
            "description": "Large export job accepted.",
        },
        200: {"description": "JSON report data or synchronous file download (CSV/Excel/PDF)."},
    },
    summary="Pending Approval Report",
    description="Fetch roster of items awaiting resolution.",
    dependencies=[Depends(require_permission(_FEATURE_KEY, A.READ))],
)
async def get_pending_approvals_report(
    service: ReportsServiceDep,
    org_id: OrgIdDep,
    current_user: CurrentUserDep,
    response: Response,
    query: ReportQueryDep,
) -> Any:
    """Retrieve paginated pending approvals roster."""
    res = await service.get_pending_approvals_report(org_id=org_id, user=current_user, query=query)
    return await _map_report_result(res, response)


@router.get(
    "/approvals/history",
    response_model=None,
    responses={
        202: {
            "model": SuccessResponse[ExportJobStatusResponse],
            "description": "Large export job accepted.",
        },
        200: {"description": "JSON report data or synchronous file download (CSV/Excel/PDF)."},
    },
    summary="Approval History Report",
    description="Fetch roster of decided approval requests.",
    dependencies=[Depends(require_permission(_FEATURE_KEY, A.READ))],
)
async def get_approval_history_report(
    service: ReportsServiceDep,
    org_id: OrgIdDep,
    current_user: CurrentUserDep,
    response: Response,
    query: ReportQueryDep,
) -> Any:
    """Retrieve paginated resolved approvals history."""
    res = await service.get_approval_history_report(org_id=org_id, user=current_user, query=query)
    return await _map_report_result(res, response)


@router.get(
    "/approvals/performance",
    response_model=None,
    responses={
        202: {
            "model": SuccessResponse[ExportJobStatusResponse],
            "description": "Large export job accepted.",
        },
        200: {"description": "JSON report data or synchronous file download (CSV/Excel/PDF)."},
    },
    summary="Approval Performance Report",
    description="Fetch decision throughput and performance metrics per approver.",
    dependencies=[Depends(require_permission(_FEATURE_KEY, A.READ))],
)
async def get_approval_performance_report(
    service: ReportsServiceDep,
    org_id: OrgIdDep,
    current_user: CurrentUserDep,
    response: Response,
    query: ReportQueryDep,
) -> Any:
    """Retrieve paginated approval performance report."""
    res = await service.get_approval_performance_report(
        org_id=org_id, user=current_user, query=query
    )
    return await _map_report_result(res, response)


# =========================================================================
# 5. Payroll Reports
# =========================================================================


@router.get(
    "/payroll/register",
    response_model=None,
    responses={
        202: {
            "model": SuccessResponse[ExportJobStatusResponse],
            "description": "Large export job accepted.",
        },
        200: {"description": "JSON report data or synchronous file download (CSV/Excel/PDF)."},
    },
    summary="Payroll Register Report",
    description="Fetch computed payroll components register.",
    dependencies=[Depends(require_permission(_FEATURE_KEY, A.READ))],
)
async def get_payroll_register_report(
    service: ReportsServiceDep,
    org_id: OrgIdDep,
    current_user: CurrentUserDep,
    response: Response,
    payroll_group_id: int | None = Query(None, description="Filter by payroll group ID."),
    salary_cycle_id: int | None = Query(None, description="Filter by salary cycle ID."),
    query: ReportQueryDep = None,
) -> Any:
    """Retrieve computed payroll register report."""
    res = await service.get_payroll_register_report(
        org_id=org_id,
        user=current_user,
        query=query,
        payroll_group_id=payroll_group_id,
        salary_cycle_id=salary_cycle_id,
    )
    return await _map_report_result(res, response)


@router.get(
    "/payroll/salary-register",
    response_model=None,
    responses={
        202: {
            "model": SuccessResponse[ExportJobStatusResponse],
            "description": "Large export job accepted.",
        },
        200: {"description": "JSON report data or synchronous file download (CSV/Excel/PDF)."},
    },
    summary="Salary Register Report",
    description="Fetch salary-focused register roster.",
    dependencies=[Depends(require_permission(_FEATURE_KEY, A.READ))],
)
async def get_salary_register_report(
    service: ReportsServiceDep,
    org_id: OrgIdDep,
    current_user: CurrentUserDep,
    response: Response,
    payroll_group_id: int | None = Query(None, description="Filter by payroll group ID."),
    salary_cycle_id: int | None = Query(None, description="Filter by salary cycle ID."),
    query: ReportQueryDep = None,
) -> Any:
    """Retrieve computed salary register report."""
    res = await service.get_salary_register_report(
        org_id=org_id,
        user=current_user,
        query=query,
        payroll_group_id=payroll_group_id,
        salary_cycle_id=salary_cycle_id,
    )
    return await _map_report_result(res, response)


@router.get(
    "/payroll/summary",
    response_model=None,
    responses={
        202: {
            "model": SuccessResponse[ExportJobStatusResponse],
            "description": "Large export job accepted.",
        },
        200: {"description": "JSON summary data or synchronous file download (CSV/Excel/PDF)."},
    },
    summary="Payroll Summary Report",
    description="Fetch total aggregates across a payroll cycle.",
    dependencies=[Depends(require_permission(_FEATURE_KEY, A.READ))],
)
async def get_payroll_summary_report(
    service: ReportsServiceDep,
    org_id: OrgIdDep,
    current_user: CurrentUserDep,
    response: Response,
    payroll_group_id: int | None = Query(None, description="Filter by payroll group ID."),
    salary_cycle_id: int | None = Query(None, description="Filter by salary cycle ID."),
    query: ReportQueryDep = None,
) -> Any:
    """Retrieve payroll summary report."""
    res = await service.get_payroll_summary_report(
        org_id=org_id,
        user=current_user,
        query=query,
        payroll_group_id=payroll_group_id,
        salary_cycle_id=salary_cycle_id,
    )
    return await _map_report_result(res, response)


@router.get(
    "/payroll/payslips",
    response_model=None,
    responses={
        202: {
            "model": SuccessResponse[ExportJobStatusResponse],
            "description": "Large export job accepted.",
        },
        200: {"description": "JSON report data or synchronous file download (CSV/Excel/PDF)."},
    },
    summary="Payslip Report",
    description="Fetch generated payslips metadata roster.",
    dependencies=[Depends(require_permission(_FEATURE_KEY, A.READ))],
)
async def get_payslips_report(
    service: ReportsServiceDep,
    org_id: OrgIdDep,
    current_user: CurrentUserDep,
    response: Response,
    payroll_group_id: int | None = Query(None, description="Filter by payroll group ID."),
    salary_cycle_id: int | None = Query(None, description="Filter by salary cycle ID."),
    query: ReportQueryDep = None,
) -> Any:
    """Retrieve generated payslips metadata roster."""
    res = await service.get_payslips_report(
        org_id=org_id,
        user=current_user,
        query=query,
        payroll_group_id=payroll_group_id,
        salary_cycle_id=salary_cycle_id,
    )
    return await _map_report_result(res, response)


# =========================================================================
# 6. Settlement Reports
# =========================================================================


@router.get(
    "/settlements/ledger",
    response_model=None,
    responses={
        202: {
            "model": SuccessResponse[ExportJobStatusResponse],
            "description": "Large export job accepted.",
        },
        200: {"description": "JSON report data or synchronous file download (CSV/Excel/PDF)."},
    },
    summary="Settlement Ledger Report",
    description="Fetch settlement transactions combining loans, advances, and arrears.",
    dependencies=[Depends(require_permission(_FEATURE_KEY, A.READ))],
)
async def get_settlement_ledger_report(
    service: ReportsServiceDep,
    org_id: OrgIdDep,
    current_user: CurrentUserDep,
    response: Response,
    query: ReportQueryDep,
) -> Any:
    """Retrieve filtered and paginated settlement ledger transactions."""
    res = await service.get_settlement_ledger_report(org_id=org_id, user=current_user, query=query)
    return await _map_report_result(res, response)


@router.get(
    "/settlements/summary",
    response_model=None,
    responses={
        202: {
            "model": SuccessResponse[ExportJobStatusResponse],
            "description": "Large export job accepted.",
        },
        200: {"description": "JSON summary data or synchronous file download (CSV/Excel/PDF)."},
    },
    summary="Settlement Summary Report",
    description="Fetch active/closed loan-advance metrics and arrears totals.",
    dependencies=[Depends(require_permission(_FEATURE_KEY, A.READ))],
)
async def get_settlement_summary_report(
    service: ReportsServiceDep,
    org_id: OrgIdDep,
    current_user: CurrentUserDep,
    response: Response,
    query: ReportQueryDep,
) -> Any:
    """Retrieve settlement summary report."""
    res = await service.get_settlement_summary_report(org_id=org_id, user=current_user, query=query)
    return await _map_report_result(res, response)


# =========================================================================
# 7. Hardware Reports
# =========================================================================


@router.get(
    "/devices/status",
    response_model=None,
    responses={
        202: {
            "model": SuccessResponse[ExportJobStatusResponse],
            "description": "Large export job accepted.",
        },
        200: {"description": "JSON report data or synchronous file download (CSV/Excel/PDF)."},
    },
    summary="Device Status Report",
    description="Fetch biometric device status summary roster.",
    dependencies=[Depends(require_permission(_FEATURE_KEY, A.READ))],
)
async def get_device_status_report(
    service: ReportsServiceDep,
    org_id: OrgIdDep,
    current_user: CurrentUserDep,
    response: Response,
    query: ReportQueryDep,
) -> Any:
    """Retrieve paginated biometric devices status roster."""
    res = await service.get_device_status_report(org_id=org_id, user=current_user, query=query)
    return await _map_report_result(res, response)


@router.get(
    "/devices/health",
    response_model=None,
    responses={
        202: {
            "model": SuccessResponse[ExportJobStatusResponse],
            "description": "Large export job accepted.",
        },
        200: {"description": "JSON report data or synchronous file download (CSV/Excel/PDF)."},
    },
    summary="Device Health Report",
    description="Fetch device health and connectivity metrics.",
    dependencies=[Depends(require_permission(_FEATURE_KEY, A.READ))],
)
async def get_device_health_report(
    service: ReportsServiceDep,
    org_id: OrgIdDep,
    current_user: CurrentUserDep,
    response: Response,
    query: ReportQueryDep,
) -> Any:
    """Retrieve paginated biometric devices health status."""
    res = await service.get_device_health_report(org_id=org_id, user=current_user, query=query)
    return await _map_report_result(res, response)


@router.get(
    "/devices/sync",
    response_model=None,
    responses={
        202: {
            "model": SuccessResponse[ExportJobStatusResponse],
            "description": "Large export job accepted.",
        },
        200: {"description": "JSON report data or synchronous file download (CSV/Excel/PDF)."},
    },
    summary="Device Sync Report",
    description="Fetch synchronization freshness audit snapshot.",
    dependencies=[Depends(require_permission(_FEATURE_KEY, A.READ))],
)
async def get_device_sync_report(
    service: ReportsServiceDep,
    org_id: OrgIdDep,
    current_user: CurrentUserDep,
    response: Response,
    query: ReportQueryDep,
) -> Any:
    """Retrieve biometric device synchronization status."""
    res = await service.get_device_sync_report(org_id=org_id, user=current_user, query=query)
    return await _map_report_result(res, response)


# =========================================================================
# 8. Notification Reports
# =========================================================================


@router.get(
    "/notifications/delivery",
    response_model=None,
    responses={
        202: {
            "model": SuccessResponse[ExportJobStatusResponse],
            "description": "Large export job accepted.",
        },
        200: {"description": "JSON report data or synchronous file download (CSV/Excel/PDF)."},
    },
    summary="Notification Delivery Report",
    description="Fetch notification dispatch and delivery logs.",
    dependencies=[Depends(require_permission(_FEATURE_KEY, A.READ))],
)
async def get_notification_delivery_report(
    service: ReportsServiceDep,
    org_id: OrgIdDep,
    current_user: CurrentUserDep,
    response: Response,
    query: ReportQueryDep,
) -> Any:
    """Retrieve paginated notification delivery dispatch logs."""
    res = await service.get_notification_delivery_report(
        org_id=org_id, user=current_user, query=query
    )
    return await _map_report_result(res, response)


@router.get(
    "/notifications/read",
    response_model=None,
    responses={
        202: {
            "model": SuccessResponse[ExportJobStatusResponse],
            "description": "Large export job accepted.",
        },
        200: {"description": "JSON report data or synchronous file download (CSV/Excel/PDF)."},
    },
    summary="Notification Read Report",
    description="Fetch notification read-status tracking logs.",
    dependencies=[Depends(require_permission(_FEATURE_KEY, A.READ))],
)
async def get_notification_read_report(
    service: ReportsServiceDep,
    org_id: OrgIdDep,
    current_user: CurrentUserDep,
    response: Response,
    query: ReportQueryDep,
) -> Any:
    """Retrieve paginated notification read-status logs."""
    res = await service.get_notification_read_report(org_id=org_id, user=current_user, query=query)
    return await _map_report_result(res, response)


@router.get(
    "/notifications/summary",
    response_model=None,
    responses={
        202: {
            "model": SuccessResponse[ExportJobStatusResponse],
            "description": "Large export job accepted.",
        },
        200: {"description": "JSON summary data or synchronous file download (CSV/Excel/PDF)."},
    },
    summary="Notification Summary Report",
    description="Fetch notification aggregates and read-rate efficiency metrics.",
    dependencies=[Depends(require_permission(_FEATURE_KEY, A.READ))],
)
async def get_notification_summary_report(
    service: ReportsServiceDep,
    org_id: OrgIdDep,
    current_user: CurrentUserDep,
    response: Response,
    query: ReportQueryDep,
) -> Any:
    """Retrieve notification summary aggregates."""
    res = await service.get_notification_summary_report(
        org_id=org_id, user=current_user, query=query
    )
    return await _map_report_result(res, response)


# =========================================================================
# 9. Audit Reports
# =========================================================================


@router.get(
    "/audit/user-activity",
    response_model=None,
    responses={
        202: {
            "model": SuccessResponse[ExportJobStatusResponse],
            "description": "Large export job accepted.",
        },
        200: {"description": "JSON report data or synchronous file download (CSV/Excel/PDF)."},
    },
    summary="User Activity Report",
    description="Fetch mutation logs filtered by user.",
    dependencies=[Depends(require_permission(_FEATURE_KEY, A.READ))],
)
async def get_user_activity_report(
    service: ReportsServiceDep,
    org_id: OrgIdDep,
    current_user: CurrentUserDep,
    response: Response,
    query: ReportQueryDep,
) -> Any:
    """Retrieve paginated user mutation activity roster."""
    res = await service.get_user_activity_report(org_id=org_id, user=current_user, query=query)
    return await _map_report_result(res, response)


@router.get(
    "/audit/trail",
    response_model=None,
    responses={
        202: {
            "model": SuccessResponse[ExportJobStatusResponse],
            "description": "Large export job accepted.",
        },
        200: {"description": "JSON report data or synchronous file download (CSV/Excel/PDF)."},
    },
    summary="Audit Trail Report",
    description="Fetch generic system-mutation audit logs.",
    dependencies=[Depends(require_permission(_FEATURE_KEY, A.READ))],
)
async def get_audit_trail_report(
    service: ReportsServiceDep,
    org_id: OrgIdDep,
    current_user: CurrentUserDep,
    response: Response,
    query: ReportQueryDep,
) -> Any:
    """Retrieve paginated system audit trail roster."""
    res = await service.get_audit_trail_report(org_id=org_id, user=current_user, query=query)
    return await _map_report_result(res, response)


@router.get(
    "/audit/security-events",
    response_model=None,
    responses={
        202: {
            "model": SuccessResponse[ExportJobStatusResponse],
            "description": "Large export job accepted.",
        },
        200: {"description": "JSON report data or synchronous file download (CSV/Excel/PDF)."},
    },
    summary="Security Event Report",
    description="Fetch approximate security-events logs.",
    dependencies=[Depends(require_permission(_FEATURE_KEY, A.READ))],
)
async def get_security_events_report(
    service: ReportsServiceDep,
    org_id: OrgIdDep,
    current_user: CurrentUserDep,
    response: Response,
    query: ReportQueryDep,
) -> Any:
    """Retrieve paginated security events logs."""
    res = await service.get_security_events_report(org_id=org_id, user=current_user, query=query)
    return await _map_report_result(res, response)


# =========================================================================
# 10. Organization Reports
# =========================================================================


@router.get(
    "/organization/branch-summary",
    response_model=None,
    responses={
        202: {
            "model": SuccessResponse[ExportJobStatusResponse],
            "description": "Large export job accepted.",
        },
        200: {"description": "JSON report data or synchronous file download (CSV/Excel/PDF)."},
    },
    summary="Branch Summary Report",
    description="Fetch summary count roster of employees per branch.",
    dependencies=[Depends(require_permission(_FEATURE_KEY, A.READ))],
)
async def get_branch_summary_report(
    service: ReportsServiceDep,
    org_id: OrgIdDep,
    current_user: CurrentUserDep,
    response: Response,
    query: ReportQueryDep,
) -> Any:
    """Retrieve paginated branch employee distribution summary."""
    res = await service.get_branch_summary_report(org_id=org_id, user=current_user, query=query)
    return await _map_report_result(res, response)


@router.get(
    "/organization/department-summary",
    response_model=None,
    responses={
        202: {
            "model": SuccessResponse[ExportJobStatusResponse],
            "description": "Large export job accepted.",
        },
        200: {"description": "JSON report data or synchronous file download (CSV/Excel/PDF)."},
    },
    summary="Department Summary Report",
    description="Fetch summary count roster of employees per department.",
    dependencies=[Depends(require_permission(_FEATURE_KEY, A.READ))],
)
async def get_department_summary_report(
    service: ReportsServiceDep,
    org_id: OrgIdDep,
    current_user: CurrentUserDep,
    response: Response,
    query: ReportQueryDep,
) -> Any:
    """Retrieve paginated department employee distribution summary."""
    res = await service.get_department_summary_report(org_id=org_id, user=current_user, query=query)
    return await _map_report_result(res, response)


@router.get(
    "/organization/workforce-summary",
    response_model=None,
    responses={
        202: {
            "model": SuccessResponse[ExportJobStatusResponse],
            "description": "Large export job accepted.",
        },
        200: {"description": "JSON summary data or synchronous file download (CSV/Excel/PDF)."},
    },
    summary="Workforce Summary Report",
    description="Fetch overall global headcount breakdowns.",
    dependencies=[Depends(require_permission(_FEATURE_KEY, A.READ))],
)
async def get_workforce_summary_report(
    service: ReportsServiceDep,
    org_id: OrgIdDep,
    current_user: CurrentUserDep,
    response: Response,
    query: ReportQueryDep,
) -> Any:
    """Retrieve workforce headcount summary breakdown."""
    res = await service.get_workforce_summary_report(org_id=org_id, user=current_user, query=query)
    return await _map_report_result(res, response)


# =========================================================================
# 11. Shift Assignment Reports (Additional)
# =========================================================================


@router.get(
    "/employees/shift-assignments",
    response_model=None,
    responses={
        202: {
            "model": SuccessResponse[ExportJobStatusResponse],
            "description": "Large export job accepted.",
        },
        200: {"description": "JSON report data or synchronous file download (CSV/Excel/PDF)."},
    },
    summary="Shift Assignments Report",
    description="Fetch employee shift assignments history list.",
    dependencies=[Depends(require_permission(_FEATURE_KEY, A.READ))],
)
async def get_shift_assignments_report(
    service: ReportsServiceDep,
    org_id: OrgIdDep,
    current_user: CurrentUserDep,
    response: Response,
    query: ReportQueryDep,
) -> Any:
    """Retrieve paginated employee shift assignments history."""
    res = await service.get_shift_assignments_report(org_id=org_id, user=current_user, query=query)
    return await _map_report_result(res, response)


# =========================================================================
# 12. Export Jobs & Downloads
# =========================================================================


@router.get(
    "/exports/{export_job_id}",
    response_model=None,
    summary="Get Export Job Status",
    description="Poll status of an active asynchronous export job.",
    dependencies=[Depends(require_permission(_FEATURE_KEY, A.READ))],
)
async def get_export_job_status(
    export_job_id: str,
    service: ReportsServiceDep,
    org_id: OrgIdDep,
    current_user: CurrentUserDep,
) -> Any:
    """Retrieve the current processing status of the asynchronous export job."""
    res = await service.get_export_job_status(org_id=org_id, job_id=export_job_id)
    return success_response(
        data=res,
        message="Export job status retrieved.",
        request_id=get_request_id(),
    )


@router.get(
    "/exports/{export_job_id}/download",
    summary="Download Compiled Export File",
    description="Download the compiled CSV, Excel or PDF binary content for a completed job.",
    dependencies=[Depends(require_permission(_FEATURE_KEY, A.READ))],
)
async def download_export_file(
    export_job_id: str,
    service: ReportsServiceDep,
    org_id: OrgIdDep,
    current_user: CurrentUserDep,
) -> Any:
    """Download the final generated binary file representing the report."""
    res = await service.get_export_file(org_id=org_id, job_id=export_job_id)
    return Response(
        content=res["file_bytes"],
        media_type=res["media_type"],
        headers={"Content-Disposition": f'attachment; filename="{res["filename"]}"'},
    )
