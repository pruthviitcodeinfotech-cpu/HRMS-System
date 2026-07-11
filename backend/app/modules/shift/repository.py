"""Shift Management — data-access layer (async SQLAlchemy).

One focused repository per aggregate, all extending
:class:`app.shared.base.repository.BaseRepository` and operating on the existing
Shift-Management models. **Database operations only** — no business rules, no shift
resolution logic, no rotation generation policy, no supersession decisions. Methods
run queries and flush writes; the **service owns the commit boundary**.

Scoping notes:

* ``shifts``, ``shift_assignments`` and ``roster`` carry ``org_id`` and are queried
  org-scoped. ``shift_day_timings`` is scoped through its parent ``shift_id``.
* ``employee_weekoffs`` has **no ``org_id`` column** (the approved schema keys it on
  ``employee_id`` only); its queries scope by ``employee_id`` (already org-bounded
  upstream via the employee master).
* There is **no shift-rotation table**. ``POST /shift-rotations`` materialises
  ``roster`` rows, so rotation persistence is handled by :class:`RosterRepository`.
* ``working_hours_config`` is surfaced by the Settings API (``/settings/attendance``),
  not by Shift Management §10, so it is intentionally not represented here.
"""

from __future__ import annotations

from datetime import date

from sqlalchemy import and_, delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.constants.enums import SortOrder
from app.modules.shift.models import (
    EmployeeWeekoff,
    Roster,
    Shift,
    ShiftAssignment,
    ShiftDayTiming,
)
from app.shared.base.repository import BaseRepository
from app.shared.utils.query import apply_sorting

_SHIFT_SORTS = {"shift_name", "shift_type", "is_default", "created_at", "updated_at"}
_ASSIGNMENT_SORTS = {"effective_from", "effective_to", "created_at"}


