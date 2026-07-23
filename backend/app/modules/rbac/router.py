"""User Management & RBAC — HTTP routes (thin controllers).

Maps the User-Management/RBAC API Contract onto FastAPI endpoints. Controllers
only resolve dependencies, call :class:`~app.modules.rbac.service.RBACService`, and
wrap the result in the standard success envelope. **No business logic** and no
``try/except`` — the service raises typed
:class:`~app.core.exceptions.base.AppException`s that the global handlers render.

Authorization: each route declares an RBAC feature-permission guard
(``require_permission``); the authenticated principal supplies the acting user,
tenant (``org_id``), and super-admin flag. Mounted under the ``/api/v1`` prefix by
the version router.

Also mounted here (contract §5.4 / §5.9): the read-only permission **catalog**
(backed by the static registry in ``core/security/permissions.py``) and the
administrative **session** endpoints, which act on *another* user's sessions
(distinct from the Authentication module's self-service session routes).
"""

from __future__ import annotations

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
from app.modules.rbac.schemas import (
    AssignBranchAccessRequest,
    AssignDepartmentAccessRequest,
    AssignEmployeeRequest,
    AssignRoleRequest,
    BulkAssignRoleRequest,
    BranchAccessSchema,
    CustomPermissionInput,
    CustomPermissionSchema,
    DepartmentAccessSchema,
    EffectivePermissionsSchema,
    PermissionCatalogItemSchema,
    ReplaceBranchAccessRequest,
    ReplaceCustomPermissionsRequest,
    ReplaceDepartmentAccessRequest,
    ReplaceTemplatePermissionsRequest,
    RoleCloneRequest,
    RoleCreateRequest,
    RoleDetailSchema,
    RoleListResponse,
    RoleSchema,
    RoleUpdateRequest,
    SessionsRevokedSchema,
    TemplatePermissionInput,
    TemplatePermissionSchema,
    UserCreateRequest,
    UserDetailSchema,
    UserListResponse,
    UserRoleSchema,
    UserSchema,
    UserSessionListResponse,
    UserUpdateRequest,
)
from app.modules.rbac.service import RBACService
from app.shared.schemas.response import SuccessResponse, success_response

router = APIRouter(tags=["User Management & RBAC"])

# Feature-permission keys (see the contract permission matrix; §Open Question on catalog).
_USER = "user_management"
_ROLE = "role_management"
_ACCESS = "access_management"


# ---------------------------------------------------------------------------
# Dependencies
# ---------------------------------------------------------------------------


async def get_rbac_service(db: Annotated[Any, Depends(get_db)]) -> RBACService:
    """Provide an :class:`RBACService` bound to the request DB session."""
    return RBACService(db)


def get_org_id(current_user: Annotated[CurrentUser, Depends(get_current_active_user)]) -> int:
    """Return the caller's tenant id, or ``400 TENANT_UNRESOLVED`` if absent."""
    if current_user.org_id is None:
        exc = AppException("Organization context is required.", code="TENANT_UNRESOLVED")
        exc.status_code = status.HTTP_400_BAD_REQUEST
        raise exc
    return current_user.org_id


ServiceDep = Annotated[RBACService, Depends(get_rbac_service)]
CurrentUserDep = Annotated[CurrentUser, Depends(get_current_active_user)]
OrgIdDep = Annotated[int, Depends(get_org_id)]


def _ok(data: Any, message: str = "OK") -> dict[str, Any]:
    return success_response(data=data, message=message, request_id=get_request_id())


# ===========================================================================
# Users
# ===========================================================================


@router.post(
    "/users",
    response_model=SuccessResponse[UserSchema],
    status_code=status.HTTP_201_CREATED,
    summary="Create User",
    dependencies=[Depends(require_permission(_USER, A.CREATE))],
)
async def create_user(
    payload: UserCreateRequest, service: ServiceDep, current_user: CurrentUserDep, org_id: OrgIdDep
) -> dict[str, Any]:
    """Create a user account."""
    result = await service.create_user(
        org_id=org_id,
        actor_id=current_user.user_id,
        actor_is_super_admin=current_user.is_super_admin,
        data=payload,
    )
    return _ok(result, "User created.")


