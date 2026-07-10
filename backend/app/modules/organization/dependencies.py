"""Organization / Branch / Department / Designation — module-scoped dependencies.

Wires the four services to the request-scoped :class:`AsyncSession` and exposes
the tenant-context / super-admin guard helpers shared by the routers.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies.auth import CurrentUser, get_current_active_user
from app.core.dependencies.db import get_db
from app.core.exceptions.base import AppException, AuthorizationException
from app.modules.organization.service import (
    BranchService,
    DepartmentService,
    DesignationService,
    OrganizationService,
)

# --- Service providers -------------------------------------------------------


async def get_organization_service(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> OrganizationService:
    """Provide an :class:`OrganizationService` bound to the request session."""
    return OrganizationService(db)


async def get_branch_service(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> BranchService:
    """Provide a :class:`BranchService` bound to the request session."""
    return BranchService(db)


async def get_department_service(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DepartmentService:
    """Provide a :class:`DepartmentService` bound to the request session."""
    return DepartmentService(db)


async def get_designation_service(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DesignationService:
    """Provide a :class:`DesignationService` bound to the request session."""
    return DesignationService(db)


OrganizationServiceDep = Annotated[OrganizationService, Depends(get_organization_service)]
BranchServiceDep = Annotated[BranchService, Depends(get_branch_service)]
DepartmentServiceDep = Annotated[DepartmentService, Depends(get_department_service)]
DesignationServiceDep = Annotated[DesignationService, Depends(get_designation_service)]


# --- Tenant context & authorization guards -----------------------------------


def get_org_id(
    current_user: Annotated[CurrentUser, Depends(get_current_active_user)],
) -> int:
    """Return the caller's tenant id, or raise ``TENANT_UNRESOLVED`` (400) if absent."""
    if current_user.org_id is None:
        exc = AppException("Organization context is required.", code="TENANT_UNRESOLVED")
        exc.status_code = status.HTTP_400_BAD_REQUEST
        raise exc
    return current_user.org_id


def require_super_admin(
    current_user: Annotated[CurrentUser, Depends(get_current_active_user)],
) -> CurrentUser:
    """Require the caller to be a platform super-admin (API Contract §4)."""
    if not current_user.is_super_admin:
        raise AuthorizationException("This operation requires super-admin privileges.")
    return current_user


CurrentUserDep = Annotated[CurrentUser, Depends(get_current_active_user)]
OrgIdDep = Annotated[int, Depends(get_org_id)]
SuperAdminDep = Annotated[CurrentUser, Depends(require_super_admin)]


__all__ = [
    "get_organization_service",
    "get_branch_service",
    "get_department_service",
    "get_designation_service",
    "OrganizationServiceDep",
    "BranchServiceDep",
    "DepartmentServiceDep",
    "DesignationServiceDep",
    "get_org_id",
    "require_super_admin",
    "CurrentUserDep",
    "OrgIdDep",
    "SuperAdminDep",
]
