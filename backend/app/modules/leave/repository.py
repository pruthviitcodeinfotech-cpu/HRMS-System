"""Leave & Holiday Management — data-access layer (async SQLAlchemy).

One focused repository per aggregate, all extending BaseRepository and operating
on the existing Leave-Management models. Database operations only — no business rules.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.constants.enums import SortOrder
from app.modules.employee.models.employee import Employee
from app.modules.leave.constants import LeaveRequestStatus
from app.modules.leave.models import (
    EmployeeHolidayAssignment,
    EmployeeLeaveAllocation,
    EmployeeLeaveBalance,
    HolidayTemplate,
    HolidayTemplateItem,
    LeaveBalanceAdjustment,
    LeaveRequest,
    LeaveSetting,
    LeaveType,
)
from app.shared.base.repository import BaseRepository
from app.shared.utils.query import apply_sorting

# ===========================================================================
# 1. Leave Type Repository
# ===========================================================================


class LeaveTypeRepository(BaseRepository[LeaveType]):
    """CRUD, search, and exists checks for leave types."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, LeaveType)

    async def get_by_id_in_org(self, org_id: int, leave_type_id: int) -> LeaveType | None:
        """Return a non-deleted leave type by ID scoped to org_id, or None."""
        stmt = select(LeaveType).where(
            LeaveType.id == leave_type_id,
            LeaveType.org_id == org_id,
            LeaveType.is_deleted.is_(False),
        )
        return (await self.session.execute(stmt.limit(1))).scalar_one_or_none()

    async def alias_exists(self, org_id: int, alias: str, exclude_id: int | None = None) -> bool:
        """Check if a non-deleted leave type with the same alias exists in the organization."""
        stmt = select(LeaveType.id).where(
            LeaveType.org_id == org_id,
            LeaveType.alias == alias,
            LeaveType.is_deleted.is_(False),
        )
        if exclude_id is not None:
            stmt = stmt.where(LeaveType.id != exclude_id)
        return (await self.session.execute(stmt.limit(1))).first() is not None

    async def exists_in_org(self, org_id: int, leave_type_id: int) -> bool:
        """Check if a non-deleted leave type exists in the organization."""
        stmt = select(LeaveType.id).where(
            LeaveType.id == leave_type_id,
            LeaveType.org_id == org_id,
            LeaveType.is_deleted.is_(False),
        )
        return (await self.session.execute(stmt.limit(1))).first() is not None

    async def has_references(self, leave_type_id: int) -> bool:
        """Return whether any active balance or leave request references this leave type."""
        req_stmt = select(LeaveRequest.id).where(
            LeaveRequest.leave_type_id == leave_type_id
        ).limit(1)
        if (await self.session.execute(req_stmt)).first() is not None:
            return True

        bal_stmt = select(EmployeeLeaveBalance.id).where(
            EmployeeLeaveBalance.leave_type_id == leave_type_id
        ).limit(1)
        if (await self.session.execute(bal_stmt)).first() is not None:
            return True

        return False

    async def soft_delete(self, instance: LeaveType) -> LeaveType:
        """Soft-delete a leave type by setting ``is_deleted=True``."""
        return await self.update(instance, {"is_deleted": True})

    @staticmethod
    def _search_conditions(
        org_id: int,
        search: str | None = None,
        is_active: bool | None = None,
    ) -> list:
        conds = [LeaveType.org_id == org_id, LeaveType.is_deleted.is_(False)]
        if is_active is not None:
            conds.append(LeaveType.is_active.is_(is_active))
        if search:
            conds.append(LeaveType.name.ilike(f"%{search.strip()}%"))
        return conds

    async def search(
        self,
        org_id: int,
        *,
        search: str | None = None,
        is_active: bool | None = None,
        sort_by: str | None = "name",
        sort_order: SortOrder | str = SortOrder.ASC,
        page: int = 1,
        page_size: int = 25,
    ) -> list[LeaveType]:
        """Return a filtered, sorted, paginated page of leave types."""
        conds = self._search_conditions(org_id, search=search, is_active=is_active)
        stmt = select(LeaveType).where(and_(*conds))
        stmt = apply_sorting(
            stmt,
            LeaveType,
            sort_by,
            sort_order,
            allowed={"name", "alias", "created_at", "updated_at"},
            default_sort_by="name",
        )
        stmt = stmt.limit(page_size).offset((page - 1) * page_size)
        return list((await self.session.execute(stmt)).scalars().all())

    async def search_count(
        self,
        org_id: int,
        *,
        search: str | None = None,
        is_active: bool | None = None,
    ) -> int:
        """Return the count of leave types matching the search criteria."""
        conds = self._search_conditions(org_id, search=search, is_active=is_active)
        stmt = select(func.count()).select_from(LeaveType).where(and_(*conds))
        return int((await self.session.execute(stmt)).scalar_one())


