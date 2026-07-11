"""Approval Management — HTTP routes (thin controllers).

Maps the Approval Management API Contract onto FastAPI endpoints.
All business logic is kept strictly inside the ApprovalService.
Controllers handle auth, permissions, data scoping, DTO parsing,
and format responses into the standard success envelope.
"""

from __future__ import annotations

from datetime import date
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
from app.modules.approvals.constants import ApprovalStatus, RequestType
from app.modules.approvals.exceptions import (
    ApprovalForbiddenScopeException,
    ApprovalNotFoundException,
)
from app.modules.approvals.schemas import (
    ApprovalDetailsSchema,
    ApprovalListResponse,
    ApprovalPendingCountSchema,
    ApprovalRequestSchema,
    ApprovalStatusSchema,
    ApprovalTimelineEventSchema,
    ApproveRequestInput,
    BulkActionItemError,
    BulkActionItemResultSchema,
    BulkActionResponseSchema,
    BulkApproveRequestInput,
    BulkRejectRequestInput,
    RejectRequestInput,
)
from app.modules.approvals.service import ApprovalService
from app.shared.schemas.response import SuccessResponse, success_response

router = APIRouter(tags=["Approval Management"])

# RBAC Permission feature key
_APPROVAL = "approval"


# ---------------------------------------------------------------------------
# Dependencies & Helpers
# ---------------------------------------------------------------------------


async def get_approval_service(db: Annotated[Any, Depends(get_db)]) -> ApprovalService:
    """Provide an ApprovalService bound to the request DB session."""
    return ApprovalService(db)


def get_org_id(current_user: Annotated[CurrentUser, Depends(get_current_active_user)]) -> int:
    """Return the caller's tenant id, or 400 TENANT_UNRESOLVED if absent."""
    if current_user.org_id is None:
        exc = AppException("Organization context is required.", code="TENANT_UNRESOLVED")
        exc.status_code = status.HTTP_400_BAD_REQUEST
        raise exc
    return current_user.org_id


ServiceDep = Annotated[ApprovalService, Depends(get_approval_service)]
CurrentUserDep = Annotated[CurrentUser, Depends(get_current_active_user)]
OrgIdDep = Annotated[int, Depends(get_org_id)]


def _ok(data: Any, message: str = "OK") -> dict[str, Any]:
    return success_response(data=data, message=message, request_id=get_request_id())


async def check_approval_data_scope(
    service: ApprovalService,
    org_id: int,
    approval_id: int,
    current_user: CurrentUser,
) -> None:
    """Raise ApprovalForbiddenScopeException if user is not super admin and lacks access to the
    approval request's scope."""
    if current_user.is_super_admin:
        return

    # Fetch approval envelope
    approval = await service.approvals.get_by_id_in_org(org_id, approval_id)
    if not approval:
        raise ApprovalNotFoundException()

    # Load active employee associated with the approval request
    employee = await service.employees.get_active_by_id(approval.employee_id, org_id)
    if (
        not employee
        or not current_user.permissions.can_access_branch(employee.master_branch_id)
        or not current_user.permissions.can_access_department(employee.dept_id)
    ):
        raise ApprovalForbiddenScopeException()


def resolve_read_data_scope(
    current_user: CurrentUser,
    branch_id: int | None,
    dept_id: int | None,
) -> tuple[int | None, int | None]:
    """Validate requested scope filters against current user permissions and return applicable
    filters."""
    if current_user.is_super_admin:
        return branch_id, dept_id

    # If non-super admin specifies a branch, validate they can access it
    if branch_id is not None:
        if not current_user.permissions.can_access_branch(branch_id):
            raise ApprovalForbiddenScopeException()
    else:
        # Default to first permitted branch scope if available, else restrict
        branch_ids = list(current_user.permissions.branch_ids)
        branch_id = branch_ids[0] if branch_ids else -1

    # If non-super admin specifies a department, validate they can access it
    if dept_id is not None:
        if not current_user.permissions.can_access_department(dept_id):
            raise ApprovalForbiddenScopeException()
    else:
        dept_ids = list(current_user.permissions.department_ids)
        dept_id = dept_ids[0] if dept_ids else -1

    return branch_id, dept_id


