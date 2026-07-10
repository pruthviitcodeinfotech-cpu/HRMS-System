"""Activity Log / Audit — HTTP routes (thin, read-only controllers).

Maps the Activity Log / Audit Management API Contract onto FastAPI endpoints. The
audit trail is append-only: this router exposes reads only (no create/update/
delete). Controllers resolve dependencies, build the query schema, call
:class:`~app.modules.audit.service.AuditService`, and wrap the result in the
standard success envelope.

Route-ordering note: the STATIC ``/activity-logs/security-events`` route is
declared BEFORE the PARAMETERIZED ``/activity-logs/{log_id}`` route so it is not
shadowed (which would 422 on the string ``security-events``).
"""

from __future__ import annotations

import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, status

from app.core.constants.enums import PermissionAction as A
from app.core.constants.enums import SortOrder
from app.core.dependencies.auth import (
    CurrentUser,
    get_current_active_user,
    require_permission,
)
from app.core.exceptions.base import AppException
from app.core.middleware.request_context import get_request_id
from app.modules.audit.constants import ActionFrom, ActionType
from app.modules.audit.dependencies import AuditServiceDep
from app.modules.audit.schemas import (
    ActivityLogDetail,
    ActivityLogListResponse,
    ActivityLogSearchQuery,
    SecurityEventQuery,
    SecurityEventType,
    SubjectActivityLogQuery,
)
from app.shared.schemas.response import SuccessResponse, success_response

router = APIRouter(tags=["Activity Log / Audit"])

_AUDIT = "audit"


# ---------------------------------------------------------------------------
# Dependencies
# ---------------------------------------------------------------------------

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
    """Wrap a controller result in the standard SuccessResponse envelope."""
    return success_response(data=data, message=message, request_id=get_request_id())


def _branch_scope(current_user: CurrentUser) -> list[int] | None:
    """Resolve caller's branch data scope. None means unrestricted (super admin/org-wide)."""
    branch_ids = current_user.permissions.branch_ids
    if current_user.is_super_admin or not branch_ids:
        return None
    return list(branch_ids)


# ===========================================================================
# Activity / Audit Logs (§4)
# ===========================================================================

