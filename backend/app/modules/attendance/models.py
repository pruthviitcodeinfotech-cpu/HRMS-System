"""Attendance — core daily attendance schema (module-owned tables).

Tables: attendance_days, attendance_punches, attendance_penalties.

Implements the approved Attendance Database Architecture. All primary keys and
foreign keys use BIGINT (project-wide PK convention). Enumerated columns use
VARCHAR + CHECK constraints (this project does not use native PostgreSQL ENUM
types). Cross-module foreign keys reference the real primary keys of the target
tables, verified against the existing schema:

    * organizations.org_id     (employee module)
    * employees.employee_id    (employee module)
    * shifts.shift_id          (shift module)
    * leave_requests.id        (leave module)  -- the PDF's `leaves` table does
                                                  not exist; `leave_requests` is
                                                  the approved leave record.
    * biometric_devices.id     (hardware module)
    * users.id                 (rbac/user-management module)

Overlapping attendance-configuration and regularization tables already exist in
other modules and are intentionally NOT redefined here (reused as-is):
    * org_attendance_settings / employee_attendance_permissions (employee module)
    * attendance_regularization_requests (approvals module)

DEFERRED cross-module FK (column only, no constraint):
    * attendance_penalties.payroll_reference_id -> no payroll line-item table
      exists yet; kept as a plain BIGINT column per the project deferred-FK
      convention (no payroll tables are created here).
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
    Integer,
    Numeric,
    SmallInteger,
    String,
    Time,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database.base import Base


class AttendanceDay(Base):
    """Core daily attendance summary — one row per employee per calendar date."""

    __tablename__ = "attendance_days"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    org_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("organizations.org_id", name="fk_attendance_days_org_id_organizations"),
        nullable=False,
    )
    employee_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("employees.employee_id", name="fk_attendance_days_employee_id_employees"),
        nullable=False,
    )
    attendance_date: Mapped[date] = mapped_column(Date, nullable=False)
    shift_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("shifts.shift_id", name="fk_attendance_days_shift_id_shifts"),
    )
    expected_start_time: Mapped[time | None] = mapped_column(Time)
    expected_end_time: Mapped[time | None] = mapped_column(Time)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'not_marked'")
    )
    first_punch_in: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_punch_out: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    total_working_minutes: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    total_break_minutes: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    overtime_minutes: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    late_minutes: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    early_leaving_minutes: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    leave_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("leave_requests.id", name="fk_attendance_days_leave_id_leave_requests"),
    )
    is_regularized: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    source: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'system'")
    )
    marked_by: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("users.id", name="fk_attendance_days_marked_by_users"),
    )
    remarks: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    created_by: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("users.id", name="fk_attendance_days_created_by_users"),
    )
    updated_by: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("users.id", name="fk_attendance_days_updated_by_users"),
    )

    __table_args__ = (
        UniqueConstraint(
            "employee_id",
            "attendance_date",
            name="uq_attendance_days_employee_id_attendance_date",
        ),
        CheckConstraint(
            "status IN ('present', 'absent', 'half_day', 'week_off', "
            "'holiday', 'on_leave', 'not_marked')",
            name="ck_attendance_days_status",
        ),
        CheckConstraint(
            "source IN ('biometric', 'mobile', 'web', 'manual', 'system')",
            name="ck_attendance_days_source",
        ),
        CheckConstraint(
            "total_working_minutes >= 0",
            name="ck_attendance_days_total_working_minutes_non_negative",
        ),
        CheckConstraint(
            "total_break_minutes >= 0",
            name="ck_attendance_days_total_break_minutes_non_negative",
        ),
        CheckConstraint(
            "overtime_minutes >= 0",
            name="ck_attendance_days_overtime_minutes_non_negative",
        ),
        CheckConstraint(
            "late_minutes >= 0",
            name="ck_attendance_days_late_minutes_non_negative",
        ),
        CheckConstraint(
            "early_leaving_minutes >= 0",
            name="ck_attendance_days_early_leaving_minutes_non_negative",
        ),
        Index("ix_attendance_days_org_id_attendance_date", "org_id", "attendance_date"),
        # attendance/repository.py:103 filters days by shift_id.
        Index("ix_attendance_days_shift_id", "shift_id"),
    )

    punches: Mapped[list["AttendancePunch"]] = relationship(back_populates="attendance_day")
    penalties: Mapped[list["AttendancePenalty"]] = relationship(back_populates="attendance_day")


class AttendancePunch(Base):
    """Immutable, append-only log of individual punch events for a day."""

    __tablename__ = "attendance_punches"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    org_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("organizations.org_id", name="fk_attendance_punches_org_id_organizations"),
        nullable=False,
    )
    employee_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("employees.employee_id", name="fk_attendance_punches_employee_id_employees"),
        nullable=False,
    )
    attendance_day_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "attendance_days.id",
            name="fk_attendance_punches_attendance_day_id_attendance_days",
        ),
        nullable=False,
    )
    punch_type: Mapped[str] = mapped_column(String(20), nullable=False)
    punch_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    sequence_no: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    punch_source: Mapped[str] = mapped_column(String(20), nullable=False)
    device_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey(
            "biometric_devices.id",
            name="fk_attendance_punches_device_id_biometric_devices",
        ),
    )
    latitude: Mapped[Decimal | None] = mapped_column(Numeric(9, 6))
    longitude: Mapped[Decimal | None] = mapped_column(Numeric(9, 6))
    is_valid: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    created_by: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("users.id", name="fk_attendance_punches_created_by_users"),
    )

    __table_args__ = (
        CheckConstraint(
            "punch_type IN ('in', 'out', 'break_in', 'break_out')",
            name="ck_attendance_punches_punch_type",
        ),
        CheckConstraint(
            "punch_source IN ('biometric_device', 'mobile_app', 'web_portal', 'manual_entry')",
            name="ck_attendance_punches_punch_source",
        ),
        CheckConstraint("sequence_no > 0", name="ck_attendance_punches_sequence_no_positive"),
        Index(
            "ix_attendance_punches_attendance_day_id_sequence_no",
            "attendance_day_id",
            "sequence_no",
        ),
        Index("ix_attendance_punches_employee_id_punch_time", "employee_id", "punch_time"),
        Index("ix_attendance_punches_device_id_punch_time", "device_id", "punch_time"),
        # AttendancePunchRepository.search(): WHERE org_id = ? ORDER BY punch_time DESC.
        # The leading org_id also supplies the missing FK index.
        Index("ix_attendance_punches_org_id_punch_time", "org_id", "punch_time"),
    )

    attendance_day: Mapped["AttendanceDay"] = relationship(back_populates="punches")


class AttendancePenalty(Base):
    """Attendance-driven penalties (e.g. late-coming) that feed into Payroll."""

    __tablename__ = "attendance_penalties"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    org_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("organizations.org_id", name="fk_attendance_penalties_org_id_organizations"),
        nullable=False,
    )
    employee_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("employees.employee_id", name="fk_attendance_penalties_employee_id_employees"),
        nullable=False,
    )
    attendance_day_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "attendance_days.id",
            name="fk_attendance_penalties_attendance_day_id_attendance_days",
        ),
        nullable=False,
    )
    penalty_type: Mapped[str] = mapped_column(String(30), nullable=False)
    penalty_unit: Mapped[str] = mapped_column(String(10), nullable=False)
    penalty_value: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    status: Mapped[str] = mapped_column(
        String(10), nullable=False, server_default=text("'active'")
    )
    applied_by: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", name="fk_attendance_penalties_applied_by_users"),
        nullable=False,
    )
    # DEFERRED cross-module FK -> payroll line item (no such table exists yet).
    payroll_reference_id: Mapped[int | None] = mapped_column(BigInteger)
    remarks: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))

    __table_args__ = (
        CheckConstraint(
            "penalty_type IN ('late_coming', 'early_going', 'absent_without_notice', 'other')",
            name="ck_attendance_penalties_penalty_type",
        ),
        CheckConstraint(
            "penalty_unit IN ('amount', 'days', 'hours')",
            name="ck_attendance_penalties_penalty_unit",
        ),
        CheckConstraint(
            "status IN ('active', 'waived')",
            name="ck_attendance_penalties_status",
        ),
        CheckConstraint(
            "penalty_value >= 0",
            name="ck_attendance_penalties_penalty_value_non_negative",
        ),
        Index("ix_attendance_penalties_employee_id_status", "employee_id", "status"),
        # AttendancePenaltyRepository._search_stmt(): WHERE org_id = ? [AND status = ?].
        # The leading org_id also supplies the missing FK index.
        Index("ix_attendance_penalties_org_id_status", "org_id", "status"),
        Index("ix_attendance_penalties_attendance_day_id", "attendance_day_id"),
        Index("ix_attendance_penalties_payroll_reference_id", "payroll_reference_id"),
    )

    attendance_day: Mapped["AttendanceDay"] = relationship(back_populates="penalties")
