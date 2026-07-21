"""Attendance Management — HTTP routes (thin controllers).

Maps the Attendance Management API Contract (Section 11) onto FastAPI endpoints.
Controllers resolve dependencies, build query/request DTOs, call AttendanceService,
and wrap results in the standard success envelope.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, status

from app.core.constants.enums import PermissionAction as A
from app.core.dependencies.auth import (
    CurrentUser,
    get_current_active_user,
    require_permission,
)
from app.core.dependencies.db import get_db
from app.core.dependencies.pagination import PaginationParams, pagination_params
from app.core.exceptions.base import AppException
from app.core.middleware.request_context import get_request_id
from app.modules.attendance.constants import (
    AttendanceDayStatus,
    PenaltyStatus,
    PenaltyType,
    PenaltyUnit,
    PunchType,
)
from app.modules.attendance.schemas import (
    AttendanceCorrectionApproveRequest,
    AttendanceCorrectionCreateRequest,
    AttendanceCorrectionSchema,
    AttendanceDailyListResponse,
    AttendanceDailyQuery,
    AttendanceDayDetailSchema,
    AttendanceGenerateRequest,
    AttendanceGenerateResponse,
    AttendanceLockRequest,
    AttendanceLockSchema,
    AttendanceLogsQuery,
    AttendanceLogsResponse,
    AttendanceManualCreateRequest,
    AttendanceMissingPunchesQuery,
    AttendanceMissingPunchesResponse,
    AttendanceMonthlyDaySchema,
    AttendancePenaltySchema,
    AttendancePunchSchema,
    AttendanceRecomputeRequest,
    AttendanceUnlockRequest,
)
from app.modules.attendance.service import AttendanceGenerationService, AttendanceService
from app.shared.schemas.pagination import PaginatedResponse
from app.shared.schemas.response import SuccessResponse, success_response

router = APIRouter(tags=["Attendance Management"])

# RBAC permission feature keys
_ATTENDANCE = "attendance"
_PUNCH = "attendance_punch"
_PENALTY = "attendance_penalty"


# ---------------------------------------------------------------------------
# Dependencies
# ---------------------------------------------------------------------------


async def get_attendance_service(db: Annotated[Any, Depends(get_db)]) -> AttendanceService:
    """Provide an AttendanceService bound to the request DB session."""
    return AttendanceService(db)


def get_org_id(current_user: Annotated[CurrentUser, Depends(get_current_active_user)]) -> int:
    """Return the caller's tenant id, or 400 TENANT_UNRESOLVED if absent."""
    if current_user.org_id is None:
        exc = AppException("Organization context is required.", code="TENANT_UNRESOLVED")
        exc.status_code = status.HTTP_400_BAD_REQUEST
        raise exc
    return current_user.org_id


ServiceDep = Annotated[AttendanceService, Depends(get_attendance_service)]
CurrentUserDep = Annotated[CurrentUser, Depends(get_current_active_user)]
OrgIdDep = Annotated[int, Depends(get_org_id)]


def _ok(data: Any, message: str = "OK") -> dict[str, Any]:
    return success_response(data=data, message=message, request_id=get_request_id())


# ===========================================================================
# Daily Attendance Days
# ===========================================================================


@router.get(
    "/attendance/days",
    response_model=SuccessResponse[AttendanceDailyListResponse],
    summary="List / Search Attendance Days",
    dependencies=[Depends(require_permission(_ATTENDANCE, A.READ))],
)
async def list_attendance_days(
    service: ServiceDep,
    org_id: OrgIdDep,
    q_date: Annotated[date | None, Query(alias="date", description="Target calendar date.")] = None,
    date_from: Annotated[date | None, Query(alias="date_from", description="Start date of range.")] = None,
    date_to: Annotated[date | None, Query(alias="date_to", description="End date of range.")] = None,
    branch_id: Annotated[int | None, Query(description="Filter by branch.")] = None,
    department_id: Annotated[int | None, Query(description="Filter by department.")] = None,
    pagination: Annotated[PaginationParams, Depends(pagination_params)] = None,
) -> dict[str, Any]:
    """Return a filtered, searched, paginated list of daily attendance rows."""
    page = pagination.page if pagination else 1
    page_size = pagination.page_size if pagination else 25
    query = AttendanceDailyQuery(
        date=q_date,
        date_from=date_from,
        date_to=date_to,
        branch_id=branch_id,
        department_id=department_id,
        page=page,
        page_size=page_size,
    )
    result = await service.list_attendance_days(org_id=org_id, query=query)
    return _ok(result)


