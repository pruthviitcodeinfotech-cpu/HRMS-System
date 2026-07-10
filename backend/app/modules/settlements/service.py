"""Settlement Management — service layer (business logic & orchestration).

Implements the business logic of the Settlement Management API Contract.
All database access is performed strictly via repositories.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants.enums import SortOrder
from app.modules.audit.constants import ActionType
from app.modules.audit.service import AuditService
from app.modules.employee.constants import EmploymentStatus
from app.modules.employee.models.employee import Employee
from app.modules.payroll.models.run import FinalizedPayrollRun
from app.modules.settlements.exceptions import (
    ArrearsNotFoundException,
    EmployeeNotExitedException,
    EmployeeNotFoundException,
    InsufficientArrearsException,
    InvalidTransactionException,
    LoanAdvanceClosedException,
    LoanAdvanceHasTransactionsException,
    LoanAdvanceNotFoundException,
    PayrollNotFinalizedException,
    SettlementAlreadyFinalizedException,
)
from app.modules.settlements.models import (
    ArrearsTransaction,
    EmployeeArrears,
    EmployeeLoanAdvance,
    LoanAdvanceTransaction,
)
from app.modules.settlements.repository import (
    ArrearsTransactionRepository,
    EmployeeArrearsRepository,
    EmployeeLoanAdvanceRepository,
    LoanAdvanceTransactionRepository,
    SettlementRepository,
)
from app.modules.settlements.schemas import (
    ArrearsSearchQuery,
    ArrearsTransactionSearchQuery,
    LoanAdvanceSearchQuery,
    LoanAdvanceTransactionSearchQuery,
    SettlementHistoryQuery,
    SettlementStatementQuery,
    SettlementSummaryQuery,
)
from app.shared.base.service import BaseService
from app.shared.schemas.pagination import PaginatedResponse
from app.shared.utils.datetime import utcnow


class SettlementService(BaseService):
    """Settlement Management business rules engine and service."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)
        # Repositories
        self.loans_advances = EmployeeLoanAdvanceRepository(session)
        self.loan_transactions = LoanAdvanceTransactionRepository(session)
        self.arrears = EmployeeArrearsRepository(session)
        self.arrears_transactions = ArrearsTransactionRepository(session)
        self.settlement_coords = SettlementRepository(session)

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

    async def _validate_ff_preconditions(self, org_id: int, employee_id: int) -> Employee:
        """Return the employee, having enforced every Full & Final precondition.

        A Full & Final settlement debits the employee's loan and arrears ledgers, so it may
        only run once, and only when the employee has actually left and their final payroll
        has been locked:

        * **Employee Exit -> Settlement** — ``employment_status`` must be ``terminated``.
        * **Payroll -> Settlement** — a finalized (not de-finalized) payroll run must cover
          the employee's ``date_of_leaving``.
        * **Idempotency** — ``settlement_finalized_at`` must not already be stamped.
        """
        emp = await self._validate_employee(org_id, employee_id)

        if emp.employment_status != EmploymentStatus.TERMINATED.value:
            raise EmployeeNotExitedException()
        if emp.settlement_finalized_at is not None:
            raise SettlementAlreadyFinalizedException()
        if emp.date_of_leaving is None:
            raise PayrollNotFinalizedException(
                "The employee has no last working day recorded, so no payroll run can cover it."
            )

        run_stmt = select(FinalizedPayrollRun.id).where(
            FinalizedPayrollRun.org_id == org_id,
            FinalizedPayrollRun.cycle_from <= emp.date_of_leaving,
            FinalizedPayrollRun.cycle_to >= emp.date_of_leaving,
            FinalizedPayrollRun.is_definalized.is_(False),
        )
        if (await self.session.execute(run_stmt.limit(1))).first() is None:
            raise PayrollNotFinalizedException()

        return emp

    # =========================================================================
    # 1. Loans & Advances (Registry Headers)
    # =========================================================================

    async def create_loan_advance(
        self, org_id: int, data: dict[str, Any], user_id: int
    ) -> EmployeeLoanAdvance:
        """Create and register a new loan or advance header."""
        employee_id = data["employee_id"]
        emp = await self._validate_employee(org_id, employee_id)

        principal = Decimal(str(data["principal_amount"]))
        installment = Decimal(str(data["monthly_installment"]))

        if principal <= 0 or installment <= 0:
            raise InvalidTransactionException(
                "Principal amount and monthly installment must be positive."
            )
        if installment > principal:
            raise InvalidTransactionException("Monthly installment cannot exceed principal amount.")

        async with self.transaction():
            loan = await self.loans_advances.create(
                {
                    "org_id": org_id,
                    "employee_id": employee_id,
                    "name": data["name"],
                    "type": getattr(data["type"], "value", data["type"]),
                    "principal_amount": principal,
                    "monthly_installment": installment,
                    "total_debit": Decimal("0.00"),
                    "outstanding_amount": principal,
                    "transaction_date": data["transaction_date"],
                    "status": "active",
                    "comment": data.get("comment"),
                    "created_by": user_id,
                }
            )

            await self.audit.record(
                org_id=org_id,
                module="settlements",
                sub_module="loan_advance",
                action_type=ActionType.INSERT,
                title="Create Loan/Advance",
                description=(
                    f"Registered {loan.type} '{loan.name}' of principal {loan.principal_amount} "
                    f"for employee {employee_id}."
                ),
                performed_by_user_id=user_id,
                performed_by_name=f"User {user_id}",
                employee_id=employee_id,
                employee_name=emp.employee_name,
            )
            return loan

    async def get_loan_advance(self, org_id: int, loan_advance_id: int) -> EmployeeLoanAdvance:
        """Retrieve a loan/advance registry details by ID."""
        loan = await self.loans_advances.get_by_id_in_org(org_id, loan_advance_id)
        if not loan:
            raise LoanAdvanceNotFoundException()
        return loan

    async def search_loans_advances(
        self, org_id: int, query: LoanAdvanceSearchQuery
    ) -> PaginatedResponse[EmployeeLoanAdvance]:
        """Search and paginate loan/advance registry headers."""
        items = await self.loans_advances.search(
            org_id,
            employee_id=query.employee_id,
            type=getattr(query.type, "value", query.type) if query.type else None,
            status=getattr(query.status, "value", query.status) if query.status else None,
            date_from=query.date_from,
            date_to=query.date_to,
            search=query.search,
            branch_id=query.branch_id,
            dept_id=query.dept_id,
            sort_by=query.sort_by,
            sort_order=query.sort_order or SortOrder.DESC,
            page=query.page,
            page_size=query.page_size,
        )
        total = await self.loans_advances.search_count(
            org_id,
            employee_id=query.employee_id,
            type=getattr(query.type, "value", query.type) if query.type else None,
            status=getattr(query.status, "value", query.status) if query.status else None,
            date_from=query.date_from,
            date_to=query.date_to,
            search=query.search,
            branch_id=query.branch_id,
            dept_id=query.dept_id,
        )
        return self.paginate(items, page=query.page, page_size=query.page_size, total_records=total)

    async def update_loan_advance(
        self, org_id: int, loan_advance_id: int, data: dict[str, Any], user_id: int
    ) -> EmployeeLoanAdvance:
        """Update fields of an active loan/advance registry."""
        loan = await self.get_loan_advance(org_id, loan_advance_id)
        if loan.status == "closed":
            raise LoanAdvanceClosedException()

        updates: dict[str, Any] = {"updated_by": user_id, "updated_at": datetime.now()}

        if "name" in data and data["name"] is not None:
            updates["name"] = data["name"]
        if "comment" in data:
            updates["comment"] = data["comment"]

        if "monthly_installment" in data and data["monthly_installment"] is not None:
            installment = Decimal(str(data["monthly_installment"]))
            if installment <= 0:
                raise InvalidTransactionException("Monthly installment must be positive.")
            if installment > loan.principal_amount:
                raise InvalidTransactionException(
                    "Monthly installment cannot exceed principal amount."
                )
            updates["monthly_installment"] = installment

        async with self.transaction():
            updated = await self.loans_advances.update(loan, updates)
            await self.audit.record(
                org_id=org_id,
                module="settlements",
                sub_module="loan_advance",
                action_type=ActionType.UPDATE,
                title="Update Loan/Advance",
                description=f"Updated registry details for loan/advance '{loan.name}' ({loan.id}).",
                performed_by_user_id=user_id,
                performed_by_name=f"User {user_id}",
                employee_id=loan.employee_id,
            )
            return updated

    async def close_loan_advance(
        self, org_id: int, loan_advance_id: int, user_id: int
    ) -> EmployeeLoanAdvance:
        """Manually close an active loan/advance registry."""
        loan = await self.get_loan_advance(org_id, loan_advance_id)
        if loan.status == "closed":
            raise LoanAdvanceClosedException()

        async with self.transaction():
            updated = await self.loans_advances.update(
                loan,
                {
                    "status": "closed",
                    "updated_by": user_id,
                    "updated_at": datetime.now(),
                },
            )
            await self.audit.record(
                org_id=org_id,
                module="settlements",
                sub_module="loan_advance",
                action_type=ActionType.UPDATE,
                title="Close Loan/Advance",
                description=f"Manually closed loan/advance registry '{loan.name}' ({loan.id}).",
                performed_by_user_id=user_id,
                performed_by_name=f"User {user_id}",
                employee_id=loan.employee_id,
            )
            return updated

    async def delete_loan_advance(self, org_id: int, loan_advance_id: int, user_id: int) -> None:
        """Delete a loan/advance registry header if no transaction ledger entries exist."""
        loan = await self.get_loan_advance(org_id, loan_advance_id)
        if await self.loans_advances.has_transactions(loan_advance_id):
            raise LoanAdvanceHasTransactionsException()

        async with self.transaction():
            await self.loans_advances.delete(loan)
            await self.audit.record(
                org_id=org_id,
                module="settlements",
                sub_module="loan_advance",
                action_type=ActionType.DELETE,
                title="Delete Loan/Advance",
                description=f"Deleted loan/advance registry '{loan.name}' ({loan.id}).",
                performed_by_user_id=user_id,
                performed_by_name=f"User {user_id}",
                employee_id=loan.employee_id,
            )

    # =========================================================================
    # 2. Loan & Advance Ledger Transactions
    # =========================================================================

    async def add_loan_advance_transaction(
        self, org_id: int, loan_advance_id: int, data: dict[str, Any], user_id: int
    ) -> LoanAdvanceTransaction:
        """Add a manual transaction ledger entry to a loan/advance registry."""
        loan = await self.get_loan_advance(org_id, loan_advance_id)
        if loan.status == "closed":
            raise LoanAdvanceClosedException()

        amount = Decimal(str(data["amount"]))
        if amount <= 0:
            raise InvalidTransactionException("Transaction amount must be positive.")

        tx_type = getattr(data["transaction_type"], "value", data["transaction_type"])
        if tx_type not in ("credit", "debit"):
            raise InvalidTransactionException("Transaction type must be 'credit' or 'debit'.")

        async with self.transaction():
            # Update header totals
            if tx_type == "debit":
                if amount > loan.outstanding_amount:
                    raise InvalidTransactionException("Repayment exceeds outstanding exposure.")
                loan.outstanding_amount -= amount
                loan.total_debit = (loan.total_debit or Decimal("0.00")) + amount
                if loan.outstanding_amount == 0:
                    loan.status = "closed"
            else:
                loan.outstanding_amount += amount

            # Apply monthly installment revision if requested
            inst_amount = data.get("installment_amount")
            if inst_amount is not None:
                new_inst = Decimal(str(inst_amount))
                if new_inst <= 0 or new_inst > loan.principal_amount:
                    raise InvalidTransactionException("Invalid revised monthly installment amount.")
                loan.monthly_installment = new_inst

            loan.updated_by = user_id
            loan.updated_at = datetime.now()
            await self.loans_advances.update(loan, {})

            # Create ledger log
            tx = await self.loan_transactions.create(
                {
                    "org_id": org_id,
                    "loan_advance_id": loan_advance_id,
                    "employee_id": loan.employee_id,
                    "transaction_date": data["transaction_date"],
                    "transaction_type": tx_type,
                    "amount": amount,
                    "installment_amount": inst_amount,
                    "type_label": getattr(data["type_label"], "value", data["type_label"]),
                    "comment": data.get("comment"),
                    "source": "manual",
                    "created_by": user_id,
                }
            )

            await self.audit.record(
                org_id=org_id,
                module="settlements",
                sub_module="loan_transaction",
                action_type=ActionType.INSERT,
                title="Add Loan/Advance Transaction",
                description=(
                    f"Added {tx_type} transaction of {amount} "
                    f"to loan/advance '{loan.name}' ({loan.id})."
                ),
                performed_by_user_id=user_id,
                performed_by_name=f"User {user_id}",
                employee_id=loan.employee_id,
            )
            return tx

    async def list_loan_advance_transactions(
        self,
        org_id: int,
        loan_advance_id: int,
        query: LoanAdvanceTransactionSearchQuery,
    ) -> PaginatedResponse[LoanAdvanceTransaction]:
        """List and paginate ledger transactions for a loan/advance registry."""
        await self.get_loan_advance(org_id, loan_advance_id)

        items = await self.loan_transactions.search(
            loan_advance_id,
            transaction_type=(
                getattr(query.transaction_type, "value", query.transaction_type)
                if query.transaction_type
                else None
            ),
            source=getattr(query.source, "value", query.source) if query.source else None,
            date_from=query.date_from,
            date_to=query.date_to,
            sort_by=query.sort_by,
            sort_order=query.sort_order or SortOrder.DESC,
            page=query.page,
            page_size=query.page_size,
        )
        total = await self.loan_transactions.search_count(
            loan_advance_id,
            transaction_type=(
                getattr(query.transaction_type, "value", query.transaction_type)
                if query.transaction_type
                else None
            ),
            source=getattr(query.source, "value", query.source) if query.source else None,
            date_from=query.date_from,
            date_to=query.date_to,
        )
        return self.paginate(items, page=query.page, page_size=query.page_size, total_records=total)

    # =========================================================================
    # 3. Arrears (Headers)
    # =========================================================================

    async def get_employee_arrears(self, org_id: int, employee_id: int) -> EmployeeArrears:
        """Retrieve the arrears header details for an employee."""
        await self._validate_employee(org_id, employee_id)
        arrears = await self.arrears.get_by_employee_id(org_id, employee_id)
        if not arrears:
            raise ArrearsNotFoundException()
        return arrears

    async def list_employee_arrears(
        self, org_id: int, query: ArrearsSearchQuery
    ) -> PaginatedResponse[EmployeeArrears]:
        """List and paginate organization arrears registry headers."""
        items = await self.arrears.search(
            org_id,
            employee_id=query.employee_id,
            min_outstanding=query.min_outstanding,
            branch_id=query.branch_id,
            dept_id=query.dept_id,
            sort_by=query.sort_by,
            sort_order=query.sort_order or SortOrder.DESC,
            page=query.page,
            page_size=query.page_size,
        )
        total = await self.arrears.search_count(
            org_id,
            employee_id=query.employee_id,
            min_outstanding=query.min_outstanding,
            branch_id=query.branch_id,
            dept_id=query.dept_id,
        )
        return self.paginate(items, page=query.page, page_size=query.page_size, total_records=total)

    # =========================================================================
    # 4. Arrears Ledger Transactions
    # =========================================================================

    async def add_arrears_transaction(
        self, org_id: int, employee_id: int, data: dict[str, Any], user_id: int
    ) -> ArrearsTransaction:
        """Add a transaction ledger entry, auto-initializing arrears header if absent."""
        emp = await self._validate_employee(org_id, employee_id)

        amount = Decimal(str(data["amount"]))
        if amount <= 0:
            raise InvalidTransactionException("Transaction amount must be positive.")

        tx_type = getattr(data["transaction_type"], "value", data["transaction_type"])
        if tx_type not in ("credit", "debit"):
            raise InvalidTransactionException("Transaction type must be 'credit' or 'debit'.")

        async with self.transaction():
            # Get or create header
            arrears = await self.arrears.get_by_employee_id(org_id, employee_id)
            if arrears is None:
                arrears = await self.arrears.create(
                    {
                        "org_id": org_id,
                        "employee_id": employee_id,
                        "arrears_created": Decimal("0.00"),
                        "arrears_paid": Decimal("0.00"),
                        "outstanding_arrears": Decimal("0.00"),
                    }
                )

            outstanding_before = arrears.outstanding_arrears

            if tx_type == "credit":
                arrears.arrears_created += amount
                arrears.outstanding_arrears += amount
            else:
                if amount > arrears.outstanding_arrears:
                    raise InsufficientArrearsException()
                arrears.arrears_paid += amount
                arrears.outstanding_arrears -= amount

            outstanding_after = arrears.outstanding_arrears
            arrears.updated_at = datetime.now()
            await self.arrears.update(arrears, {})

            # Create transaction ledger log
            tx = await self.arrears_transactions.create(
                {
                    "org_id": org_id,
                    "employee_arrears_id": arrears.id,
                    "employee_id": employee_id,
                    "transaction_date": data["transaction_date"],
                    "transaction_type": tx_type,
                    "amount": amount,
                    "outstanding_before": outstanding_before,
                    "outstanding_after": outstanding_after,
                    "comment": data.get("comment"),
                    "source": "manual",
                    "created_by": user_id,
                }
            )

            await self.audit.record(
                org_id=org_id,
                module="settlements",
                sub_module="arrears_transaction",
                action_type=ActionType.INSERT,
                title="Add Arrears Transaction",
                description=(f"Added {tx_type} transaction of {amount} to employee arrears."),
                performed_by_user_id=user_id,
                performed_by_name=f"User {user_id}",
                employee_id=employee_id,
                employee_name=emp.employee_name,
            )
            return tx

    async def list_arrears_transactions(
        self, org_id: int, employee_id: int, query: ArrearsTransactionSearchQuery
    ) -> PaginatedResponse[ArrearsTransaction]:
        """List and paginate ledger transactions for employee arrears."""
        await self._validate_employee(org_id, employee_id)

        items = await self.arrears_transactions.search(
            employee_id,
            transaction_type=(
                getattr(query.transaction_type, "value", query.transaction_type)
                if query.transaction_type
                else None
            ),
            source=getattr(query.source, "value", query.source) if query.source else None,
            date_from=query.date_from,
            date_to=query.date_to,
            sort_by=query.sort_by,
            sort_order=query.sort_order or SortOrder.DESC,
            page=query.page,
            page_size=query.page_size,
        )
        total = await self.arrears_transactions.search_count(
            employee_id,
            transaction_type=(
                getattr(query.transaction_type, "value", query.transaction_type)
                if query.transaction_type
                else None
            ),
            source=getattr(query.source, "value", query.source) if query.source else None,
            date_from=query.date_from,
            date_to=query.date_to,
        )
        return self.paginate(items, page=query.page, page_size=query.page_size, total_records=total)

    # =========================================================================
    # 5. Combined Statement, History & Summary
    # =========================================================================

    async def get_settlement_history(
        self, org_id: int, employee_id: int, query: SettlementHistoryQuery
    ) -> PaginatedResponse[dict[str, Any]]:
        """Retrieve chronological combined transaction history."""
        await self._validate_employee(org_id, employee_id)

        items = await self.settlement_coords.get_combined_history(
            org_id,
            employee_id,
            date_from=query.date_from,
            date_to=query.date_to,
            source=getattr(query.source, "value", query.source) if query.source else None,
            page=query.page,
            page_size=query.page_size,
        )
        total = await self.settlement_coords.get_combined_history_count(
            org_id,
            employee_id,
            date_from=query.date_from,
            date_to=query.date_to,
            source=getattr(query.source, "value", query.source) if query.source else None,
        )
        return self.paginate(items, page=query.page, page_size=query.page_size, total_records=total)

    async def get_settlement_statement(
        self, org_id: int, employee_id: int, query: SettlementStatementQuery
    ) -> dict[str, Any]:
        """Compile a combined statement for the employee including outstanding amounts."""
        await self._validate_employee(org_id, employee_id)

        # 1. Fetch loan/advance registries
        stmt = (
            select(EmployeeLoanAdvance)
            .where(
                EmployeeLoanAdvance.org_id == org_id,
                EmployeeLoanAdvance.employee_id == employee_id,
            )
            .order_by(EmployeeLoanAdvance.transaction_date.desc())
        )
        loans_advances = list((await self.session.execute(stmt)).scalars().all())

        total_outstanding_loans = sum(
            loan_item.outstanding_amount
            for loan_item in loans_advances
            if loan_item.status == "active"
        )

        # 2. Fetch arrears header
        arrears = await self.arrears.get_by_employee_id(org_id, employee_id)
        total_outstanding_arrears = arrears.outstanding_arrears if arrears else Decimal("0.00")

        # 3. Fetch full combined history for the statement period
        ledger = await self.settlement_coords.get_combined_history(
            org_id,
            employee_id,
            date_from=query.date_from,
            date_to=query.date_to,
            page=1,
            page_size=10000,
        )

        return {
            "employee_id": employee_id,
            "org_id": org_id,
            "loans_advances": loans_advances,
            "total_outstanding_loans_advances": total_outstanding_loans,
            "arrears": arrears,
            "total_outstanding_arrears": total_outstanding_arrears,
            "statement_period_start": query.date_from,
            "statement_period_end": query.date_to,
            "ledger": ledger,
        }

    async def get_settlement_summary(
        self, org_id: int, query: SettlementSummaryQuery
    ) -> dict[str, Any]:
        """Retrieve organizational outstanding loans/advances and arrears aggregates."""
        if query.employee_id is not None:
            await self._validate_employee(org_id, query.employee_id)

        return await self.settlement_coords.get_employee_settlement_summary(
            org_id, employee_id=query.employee_id
        )

    # =========================================================================
    # 6. F&F Settlement, Approvals & Finalization
    # =========================================================================

    async def calculate_ff_settlement(self, org_id: int, employee_id: int) -> dict[str, Any]:
        """Perform dry-run calculations of employee net outstanding exposure."""
        await self._validate_employee(org_id, employee_id)

        summary = await self.settlement_coords.get_employee_settlement_summary(org_id, employee_id)
        outstanding_loans = summary["total_outstanding_loans_advances"]
        outstanding_arrears = summary["total_outstanding_arrears"]
        net_amount = outstanding_loans - outstanding_arrears

        return {
            "employee_id": employee_id,
            "outstanding_loans_advances": outstanding_loans,
            "outstanding_arrears": outstanding_arrears,
            "net_amount_due": net_amount,
            "currency": "INR",
            "status": "draft",
        }

    async def approve_ff_settlement(
        self, org_id: int, employee_id: int, user_id: int
    ) -> dict[str, Any]:
        """Record the approval of a Full & Final Settlement preview."""
        emp = await self._validate_ff_preconditions(org_id, employee_id)

        async with self.transaction():
            await self.audit.record(
                org_id=org_id,
                module="settlements",
                sub_module="approvals",
                action_type=ActionType.UPDATE,
                title="Approve F&F Settlement",
                description=(
                    f"Approved Full & Final Settlement calculations for employee {employee_id}."
                ),
                performed_by_user_id=user_id,
                performed_by_name=f"User {user_id}",
                employee_id=employee_id,
                employee_name=emp.employee_name,
            )

        return {
            "employee_id": employee_id,
            "status": "approved",
            "approved_by": user_id,
            "approved_at": utcnow(),
        }

    async def finalize_ff_settlement(
        self, org_id: int, employee_id: int, user_id: int
    ) -> dict[str, Any]:
        """Process and finalize Full & Final Settlement by settling outstanding ledgers."""
        emp = await self._validate_ff_preconditions(org_id, employee_id)

        async with self.transaction():
            # 1. Clear active loans/advances
            stmt = select(EmployeeLoanAdvance).where(
                EmployeeLoanAdvance.org_id == org_id,
                EmployeeLoanAdvance.employee_id == employee_id,
                EmployeeLoanAdvance.status == "active",
            )
            active_loans = list((await self.session.execute(stmt)).scalars().all())

            loans_cleared = []
            for loan in active_loans:
                amount_to_clear = loan.outstanding_amount
                if amount_to_clear > 0:
                    # Write transaction debit
                    await self.loan_transactions.create(
                        {
                            "org_id": org_id,
                            "loan_advance_id": loan.id,
                            "employee_id": employee_id,
                            "transaction_date": date.today(),
                            "transaction_type": "debit",
                            "amount": amount_to_clear,
                            "type_label": loan.type,
                            "source": "manual",
                            "created_by": user_id,
                            "comment": "Auto-repayment on Full & Final Settlement",
                        }
                    )
                    # Update loan header status
                    loan.outstanding_amount = Decimal("0.00")
                    loan.total_debit = (loan.total_debit or Decimal("0.00")) + amount_to_clear
                    loan.status = "closed"
                    loan.updated_by = user_id
                    loan.updated_at = datetime.now()
                    await self.loans_advances.update(loan, {})
                    loans_cleared.append(loan.id)

            # 2. Clear outstanding arrears
            arrears = await self.arrears.get_by_employee_id(org_id, employee_id)
            arrears_cleared_amount = Decimal("0.00")
            if arrears and arrears.outstanding_arrears > 0:
                arrears_cleared_amount = arrears.outstanding_arrears
                await self.arrears_transactions.create(
                    {
                        "org_id": org_id,
                        "employee_arrears_id": arrears.id,
                        "employee_id": employee_id,
                        "transaction_date": date.today(),
                        "transaction_type": "debit",
                        "amount": arrears_cleared_amount,
                        "outstanding_before": arrears_cleared_amount,
                        "outstanding_after": Decimal("0.00"),
                        "source": "manual",
                        "created_by": user_id,
                        "comment": "Arrears paid out on Full & Final Settlement",
                    }
                )
                arrears.arrears_paid += arrears_cleared_amount
                arrears.outstanding_arrears = Decimal("0.00")
                arrears.updated_at = utcnow()
                await self.arrears.update(arrears, {})

            # 3. Stamp the settlement as complete. This is the idempotency marker checked
            #    by _validate_ff_preconditions, written in the same transaction as the
            #    ledger debits above so the two can never disagree.
            emp.settlement_finalized_at = utcnow()
            emp.settlement_finalized_by = user_id
            self.session.add(emp)
            await self.session.flush()

            # 4. Log audit log
            await self.audit.record(
                org_id=org_id,
                module="settlements",
                sub_module="finalization",
                action_type=ActionType.UPDATE,
                title="Finalize F&F Settlement",
                description=(
                    f"Finalized F&F Settlement for employee {employee_id}. "
                    f"Cleared {len(loans_cleared)} active loans, "
                    f"paid out {arrears_cleared_amount} arrears."
                ),
                performed_by_user_id=user_id,
                performed_by_name=f"User {user_id}",
                employee_id=employee_id,
                employee_name=emp.employee_name,
            )

        return {
            "employee_id": employee_id,
            "loans_cleared_count": len(loans_cleared),
            "arrears_cleared_amount": arrears_cleared_amount,
            "status": "finalized",
        }