@router.get(
    "/activity-logs",
    response_model=SuccessResponse[ActivityLogListResponse],
    summary="List / Search / Filter Activity Logs",
    dependencies=[Depends(require_permission(_AUDIT, A.READ))],
)
async def list_activity_logs(
    service: AuditServiceDep,
    org_id: OrgIdDep,
    page: Annotated[int, Query(ge=1, description="1-based page number.")] = 1,
    page_size: Annotated[int, Query(ge=1, le=100, description="Items per page.")] = 25,
    module: Annotated[str | None, Query(description="Filter by module.")] = None,
    sub_module: Annotated[str | None, Query(description="Filter by sub-module.")] = None,
    action_type: Annotated[ActionType | None, Query(description="Filter by action type.")] = None,
    action_from: Annotated[ActionFrom | None, Query(description="Filter by platform.")] = None,
    employee_id: Annotated[int | None, Query(description="Filter by employee subject.")] = None,
    performed_by_user_id: Annotated[int | None, Query(description="Filter by acting user.")] = None,
    date_from: Annotated[datetime.date | None, Query(description="log_date lower bound.")] = None,
    date_to: Annotated[datetime.date | None, Query(description="log_date upper bound.")] = None,
    search: Annotated[str | None, Query(description="Free-text on title/description.")] = None,
    sort_by: Annotated[str | None, Query(description="logged_at (default) | log_date.")] = None,
    sort_order: Annotated[SortOrder, Query(description="asc | desc.")] = SortOrder.DESC,
) -> dict[str, Any]:
    """Search, filter, sort, and paginate the tenant's audit trail (§4.1, §4.3)."""
    query = ActivityLogSearchQuery(
        page=page,
        page_size=page_size,
        module=module,
        sub_module=sub_module,
        action_type=action_type,
        action_from=action_from,
        employee_id=employee_id,
        performed_by_user_id=performed_by_user_id,
        date_from=date_from,
        date_to=date_to,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    result = await service.list_logs(org_id=org_id, query=query)
    return _ok(result)


@router.get(
    "/activity-logs/security-events",
    response_model=SuccessResponse[ActivityLogListResponse],
    summary="Security Event Timeline",
    dependencies=[Depends(require_permission(_AUDIT, A.READ))],
)
async def list_security_events(
    service: AuditServiceDep,
    org_id: OrgIdDep,
    page: Annotated[int, Query(ge=1, description="1-based page number.")] = 1,
    page_size: Annotated[int, Query(ge=1, le=100, description="Items per page.")] = 25,
    event: Annotated[SecurityEventType | None, Query(description="Event category.")] = None,
    employee_id: Annotated[int | None, Query(description="Filter by employee subject.")] = None,
    performed_by_user_id: Annotated[int | None, Query(description="Filter by acting user.")] = None,
    date_from: Annotated[datetime.date | None, Query(description="log_date lower bound.")] = None,
    date_to: Annotated[datetime.date | None, Query(description="log_date upper bound.")] = None,
) -> dict[str, Any]:
    """Approximate, chronological security-event view over the audit trail (§6)."""
    query = SecurityEventQuery(
        page=page,
        page_size=page_size,
        event=event,
        employee_id=employee_id,
        performed_by_user_id=performed_by_user_id,
        date_from=date_from,
        date_to=date_to,
    )
    result = await service.list_security_events(org_id=org_id, query=query)
    return _ok(result)


@router.get(
    "/activity-logs/{log_id}",
    response_model=SuccessResponse[ActivityLogDetail],
    summary="Get Activity Log Details",
    dependencies=[Depends(require_permission(_AUDIT, A.READ))],
)
async def get_activity_log(
    log_id: int,
    service: AuditServiceDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Retrieve the full detail of a single audit row (§4.2)."""
    result = await service.get_log(org_id=org_id, log_id=log_id)
    return _ok(result)


# ===========================================================================
# Change History Views (§5)
# ===========================================================================

@router.get(
    "/employees/{employee_id}/activity-logs",
    response_model=SuccessResponse[ActivityLogListResponse],
    summary="Employee Activity / Entity Change History",
    dependencies=[Depends(require_permission(_AUDIT, A.READ))],
)
async def list_employee_activity_logs(
    employee_id: int,
    service: AuditServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
    page: Annotated[int, Query(ge=1, description="1-based page number.")] = 1,
    page_size: Annotated[int, Query(ge=1, le=100, description="Items per page.")] = 25,
    module: Annotated[str | None, Query(description="Filter by module.")] = None,
    sub_module: Annotated[str | None, Query(description="Filter by sub-module.")] = None,
    action_type: Annotated[ActionType | None, Query(description="Filter by action type.")] = None,
    date_from: Annotated[datetime.date | None, Query(description="log_date lower bound.")] = None,
    date_to: Annotated[datetime.date | None, Query(description="log_date upper bound.")] = None,
    sort_by: Annotated[str | None, Query(description="logged_at (default) | log_date.")] = None,
    sort_order: Annotated[SortOrder, Query(description="asc | desc.")] = SortOrder.DESC,
) -> dict[str, Any]:
    """Audit history where this employee is the subject (§5.4), branch/dept scoped."""
    query = SubjectActivityLogQuery(
        page=page,
        page_size=page_size,
        module=module,
        sub_module=sub_module,
        action_type=action_type,
        date_from=date_from,
        date_to=date_to,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    result = await service.list_employee_logs(
        org_id=org_id,
        employee_id=employee_id,
        query=query,
        allowed_branch_ids=_branch_scope(current_user),
    )
    return _ok(result)


@router.get(
    "/users/{user_id}/activity-logs",
    response_model=SuccessResponse[ActivityLogListResponse],
    summary="User Activity / User Change History (User Actions)",
    dependencies=[Depends(require_permission(_AUDIT, A.READ))],
)
async def list_user_activity_logs(
    user_id: int,
    service: AuditServiceDep,
    org_id: OrgIdDep,
    page: Annotated[int, Query(ge=1, description="1-based page number.")] = 1,
    page_size: Annotated[int, Query(ge=1, le=100, description="Items per page.")] = 25,
    module: Annotated[str | None, Query(description="Filter by module.")] = None,
    sub_module: Annotated[str | None, Query(description="Filter by sub-module.")] = None,
    action_type: Annotated[ActionType | None, Query(description="Filter by action type.")] = None,
    date_from: Annotated[datetime.date | None, Query(description="log_date lower bound.")] = None,
    date_to: Annotated[datetime.date | None, Query(description="log_date upper bound.")] = None,
    sort_by: Annotated[str | None, Query(description="logged_at (default) | log_date.")] = None,
    sort_order: Annotated[SortOrder, Query(description="asc | desc.")] = SortOrder.DESC,
) -> dict[str, Any]:
    """Audit history of mutation actions performed BY this user (§5.5)."""
    query = SubjectActivityLogQuery(
        page=page,
        page_size=page_size,
        module=module,
        sub_module=sub_module,
        action_type=action_type,
        date_from=date_from,
        date_to=date_to,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    result = await service.list_user_logs(org_id=org_id, user_id=user_id, query=query)
    return _ok(result)
