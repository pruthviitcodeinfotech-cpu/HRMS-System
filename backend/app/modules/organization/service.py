"""Organization / Branch / Department / Designation — service layer.

Business logic and transaction orchestration for the organizational hierarchy.
Enforces the API Contract §4/§5/§9 rules: global ``org_code`` uniqueness, per-org
uniqueness of department/designation names among non-deleted rows, tenant
isolation, and the referential guards that block deactivating a
branch/department/designation still referenced by active employees.

Every mutating operation writes one immutable Activity-Log row via
:class:`AuditService` inside the same transaction, so the audit trail and the
business mutation commit (or roll back) atomically.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.audit.constants import ActionType
from app.modules.audit.service import AuditService
from app.modules.employee.models.organization import (
    Branch,
    Department,
    Designation,
    Organization,
)
from app.modules.organization.constants import AUDIT_MODULE
from app.modules.organization.exceptions import (
    BranchInUseException,
    BranchNotFoundException,
    DepartmentInUseException,
    DepartmentNameExistsException,
    DepartmentNotFoundException,
    DesignationInUseException,
    DesignationNameExistsException,
    DesignationNotFoundException,
    OrganizationCodeExistsException,
    OrganizationNotFoundException,
)
from app.modules.organization.repository import (
    BranchRepository,
    DepartmentRepository,
    DesignationRepository,
    OrganizationRepository,
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
from app.modules.rbac.repository import UserRepository
from app.shared.base.service import BaseService


class _OrgBaseService(BaseService):
    """Shared audit + actor-name helpers for the organizational services."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)
        self.users = UserRepository(session)
        self.audit = AuditService(session)

    async def _actor_name(self, org_id: int, actor_id: int) -> str:
        """Resolve the acting user's display name for the audit trail."""
        user = await self.users.get_active_by_id(actor_id, org_id)
        name = getattr(user, "name", None)
        return name if isinstance(name, str) and name else f"user #{actor_id}"

    async def _audit(
        self,
        *,
        org_id: int,
        actor_id: int,
        action_type: ActionType,
        sub_module: str,
        title: str,
        description: str,
    ) -> None:
        """Write a single Activity-Log row (flushed within the caller's transaction)."""
        await self.audit.record(
            org_id=org_id,
            module=AUDIT_MODULE,
            sub_module=sub_module,
            action_type=action_type,
            title=title,
            description=description,
            performed_by_user_id=actor_id,
            performed_by_name=await self._actor_name(org_id, actor_id),
        )


