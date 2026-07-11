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

from datetime import date
from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status
from fastapi.responses import FileResponse, Response

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
from app.modules.employee.constants import DocumentType, EmploymentStatus
from app.modules.employee.schemas import (
    EmployeeBankDetailCreateRequest,
    EmployeeBankDetailSchema,
    EmployeeBankDetailUpdateRequest,
    EmployeeCreateRequest,
    EmployeeCreateResponse,
    EmployeeDetailSchema,
    EmployeeDocumentCreateRequest,
    EmployeeDocumentSchema,
    EmployeeEmergencyContactCreateRequest,
    EmployeeEmergencyContactSchema,
    EmployeeEmergencyContactUpdateRequest,
    EmployeeExitRequest,
    EmployeeListQuery,
    EmployeeListResponse,
    EmployeePhotoUploadRequest,
    EmployeePromoteRequest,
    EmployeeReferenceCreateRequest,
    EmployeeReferenceSchema,
    EmployeeReferenceUpdateRequest,
    EmployeeRehireRequest,
    EmployeeStatusChangeRequest,
    EmployeeStatusHistorySchema,
    EmployeeTagCreateRequest,
    EmployeeTagSchema,
    EmployeeTerminateRequest,
    EmployeeTransferRequest,
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


def _can_view_bank_details(current_user: CurrentUser) -> bool:
    """Whether the caller may see bank details (account numbers / IFSC codes).

    Same gate as the standalone ``GET /employees/{id}/bank-details`` route
    (``employee:read`` **and** ``employee_salary:read``). The detail projection embeds
    the same rows, so it must honour the same permission — otherwise plain
    ``employee:read`` would read every colleague's account number. Missing the
    permission omits the section; it never turns the whole employee read into a 403.
    """
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
    """Return an employee's full profile.

    The ``salary`` and ``bank_details`` sections are sensitive: both require
    ``employee_salary:read``. A caller with only ``employee:read`` still gets the
    employee — those two sections are simply omitted.
    """
    result = await service.get_employee(
        org_id=org_id,
        employee_id=employee_id,
        include_salary=_can_view_salary(current_user),
        include_bank_details=_can_view_bank_details(current_user),
    )
    return _ok(result)


@router.patch(
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


# ===========================================================================
# Status lifecycle (#29–#31) and org moves (#32–#33)
# ===========================================================================


@router.post(
    "/employees/{employee_id}/activate",
    response_model=SuccessResponse[EmployeeDetailSchema],
    summary="Activate Employee",
    dependencies=[Depends(require_permission(_EMPLOYEE, A.EDIT))],
)
async def activate_employee(
    employee_id: int,
    service: ServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
    payload: EmployeeStatusChangeRequest | None = None,
) -> dict[str, Any]:
    """Set employment status to ``active`` and append the status-history row."""
    data = payload or EmployeeStatusChangeRequest()
    result = await service.activate_employee(
        org_id=org_id,
        actor_id=current_user.user_id,
        employee_id=employee_id,
        reason=data.reason,
        effective_date=data.effective_date,
    )
    return _ok(result, "Employee activated.")


@router.post(
    "/employees/{employee_id}/deactivate",
    response_model=SuccessResponse[EmployeeDetailSchema],
    summary="Deactivate Employee",
    dependencies=[Depends(require_permission(_EMPLOYEE, A.EDIT))],
)
async def deactivate_employee(
    employee_id: int,
    service: ServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
    payload: EmployeeStatusChangeRequest | None = None,
) -> dict[str, Any]:
    """Set employment status to ``inactive`` and append the status-history row."""
    data = payload or EmployeeStatusChangeRequest()
    result = await service.deactivate_employee(
        org_id=org_id,
        actor_id=current_user.user_id,
        employee_id=employee_id,
        reason=data.reason,
        effective_date=data.effective_date,
    )
    return _ok(result, "Employee deactivated.")


@router.post(
    "/employees/{employee_id}/terminate",
    response_model=SuccessResponse[EmployeeDetailSchema],
    summary="Terminate Employee",
    dependencies=[Depends(require_permission(_EMPLOYEE, A.EDIT))],
)
async def terminate_employee(
    employee_id: int,
    payload: EmployeeTerminateRequest,
    service: ServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Terminate an employee (terminal): sets ``date_of_leaving`` and appends history."""
    result = await service.terminate_employee(
        org_id=org_id,
        actor_id=current_user.user_id,
        employee_id=employee_id,
        data=payload,
    )
    return _ok(result, "Employee terminated.")


@router.post(
    "/employees/{employee_id}/transfer",
    response_model=SuccessResponse[EmployeeDetailSchema],
    summary="Transfer Employee",
    dependencies=[Depends(require_permission(_EMPLOYEE, A.EDIT))],
)
async def transfer_employee(
    employee_id: int,
    payload: EmployeeTransferRequest,
    service: ServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Move an employee to another branch and/or department (context audited only)."""
    result = await service.transfer_employee(
        org_id=org_id,
        actor_id=current_user.user_id,
        employee_id=employee_id,
        data=payload,
    )
    return _ok(result, "Employee transferred.")


@router.post(
    "/employees/{employee_id}/promote",
    response_model=SuccessResponse[EmployeeDetailSchema],
    summary="Promote Employee",
    dependencies=[Depends(require_permission(_EMPLOYEE, A.EDIT))],
)
async def promote_employee(
    employee_id: int,
    payload: EmployeePromoteRequest,
    service: ServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Change the designation (salary revision gated by ``employee_salary`` read)."""
    result = await service.promote_employee(
        org_id=org_id,
        actor_id=current_user.user_id,
        employee_id=employee_id,
        data=payload,
        can_set_salary=_can_view_salary(current_user),
    )
    return _ok(result, "Employee promoted.")


@router.post(
    "/employees/{employee_id}/exit",
    response_model=SuccessResponse[EmployeeDetailSchema],
    summary="Exit Employee (deprecated — use /terminate)",
    dependencies=[Depends(require_permission(_EMPLOYEE, A.DELETE))],
    deprecated=True,
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
    service: ServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
    document_type: Annotated[DocumentType, Form(description="Document category.")],
    file: Annotated[UploadFile, File(description="The document binary (pdf/png/jpg/jpeg).")],
    expires_at: Annotated[
        date | None, Form(description="Optional expiry for ID / contract documents.")
    ] = None,
) -> dict[str, Any]:
    """Upload a document (``multipart/form-data``; contract #34; audited).

    The server validates size / extension / content type and generates the storage key —
    no client-supplied path is accepted. The response is metadata only (no filesystem
    path); the bytes are fetched from the download route.
    """
    payload = EmployeeDocumentCreateRequest(document_type=document_type, expires_at=expires_at)
    result = await service.add_document(
        org_id=org_id,
        actor_id=current_user.user_id,
        employee_id=employee_id,
        data=payload,
        upload=file,
    )
    return _ok(result, "Document uploaded.")


@router.get(
    "/employees/{employee_id}/documents",
    response_model=SuccessResponse[list[EmployeeDocumentSchema]],
    summary="List Employee Documents",
    dependencies=[Depends(require_permission(_EMPLOYEE, A.READ))],
)
async def list_employee_documents(
    employee_id: int,
    service: ServiceDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Return the employee's non-deleted document metadata."""
    result = await service.list_documents(org_id=org_id, employee_id=employee_id)
    return _ok(result)


@router.get(
    "/employees/{employee_id}/documents/{document_id}",
    response_class=FileResponse,
    summary="Download Employee Document",
    dependencies=[Depends(require_permission(_EMPLOYEE, A.READ))],
)
async def get_employee_document(
    employee_id: int,
    document_id: int,
    service: ServiceDep,
    org_id: OrgIdDep,
) -> FileResponse:
    """Stream the stored document (contract #36).

    The file is served from the storage root by its server-generated key — the client
    never sees or supplies a filesystem path.
    """
    download = await service.open_document(
        org_id=org_id, employee_id=employee_id, document_id=document_id
    )
    return FileResponse(
        path=download.path,
        media_type=download.content_type,
        filename=download.filename,
    )


@router.delete(
    "/employees/{employee_id}/documents/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Employee Document",
    dependencies=[Depends(require_permission(_EMPLOYEE, A.EDIT))],
)
async def delete_employee_document(
    employee_id: int,
    document_id: int,
    service: ServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
) -> Response:
    """Soft-delete a document (``is_deleted=true``)."""
    await service.delete_document(
        org_id=org_id,
        actor_id=current_user.user_id,
        employee_id=employee_id,
        document_id=document_id,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


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


# ===========================================================================
# Bank details (#38–#41) — SENSITIVE: reads also require employee_salary read
# ===========================================================================


@router.get(
    "/employees/{employee_id}/bank-details",
    response_model=SuccessResponse[list[EmployeeBankDetailSchema]],
    summary="List Bank Details",
    dependencies=[
        Depends(require_permission(_EMPLOYEE, A.READ)),
        Depends(require_permission(_EMPLOYEE_SALARY, A.READ)),
    ],
)
async def list_bank_details(
    employee_id: int,
    service: ServiceDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Return the employee's non-deleted bank details (account numbers are sensitive)."""
    result = await service.list_bank_details(org_id=org_id, employee_id=employee_id)
    return _ok(result)


@router.post(
    "/employees/{employee_id}/bank-details",
    response_model=SuccessResponse[EmployeeBankDetailSchema],
    status_code=status.HTTP_201_CREATED,
    summary="Add Bank Detail",
    dependencies=[Depends(require_permission(_EMPLOYEE, A.EDIT))],
)
async def add_bank_detail(
    employee_id: int,
    payload: EmployeeBankDetailCreateRequest,
    service: ServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Add a bank detail (a primary row demotes any existing primary)."""
    result = await service.add_bank_detail(
        org_id=org_id,
        actor_id=current_user.user_id,
        employee_id=employee_id,
        data=payload,
    )
    return _ok(result, "Bank detail added.")


@router.patch(
    "/employees/{employee_id}/bank-details/{bank_detail_id}",
    response_model=SuccessResponse[EmployeeBankDetailSchema],
    summary="Update Bank Detail",
    dependencies=[Depends(require_permission(_EMPLOYEE, A.EDIT))],
)
async def update_bank_detail(
    employee_id: int,
    bank_detail_id: int,
    payload: EmployeeBankDetailUpdateRequest,
    service: ServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Partially update a bank detail (primary uniqueness re-enforced)."""
    result = await service.update_bank_detail(
        org_id=org_id,
        actor_id=current_user.user_id,
        employee_id=employee_id,
        bank_detail_id=bank_detail_id,
        data=payload,
    )
    return _ok(result, "Bank detail updated.")


@router.delete(
    "/employees/{employee_id}/bank-details/{bank_detail_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Bank Detail",
    dependencies=[Depends(require_permission(_EMPLOYEE, A.EDIT))],
)
async def delete_bank_detail(
    employee_id: int,
    bank_detail_id: int,
    service: ServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
) -> Response:
    """Soft-delete a bank detail (``is_deleted=true``)."""
    await service.delete_bank_detail(
        org_id=org_id,
        actor_id=current_user.user_id,
        employee_id=employee_id,
        bank_detail_id=bank_detail_id,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ===========================================================================
# Emergency contacts (#42–#45)
# ===========================================================================


@router.get(
    "/employees/{employee_id}/emergency-contacts",
    response_model=SuccessResponse[list[EmployeeEmergencyContactSchema]],
    summary="List Emergency Contacts",
    dependencies=[Depends(require_permission(_EMPLOYEE, A.READ))],
)
async def list_emergency_contacts(
    employee_id: int,
    service: ServiceDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Return the employee's non-deleted emergency contacts."""
    result = await service.list_emergency_contacts(org_id=org_id, employee_id=employee_id)
    return _ok(result)


@router.post(
    "/employees/{employee_id}/emergency-contacts",
    response_model=SuccessResponse[EmployeeEmergencyContactSchema],
    status_code=status.HTTP_201_CREATED,
    summary="Add Emergency Contact",
    dependencies=[Depends(require_permission(_EMPLOYEE, A.EDIT))],
)
async def add_emergency_contact(
    employee_id: int,
    payload: EmployeeEmergencyContactCreateRequest,
    service: ServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Add an emergency contact for the employee."""
    result = await service.add_emergency_contact(
        org_id=org_id,
        actor_id=current_user.user_id,
        employee_id=employee_id,
        data=payload,
    )
    return _ok(result, "Emergency contact added.")


@router.patch(
    "/employees/{employee_id}/emergency-contacts/{emergency_contact_id}",
    response_model=SuccessResponse[EmployeeEmergencyContactSchema],
    summary="Update Emergency Contact",
    dependencies=[Depends(require_permission(_EMPLOYEE, A.EDIT))],
)
async def update_emergency_contact(
    employee_id: int,
    emergency_contact_id: int,
    payload: EmployeeEmergencyContactUpdateRequest,
    service: ServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Partially update an emergency contact."""
    result = await service.update_emergency_contact(
        org_id=org_id,
        actor_id=current_user.user_id,
        employee_id=employee_id,
        emergency_contact_id=emergency_contact_id,
        data=payload,
    )
    return _ok(result, "Emergency contact updated.")


@router.delete(
    "/employees/{employee_id}/emergency-contacts/{emergency_contact_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Emergency Contact",
    dependencies=[Depends(require_permission(_EMPLOYEE, A.EDIT))],
)
async def delete_emergency_contact(
    employee_id: int,
    emergency_contact_id: int,
    service: ServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
) -> Response:
    """Soft-delete an emergency contact (``is_deleted=true``)."""
    await service.delete_emergency_contact(
        org_id=org_id,
        actor_id=current_user.user_id,
        employee_id=employee_id,
        emergency_contact_id=emergency_contact_id,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ===========================================================================
# References (#46–#49)
# ===========================================================================


@router.get(
    "/employees/{employee_id}/references",
    response_model=SuccessResponse[list[EmployeeReferenceSchema]],
    summary="List References",
    dependencies=[Depends(require_permission(_EMPLOYEE, A.READ))],
)
async def list_references(
    employee_id: int,
    service: ServiceDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Return the employee's non-deleted references (ordered by ``sort_order``)."""
    result = await service.list_references(org_id=org_id, employee_id=employee_id)
    return _ok(result)


@router.post(
    "/employees/{employee_id}/references",
    response_model=SuccessResponse[EmployeeReferenceSchema],
    status_code=status.HTTP_201_CREATED,
    summary="Add Reference",
    dependencies=[Depends(require_permission(_EMPLOYEE, A.EDIT))],
)
async def add_reference(
    employee_id: int,
    payload: EmployeeReferenceCreateRequest,
    service: ServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Add a reference for the employee."""
    result = await service.add_reference(
        org_id=org_id,
        actor_id=current_user.user_id,
        employee_id=employee_id,
        data=payload,
    )
    return _ok(result, "Reference added.")


@router.patch(
    "/employees/{employee_id}/references/{reference_id}",
    response_model=SuccessResponse[EmployeeReferenceSchema],
    summary="Update Reference",
    dependencies=[Depends(require_permission(_EMPLOYEE, A.EDIT))],
)
async def update_reference(
    employee_id: int,
    reference_id: int,
    payload: EmployeeReferenceUpdateRequest,
    service: ServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Partially update a reference."""
    result = await service.update_reference(
        org_id=org_id,
        actor_id=current_user.user_id,
        employee_id=employee_id,
        reference_id=reference_id,
        data=payload,
    )
    return _ok(result, "Reference updated.")


@router.delete(
    "/employees/{employee_id}/references/{reference_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Reference",
    dependencies=[Depends(require_permission(_EMPLOYEE, A.EDIT))],
)
async def delete_reference(
    employee_id: int,
    reference_id: int,
    service: ServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
) -> Response:
    """Soft-delete a reference (``is_deleted=true``)."""
    await service.delete_reference(
        org_id=org_id,
        actor_id=current_user.user_id,
        employee_id=employee_id,
        reference_id=reference_id,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ===========================================================================
# Tags (#50–#52) — hard-deleted (no is_deleted column)
# ===========================================================================


@router.get(
    "/employees/{employee_id}/tags",
    response_model=SuccessResponse[list[EmployeeTagSchema]],
    summary="List Tags",
    dependencies=[Depends(require_permission(_EMPLOYEE, A.READ))],
)
async def list_tags(
    employee_id: int,
    service: ServiceDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Return the employee's tags."""
    result = await service.list_tags(org_id=org_id, employee_id=employee_id)
    return _ok(result)


@router.post(
    "/employees/{employee_id}/tags",
    response_model=SuccessResponse[EmployeeTagSchema],
    status_code=status.HTTP_201_CREATED,
    summary="Add Tag",
    dependencies=[Depends(require_permission(_EMPLOYEE, A.EDIT))],
)
async def add_tag(
    employee_id: int,
    payload: EmployeeTagCreateRequest,
    service: ServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Add a tag to the employee."""
    result = await service.add_tag(
        org_id=org_id,
        actor_id=current_user.user_id,
        employee_id=employee_id,
        data=payload,
    )
    return _ok(result, "Tag added.")


@router.delete(
    "/employees/{employee_id}/tags/{tag_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Tag",
    dependencies=[Depends(require_permission(_EMPLOYEE, A.EDIT))],
)
async def delete_tag(
    employee_id: int,
    tag_id: int,
    service: ServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
) -> Response:
    """Hard-delete a tag (``employee_tags`` has no soft-delete column)."""
    await service.delete_tag(
        org_id=org_id,
        actor_id=current_user.user_id,
        employee_id=employee_id,
        tag_id=tag_id,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ===========================================================================
# Status history (#53) — read-only, system-maintained
# ===========================================================================


@router.get(
    "/employees/{employee_id}/status-history",
    response_model=SuccessResponse[list[EmployeeStatusHistorySchema]],
    summary="List Status History",
    dependencies=[Depends(require_permission(_EMPLOYEE, A.READ))],
)
async def list_status_history(
    employee_id: int,
    service: ServiceDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Return the employee's status transitions in chronological order."""
    result = await service.list_status_history(org_id=org_id, employee_id=employee_id)
    return _ok(result)