# ===========================================================================
# 1. Read Operations / List / Timeline / Detail
# ===========================================================================


@router.get(
    "/approvals",
    response_model=SuccessResponse[ApprovalListResponse],
    summary="List / Search / Filter Approvals",
    dependencies=[Depends(require_permission(_APPROVAL, A.READ))],
)
async def list_approvals(
    service: ServiceDep,
    org_id: OrgIdDep,
    current_user: CurrentUserDep,
    status_val: Annotated[
        ApprovalStatus | None, Query(alias="status", description="Filter by status.")
    ] = None,
    request_type: Annotated[
        RequestType | None, Query(description="Filter by request type.")
    ] = None,
    request_subtype: Annotated[str | None, Query(description="Filter by request subtype.")] = None,
    employee_id: Annotated[int | None, Query(description="Filter by employee ID.")] = None,
    date_from: Annotated[date | None, Query(description="Filter by start requested date.")] = None,
    date_to: Annotated[date | None, Query(description="Filter by end requested date.")] = None,
    branch_id: Annotated[int | None, Query(description="Filter by branch.")] = None,
    dept_id: Annotated[int | None, Query(description="Filter by department.")] = None,
    pagination: Annotated[PaginationParams, Depends(pagination_params)] = None,
) -> dict[str, Any]:
    """Search and filter approval requests. Applies tenant isolation and branch/department scope
    checks."""
    p_branch, p_dept = resolve_read_data_scope(current_user, branch_id, dept_id)
    page = pagination.page if pagination else 1
    page_size = pagination.page_size if pagination else 25

    items = await service.approvals.search(
        org_id,
        status=status_val,
        request_type=request_type,
        request_subtype=request_subtype,
        employee_id=employee_id,
        date_from=date_from,
        date_to=date_to,
        branch_id=p_branch,
        dept_id=p_dept,
        page=page,
        page_size=page_size,
    )
    total = await service.approvals.search_count(
        org_id,
        status=status_val,
        request_type=request_type,
        request_subtype=request_subtype,
        employee_id=employee_id,
        date_from=date_from,
        date_to=date_to,
        branch_id=p_branch,
        dept_id=p_dept,
    )

    res = service.paginate(items, page=page, page_size=page_size, total_records=total)
    return _ok(res)


@router.get(
    "/approvals/pending",
    response_model=SuccessResponse[ApprovalListResponse],
    summary="List Pending Approvals",
    dependencies=[Depends(require_permission(_APPROVAL, A.READ))],
)
async def list_pending_approvals(
    service: ServiceDep,
    org_id: OrgIdDep,
    current_user: CurrentUserDep,
    branch_id: Annotated[int | None, Query(description="Filter by branch.")] = None,
    dept_id: Annotated[int | None, Query(description="Filter by department.")] = None,
    pagination: Annotated[PaginationParams, Depends(pagination_params)] = None,
) -> dict[str, Any]:
    """Retrieve pending approvals scoped by the caller's organization and permissions."""
    p_branch, p_dept = resolve_read_data_scope(current_user, branch_id, dept_id)
    page = pagination.page if pagination else 1
    page_size = pagination.page_size if pagination else 25

    res = await service.list_pending_approvals(
        org_id,
        branch_id=p_branch,
        dept_id=p_dept,
        page=page,
        page_size=page_size,
    )
    return _ok(res)


