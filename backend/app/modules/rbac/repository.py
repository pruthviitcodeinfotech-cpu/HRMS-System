"""User Management & RBAC — data-access layer (async SQLAlchemy).

One focused repository per aggregate, all extending
:class:`app.shared.base.repository.BaseRepository` and operating on the existing
RBAC models. **Database operations only** — no business rules, no permission
merging, no password/token handling. Methods run queries and flush writes; the
**service owns the commit boundary**. Every query is org-scoped where the table
carries ``org_id``.

Phase 2 addition
────────────────
:class:`UserOrganizationMembershipRepository` — data access for the new
``user_organization_memberships`` junction table.  All existing repositories
and their public APIs are unchanged.
"""

from __future__ import annotations

from sqlalchemy import and_, delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants.enums import SortOrder
from app.modules.rbac.models import (
    RightsTemplate,
    RightsTemplatePermission,
    User,
    UserBranchAccess,
    UserCustomPermission,
    UserDepartmentAccess,
    UserOrganizationMembership,
    UserTemplateAssignment,
)
from app.shared.base.repository import BaseRepository
from app.shared.utils.query import apply_sorting

_USER_SORTS = {"name", "email", "created_at", "last_login_at"}
_ROLE_SORTS = {"name", "created_at", "updated_at"}


