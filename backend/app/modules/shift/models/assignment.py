"""Shift Management — assignment, week-off, and roster models.

Tables: shift_assignments, employee_weekoffs, roster.

Implements the approved Shift Management Database Architecture exactly.
All primary keys and foreign keys use BIGINT (project-wide PK convention).

Enforced cross-module FKs (Employee Management): org_id -> organizations,
employee_id -> employees. Intra-module FK: shift_id -> shifts.
DEFERRED cross-module FKs -> users (User Management):
    shift_assignments.assigned_by, employee_weekoffs.updated_by,
    roster.created_by, roster.updated_by.
"""

from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    SmallInteger,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database.base import Base


class ShiftAssignment(Base):
    __tablename__ = "shift_assignments"

    assignment_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    org_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("organizations.org_id", name="fk_shift_assignments_org_id_organizations"),
        nullable=False,
    )
    employee_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("employees.employee_id", name="fk_shift_assignments_employee_id_employees"),
        nullable=False,
    )
    shift_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("shifts.shift_id", name="fk_shift_assignments_shift_id_shifts"),
        nullable=False,
    )
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[date | None] = mapped_column(Date)
    # DEFERRED cross-module FK -> users.id
    assigned_by: Mapped[int | None] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )

    __table_args__ = (
        Index(
            "ix_shift_assignments_employee_id_effective_from_effective_to",
            "employee_id",
            "effective_from",
            "effective_to",
        ),
    )

    shift: Mapped["Shift"] = relationship(back_populates="assignments")  # noqa: F821


class EmployeeWeekoff(Base):
    __tablename__ = "employee_weekoffs"

    weekoff_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    employee_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("employees.employee_id", name="fk_employee_weekoffs_employee_id_employees"),
        nullable=False,
    )
    day_of_week: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    weekoff_type: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'working'")
    )
    occurrence_1st: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true")
    )
    occurrence_2nd: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true")
    )
    occurrence_3rd: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true")
    )
    occurrence_4th: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true")
    )
    occurrence_5th: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true")
    )
    effective_from: Mapped[date | None] = mapped_column(Date)
    effective_to: Mapped[date | None] = mapped_column(Date)
    # DEFERRED cross-module FK -> users.id
    updated_by: Mapped[int | None] = mapped_column(BigInteger)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )

    __table_args__ = (
        Index(
            "uq_employee_weekoffs_employee_id_day_of_week",
            "employee_id",
            "day_of_week",
            unique=True,
            postgresql_where=text("effective_to IS NULL"),
        ),
        CheckConstraint(
            "day_of_week BETWEEN 0 AND 6", name="ck_employee_weekoffs_day_of_week"
        ),
        CheckConstraint(
            "weekoff_type IN ('working', 'week_off', 'occasional_week_off')",
            name="ck_employee_weekoffs_weekoff_type",
        ),
    )


class Roster(Base):
    __tablename__ = "roster"

    roster_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    org_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("organizations.org_id", name="fk_roster_org_id_organizations"),
        nullable=False,
    )
    employee_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("employees.employee_id", name="fk_roster_employee_id_employees"),
        nullable=False,
    )
    roster_date: Mapped[date] = mapped_column(Date, nullable=False)
    shift_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("shifts.shift_id", name="fk_roster_shift_id_shifts"),
    )
    is_week_off: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    # DEFERRED cross-module FKs -> users.id
    created_by: Mapped[int | None] = mapped_column(BigInteger)
    updated_by: Mapped[int | None] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )

    __table_args__ = (
        UniqueConstraint("employee_id", "roster_date", name="uq_roster_employee_id_roster_date"),
        Index("ix_roster_org_id_roster_date", "org_id", "roster_date"),
    )

    shift: Mapped["Shift"] = relationship(back_populates="roster_entries")  # noqa: F821
