"""Payroll — settings, groups, assignments, salary cycles, column settings.

Tables: payroll_settings, payroll_groups, employee_payroll_group_assignments,
payroll_salary_cycles, payroll_column_settings.

Implements the approved Payroll Database Architecture exactly (BIGINT `id`).

Intra-module FKs (enforced): payroll_group_id / previous_group_id -> payroll_groups.
DEFERRED cross-module FKs (columns only):
    * employee_id -> employees (Employee Management built, but its approved schema
      uses employees.employee_id (INTEGER) while this module references
      employees.id (BIGINT); deferred pending the project-wide PK convention).
    * created_by / updated_by / assigned_by -> users (User Management).
"""

from datetime import date, datetime, time
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
    Time,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database.base import Base


class PayrollSetting(Base):
    __tablename__ = "payroll_settings"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    org_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    working_hour_type: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'fixed'")
    )
    full_day_working_hours: Mapped[time] = mapped_column(
        Time, nullable=False, server_default=text("'08:00'")
    )
    half_day_working_hours: Mapped[time] = mapped_column(
        Time, nullable=False, server_default=text("'04:00'")
    )
    attendance_mode: Mapped[str] = mapped_column(
        String(30), nullable=False, server_default=text("'consider_all_punch'")
    )
    off_day_compensation: Mapped[str] = mapped_column(
        String(30), nullable=False, server_default=text("'monetary_compensation'")
    )
    off_day_wage_multiplier: Mapped[Decimal] = mapped_column(
        Numeric(4, 2), nullable=False, server_default=text("1.00")
    )
    daily_wage_formula: Mapped[str] = mapped_column(
        String(50), nullable=False, server_default=text("'monthly_calendar_days'")
    )
    overtime_type: Mapped[str] = mapped_column(
        String(30), nullable=False, server_default=text("'fixed_per_hour_pay'")
    )
    overtime_hourly_multiplier: Mapped[Decimal] = mapped_column(
        Numeric(4, 2), nullable=False, server_default=text("0.00")
    )
    overtime_buffer_period: Mapped[time] = mapped_column(
        Time, nullable=False, server_default=text("'00:00'")
    )
    overtime_period_interval: Mapped[str | None] = mapped_column(
        String(10), server_default=text("'15 Min'")
    )
    full_day_penalty_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    half_day_penalty_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    late_coming_penalty_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    grace_time: Mapped[time] = mapped_column(Time, nullable=False, server_default=text("'00:00'"))
    # DEFERRED cross-module FK -> users.id
    updated_by: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("users.id", name="fk_payroll_settings_updated_by_users"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )

    __table_args__ = (UniqueConstraint("org_id", name="uq_payroll_settings_org_id"),)


class PayrollGroup(Base):
    __tablename__ = "payroll_groups"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    org_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    payroll_type: Mapped[str] = mapped_column(String(30), nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    # DEFERRED cross-module FKs -> users.id
    created_by: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("users.id", name="fk_payroll_groups_created_by_users"),
    )
    updated_by: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("users.id", name="fk_payroll_groups_updated_by_users"),
    )

    __table_args__ = (
        Index(
            "uq_payroll_groups_org_id_name",
            "org_id",
            "name",
            unique=True,
            postgresql_where=text("is_deleted = false"),
        ),
        CheckConstraint(
            "payroll_type IN ('monthly_without_compliance', 'monthly_with_compliance', "
            "'hourly_payroll')",
            name="ck_payroll_groups_payroll_type",
        ),
    )

    assignments: Mapped[list["EmployeePayrollGroupAssignment"]] = relationship(
        back_populates="payroll_group",
        foreign_keys="EmployeePayrollGroupAssignment.payroll_group_id",
    )
    salary_cycles: Mapped[list["PayrollSalaryCycle"]] = relationship(back_populates="payroll_group")
    column_settings: Mapped[list["PayrollColumnSetting"]] = relationship(
        back_populates="payroll_group"
    )
    finalized_runs: Mapped[list["FinalizedPayrollRun"]] = relationship(  # noqa: F821
        back_populates="payroll_group"
    )
    computed_rows: Mapped[list["PayrollComputedRow"]] = relationship(  # noqa: F821
        back_populates="payroll_group"
    )


class EmployeePayrollGroupAssignment(Base):
    __tablename__ = "employee_payroll_group_assignments"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    # DEFERRED cross-module FK -> employees
    employee_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    payroll_group_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "payroll_groups.id",
            name="fk_emp_payroll_grp_assign_payroll_group_id_payroll_groups",
        ),
        nullable=False,
    )
    salary_type: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'monthly'")
    )
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    # DEFERRED cross-module FK -> users.id (NOT NULL per the architecture)
    assigned_by: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", name="fk_employee_payroll_group_assignments_assigned_by_users"),
        nullable=False,
    )
    previous_group_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey(
            "payroll_groups.id",
            name="fk_emp_payroll_grp_assign_previous_group_id_payroll_groups",
        ),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )

    __table_args__ = (
        UniqueConstraint("employee_id", name="uq_employee_payroll_group_assignments_employee_id"),
        CheckConstraint(
            "salary_type IN ('monthly', 'hourly')",
            name="ck_employee_payroll_group_assignments_salary_type",
        ),
    )

    payroll_group: Mapped["PayrollGroup"] = relationship(
        back_populates="assignments", foreign_keys=[payroll_group_id]
    )


class PayrollSalaryCycle(Base):
    __tablename__ = "payroll_salary_cycles"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    payroll_group_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "payroll_groups.id", name="fk_payroll_salary_cycles_payroll_group_id_payroll_groups"
        ),
        nullable=False,
    )
    cycle_date: Mapped[date] = mapped_column(Date, nullable=False)
    is_finalized: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    # DEFERRED cross-module FK -> users.id
    created_by: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("users.id", name="fk_payroll_salary_cycles_created_by_users"),
    )

    __table_args__ = (
        UniqueConstraint(
            "payroll_group_id",
            "cycle_date",
            name="uq_payroll_salary_cycles_payroll_group_id_cycle_date",
        ),
    )

    payroll_group: Mapped["PayrollGroup"] = relationship(back_populates="salary_cycles")


class PayrollColumnSetting(Base):
    __tablename__ = "payroll_column_settings"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    payroll_group_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "payroll_groups.id", name="fk_payroll_column_settings_payroll_group_id_payroll_groups"
        ),
        nullable=False,
    )
    column_key: Mapped[str] = mapped_column(String(50), nullable=False)
    column_label: Mapped[str] = mapped_column(String(100), nullable=False)
    is_visible: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    display_order: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    # DEFERRED cross-module FK -> users.id
    updated_by: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("users.id", name="fk_payroll_column_settings_updated_by_users"),
    )

    __table_args__ = (
        UniqueConstraint(
            "payroll_group_id",
            "column_key",
            name="uq_payroll_column_settings_payroll_group_id_column_key",
        ),
    )

    payroll_group: Mapped["PayrollGroup"] = relationship(back_populates="column_settings")
