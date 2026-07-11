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

from fastapi import APIRouter, Depends, Query, Response, status

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
    RosterBulkRequest,
    RosterBulkResponse,
    RosterEntrySchema,
    RosterListResponse,
    RosterQuery,
    RosterRangeQuery,
    RosterUpdateRequest,
    RosterUpsertRequest,
    RosterUpsertResult,
    ShiftAssignmentBulkRequest,
    ShiftAssignmentBulkResponse,
    ShiftAssignmentCreateRequest,
    ShiftAssignmentListResponse,
    ShiftAssignmentQuery,
    ShiftAssignmentSchema,
    ShiftAssignmentUpdateRequest,
    ShiftCreateRequest,
    ShiftDayTimingSchema,
    ShiftDayTimingUpdateRequest,
    ShiftDetailSchema,
    ShiftListResponse,
    ShiftResolveQuery,
    ShiftResolveResponse,
    ShiftRotationRequest,
    ShiftRotationResponse,
    ShiftTimingsReplaceRequest,
    ShiftUpdateRequest,
    WeeklyOffListResponse,
    WeeklyOffSchema,
    WeekoffConfigureRequest,
    WeekoffPatchRequest,
)
from app.modules.shift.service import ShiftService
from app.shared.schemas.response import SuccessResponse, success_response

router = APIRouter(tags=["Shift Management"])

# Feature-permission keys per the contract's Permission Matrix (§10):
# `shift` (master + timings), `shift_assignment`, `weekoff`, `roster`.
_SHIFT = "shift"
_SHIFT_ASSIGN = "shift_assignment"
_SHIFT_ROTATION = "shift_rotation"  # rotation generator (outside the §10 matrix)
_WEEKOFF = "weekoff"
_ROSTER = "roster"


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


@router.patch(
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
) -> Response:
    """Deactivate a shift (soft delete); blocked when active assignments reference it."""
    await service.delete_shift(
        org_id=org_id, actor_id=current_user.user_id, shift_id=shift_id
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/shifts/{shift_id}/restore",
    response_model=SuccessResponse[ShiftDetailSchema],
    summary="Restore Shift",
    dependencies=[Depends(require_permission(_SHIFT, A.EDIT))],
)
async def restore_shift(
    shift_id: int, service: ServiceDep, current_user: CurrentUserDep, org_id: OrgIdDep
) -> dict[str, Any]:
    """Restore a soft-deleted shift (contract #6)."""
    result = await service.restore_shift(
        org_id=org_id, actor_id=current_user.user_id, shift_id=shift_id
    )
    return _ok(result, "Shift restored.")


# ===========================================================================
# Shift day timings (contract §5)
# ===========================================================================


@router.get(
    "/shifts/{shift_id}/timings",
    response_model=SuccessResponse[list[ShiftDayTimingSchema]],
    summary="List Shift Timings",
    dependencies=[Depends(require_permission(_SHIFT, A.READ))],
)
async def list_shift_timings(
    shift_id: int, service: ServiceDep, org_id: OrgIdDep
) -> dict[str, Any]:
    """Return a shift's timing rows (contract #7)."""
    return _ok(await service.list_timings(org_id=org_id, shift_id=shift_id))


