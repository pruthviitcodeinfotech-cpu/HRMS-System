"""Shift Management — service layer (business rules & orchestration).

Implements the behaviour of the Shift-Management API Contract (section 10): shift
definitions + per-day timings, shift assignment with supersession, the shift-resolve
lookup used by the Attendance Engine, shift rotations (roster generation), and
weekly-off configuration.

Design rules honoured here:

* **No direct database access.** All persistence goes through the Shift
  repositories; cross-module reads (employee / branch / department existence) go
  through the Employee module's repositories, and the actor's audit name through the
  RBAC :class:`UserRepository` — the same cross-module-via-repository pattern the
  Employee service uses. Audit rows go through :class:`AuditService`.
* **Validate all cross-module references before processing.** Employee, branch,
  department, and shift references are resolved/checked before any write.
* The service owns the transaction boundary (:class:`BaseService`); audit rows are
  written inside the same transaction as the mutation they describe.

Schema-reconciliation notes (the models are the source of truth):

* A shift's timings live in ``shift_day_timings`` (a uniform row with
  ``day_of_week = NULL`` or one row per weekday). ``crosses_midnight`` on the input
  is a validation-only flag (no column) and is not persisted.
* There is **no rotation table** — ``POST /shift-rotations`` materialises ``roster``
  rows (per employee, per date), so the response returns generated roster entries.
* ``day_of_week`` uses the schema convention 0=Sunday … 6=Saturday. Python's
  ``date.weekday()`` is Monday=0 … Sunday=6, so it is converted via
  ``(weekday() + 1) % 7`` in :meth:`_weekday_ordinal`.
* Working-day resolution uses the maximum fidelity the schema supports:
  :meth:`resolve_shift` combines the weekly-off configuration **and** the resolved
  shift's per-weekday ``shift_day_timings.is_working_day``. Anything beyond this
  (holiday calendars, attendance thresholds) is the Attendance Engine's concern.
* Shift-rotation generation is synchronous today but structured for a future
  background job — see :meth:`generate_rotation` / :meth:`_materialise_rotation`.
"""

from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions.base import (
    ConflictException,
    NotFoundException,
    ValidationException,
)
from app.modules.audit.constants import ActionType
from app.modules.audit.service import AuditService
from app.modules.employee.repository import (
    BranchRepository,
    DepartmentRepository,
    EmployeeRepository,
)
from app.modules.rbac.repository import UserRepository
from app.modules.shift.constants import WeekoffType
from app.modules.shift.repository import (
    RosterRepository,
    ShiftAssignmentRepository,
    ShiftDayTimingRepository,
    ShiftRepository,
    WeeklyOffRepository,
)
from app.modules.shift.schemas import (
    RosterEntrySchema,
    ShiftAssignmentListResponse,
    ShiftAssignmentQuery,
    ShiftAssignmentSchema,
    ShiftAssignRequest,
    ShiftCreateRequest,
    ShiftDayTimingInput,
    ShiftDetailSchema,
    ShiftListResponse,
    ShiftResolveQuery,
    ShiftResolveResponse,
    ShiftRotationRequest,
    ShiftRotationResponse,
    ShiftSchema,
    ShiftSummarySchema,
    ShiftUpdateRequest,
    WeeklyOffListResponse,
    WeeklyOffQuery,
    WeeklyOffSchema,
    WeeklyOffUpdateRequest,
)
from app.shared.base.service import BaseService
from app.shared.utils.datetime import utcnow

_AUDIT_MODULE = "Shift Management"
_SCAN_PAGE_SIZE = 200  # page size for scanning employees within a scope