@router.get(
    "/approvals/history",
    response_model=SuccessResponse[ApprovalListResponse],
    summary="Approval History",
    dependencies=[Depends(require_permission(_APPROVAL, A.READ))],
)
async def get_approval_history(
    service: ServiceDep,
    org_id: OrgIdDep,
    current_user: CurrentUserDep,
    request_type: Annotated[
        RequestType | None, Query(description="Filter by request type.")
    ] = None,
    employee_id: Annotated[int | None, Query(description="Filter by employee ID.")] = None,
    date_from: Annotated[date | None, Query(description="Filter start date.")] = None,
    date_to: Annotated[date | None, Query(description="Filter end date.")] = None,
    branch_id: Annotated[int | None, Query(description="Filter by branch.")] = None,
    dept_id: Annotated[int | None, Query(description="Filter by department.")] = None,
    pagination: Annotated[PaginationParams, Depends(pagination_params)] = None,
) -> dict[str, Any]:
    """List completed/decided approvals matching the query context."""
    p_branch, p_dept = resolve_read_data_scope(current_user, branch_id, dept_id)
    page = pagination.page if pagination else 1
    page_size = pagination.page_size if pagination else 25

    res = await service.get_approval_history(
        org_id,
        branch_id=p_branch,
        dept_id=p_dept,
        request_type=request_type,
        employee_id=employee_id,
        date_from=date_from,
        date_to=date_to,
        page=page,
        page_size=page_size,
    )
    return _ok(res)


@router.get(
    "/approvals/my-pending",
    response_model=SuccessResponse[ApprovalListResponse],
    summary="My Pending Approvals",
    dependencies=[Depends(require_permission(_APPROVAL, A.READ))],
)
async def get_my_pending_approvals(
    service: ServiceDep,
    org_id: OrgIdDep,
    current_user: CurrentUserDep,
    branch_id: Annotated[int | None, Query(description="Filter by branch.")] = None,
    dept_id: Annotated[int | None, Query(description="Filter by department.")] = None,
    pagination: Annotated[PaginationParams, Depends(pagination_params)] = None,
) -> dict[str, Any]:
    """Convenience list of pending approvals scoped by reviewer permission context."""
    p_branch, p_dept = resolve_read_data_scope(current_user, branch_id, dept_id)
    page = pagination.page if pagination else 1
    page_size = pagination.page_size if pagination else 25

    res = await service.get_my_pending_approvals(
        org_id,
        branch_id=p_branch,
        dept_id=p_dept,
        page=page,
        page_size=page_size,
    )
    return _ok(res)


@router.get(
    "/approvals/recent",
    response_model=SuccessResponse[list[ApprovalRequestSchema]],
    summary="Recent Decisions",
    dependencies=[Depends(require_permission(_APPROVAL, A.READ))],
)
async def get_recent_decisions(
    service: ServiceDep,
    org_id: OrgIdDep,
    current_user: CurrentUserDep,
    decision: Annotated[ApprovalStatus, Query(description="Target decision filter: approved or "
        "rejected.")],
    request_type: Annotated[
        RequestType | None, Query(description="Filter by request type.")
    ] = None,
    branch_id: Annotated[int | None, Query(description="Filter by branch.")] = None,
    dept_id: Annotated[int | None, Query(description="Filter by department.")] = None,
    limit: Annotated[int, Query(ge=1, le=100, description="Number of records to return.")] = 10,
) -> dict[str, Any]:
    """Retrieve recently decided approval requests ordered descending by review timestamp."""
    p_branch, p_dept = resolve_read_data_scope(current_user, branch_id, dept_id)
    
    # Enforce only completed decisions (approved/rejected) are queryable here
    if decision not in (ApprovalStatus.APPROVED, ApprovalStatus.REJECTED):
        raise AppException(
            "Recent decisions view is only available for 'approved' or 'rejected' statuses.",
            code="VALIDATION_ERROR",
        )

    res = await service.get_recent_decisions(
        org_id,
        decision=decision,
        request_type=request_type,
        branch_id=p_branch,
        dept_id=p_dept,
        limit=limit,
    )
    return _ok(res)


