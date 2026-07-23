"""Payroll — finalized payroll history and employee frozen snapshots.

Tables: payroll_finalizations, payroll_finalization_employees.

Implements the approved Payroll Database Architecture (BIGINT `id`).
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    BigInteger,
    Date,
    DateTime,
    ForeignKey,
    Index,
    JSON,
    Numeric,
    SmallInteger,
    String,
    Text,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database.base import Base


class PayrollFinalization(Base):
    __tablename__ = "payroll_finalizations"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    org_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    payroll_group_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "payroll_groups.id", name="fk_payroll_finalizations_payroll_group_id_payroll_groups"
        ),
        nullable=False,
    )
    payroll_period_id: Mapped[int | None] = mapped_column(BigInteger)
    from_date: Mapped[date] = mapped_column(Date, nullable=False)
    to_date: Mapped[date] = mapped_column(Date, nullable=False)
    payroll_module: Mapped[str] = mapped_column(
        String(50), nullable=False, server_default=text("'Monthly Payroll'")
    )
    employee_count: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, server_default=text("0")
    )
    gross_amount: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, server_default=text("0")
    )
    deduction_amount: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, server_default=text("0")
    )
    net_payable: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, server_default=text("0")
    )
    finalized_amount: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, server_default=text("0")
    )
    paid_amount: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    paid_on: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'Finalized'")
    )
    # DEFERRED cross-module FK -> users.id
    finalized_by: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", name="fk_payroll_finalizations_finalized_by_users"),
        nullable=False,
    )
    finalized_on: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    remarks: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )

    __table_args__ = (
        Index(
            "ix_payroll_finalizations_org_id_group_dates",
            "org_id",
            "payroll_group_id",
            "from_date",
            "to_date",
        ),
        Index("ix_payroll_finalizations_org_id_status", "org_id", "status"),
    )

    payroll_group: Mapped["PayrollGroup"] = relationship(back_populates="finalizations")  # noqa: F821
    employees: Mapped[list["PayrollFinalizationEmployee"]] = relationship(
        back_populates="finalization", cascade="all, delete-orphan"
    )


class PayrollFinalizationEmployee(Base):
    __tablename__ = "payroll_finalization_employees"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    payroll_finalization_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "payroll_finalizations.id", name="fk_payroll_fin_emp_finalization_id_payroll_fin"
        ),
        nullable=False,
    )
    employee_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    attendance_summary: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    earnings_summary: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    deduction_summary: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    loan_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, server_default=text("0")
    )
    arrears_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, server_default=text("0")
    )
    net_salary: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, server_default=text("0")
    )
    json_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )

    __table_args__ = (
        Index("ix_payroll_fin_emp_finalization_id", "payroll_finalization_id"),
        Index("ix_payroll_fin_emp_employee_id", "employee_id"),
    )

    finalization: Mapped["PayrollFinalization"] = relationship(back_populates="employees")
