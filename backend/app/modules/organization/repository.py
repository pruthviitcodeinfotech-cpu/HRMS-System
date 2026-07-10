"""Organization / Branch / Department / Designation — data-access layer.

One focused repository per aggregate, each extending
:class:`app.shared.base.repository.BaseRepository` and operating on the existing
Employee-Management organizational models
(:mod:`app.modules.employee.models.organization`). **Database operations only** —
no business rules; the service owns the commit boundary (methods only flush).

Every branch/department/designation query is org-scoped (``org_id``) and, by
default, excludes soft-deleted rows (``is_deleted``). Organizations are the tenant
root and therefore *not* org-scoped; their list surface is super-admin only.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants.enums import SortOrder
from app.modules.employee.models.employee import Employee
from app.modules.employee.models.organization import (
    Branch,
    Department,
    Designation,
    Organization,
)
from app.modules.organization.constants import (
    ACTIVE_EMPLOYMENT_STATUS,
    BRANCH_SORTS,
    DEPARTMENT_SORTS,
    DESIGNATION_SORTS,
    ORGANIZATION_SORTS,
)
from app.shared.base.repository import BaseRepository
from app.shared.utils.query import apply_sorting


class OrganizationRepository(BaseRepository[Organization]):
    """CRUD, search, and uniqueness checks for ``organizations`` (tenant root)."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Organization)

    async def get_active(self, org_id: int) -> Organization | None:
        """Return a non-deleted organization by id, or ``None``."""
        stmt = select(Organization).where(
            Organization.org_id == org_id,
            Organization.is_deleted.is_(False),
        )
        return (await self.session.execute(stmt.limit(1))).scalar_one_or_none()

    async def code_exists(self, org_code: str, *, exclude_org_id: int | None = None) -> bool:
        """Return whether ``org_code`` is already registered (globally unique)."""
        stmt = select(Organization.org_id).where(Organization.org_code == org_code)
        if exclude_org_id is not None:
            stmt = stmt.where(Organization.org_id != exclude_org_id)
        return (await self.session.execute(stmt.limit(1))).first() is not None

    @staticmethod
    def _conditions(
        *,
        search: str | None,
        is_active: bool | None,
        include_deleted: bool,
    ) -> list[Any]:
        conds: list[Any] = []
        if not include_deleted:
            conds.append(Organization.is_deleted.is_(False))
        if is_active is not None:
            conds.append(Organization.is_active.is_(is_active))
        if search:
            like = f"%{search.strip()}%"
            conds.append(
                or_(
                    Organization.org_code.ilike(like),
                    Organization.org_name.ilike(like),
                )
            )
        return conds

    async def search(
        self,
        *,
        search: str | None = None,
        is_active: bool | None = None,
        include_deleted: bool = False,
        sort_by: str | None = None,
        sort_order: SortOrder | str = SortOrder.ASC,
        page: int = 1,
        page_size: int = 25,
    ) -> list[Organization]:
        """Return a filtered, sorted, paginated page of organizations (super-admin)."""
        conds = self._conditions(
            search=search, is_active=is_active, include_deleted=include_deleted
        )
        stmt = select(Organization)
        if conds:
            stmt = stmt.where(and_(*conds))
        stmt = apply_sorting(
            stmt,
            Organization,
            sort_by,
            sort_order,
            allowed=ORGANIZATION_SORTS,
            default_sort_by="created_at",
        )
        stmt = stmt.limit(page_size).offset((page - 1) * page_size)
        return list((await self.session.execute(stmt)).scalars().all())

    async def search_count(
        self,
        *,
        search: str | None = None,
        is_active: bool | None = None,
        include_deleted: bool = False,
    ) -> int:
        """Return the total number of organizations matching :meth:`search` filters."""
        conds = self._conditions(
            search=search, is_active=is_active, include_deleted=include_deleted
        )
        stmt = select(func.count()).select_from(Organization)
        if conds:
            stmt = stmt.where(and_(*conds))
        return int((await self.session.execute(stmt)).scalar_one())


