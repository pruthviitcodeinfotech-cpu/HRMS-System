"""Shift Management — HTTP routes (thin controllers).

Maps the Shift-Management API Contract (section 10) onto FastAPI endpoints.
Controllers only resolve dependencies, build query DTOs, call
:class:`~app.modules.shift.service.ShiftService`, and wrap the result in the
standard success envelope. **No business logic** and no ``try/except`` — the service
raises typed :class:`~app.core.exceptions.base.AppException`s and manual query-DTO
construction raises pydantic ``ValidationError``; both are rendered as the standard
error envelope by the global handlers.

Authorization: each route declares an RBAC feature-permission guard
(``require_permission``); the authenticated principal supplies the acting user and
tenant (``org_id``). Mounted under the ``/api/v1`` prefix by the version router.

Route ordering note: the static ``GET /shifts/resolve`` is declared before the
parameterised ``GET /shifts/{shift_id}`` so it is matched first.
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
from app.modules.shift.constants import ShiftType
from app.modules.shift.schemas import (
    ShiftAssignmentListResponse,
    ShiftAssignmentQuery,
    ShiftAssignmentSchema,
    ShiftAssignRequest,
    ShiftCreateRequest,
    ShiftDetailSchema,
    ShiftListResponse,
    ShiftResolveQuery,
    ShiftResolveResponse,
    ShiftRotationRequest,
    ShiftRotationResponse,
    ShiftUpdateRequest,
    WeeklyOffListResponse,
    WeeklyOffQuery,
    WeeklyOffSchema,
    WeeklyOffUpdateRequest,
)
from app.modules.shift.service import ShiftService
from app.shared.schemas.response import SuccessResponse, success_response

router = APIRouter(tags=["Shift Management"])

# Feature-permission keys (contract §10 dotted codes mapped onto the project's
# feature_key × CRUD-action model).
_SHIFT = "shift"  # shift.view (read) / shift.manage (create/edit/delete)
_SHIFT_ASSIGN = "shift_assignment"  # shift.assign
_SHIFT_ROTATION = "shift_rotation"  # shift.rotation.manage
_WEEKLY_OFF = "weekly_off"  # weeklyoff.manage


# ---------------------------------------------------------------------------
# Dependencies
# ---------------------------------------------------------------------------


async def get_shift_service(db: Annotated[Any, Depends(get_db)]) -> ShiftService:
    """Provide a :class:`ShiftService` bound to the request DB session."""
    return ShiftService(db)


def get_org_id(current_user: Annotated[CurrentUser, Depends(get_current_active_user)]) -> int:
    """Return the caller's tenant id, or ``400 TENANT_UNRESOLVED`` if absent."""
    if current_user.org_id is None:
        exc = AppException("Organization context is required.", code="TENANT_UNRESOLVED")
        exc.status_code = status.HTTP_400_BAD_REQUEST
        raise exc
    return current_user.org_id


ServiceDep = Annotated[ShiftService, Depends(get_shift_service)]
CurrentUserDep = Annotated[CurrentUser, Depends(get_current_active_user)]
OrgIdDep = Annotated[int, Depends(get_org_id)]


def _ok(data: Any, message: str = "OK") -> dict[str, Any]:
    return success_response(data=data, message=message, request_id=get_request_id())


# ===========================================================================
# Shifts
# ===========================================================================


@router.get(
    "/shifts",
    response_model=SuccessResponse[ShiftListResponse],
    summary="List / Search Shifts",
    dependencies=[Depends(require_permission(_SHIFT, A.READ))],
)
async def list_shifts(
    service: ServiceDep,
    org_id: OrgIdDep,
    pagination: Annotated[PaginationParams, Depends(pagination_params)],
    q: Annotated[str | None, Query(description="Free-text search on shift name.")] = None,
    shift_type: Annotated[ShiftType | None, Query(description="Filter by shift type.")] = None,
    is_default: Annotated[bool | None, Query(description="Filter by default flag.")] = None,
    is_open_shift: Annotated[bool | None, Query(description="Filter by open-shift flag.")] = None,
) -> dict[str, Any]:
    """Return a filtered, searched, paginated list of shift definitions."""
    result = await service.list_shifts(
        org_id=org_id,
        search=q,
        shift_type=shift_type.value if shift_type is not None else None,
        is_default=is_default,
        is_open_shift=is_open_shift,
        page=pagination.page,
        page_size=pagination.page_size,
    )
    return _ok(result)