# ===========================================================================
# 2. Leave Settings Repository
# ===========================================================================


class LeaveSettingRepository(BaseRepository[LeaveSetting]):
    """Operations for organization-level leave cycle configuration."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, LeaveSetting)

    async def get_by_org_id(self, org_id: int) -> LeaveSetting | None:
        """Return the single leave setting configuration for the organization."""
        stmt = select(LeaveSetting).where(LeaveSetting.org_id == org_id)
        return (await self.session.execute(stmt.limit(1))).scalar_one_or_none()

    async def upsert(self, org_id: int, data: dict[str, Any]) -> LeaveSetting:
        """Upsert the single leave setting configuration for an organization."""
        existing = await self.get_by_org_id(org_id)
        if existing:
            return await self.update(existing, data)
        else:
            insert_data = {**data, "org_id": org_id}
            return await self.create(insert_data)


# ===========================================================================
# 3. Employee Leave Balance Repository
# ===========================================================================


class EmployeeLeaveBalanceRepository(BaseRepository[EmployeeLeaveBalance]):
    """CRUD, search, and details for per-employee leave balances."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, EmployeeLeaveBalance)

    async def get_by_employee_type_year(
        self, employee_id: int, leave_type_id: int, cycle_year: int
    ) -> EmployeeLeaveBalance | None:
        """Return a specific leave balance with its leave_type eager-loaded."""
        stmt = (
            select(EmployeeLeaveBalance)
            .where(
                EmployeeLeaveBalance.employee_id == employee_id,
                EmployeeLeaveBalance.leave_type_id == leave_type_id,
                EmployeeLeaveBalance.cycle_year == cycle_year,
            )
            .options(selectinload(EmployeeLeaveBalance.leave_type))
        )
        return (await self.session.execute(stmt.limit(1))).scalar_one_or_none()

    async def list_by_employee(
        self, employee_id: int, cycle_year: int, *, leave_type_id: int | None = None
    ) -> list[EmployeeLeaveBalance]:
        """List leave balances for an employee, eager-loading leave_types."""
        stmt = (
            select(EmployeeLeaveBalance)
            .where(
                EmployeeLeaveBalance.employee_id == employee_id,
                EmployeeLeaveBalance.cycle_year == cycle_year,
            )
            .options(selectinload(EmployeeLeaveBalance.leave_type))
        )
        if leave_type_id is not None:
            stmt = stmt.where(EmployeeLeaveBalance.leave_type_id == leave_type_id)
        return list((await self.session.execute(stmt)).scalars().all())

    @staticmethod
    def _search_conditions(
        org_id: int,
        *,
        leave_type_id: int | None = None,
        cycle_year: int | None = None,
        employee_id: int | None = None,
    ) -> list:
        conds = [LeaveType.org_id == org_id, LeaveType.is_deleted.is_(False)]
        if leave_type_id is not None:
            conds.append(EmployeeLeaveBalance.leave_type_id == leave_type_id)
        if cycle_year is not None:
            conds.append(EmployeeLeaveBalance.cycle_year == cycle_year)
        if employee_id is not None:
            conds.append(EmployeeLeaveBalance.employee_id == employee_id)
        return conds

    async def search(
        self,
        org_id: int,
        *,
        leave_type_id: int | None = None,
        cycle_year: int | None = None,
        employee_id: int | None = None,
        branch_id: int | None = None,
        dept_id: int | None = None,
        page: int = 1,
        page_size: int = 25,
    ) -> list[EmployeeLeaveBalance]:
        """Return a filtered, eager-loaded, paginated page of leave balances."""
        conds = self._search_conditions(
            org_id,
            leave_type_id=leave_type_id,
            cycle_year=cycle_year,
            employee_id=employee_id,
        )
        stmt = select(EmployeeLeaveBalance).join(LeaveType)
        if branch_id is not None or dept_id is not None:
            stmt = stmt.join(Employee, Employee.employee_id == EmployeeLeaveBalance.employee_id)
            if branch_id is not None:
                conds.append(Employee.master_branch_id == branch_id)
            if dept_id is not None:
                conds.append(Employee.dept_id == dept_id)
        stmt = stmt.where(and_(*conds)).options(selectinload(EmployeeLeaveBalance.leave_type))
        stmt = stmt.limit(page_size).offset((page - 1) * page_size)
        return list((await self.session.execute(stmt)).scalars().all())

    async def search_count(
        self,
        org_id: int,
        *,
        leave_type_id: int | None = None,
        cycle_year: int | None = None,
        employee_id: int | None = None,
        branch_id: int | None = None,
        dept_id: int | None = None,
    ) -> int:
        """Return the count of leave balances matching the filter criteria."""
        conds = self._search_conditions(
            org_id,
            leave_type_id=leave_type_id,
            cycle_year=cycle_year,
            employee_id=employee_id,
        )
        stmt = select(func.count()).select_from(EmployeeLeaveBalance).join(LeaveType)
        if branch_id is not None or dept_id is not None:
            stmt = stmt.join(Employee, Employee.employee_id == EmployeeLeaveBalance.employee_id)
            if branch_id is not None:
                conds.append(Employee.master_branch_id == branch_id)
            if dept_id is not None:
                conds.append(Employee.dept_id == dept_id)
        stmt = stmt.where(and_(*conds))
        return int((await self.session.execute(stmt)).scalar_one())