class BranchRepository(BaseRepository[Branch]):
    """CRUD, search, and referential checks for ``branches`` (org-scoped)."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Branch)

    async def get_by_id_in_org(self, org_id: int, branch_id: int) -> Branch | None:
        """Return a non-deleted branch by id within ``org_id``, or ``None``."""
        stmt = select(Branch).where(
            Branch.branch_id == branch_id,
            Branch.org_id == org_id,
            Branch.is_deleted.is_(False),
        )
        return (await self.session.execute(stmt.limit(1))).scalar_one_or_none()

    async def has_active_employees(self, org_id: int, branch_id: int) -> bool:
        """Return whether any active, non-deleted employee references this branch."""
        stmt = select(Employee.employee_id).where(
            Employee.org_id == org_id,
            Employee.master_branch_id == branch_id,
            Employee.is_deleted.is_(False),
            Employee.employment_status == ACTIVE_EMPLOYMENT_STATUS,
        )
        return (await self.session.execute(stmt.limit(1))).first() is not None

    @staticmethod
    def _conditions(
        org_id: int,
        *,
        search: str | None,
        is_active: bool | None,
        include_deleted: bool,
        branch_scope: list[int] | None,
    ) -> list[Any]:
        conds: list[Any] = [Branch.org_id == org_id]
        if not include_deleted:
            conds.append(Branch.is_deleted.is_(False))
        if is_active is not None:
            conds.append(Branch.is_active.is_(is_active))
        if branch_scope is not None:
            conds.append(Branch.branch_id.in_(branch_scope))
        if search:
            like = f"%{search.strip()}%"
            conds.append(
                or_(
                    Branch.branch_name.ilike(like),
                    Branch.city.ilike(like),
                )
            )
        return conds

    async def search(
        self,
        org_id: int,
        *,
        search: str | None = None,
        is_active: bool | None = None,
        include_deleted: bool = False,
        branch_scope: list[int] | None = None,
        sort_by: str | None = None,
        sort_order: SortOrder | str = SortOrder.ASC,
        page: int = 1,
        page_size: int = 25,
    ) -> list[Branch]:
        """Return a filtered, sorted, paginated page of branches in ``org_id``."""
        conds = self._conditions(
            org_id,
            search=search,
            is_active=is_active,
            include_deleted=include_deleted,
            branch_scope=branch_scope,
        )
        stmt = select(Branch).where(and_(*conds))
        stmt = apply_sorting(
            stmt,
            Branch,
            sort_by,
            sort_order,
            allowed=BRANCH_SORTS,
            default_sort_by="branch_name",
        )
        stmt = stmt.limit(page_size).offset((page - 1) * page_size)
        return list((await self.session.execute(stmt)).scalars().all())

    async def search_count(
        self,
        org_id: int,
        *,
        search: str | None = None,
        is_active: bool | None = None,
        include_deleted: bool = False,
        branch_scope: list[int] | None = None,
    ) -> int:
        """Return the total number of branches matching :meth:`search` filters."""
        conds = self._conditions(
            org_id,
            search=search,
            is_active=is_active,
            include_deleted=include_deleted,
            branch_scope=branch_scope,
        )
        stmt = select(func.count()).select_from(Branch).where(and_(*conds))
        return int((await self.session.execute(stmt)).scalar_one())


class DepartmentRepository(BaseRepository[Department]):
    """CRUD, search, uniqueness, and referential checks for ``departments``."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Department)

    async def get_by_id_in_org(self, org_id: int, dept_id: int) -> Department | None:
        """Return a non-deleted department by id within ``org_id``, or ``None``."""
        stmt = select(Department).where(
            Department.dept_id == dept_id,
            Department.org_id == org_id,
            Department.is_deleted.is_(False),
        )
        return (await self.session.execute(stmt.limit(1))).scalar_one_or_none()

    async def name_exists(
        self, org_id: int, dept_name: str, *, exclude_dept_id: int | None = None
    ) -> bool:
        """Return whether a non-deleted department already uses ``dept_name`` in ``org_id``.

        Mirrors the partial unique index ``uq_departments_org_id_dept_name``.
        """
        stmt = select(Department.dept_id).where(
            Department.org_id == org_id,
            func.lower(Department.dept_name) == dept_name.strip().lower(),
            Department.is_deleted.is_(False),
        )
        if exclude_dept_id is not None:
            stmt = stmt.where(Department.dept_id != exclude_dept_id)
        return (await self.session.execute(stmt.limit(1))).first() is not None

    async def has_active_employees(self, org_id: int, dept_id: int) -> bool:
        """Return whether any active, non-deleted employee references this department."""
        stmt = select(Employee.employee_id).where(
            Employee.org_id == org_id,
            Employee.dept_id == dept_id,
            Employee.is_deleted.is_(False),
            Employee.employment_status == ACTIVE_EMPLOYMENT_STATUS,
        )
        return (await self.session.execute(stmt.limit(1))).first() is not None

    @staticmethod
    def _conditions(
        org_id: int,
        *,
        search: str | None,
        is_active: bool | None,
        include_deleted: bool,
    ) -> list[Any]:
        conds: list[Any] = [Department.org_id == org_id]
        if not include_deleted:
            conds.append(Department.is_deleted.is_(False))
        if is_active is not None:
            conds.append(Department.is_active.is_(is_active))
        if search:
            like = f"%{search.strip()}%"
            conds.append(Department.dept_name.ilike(like))
        return conds

    async def search(
        self,
        org_id: int,
        *,
        search: str | None = None,
        is_active: bool | None = None,
        include_deleted: bool = False,
        sort_by: str | None = None,
        sort_order: SortOrder | str = SortOrder.ASC,
        page: int = 1,
        page_size: int = 25,
    ) -> list[Department]:
        """Return a filtered, sorted, paginated page of departments in ``org_id``."""
        conds = self._conditions(
            org_id, search=search, is_active=is_active, include_deleted=include_deleted
        )
        stmt = select(Department).where(and_(*conds))
        stmt = apply_sorting(
            stmt,
            Department,
            sort_by,
            sort_order,
            allowed=DEPARTMENT_SORTS,
            default_sort_by="dept_name",
        )
        stmt = stmt.limit(page_size).offset((page - 1) * page_size)
        return list((await self.session.execute(stmt)).scalars().all())

    async def search_count(
        self,
        org_id: int,
        *,
        search: str | None = None,
        is_active: bool | None = None,
        include_deleted: bool = False,
    ) -> int:
        """Return the total number of departments matching :meth:`search` filters."""
        conds = self._conditions(
            org_id, search=search, is_active=is_active, include_deleted=include_deleted
        )
        stmt = select(func.count()).select_from(Department).where(and_(*conds))
        return int((await self.session.execute(stmt)).scalar_one())


