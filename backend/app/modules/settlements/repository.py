"""Settlement Management — data-access layer (async SQLAlchemy).

Defines the repository classes for Employee Loans & Advances, Loan/Advance Transactions,
Employee Arrears, Arrears Transactions, and combined Settlement operations.
Only database operations are handled here — no business rules are evaluated.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import and_, func, literal_column, select, union_all
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.constants.enums import SortOrder
from app.modules.employee.models.employee import Employee
from app.modules.settlements.models import (
    ArrearsTransaction,
    EmployeeArrears,
    EmployeeLoanAdvance,
    LoanAdvanceTransaction,
)
from app.shared.base.repository import BaseRepository
from app.shared.utils.query import apply_sorting

# ===========================================================================
# 1. Employee Loan & Advance Repository
# ===========================================================================


class EmployeeLoanAdvanceRepository(BaseRepository[EmployeeLoanAdvance]):
    """CRUD, search, and exists checks for employee loans and advances."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, EmployeeLoanAdvance)

    async def get_by_id_in_org(
        self, org_id: int, loan_advance_id: int
    ) -> EmployeeLoanAdvance | None:
        """Return a loan/advance by ID scoped to org_id, with transactions loaded."""
        stmt = (
            select(EmployeeLoanAdvance)
            .where(
                EmployeeLoanAdvance.id == loan_advance_id,
                EmployeeLoanAdvance.org_id == org_id,
            )
            .options(selectinload(EmployeeLoanAdvance.transactions))
        )
        return (await self.session.execute(stmt.limit(1))).scalar_one_or_none()

    async def exists_in_org(self, org_id: int, loan_advance_id: int) -> bool:
        """Check if a loan/advance registry exists within the organization."""
        stmt = select(EmployeeLoanAdvance.id).where(
            EmployeeLoanAdvance.id == loan_advance_id,
            EmployeeLoanAdvance.org_id == org_id,
        )
        return (await self.session.execute(stmt.limit(1))).first() is not None

    async def has_transactions(self, loan_advance_id: int) -> bool:
        """Return whether any ledger transaction references the loan/advance."""
        stmt = (
            select(LoanAdvanceTransaction.id)
            .where(LoanAdvanceTransaction.loan_advance_id == loan_advance_id)
            .limit(1)
        )
        return (await self.session.execute(stmt)).first() is not None

    def _build_search_query(
        self,
        org_id: int,
        employee_id: int | None = None,
        type: str | None = None,
        status: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        search: str | None = None,
        branch_id: int | None = None,
        dept_id: int | None = None,
    ) -> select:
        stmt = select(EmployeeLoanAdvance)
        conds = [EmployeeLoanAdvance.org_id == org_id]

        if employee_id is not None:
            conds.append(EmployeeLoanAdvance.employee_id == employee_id)
        if type is not None:
            conds.append(EmployeeLoanAdvance.type == type)
        if status is not None:
            conds.append(EmployeeLoanAdvance.status == status)
        if date_from is not None:
            conds.append(EmployeeLoanAdvance.transaction_date >= date_from)
        if date_to is not None:
            conds.append(EmployeeLoanAdvance.transaction_date <= date_to)
        if search:
            conds.append(EmployeeLoanAdvance.name.ilike(f"%{search.strip()}%"))

        if branch_id is not None or dept_id is not None:
            stmt = stmt.join(Employee, Employee.employee_id == EmployeeLoanAdvance.employee_id)
            if branch_id is not None:
                conds.append(Employee.master_branch_id == branch_id)
            if dept_id is not None:
                conds.append(Employee.dept_id == dept_id)

        return stmt.where(and_(*conds))

    async def search(
        self,
        org_id: int,
        *,
        employee_id: int | None = None,
        type: str | None = None,
        status: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        search: str | None = None,
        branch_id: int | None = None,
        dept_id: int | None = None,
        sort_by: str | None = "transaction_date",
        sort_order: str | SortOrder = SortOrder.DESC,
        page: int = 1,
        page_size: int = 25,
    ) -> list[EmployeeLoanAdvance]:
        """Return a filtered, sorted, and paginated page of loans/advances."""
        stmt = self._build_search_query(
            org_id=org_id,
            employee_id=employee_id,
            type=type,
            status=status,
            date_from=date_from,
            date_to=date_to,
            search=search,
            branch_id=branch_id,
            dept_id=dept_id,
        )
        stmt = apply_sorting(
            stmt,
            EmployeeLoanAdvance,
            sort_by,
            sort_order,
            allowed={"transaction_date", "outstanding_amount", "principal_amount", "created_at"},
            default_sort_by="transaction_date",
        )
        stmt = stmt.limit(page_size).offset((page - 1) * page_size)
        return list((await self.session.execute(stmt)).scalars().all())

    async def search_count(
        self,
        org_id: int,
        *,
        employee_id: int | None = None,
        type: str | None = None,
        status: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        search: str | None = None,
        branch_id: int | None = None,
        dept_id: int | None = None,
    ) -> int:
        """Return the count of loans/advances matching the filter criteria."""
        base_stmt = self._build_search_query(
            org_id=org_id,
            employee_id=employee_id,
            type=type,
            status=status,
            date_from=date_from,
            date_to=date_to,
            search=search,
            branch_id=branch_id,
            dept_id=dept_id,
        )
        stmt = select(func.count()).select_from(base_stmt.subquery())
        return int((await self.session.execute(stmt)).scalar_one())

    async def list_active_by_employee(
        self, org_id: int, employee_id: int
    ) -> list[EmployeeLoanAdvance]:
        """Return all active loans/advances for a single employee."""
        stmt = (
            select(EmployeeLoanAdvance)
            .where(
                EmployeeLoanAdvance.org_id == org_id,
                EmployeeLoanAdvance.employee_id == employee_id,
                EmployeeLoanAdvance.status == "active",
            )
            .order_by(EmployeeLoanAdvance.transaction_date.desc())
        )
        return list((await self.session.execute(stmt)).scalars().all())


