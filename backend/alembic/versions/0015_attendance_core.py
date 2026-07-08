"""attendance core

Creates the Attendance module's three owned tables: attendance_days,
attendance_punches, attendance_penalties.

This module's approved architecture uses BIGINT `id` primary keys and BIGINT
foreign keys throughout. Enumerated columns are VARCHAR + CHECK (this project
does not use native PostgreSQL ENUM types).

Cross-module FOREIGN KEYs are ENFORCED against the verified target primary keys
(all exist and are BIGINT by this revision):
    * organizations.org_id, employees.employee_id, shifts.shift_id,
      leave_requests.id, biometric_devices.id, users.id

DEFERRED cross-module FK (column only, no constraint):
    * attendance_penalties.payroll_reference_id -> no payroll line-item table
      exists yet; kept as a plain BIGINT column per the project deferred-FK
      convention.

Overlapping attendance-configuration and regularization tables already exist in
other modules and are NOT touched here:
    * org_attendance_settings / employee_attendance_permissions (0001, employee)
    * attendance_regularization_requests (0004, approvals)

Revision ID: 0015_attendance_core
Revises: 0014_notifications
Create Date: 2026-07-08
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0015_attendance_core"
down_revision: Union[str, None] = "0014_notifications"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ----- attendance_days ---------------------------------------------------
    op.create_table(
        "attendance_days",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("org_id", sa.BigInteger(), nullable=False),
        sa.Column("employee_id", sa.BigInteger(), nullable=False),
        sa.Column("attendance_date", sa.Date(), nullable=False),
        sa.Column("shift_id", sa.BigInteger(), nullable=True),
        sa.Column("expected_start_time", sa.Time(), nullable=True),
        sa.Column("expected_end_time", sa.Time(), nullable=True),
        sa.Column("status", sa.String(length=20), server_default=sa.text("'not_marked'"), nullable=False),
        sa.Column("first_punch_in", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_punch_out", sa.DateTime(timezone=True), nullable=True),
        sa.Column("total_working_minutes", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("total_break_minutes", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("overtime_minutes", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("late_minutes", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("early_leaving_minutes", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("leave_id", sa.BigInteger(), nullable=True),
        sa.Column("is_regularized", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("source", sa.String(length=20), server_default=sa.text("'system'"), nullable=False),
        sa.Column("marked_by", sa.BigInteger(), nullable=True),
        sa.Column("remarks", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", sa.BigInteger(), nullable=True),
        sa.Column("updated_by", sa.BigInteger(), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_attendance_days"),
        sa.ForeignKeyConstraint(
            ["org_id"], ["organizations.org_id"], name="fk_attendance_days_org_id_organizations"
        ),
        sa.ForeignKeyConstraint(
            ["employee_id"], ["employees.employee_id"], name="fk_attendance_days_employee_id_employees"
        ),
        sa.ForeignKeyConstraint(
            ["shift_id"], ["shifts.shift_id"], name="fk_attendance_days_shift_id_shifts"
        ),
        sa.ForeignKeyConstraint(
            ["leave_id"], ["leave_requests.id"], name="fk_attendance_days_leave_id_leave_requests"
        ),
        sa.ForeignKeyConstraint(
            ["marked_by"], ["users.id"], name="fk_attendance_days_marked_by_users"
        ),
        sa.ForeignKeyConstraint(
            ["created_by"], ["users.id"], name="fk_attendance_days_created_by_users"
        ),
        sa.ForeignKeyConstraint(
            ["updated_by"], ["users.id"], name="fk_attendance_days_updated_by_users"
        ),
        sa.UniqueConstraint(
            "employee_id", "attendance_date", name="uq_attendance_days_employee_id_attendance_date"
        ),
        sa.CheckConstraint(
            "status IN ('present', 'absent', 'half_day', 'week_off', "
            "'holiday', 'on_leave', 'not_marked')",
            name="ck_attendance_days_status",
        ),
        sa.CheckConstraint(
            "source IN ('biometric', 'mobile', 'web', 'manual', 'system')",
            name="ck_attendance_days_source",
        ),
        sa.CheckConstraint(
            "total_working_minutes >= 0", name="ck_attendance_days_total_working_minutes_non_negative"
        ),
        sa.CheckConstraint(
            "total_break_minutes >= 0", name="ck_attendance_days_total_break_minutes_non_negative"
        ),
        sa.CheckConstraint(
            "overtime_minutes >= 0", name="ck_attendance_days_overtime_minutes_non_negative"
        ),
        sa.CheckConstraint(
            "late_minutes >= 0", name="ck_attendance_days_late_minutes_non_negative"
        ),
        sa.CheckConstraint(
            "early_leaving_minutes >= 0", name="ck_attendance_days_early_leaving_minutes_non_negative"
        ),
    )
    op.create_index(
        "ix_attendance_days_org_id_attendance_date", "attendance_days", ["org_id", "attendance_date"]
    )

    # ----- attendance_punches ------------------------------------------------
    op.create_table(
        "attendance_punches",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("org_id", sa.BigInteger(), nullable=False),
        sa.Column("employee_id", sa.BigInteger(), nullable=False),
        sa.Column("attendance_day_id", sa.BigInteger(), nullable=False),
        sa.Column("punch_type", sa.String(length=20), nullable=False),
        sa.Column("punch_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sequence_no", sa.SmallInteger(), nullable=False),
        sa.Column("punch_source", sa.String(length=20), nullable=False),
        sa.Column("device_id", sa.BigInteger(), nullable=True),
        sa.Column("latitude", sa.Numeric(precision=9, scale=6), nullable=True),
        sa.Column("longitude", sa.Numeric(precision=9, scale=6), nullable=True),
        sa.Column("is_valid", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", sa.BigInteger(), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_attendance_punches"),
        sa.ForeignKeyConstraint(
            ["org_id"], ["organizations.org_id"], name="fk_attendance_punches_org_id_organizations"
        ),
        sa.ForeignKeyConstraint(
            ["employee_id"], ["employees.employee_id"], name="fk_attendance_punches_employee_id_employees"
        ),
        sa.ForeignKeyConstraint(
            ["attendance_day_id"], ["attendance_days.id"],
            name="fk_attendance_punches_attendance_day_id_attendance_days",
        ),
        sa.ForeignKeyConstraint(
            ["device_id"], ["biometric_devices.id"],
            name="fk_attendance_punches_device_id_biometric_devices",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"], ["users.id"], name="fk_attendance_punches_created_by_users"
        ),
        sa.CheckConstraint(
            "punch_type IN ('in', 'out', 'break_in', 'break_out')",
            name="ck_attendance_punches_punch_type",
        ),
        sa.CheckConstraint(
            "punch_source IN ('biometric_device', 'mobile_app', 'web_portal', 'manual_entry')",
            name="ck_attendance_punches_punch_source",
        ),
        sa.CheckConstraint("sequence_no > 0", name="ck_attendance_punches_sequence_no_positive"),
    )
    op.create_index(
        "ix_attendance_punches_attendance_day_id_sequence_no",
        "attendance_punches",
        ["attendance_day_id", "sequence_no"],
    )
    op.create_index(
        "ix_attendance_punches_employee_id_punch_time",
        "attendance_punches",
        ["employee_id", "punch_time"],
    )
    op.create_index(
        "ix_attendance_punches_device_id_punch_time",
        "attendance_punches",
        ["device_id", "punch_time"],
    )

    # ----- attendance_penalties ----------------------------------------------
    op.create_table(
        "attendance_penalties",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("org_id", sa.BigInteger(), nullable=False),
        sa.Column("employee_id", sa.BigInteger(), nullable=False),
        sa.Column("attendance_day_id", sa.BigInteger(), nullable=False),
        sa.Column("penalty_type", sa.String(length=30), nullable=False),
        sa.Column("penalty_unit", sa.String(length=10), nullable=False),
        sa.Column("penalty_value", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("status", sa.String(length=10), server_default=sa.text("'active'"), nullable=False),
        sa.Column("applied_by", sa.BigInteger(), nullable=False),
        sa.Column("payroll_reference_id", sa.BigInteger(), nullable=True),
        sa.Column("remarks", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_attendance_penalties"),
        sa.ForeignKeyConstraint(
            ["org_id"], ["organizations.org_id"], name="fk_attendance_penalties_org_id_organizations"
        ),
        sa.ForeignKeyConstraint(
            ["employee_id"], ["employees.employee_id"], name="fk_attendance_penalties_employee_id_employees"
        ),
        sa.ForeignKeyConstraint(
            ["attendance_day_id"], ["attendance_days.id"],
            name="fk_attendance_penalties_attendance_day_id_attendance_days",
        ),
        sa.ForeignKeyConstraint(
            ["applied_by"], ["users.id"], name="fk_attendance_penalties_applied_by_users"
        ),
        sa.CheckConstraint(
            "penalty_type IN ('late_coming', 'early_going', 'absent_without_notice', 'other')",
            name="ck_attendance_penalties_penalty_type",
        ),
        sa.CheckConstraint(
            "penalty_unit IN ('amount', 'days', 'hours')",
            name="ck_attendance_penalties_penalty_unit",
        ),
        sa.CheckConstraint(
            "status IN ('active', 'waived')", name="ck_attendance_penalties_status"
        ),
        sa.CheckConstraint(
            "penalty_value >= 0", name="ck_attendance_penalties_penalty_value_non_negative"
        ),
    )
    op.create_index(
        "ix_attendance_penalties_employee_id_status",
        "attendance_penalties",
        ["employee_id", "status"],
    )
    op.create_index(
        "ix_attendance_penalties_attendance_day_id",
        "attendance_penalties",
        ["attendance_day_id"],
    )
    op.create_index(
        "ix_attendance_penalties_payroll_reference_id",
        "attendance_penalties",
        ["payroll_reference_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_attendance_penalties_payroll_reference_id", table_name="attendance_penalties")
    op.drop_index("ix_attendance_penalties_attendance_day_id", table_name="attendance_penalties")
    op.drop_index("ix_attendance_penalties_employee_id_status", table_name="attendance_penalties")
    op.drop_table("attendance_penalties")

    op.drop_index("ix_attendance_punches_device_id_punch_time", table_name="attendance_punches")
    op.drop_index("ix_attendance_punches_employee_id_punch_time", table_name="attendance_punches")
    op.drop_index(
        "ix_attendance_punches_attendance_day_id_sequence_no", table_name="attendance_punches"
    )
    op.drop_table("attendance_punches")

    op.drop_index("ix_attendance_days_org_id_attendance_date", table_name="attendance_days")
    op.drop_table("attendance_days")