@router.get(
    "/approvals/{approval_id}",
    response_model=SuccessResponse[ApprovalDetailsSchema],
    summary="Get Approval Details",
    dependencies=[Depends(require_permission(_APPROVAL, A.READ))],
)
async def get_approval_details(
    approval_id: int,
    service: ServiceDep,
    org_id: OrgIdDep,
    current_user: CurrentUserDep,
) -> dict[str, Any]:
    """Fetch complete details of an approval including resolved polymorphic source details."""
    await check_approval_data_scope(service, org_id, approval_id, current_user)
    details = await service.get_approval_details(org_id, approval_id)
    return _ok(details)


# ===========================================================================
# 2. Workflow Timeline & Status
# ===========================================================================


@router.get(
    "/approvals/{approval_id}/status",
    response_model=SuccessResponse[ApprovalStatusSchema],
    summary="View Current Approval Status",
    dependencies=[Depends(require_permission(_APPROVAL, A.READ))],
)
async def get_approval_status(
    approval_id: int,
    service: ServiceDep,
    org_id: OrgIdDep,
    current_user: CurrentUserDep,
) -> dict[str, Any]:
    """Query current status, reviewer information, and rejection remarks."""
    await check_approval_data_scope(service, org_id, approval_id, current_user)
    status_details = await service.get_approval_status(org_id, approval_id)
    return _ok(status_details)


@router.get(
    "/approvals/{approval_id}/timeline",
    response_model=SuccessResponse[list[ApprovalTimelineEventSchema]],
    summary="View Approval Timeline",
    dependencies=[Depends(require_permission(_APPROVAL, A.READ))],
)
async def get_approval_timeline(
    approval_id: int,
    service: ServiceDep,
    org_id: OrgIdDep,
    current_user: CurrentUserDep,
) -> dict[str, Any]:
    """Fetch single-level trail events (requested, and decided if applicable)."""
    await check_approval_data_scope(service, org_id, approval_id, current_user)
    timeline = await service.get_approval_timeline(org_id, approval_id)
    return _ok(timeline)


# ===========================================================================
# 3. Actions / Approve / Reject / Bulk
# ===========================================================================


@router.post(
    "/approvals/{approval_id}/approve",
    response_model=SuccessResponse[ApprovalRequestSchema],
    summary="Approve Request",
    dependencies=[Depends(require_permission(_APPROVAL, A.EDIT))],
)
async def approve_request(
    approval_id: int,
    payload: ApproveRequestInput,
    service: ServiceDep,
    org_id: OrgIdDep,
    current_user: CurrentUserDep,
) -> dict[str, Any]:
    """Approve a pending request envelope and apply side-effects to the target module."""
    await check_approval_data_scope(service, org_id, approval_id, current_user)
    res = await service.approve_request(
        org_id=org_id,
        approval_id=approval_id,
        reviewer_id=current_user.user_id,
        remarks=payload.remarks,
    )
    return _ok(res, "Approval request approved successfully.")


@router.post(
    "/approvals/{approval_id}/reject",
    response_model=SuccessResponse[ApprovalRequestSchema],
    summary="Reject Request",
    dependencies=[Depends(require_permission(_APPROVAL, A.EDIT))],
)
async def reject_request(
    approval_id: int,
    payload: RejectRequestInput,
    service: ServiceDep,
    org_id: OrgIdDep,
    current_user: CurrentUserDep,
) -> dict[str, Any]:
    """Reject a pending request envelope and propagate status change."""
    await check_approval_data_scope(service, org_id, approval_id, current_user)
    res = await service.reject_request(
        org_id=org_id,
        approval_id=approval_id,
        reject_remarks=payload.reject_remarks,
        reviewer_id=current_user.user_id,
    )
    return _ok(res, "Approval request rejected successfully.")


