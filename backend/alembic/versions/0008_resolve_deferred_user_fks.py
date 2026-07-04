"""resolve deferred user foreign keys

Adds the previously-deferred cross-module FOREIGN KEY constraints that reference
the now-existing `users` table, for the modules whose audit/actor columns are
BIGINT (type-compatible with users.id BIGINT):

    * Leave & Holiday Management (0003)
    * Approval Requests (0004)
    * Payroll (0005)
    * Settlements (0006)

NOT resolved here (remain deferred): the `-> users` columns in the Employee
Management (0001) and Shift Management (0002) modules are INTEGER (those modules
use the SERIAL/INTEGER primary-key convention) and are therefore NOT type
-compatible with users.id (BIGINT). Wiring them requires the pending project
-wide primary-key convention decision (INTEGER vs BIGINT) and a type change,
which is out of scope for this migration.

No ON DELETE action is specified for these actor columns (the source module
architectures define none) -> PostgreSQL default (NO ACTION).

Revision ID: 0008_resolve_deferred_user_fks
Revises: 0007_user_management_rbac
Create Date: 2026-07-04
"""

from collections.abc import Sequence
from typing import Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0008_resolve_deferred_user_fks"
down_revision: Union[str, None] = "0007_user_management_rbac"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# (source_table, column, constraint_name) -> users.id
_USER_FKS: list[tuple[str, str, str]] = [
    # ----- Leave & Holiday Management (0003) -----
    ("leave_settings", "created_by", "fk_leave_settings_created_by_users"),
    ("leave_settings", "updated_by", "fk_leave_settings_updated_by_users"),
    ("leave_types", "created_by", "fk_leave_types_created_by_users"),
    ("leave_types", "updated_by", "fk_leave_types_updated_by_users"),
    ("employee_leave_allocations", "created_by", "fk_employee_leave_allocations_created_by_users"),
    ("employee_leave_balances", "updated_by", "fk_employee_leave_balances_updated_by_users"),
    ("leave_balance_adjustments", "adjusted_by", "fk_leave_balance_adjustments_adjusted_by_users"),
    ("holiday_templates", "created_by", "fk_holiday_templates_created_by_users"),
    ("holiday_templates", "updated_by", "fk_holiday_templates_updated_by_users"),
    ("holiday_template_items", "created_by", "fk_holiday_template_items_created_by_users"),
    ("employee_holiday_assignments", "assigned_by", "fk_employee_holiday_assignments_assigned_by_users"),
    ("leave_requests", "reviewed_by", "fk_leave_requests_reviewed_by_users"),
    # ----- Approval Requests (0004) -----
    ("approval_requests", "reviewed_by", "fk_approval_requests_reviewed_by_users"),
    ("login_reset_requests", "reviewed_by", "fk_login_reset_requests_reviewed_by_users"),
    # ----- Payroll (0005) -----
    ("payroll_settings", "updated_by", "fk_payroll_settings_updated_by_users"),
    ("payroll_groups", "created_by", "fk_payroll_groups_created_by_users"),
    ("payroll_groups", "updated_by", "fk_payroll_groups_updated_by_users"),
    ("employee_payroll_group_assignments", "assigned_by", "fk_employee_payroll_group_assignments_assigned_by_users"),
    ("payroll_salary_cycles", "created_by", "fk_payroll_salary_cycles_created_by_users"),
    ("attendance_adjustments", "adjusted_by", "fk_attendance_adjustments_adjusted_by_users"),
    ("attendance_adjustment_penalties", "created_by", "fk_attendance_adjustment_penalties_created_by_users"),
    ("attendance_adjustment_extra_hours", "created_by", "fk_attendance_adjustment_extra_hours_created_by_users"),
    ("payroll_column_settings", "updated_by", "fk_payroll_column_settings_updated_by_users"),
    ("finalized_payroll_runs", "finalized_by", "fk_finalized_payroll_runs_finalized_by_users"),
    ("finalized_payroll_runs", "definalized_by", "fk_finalized_payroll_runs_definalized_by_users"),
    ("payroll_computed_rows", "computed_by", "fk_payroll_computed_rows_computed_by_users"),
    # ----- Settlements (0006) -----
    ("employee_loans_advances", "created_by", "fk_employee_loans_advances_created_by_users"),
    ("employee_loans_advances", "updated_by", "fk_employee_loans_advances_updated_by_users"),
    ("loan_advance_transactions", "created_by", "fk_loan_advance_transactions_created_by_users"),
    ("arrears_transactions", "created_by", "fk_arrears_transactions_created_by_users"),
]


def upgrade() -> None:
    for source_table, column, name in _USER_FKS:
        op.create_foreign_key(name, source_table, "users", [column], ["id"])


def downgrade() -> None:
    for source_table, _column, name in reversed(_USER_FKS):
        op.drop_constraint(name, source_table, type_="foreignkey")