@router.post(
    "/shifts",
    response_model=SuccessResponse[ShiftDetailSchema],
    status_code=status.HTTP_201_CREATED,
    summary="Create Shift",
    dependencies=[Depends(require_permission(_SHIFT, A.CREATE))],
)
async def create_shift(
    payload: ShiftCreateRequest,
    service: ServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Define a shift and its day timings."""
    result = await service.create_shift(
        org_id=org_id, actor_id=current_user.user_id, data=payload
    )
    return _ok(result, "Shift created.")


@router.get(
    "/shifts/resolve",
    response_model=SuccessResponse[ShiftResolveResponse],
    summary="Resolve Shift for a Date",
    dependencies=[Depends(require_permission(_SHIFT, A.READ))],
)
async def resolve_shift(
    service: ServiceDep,
    org_id: OrgIdDep,
    employee_id: Annotated[int, Query(description="Employee to resolve the shift for.")],
    on_date: Annotated[date, Query(alias="date", description="Date to resolve.")],
) -> dict[str, Any]:
    """Resolve the effective shift + weekly-off / working-day flags for an employee on a date."""
    query = ShiftResolveQuery(employee_id=employee_id, on_date=on_date)
    return _ok(await service.resolve_shift(org_id=org_id, query=query))


@router.get(
    "/shifts/{shift_id}",
    response_model=SuccessResponse[ShiftDetailSchema],
    summary="Get Shift",
    dependencies=[Depends(require_permission(_SHIFT, A.READ))],
)
async def get_shift(shift_id: int, service: ServiceDep, org_id: OrgIdDep) -> dict[str, Any]:
    """Return a shift with its day timings."""
    return _ok(await service.get_shift(org_id=org_id, shift_id=shift_id))


@router.put(
    "/shifts/{shift_id}",
    response_model=SuccessResponse[ShiftDetailSchema],
    summary="Update Shift",
    dependencies=[Depends(require_permission(_SHIFT, A.EDIT))],
)
async def update_shift(
    shift_id: int,
    payload: ShiftUpdateRequest,
    service: ServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Partially update a shift (supplying ``day_timings`` replaces them wholesale)."""
    result = await service.update_shift(
        org_id=org_id, actor_id=current_user.user_id, shift_id=shift_id, data=payload
    )
    return _ok(result, "Shift updated.")


@router.delete(
    "/shifts/{shift_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Shift (deactivate)",
    dependencies=[Depends(require_permission(_SHIFT, A.DELETE))],
)
async def delete_shift(
    shift_id: int, service: ServiceDep, current_user: CurrentUserDep, org_id: OrgIdDep
) -> None:
    """Deactivate a shift (soft delete); blocked when active assignments reference it."""
    await service.delete_shift(
        org_id=org_id, actor_id=current_user.user_id, shift_id=shift_id
    )


@router.post(
    "/shifts/{shift_id}/assign",
    response_model=SuccessResponse[ShiftAssignmentSchema],
    status_code=status.HTTP_201_CREATED,
    summary="Assign Shift to Employee",
    dependencies=[Depends(require_permission(_SHIFT_ASSIGN, A.CREATE))],
)
async def assign_shift(
    shift_id: int,
    payload: ShiftAssignRequest,
    service: ServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Assign a shift to an employee (supersedes the prior open assignment)."""
    result = await service.assign_shift(
        org_id=org_id, actor_id=current_user.user_id, shift_id=shift_id, data=payload
    )
    return _ok(result, "Shift assigned.")


# ===========================================================================
# Shift assignments
# ===========================================================================


@router.get(
    "/shift-assignments",
    response_model=SuccessResponse[ShiftAssignmentListResponse],
    summary="List Shift Assignments",
    dependencies=[Depends(require_permission(_SHIFT, A.READ))],
)
async def list_shift_assignments(
    service: ServiceDep,
    org_id: OrgIdDep,
    pagination: Annotated[PaginationParams, Depends(pagination_params)],
    employee_id: Annotated[int | None, Query(description="Filter by employee.")] = None,
    on_date: Annotated[
        date | None, Query(alias="date", description="Resolve the single effective assignment.")
    ] = None,
) -> dict[str, Any]:
    """Return an employee's assignment timeline, or the single shift resolved for a date."""
    query = ShiftAssignmentQuery(
        employee_id=employee_id,
        on_date=on_date,
        page=pagination.page,
        page_size=pagination.page_size,
    )
    return _ok(await service.list_assignments(org_id=org_id, query=query))


# ===========================================================================
# Shift rotations
# ===========================================================================


@router.post(
    "/shift-rotations",
    response_model=SuccessResponse[ShiftRotationResponse],
    status_code=status.HTTP_202_ACCEPTED,
    summary="Generate Shift Rotation",
    dependencies=[Depends(require_permission(_SHIFT_ROTATION, A.CREATE))],
)
async def generate_shift_rotation(
    payload: ShiftRotationRequest,
    service: ServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Generate a rotating roster over the horizon and materialise roster entries."""
    result = await service.generate_rotation(
        org_id=org_id, actor_id=current_user.user_id, data=payload
    )
    return _ok(result, "Rotation generated.")


# ===========================================================================
# Weekly offs
# ===========================================================================


@router.get(
    "/weekly-offs",
    response_model=SuccessResponse[WeeklyOffListResponse],
    summary="Get Weekly-Off Configuration",
    dependencies=[Depends(require_permission(_SHIFT, A.READ))],
)
async def get_weekly_offs(
    service: ServiceDep,
    org_id: OrgIdDep,
    employee_id: Annotated[int | None, Query(description="Employee scope.")] = None,
    department_id: Annotated[int | None, Query(description="Department scope.")] = None,
) -> dict[str, Any]:
    """Return the active weekly-off configuration for an employee or a department."""
    query = WeeklyOffQuery(employee_id=employee_id, department_id=department_id)
    return _ok(await service.get_weekly_offs(org_id=org_id, query=query))


@router.put(
    "/weekly-offs",
    response_model=SuccessResponse[WeeklyOffSchema],
    summary="Set Weekly-Off Configuration",
    dependencies=[Depends(require_permission(_WEEKLY_OFF, A.EDIT))],
)
async def set_weekly_off(
    payload: WeeklyOffUpdateRequest,
    service: ServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Set a weekday's week-off configuration for an employee or a whole department."""
    result = await service.set_weekly_off(
        org_id=org_id, actor_id=current_user.user_id, data=payload
    )
    return _ok(result, "Weekly-off updated.")