class DesignationRepository(BaseRepository[Designation]):
    """CRUD, search, uniqueness, and referential checks for ``designations``."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Designation)

    async def get_by_id_in_org(self, org_id: int, designation_id: int) -> Designation | None:
        """Return a non-deleted designation by id within ``org_id``, or ``None``."""
        stmt = select(Designation).where(
            Designation.designation_id == designation_id,
            Designation.org_id == org_id,
            Designation.is_deleted.is_(False),
        )
        return (await self.session.execute(stmt.limit(1))).scalar_one_or_none()

    async def name_exists(
        self, org_id: int, designation_name: str, *, exclude_designation_id: int | None = None
    ) -> bool:
        """Return whether a non-deleted designation already uses ``designation_name``.

        Mirrors the partial unique index ``uq_designations_org_id_designation_name``.
        """
        stmt = select(Designation.designation_id).where(
            Designation.org_id == org_id,
            func.lower(Designation.designation_name) == designation_name.strip().lower(),
            Designation.is_deleted.is_(False),
        )
        if exclude_designation_id is not None:
            stmt = stmt.where(Designation.designation_id != exclude_designation_id)
        return (await self.session.execute(stmt.limit(1))).first() is not None

    async def has_active_employees(self, org_id: int, designation_id: int) -> bool:
        """Return whether any active, non-deleted employee references this designation."""
        stmt = select(Employee.employee_id).where(
            Employee.org_id == org_id,
            Employee.designation_id == designation_id,
            Employee.is_deleted.is_(False),
            Employee.employment_status == ACTIVE_EMPLOYMENT_STATUS,
        )
        return (await self.session.execute(stmt.limit(1))).first() is not None

    @staticmethod
    def _conditions(
        org_id: int,
        *,
        search: str | None,
        is_active: bool | None,
        include_deleted: bool,
    ) -> list[Any]:
        conds: list[Any] = [Designation.org_id == org_id]
        if not include_deleted:
            conds.append(Designation.is_deleted.is_(False))
        if is_active is not None:
            conds.append(Designation.is_active.is_(is_active))
        if search:
            like = f"%{search.strip()}%"
            conds.append(Designation.designation_name.ilike(like))
        return conds

    async def search(
        self,
        org_id: int,
        *,
        search: str | None = None,
        is_active: bool | None = None,
        include_deleted: bool = False,
        sort_by: str | None = None,
        sort_order: SortOrder | str = SortOrder.ASC,
        page: int = 1,
        page_size: int = 25,
    ) -> list[Designation]:
        """Return a filtered, sorted, paginated page of designations in ``org_id``."""
        conds = self._conditions(
            org_id, search=search, is_active=is_active, include_deleted=include_deleted
        )
        stmt = select(Designation).where(and_(*conds))
        stmt = apply_sorting(
            stmt,
            Designation,
            sort_by,
            sort_order,
            allowed=DESIGNATION_SORTS,
            default_sort_by="designation_name",
        )
        stmt = stmt.limit(page_size).offset((page - 1) * page_size)
        return list((await self.session.execute(stmt)).scalars().all())

    async def search_count(
        self,
        org_id: int,
        *,
        search: str | None = None,
        is_active: bool | None = None,
        include_deleted: bool = False,
    ) -> int:
        """Return the total number of designations matching :meth:`search` filters."""
        conds = self._conditions(
            org_id, search=search, is_active=is_active, include_deleted=include_deleted
        )
        stmt = select(func.count()).select_from(Designation).where(and_(*conds))
        return int((await self.session.execute(stmt)).scalar_one())


__all__ = [
    "OrganizationRepository",
    "BranchRepository",
    "DepartmentRepository",
    "DesignationRepository",
]