class UserRepository(BaseRepository[User]):
    """CRUD, search, and lookup operations for ``users``."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, User)

    # --- Lookups -------------------------------------------------------------
    async def get_active_by_id(self, user_id: int, org_id: int) -> User | None:
        """Return a non-deleted user by id within ``org_id``."""
        stmt = select(User).where(
            User.id == user_id, User.org_id == org_id, User.deleted_at.is_(None)
        )
        return (await self.session.execute(stmt.limit(1))).scalar_one_or_none()

    async def get_by_email(
        self, org_id: int, email: str, *, include_deleted: bool = False
    ) -> User | None:
        """Return the user with ``email`` in ``org_id`` (soft-deleted excluded by default)."""
        stmt = select(User).where(User.org_id == org_id, User.email == email)
        if not include_deleted:
            stmt = stmt.where(User.deleted_at.is_(None))
        return (await self.session.execute(stmt.limit(1))).scalar_one_or_none()

    # --- Exists checks -------------------------------------------------------
    async def email_exists(
        self, org_id: int, email: str, *, exclude_user_id: int | None = None
    ) -> bool:
        """Return whether an active user already uses ``email`` in ``org_id``."""
        stmt = select(User.id).where(
            User.org_id == org_id, User.email == email, User.deleted_at.is_(None)
        )
        if exclude_user_id is not None:
            stmt = stmt.where(User.id != exclude_user_id)
        return (await self.session.execute(stmt.limit(1))).first() is not None

    async def mobile_exists(
        self,
        org_id: int,
        mobile_country_code: str,
        mobile_number: str,
        *,
        exclude_user_id: int | None = None,
    ) -> bool:
        """Return whether an active user already uses this mobile in ``org_id``."""
        stmt = select(User.id).where(
            User.org_id == org_id,
            User.mobile_country_code == mobile_country_code,
            User.mobile_number == mobile_number,
            User.deleted_at.is_(None),
        )
        if exclude_user_id is not None:
            stmt = stmt.where(User.id != exclude_user_id)
        return (await self.session.execute(stmt.limit(1))).first() is not None

    async def employee_is_mapped(
        self, org_id: int, employee_id: int, *, exclude_user_id: int | None = None
    ) -> bool:
        """Return whether ``employee_id`` is already linked to another active user."""
        stmt = select(User.id).where(
            User.org_id == org_id,
            User.employee_id == employee_id,
            User.deleted_at.is_(None),
        )
        if exclude_user_id is not None:
            stmt = stmt.where(User.id != exclude_user_id)
        return (await self.session.execute(stmt.limit(1))).first() is not None

    # --- Search / pagination -------------------------------------------------
    @staticmethod
    def _conditions(
        org_id: int,
        *,
        search: str | None,
        is_active: bool | None,
        is_super_admin: bool | None,
        has_employee: bool | None,
        include_deleted: bool,
    ) -> list:
        conds: list = [User.org_id == org_id]
        if not include_deleted:
            conds.append(User.deleted_at.is_(None))
        if is_active is not None:
            conds.append(User.is_active.is_(is_active))
        if is_super_admin is not None:
            conds.append(User.is_super_admin.is_(is_super_admin))
        if has_employee is True:
            conds.append(User.employee_id.is_not(None))
        elif has_employee is False:
            conds.append(User.employee_id.is_(None))
        if search:
            like = f"%{search.strip()}%"
            conds.append(
                or_(
                    User.name.ilike(like),
                    User.email.ilike(like),
                    User.mobile_number.ilike(like),
                )
            )
        return conds

    async def search(
        self,
        org_id: int,
        *,
        search: str | None = None,
        is_active: bool | None = None,
        is_super_admin: bool | None = None,
        has_employee: bool | None = None,
        include_deleted: bool = False,
        sort_by: str | None = "created_at",
        sort_order: SortOrder | str = SortOrder.DESC,
        page: int = 1,
        page_size: int = 25,
    ) -> list[User]:
        """Return a filtered, sorted, paginated page of users in ``org_id``."""
        conds = self._conditions(
            org_id,
            search=search,
            is_active=is_active,
            is_super_admin=is_super_admin,
            has_employee=has_employee,
            include_deleted=include_deleted,
        )
        stmt = select(User).where(and_(*conds))
        stmt = apply_sorting(
            stmt, User, sort_by, sort_order, allowed=_USER_SORTS, default_sort_by="created_at"
        )
        stmt = stmt.limit(page_size).offset((page - 1) * page_size)
        return list((await self.session.execute(stmt)).scalars().all())

    async def search_count(
        self,
        org_id: int,
        *,
        search: str | None = None,
        is_active: bool | None = None,
        is_super_admin: bool | None = None,
        has_employee: bool | None = None,
        include_deleted: bool = False,
    ) -> int:
        """Return the total number of users matching the same filters as :meth:`search`."""
        conds = self._conditions(
            org_id,
            search=search,
            is_active=is_active,
            is_super_admin=is_super_admin,
            has_employee=has_employee,
            include_deleted=include_deleted,
        )
        stmt = select(func.count()).select_from(User).where(and_(*conds))
        return int((await self.session.execute(stmt)).scalar_one())


class RightsTemplateRepository(BaseRepository[RightsTemplate]):
    """CRUD, search, and lookup operations for ``rights_templates`` (roles)."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, RightsTemplate)

    async def get_active_by_id(self, template_id: int, org_id: int) -> RightsTemplate | None:
        """Return a non-deleted template by id within ``org_id``."""
        stmt = select(RightsTemplate).where(
            RightsTemplate.id == template_id,
            RightsTemplate.org_id == org_id,
            RightsTemplate.deleted_at.is_(None),
        )
        return (await self.session.execute(stmt.limit(1))).scalar_one_or_none()

    async def name_exists(
        self, org_id: int, name: str, *, exclude_id: int | None = None
    ) -> bool:
        """Return whether a non-deleted template already uses ``name`` in ``org_id``."""
        stmt = select(RightsTemplate.id).where(
            RightsTemplate.org_id == org_id,
            RightsTemplate.name == name,
            RightsTemplate.deleted_at.is_(None),
        )
        if exclude_id is not None:
            stmt = stmt.where(RightsTemplate.id != exclude_id)
        return (await self.session.execute(stmt.limit(1))).first() is not None

    async def search(
        self,
        org_id: int,
        *,
        search: str | None = None,
        include_deleted: bool = False,
        sort_by: str | None = "name",
        sort_order: SortOrder | str = SortOrder.ASC,
        page: int = 1,
        page_size: int = 25,
    ) -> list[RightsTemplate]:
        """Return a filtered, sorted, paginated page of templates in ``org_id``."""
        conds: list = [RightsTemplate.org_id == org_id]
        if not include_deleted:
            conds.append(RightsTemplate.deleted_at.is_(None))
        if search:
            conds.append(RightsTemplate.name.ilike(f"%{search.strip()}%"))
        stmt = select(RightsTemplate).where(and_(*conds))
        stmt = apply_sorting(
            stmt, RightsTemplate, sort_by, sort_order, allowed=_ROLE_SORTS, default_sort_by="name"
        )
        stmt = stmt.limit(page_size).offset((page - 1) * page_size)
        return list((await self.session.execute(stmt)).scalars().all())

    async def search_count(
        self, org_id: int, *, search: str | None = None, include_deleted: bool = False
    ) -> int:
        """Return the total number of templates matching :meth:`search`."""
        conds: list = [RightsTemplate.org_id == org_id]
        if not include_deleted:
            conds.append(RightsTemplate.deleted_at.is_(None))
        if search:
            conds.append(RightsTemplate.name.ilike(f"%{search.strip()}%"))
        stmt = select(func.count()).select_from(RightsTemplate).where(and_(*conds))
        return int((await self.session.execute(stmt)).scalar_one())

    async def permission_count(self, template_id: int) -> int:
        """Return the number of permission rows attached to a template."""
        stmt = (
            select(func.count())
            .select_from(RightsTemplatePermission)
            .where(RightsTemplatePermission.template_id == template_id)
        )
        return int((await self.session.execute(stmt)).scalar_one())

    async def assigned_user_count(self, template_id: int) -> int:
        """Return the number of users assigned to a template."""
        stmt = (
            select(func.count())
            .select_from(UserTemplateAssignment)
            .where(UserTemplateAssignment.template_id == template_id)
        )
        return int((await self.session.execute(stmt)).scalar_one())

    async def has_assignments(self, template_id: int) -> bool:
        """Return whether any user is currently assigned this template."""
        stmt = select(UserTemplateAssignment.id).where(
            UserTemplateAssignment.template_id == template_id
        )
        return (await self.session.execute(stmt.limit(1))).first() is not None