@router.post(
    "/approvals/bulk-approve",
    response_model=SuccessResponse[BulkActionResponseSchema],
    summary="Bulk Approve Requests",
    dependencies=[Depends(require_permission(_APPROVAL, A.EDIT))],
)
async def bulk_approve(
    payload: BulkApproveRequestInput,
    service: ServiceDep,
    org_id: OrgIdDep,
    current_user: CurrentUserDep,
) -> dict[str, Any]:
    """Process bulk approvals under individual savepoint isolation."""
    # Filter/verify scope for requested IDs beforehand to mark out-of-scope items
    validated_ids = []
    skipped_items = []
    
    for approval_id in payload.approval_ids:
        try:
            await check_approval_data_scope(service, org_id, approval_id, current_user)
            validated_ids.append(approval_id)
        except AppException as e:
            skipped_items.append(
                BulkActionItemResultSchema(
                    id=approval_id,
                    success=False,
                    error=BulkActionItemError(code=e.code, message=e.message),
                )
            )
        except Exception as e:
            skipped_items.append(
                BulkActionItemResultSchema(
                    id=approval_id,
                    success=False,
                    error=BulkActionItemError(code="SYSTEM_ERROR", message=str(e)),
                )
            )

    results = []
    if validated_ids:
        raw_results = await service.bulk_approve(
            org_id=org_id,
            approval_ids=validated_ids,
            reviewer_id=current_user.user_id,
        )
        for item in raw_results:
            err = BulkActionItemError(**item["error"]) if item.get("error") else None
            results.append(
                BulkActionItemResultSchema(
                    id=item["id"],
                    success=item["success"],
                    error=err,
                )
            )
            
    all_results = skipped_items + results
    return _ok({"results": all_results}, "Bulk approval completed.")


@router.post(
    "/approvals/bulk-reject",
    response_model=SuccessResponse[BulkActionResponseSchema],
    summary="Bulk Reject Requests",
    dependencies=[Depends(require_permission(_APPROVAL, A.EDIT))],
)
async def bulk_reject(
    payload: BulkRejectRequestInput,
    service: ServiceDep,
    org_id: OrgIdDep,
    current_user: CurrentUserDep,
) -> dict[str, Any]:
    """Process bulk rejections under savepoint isolation."""
    validated_ids = []
    skipped_items = []

    for approval_id in payload.approval_ids:
        try:
            await check_approval_data_scope(service, org_id, approval_id, current_user)
            validated_ids.append(approval_id)
        except AppException as e:
            skipped_items.append(
                BulkActionItemResultSchema(
                    id=approval_id,
                    success=False,
                    error=BulkActionItemError(code=e.code, message=e.message),
                )
            )
        except Exception as e:
            skipped_items.append(
                BulkActionItemResultSchema(
                    id=approval_id,
                    success=False,
                    error=BulkActionItemError(code="SYSTEM_ERROR", message=str(e)),
                )
            )

    results = []
    if validated_ids:
        raw_results = await service.bulk_reject(
            org_id=org_id,
            approval_ids=validated_ids,
            reject_remarks=payload.reject_remarks,
            reviewer_id=current_user.user_id,
        )
        for item in raw_results:
            err = BulkActionItemError(**item["error"]) if item.get("error") else None
            results.append(
                BulkActionItemResultSchema(
                    id=item["id"],
                    success=item["success"],
                    error=err,
                )
            )

    all_results = skipped_items + results
    return _ok({"results": all_results}, "Bulk rejection completed.")


# ===========================================================================
# 4. Dashboard Summary & Convenience Views
# ===========================================================================


@router.get(
    "/approvals/summary/pending-count",
    response_model=SuccessResponse[ApprovalPendingCountSchema],
    summary="Pending Approval Count",
    dependencies=[Depends(require_permission(_APPROVAL, A.READ))],
)
async def get_pending_approval_count(
    service: ServiceDep,
    org_id: OrgIdDep,
    current_user: CurrentUserDep,
    branch_id: Annotated[int | None, Query(description="Filter by branch.")] = None,
    dept_id: Annotated[int | None, Query(description="Filter by department.")] = None,
) -> dict[str, Any]:
    """Retrieve total and type-specific breakdown of pending approvals inside the caller's scope."""
    p_branch, p_dept = resolve_read_data_scope(current_user, branch_id, dept_id)
    res = await service.get_pending_approval_count(
        org_id,
        branch_id=p_branch,
        dept_id=p_dept,
    )
    return _ok(res)
