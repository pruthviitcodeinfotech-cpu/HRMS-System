"""User Management & RBAC — service layer (business rules & orchestration).

Implements the behaviour of the User-Management/RBAC API Contract: user
administration, rights templates ("roles"), template + per-user permissions,
user↔template assignment, effective-permission calculation, and branch/department
data-scope access. All persistence goes through the module repositories; password
hashing reuses the shared security utility. The service owns the transaction
boundary (:class:`app.shared.base.service.BaseService`) and issues no SQL directly.

Scope note — **Lock / Unlock User is not implemented**: the ``users`` table has no
lock column (only ``is_active`` and ``deleted_at``), and the approved contract lists
account locking as an unsupported Open Question. Enable/disable is provided via
:meth:`activate_user` / :meth:`deactivate_user`; permanent removal via
:meth:`delete_user` (soft) / :meth:`restore_user`.
"""

from __future__ import annotations

from collections.abc import Iterable

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions.base import (
    AuthorizationException,
    ConflictException,
    NotFoundException,
    ValidationException,
)
from app.core.security.password import hash_password
from app.core.security.permissions import (
    FeatureCatalogEntry,
    get_catalog_entry,
    is_known_feature,
    list_catalog,
)
from app.modules.audit.constants import ActionType
from app.modules.audit.service import AuditService
from app.modules.auth.repository import UserSessionRepository
from app.modules.rbac.authorization import PermissionResolver
from app.modules.rbac.models import RightsTemplate, User
from app.modules.rbac.repository import (
    RightsTemplateRepository,
    TemplatePermissionRepository,
    UserBranchAccessRepository,
    UserCustomPermissionRepository,
    UserDepartmentAccessRepository,
    UserRepository,
    UserTemplateAssignmentRepository,
)
from app.modules.rbac.schemas import (
    AssignRoleRequest,
    BranchAccessSchema,
    CustomPermissionInput,
    CustomPermissionSchema,
    DataScopeSchema,
    DepartmentAccessSchema,
    EffectivePermissionSchema,
    EffectivePermissionsSchema,
    PermissionCatalogItemSchema,
    RoleCloneRequest,
    RoleCreateRequest,
    RoleDetailSchema,
    RoleListResponse,
    RoleRefSchema,
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
    UserSessionSchema,
    UserSummarySchema,
    UserUpdateRequest,
)
from app.shared.base.service import BaseService
from app.shared.utils.datetime import utcnow

_CRUD_KEYS = ("can_create", "can_read", "can_edit", "can_delete")


