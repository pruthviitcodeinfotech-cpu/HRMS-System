"""Payroll — computed rows and finalized runs.

Tables: finalized_payroll_runs, payroll_computed_rows.

Implements the approved Payroll Database Architecture exactly (BIGINT `id`).

Intra-module FKs (enforced):
    * payroll_computed_rows.payroll_group_id  -> payroll_groups
    * payroll_computed_rows.finalized_run_id  -> finalized_payroll_runs
    * finalized_payroll_runs.payroll_group_id -> payroll_groups
DEFERRED cross-module FKs (columns only):
    * employee_id -> employees (see settings.py module docstring)
    * computed_by / finalized_by / definalized_by -> users (User Management)
"""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    SmallInteger,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database.base import Base


class FinalizedPayrollRun(Base):
    __tablename__ = "finalized_payroll_runs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    org_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    payroll_group_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("payroll_groups.id", name="fk_finalized_payroll_runs_payroll_group_id_payroll_groups"),
        nullable=False,
    )
    cycle_from: Mapped[date] = mapped_column(Date, nullable=False)
    cycle_to: Mapped[date] = mapped_column(Date, nullable=False)
    payroll_module: Mapped[str] = mapped_column(String(30), nullable=False)
    finalized_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    finalized_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    # DEFERRED cross-module FK -> users.id (NOT NULL per the architecture)
    finalized_by: Mapped[int] = mapped_column(BigInteger, nullable=False)
    paid_amount: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    payment_status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'pending'")
    )
    is_definalized: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    definalized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # DEFERRED cross-module FK -> users.id
    definalized_by: Mapped[int | None] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )

    __table_args__ = (
        Index(
            "ix_finalized_payroll_runs_org_id_payroll_group_id_cycle_from",
            "org_id",
            "payroll_group_id",
            "cycle_from",
        ),
        CheckConstraint(
            "payment_status IN ('pending', 'paid', 'partial')",
            name="ck_finalized_payroll_runs_payment_status",
        ),
    )

    payroll_group: Mapped["PayrollGroup"] = relationship(back_populates="finalized_runs")  # noqa: F821
    computed_rows: Mapped[list["PayrollComputedRow"]] = relationship(back_populates="finalized_run")


class PayrollComputedRow(Base):
    __tablename__ = "payroll_computed_rows"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    payroll_group_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("payroll_groups.id", name="fk_payroll_computed_rows_payroll_group_id_payroll_groups"),
        nullable=False,
    )
    # DEFERRED cross-module FK -> employees
    employee_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    cycle_from: Mapped[date] = mapped_column(Date, nullable=False)
    cycle_to: Mapped[date] = mapped_column(Date, nullable=False)
    total_days: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    full_day_count: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default=text("0"))
    half_day_count: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default=text("0"))
    off_day_count: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default=text("0"))
    paid_leave_count: Mapped[Decimal] = mapped_column(
        Numeric(5, 1), nullable=False, server_default=text("0")
    )
    paid_day_count: Mapped[Decimal] = mapped_column(
        Numeric(5, 1), nullable=False, server_default=text("0")
    )
    unpaid_day_count: Mapped[Decimal] = mapped_column(
        Numeric(5, 1), nullable=False, server_default=text("0")
    )
    daily_wage: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False, server_default=text("0")
    )
    gross_wages: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, server_default=text("0")
    )
    overtime_amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False, server_default=text("0")
    )
    penalties_amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False, server_default=text("0")
    )
    extras_amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False, server_default=text("0")
    )
    gross_earnings: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, server_default=text("0")
    )
    loan_advance_deduction: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False, server_default=text("0")
    )
    arrears_amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False, server_default=text("0")
    )
    to_pay: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, server_default=text("0"))
    balance_arrears: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False, server_default=text("0")
    )
    payment_method: Mapped[str | None] = mapped_column(String(30))
    is_finalized: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    finalized_run_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey(
            "finalized_payroll_runs.id",
            name="fk_payroll_computed_rows_finalized_run_id_final_runs",
        ),
    )
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    # DEFERRED cross-module FK -> users.id
    computed_by: Mapped[int | None] = mapped_column(BigInteger)

    __table_args__ = (
        UniqueConstraint(
            "payroll_group_id",
            "employee_id",
            "cycle_from",
            "cycle_to",
            name="uq_payroll_computed_rows_group_employee_cycle",
        ),
        Index(
            "ix_payroll_computed_rows_payroll_group_id_cycle_from_cycle_to",
            "payroll_group_id",
            "cycle_from",
            "cycle_to",
        ),
        Index("ix_payroll_computed_rows_employee_id_is_finalized", "employee_id", "is_finalized"),
    )

    payroll_group: Mapped["PayrollGroup"] = relationship(back_populates="computed_rows")  # noqa: F821
    finalized_run: Mapped["FinalizedPayrollRun"] = relationship(back_populates="computed_rows")
