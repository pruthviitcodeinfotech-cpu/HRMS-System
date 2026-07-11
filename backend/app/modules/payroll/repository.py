"""Payroll Management — data-access layer (async SQLAlchemy).

Provides repository classes for:
- PayrollSetting (organization configuration)
- PayrollGroup (Salary Structures)
- EmployeePayrollGroupAssignment (assignment logs)
- PayrollSalaryCycle (salary periods)
- PayrollColumnSetting (display layouts)
- FinalizedPayrollRun (payout finalizations)
- PayrollComputedRow (employee computed records)
- AttendanceAdjustment (status corrections)
- AttendanceAdjustmentPenalty (penalty overrides)
- AttendanceAdjustmentExtraHours (extra hours overrides)

Operates entirely on existing database models and inherits from BaseRepository.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date
from typing import Any

from sqlalchemy import and_, delete, desc, func, insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.employee.models.employee import Employee
from app.modules.payroll.constants import (
    AdjustmentSource,
    PaymentStatus,
)
from app.modules.payroll.models import (
    AttendanceAdjustment,
    AttendanceAdjustmentExtraHours,
    AttendanceAdjustmentPenalty,
    EmployeePayrollGroupAssignment,
    FinalizedPayrollRun,
    PayrollColumnSetting,
    PayrollComputedRow,
    PayrollGroup,
    PayrollSalaryCycle,
    PayrollSetting,
)
from app.shared.base.repository import BaseRepository
from app.shared.utils.query import apply_pagination

# ===========================================================================
# 1. Payroll Settings Repository
# ===========================================================================

class PayrollSettingRepository(BaseRepository[PayrollSetting]):
    """CRUD operations and helpers for PayrollSetting."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, PayrollSetting)

    async def get_by_org(self, org_id: int) -> PayrollSetting | None:
        """Retrieve the single settings row scoped to the organization ID."""
        stmt = select(PayrollSetting).where(PayrollSetting.org_id == org_id)
        return (await self.session.execute(stmt.limit(1))).scalar_one_or_none()


# ===========================================================================
# 2. Payroll Groups Repository
# ===========================================================================