# ===========================================================================
# 4. Leave Balance Adjustment Repository
# ===========================================================================


class LeaveBalanceAdjustmentRepository(BaseRepository[LeaveBalanceAdjustment]):
    """Operations for leave balance adjustment logging."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, LeaveBalanceAdjustment)

    async def list_history(
        self, employee_id: int, cycle_year: int, *, leave_type_id: int | None = None
    ) -> list[LeaveBalanceAdjustment]:
        """Return adjustment history logs with their leave_type eager-loaded."""
        stmt = (
            select(LeaveBalanceAdjustment)
            .where(
                LeaveBalanceAdjustment.employee_id == employee_id,
                LeaveBalanceAdjustment.cycle_year == cycle_year,
            )
            .options(selectinload(LeaveBalanceAdjustment.leave_type))
            .order_by(LeaveBalanceAdjustment.adjusted_at.desc())
        )
        if leave_type_id is not None:
            stmt = stmt.where(LeaveBalanceAdjustment.leave_type_id == leave_type_id)
        return list((await self.session.execute(stmt)).scalars().all())


# ===========================================================================
# 5. Employee Leave Allocation Repository
# ===========================================================================


class EmployeeLeaveAllocationRepository(BaseRepository[EmployeeLeaveAllocation]):
    """Operations for leave allocation events."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, EmployeeLeaveAllocation)

    async def get_for_cycle(
        self,
        employee_id: int,
        leave_type_id: int,
        cycle_year: int,
        *,
        cycle_period: str | None = None,
    ) -> EmployeeLeaveAllocation | None:
        """Return the allocation already made for this employee/type/cycle, if any.

        This is the idempotency probe for the auto-allocation job: the accrual credits
        an employee only when this returns ``None``, so a re-run (or an arq retry) can
        never double-credit. ``cycle_period`` discriminates the monthly accruals within
        a cycle year; yearly leave types allocate once, with ``cycle_period IS NULL``.
        """
        stmt = select(EmployeeLeaveAllocation).where(
            EmployeeLeaveAllocation.employee_id == employee_id,
            EmployeeLeaveAllocation.leave_type_id == leave_type_id,
            EmployeeLeaveAllocation.cycle_year == cycle_year,
            (
                EmployeeLeaveAllocation.cycle_period.is_(None)
                if cycle_period is None
                else EmployeeLeaveAllocation.cycle_period == cycle_period
            ),
        )
        return (await self.session.execute(stmt.limit(1))).scalar_one_or_none()

    async def list_allocations(
        self, employee_id: int, *, cycle_year: int | None = None
    ) -> list[EmployeeLeaveAllocation]:
        """List leave allocation history with eager-loaded leave_types."""
        stmt = (
            select(EmployeeLeaveAllocation)
            .where(EmployeeLeaveAllocation.employee_id == employee_id)
            .options(selectinload(EmployeeLeaveAllocation.leave_type))
            .order_by(EmployeeLeaveAllocation.allocation_date.desc())
        )
        if cycle_year is not None:
            stmt = stmt.where(EmployeeLeaveAllocation.cycle_year == cycle_year)
        return list((await self.session.execute(stmt)).scalars().all())


