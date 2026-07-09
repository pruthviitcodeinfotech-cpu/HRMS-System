"""Employee Management — HTTP routes (thin controllers).

Maps the Employee-Management API Contract (section 7) onto FastAPI endpoints.
Controllers only resolve dependencies, derive the caller's permission/scope flags,
call :class:`~app.modules.employee.service.EmployeeService`, and wrap the result in
the standard success envelope. **No business logic** and no ``try/except`` — the
service raises typed :class:`~app.core.exceptions.base.AppException`s that the
global handlers render into the error envelope.

Authorization: each route declares an RBAC feature-permission guard
(``require_permission``); the authenticated principal supplies the acting user,
tenant (``org_id``), branch data-scope, and salary-visibility. Mounted under the
``/api/v1`` prefix by the version router.

Scope note — ``POST /employees/{id}/device-mapping`` is intentionally **not** served
here. It links a device-local ``device_user_id`` (which has no column in this
module's approved schema) and belongs to the Hardware / Device module (Module 04,
``employee_device_mapping`` bridge + ``employee_enrollment_service``). Implementing
it here would duplicate that module's ownership of device identity, so it stays
deferred; its request/response schemas already exist in
:mod:`app.modules.employee.schemas` for the owning module to reuse.
"""

from __future__ import annotations

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
from app.modules.employee.constants import EmploymentStatus
from app.modules.employee.schemas import (
    EmployeeCreateRequest,
    EmployeeCreateResponse,
    EmployeeDetailSchema,
    EmployeeDocumentCreateRequest,
    EmployeeDocumentSchema,
    EmployeeExitRequest,
    EmployeeListQuery,
    EmployeeListResponse,
    EmployeePhotoUploadRequest,
    EmployeeRehireRequest,
    EmployeeUpdateRequest,
)
from app.modules.employee.service import EmployeeService
from app.shared.schemas.response import SuccessResponse, success_response

router = APIRouter(tags=["Employee Management"])

# Feature-permission keys (contract §4 permission matrix, dotted codes mapped onto
# the project's feature_key × CRUD-action model).
_EMPLOYEE = "employee"  # employee.view / .create / .edit / .exit
_EMPLOYEE_SALARY = "employee_salary"  # employee.salary.view (segregated pay visibility)
_EMPLOYEE_DOCUMENT = "employee_document"  # employee.document.manage


# ---------------------------------------------------------------------------
# Dependencies
# ---------------------------------------------------------------------------


async def get_employee_service(db: Annotated[Any, Depends(get_db)]) -> EmployeeService:
    """Provide an :class:`EmployeeService` bound to the request DB session."""
    return EmployeeService(db)


def get_org_id(current_user: Annotated[CurrentUser, Depends(get_current_active_user)]) -> int:
    """Return the caller's tenant id, or ``400 TENANT_UNRESOLVED`` if absent."""
    if current_user.org_id is None:
        exc = AppException("Organization context is required.", code="TENANT_UNRESOLVED")
        exc.status_code = status.HTTP_400_BAD_REQUEST
        raise exc
    return current_user.org_id


ServiceDep = Annotated[EmployeeService, Depends(get_employee_service)]
CurrentUserDep = Annotated[CurrentUser, Depends(get_current_active_user)]
OrgIdDep = Annotated[int, Depends(get_org_id)]


def _ok(data: Any, message: str = "OK") -> dict[str, Any]:
    return success_response(data=data, message=message, request_id=get_request_id())


def _can_view_salary(current_user: CurrentUser) -> bool:
    """Whether the caller may see/set the segregated salary block (``employee.salary.view``)."""
    return current_user.permissions.has_permission(_EMPLOYEE_SALARY, A.READ)


def _branch_scope(current_user: CurrentUser) -> list[int] | None:
    """Resolve the caller's branch data scope for list queries.

    ``None`` means org-wide access (super admin or an unrestricted role such as HR
    Manager); a populated list confines a Branch Admin to their permitted branches.
    """
    branch_ids = current_user.permissions.branch_ids
    if current_user.is_super_admin or not branch_ids:
        return None
    return list(branch_ids)


# ===========================================================================
# Employees
# ===========================================================================


@router.get(
    "/employees",
    response_model=SuccessResponse[EmployeeListResponse],
    summary="List / Search Employees",
    dependencies=[Depends(require_permission(_EMPLOYEE, A.READ))],
)
async def list_employees(
    service: ServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
    pagination: Annotated[PaginationParams, Depends(pagination_params)],
    branch_id: Annotated[int | None, Query(description="Filter by master branch.")] = None,
    department_id: Annotated[int | None, Query(description="Filter by department.")] = None,
    employee_status: Annotated[
        EmploymentStatus | None, Query(alias="status", description="Filter by employment status.")
    ] = None,
    q: Annotated[str | None, Query(description="Free-text search (name / code / contact).")] = None,
) -> dict[str, Any]:
    """Return a filtered, searched, paginated page of employees (branch-scoped)."""
    query = EmployeeListQuery(
        page=pagination.page,
        page_size=pagination.page_size,
        branch_id=branch_id,
        department_id=department_id,
        status=employee_status,
        q=q,
    )
    result = await service.list_employees(
        org_id=org_id, query=query, branch_scope=_branch_scope(current_user)
    )
    return _ok(result)