# ===========================================================================
# 2. Loan & Advance Ledger Transactions Repository
# ===========================================================================


class LoanAdvanceTransactionRepository(BaseRepository[LoanAdvanceTransaction]):
    """Operations for loan and advance ledger transaction records."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, LoanAdvanceTransaction)

    def _build_search_query(
        self,
        loan_advance_id: int,
        transaction_type: str | None = None,
        source: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> select:
        conds = [LoanAdvanceTransaction.loan_advance_id == loan_advance_id]
        if transaction_type is not None:
            conds.append(LoanAdvanceTransaction.transaction_type == transaction_type)
        if source is not None:
            conds.append(LoanAdvanceTransaction.source == source)
        if date_from is not None:
            conds.append(LoanAdvanceTransaction.transaction_date >= date_from)
        if date_to is not None:
            conds.append(LoanAdvanceTransaction.transaction_date <= date_to)
        return select(LoanAdvanceTransaction).where(and_(*conds))

    async def search(
        self,
        loan_advance_id: int,
        *,
        transaction_type: str | None = None,
        source: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        sort_by: str | None = "transaction_date",
        sort_order: str | SortOrder = SortOrder.DESC,
        page: int = 1,
        page_size: int = 25,
    ) -> list[LoanAdvanceTransaction]:
        """Return a filtered, sorted, and paginated list of ledger transactions."""
        stmt = self._build_search_query(
            loan_advance_id=loan_advance_id,
            transaction_type=transaction_type,
            source=source,
            date_from=date_from,
            date_to=date_to,
        )
        stmt = apply_sorting(
            stmt,
            LoanAdvanceTransaction,
            sort_by,
            sort_order,
            allowed={"transaction_date", "amount", "created_at"},
            default_sort_by="transaction_date",
        )
        stmt = stmt.limit(page_size).offset((page - 1) * page_size)
        return list((await self.session.execute(stmt)).scalars().all())

    async def search_count(
        self,
        loan_advance_id: int,
        *,
        transaction_type: str | None = None,
        source: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> int:
        """Return the count of ledger transactions matching the filters."""
        base_stmt = self._build_search_query(
            loan_advance_id=loan_advance_id,
            transaction_type=transaction_type,
            source=source,
            date_from=date_from,
            date_to=date_to,
        )
        stmt = select(func.count()).select_from(base_stmt.subquery())
        return int((await self.session.execute(stmt)).scalar_one())

    def _build_search_all_query(
        self,
        org_id: int,
        employee_id: int | None = None,
        transaction_type: str | None = None,
        source: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> select:
        stmt = (
            select(LoanAdvanceTransaction)
            .join(EmployeeLoanAdvance, LoanAdvanceTransaction.loan_advance_id == EmployeeLoanAdvance.id)
            .where(EmployeeLoanAdvance.org_id == org_id)
        )
        if employee_id is not None:
            stmt = stmt.where(EmployeeLoanAdvance.employee_id == employee_id)
        if transaction_type is not None:
            stmt = stmt.where(LoanAdvanceTransaction.transaction_type == transaction_type)
        if source is not None:
            stmt = stmt.where(LoanAdvanceTransaction.source == source)
        if date_from is not None:
            stmt = stmt.where(LoanAdvanceTransaction.transaction_date >= date_from)
        if date_to is not None:
            stmt = stmt.where(LoanAdvanceTransaction.transaction_date <= date_to)
        return stmt

    async def search_all_transactions(
        self,
        org_id: int,
        *,
        employee_id: int | None = None,
        transaction_type: str | None = None,
        source: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        sort_by: str | None = "transaction_date",
        sort_order: str | SortOrder = SortOrder.DESC,
        page: int = 1,
        page_size: int = 25,
    ) -> list[LoanAdvanceTransaction]:
        """Return org-wide filtered, sorted, and paginated list of loan transactions."""
        stmt = self._build_search_all_query(
            org_id=org_id,
            employee_id=employee_id,
            transaction_type=transaction_type,
            source=source,
            date_from=date_from,
            date_to=date_to,
        )
        stmt = apply_sorting(
            stmt,
            LoanAdvanceTransaction,
            sort_by,
            sort_order,
            allowed={"transaction_date", "amount", "created_at"},
            default_sort_by="transaction_date",
        )
        stmt = stmt.limit(page_size).offset((page - 1) * page_size)
        return list((await self.session.execute(stmt)).scalars().all())

    async def search_all_transactions_count(
        self,
        org_id: int,
        *,
        employee_id: int | None = None,
        transaction_type: str | None = None,
        source: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> int:
        """Return count of org-wide loan transactions matching filters."""
        base_stmt = self._build_search_all_query(
            org_id=org_id,
            employee_id=employee_id,
            transaction_type=transaction_type,
            source=source,
            date_from=date_from,
            date_to=date_to,
        )
        stmt = select(func.count()).select_from(base_stmt.subquery())
        return int((await self.session.execute(stmt)).scalar_one())


# ===========================================================================
# 3. Employee Arrears Repository
# ===========================================================================


class EmployeeArrearsRepository(BaseRepository[EmployeeArrears]):
    """CRUD, search, and exists checks for employee arrears."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, EmployeeArrears)

    async def get_by_employee_id(self, org_id: int, employee_id: int) -> EmployeeArrears | None:
        """Return the arrears header record for an employee within an organization."""
        stmt = select(EmployeeArrears).where(
            EmployeeArrears.org_id == org_id,
            EmployeeArrears.employee_id == employee_id,
        )
        return (await self.session.execute(stmt.limit(1))).scalar_one_or_none()

    def _build_search_query(
        self,
        org_id: int,
        employee_id: int | None = None,
        min_outstanding: Decimal | None = None,
        branch_id: int | None = None,
        dept_id: int | None = None,
    ) -> select:
        stmt = select(EmployeeArrears)
        conds = [EmployeeArrears.org_id == org_id]
        if employee_id is not None:
            conds.append(EmployeeArrears.employee_id == employee_id)
        if min_outstanding is not None:
            conds.append(EmployeeArrears.outstanding_arrears >= min_outstanding)

        if branch_id is not None or dept_id is not None:
            stmt = stmt.join(Employee, Employee.employee_id == EmployeeArrears.employee_id)
            if branch_id is not None:
                conds.append(Employee.master_branch_id == branch_id)
            if dept_id is not None:
                conds.append(Employee.dept_id == dept_id)
        return stmt.where(and_(*conds))

    async def search(
        self,
        org_id: int,
        *,
        employee_id: int | None = None,
        min_outstanding: Decimal | None = None,
        branch_id: int | None = None,
        dept_id: int | None = None,
        sort_by: str | None = "outstanding_arrears",
        sort_order: str | SortOrder = SortOrder.DESC,
        page: int = 1,
        page_size: int = 25,
    ) -> list[EmployeeArrears]:
        """Return a filtered, sorted, and paginated page of arrears headers."""
        stmt = self._build_search_query(
            org_id=org_id,
            employee_id=employee_id,
            min_outstanding=min_outstanding,
            branch_id=branch_id,
            dept_id=dept_id,
        )
        stmt = apply_sorting(
            stmt,
            EmployeeArrears,
            sort_by,
            sort_order,
            allowed={"outstanding_arrears", "arrears_created", "arrears_paid", "created_at"},
            default_sort_by="outstanding_arrears",
        )
        stmt = stmt.limit(page_size).offset((page - 1) * page_size)
        return list((await self.session.execute(stmt)).scalars().all())

    async def search_count(
        self,
        org_id: int,
        *,
        employee_id: int | None = None,
        min_outstanding: Decimal | None = None,
        branch_id: int | None = None,
        dept_id: int | None = None,
    ) -> int:
        """Return the count of arrears headers matching the criteria."""
        base_stmt = self._build_search_query(
            org_id=org_id,
            employee_id=employee_id,
            min_outstanding=min_outstanding,
            branch_id=branch_id,
            dept_id=dept_id,
        )
        stmt = select(func.count()).select_from(base_stmt.subquery())
        return int((await self.session.execute(stmt)).scalar_one())


