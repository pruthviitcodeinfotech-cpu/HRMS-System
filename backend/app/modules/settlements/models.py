"""Settlements — ORM models (Loan & Advance, Arrears).

Tables OWNED by this module (all keys BIGINT per project-wide PK convention):
    * employee_loans_advances  (loan/advance header)
    * loan_advance_transactions (loan/advance debit-credit ledger)
    * employee_arrears         (arrears header, one per employee per org)
    * arrears_transactions     (arrears ledger)

NOT implemented: `settlement_logs_view` — the approved architecture describes it
as a derived UNION view over the two transaction tables but does NOT define its
SQL; per the SQL rules it is not invented here (see the module migration note).

ENUM(...) columns from the PDF are implemented as VARCHAR + CHECK to match the
project-wide convention (values preserved exactly). See constants.py.

Intra-module FKs (enforced, RESTRICT on delete per the architecture):
    * loan_advance_transactions.loan_advance_id -> employee_loans_advances
    * arrears_transactions.employee_arrears_id   -> employee_arrears
DEFERRED cross-module FKs (columns only, constraints deferred):
    * org_id -> organizations : the built `organizations` table uses PK
      `org_id` (BIGINT); FK constraint deferred pending cross-module wiring.
    * employee_id -> employees : built `employees` uses PK `employee_id`
      (BIGINT); FK constraint deferred pending cross-module wiring.
    * created_by / updated_by -> users (User Management, not yet built).
    * payroll_run_id -> Payroll : the approved schema states the target
      ambiguously ("payroll_computed_rows.id or a payroll run table"); deferred
      until the exact target is confirmed. Column created as BIGINT.
"""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database.base import Base


class EmployeeLoanAdvance(Base):
    __tablename__ = "employee_loans_advances"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    org_id: Mapped[int] = mapped_column(BigInteger, nullable=False)  # deferred FK -> organizations
    employee_id: Mapped[int] = mapped_column(BigInteger, nullable=False)  # deferred FK -> employees
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    type: Mapped[str] = mapped_column(String(20), nullable=False, server_default=text("'loan'"))
    principal_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    monthly_installment: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    total_debit: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, server_default=text("0.00")
    )
    outstanding_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    transaction_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default=text("'active'"))
    comment: Mapped[str | None] = mapped_column(Text)
    # DEFERRED cross-module FKs -> users.id
    created_by: Mapped[int] = mapped_column(BigInteger, nullable=False)
    updated_by: Mapped[int | None] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )

    __table_args__ = (
        CheckConstraint("type IN ('loan', 'advance')", name="ck_employee_loans_advances_type"),
        CheckConstraint(
            "status IN ('active', 'closed')", name="ck_employee_loans_advances_status"
        ),
        CheckConstraint("principal_amount > 0", name="ck_employee_loans_advances_principal_amount"),
        CheckConstraint(
            "monthly_installment > 0", name="ck_employee_loans_advances_monthly_installment"
        ),
        CheckConstraint("total_debit >= 0", name="ck_employee_loans_advances_total_debit"),
        CheckConstraint(
            "outstanding_amount >= 0", name="ck_employee_loans_advances_outstanding_amount"
        ),
    )

    transactions: Mapped[list["LoanAdvanceTransaction"]] = relationship(
        back_populates="loan_advance"
    )


