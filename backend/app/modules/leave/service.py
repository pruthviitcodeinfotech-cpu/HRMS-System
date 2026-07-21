"""Leave & Holiday Management — service layer (business logic & orchestration).

Implements the business logic of the Leave Management API Contract.
All database access is performed strictly via repositories.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants.enums import SortOrder
from app.core.exceptions.base import ValidationException
from app.modules.audit.constants import ActionType
from app.modules.audit.service import AuditService
from app.modules.employee.constants import EmploymentStatus
from app.modules.employee.models.employee import Employee
from app.modules.leave.constants import (
    AdjustmentType,
    AllocationFrequency,
    AllocationSource,
    LeaveRequestStatus,
)
from app.modules.leave.exceptions import (
    EmployeeNotFoundException,
    HolidayItemNotFoundException,
    HolidayTemplateNameExistsException,
    HolidayTemplateNotFoundException,
    InsufficientBalanceException,
    LeaveNotCancellableException,
    LeaveNotEditableException,
    LeaveOverlapException,
    LeaveRequestNotFoundException,
    LeaveTypeAliasExistsException,
    LeaveTypeInUseException,
    LeaveTypeNotFoundException,
)
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
from app.modules.leave.repository import (
    EmployeeHolidayAssignmentRepository,
    EmployeeLeaveAllocationRepository,
    EmployeeLeaveBalanceRepository,
    HolidayTemplateItemRepository,
    HolidayTemplateRepository,
    LeaveBalanceAdjustmentRepository,
    LeaveRequestRepository,
    LeaveSettingRepository,
    LeaveTypeRepository,
)
from app.shared.base.service import BaseService
from app.shared.schemas.pagination import PaginatedResponse
from app.shared.utils.datetime import utcnow

#: Upper bound on the leave types the accrual run reads in one page. An org configures a
#: handful (CL/SL/PL/…); this is a guard rail, not a real limit.
_MAX_LEAVE_TYPES_PER_ORG = 500

#: ``performed_by_name`` recorded for machine-driven writes (the nightly accrual job),
#: which have no human actor.
_SYSTEM_ACTOR = "System (auto-allocation)"


class LeaveService(BaseService):
    """Leave & Holiday Management business rules engine and service."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)
        # Main module repositories
        self.leave_types = LeaveTypeRepository(session)
        self.settings = LeaveSettingRepository(session)
        self.balances = EmployeeLeaveBalanceRepository(session)
        self.adjustments = LeaveBalanceAdjustmentRepository(session)
        self.allocations = EmployeeLeaveAllocationRepository(session)
        self.requests = LeaveRequestRepository(session)
        self.templates = HolidayTemplateRepository(session)
        self.assignments = EmployeeHolidayAssignmentRepository(session)
        self.items = HolidayTemplateItemRepository(session)

        # Audit logger
        self.audit = AuditService(session)

    # =========================================================================
    # Helpers & Validations
    # =========================================================================

    async def _validate_employee(self, org_id: int, employee_id: int) -> Employee:
        """Validate employee existence and active status in organization context."""
        stmt = select(Employee).where(
            Employee.employee_id == employee_id,
            Employee.org_id == org_id,
            Employee.is_deleted.is_(False),
        )
        emp = (await self.session.execute(stmt.limit(1))).scalar_one_or_none()
        if emp is None:
            raise EmployeeNotFoundException()
        return emp

    async def _validate_employee_simple(self, employee_id: int) -> Employee:
        """Simple check if employee exists, regardless of org scoping."""
        stmt = select(Employee).where(
            Employee.employee_id == employee_id,
            Employee.is_deleted.is_(False),
        )
        emp = (await self.session.execute(stmt.limit(1))).scalar_one_or_none()
        if emp is None:
            raise EmployeeNotFoundException()
        return emp

    def get_cycle_year(self, start_date: date, leave_cycle: str, start_month: int) -> int:
        """Compute target cycle year for a date based on cycle configurations."""
        if leave_cycle == "financial_year":
            if start_date.month >= start_month:
                return start_date.year
            else:
                return start_date.year - 1
        return start_date.year

    # =========================================================================
    # Leave Type Endpoints
    # =========================================================================

    async def create_leave_type(self, org_id: int, data: dict[str, Any], user_id: int) -> LeaveType:
        """Create a new leave type."""
        alias = data.get("alias")
        if alias and await self.leave_types.alias_exists(org_id, alias):
            raise LeaveTypeAliasExistsException()

        async with self.transaction():
            leave_type = await self.leave_types.create({**data, "org_id": org_id, "created_by": user_id})
            await self.audit.record(
                org_id=org_id,
                module="leave",
                sub_module="leave_type",
                action_type=ActionType.INSERT,
                title="Create Leave Type",
                description=f"Created leave type '{leave_type.name}' ({leave_type.alias})",
                performed_by_user_id=user_id,
                performed_by_name=f"User {user_id}",
            )
            return leave_type

    async def get_leave_type(self, org_id: int, leave_type_id: int) -> LeaveType:
        """Retrieve a leave type by ID in organization context."""
        leave_type = await self.leave_types.get_by_id_in_org(org_id, leave_type_id)
        if not leave_type:
            raise LeaveTypeNotFoundException()
        return leave_type

    async def list_leave_types(
        self,
        org_id: int,
        *,
        search: str | None = None,
        is_active: bool | None = None,
        sort_by: str | None = "name",
        sort_order: SortOrder | str = SortOrder.ASC,
        page: int = 1,
        page_size: int = 25,
    ) -> PaginatedResponse[LeaveType]:
        """Search and paginate leave types."""
        items = await self.leave_types.search(
            org_id,
            search=search,
            is_active=is_active,
            sort_by=sort_by,
            sort_order=sort_order,
            page=page,
            page_size=page_size,
        )
        total = await self.leave_types.search_count(org_id, search=search, is_active=is_active)
        return self.paginate(items, page=page, page_size=page_size, total_records=total)

    async def update_leave_type(
        self, org_id: int, leave_type_id: int, data: dict[str, Any], user_id: int
    ) -> LeaveType:
        """Update a leave type."""
        leave_type = await self.get_leave_type(org_id, leave_type_id)
        alias = data.get("alias")
        if alias and alias != leave_type.alias:
            if await self.leave_types.alias_exists(org_id, alias, exclude_id=leave_type_id):
                raise LeaveTypeAliasExistsException()

        # Handle encashment rules logic
        encashment_enabled = data.get("encashment_enabled", leave_type.encashment_enabled)
        encashment_limit = data.get("encashment_limit", leave_type.encashment_limit)
        if encashment_enabled and encashment_limit is None:
            raise ValidationException(
                "encashment_limit is required when encashment is enabled.",
                code="ENCASHMENT_LIMIT_REQUIRED",
            )

        async with self.transaction():
            updated = await self.leave_types.update(leave_type, {**data, "updated_by": user_id})
            await self.audit.record(
                org_id=org_id,
                module="leave",
                sub_module="leave_type",
                action_type=ActionType.UPDATE,
                title="Update Leave Type",
                description=f"Updated leave type '{updated.name}' ({updated.alias})",
                performed_by_user_id=user_id,
                performed_by_name=f"User {user_id}",
            )
            return updated

    async def delete_leave_type(self, org_id: int, leave_type_id: int, user_id: int) -> None:
        """Soft-delete a leave type if not referenced."""
        leave_type = await self.get_leave_type(org_id, leave_type_id)
        if await self.leave_types.has_references(leave_type_id):
            raise LeaveTypeInUseException()

        async with self.transaction():
            await self.leave_types.soft_delete(leave_type)
            await self.audit.record(
                org_id=org_id,
                module="leave",
                sub_module="leave_type",
                action_type=ActionType.DELETE,
                title="Delete Leave Type",
                description=f"Deleted leave type '{leave_type.name}' ({leave_type.alias})",
                performed_by_user_id=user_id,
                performed_by_name=f"User {user_id}",
            )

    # =========================================================================
    # Leave Settings Endpoints
    # =========================================================================

    async def get_leave_settings(self, org_id: int) -> LeaveSetting:
        """Get or initialize the organization cycle configurations."""
        existing = await self.settings.get_by_org_id(org_id)
        if not existing:
            # Initialize with default cycle
            async with self.transaction():
                return await self.settings.create(
                    {"org_id": org_id, "leave_cycle": "calendar_year", "cycle_start_month": 1}
                )
        return existing

    async def update_leave_settings(self, org_id: int, data: dict[str, Any], user_id: int) -> LeaveSetting:
        """Upsert organization leave cycle settings."""
        async with self.transaction():
            updated = await self.settings.upsert(org_id, {**data, "updated_by": user_id})
            await self.audit.record(
                org_id=org_id,
                module="leave",
                sub_module="leave_settings",
                action_type=ActionType.UPDATE,
                title="Update Leave Settings",
                description=f"Updated leave cycle configuration to {updated.leave_cycle} starting month {updated.cycle_start_month}",
                performed_by_user_id=user_id,
                performed_by_name=f"User {user_id}",
            )
            return updated

    # =========================================================================
    # Leave Balances & Adjustments Endpoints
    # =========================================================================

    async def get_employee_leave_balances(
        self, org_id: int, employee_id: int, cycle_year: int, *, leave_type_id: int | None = None
    ) -> list[EmployeeLeaveBalance]:
        """List leave balances for an employee in org context."""
        await self._validate_employee(org_id, employee_id)
        return await self.balances.list_by_employee(employee_id, cycle_year, leave_type_id=leave_type_id)

    async def list_leave_balances(
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
    ) -> PaginatedResponse[EmployeeLeaveBalance]:
        """Search and paginate leave balances for organization."""
        items = await self.balances.search(
            org_id,
            leave_type_id=leave_type_id,
            cycle_year=cycle_year,
            employee_id=employee_id,
            branch_id=branch_id,
            dept_id=dept_id,
            page=page,
            page_size=page_size,
        )
        total = await self.balances.search_count(
            org_id,
            leave_type_id=leave_type_id,
            cycle_year=cycle_year,
            employee_id=employee_id,
            branch_id=branch_id,
            dept_id=dept_id,
        )
        return self.paginate(items, page=page, page_size=page_size, total_records=total)

    async def credit_leave_balance(
        self, org_id: int, employee_id: int, data: dict[str, Any], adjusted_by: int
    ) -> EmployeeLeaveBalance:
        """Credit leave balance manually."""
        emp = await self._validate_employee(org_id, employee_id)
        leave_type_id = data["leave_type_id"]
        cycle_year = data["cycle_year"]
        days = data["days"]
        adjustment_type = data.get("adjustment_type", AdjustmentType.MANUAL)
        remarks = data.get("remarks")

        await self.get_leave_type(org_id, leave_type_id)

        async with self.transaction():
            balance = await self.balances.get_by_employee_type_year(employee_id, leave_type_id, cycle_year)
            if not balance:
                balance = await self.balances.create(
                    {
                        "employee_id": employee_id,
                        "leave_type_id": leave_type_id,
                        "cycle_year": cycle_year,
                        "opening_balance": 0.00,
                        "allocated": 0.00,
                        "used": 0.00,
                        "carried_forward": 0.00,
                        "encashed": 0.00,
                        "adjusted": 0.00,
                        "closing_balance": 0.00,
                        "updated_by": adjusted_by,
                    }
                )

            new_adjusted = balance.adjusted + days
            new_closing = balance.closing_balance + days

            await self.balances.update(
                balance,
                {
                    "adjusted": new_adjusted,
                    "closing_balance": new_closing,
                    "updated_by": adjusted_by,
                },
            )

            # Record history
            await self.adjustments.create(
                {
                    "employee_id": employee_id,
                    "leave_type_id": leave_type_id,
                    "adjustment_type": adjustment_type,
                    "delta": days,
                    "new_balance": new_closing,
                    "remarks": remarks,
                    "cycle_year": cycle_year,
                    "adjusted_by": adjusted_by,
                }
            )

            await self.audit.record(
                org_id=org_id,
                module="leave",
                sub_module="leave_balance",
                action_type=ActionType.UPDATE,
                title="Credit Leave Balance",
                description=f"Credited {days} days to employee {employee_id} leave type {leave_type_id}",
                performed_by_user_id=adjusted_by,
                performed_by_name=f"User {adjusted_by}",
                employee_id=employee_id,
                employee_name=emp.employee_name,
            )

        # Re-read through the eager-loading accessor: a freshly created row has its
        # ``leave_type`` relationship unloaded, and serialising the response would
        # trigger a lazy load outside the async greenlet context (MissingGreenlet).
        return await self.balances.get_by_employee_type_year(
            employee_id, leave_type_id, cycle_year
        )

    async def debit_leave_balance(
        self, org_id: int, employee_id: int, data: dict[str, Any], adjusted_by: int
    ) -> EmployeeLeaveBalance:
        """Debit leave balance manually."""
        emp = await self._validate_employee(org_id, employee_id)
        leave_type_id = data["leave_type_id"]
        cycle_year = data["cycle_year"]
        days = data["days"]
        adjustment_type = data.get("adjustment_type", AdjustmentType.MANUAL)
        remarks = data.get("remarks")

        await self.get_leave_type(org_id, leave_type_id)

        async with self.transaction():
            balance = await self.balances.get_by_employee_type_year(employee_id, leave_type_id, cycle_year)
            if not balance or balance.closing_balance < days:
                raise InsufficientBalanceException()

            new_adjusted = balance.adjusted - days
            new_closing = balance.closing_balance - days

            await self.balances.update(
                balance,
                {
                    "adjusted": new_adjusted,
                    "closing_balance": new_closing,
                    "updated_by": adjusted_by,
                },
            )

            # Record history
            await self.adjustments.create(
                {
                    "employee_id": employee_id,
                    "leave_type_id": leave_type_id,
                    "adjustment_type": adjustment_type,
                    "delta": -days,
                    "new_balance": new_closing,
                    "remarks": remarks,
                    "cycle_year": cycle_year,
                    "adjusted_by": adjusted_by,
                }
            )

            await self.audit.record(
                org_id=org_id,
                module="leave",
                sub_module="leave_balance",
                action_type=ActionType.UPDATE,
                title="Debit Leave Balance",
                description=f"Debited {days} days from employee {employee_id} leave type {leave_type_id}",
                performed_by_user_id=adjusted_by,
                performed_by_name=f"User {adjusted_by}",
                employee_id=employee_id,
                employee_name=emp.employee_name,
            )

        # Re-read through the eager-loading accessor: a freshly created row has its
        # ``leave_type`` relationship unloaded, and serialising the response would
        # trigger a lazy load outside the async greenlet context (MissingGreenlet).
        return await self.balances.get_by_employee_type_year(
            employee_id, leave_type_id, cycle_year
        )

    async def adjust_leave_balance(
        self, org_id: int, employee_id: int, data: dict[str, Any], adjusted_by: int
    ) -> EmployeeLeaveBalance:
        """Adjust leave balance manually to a set value."""
        emp = await self._validate_employee(org_id, employee_id)
        leave_type_id = data["leave_type_id"]
        cycle_year = data["cycle_year"]
        new_balance = data["new_balance"]
        adjustment_type = data.get("adjustment_type", AdjustmentType.MANUAL)
        remarks = data.get("remarks")

        await self.get_leave_type(org_id, leave_type_id)

        async with self.transaction():
            balance = await self.balances.get_by_employee_type_year(employee_id, leave_type_id, cycle_year)
            if not balance:
                balance = await self.balances.create(
                    {
                        "employee_id": employee_id,
                        "leave_type_id": leave_type_id,
                        "cycle_year": cycle_year,
                        "opening_balance": 0.00,
                        "allocated": 0.00,
                        "used": 0.00,
                        "carried_forward": 0.00,
                        "encashed": 0.00,
                        "adjusted": 0.00,
                        "closing_balance": 0.00,
                        "updated_by": adjusted_by,
                    }
                )

            delta = new_balance - balance.closing_balance

            await self.balances.update(
                balance,
                {
                    "adjusted": balance.adjusted + delta,
                    "closing_balance": new_balance,
                    "updated_by": adjusted_by,
                },
            )

            # Record history
            await self.adjustments.create(
                {
                    "employee_id": employee_id,
                    "leave_type_id": leave_type_id,
                    "adjustment_type": adjustment_type,
                    "delta": delta,
                    "new_balance": new_balance,
                    "remarks": remarks,
                    "cycle_year": cycle_year,
                    "adjusted_by": adjusted_by,
                }
            )

            await self.audit.record(
                org_id=org_id,
                module="leave",
                sub_module="leave_balance",
                action_type=ActionType.UPDATE,
                title="Adjust Leave Balance",
                description=f"Adjusted employee {employee_id} leave type {leave_type_id} balance to {new_balance} (delta {delta})",
                performed_by_user_id=adjusted_by,
                performed_by_name=f"User {adjusted_by}",
                employee_id=employee_id,
                employee_name=emp.employee_name,
            )

        # Re-read through the eager-loading accessor: a freshly created row has its
        # ``leave_type`` relationship unloaded, and serialising the response would
        # trigger a lazy load outside the async greenlet context (MissingGreenlet).
        return await self.balances.get_by_employee_type_year(
            employee_id, leave_type_id, cycle_year
        )

    async def get_leave_balance_history(
        self, org_id: int, employee_id: int, cycle_year: int, *, leave_type_id: int | None = None
    ) -> list[LeaveBalanceAdjustment]:
        """List leave balance adjustments history in org context."""
        await self._validate_employee(org_id, employee_id)
        return await self.adjustments.list_history(employee_id, cycle_year, leave_type_id=leave_type_id)

    async def list_leave_allocations(
        self, org_id: int, employee_id: int, *, cycle_year: int | None = None
    ) -> list[EmployeeLeaveAllocation]:
        """List leave allocation history in org context."""
        await self._validate_employee(org_id, employee_id)
        return await self.allocations.list_allocations(employee_id, cycle_year=cycle_year)

    # =========================================================================
    # Auto-allocation (accrual)
    #
    # Driven by the nightly ``run_leave_accrual`` job (:mod:`app.jobs.tasks`); the API
    # exposes allocations read-only. The business rules live here, in the service, so
    # the job stays a thin wrapper around a session.
    #
    # This is NOT ``credit_leave_balance``: that method is the *manual adjustment* path
    # (it moves ``adjusted`` and writes a ``leave_balance_adjustments`` history row). An
    # accrual is an *allocation* — it moves ``allocated`` and writes an
    # ``employee_leave_allocations`` event, which is what ``list_leave_allocations``
    # reads back. Routing accruals through the manual-credit path would mislabel every
    # nightly grant as a hand-made adjustment.
    # =========================================================================

    def _cycle_period(self, target: date, allocation_frequency: str) -> str | None:
        """Return the allocation period key for ``target`` (``None`` for yearly types).

        Monthly leave types accrue once per calendar month, so the month is part of the
        idempotency key (``2026-07``). Yearly types accrue once per cycle year, so they
        have no period.
        """
        if allocation_frequency == AllocationFrequency.MONTHLY.value:
            return f"{target.year:04d}-{target.month:02d}"
        return None

    async def _list_active_employee_ids(self, org_id: int) -> list[int]:
        """Return the ids of the org's active, non-deleted employees."""
        stmt = (
            select(Employee.employee_id)
            .where(
                Employee.org_id == org_id,
                Employee.is_deleted.is_(False),
                Employee.employment_status == EmploymentStatus.ACTIVE.value,
            )
            .order_by(Employee.employee_id)
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def allocate_leave(
        self,
        org_id: int,
        employee_id: int,
        leave_type: LeaveType,
        *,
        cycle_year: int,
        allocation_date: date,
        allocated_by: int | None = None,
    ) -> EmployeeLeaveAllocation | None:
        """Credit one employee's auto-allocation for one leave type, exactly once.

        Idempotent by construction: an allocation event already recorded for this
        ``employee + leave_type + cycle_year (+ cycle_period)`` short-circuits and
        returns ``None``. Both the balance mutation and the allocation event are written
        in a single transaction, so a crash mid-way cannot leave a credited balance with
        no allocation row (which would let the next run credit it again).
        """
        days = leave_type.auto_allocation_count
        if days is None or days <= 0:
            return None

        period = self._cycle_period(allocation_date, leave_type.allocation_frequency)
        existing = await self.allocations.get_for_cycle(
            employee_id, leave_type.id, cycle_year, cycle_period=period
        )
        if existing is not None:
            return None

        async with self.transaction():
            balance = await self.balances.get_by_employee_type_year(
                employee_id, leave_type.id, cycle_year
            )
            if not balance:
                balance = await self.balances.create(
                    {
                        "employee_id": employee_id,
                        "leave_type_id": leave_type.id,
                        "cycle_year": cycle_year,
                        "opening_balance": 0.00,
                        "allocated": 0.00,
                        "used": 0.00,
                        "carried_forward": 0.00,
                        "encashed": 0.00,
                        "adjusted": 0.00,
                        "closing_balance": 0.00,
                        "updated_by": allocated_by,
                    }
                )

            await self.balances.update(
                balance,
                {
                    "allocated": balance.allocated + days,
                    "closing_balance": balance.closing_balance + days,
                    "updated_by": allocated_by,
                },
            )

            allocation = await self.allocations.create(
                {
                    "employee_id": employee_id,
                    "leave_type_id": leave_type.id,
                    "cycle_year": cycle_year,
                    "cycle_period": period,
                    "allocated_days": days,
                    "allocation_date": allocation_date,
                    "allocation_source": AllocationSource.AUTO.value,
                    "created_by": allocated_by,
                }
            )

            await self.audit.record(
                org_id=org_id,
                module="leave",
                sub_module="leave_allocation",
                action_type=ActionType.INSERT,
                title="Auto-allocate Leave",
                description=(
                    f"Allocated {days} days of leave type {leave_type.id} to employee "
                    f"{employee_id} for cycle {cycle_year}"
                    + (f" ({period})" if period else "")
                ),
                performed_by_user_id=allocated_by,
                # No actor: the accrual is machine-driven. ``action_from`` keeps its
                # default — the DB CHECK on activity_logs admits only 'Web App' /
                # 'Mobile App', so there is no 'System' value to record here.
                performed_by_name=_SYSTEM_ACTOR,
                employee_id=employee_id,
            )
            return allocation

    async def run_auto_allocation(
        self,
        org_id: int,
        *,
        as_of: date | None = None,
        allocated_by: int | None = None,
    ) -> dict[str, int]:
        """Credit every active employee's auto-allocation for the current leave cycle.

        Walks the org's active leave types and active employees, allocating the ones not
        yet allocated for the cycle. Safe to run repeatedly (see :meth:`allocate_leave`):
        a second run on the same day allocates nothing.

        Returns a ``{"employees", "leave_types", "allocated", "skipped"}`` tally.
        """
        target = as_of or utcnow().date()
        config = await self.get_leave_settings(org_id)
        cycle_year = self.get_cycle_year(target, config.leave_cycle, config.cycle_start_month)

        leave_types = await self.leave_types.search(
            org_id, is_active=True, page=1, page_size=_MAX_LEAVE_TYPES_PER_ORG
        )
        accruing = [
            lt for lt in leave_types if lt.auto_allocation_count and lt.auto_allocation_count > 0
        ]
        employee_ids = await self._list_active_employee_ids(org_id)

        allocated = 0
        skipped = 0
        for employee_id in employee_ids:
            for leave_type in accruing:
                result = await self.allocate_leave(
                    org_id,
                    employee_id,
                    leave_type,
                    cycle_year=cycle_year,
                    allocation_date=target,
                    allocated_by=allocated_by,
                )
                if result is None:
                    skipped += 1
                else:
                    allocated += 1

        return {
            "org_id": org_id,
            "cycle_year": cycle_year,
            "employees": len(employee_ids),
            "leave_types": len(accruing),
            "allocated": allocated,
            "skipped": skipped,
        }

    # =========================================================================
    # Leave Request Endpoints
    # =========================================================================

    async def apply_leave(self, org_id: int, data: dict[str, Any], applied_by: int) -> LeaveRequest:
        """Submit a new leave request (creates pending entry)."""
        employee_id = data.get("employee_id")
        if not employee_id:
            # The router resolves the caller's own employee for self-service applications.
            # Reaching here means the caller's user has no linked employee record; surface
            # that as a 422 rather than letting a bare ValueError become a 500.
            raise ValidationException(
                "employee_id is required and could not be resolved from the caller.",
                code="EMPLOYEE_ID_REQUIRED",
            )

        emp = await self._validate_employee(org_id, employee_id)
        leave_type_id = data["leave_type_id"]
        start_date = data["start_date"]
        end_date = data["end_date"]
        duration_days = data["duration_days"]

        # 1. Validate leave type is active in organization
        leave_type = await self.get_leave_type(org_id, leave_type_id)
        if not leave_type.is_active:
            raise LeaveTypeNotFoundException()

        # 2. Check conflicts (overlapping requests)
        if await self.requests.has_overlap(employee_id, start_date, end_date):
            raise LeaveOverlapException()

        # 3. Check sufficient leave balance eligibility
        settings = await self.get_leave_settings(org_id)
        cycle_year = self.get_cycle_year(start_date, settings.leave_cycle, settings.cycle_start_month)

        balance = await self.balances.get_by_employee_type_year(employee_id, leave_type_id, cycle_year)
        available = balance.closing_balance if balance else 0.00
        if available < duration_days:
            raise InsufficientBalanceException()

        # Local imports avoid a circular import (approvals.service depends on the
        # leave repositories/constants). Matches the cross-module orchestration
        # pattern already used by ApprovalService.
        from app.modules.approvals.constants import RequestType
        from app.modules.approvals.service import ApprovalService

        async with self.transaction():
            request = await self.requests.create(
                {
                    "employee_id": employee_id,
                    "leave_type_id": leave_type_id,
                    "start_date": start_date,
                    "end_date": end_date,
                    "duration_days": duration_days,
                    "reason": data.get("reason"),
                    "status": LeaveRequestStatus.PENDING,
                }
            )

            await self.audit.record(
                org_id=org_id,
                module="leave",
                sub_module="leave_request",
                action_type=ActionType.INSERT,
                title="Apply Leave",
                description=f"Employee {employee_id} applied leave for {duration_days} days starting {start_date}",
                performed_by_user_id=applied_by,
                performed_by_name=f"User {applied_by}",
                employee_id=employee_id,
                employee_name=emp.employee_name,
            )

            # Initiate the approval workflow in the SAME transaction: create the
            # polymorphic ApprovalRequest envelope (request_type='leave',
            # reference_id=<leave request id>) so a reviewer can act on it. Without
            # this the request would remain permanently pending. Delegated to
            # ApprovalService so envelope creation logic is not duplicated.
            approval_service = ApprovalService(self.session)
            await approval_service.submit_approval_request(
                org_id=org_id,
                request_type=RequestType.LEAVE,
                reference_id=request.id,
                employee_id=employee_id,
                created_by=applied_by,
            )

        # Re-read through the eager-loading accessor: the freshly created row has its
        # ``leave_type`` relationship unloaded, and serialising the response would
        # trigger a lazy load outside the async greenlet context (MissingGreenlet).
        return await self.requests.get_by_id_in_org(org_id, request.id)

    async def get_leave_request(self, org_id: int, request_id: int) -> LeaveRequest:
        """Get leave request details."""
        request = await self.requests.get_by_id_in_org(org_id, request_id)
        if not request:
            raise LeaveRequestNotFoundException()
        return request

    async def update_leave_request(
        self, org_id: int, request_id: int, data: dict[str, Any], updated_by: int
    ) -> LeaveRequest:
        """Update a pending leave request details."""
        request = await self.get_leave_request(org_id, request_id)
        if request.status != LeaveRequestStatus.PENDING:
            raise LeaveNotEditableException()

        employee_id = request.employee_id
        leave_type_id = data.get("leave_type_id", request.leave_type_id)
        start_date = data.get("start_date", request.start_date)
        end_date = data.get("end_date", request.end_date)
        duration_days = data.get("duration_days", request.duration_days)

        # 1. Validate type is active in organization
        leave_type = await self.get_leave_type(org_id, leave_type_id)
        if not leave_type.is_active:
            raise LeaveTypeNotFoundException()

        # 2. Check overlap conflicts excluding this request
        if await self.requests.has_overlap(employee_id, start_date, end_date, exclude_request_id=request_id):
            raise LeaveOverlapException()

        # 3. Check balance
        settings = await self.get_leave_settings(org_id)
        cycle_year = self.get_cycle_year(start_date, settings.leave_cycle, settings.cycle_start_month)

        balance = await self.balances.get_by_employee_type_year(employee_id, leave_type_id, cycle_year)
        available = balance.closing_balance if balance else 0.00
        if available < duration_days:
            raise InsufficientBalanceException()

        async with self.transaction():
            updated = await self.requests.update(request, {**data, "updated_at": date.today()})
            await self.audit.record(
                org_id=org_id,
                module="leave",
                sub_module="leave_request",
                action_type=ActionType.UPDATE,
                title="Update Leave Request",
                description=f"Updated pending leave request {request_id} for employee {employee_id}",
                performed_by_user_id=updated_by,
                performed_by_name=f"User {updated_by}",
                employee_id=employee_id,
            )
            return updated

    async def cancel_leave_request(self, org_id: int, request_id: int, user_id: int) -> None:
        """Cancel a pending leave request (hard-delete)."""
        request = await self.get_leave_request(org_id, request_id)
        if request.status != LeaveRequestStatus.PENDING:
            raise LeaveNotCancellableException()

        async with self.transaction():
            await self.requests.delete(request)
            await self.audit.record(
                org_id=org_id,
                module="leave",
                sub_module="leave_request",
                action_type=ActionType.DELETE,
                title="Cancel Leave Request",
                description=f"Cancelled pending leave request {request_id} for employee {request.employee_id}",
                performed_by_user_id=user_id,
                performed_by_name=f"User {user_id}",
                employee_id=request.employee_id,
            )

    async def list_leave_requests(
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
    ) -> PaginatedResponse[LeaveRequest]:
        """Search and paginate leave requests for organization."""
        items = await self.requests.search(
            org_id,
            employee_id=employee_id,
            leave_type_id=leave_type_id,
            status=status,
            date_from=date_from,
            date_to=date_to,
            branch_id=branch_id,
            dept_id=dept_id,
            sort_by=sort_by,
            sort_order=sort_order,
            page=page,
            page_size=page_size,
        )
        total = await self.requests.search_count(
            org_id,
            employee_id=employee_id,
            leave_type_id=leave_type_id,
            status=status,
            date_from=date_from,
            date_to=date_to,
            branch_id=branch_id,
            dept_id=dept_id,
        )
        return self.paginate(items, page=page, page_size=page_size, total_records=total)

    # =========================================================================
    # Holiday Group / Template Endpoints
    # =========================================================================

    async def create_holiday_group(
        self, org_id: int, data: dict[str, Any], created_by: int
    ) -> HolidayTemplate:
        """Atomically create a holiday group template together with its items.

        Everything (template row, all item rows, holiday_count update, audit log)
        executes inside ONE database transaction.  If any step fails, the entire
        transaction is rolled back — no orphan template, no partial items.

        ``data`` must contain:
          - ``name``  (str)        — template name, unique (case-insensitive) per org.
          - ``items`` (list[dict]) — zero or more holiday item payloads.
        """
        name: str = data["name"]
        items_data: list[dict[str, Any]] = data.get("items", [])

        # Pre-transaction read-only uniqueness check
        if await self.templates.name_exists(org_id, name):
            raise HolidayTemplateNameExistsException()

        async with self.transaction():
            # 1. Create template row (flushed, not yet committed)
            template = await self.templates.create(
                {"org_id": org_id, "name": name, "holiday_count": 0, "created_by": created_by}
            )

            # 2. Bulk-insert all holiday items in one flush (same transaction)
            if items_data:
                await self.items.bulk_create(
                    template.id,
                    [
                        {
                            "name": item["name"],
                            "start_date": item["start_date"],
                            "end_date": item["end_date"],
                            "day_of_week": item.get("day_of_week"),
                            "duration_days": item.get("duration_days", 1),
                            "created_by": created_by,
                        }
                        for item in items_data
                    ],
                )
                # 3. Update holiday_count to match items inserted
                await self.templates.update(template, {"holiday_count": len(items_data)})

            # 4. Audit log (flushed in the same transaction)
            await self.audit.record(
                org_id=org_id,
                module="leave",
                sub_module="holiday",
                action_type=ActionType.INSERT,
                title="Create Holiday Group",
                description=(
                    f"Created holiday group template '{name}' "
                    f"with {len(items_data)} holiday item(s)"
                ),
                performed_by_user_id=created_by,
                performed_by_name=f"User {created_by}",
            )
        return await self.get_holiday_group(org_id, template.id)


    async def list_holiday_groups(
        self, org_id: int, *, page: int = 1, page_size: int = 25
    ) -> PaginatedResponse[HolidayTemplate]:
        """List and paginate holiday group templates."""
        items = await self.templates.search(org_id, page=page, page_size=page_size)
        total = await self.templates.search_count(org_id)
        return self.paginate(items, page=page, page_size=page_size, total_records=total)

    async def get_holiday_group(self, org_id: int, template_id: int) -> HolidayTemplate:
        """Get holiday group template details with its items."""
        template = await self.templates.get_by_id_in_org(org_id, template_id)
        if not template:
            raise HolidayTemplateNotFoundException()
        return template

    async def update_holiday_group(
        self, org_id: int, template_id: int, data: dict[str, Any], updated_by: int
    ) -> HolidayTemplate:
        """Update a holiday group template name."""
        template = await self.get_holiday_group(org_id, template_id)
        name = data["name"]
        if name != template.name and await self.templates.name_exists(org_id, name, exclude_id=template_id):
            raise HolidayTemplateNameExistsException()

        async with self.transaction():
            await self.templates.update(template, {"name": name, "updated_by": updated_by})
            await self.audit.record(
                org_id=org_id,
                module="leave",
                sub_module="holiday",
                action_type=ActionType.UPDATE,
                title="Update Holiday Group",
                description=f"Updated holiday group template name to '{name}'",
                performed_by_user_id=updated_by,
                performed_by_name=f"User {updated_by}",
            )
        return await self.get_holiday_group(org_id, template_id)

    async def delete_holiday_group(self, org_id: int, template_id: int, user_id: int) -> None:
        """Soft-delete a holiday template group."""
        template = await self.get_holiday_group(org_id, template_id)

        async with self.transaction():
            await self.templates.soft_delete(template)
            await self.audit.record(
                org_id=org_id,
                module="leave",
                sub_module="holiday",
                action_type=ActionType.DELETE,
                title="Delete Holiday Group",
                description=f"Soft-deleted holiday group template '{template.name}'",
                performed_by_user_id=user_id,
                performed_by_name=f"User {user_id}",
            )

    async def assign_holiday_group(
        self, org_id: int, employee_id: int, template_id: int, assigned_by: int
    ) -> EmployeeHolidayAssignment:
        """Assign holiday group template mapping to employee."""
        emp = await self._validate_employee(org_id, employee_id)
        await self.get_holiday_group(org_id, template_id)

        async with self.transaction():
            assignment = await self.assignments.upsert_assignment(employee_id, template_id, assigned_by)
            await self.audit.record(
                org_id=org_id,
                module="leave",
                sub_module="holiday",
                action_type=ActionType.ASSIGN,
                title="Assign Holiday Group",
                description=f"Assigned holiday group {template_id} to employee {employee_id}",
                performed_by_user_id=assigned_by,
                performed_by_name=f"User {assigned_by}",
                employee_id=employee_id,
                employee_name=emp.employee_name,
            )
            return assignment

    async def list_holiday_assignments(self, org_id: int) -> list[EmployeeHolidayAssignment]:
        """List all employee holiday assignments for the organization."""
        return await self.assignments.list_all_assignments(org_id)

    async def get_holiday_assignment(self, org_id: int, employee_id: int) -> EmployeeHolidayAssignment | None:
        """Get holiday template mapping for an employee in org context."""
        await self._validate_employee(org_id, employee_id)
        return await self.assignments.get_by_employee_id(employee_id)

    # =========================================================================
    # Holiday Item Endpoints
    # =========================================================================

    async def create_holiday(
        self, org_id: int, template_id: int, data: dict[str, Any], created_by: int
    ) -> HolidayTemplateItem:
        """Create a holiday item inside a template."""
        template = await self.get_holiday_group(org_id, template_id)

        async with self.transaction():
            item = await self.items.create({**data, "template_id": template_id, "created_by": created_by})
            # Increment template count
            await self.templates.update(template, {"holiday_count": template.holiday_count + 1})

            await self.audit.record(
                org_id=org_id,
                module="leave",
                sub_module="holiday",
                action_type=ActionType.INSERT,
                title="Create Holiday",
                description=f"Created holiday '{item.name}' inside template {template_id}",
                performed_by_user_id=created_by,
                performed_by_name=f"User {created_by}",
            )
            return item

    async def update_holiday(
        self, org_id: int, template_id: int, item_id: int, data: dict[str, Any], user_id: int
    ) -> HolidayTemplateItem:
        """Update a holiday item details."""
        await self.get_holiday_group(org_id, template_id)
        item = await self.items.get_by_id_in_template(template_id, item_id)
        if not item:
            raise HolidayItemNotFoundException()

        async with self.transaction():
            updated = await self.items.update(item, data)
            await self.audit.record(
                org_id=org_id,
                module="leave",
                sub_module="holiday",
                action_type=ActionType.UPDATE,
                title="Update Holiday",
                description=f"Updated holiday details '{updated.name}' inside template {template_id}",
                performed_by_user_id=user_id,
                performed_by_name=f"User {user_id}",
            )
            return updated

    async def delete_holiday(self, org_id: int, template_id: int, item_id: int, user_id: int) -> None:
        """Soft-delete a holiday item from group template."""
        template = await self.get_holiday_group(org_id, template_id)
        item = await self.items.get_by_id_in_template(template_id, item_id)
        if not item:
            raise HolidayItemNotFoundException()

        async with self.transaction():
            await self.items.soft_delete(item)
            # Decrement count
            new_count = max(0, template.holiday_count - 1)
            await self.templates.update(template, {"holiday_count": new_count})

            await self.audit.record(
                org_id=org_id,
                module="leave",
                sub_module="holiday",
                action_type=ActionType.DELETE,
                title="Delete Holiday",
                description=f"Deleted holiday '{item.name}' inside template {template_id}",
                performed_by_user_id=user_id,
                performed_by_name=f"User {user_id}",
            )

    async def list_holidays(self, org_id: int, template_id: int) -> list[HolidayTemplateItem]:
        """List non-deleted holidays in template."""
        await self.get_holiday_group(org_id, template_id)
        return await self.items.list_for_template(template_id)

    async def get_employee_holiday_calendar(
        self,
        org_id: int,
        employee_id: int,
        *,
        year: int | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> list[HolidayTemplateItem]:
        """Retrieve holiday items in employee's calendar view."""
        await self._validate_employee(org_id, employee_id)
        return await self.items.get_employee_holidays(
            employee_id, year=year, date_from=date_from, date_to=date_to
        )