# ===========================================================================
# 6. Leave Request Repository
# ===========================================================================


class LeaveRequestRepository(BaseRepository[LeaveRequest]):
    """CRUD, search, and overlap checks for leave requests."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, LeaveRequest)

    async def get_by_id_in_org(self, org_id: int, request_id: int) -> LeaveRequest | None:
        """Return a leave request with its leave_type eager-loaded."""
        stmt = (
            select(LeaveRequest)
            .join(LeaveType)
            .where(
                LeaveRequest.id == request_id,
                LeaveType.org_id == org_id,
            )
            .options(selectinload(LeaveRequest.leave_type))
        )
        return (await self.session.execute(stmt.limit(1))).scalar_one_or_none()

    async def has_overlap(
        self, employee_id: int, start_date: date, end_date: date, exclude_request_id: int | None = None
    ) -> bool:
        """Return whether an employee already has overlapping pending/approved requests."""
        stmt = select(LeaveRequest.id).where(
            LeaveRequest.employee_id == employee_id,
            LeaveRequest.status.in_([LeaveRequestStatus.PENDING, LeaveRequestStatus.APPROVED]),
            LeaveRequest.start_date <= end_date,
            LeaveRequest.end_date >= start_date,
        )
        if exclude_request_id is not None:
            stmt = stmt.where(LeaveRequest.id != exclude_request_id)
        return (await self.session.execute(stmt.limit(1))).first() is not None

    @staticmethod
    def _search_conditions(
        org_id: int,
        *,
        employee_id: int | None = None,
        leave_type_id: int | None = None,
        status: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> list:
        conds = [LeaveType.org_id == org_id]
        if employee_id is not None:
            conds.append(LeaveRequest.employee_id == employee_id)
        if leave_type_id is not None:
            conds.append(LeaveRequest.leave_type_id == leave_type_id)
        if status is not None:
            conds.append(LeaveRequest.status == status)
        if date_from is not None:
            conds.append(LeaveRequest.end_date >= date_from)
        if date_to is not None:
            conds.append(LeaveRequest.start_date <= date_to)
        return conds

    async def search(
        self,
        org_id: int,
        *,
        employee_id: int | None = None,
        leave_type_id: int | None = None,
        status: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        branch_id: int | None = None,
        dept_id: int | None = None,
        sort_by: str | None = "applied_on",
        sort_order: SortOrder | str = SortOrder.DESC,
        page: int = 1,
        page_size: int = 25,
    ) -> list[LeaveRequest]:
        """Return a filtered, sorted, paginated page of leave requests."""
        conds = self._search_conditions(
            org_id,
            employee_id=employee_id,
            leave_type_id=leave_type_id,
            status=status,
            date_from=date_from,
            date_to=date_to,
        )
        stmt = select(LeaveRequest).join(LeaveType)
        if branch_id is not None or dept_id is not None:
            stmt = stmt.join(Employee, Employee.employee_id == LeaveRequest.employee_id)
            if branch_id is not None:
                conds.append(Employee.master_branch_id == branch_id)
            if dept_id is not None:
                conds.append(Employee.dept_id == dept_id)
        stmt = stmt.where(and_(*conds)).options(selectinload(LeaveRequest.leave_type))
        stmt = apply_sorting(
            stmt,
            LeaveRequest,
            sort_by,
            sort_order,
            allowed={"applied_on", "start_date", "end_date", "created_at"},
            default_sort_by="applied_on",
        )
        stmt = stmt.limit(page_size).offset((page - 1) * page_size)
        return list((await self.session.execute(stmt)).scalars().all())

    async def search_count(
        self,
        org_id: int,
        *,
        employee_id: int | None = None,
        leave_type_id: int | None = None,
        status: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        branch_id: int | None = None,
        dept_id: int | None = None,
    ) -> int:
        """Return the total count of leave requests matching filter criteria."""
        conds = self._search_conditions(
            org_id,
            employee_id=employee_id,
            leave_type_id=leave_type_id,
            status=status,
            date_from=date_from,
            date_to=date_to,
        )
        stmt = select(func.count()).select_from(LeaveRequest).join(LeaveType)
        if branch_id is not None or dept_id is not None:
            stmt = stmt.join(Employee, Employee.employee_id == LeaveRequest.employee_id)
            if branch_id is not None:
                conds.append(Employee.master_branch_id == branch_id)
            if dept_id is not None:
                conds.append(Employee.dept_id == dept_id)
        stmt = stmt.where(and_(*conds))
        return int((await self.session.execute(stmt)).scalar_one())


# ===========================================================================
# 7. Holiday Template Repository
# ===========================================================================


class HolidayTemplateRepository(BaseRepository[HolidayTemplate]):
    """CRUD, search, and exists checks for holiday templates/groups."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, HolidayTemplate)

    async def name_exists(self, org_id: int, name: str, exclude_id: int | None = None) -> bool:
        """Return whether a template with the same name exists (non-deleted)."""
        stmt = select(HolidayTemplate.id).where(
            HolidayTemplate.org_id == org_id,
            func.lower(HolidayTemplate.name) == func.lower(name),
            HolidayTemplate.is_deleted.is_(False),
        )
        if exclude_id is not None:
            stmt = stmt.where(HolidayTemplate.id != exclude_id)
        return (await self.session.execute(stmt.limit(1))).first() is not None

    async def get_by_id_in_org(self, org_id: int, template_id: int) -> HolidayTemplate | None:
        """Return a template by ID in org, eager-loading its items."""
        stmt = (
            select(HolidayTemplate)
            .where(
                HolidayTemplate.id == template_id,
                HolidayTemplate.org_id == org_id,
                HolidayTemplate.is_deleted.is_(False),
            )
            .options(selectinload(HolidayTemplate.items))
        )
        return (await self.session.execute(stmt.limit(1))).scalar_one_or_none()

    @staticmethod
    def _search_conditions(org_id: int) -> list:
        return [HolidayTemplate.org_id == org_id, HolidayTemplate.is_deleted.is_(False)]

    async def search(
        self,
        org_id: int,
        *,
        page: int = 1,
        page_size: int = 25,
    ) -> list[HolidayTemplate]:
        """Return a sorted, paginated list of non-deleted holiday templates."""
        conds = self._search_conditions(org_id)
        stmt = select(HolidayTemplate).where(and_(*conds))
        stmt = apply_sorting(
            stmt,
            HolidayTemplate,
            "name",
            SortOrder.ASC,
            allowed={"name", "created_at"},
            default_sort_by="name",
        )
        stmt = stmt.limit(page_size).offset((page - 1) * page_size)
        return list((await self.session.execute(stmt)).scalars().all())

    async def search_count(self, org_id: int) -> int:
        """Return the count of holiday templates in the organization."""
        conds = self._search_conditions(org_id)
        stmt = select(func.count()).select_from(HolidayTemplate).where(and_(*conds))
        return int((await self.session.execute(stmt)).scalar_one())

    async def soft_delete(self, instance: HolidayTemplate) -> HolidayTemplate:
        """Soft-delete a template."""
        return await self.update(instance, {"is_deleted": True})