class OrganizationService(_OrgBaseService):
    """Business rules for the tenant root (``organizations``) — super-admin scoped."""

    _SUB_MODULE = "organization"

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)
        self.orgs = OrganizationRepository(session)

    async def create_organization(
        self, *, actor_id: int, data: OrganizationCreateRequest
    ) -> OrganizationSchema:
        """Provision a new organization (super-admin). Enforces global ``org_code``."""
        if await self.orgs.code_exists(data.org_code):
            raise OrganizationCodeExistsException()

        payload = data.model_dump()

        async with self.transaction():
            org = await self.orgs.create(payload)
            await self._audit(
                org_id=org.org_id,
                actor_id=actor_id,
                action_type=ActionType.INSERT,
                sub_module=self._SUB_MODULE,
                title="Organization created",
                description=f"Created organization '{org.org_name}' (code '{org.org_code}').",
            )
        return OrganizationSchema.model_validate(org)

    async def list_organizations(
        self, *, query: OrganizationSearchQuery
    ) -> OrganizationListResponse:
        """List organizations with search / filter / pagination (super-admin)."""
        rows = await self.orgs.search(
            search=query.search,
            is_active=query.is_active,
            include_deleted=query.include_deleted,
            sort_by=query.sort_by,
            sort_order=query.sort_order or "asc",
            page=query.page,
            page_size=query.page_size,
        )
        total = await self.orgs.search_count(
            search=query.search,
            is_active=query.is_active,
            include_deleted=query.include_deleted,
        )
        items = [OrganizationSchema.model_validate(row) for row in rows]
        return OrganizationListResponse.build(
            items=items, page=query.page, page_size=query.page_size, total_records=total
        )

    async def get_organization(self, *, org_id: int) -> OrganizationSchema:
        """Return a single organization by id."""
        org = await self._get_or_404(org_id)
        return OrganizationSchema.model_validate(org)

    async def update_organization(
        self, *, actor_id: int, org_id: int, data: OrganizationUpdateRequest
    ) -> OrganizationSchema:
        """Update an organization profile. Re-checks ``org_code`` uniqueness on change."""
        org = await self._get_or_404(org_id)
        updates = data.model_dump(exclude_unset=True)

        if "org_code" in updates and updates["org_code"] != org.org_code:
            if await self.orgs.code_exists(updates["org_code"], exclude_org_id=org_id):
                raise OrganizationCodeExistsException()

        async with self.transaction():
            org = await self.orgs.update(org, updates)
            await self._audit(
                org_id=org.org_id,
                actor_id=actor_id,
                action_type=ActionType.UPDATE,
                sub_module=self._SUB_MODULE,
                title="Organization updated",
                description=f"Updated organization '{org.org_name}'.",
            )
        return OrganizationSchema.model_validate(org)

    async def set_active(
        self, *, actor_id: int, org_id: int, is_active: bool
    ) -> OrganizationSchema:
        """Activate / deactivate an organization (idempotent, super-admin)."""
        org = await self._get_or_404(org_id)
        if org.is_active == is_active:
            return OrganizationSchema.model_validate(org)

        async with self.transaction():
            org = await self.orgs.update(org, {"is_active": is_active})
            verb = "activated" if is_active else "deactivated"
            await self._audit(
                org_id=org.org_id,
                actor_id=actor_id,
                action_type=ActionType.UPDATE,
                sub_module=self._SUB_MODULE,
                title=f"Organization {verb}",
                description=f"Organization '{org.org_name}' {verb}.",
            )
        return OrganizationSchema.model_validate(org)

    async def _get_or_404(self, org_id: int) -> Organization:
        org = await self.orgs.get_active(org_id)
        if org is None:
            raise OrganizationNotFoundException()
        return org


