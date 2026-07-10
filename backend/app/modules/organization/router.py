"""Organization / Branch / Department / Designation — HTTP routes (thin controllers).

Maps API Contract §4 (Organization, super-admin) and §5 (Branch / Department /
Designation, tenant-scoped) onto FastAPI endpoints. Controllers only resolve
dependencies, build query schemas, call the services, and wrap the result in the
standard success envelope — no business logic lives here.
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, status

from app.core.constants.enums import PermissionAction as A
from app.core.dependencies.auth import require_permission
from app.core.exceptions.base import AuthorizationException
from app.core.middleware.request_context import get_request_id
from app.modules.organization.constants import (
    BRANCH_FEATURE,
    DEPARTMENT_FEATURE,
    DESIGNATION_FEATURE,
    ORGANIZATION_FEATURE,
)
from app.modules.organization.dependencies import (
    BranchServiceDep,
    CurrentUserDep,
    DepartmentServiceDep,
    DesignationServiceDep,
    OrganizationServiceDep,
    OrgIdDep,
    SuperAdminDep,
)
from app.modules.organization.schemas import (
    BranchCreateRequest,
    BranchListResponse,
    BranchSchema,
    BranchSearchQuery,
    BranchUpdateRequest,
    DepartmentCreateRequest,
    DepartmentListResponse,
    DepartmentSchema,
    DepartmentSearchQuery,
    DepartmentUpdateRequest,
    DesignationCreateRequest,
    DesignationListResponse,
    DesignationSchema,
    DesignationSearchQuery,
    DesignationUpdateRequest,
    OrganizationCreateRequest,
    OrganizationListResponse,
    OrganizationSchema,
    OrganizationSearchQuery,
    OrganizationUpdateRequest,
)
from app.shared.schemas.response import SuccessResponse, success_response

router = APIRouter(tags=["Organization Management"])


def _ok(data: Any, message: str = "OK") -> dict[str, Any]:
    """Wrap controller response data in the standard SuccessResponse envelope."""
    return success_response(data=data, message=message, request_id=get_request_id())


def _branch_scope(current_user: CurrentUserDep) -> list[int] | None:
    """Resolve the caller's branch data scope. ``None`` means unrestricted access."""
    branch_ids = current_user.permissions.branch_ids
    if current_user.is_super_admin or not branch_ids:
        return None
    return list(branch_ids)


def _assert_own_org_or_super_admin(current_user: CurrentUserDep, org_id: int) -> None:
    """Tenant admins may only touch their own org; super-admins may touch any."""
    if current_user.is_super_admin:
        return
    if current_user.org_id != org_id:
        raise AuthorizationException("You may only access your own organization.")


# ===========================================================================
# 1-6. Organization Management (§4) — platform / super-admin
# ===========================================================================


@router.post(
    "/organizations",
    response_model=SuccessResponse[OrganizationSchema],
    status_code=status.HTTP_201_CREATED,
    summary="Create Organization",
    dependencies=[Depends(require_permission(ORGANIZATION_FEATURE, A.CREATE))],
)
async def create_organization(
    payload: OrganizationCreateRequest,
    service: OrganizationServiceDep,
    current_user: SuperAdminDep,
) -> dict[str, Any]:
    """Provision a new organization (super-admin only)."""
    result = await service.create_organization(actor_id=current_user.user_id, data=payload)
    return _ok(result, "Organization created successfully.")