@router.post(
    "/attendance/generate",
    response_model=SuccessResponse[AttendanceGenerateResponse],
    status_code=status.HTTP_200_OK,
    summary="Trigger batch attendance generation engine",
    dependencies=[Depends(require_permission(_ATTENDANCE, A.CREATE))],
)
async def generate_attendance(
    payload: AttendanceGenerateRequest,
    service: ServiceDep,
    org_id: OrgIdDep,
    current_user: CurrentUserDep,
) -> dict[str, Any]:
    """Explicitly trigger batch generation of attendance_days records."""
    gen_service = AttendanceGenerationService(service.session)
    count = await gen_service.generate_for_range(
        org_id=org_id,
        date_from=payload.date_from,
        date_to=payload.date_to,
        branch_id=payload.branch_id,
        department_id=payload.department_id,
        employee_ids=payload.employee_ids,
        actor_id=current_user.id,
    )
    return _ok(
        AttendanceGenerateResponse(
            success=True,
            message=f"Attendance generation completed. {count} records generated.",
            records_generated=count,
        ),
        message="Attendance generation completed successfully.",
    )


@router.post(
    "/attendance/days",
    response_model=SuccessResponse[AttendanceDayDetailSchema],
    status_code=status.HTTP_201_CREATED,
    summary="Mark / Create Attendance Day (manual)",
    dependencies=[Depends(require_permission(_ATTENDANCE, A.CREATE))],
)
async def create_attendance_day(
    service: ServiceDep,
    org_id: OrgIdDep,
    current_user: CurrentUserDep,
    employee_id: Annotated[int, Query(description="Employee ID.")],
    attendance_date: Annotated[date, Query(description="Date.")],
    status_val: Annotated[AttendanceDayStatus, Query(alias="status", description="Status.")],
    shift_id: Annotated[int | None, Query(description="Shift ID.")] = None,
    leave_id: Annotated[int | None, Query(description="Leave ID.")] = None,
    remarks: Annotated[str | None, Query(description="Remarks.")] = None,
) -> dict[str, Any]:
    """Directly mark or override a daily attendance record without punches."""
    result = await service.create_attendance_day(
        org_id,
        current_user.user_id,
        employee_id=employee_id,
        attendance_date=attendance_date,
        status=status_val,
        shift_id=shift_id,
        leave_id=leave_id,
        remarks=remarks,
    )
    return _ok(result, "Manual attendance day created.")