class ShiftService(BaseService):
    """Shift Management business logic (data access via repositories only)."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)
        self.shifts = ShiftRepository(session)
        self.day_timings = ShiftDayTimingRepository(session)
        self.assignments = ShiftAssignmentRepository(session)
        self.rosters = RosterRepository(session)
        self.weekoffs = WeeklyOffRepository(session)
        # Cross-module reads (Employee Management owns these tables).
        self.employees = EmployeeRepository(session)
        self.branches = BranchRepository(session)
        self.departments = DepartmentRepository(session)
        # Actor name for the audit snapshot (User Management / RBAC).
        self.users = UserRepository(session)
        self.audit = AuditService(session)

    # =====================================================================
    # Shifts — CRUD
    # =====================================================================
    async def create_shift(
        self, *, org_id: int, actor_id: int, data: ShiftCreateRequest
    ) -> ShiftDetailSchema:
        """Define a shift and its day timings (409 on a duplicate name in the org)."""
        if await self.shifts.name_exists(org_id, data.shift_name):
            raise ConflictException("Shift name already in use.", code="duplicate_shift_name")

        payload = {
            "org_id": org_id,
            "shift_name": data.shift_name,
            "shift_type": data.shift_type.value,
            "is_open_shift": data.is_open_shift,
            "is_default": data.is_default,
            "is_uniform_time": data.is_uniform_time,
            "has_break_time": data.has_break_time,
            "shift_color": data.shift_color,
            "remark": data.remark,
            "is_advanced_mode": data.is_advanced_mode,
            "created_by": actor_id,
        }
        async with self.transaction():
            shift = await self.shifts.create(payload)
            await self._create_day_timings(shift.shift_id, data.day_timings)
            await self._audit(
                org_id=org_id,
                actor_id=actor_id,
                action_type=ActionType.INSERT,
                title="Shift created",
                description=f"Created shift '{shift.shift_name}'.",
            )
        return await self._load_shift_detail(org_id, shift.shift_id)

    async def update_shift(
        self, *, org_id: int, actor_id: int, shift_id: int, data: ShiftUpdateRequest
    ) -> ShiftDetailSchema:
        """Partially update a shift; when ``day_timings`` is supplied it replaces them."""
        shift = await self._get_active_shift(org_id, shift_id)
        updates = data.model_dump(exclude_unset=True, exclude={"day_timings"})

        if updates.get("shift_type") is not None and hasattr(updates["shift_type"], "value"):
            updates["shift_type"] = updates["shift_type"].value

        new_name = updates.get("shift_name")
        if new_name is not None and new_name != shift.shift_name:
            if await self.shifts.name_exists(org_id, new_name, exclude_shift_id=shift_id):
                raise ConflictException(
                    "Shift name already in use.", code="duplicate_shift_name"
                )

        async with self.transaction():
            if updates:
                await self.shifts.update(shift, updates)
            if data.day_timings is not None:
                await self.day_timings.delete_all_for_shift(shift_id)
                await self._create_day_timings(shift_id, data.day_timings)
            await self._audit(
                org_id=org_id,
                actor_id=actor_id,
                action_type=ActionType.UPDATE,
                title="Shift updated",
                description=f"Updated shift '{shift.shift_name}'.",
            )
        return await self._load_shift_detail(org_id, shift_id)

    async def get_shift(self, *, org_id: int, shift_id: int) -> ShiftDetailSchema:
        """Return a shift with its day timings."""
        return await self._load_shift_detail(org_id, shift_id)

    async def list_shifts(
        self,
        *,
        org_id: int,
        search: str | None = None,
        shift_type: str | None = None,
        is_default: bool | None = None,
        is_open_shift: bool | None = None,
        page: int = 1,
        page_size: int = 25,
    ) -> ShiftListResponse:
        """Return a filtered, searched, paginated page of shift definitions."""
        rows = await self.shifts.search(
            org_id,
            search=search,
            shift_type=shift_type,
            is_default=is_default,
            is_open_shift=is_open_shift,
            page=page,
            page_size=page_size,
        )
        total = await self.shifts.search_count(
            org_id,
            search=search,
            shift_type=shift_type,
            is_default=is_default,
            is_open_shift=is_open_shift,
        )
        items = [ShiftSummarySchema.model_validate(row) for row in rows]
        return ShiftListResponse.build(
            items=items, page=page, page_size=page_size, total_records=total
        )

    async def delete_shift(self, *, org_id: int, actor_id: int, shift_id: int) -> None:
        """Deactivate (soft-delete) a shift; blocked when active assignments reference it."""
        shift = await self._get_active_shift(org_id, shift_id)
        if await self.shifts.has_open_assignments(shift_id):
            raise ConflictException(
                "Shift has active assignments and cannot be deleted.",
                code="shift_in_use",
            )
        async with self.transaction():
            await self.shifts.soft_delete(shift)
            await self._audit(
                org_id=org_id,
                actor_id=actor_id,
                action_type=ActionType.DELETE,
                title="Shift deleted",
                description=f"Deactivated shift '{shift.shift_name}'.",
            )

    # =====================================================================
    # Shift assignment
    # =====================================================================
    async def assign_shift(
        self, *, org_id: int, actor_id: int, shift_id: int, data: ShiftAssignRequest
    ) -> ShiftAssignmentSchema:
        """Assign a shift to an employee, superseding the prior open assignment.

        Cross-reference validation: the shift and the employee must both exist in the
        org. 422 if ``effective_from`` precedes the employee's joining date; 409 on a
        duplicate same-date assignment. The prior open assignment (if any) is closed
        the day before the new one begins.
        """
        shift = await self._get_active_shift(org_id, shift_id)
        employee = await self._get_active_employee(org_id, data.employee_id)

        if employee.date_of_joining is not None and data.effective_from < employee.date_of_joining:
            raise ValidationException(
                "Shift assignment cannot start before the employee's joining date.",
                code="invalid_assignment_date",
            )
        if await self.assignments.exists_on_effective_from(data.employee_id, data.effective_from):
            raise ConflictException(
                "An assignment already starts on this date.", code="duplicate_assignment"
            )

        async with self.transaction():
            prior = await self.assignments.get_open_for_employee(org_id, data.employee_id)
            if prior is not None and prior.effective_from < data.effective_from:
                await self.assignments.update(
                    prior, {"effective_to": data.effective_from - timedelta(days=1)}
                )
            assignment = await self.assignments.create(
                {
                    "org_id": org_id,
                    "employee_id": data.employee_id,
                    "shift_id": shift_id,
                    "effective_from": data.effective_from,
                    "effective_to": data.effective_to,
                    "assigned_by": actor_id,
                }
            )
            await self._audit(
                org_id=org_id,
                actor_id=actor_id,
                action_type=ActionType.ASSIGN,
                title="Shift assigned",
                description=(
                    f"Assigned shift '{shift.shift_name}' from "
                    f"{data.effective_from.isoformat()}."
                ),
                employee_id=employee.employee_id,
                employee_name=employee.employee_name,
            )
        return ShiftAssignmentSchema.model_validate(assignment)

    async def list_assignments(
        self, *, org_id: int, query: ShiftAssignmentQuery
    ) -> ShiftAssignmentListResponse:
        """Return an employee's assignment timeline, or the single shift resolved for a date."""
        if query.employee_id is None:
            raise ValidationException(
                "employee_id is required.", code="validation_error"
            )

        if query.on_date is not None:
            resolved = await self.assignments.resolve_for_date(
                org_id, query.employee_id, query.on_date
            )
            items = [ShiftAssignmentSchema.model_validate(resolved)] if resolved else []
            return ShiftAssignmentListResponse.build(
                items=items, page=1, page_size=max(len(items), 1), total_records=len(items)
            )

        rows = await self.assignments.list_for_employee(
            org_id, query.employee_id, page=query.page, page_size=query.page_size
        )
        total = await self.assignments.count_for_employee(org_id, query.employee_id)
        items = [ShiftAssignmentSchema.model_validate(row) for row in rows]
        return ShiftAssignmentListResponse.build(
            items=items, page=query.page, page_size=query.page_size, total_records=total
        )

    async def resolve_shift(
        self, *, org_id: int, query: ShiftResolveQuery
    ) -> ShiftResolveResponse:
        """Resolve the shift effective for an employee on a date, plus day flags.

        Mirrors the Attendance Engine's internal lookup at the maximum fidelity the
        current schema supports: the effective assignment's shift (loaded with its
        day timings), whether the date is a configured weekly-off, and whether it is
        a working day. ``is_working_day`` combines **both** signals — it is false when
        the date is a weekly-off **or** when the resolved shift's timing for that
        weekday is marked non-working (``shift_day_timings.is_working_day = false``).
        """
        await self._get_active_employee(org_id, query.employee_id)
        weekday = self._weekday_ordinal(query.on_date)

        assignment = await self.assignments.resolve_for_date(
            org_id, query.employee_id, query.on_date
        )
        shift_schema: ShiftSchema | None = None
        shift_marks_working = True
        if assignment is not None:
            # get_detail eager-loads day_timings so the per-weekday working flag is
            # available without an extra query.
            shift = await self.shifts.get_detail(assignment.shift_id, org_id)
            if shift is not None:
                shift_schema = ShiftSchema.model_validate(shift)
                shift_marks_working = self._day_is_working(shift, weekday)

        weekoff = await self.weekoffs.get_active_for_day(query.employee_id, weekday)
        is_weekly_off = self._is_weekly_off(weekoff, query.on_date)
        return ShiftResolveResponse(
            shift=shift_schema,
            is_weekly_off=is_weekly_off,
            is_working_day=(not is_weekly_off) and shift_marks_working,
        )

    # =====================================================================
    # Shift rotations (roster generation)
    # =====================================================================
    async def generate_rotation(
        self, *, org_id: int, actor_id: int, data: ShiftRotationRequest
    ) -> ShiftRotationResponse:
        """Generate a rotating roster over ``horizon_days`` and materialise ``roster`` rows.

        Validates every shift in ``shift_sequence`` and every scope reference before
        writing. The ``shift_sequence`` is cycled per ``cadence`` (``daily`` advances
        each day, ``weekly`` advances every 7 days). Roster dates that fall on an
        employee's configured weekly-off are marked ``is_week_off`` with no shift.
        Existing roster rows in the window are replaced so regeneration is idempotent.

        Deferred async note (contract §10 returns ``202 Accepted``): today this runs
        **synchronously** in-request. When the project-wide background-job library is
        finalised (see ``PROJECT_CONTEXT.md`` / ``pyproject.toml`` open decision), the
        validation above should stay here and the heavy write loop —
        :meth:`_materialise_rotation` — should be **enqueued** as a job, with this
        method returning a job handle. That method is deliberately isolated so a worker
        can call it unchanged; no job dependency is introduced now.
        """
        for shift_id in data.shift_sequence:
            if not await self.shifts.exists_in_org(org_id, shift_id):
                raise ValidationException(
                    f"Shift {shift_id} does not exist.", code="invalid_shift"
                )

        employees = await self._employees_for_scope(org_id, data.group_scope)
        if not employees:
            raise ValidationException(
                "No active employees matched the rotation scope.", code="empty_rotation_scope"
            )

        async with self.transaction():
            generated = await self._materialise_rotation(org_id, actor_id, data, employees)
            await self._audit(
                org_id=org_id,
                actor_id=actor_id,
                action_type=ActionType.BULK_ASSIGN,
                title="Shift rotation generated",
                description=(
                    f"Rotation '{data.name}' generated {len(generated)} roster entries "
                    f"for {len(employees)} employees."
                ),
            )
        return ShiftRotationResponse(
            generated_count=len(generated),
            generated_assignments=[RosterEntrySchema.model_validate(r) for r in generated],
        )

    async def _materialise_rotation(
        self, org_id: int, actor_id: int, data: ShiftRotationRequest, employees: list
    ) -> list:
        """Write the rotating roster for ``employees`` (the worker-callable unit).

        Isolated so a future background job can call it unchanged. Caller owns the
        transaction. Weekly-offs are honoured: a date on an employee's active
        week-off gets ``is_week_off=True`` and no shift. Weekly-off rows for all
        target employees are read in **one** batched query to avoid N+1.
        """
        window_end = data.start_date + timedelta(days=data.horizon_days - 1)
        employee_ids = [employee.employee_id for employee in employees]

        weekoffs_by_employee: dict[int, dict[int, object]] = {}
        for row in await self.weekoffs.list_for_employees(employee_ids, active_only=True):
            weekoffs_by_employee.setdefault(row.employee_id, {})[row.day_of_week] = row

        generated: list = []
        for employee in employees:
            await self.rosters.delete_for_employee_range(
                org_id, employee.employee_id, data.start_date, window_end
            )
            by_day = weekoffs_by_employee.get(employee.employee_id, {})
            rows = []
            for offset in range(data.horizon_days):
                roster_date = data.start_date + timedelta(days=offset)
                weekoff = by_day.get(self._weekday_ordinal(roster_date))
                is_off = self._is_weekly_off(weekoff, roster_date)
                rows.append(
                    {
                        "org_id": org_id,
                        "employee_id": employee.employee_id,
                        "roster_date": roster_date,
                        "shift_id": None if is_off else self._rotation_shift(data, offset),
                        "is_week_off": is_off,
                        "created_by": actor_id,
                        "updated_by": actor_id,
                    }
                )
            generated.extend(await self.rosters.bulk_create(rows))
        return generated

    # =====================================================================
    # Weekly offs
    # =====================================================================
    async def get_weekly_offs(
        self, *, org_id: int, query: WeeklyOffQuery
    ) -> WeeklyOffListResponse:
        """Return the active weekly-off configuration for an employee or a department."""
        if query.employee_id is not None:
            await self._get_active_employee(org_id, query.employee_id)
            rows = await self.weekoffs.list_for_employee(query.employee_id, active_only=True)
        else:
            await self._require_department(org_id, query.department_id)
            employees = await self._all_employees_by_filter(
                org_id, department_id=query.department_id
            )
            # One batched read for the whole department (no per-employee N+1).
            employee_ids = [employee.employee_id for employee in employees]
            rows = await self.weekoffs.list_for_employees(employee_ids, active_only=True)
        items = [WeeklyOffSchema.model_validate(row) for row in rows]
        return WeeklyOffListResponse.build(
            items=items, page=1, page_size=max(len(items), 1), total_records=len(items)
        )

    async def set_weekly_off(
        self, *, org_id: int, actor_id: int, data: WeeklyOffUpdateRequest
    ) -> WeeklyOffSchema:
        """Set a weekday's week-off configuration for an employee, or a whole department.

        Exactly one of ``employee_id`` / ``department_id`` is required (enforced by the
        schema). An existing active row for the same weekday is closed (effective-dated)
        before the new one is inserted, preserving the partial-unique invariant.
        """
        effective_from = data.effective_from or utcnow().date()

        async with self.transaction():
            if data.employee_id is not None:
                await self._get_active_employee(org_id, data.employee_id)
                row = await self._upsert_weekoff(actor_id, data.employee_id, data, effective_from)
                await self._audit(
                    org_id=org_id,
                    actor_id=actor_id,
                    action_type=ActionType.ASSIGN,
                    title="Weekly-off updated",
                    description=f"Set weekday {int(data.day_of_week)} to {data.weekoff_type.value}.",
                    employee_id=data.employee_id,
                )
                return WeeklyOffSchema.model_validate(row)

            await self._require_department(org_id, data.department_id)
            employees = await self._all_employees_by_filter(
                org_id, department_id=data.department_id
            )
            if not employees:
                raise NotFoundException(
                    "No active employees in the department.", code="not_found"
                )
            # Batched upsert: one read of existing active rows, one bulk close, one
            # bulk insert — avoids the per-employee N+1 (3 queries instead of 3N).
            employee_ids = [employee.employee_id for employee in employees]
            day = int(data.day_of_week)
            existing = await self.weekoffs.active_for_day_by_employees(employee_ids, day)
            await self.weekoffs.close_by_ids(
                [row.weekoff_id for row in existing], effective_from - timedelta(days=1)
            )
            created = await self.weekoffs.bulk_create(
                [
                    self._weekoff_payload(actor_id, employee_id, data, effective_from)
                    for employee_id in employee_ids
                ]
            )
            await self._audit(
                org_id=org_id,
                actor_id=actor_id,
                action_type=ActionType.BULK_ASSIGN,
                title="Weekly-off bulk updated",
                description=(
                    f"Set weekday {day} to {data.weekoff_type.value} "
                    f"for {len(employees)} employees."
                ),
            )
            return WeeklyOffSchema.model_validate(created[0])

    # =====================================================================
    # Internal helpers
    # =====================================================================
    async def _get_active_shift(self, org_id: int, shift_id: int):
        """Return the active shift or raise :class:`NotFoundException`."""
        shift = await self.shifts.get_active_by_id(shift_id, org_id)
        if shift is None:
            raise NotFoundException("Shift not found.", code="not_found")
        return shift

    async def _get_active_employee(self, org_id: int, employee_id: int):
        """Cross-module: return the active employee or raise ``not_found`` (404)."""
        employee = await self.employees.get_active_by_id(employee_id, org_id)
        if employee is None:
            raise NotFoundException("Employee not found.", code="not_found")
        return employee

    async def _require_department(self, org_id: int, department_id: int | None) -> None:
        """Cross-module: ensure a department exists and is active in the org."""
        if department_id is None or not await self.departments.exists_active(org_id, department_id):
            raise NotFoundException("Department not found.", code="not_found")

    async def _load_shift_detail(self, org_id: int, shift_id: int) -> ShiftDetailSchema:
        """Fetch the eager-loaded shift and build the detail projection."""
        shift = await self.shifts.get_detail(shift_id, org_id)
        if shift is None:
            raise NotFoundException("Shift not found.", code="not_found")
        return ShiftDetailSchema.model_validate(shift)

    async def _create_day_timings(
        self, shift_id: int, timings: list[ShiftDayTimingInput]
    ) -> None:
        """Persist a shift's day-timing rows (``crosses_midnight`` is not a column)."""
        for timing in timings:
            await self.day_timings.create(
                {
                    "shift_id": shift_id,
                    "day_of_week": (
                        int(timing.day_of_week) if timing.day_of_week is not None else None
                    ),
                    "start_time": timing.start_time,
                    "end_time": timing.end_time,
                    "break_start_time": timing.break_start_time,
                    "break_end_time": timing.break_end_time,
                    "duration_minutes": timing.duration_minutes,
                    "is_working_day": timing.is_working_day,
                }
            )

    @staticmethod
    def _weekoff_payload(
        actor_id: int, employee_id: int, data: WeeklyOffUpdateRequest, effective_from: date
    ) -> dict:
        """Build an ``employee_weekoffs`` insert payload (shared by single + bulk paths)."""
        return {
            "employee_id": employee_id,
            "day_of_week": int(data.day_of_week),
            "weekoff_type": data.weekoff_type.value,
            "occurrence_1st": data.occurrence_1st,
            "occurrence_2nd": data.occurrence_2nd,
            "occurrence_3rd": data.occurrence_3rd,
            "occurrence_4th": data.occurrence_4th,
            "occurrence_5th": data.occurrence_5th,
            "effective_from": effective_from,
            "effective_to": data.effective_to,
            "updated_by": actor_id,
        }

    async def _upsert_weekoff(
        self, actor_id: int, employee_id: int, data: WeeklyOffUpdateRequest, effective_from: date
    ):
        """Effective-date a weekday's week-off for one employee (close old, insert new)."""
        existing = await self.weekoffs.get_active_for_day(employee_id, int(data.day_of_week))
        if existing is not None:
            await self.weekoffs.update(
                existing, {"effective_to": effective_from - timedelta(days=1)}
            )
        return await self.weekoffs.create(
            self._weekoff_payload(actor_id, employee_id, data, effective_from)
        )

    async def _employees_for_scope(self, org_id: int, scope) -> list:
        """Resolve the unique active employees a rotation targets (validated)."""
        by_id: dict[int, object] = {}
        for employee_id in scope.employee_ids:
            by_id[employee_id] = await self._get_active_employee(org_id, employee_id)
        for department_id in scope.department_ids:
            await self._require_department(org_id, department_id)
            for employee in await self._all_employees_by_filter(
                org_id, department_id=department_id
            ):
                by_id[employee.employee_id] = employee
        for branch_id in scope.branch_ids:
            if not await self.branches.exists_active(org_id, branch_id):
                raise NotFoundException("Branch not found.", code="not_found")
            for employee in await self._all_employees_by_filter(org_id, branch_id=branch_id):
                by_id[employee.employee_id] = employee
        return list(by_id.values())

    async def _all_employees_by_filter(self, org_id: int, **filters) -> list:
        """Page through the employee search to collect every matching active employee."""
        collected: list = []
        page = 1
        while True:
            rows = await self.employees.search(
                org_id, page=page, page_size=_SCAN_PAGE_SIZE, **filters
            )
            collected.extend(rows)
            if len(rows) < _SCAN_PAGE_SIZE:
                break
            page += 1
        return collected

    @staticmethod
    def _weekday_ordinal(on_date: date) -> int:
        """Convert a date to the schema's weekday ordinal (0=Sunday … 6=Saturday)."""
        return (on_date.weekday() + 1) % 7

    @staticmethod
    def _rotation_shift(data: ShiftRotationRequest, offset: int) -> int:
        """Pick the shift for day ``offset`` of a rotation, per its cadence."""
        sequence = data.shift_sequence
        if data.cadence.strip().lower() == "weekly":
            return sequence[(offset // 7) % len(sequence)]
        return sequence[offset % len(sequence)]

    @staticmethod
    def _day_is_working(shift, weekday: int) -> bool:
        """Whether the shift marks ``weekday`` as a working day (per ``shift_day_timings``).

        Prefers an exact per-weekday timing, falls back to the uniform timing
        (``day_of_week IS NULL``), and defaults to working when no timing is defined.
        """
        timings = getattr(shift, "day_timings", None) or []
        exact = next((t for t in timings if t.day_of_week == weekday), None)
        uniform = next((t for t in timings if t.day_of_week is None), None)
        timing = exact or uniform
        return bool(timing.is_working_day) if timing is not None else True

    @staticmethod
    def _is_weekly_off(weekoff, on_date: date) -> bool:
        """Whether ``on_date`` is a weekly-off given the active week-off row.

        ``working`` → never off; ``week_off`` → always off; ``occasional_week_off`` →
        off only on the selected occurrence(s) of that weekday within the month.
        """
        if weekoff is None or weekoff.weekoff_type == WeekoffType.WORKING.value:
            return False
        if weekoff.weekoff_type == WeekoffType.WEEK_OFF.value:
            return True
        occurrence = (on_date.day - 1) // 7 + 1  # 1st … 5th occurrence of this weekday
        flags = [
            weekoff.occurrence_1st,
            weekoff.occurrence_2nd,
            weekoff.occurrence_3rd,
            weekoff.occurrence_4th,
            weekoff.occurrence_5th,
        ]
        return bool(flags[occurrence - 1]) if 1 <= occurrence <= 5 else False

    async def _actor_name(self, org_id: int, actor_id: int) -> str:
        """Resolve the acting user's display name for the audit snapshot (best-effort)."""
        user = await self.users.get_active_by_id(actor_id, org_id)
        name = getattr(user, "name", None)
        return name if isinstance(name, str) and name else f"user #{actor_id}"

    async def _audit(
        self,
        *,
        org_id: int,
        actor_id: int,
        action_type: ActionType,
        title: str,
        description: str,
        employee_id: int | None = None,
        employee_name: str | None = None,
        sub_module: str | None = None,
    ) -> None:
        """Write one audit row for a mutation (inside the caller's transaction)."""
        await self.audit.record(
            org_id=org_id,
            module=_AUDIT_MODULE,
            sub_module=sub_module,
            action_type=action_type,
            title=title,
            description=description,
            performed_by_user_id=actor_id,
            performed_by_name=await self._actor_name(org_id, actor_id),
            employee_id=employee_id,
            employee_name=employee_name,
        )


__all__ = ["ShiftService"]