@router.put(
    "/shifts/{shift_id}/timings",
    response_model=SuccessResponse[list[ShiftDayTimingSchema]],
    summary="Replace Shift Timings",
    dependencies=[Depends(require_permission(_SHIFT, A.EDIT))],
)
async def replace_shift_timings(
    shift_id: int,
    payload: ShiftTimingsReplaceRequest,
    service: ServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Atomically replace the shift's full timing set (contract #8)."""
    result = await service.replace_timings(
        org_id=org_id, actor_id=current_user.user_id, shift_id=shift_id, data=payload
    )
    return _ok(result, "Shift timings replaced.")


@router.patch(
    "/shifts/{shift_id}/timings/{timing_id}",
    response_model=SuccessResponse[ShiftDayTimingSchema],
    summary="Update One Shift Timing",
    dependencies=[Depends(require_permission(_SHIFT, A.EDIT))],
)
async def update_shift_timing(
    shift_id: int,
    timing_id: int,
    payload: ShiftDayTimingUpdateRequest,
    service: ServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Partially update one timing row (contract #9)."""
    result = await service.update_timing(
        org_id=org_id,
        actor_id=current_user.user_id,
        shift_id=shift_id,
        timing_id=timing_id,
        data=payload,
    )
    return _ok(result, "Shift timing updated.")


@router.delete(
    "/shifts/{shift_id}/timings/{timing_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete One Shift Timing",
    dependencies=[Depends(require_permission(_SHIFT, A.EDIT))],
)
async def delete_shift_timing(
    shift_id: int,
    timing_id: int,
    service: ServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
) -> Response:
    """Delete one timing row (contract #10)."""
    await service.delete_timing(
        org_id=org_id, actor_id=current_user.user_id, shift_id=shift_id, timing_id=timing_id
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ===========================================================================
# Shift assignments (contract §7)
# ===========================================================================
# Route ordering: the static POST /shift-assignments/bulk is declared before the
# parameterised /shift-assignments/{assignment_id} routes.


@router.post(
    "/shift-assignments",
    response_model=SuccessResponse[ShiftAssignmentSchema],
    status_code=status.HTTP_201_CREATED,
    summary="Assign Shift to Employee",
    dependencies=[Depends(require_permission(_SHIFT_ASSIGN, A.CREATE))],
)
async def create_shift_assignment(
    payload: ShiftAssignmentCreateRequest,
    service: ServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Assign a shift to an employee (contract #14; ``shift_id`` in the body)."""
    result = await service.assign_shift(
        org_id=org_id, actor_id=current_user.user_id, shift_id=payload.shift_id, data=payload
    )
    return _ok(result, "Shift assigned.")


@router.post(
    "/shift-assignments/bulk",
    response_model=SuccessResponse[ShiftAssignmentBulkResponse],
    summary="Bulk Assign Shift",
    dependencies=[Depends(require_permission(_SHIFT_ASSIGN, A.CREATE))],
)
async def bulk_assign_shift(
    payload: ShiftAssignmentBulkRequest,
    service: ServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Assign one shift to many employees with per-item results (contract #15)."""
    result = await service.bulk_assign_shift(
        org_id=org_id, actor_id=current_user.user_id, data=payload
    )
    return _ok(result, "Bulk assignment processed.")


@router.get(
    "/shift-assignments",
    response_model=SuccessResponse[ShiftAssignmentListResponse],
    summary="List Shift Assignments",
    dependencies=[Depends(require_permission(_SHIFT_ASSIGN, A.READ))],
)
async def list_shift_assignments(
    service: ServiceDep,
    org_id: OrgIdDep,
    pagination: Annotated[PaginationParams, Depends(pagination_params)],
    employee_id: Annotated[int | None, Query(description="Filter by employee.")] = None,
    shift_id: Annotated[int | None, Query(description="Filter by shift.")] = None,
    active_on: Annotated[
        date | None, Query(description="Assignments whose effective range covers this date.")
    ] = None,
    on_date: Annotated[
        date | None, Query(alias="date", description="Resolve the single effective assignment.")
    ] = None,
) -> dict[str, Any]:
    """Filtered, paginated assignment list (contract #16)."""
    query = ShiftAssignmentQuery(
        employee_id=employee_id,
        shift_id=shift_id,
        active_on=active_on,
        on_date=on_date,
        page=pagination.page,
        page_size=pagination.page_size,
    )
    return _ok(await service.list_assignments(org_id=org_id, query=query))


@router.patch(
    "/shift-assignments/{assignment_id}",
    response_model=SuccessResponse[ShiftAssignmentSchema],
    summary="Update Shift Assignment",
    dependencies=[Depends(require_permission(_SHIFT_ASSIGN, A.EDIT))],
)
async def update_shift_assignment(
    assignment_id: int,
    payload: ShiftAssignmentUpdateRequest,
    service: ServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Patch an assignment's shift / effective range (contract #17)."""
    result = await service.update_assignment(
        org_id=org_id,
        actor_id=current_user.user_id,
        assignment_id=assignment_id,
        data=payload,
    )
    return _ok(result, "Assignment updated.")


@router.delete(
    "/shift-assignments/{assignment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove Shift Assignment",
    dependencies=[Depends(require_permission(_SHIFT_ASSIGN, A.DELETE))],
)
async def delete_shift_assignment(
    assignment_id: int, service: ServiceDep, current_user: CurrentUserDep, org_id: OrgIdDep
) -> Response:
    """Hard-delete an assignment (contract #18)."""
    await service.delete_assignment(
        org_id=org_id, actor_id=current_user.user_id, assignment_id=assignment_id
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/employees/{employee_id}/shift-assignments",
    response_model=SuccessResponse[ShiftAssignmentListResponse],
    summary="View Employee Shift Assignments",
    dependencies=[Depends(require_permission(_SHIFT_ASSIGN, A.READ))],
)
async def list_employee_shift_assignments(
    employee_id: int,
    service: ServiceDep,
    org_id: OrgIdDep,
    pagination: Annotated[PaginationParams, Depends(pagination_params)],
    current: Annotated[
        bool, Query(description="Return only the assignment effective today.")
    ] = False,
) -> dict[str, Any]:
    """The employee's assignment history, or only the current one (contract #19)."""
    result = await service.list_employee_assignments(
        org_id=org_id,
        employee_id=employee_id,
        current=current,
        page=pagination.page,
        page_size=pagination.page_size,
    )
    return _ok(result)


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
# Weekly offs (contract §6 — /employees/{employee_id}/weekoffs)
# ===========================================================================


@router.get(
    "/employees/{employee_id}/weekoffs",
    response_model=SuccessResponse[WeeklyOffListResponse],
    summary="View Weekly-Off Configuration",
    dependencies=[Depends(require_permission(_WEEKOFF, A.READ))],
)
async def get_employee_weekoffs(
    employee_id: int,
    service: ServiceDep,
    org_id: OrgIdDep,
    include_history: Annotated[
        bool, Query(description="Include superseded (closed) rows.")
    ] = False,
) -> dict[str, Any]:
    """The employee's current weekly-off configuration (contract #11)."""
    result = await service.list_weekoffs(
        org_id=org_id, employee_id=employee_id, include_history=include_history
    )
    return _ok(result)


@router.put(
    "/employees/{employee_id}/weekoffs",
    response_model=SuccessResponse[WeeklyOffListResponse],
    summary="Configure Weekly Off",
    dependencies=[Depends(require_permission(_WEEKOFF, A.EDIT))],
)
async def configure_employee_weekoffs(
    employee_id: int,
    payload: WeekoffConfigureRequest,
    service: ServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Set/replace the employee's current weekly-off configuration (contract #12)."""
    result = await service.configure_weekoffs(
        org_id=org_id, actor_id=current_user.user_id, employee_id=employee_id, data=payload
    )
    return _ok(result, "Weekly-off configuration updated.")


@router.patch(
    "/employees/{employee_id}/weekoffs/{weekoff_id}",
    response_model=SuccessResponse[WeeklyOffSchema],
    summary="Update One Weekly Off",
    dependencies=[Depends(require_permission(_WEEKOFF, A.EDIT))],
)
async def update_employee_weekoff(
    employee_id: int,
    weekoff_id: int,
    payload: WeekoffPatchRequest,
    service: ServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Patch one weekday's weekly-off rule (contract #13)."""
    result = await service.update_weekoff(
        org_id=org_id,
        actor_id=current_user.user_id,
        employee_id=employee_id,
        weekoff_id=weekoff_id,
        data=payload,
    )
    return _ok(result, "Weekly-off updated.")


# ===========================================================================
# Roster / shift calendar (contract §8)
# ===========================================================================
# Route ordering: the static POST /roster/bulk is declared before the
# parameterised /roster/{roster_id} routes.


@router.get(
    "/roster",
    response_model=SuccessResponse[RosterListResponse],
    summary="View Shift Calendar",
    dependencies=[Depends(require_permission(_ROSTER, A.READ))],
)
async def get_roster(
    service: ServiceDep,
    org_id: OrgIdDep,
    pagination: Annotated[PaginationParams, Depends(pagination_params)],
    date_from: Annotated[date | None, Query(description="Range start (with date_to).")] = None,
    date_to: Annotated[date | None, Query(description="Range end (with date_from).")] = None,
    month: Annotated[str | None, Query(description="Calendar month (YYYY-MM).")] = None,
    branch_id: Annotated[int | None, Query(description="Filter by branch.")] = None,
    department_id: Annotated[
        int | None, Query(alias="dept_id", description="Filter by department.")
    ] = None,
    employee_id: Annotated[int | None, Query(description="Filter by employee.")] = None,
    shift_id: Annotated[int | None, Query(description="Filter by shift.")] = None,
) -> dict[str, Any]:
    """Org shift calendar over a date range or month (contract #20)."""
    query = RosterQuery(
        date_from=date_from,
        date_to=date_to,
        month=month,
        branch_id=branch_id,
        department_id=department_id,
        employee_id=employee_id,
        shift_id=shift_id,
        page=pagination.page,
        page_size=pagination.page_size,
    )
    return _ok(await service.get_roster(org_id=org_id, query=query))


@router.put(
    "/roster",
    response_model=SuccessResponse[RosterUpsertResult],
    summary="Set Roster Entry (upsert)",
    dependencies=[Depends(require_permission(_ROSTER, A.EDIT))],
)
async def set_roster_entry(
    payload: RosterUpsertRequest,
    service: ServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Upsert one roster entry on ``(employee_id, roster_date)`` (contract #22)."""
    result = await service.upsert_roster_entry(
        org_id=org_id, actor_id=current_user.user_id, data=payload
    )
    return _ok(result, "Roster entry created." if result.created else "Roster entry updated.")


@router.post(
    "/roster/bulk",
    response_model=SuccessResponse[RosterBulkResponse],
    summary="Bulk Set Roster",
    dependencies=[Depends(require_permission(_ROSTER, A.EDIT))],
)
async def bulk_set_roster(
    payload: RosterBulkRequest,
    service: ServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Upsert many roster entries with per-item results (contract #23)."""
    result = await service.bulk_set_roster(
        org_id=org_id, actor_id=current_user.user_id, data=payload
    )
    return _ok(result, "Bulk roster processed.")


@router.patch(
    "/roster/{roster_id}",
    response_model=SuccessResponse[RosterEntrySchema],
    summary="Update Roster Entry",
    dependencies=[Depends(require_permission(_ROSTER, A.EDIT))],
)
async def update_roster_entry(
    roster_id: int,
    payload: RosterUpdateRequest,
    service: ServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Patch a roster entry's ``shift_id`` / ``is_week_off`` (contract #24)."""
    result = await service.update_roster_entry(
        org_id=org_id, actor_id=current_user.user_id, roster_id=roster_id, data=payload
    )
    return _ok(result, "Roster entry updated.")


@router.delete(
    "/roster/{roster_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Roster Entry",
    dependencies=[Depends(require_permission(_ROSTER, A.DELETE))],
)
async def delete_roster_entry(
    roster_id: int, service: ServiceDep, current_user: CurrentUserDep, org_id: OrgIdDep
) -> Response:
    """Hard-delete a roster entry (contract #25)."""
    await service.delete_roster_entry(
        org_id=org_id, actor_id=current_user.user_id, roster_id=roster_id
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/employees/{employee_id}/roster",
    response_model=SuccessResponse[RosterListResponse],
    summary="Employee Shift Calendar",
    dependencies=[Depends(require_permission(_ROSTER, A.READ))],
)
async def get_employee_roster(
    employee_id: int,
    service: ServiceDep,
    org_id: OrgIdDep,
    date_from: Annotated[date | None, Query(description="Range start (with date_to).")] = None,
    date_to: Annotated[date | None, Query(description="Range end (with date_from).")] = None,
    month: Annotated[str | None, Query(description="Calendar month (YYYY-MM).")] = None,
) -> dict[str, Any]:
    """One employee's shift calendar over a date range or month (contract #21)."""
    query = RosterRangeQuery(date_from=date_from, date_to=date_to, month=month)
    return _ok(
        await service.get_employee_roster(org_id=org_id, employee_id=employee_id, query=query)
    )