class PayrollGroupRepository(BaseRepository[PayrollGroup]):
    """CRUD operations, exists checking, defaults and searching for PayrollGroup."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, PayrollGroup)

    async def get_by_id_in_org(self, org_id: int, group_id: int) -> PayrollGroup | None:
        """Retrieve a non-deleted group scoped to the organization ID."""
        stmt = select(PayrollGroup).where(
            PayrollGroup.id == group_id,
            PayrollGroup.org_id == org_id,
            PayrollGroup.is_deleted.is_(False),
        )
        return (await self.session.execute(stmt.limit(1))).scalar_one_or_none()

    async def name_exists(self, org_id: int, name: str, exclude_id: int | None = None) -> bool:
        """Check if an active group name already exists inside the organization."""
        stmt = select(PayrollGroup.id).where(
            PayrollGroup.org_id == org_id,
            PayrollGroup.name == name,
            PayrollGroup.is_deleted.is_(False),
        )
        if exclude_id is not None:
            stmt = stmt.where(PayrollGroup.id != exclude_id)
        return (await self.session.execute(stmt.limit(1))).first() is not None

    async def get_default_group(self, org_id: int) -> PayrollGroup | None:
        """Retrieve the default payroll group for the organization."""
        stmt = select(PayrollGroup).where(
            PayrollGroup.org_id == org_id,
            PayrollGroup.is_default.is_(True),
            PayrollGroup.is_deleted.is_(False),
        )
        return (await self.session.execute(stmt.limit(1))).scalar_one_or_none()

    async def clear_defaults_except(self, org_id: int, group_id: int) -> None:
        """Reset is_default to False for all groups in the org except the target one."""
        stmt = (
            update(PayrollGroup)
            .where(
                PayrollGroup.org_id == org_id,
                PayrollGroup.id != group_id,
                PayrollGroup.is_default.is_(True),
            )
            .values(is_default=False)
        )
        await self.session.execute(stmt)

    async def search(
        self, org_id: int, *, page: int = 1, page_size: int = 25
    ) -> list[PayrollGroup]:
        """Search and list active payroll groups in the organization."""
        stmt = select(PayrollGroup).where(
            PayrollGroup.org_id == org_id,
            PayrollGroup.is_deleted.is_(False),
        ).order_by(PayrollGroup.name)
        stmt = apply_pagination(stmt, page=page, page_size=page_size)
        return list((await self.session.execute(stmt)).scalars().all())

    async def search_count(self, org_id: int) -> int:
        """Count active payroll groups in the organization."""
        stmt = select(func.count()).select_from(PayrollGroup).where(
            PayrollGroup.org_id == org_id,
            PayrollGroup.is_deleted.is_(False),
        )
        return int((await self.session.execute(stmt)).scalar_one())


# ===========================================================================
# 3. Employee Group Assignment Repository
# ===========================================================================

class EmployeePayrollGroupAssignmentRepository(BaseRepository[EmployeePayrollGroupAssignment]):
    """CRUD operations and assignment looks for EmployeePayrollGroupAssignment."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, EmployeePayrollGroupAssignment)

    async def get_by_employee(self, employee_id: int) -> EmployeePayrollGroupAssignment | None:
        """Retrieve the active assignment record for the employee."""
        stmt = select(EmployeePayrollGroupAssignment).where(
            EmployeePayrollGroupAssignment.employee_id == employee_id
        )
        return (await self.session.execute(stmt.limit(1))).scalar_one_or_none()

    async def get_by_employees(
        self, employee_ids: Sequence[int]
    ) -> list[EmployeePayrollGroupAssignment]:
        """Bulk-retrieve assignment records for a set of employees in a single query.

        ``employee_id`` is unique on this table, so callers may safely key the result
        by employee id.
        """
        if not employee_ids:
            return []
        stmt = select(EmployeePayrollGroupAssignment).where(
            EmployeePayrollGroupAssignment.employee_id.in_(employee_ids)
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def get_assignments_by_group(self, group_id: int) -> list[EmployeePayrollGroupAssignment]:
        """Retrieve assignments currently associated with the payroll group."""
        stmt = select(EmployeePayrollGroupAssignment).where(
            EmployeePayrollGroupAssignment.payroll_group_id == group_id
        )
        return list((await self.session.execute(stmt)).scalars().all())


# ===========================================================================
# 4. Payroll Salary Cycles Repository
# ===========================================================================

class PayrollSalaryCycleRepository(BaseRepository[PayrollSalaryCycle]):
    """CRUD operations and search/exist checks for PayrollSalaryCycle."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, PayrollSalaryCycle)

    async def get_cycle(self, group_id: int, cycle_date: date) -> PayrollSalaryCycle | None:
        """Retrieve a specific group cycle by date."""
        stmt = select(PayrollSalaryCycle).where(
            PayrollSalaryCycle.payroll_group_id == group_id,
            PayrollSalaryCycle.cycle_date == cycle_date,
        )
        return (await self.session.execute(stmt.limit(1))).scalar_one_or_none()

    async def search(
        self,
        org_id: int,
        *,
        payroll_group_id: int | None = None,
        is_finalized: bool | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        page: int = 1,
        page_size: int = 25,
    ) -> list[PayrollSalaryCycle]:
        """Search and filter salary cycles for an organization."""
        stmt = select(PayrollSalaryCycle).join(
            PayrollGroup, PayrollGroup.id == PayrollSalaryCycle.payroll_group_id
        )
        conds = [PayrollGroup.org_id == org_id, PayrollGroup.is_deleted.is_(False)]
        if payroll_group_id is not None:
            conds.append(PayrollSalaryCycle.payroll_group_id == payroll_group_id)
        if is_finalized is not None:
            conds.append(PayrollSalaryCycle.is_finalized == is_finalized)
        if date_from is not None:
            conds.append(PayrollSalaryCycle.cycle_date >= date_from)
        if date_to is not None:
            conds.append(PayrollSalaryCycle.cycle_date <= date_to)

        stmt = stmt.where(and_(*conds)).order_by(desc(PayrollSalaryCycle.cycle_date))
        stmt = apply_pagination(stmt, page=page, page_size=page_size)
        return list((await self.session.execute(stmt)).scalars().all())

    async def search_count(
        self,
        org_id: int,
        *,
        payroll_group_id: int | None = None,
        is_finalized: bool | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> int:
        """Count matching salary cycles for an organization."""
        stmt = select(func.count()).select_from(PayrollSalaryCycle).join(
            PayrollGroup, PayrollGroup.id == PayrollSalaryCycle.payroll_group_id
        )
        conds = [PayrollGroup.org_id == org_id, PayrollGroup.is_deleted.is_(False)]
        if payroll_group_id is not None:
            conds.append(PayrollSalaryCycle.payroll_group_id == payroll_group_id)
        if is_finalized is not None:
            conds.append(PayrollSalaryCycle.is_finalized == is_finalized)
        if date_from is not None:
            conds.append(PayrollSalaryCycle.cycle_date >= date_from)
        if date_to is not None:
            conds.append(PayrollSalaryCycle.cycle_date <= date_to)

        stmt = stmt.where(and_(*conds))
        return int((await self.session.execute(stmt)).scalar_one())


# ===========================================================================
# 5. Column Settings Repository
# ===========================================================================

class PayrollColumnSettingRepository(BaseRepository[PayrollColumnSetting]):
    """CRUD operations and bulk replaces for PayrollColumnSetting."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, PayrollColumnSetting)

    async def get_by_group(self, group_id: int) -> list[PayrollColumnSetting]:
        """Retrieve all column setting lines for a group ordered by display order."""
        stmt = select(PayrollColumnSetting).where(
            PayrollColumnSetting.payroll_group_id == group_id
        ).order_by(PayrollColumnSetting.display_order)
        return list((await self.session.execute(stmt)).scalars().all())

    async def replace_columns(
        self, group_id: int, columns_list: list[dict[str, Any]], user_id: int | None = None
    ) -> list[PayrollColumnSetting]:
        """Replace all column configurations for a payroll group within a single transaction."""
        delete_stmt = delete(PayrollColumnSetting).where(
            PayrollColumnSetting.payroll_group_id == group_id
        )
        await self.session.execute(delete_stmt)

        inserted = []
        for col in columns_list:
            data = {
                "payroll_group_id": group_id,
                "column_key": col["column_key"],
                "column_label": col["column_label"],
                "is_visible": col.get("is_visible", True),
                "display_order": col["display_order"],
                "updated_by": user_id,
            }
            instance = PayrollColumnSetting(**data)
            self.session.add(instance)
            inserted.append(instance)

        await self.session.flush()
        return inserted


# ===========================================================================
# 6. Finalized Payroll Runs Repository
# ===========================================================================

class FinalizedPayrollRunRepository(BaseRepository[FinalizedPayrollRun]):
    """CRUD operations and searches for FinalizedPayrollRun."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, FinalizedPayrollRun)

    async def get_by_id_in_org(self, org_id: int, run_id: int) -> FinalizedPayrollRun | None:
        """Retrieve a specific run envelope scoped to the organization."""
        stmt = select(FinalizedPayrollRun).where(
            FinalizedPayrollRun.id == run_id,
            FinalizedPayrollRun.org_id == org_id,
        )
        return (await self.session.execute(stmt.limit(1))).scalar_one_or_none()

    async def search(
        self,
        org_id: int,
        *,
        payroll_group_id: int | None = None,
        payment_status: PaymentStatus | str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        page: int = 1,
        page_size: int = 25,
    ) -> list[FinalizedPayrollRun]:
        """Search and list finalized runs in the organization."""
        conds = [FinalizedPayrollRun.org_id == org_id]
        if payroll_group_id is not None:
            conds.append(FinalizedPayrollRun.payroll_group_id == payroll_group_id)
        if payment_status is not None:
            val = (
                payment_status.value
                if isinstance(payment_status, PaymentStatus)
                else payment_status
            )
            conds.append(FinalizedPayrollRun.payment_status == val)
        if date_from is not None:
            conds.append(FinalizedPayrollRun.cycle_from >= date_from)
        if date_to is not None:
            conds.append(FinalizedPayrollRun.cycle_to <= date_to)

        stmt = select(FinalizedPayrollRun).where(and_(*conds)).order_by(
            desc(FinalizedPayrollRun.cycle_from)
        )
        stmt = apply_pagination(stmt, page=page, page_size=page_size)
        return list((await self.session.execute(stmt)).scalars().all())

    async def search_count(
        self,
        org_id: int,
        *,
        payroll_group_id: int | None = None,
        payment_status: PaymentStatus | str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> int:
        """Count finalized runs in the organization."""
        conds = [FinalizedPayrollRun.org_id == org_id]
        if payroll_group_id is not None:
            conds.append(FinalizedPayrollRun.payroll_group_id == payroll_group_id)
        if payment_status is not None:
            val = (
                payment_status.value
                if isinstance(payment_status, PaymentStatus)
                else payment_status
            )
            conds.append(FinalizedPayrollRun.payment_status == val)
        if date_from is not None:
            conds.append(FinalizedPayrollRun.cycle_from >= date_from)
        if date_to is not None:
            conds.append(FinalizedPayrollRun.cycle_to <= date_to)

        stmt = select(func.count()).select_from(FinalizedPayrollRun).where(and_(*conds))
        return int((await self.session.execute(stmt)).scalar_one())


# ===========================================================================
# 7. Computed Payroll Rows Repository
# ===========================================================================

class PayrollComputedRowRepository(BaseRepository[PayrollComputedRow]):
    """CRUD operations, summaries, searches, and data-scoping for PayrollComputedRow."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, PayrollComputedRow)

    async def get_row(
        self, group_id: int, employee_id: int, cycle_from: date, cycle_to: date
    ) -> PayrollComputedRow | None:
        """Retrieve a specific computed row matching group, employee, and target cycle dates."""
        stmt = select(PayrollComputedRow).where(
            PayrollComputedRow.payroll_group_id == group_id,
            PayrollComputedRow.employee_id == employee_id,
            PayrollComputedRow.cycle_from == cycle_from,
            PayrollComputedRow.cycle_to == cycle_to,
        )
        return (await self.session.execute(stmt.limit(1))).scalar_one_or_none()

    async def get_rows_for_cycle(
        self,
        group_id: int,
        employee_ids: Sequence[int],
        cycle_from: date,
        cycle_to: date,
    ) -> list[PayrollComputedRow]:
        """Bulk-retrieve the computed rows of a whole employee set for one cycle (one query)."""
        if not employee_ids:
            return []
        stmt = select(PayrollComputedRow).where(
            PayrollComputedRow.payroll_group_id == group_id,
            PayrollComputedRow.employee_id.in_(employee_ids),
            PayrollComputedRow.cycle_from == cycle_from,
            PayrollComputedRow.cycle_to == cycle_to,
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def bulk_insert_rows(self, rows: list[dict[str, Any]]) -> None:
        """Insert many computed rows with a single executemany INSERT."""
        if not rows:
            return
        await self.session.execute(insert(PayrollComputedRow), rows)

    async def bulk_update_rows(self, rows: list[dict[str, Any]]) -> None:
        """Update many computed rows by primary key with a single executemany UPDATE.

        Every mapping must carry an ``id`` key plus the identical set of value columns,
        so SQLAlchemy can batch them into one statement.
        """
        if not rows:
            return
        await self.session.execute(
            update(PayrollComputedRow).execution_options(synchronize_session=False), rows
        )

    async def search(
        self,
        org_id: int,
        *,
        payroll_group_id: int | None = None,
        employee_id: int | None = None,
        cycle_from: date | None = None,
        cycle_to: date | None = None,
        is_finalized: bool | None = None,
        branch_id: int | None = None,
        dept_id: int | None = None,
        page: int = 1,
        page_size: int = 25,
    ) -> list[PayrollComputedRow]:
        """Search and list computed rows with branch and department data scopes applied."""
        stmt = select(PayrollComputedRow).join(
            PayrollGroup, PayrollGroup.id == PayrollComputedRow.payroll_group_id
        )
        conds = [PayrollGroup.org_id == org_id, PayrollGroup.is_deleted.is_(False)]
        if payroll_group_id is not None:
            conds.append(PayrollComputedRow.payroll_group_id == payroll_group_id)
        if employee_id is not None:
            conds.append(PayrollComputedRow.employee_id == employee_id)
        if cycle_from is not None:
            conds.append(PayrollComputedRow.cycle_from >= cycle_from)
        if cycle_to is not None:
            conds.append(PayrollComputedRow.cycle_to <= cycle_to)
        if is_finalized is not None:
            conds.append(PayrollComputedRow.is_finalized == is_finalized)

        if branch_id is not None or dept_id is not None:
            stmt = stmt.join(Employee, Employee.employee_id == PayrollComputedRow.employee_id)
            if branch_id is not None:
                conds.append(Employee.master_branch_id == branch_id)
            if dept_id is not None:
                conds.append(Employee.dept_id == dept_id)
            conds.append(Employee.is_deleted.is_(False))

        stmt = stmt.where(and_(*conds)).order_by(desc(PayrollComputedRow.cycle_from))
        stmt = apply_pagination(stmt, page=page, page_size=page_size)
        return list((await self.session.execute(stmt)).scalars().all())

    async def search_count(
        self,
        org_id: int,
        *,
        payroll_group_id: int | None = None,
        employee_id: int | None = None,
        cycle_from: date | None = None,
        cycle_to: date | None = None,
        is_finalized: bool | None = None,
        branch_id: int | None = None,
        dept_id: int | None = None,
    ) -> int:
        """Count matching computed rows with branch and department data scopes applied."""
        stmt = select(func.count()).select_from(PayrollComputedRow).join(
            PayrollGroup, PayrollGroup.id == PayrollComputedRow.payroll_group_id
        )
        conds = [PayrollGroup.org_id == org_id, PayrollGroup.is_deleted.is_(False)]
        if payroll_group_id is not None:
            conds.append(PayrollComputedRow.payroll_group_id == payroll_group_id)
        if employee_id is not None:
            conds.append(PayrollComputedRow.employee_id == employee_id)
        if cycle_from is not None:
            conds.append(PayrollComputedRow.cycle_from >= cycle_from)
        if cycle_to is not None:
            conds.append(PayrollComputedRow.cycle_to <= cycle_to)
        if is_finalized is not None:
            conds.append(PayrollComputedRow.is_finalized == is_finalized)

        if branch_id is not None or dept_id is not None:
            stmt = stmt.join(Employee, Employee.employee_id == PayrollComputedRow.employee_id)
            if branch_id is not None:
                conds.append(Employee.master_branch_id == branch_id)
            if dept_id is not None:
                conds.append(Employee.dept_id == dept_id)
            conds.append(Employee.is_deleted.is_(False))

        stmt = stmt.where(and_(*conds))
        return int((await self.session.execute(stmt)).scalar_one())

    async def get_summary(
        self, org_id: int, group_id: int, cycle_from: date, cycle_to: date
    ) -> dict[str, Any]:
        """Aggregate summary metrics for a specific cycle range."""
        stmt = select(
            func.count(PayrollComputedRow.employee_id.distinct()).label("headcount"),
            func.coalesce(func.sum(PayrollComputedRow.gross_earnings), 0).label(
                "total_gross_earnings"
            ),
            func.coalesce(func.sum(PayrollComputedRow.to_pay), 0).label("total_to_pay"),
            func.coalesce(func.sum(PayrollComputedRow.overtime_amount), 0).label("total_overtime"),
            func.coalesce(func.sum(PayrollComputedRow.penalties_amount), 0).label(
                "total_penalties"
            ),
            func.coalesce(func.sum(PayrollComputedRow.loan_advance_deduction), 0).label(
                "total_deductions"
            ),
        ).join(
            PayrollGroup, PayrollGroup.id == PayrollComputedRow.payroll_group_id
        ).where(
            PayrollGroup.org_id == org_id,
            PayrollGroup.is_deleted.is_(False),
            PayrollComputedRow.payroll_group_id == group_id,
            PayrollComputedRow.cycle_from == cycle_from,
            PayrollComputedRow.cycle_to == cycle_to,
        )
        res = (await self.session.execute(stmt)).one()
        return {
            "headcount": res.headcount,
            "total_gross_earnings": res.total_gross_earnings,
            "total_to_pay": res.total_to_pay,
            "total_overtime": res.total_overtime,
            "total_penalties": res.total_penalties,
            "total_deductions": res.total_deductions,
        }

    async def get_employee_history(
        self, employee_id: int, page: int = 1, page_size: int = 25
    ) -> list[PayrollComputedRow]:
        """Retrieve paginated computed history logs for a single employee."""
        stmt = select(PayrollComputedRow).where(
            PayrollComputedRow.employee_id == employee_id
        ).order_by(desc(PayrollComputedRow.cycle_from))
        stmt = apply_pagination(stmt, page=page, page_size=page_size)
        return list((await self.session.execute(stmt)).scalars().all())

    async def get_employee_history_count(self, employee_id: int) -> int:
        """Count computed history logs for a single employee."""
        stmt = select(func.count()).select_from(PayrollComputedRow).where(
            PayrollComputedRow.employee_id == employee_id
        )
        return int((await self.session.execute(stmt)).scalar_one())


# ===========================================================================
# 8. Attendance Adjustments Repository
# ===========================================================================

class AttendanceAdjustmentRepository(BaseRepository[AttendanceAdjustment]):
    """CRUD operations, exist checks and searches for AttendanceAdjustment."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, AttendanceAdjustment)

    async def get_adjustment(
        self, employee_id: int, attendance_date: date
    ) -> AttendanceAdjustment | None:
        """Retrieve a specific override adjustment for the employee and date."""
        stmt = select(AttendanceAdjustment).where(
            AttendanceAdjustment.employee_id == employee_id,
            AttendanceAdjustment.attendance_date == attendance_date,
        )
        return (await self.session.execute(stmt.limit(1))).scalar_one_or_none()

    async def get_adjustments_for_employees(
        self,
        org_id: int,
        employee_ids: Sequence[int],
        date_from: date,
        date_to: date,
    ) -> list[AttendanceAdjustment]:
        """Bulk-retrieve adjustments for a set of employees over a date range (one query).

        Ordered like :meth:`search` (newest attendance_date first) so callers can bucket
        by employee and reproduce its per-employee page ordering exactly.
        """
        if not employee_ids:
            return []
        stmt = select(AttendanceAdjustment).where(
            AttendanceAdjustment.org_id == org_id,
            AttendanceAdjustment.employee_id.in_(employee_ids),
            AttendanceAdjustment.attendance_date >= date_from,
            AttendanceAdjustment.attendance_date <= date_to,
        ).order_by(desc(AttendanceAdjustment.attendance_date))
        return list((await self.session.execute(stmt)).scalars().all())

    async def search(
        self,
        org_id: int,
        *,
        employee_id: int | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        adjustment_source: AdjustmentSource | str | None = None,
        branch_id: int | None = None,
        dept_id: int | None = None,
        page: int = 1,
        page_size: int = 25,
    ) -> list[AttendanceAdjustment]:
        """Search and filter adjustments with branch and department data scopes applied."""
        conds = [AttendanceAdjustment.org_id == org_id]
        if employee_id is not None:
            conds.append(AttendanceAdjustment.employee_id == employee_id)
        if date_from is not None:
            conds.append(AttendanceAdjustment.attendance_date >= date_from)
        if date_to is not None:
            conds.append(AttendanceAdjustment.attendance_date <= date_to)
        if adjustment_source is not None:
            val = (
                adjustment_source.value
                if isinstance(adjustment_source, AdjustmentSource)
                else adjustment_source
            )
            conds.append(AttendanceAdjustment.adjustment_source == val)

        stmt = select(AttendanceAdjustment)
        if branch_id is not None or dept_id is not None:
            stmt = stmt.join(Employee, Employee.employee_id == AttendanceAdjustment.employee_id)
            if branch_id is not None:
                conds.append(Employee.master_branch_id == branch_id)
            if dept_id is not None:
                conds.append(Employee.dept_id == dept_id)
            conds.append(Employee.is_deleted.is_(False))

        stmt = stmt.where(and_(*conds)).order_by(desc(AttendanceAdjustment.attendance_date))
        stmt = apply_pagination(stmt, page=page, page_size=page_size)
        return list((await self.session.execute(stmt)).scalars().all())

    async def search_count(
        self,
        org_id: int,
        *,
        employee_id: int | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        adjustment_source: AdjustmentSource | str | None = None,
        branch_id: int | None = None,
        dept_id: int | None = None,
    ) -> int:
        """Count adjustments with branch and department data scopes applied."""
        conds = [AttendanceAdjustment.org_id == org_id]
        if employee_id is not None:
            conds.append(AttendanceAdjustment.employee_id == employee_id)
        if date_from is not None:
            conds.append(AttendanceAdjustment.attendance_date >= date_from)
        if date_to is not None:
            conds.append(AttendanceAdjustment.attendance_date <= date_to)
        if adjustment_source is not None:
            val = (
                adjustment_source.value
                if isinstance(adjustment_source, AdjustmentSource)
                else adjustment_source
            )
            conds.append(AttendanceAdjustment.adjustment_source == val)

        stmt = select(func.count()).select_from(AttendanceAdjustment)
        if branch_id is not None or dept_id is not None:
            stmt = stmt.join(Employee, Employee.employee_id == AttendanceAdjustment.employee_id)
            if branch_id is not None:
                conds.append(Employee.master_branch_id == branch_id)
            if dept_id is not None:
                conds.append(Employee.dept_id == dept_id)
            conds.append(Employee.is_deleted.is_(False))

        stmt = stmt.where(and_(*conds))
        return int((await self.session.execute(stmt)).scalar_one())


# ===========================================================================
# 9. Attendance Adjustment Penalties Repository
# ===========================================================================

class AttendanceAdjustmentPenaltyRepository(BaseRepository[AttendanceAdjustmentPenalty]):
    """CRUD operations and helpers for AttendanceAdjustmentPenalty."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, AttendanceAdjustmentPenalty)

    async def get_penalties(
        self, employee_id: int, date_from: date, date_to: date
    ) -> list[AttendanceAdjustmentPenalty]:
        """Retrieve all active penalties assigned to an employee within a date range."""
        stmt = select(AttendanceAdjustmentPenalty).where(
            AttendanceAdjustmentPenalty.employee_id == employee_id,
            AttendanceAdjustmentPenalty.attendance_date >= date_from,
            AttendanceAdjustmentPenalty.attendance_date <= date_to,
            AttendanceAdjustmentPenalty.is_removed.is_(False),
        ).order_by(AttendanceAdjustmentPenalty.attendance_date)
        return list((await self.session.execute(stmt)).scalars().all())

    async def get_penalties_for_employees(
        self, employee_ids: Sequence[int], date_from: date, date_to: date
    ) -> list[AttendanceAdjustmentPenalty]:
        """Bulk-retrieve active penalties for a set of employees over a date range (one query)."""
        if not employee_ids:
            return []
        stmt = select(AttendanceAdjustmentPenalty).where(
            AttendanceAdjustmentPenalty.employee_id.in_(employee_ids),
            AttendanceAdjustmentPenalty.attendance_date >= date_from,
            AttendanceAdjustmentPenalty.attendance_date <= date_to,
            AttendanceAdjustmentPenalty.is_removed.is_(False),
        ).order_by(AttendanceAdjustmentPenalty.attendance_date)
        return list((await self.session.execute(stmt)).scalars().all())


# ===========================================================================
# 10. Attendance Adjustment Extra Hours Repository
# ===========================================================================

class AttendanceAdjustmentExtraHoursRepository(BaseRepository[AttendanceAdjustmentExtraHours]):
    """CRUD operations and helpers for AttendanceAdjustmentExtraHours."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, AttendanceAdjustmentExtraHours)

    async def get_extra_hours(
        self, employee_id: int, attendance_date: date
    ) -> AttendanceAdjustmentExtraHours | None:
        """Retrieve the extra hours override for an employee on a specific date."""
        stmt = select(AttendanceAdjustmentExtraHours).where(
            AttendanceAdjustmentExtraHours.employee_id == employee_id,
            AttendanceAdjustmentExtraHours.attendance_date == attendance_date,
        )
        return (await self.session.execute(stmt.limit(1))).scalar_one_or_none()

    async def get_extra_hours_range(
        self, employee_id: int, date_from: date, date_to: date
    ) -> list[AttendanceAdjustmentExtraHours]:
        """Retrieve all extra hours override logs for an employee within a date range."""
        stmt = select(AttendanceAdjustmentExtraHours).where(
            AttendanceAdjustmentExtraHours.employee_id == employee_id,
            AttendanceAdjustmentExtraHours.attendance_date >= date_from,
            AttendanceAdjustmentExtraHours.attendance_date <= date_to,
        ).order_by(AttendanceAdjustmentExtraHours.attendance_date)
        return list((await self.session.execute(stmt)).scalars().all())

    async def get_extra_hours_for_employees(
        self, employee_ids: Sequence[int], date_from: date, date_to: date
    ) -> list[AttendanceAdjustmentExtraHours]:
        """Bulk-retrieve extra hours logs for a set of employees over a date range (one query)."""
        if not employee_ids:
            return []
        stmt = select(AttendanceAdjustmentExtraHours).where(
            AttendanceAdjustmentExtraHours.employee_id.in_(employee_ids),
            AttendanceAdjustmentExtraHours.attendance_date >= date_from,
            AttendanceAdjustmentExtraHours.attendance_date <= date_to,
        ).order_by(AttendanceAdjustmentExtraHours.attendance_date)
        return list((await self.session.execute(stmt)).scalars().all())