# ===========================================================================
# 4. Arrears Transaction Ledger Repository
# ===========================================================================


class ArrearsTransactionRepository(BaseRepository[ArrearsTransaction]):
    """Operations for arrears transaction logs."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, ArrearsTransaction)

    def _build_search_query(
        self,
        employee_id: int,
        transaction_type: str | None = None,
        source: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> select:
        conds = [ArrearsTransaction.employee_id == employee_id]
        if transaction_type is not None:
            conds.append(ArrearsTransaction.transaction_type == transaction_type)
        if source is not None:
            conds.append(ArrearsTransaction.source == source)
        if date_from is not None:
            conds.append(ArrearsTransaction.transaction_date >= date_from)
        if date_to is not None:
            conds.append(ArrearsTransaction.transaction_date <= date_to)
        return select(ArrearsTransaction).where(and_(*conds))

    async def search(
        self,
        employee_id: int,
        *,
        transaction_type: str | None = None,
        source: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        sort_by: str | None = "transaction_date",
        sort_order: str | SortOrder = SortOrder.DESC,
        page: int = 1,
        page_size: int = 25,
    ) -> list[ArrearsTransaction]:
        """Return a filtered, sorted, and paginated page of arrears transactions."""
        stmt = self._build_search_query(
            employee_id=employee_id,
            transaction_type=transaction_type,
            source=source,
            date_from=date_from,
            date_to=date_to,
        )
        stmt = apply_sorting(
            stmt,
            ArrearsTransaction,
            sort_by,
            sort_order,
            allowed={"transaction_date", "amount", "created_at"},
            default_sort_by="transaction_date",
        )
        stmt = stmt.limit(page_size).offset((page - 1) * page_size)
        return list((await self.session.execute(stmt)).scalars().all())

    async def search_count(
        self,
        employee_id: int,
        *,
        transaction_type: str | None = None,
        source: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> int:
        """Return the count of arrears transactions matching the filters."""
        base_stmt = self._build_search_query(
            employee_id=employee_id,
            transaction_type=transaction_type,
            source=source,
            date_from=date_from,
            date_to=date_to,
        )
        stmt = select(func.count()).select_from(base_stmt.subquery())
        return int((await self.session.execute(stmt)).scalar_one())

    def _build_search_all_query(
        self,
        org_id: int,
        employee_id: int | None = None,
        transaction_type: str | None = None,
        source: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> select:
        stmt = select(ArrearsTransaction).where(ArrearsTransaction.org_id == org_id)
        if employee_id is not None:
            stmt = stmt.where(ArrearsTransaction.employee_id == employee_id)
        if transaction_type is not None:
            stmt = stmt.where(ArrearsTransaction.transaction_type == transaction_type)
        if source is not None:
            stmt = stmt.where(ArrearsTransaction.source == source)
        if date_from is not None:
            stmt = stmt.where(ArrearsTransaction.transaction_date >= date_from)
        if date_to is not None:
            stmt = stmt.where(ArrearsTransaction.transaction_date <= date_to)
        return stmt

    async def search_all_transactions(
        self,
        org_id: int,
        *,
        employee_id: int | None = None,
        transaction_type: str | None = None,
        source: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        sort_by: str | None = "transaction_date",
        sort_order: str | SortOrder = SortOrder.DESC,
        page: int = 1,
        page_size: int = 25,
    ) -> list[ArrearsTransaction]:
        """Return org-wide filtered, sorted, and paginated list of arrears transactions."""
        stmt = self._build_search_all_query(
            org_id=org_id,
            employee_id=employee_id,
            transaction_type=transaction_type,
            source=source,
            date_from=date_from,
            date_to=date_to,
        )
        stmt = apply_sorting(
            stmt,
            ArrearsTransaction,
            sort_by,
            sort_order,
            allowed={"transaction_date", "amount", "created_at"},
            default_sort_by="transaction_date",
        )
        stmt = stmt.limit(page_size).offset((page - 1) * page_size)
        return list((await self.session.execute(stmt)).scalars().all())

    async def search_all_transactions_count(
        self,
        org_id: int,
        *,
        employee_id: int | None = None,
        transaction_type: str | None = None,
        source: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> int:
        """Return count of org-wide arrears transactions matching filters."""
        base_stmt = self._build_search_all_query(
            org_id=org_id,
            employee_id=employee_id,
            transaction_type=transaction_type,
            source=source,
            date_from=date_from,
            date_to=date_to,
        )
        stmt = select(func.count()).select_from(base_stmt.subquery())
        return int((await self.session.execute(stmt)).scalar_one())


# ===========================================================================
# 5. Coordinate Settlement Views Repository
# ===========================================================================


class SettlementRepository:
    """Repository coordinating cross-model settlement statement, history, and summaries."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def _build_combined_history_query(
        self,
        org_id: int,
        employee_id: int,
        date_from: date | None = None,
        date_to: date | None = None,
        source: str | None = None,
    ) -> Any:
        # Query for Loan/Advance Transactions
        loan_stmt = select(
            LoanAdvanceTransaction.transaction_date.label("transaction_date"),
            LoanAdvanceTransaction.type_label.label("kind"),
            LoanAdvanceTransaction.transaction_type.label("transaction_type"),
            LoanAdvanceTransaction.amount.label("amount"),
            literal_column("0.00").label("running_outstanding"),
            LoanAdvanceTransaction.source.label("source"),
            LoanAdvanceTransaction.comment.label("comment"),
            LoanAdvanceTransaction.created_at.label("created_at"),
        ).where(
            LoanAdvanceTransaction.org_id == org_id,
            LoanAdvanceTransaction.employee_id == employee_id,
        )

        # Query for Arrears Transactions
        arrears_stmt = select(
            ArrearsTransaction.transaction_date.label("transaction_date"),
            literal_column("'arrears'").label("kind"),
            ArrearsTransaction.transaction_type.label("transaction_type"),
            ArrearsTransaction.amount.label("amount"),
            ArrearsTransaction.outstanding_after.label("running_outstanding"),
            ArrearsTransaction.source.label("source"),
            ArrearsTransaction.comment.label("comment"),
            ArrearsTransaction.created_at.label("created_at"),
        ).where(
            ArrearsTransaction.org_id == org_id,
            ArrearsTransaction.employee_id == employee_id,
        )

        # Apply common filters
        if date_from is not None:
            loan_stmt = loan_stmt.where(LoanAdvanceTransaction.transaction_date >= date_from)
            arrears_stmt = arrears_stmt.where(ArrearsTransaction.transaction_date >= date_from)
        if date_to is not None:
            loan_stmt = loan_stmt.where(LoanAdvanceTransaction.transaction_date <= date_to)
            arrears_stmt = arrears_stmt.where(ArrearsTransaction.transaction_date <= date_to)
        if source is not None:
            loan_stmt = loan_stmt.where(LoanAdvanceTransaction.source == source)
            arrears_stmt = arrears_stmt.where(ArrearsTransaction.source == source)

        return union_all(loan_stmt, arrears_stmt).subquery("combined_history")

    async def get_combined_history(
        self,
        org_id: int,
        employee_id: int,
        *,
        date_from: date | None = None,
        date_to: date | None = None,
        source: str | None = None,
        page: int = 1,
        page_size: int = 25,
    ) -> list[dict[str, Any]]:
        """Return combined, sorted, and paginated transaction history."""
        union_stmt = self._build_combined_history_query(
            org_id=org_id,
            employee_id=employee_id,
            date_from=date_from,
            date_to=date_to,
            source=source,
        )
        alias_stmt = (
            select(
                union_stmt.c.transaction_date,
                union_stmt.c.kind,
                union_stmt.c.transaction_type,
                union_stmt.c.amount,
                union_stmt.c.running_outstanding,
                union_stmt.c.source,
                union_stmt.c.comment,
                union_stmt.c.created_at,
            )
            .order_by(
                union_stmt.c.transaction_date.desc(),
                union_stmt.c.created_at.desc(),
            )
            .limit(page_size)
            .offset((page - 1) * page_size)
        )
        res = await self.session.execute(alias_stmt)
        return [
            {
                "date": row[0],
                "kind": row[1],
                "transaction_type": row[2],
                "amount": Decimal(row[3]),
                "running_outstanding": Decimal(row[4]),
                "source": row[5],
                "comment": row[6],
            }
            for row in res.all()
        ]

    async def get_combined_history_count(
        self,
        org_id: int,
        employee_id: int,
        *,
        date_from: date | None = None,
        date_to: date | None = None,
        source: str | None = None,
    ) -> int:
        """Return the count of combined settlement history log records."""
        union_stmt = self._build_combined_history_query(
            org_id=org_id,
            employee_id=employee_id,
            date_from=date_from,
            date_to=date_to,
            source=source,
        )
        stmt = select(func.count()).select_from(union_stmt)
        return int((await self.session.execute(stmt)).scalar_one())

    async def get_employee_settlement_summary(
        self, org_id: int, employee_id: int | None = None
    ) -> dict[str, Any]:
        """Aggregate outstanding loans/advances and arrears (Settlement Calculation Lookup)."""
        loan_conds = [
            EmployeeLoanAdvance.org_id == org_id,
            EmployeeLoanAdvance.status == "active",
        ]
        if employee_id is not None:
            loan_conds.append(EmployeeLoanAdvance.employee_id == employee_id)

        loan_stmt = select(
            func.coalesce(func.sum(EmployeeLoanAdvance.principal_amount), 0),
            func.coalesce(func.sum(EmployeeLoanAdvance.outstanding_amount), 0),
            func.count(EmployeeLoanAdvance.id),
        ).where(and_(*loan_conds))

        loan_res = (await self.session.execute(loan_stmt)).first()

        arrears_conds = [EmployeeArrears.org_id == org_id]
        if employee_id is not None:
            arrears_conds.append(EmployeeArrears.employee_id == employee_id)

        arrears_stmt = select(
            func.coalesce(func.sum(EmployeeArrears.outstanding_arrears), 0)
        ).where(and_(*arrears_conds))

        arrears_res = (await self.session.execute(arrears_stmt)).scalar()

        return {
            "total_active_loans_advances": Decimal(loan_res[0]) if loan_res else Decimal("0.00"),
            "total_outstanding_loans_advances": (
                Decimal(loan_res[1]) if loan_res else Decimal("0.00")
            ),
            "total_outstanding_arrears": Decimal(arrears_res) if arrears_res else Decimal("0.00"),
            "count_active": int(loan_res[2]) if loan_res else 0,
        }