class BranchService(_OrgBaseService):
    """Business rules for ``branches`` (tenant-scoped, feature key ``branch``)."""

    _SUB_MODULE = "branch"

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)
        self.branches = BranchRepository(session)

    async def create_branch(
        self, *, org_id: int, actor_id: int, data: BranchCreateRequest
    ) -> BranchSchema:
        """Create a branch. ``branch_name`` has no DB uniqueness (Contract §5.1)."""
        payload = data.model_dump()
        payload["org_id"] = org_id

        async with self.transaction():
            branch = await self.branches.create(payload)
            await self._audit(
                org_id=org_id,
                actor_id=actor_id,
                action_type=ActionType.INSERT,
                sub_module=self._SUB_MODULE,
                title="Branch created",
                description=f"Created branch '{branch.branch_name}'.",
            )
        return BranchSchema.model_validate(branch)

    async def list_branches(
        self,
        *,
        org_id: int,
        query: BranchSearchQuery,
        allowed_branch_ids: list[int] | None = None,
    ) -> BranchListResponse:
        """List branches with search / filter / sort, honouring branch data scope."""
        rows = await self.branches.search(
            org_id,
            search=query.search,
            is_active=query.is_active,
            include_deleted=query.include_deleted,
            branch_scope=allowed_branch_ids,
            sort_by=query.sort_by,
            sort_order=query.sort_order or "asc",
            page=query.page,
            page_size=query.page_size,
        )
        total = await self.branches.search_count(
            org_id,
            search=query.search,
            is_active=query.is_active,
            include_deleted=query.include_deleted,
            branch_scope=allowed_branch_ids,
        )
        items = [BranchSchema.model_validate(row) for row in rows]
        return BranchListResponse.build(
            items=items, page=query.page, page_size=query.page_size, total_records=total
        )

    async def get_branch(self, *, org_id: int, branch_id: int) -> BranchSchema:
        """Return a single branch scoped to the caller's organization."""
        branch = await self._get_or_404(org_id, branch_id)
        return BranchSchema.model_validate(branch)

    async def update_branch(
        self, *, org_id: int, actor_id: int, branch_id: int, data: BranchUpdateRequest
    ) -> BranchSchema:
        """Update a branch's master attributes."""
        branch = await self._get_or_404(org_id, branch_id)
        updates = data.model_dump(exclude_unset=True)

        async with self.transaction():
            branch = await self.branches.update(branch, updates)
            await self._audit(
                org_id=org_id,
                actor_id=actor_id,
                action_type=ActionType.UPDATE,
                sub_module=self._SUB_MODULE,
                title="Branch updated",
                description=f"Updated branch '{branch.branch_name}'.",
            )
        return BranchSchema.model_validate(branch)

    async def set_active(
        self, *, org_id: int, actor_id: int, branch_id: int, is_active: bool
    ) -> BranchSchema:
        """Activate / deactivate a branch. Deactivation is blocked when in use."""
        branch = await self._get_or_404(org_id, branch_id)

        if not is_active and await self.branches.has_active_employees(org_id, branch_id):
            raise BranchInUseException()

        if branch.is_active == is_active:
            return BranchSchema.model_validate(branch)

        async with self.transaction():
            branch = await self.branches.update(branch, {"is_active": is_active})
            verb = "activated" if is_active else "deactivated"
            await self._audit(
                org_id=org_id,
                actor_id=actor_id,
                action_type=ActionType.UPDATE,
                sub_module=self._SUB_MODULE,
                title=f"Branch {verb}",
                description=f"Branch '{branch.branch_name}' {verb}.",
            )
        return BranchSchema.model_validate(branch)

    async def _get_or_404(self, org_id: int, branch_id: int) -> Branch:
        branch = await self.branches.get_by_id_in_org(org_id, branch_id)
        if branch is None:
            raise BranchNotFoundException()
        return branch