@router.post(
    "/employees",
    response_model=SuccessResponse[EmployeeCreateResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create Employee",
    dependencies=[Depends(require_permission(_EMPLOYEE, A.CREATE))],
)
async def create_employee(
    payload: EmployeeCreateRequest,
    service: ServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Onboard an employee (auto-generates code; queues async device enrollment)."""
    result = await service.create_employee(
        org_id=org_id,
        actor_id=current_user.user_id,
        data=payload,
        can_set_salary=_can_view_salary(current_user),
    )
    return _ok(result, "Employee created.")


@router.get(
    "/employees/{employee_id}",
    response_model=SuccessResponse[EmployeeDetailSchema],
    summary="Get Employee",
    dependencies=[Depends(require_permission(_EMPLOYEE, A.READ))],
)
async def get_employee(
    employee_id: int,
    service: ServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Return an employee's full profile; the salary block requires ``employee.salary.view``."""
    result = await service.get_employee(
        org_id=org_id, employee_id=employee_id, include_salary=_can_view_salary(current_user)
    )
    return _ok(result)


@router.put(
    "/employees/{employee_id}",
    response_model=SuccessResponse[EmployeeDetailSchema],
    summary="Update Employee",
    dependencies=[Depends(require_permission(_EMPLOYEE, A.EDIT))],
)
async def update_employee(
    employee_id: int,
    payload: EmployeeUpdateRequest,
    service: ServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Partially update an employee (org reassignment re-validates hierarchy consistency)."""
    result = await service.update_employee(
        org_id=org_id,
        actor_id=current_user.user_id,
        employee_id=employee_id,
        data=payload,
        can_set_salary=_can_view_salary(current_user),
    )
    return _ok(result, "Employee updated.")


@router.post(
    "/employees/{employee_id}/exit",
    response_model=SuccessResponse[EmployeeDetailSchema],
    summary="Exit Employee",
    dependencies=[Depends(require_permission(_EMPLOYEE, A.DELETE))],
)
async def exit_employee(
    employee_id: int,
    payload: EmployeeExitRequest,
    service: ServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Trigger off-boarding (records last working day; raises F&F / de-map cascade)."""
    result = await service.exit_employee(
        org_id=org_id,
        actor_id=current_user.user_id,
        employee_id=employee_id,
        data=payload,
    )
    return _ok(result, "Employee exit recorded.")


@router.post(
    "/employees/{employee_id}/rehire",
    response_model=SuccessResponse[EmployeeDetailSchema],
    summary="Rehire Employee",
    dependencies=[Depends(require_permission(_EMPLOYEE, A.CREATE))],
)
async def rehire_employee(
    employee_id: int,
    payload: EmployeeRehireRequest,
    service: ServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Reactivate a previously exited employee with a new joining date (history preserved)."""
    result = await service.rehire_employee(
        org_id=org_id,
        actor_id=current_user.user_id,
        employee_id=employee_id,
        data=payload,
    )
    return _ok(result, "Employee rehired.")


@router.post(
    "/employees/{employee_id}/documents",
    response_model=SuccessResponse[EmployeeDocumentSchema],
    status_code=status.HTTP_201_CREATED,
    summary="Upload Employee Document",
    dependencies=[Depends(require_permission(_EMPLOYEE_DOCUMENT, A.EDIT))],
)
async def add_employee_document(
    employee_id: int,
    payload: EmployeeDocumentCreateRequest,
    service: ServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Attach a document's metadata to an employee (pre-signed upload pattern; audited)."""
    result = await service.add_document(
        org_id=org_id,
        actor_id=current_user.user_id,
        employee_id=employee_id,
        data=payload,
    )
    return _ok(result, "Document uploaded.")


@router.post(
    "/employees/{employee_id}/photo",
    response_model=SuccessResponse[EmployeeDetailSchema],
    summary="Upload Employee Photo",
    dependencies=[Depends(require_permission(_EMPLOYEE, A.EDIT))],
)
async def set_employee_photo(
    employee_id: int,
    payload: EmployeePhotoUploadRequest,
    service: ServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Store the employee's photo metadata (device photo-push queued by the Hardware module)."""
    result = await service.set_photo(
        org_id=org_id,
        actor_id=current_user.user_id,
        employee_id=employee_id,
        data=payload,
    )
    return _ok(result, "Photo updated.")
