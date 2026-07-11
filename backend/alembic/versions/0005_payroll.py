"""payroll

Creates the Payroll module schema: payroll_settings, payroll_groups,
employee_payroll_group_assignments, payroll_salary_cycles,
attendance_adjustments, attendance_adjustment_penalties,
attendance_adjustment_extra_hours, payroll_column_settings,
finalized_payroll_runs, payroll_computed_rows.

This module's approved architecture uses BIGINT `id` primary keys.

DEFERRED cross-module FOREIGN KEY constraints (columns created, constraints not):
    * employee_id -> employees (Employee Management built, but its approved schema
      uses employees.employee_id (INTEGER) whereas THIS module references
      employees.id (BIGINT); deferred pending a project-wide primary-key
      convention decision). Columns are BIGINT.
    * created_by / updated_by / assigned_by / adjusted_by / computed_by /
      finalized_by / definalized_by -> users (User Management, not yet built).

Revision ID: 0005_payroll
Revises: 0004_approval_requests
Create Date: 2026-07-04
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0005_payroll"
down_revision: Union[str, None] = "0004_approval_requests"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ----- payroll_settings --------------------------------------------------
    op.create_table(
        "payroll_settings",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("org_id", sa.BigInteger(), nullable=False),
        sa.Column("working_hour_type", sa.String(length=20), server_default=sa.text("'fixed'"), nullable=False),
        sa.Column("full_day_working_hours", sa.Time(), server_default=sa.text("'08:00'"), nullable=False),
        sa.Column("half_day_working_hours", sa.Time(), server_default=sa.text("'04:00'"), nullable=False),
        sa.Column("attendance_mode", sa.String(length=30), server_default=sa.text("'consider_all_punch'"), nullable=False),
        sa.Column("off_day_compensation", sa.String(length=30), server_default=sa.text("'monetary_compensation'"), nullable=False),
        sa.Column("off_day_wage_multiplier", sa.Numeric(precision=4, scale=2), server_default=sa.text("1.00"), nullable=False),
        sa.Column("daily_wage_formula", sa.String(length=50), server_default=sa.text("'monthly_calendar_days'"), nullable=False),
        sa.Column("overtime_type", sa.String(length=30), server_default=sa.text("'fixed_per_hour_pay'"), nullable=False),
        sa.Column("overtime_hourly_multiplier", sa.Numeric(precision=4, scale=2), server_default=sa.text("0.00"), nullable=False),
        sa.Column("overtime_buffer_period", sa.Time(), server_default=sa.text("'00:00'"), nullable=False),
        sa.Column("overtime_period_interval", sa.String(length=10), server_default=sa.text("'15 Min'"), nullable=True),
        sa.Column("full_day_penalty_enabled", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("half_day_penalty_enabled", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("late_coming_penalty_enabled", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("grace_time", sa.Time(), server_default=sa.text("'00:00'"), nullable=False),
        sa.Column("updated_by", sa.BigInteger(), nullable=True),  # deferred FK -> users
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_payroll_settings"),
        sa.UniqueConstraint("org_id", name="uq_payroll_settings_org_id"),
    )

    # ----- payroll_groups ----------------------------------------------------
    op.create_table(
        "payroll_groups",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("org_id", sa.BigInteger(), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("payroll_type", sa.String(length=30), nullable=False),
        sa.Column("is_default", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", sa.BigInteger(), nullable=True),  # deferred FK -> users
        sa.Column("updated_by", sa.BigInteger(), nullable=True),  # deferred FK -> users
        sa.PrimaryKeyConstraint("id", name="pk_payroll_groups"),
        sa.CheckConstraint(
            "payroll_type IN ('monthly_without_compliance', 'monthly_with_compliance', 'hourly_payroll')",
            name="ck_payroll_groups_payroll_type",
        ),
    )
    op.create_index(
        "uq_payroll_groups_org_id_name",
        "payroll_groups",
        ["org_id", "name"],
        unique=True,
        postgresql_where=sa.text("is_deleted = false"),
    )

    # ----- employee_payroll_group_assignments --------------------------------
    op.create_table(
        "employee_payroll_group_assignments",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("employee_id", sa.BigInteger(), nullable=False),  # deferred FK -> employees
        sa.Column("payroll_group_id", sa.BigInteger(), nullable=False),
        sa.Column("salary_type", sa.String(length=20), server_default=sa.text("'monthly'"), nullable=False),
        sa.Column("assigned_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("assigned_by", sa.BigInteger(), nullable=False),  # deferred FK -> users (NOT NULL)
        sa.Column("previous_group_id", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_employee_payroll_group_assignments"),
        sa.ForeignKeyConstraint(
            ["payroll_group_id"], ["payroll_groups.id"],
            name="fk_emp_payroll_grp_assign_payroll_group_id_payroll_groups",
        ),
        sa.ForeignKeyConstraint(
            ["previous_group_id"], ["payroll_groups.id"],
            name="fk_emp_payroll_grp_assign_previous_group_id_payroll_groups",
        ),
        sa.UniqueConstraint("employee_id", name="uq_employee_payroll_group_assignments_employee_id"),
        sa.CheckConstraint(
            "salary_type IN ('monthly', 'hourly')",
            name="ck_employee_payroll_group_assignments_salary_type",
        ),
    )

    # ----- payroll_salary_cycles ---------------------------------------------
    op.create_table(
        "payroll_salary_cycles",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("payroll_group_id", sa.BigInteger(), nullable=False),
        sa.Column("cycle_date", sa.Date(), nullable=False),
        sa.Column("is_finalized", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", sa.BigInteger(), nullable=True),  # deferred FK -> users
        sa.PrimaryKeyConstraint("id", name="pk_payroll_salary_cycles"),
        sa.ForeignKeyConstraint(
            ["payroll_group_id"], ["payroll_groups.id"],
            name="fk_payroll_salary_cycles_payroll_group_id_payroll_groups",
        ),
        sa.UniqueConstraint(
            "payroll_group_id", "cycle_date",
            name="uq_payroll_salary_cycles_payroll_group_id_cycle_date",
        ),
    )

    # ----- attendance_adjustments --------------------------------------------
    op.create_table(
        "attendance_adjustments",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("org_id", sa.BigInteger(), nullable=False),
        sa.Column("employee_id", sa.BigInteger(), nullable=False),  # deferred FK -> employees
        sa.Column("attendance_date", sa.Date(), nullable=False),
        sa.Column("original_status", sa.String(length=5), nullable=True),
        sa.Column("adjusted_status", sa.String(length=5), nullable=False),
        sa.Column("is_forced_overwrite", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("has_punch_error", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("adjustment_source", sa.String(length=20), server_default=sa.text("'spreadsheet'"), nullable=False),
        sa.Column("adjusted_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("adjusted_by", sa.BigInteger(), nullable=False),  # deferred FK -> users (NOT NULL)
        sa.PrimaryKeyConstraint("id", name="pk_attendance_adjustments"),
        sa.UniqueConstraint(
            "employee_id", "attendance_date",
            name="uq_attendance_adjustments_employee_id_attendance_date",
        ),
        sa.CheckConstraint(
            "adjusted_status IN ('FD', 'HD', 'A', 'WO', 'LWP')",
            name="ck_attendance_adjustments_adjusted_status",
        ),
    )
    op.create_index(
        "ix_attendance_adjustments_org_id_attendance_date",
        "attendance_adjustments", ["org_id", "attendance_date"],
    )
    op.create_index(
        "ix_attendance_adjustments_employee_id_attendance_date",
        "attendance_adjustments", ["employee_id", "attendance_date"],
    )

    # ----- attendance_adjustment_penalties -----------------------------------
    op.create_table(
        "attendance_adjustment_penalties",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("employee_id", sa.BigInteger(), nullable=False),  # deferred FK -> employees
        sa.Column("attendance_date", sa.Date(), nullable=False),
        sa.Column("penalty_amount", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("remark", sa.Text(), nullable=True),
        sa.Column("is_removed", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", sa.BigInteger(), nullable=False),  # deferred FK -> users (NOT NULL)
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_attendance_adjustment_penalties"),
    )
    op.create_index(
        "ix_attendance_adjustment_penalties_employee_id_attendance_date",
        "attendance_adjustment_penalties", ["employee_id", "attendance_date"],
    )

    # ----- attendance_adjustment_extra_hours ---------------------------------
    op.create_table(
        "attendance_adjustment_extra_hours",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("employee_id", sa.BigInteger(), nullable=False),  # deferred FK -> employees
        sa.Column("attendance_date", sa.Date(), nullable=False),
        sa.Column("extra_hours", sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column("remark", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", sa.BigInteger(), nullable=False),  # deferred FK -> users (NOT NULL)
        sa.PrimaryKeyConstraint("id", name="pk_attendance_adjustment_extra_hours"),
        sa.UniqueConstraint(
            "employee_id", "attendance_date",
            name="uq_att_adjust_extra_hours_employee_id_attendance_date",
        ),
    )

    # ----- payroll_column_settings -------------------------------------------
    op.create_table(
        "payroll_column_settings",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("payroll_group_id", sa.BigInteger(), nullable=False),
        sa.Column("column_key", sa.String(length=50), nullable=False),
        sa.Column("column_label", sa.String(length=100), nullable=False),
        sa.Column("is_visible", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("display_order", sa.SmallInteger(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_by", sa.BigInteger(), nullable=True),  # deferred FK -> users
        sa.PrimaryKeyConstraint("id", name="pk_payroll_column_settings"),
        sa.ForeignKeyConstraint(
            ["payroll_group_id"], ["payroll_groups.id"],
            name="fk_payroll_column_settings_payroll_group_id_payroll_groups",
        ),
        sa.UniqueConstraint(
            "payroll_group_id", "column_key",
            name="uq_payroll_column_settings_payroll_group_id_column_key",
        ),
    )

    # ----- finalized_payroll_runs --------------------------------------------
    op.create_table(
        "finalized_payroll_runs",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("org_id", sa.BigInteger(), nullable=False),
        sa.Column("payroll_group_id", sa.BigInteger(), nullable=False),
        sa.Column("cycle_from", sa.Date(), nullable=False),
        sa.Column("cycle_to", sa.Date(), nullable=False),
        sa.Column("payroll_module", sa.String(length=30), nullable=False),
        sa.Column("finalized_amount", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("finalized_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("finalized_by", sa.BigInteger(), nullable=False),  # deferred FK -> users (NOT NULL)
        sa.Column("paid_amount", sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("payment_status", sa.String(length=20), server_default=sa.text("'pending'"), nullable=False),
        sa.Column("is_definalized", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("definalized_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("definalized_by", sa.BigInteger(), nullable=True),  # deferred FK -> users
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_finalized_payroll_runs"),
        sa.ForeignKeyConstraint(
            ["payroll_group_id"], ["payroll_groups.id"],
            name="fk_finalized_payroll_runs_payroll_group_id_payroll_groups",
        ),
        sa.CheckConstraint(
            "payment_status IN ('pending', 'paid', 'partial')",
            name="ck_finalized_payroll_runs_payment_status",
        ),
    )
    op.create_index(
        "ix_finalized_payroll_runs_org_id_payroll_group_id_cycle_from",
        "finalized_payroll_runs", ["org_id", "payroll_group_id", "cycle_from"],
    )

    # ----- payroll_computed_rows ---------------------------------------------
    op.create_table(
        "payroll_computed_rows",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("payroll_group_id", sa.BigInteger(), nullable=False),
        sa.Column("employee_id", sa.BigInteger(), nullable=False),  # deferred FK -> employees
        sa.Column("cycle_from", sa.Date(), nullable=False),
        sa.Column("cycle_to", sa.Date(), nullable=False),
        sa.Column("total_days", sa.SmallInteger(), nullable=False),
        sa.Column("full_day_count", sa.SmallInteger(), server_default=sa.text("0"), nullable=False),
        sa.Column("half_day_count", sa.SmallInteger(), server_default=sa.text("0"), nullable=False),
        sa.Column("off_day_count", sa.SmallInteger(), server_default=sa.text("0"), nullable=False),
        sa.Column("paid_leave_count", sa.Numeric(precision=5, scale=1), server_default=sa.text("0"), nullable=False),
        sa.Column("paid_day_count", sa.Numeric(precision=5, scale=1), server_default=sa.text("0"), nullable=False),
        sa.Column("unpaid_day_count", sa.Numeric(precision=5, scale=1), server_default=sa.text("0"), nullable=False),
        sa.Column("daily_wage", sa.Numeric(precision=10, scale=2), server_default=sa.text("0"), nullable=False),
        sa.Column("gross_wages", sa.Numeric(precision=12, scale=2), server_default=sa.text("0"), nullable=False),
        sa.Column("overtime_amount", sa.Numeric(precision=10, scale=2), server_default=sa.text("0"), nullable=False),
        sa.Column("penalties_amount", sa.Numeric(precision=10, scale=2), server_default=sa.text("0"), nullable=False),
        sa.Column("extras_amount", sa.Numeric(precision=10, scale=2), server_default=sa.text("0"), nullable=False),
        sa.Column("gross_earnings", sa.Numeric(precision=12, scale=2), server_default=sa.text("0"), nullable=False),
        sa.Column("loan_advance_deduction", sa.Numeric(precision=10, scale=2), server_default=sa.text("0"), nullable=False),
        sa.Column("arrears_amount", sa.Numeric(precision=10, scale=2), server_default=sa.text("0"), nullable=False),
        sa.Column("to_pay", sa.Numeric(precision=12, scale=2), server_default=sa.text("0"), nullable=False),
        sa.Column("balance_arrears", sa.Numeric(precision=10, scale=2), server_default=sa.text("0"), nullable=False),
        sa.Column("payment_method", sa.String(length=30), nullable=True),
        sa.Column("is_finalized", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("finalized_run_id", sa.BigInteger(), nullable=True),
        sa.Column("computed_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("computed_by", sa.BigInteger(), nullable=True),  # deferred FK -> users
        sa.PrimaryKeyConstraint("id", name="pk_payroll_computed_rows"),
        sa.ForeignKeyConstraint(
            ["payroll_group_id"], ["payroll_groups.id"],
            name="fk_payroll_computed_rows_payroll_group_id_payroll_groups",
        ),
        sa.ForeignKeyConstraint(
            ["finalized_run_id"], ["finalized_payroll_runs.id"],
            name="fk_payroll_computed_rows_finalized_run_id_final_runs",
        ),
        sa.UniqueConstraint(
            "payroll_group_id", "employee_id", "cycle_from", "cycle_to",
            name="uq_payroll_computed_rows_group_employee_cycle",
        ),
    )
    op.create_index(
        "ix_payroll_computed_rows_payroll_group_id_cycle_from_cycle_to",
        "payroll_computed_rows", ["payroll_group_id", "cycle_from", "cycle_to"],
    )
    op.create_index(
        "ix_payroll_computed_rows_employee_id_is_finalized",
        "payroll_computed_rows", ["employee_id", "is_finalized"],
    )


def downgrade() -> None:
    op.drop_index("ix_payroll_computed_rows_employee_id_is_finalized", table_name="payroll_computed_rows")
    op.drop_index("ix_payroll_computed_rows_payroll_group_id_cycle_from_cycle_to", table_name="payroll_computed_rows")
    op.drop_table("payroll_computed_rows")
    op.drop_index("ix_finalized_payroll_runs_org_id_payroll_group_id_cycle_from", table_name="finalized_payroll_runs")
    op.drop_table("finalized_payroll_runs")
    op.drop_table("payroll_column_settings")
    op.drop_table("attendance_adjustment_extra_hours")
    op.drop_index("ix_attendance_adjustment_penalties_employee_id_attendance_date", table_name="attendance_adjustment_penalties")
    op.drop_table("attendance_adjustment_penalties")
    op.drop_index("ix_attendance_adjustments_employee_id_attendance_date", table_name="attendance_adjustments")
    op.drop_index("ix_attendance_adjustments_org_id_attendance_date", table_name="attendance_adjustments")
    op.drop_table("attendance_adjustments")
    op.drop_table("payroll_salary_cycles")
    op.drop_table("employee_payroll_group_assignments")
    op.drop_index("uq_payroll_groups_org_id_name", table_name="payroll_groups")
    op.drop_table("payroll_groups")
    op.drop_table("payroll_settings")