# ===========================================================================
# 8. Employee Holiday Assignment Repository
# ===========================================================================


class EmployeeHolidayAssignmentRepository(BaseRepository[EmployeeHolidayAssignment]):
    """Operations for employee holiday group assignments."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, EmployeeHolidayAssignment)

    async def get_by_employee_id(self, employee_id: int) -> EmployeeHolidayAssignment | None:
        """Return the current assignment record for an employee."""
        stmt = select(EmployeeHolidayAssignment).where(
            EmployeeHolidayAssignment.employee_id == employee_id
        )
        return (await self.session.execute(stmt.limit(1))).scalar_one_or_none()

    async def upsert_assignment(
        self, employee_id: int, template_id: int, assigned_by: int
    ) -> EmployeeHolidayAssignment:
        """Upsert assignment, archiving the current template as previous_template_id."""
        existing = await self.get_by_employee_id(employee_id)
        if existing:
            prev_id = existing.template_id
            return await self.update(
                existing,
                {
                    "template_id": template_id,
                    "previous_template_id": prev_id,
                    "assigned_by": assigned_by,
                    "assigned_at": func.now(),
                },
            )
        else:
            return await self.create(
                {
                    "employee_id": employee_id,
                    "template_id": template_id,
                    "previous_template_id": None,
                    "assigned_by": assigned_by,
                }
            )


# ===========================================================================
# 9. Holiday Template Item Repository
# ===========================================================================


class HolidayTemplateItemRepository(BaseRepository[HolidayTemplateItem]):
    """Operations for individual holiday items inside templates."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, HolidayTemplateItem)

    async def get_by_id_in_template(self, template_id: int, item_id: int) -> HolidayTemplateItem | None:
        """Return a non-deleted item by ID within a template."""
        stmt = select(HolidayTemplateItem).where(
            HolidayTemplateItem.id == item_id,
            HolidayTemplateItem.template_id == template_id,
            HolidayTemplateItem.is_deleted.is_(False),
        )
        return (await self.session.execute(stmt.limit(1))).scalar_one_or_none()

    async def list_for_template(self, template_id: int) -> list[HolidayTemplateItem]:
        """Return all non-deleted holidays in a template, ordered by start date."""
        stmt = (
            select(HolidayTemplateItem)
            .where(
                HolidayTemplateItem.template_id == template_id,
                HolidayTemplateItem.is_deleted.is_(False),
            )
            .order_by(HolidayTemplateItem.start_date.asc())
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def bulk_create(
        self, template_id: int, items_data: list[dict[str, Any]]
    ) -> list[HolidayTemplateItem]:
        """Insert multiple holiday items for a template in a single flush.

        All items participate in the caller's transaction — nothing is committed here.
        """
        instances: list[HolidayTemplateItem] = []
        for data in items_data:
            instance = HolidayTemplateItem(**{**data, "template_id": template_id})
            self.session.add(instance)
            instances.append(instance)
        # Flush once for the whole batch
        await self.session.flush()
        for inst in instances:
            await self.session.refresh(inst)
        return instances

    async def soft_delete(self, instance: HolidayTemplateItem) -> HolidayTemplateItem:
        """Soft-delete a holiday item."""
        return await self.update(instance, {"is_deleted": True})

    async def get_employee_holidays(
        self,
        employee_id: int,
        *,
        year: int | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> list[HolidayTemplateItem]:
        """Return holidays for an employee's assigned template within a date range."""
        assignment_stmt = select(EmployeeHolidayAssignment.template_id).where(
            EmployeeHolidayAssignment.employee_id == employee_id
        )
        template_id = (await self.session.execute(assignment_stmt.limit(1))).scalar()
        if not template_id:
            return []

        stmt = select(HolidayTemplateItem).where(
            HolidayTemplateItem.template_id == template_id,
            HolidayTemplateItem.is_deleted.is_(False),
        )

        if year is not None:
            stmt = stmt.where(
                HolidayTemplateItem.start_date >= date(year, 1, 1),
                HolidayTemplateItem.start_date <= date(year, 12, 31),
            )
        else:
            if date_from is not None:
                stmt = stmt.where(HolidayTemplateItem.end_date >= date_from)
            if date_to is not None:
                stmt = stmt.where(HolidayTemplateItem.start_date <= date_to)

        stmt = stmt.order_by(HolidayTemplateItem.start_date.asc())
        return list((await self.session.execute(stmt)).scalars().all())
