"""Leave & Holiday Management — HTTP routes (thin controllers).

Maps the Leave Management API Contract onto FastAPI endpoints. Controllers only
resolve dependencies, parse DTOs, call LeaveService, and wrap the result in the
standard success envelope. No business logic lives here.
"""

from __future__ import annotations

import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import Response

from app.core.constants.enums import PermissionAction as A
from app.core.constants.enums import SortOrder
from app.core.dependencies.auth import (
    CurrentUser,
    get_current_active_user,
    require_permission,
)
from app.core.dependencies.pagination import PaginationParams, pagination_params
from app.core.exceptions.base import AppException
from app.core.middleware.request_context import get_request_id
from app.modules.leave.constants import LeaveRequestStatus
from app.modules.leave.dependencies import LeaveServiceDep
from app.modules.leave.exceptions import EmployeeNotFoundException
from app.modules.leave.schemas import (
    EmployeeHolidayAssignmentSchema,
    EmployeeHolidayCalendarSchema,
    EmployeeLeaveAllocationSchema,
    EmployeeLeaveBalanceSchema,
    HolidayTemplateAssignRequest,
    HolidayTemplateCreateRequest,
    HolidayTemplateItemCreateRequest,
    HolidayTemplateItemSchema,
    HolidayTemplateItemUpdateRequest,
    HolidayTemplateSchema,
    HolidayTemplateUpdateRequest,
    LeaveBalanceAdjustmentSchema,
    LeaveBalanceAdjustRequest,
    LeaveBalanceListResponse,
    LeaveCreditDebitRequest,
    LeaveRequestCreateRequest,
    LeaveRequestListResponse,
    LeaveRequestSchema,
    LeaveRequestUpdateRequest,
    LeaveSettingsSchema,
    LeaveSettingsUpdateRequest,
    LeaveTypeCreateRequest,
    LeaveTypeListResponse,
    LeaveTypeSchema,
    LeaveTypeUpdateRequest,
)
from app.modules.rbac.repository import UserRepository
from app.shared.schemas.pagination import PaginatedResponse
from app.shared.schemas.response import SuccessResponse, success_response

router = APIRouter(tags=["Leave & Holiday Management"])

# RBAC feature keys (per contract §2 / §10 permission matrix)
_LEAVE_TYPE = "leave_type"
_LEAVE_CONFIG = "leave_config"
_LEAVE_BALANCE = "leave_balance"
_LEAVE_REQUEST = "leave_request"
_HOLIDAY = "holiday"


# ---------------------------------------------------------------------------
# Dependencies & Helpers
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


def _current_cycle_year() -> int:
    """Default cycle year (calendar) used when a caller omits ``cycle_year``."""
    return datetime.date.today().year


async def _resolve_self_employee_id(service: LeaveServiceDep, user_id: int) -> int:
    """Resolve the calling user's linked employee id for self-service actions."""
    user = await UserRepository(service.session).get_by_id(user_id)
    if user is None or user.employee_id is None:
        raise EmployeeNotFoundException()
    return user.employee_id


# ===========================================================================
# 1. Leave Types — feature key `leave_type`
# ===========================================================================