@router.get(
    "/organizations",
    response_model=SuccessResponse[OrganizationListResponse],
    summary="List Organizations",
    dependencies=[Depends(require_permission(ORGANIZATION_FEATURE, A.READ))],
)
async def list_organizations(
    service: OrganizationServiceDep,
    current_user: SuperAdminDep,
    page: Annotated[int, Query(ge=1, description="1-based page number.")] = 1,
    page_size: Annotated[int, Query(ge=1, le=200, description="Items per page.")] = 25,
    search: Annotated[str | None, Query(description="Search by code or name.")] = None,
    is_active: Annotated[bool | None, Query(description="Filter by active flag.")] = None,
    include_deleted: Annotated[bool, Query(description="Include soft-deleted rows.")] = False,
    sort_by: Annotated[
        str | None, Query(description="Sort field: org_code|org_name|created_at.")
    ] = None,
    sort_order: Annotated[str | None, Query(description="Sort order: asc, desc.")] = None,
) -> dict[str, Any]:
    """List all organizations (super-admin only)."""
    query = OrganizationSearchQuery(
        page=page,
        page_size=page_size,
        search=search,
        is_active=is_active,
        include_deleted=include_deleted,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    result = await service.list_organizations(query=query)
    return _ok(result)


@router.get(
    "/organizations/{org_id}",
    response_model=SuccessResponse[OrganizationSchema],
    summary="Get Organization",
    dependencies=[Depends(require_permission(ORGANIZATION_FEATURE, A.READ))],
)
async def get_organization(
    org_id: int,
    service: OrganizationServiceDep,
    current_user: CurrentUserDep,
) -> dict[str, Any]:
    """Retrieve an organization (own org, or any for super-admin)."""
    _assert_own_org_or_super_admin(current_user, org_id)
    result = await service.get_organization(org_id=org_id)
    return _ok(result)


@router.patch(
    "/organizations/{org_id}",
    response_model=SuccessResponse[OrganizationSchema],
    summary="Update Organization",
    dependencies=[Depends(require_permission(ORGANIZATION_FEATURE, A.EDIT))],
)
async def update_organization(
    org_id: int,
    payload: OrganizationUpdateRequest,
    service: OrganizationServiceDep,
    current_user: CurrentUserDep,
) -> dict[str, Any]:
    """Update an organization profile (own org, or any for super-admin)."""
    _assert_own_org_or_super_admin(current_user, org_id)
    result = await service.update_organization(
        actor_id=current_user.user_id, org_id=org_id, data=payload
    )
    return _ok(result, "Organization updated successfully.")


@router.post(
    "/organizations/{org_id}/activate",
    response_model=SuccessResponse[OrganizationSchema],
    summary="Activate Organization",
    dependencies=[Depends(require_permission(ORGANIZATION_FEATURE, A.EDIT))],
)
async def activate_organization(
    org_id: int,
    service: OrganizationServiceDep,
    current_user: SuperAdminDep,
) -> dict[str, Any]:
    """Activate an organization (super-admin only, idempotent)."""
    result = await service.set_active(actor_id=current_user.user_id, org_id=org_id, is_active=True)
    return _ok(result, "Organization activated.")


@router.post(
    "/organizations/{org_id}/deactivate",
    response_model=SuccessResponse[OrganizationSchema],
    summary="Deactivate Organization",
    dependencies=[Depends(require_permission(ORGANIZATION_FEATURE, A.EDIT))],
)
async def deactivate_organization(
    org_id: int,
    service: OrganizationServiceDep,
    current_user: SuperAdminDep,
) -> dict[str, Any]:
    """Deactivate an organization (super-admin only, idempotent)."""
    result = await service.set_active(actor_id=current_user.user_id, org_id=org_id, is_active=False)
    return _ok(result, "Organization deactivated.")


# ===========================================================================
# 7-12. Branch Management (§5.1) — feature key `branch`
# ===========================================================================


@router.post(
    "/branches",
    response_model=SuccessResponse[BranchSchema],
    status_code=status.HTTP_201_CREATED,
    summary="Create Branch",
    dependencies=[Depends(require_permission(BRANCH_FEATURE, A.CREATE))],
)
async def create_branch(
    payload: BranchCreateRequest,
    service: BranchServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Create a branch within the caller's organization."""
    result = await service.create_branch(org_id=org_id, actor_id=current_user.user_id, data=payload)
    return _ok(result, "Branch created successfully.")


@router.get(
    "/branches",
    response_model=SuccessResponse[BranchListResponse],
    summary="List Branches",
    dependencies=[Depends(require_permission(BRANCH_FEATURE, A.READ))],
)
async def list_branches(
    service: BranchServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
    page: Annotated[int, Query(ge=1, description="1-based page number.")] = 1,
    page_size: Annotated[int, Query(ge=1, le=200, description="Items per page.")] = 25,
    search: Annotated[str | None, Query(description="Search by name or city.")] = None,
    is_active: Annotated[bool | None, Query(description="Filter by active flag.")] = None,
    include_deleted: Annotated[bool, Query(description="Include soft-deleted rows.")] = False,
    sort_by: Annotated[str | None, Query(description="Sort field: branch_name|created_at.")] = None,
    sort_order: Annotated[str | None, Query(description="Sort order: asc, desc.")] = None,
) -> dict[str, Any]:
    """List branches in the caller's organization (respects branch data scope)."""
    query = BranchSearchQuery(
        page=page,
        page_size=page_size,
        search=search,
        is_active=is_active,
        include_deleted=include_deleted,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    result = await service.list_branches(
        org_id=org_id, query=query, allowed_branch_ids=_branch_scope(current_user)
    )
    return _ok(result)


@router.get(
    "/branches/{branch_id}",
    response_model=SuccessResponse[BranchSchema],
    summary="Get Branch",
    dependencies=[Depends(require_permission(BRANCH_FEATURE, A.READ))],
)
async def get_branch(
    branch_id: int,
    service: BranchServiceDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Retrieve a single branch scoped to the caller's organization."""
    result = await service.get_branch(org_id=org_id, branch_id=branch_id)
    return _ok(result)


@router.patch(
    "/branches/{branch_id}",
    response_model=SuccessResponse[BranchSchema],
    summary="Update Branch",
    dependencies=[Depends(require_permission(BRANCH_FEATURE, A.EDIT))],
)
async def update_branch(
    branch_id: int,
    payload: BranchUpdateRequest,
    service: BranchServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Update a branch's master attributes."""
    result = await service.update_branch(
        org_id=org_id, actor_id=current_user.user_id, branch_id=branch_id, data=payload
    )
    return _ok(result, "Branch updated successfully.")


@router.post(
    "/branches/{branch_id}/activate",
    response_model=SuccessResponse[BranchSchema],
    summary="Activate Branch",
    dependencies=[Depends(require_permission(BRANCH_FEATURE, A.EDIT))],
)
async def activate_branch(
    branch_id: int,
    service: BranchServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Activate a branch (idempotent)."""
    result = await service.set_active(
        org_id=org_id, actor_id=current_user.user_id, branch_id=branch_id, is_active=True
    )
    return _ok(result, "Branch activated.")


@router.post(
    "/branches/{branch_id}/deactivate",
    response_model=SuccessResponse[BranchSchema],
    summary="Deactivate Branch",
    dependencies=[Depends(require_permission(BRANCH_FEATURE, A.EDIT))],
)
async def deactivate_branch(
    branch_id: int,
    service: BranchServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Deactivate a branch (blocked if referenced by active employees)."""
    result = await service.set_active(
        org_id=org_id, actor_id=current_user.user_id, branch_id=branch_id, is_active=False
    )
    return _ok(result, "Branch deactivated.")


# ===========================================================================
# 13-18. Department Management (§5.2) — feature key `department`
# ===========================================================================


@router.post(
    "/departments",
    response_model=SuccessResponse[DepartmentSchema],
    status_code=status.HTTP_201_CREATED,
    summary="Create Department",
    dependencies=[Depends(require_permission(DEPARTMENT_FEATURE, A.CREATE))],
)
async def create_department(
    payload: DepartmentCreateRequest,
    service: DepartmentServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Create a department within the caller's organization."""
    result = await service.create_department(
        org_id=org_id, actor_id=current_user.user_id, data=payload
    )
    return _ok(result, "Department created successfully.")


@router.get(
    "/departments",
    response_model=SuccessResponse[DepartmentListResponse],
    summary="List Departments",
    dependencies=[Depends(require_permission(DEPARTMENT_FEATURE, A.READ))],
)
async def list_departments(
    service: DepartmentServiceDep,
    org_id: OrgIdDep,
    page: Annotated[int, Query(ge=1, description="1-based page number.")] = 1,
    page_size: Annotated[int, Query(ge=1, le=200, description="Items per page.")] = 25,
    search: Annotated[str | None, Query(description="Search by department name.")] = None,
    is_active: Annotated[bool | None, Query(description="Filter by active flag.")] = None,
    include_deleted: Annotated[bool, Query(description="Include soft-deleted rows.")] = False,
    sort_by: Annotated[str | None, Query(description="Sort field (dept_name, created_at).")] = None,
    sort_order: Annotated[str | None, Query(description="Sort order: asc, desc.")] = None,
) -> dict[str, Any]:
    """List departments in the caller's organization."""
    query = DepartmentSearchQuery(
        page=page,
        page_size=page_size,
        search=search,
        is_active=is_active,
        include_deleted=include_deleted,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    result = await service.list_departments(org_id=org_id, query=query)
    return _ok(result)


@router.get(
    "/departments/{dept_id}",
    response_model=SuccessResponse[DepartmentSchema],
    summary="Get Department",
    dependencies=[Depends(require_permission(DEPARTMENT_FEATURE, A.READ))],
)
async def get_department(
    dept_id: int,
    service: DepartmentServiceDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Retrieve a single department scoped to the caller's organization."""
    result = await service.get_department(org_id=org_id, dept_id=dept_id)
    return _ok(result)


@router.patch(
    "/departments/{dept_id}",
    response_model=SuccessResponse[DepartmentSchema],
    summary="Update Department",
    dependencies=[Depends(require_permission(DEPARTMENT_FEATURE, A.EDIT))],
)
async def update_department(
    dept_id: int,
    payload: DepartmentUpdateRequest,
    service: DepartmentServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Update a department (name re-checked for per-org uniqueness)."""
    result = await service.update_department(
        org_id=org_id, actor_id=current_user.user_id, dept_id=dept_id, data=payload
    )
    return _ok(result, "Department updated successfully.")


@router.post(
    "/departments/{dept_id}/activate",
    response_model=SuccessResponse[DepartmentSchema],
    summary="Activate Department",
    dependencies=[Depends(require_permission(DEPARTMENT_FEATURE, A.EDIT))],
)
async def activate_department(
    dept_id: int,
    service: DepartmentServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Activate a department (idempotent)."""
    result = await service.set_active(
        org_id=org_id, actor_id=current_user.user_id, dept_id=dept_id, is_active=True
    )
    return _ok(result, "Department activated.")


@router.post(
    "/departments/{dept_id}/deactivate",
    response_model=SuccessResponse[DepartmentSchema],
    summary="Deactivate Department",
    dependencies=[Depends(require_permission(DEPARTMENT_FEATURE, A.EDIT))],
)
async def deactivate_department(
    dept_id: int,
    service: DepartmentServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Deactivate a department (blocked if referenced by active employees)."""
    result = await service.set_active(
        org_id=org_id, actor_id=current_user.user_id, dept_id=dept_id, is_active=False
    )
    return _ok(result, "Department deactivated.")


# ===========================================================================
# 19-24. Designation Management (§5.3) — feature key `designation`
# ===========================================================================


@router.post(
    "/designations",
    response_model=SuccessResponse[DesignationSchema],
    status_code=status.HTTP_201_CREATED,
    summary="Create Designation",
    dependencies=[Depends(require_permission(DESIGNATION_FEATURE, A.CREATE))],
)
async def create_designation(
    payload: DesignationCreateRequest,
    service: DesignationServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Create a designation within the caller's organization."""
    result = await service.create_designation(
        org_id=org_id, actor_id=current_user.user_id, data=payload
    )
    return _ok(result, "Designation created successfully.")


@router.get(
    "/designations",
    response_model=SuccessResponse[DesignationListResponse],
    summary="List Designations",
    dependencies=[Depends(require_permission(DESIGNATION_FEATURE, A.READ))],
)
async def list_designations(
    service: DesignationServiceDep,
    org_id: OrgIdDep,
    page: Annotated[int, Query(ge=1, description="1-based page number.")] = 1,
    page_size: Annotated[int, Query(ge=1, le=200, description="Items per page.")] = 25,
    search: Annotated[str | None, Query(description="Search by designation name.")] = None,
    is_active: Annotated[bool | None, Query(description="Filter by active flag.")] = None,
    include_deleted: Annotated[bool, Query(description="Include soft-deleted rows.")] = False,
    sort_by: Annotated[
        str | None, Query(description="Sort field: designation_name|created_at.")
    ] = None,
    sort_order: Annotated[str | None, Query(description="Sort order: asc, desc.")] = None,
) -> dict[str, Any]:
    """List designations in the caller's organization."""
    query = DesignationSearchQuery(
        page=page,
        page_size=page_size,
        search=search,
        is_active=is_active,
        include_deleted=include_deleted,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    result = await service.list_designations(org_id=org_id, query=query)
    return _ok(result)


@router.get(
    "/designations/{designation_id}",
    response_model=SuccessResponse[DesignationSchema],
    summary="Get Designation",
    dependencies=[Depends(require_permission(DESIGNATION_FEATURE, A.READ))],
)
async def get_designation(
    designation_id: int,
    service: DesignationServiceDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Retrieve a single designation scoped to the caller's organization."""
    result = await service.get_designation(org_id=org_id, designation_id=designation_id)
    return _ok(result)


@router.patch(
    "/designations/{designation_id}",
    response_model=SuccessResponse[DesignationSchema],
    summary="Update Designation",
    dependencies=[Depends(require_permission(DESIGNATION_FEATURE, A.EDIT))],
)
async def update_designation(
    designation_id: int,
    payload: DesignationUpdateRequest,
    service: DesignationServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Update a designation (name re-checked for per-org uniqueness)."""
    result = await service.update_designation(
        org_id=org_id,
        actor_id=current_user.user_id,
        designation_id=designation_id,
        data=payload,
    )
    return _ok(result, "Designation updated successfully.")


@router.post(
    "/designations/{designation_id}/activate",
    response_model=SuccessResponse[DesignationSchema],
    summary="Activate Designation",
    dependencies=[Depends(require_permission(DESIGNATION_FEATURE, A.EDIT))],
)
async def activate_designation(
    designation_id: int,
    service: DesignationServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Activate a designation (idempotent)."""
    result = await service.set_active(
        org_id=org_id,
        actor_id=current_user.user_id,
        designation_id=designation_id,
        is_active=True,
    )
    return _ok(result, "Designation activated.")


@router.post(
    "/designations/{designation_id}/deactivate",
    response_model=SuccessResponse[DesignationSchema],
    summary="Deactivate Designation",
    dependencies=[Depends(require_permission(DESIGNATION_FEATURE, A.EDIT))],
)
async def deactivate_designation(
    designation_id: int,
    service: DesignationServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Deactivate a designation (blocked if referenced by active employees)."""
    result = await service.set_active(
        org_id=org_id,
        actor_id=current_user.user_id,
        designation_id=designation_id,
        is_active=False,
    )
    return _ok(result, "Designation deactivated.")


__all__ = ["router"]