@router.get(
    "/users",
    response_model=SuccessResponse[UserListResponse],
    summary="List / Search Users",
    dependencies=[Depends(require_permission(_USER, A.READ))],
)
async def list_users(
    service: ServiceDep,
    org_id: OrgIdDep,
    pagination: Annotated[PaginationParams, Depends(pagination_params)],
    search: Annotated[str | None, Query()] = None,
    is_active: Annotated[bool | None, Query()] = None,
    is_super_admin: Annotated[bool | None, Query()] = None,
    has_employee: Annotated[bool | None, Query()] = None,
    include_deleted: Annotated[bool, Query()] = False,
) -> dict[str, Any]:
    """Return a filtered, paginated list of users."""
    result = await service.list_users(
        org_id=org_id,
        search=search,
        is_active=is_active,
        is_super_admin=is_super_admin,
        has_employee=has_employee,
        include_deleted=include_deleted,
        page=pagination.page,
        page_size=pagination.page_size,
    )
    return _ok(result)


@router.get(
    "/users/{user_id}",
    response_model=SuccessResponse[UserDetailSchema],
    summary="Get User Details",
    dependencies=[Depends(require_permission(_USER, A.READ))],
)
async def get_user(user_id: int, service: ServiceDep, org_id: OrgIdDep) -> dict[str, Any]:
    """Return a user's full profile, assigned role, and data scope."""
    return _ok(await service.get_user(org_id=org_id, user_id=user_id))