class TemplatePermissionRepository(BaseRepository[RightsTemplatePermission]):
    """Operations for ``rights_template_permissions`` (role permissions)."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, RightsTemplatePermission)

    async def list_for_template(self, template_id: int) -> list[RightsTemplatePermission]:
        """Return all permission rows for a template."""
        stmt = select(RightsTemplatePermission).where(
            RightsTemplatePermission.template_id == template_id
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def get_for_feature(
        self, template_id: int, feature_key: str
    ) -> RightsTemplatePermission | None:
        """Return the permission row for ``(template_id, feature_key)`` if present."""
        stmt = select(RightsTemplatePermission).where(
            RightsTemplatePermission.template_id == template_id,
            RightsTemplatePermission.feature_key == feature_key,
        )
        return (await self.session.execute(stmt.limit(1))).scalar_one_or_none()

    async def delete_for_feature(self, template_id: int, feature_key: str) -> int:
        """Delete a single feature's permission row; returns rows removed."""
        stmt = delete(RightsTemplatePermission).where(
            RightsTemplatePermission.template_id == template_id,
            RightsTemplatePermission.feature_key == feature_key,
        )
        result = await self.session.execute(stmt.execution_options(synchronize_session=False))
        await self.session.flush()
        return int(result.rowcount or 0)

    async def delete_all_for_template(self, template_id: int) -> int:
        """Delete every permission row for a template (for replace-all); returns count."""
        stmt = delete(RightsTemplatePermission).where(
            RightsTemplatePermission.template_id == template_id
        )
        result = await self.session.execute(stmt.execution_options(synchronize_session=False))
        await self.session.flush()
        return int(result.rowcount or 0)


class UserTemplateAssignmentRepository(BaseRepository[UserTemplateAssignment]):
    """Operations for ``user_template_assignments`` (one template per user)."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, UserTemplateAssignment)

    async def get_for_user(self, user_id: int) -> UserTemplateAssignment | None:
        """Return the user's single template assignment, if any."""
        stmt = select(UserTemplateAssignment).where(UserTemplateAssignment.user_id == user_id)
        return (await self.session.execute(stmt.limit(1))).scalar_one_or_none()

    async def delete_for_user(self, user_id: int) -> int:
        """Remove the user's template assignment; returns rows removed."""
        stmt = delete(UserTemplateAssignment).where(UserTemplateAssignment.user_id == user_id)
        result = await self.session.execute(stmt.execution_options(synchronize_session=False))
        await self.session.flush()
        return int(result.rowcount or 0)


