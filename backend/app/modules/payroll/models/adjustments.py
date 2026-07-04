"""Payroll — bulk attendance adjustment tables.

Tables: attendance_adjustments, attendance_adjustment_penalties,
attendance_adjustment_extra_hours.

Implements the approved Payroll Database Architecture exactly (BIGINT `id`).

DEFERRED cross-module FKs (columns only):
    * employee_id -> employees (see settings.py module docstring)
    * adjusted_by / created_by -> users (User Management)
"""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database.base import Base


class AttendanceAdjustment(Base):
    __tablename__ = "attendance_adjustments"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    org_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    # DEFERRED cross-module FK -> employees
    employee_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    attendance_date: Mapped[date] = mapped_column(Date, nullable=False)
    original_status: Mapped[str | None] = mapped_column(String(5))
    adjusted_status: Mapped[str] = mapped_column(String(5), nullable=False)
    is_forced_overwrite: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    has_punch_error: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    adjustment_source: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'spreadsheet'")
    )
    adjusted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    # DEFERRED cross-module FK -> users.id (NOT NULL per the architecture)
    adjusted_by: Mapped[int] = mapped_column(BigInteger, nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "employee_id", "attendance_date", name="uq_attendance_adjustments_employee_id_attendance_date"
        ),
        Index("ix_attendance_adjustments_org_id_attendance_date", "org_id", "attendance_date"),
        Index(
            "ix_attendance_adjustments_employee_id_attendance_date",
            "employee_id",
            "attendance_date",
        ),
        CheckConstraint(
            "adjusted_status IN ('FD', 'HD', 'A', 'WO', 'LWP')",
            name="ck_attendance_adjustments_adjusted_status",
        ),
    )


class AttendanceAdjustmentPenalty(Base):
    __tablename__ = "attendance_adjustment_penalties"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    # DEFERRED cross-module FK -> employees
    employee_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    attendance_date: Mapped[date] = mapped_column(Date, nullable=False)
    penalty_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    remark: Mapped[str | None] = mapped_column(Text)
    is_removed: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    # DEFERRED cross-module FK -> users.id (NOT NULL per the architecture)
    created_by: Mapped[int] = mapped_column(BigInteger, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )

    __table_args__ = (
        Index(
            "ix_attendance_adjustment_penalties_employee_id_attendance_date",
            "employee_id",
            "attendance_date",
        ),
    )


class AttendanceAdjustmentExtraHours(Base):
    __tablename__ = "attendance_adjustment_extra_hours"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    # DEFERRED cross-module FK -> employees
    employee_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    attendance_date: Mapped[date] = mapped_column(Date, nullable=False)
    extra_hours: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    remark: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    # DEFERRED cross-module FK -> users.id (NOT NULL per the architecture)
    created_by: Mapped[int] = mapped_column(BigInteger, nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "employee_id",
            "attendance_date",
            name="uq_attendance_adjustment_extra_hours_employee_id_attendance_date",
        ),
    )