class RBACService(BaseService):
    """User Management & RBAC business logic."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)
        self.users = UserRepository(session)
        self.roles = RightsTemplateRepository(session)
        self.template_perms = TemplatePermissionRepository(session)
        self.assignments = UserTemplateAssignmentRepository(session)
        self.custom_perms = UserCustomPermissionRepository(session)
        self.branch_access = UserBranchAccessRepository(session)
        self.dept_access = UserDepartmentAccessRepository(session)
        self.sessions = UserSessionRepository(session)
        self._resolver = PermissionResolver(session)
        self.audit = AuditService(session)

    # =====================================================================
    # Audit helpers
    # =====================================================================
    async def _actor_name(self, org_id: int, actor_id: int | None) -> str:
        """Resolve the acting user's display name for auditing (best-effort).

        Several mutating methods do not receive an ``actor_id`` (their contract
        signature omits it); those actions are attributed to ``"System"`` rather
        than inventing an identity.
        """
        if actor_id is None:
            return "System"
        user = await self.users.get_active_by_id(actor_id, org_id)
        name = getattr(user, "name", None)
        return name if isinstance(name, str) and name else f"user #{actor_id}"

    async def _audit(
        self,
        *,
        org_id: int,
        actor_id: int | None,
        module: str,
        action_type: ActionType,
        title: str,
        description: str,
        sub_module: str | None = None,
        employee_id: int | None = None,
    ) -> None:
        """Write one audit row inside the caller's active transaction boundary.

        ``module`` is either ``"user_management"`` (user accounts) or ``"rbac"``
        (roles, permissions, assignments, data scope) so the security/access report
        (``reports.repository`` security-events query) returns these rows.
        """
        await self.audit.record(
            org_id=org_id,
            module=module,
            sub_module=sub_module,
            action_type=action_type,
            title=title,
            description=description,
            performed_by_user_id=actor_id,
            performed_by_name=await self._actor_name(org_id, actor_id),
            employee_id=employee_id,
        )

    # =====================================================================
    # Users
    # =====================================================================
    async def create_user(
        self, *, org_id: int, actor_id: int, actor_is_super_admin: bool, data: UserCreateRequest
    ) -> UserSchema:
        """Create a user account, enforcing uniqueness and super-admin gating."""
        if data.is_super_admin and not actor_is_super_admin:
            raise AuthorizationException(
                "Only a super admin may grant super-admin.", code="AUTH_FORBIDDEN"
            )
        if await self.users.email_exists(org_id, data.email):
            raise ConflictException("Email already in use.", code="USER_EMAIL_EXISTS")
        if await self.users.mobile_exists(org_id, data.mobile_country_code, data.mobile_number):
            raise ConflictException("Mobile number already in use.", code="USER_MOBILE_EXISTS")
        if data.employee_id is not None and await self.users.employee_is_mapped(
            org_id, data.employee_id
        ):
            raise ConflictException(
                "Employee is already linked to a user.", code="EMPLOYEE_ALREADY_MAPPED"
            )

        payload = {
            "org_id": org_id,
            "name": data.name,
            "email": data.email,
            "mobile_country_code": data.mobile_country_code,
            "mobile_number": data.mobile_number,
            "employee_id": data.employee_id,
            "is_super_admin": data.is_super_admin,
            "password_hash": hash_password(data.password) if data.password else None,
            "created_by": actor_id,
        }
        async with self.transaction():
            user = await self.users.create(payload)
            await self._audit(
                org_id=org_id,
                actor_id=actor_id,
                module="user_management",
                sub_module="user",
                action_type=ActionType.INSERT,
                title="User created",
                description=f"Created user '{user.name}' ({user.email}) #{user.id}",
            )
        return self._user_schema(user)

    async def update_user(
        self,
        *,
        org_id: int,
        actor_is_super_admin: bool,
        user_id: int,
        data: UserUpdateRequest,
    ) -> UserSchema:
        """Update mutable identity fields (uniqueness + super-admin re-checked)."""
        user = await self._get_active_user(org_id, user_id)
        updates = data.model_dump(exclude_unset=True)

        # Gate any *change* to the flag, not just grants. Checking only the truthy case
        # would let a non-super-admin user-editor strip another user's super-admin —
        # privilege manipulation, and a route to locking the org out of its own admin.
        if "is_super_admin" in updates and updates["is_super_admin"] != user.is_super_admin:
            if not actor_is_super_admin:
                raise AuthorizationException(
                    "Only a super admin may grant or revoke super-admin.", code="AUTH_FORBIDDEN"
                )
        if "email" in updates and updates["email"] != user.email:
            if await self.users.email_exists(org_id, updates["email"], exclude_user_id=user_id):
                raise ConflictException("Email already in use.", code="USER_EMAIL_EXISTS")
        if "mobile_number" in updates or "mobile_country_code" in updates:
            cc = updates.get("mobile_country_code", user.mobile_country_code)
            number = updates.get("mobile_number", user.mobile_number)
            if (cc, number) != (user.mobile_country_code, user.mobile_number) and (
                await self.users.mobile_exists(org_id, cc, number, exclude_user_id=user_id)
            ):
                raise ConflictException("Mobile number already in use.", code="USER_MOBILE_EXISTS")

        async with self.transaction():
            user = await self.users.update(user, updates)
            await self._audit(
                org_id=org_id,
                actor_id=None,
                module="user_management",
                sub_module="user",
                action_type=ActionType.UPDATE,
                title="User updated",
                description=(
                    f"Updated user '{user.name}' #{user.id}; "
                    f"fields: {sorted(updates.keys())}"
                ),
            )
        return self._user_schema(user)

    async def get_user(self, *, org_id: int, user_id: int) -> UserDetailSchema:
        """Return a user's full profile plus assigned role and data scope."""
        user = await self._get_active_user(org_id, user_id)
        template = await self._assigned_role_ref(user_id)
        scope = DataScopeSchema(
            branch_ids=await self.branch_access.branch_ids_for_user(user_id),
            department_ids=await self.dept_access.department_ids_for_user(user_id),
        )
        return UserDetailSchema(
            **self._user_schema(user).model_dump(), template=template, data_scope=scope
        )

    async def list_users(
        self,
        *,
        org_id: int,
        search: str | None = None,
        is_active: bool | None = None,
        is_super_admin: bool | None = None,
        has_employee: bool | None = None,
        include_deleted: bool = False,
        page: int = 1,
        page_size: int = 25,
    ) -> UserListResponse:
        """Return a filtered, paginated list of users."""
        rows = await self.users.search(
            org_id,
            search=search,
            is_active=is_active,
            is_super_admin=is_super_admin,
            has_employee=has_employee,
            include_deleted=include_deleted,
            page=page,
            page_size=page_size,
        )
        total = await self.users.search_count(
            org_id,
            search=search,
            is_active=is_active,
            is_super_admin=is_super_admin,
            has_employee=has_employee,
            include_deleted=include_deleted,
        )
        items = [UserSummarySchema.model_validate(row) for row in rows]
        return UserListResponse.build(
            items=items, page=page, page_size=page_size, total_records=total
        )

    async def activate_user(self, *, org_id: int, user_id: int) -> UserSchema:
        """Enable a user account (``is_active = True``)."""
        user = await self._get_active_user(org_id, user_id)
        async with self.transaction():
            user = await self.users.update(user, {"is_active": True})
            await self._audit(
                org_id=org_id,
                actor_id=None,
                module="user_management",
                sub_module="user",
                action_type=ActionType.UPDATE,
                title="User activated",
                description=f"Activated user '{user.name}' #{user.id}",
            )
        return self._user_schema(user)

    async def deactivate_user(self, *, org_id: int, actor_id: int, user_id: int) -> UserSchema:
        """Disable a user account (``is_active = False``); cannot deactivate self."""
        if user_id == actor_id:
            raise ConflictException(
                "You cannot deactivate your own account.", code="CANNOT_MODIFY_SELF"
            )
        user = await self._get_active_user(org_id, user_id)
        async with self.transaction():
            user = await self.users.update(user, {"is_active": False})
            await self._audit(
                org_id=org_id,
                actor_id=actor_id,
                module="user_management",
                sub_module="user",
                action_type=ActionType.UPDATE,
                title="User deactivated",
                description=f"Deactivated user '{user.name}' #{user.id}",
            )
        return self._user_schema(user)

    async def delete_user(self, *, org_id: int, actor_id: int, user_id: int) -> None:
        """Soft-delete a user (``deleted_at = now``); cannot delete self."""
        if user_id == actor_id:
            raise ConflictException(
                "You cannot delete your own account.", code="CANNOT_MODIFY_SELF"
            )
        user = await self._get_active_user(org_id, user_id)
        async with self.transaction():
            await self.users.update(user, {"deleted_at": utcnow()})
            await self._audit(
                org_id=org_id,
                actor_id=actor_id,
                module="user_management",
                sub_module="user",
                action_type=ActionType.DELETE,
                title="User deleted",
                description=f"Soft-deleted user '{user.name}' #{user.id}",
            )

    async def restore_user(self, *, org_id: int, user_id: int) -> UserSchema:
        """Restore a soft-deleted user (clear ``deleted_at``)."""
        user = await self._get_any_user(org_id, user_id)
        if user.deleted_at is None:
            raise ConflictException("User is not deleted.", code="USER_NOT_DELETED")
        async with self.transaction():
            user = await self.users.update(user, {"deleted_at": None})
            await self._audit(
                org_id=org_id,
                actor_id=None,
                module="user_management",
                sub_module="user",
                action_type=ActionType.UPDATE,
                title="User restored",
                description=f"Restored user '{user.name}' #{user.id}",
            )
        return self._user_schema(user)

    async def assign_employee(
        self, *, org_id: int, user_id: int, employee_id: int
    ) -> UserSchema:
        """Link an employee to a user (1:1 within the org)."""
        user = await self._get_active_user(org_id, user_id)
        if await self.users.employee_is_mapped(org_id, employee_id, exclude_user_id=user_id):
            raise ConflictException(
                "Employee is already linked to a user.", code="EMPLOYEE_ALREADY_MAPPED"
            )
        async with self.transaction():
            user = await self.users.update(user, {"employee_id": employee_id})
            await self._audit(
                org_id=org_id,
                actor_id=None,
                module="user_management",
                sub_module="user",
                action_type=ActionType.ASSIGN,
                title="Employee linked to user",
                description=f"Linked employee #{employee_id} to user '{user.name}' #{user.id}",
                employee_id=employee_id,
            )
        return self._user_schema(user)

    async def remove_employee(self, *, org_id: int, user_id: int) -> UserSchema:
        """Unlink the employee from a user."""
        user = await self._get_active_user(org_id, user_id)
        prior_employee_id = user.employee_id
        async with self.transaction():
            user = await self.users.update(user, {"employee_id": None})
            await self._audit(
                org_id=org_id,
                actor_id=None,
                module="user_management",
                sub_module="user",
                action_type=ActionType.DELETE,
                title="Employee unlinked from user",
                description=(
                    f"Unlinked employee #{prior_employee_id} from user "
                    f"'{user.name}' #{user.id}"
                ),
                employee_id=prior_employee_id,
            )
        return self._user_schema(user)

    # =====================================================================
    # Roles (rights templates)
    # =====================================================================
    async def create_role(
        self, *, org_id: int, actor_id: int, data: RoleCreateRequest
    ) -> RoleDetailSchema:
        """Create a rights template and (optionally) its initial permissions."""
        if await self.roles.name_exists(org_id, data.name):
            raise ConflictException("Role name already in use.", code="TEMPLATE_NAME_EXISTS")
        self._require_known_feature_keys(item.feature_key for item in data.permissions)
        async with self.transaction():
            role = await self.roles.create(
                {"org_id": org_id, "name": data.name, "created_by": actor_id}
            )
            for item in data.permissions:
                await self.template_perms.create(self._template_perm_payload(role.id, item))
            await self._audit(
                org_id=org_id,
                actor_id=actor_id,
                module="rbac",
                sub_module="role",
                action_type=ActionType.INSERT,
                title="Role created",
                description=(
                    f"Created role '{role.name}' #{role.id} "
                    f"with {len(data.permissions)} permission(s)"
                ),
            )
        return await self.get_role(org_id=org_id, template_id=role.id)

    async def update_role(
        self, *, org_id: int, actor_id: int, template_id: int, data: RoleUpdateRequest
    ) -> RoleSchema:
        """Rename a rights template."""
        role = await self._get_active_role(org_id, template_id)
        if data.name != role.name and await self.roles.name_exists(
            org_id, data.name, exclude_id=template_id
        ):
            raise ConflictException("Role name already in use.", code="TEMPLATE_NAME_EXISTS")
        async with self.transaction():
            role = await self.roles.update(role, {"name": data.name, "updated_by": actor_id})
            await self._audit(
                org_id=org_id,
                actor_id=actor_id,
                module="rbac",
                sub_module="role",
                action_type=ActionType.UPDATE,
                title="Role updated",
                description=f"Renamed role to '{role.name}' #{role.id}",
            )
        return await self._role_schema(role)

    async def get_role(self, *, org_id: int, template_id: int) -> RoleDetailSchema:
        """Return a rights template with its permission rows."""
        role = await self._get_active_role(org_id, template_id)
        perms = await self.template_perms.list_for_template(template_id)
        base = await self._role_schema(role)
        return RoleDetailSchema(
            **base.model_dump(),
            permissions=[TemplatePermissionSchema.model_validate(p) for p in perms],
        )

    async def list_roles(
        self,
        *,
        org_id: int,
        search: str | None = None,
        include_deleted: bool = False,
        page: int = 1,
        page_size: int = 25,
    ) -> RoleListResponse:
        """Return a filtered, paginated list of rights templates."""
        rows = await self.roles.search(
            org_id,
            search=search,
            include_deleted=include_deleted,
            page=page,
            page_size=page_size,
        )
        total = await self.roles.search_count(
            org_id, search=search, include_deleted=include_deleted
        )
        items = [await self._role_schema(role) for role in rows]
        return RoleListResponse.build(
            items=items, page=page, page_size=page_size, total_records=total
        )

    async def delete_role(self, *, org_id: int, template_id: int) -> None:
        """Soft-delete a template; blocked while assigned to any user."""
        role = await self._get_active_role(org_id, template_id)
        if await self.roles.has_assignments(template_id):
            raise ConflictException("Role is assigned to users.", code="TEMPLATE_IN_USE")
        async with self.transaction():
            await self.roles.update(role, {"deleted_at": utcnow()})
            await self._audit(
                org_id=org_id,
                actor_id=None,
                module="rbac",
                sub_module="role",
                action_type=ActionType.DELETE,
                title="Role deleted",
                description=f"Soft-deleted role '{role.name}' #{role.id}",
            )

    async def restore_role(self, *, org_id: int, template_id: int) -> RoleSchema:
        """Restore a soft-deleted template."""
        role = await self._get_any_role(org_id, template_id)
        if role.deleted_at is None:
            raise ConflictException("Role is not deleted.", code="TEMPLATE_NOT_DELETED")
        async with self.transaction():
            role = await self.roles.update(role, {"deleted_at": None})
            await self._audit(
                org_id=org_id,
                actor_id=None,
                module="rbac",
                sub_module="role",
                action_type=ActionType.UPDATE,
                title="Role restored",
                description=f"Restored role '{role.name}' #{role.id}",
            )
        return await self._role_schema(role)

    async def clone_role(
        self, *, org_id: int, actor_id: int, template_id: int, data: RoleCloneRequest
    ) -> RoleDetailSchema:
        """Copy a template and all its permissions under a new name."""
        source = await self._get_active_role(org_id, template_id)
        if await self.roles.name_exists(org_id, data.name):
            raise ConflictException("Role name already in use.", code="TEMPLATE_NAME_EXISTS")
        source_perms = await self.template_perms.list_for_template(source.id)
        async with self.transaction():
            clone = await self.roles.create(
                {"org_id": org_id, "name": data.name, "created_by": actor_id}
            )
            for perm in source_perms:
                await self.template_perms.create(
                    {
                        "template_id": clone.id,
                        "feature_key": perm.feature_key,
                        "feature_label": perm.feature_label,
                        "parent_feature_key": perm.parent_feature_key,
                        **{key: getattr(perm, key) for key in _CRUD_KEYS},
                    }
                )
            await self._audit(
                org_id=org_id,
                actor_id=actor_id,
                module="rbac",
                sub_module="role",
                action_type=ActionType.INSERT,
                title="Role cloned",
                description=(
                    f"Cloned role '{source.name}' #{source.id} into "
                    f"'{clone.name}' #{clone.id}"
                ),
            )
        return await self.get_role(org_id=org_id, template_id=clone.id)

    # =====================================================================
    # Role (template) permissions
    # =====================================================================
    async def list_template_permissions(
        self, *, org_id: int, template_id: int
    ) -> list[TemplatePermissionSchema]:
        """Return a template's permission rows."""
        await self._get_active_role(org_id, template_id)
        perms = await self.template_perms.list_for_template(template_id)
        return [TemplatePermissionSchema.model_validate(p) for p in perms]

    async def set_template_permission(
        self, *, org_id: int, template_id: int, item: TemplatePermissionInput
    ) -> TemplatePermissionSchema:
        """Add or update (upsert) one feature's permission on a template."""
        self._require_known_feature_keys((item.feature_key,))
        await self._get_active_role(org_id, template_id)
        existing = await self.template_perms.get_for_feature(template_id, item.feature_key)
        async with self.transaction():
            if existing is not None:
                row = await self.template_perms.update(
                    existing, self._template_perm_payload(template_id, item, with_key=False)
                )
            else:
                row = await self.template_perms.create(
                    self._template_perm_payload(template_id, item)
                )
            await self._audit(
                org_id=org_id,
                actor_id=None,
                module="rbac",
                sub_module="role_permission",
                action_type=ActionType.ASSIGN,
                title="Role permission set",
                description=(
                    f"Set permission for feature '{item.feature_key}' on role #{template_id}"
                ),
            )
        return TemplatePermissionSchema.model_validate(row)

    async def remove_template_permission(
        self, *, org_id: int, template_id: int, feature_key: str
    ) -> None:
        """Remove one feature's permission from a template."""
        await self._get_active_role(org_id, template_id)
        async with self.transaction():
            removed = await self.template_perms.delete_for_feature(template_id, feature_key)
            if removed:
                await self._audit(
                    org_id=org_id,
                    actor_id=None,
                    module="rbac",
                    sub_module="role_permission",
                    action_type=ActionType.DELETE,
                    title="Role permission removed",
                    description=(
                        f"Removed permission for feature '{feature_key}' from role #{template_id}"
                    ),
                )
        if not removed:
            raise NotFoundException("Permission not found.", code="PERMISSION_NOT_FOUND")

    async def replace_template_permissions(
        self, *, org_id: int, template_id: int, items: list[TemplatePermissionInput]
    ) -> list[TemplatePermissionSchema]:
        """Replace a template's entire permission set atomically."""
        self._require_known_feature_keys(item.feature_key for item in items)
        await self._get_active_role(org_id, template_id)
        async with self.transaction():
            await self.template_perms.delete_all_for_template(template_id)
            rows = [
                await self.template_perms.create(self._template_perm_payload(template_id, item))
                for item in items
            ]
            await self._audit(
                org_id=org_id,
                actor_id=None,
                module="rbac",
                sub_module="role_permission",
                action_type=ActionType.BULK_ASSIGN,
                title="Role permissions replaced",
                description=(
                    f"Replaced permission set on role #{template_id} "
                    f"with {len(rows)} feature(s)"
                ),
            )
        return [TemplatePermissionSchema.model_validate(r) for r in rows]

    # =====================================================================
    # Permission catalog (static code registry — contract §5.4)
    # =====================================================================
    async def list_permission_catalog(
        self, *, parent_feature_key: str | None = None
    ) -> list[PermissionCatalogItemSchema]:
        """Return the registered feature catalog (optionally one parent's subtree)."""
        return [self._catalog_item(entry) for entry in list_catalog(parent_feature_key)]

    async def get_permission_catalog_entry(
        self, *, feature_key: str
    ) -> PermissionCatalogItemSchema:
        """Return one registered feature's metadata (404 ``FEATURE_KEY_UNKNOWN``)."""
        entry = get_catalog_entry(feature_key)
        if entry is None:
            raise NotFoundException(
                "Feature key is not registered in the permission catalog.",
                code="FEATURE_KEY_UNKNOWN",
            )
        return self._catalog_item(entry)

    # =====================================================================
    # User ↔ template assignment (user role)
    # =====================================================================
    async def get_user_role(self, *, org_id: int, user_id: int) -> UserRoleSchema:
        """Return the user's assigned template (role), if any."""
        await self._get_active_user(org_id, user_id)
        assignment = await self.assignments.get_for_user(user_id)
        if assignment is None:
            return UserRoleSchema(template=None)
        role = await self.roles.get_by_id(assignment.template_id)
        return UserRoleSchema(
            template=RoleRefSchema.model_validate(role) if role else None,
            assigned_by=assignment.assigned_by,
            assigned_at=assignment.assigned_at,
        )

    async def assign_role(
        self, *, org_id: int, actor_id: int, user_id: int, data: AssignRoleRequest
    ) -> UserRoleSchema:
        """Assign or replace the user's single rights template."""
        await self._get_active_user(org_id, user_id)
        role = await self._get_active_role(org_id, data.template_id)
        async with self.transaction():
            await self.assignments.delete_for_user(user_id)
            await self.assignments.create(
                {"user_id": user_id, "template_id": data.template_id, "assigned_by": actor_id}
            )
            await self._audit(
                org_id=org_id,
                actor_id=actor_id,
                module="rbac",
                sub_module="user_role",
                action_type=ActionType.ASSIGN,
                title="Role assigned to user",
                description=f"Assigned role '{role.name}' #{role.id} to user #{user_id}",
            )
        return await self.get_user_role(org_id=org_id, user_id=user_id)

    async def remove_role(self, *, org_id: int, user_id: int) -> None:
        """Remove the user's template assignment."""
        await self._get_active_user(org_id, user_id)
        async with self.transaction():
            removed = await self.assignments.delete_for_user(user_id)
            if removed:
                await self._audit(
                    org_id=org_id,
                    actor_id=None,
                    module="rbac",
                    sub_module="user_role",
                    action_type=ActionType.DELETE,
                    title="Role removed from user",
                    description=f"Removed role assignment from user #{user_id}",
                )
        if not removed:
            raise NotFoundException("No role assigned.", code="ASSIGNMENT_NOT_FOUND")

    # =====================================================================
    # Per-user custom permission overrides
    # =====================================================================
    async def list_custom_permissions(
        self, *, org_id: int, user_id: int
    ) -> list[CustomPermissionSchema]:
        """Return a user's custom permission overrides."""
        await self._get_active_user(org_id, user_id)
        rows = await self.custom_perms.list_for_user(user_id)
        return [CustomPermissionSchema.model_validate(r) for r in rows]

    async def set_custom_permission(
        self, *, org_id: int, actor_id: int, user_id: int, item: CustomPermissionInput
    ) -> CustomPermissionSchema:
        """Add or update (upsert) a per-user permission override."""
        self._require_known_feature_keys((item.feature_key,))
        await self._get_active_user(org_id, user_id)
        existing = await self.custom_perms.get_for_feature(user_id, item.feature_key)
        async with self.transaction():
            if existing is not None:
                row = await self.custom_perms.update(
                    existing, self._custom_perm_payload(user_id, actor_id, item, with_key=False)
                )
            else:
                row = await self.custom_perms.create(
                    self._custom_perm_payload(user_id, actor_id, item)
                )
            await self._audit(
                org_id=org_id,
                actor_id=actor_id,
                module="rbac",
                sub_module="custom_permission",
                action_type=ActionType.ASSIGN,
                title="Custom permission set",
                description=(
                    f"Set custom permission for feature '{item.feature_key}' on user #{user_id}"
                ),
            )
        return CustomPermissionSchema.model_validate(row)

    async def remove_custom_permission(
        self, *, org_id: int, user_id: int, feature_key: str
    ) -> None:
        """Remove a per-user permission override."""
        await self._get_active_user(org_id, user_id)
        async with self.transaction():
            removed = await self.custom_perms.delete_for_feature(user_id, feature_key)
            if removed:
                await self._audit(
                    org_id=org_id,
                    actor_id=None,
                    module="rbac",
                    sub_module="custom_permission",
                    action_type=ActionType.DELETE,
                    title="Custom permission removed",
                    description=(
                        f"Removed custom permission for feature '{feature_key}' "
                        f"from user #{user_id}"
                    ),
                )
        if not removed:
            raise NotFoundException("Permission not found.", code="PERMISSION_NOT_FOUND")

    async def replace_custom_permissions(
        self, *, org_id: int, actor_id: int, user_id: int, items: list[CustomPermissionInput]
    ) -> list[CustomPermissionSchema]:
        """Replace a user's entire override set atomically."""
        self._require_known_feature_keys(item.feature_key for item in items)
        await self._get_active_user(org_id, user_id)
        async with self.transaction():
            await self.custom_perms.delete_all_for_user(user_id)
            rows = [
                await self.custom_perms.create(self._custom_perm_payload(user_id, actor_id, item))
                for item in items
            ]
            await self._audit(
                org_id=org_id,
                actor_id=actor_id,
                module="rbac",
                sub_module="custom_permission",
                action_type=ActionType.BULK_ASSIGN,
                title="Custom permissions replaced",
                description=(
                    f"Replaced custom permission set for user #{user_id} "
                    f"with {len(rows)} feature(s)"
                ),
            )
        return [CustomPermissionSchema.model_validate(r) for r in rows]

    # =====================================================================
    # Effective permissions (template ⊕ custom + data scope)
    # =====================================================================
    async def get_effective_permissions(
        self, *, org_id: int, user_id: int
    ) -> EffectivePermissionsSchema:
        """Compute a user's effective permissions and data scope.

        Delegates the template ⊕ custom merge + scope resolution to the canonical
        :class:`~app.modules.rbac.authorization.PermissionResolver` (single source of
        truth), then maps the resulting ``EffectivePermissions`` to the API DTO.
        """
        user = await self._get_active_user(org_id, user_id)
        effective = await self._resolver.resolve(
            user_id=user_id, is_super_admin=user.is_super_admin
        )
        permissions = [
            EffectivePermissionSchema(
                feature_key=feature.feature_key,
                can_create=feature.can_create,
                can_read=feature.can_read,
                can_edit=feature.can_edit,
                can_delete=feature.can_delete,
            )
            for feature in effective.features.values()
        ]
        scope = DataScopeSchema(
            branch_ids=sorted(effective.branch_ids),
            department_ids=sorted(effective.department_ids),
        )
        return EffectivePermissionsSchema(permissions=permissions, data_scope=scope)

    # =====================================================================
    # Branch access (data scope)
    # =====================================================================
    async def list_branch_access(self, *, org_id: int, user_id: int) -> list[BranchAccessSchema]:
        """Return a user's branch grants."""
        await self._get_active_user(org_id, user_id)
        rows = await self.branch_access.list_for_user(user_id)
        return [BranchAccessSchema.model_validate(r) for r in rows]

    async def assign_branch_access(
        self, *, org_id: int, actor_id: int, user_id: int, branch_id: int
    ) -> BranchAccessSchema:
        """Grant branch access to a user."""
        await self._get_active_user(org_id, user_id)
        if await self.branch_access.exists(user_id, branch_id):
            raise ConflictException("Branch access already granted.", code="BRANCH_ACCESS_EXISTS")
        async with self.transaction():
            row = await self.branch_access.create(
                {"user_id": user_id, "branch_id": branch_id, "granted_by": actor_id}
            )
            await self._audit(
                org_id=org_id,
                actor_id=actor_id,
                module="rbac",
                sub_module="branch_access",
                action_type=ActionType.ASSIGN,
                title="Branch access granted",
                description=f"Granted branch #{branch_id} access to user #{user_id}",
            )
        return BranchAccessSchema.model_validate(row)

    async def remove_branch_access(self, *, org_id: int, user_id: int, branch_id: int) -> None:
        """Revoke a branch grant from a user."""
        await self._get_active_user(org_id, user_id)
        async with self.transaction():
            removed = await self.branch_access.delete_for_branch(user_id, branch_id)
            if removed:
                await self._audit(
                    org_id=org_id,
                    actor_id=None,
                    module="rbac",
                    sub_module="branch_access",
                    action_type=ActionType.DELETE,
                    title="Branch access revoked",
                    description=f"Revoked branch #{branch_id} access from user #{user_id}",
                )
        if not removed:
            raise NotFoundException("Branch access not found.", code="BRANCH_ACCESS_NOT_FOUND")

    async def replace_branch_access(
        self, *, org_id: int, actor_id: int, user_id: int, branch_ids: list[int]
    ) -> list[BranchAccessSchema]:
        """Replace a user's entire branch-access set atomically."""
        await self._get_active_user(org_id, user_id)
        async with self.transaction():
            await self.branch_access.delete_all_for_user(user_id)
            rows = [
                await self.branch_access.create(
                    {"user_id": user_id, "branch_id": bid, "granted_by": actor_id}
                )
                for bid in dict.fromkeys(branch_ids)  # de-duplicate, preserve order
            ]
            await self._audit(
                org_id=org_id,
                actor_id=actor_id,
                module="rbac",
                sub_module="branch_access",
                action_type=ActionType.BULK_ASSIGN,
                title="Branch access replaced",
                description=(
                    f"Replaced branch access for user #{user_id} "
                    f"with {len(rows)} branch(es)"
                ),
            )
        return [BranchAccessSchema.model_validate(r) for r in rows]

    # =====================================================================
    # Department access (data scope)
    # =====================================================================
    async def list_department_access(
        self, *, org_id: int, user_id: int
    ) -> list[DepartmentAccessSchema]:
        """Return a user's department grants."""
        await self._get_active_user(org_id, user_id)
        rows = await self.dept_access.list_for_user(user_id)
        return [DepartmentAccessSchema.model_validate(r) for r in rows]

    async def assign_department_access(
        self, *, org_id: int, actor_id: int, user_id: int, department_id: int
    ) -> DepartmentAccessSchema:
        """Grant department access to a user."""
        await self._get_active_user(org_id, user_id)
        if await self.dept_access.exists(user_id, department_id):
            raise ConflictException(
                "Department access already granted.", code="DEPARTMENT_ACCESS_EXISTS"
            )
        async with self.transaction():
            row = await self.dept_access.create(
                {"user_id": user_id, "department_id": department_id, "granted_by": actor_id}
            )
            await self._audit(
                org_id=org_id,
                actor_id=actor_id,
                module="rbac",
                sub_module="department_access",
                action_type=ActionType.ASSIGN,
                title="Department access granted",
                description=f"Granted department #{department_id} access to user #{user_id}",
            )
        return DepartmentAccessSchema.model_validate(row)

    async def remove_department_access(
        self, *, org_id: int, user_id: int, department_id: int
    ) -> None:
        """Revoke a department grant from a user."""
        await self._get_active_user(org_id, user_id)
        async with self.transaction():
            removed = await self.dept_access.delete_for_department(user_id, department_id)
            if removed:
                await self._audit(
                    org_id=org_id,
                    actor_id=None,
                    module="rbac",
                    sub_module="department_access",
                    action_type=ActionType.DELETE,
                    title="Department access revoked",
                    description=f"Revoked department #{department_id} access from user #{user_id}",
                )
        if not removed:
            raise NotFoundException(
                "Department access not found.", code="DEPARTMENT_ACCESS_NOT_FOUND"
            )

    async def replace_department_access(
        self, *, org_id: int, actor_id: int, user_id: int, department_ids: list[int]
    ) -> list[DepartmentAccessSchema]:
        """Replace a user's entire department-access set atomically."""
        await self._get_active_user(org_id, user_id)
        async with self.transaction():
            await self.dept_access.delete_all_for_user(user_id)
            rows = [
                await self.dept_access.create(
                    {"user_id": user_id, "department_id": did, "granted_by": actor_id}
                )
                for did in dict.fromkeys(department_ids)
            ]
            await self._audit(
                org_id=org_id,
                actor_id=actor_id,
                module="rbac",
                sub_module="department_access",
                action_type=ActionType.BULK_ASSIGN,
                title="Department access replaced",
                description=(
                    f"Replaced department access for user #{user_id} with {len(rows)} department(s)"
                ),
            )
        return [DepartmentAccessSchema.model_validate(r) for r in rows]

    # =====================================================================
    # Session administration (admin — another user's ``user_sessions``)
    # =====================================================================
    async def list_user_sessions(
        self,
        *,
        org_id: int,
        user_id: int,
        active_only: bool = True,
        page: int = 1,
        page_size: int = 25,
    ) -> UserSessionListResponse:
        """Return a page of the target user's sessions (``session_token`` never leaves)."""
        await self._get_any_user(org_id, user_id)
        rows = await self.sessions.list_for_user(
            user_id, active_only=active_only, page=page, page_size=page_size
        )
        total = await self.sessions.count_for_user(user_id, active_only=active_only)
        items = [UserSessionSchema.model_validate(row) for row in rows]
        return UserSessionListResponse.build(
            items=items, page=page, page_size=page_size, total_records=total
        )

    async def force_logout_session(
        self, *, org_id: int, actor_id: int, user_id: int, session_id: int
    ) -> None:
        """Revoke one of the target user's sessions (force logout)."""
        user = await self._get_any_user(org_id, user_id)
        session_row = await self.sessions.get_for_user(session_id, user_id)
        if session_row is None:
            raise NotFoundException("Session not found.", code="SESSION_NOT_FOUND")
        async with self.transaction():
            await self.sessions.revoke(session_row, when=utcnow())
            await self._audit(
                org_id=org_id,
                actor_id=actor_id,
                module="user_management",
                sub_module="session",
                action_type=ActionType.DELETE,
                title="Session force-logged-out",
                description=(
                    f"Force-logged-out session #{session_id} of user "
                    f"'{user.name}' #{user_id}"
                ),
            )

    async def revoke_all_user_sessions(
        self, *, org_id: int, actor_id: int, user_id: int
    ) -> SessionsRevokedSchema:
        """Revoke all of the target user's active sessions (e.g. after deactivate/delete)."""
        user = await self._get_any_user(org_id, user_id)
        async with self.transaction():
            revoked = await self.sessions.revoke_all_for_user(user_id, when=utcnow())
            await self._audit(
                org_id=org_id,
                actor_id=actor_id,
                module="user_management",
                sub_module="session",
                action_type=ActionType.DELETE,
                title="All user sessions revoked",
                description=(
                    f"Revoked {revoked} session(s) of user '{user.name}' #{user_id}"
                ),
            )
        return SessionsRevokedSchema(revoked_count=revoked)

    # =====================================================================
    # Internal helpers
    # =====================================================================
    @staticmethod
    def _require_known_feature_keys(feature_keys: Iterable[str]) -> None:
        """Raise 422 ``FEATURE_KEY_UNKNOWN`` if any key is not in the catalog."""
        unknown = sorted({key for key in feature_keys if not is_known_feature(key)})
        if unknown:
            raise ValidationException(
                f"Unknown feature key(s): {', '.join(unknown)}.",
                code="FEATURE_KEY_UNKNOWN",
                details={"unknown_feature_keys": unknown},
            )

    @staticmethod
    def _catalog_item(entry: FeatureCatalogEntry) -> PermissionCatalogItemSchema:
        return PermissionCatalogItemSchema(
            feature_key=entry.feature_key,
            feature_label=entry.feature_label,
            parent_feature_key=entry.parent_feature_key,
            supported_actions=list(entry.supported_actions),
        )

    async def _get_active_user(self, org_id: int, user_id: int) -> User:
        user = await self.users.get_active_by_id(user_id, org_id)
        if user is None:
            raise NotFoundException("User not found.", code="USER_NOT_FOUND")
        return user

    async def _get_any_user(self, org_id: int, user_id: int) -> User:
        user = await self.users.get_by_id(user_id)
        if user is None or user.org_id != org_id:
            raise NotFoundException("User not found.", code="USER_NOT_FOUND")
        return user

    async def _get_active_role(self, org_id: int, template_id: int) -> RightsTemplate:
        role = await self.roles.get_active_by_id(template_id, org_id)
        if role is None:
            raise NotFoundException("Role not found.", code="TEMPLATE_NOT_FOUND")
        return role

    async def _get_any_role(self, org_id: int, template_id: int) -> RightsTemplate:
        role = await self.roles.get_by_id(template_id)
        if role is None or role.org_id != org_id:
            raise NotFoundException("Role not found.", code="TEMPLATE_NOT_FOUND")
        return role

    async def _assigned_role_ref(self, user_id: int) -> RoleRefSchema | None:
        assignment = await self.assignments.get_for_user(user_id)
        if assignment is None:
            return None
        role = await self.roles.get_by_id(assignment.template_id)
        return RoleRefSchema.model_validate(role) if role else None

    @staticmethod
    def _user_schema(user: User) -> UserSchema:
        return UserSchema.model_validate(user).model_copy(
            update={"is_deleted": user.deleted_at is not None}
        )

    async def _role_schema(self, role: RightsTemplate) -> RoleSchema:
        return RoleSchema.model_validate(role).model_copy(
            update={
                "permission_count": await self.roles.permission_count(role.id),
                "assigned_user_count": await self.roles.assigned_user_count(role.id),
                "is_deleted": role.deleted_at is not None,
            }
        )

    @staticmethod
    def _template_perm_payload(
        template_id: int, item: TemplatePermissionInput, *, with_key: bool = True
    ) -> dict[str, object]:
        payload: dict[str, object] = {
            "feature_label": item.feature_label,
            "parent_feature_key": item.parent_feature_key,
            **{key: getattr(item, key) for key in _CRUD_KEYS},
        }
        if with_key:
            payload["template_id"] = template_id
            payload["feature_key"] = item.feature_key
        return payload

    @staticmethod
    def _custom_perm_payload(
        user_id: int, actor_id: int, item: CustomPermissionInput, *, with_key: bool = True
    ) -> dict[str, object]:
        payload: dict[str, object] = {
            "parent_feature_key": item.parent_feature_key,
            "set_by": actor_id,
            **{key: getattr(item, key) for key in _CRUD_KEYS},
        }
        if with_key:
            payload["user_id"] = user_id
            payload["feature_key"] = item.feature_key
        return payload