class ShiftRepository(BaseRepository[Shift]):
    """CRUD, search, and exists checks for ``shifts``."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Shift)

    # --- Lookups -------------------------------------------------------------
    async def get_active_by_id(self, shift_id: int, org_id: int) -> Shift | None:
        """Return a non-deleted shift by id within ``org_id``, or ``None``."""
        stmt = select(Shift).where(
            Shift.shift_id == shift_id,
            Shift.org_id == org_id,
            Shift.is_deleted.is_(False),
        )
        return (await self.session.execute(stmt.limit(1))).scalar_one_or_none()

    async def get_any_by_id(self, shift_id: int, org_id: int) -> Shift | None:
        """Return a shift by id within ``org_id`` **including soft-deleted** (restore)."""
        stmt = select(Shift).where(Shift.shift_id == shift_id, Shift.org_id == org_id)
        return (await self.session.execute(stmt.limit(1))).scalar_one_or_none()

    async def get_detail(self, shift_id: int, org_id: int) -> Shift | None:
        """Return a non-deleted shift with its ``day_timings`` eager-loaded."""
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

    # --- Exists checks -------------------------------------------------------
    async def name_exists(
        self, org_id: int, shift_name: str, *, exclude_shift_id: int | None = None
    ) -> bool:
        """Return whether a non-deleted shift already uses ``shift_name`` in ``org_id``.

        Mirrors the partial unique index ``uq_shifts_org_id_shift_name``.
        """
        stmt = select(Shift.shift_id).where(
            Shift.org_id == org_id,
            Shift.shift_name == shift_name,
            Shift.is_deleted.is_(False),
        )
        if exclude_shift_id is not None:
            stmt = stmt.where(Shift.shift_id != exclude_shift_id)
        return (await self.session.execute(stmt.limit(1))).first() is not None

    async def exists_in_org(self, org_id: int, shift_id: int) -> bool:
        """Return whether a non-deleted shift ``shift_id`` exists in ``org_id``."""
        stmt = select(Shift.shift_id).where(
            Shift.shift_id == shift_id,
            Shift.org_id == org_id,
            Shift.is_deleted.is_(False),
        )
        return (await self.session.execute(stmt.limit(1))).first() is not None

    async def has_assignments(self, shift_id: int) -> bool:
        """Return whether ANY assignment references this shift."""
        stmt = select(ShiftAssignment.assignment_id).where(
            ShiftAssignment.shift_id == shift_id
        )
        return (await self.session.execute(stmt.limit(1))).first() is not None

    async def has_open_assignments(self, shift_id: int) -> bool:
        """Return whether any still-open assignment (``effective_to IS NULL``) references it.

        Backs the "DELETE blocked if active assignments reference this shift" (409)
        rule; the service decides whether open-only or any assignment blocks delete.
        """
        stmt = select(ShiftAssignment.assignment_id).where(
            ShiftAssignment.shift_id == shift_id,
            ShiftAssignment.effective_to.is_(None),
        )
        return (await self.session.execute(stmt.limit(1))).first() is not None

    # --- Search / filtering / pagination -------------------------------------
    @staticmethod
    def _conditions(
        org_id: int,
        *,
        search: str | None,
        shift_type: str | None,
        is_default: bool | None,
        is_open_shift: bool | None,
        include_deleted: bool,
    ) -> list:
        """Build the WHERE conditions shared by :meth:`search` and :meth:`search_count`."""
        conds: list = [Shift.org_id == org_id]
        if not include_deleted:
            conds.append(Shift.is_deleted.is_(False))
        if shift_type is not None:
            conds.append(Shift.shift_type == shift_type)
        if is_default is not None:
            conds.append(Shift.is_default.is_(is_default))
        if is_open_shift is not None:
            conds.append(Shift.is_open_shift.is_(is_open_shift))
        if search:
            conds.append(Shift.shift_name.ilike(f"%{search.strip()}%"))
        return conds

    async def search(
        self,
        org_id: int,
        *,
        search: str | None = None,
        shift_type: str | None = None,
        is_default: bool | None = None,
        is_open_shift: bool | None = None,
        include_deleted: bool = False,
        sort_by: str | None = "shift_name",
        sort_order: SortOrder | str = SortOrder.ASC,
        page: int = 1,
        page_size: int = 25,
    ) -> list[Shift]:
        """Return a filtered, sorted, paginated page of shifts in ``org_id``."""
        conds = self._conditions(
            org_id,
            search=search,
            shift_type=shift_type,
            is_default=is_default,
            is_open_shift=is_open_shift,
            include_deleted=include_deleted,
        )
        stmt = select(Shift).where(and_(*conds))
        stmt = apply_sorting(
            stmt, Shift, sort_by, sort_order, allowed=_SHIFT_SORTS, default_sort_by="shift_name"
        )
        stmt = stmt.limit(page_size).offset((page - 1) * page_size)
        return list((await self.session.execute(stmt)).scalars().all())

    async def search_count(
        self,
        org_id: int,
        *,
        search: str | None = None,
        shift_type: str | None = None,
        is_default: bool | None = None,
        is_open_shift: bool | None = None,
        include_deleted: bool = False,
    ) -> int:
        """Return the total number of shifts matching the same filters as :meth:`search`."""
        conds = self._conditions(
            org_id,
            search=search,
            shift_type=shift_type,
            is_default=is_default,
            is_open_shift=is_open_shift,
            include_deleted=include_deleted,
        )
        stmt = select(func.count()).select_from(Shift).where(and_(*conds))
        return int((await self.session.execute(stmt)).scalar_one())

    # --- Writes --------------------------------------------------------------
    async def soft_delete(self, instance: Shift) -> Shift:
        """Soft-delete a shift by setting ``is_deleted`` (flushed, not committed).

        The contract's ``DELETE /shifts/{id}`` is a deactivate (soft delete); the
        service blocks it when active assignments reference the shift.
        """
        return await self.update(instance, {"is_deleted": True})


class ShiftDayTimingRepository(BaseRepository[ShiftDayTiming]):
    """Operations for ``shift_day_timings`` (a shift's per-day / uniform timings)."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, ShiftDayTiming)

    async def list_for_shift(self, shift_id: int) -> list[ShiftDayTiming]:
        """Return all timing rows for a shift, ordered by day (uniform row first)."""
        stmt = (
            select(ShiftDayTiming)
            .where(ShiftDayTiming.shift_id == shift_id)
            .order_by(ShiftDayTiming.day_of_week.asc().nulls_first())
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def get_for_shift(self, timing_id: int, shift_id: int) -> ShiftDayTiming | None:
        """Return a timing row by id belonging to ``shift_id``, or ``None``."""
        stmt = select(ShiftDayTiming).where(
            ShiftDayTiming.timing_id == timing_id, ShiftDayTiming.shift_id == shift_id
        )
        return (await self.session.execute(stmt.limit(1))).scalar_one_or_none()

    async def exists_for_day(
        self, shift_id: int, day_of_week: int | None, *, exclude_timing_id: int | None = None
    ) -> bool:
        """Return whether the shift already has a timing row for ``day_of_week``.

        Mirrors the unique constraint ``uq_shift_day_timings_shift_id_day_of_week``
        (with NULL treated as a distinct 'uniform' slot at the app level).
        """
        stmt = select(ShiftDayTiming.timing_id).where(ShiftDayTiming.shift_id == shift_id)
        if day_of_week is None:
            stmt = stmt.where(ShiftDayTiming.day_of_week.is_(None))
        else:
            stmt = stmt.where(ShiftDayTiming.day_of_week == day_of_week)
        if exclude_timing_id is not None:
            stmt = stmt.where(ShiftDayTiming.timing_id != exclude_timing_id)
        return (await self.session.execute(stmt.limit(1))).first() is not None

    async def delete_all_for_shift(self, shift_id: int) -> int:
        """Delete every timing row for a shift (for wholesale replace); returns count."""
        stmt = delete(ShiftDayTiming).where(ShiftDayTiming.shift_id == shift_id)
        result = await self.session.execute(stmt.execution_options(synchronize_session=False))
        await self.session.flush()
        return int(result.rowcount or 0)


class ShiftAssignmentRepository(BaseRepository[ShiftAssignment]):
    """CRUD, timeline, resolution, and exists checks for ``shift_assignments``."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, ShiftAssignment)

    async def get_by_id_in_org(self, assignment_id: int, org_id: int) -> ShiftAssignment | None:
        """Return an assignment by id within ``org_id``, or ``None``."""
        stmt = select(ShiftAssignment).where(
            ShiftAssignment.assignment_id == assignment_id,
            ShiftAssignment.org_id == org_id,
        )
        return (await self.session.execute(stmt.limit(1))).scalar_one_or_none()

    async def get_open_for_employee(
        self, org_id: int, employee_id: int
    ) -> ShiftAssignment | None:
        """Return the employee's currently-open assignment (``effective_to IS NULL``).

        Used by the service to supersede the prior assignment by closing its
        ``effective_to``. Returns the one with the latest ``effective_from``.
        """
        stmt = (
            select(ShiftAssignment)
            .where(
                ShiftAssignment.org_id == org_id,
                ShiftAssignment.employee_id == employee_id,
                ShiftAssignment.effective_to.is_(None),
            )
            .order_by(ShiftAssignment.effective_from.desc())
        )
        return (await self.session.execute(stmt.limit(1))).scalar_one_or_none()

    async def resolve_for_date(
        self, org_id: int, employee_id: int, on_date: date
    ) -> ShiftAssignment | None:
        """Return the assignment effective on ``on_date`` for an employee.

        An assignment applies when ``effective_from <= on_date`` and
        (``effective_to IS NULL`` OR ``effective_to >= on_date``); the latest
        ``effective_from`` wins.
        """
        stmt = (
            select(ShiftAssignment)
            .where(
                ShiftAssignment.org_id == org_id,
                ShiftAssignment.employee_id == employee_id,
                ShiftAssignment.effective_from <= on_date,
                (ShiftAssignment.effective_to.is_(None))
                | (ShiftAssignment.effective_to >= on_date),
            )
            .order_by(ShiftAssignment.effective_from.desc())
        )
        return (await self.session.execute(stmt.limit(1))).scalar_one_or_none()

    async def exists_on_effective_from(
        self, employee_id: int, effective_from: date, *, exclude_assignment_id: int | None = None
    ) -> bool:
        """Return whether the employee already has an assignment starting on that date.

        Backs the "409 on duplicate same-date assignment" rule.
        """
        stmt = select(ShiftAssignment.assignment_id).where(
            ShiftAssignment.employee_id == employee_id,
            ShiftAssignment.effective_from == effective_from,
        )
        if exclude_assignment_id is not None:
            stmt = stmt.where(ShiftAssignment.assignment_id != exclude_assignment_id)
        return (await self.session.execute(stmt.limit(1))).first() is not None

    async def overlap_exists(
        self,
        employee_id: int,
        effective_from: date,
        effective_to: date | None,
        *,
        exclude_assignment_id: int | None = None,
    ) -> bool:
        """Return whether ``[effective_from, effective_to]`` overlaps another assignment.

        An open-ended range (``effective_to IS NULL``) extends to infinity. Backs the
        contract's ``409 ASSIGNMENT_OVERLAP`` business guard (no DB constraint exists).
        """
        stmt = select(ShiftAssignment.assignment_id).where(
            ShiftAssignment.employee_id == employee_id,
            (ShiftAssignment.effective_to.is_(None))
            | (ShiftAssignment.effective_to >= effective_from),
        )
        if effective_to is not None:
            stmt = stmt.where(ShiftAssignment.effective_from <= effective_to)
        if exclude_assignment_id is not None:
            stmt = stmt.where(ShiftAssignment.assignment_id != exclude_assignment_id)
        return (await self.session.execute(stmt.limit(1))).first() is not None

    @staticmethod
    def _search_conditions(
        org_id: int,
        *,
        employee_id: int | None,
        shift_id: int | None,
        active_on: date | None,
    ) -> list:
        """Build the WHERE conditions shared by :meth:`search` and :meth:`search_count`."""
        conds: list = [ShiftAssignment.org_id == org_id]
        if employee_id is not None:
            conds.append(ShiftAssignment.employee_id == employee_id)
        if shift_id is not None:
            conds.append(ShiftAssignment.shift_id == shift_id)
        if active_on is not None:
            conds.append(ShiftAssignment.effective_from <= active_on)
            conds.append(
                (ShiftAssignment.effective_to.is_(None))
                | (ShiftAssignment.effective_to >= active_on)
            )
        return conds

    async def search(
        self,
        org_id: int,
        *,
        employee_id: int | None = None,
        shift_id: int | None = None,
        active_on: date | None = None,
        sort_by: str | None = "effective_from",
        sort_order: SortOrder | str = SortOrder.DESC,
        page: int = 1,
        page_size: int = 25,
    ) -> list[ShiftAssignment]:
        """Return a filtered, sorted, paginated page of assignments in ``org_id``."""
        conds = self._search_conditions(
            org_id, employee_id=employee_id, shift_id=shift_id, active_on=active_on
        )
        stmt = select(ShiftAssignment).where(and_(*conds))
        stmt = apply_sorting(
            stmt,
            ShiftAssignment,
            sort_by,
            sort_order,
            allowed=_ASSIGNMENT_SORTS,
            default_sort_by="effective_from",
        )
        stmt = stmt.limit(page_size).offset((page - 1) * page_size)
        return list((await self.session.execute(stmt)).scalars().all())

    async def search_count(
        self,
        org_id: int,
        *,
        employee_id: int | None = None,
        shift_id: int | None = None,
        active_on: date | None = None,
    ) -> int:
        """Return the total number of assignments matching the same filters as :meth:`search`."""
        conds = self._search_conditions(
            org_id, employee_id=employee_id, shift_id=shift_id, active_on=active_on
        )
        stmt = select(func.count()).select_from(ShiftAssignment).where(and_(*conds))
        return int((await self.session.execute(stmt)).scalar_one())

    async def list_for_employee(
        self,
        org_id: int,
        employee_id: int,
        *,
        sort_by: str | None = "effective_from",
        sort_order: SortOrder | str = SortOrder.DESC,
        page: int = 1,
        page_size: int = 25,
    ) -> list[ShiftAssignment]:
        """Return the employee's assignment timeline (sorted, paginated)."""
        stmt = select(ShiftAssignment).where(
            ShiftAssignment.org_id == org_id, ShiftAssignment.employee_id == employee_id
        )
        stmt = apply_sorting(
            stmt,
            ShiftAssignment,
            sort_by,
            sort_order,
            allowed=_ASSIGNMENT_SORTS,
            default_sort_by="effective_from",
        )
        stmt = stmt.limit(page_size).offset((page - 1) * page_size)
        return list((await self.session.execute(stmt)).scalars().all())

    async def count_for_employee(self, org_id: int, employee_id: int) -> int:
        """Return the total number of assignments for an employee in ``org_id``."""
        stmt = (
            select(func.count())
            .select_from(ShiftAssignment)
            .where(
                ShiftAssignment.org_id == org_id,
                ShiftAssignment.employee_id == employee_id,
            )
        )
        return int((await self.session.execute(stmt)).scalar_one())


class RosterRepository(BaseRepository[Roster]):
    """Operations for ``roster`` — the per-date schedule that rotations materialise."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Roster)

    async def get_by_id_in_org(self, roster_id: int, org_id: int) -> Roster | None:
        """Return a roster row by id within ``org_id``, or ``None``."""
        stmt = select(Roster).where(Roster.roster_id == roster_id, Roster.org_id == org_id)
        return (await self.session.execute(stmt.limit(1))).scalar_one_or_none()

    async def exists_for_shift_on_or_after(self, shift_id: int, on_date: date) -> bool:
        """Return whether any roster row on/after ``on_date`` references ``shift_id``.

        Backs the "shift delete blocked while referenced by roster entries" rule
        (contract §4 #5 → ``409 SHIFT_IN_USE``).
        """
        stmt = select(Roster.roster_id).where(
            Roster.shift_id == shift_id, Roster.roster_date >= on_date
        )
        return (await self.session.execute(stmt.limit(1))).first() is not None

    @staticmethod
    def _range_conditions(
        org_id: int,
        date_from: date,
        date_to: date,
        *,
        employee_id: int | None,
        shift_id: int | None,
        employee_ids: list[int] | None,
    ) -> list:
        """Build the WHERE conditions shared by :meth:`search_range` and its count."""
        conds: list = [
            Roster.org_id == org_id,
            Roster.roster_date >= date_from,
            Roster.roster_date <= date_to,
        ]
        if employee_id is not None:
            conds.append(Roster.employee_id == employee_id)
        if employee_ids is not None:
            conds.append(Roster.employee_id.in_(employee_ids))
        if shift_id is not None:
            conds.append(Roster.shift_id == shift_id)
        return conds

    async def search_range(
        self,
        org_id: int,
        date_from: date,
        date_to: date,
        *,
        employee_id: int | None = None,
        shift_id: int | None = None,
        employee_ids: list[int] | None = None,
        page: int = 1,
        page_size: int = 25,
    ) -> list[Roster]:
        """Return a filtered, paginated page of roster rows in a date window.

        ``employee_ids`` confines the result to a resolved branch/department scope
        (the service resolves scope → employee ids to respect module boundaries).
        """
        conds = self._range_conditions(
            org_id,
            date_from,
            date_to,
            employee_id=employee_id,
            shift_id=shift_id,
            employee_ids=employee_ids,
        )
        stmt = (
            select(Roster)
            .where(and_(*conds))
            .order_by(Roster.roster_date.asc(), Roster.employee_id.asc())
            .limit(page_size)
            .offset((page - 1) * page_size)
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def search_range_count(
        self,
        org_id: int,
        date_from: date,
        date_to: date,
        *,
        employee_id: int | None = None,
        shift_id: int | None = None,
        employee_ids: list[int] | None = None,
    ) -> int:
        """Return the total roster rows matching the same filters as :meth:`search_range`."""
        conds = self._range_conditions(
            org_id,
            date_from,
            date_to,
            employee_id=employee_id,
            shift_id=shift_id,
            employee_ids=employee_ids,
        )
        stmt = select(func.count()).select_from(Roster).where(and_(*conds))
        return int((await self.session.execute(stmt)).scalar_one())

    async def get_for_employee_date(self, employee_id: int, roster_date: date) -> Roster | None:
        """Return the roster row for an employee on a date (unique), or ``None``."""
        stmt = select(Roster).where(
            Roster.employee_id == employee_id, Roster.roster_date == roster_date
        )
        return (await self.session.execute(stmt.limit(1))).scalar_one_or_none()

    async def exists_for_employee_date(self, employee_id: int, roster_date: date) -> bool:
        """Return whether a roster row already exists for the employee/date pair."""
        stmt = select(Roster.roster_id).where(
            Roster.employee_id == employee_id, Roster.roster_date == roster_date
        )
        return (await self.session.execute(stmt.limit(1))).first() is not None

    async def list_for_employee_range(
        self, org_id: int, employee_id: int, from_date: date, to_date: date
    ) -> list[Roster]:
        """Return an employee's roster rows within ``[from_date, to_date]`` (date-ordered)."""
        stmt = (
            select(Roster)
            .where(
                Roster.org_id == org_id,
                Roster.employee_id == employee_id,
                Roster.roster_date >= from_date,
                Roster.roster_date <= to_date,
            )
            .order_by(Roster.roster_date.asc())
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def bulk_create(self, rows: list[dict]) -> list[Roster]:
        """Insert many roster rows at once (rotation generation); flushed, not committed."""
        instances = [Roster(**row) for row in rows]
        self.session.add_all(instances)
        await self.session.flush()
        return instances

    async def delete_for_employee_range(
        self, org_id: int, employee_id: int, from_date: date, to_date: date
    ) -> int:
        """Delete an employee's roster rows in a date window (regeneration); returns count."""
        stmt = delete(Roster).where(
            Roster.org_id == org_id,
            Roster.employee_id == employee_id,
            Roster.roster_date >= from_date,
            Roster.roster_date <= to_date,
        )
        result = await self.session.execute(stmt.execution_options(synchronize_session=False))
        await self.session.flush()
        return int(result.rowcount or 0)


class WeeklyOffRepository(BaseRepository[EmployeeWeekoff]):
    """Operations for ``employee_weekoffs`` (weekly-off configuration).

    Note: this table has no ``org_id`` column — queries scope by ``employee_id``.
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, EmployeeWeekoff)

    async def list_for_employee(
        self, employee_id: int, *, active_only: bool = True
    ) -> list[EmployeeWeekoff]:
        """Return an employee's week-off rows, ordered by weekday.

        ``active_only`` keeps only currently-active rows (``effective_to IS NULL``),
        matching the partial unique index ``uq_employee_weekoffs_employee_id_day_of_week``.
        """
        stmt = select(EmployeeWeekoff).where(EmployeeWeekoff.employee_id == employee_id)
        if active_only:
            stmt = stmt.where(EmployeeWeekoff.effective_to.is_(None))
        stmt = stmt.order_by(EmployeeWeekoff.day_of_week.asc())
        return list((await self.session.execute(stmt)).scalars().all())

    async def get_by_id_for_employee(
        self, weekoff_id: int, employee_id: int
    ) -> EmployeeWeekoff | None:
        """Return a week-off row by id belonging to ``employee_id``, or ``None``."""
        stmt = select(EmployeeWeekoff).where(
            EmployeeWeekoff.weekoff_id == weekoff_id,
            EmployeeWeekoff.employee_id == employee_id,
        )
        return (await self.session.execute(stmt.limit(1))).scalar_one_or_none()

    async def get_active_for_day(
        self, employee_id: int, day_of_week: int
    ) -> EmployeeWeekoff | None:
        """Return the employee's active week-off row for a weekday, or ``None``."""
        stmt = select(EmployeeWeekoff).where(
            EmployeeWeekoff.employee_id == employee_id,
            EmployeeWeekoff.day_of_week == day_of_week,
            EmployeeWeekoff.effective_to.is_(None),
        )
        return (await self.session.execute(stmt.limit(1))).scalar_one_or_none()

    async def exists_active_for_day(
        self, employee_id: int, day_of_week: int, *, exclude_weekoff_id: int | None = None
    ) -> bool:
        """Return whether an active week-off row exists for the employee/weekday pair."""
        stmt = select(EmployeeWeekoff.weekoff_id).where(
            EmployeeWeekoff.employee_id == employee_id,
            EmployeeWeekoff.day_of_week == day_of_week,
            EmployeeWeekoff.effective_to.is_(None),
        )
        if exclude_weekoff_id is not None:
            stmt = stmt.where(EmployeeWeekoff.weekoff_id != exclude_weekoff_id)
        return (await self.session.execute(stmt.limit(1))).first() is not None

    # --- Batched operations (avoid N+1 across a set of employees) ------------
    async def list_for_employees(
        self, employee_ids: list[int], *, active_only: bool = True
    ) -> list[EmployeeWeekoff]:
        """Return week-off rows for many employees in a single query.

        Ordered by ``(employee_id, day_of_week)`` so callers can group by employee.
        """
        if not employee_ids:
            return []
        stmt = select(EmployeeWeekoff).where(EmployeeWeekoff.employee_id.in_(employee_ids))
        if active_only:
            stmt = stmt.where(EmployeeWeekoff.effective_to.is_(None))
        stmt = stmt.order_by(
            EmployeeWeekoff.employee_id.asc(), EmployeeWeekoff.day_of_week.asc()
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def active_for_day_by_employees(
        self, employee_ids: list[int], day_of_week: int
    ) -> list[EmployeeWeekoff]:
        """Return the active week-off rows for many employees on one weekday (single query)."""
        if not employee_ids:
            return []
        stmt = select(EmployeeWeekoff).where(
            EmployeeWeekoff.employee_id.in_(employee_ids),
            EmployeeWeekoff.day_of_week == day_of_week,
            EmployeeWeekoff.effective_to.is_(None),
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def close_by_ids(self, weekoff_ids: list[int], effective_to: date) -> int:
        """Close (effective-date) many active week-off rows in one UPDATE; returns count."""
        if not weekoff_ids:
            return 0
        stmt = (
            update(EmployeeWeekoff)
            .where(EmployeeWeekoff.weekoff_id.in_(weekoff_ids))
            .values(effective_to=effective_to)
        )
        result = await self.session.execute(stmt.execution_options(synchronize_session=False))
        await self.session.flush()
        return int(result.rowcount or 0)

    async def bulk_create(self, rows: list[dict]) -> list[EmployeeWeekoff]:
        """Insert many week-off rows at once (flushed, not committed)."""
        instances = [EmployeeWeekoff(**row) for row in rows]
        self.session.add_all(instances)
        await self.session.flush()
        return instances


__all__ = [
    "ShiftRepository",
    "ShiftDayTimingRepository",
    "ShiftAssignmentRepository",
    "RosterRepository",
    "WeeklyOffRepository",
]