class UserCustomPermissionRepository(BaseRepository[UserCustomPermission]):
    """Operations for ``user_custom_permissions`` (per-user overrides)."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, UserCustomPermission)

    async def list_for_user(self, user_id: int) -> list[UserCustomPermission]:
        """Return all custom permission overrides for a user."""
        stmt = select(UserCustomPermission).where(UserCustomPermission.user_id == user_id)
        return list((await self.session.execute(stmt)).scalars().all())

    async def get_for_feature(
        self, user_id: int, feature_key: str
    ) -> UserCustomPermission | None:
        """Return the override for ``(user_id, feature_key)`` if present."""
        stmt = select(UserCustomPermission).where(
            UserCustomPermission.user_id == user_id,
            UserCustomPermission.feature_key == feature_key,
        )
        return (await self.session.execute(stmt.limit(1))).scalar_one_or_none()

    async def delete_for_feature(self, user_id: int, feature_key: str) -> int:
        """Delete a single override; returns rows removed."""
        stmt = delete(UserCustomPermission).where(
            UserCustomPermission.user_id == user_id,
            UserCustomPermission.feature_key == feature_key,
        )
        result = await self.session.execute(stmt.execution_options(synchronize_session=False))
        await self.session.flush()
        return int(result.rowcount or 0)

    async def delete_all_for_user(self, user_id: int) -> int:
        """Delete every override for a user (for replace-all); returns count."""
        stmt = delete(UserCustomPermission).where(UserCustomPermission.user_id == user_id)
        result = await self.session.execute(stmt.execution_options(synchronize_session=False))
        await self.session.flush()
        return int(result.rowcount or 0)


class UserBranchAccessRepository(BaseRepository[UserBranchAccess]):
    """Operations for ``user_branch_access`` (branch data scope)."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, UserBranchAccess)

    async def list_for_user(self, user_id: int) -> list[UserBranchAccess]:
        """Return all branch grants for a user."""
        stmt = select(UserBranchAccess).where(UserBranchAccess.user_id == user_id)
        return list((await self.session.execute(stmt)).scalars().all())

    async def branch_ids_for_user(self, user_id: int) -> list[int]:
        """Return the set of branch ids a user may access."""
        stmt = select(UserBranchAccess.branch_id).where(UserBranchAccess.user_id == user_id)
        return list((await self.session.execute(stmt)).scalars().all())

    async def exists(self, user_id: int, branch_id: int) -> bool:
        """Return whether the user already has access to ``branch_id``."""
        stmt = select(UserBranchAccess.id).where(
            UserBranchAccess.user_id == user_id, UserBranchAccess.branch_id == branch_id
        )
        return (await self.session.execute(stmt.limit(1))).first() is not None

    async def delete_for_branch(self, user_id: int, branch_id: int) -> int:
        """Revoke a single branch grant; returns rows removed."""
        stmt = delete(UserBranchAccess).where(
            UserBranchAccess.user_id == user_id, UserBranchAccess.branch_id == branch_id
        )
        result = await self.session.execute(stmt.execution_options(synchronize_session=False))
        await self.session.flush()
        return int(result.rowcount or 0)

    async def delete_all_for_user(self, user_id: int) -> int:
        """Revoke all branch grants for a user (for replace-all); returns count."""
        stmt = delete(UserBranchAccess).where(UserBranchAccess.user_id == user_id)
        result = await self.session.execute(stmt.execution_options(synchronize_session=False))
        await self.session.flush()
        return int(result.rowcount or 0)


