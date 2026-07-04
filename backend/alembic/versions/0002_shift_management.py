"""shift management

Creates the Shift Management module schema: shifts, shift_day_timings,
shift_assignments, employee_weekoffs, roster, working_hours_config,
working_hours_config_history.

Cross-module FKs to Employee Management (organizations, employees) are ENFORCED
here because those tables already exist (revision 0001).

Cross-module FOREIGN KEY constraints to `users` (User Management) are DEFERRED
(columns are created, constraints are not) until that module exists:
    shifts.created_by, shift_assignments.assigned_by, employee_weekoffs.updated_by,
    roster.created_by, roster.updated_by, working_hours_config.created_by,
    working_hours_config_history.changed_by.

Revision ID: 0002_shift_management
Revises: 0001_employee_management
Create Date: 2026-07-04
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0002_shift_management"
down_revision: Union[str, None] = "0001_employee_management"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ----- shifts ------------------------------------------------------------
    op.create_table(
        "shifts",
        sa.Column("shift_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("org_id", sa.Integer(), nullable=False),
        sa.Column("shift_name", sa.String(length=150), nullable=False),
        sa.Column("shift_type", sa.String(length=20), server_default=sa.text("'fixed'"), nullable=False),
        sa.Column("is_open_shift", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("is_default", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("is_uniform_time", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("has_break_time", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("shift_color", sa.String(length=30), nullable=True),
        sa.Column("remark", sa.Text(), nullable=True),
        sa.Column("is_advanced_mode", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=True),  # deferred FK -> users
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("shift_id", name="pk_shifts"),
        sa.ForeignKeyConstraint(
            ["org_id"], ["organizations.org_id"], name="fk_shifts_org_id_organizations"
        ),
        sa.CheckConstraint("shift_type IN ('fixed', 'open')", name="ck_shifts_shift_type"),
    )
    op.create_index(
        "uq_shifts_org_id_shift_name",
        "shifts",
        ["org_id", "shift_name"],
        unique=True,
        postgresql_where=sa.text("is_deleted = false"),
    )

    # ----- shift_day_timings -------------------------------------------------
    op.create_table(
        "shift_day_timings",
        sa.Column("timing_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("shift_id", sa.Integer(), nullable=False),
        sa.Column("day_of_week", sa.SmallInteger(), nullable=True),
        sa.Column("start_time", sa.Time(), nullable=True),
        sa.Column("end_time", sa.Time(), nullable=True),
        sa.Column("break_start_time", sa.Time(), nullable=True),
        sa.Column("break_end_time", sa.Time(), nullable=True),
        sa.Column("duration_minutes", sa.Integer(), nullable=True),
        sa.Column("is_working_day", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.PrimaryKeyConstraint("timing_id", name="pk_shift_day_timings"),
        sa.ForeignKeyConstraint(
            ["shift_id"], ["shifts.shift_id"], name="fk_shift_day_timings_shift_id_shifts"
        ),
        sa.UniqueConstraint(
            "shift_id", "day_of_week", name="uq_shift_day_timings_shift_id_day_of_week"
        ),
    )

    # ----- shift_assignments -------------------------------------------------
    op.create_table(
        "shift_assignments",
        sa.Column("assignment_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("org_id", sa.Integer(), nullable=False),
        sa.Column("employee_id", sa.Integer(), nullable=False),
        sa.Column("shift_id", sa.Integer(), nullable=False),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("effective_to", sa.Date(), nullable=True),
        sa.Column("assigned_by", sa.Integer(), nullable=True),  # deferred FK -> users
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("assignment_id", name="pk_shift_assignments"),
        sa.ForeignKeyConstraint(
            ["org_id"], ["organizations.org_id"], name="fk_shift_assignments_org_id_organizations"
        ),
        sa.ForeignKeyConstraint(
            ["employee_id"], ["employees.employee_id"],
            name="fk_shift_assignments_employee_id_employees",
        ),
        sa.ForeignKeyConstraint(
            ["shift_id"], ["shifts.shift_id"], name="fk_shift_assignments_shift_id_shifts"
        ),
    )
    op.create_index(
        "ix_shift_assignments_employee_id_effective_from_effective_to",
        "shift_assignments",
        ["employee_id", "effective_from", "effective_to"],
    )

    # ----- employee_weekoffs -------------------------------------------------
    op.create_table(
        "employee_weekoffs",
        sa.Column("weekoff_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("employee_id", sa.Integer(), nullable=False),
        sa.Column("day_of_week", sa.SmallInteger(), nullable=False),
        sa.Column("weekoff_type", sa.String(length=20), server_default=sa.text("'working'"), nullable=False),
        sa.Column("occurrence_1st", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("occurrence_2nd", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("occurrence_3rd", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("occurrence_4th", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("occurrence_5th", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("effective_from", sa.Date(), nullable=True),
        sa.Column("effective_to", sa.Date(), nullable=True),
        sa.Column("updated_by", sa.Integer(), nullable=True),  # deferred FK -> users
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("weekoff_id", name="pk_employee_weekoffs"),
        sa.ForeignKeyConstraint(
            ["employee_id"], ["employees.employee_id"],
            name="fk_employee_weekoffs_employee_id_employees",
        ),
        sa.CheckConstraint("day_of_week BETWEEN 0 AND 6", name="ck_employee_weekoffs_day_of_week"),
        sa.CheckConstraint(
            "weekoff_type IN ('working', 'week_off', 'occasional_week_off')",
            name="ck_employee_weekoffs_weekoff_type",
        ),
    )
    op.create_index(
        "uq_employee_weekoffs_employee_id_day_of_week",
        "employee_weekoffs",
        ["employee_id", "day_of_week"],
        unique=True,
        postgresql_where=sa.text("effective_to IS NULL"),
    )

    # ----- roster ------------------------------------------------------------
    op.create_table(
        "roster",
        sa.Column("roster_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("org_id", sa.Integer(), nullable=False),
        sa.Column("employee_id", sa.Integer(), nullable=False),
        sa.Column("roster_date", sa.Date(), nullable=False),
        sa.Column("shift_id", sa.Integer(), nullable=True),
        sa.Column("is_week_off", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=True),  # deferred FK -> users
        sa.Column("updated_by", sa.Integer(), nullable=True),  # deferred FK -> users
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("roster_id", name="pk_roster"),
        sa.ForeignKeyConstraint(
            ["org_id"], ["organizations.org_id"], name="fk_roster_org_id_organizations"
        ),
        sa.ForeignKeyConstraint(
            ["employee_id"], ["employees.employee_id"], name="fk_roster_employee_id_employees"
        ),
        sa.ForeignKeyConstraint(
            ["shift_id"], ["shifts.shift_id"], name="fk_roster_shift_id_shifts"
        ),
        sa.UniqueConstraint("employee_id", "roster_date", name="uq_roster_employee_id_roster_date"),
    )
    op.create_index("ix_roster_org_id_roster_date", "roster", ["org_id", "roster_date"])

    # ----- working_hours_config ----------------------------------------------
    op.create_table(
        "working_hours_config",
        sa.Column("config_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("org_id", sa.Integer(), nullable=False),
        sa.Column("working_hours_mode", sa.String(length=20), server_default=sa.text("'fixed'"), nullable=False),
        sa.Column("full_day_hours", sa.Time(), server_default=sa.text("'08:00'"), nullable=True),
        sa.Column("half_day_hours", sa.Time(), server_default=sa.text("'04:00'"), nullable=True),
        sa.Column("full_day_buffer_period", sa.Time(), server_default=sa.text("'00:00'"), nullable=True),
        sa.Column("half_day_buffer_period", sa.Time(), server_default=sa.text("'00:00'"), nullable=True),
        sa.Column("attendance_mode", sa.String(length=40), server_default=sa.text("'consider_all_punch'"), nullable=False),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=True),  # deferred FK -> users
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("config_id", name="pk_working_hours_config"),
        sa.ForeignKeyConstraint(
            ["org_id"], ["organizations.org_id"],
            name="fk_working_hours_config_org_id_organizations",
        ),
        sa.CheckConstraint(
            "working_hours_mode IN ('fixed', 'shift_wise')",
            name="ck_working_hours_config_working_hours_mode",
        ),
        sa.CheckConstraint(
            "attendance_mode IN ('consider_all_punch', 'first_and_last_punch_only', "
            "'full_day_on_single_punch', 'default_full_day')",
            name="ck_working_hours_config_attendance_mode",
        ),
    )

    # ----- working_hours_config_history --------------------------------------
    op.create_table(
        "working_hours_config_history",
        sa.Column("history_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("org_id", sa.Integer(), nullable=False),
        sa.Column("config_id", sa.Integer(), nullable=False),
        sa.Column("working_hours_mode", sa.String(length=20), nullable=False),
        sa.Column("full_day_hours", sa.Time(), nullable=True),
        sa.Column("half_day_hours", sa.Time(), nullable=True),
        sa.Column("full_day_buffer_period", sa.Time(), nullable=True),
        sa.Column("half_day_buffer_period", sa.Time(), nullable=True),
        sa.Column("attendance_mode", sa.String(length=40), nullable=False),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("effective_to", sa.Date(), nullable=False),
        sa.Column("changed_by", sa.Integer(), nullable=True),  # deferred FK -> users
        sa.Column("changed_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("history_id", name="pk_working_hours_config_history"),
        sa.ForeignKeyConstraint(
            ["org_id"], ["organizations.org_id"],
            name="fk_working_hours_config_history_org_id_organizations",
        ),
        sa.ForeignKeyConstraint(
            ["config_id"], ["working_hours_config.config_id"],
            name="fk_working_hours_config_history_config_id_working_hours_config",
        ),
        sa.CheckConstraint(
            "working_hours_mode IN ('fixed', 'shift_wise')",
            name="ck_working_hours_config_history_working_hours_mode",
        ),
        sa.CheckConstraint(
            "attendance_mode IN ('consider_all_punch', 'first_and_last_punch_only', "
            "'full_day_on_single_punch', 'default_full_day')",
            name="ck_working_hours_config_history_attendance_mode",
        ),
    )


def downgrade() -> None:
    # Drop in reverse dependency order. Table drops cascade their own indexes.
    op.drop_table("working_hours_config_history")
    op.drop_table("working_hours_config")
    op.drop_index("ix_roster_org_id_roster_date", table_name="roster")
    op.drop_table("roster")
    op.drop_index("uq_employee_weekoffs_employee_id_day_of_week", table_name="employee_weekoffs")
    op.drop_table("employee_weekoffs")
    op.drop_index(
        "ix_shift_assignments_employee_id_effective_from_effective_to",
        table_name="shift_assignments",
    )
    op.drop_table("shift_assignments")
    op.drop_table("shift_day_timings")
    op.drop_index("uq_shifts_org_id_shift_name", table_name="shifts")
    op.drop_table("shifts")
