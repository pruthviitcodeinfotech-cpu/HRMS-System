"""Leave & Holiday Management — leave configuration, balances, and requests.

Tables: leave_settings, leave_types, employee_leave_allocations,
employee_leave_balances, leave_balance_adjustments, leave_requests.

Implements the approved Leave & Holiday Management Database Architecture exactly.
This module's approved architecture uses BIGINT `id` primary keys.

Intra-module FKs (enforced): leave_type_id -> leave_types.
DEFERRED cross-module FKs (columns only, no constraint):
    * employee_id -> employees  (Employee Management is built, but its approved
      schema uses employees.employee_id (INTEGER) while this module's approved
      schema references employees.id (BIGINT). The FK is deferred pending a
      project-wide primary-key convention decision — see the migration.)
    * created_by / updated_by / adjusted_by / reviewed_by -> users (User Management)
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
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database.base import Base


class LeaveSetting(Base):
    __tablename__ = "leave_settings"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    org_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    leave_cycle: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'calendar_year'")
    )
    cycle_start_month: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, server_default=text("1")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    # DEFERRED cross-module FKs -> users.id
    created_by: Mapped[int | None] = mapped_column(BigInteger)
    updated_by: Mapped[int | None] = mapped_column(BigInteger)

    __table_args__ = (UniqueConstraint("org_id", name="uq_leave_settings_org_id"),)


class LeaveType(Base):
    __tablename__ = "leave_types"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    org_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    alias: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    auto_allocation_count: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    allocation_frequency: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'monthly'")
    )
    carry_forward_count: Mapped[Decimal] = mapped_column(
        Numeric(6, 2), nullable=False, server_default=text("0")
    )
    carry_forward_frequency: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'monthly'")
    )
    encashment_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    encashment_limit: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    encashment_frequency: Mapped[str | None] = mapped_column(String(20))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    # DEFERRED cross-module FKs -> users.id
    created_by: Mapped[int | None] = mapped_column(BigInteger)
    updated_by: Mapped[int | None] = mapped_column(BigInteger)

    __table_args__ = (
        UniqueConstraint("org_id", "alias", name="uq_leave_types_org_id_alias"),
        CheckConstraint(
            "allocation_frequency IN ('monthly', 'yearly')",
            name="ck_leave_types_allocation_frequency",
        ),
        CheckConstraint(
            "carry_forward_frequency IN ('monthly', 'yearly')",
            name="ck_leave_types_carry_forward_frequency",
        ),
        CheckConstraint(
            "encashment_frequency IN ('monthly', 'yearly')",
            name="ck_leave_types_encashment_frequency",
        ),
        CheckConstraint(
            "NOT encashment_enabled OR encashment_limit IS NOT NULL",
            name="ck_leave_types_encashment_limit_required",
        ),
    )

    allocations: Mapped[list["EmployeeLeaveAllocation"]] = relationship(back_populates="leave_type")
    balances: Mapped[list["EmployeeLeaveBalance"]] = relationship(back_populates="leave_type")
    adjustments: Mapped[list["LeaveBalanceAdjustment"]] = relationship(back_populates="leave_type")
    requests: Mapped[list["LeaveRequest"]] = relationship(back_populates="leave_type")


class EmployeeLeaveAllocation(Base):
    __tablename__ = "employee_leave_allocations"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    # DEFERRED cross-module FK -> employees (see module docstring)
    employee_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    leave_type_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("leave_types.id", name="fk_employee_leave_allocations_leave_type_id_leave_types"),
        nullable=False,
    )
    cycle_year: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    cycle_period: Mapped[str | None] = mapped_column(String(20))
    allocated_days: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    allocation_date: Mapped[date] = mapped_column(Date, nullable=False)
    allocation_source: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'auto'")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    # DEFERRED cross-module FK -> users.id
    created_by: Mapped[int | None] = mapped_column(BigInteger)

    __table_args__ = (
        UniqueConstraint(
            "employee_id",
            "leave_type_id",
            "cycle_year",
            "cycle_period",
            name="uq_employee_leave_allocations_employee_id_leave_type_id_cycle_year_cycle_period",
        ),
    )

    leave_type: Mapped["LeaveType"] = relationship(back_populates="allocations")


class EmployeeLeaveBalance(Base):
    __tablename__ = "employee_leave_balances"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    # DEFERRED cross-module FK -> employees
    employee_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    leave_type_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("leave_types.id", name="fk_employee_leave_balances_leave_type_id_leave_types"),
        nullable=False,
    )
    cycle_year: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    opening_balance: Mapped[Decimal] = mapped_column(
        Numeric(6, 2), nullable=False, server_default=text("0")
    )
    allocated: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False, server_default=text("0"))
    used: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False, server_default=text("0"))
    carried_forward: Mapped[Decimal] = mapped_column(
        Numeric(6, 2), nullable=False, server_default=text("0")
    )
    encashed: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False, server_default=text("0"))
    adjusted: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False, server_default=text("0"))
    closing_balance: Mapped[Decimal] = mapped_column(
        Numeric(6, 2), nullable=False, server_default=text("0")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    # DEFERRED cross-module FK -> users.id
    updated_by: Mapped[int | None] = mapped_column(BigInteger)

    __table_args__ = (
        UniqueConstraint(
            "employee_id",
            "leave_type_id",
            "cycle_year",
            name="uq_employee_leave_balances_employee_id_leave_type_id_cycle_year",
        ),
    )

    leave_type: Mapped["LeaveType"] = relationship(back_populates="balances")


class LeaveBalanceAdjustment(Base):
    __tablename__ = "leave_balance_adjustments"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    # DEFERRED cross-module FK -> employees
    employee_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    leave_type_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("leave_types.id", name="fk_leave_balance_adjustments_leave_type_id_leave_types"),
        nullable=False,
    )
    adjustment_type: Mapped[str] = mapped_column(String(20), nullable=False)
    delta: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    new_balance: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    remarks: Mapped[str | None] = mapped_column(Text)
    cycle_year: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    adjusted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    # DEFERRED cross-module FK -> users.id (NOT NULL per the architecture)
    adjusted_by: Mapped[int] = mapped_column(BigInteger, nullable=False)

    __table_args__ = (
        Index(
            "ix_leave_balance_adjustments_employee_id_cycle_year",
            "employee_id",
            "cycle_year",
        ),
    )

    leave_type: Mapped["LeaveType"] = relationship(back_populates="adjustments")


class LeaveRequest(Base):
    __tablename__ = "leave_requests"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    # DEFERRED cross-module FK -> employees
    employee_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    leave_type_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("leave_types.id", name="fk_leave_requests_leave_type_id_leave_types"),
        nullable=False,
    )
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    duration_days: Mapped[Decimal] = mapped_column(Numeric(4, 1), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default=text("'pending'"))
    applied_on: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # DEFERRED cross-module FK -> users.id
    reviewed_by: Mapped[int | None] = mapped_column(BigInteger)
    rejection_reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )

    __table_args__ = (
        Index("ix_leave_requests_employee_id_status", "employee_id", "status"),
        Index("ix_leave_requests_leave_type_id_status", "leave_type_id", "status"),
        CheckConstraint(
            "status IN ('pending', 'approved', 'rejected')", name="ck_leave_requests_status"
        ),
        CheckConstraint(
            "end_date >= start_date", name="ck_leave_requests_end_date_after_start_date"
        ),
    )

    leave_type: Mapped["LeaveType"] = relationship(back_populates="requests")