@router.post(
    "/attendance/manual",
    response_model=SuccessResponse[AttendanceDayDetailSchema],
    status_code=status.HTTP_201_CREATED,
    summary="Create Manual Attendance check-in/out",
    dependencies=[Depends(require_permission(_ATTENDANCE, A.CREATE))],
)
async def create_manual_attendance(
    payload: AttendanceManualCreateRequest,
    service: ServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Mark manual attendance containing a punch-in and punch-out event."""
    result = await service.create_manual_attendance(
        org_id=org_id,
        actor_id=current_user.user_id,
        data=payload,
    )
    return _ok(result, "Manual check-in/out attendance created.")


@router.patch(
    "/attendance/days/{day_id}",
    response_model=SuccessResponse[AttendanceDayDetailSchema],
    summary="Override Attendance Day Parameters",
    dependencies=[Depends(require_permission(_ATTENDANCE, A.EDIT))],
)
async def override_attendance_day(
    day_id: int,
    payload: dict[str, Any],
    service: ServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Manually override an attendance day's fields (e.g. status, worked minutes)."""
    result = await service.override_attendance_day(
        org_id=org_id,
        actor_id=current_user.user_id,
        day_id=day_id,
        updates=payload,
    )
    return _ok(result, "Attendance day overrode.")


@router.get(
    "/attendance/days/{day_id}",
    response_model=SuccessResponse[AttendanceDayDetailSchema],
    summary="Get Attendance Day details",
    dependencies=[Depends(require_permission(_ATTENDANCE, A.READ))],
)
async def get_attendance_day(
    day_id: int,
    service: ServiceDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Return an eager-loaded attendance day including nested punches and penalties."""
    result = await service.get_attendance_day(org_id=org_id, day_id=day_id)
    return _ok(result)


@router.get(
    "/employees/{employee_id}/attendance/days",
    response_model=SuccessResponse[AttendanceDailyListResponse],
    summary="Get Employee Attendance History",
    dependencies=[Depends(require_permission(_ATTENDANCE, A.READ))],
)
async def get_employee_attendance_history(
    employee_id: int,
    service: ServiceDep,
    org_id: OrgIdDep,
    date_from: Annotated[date | None, Query(alias="from", description="Start date.")] = None,
    date_to: Annotated[date | None, Query(alias="to", description="End date.")] = None,
    pagination: Annotated[PaginationParams, Depends(pagination_params)] = None,
) -> dict[str, Any]:
    """Retrieve paginated historical attendance days for an employee."""
    page = pagination.page if pagination else 1
    page_size = pagination.page_size if pagination else 25
    result = await service.get_employee_attendance_history(
        org_id=org_id,
        employee_id=employee_id,
        date_from=date_from,
        date_to=date_to,
        page=page,
        page_size=page_size,
    )
    return _ok(result)


@router.get(
    "/employees/{employee_id}/attendance/calendar",
    response_model=SuccessResponse[list[AttendanceMonthlyDaySchema]],
    summary="Get Attendance Monthly Calendar view",
    dependencies=[Depends(require_permission(_ATTENDANCE, A.READ))],
)
async def get_attendance_calendar_view(
    employee_id: int,
    service: ServiceDep,
    org_id: OrgIdDep,
    month: Annotated[int, Query(ge=1, le=12, description="Target calendar month.")],
    year: Annotated[int, Query(ge=1900, le=2100, description="Target calendar year.")],
) -> dict[str, Any]:
    """Fetch calendar cells for an employee across a specific month."""
    result = await service.get_attendance_calendar_view(
        org_id=org_id,
        employee_id=employee_id,
        month=month,
        year=year,
    )
    return _ok(result)


# ===========================================================================
# Punches
# ===========================================================================


@router.post(
    "/attendance/punches",
    response_model=SuccessResponse[AttendancePunchSchema],
    status_code=status.HTTP_201_CREATED,
    summary="Add Manual Punch log",
    dependencies=[Depends(require_permission(_PUNCH, A.CREATE))],
)
async def add_manual_punch(
    service: ServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
    employee_id: Annotated[int, Query(description="Employee ID.")],
    punch_time: Annotated[datetime, Query(description="Timestamp.")],
    punch_type: Annotated[PunchType, Query(description="Punch type.")],
    latitude: Annotated[Decimal | None, Query(description="GPS Lat.")] = None,
    longitude: Annotated[Decimal | None, Query(description="GPS Lon.")] = None,
) -> dict[str, Any]:
    """Append a raw punch log manually for an employee."""
    result = await service.add_manual_punch(
        org_id=org_id,
        actor_id=current_user.user_id,
        employee_id=employee_id,
        punch_time=punch_time,
        punch_type=punch_type,
        latitude=latitude,
        longitude=longitude,
    )
    return _ok(result, "Manual punch entry logged.")


@router.get(
    "/attendance/punches",
    response_model=SuccessResponse[AttendanceLogsResponse],
    summary="List Raw Punch Logs",
    dependencies=[Depends(require_permission(_PUNCH, A.READ))],
)
async def list_punches(
    service: ServiceDep,
    org_id: OrgIdDep,
    from_date: Annotated[date, Query(alias="from", description="Start date.")],
    to_date: Annotated[date, Query(alias="to", description="End date.")],
    employee_id: Annotated[int | None, Query(description="Filter by employee.")] = None,
    device_id: Annotated[int | None, Query(description="Filter by device.")] = None,
    pagination: Annotated[PaginationParams, Depends(pagination_params)] = None,
) -> dict[str, Any]:
    """Search and filter raw punch logs."""
    page = pagination.page if pagination else 1
    page_size = pagination.page_size if pagination else 25
    query = AttendanceLogsQuery(
        employee_id=employee_id,
        device_id=device_id,
        from_date=from_date,
        to_date=to_date,
        page=page,
        page_size=page_size,
    )
    result = await service.list_punches(org_id=org_id, query=query)
    return _ok(result)


@router.get(
    "/attendance/days/{day_id}/punches",
    response_model=SuccessResponse[list[AttendancePunchSchema]],
    summary="Get Day Punches",
    dependencies=[Depends(require_permission(_PUNCH, A.READ))],
)
async def get_day_punches(
    day_id: int,
    service: ServiceDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Fetch chronological punches for a specific attendance day."""
    result = await service.get_day_punches(org_id=org_id, day_id=day_id)
    return _ok(result)


@router.get(
    "/employees/{employee_id}/attendance/punches",
    response_model=SuccessResponse[list[AttendancePunchSchema]],
    summary="Get Employee Punch Timeline",
    dependencies=[Depends(require_permission(_PUNCH, A.READ))],
)
async def get_employee_punch_timeline(
    employee_id: int,
    service: ServiceDep,
    org_id: OrgIdDep,
    date_from: Annotated[date, Query(alias="from", description="Start date.")],
    date_to: Annotated[date, Query(alias="to", description="End date.")],
) -> dict[str, Any]:
    """Fetch chronological punch timeline for an employee within a window."""
    result = await service.get_employee_punch_timeline(
        org_id=org_id,
        employee_id=employee_id,
        date_from=date_from,
        date_to=date_to,
    )
    return _ok(result)


# ===========================================================================
# Penalties
# ===========================================================================


@router.post(
    "/attendance/penalties",
    response_model=SuccessResponse[AttendancePenaltySchema],
    status_code=status.HTTP_201_CREATED,
    summary="Apply Penalty",
    dependencies=[Depends(require_permission(_PENALTY, A.CREATE))],
)
async def apply_penalty(
    service: ServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
    employee_id: Annotated[int, Query(description="Employee ID.")],
    attendance_day_id: Annotated[int, Query(description="Daily summary ID.")],
    penalty_type: Annotated[PenaltyType, Query(description="Penalty type.")],
    penalty_unit: Annotated[PenaltyUnit, Query(description="Penalty unit.")],
    penalty_value: Annotated[Decimal, Query(description="Deduction value.")],
    remarks: Annotated[str | None, Query(description="Remarks.")] = None,
) -> dict[str, Any]:
    """Manually apply an attendance penalty."""
    result = await service.apply_penalty(
        org_id=org_id,
        actor_id=current_user.user_id,
        employee_id=employee_id,
        attendance_day_id=attendance_day_id,
        penalty_type=penalty_type,
        penalty_unit=penalty_unit,
        penalty_value=penalty_value,
        remarks=remarks,
    )
    return _ok(result, "Penalty applied.")


@router.get(
    "/attendance/penalties",
    response_model=SuccessResponse[PaginatedResponse[AttendancePenaltySchema]],
    summary="List Penalties",
    dependencies=[Depends(require_permission(_PENALTY, A.READ))],
)
async def list_penalties(
    service: ServiceDep,
    org_id: OrgIdDep,
    employee_id: Annotated[int | None, Query(description="Filter by employee.")] = None,
    status_val: Annotated[
        PenaltyStatus | None, Query(alias="status", description="Filter by status.")
    ] = None,
    pagination: Annotated[PaginationParams, Depends(pagination_params)] = None,
) -> dict[str, Any]:
    """Search and filter applied penalties."""
    page = pagination.page if pagination else 1
    page_size = pagination.page_size if pagination else 25
    result = await service.list_penalties(
        org_id=org_id,
        employee_id=employee_id,
        status=status_val,
        page=page,
        page_size=page_size,
    )
    return _ok(result)


@router.get(
    "/attendance/penalties/{penalty_id}",
    response_model=SuccessResponse[AttendancePenaltySchema],
    summary="Get Penalty Details",
    dependencies=[Depends(require_permission(_PENALTY, A.READ))],
)
async def get_penalty_details(
    penalty_id: int,
    service: ServiceDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Retrieve details of a single penalty."""
    result = await service.get_penalty_details(org_id=org_id, penalty_id=penalty_id)
    return _ok(result)


@router.post(
    "/attendance/penalties/{penalty_id}/waive",
    response_model=SuccessResponse[AttendancePenaltySchema],
    summary="Waive Penalty",
    dependencies=[Depends(require_permission(_PENALTY, A.EDIT))],
)
async def waive_penalty(
    penalty_id: int,
    service: ServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
    remarks: Annotated[str | None, Query(description="Reason for waive.")] = None,
) -> dict[str, Any]:
    """Waive an active penalty with reason audit."""
    result = await service.waive_penalty(
        org_id=org_id,
        actor_id=current_user.user_id,
        penalty_id=penalty_id,
        remarks=remarks,
    )
    return _ok(result, "Penalty waived successfully.")


@router.get(
    "/employees/{employee_id}/attendance/penalties",
    response_model=SuccessResponse[list[AttendancePenaltySchema]],
    summary="Get Employee Penalty History",
    dependencies=[Depends(require_permission(_PENALTY, A.READ))],
)
async def get_employee_penalty_history(
    employee_id: int,
    service: ServiceDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Fetch all penalties (both active and waived) for a single employee."""
    result = await service.get_employee_penalty_history(org_id=org_id, employee_id=employee_id)
    return _ok(result)


# ===========================================================================
# Summarization & Reports
# ===========================================================================


@router.get(
    "/attendance/summary/daily",
    response_model=SuccessResponse[dict[str, Any]],
    summary="Daily Attendance Summary",
    dependencies=[Depends(require_permission(_ATTENDANCE, A.READ))],
)
async def get_daily_summary(
    service: ServiceDep,
    org_id: OrgIdDep,
    q_date: Annotated[date, Query(alias="date", description="Target summary date.")],
    branch_id: Annotated[int | None, Query(description="Filter by branch.")] = None,
    department_id: Annotated[int | None, Query(description="Filter by department.")] = None,
    shift_id: Annotated[int | None, Query(description="Filter by shift.")] = None,
) -> dict[str, Any]:
    """Retrieve daily summary metrics for the dashboard grid."""
    result = await service.get_daily_summary(
        org_id=org_id,
        date_val=q_date,
        branch_id=branch_id,
        dept_id=department_id,
        shift_id=shift_id,
    )
    return _ok(result)


@router.get(
    "/attendance/summary/monthly",
    response_model=SuccessResponse[list[dict[str, Any]]],
    summary="Monthly Attendance Summary",
    dependencies=[Depends(require_permission(_ATTENDANCE, A.READ))],
)
async def get_monthly_summary(
    service: ServiceDep,
    org_id: OrgIdDep,
    month: Annotated[int, Query(ge=1, le=12, description="Month.")],
    year: Annotated[int, Query(ge=1900, le=2100, description="Year.")],
    employee_id: Annotated[int | None, Query(description="Filter by employee.")] = None,
    branch_id: Annotated[int | None, Query(description="Filter by branch.")] = None,
    department_id: Annotated[int | None, Query(description="Filter by department.")] = None,
    shift_id: Annotated[int | None, Query(description="Filter by shift.")] = None,
) -> dict[str, Any]:
    """Retrieve monthly consolidated attendance summaries for employees."""
    result = await service.get_monthly_summary(
        org_id=org_id,
        month=month,
        year=year,
        employee_id=employee_id,
        branch_id=branch_id,
        dept_id=department_id,
        shift_id=shift_id,
    )
    return _ok(result)


@router.get(
    "/attendance/reports/employee",
    response_model=SuccessResponse[dict[str, Any]],
    summary="Employee Attendance Report",
    dependencies=[Depends(require_permission(_ATTENDANCE, A.READ))],
)
async def get_employee_attendance_report(
    service: ServiceDep,
    org_id: OrgIdDep,
    employee_id: Annotated[int, Query(description="Employee ID.")],
    date_from: Annotated[date, Query(alias="from", description="Start date.")],
    date_to: Annotated[date, Query(alias="to", description="End date.")],
) -> dict[str, Any]:
    """Generate detailed attendance report for an employee."""
    result = await service.get_employee_attendance_report(
        org_id=org_id,
        employee_id=employee_id,
        date_from=date_from,
        date_to=date_to,
    )
    return _ok(result)


@router.get(
    "/attendance/reports/department",
    response_model=SuccessResponse[dict[str, Any]],
    summary="Department Attendance Report",
    dependencies=[Depends(require_permission(_ATTENDANCE, A.READ))],
)
async def get_department_attendance_report(
    service: ServiceDep,
    org_id: OrgIdDep,
    department_id: Annotated[int, Query(alias="department", description="Department ID.")],
    date_from: Annotated[date, Query(alias="from", description="Start date.")],
    date_to: Annotated[date, Query(alias="to", description="End date.")],
) -> dict[str, Any]:
    """Generate consolidated attendance report for a department."""
    result = await service.get_department_attendance_report(
        org_id=org_id,
        dept_id=department_id,
        date_from=date_from,
        date_to=date_to,
    )
    return _ok(result)


@router.get(
    "/attendance/reports/branch",
    response_model=SuccessResponse[dict[str, Any]],
    summary="Branch Attendance Report",
    dependencies=[Depends(require_permission(_ATTENDANCE, A.READ))],
)
async def get_branch_attendance_report(
    service: ServiceDep,
    org_id: OrgIdDep,
    branch_id: Annotated[int, Query(alias="branch", description="Branch ID.")],
    date_from: Annotated[date, Query(alias="from", description="Start date.")],
    date_to: Annotated[date, Query(alias="to", description="End date.")],
) -> dict[str, Any]:
    """Generate consolidated attendance report for a branch."""
    result = await service.get_branch_attendance_report(
        org_id=org_id,
        branch_id=branch_id,
        date_from=date_from,
        date_to=date_to,
    )
    return _ok(result)


@router.get(
    "/attendance/reports/shift",
    response_model=SuccessResponse[dict[str, Any]],
    summary="Shift-wise Attendance Report",
    dependencies=[Depends(require_permission(_ATTENDANCE, A.READ))],
)
async def get_shift_attendance_report(
    service: ServiceDep,
    org_id: OrgIdDep,
    shift_id: Annotated[int, Query(alias="shift", description="Shift ID.")],
    date_from: Annotated[date, Query(alias="from", description="Start date.")],
    date_to: Annotated[date, Query(alias="to", description="End date.")],
) -> dict[str, Any]:
    """Generate consolidated attendance report grouped by shift."""
    result = await service.get_shift_attendance_report(
        org_id=org_id,
        shift_id=shift_id,
        date_from=date_from,
        date_to=date_to,
    )
    return _ok(result)


# ===========================================================================
# Corrections & Regularizations
# ===========================================================================


@router.post(
    "/attendance/corrections",
    response_model=SuccessResponse[AttendanceCorrectionSchema],
    status_code=status.HTTP_201_CREATED,
    summary="Request Attendance Correction / Regularization",
    dependencies=[Depends(require_permission(_ATTENDANCE, A.CREATE))],
)
async def request_correction(
    payload: AttendanceCorrectionCreateRequest,
    service: ServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Request manual correction/regularization of punches for an attendance day."""
    result = await service.request_correction(
        org_id=org_id,
        actor_id=current_user.user_id,
        data=payload,
    )
    return _ok(result, "Correction request submitted.")


@router.put(
    "/attendance/corrections/{request_id}/approve",
    response_model=SuccessResponse[AttendanceCorrectionSchema],
    summary="Approve / Reject Attendance Correction",
    dependencies=[Depends(require_permission(_ATTENDANCE, A.EDIT))],
)
async def approve_correction(
    request_id: int,
    payload: AttendanceCorrectionApproveRequest,
    service: ServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Process approval decision for an attendance regularization request."""
    result = await service.approve_correction(
        org_id=org_id,
        actor_id=current_user.user_id,
        request_id=request_id,
        data=payload,
    )
    return _ok(result, f"Regularization request status updated to {payload.decision.value}.")


# ===========================================================================
# Missing Punches Analysis & Locks & Recomputations
# ===========================================================================


@router.get(
    "/attendance/missing-punches",
    response_model=SuccessResponse[AttendanceMissingPunchesResponse],
    summary="Analyze Missing Punches",
    dependencies=[Depends(require_permission(_ATTENDANCE, A.READ))],
)
async def get_missing_punches(
    service: ServiceDep,
    org_id: OrgIdDep,
    from_date: Annotated[date, Query(alias="from", description="Start date.")],
    to_date: Annotated[date, Query(alias="to", description="End date.")],
    branch_id: Annotated[int | None, Query(description="Filter by branch.")] = None,
    pagination: Annotated[PaginationParams, Depends(pagination_params)] = None,
) -> dict[str, Any]:
    """Scan and list flagged missing punches in a date window."""
    page = pagination.page if pagination else 1
    page_size = pagination.page_size if pagination else 25
    query = AttendanceMissingPunchesQuery(
        from_date=from_date,
        to_date=to_date,
        branch_id=branch_id,
        page=page,
        page_size=page_size,
    )
    result = await service.get_missing_punches(org_id=org_id, query=query)
    return _ok(result)


@router.post(
    "/attendance/lock",
    response_model=SuccessResponse[bool],
    summary="Freeze Attendance Period",
    dependencies=[Depends(require_permission(_ATTENDANCE, A.EDIT))],
)
async def lock_attendance(
    payload: AttendanceLockRequest,
    service: ServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Freeze mutations for a specific date range."""
    result = await service.lock_attendance(
        org_id=org_id,
        actor_id=current_user.user_id,
        data=payload,
    )
    return _ok(result, "Period locked successfully.")


@router.post(
    "/attendance/{employee_id}/recompute",
    response_model=SuccessResponse[AttendanceDayDetailSchema],
    summary="On-demand Recompute Attendance",
    dependencies=[Depends(require_permission(_ATTENDANCE, A.EDIT))],
)
async def recompute_attendance(
    employee_id: int,
    payload: AttendanceRecomputeRequest,
    service: ServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Recompute daily metrics on-demand for a given employee and date."""
    result = await service.recompute_attendance(
        org_id=org_id,
        actor_id=current_user.user_id,
        employee_id=employee_id,
        date_val=payload.date,
    )
    return _ok(result, "Recomputation completed.")


@router.post(
    "/attendance/unlock",
    response_model=SuccessResponse[bool],
    summary="Unfreeze Attendance Period",
    dependencies=[Depends(require_permission(_ATTENDANCE, A.EDIT))],
)
async def unlock_attendance(
    payload: AttendanceUnlockRequest,
    service: ServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Unfreeze mutations for a specific date range."""
    result = await service.unlock_attendance(
        org_id=org_id,
        actor_id=current_user.user_id,
        data=payload,
    )
    return _ok(result, "Period unlocked successfully.")


@router.get(
    "/attendance/locks",
    response_model=SuccessResponse[list[AttendanceLockSchema]],
    summary="List Attendance Locks",
    dependencies=[Depends(require_permission(_ATTENDANCE, A.READ))],
)
async def list_attendance_locks(
    service: ServiceDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """List all locked attendance periods for the organization."""
    result = await service.get_locked_periods(org_id=org_id)
    return _ok(result)