@router.post(
    "/leave-types",
    response_model=SuccessResponse[LeaveTypeSchema],
    status_code=status.HTTP_201_CREATED,
    summary="Create Leave Type",
    dependencies=[Depends(require_permission(_LEAVE_TYPE, A.CREATE))],
)
async def create_leave_type(
    payload: LeaveTypeCreateRequest,
    service: LeaveServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Create a new leave type (with embedded allocation/carry-forward/encashment policy)."""
    result = await service.create_leave_type(org_id, payload.model_dump(), current_user.user_id)
    return _ok(result, "Leave type created successfully.")


@router.get(
    "/leave-types",
    response_model=SuccessResponse[LeaveTypeListResponse],
    summary="List Leave Types",
    dependencies=[Depends(require_permission(_LEAVE_TYPE, A.READ))],
)
async def list_leave_types(
    service: LeaveServiceDep,
    org_id: OrgIdDep,
    pagination: Annotated[PaginationParams, Depends(pagination_params)],
    search: Annotated[str | None, Query(description="Search by name or alias.")] = None,
    is_active: Annotated[bool | None, Query(description="Filter by active state.")] = None,
    sort_by: Annotated[str | None, Query(description="Sort field (name, created_at).")] = "name",
    sort_order: Annotated[SortOrder, Query(description="Sort direction.")] = SortOrder.ASC,
) -> dict[str, Any]:
    """Search, filter, and paginate leave types within the organization."""
    result = await service.list_leave_types(
        org_id,
        search=search,
        is_active=is_active,
        sort_by=sort_by,
        sort_order=sort_order,
        page=pagination.page,
        page_size=pagination.page_size,
    )
    return _ok(result)


@router.get(
    "/leave-types/{leave_type_id}",
    response_model=SuccessResponse[LeaveTypeSchema],
    summary="Get Leave Type Details",
    dependencies=[Depends(require_permission(_LEAVE_TYPE, A.READ))],
)
async def get_leave_type(
    leave_type_id: int,
    service: LeaveServiceDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Retrieve full details of a specific leave type."""
    result = await service.get_leave_type(org_id, leave_type_id)
    return _ok(result)


@router.patch(
    "/leave-types/{leave_type_id}",
    response_model=SuccessResponse[LeaveTypeSchema],
    summary="Update Leave Type",
    dependencies=[Depends(require_permission(_LEAVE_TYPE, A.EDIT))],
)
async def update_leave_type(
    leave_type_id: int,
    payload: LeaveTypeUpdateRequest,
    service: LeaveServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Update a leave type (including activate/deactivate via ``is_active``)."""
    data = payload.model_dump(exclude_unset=True)
    result = await service.update_leave_type(org_id, leave_type_id, data, current_user.user_id)
    return _ok(result, "Leave type updated successfully.")


@router.delete(
    "/leave-types/{leave_type_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Leave Type",
    dependencies=[Depends(require_permission(_LEAVE_TYPE, A.DELETE))],
)
async def delete_leave_type(
    leave_type_id: int,
    service: LeaveServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
) -> Response:
    """Soft-delete a leave type when it is not referenced by active balances/requests."""
    await service.delete_leave_type(org_id, leave_type_id, current_user.user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ===========================================================================
# 2. Leave Cycle Configuration — feature key `leave_config`
# ===========================================================================


@router.get(
    "/leave-settings",
    response_model=SuccessResponse[LeaveSettingsSchema],
    summary="Get Leave Cycle Config",
    dependencies=[Depends(require_permission(_LEAVE_CONFIG, A.READ))],
)
async def get_leave_settings(
    service: LeaveServiceDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Retrieve (initializing on first read) the org's single leave-cycle configuration."""
    result = await service.get_leave_settings(org_id)
    return _ok(result)


@router.put(
    "/leave-settings",
    response_model=SuccessResponse[LeaveSettingsSchema],
    summary="Update Leave Cycle Config",
    dependencies=[Depends(require_permission(_LEAVE_CONFIG, A.EDIT))],
)
async def update_leave_settings(
    payload: LeaveSettingsUpdateRequest,
    service: LeaveServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Upsert the single org-level leave cycle configuration row."""
    result = await service.update_leave_settings(org_id, payload.model_dump(), current_user.user_id)
    return _ok(result, "Leave settings updated successfully.")


# ===========================================================================
# 3. Leave Balances, Allocations & Adjustments — feature key `leave_balance`
# ===========================================================================


@router.get(
    "/leave-balances",
    response_model=SuccessResponse[LeaveBalanceListResponse],
    summary="List Leave Balances",
    dependencies=[Depends(require_permission(_LEAVE_BALANCE, A.READ))],
)
async def list_leave_balances(
    service: LeaveServiceDep,
    org_id: OrgIdDep,
    pagination: Annotated[PaginationParams, Depends(pagination_params)],
    leave_type_id: Annotated[int | None, Query(description="Filter by leave type.")] = None,
    cycle_year: Annotated[int | None, Query(description="Filter by cycle year.")] = None,
    employee_id: Annotated[int | None, Query(description="Filter by employee.")] = None,
    branch_id: Annotated[int | None, Query(description="Filter by branch.")] = None,
    dept_id: Annotated[int | None, Query(description="Filter by department.")] = None,
) -> dict[str, Any]:
    """Search and paginate employee leave balances (org-scoped)."""
    result = await service.list_leave_balances(
        org_id,
        leave_type_id=leave_type_id,
        cycle_year=cycle_year,
        employee_id=employee_id,
        branch_id=branch_id,
        dept_id=dept_id,
        page=pagination.page,
        page_size=pagination.page_size,
    )
    return _ok(result)


@router.get(
    "/employees/{employee_id}/leave-balances",
    response_model=SuccessResponse[list[EmployeeLeaveBalanceSchema]],
    summary="Get Employee Leave Balance",
    dependencies=[Depends(require_permission(_LEAVE_BALANCE, A.READ))],
)
async def get_employee_leave_balances(
    employee_id: int,
    service: LeaveServiceDep,
    org_id: OrgIdDep,
    cycle_year: Annotated[int | None, Query(description="Cycle year (default current).")] = None,
    leave_type_id: Annotated[int | None, Query(description="Filter by leave type.")] = None,
) -> dict[str, Any]:
    """Retrieve an employee's per-type leave balances for a cycle year."""
    result = await service.get_employee_leave_balances(
        org_id,
        employee_id,
        cycle_year if cycle_year is not None else _current_cycle_year(),
        leave_type_id=leave_type_id,
    )
    return _ok(result)


@router.post(
    "/employees/{employee_id}/leave-balances/credit",
    response_model=SuccessResponse[EmployeeLeaveBalanceSchema],
    summary="Credit Leave",
    dependencies=[Depends(require_permission(_LEAVE_BALANCE, A.EDIT))],
)
async def credit_leave_balance(
    employee_id: int,
    payload: LeaveCreditDebitRequest,
    service: LeaveServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Credit (add) days to an employee's leave balance and record the adjustment."""
    result = await service.credit_leave_balance(
        org_id, employee_id, payload.model_dump(), current_user.user_id
    )
    return _ok(result, "Leave balance credited successfully.")


@router.post(
    "/employees/{employee_id}/leave-balances/debit",
    response_model=SuccessResponse[EmployeeLeaveBalanceSchema],
    summary="Debit Leave",
    dependencies=[Depends(require_permission(_LEAVE_BALANCE, A.EDIT))],
)
async def debit_leave_balance(
    employee_id: int,
    payload: LeaveCreditDebitRequest,
    service: LeaveServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Debit (subtract) days from an employee's leave balance and record the adjustment."""
    result = await service.debit_leave_balance(
        org_id, employee_id, payload.model_dump(), current_user.user_id
    )
    return _ok(result, "Leave balance debited successfully.")


@router.post(
    "/employees/{employee_id}/leave-balances/adjust",
    response_model=SuccessResponse[EmployeeLeaveBalanceSchema],
    summary="Adjust Leave Balance",
    dependencies=[Depends(require_permission(_LEAVE_BALANCE, A.EDIT))],
)
async def adjust_leave_balance(
    employee_id: int,
    payload: LeaveBalanceAdjustRequest,
    service: LeaveServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Adjust an employee's leave balance to an absolute value and record the delta."""
    result = await service.adjust_leave_balance(
        org_id, employee_id, payload.model_dump(), current_user.user_id
    )
    return _ok(result, "Leave balance adjusted successfully.")


@router.get(
    "/employees/{employee_id}/leave-balances/history",
    response_model=SuccessResponse[list[LeaveBalanceAdjustmentSchema]],
    summary="Leave Balance History",
    dependencies=[Depends(require_permission(_LEAVE_BALANCE, A.READ))],
)
async def get_leave_balance_history(
    employee_id: int,
    service: LeaveServiceDep,
    org_id: OrgIdDep,
    cycle_year: Annotated[int | None, Query(description="Cycle year (default current).")] = None,
    leave_type_id: Annotated[int | None, Query(description="Filter by leave type.")] = None,
) -> dict[str, Any]:
    """List the manual balance adjustment history for an employee."""
    result = await service.get_leave_balance_history(
        org_id,
        employee_id,
        cycle_year if cycle_year is not None else _current_cycle_year(),
        leave_type_id=leave_type_id,
    )
    return _ok(result)


@router.get(
    "/employees/{employee_id}/leave-allocations",
    response_model=SuccessResponse[list[EmployeeLeaveAllocationSchema]],
    summary="List Leave Allocations",
    dependencies=[Depends(require_permission(_LEAVE_BALANCE, A.READ))],
)
async def list_leave_allocations(
    employee_id: int,
    service: LeaveServiceDep,
    org_id: OrgIdDep,
    cycle_year: Annotated[int | None, Query(description="Filter by cycle year.")] = None,
) -> dict[str, Any]:
    """List an employee's allocation events (read-only; auto-allocation is a background job)."""
    result = await service.list_leave_allocations(org_id, employee_id, cycle_year=cycle_year)
    return _ok(result)


# ===========================================================================
# 4. Leave Requests — feature key `leave_request`
# ===========================================================================


@router.post(
    "/leave-requests",
    response_model=SuccessResponse[LeaveRequestSchema],
    status_code=status.HTTP_201_CREATED,
    summary="Apply Leave",
    dependencies=[Depends(require_permission(_LEAVE_REQUEST, A.CREATE))],
)
async def apply_leave(
    payload: LeaveRequestCreateRequest,
    service: LeaveServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Apply for leave (creates a pending request and initiates the approval workflow).

    Self-service: when ``employee_id`` is omitted it defaults to the caller's own
    linked employee.
    """
    data = payload.model_dump()
    if data.get("employee_id") is None:
        data["employee_id"] = await _resolve_self_employee_id(service, current_user.user_id)
    result = await service.apply_leave(org_id, data, current_user.user_id)
    return _ok(result, "Leave request submitted successfully.")


@router.get(
    "/leave-requests",
    response_model=SuccessResponse[LeaveRequestListResponse],
    summary="List / Search Leave Requests",
    dependencies=[Depends(require_permission(_LEAVE_REQUEST, A.READ))],
)
async def list_leave_requests(
    service: LeaveServiceDep,
    org_id: OrgIdDep,
    pagination: Annotated[PaginationParams, Depends(pagination_params)],
    employee_id: Annotated[int | None, Query(description="Filter by employee.")] = None,
    leave_type_id: Annotated[int | None, Query(description="Filter by leave type.")] = None,
    request_status: Annotated[
        LeaveRequestStatus | None, Query(alias="status", description="Filter by status.")
    ] = None,
    date_from: Annotated[datetime.date | None, Query(description="Overlap range start.")] = None,
    date_to: Annotated[datetime.date | None, Query(description="Overlap range end.")] = None,
    branch_id: Annotated[int | None, Query(description="Filter by branch.")] = None,
    dept_id: Annotated[int | None, Query(description="Filter by department.")] = None,
    sort_by: Annotated[str | None, Query(description="Sort field.")] = "applied_on",
    sort_dir: Annotated[SortOrder, Query(description="Sort direction.")] = SortOrder.DESC,
) -> dict[str, Any]:
    """Search and paginate leave requests (org-scoped)."""
    result = await service.list_leave_requests(
        org_id,
        employee_id=employee_id,
        leave_type_id=leave_type_id,
        status=request_status.value if request_status is not None else None,
        date_from=date_from,
        date_to=date_to,
        branch_id=branch_id,
        dept_id=dept_id,
        sort_by=sort_by,
        sort_order=sort_dir,
        page=pagination.page,
        page_size=pagination.page_size,
    )
    return _ok(result)


@router.get(
    "/leave-requests/{request_id}",
    response_model=SuccessResponse[LeaveRequestSchema],
    summary="Get Leave Details",
    dependencies=[Depends(require_permission(_LEAVE_REQUEST, A.READ))],
)
async def get_leave_request(
    request_id: int,
    service: LeaveServiceDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Retrieve a leave request including status and review fields."""
    result = await service.get_leave_request(org_id, request_id)
    return _ok(result)


@router.patch(
    "/leave-requests/{request_id}",
    response_model=SuccessResponse[LeaveRequestSchema],
    summary="Edit Leave Request",
    dependencies=[Depends(require_permission(_LEAVE_REQUEST, A.EDIT))],
)
async def update_leave_request(
    request_id: int,
    payload: LeaveRequestUpdateRequest,
    service: LeaveServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Edit a leave request (allowed only while it is pending)."""
    data = payload.model_dump(exclude_unset=True)
    result = await service.update_leave_request(org_id, request_id, data, current_user.user_id)
    return _ok(result, "Leave request updated successfully.")


@router.delete(
    "/leave-requests/{request_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Cancel Leave Request",
    dependencies=[Depends(require_permission(_LEAVE_REQUEST, A.DELETE))],
)
async def cancel_leave_request(
    request_id: int,
    service: LeaveServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
) -> Response:
    """Cancel (hard-delete) a leave request, allowed only while it is pending."""
    await service.cancel_leave_request(org_id, request_id, current_user.user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ===========================================================================
# 5. Holiday Groups / Templates — feature key `holiday`
# ===========================================================================


@router.post(
    "/holiday-templates",
    response_model=SuccessResponse[HolidayTemplateSchema],
    status_code=status.HTTP_201_CREATED,
    summary="Create Holiday Group",
    dependencies=[Depends(require_permission(_HOLIDAY, A.CREATE))],
)
async def create_holiday_group(
    payload: HolidayTemplateCreateRequest,
    service: LeaveServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Create a new holiday group/template with all its items atomically."""
    result = await service.create_holiday_group(org_id, payload.model_dump(), current_user.user_id)
    return _ok(result, "Holiday group created successfully.")


@router.get(
    "/holiday-templates",
    response_model=SuccessResponse[PaginatedResponse[HolidayTemplateSchema]],
    summary="List Holiday Groups",
    dependencies=[Depends(require_permission(_HOLIDAY, A.READ))],
)
async def list_holiday_groups(
    service: LeaveServiceDep,
    org_id: OrgIdDep,
    pagination: Annotated[PaginationParams, Depends(pagination_params)],
) -> dict[str, Any]:
    """List and paginate holiday groups/templates."""
    result = await service.list_holiday_groups(
        org_id, page=pagination.page, page_size=pagination.page_size
    )
    return _ok(result)


@router.get(
    "/holiday-templates/{template_id}",
    response_model=SuccessResponse[HolidayTemplateSchema],
    summary="Get Holiday Group",
    dependencies=[Depends(require_permission(_HOLIDAY, A.READ))],
)
async def get_holiday_group(
    template_id: int,
    service: LeaveServiceDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Retrieve a holiday group/template together with its items."""
    result = await service.get_holiday_group(org_id, template_id)
    return _ok(result)


@router.patch(
    "/holiday-templates/{template_id}",
    response_model=SuccessResponse[HolidayTemplateSchema],
    summary="Update Holiday Group",
    dependencies=[Depends(require_permission(_HOLIDAY, A.EDIT))],
)
async def update_holiday_group(
    template_id: int,
    payload: HolidayTemplateUpdateRequest,
    service: LeaveServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Update a holiday group/template name."""
    result = await service.update_holiday_group(
        org_id, template_id, payload.model_dump(), current_user.user_id
    )
    return _ok(result, "Holiday group updated successfully.")


@router.delete(
    "/holiday-templates/{template_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Holiday Group",
    dependencies=[Depends(require_permission(_HOLIDAY, A.DELETE))],
)
async def delete_holiday_group(
    template_id: int,
    service: LeaveServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
) -> Response:
    """Soft-delete a holiday group/template."""
    await service.delete_holiday_group(org_id, template_id, current_user.user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ===========================================================================
# 6. Holidays / Template Items — feature key `holiday`
# ===========================================================================


@router.post(
    "/holiday-templates/{template_id}/holidays",
    response_model=SuccessResponse[HolidayTemplateItemSchema],
    status_code=status.HTTP_201_CREATED,
    summary="Create Holiday",
    dependencies=[Depends(require_permission(_HOLIDAY, A.EDIT))],
)
async def create_holiday(
    template_id: int,
    payload: HolidayTemplateItemCreateRequest,
    service: LeaveServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Add a holiday item to a template (maintains the template's holiday count)."""
    result = await service.create_holiday(
        org_id, template_id, payload.model_dump(), current_user.user_id
    )
    return _ok(result, "Holiday created successfully.")


@router.get(
    "/holiday-templates/{template_id}/holidays",
    response_model=SuccessResponse[list[HolidayTemplateItemSchema]],
    summary="List Holidays",
    dependencies=[Depends(require_permission(_HOLIDAY, A.READ))],
)
async def list_holidays(
    template_id: int,
    service: LeaveServiceDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """List non-deleted holidays inside a template."""
    result = await service.list_holidays(org_id, template_id)
    return _ok(result)


@router.patch(
    "/holiday-templates/{template_id}/holidays/{item_id}",
    response_model=SuccessResponse[HolidayTemplateItemSchema],
    summary="Update Holiday",
    dependencies=[Depends(require_permission(_HOLIDAY, A.EDIT))],
)
async def update_holiday(
    template_id: int,
    item_id: int,
    payload: HolidayTemplateItemUpdateRequest,
    service: LeaveServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Update a holiday item inside a template."""
    data = payload.model_dump(exclude_unset=True)
    result = await service.update_holiday(org_id, template_id, item_id, data, current_user.user_id)
    return _ok(result, "Holiday updated successfully.")


@router.delete(
    "/holiday-templates/{template_id}/holidays/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Holiday",
    dependencies=[Depends(require_permission(_HOLIDAY, A.EDIT))],
)
async def delete_holiday(
    template_id: int,
    item_id: int,
    service: LeaveServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
) -> Response:
    """Soft-delete a holiday item from a template (maintains the template's count)."""
    await service.delete_holiday(org_id, template_id, item_id, current_user.user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ===========================================================================
# 7. Holiday Assignment & Calendar — feature key `holiday`
# ===========================================================================


@router.put(
    "/employees/{employee_id}/holiday-template",
    response_model=SuccessResponse[EmployeeHolidayAssignmentSchema],
    summary="Assign Holiday Group to Employee",
    dependencies=[Depends(require_permission(_HOLIDAY, A.EDIT))],
)
async def assign_holiday_group(
    employee_id: int,
    payload: HolidayTemplateAssignRequest,
    service: LeaveServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Assign a holiday group/template to an employee (one template per employee)."""
    result = await service.assign_holiday_group(
        org_id, employee_id, payload.template_id, current_user.user_id
    )
    return _ok(result, "Holiday group assigned successfully.")


@router.get(
    "/holiday-assignments",
    response_model=SuccessResponse[list[EmployeeHolidayAssignmentSchema]],
    summary="List All Employee Holiday Assignments",
    dependencies=[Depends(require_permission(_HOLIDAY, A.READ))],
)
async def list_holiday_assignments(
    service: LeaveServiceDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """List all employee holiday assignments in the organization."""
    result = await service.list_holiday_assignments(org_id)
    return _ok(result)


@router.get(
    "/employees/{employee_id}/holiday-template",
    response_model=SuccessResponse[EmployeeHolidayAssignmentSchema],
    summary="View Employee Holiday Assignment",
    dependencies=[Depends(require_permission(_HOLIDAY, A.READ))],
)
async def get_holiday_assignment(
    employee_id: int,
    service: LeaveServiceDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """View an employee's current holiday template assignment (or null)."""
    result = await service.get_holiday_assignment(org_id, employee_id)
    return _ok(result)


@router.get(
    "/employees/{employee_id}/holidays",
    response_model=SuccessResponse[list[EmployeeHolidayCalendarSchema]],
    summary="Employee Holiday Calendar",
    dependencies=[Depends(require_permission(_HOLIDAY, A.READ))],
)
async def get_employee_holiday_calendar(
    employee_id: int,
    service: LeaveServiceDep,
    org_id: OrgIdDep,
    year: Annotated[int | None, Query(description="Filter by calendar year.")] = None,
    date_from: Annotated[datetime.date | None, Query(description="Range start.")] = None,
    date_to: Annotated[datetime.date | None, Query(description="Range end.")] = None,
) -> dict[str, Any]:
    """Return the holidays from the employee's assigned template within the range."""
    result = await service.get_employee_holiday_calendar(
        org_id, employee_id, year=year, date_from=date_from, date_to=date_to
    )
    return _ok(result)
