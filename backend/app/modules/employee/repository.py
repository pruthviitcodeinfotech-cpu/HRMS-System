"""Employee Management — data-access layer (async SQLAlchemy).

One focused repository per aggregate, all extending
:class:`app.shared.base.repository.BaseRepository` and operating on the existing
Employee-Management models. **Database operations only** — no business rules, no
org-hierarchy consistency checks, no code generation, no lifecycle orchestration.
Methods run queries and flush writes; the **service owns the commit boundary**.

Every query is org-scoped (the tables carry ``org_id``, directly or via the parent
``employees`` row) and, by default, excludes soft-deleted rows (``is_deleted``).

Reporting-manager note: the ``employees`` table has no dedicated
``reporting_manager_id`` column, so a "reporting manager" is simply another active
employee in the same organisation. :meth:`EmployeeRepository.get_reporting_manager`
resolves a supplied manager reference to that active employee row so the service
can validate it — no schema is invented or modified here.
"""

from __future__ import annotations

from typing import TypeVar

from sqlalchemy import BigInteger, and_, cast, func, or_, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.core.constants.enums import SortOrder
from app.core.database.base import Base
from app.modules.employee.models import (
    Branch,
    Department,
    Designation,
    Employee,
)
from app.modules.employee.models.satellites import (
    EmployeeBankDetail,
    EmployeeDocument,
    EmployeeEmergencyContact,
    EmployeeReference,
    EmployeeStatusHistory,
    EmployeeTag,
)
from app.shared.base.repository import BaseRepository
from app.shared.utils.query import apply_sorting

SatelliteModel = TypeVar("SatelliteModel", bound=Base)

_EMPLOYEE_SORTS = {
    "employee_code",
    "employee_name",
    "date_of_joining",
    "employment_status",
    "created_at",
    "updated_at",
}