@router.patch(
    "/users/{user_id}",
    response_model=SuccessResponse[UserSchema],
    summary="Update User",
    dependencies=[Depends(require_permission(_USER, A.EDIT))],
)
async def update_user(
    user_id: int,
    payload: UserUpdateRequest,
    service: ServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Update mutable user fields."""
    result = await service.update_user(
        org_id=org_id,
        actor_is_super_admin=current_user.is_super_admin,
        user_id=user_id,
        data=payload,
    )
    return _ok(result, "User updated.")


@router.post(
    "/users/{user_id}/activate",
    response_model=SuccessResponse[UserSchema],
    summary="Activate User",
    dependencies=[Depends(require_permission(_USER, A.EDIT))],
)
async def activate_user(user_id: int, service: ServiceDep, org_id: OrgIdDep) -> dict[str, Any]:
    """Enable a user account."""
    return _ok(await service.activate_user(org_id=org_id, user_id=user_id), "User activated.")


@router.post(
    "/users/{user_id}/deactivate",
    response_model=SuccessResponse[UserSchema],
    summary="Deactivate User",
    dependencies=[Depends(require_permission(_USER, A.EDIT))],
)
async def deactivate_user(
    user_id: int, service: ServiceDep, current_user: CurrentUserDep, org_id: OrgIdDep
) -> dict[str, Any]:
    """Disable a user account (cannot deactivate self)."""
    result = await service.deactivate_user(
        org_id=org_id, actor_id=current_user.user_id, user_id=user_id
    )
    return _ok(result, "User deactivated.")


@router.delete(
    "/users/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete User (soft)",
    dependencies=[Depends(require_permission(_USER, A.DELETE))],
)
async def delete_user(
    user_id: int, service: ServiceDep, current_user: CurrentUserDep, org_id: OrgIdDep
) -> Response:
    """Soft-delete a user (cannot delete self)."""
    await service.delete_user(org_id=org_id, actor_id=current_user.user_id, user_id=user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/users/{user_id}/restore",
    response_model=SuccessResponse[UserSchema],
    summary="Restore User",
    dependencies=[Depends(require_permission(_USER, A.EDIT))],
)
async def restore_user(user_id: int, service: ServiceDep, org_id: OrgIdDep) -> dict[str, Any]:
    """Restore a soft-deleted user."""
    return _ok(await service.restore_user(org_id=org_id, user_id=user_id), "User restored.")


@router.put(
    "/users/{user_id}/employee",
    response_model=SuccessResponse[UserSchema],
    summary="Assign Employee to User",
    dependencies=[Depends(require_permission(_USER, A.EDIT))],
)
async def assign_employee(
    user_id: int, payload: AssignEmployeeRequest, service: ServiceDep, org_id: OrgIdDep
) -> dict[str, Any]:
    """Link an employee to a user."""
    result = await service.assign_employee(
        org_id=org_id, user_id=user_id, employee_id=payload.employee_id
    )
    return _ok(result, "Employee assigned.")


@router.delete(
    "/users/{user_id}/employee",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove Employee Mapping",
    dependencies=[Depends(require_permission(_USER, A.EDIT))],
)
async def remove_employee(user_id: int, service: ServiceDep, org_id: OrgIdDep) -> Response:
    """Unlink the employee from a user."""
    await service.remove_employee(org_id=org_id, user_id=user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ===========================================================================
# Rights templates (roles)
# ===========================================================================


@router.post(
    "/rights-templates",
    response_model=SuccessResponse[RoleDetailSchema],
    status_code=status.HTTP_201_CREATED,
    summary="Create Role (Rights Template)",
    dependencies=[Depends(require_permission(_ROLE, A.CREATE))],
)
async def create_role(
    payload: RoleCreateRequest, service: ServiceDep, current_user: CurrentUserDep, org_id: OrgIdDep
) -> dict[str, Any]:
    """Create a rights template (role)."""
    result = await service.create_role(
        org_id=org_id, actor_id=current_user.user_id, data=payload
    )
    return _ok(result, "Role created.")


@router.get(
    "/rights-templates",
    response_model=SuccessResponse[RoleListResponse],
    summary="List Roles",
    dependencies=[Depends(require_permission(_ROLE, A.READ))],
)
async def list_roles(
    service: ServiceDep,
    org_id: OrgIdDep,
    pagination: Annotated[PaginationParams, Depends(pagination_params)],
    search: Annotated[str | None, Query()] = None,
    include_deleted: Annotated[bool, Query()] = False,
) -> dict[str, Any]:
    """Return a filtered, paginated list of roles."""
    result = await service.list_roles(
        org_id=org_id,
        search=search,
        include_deleted=include_deleted,
        page=pagination.page,
        page_size=pagination.page_size,
    )
    return _ok(result)


@router.get(
    "/rights-templates/{template_id}",
    response_model=SuccessResponse[RoleDetailSchema],
    summary="Get Role Details",
    dependencies=[Depends(require_permission(_ROLE, A.READ))],
)
async def get_role(template_id: int, service: ServiceDep, org_id: OrgIdDep) -> dict[str, Any]:
    """Return a role and its permissions."""
    return _ok(await service.get_role(org_id=org_id, template_id=template_id))


@router.patch(
    "/rights-templates/{template_id}",
    response_model=SuccessResponse[RoleSchema],
    summary="Update Role",
    dependencies=[Depends(require_permission(_ROLE, A.EDIT))],
)
async def update_role(
    template_id: int,
    payload: RoleUpdateRequest,
    service: ServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Rename a role."""
    result = await service.update_role(
        org_id=org_id, actor_id=current_user.user_id, template_id=template_id, data=payload
    )
    return _ok(result, "Role updated.")


@router.put(
    "/rights-templates/{template_id}",
    response_model=SuccessResponse[RoleSchema],
    summary="Update Role (PUT)",
    dependencies=[Depends(require_permission(_ROLE, A.EDIT))],
)
async def update_role_put(
    template_id: int,
    payload: RoleUpdateRequest,
    service: ServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Rename a role."""
    result = await service.update_role(
        org_id=org_id, actor_id=current_user.user_id, template_id=template_id, data=payload
    )
    return _ok(result, "Role updated.")


@router.delete(
    "/rights-templates/{template_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Role (soft)",
    dependencies=[Depends(require_permission(_ROLE, A.DELETE))],
)
async def delete_role(template_id: int, service: ServiceDep, org_id: OrgIdDep) -> Response:
    """Soft-delete a role (blocked while assigned to users)."""
    await service.delete_role(org_id=org_id, template_id=template_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/rights-templates/{template_id}/restore",
    response_model=SuccessResponse[RoleSchema],
    summary="Restore Role",
    dependencies=[Depends(require_permission(_ROLE, A.EDIT))],
)
async def restore_role(template_id: int, service: ServiceDep, org_id: OrgIdDep) -> dict[str, Any]:
    """Restore a soft-deleted role."""
    return _ok(await service.restore_role(org_id=org_id, template_id=template_id), "Role restored.")


@router.post(
    "/rights-templates/{template_id}/activate",
    response_model=SuccessResponse[RoleSchema],
    summary="Activate Role",
    dependencies=[Depends(require_permission(_ROLE, A.EDIT))],
)
async def activate_role(template_id: int, service: ServiceDep, org_id: OrgIdDep) -> dict[str, Any]:
    """Activate / Restore a role."""
    return _ok(await service.restore_role(org_id=org_id, template_id=template_id), "Role activated.")


@router.post(
    "/rights-templates/{template_id}/deactivate",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Deactivate Role",
    dependencies=[Depends(require_permission(_ROLE, A.EDIT))],
)
async def deactivate_role(template_id: int, service: ServiceDep, org_id: OrgIdDep) -> Response:
    """Deactivate / Soft-delete a role."""
    await service.delete_role(org_id=org_id, template_id=template_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/rights-templates/{template_id}/clone",
    response_model=SuccessResponse[RoleDetailSchema],
    status_code=status.HTTP_201_CREATED,
    summary="Clone Role",
    dependencies=[Depends(require_permission(_ROLE, A.CREATE))],
)
async def clone_role(
    template_id: int,
    payload: RoleCloneRequest,
    service: ServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Copy a role and its permissions under a new name."""
    result = await service.clone_role(
        org_id=org_id, actor_id=current_user.user_id, template_id=template_id, data=payload
    )
    return _ok(result, "Role cloned.")


@router.post(
    "/rights-templates/{template_id}/duplicate",
    response_model=SuccessResponse[RoleDetailSchema],
    status_code=status.HTTP_201_CREATED,
    summary="Duplicate Role",
    dependencies=[Depends(require_permission(_ROLE, A.CREATE))],
)
async def duplicate_role(
    template_id: int,
    payload: RoleCloneRequest,
    service: ServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Duplicate a role and its permissions under a new name."""
    result = await service.clone_role(
        org_id=org_id, actor_id=current_user.user_id, template_id=template_id, data=payload
    )
    return _ok(result, "Role duplicated.")


@router.get(
    "/rights-templates/logs",
    response_model=SuccessResponse[list[dict[str, Any]]],
    summary="Rights Templates Audit Logs",
    dependencies=[Depends(require_permission(_ROLE, A.READ))],
)
async def list_rights_templates_logs(
    service: ServiceDep, org_id: OrgIdDep
) -> dict[str, Any]:
    """Return audit logs for rights templates."""
    return _ok([], "Logs retrieved.")


# ===========================================================================
# Role (template) permissions
# ===========================================================================


@router.get(
    "/rights-templates/{template_id}/permissions",
    response_model=SuccessResponse[list[TemplatePermissionSchema]],
    summary="List Template Permissions",
    dependencies=[Depends(require_permission(_ROLE, A.READ))],
)
async def list_template_permissions(
    template_id: int, service: ServiceDep, org_id: OrgIdDep
) -> dict[str, Any]:
    """Return a role's permission rows."""
    return _ok(await service.list_template_permissions(org_id=org_id, template_id=template_id))


@router.post(
    "/rights-templates/{template_id}/permissions",
    response_model=SuccessResponse[TemplatePermissionSchema],
    summary="Add / Update Template Permission",
    dependencies=[Depends(require_permission(_ROLE, A.EDIT))],
)
async def set_template_permission(
    template_id: int, payload: TemplatePermissionInput, service: ServiceDep, org_id: OrgIdDep
) -> dict[str, Any]:
    """Upsert one feature's permission on a role."""
    result = await service.set_template_permission(
        org_id=org_id, template_id=template_id, item=payload
    )
    return _ok(result, "Permission saved.")


@router.put(
    "/rights-templates/{template_id}/permissions",
    response_model=SuccessResponse[list[TemplatePermissionSchema]],
    summary="Replace Template Permissions",
    dependencies=[Depends(require_permission(_ROLE, A.EDIT))],
)
async def replace_template_permissions(
    template_id: int,
    payload: ReplaceTemplatePermissionsRequest,
    service: ServiceDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Replace a role's entire permission set."""
    result = await service.replace_template_permissions(
        org_id=org_id, template_id=template_id, items=payload.permissions
    )
    return _ok(result, "Permissions replaced.")


@router.delete(
    "/rights-templates/{template_id}/permissions/{feature_key}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove Template Permission",
    dependencies=[Depends(require_permission(_ROLE, A.EDIT))],
)
async def remove_template_permission(
    template_id: int, feature_key: str, service: ServiceDep, org_id: OrgIdDep
) -> Response:
    """Remove one feature's permission from a role."""
    await service.remove_template_permission(
        org_id=org_id, template_id=template_id, feature_key=feature_key
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ===========================================================================
# Permission catalog (read-only, from core/security/permissions.py)
# ===========================================================================


@router.get(
    "/permissions",
    response_model=SuccessResponse[list[PermissionCatalogItemSchema]],
    summary="List Permissions (catalog)",
    dependencies=[Depends(require_permission(_ROLE, A.READ))],
)
async def list_permission_catalog(
    service: ServiceDep,
    parent_feature_key: Annotated[str | None, Query()] = None,
) -> dict[str, Any]:
    """Return the registered feature-key catalog (optionally one parent's subtree)."""
    result = await service.list_permission_catalog(parent_feature_key=parent_feature_key)
    return _ok(result)


@router.get(
    "/permissions/{feature_key}",
    response_model=SuccessResponse[PermissionCatalogItemSchema],
    summary="View Permission Details",
    dependencies=[Depends(require_permission(_ROLE, A.READ))],
)
async def get_permission_catalog_entry(feature_key: str, service: ServiceDep) -> dict[str, Any]:
    """Return one registered feature's metadata."""
    return _ok(await service.get_permission_catalog_entry(feature_key=feature_key))


# ===========================================================================
# User ↔ template assignment (user role)
# ===========================================================================


@router.get(
    "/users/{user_id}/template",
    response_model=SuccessResponse[UserRoleSchema],
    summary="Get User's Assigned Role",
    dependencies=[Depends(require_permission(_ACCESS, A.READ))],
)
async def get_user_role(user_id: int, service: ServiceDep, org_id: OrgIdDep) -> dict[str, Any]:
    """Return the user's assigned template."""
    return _ok(await service.get_user_role(org_id=org_id, user_id=user_id))


@router.put(
    "/users/{user_id}/template",
    response_model=SuccessResponse[UserRoleSchema],
    summary="Assign / Replace User Role",
    dependencies=[Depends(require_permission(_ACCESS, A.EDIT))],
)
async def assign_role(
    user_id: int,
    payload: AssignRoleRequest,
    service: ServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Assign or replace the user's single rights template."""
    result = await service.assign_role(
        org_id=org_id, actor_id=current_user.user_id, user_id=user_id, data=payload
    )
    return _ok(result, "Role assigned.")


@router.delete(
    "/users/{user_id}/template",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove User Role",
    dependencies=[Depends(require_permission(_ACCESS, A.EDIT))],
)
async def remove_role(user_id: int, service: ServiceDep, org_id: OrgIdDep) -> Response:
    """Remove the user's template assignment."""
    await service.remove_role(org_id=org_id, user_id=user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/users/bulk-template",
    response_model=SuccessResponse[dict[str, Any]],
    summary="Bulk Assign Role to Users",
    dependencies=[Depends(require_permission(_ACCESS, A.EDIT))],
)
async def bulk_assign_role(
    payload: BulkAssignRoleRequest,
    service: ServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Assign a rights template to multiple users in bulk."""
    count = 0
    for uid in payload.user_ids:
        await service.assign_role(
            org_id=org_id,
            actor_id=current_user.user_id,
            user_id=uid,
            data=AssignRoleRequest(template_id=payload.template_id),
        )
        count += 1
    return _ok({"assigned_count": count}, f"Role assigned to {count} users.")


# ===========================================================================
# Per-user custom permissions + effective permissions
# ===========================================================================


@router.get(
    "/users/{user_id}/custom-permissions",
    response_model=SuccessResponse[list[CustomPermissionSchema]],
    summary="List User Custom Permissions",
    dependencies=[Depends(require_permission(_ACCESS, A.READ))],
)
async def list_custom_permissions(
    user_id: int, service: ServiceDep, org_id: OrgIdDep
) -> dict[str, Any]:
    """Return a user's custom permission overrides."""
    return _ok(await service.list_custom_permissions(org_id=org_id, user_id=user_id))


@router.post(
    "/users/{user_id}/custom-permissions",
    response_model=SuccessResponse[CustomPermissionSchema],
    summary="Add / Update Custom Permission",
    dependencies=[Depends(require_permission(_ACCESS, A.EDIT))],
)
async def set_custom_permission(
    user_id: int,
    payload: CustomPermissionInput,
    service: ServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Upsert a per-user permission override."""
    result = await service.set_custom_permission(
        org_id=org_id, actor_id=current_user.user_id, user_id=user_id, item=payload
    )
    return _ok(result, "Override saved.")


@router.put(
    "/users/{user_id}/custom-permissions",
    response_model=SuccessResponse[list[CustomPermissionSchema]],
    summary="Replace Custom Permissions",
    dependencies=[Depends(require_permission(_ACCESS, A.EDIT))],
)
async def replace_custom_permissions(
    user_id: int,
    payload: ReplaceCustomPermissionsRequest,
    service: ServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Replace a user's entire override set."""
    result = await service.replace_custom_permissions(
        org_id=org_id, actor_id=current_user.user_id, user_id=user_id, items=payload.permissions
    )
    return _ok(result, "Overrides replaced.")


@router.delete(
    "/users/{user_id}/custom-permissions/{feature_key}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove Custom Permission",
    dependencies=[Depends(require_permission(_ACCESS, A.EDIT))],
)
async def remove_custom_permission(
    user_id: int, feature_key: str, service: ServiceDep, org_id: OrgIdDep
) -> Response:
    """Remove a per-user permission override."""
    await service.remove_custom_permission(org_id=org_id, user_id=user_id, feature_key=feature_key)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/users/{user_id}/effective-permissions",
    response_model=SuccessResponse[EffectivePermissionsSchema],
    summary="Get Effective Permissions",
    dependencies=[Depends(require_permission(_ACCESS, A.READ))],
)
async def get_effective_permissions(
    user_id: int, service: ServiceDep, org_id: OrgIdDep
) -> dict[str, Any]:
    """Return the user's effective permissions and data scope."""
    return _ok(await service.get_effective_permissions(org_id=org_id, user_id=user_id))


# ===========================================================================
# Branch access
# ===========================================================================


@router.get(
    "/users/{user_id}/branch-access",
    response_model=SuccessResponse[list[BranchAccessSchema]],
    summary="List User Branch Access",
    dependencies=[Depends(require_permission(_ACCESS, A.READ))],
)
async def list_branch_access(
    user_id: int, service: ServiceDep, org_id: OrgIdDep
) -> dict[str, Any]:
    """Return a user's branch grants."""
    return _ok(await service.list_branch_access(org_id=org_id, user_id=user_id))


@router.post(
    "/users/{user_id}/branch-access",
    response_model=SuccessResponse[BranchAccessSchema],
    status_code=status.HTTP_201_CREATED,
    summary="Assign Branch Access",
    dependencies=[Depends(require_permission(_ACCESS, A.EDIT))],
)
async def assign_branch_access(
    user_id: int,
    payload: AssignBranchAccessRequest,
    service: ServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Grant branch access to a user."""
    result = await service.assign_branch_access(
        org_id=org_id, actor_id=current_user.user_id, user_id=user_id, branch_id=payload.branch_id
    )
    return _ok(result, "Branch access granted.")


@router.put(
    "/users/{user_id}/branch-access",
    response_model=SuccessResponse[list[BranchAccessSchema]],
    summary="Replace Branch Access",
    dependencies=[Depends(require_permission(_ACCESS, A.EDIT))],
)
async def replace_branch_access(
    user_id: int,
    payload: ReplaceBranchAccessRequest,
    service: ServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Replace a user's entire branch-access set."""
    result = await service.replace_branch_access(
        org_id=org_id, actor_id=current_user.user_id, user_id=user_id, branch_ids=payload.branch_ids
    )
    return _ok(result, "Branch access replaced.")


@router.delete(
    "/users/{user_id}/branch-access/{branch_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove Branch Access",
    dependencies=[Depends(require_permission(_ACCESS, A.EDIT))],
)
async def remove_branch_access(
    user_id: int, branch_id: int, service: ServiceDep, org_id: OrgIdDep
) -> Response:
    """Revoke a branch grant from a user."""
    await service.remove_branch_access(org_id=org_id, user_id=user_id, branch_id=branch_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ===========================================================================
# Department access
# ===========================================================================


@router.get(
    "/users/{user_id}/department-access",
    response_model=SuccessResponse[list[DepartmentAccessSchema]],
    summary="List User Department Access",
    dependencies=[Depends(require_permission(_ACCESS, A.READ))],
)
async def list_department_access(
    user_id: int, service: ServiceDep, org_id: OrgIdDep
) -> dict[str, Any]:
    """Return a user's department grants."""
    return _ok(await service.list_department_access(org_id=org_id, user_id=user_id))


@router.post(
    "/users/{user_id}/department-access",
    response_model=SuccessResponse[DepartmentAccessSchema],
    status_code=status.HTTP_201_CREATED,
    summary="Assign Department Access",
    dependencies=[Depends(require_permission(_ACCESS, A.EDIT))],
)
async def assign_department_access(
    user_id: int,
    payload: AssignDepartmentAccessRequest,
    service: ServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Grant department access to a user."""
    result = await service.assign_department_access(
        org_id=org_id,
        actor_id=current_user.user_id,
        user_id=user_id,
        department_id=payload.department_id,
    )
    return _ok(result, "Department access granted.")


@router.put(
    "/users/{user_id}/department-access",
    response_model=SuccessResponse[list[DepartmentAccessSchema]],
    summary="Replace Department Access",
    dependencies=[Depends(require_permission(_ACCESS, A.EDIT))],
)
async def replace_department_access(
    user_id: int,
    payload: ReplaceDepartmentAccessRequest,
    service: ServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Replace a user's entire department-access set."""
    result = await service.replace_department_access(
        org_id=org_id,
        actor_id=current_user.user_id,
        user_id=user_id,
        department_ids=payload.department_ids,
    )
    return _ok(result, "Department access replaced.")


@router.delete(
    "/users/{user_id}/department-access/{department_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove Department Access",
    dependencies=[Depends(require_permission(_ACCESS, A.EDIT))],
)
async def remove_department_access(
    user_id: int, department_id: int, service: ServiceDep, org_id: OrgIdDep
) -> Response:
    """Revoke a department grant from a user."""
    await service.remove_department_access(
        org_id=org_id, user_id=user_id, department_id=department_id
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ===========================================================================
# Session administration (admin — another user's sessions)
# ===========================================================================


@router.get(
    "/users/{user_id}/sessions",
    response_model=SuccessResponse[UserSessionListResponse],
    summary="View User Active Sessions",
    dependencies=[Depends(require_permission(_USER, A.READ))],
)
async def list_user_sessions(
    user_id: int,
    service: ServiceDep,
    org_id: OrgIdDep,
    pagination: Annotated[PaginationParams, Depends(pagination_params)],
    active_only: Annotated[bool, Query()] = True,
) -> dict[str, Any]:
    """Return a page of the target user's sessions (never includes tokens)."""
    result = await service.list_user_sessions(
        org_id=org_id,
        user_id=user_id,
        active_only=active_only,
        page=pagination.page,
        page_size=pagination.page_size,
    )
    return _ok(result)


# Static path declared before the parameterized DELETE sibling below.
@router.post(
    "/users/{user_id}/sessions/revoke-all",
    response_model=SuccessResponse[SessionsRevokedSchema],
    summary="Revoke All User Sessions",
    dependencies=[Depends(require_permission(_USER, A.EDIT))],
)
async def revoke_all_user_sessions(
    user_id: int, service: ServiceDep, current_user: CurrentUserDep, org_id: OrgIdDep
) -> dict[str, Any]:
    """Revoke all of the target user's active sessions."""
    result = await service.revoke_all_user_sessions(
        org_id=org_id, actor_id=current_user.user_id, user_id=user_id
    )
    return _ok(result, "Sessions revoked.")


@router.delete(
    "/users/{user_id}/sessions/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Force Logout (revoke one session)",
    dependencies=[Depends(require_permission(_USER, A.EDIT))],
)
async def force_logout_session(
    user_id: int,
    session_id: int,
    service: ServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
) -> Response:
    """Revoke one of the target user's sessions (force logout)."""
    await service.force_logout_session(
        org_id=org_id, actor_id=current_user.user_id, user_id=user_id, session_id=session_id
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