class DepartmentService(_OrgBaseService):
    """Business rules for ``departments`` (tenant-scoped, feature key ``department``)."""

    _SUB_MODULE = "department"

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)
        self.departments = DepartmentRepository(session)

    async def create_department(
        self, *, org_id: int, actor_id: int, data: DepartmentCreateRequest
    ) -> DepartmentSchema:
        """Create a department. Enforces per-org name uniqueness (non-deleted)."""
        if await self.departments.name_exists(org_id, data.dept_name):
            raise DepartmentNameExistsException()

        payload = data.model_dump()
        payload["org_id"] = org_id
        payload["created_by"] = actor_id

        async with self.transaction():
            dept = await self.departments.create(payload)
            await self._audit(
                org_id=org_id,
                actor_id=actor_id,
                action_type=ActionType.INSERT,
                sub_module=self._SUB_MODULE,
                title="Department created",
                description=f"Created department '{dept.dept_name}'.",
            )
        return DepartmentSchema.model_validate(dept)

    async def list_departments(
        self, *, org_id: int, query: DepartmentSearchQuery
    ) -> DepartmentListResponse:
        """List departments with search / filter / sort / pagination."""
        rows = await self.departments.search(
            org_id,
            search=query.search,
            is_active=query.is_active,
            include_deleted=query.include_deleted,
            sort_by=query.sort_by,
            sort_order=query.sort_order or "asc",
            page=query.page,
            page_size=query.page_size,
        )
        total = await self.departments.search_count(
            org_id,
            search=query.search,
            is_active=query.is_active,
            include_deleted=query.include_deleted,
        )
        items = [DepartmentSchema.model_validate(row) for row in rows]
        return DepartmentListResponse.build(
            items=items, page=query.page, page_size=query.page_size, total_records=total
        )

    async def get_department(self, *, org_id: int, dept_id: int) -> DepartmentSchema:
        """Return a single department scoped to the caller's organization."""
        dept = await self._get_or_404(org_id, dept_id)
        return DepartmentSchema.model_validate(dept)

    async def update_department(
        self, *, org_id: int, actor_id: int, dept_id: int, data: DepartmentUpdateRequest
    ) -> DepartmentSchema:
        """Update a department. Re-checks name uniqueness on change."""
        dept = await self._get_or_404(org_id, dept_id)
        updates = data.model_dump(exclude_unset=True)

        if "dept_name" in updates and updates["dept_name"] != dept.dept_name:
            if await self.departments.name_exists(
                org_id, updates["dept_name"], exclude_dept_id=dept_id
            ):
                raise DepartmentNameExistsException()

        async with self.transaction():
            dept = await self.departments.update(dept, updates)
            await self._audit(
                org_id=org_id,
                actor_id=actor_id,
                action_type=ActionType.UPDATE,
                sub_module=self._SUB_MODULE,
                title="Department updated",
                description=f"Updated department '{dept.dept_name}'.",
            )
        return DepartmentSchema.model_validate(dept)

    async def set_active(
        self, *, org_id: int, actor_id: int, dept_id: int, is_active: bool
    ) -> DepartmentSchema:
        """Activate / deactivate a department. Deactivation is blocked when in use."""
        dept = await self._get_or_404(org_id, dept_id)

        if not is_active and await self.departments.has_active_employees(org_id, dept_id):
            raise DepartmentInUseException()

        if dept.is_active == is_active:
            return DepartmentSchema.model_validate(dept)

        async with self.transaction():
            dept = await self.departments.update(dept, {"is_active": is_active})
            verb = "activated" if is_active else "deactivated"
            await self._audit(
                org_id=org_id,
                actor_id=actor_id,
                action_type=ActionType.UPDATE,
                sub_module=self._SUB_MODULE,
                title=f"Department {verb}",
                description=f"Department '{dept.dept_name}' {verb}.",
            )
        return DepartmentSchema.model_validate(dept)

    async def delete_department(
        self, *, org_id: int, actor_id: int, dept_id: int
    ) -> DepartmentSchema:
        """Soft-delete a department. Blocked if referenced by active employees."""
        dept = await self._get_or_404(org_id, dept_id)

        if await self.departments.has_active_employees(org_id, dept_id):
            raise DepartmentInUseException()

        async with self.transaction():
            dept = await self.departments.update(dept, {"is_deleted": True})
            await self._audit(
                org_id=org_id,
                actor_id=actor_id,
                action_type=ActionType.DELETE,
                sub_module=self._SUB_MODULE,
                title="Department deleted",
                description=f"Deleted department '{dept.dept_name}'.",
            )
        return DepartmentSchema.model_validate(dept)

    async def _get_or_404(self, org_id: int, dept_id: int) -> Department:
        dept = await self.departments.get_by_id_in_org(org_id, dept_id)
        if dept is None:
            raise DepartmentNotFoundException()
        return dept