class EmployeeRepository(BaseRepository[Employee]):
    """CRUD, search, lookup, and exists checks for ``employees``."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Employee)

    # --- Lookups -------------------------------------------------------------
    async def get_active_by_id(self, employee_id: int, org_id: int) -> Employee | None:
        """Return a non-deleted employee by id within ``org_id``, or ``None``."""
        stmt = select(Employee).where(
            Employee.employee_id == employee_id,
            Employee.org_id == org_id,
            Employee.is_deleted.is_(False),
        )
        return (await self.session.execute(stmt.limit(1))).scalar_one_or_none()

    async def get_detail(self, employee_id: int, org_id: int) -> Employee | None:
        """Return a non-deleted employee with all profile relationships eager-loaded.

        Loads org links (branch/department/designation) and every satellite
        collection (bank details, documents, emergency contacts, references,
        biometrics, punch branches, attendance permission, tags, status history)
        for the ``GET /employees/{id}`` detail projection.
        """
        stmt = (
            select(Employee)
            .where(
                Employee.employee_id == employee_id,
                Employee.org_id == org_id,
                Employee.is_deleted.is_(False),
            )
            .options(
                # Many-to-one / one-to-one links are single rows: JOIN them into the
                # parent SELECT instead of paying a round-trip each. `selectinload`
                # would issue one extra statement per relationship — four wasted
                # round-trips on the hottest read in the module.
                joinedload(Employee.master_branch),
                joinedload(Employee.department),
                joinedload(Employee.designation),
                joinedload(Employee.attendance_permission),
                # The to-many collections stay on `selectinload`: joining them would
                # multiply the parent row by the cartesian product of every satellite.
                selectinload(Employee.bank_details),
                selectinload(Employee.documents),
                selectinload(Employee.emergency_contacts),
                selectinload(Employee.references),
                selectinload(Employee.biometrics),
                selectinload(Employee.punch_branches),
                selectinload(Employee.tags),
                selectinload(Employee.status_history),
            )
        )
        return (await self.session.execute(stmt.limit(1))).scalar_one_or_none()

    async def get_by_code(
        self, org_id: int, employee_code: str, *, include_deleted: bool = False
    ) -> Employee | None:
        """Return the employee with ``employee_code`` in ``org_id`` (active by default)."""
        stmt = select(Employee).where(
            Employee.org_id == org_id, Employee.employee_code == employee_code
        )
        if not include_deleted:
            stmt = stmt.where(Employee.is_deleted.is_(False))
        return (await self.session.execute(stmt.limit(1))).scalar_one_or_none()

    async def get_reporting_manager(
        self, org_id: int, manager_employee_id: int
    ) -> Employee | None:
        """Resolve a reporting-manager reference to an active employee in ``org_id``.

        The schema has no ``reporting_manager_id`` column; a manager is any active
        employee in the same organisation. Returns the manager's row, or ``None``
        when the id does not resolve to an active employee.
        """
        return await self.get_active_by_id(manager_employee_id, org_id)

    # --- Exists checks -------------------------------------------------------
    async def exists_in_org(self, org_id: int, employee_id: int) -> bool:
        """Return whether an active employee ``employee_id`` exists in ``org_id``."""
        stmt = select(Employee.employee_id).where(
            Employee.employee_id == employee_id,
            Employee.org_id == org_id,
            Employee.is_deleted.is_(False),
        )
        return (await self.session.execute(stmt.limit(1))).first() is not None

    async def code_exists(
        self, org_id: int, employee_code: str, *, exclude_employee_id: int | None = None
    ) -> bool:
        """Return whether an active employee already uses ``employee_code`` in ``org_id``.

        Mirrors the partial unique index ``uq_employees_org_id_employee_code``
        (which applies only to non-deleted rows).
        """
        stmt = select(Employee.employee_id).where(
            Employee.org_id == org_id,
            Employee.employee_code == employee_code,
            Employee.is_deleted.is_(False),
        )
        if exclude_employee_id is not None:
            stmt = stmt.where(Employee.employee_id != exclude_employee_id)
        return (await self.session.execute(stmt.limit(1))).first() is not None

    async def manager_exists(self, org_id: int, manager_employee_id: int) -> bool:
        """Return whether ``manager_employee_id`` is an active employee in ``org_id``."""
        return await self.exists_in_org(org_id, manager_employee_id)

    # --- Search / filtering / pagination -------------------------------------
    @staticmethod
    def _conditions(
        org_id: int,
        *,
        search: str | None,
        branch_id: int | None,
        department_id: int | None,
        designation_id: int | None,
        status: str | None,
        branch_scope: list[int] | None,
        include_deleted: bool,
    ) -> list:
        """Build the WHERE conditions shared by :meth:`search` and :meth:`search_count`."""
        conds: list = [Employee.org_id == org_id]
        if not include_deleted:
            conds.append(Employee.is_deleted.is_(False))
        if branch_id is not None:
            conds.append(Employee.master_branch_id == branch_id)
        if department_id is not None:
            conds.append(Employee.dept_id == department_id)
        if designation_id is not None:
            conds.append(Employee.designation_id == designation_id)
        if status is not None:
            conds.append(Employee.employment_status == status)
        # Branch-scope restriction for Branch Admins (contract §7 scope note).
        if branch_scope is not None:
            conds.append(Employee.master_branch_id.in_(branch_scope))
        if search:
            like = f"%{search.strip()}%"
            conds.append(
                or_(
                    Employee.employee_name.ilike(like),
                    Employee.display_name.ilike(like),
                    Employee.employee_code.ilike(like),
                    Employee.employee_uid.ilike(like),
                    Employee.email.ilike(like),
                    Employee.mobile_number.ilike(like),
                )
            )
        return conds

    async def search(
        self,
        org_id: int,
        *,
        search: str | None = None,
        branch_id: int | None = None,
        department_id: int | None = None,
        designation_id: int | None = None,
        status: str | None = None,
        branch_scope: list[int] | None = None,
        include_deleted: bool = False,
        sort_by: str | None = "created_at",
        sort_order: SortOrder | str = SortOrder.DESC,
        page: int = 1,
        page_size: int = 25,
    ) -> list[Employee]:
        """Return a filtered, sorted, paginated page of employees in ``org_id``.

        Supports the ``GET /employees`` query surface: free-text ``search`` and
        ``branch_id`` / ``department_id`` / ``designation_id`` / ``status`` filters,
        optionally confined to ``branch_scope`` (Branch-Admin data scope).
        """
        conds = self._conditions(
            org_id,
            search=search,
            branch_id=branch_id,
            department_id=department_id,
            designation_id=designation_id,
            status=status,
            branch_scope=branch_scope,
            include_deleted=include_deleted,
        )
        stmt = select(Employee).where(and_(*conds))
        stmt = apply_sorting(
            stmt,
            Employee,
            sort_by,
            sort_order,
            allowed=_EMPLOYEE_SORTS,
            default_sort_by="created_at",
        )
        stmt = stmt.limit(page_size).offset((page - 1) * page_size)
        return list((await self.session.execute(stmt)).scalars().all())

    async def search_count(
        self,
        org_id: int,
        *,
        search: str | None = None,
        branch_id: int | None = None,
        department_id: int | None = None,
        designation_id: int | None = None,
        status: str | None = None,
        branch_scope: list[int] | None = None,
        include_deleted: bool = False,
    ) -> int:
        """Return the total number of employees matching the same filters as :meth:`search`."""
        conds = self._conditions(
            org_id,
            search=search,
            branch_id=branch_id,
            department_id=department_id,
            designation_id=designation_id,
            status=status,
            branch_scope=branch_scope,
            include_deleted=include_deleted,
        )
        stmt = select(func.count()).select_from(Employee).where(and_(*conds))
        return int((await self.session.execute(stmt)).scalar_one())

    # --- Writes --------------------------------------------------------------
    async def soft_delete(self, instance: Employee) -> Employee:
        """Soft-delete an employee by setting ``is_deleted`` (flushed, not committed).

        The contract prefers exit/rehire over hard delete; ``DELETE`` is a soft
        delete. Setting the flag is a data operation — status transitions and the
        exit cascade are the service's responsibility.
        """
        return await self.update(instance, {"is_deleted": True})

    async def allocate_employee_code(
        self, org_id: int, *, prefix: str = "EMP", pad: int = 5
    ) -> str:
        """Allocate the next unique ``employee_code`` for ``org_id``, race-free.

        The approved architecture (contract §18) calls for a Settings-driven,
        transaction-safe sequence. A dedicated PostgreSQL ``SEQUENCE`` would require
        a schema/migration change (out of scope for hardening), so this uses a
        **transaction-scoped advisory lock** (``pg_advisory_xact_lock``) instead:
        concurrent creators for the same org serialise on the lock, the highest
        existing numeric suffix is read *inside* the lock, and the lock releases
        automatically at commit/rollback. Soft-deleted rows are included so codes are
        never reused (immutable, unique history). Requires PostgreSQL — consistent
        with the module's other Postgres-specific features (partial unique indexes).
        """
        await self.session.execute(
            text("SELECT pg_advisory_xact_lock(hashtext(:key))"),
            {"key": f"employee_code:{org_id}:{prefix}"},
        )
        numeric_suffix = cast(func.substr(Employee.employee_code, len(prefix) + 1), BigInteger)
        stmt = select(func.coalesce(func.max(numeric_suffix), 0)).where(
            Employee.org_id == org_id,
            Employee.employee_code.op("~")(f"^{prefix}[0-9]+$"),
        )
        highest = int((await self.session.execute(stmt)).scalar_one())
        return f"{prefix}{highest + 1:0{pad}d}"


class BranchRepository(BaseRepository[Branch]):
    """Lookup and exists checks for ``branches`` (org FK validation)."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Branch)

    async def get_active_by_id(self, branch_id: int, org_id: int) -> Branch | None:
        """Return a non-deleted branch by id within ``org_id``, or ``None``."""
        stmt = select(Branch).where(
            Branch.branch_id == branch_id,
            Branch.org_id == org_id,
            Branch.is_deleted.is_(False),
        )
        return (await self.session.execute(stmt.limit(1))).scalar_one_or_none()

    async def exists_active(self, org_id: int, branch_id: int) -> bool:
        """Return whether ``branch_id`` is an active, non-deleted branch in ``org_id``."""
        stmt = select(Branch.branch_id).where(
            Branch.branch_id == branch_id,
            Branch.org_id == org_id,
            Branch.is_active.is_(True),
            Branch.is_deleted.is_(False),
        )
        return (await self.session.execute(stmt.limit(1))).first() is not None


