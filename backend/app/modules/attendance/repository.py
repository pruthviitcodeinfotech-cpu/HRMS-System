"""Attendance Management — data-access layer (async SQLAlchemy).

One focused repository per module-owned aggregate (``attendance_days``,
``attendance_punches``, ``attendance_penalties``), each extending
:class:`app.shared.base.repository.BaseRepository`. **Database operations only** —
no business rules, no metric recomputation, no regularization policy. Methods run
queries and flush writes; the **service owns the commit boundary**.

Scoping notes:

* All three module tables carry ``org_id`` and are queried org-scoped.
* Branch/department filtering on ``attendance_days`` is expressed by joining the
  employee master (``employees.master_branch_id`` / ``employees.dept_id``); the
  attendance tables themselves carry no branch or department column.
* ``EmployeeLookupRepository`` and ``ShiftLookupRepository`` are read-only
  cross-module readers that expose only the lookups Attendance needs for
  reference validation.
"""

from __future__ import annotations

from datetime import date as date_type

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.attendance.models import (
    AttendanceDay,
    AttendancePenalty,
    AttendancePunch,
    AttendanceLock,
)
from app.modules.employee.models.employee import Employee
from app.modules.shift.models.shift import Shift
from app.shared.base.repository import BaseRepository


class AttendanceDayRepository(BaseRepository[AttendanceDay]):
    """CRUD, search, and lookups for ``attendance_days``."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, AttendanceDay)

    # --- Lookups -------------------------------------------------------------
    async def get_by_id_in_org(self, day_id: int, org_id: int) -> AttendanceDay | None:
        """Return an attendance day by id within ``org_id``, or ``None``."""
        stmt = select(AttendanceDay).where(
            AttendanceDay.id == day_id,
            AttendanceDay.org_id == org_id,
        )
        return (await self.session.execute(stmt.limit(1))).scalar_one_or_none()

    async def get_by_employee_date(
        self, org_id: int, employee_id: int, attendance_date: date_type
    ) -> AttendanceDay | None:
        """Return the unique day row for an employee/date pair within ``org_id``."""
        stmt = select(AttendanceDay).where(
            AttendanceDay.org_id == org_id,
            AttendanceDay.employee_id == employee_id,
            AttendanceDay.attendance_date == attendance_date,
        )
        return (await self.session.execute(stmt.limit(1))).scalar_one_or_none()

    async def get_detail(self, day_id: int, org_id: int) -> AttendanceDay | None:
        """Return a day with its punches and penalties eagerly loaded."""
        stmt = (
            select(AttendanceDay)
            .where(AttendanceDay.id == day_id, AttendanceDay.org_id == org_id)
            .options(
                selectinload(AttendanceDay.punches),
                selectinload(AttendanceDay.penalties),
            )
        )
        return (await self.session.execute(stmt.limit(1))).scalar_one_or_none()

    # --- Search --------------------------------------------------------------
    def _search_stmt(
        self,
        stmt: Select,
        org_id: int,
        *,
        employee_id: int | None,
        date: date_type | None,
        date_from: date_type | None,
        date_to: date_type | None,
        shift_id: int | None,
        branch_id: int | None,
        dept_id: int | None,
        branch_scope: list[int] | None,
    ) -> Select:
        """Apply the shared ``attendance_days`` filter predicate to ``stmt``."""
        stmt = stmt.where(AttendanceDay.org_id == org_id)

        if employee_id is not None:
            stmt = stmt.where(AttendanceDay.employee_id == employee_id)
        if date is not None:
            stmt = stmt.where(AttendanceDay.attendance_date == date)
        if date_from is not None:
            stmt = stmt.where(AttendanceDay.attendance_date >= date_from)
        if date_to is not None:
            stmt = stmt.where(AttendanceDay.attendance_date <= date_to)
        if shift_id is not None:
            stmt = stmt.where(AttendanceDay.shift_id == shift_id)

        # Branch / department live on the employee master, so scope through a join.
        if branch_id is not None or dept_id is not None or branch_scope is not None:
            stmt = stmt.join(Employee, Employee.employee_id == AttendanceDay.employee_id)
            if branch_id is not None:
                stmt = stmt.where(Employee.master_branch_id == branch_id)
            if dept_id is not None:
                stmt = stmt.where(Employee.dept_id == dept_id)
            if branch_scope is not None:
                stmt = stmt.where(Employee.master_branch_id.in_(branch_scope))
        return stmt

    async def search(
        self,
        org_id: int,
        *,
        employee_id: int | None = None,
        date: date_type | None = None,
        date_from: date_type | None = None,
        date_to: date_type | None = None,
        shift_id: int | None = None,
        branch_id: int | None = None,
        dept_id: int | None = None,
        branch_scope: list[int] | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> list[AttendanceDay]:
        """Return a filtered, paginated page of attendance days (newest date first)."""
        stmt = self._search_stmt(
            select(AttendanceDay),
            org_id,
            employee_id=employee_id,
            date=date,
            date_from=date_from,
            date_to=date_to,
            shift_id=shift_id,
            branch_id=branch_id,
            dept_id=dept_id,
            branch_scope=branch_scope,
        )
        stmt = (
            stmt.order_by(AttendanceDay.attendance_date.desc(), AttendanceDay.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def search_count(
        self,
        org_id: int,
        *,
        employee_id: int | None = None,
        date: date_type | None = None,
        date_from: date_type | None = None,
        date_to: date_type | None = None,
        shift_id: int | None = None,
        branch_id: int | None = None,
        dept_id: int | None = None,
        branch_scope: list[int] | None = None,
    ) -> int:
        """Return the number of attendance days matching the same filters as :meth:`search`."""
        stmt = self._search_stmt(
            select(func.count(AttendanceDay.id)),
            org_id,
            employee_id=employee_id,
            date=date,
            date_from=date_from,
            date_to=date_to,
            shift_id=shift_id,
            branch_id=branch_id,
            dept_id=dept_id,
            branch_scope=branch_scope,
        )
        return int((await self.session.execute(stmt)).scalar_one())


class AttendancePunchRepository(BaseRepository[AttendancePunch]):
    """Append-only punch log access for ``attendance_punches``."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, AttendancePunch)

    async def get_for_day(self, org_id: int, attendance_day_id: int) -> list[AttendancePunch]:
        """Return every punch recorded against a day, in sequence order."""
        stmt = (
            select(AttendancePunch)
            .where(
                AttendancePunch.org_id == org_id,
                AttendancePunch.attendance_day_id == attendance_day_id,
            )
            .order_by(AttendancePunch.sequence_no.asc())
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def get_timeline(
        self, org_id: int, employee_id: int, date_from: date_type, date_to: date_type
    ) -> list[AttendancePunch]:
        """Return an employee's punches across a date range, oldest first."""
        stmt = (
            select(AttendancePunch)
            .where(
                AttendancePunch.org_id == org_id,
                AttendancePunch.employee_id == employee_id,
                func.date(AttendancePunch.punch_time) >= date_from,
                func.date(AttendancePunch.punch_time) <= date_to,
            )
            .order_by(AttendancePunch.punch_time.asc())
        )
        return list((await self.session.execute(stmt)).scalars().all())

    def _search_stmt(
        self,
        stmt: Select,
        org_id: int,
        *,
        employee_id: int | None,
        device_id: int | None,
        from_date: date_type | None,
        to_date: date_type | None,
    ) -> Select:
        """Apply the shared ``attendance_punches`` filter predicate to ``stmt``."""
        stmt = stmt.where(AttendancePunch.org_id == org_id)
        if employee_id is not None:
            stmt = stmt.where(AttendancePunch.employee_id == employee_id)
        if device_id is not None:
            stmt = stmt.where(AttendancePunch.device_id == device_id)
        if from_date is not None:
            stmt = stmt.where(func.date(AttendancePunch.punch_time) >= from_date)
        if to_date is not None:
            stmt = stmt.where(func.date(AttendancePunch.punch_time) <= to_date)
        return stmt

    async def search(
        self,
        org_id: int,
        *,
        employee_id: int | None = None,
        device_id: int | None = None,
        from_date: date_type | None = None,
        to_date: date_type | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> list[AttendancePunch]:
        """Return a filtered, paginated page of punches (most recent first)."""
        stmt = self._search_stmt(
            select(AttendancePunch),
            org_id,
            employee_id=employee_id,
            device_id=device_id,
            from_date=from_date,
            to_date=to_date,
        )
        stmt = (
            stmt.order_by(AttendancePunch.punch_time.desc(), AttendancePunch.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def search_count(
        self,
        org_id: int,
        *,
        employee_id: int | None = None,
        device_id: int | None = None,
        from_date: date_type | None = None,
        to_date: date_type | None = None,
    ) -> int:
        """Return the number of punches matching the same filters as :meth:`search`."""
        stmt = self._search_stmt(
            select(func.count(AttendancePunch.id)),
            org_id,
            employee_id=employee_id,
            device_id=device_id,
            from_date=from_date,
            to_date=to_date,
        )
        return int((await self.session.execute(stmt)).scalar_one())


class AttendancePenaltyRepository(BaseRepository[AttendancePenalty]):
    """CRUD and search for ``attendance_penalties``."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, AttendancePenalty)

    async def get_by_id_in_org(self, penalty_id: int, org_id: int) -> AttendancePenalty | None:
        """Return a penalty by id within ``org_id``.

        Soft-deleted rows are returned: waiving a penalty sets ``is_deleted``, and the
        service must distinguish "already waived" from "not found".
        """
        stmt = select(AttendancePenalty).where(
            AttendancePenalty.id == penalty_id,
            AttendancePenalty.org_id == org_id,
        )
        return (await self.session.execute(stmt.limit(1))).scalar_one_or_none()

    def _search_stmt(
        self,
        stmt: Select,
        org_id: int,
        *,
        employee_id: int | None,
        status: str | None,
    ) -> Select:
        """Apply the shared ``attendance_penalties`` filter predicate to ``stmt``."""
        stmt = stmt.where(
            AttendancePenalty.org_id == org_id,
            AttendancePenalty.is_deleted.is_(False),
        )
        if employee_id is not None:
            stmt = stmt.where(AttendancePenalty.employee_id == employee_id)
        if status is not None:
            stmt = stmt.where(AttendancePenalty.status == status)
        return stmt

    async def search(
        self,
        org_id: int,
        *,
        employee_id: int | None = None,
        status: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> list[AttendancePenalty]:
        """Return a filtered, paginated page of active penalties (most recent first)."""
        stmt = self._search_stmt(
            select(AttendancePenalty), org_id, employee_id=employee_id, status=status
        )
        stmt = (
            stmt.order_by(AttendancePenalty.created_at.desc(), AttendancePenalty.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def search_count(
        self,
        org_id: int,
        *,
        employee_id: int | None = None,
        status: str | None = None,
    ) -> int:
        """Return the number of penalties matching the same filters as :meth:`search`."""
        stmt = self._search_stmt(
            select(func.count(AttendancePenalty.id)),
            org_id,
            employee_id=employee_id,
            status=status,
        )
        return int((await self.session.execute(stmt)).scalar_one())


class EmployeeLookupRepository(BaseRepository[Employee]):
    """Read-only employee reader used by Attendance for reference validation."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Employee)

    async def get_active_by_id(self, employee_id: int, org_id: int) -> Employee | None:
        """Return a non-deleted employee by id within ``org_id``, or ``None``."""
        stmt = select(Employee).where(
            Employee.employee_id == employee_id,
            Employee.org_id == org_id,
            Employee.is_deleted.is_(False),
        )
        return (await self.session.execute(stmt.limit(1))).scalar_one_or_none()


class ShiftLookupRepository(BaseRepository[Shift]):
    """Read-only shift reader used by Attendance for reference validation."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Shift)

    async def get_active_by_id(self, shift_id: int, org_id: int) -> Shift | None:
        """Return a non-deleted shift by id within ``org_id`` with its day timings loaded.

        ``day_timings`` is eager-loaded because callers read it to derive a day's
        expected start/end time; lazy loading it would raise ``MissingGreenlet``
        under the async session.
        """
        stmt = (
            select(Shift)
            .where(
                Shift.shift_id == shift_id,
                Shift.org_id == org_id,
                Shift.is_deleted.is_(False),
            )
            .options(selectinload(Shift.day_timings))
        )
        return (await self.session.execute(stmt.limit(1))).scalar_one_or_none()

    async def exists_active(self, org_id: int, shift_id: int) -> bool:
        """Return whether a non-deleted shift with ``shift_id`` exists in ``org_id``."""
        stmt = select(Shift.shift_id).where(
            Shift.shift_id == shift_id,
            Shift.org_id == org_id,
            Shift.is_deleted.is_(False),
        )
        return (await self.session.execute(stmt.limit(1))).first() is not None


class AttendanceLockRepository(BaseRepository[AttendanceLock]):
    """CRUD and locking operations for ``attendance_locks``."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, AttendanceLock)

    async def create_lock(
        self,
        org_id: int,
        month: int,
        year: int,
        lock_type: str,
        status: str,
        locked_by: int,
        reason: str | None,
        branch_id: int | None = None,
    ) -> AttendanceLock:
        """Create a new attendance lock record."""
        lock = AttendanceLock(
            org_id=org_id,
            lock_month=month,
            lock_year=year,
            lock_type=lock_type,
            status=status,
            locked_by=locked_by,
            reason=reason,
            branch_id=branch_id,
        )
        self.session.add(lock)
        await self.session.flush()
        return lock

    async def get_lock(
        self, org_id: int, month: int, year: int, branch_id: int | None = None
    ) -> AttendanceLock | None:
        """Get lock record for period and organization/branch."""
        stmt = select(AttendanceLock).where(
            AttendanceLock.org_id == org_id,
            AttendanceLock.lock_month == month,
            AttendanceLock.lock_year == year,
            AttendanceLock.branch_id == branch_id,
        )
        return (await self.session.execute(stmt.limit(1))).scalar_one_or_none()

    async def is_locked(self, org_id: int, month: int, year: int, branch_id: int | None = None) -> bool:
        """Check if attendance period is locked for this organization/branch.
        
        A period is locked if there exists a lock with status = 'locked' covering
        either company-wide or this specific branch.
        """
        stmt = select(AttendanceLock).where(
            AttendanceLock.org_id == org_id,
            AttendanceLock.lock_month == month,
            AttendanceLock.lock_year == year,
            AttendanceLock.status == "locked",
        )
        if branch_id is not None:
            stmt = stmt.where(
                (AttendanceLock.branch_id.is_(None)) | (AttendanceLock.branch_id == branch_id)
            )
        else:
            stmt = stmt.where(AttendanceLock.branch_id.is_(None))
        
        result = (await self.session.execute(stmt.limit(1))).scalar_one_or_none()
        return result is not None

    async def unlock(
        self,
        org_id: int,
        month: int,
        year: int,
        branch_id: int | None = None,
    ) -> bool:
        """Deactivate/unlock a locked period by setting status to 'unlocked'."""
        stmt = select(AttendanceLock).where(
            AttendanceLock.org_id == org_id,
            AttendanceLock.lock_month == month,
            AttendanceLock.lock_year == year,
            AttendanceLock.branch_id == branch_id,
            AttendanceLock.status == "locked",
        )
        lock = (await self.session.execute(stmt.limit(1))).scalar_one_or_none()
        if lock:
            lock.status = "unlocked"
            await self.session.flush()
            return True
        return False

    async def get_locked_periods(self, org_id: int) -> list[AttendanceLock]:
        """Retrieve list of all active locks for an organization."""
        stmt = select(AttendanceLock).where(
            AttendanceLock.org_id == org_id,
            AttendanceLock.status == "locked",
        ).order_by(AttendanceLock.lock_year.desc(), AttendanceLock.lock_month.desc())
        return list((await self.session.execute(stmt)).scalars().all())