class DesignationService(_OrgBaseService):
    """Business rules for ``designations`` (tenant-scoped, feature key ``designation``)."""

    _SUB_MODULE = "designation"

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)
        self.designations = DesignationRepository(session)

    async def create_designation(
        self, *, org_id: int, actor_id: int, data: DesignationCreateRequest
    ) -> DesignationSchema:
        """Create a designation. Enforces per-org name uniqueness (non-deleted)."""
        if await self.designations.name_exists(org_id, data.designation_name):
            raise DesignationNameExistsException()

        payload = data.model_dump()
        payload["org_id"] = org_id
        payload["created_by"] = actor_id

        async with self.transaction():
            designation = await self.designations.create(payload)
            await self._audit(
                org_id=org_id,
                actor_id=actor_id,
                action_type=ActionType.INSERT,
                sub_module=self._SUB_MODULE,
                title="Designation created",
                description=f"Created designation '{designation.designation_name}'.",
            )
        return DesignationSchema.model_validate(designation)

    async def list_designations(
        self, *, org_id: int, query: DesignationSearchQuery
    ) -> DesignationListResponse:
        """List designations with search / filter / sort / pagination."""
        rows = await self.designations.search(
            org_id,
            search=query.search,
            is_active=query.is_active,
            include_deleted=query.include_deleted,
            sort_by=query.sort_by,
            sort_order=query.sort_order or "asc",
            page=query.page,
            page_size=query.page_size,
        )
        total = await self.designations.search_count(
            org_id,
            search=query.search,
            is_active=query.is_active,
            include_deleted=query.include_deleted,
        )
        items = [DesignationSchema.model_validate(row) for row in rows]
        return DesignationListResponse.build(
            items=items, page=query.page, page_size=query.page_size, total_records=total
        )

    async def get_designation(self, *, org_id: int, designation_id: int) -> DesignationSchema:
        """Return a single designation scoped to the caller's organization."""
        designation = await self._get_or_404(org_id, designation_id)
        return DesignationSchema.model_validate(designation)

    async def update_designation(
        self,
        *,
        org_id: int,
        actor_id: int,
        designation_id: int,
        data: DesignationUpdateRequest,
    ) -> DesignationSchema:
        """Update a designation. Re-checks name uniqueness on change."""
        designation = await self._get_or_404(org_id, designation_id)
        updates = data.model_dump(exclude_unset=True)

        if (
            "designation_name" in updates
            and updates["designation_name"] != designation.designation_name
        ):
            if await self.designations.name_exists(
                org_id, updates["designation_name"], exclude_designation_id=designation_id
            ):
                raise DesignationNameExistsException()

        async with self.transaction():
            designation = await self.designations.update(designation, updates)
            await self._audit(
                org_id=org_id,
                actor_id=actor_id,
                action_type=ActionType.UPDATE,
                sub_module=self._SUB_MODULE,
                title="Designation updated",
                description=f"Updated designation '{designation.designation_name}'.",
            )
        return DesignationSchema.model_validate(designation)

    async def set_active(
        self, *, org_id: int, actor_id: int, designation_id: int, is_active: bool
    ) -> DesignationSchema:
        """Activate / deactivate a designation. Deactivation is blocked when in use."""
        designation = await self._get_or_404(org_id, designation_id)

        if not is_active and await self.designations.has_active_employees(org_id, designation_id):
            raise DesignationInUseException()

        if designation.is_active == is_active:
            return DesignationSchema.model_validate(designation)

        async with self.transaction():
            designation = await self.designations.update(designation, {"is_active": is_active})
            verb = "activated" if is_active else "deactivated"
            await self._audit(
                org_id=org_id,
                actor_id=actor_id,
                action_type=ActionType.UPDATE,
                sub_module=self._SUB_MODULE,
                title=f"Designation {verb}",
                description=f"Designation '{designation.designation_name}' {verb}.",
            )
        return DesignationSchema.model_validate(designation)

    async def delete_designation(
        self, *, org_id: int, actor_id: int, designation_id: int
    ) -> DesignationSchema:
        """Soft-delete a designation. Blocked if referenced by active employees."""
        designation = await self._get_or_404(org_id, designation_id)

        if await self.designations.has_active_employees(org_id, designation_id):
            raise DesignationInUseException()

        async with self.transaction():
            designation = await self.designations.update(designation, {"is_deleted": True})
            await self._audit(
                org_id=org_id,
                actor_id=actor_id,
                action_type=ActionType.DELETE,
                sub_module=self._SUB_MODULE,
                title="Designation deleted",
                description=f"Deleted designation '{designation.designation_name}'.",
            )
        return DesignationSchema.model_validate(designation)

    async def _get_or_404(self, org_id: int, designation_id: int) -> Designation:
        designation = await self.designations.get_by_id_in_org(org_id, designation_id)
        if designation is None:
            raise DesignationNotFoundException()
        return designation


__all__ = [
    "OrganizationService",
    "BranchService",
    "DepartmentService",
    "DesignationService",
]