class DepartmentRepository(BaseRepository[Department]):
    """Lookup and exists checks for ``departments`` (org FK validation)."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Department)

    async def get_active_by_id(self, dept_id: int, org_id: int) -> Department | None:
        """Return a non-deleted department by id within ``org_id``, or ``None``."""
        stmt = select(Department).where(
            Department.dept_id == dept_id,
            Department.org_id == org_id,
            Department.is_deleted.is_(False),
        )
        return (await self.session.execute(stmt.limit(1))).scalar_one_or_none()

    async def exists_active(self, org_id: int, dept_id: int) -> bool:
        """Return whether ``dept_id`` is an active, non-deleted department in ``org_id``."""
        stmt = select(Department.dept_id).where(
            Department.dept_id == dept_id,
            Department.org_id == org_id,
            Department.is_active.is_(True),
            Department.is_deleted.is_(False),
        )
        return (await self.session.execute(stmt.limit(1))).first() is not None


class DesignationRepository(BaseRepository[Designation]):
    """Lookup and exists checks for ``designations`` (org FK validation)."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Designation)

    async def get_active_by_id(
        self, designation_id: int, org_id: int
    ) -> Designation | None:
        """Return a non-deleted designation by id within ``org_id``, or ``None``."""
        stmt = select(Designation).where(
            Designation.designation_id == designation_id,
            Designation.org_id == org_id,
            Designation.is_deleted.is_(False),
        )
        return (await self.session.execute(stmt.limit(1))).scalar_one_or_none()

    async def exists_active(self, org_id: int, designation_id: int) -> bool:
        """Return whether ``designation_id`` is an active designation in ``org_id``."""
        stmt = select(Designation.designation_id).where(
            Designation.designation_id == designation_id,
            Designation.org_id == org_id,
            Designation.is_active.is_(True),
            Designation.is_deleted.is_(False),
        )
        return (await self.session.execute(stmt.limit(1))).first() is not None


