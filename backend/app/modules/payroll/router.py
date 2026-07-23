"""Payroll Management — HTTP routes (thin controllers).

Maps the Payroll Management API Contract onto FastAPI endpoints. Controllers
resolve dependencies, parse queries/bodies, call :class:`PayrollService`, and
wrap results in the shared success envelope. No business logic lives here.

Route ordering note: static routes (e.g. ``/payroll/records/summary``) are
declared before parameterized ones (``/payroll/records/{row_id}``) so the static
path stays reachable.
"""

from __future__ import annotations

import datetime
import io
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import Response, StreamingResponse

from app.core.constants.enums import PermissionAction as A
from app.core.dependencies.auth import (
    CurrentUser,
    get_current_active_user,
    require_permission,
)
from app.core.dependencies.pagination import PaginationParams, pagination_params
from app.core.exceptions.base import AppException
from app.core.middleware.request_context import get_request_id
from app.jobs.queue import JobName, enqueue
from app.modules.payroll.constants import PaymentStatus
from app.modules.payroll.dependencies import PayrollServiceDep
from app.modules.payroll.schemas import (
    AttendanceAdjustmentCreateSchema,
    AttendanceAdjustmentExtraHoursCreateSchema,
    AttendanceAdjustmentExtraHoursResponseSchema,
    AttendanceAdjustmentListResponse,
    AttendanceAdjustmentPenaltyCreateSchema,
    AttendanceAdjustmentPenaltyResponseSchema,
    AttendanceAdjustmentResponseSchema,
    AttendanceAdjustmentUpdateSchema,
    BulkAttendanceAdjustmentBatchUpdateResponseSchema,
    BulkAttendanceAdjustmentBatchUpdateSchema,
    BulkAttendanceAdjustmentMatrixResponseSchema,
    BulkAttendanceAdjustmentResetSchema,
    EmployeeGroupAssignmentResponseSchema,
    EmployeeGroupAssignRequestSchema,
    FinalizedPayrollRunListResponse,
    FinalizedPayrollRunResponseSchema,
    PayrollColumnSettingsReplaceSchema,
    PayrollColumnSettingsResponseSchema,
    PayrollComputedRowSchema,
    PayrollCycleCreateSchema,
    PayrollCycleListResponse,
    PayrollCycleResponseSchema,
    PayrollCycleUpdateSchema,
    PayrollGroupCreateSchema,
    PayrollGroupListResponse,
    PayrollGroupResponseSchema,
    PayrollGroupUpdateSchema,
    PayrollPreviewResponseSchema,
    PayrollProcessRequestSchema,
    PayrollProcessResponseSchema,
    PayrollRecordListResponse,
    PayrollSettingResponseSchema,
    PayrollSettingUpdateSchema,
    PayrollSummaryResponseSchema,
    PayslipResponseSchema,
    RecordPaymentRequestSchema,
)
from app.shared.schemas.response import SuccessResponse, success_response

router = APIRouter(tags=["Payroll Management"])

# Feature-permission keys (Permission Matrix §12).
_CONFIG = "payroll_config"
_GROUP = "payroll_group"
_CYCLE = "payroll_cycle"
_PROCESSING = "payroll_processing"
_RECORD = "payroll_record"
_ADJUSTMENT = "payroll_adjustment"


# ===========================================================================
# Common Dependencies & Helpers
# ===========================================================================


def get_org_id(current_user: Annotated[CurrentUser, Depends(get_current_active_user)]) -> int:
    """Return the caller's tenant id, or raise TENANT_UNRESOLVED if absent."""
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


# ===========================================================================
# 4. Payroll Configuration
# ===========================================================================


