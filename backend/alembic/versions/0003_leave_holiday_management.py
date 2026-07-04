"""leave and holiday management

Creates the Leave & Holiday Management module schema: leave_settings,
leave_types, employee_leave_allocations, employee_leave_balances,
leave_balance_adjustments, holiday_templates, holiday_template_items,
employee_holiday_assignments, leave_requests.

This module's approved architecture uses BIGINT `id` primary keys.

NOT IMPLEMENTED HERE: `approval_requests` is authoritatively owned by the
Approval Requests module (different canonical schema) and is excluded per the
"never implement another module" rule.

DEFERRED cross-module FOREIGN KEY constraints (columns created, constraints not):
    * employee_id -> employees : DEFERRED. Employee Management is built, but its
      approved schema uses employees.employee_id (INTEGER) whereas THIS module's
      approved schema references employees.id (BIGINT). The FK is deferred pending
      a project-wide primary-key convention decision (INTEGER vs BIGINT). Columns
      are created as BIGINT, matching this module's approved architecture.
    * created_by / updated_by / adjusted_by / reviewed_by / assigned_by -> users
      (User Management, not yet built).

Revision ID: 0003_leave_holiday_management
Revises: 0002_shift_management
Create Date: 2026-07-04
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0003_leave_holiday_management"
down_revision: Union[str, None] = "0002_shift_management"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ----- leave_settings ----------------------------------------------------
    op.create_table(
        "leave_settings",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("org_id", sa.BigInteger(), nullable=False),
        sa.Column("leave_cycle", sa.String(length=20), server_default=sa.text("'calendar_year'"), nullable=False),
        sa.Column("cycle_start_month", sa.SmallInteger(), server_default=sa.text("1"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", sa.BigInteger(), nullable=True),  # deferred FK -> users
        sa.Column("updated_by", sa.BigInteger(), nullable=True),  # deferred FK -> users
        sa.PrimaryKeyConstraint("id", name="pk_leave_settings"),
        sa.UniqueConstraint("org_id", name="uq_leave_settings_org_id"),
    )

    # ----- leave_types -------------------------------------------------------
    op.create_table(
        "leave_types",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("org_id", sa.BigInteger(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("alias", sa.String(length=50), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("auto_allocation_count", sa.Numeric(precision=6, scale=2), nullable=False),
        sa.Column("allocation_frequency", sa.String(length=20), server_default=sa.text("'monthly'"), nullable=False),
        sa.Column("carry_forward_count", sa.Numeric(precision=6, scale=2), server_default=sa.text("0"), nullable=False),
        sa.Column("carry_forward_frequency", sa.String(length=20), server_default=sa.text("'monthly'"), nullable=False),
        sa.Column("encashment_enabled", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("encashment_limit", sa.Numeric(precision=6, scale=2), nullable=True),
        sa.Column("encashment_frequency", sa.String(length=20), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", sa.BigInteger(), nullable=True),  # deferred FK -> users
        sa.Column("updated_by", sa.BigInteger(), nullable=True),  # deferred FK -> users
        sa.PrimaryKeyConstraint("id", name="pk_leave_types"),
        sa.UniqueConstraint("org_id", "alias", name="uq_leave_types_org_id_alias"),
        sa.CheckConstraint(
            "allocation_frequency IN ('monthly', 'yearly')",
            name="ck_leave_types_allocation_frequency",
        ),
        sa.CheckConstraint(
            "carry_forward_frequency IN ('monthly', 'yearly')",
            name="ck_leave_types_carry_forward_frequency",
        ),
        sa.CheckConstraint(
            "encashment_frequency IN ('monthly', 'yearly')",
            name="ck_leave_types_encashment_frequency",
        ),
        sa.CheckConstraint(
            "NOT encashment_enabled OR encashment_limit IS NOT NULL",
            name="ck_leave_types_encashment_limit_required",
        ),
    )

    # ----- employee_leave_allocations ----------------------------------------
    op.create_table(
        "employee_leave_allocations",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("employee_id", sa.BigInteger(), nullable=False),  # deferred FK -> employees
        sa.Column("leave_type_id", sa.BigInteger(), nullable=False),
        sa.Column("cycle_year", sa.SmallInteger(), nullable=False),
        sa.Column("cycle_period", sa.String(length=20), nullable=True),
        sa.Column("allocated_days", sa.Numeric(precision=6, scale=2), nullable=False),
        sa.Column("allocation_date", sa.Date(), nullable=False),
        sa.Column("allocation_source", sa.String(length=20), server_default=sa.text("'auto'"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", sa.BigInteger(), nullable=True),  # deferred FK -> users
        sa.PrimaryKeyConstraint("id", name="pk_employee_leave_allocations"),
        sa.ForeignKeyConstraint(
            ["leave_type_id"], ["leave_types.id"],
            name="fk_employee_leave_allocations_leave_type_id_leave_types",
        ),
        sa.UniqueConstraint(
            "employee_id", "leave_type_id", "cycle_year", "cycle_period",
            name="uq_employee_leave_allocations_employee_id_leave_type_id_cycle_year_cycle_period",
        ),
    )

    # ----- employee_leave_balances -------------------------------------------
    op.create_table(
        "employee_leave_balances",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("employee_id", sa.BigInteger(), nullable=False),  # deferred FK -> employees
        sa.Column("leave_type_id", sa.BigInteger(), nullable=False),
        sa.Column("cycle_year", sa.SmallInteger(), nullable=False),
        sa.Column("opening_balance", sa.Numeric(precision=6, scale=2), server_default=sa.text("0"), nullable=False),
        sa.Column("allocated", sa.Numeric(precision=6, scale=2), server_default=sa.text("0"), nullable=False),
        sa.Column("used", sa.Numeric(precision=6, scale=2), server_default=sa.text("0"), nullable=False),
        sa.Column("carried_forward", sa.Numeric(precision=6, scale=2), server_default=sa.text("0"), nullable=False),
        sa.Column("encashed", sa.Numeric(precision=6, scale=2), server_default=sa.text("0"), nullable=False),
        sa.Column("adjusted", sa.Numeric(precision=6, scale=2), server_default=sa.text("0"), nullable=False),
        sa.Column("closing_balance", sa.Numeric(precision=6, scale=2), server_default=sa.text("0"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_by", sa.BigInteger(), nullable=True),  # deferred FK -> users
        sa.PrimaryKeyConstraint("id", name="pk_employee_leave_balances"),
        sa.ForeignKeyConstraint(
            ["leave_type_id"], ["leave_types.id"],
            name="fk_employee_leave_balances_leave_type_id_leave_types",
        ),
        sa.UniqueConstraint(
            "employee_id", "leave_type_id", "cycle_year",
            name="uq_employee_leave_balances_employee_id_leave_type_id_cycle_year",
        ),
    )

    # ----- leave_balance_adjustments -----------------------------------------
    op.create_table(
        "leave_balance_adjustments",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("employee_id", sa.BigInteger(), nullable=False),  # deferred FK -> employees
        sa.Column("leave_type_id", sa.BigInteger(), nullable=False),
        sa.Column("adjustment_type", sa.String(length=20), nullable=False),
        sa.Column("delta", sa.Numeric(precision=6, scale=2), nullable=False),
        sa.Column("new_balance", sa.Numeric(precision=6, scale=2), nullable=False),
        sa.Column("remarks", sa.Text(), nullable=True),
        sa.Column("cycle_year", sa.SmallInteger(), nullable=False),
        sa.Column("adjusted_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("adjusted_by", sa.BigInteger(), nullable=False),  # deferred FK -> users (NOT NULL)
        sa.PrimaryKeyConstraint("id", name="pk_leave_balance_adjustments"),
        sa.ForeignKeyConstraint(
            ["leave_type_id"], ["leave_types.id"],
            name="fk_leave_balance_adjustments_leave_type_id_leave_types",
        ),
    )
    op.create_index(
        "ix_leave_balance_adjustments_employee_id_cycle_year",
        "leave_balance_adjustments",
        ["employee_id", "cycle_year"],
    )

    # ----- holiday_templates -------------------------------------------------
    op.create_table(
        "holiday_templates",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("org_id", sa.BigInteger(), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("holiday_count", sa.SmallInteger(), server_default=sa.text("0"), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", sa.BigInteger(), nullable=True),  # deferred FK -> users
        sa.Column("updated_by", sa.BigInteger(), nullable=True),  # deferred FK -> users
        sa.PrimaryKeyConstraint("id", name="pk_holiday_templates"),
    )
    op.create_index(
        "uq_holiday_templates_org_id_name",
        "holiday_templates",
        ["org_id", "name"],
        unique=True,
        postgresql_where=sa.text("is_deleted = false"),
    )

    # ----- holiday_template_items --------------------------------------------
    op.create_table(
        "holiday_template_items",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("template_id", sa.BigInteger(), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("day_of_week", sa.String(length=15), nullable=True),
        sa.Column("duration_days", sa.SmallInteger(), server_default=sa.text("1"), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", sa.BigInteger(), nullable=True),  # deferred FK -> users
        sa.PrimaryKeyConstraint("id", name="pk_holiday_template_items"),
        sa.ForeignKeyConstraint(
            ["template_id"], ["holiday_templates.id"],
            name="fk_holiday_template_items_template_id_holiday_templates",
        ),
        sa.CheckConstraint(
            "end_date >= start_date",
            name="ck_holiday_template_items_end_date_after_start_date",
        ),
    )
    op.create_index(
        "ix_holiday_template_items_template_id_start_date",
        "holiday_template_items",
        ["template_id", "start_date"],
    )

    # ----- employee_holiday_assignments --------------------------------------
    op.create_table(
        "employee_holiday_assignments",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("employee_id", sa.BigInteger(), nullable=False),  # deferred FK -> employees
        sa.Column("template_id", sa.BigInteger(), nullable=True),
        sa.Column("assigned_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("assigned_by", sa.BigInteger(), nullable=False),  # deferred FK -> users (NOT NULL)
        sa.Column("previous_template_id", sa.BigInteger(), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_employee_holiday_assignments"),
        sa.ForeignKeyConstraint(
            ["template_id"], ["holiday_templates.id"],
            name="fk_employee_holiday_assignments_template_id_holiday_templates",
        ),
        sa.ForeignKeyConstraint(
            ["previous_template_id"], ["holiday_templates.id"],
            name="fk_employee_holiday_assignments_previous_template_id_holiday_templates",
        ),
        sa.UniqueConstraint("employee_id", name="uq_employee_holiday_assignments_employee_id"),
    )

    # ----- leave_requests ----------------------------------------------------
    op.create_table(
        "leave_requests",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("employee_id", sa.BigInteger(), nullable=False),  # deferred FK -> employees
        sa.Column("leave_type_id", sa.BigInteger(), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("duration_days", sa.Numeric(precision=4, scale=1), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=20), server_default=sa.text("'pending'"), nullable=False),
        sa.Column("applied_on", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewed_by", sa.BigInteger(), nullable=True),  # deferred FK -> users
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_leave_requests"),
        sa.ForeignKeyConstraint(
            ["leave_type_id"], ["leave_types.id"],
            name="fk_leave_requests_leave_type_id_leave_types",
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'approved', 'rejected')", name="ck_leave_requests_status"
        ),
        sa.CheckConstraint(
            "end_date >= start_date", name="ck_leave_requests_end_date_after_start_date"
        ),
    )
    op.create_index("ix_leave_requests_employee_id_status", "leave_requests", ["employee_id", "status"])
    op.create_index("ix_leave_requests_leave_type_id_status", "leave_requests", ["leave_type_id", "status"])


def downgrade() -> None:
    op.drop_index("ix_leave_requests_leave_type_id_status", table_name="leave_requests")
    op.drop_index("ix_leave_requests_employee_id_status", table_name="leave_requests")
    op.drop_table("leave_requests")
    op.drop_table("employee_holiday_assignments")
    op.drop_index(
        "ix_holiday_template_items_template_id_start_date", table_name="holiday_template_items"
    )
    op.drop_table("holiday_template_items")
    op.drop_index("uq_holiday_templates_org_id_name", table_name="holiday_templates")
    op.drop_table("holiday_templates")
    op.drop_index(
        "ix_leave_balance_adjustments_employee_id_cycle_year",
        table_name="leave_balance_adjustments",
    )
    op.drop_table("leave_balance_adjustments")
    op.drop_table("employee_leave_balances")
    op.drop_table("employee_leave_allocations")
    op.drop_table("leave_types")
    op.drop_table("leave_settings")