class EmployeeSatelliteRepository(BaseRepository[SatelliteModel]):
    """Org-scoped data access for one employee satellite (child) table.

    Every lookup joins through the parent ``employees`` row and filters by its
    ``org_id``, so a record belonging to another organisation can never be
    returned. Subclasses declare the primary-key attribute name, whether the
    table carries an ``is_deleted`` flag (``employee_tags`` and
    ``employee_status_history`` do not), and the default list ordering.
    """

    pk_attr: str
    has_soft_delete: bool = True
    order_attrs: tuple[str, ...] = ()

    def _scoped(self, org_id: int, employee_id: int) -> list:
        """WHERE conditions confining rows to one employee within ``org_id``."""
        conds: list = [
            self.model.employee_id == employee_id,
            Employee.org_id == org_id,
            Employee.is_deleted.is_(False),
        ]
        if self.has_soft_delete:
            conds.append(self.model.is_deleted.is_(False))
        return conds

    async def list_for_employee(self, org_id: int, employee_id: int) -> list[SatelliteModel]:
        """Return the employee's non-deleted satellite rows (org-scoped, ordered)."""
        stmt = (
            select(self.model)
            .join(Employee, Employee.employee_id == self.model.employee_id)
            .where(and_(*self._scoped(org_id, employee_id)))
        )
        order_attrs = self.order_attrs or (self.pk_attr,)
        stmt = stmt.order_by(*(getattr(self.model, name).asc() for name in order_attrs))
        return list((await self.session.execute(stmt)).scalars().all())

    async def get_by_id_in_org(
        self, org_id: int, employee_id: int, record_id: int
    ) -> SatelliteModel | None:
        """Return one non-deleted satellite row by id, scoped to the employee's org."""
        stmt = (
            select(self.model)
            .join(Employee, Employee.employee_id == self.model.employee_id)
            .where(
                and_(
                    *self._scoped(org_id, employee_id),
                    getattr(self.model, self.pk_attr) == record_id,
                )
            )
            .limit(1)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()


class EmployeeBankDetailRepository(EmployeeSatelliteRepository[EmployeeBankDetail]):
    """Org-scoped CRUD for ``employee_bank_details`` (soft-deleted)."""

    pk_attr = "bank_detail_id"

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, EmployeeBankDetail)

    async def unset_primary(self, employee_id: int, *, exclude_id: int | None = None) -> None:
        """Clear ``is_primary`` on the employee's other non-deleted bank rows.

        Enforces the "at most one primary account per employee" rule (contract
        §9) ahead of inserting/updating a primary row. Flushed, not committed.
        """
        stmt = (
            update(EmployeeBankDetail)
            .where(
                EmployeeBankDetail.employee_id == employee_id,
                EmployeeBankDetail.is_deleted.is_(False),
                EmployeeBankDetail.is_primary.is_(True),
            )
            .values(is_primary=False)
            .execution_options(synchronize_session="fetch")
        )
        if exclude_id is not None:
            stmt = stmt.where(EmployeeBankDetail.bank_detail_id != exclude_id)
        await self.session.execute(stmt)


