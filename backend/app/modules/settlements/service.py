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
from sqlalchemy.orm import selectinload


def _parse_date(val: Any) -> date:
    if not val:
        return date.today()
    if isinstance(val, str):
        return date.fromisoformat(val)
    if isinstance(val, datetime):
        return val.date()
    return val

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
    LoanInstallmentSchedule,
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
    ArrearsTransactionSchema,
    ArrearsTransactionSearchQuery,
    EditInstallmentResponse,
    EmployeeArrearsListResponse,
    EmployeeArrearsSchema,
    LoanAdvanceSchema,
    LoanAdvanceSearchQuery,
    LoanAdvanceTransactionListResponse,
    LoanAdvanceTransactionSchema,
    LoanAdvanceTransactionSearchQuery,
    LoanEarlyClosureRequest,
    LoanInstallmentScheduleSchema,
    LoanRequestCreate,
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
                    "transaction_date": _parse_date(data.get("transaction_date")),
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
    ) -> PaginatedResponse[LoanAdvanceSchema]:
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
        # Enrich with Employee data
        emp_ids = list({item.employee_id for item in items if getattr(item, "employee_id", None)})
        emp_map: dict[int, dict[str, Any]] = {}
        if emp_ids:
            from app.modules.employee.models.organization import Branch, Department, Designation
            stmt_emp = (
                select(
                    Employee.employee_id,
                    Employee.employee_code,
                    Employee.employee_name,
                    Employee.display_name,
                    Branch.branch_name,
                    Department.dept_name,
                    Designation.designation_name,
                )
                .join(Branch, Employee.master_branch_id == Branch.branch_id, isouter=True)
                .join(Department, Employee.dept_id == Department.dept_id, isouter=True)
                .join(Designation, Employee.designation_id == Designation.designation_id, isouter=True)
                .where(Employee.org_id == org_id, Employee.employee_id.in_(emp_ids))
            )
            rows = (await self.session.execute(stmt_emp)).all()
            for r in rows:
                emp_map[r[0]] = {
                    "code": r[1] or str(r[0]),
                    "name": r[2] or r[3] or f"Employee #{r[0]}",
                    "branch": r[4] or None,
                    "dept": r[5] or None,
                    "desig": r[6] or None,
                }

        enriched: list[LoanAdvanceSchema] = []
        for item in items:
            s = LoanAdvanceSchema.model_validate(item)
            info = emp_map.get(item.employee_id)
            if info:
                s.employee_code = info["code"]
                s.employee_name = info["name"]
                s.branch_name = info["branch"]
                s.department_name = info["dept"]
                s.designation_name = info["desig"]
            else:
                s.employee_code = f"EMP-{item.employee_id}"
                s.employee_name = f"Employee #{item.employee_id}"
            enriched.append(s)

        return self.paginate(enriched, page=query.page, page_size=query.page_size, total_records=total)

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
            if loan.status == "closed":
                raise LoanAdvanceClosedException("Cannot edit installment for a closed loan.")
            out_amt = (
                loan.outstanding_amount
                if loan.outstanding_amount is not None
                else (loan.principal_amount if loan.principal_amount is not None else Decimal("0"))
            )
            if out_amt <= 0:
                raise InvalidTransactionException("Loan already completed. Cannot edit installment.")
            if installment > out_amt:
                raise InvalidTransactionException(
                    f"Monthly installment cannot exceed outstanding amount ({out_amt})."
                )
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

    async def update_installment(
        self,
        org_id: int,
        loan_advance_id: int,
        installment_amount: Decimal,
        user_id: int,
        comment: str | None = None,
    ) -> EditInstallmentResponse:
        """Update the monthly installment amount for an active loan/advance and create transaction log."""
        loan = await self.get_loan_advance(org_id, loan_advance_id)

        # 1. Validate loan status is Active
        if loan.status != "active":
            raise LoanAdvanceClosedException("Cannot edit installment for a closed or inactive loan.")

        # 2. Validate Outstanding Amount > 0
        if loan.outstanding_amount <= 0:
            raise InvalidTransactionException("Loan already completed. Outstanding amount is zero.")

        # 3. Validate New installment > 0
        if installment_amount <= 0:
            raise InvalidTransactionException("New installment amount must be greater than zero.")

        # 4. Validate New installment <= Outstanding Amount
        if installment_amount > loan.outstanding_amount:
            raise InvalidTransactionException(
                f"New installment amount ({installment_amount}) cannot exceed remaining outstanding balance ({loan.outstanding_amount})."
            )

        old_installment = loan.monthly_installment

        updates: dict[str, Any] = {
            "monthly_installment": installment_amount,
            "updated_by": user_id,
            "updated_at": datetime.now(),
        }

        async with self.transaction():
            updated = await self.loans_advances.update(loan, updates)

            # Create Transaction Entry for INSTALLMENT_UPDATED
            remarks_text = f"Installment updated from {old_installment} to {installment_amount}."
            if comment:
                remarks_text += f" Remarks: {comment}"

            await self.loan_transactions.create(
                {
                    "org_id": org_id,
                    "loan_advance_id": loan_advance_id,
                    "employee_id": loan.employee_id,
                    "transaction_date": date.today(),
                    "transaction_type": "debit",
                    "amount": Decimal("0.00"),
                    "installment_amount": installment_amount,
                    "type_label": getattr(loan.type, "value", loan.type),
                    "comment": remarks_text,
                    "source": "manual",
                    "created_by": user_id,
                }
            )

            await self.audit.record(
                org_id=org_id,
                module="settlements",
                sub_module="loan_installment",
                action_type=ActionType.UPDATE,
                title="Update Loan Installment",
                description=(
                    f"Updated monthly installment for loan '{loan.name}' ({loan.id}) "
                    f"from {old_installment} to {installment_amount}."
                ),
                performed_by_user_id=user_id,
                performed_by_name=f"User {user_id}",
                employee_id=loan.employee_id,
            )
            return EditInstallmentResponse(
                loan_id=updated.id,
                old_installment=old_installment,
                new_installment=installment_amount,
                outstanding_amount=updated.outstanding_amount,
                status=str(updated.status).upper(),
            )

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
                    raise InvalidTransactionException("Debit amount exceeds current outstanding amount.")
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
                    "transaction_date": _parse_date(data.get("transaction_date")),
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

    async def list_all_loan_transactions(
        self,
        org_id: int,
        query: LoanAdvanceTransactionSearchQuery,
        employee_id: int | None = None,
        loan_id: int | None = None,
    ) -> LoanAdvanceTransactionListResponse:
        """List and paginate ledger transactions for loans/advances with summary totals."""
        total_amt = Decimal("0.00")
        outstanding_amt = Decimal("0.00")

        if loan_id:
            try:
                loan = await self.get_loan_advance(org_id, loan_id)
                total_amt = loan.principal_amount or Decimal("0.00")
                outstanding_amt = loan.outstanding_amount or Decimal("0.00")
                if not employee_id:
                    employee_id = loan.employee_id
            except Exception:
                pass
        elif employee_id:
            loans = await self.loans_advances.get_all_by_employee_id(org_id, employee_id)
            for ln in loans:
                total_amt += ln.principal_amount or Decimal("0.00")
                outstanding_amt += ln.outstanding_amount or Decimal("0.00")

        items = await self.loan_transactions.search_all_transactions(
            org_id,
            employee_id=employee_id,
            loan_advance_id=loan_id,
            transaction_type=(
                getattr(query.transaction_type, "value", query.transaction_type)
                if query.transaction_type
                else None
            ),
            source=getattr(query.source, "value", query.source) if query.source else None,
            date_from=query.date_from,
            date_to=query.date_to,
            branch_id=query.branch_id,
            sort_by=query.sort_by,
            sort_order=query.sort_order or SortOrder.DESC,
            page=query.page,
            page_size=query.page_size,
        )
        total = await self.loan_transactions.search_all_transactions_count(
            org_id,
            employee_id=employee_id,
            loan_advance_id=loan_id,
            transaction_type=(
                getattr(query.transaction_type, "value", query.transaction_type)
                if query.transaction_type
                else None
            ),
            source=getattr(query.source, "value", query.source) if query.source else None,
            date_from=query.date_from,
            date_to=query.date_to,
            branch_id=query.branch_id,
        )
        emp_ids = {tx.employee_id for tx in items if tx.employee_id}
        emp_map: dict[int, Employee] = {}
        if emp_ids:
            stmt_emp = select(Employee).where(
                Employee.org_id == org_id, Employee.employee_id.in_(emp_ids)
            )
            emps = (await self.session.execute(stmt_emp)).scalars().all()
            emp_map = {e.employee_id: e for e in emps}

        schema_items = []
        for tx in items:
            s = LoanAdvanceTransactionSchema.model_validate(tx)
            emp = emp_map.get(tx.employee_id)
            if emp:
                s.employee_name = emp.employee_name or emp.display_name or f"Employee #{tx.employee_id}"
                s.employee_code = emp.employee_code or f"EMP-{tx.employee_id}"
            else:
                s.employee_name = f"Employee #{tx.employee_id}"
                s.employee_code = f"EMP-{tx.employee_id}"
            schema_items.append(s)

        paginated = self.paginate(schema_items, page=query.page, page_size=query.page_size, total_records=total)
        return LoanAdvanceTransactionListResponse(
            items=paginated.items,
            pagination=paginated.pagination,
            total_amount=total_amt,
            outstanding_amount=outstanding_amt,
        )

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

    async def get_arrears_by_id(self, org_id: int, arrears_id: int) -> EmployeeArrears:
        """Retrieve an arrears header record by its primary key ID."""
        arrears = await self.arrears.get_by_id(arrears_id)
        if not arrears or arrears.org_id != org_id:
            raise ArrearsNotFoundException()
        return arrears

    async def list_employee_arrears(
        self, org_id: int, query: ArrearsSearchQuery
    ) -> EmployeeArrearsListResponse:
        """List and paginate organization arrears registry headers, enriched with employee details."""
        items = await self.arrears.search(
            org_id,
            employee_id=query.employee_id,
            min_outstanding=query.min_outstanding,
            branch_id=query.branch_id,
            dept_id=query.dept_id,
            search=query.search,
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
            search=query.search,
        )

        # Enrich with Employee data
        emp_ids = {item.employee_id for item in items if hasattr(item, "employee_id")}
        emp_map: dict[int, Employee] = {}
        if emp_ids:
            stmt_emp = (
                select(Employee)
                .where(Employee.org_id == org_id, Employee.employee_id.in_(emp_ids))
                .options(
                    selectinload(Employee.master_branch),
                    selectinload(Employee.department),
                    selectinload(Employee.designation),
                )
            )
            emps = (await self.session.execute(stmt_emp)).scalars().all()
            emp_map = {e.employee_id: e for e in emps}

        schema_items: list[Any] = []
        for arrear in items:
            if isinstance(arrear, str):
                schema_items.append(arrear)
                continue
            s = EmployeeArrearsSchema.model_validate(arrear)
            emp = emp_map.get(arrear.employee_id)
            if emp:
                s.employee_code = emp.employee_code
                s.employee_name = emp.employee_name
                s.branch_name = emp.master_branch.branch_name if emp.master_branch else None
                s.department_name = emp.department.dept_name if emp.department else None
                s.designation_name = emp.designation.designation_name if emp.designation else None
            else:
                s.employee_code = f"EMP-{arrear.employee_id}"
                s.employee_name = f"Employee #{arrear.employee_id}"
            schema_items.append(s)

        paginated = self.paginate(schema_items, page=query.page, page_size=query.page_size, total_records=total)
        return EmployeeArrearsListResponse(
            items=paginated.items,
            pagination=paginated.pagination,
        )

    async def create_arrears(
        self, org_id: int, data: dict[str, Any], user_id: int
    ) -> EmployeeArrears:
        """Create a new employee arrears entry and post credit transaction."""
        employee_id = data["employee_id"]
        emp = await self._validate_employee(org_id, employee_id)

        amount = Decimal(str(data["amount"]))
        if amount <= 0:
            raise InvalidTransactionException("Arrears amount must be positive.")

        async with self.transaction():
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
            arrears.arrears_created += amount
            arrears.outstanding_arrears += amount
            outstanding_after = arrears.outstanding_arrears
            arrears.updated_at = datetime.now()
            await self.arrears.update(arrears, {})

            # Record credit ledger transaction
            await self.arrears_transactions.create(
                {
                    "org_id": org_id,
                    "employee_arrears_id": arrears.id,
                    "employee_id": employee_id,
                    "transaction_date": _parse_date(data.get("transaction_date")),
                    "transaction_type": "credit",
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
                sub_module="arrears",
                action_type=ActionType.INSERT,
                title="Create Arrears Entry",
                description=f"Created arrears entry of {amount} for employee {emp.employee_name}.",
                performed_by_user_id=user_id,
                performed_by_name=f"User {user_id}",
                employee_id=employee_id,
                employee_name=emp.employee_name,
            )

            return arrears

    async def update_arrears(
        self, org_id: int, arrears_id: int, data: dict[str, Any], user_id: int
    ) -> EmployeeArrears:
        """Update fields of an arrears header record."""
        arrears = await self.get_arrears_by_id(org_id, arrears_id)
        emp = await self._validate_employee(org_id, arrears.employee_id)

        updates: dict[str, Any] = {"updated_at": datetime.now()}

        if "amount" in data and data["amount"] is not None:
            new_amount = Decimal(str(data["amount"]))
            if new_amount <= 0:
                raise InvalidTransactionException("Arrears amount must be positive.")
            diff = new_amount - arrears.arrears_created
            arrears.arrears_created = new_amount
            arrears.outstanding_arrears = max(Decimal("0.00"), arrears.outstanding_arrears + diff)

        async with self.transaction():
            updated = await self.arrears.update(arrears, updates)
            await self.audit.record(
                org_id=org_id,
                module="settlements",
                sub_module="arrears",
                action_type=ActionType.UPDATE,
                title="Update Arrears",
                description=f"Updated arrears record #{arrears_id}.",
                performed_by_user_id=user_id,
                performed_by_name=f"User {user_id}",
                employee_id=arrears.employee_id,
                employee_name=emp.employee_name,
            )
            return updated

    async def delete_arrears(self, org_id: int, arrears_id: int, user_id: int) -> None:
        """Delete an arrears header record."""
        arrears = await self.get_arrears_by_id(org_id, arrears_id)
        emp = await self._validate_employee(org_id, arrears.employee_id)

        async with self.transaction():
            await self.arrears.delete(arrears)
            await self.audit.record(
                org_id=org_id,
                module="settlements",
                sub_module="arrears",
                action_type=ActionType.DELETE,
                title="Delete Arrears",
                description=f"Deleted arrears record #{arrears_id}.",
                performed_by_user_id=user_id,
                performed_by_name=f"User {user_id}",
                employee_id=arrears.employee_id,
                employee_name=emp.employee_name,
            )

    async def pay_arrears(
        self, org_id: int, arrears_id: int, data: dict[str, Any], user_id: int
    ) -> ArrearsTransaction:
        """Process payment (debit transaction) against an arrears record."""
        arrears = await self.get_arrears_by_id(org_id, arrears_id)
        emp = await self._validate_employee(org_id, arrears.employee_id)

        amount = Decimal(str(data["amount"]))
        if amount <= 0:
            raise InvalidTransactionException("Payment amount must be positive.")
        if amount > arrears.outstanding_arrears:
            raise InsufficientArrearsException()

        async with self.transaction():
            outstanding_before = arrears.outstanding_arrears
            arrears.arrears_paid += amount
            arrears.outstanding_arrears -= amount
            outstanding_after = arrears.outstanding_arrears
            arrears.updated_at = datetime.now()
            await self.arrears.update(arrears, {})

            tx = await self.arrears_transactions.create(
                {
                    "org_id": org_id,
                    "employee_arrears_id": arrears.id,
                    "employee_id": arrears.employee_id,
                    "transaction_date": _parse_date(data.get("transaction_date")),
                    "transaction_type": "debit",
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
                sub_module="arrears_payment",
                action_type=ActionType.INSERT,
                title="Pay Arrears",
                description=f"Paid {amount} towards arrears for employee {emp.employee_name}.",
                performed_by_user_id=user_id,
                performed_by_name=f"User {user_id}",
                employee_id=arrears.employee_id,
                employee_name=emp.employee_name,
            )

            return tx

    async def list_all_arrears_transactions(
        self, org_id: int, query: ArrearsTransactionSearchQuery
    ) -> PaginatedResponse[ArrearsTransaction]:
        """Retrieve org-wide arrears activity/transaction logs."""
        items = await self.arrears_transactions.search_all_transactions(
            org_id,
            employee_id=query.employee_id,
            transaction_type=(
                getattr(query.transaction_type, "value", query.transaction_type)
                if query.transaction_type
                else None
            ),
            source=getattr(query.source, "value", query.source) if query.source else None,
            date_from=query.date_from,
            date_to=query.date_to,
            search=query.search,
            sort_by=query.sort_by,
            sort_order=query.sort_order or SortOrder.DESC,
            page=query.page,
            page_size=query.page_size,
        )
        total = await self.arrears_transactions.search_all_transactions_count(
            org_id,
            employee_id=query.employee_id,
            transaction_type=(
                getattr(query.transaction_type, "value", query.transaction_type)
                if query.transaction_type
                else None
            ),
            source=getattr(query.source, "value", query.source) if query.source else None,
            date_from=query.date_from,
            date_to=query.date_to,
            search=query.search,
        )
        emp_ids = {tx.employee_id for tx in items if getattr(tx, "employee_id", None)}
        emp_map: dict[int, Employee] = {}
        if emp_ids:
            stmt_emp = select(Employee).where(
                Employee.org_id == org_id, Employee.employee_id.in_(emp_ids)
            )
            emps = (await self.session.execute(stmt_emp)).scalars().all()
            emp_map = {e.employee_id: e for e in emps}

        schema_items = []
        for tx in items:
            s = ArrearsTransactionSchema.model_validate(tx)
            emp = emp_map.get(tx.employee_id)
            if emp:
                s.employee_name = emp.employee_name or emp.display_name or f"Employee #{tx.employee_id}"
                s.employee_code = emp.employee_code or f"EMP-{tx.employee_id}"
            else:
                s.employee_name = f"Employee #{tx.employee_id}"
                s.employee_code = f"EMP-{tx.employee_id}"
            schema_items.append(s)

        return self.paginate(schema_items, page=query.page, page_size=query.page_size, total_records=total)

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
                    "transaction_date": _parse_date(data.get("transaction_date")),
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

    # =========================================================================
    # Enterprise Loan & Advance Management
    # =========================================================================

    async def request_loan(
        self,
        *,
        org_id: int,
        employee_id: int,
        user_id: int,
        data: LoanRequestCreate,
    ) -> EmployeeLoanAdvance:
        """Create a new loan application in pending_approval state."""
        await self._validate_employee(org_id, employee_id)

        p = data.principal_amount
        r = (data.interest_rate / Decimal("100.0")) / Decimal("12.0")
        n = Decimal(str(data.tenure_months))
        if data.interest_type == "reducing" and r > 0:
            term = (Decimal("1.0") + r) ** int(data.tenure_months)
            monthly_inst = (p * r * term) / (term - Decimal("1.0"))
        else:
            total_interest = p * (data.interest_rate / Decimal("100.0")) * (n / Decimal("12.0"))
            monthly_inst = (p + total_interest) / n

        monthly_inst = monthly_inst.quantize(Decimal("0.01"))

        async with self.transaction():
            loan = EmployeeLoanAdvance(
                org_id=org_id,
                employee_id=employee_id,
                name=data.name,
                type="loan",
                category=data.category,
                principal_amount=p,
                interest_rate=data.interest_rate,
                interest_type=data.interest_type,
                tenure_months=data.tenure_months,
                monthly_installment=monthly_inst,
                total_debit=Decimal("0.00"),
                outstanding_amount=p,
                transaction_date=date.today(),
                approval_status="pending_approval",
                status="active",
                comment=data.comment,
                created_by=user_id,
            )
            self.session.add(loan)
            await self.session.flush()

            await self.audit.record(
                org_id=org_id,
                module="settlements",
                sub_module="loans",
                action_type=ActionType.UPDATE,
                title="Loan Request Submitted",
                description=f"Submitted {data.category} request of amount {p} for employee #{employee_id}.",
                performed_by_user_id=user_id,
                performed_by_name=f"User #{user_id}",
                employee_id=employee_id,
            )

            try:
                from app.modules.notifications.service import NotificationService
                await NotificationService(self.session).dispatch(
                    org_id=org_id,
                    event_type="LOAN_REQUESTED",
                    recipient_user_ids=[user_id],
                    context_data={"loan_id": loan.id, "amount": str(p), "category": data.category},
                )
            except Exception:
                pass
        return loan

    async def disburse_loan(
        self,
        *,
        org_id: int,
        loan_id: int,
        user_id: int,
    ) -> EmployeeLoanAdvance:
        """Disburse loan and generate monthly installment schedule."""
        loan = await self.loans_advances.get_by_id(org_id, loan_id)
        if loan is None:
            raise LoanAdvanceNotFoundException()

        async with self.transaction():
            loan.approval_status = "disbursed"
            loan.status = "active"
            loan.disbursed_at = utcnow()
            loan.updated_by = user_id

            txn = LoanAdvanceTransaction(
                org_id=org_id,
                loan_advance_id=loan.id,
                employee_id=loan.employee_id,
                transaction_date=date.today(),
                transaction_type="debit",
                amount=loan.principal_amount,
                type_label=loan.type,
                comment="Initial loan disbursement",
                source="manual",
                created_by=user_id,
            )
            self.session.add(txn)
            loan.total_debit += loan.principal_amount

            start_date = date.today()
            inst_amount = loan.monthly_installment
            for i in range(1, loan.tenure_months + 1):
                month_offset = i
                due_year = start_date.year + (start_date.month + month_offset - 1) // 12
                due_month = (start_date.month + month_offset - 1) % 12 + 1
                due_d = date(due_year, due_month, min(start_date.day, 28))

                sch = LoanInstallmentSchedule(
                    org_id=org_id,
                    loan_advance_id=loan.id,
                    installment_number=i,
                    due_date=due_d,
                    principal_amount=inst_amount,
                    interest_amount=Decimal("0.00"),
                    total_installment=inst_amount,
                    status="pending",
                )
                self.session.add(sch)

            await self.audit.record(
                org_id=org_id,
                module="settlements",
                sub_module="loans",
                action_type=ActionType.UPDATE,
                title="Loan Disbursed",
                description=f"Disbursed loan #{loan_id} of amount {loan.principal_amount}.",
                performed_by_user_id=user_id,
                performed_by_name=f"User #{user_id}",
                employee_id=loan.employee_id,
            )

            try:
                from app.modules.notifications.service import NotificationService
                await NotificationService(self.session).dispatch(
                    org_id=org_id,
                    event_type="LOAN_DISBURSED",
                    recipient_user_ids=[user_id],
                    context_data={"loan_id": loan.id, "amount": str(loan.principal_amount)},
                )
            except Exception:
                pass
        return loan

    async def early_closure(
        self,
        *,
        org_id: int,
        loan_id: int,
        user_id: int,
        data: LoanEarlyClosureRequest,
    ) -> EmployeeLoanAdvance:
        """Settle loan balance early and mark loan closed."""
        loan = await self.loans_advances.get_by_id(org_id, loan_id)
        if loan is None:
            raise LoanAdvanceNotFoundException()

        async with self.transaction():
            txn = LoanAdvanceTransaction(
                org_id=org_id,
                loan_advance_id=loan.id,
                employee_id=loan.employee_id,
                transaction_date=date.today(),
                transaction_type="credit",
                amount=data.payoff_amount + data.discount_amount,
                type_label=loan.type,
                comment=f"Early loan payoff: Paid {data.payoff_amount}, Discount {data.discount_amount}. {data.comment or ''}",
                source="manual",
                created_by=user_id,
            )
            self.session.add(txn)

            loan.outstanding_amount = Decimal("0.00")
            loan.status = "closed"
            loan.approval_status = "closed"
            loan.updated_by = user_id

            stmt = select(LoanInstallmentSchedule).where(
                LoanInstallmentSchedule.loan_advance_id == loan.id,
                LoanInstallmentSchedule.status == "pending",
            )
            schedules = (await self.session.execute(stmt)).scalars().all()
            for sch in schedules:
                sch.status = "paid"

            await self.audit.record(
                org_id=org_id,
                module="settlements",
                sub_module="loans",
                action_type=ActionType.UPDATE,
                title="Loan Early Closure",
                description=f"Early closed loan #{loan_id} with payoff of {data.payoff_amount}.",
                performed_by_user_id=user_id,
                performed_by_name=f"User #{user_id}",
                employee_id=loan.employee_id,
            )
        return loan

    async def get_loan_schedules(
        self,
        *,
        org_id: int,
        loan_id: int,
    ) -> list[LoanInstallmentScheduleSchema]:
        """Fetch installment schedule for a loan."""
        stmt = (
            select(LoanInstallmentSchedule)
            .where(
                LoanInstallmentSchedule.org_id == org_id,
                LoanInstallmentSchedule.loan_advance_id == loan_id,
            )
            .order_by(LoanInstallmentSchedule.installment_number.asc())
        )
        schedules = (await self.session.execute(stmt)).scalars().all()
        return [
            LoanInstallmentScheduleSchema(
                id=s.id,
                installment_number=s.installment_number,
                due_date=s.due_date,
                principal_amount=s.principal_amount,
                interest_amount=s.interest_amount,
                total_installment=s.total_installment,
                status=s.status,
            )
            for s in schedules
        ]