@router.get(
    "/payroll/settings",
    response_model=SuccessResponse[PayrollSettingResponseSchema],
    summary="Get Payroll Configuration",
    dependencies=[Depends(require_permission(_CONFIG, A.READ))],
)
async def get_payroll_settings(
    service: PayrollServiceDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Retrieve the organization-wide payroll calculation settings."""
    result = await service.get_settings(org_id=org_id)
    return _ok(result)


@router.put(
    "/payroll/settings",
    response_model=SuccessResponse[PayrollSettingResponseSchema],
    summary="Update Payroll Configuration",
    dependencies=[Depends(require_permission(_CONFIG, A.EDIT))],
)
async def update_payroll_settings(
    payload: PayrollSettingUpdateSchema,
    service: PayrollServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Upsert the single org-level payroll settings row."""
    result = await service.update_settings(
        org_id=org_id, payload=payload, user_id=current_user.user_id
    )
    return _ok(result, "Payroll settings updated successfully.")


# ===========================================================================
# 5. Payroll Groups ("Salary Structures")
# ===========================================================================


@router.post(
    "/payroll/groups",
    response_model=SuccessResponse[PayrollGroupResponseSchema],
    status_code=status.HTTP_201_CREATED,
    summary="Create Payroll Group",
    dependencies=[Depends(require_permission(_GROUP, A.CREATE))],
)
async def create_payroll_group(
    payload: PayrollGroupCreateSchema,
    service: PayrollServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Create a new payroll group (salary structure) for the organization."""
    result = await service.create_group(
        org_id=org_id, payload=payload, user_id=current_user.user_id
    )
    return _ok(result, "Payroll group created successfully.")


@router.get(
    "/payroll/groups",
    response_model=SuccessResponse[PayrollGroupListResponse],
    summary="List Payroll Groups",
    dependencies=[Depends(require_permission(_GROUP, A.READ))],
)
async def list_payroll_groups(
    service: PayrollServiceDep,
    org_id: OrgIdDep,
    pagination: Annotated[PaginationParams, Depends(pagination_params)],
) -> dict[str, Any]:
    """List paginated payroll groups scoped to the organization."""
    result = await service.list_groups(
        org_id=org_id, page=pagination.page, page_size=pagination.page_size
    )
    return _ok(result)


@router.get(
    "/payroll/groups/{group_id}",
    response_model=SuccessResponse[PayrollGroupResponseSchema],
    summary="Get Payroll Group Details",
    dependencies=[Depends(require_permission(_GROUP, A.READ))],
)
async def get_payroll_group(
    group_id: int,
    service: PayrollServiceDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Retrieve the details of a specific payroll group."""
    result = await service.get_group(org_id=org_id, group_id=group_id)
    return _ok(result)


@router.patch(
    "/payroll/groups/{group_id}",
    response_model=SuccessResponse[PayrollGroupResponseSchema],
    summary="Update Payroll Group",
    dependencies=[Depends(require_permission(_GROUP, A.EDIT))],
)
async def update_payroll_group(
    group_id: int,
    payload: PayrollGroupUpdateSchema,
    service: PayrollServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Update mutable attributes of a payroll group."""
    result = await service.update_group(
        org_id=org_id, group_id=group_id, payload=payload, user_id=current_user.user_id
    )
    return _ok(result, "Payroll group updated successfully.")


@router.delete(
    "/payroll/groups/{group_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Payroll Group",
    dependencies=[Depends(require_permission(_GROUP, A.DELETE))],
)
async def delete_payroll_group(
    group_id: int,
    service: PayrollServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
) -> Response:
    """Soft-delete a payroll group if it is not referenced by employees, cycles, or runs."""
    await service.delete_group(
        org_id=org_id, group_id=group_id, user_id=current_user.user_id
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.put(
    "/employees/{employee_id}/payroll-group",
    response_model=SuccessResponse[EmployeeGroupAssignmentResponseSchema],
    summary="Assign Group to Employee",
    dependencies=[Depends(require_permission(_GROUP, A.EDIT))],
)
async def assign_payroll_group(
    employee_id: int,
    payload: EmployeeGroupAssignRequestSchema,
    service: PayrollServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Assign an employee to a payroll group, recording the prior group as history."""
    result = await service.assign_group(
        org_id=org_id,
        employee_id=employee_id,
        payload=payload,
        user_id=current_user.user_id,
    )
    return _ok(result, "Payroll group assigned successfully.")


@router.get(
    "/employees/{employee_id}/payroll-group",
    response_model=SuccessResponse[EmployeeGroupAssignmentResponseSchema],
    summary="View Employee Group Assignment",
    dependencies=[Depends(require_permission(_GROUP, A.READ))],
)
async def get_employee_payroll_group(
    employee_id: int,
    service: PayrollServiceDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Retrieve the employee's current group assignment plus previous-group history."""
    result = await service.get_employee_assignment(org_id=org_id, employee_id=employee_id)
    return _ok(result)


@router.get(
    "/payroll/groups/{group_id}/columns",
    response_model=SuccessResponse[PayrollColumnSettingsResponseSchema],
    summary="List Group Column Settings",
    dependencies=[Depends(require_permission(_GROUP, A.READ))],
)
async def list_group_columns(
    group_id: int,
    service: PayrollServiceDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """List the payslip/report column layout settings for a group."""
    columns = await service.list_columns(org_id=org_id, group_id=group_id)
    return _ok(PayrollColumnSettingsResponseSchema(columns=columns))


@router.put(
    "/payroll/groups/{group_id}/columns",
    response_model=SuccessResponse[PayrollColumnSettingsResponseSchema],
    summary="Replace Group Column Settings",
    dependencies=[Depends(require_permission(_GROUP, A.EDIT))],
)
async def replace_group_columns(
    group_id: int,
    payload: PayrollColumnSettingsReplaceSchema,
    service: PayrollServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Replace the full column layout for a group."""
    columns = await service.replace_columns(
        org_id=org_id, group_id=group_id, payload=payload, user_id=current_user.user_id
    )
    return _ok(
        PayrollColumnSettingsResponseSchema(columns=columns),
        "Column settings replaced successfully.",
    )


# ===========================================================================
# 6. Payroll Cycles
# ===========================================================================


@router.post(
    "/payroll/cycles",
    response_model=SuccessResponse[PayrollCycleResponseSchema],
    status_code=status.HTTP_201_CREATED,
    summary="Create Payroll Cycle",
    dependencies=[Depends(require_permission(_CYCLE, A.CREATE))],
)
async def create_payroll_cycle(
    payload: PayrollCycleCreateSchema,
    service: PayrollServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Create a payroll cycle (unique per group + cycle date)."""
    result = await service.create_cycle(
        org_id=org_id, payload=payload, user_id=current_user.user_id
    )
    return _ok(result, "Payroll cycle created successfully.")


@router.get(
    "/payroll/cycles",
    response_model=SuccessResponse[PayrollCycleListResponse],
    summary="List Payroll Cycles",
    dependencies=[Depends(require_permission(_CYCLE, A.READ))],
)
async def list_payroll_cycles(
    service: PayrollServiceDep,
    org_id: OrgIdDep,
    pagination: Annotated[PaginationParams, Depends(pagination_params)],
    payroll_group_id: Annotated[int | None, Query(description="Filter by payroll group.")] = None,
    is_finalized: Annotated[bool | None, Query(description="Filter by finalized state.")] = None,
) -> dict[str, Any]:
    """List paginated payroll cycles filtered by group and finalized state."""
    result = await service.list_cycles(
        org_id=org_id,
        group_id=payroll_group_id,
        is_finalized=is_finalized,
        page=pagination.page,
        page_size=pagination.page_size,
    )
    return _ok(result)


@router.patch(
    "/payroll/cycles/{cycle_id}",
    response_model=SuccessResponse[PayrollCycleResponseSchema],
    summary="Update Payroll Cycle",
    dependencies=[Depends(require_permission(_CYCLE, A.EDIT))],
)
async def update_payroll_cycle(
    cycle_id: int,
    payload: PayrollCycleUpdateSchema,
    service: PayrollServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Update a cycle's date while it is not finalized."""
    result = await service.update_cycle(
        org_id=org_id, cycle_id=cycle_id, payload=payload, user_id=current_user.user_id
    )
    return _ok(result, "Payroll cycle updated successfully.")


# ===========================================================================
# 7. Payroll Processing & Finalized Runs
# ===========================================================================


@router.post(
    "/payroll/processing/generate",
    response_model=SuccessResponse[PayrollProcessResponseSchema],
    summary="Generate Payroll",
    dependencies=[Depends(require_permission(_PROCESSING, A.EDIT))],
)
async def generate_payroll(
    payload: PayrollProcessRequestSchema,
    service: PayrollServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Compute and persist payroll rows for a group's employees (skips finalized rows)."""
    result = await service.generate_payroll(
        org_id=org_id, payload=payload, user_id=current_user.user_id
    )
    return _ok(result, "Payroll generated successfully.")


@router.post(
    "/payroll/processing/recalculate",
    response_model=SuccessResponse[PayrollProcessResponseSchema],
    summary="Recalculate Payroll",
    dependencies=[Depends(require_permission(_PROCESSING, A.EDIT))],
)
async def recalculate_payroll(
    payload: PayrollProcessRequestSchema,
    service: PayrollServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Recompute existing (non-finalized) payroll rows for the period."""
    result = await service.recalculate_payroll(
        org_id=org_id, payload=payload, user_id=current_user.user_id
    )
    return _ok(result, "Payroll recalculated successfully.")


@router.post(
    "/payroll/processing/preview",
    response_model=SuccessResponse[PayrollPreviewResponseSchema],
    summary="Preview Payroll",
    dependencies=[Depends(require_permission(_PROCESSING, A.READ))],
)
async def preview_payroll(
    payload: PayrollProcessRequestSchema,
    service: PayrollServiceDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Compute payroll for the period without persisting; returns the would-be rows."""
    rows = await service.preview_payroll(org_id=org_id, payload=payload)
    return _ok(PayrollPreviewResponseSchema(items=rows))


@router.post(
    "/payroll/processing/finalize",
    response_model=SuccessResponse[FinalizedPayrollRunResponseSchema],
    status_code=status.HTTP_201_CREATED,
    summary="Finalize Payroll (Lock)",
    dependencies=[Depends(require_permission(_PROCESSING, A.EDIT))],
)
async def finalize_payroll(
    payload: PayrollProcessRequestSchema,
    service: PayrollServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Create a finalized run, lock its computed rows, and finalize the cycle."""
    result = await service.finalize_payroll(
        org_id=org_id, payload=payload, user_id=current_user.user_id
    )
    return _ok(result, "Payroll finalized successfully.")


@router.post(
    "/payroll/finalized-runs/{run_id}/definalize",
    response_model=SuccessResponse[FinalizedPayrollRunResponseSchema],
    summary="Unlock / Definalize Payroll",
    dependencies=[Depends(require_permission(_PROCESSING, A.EDIT))],
)
async def definalize_payroll(
    run_id: int,
    service: PayrollServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Unlock a finalized run so its rows can be recomputed."""
    result = await service.definalize_payroll(
        org_id=org_id, run_id=run_id, user_id=current_user.user_id
    )
    return _ok(result, "Payroll run unlocked successfully.")


@router.post(
    "/payroll/finalized-runs/{run_id}/payment",
    response_model=SuccessResponse[FinalizedPayrollRunResponseSchema],
    summary="Record Payment",
    dependencies=[Depends(require_permission(_PROCESSING, A.EDIT))],
)
async def record_payment(
    run_id: int,
    payload: RecordPaymentRequestSchema,
    service: PayrollServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Record disbursement details and payment status against a finalized run."""
    result = await service.record_payment(
        org_id=org_id, run_id=run_id, payload=payload, user_id=current_user.user_id
    )
    return _ok(result, "Payment recorded successfully.")


@router.get(
    "/payroll/finalized-runs",
    response_model=SuccessResponse[FinalizedPayrollRunListResponse],
    summary="List Finalized Runs",
    dependencies=[Depends(require_permission(_RECORD, A.READ))],
)
async def list_finalized_runs(
    service: PayrollServiceDep,
    org_id: OrgIdDep,
    pagination: Annotated[PaginationParams, Depends(pagination_params)],
    payroll_group_id: Annotated[int | None, Query(description="Filter by payroll group.")] = None,
    cycle_from: Annotated[datetime.date | None, Query(description="Cycle start.")] = None,
    cycle_to: Annotated[datetime.date | None, Query(description="Cycle end (inclusive).")] = None,
    payment_status: Annotated[
        PaymentStatus | None, Query(description="Filter by payment status.")
    ] = None,
) -> dict[str, Any]:
    """List paginated finalized payroll runs filtered by group, cycle range, and payment status."""
    result = await service.list_finalized_runs(
        org_id=org_id,
        group_id=payroll_group_id,
        cycle_from=cycle_from,
        cycle_to=cycle_to,
        payment_status=payment_status,
        page=pagination.page,
        page_size=pagination.page_size,
    )
    return _ok(result)


@router.get(
    "/payroll/finalized-runs/{run_id}",
    response_model=SuccessResponse[FinalizedPayrollRunResponseSchema],
    summary="Get Finalized Run Details",
    dependencies=[Depends(require_permission(_RECORD, A.READ))],
)
async def get_finalized_run(
    run_id: int,
    service: PayrollServiceDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Retrieve the details of a specific finalized payroll run."""
    result = await service.get_finalized_run(org_id=org_id, run_id=run_id)
    return _ok(result)


# ===========================================================================
# 8. Payroll Records & Summary
#
# Static routes (`/payroll/records/summary`) MUST precede the parameterized
# `/payroll/records/{row_id}` so the static one stays reachable.
# ===========================================================================


@router.get(
    "/payroll/records",
    response_model=SuccessResponse[PayrollRecordListResponse],
    summary="List Payroll Records",
    dependencies=[Depends(require_permission(_RECORD, A.READ))],
)
async def list_payroll_records(
    service: PayrollServiceDep,
    org_id: OrgIdDep,
    pagination: Annotated[PaginationParams, Depends(pagination_params)],
    payroll_group_id: Annotated[int | None, Query(description="Filter by payroll group.")] = None,
    cycle_from: Annotated[datetime.date | None, Query(description="Cycle start.")] = None,
    cycle_to: Annotated[datetime.date | None, Query(description="Cycle end (inclusive).")] = None,
    employee_id: Annotated[int | None, Query(description="Filter by employee.")] = None,
    is_finalized: Annotated[bool | None, Query(description="Filter by finalized state.")] = None,
    branch_id: Annotated[int | None, Query(description="Filter by branch (data scope).")] = None,
    dept_id: Annotated[int | None, Query(description="Filter by department (data scope).")] = None,
) -> dict[str, Any]:
    """List paginated, data-scoped computed payroll records with filters."""
    result = await service.list_records(
        org_id=org_id,
        group_id=payroll_group_id,
        cycle_from=cycle_from,
        cycle_to=cycle_to,
        employee_id=employee_id,
        is_finalized=is_finalized,
        branch_id=branch_id,
        dept_id=dept_id,
        page=pagination.page,
        page_size=pagination.page_size,
    )
    return _ok(result)


@router.get(
    "/payroll/records/summary",
    response_model=SuccessResponse[PayrollSummaryResponseSchema],
    summary="Payroll Summary",
    dependencies=[Depends(require_permission(_RECORD, A.READ))],
)
async def get_payroll_summary(
    service: PayrollServiceDep,
    org_id: OrgIdDep,
    payroll_group_id: Annotated[int, Query(description="Target payroll group.")],
    cycle_from: Annotated[datetime.date, Query(description="Cycle start (inclusive).")],
    cycle_to: Annotated[datetime.date, Query(description="Cycle end (inclusive).")],
) -> dict[str, Any]:
    """Aggregate summary statistics (headcount, totals) over computed records for a period."""
    result = await service.get_summary(
        org_id=org_id, group_id=payroll_group_id, cycle_from=cycle_from, cycle_to=cycle_to
    )
    return _ok(result)


@router.get(
    "/payroll/records/{row_id}",
    response_model=SuccessResponse[PayrollComputedRowSchema],
    summary="Get Payroll Details",
    dependencies=[Depends(require_permission(_RECORD, A.READ))],
)
async def get_payroll_record(
    row_id: int,
    service: PayrollServiceDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Retrieve a full computed payroll row."""
    result = await service.get_record(org_id=org_id, row_id=row_id)
    return _ok(result)


@router.get(
    "/employees/{employee_id}/payroll",
    response_model=SuccessResponse[PayrollRecordListResponse],
    summary="Employee Payroll History",
    dependencies=[Depends(require_permission(_RECORD, A.READ))],
)
async def get_employee_payroll_history(
    employee_id: int,
    service: PayrollServiceDep,
    org_id: OrgIdDep,
    pagination: Annotated[PaginationParams, Depends(pagination_params)],
) -> dict[str, Any]:
    """List an employee's computed payroll rows across cycles."""
    result = await service.get_employee_history(
        org_id=org_id,
        employee_id=employee_id,
        page=pagination.page,
        page_size=pagination.page_size,
    )
    return _ok(result)


# ===========================================================================
# 9. Payslips
# ===========================================================================


@router.get(
    "/payroll/records/{row_id}/payslip",
    response_model=SuccessResponse[PayslipResponseSchema],
    summary="View Payslip",
    dependencies=[Depends(require_permission(_RECORD, A.READ))],
)
async def view_payslip(
    row_id: int,
    service: PayrollServiceDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Render a payslip payload on demand from a computed row."""
    result = await service.view_payslip(org_id=org_id, row_id=row_id)
    return _ok(result)


@router.get(
    "/payroll/records/{row_id}/payslip/download",
    summary="Download Payslip",
    dependencies=[Depends(require_permission(_RECORD, A.READ))],
)
async def download_payslip(
    row_id: int,
    service: PayrollServiceDep,
    org_id: OrgIdDep,
) -> StreamingResponse:
    """Download the payslip PDF stream (restricted to finalized records)."""
    pdf_bytes = await service.download_payslip_pdf(org_id=org_id, row_id=row_id)
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=payslip_{row_id}.pdf"},
    )


@router.post(
    "/payroll/records/{row_id}/payslip/email",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Email Payslip",
    dependencies=[Depends(require_permission(_RECORD, A.EDIT))],
)
async def email_payslip(
    row_id: int,
    service: PayrollServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Queue delivery of the payslip on the background job queue.

    Validates the computed row exists, then enqueues ``send_payslip_email``, which
    renders the payslip and sends it over SMTP in the worker. If the queue is
    unreachable the enqueue raises (503) rather than reporting a delivery that was
    never scheduled — see :mod:`app.jobs.queue` for the policy.
    """
    payslip = await service.view_payslip(org_id=org_id, row_id=row_id)
    job_id = await enqueue(
        JobName.SEND_PAYSLIP_EMAIL,
        org_id=org_id,
        row_id=row_id,
        actor_id=current_user.user_id,
    )
    return _ok(
        {
            "row_id": payslip.row_id,
            "employee_id": payslip.employee_id,
            "queued": True,
            "job_id": job_id,
        },
        "Payslip email queued for delivery.",
    )


# ===========================================================================
# 10. Payroll Adjustments
#
# Static sub-routes (`/payroll/adjustments/penalties`, `.../extra-hours`) are
# declared before the parameterized `/payroll/adjustments/{adjustment_id}`.
# ===========================================================================


@router.post(
    "/payroll/adjustments",
    response_model=SuccessResponse[AttendanceAdjustmentResponseSchema],
    status_code=status.HTTP_201_CREATED,
    summary="Add / Upsert Adjustment",
    dependencies=[Depends(require_permission(_ADJUSTMENT, A.CREATE))],
)
async def add_adjustment(
    payload: AttendanceAdjustmentCreateSchema,
    service: PayrollServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Create or upsert an attendance status adjustment (blocked for finalized periods)."""
    result = await service.add_adjustment(
        org_id=org_id, payload=payload, user_id=current_user.user_id
    )
    return _ok(result, "Attendance adjustment saved successfully.")


@router.get(
    "/payroll/adjustments",
    response_model=SuccessResponse[AttendanceAdjustmentListResponse],
    summary="List / Adjustment History",
    dependencies=[Depends(require_permission(_ADJUSTMENT, A.READ))],
)
async def list_adjustments(
    service: PayrollServiceDep,
    org_id: OrgIdDep,
    pagination: Annotated[PaginationParams, Depends(pagination_params)],
    employee_id: Annotated[int | None, Query(description="Filter by employee.")] = None,
    date_from: Annotated[datetime.date | None, Query(description="Start date (inclusive).")] = None,
    date_to: Annotated[datetime.date | None, Query(description="End date (inclusive).")] = None,
) -> dict[str, Any]:
    """List paginated, data-scoped attendance adjustments (adjustment history)."""
    result = await service.list_adjustments(
        org_id=org_id,
        employee_id=employee_id,
        date_from=date_from,
        date_to=date_to,
        page=pagination.page,
        page_size=pagination.page_size,
    )
    return _ok(result)


@router.post(
    "/payroll/adjustments/penalties",
    response_model=SuccessResponse[AttendanceAdjustmentPenaltyResponseSchema],
    status_code=status.HTTP_201_CREATED,
    summary="Add Adjustment Penalty",
    dependencies=[Depends(require_permission(_ADJUSTMENT, A.CREATE))],
)
async def add_adjustment_penalty(
    payload: AttendanceAdjustmentPenaltyCreateSchema,
    service: PayrollServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Record a manual penalty for an employee on a date (blocked for finalized periods)."""
    result = await service.add_penalty(
        org_id=org_id, payload=payload, user_id=current_user.user_id
    )
    return _ok(result, "Penalty recorded successfully.")


@router.post(
    "/payroll/adjustments/extra-hours",
    response_model=SuccessResponse[AttendanceAdjustmentExtraHoursResponseSchema],
    status_code=status.HTTP_201_CREATED,
    summary="Add Adjustment Extra Hours",
    dependencies=[Depends(require_permission(_ADJUSTMENT, A.CREATE))],
)
async def add_adjustment_extra_hours(
    payload: AttendanceAdjustmentExtraHoursCreateSchema,
    service: PayrollServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Record extra hours for an employee on a date (unique per employee+date)."""
    result = await service.add_extra_hours(
        org_id=org_id, payload=payload, user_id=current_user.user_id
    )
    return _ok(result, "Extra hours recorded successfully.")


@router.patch(
    "/payroll/adjustments/{adjustment_id}",
    response_model=SuccessResponse[AttendanceAdjustmentResponseSchema],
    summary="Update Adjustment",
    dependencies=[Depends(require_permission(_ADJUSTMENT, A.EDIT))],
)
async def update_adjustment(
    adjustment_id: int,
    payload: AttendanceAdjustmentUpdateSchema,
    service: PayrollServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Update an attendance adjustment (blocked for finalized periods)."""
    result = await service.update_adjustment(
        org_id=org_id,
        adjustment_id=adjustment_id,
        payload=payload,
        user_id=current_user.user_id,
    )
    return _ok(result, "Attendance adjustment updated successfully.")


@router.delete(
    "/payroll/adjustments/{adjustment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Adjustment",
    dependencies=[Depends(require_permission(_ADJUSTMENT, A.DELETE))],
)
async def delete_adjustment(
    adjustment_id: int,
    service: PayrollServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
) -> Response:
    """Hard-delete an attendance adjustment (blocked for finalized periods)."""
    await service.delete_adjustment(
        org_id=org_id, adjustment_id=adjustment_id, user_id=current_user.user_id
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ===========================================================================
# 11. Bulk Attendance Adjustments (Phase 2)
# ===========================================================================


@router.get(
    "/payroll/bulk-attendance-adjustments",
    response_model=SuccessResponse[BulkAttendanceAdjustmentMatrixResponseSchema],
    summary="Get Bulk Attendance Adjustment Matrix",
    dependencies=[Depends(require_permission(_ADJUSTMENT, A.READ))],
)
async def get_bulk_attendance_matrix(
    service: PayrollServiceDep,
    org_id: OrgIdDep,
    pagination: Annotated[PaginationParams, Depends(pagination_params)],
    date_from: Annotated[datetime.date, Query(description="Start date (inclusive).")],
    date_to: Annotated[datetime.date, Query(description="End date (inclusive).")],
    branch_id: Annotated[int | None, Query(description="Filter by branch ID.")] = None,
    dept_id: Annotated[int | None, Query(description="Filter by department ID.")] = None,
    search: Annotated[str | None, Query(description="Search by employee name or code.")] = None,
) -> dict[str, Any]:
    """Fetch paginated attendance adjustment matrix grid for employees."""
    result = await service.get_bulk_attendance_matrix(
        org_id=org_id,
        date_from=date_from,
        date_to=date_to,
        branch_id=branch_id,
        dept_id=dept_id,
        search=search,
        page=pagination.page,
        page_size=pagination.page_size,
    )
    return _ok(result)


@router.put(
    "/payroll/bulk-attendance-adjustments",
    response_model=SuccessResponse[BulkAttendanceAdjustmentBatchUpdateResponseSchema],
    summary="Batch Update Bulk Attendance Adjustments",
    dependencies=[Depends(require_permission(_ADJUSTMENT, A.EDIT))],
)
async def batch_update_bulk_attendance_adjustments(
    payload: BulkAttendanceAdjustmentBatchUpdateSchema,
    service: PayrollServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Batch save modified attendance status cells for employees."""
    result = await service.batch_update_bulk_attendance_adjustments(
        org_id=org_id,
        payload=payload,
        user_id=current_user.user_id,
    )
    return _ok(result, result.message)


@router.post(
    "/payroll/bulk-attendance-adjustments/reset",
    response_model=SuccessResponse[dict[str, Any]],
    summary="Reset Bulk Attendance Adjustments",
    dependencies=[Depends(require_permission(_ADJUSTMENT, A.EDIT))],
)
async def reset_bulk_attendance_adjustments(
    payload: BulkAttendanceAdjustmentResetSchema,
    service: PayrollServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Reset bulk attendance status adjustments back to defaults/punches."""
    reset_count = await service.reset_bulk_attendance_adjustments(
        org_id=org_id,
        payload=payload,
        user_id=current_user.user_id,
    )
    return _ok({"reset_count": reset_count}, f"Reset {reset_count} attendance adjustments.")


@router.get(
    "/payroll/bulk-attendance-adjustments/export",
    summary="Export Bulk Attendance Adjustments Excel",
    dependencies=[Depends(require_permission(_ADJUSTMENT, A.READ))],
)
async def export_bulk_attendance_adjustments_excel(
    service: PayrollServiceDep,
    org_id: OrgIdDep,
    date_from: Annotated[datetime.date, Query(description="Start date (inclusive).")],
    date_to: Annotated[datetime.date, Query(description="End date (inclusive).")],
    branch_id: Annotated[int | None, Query(description="Filter by branch ID.")] = None,
    dept_id: Annotated[int | None, Query(description="Filter by department ID.")] = None,
    search: Annotated[str | None, Query(description="Search by employee name or code.")] = None,
) -> StreamingResponse:
    """Download exported Excel spreadsheet (.xlsx) of the bulk attendance matrix."""
    excel_bytes = await service.export_bulk_attendance_adjustments_excel(
        org_id=org_id,
        date_from=date_from,
        date_to=date_to,
        branch_id=branch_id,
        dept_id=dept_id,
        search=search,
    )
    filename = f"Bulk_Attendance_Adjustments_{date_from}_to_{date_to}.xlsx"
    return StreamingResponse(
        io.BytesIO(excel_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ===========================================================================
# 12. Process Payroll Endpoints (Phase 2)
# ===========================================================================


@router.get(
    "/payroll/process",
    response_model=SuccessResponse[PayrollRecordListResponse],
    summary="Get Process Payroll Matrix",
    dependencies=[Depends(require_permission(_PROCESSING, A.READ))],
)
async def get_process_payroll_matrix(
    service: PayrollServiceDep,
    org_id: OrgIdDep,
    date_from: Annotated[datetime.date, Query(description="Start date (YYYY-MM-DD).")],
    date_to: Annotated[datetime.date, Query(description="End date (YYYY-MM-DD).")],
    payroll_group_id: Annotated[int | None, Query(description="Optional payroll group ID.")] = None,
    branch_id: Annotated[int | None, Query(description="Optional branch ID.")] = None,
    dept_id: Annotated[int | None, Query(description="Optional department ID.")] = None,
    search: Annotated[str | None, Query(description="Search employee name or code.")] = None,
    pagination: PaginationParams = Depends(pagination_params),
) -> dict[str, Any]:
    """Fetch process payroll matrix for employees over a date range."""
    result = await service.get_process_payroll_matrix(
        org_id=org_id,
        date_from=date_from,
        date_to=date_to,
        payroll_group_id=payroll_group_id,
        branch_id=branch_id,
        dept_id=dept_id,
        search=search,
        page=pagination.page,
        page_size=pagination.page_size,
    )
    return _ok(result, "Process payroll matrix fetched successfully.")


@router.post(
    "/payroll/process/calculate",
    response_model=SuccessResponse[PayrollProcessResponseSchema],
    summary="Calculate Process Payroll",
    dependencies=[Depends(require_permission(_PROCESSING, A.EDIT))],
)
async def calculate_process_payroll(
    payload: PayrollProcessRequestSchema,
    service: PayrollServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Run payroll calculation for target employees in a period."""
    result = await service.calculate_process_payroll(
        org_id=org_id,
        payload=payload,
        user_id=current_user.user_id,
    )
    return _ok(result, "Payroll calculated successfully.")


@router.post(
    "/payroll/process/finalize",
    response_model=SuccessResponse[FinalizedPayrollRunResponseSchema],
    summary="Finalize Process Payroll Run",
    dependencies=[Depends(require_permission(_PROCESSING, A.EDIT))],
)
async def finalize_process_payroll(
    payload: PayrollProcessRequestSchema,
    service: PayrollServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Lock and finalize payroll run for a period."""
    result = await service.finalize_process_payroll(
        org_id=org_id,
        payload=payload,
        user_id=current_user.user_id,
    )
    return _ok(result, "Payroll run finalized and locked successfully.")


@router.get(
    "/payroll/process/export",
    summary="Export Process Payroll Excel",
    dependencies=[Depends(require_permission(_PROCESSING, A.READ))],
)
async def export_process_payroll_excel(
    service: PayrollServiceDep,
    org_id: OrgIdDep,
    date_from: Annotated[datetime.date, Query(description="Start date (YYYY-MM-DD).")],
    date_to: Annotated[datetime.date, Query(description="End date (YYYY-MM-DD).")],
    payroll_group_id: Annotated[int | None, Query(description="Optional payroll group ID.")] = None,
    branch_id: Annotated[int | None, Query(description="Optional branch ID.")] = None,
    dept_id: Annotated[int | None, Query(description="Optional department ID.")] = None,
) -> StreamingResponse:
    """Download exported Excel spreadsheet (.xlsx) of process payroll matrix."""
    excel_bytes = await service.export_process_payroll(
        org_id=org_id,
        date_from=date_from,
        date_to=date_to,
        payroll_group_id=payroll_group_id,
        branch_id=branch_id,
        dept_id=dept_id,
    )
    filename = f"Process_Payroll_{date_from}_to_{date_to}.xlsx"
    return StreamingResponse(
        io.BytesIO(excel_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get(
    "/payroll/process/{employee_id}",
    response_model=SuccessResponse[PayrollComputedRowSchema],
    summary="Get Process Payroll Employee Detail",
    dependencies=[Depends(require_permission(_PROCESSING, A.READ))],
)
async def get_process_payroll_employee_detail(
    employee_id: int,
    service: PayrollServiceDep,
    org_id: OrgIdDep,
    date_from: Annotated[datetime.date, Query(description="Start date (YYYY-MM-DD).")],
    date_to: Annotated[datetime.date, Query(description="End date (YYYY-MM-DD).")],
) -> dict[str, Any]:
    """Fetch detailed payroll calculation slip breakdown for a single employee."""
    result = await service.get_process_payroll_employee_detail(
        org_id=org_id,
        employee_id=employee_id,
        date_from=date_from,
        date_to=date_to,
    )
    return _ok(result, "Employee payroll details fetched successfully.")