class EmployeeDocumentRepository(EmployeeSatelliteRepository[EmployeeDocument]):
    """Org-scoped CRUD for ``employee_documents`` (soft-deleted)."""

    pk_attr = "document_id"

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, EmployeeDocument)


class EmployeeEmergencyContactRepository(EmployeeSatelliteRepository[EmployeeEmergencyContact]):
    """Org-scoped CRUD for ``employee_emergency_contacts`` (soft-deleted)."""

    pk_attr = "emergency_contact_id"

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, EmployeeEmergencyContact)


class EmployeeReferenceRepository(EmployeeSatelliteRepository[EmployeeReference]):
    """Org-scoped CRUD for ``employee_references`` (soft-deleted, sort_order first)."""

    pk_attr = "reference_id"
    order_attrs = ("sort_order", "reference_id")

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, EmployeeReference)


class EmployeeTagRepository(EmployeeSatelliteRepository[EmployeeTag]):
    """Org-scoped CRUD for ``employee_tags`` (no ``is_deleted`` — hard delete)."""

    pk_attr = "tag_id"
    has_soft_delete = False

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, EmployeeTag)


class EmployeeStatusHistoryRepository(EmployeeSatelliteRepository[EmployeeStatusHistory]):
    """Org-scoped reads for the append-only ``employee_status_history``."""

    pk_attr = "status_history_id"
    has_soft_delete = False
    # Chronological (contract §8.5): oldest transition first.
    order_attrs = ("created_at", "status_history_id")

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, EmployeeStatusHistory)


__all__ = [
    "EmployeeRepository",
    "BranchRepository",
    "DepartmentRepository",
    "DesignationRepository",
    "EmployeeSatelliteRepository",
    "EmployeeBankDetailRepository",
    "EmployeeDocumentRepository",
    "EmployeeEmergencyContactRepository",
    "EmployeeReferenceRepository",
    "EmployeeTagRepository",
    "EmployeeStatusHistoryRepository",
]