class LoanAdvanceTransaction(Base):
    __tablename__ = "loan_advance_transactions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    org_id: Mapped[int] = mapped_column(BigInteger, nullable=False)  # deferred FK -> organizations
    loan_advance_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "employee_loans_advances.id",
            name="fk_loan_adv_txns_loan_advance_id_employee_loans_advances",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    employee_id: Mapped[int] = mapped_column(BigInteger, nullable=False)  # deferred FK -> employees
    transaction_date: Mapped[date] = mapped_column(Date, nullable=False)
    transaction_type: Mapped[str] = mapped_column(String(10), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    installment_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    type_label: Mapped[str] = mapped_column(String(20), nullable=False)
    comment: Mapped[str | None] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(10), nullable=False, server_default=text("'manual'"))
    # DEFERRED cross-module FK -> Payroll (ambiguous target)
    payroll_run_id: Mapped[int | None] = mapped_column(BigInteger)
    # DEFERRED cross-module FK -> users.id
    created_by: Mapped[int] = mapped_column(BigInteger, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )

    __table_args__ = (
        Index(
            "ix_loan_advance_transactions_employee_id_transaction_date",
            "employee_id",
            "transaction_date",
        ),
        Index(
            "ix_loan_advance_transactions_org_id_transaction_date_type_label",
            "org_id",
            "transaction_date",
            "type_label",
        ),
        CheckConstraint(
            "transaction_type IN ('credit', 'debit')",
            name="ck_loan_advance_transactions_transaction_type",
        ),
        CheckConstraint(
            "type_label IN ('loan', 'advance')", name="ck_loan_advance_transactions_type_label"
        ),
        CheckConstraint(
            "source IN ('manual', 'payroll')", name="ck_loan_advance_transactions_source"
        ),
    )

    loan_advance: Mapped["EmployeeLoanAdvance"] = relationship(back_populates="transactions")


class EmployeeArrears(Base):
    __tablename__ = "employee_arrears"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    org_id: Mapped[int] = mapped_column(BigInteger, nullable=False)  # deferred FK -> organizations
    employee_id: Mapped[int] = mapped_column(BigInteger, nullable=False)  # deferred FK -> employees
    arrears_created: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, server_default=text("0.00")
    )
    arrears_paid: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, server_default=text("0.00")
    )
    outstanding_arrears: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, server_default=text("0.00")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )

    __table_args__ = (
        UniqueConstraint("org_id", "employee_id", name="uq_employee_arrears_org_id_employee_id"),
        CheckConstraint("arrears_created >= 0", name="ck_employee_arrears_arrears_created"),
        CheckConstraint("arrears_paid >= 0", name="ck_employee_arrears_arrears_paid"),
        CheckConstraint(
            "outstanding_arrears >= 0", name="ck_employee_arrears_outstanding_arrears"
        ),
    )

    transactions: Mapped[list["ArrearsTransaction"]] = relationship(
        back_populates="employee_arrears"
    )


class ArrearsTransaction(Base):
    __tablename__ = "arrears_transactions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    org_id: Mapped[int] = mapped_column(BigInteger, nullable=False)  # deferred FK -> organizations
    employee_arrears_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "employee_arrears.id",
            name="fk_arrears_transactions_employee_arrears_id_employee_arrears",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    employee_id: Mapped[int] = mapped_column(BigInteger, nullable=False)  # deferred FK -> employees
    transaction_date: Mapped[date] = mapped_column(Date, nullable=False)
    transaction_type: Mapped[str] = mapped_column(String(10), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    outstanding_before: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    outstanding_after: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    comment: Mapped[str | None] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(10), nullable=False, server_default=text("'manual'"))
    # DEFERRED cross-module FK -> Payroll (ambiguous target)
    payroll_run_id: Mapped[int | None] = mapped_column(BigInteger)
    # DEFERRED cross-module FK -> users.id
    created_by: Mapped[int] = mapped_column(BigInteger, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )

    __table_args__ = (
        Index(
            "ix_arrears_transactions_employee_id_transaction_date",
            "employee_id",
            "transaction_date",
        ),
        Index(
            "ix_arrears_transactions_org_id_transaction_date", "org_id", "transaction_date"
        ),
        CheckConstraint(
            "transaction_type IN ('credit', 'debit')",
            name="ck_arrears_transactions_transaction_type",
        ),
        CheckConstraint(
            "source IN ('manual', 'payroll')", name="ck_arrears_transactions_source"
        ),
    )

    employee_arrears: Mapped["EmployeeArrears"] = relationship(back_populates="transactions")