class UserDepartmentAccessRepository(BaseRepository[UserDepartmentAccess]):
    """Operations for ``user_department_access`` (department data scope)."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, UserDepartmentAccess)

    async def list_for_user(self, user_id: int) -> list[UserDepartmentAccess]:
        """Return all department grants for a user."""
        stmt = select(UserDepartmentAccess).where(UserDepartmentAccess.user_id == user_id)
        return list((await self.session.execute(stmt)).scalars().all())

    async def department_ids_for_user(self, user_id: int) -> list[int]:
        """Return the set of department ids a user may access."""
        stmt = select(UserDepartmentAccess.department_id).where(
            UserDepartmentAccess.user_id == user_id
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def exists(self, user_id: int, department_id: int) -> bool:
        """Return whether the user already has access to ``department_id``."""
        stmt = select(UserDepartmentAccess.id).where(
            UserDepartmentAccess.user_id == user_id,
            UserDepartmentAccess.department_id == department_id,
        )
        return (await self.session.execute(stmt.limit(1))).first() is not None

    async def delete_for_department(self, user_id: int, department_id: int) -> int:
        """Revoke a single department grant; returns rows removed."""
        stmt = delete(UserDepartmentAccess).where(
            UserDepartmentAccess.user_id == user_id,
            UserDepartmentAccess.department_id == department_id,
        )
        result = await self.session.execute(stmt.execution_options(synchronize_session=False))
        await self.session.flush()
        return int(result.rowcount or 0)

    async def delete_all_for_user(self, user_id: int) -> int:
        """Revoke all department grants for a user (for replace-all); returns count."""
        stmt = delete(UserDepartmentAccess).where(UserDepartmentAccess.user_id == user_id)
        result = await self.session.execute(stmt.execution_options(synchronize_session=False))
        await self.session.flush()
        return int(result.rowcount or 0)


# ---------------------------------------------------------------------------
# Phase 2 — Multi-organization membership
# ---------------------------------------------------------------------------


class UserOrganizationMembershipRepository(BaseRepository[UserOrganizationMembership]):
    """Data-access operations for ``user_organization_memberships``.

    This repository is the *only* layer allowed to query the new junction table.
    All methods are read-biased (hot paths are ``get_org_ids_for_user`` and
    ``get_membership``); writes happen during org-invitation and deactivation
    flows (Phase 3 business logic).
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, UserOrganizationMembership)

    # --- Membership lookup ---------------------------------------------------

    async def get_membership(
        self, user_id: int, org_id: int
    ) -> UserOrganizationMembership | None:
        """Return the membership row for ``(user_id, org_id)``, or ``None``."""
        stmt = select(UserOrganizationMembership).where(
            UserOrganizationMembership.user_id == user_id,
            UserOrganizationMembership.org_id == org_id,
        )
        return (await self.session.execute(stmt.limit(1))).scalar_one_or_none()

    async def is_active_member(self, user_id: int, org_id: int) -> bool:
        """Return ``True`` iff the user has an active membership in ``org_id``."""
        stmt = select(UserOrganizationMembership.id).where(
            UserOrganizationMembership.user_id == user_id,
            UserOrganizationMembership.org_id == org_id,
            UserOrganizationMembership.is_active.is_(True),
        )
        return (await self.session.execute(stmt.limit(1))).first() is not None

    # --- Org-ID list for a user (token issuance + /my-organizations) ---------

    async def get_org_ids_for_user(
        self, user_id: int, *, active_only: bool = True
    ) -> list[int]:
        """Return every ``org_id`` the user is a member of.

        ``active_only=True`` (default) excludes deactivated memberships, which
        is the correct behaviour for token issuance and the org-switch endpoint.
        ``active_only=False`` is used by admin/audit queries.
        """
        stmt = select(UserOrganizationMembership.org_id).where(
            UserOrganizationMembership.user_id == user_id,
        )
        if active_only:
            stmt = stmt.where(UserOrganizationMembership.is_active.is_(True))
        return list((await self.session.execute(stmt)).scalars().all())

    async def get_memberships_for_user(
        self, user_id: int, *, active_only: bool = True
    ) -> list[UserOrganizationMembership]:
        """Return full membership rows for a user (for the ``/my-organizations`` response)."""
        stmt = select(UserOrganizationMembership).where(
            UserOrganizationMembership.user_id == user_id,
        )
        if active_only:
            stmt = stmt.where(UserOrganizationMembership.is_active.is_(True))
        return list((await self.session.execute(stmt)).scalars().all())

    # --- Org membership list (admin: who belongs to an org?) -----------------

    async def get_memberships_for_org(
        self, org_id: int, *, active_only: bool = True
    ) -> list[UserOrganizationMembership]:
        """Return all membership rows for ``org_id`` (admin enumeration)."""
        stmt = select(UserOrganizationMembership).where(
            UserOrganizationMembership.org_id == org_id,
        )
        if active_only:
            stmt = stmt.where(UserOrganizationMembership.is_active.is_(True))
        return list((await self.session.execute(stmt)).scalars().all())

    async def count_active_members(self, org_id: int) -> int:
        """Return the number of active members in ``org_id``."""
        stmt = (
            select(func.count())
            .select_from(UserOrganizationMembership)
            .where(
                UserOrganizationMembership.org_id == org_id,
                UserOrganizationMembership.is_active.is_(True),
            )
        )
        return int((await self.session.execute(stmt)).scalar_one())

    # --- Writes (used by service layer in Phase 3) ---------------------------

    async def create_membership(
        self,
        *,
        user_id: int,
        org_id: int,
        is_primary: bool = False,
        invited_by: int | None = None,
    ) -> UserOrganizationMembership:
        """Insert a new active membership row and return it (flushed, not committed)."""
        return await self.create(
            {
                "user_id": user_id,
                "org_id": org_id,
                "is_primary": is_primary,
                "is_active": True,
                "invited_by": invited_by,
            }
        )

    async def deactivate_membership(
        self, user_id: int, org_id: int
    ) -> UserOrganizationMembership | None:
        """Set ``is_active=False`` on the row and flush.

        Returns the updated row, or ``None`` if the membership did not exist.
        The row is retained for audit purposes — it is never hard-deleted.
        """
        row = await self.get_membership(user_id, org_id)
        if row is None:
            return None
        row.is_active = False
        self.session.add(row)
        await self.session.flush()
        return row
