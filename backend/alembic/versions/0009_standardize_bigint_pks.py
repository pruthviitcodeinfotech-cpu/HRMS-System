"""standardize primary/foreign keys on BIGINT

Standardizes the whole HRMS database on a single primary-key convention: every
primary key and every corresponding foreign-key / actor column is BIGINT.

Only two modules were created with the INTEGER (SERIAL) key convention:

    * Employee Management (0001)
    * Shift Management (0002)

plus a handful of deferred-FK `org_id` columns that were left INTEGER while the
convention was undecided:

    * Settlements (0006): org_id on the 4 owned tables
    * User Management & RBAC (0007): users.org_id, rights_templates.org_id

This migration converts all of those key columns to BIGINT. Because PostgreSQL
refuses to alter the type of a column that participates in a FOREIGN KEY (on
either side), the 32 intra-Employee / intra-Shift FK constraints are dropped
first, the columns are altered, then the constraints are recreated unchanged.

Genuine data columns that merely happened to be INTEGER are intentionally left
untouched (they are not keys):
    employee_documents.file_size_bytes, employee_import_logs.total_rows /
    success_rows / failed_rows, shift_day_timings.duration_minutes.

The BIGINT `-> users` FKs added in 0008 sit on already-BIGINT columns and are
unaffected. The Settlements/RBAC `org_id` columns carry no FK constraint (still
deferred), so they are altered directly with no drop/recreate.

This migration does NOT redesign any table or add/resolve any deferred FK; it
only standardizes key column data types for consistency and referential
integrity.

Revision ID: 0009_standardize_bigint_pks
Revises: 0008_resolve_deferred_user_fks
Create Date: 2026-07-04
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0009_standardize_bigint_pks"
down_revision: Union[str, None] = "0008_resolve_deferred_user_fks"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# (name, source_table, referred_table, [local_cols], [remote_cols])
# The 32 intra-module FKs whose columns are being retyped. None carry an
# ON DELETE action (PostgreSQL default NO ACTION).
_FKS: list[tuple[str, str, str, list[str], list[str]]] = [
    # ----- Employee Management (0001) -----
    ("fk_branches_org_id_organizations", "branches", "organizations", ["org_id"], ["org_id"]),
    ("fk_departments_org_id_organizations", "departments", "organizations", ["org_id"], ["org_id"]),
    ("fk_designations_org_id_organizations", "designations", "organizations", ["org_id"], ["org_id"]),
    ("fk_employees_org_id_organizations", "employees", "organizations", ["org_id"], ["org_id"]),
    ("fk_employees_master_branch_id_branches", "employees", "branches", ["master_branch_id"], ["branch_id"]),
    ("fk_employees_dept_id_departments", "employees", "departments", ["dept_id"], ["dept_id"]),
    ("fk_employees_designation_id_designations", "employees", "designations", ["designation_id"], ["designation_id"]),
    ("fk_employee_bank_details_employee_id_employees", "employee_bank_details", "employees", ["employee_id"], ["employee_id"]),
    ("fk_employee_documents_employee_id_employees", "employee_documents", "employees", ["employee_id"], ["employee_id"]),
    ("fk_employee_emergency_contacts_employee_id_employees", "employee_emergency_contacts", "employees", ["employee_id"], ["employee_id"]),
    ("fk_employee_references_employee_id_employees", "employee_references", "employees", ["employee_id"], ["employee_id"]),
    ("fk_employee_biometrics_employee_id_employees", "employee_biometrics", "employees", ["employee_id"], ["employee_id"]),
    ("fk_employee_punch_branches_employee_id_employees", "employee_punch_branches", "employees", ["employee_id"], ["employee_id"]),
    ("fk_employee_punch_branches_branch_id_branches", "employee_punch_branches", "branches", ["branch_id"], ["branch_id"]),
    ("fk_employee_attendance_permissions_employee_id_employees", "employee_attendance_permissions", "employees", ["employee_id"], ["employee_id"]),
    ("fk_org_attendance_settings_org_id_organizations", "org_attendance_settings", "organizations", ["org_id"], ["org_id"]),
    ("fk_org_attendance_settings_branch_id_branches", "org_attendance_settings", "branches", ["branch_id"], ["branch_id"]),
    ("fk_employee_import_logs_org_id_organizations", "employee_import_logs", "organizations", ["org_id"], ["org_id"]),
    ("fk_employee_tags_employee_id_employees", "employee_tags", "employees", ["employee_id"], ["employee_id"]),
    ("fk_employee_status_history_employee_id_employees", "employee_status_history", "employees", ["employee_id"], ["employee_id"]),
    # ----- Shift Management (0002) -----
    ("fk_shifts_org_id_organizations", "shifts", "organizations", ["org_id"], ["org_id"]),
    ("fk_shift_day_timings_shift_id_shifts", "shift_day_timings", "shifts", ["shift_id"], ["shift_id"]),
    ("fk_shift_assignments_org_id_organizations", "shift_assignments", "organizations", ["org_id"], ["org_id"]),
    ("fk_shift_assignments_employee_id_employees", "shift_assignments", "employees", ["employee_id"], ["employee_id"]),
    ("fk_shift_assignments_shift_id_shifts", "shift_assignments", "shifts", ["shift_id"], ["shift_id"]),
    ("fk_employee_weekoffs_employee_id_employees", "employee_weekoffs", "employees", ["employee_id"], ["employee_id"]),
    ("fk_roster_org_id_organizations", "roster", "organizations", ["org_id"], ["org_id"]),
    ("fk_roster_employee_id_employees", "roster", "employees", ["employee_id"], ["employee_id"]),
    ("fk_roster_shift_id_shifts", "roster", "shifts", ["shift_id"], ["shift_id"]),
    ("fk_working_hours_config_org_id_organizations", "working_hours_config", "organizations", ["org_id"], ["org_id"]),
    ("fk_working_hours_config_history_org_id_organizations", "working_hours_config_history", "organizations", ["org_id"], ["org_id"]),
    ("fk_working_hours_config_history_config_id_working_hours_config", "working_hours_config_history", "working_hours_config", ["config_id"], ["config_id"]),
]


# (table, column) key columns to convert INTEGER -> BIGINT. Data columns are
# deliberately excluded.
_COLUMNS: list[tuple[str, str]] = [
    # ----- Employee Management (0001) -----
    ("organizations", "org_id"),
    ("branches", "branch_id"),
    ("branches", "org_id"),
    ("departments", "dept_id"),
    ("departments", "org_id"),
    ("departments", "created_by"),
    ("designations", "designation_id"),
    ("designations", "org_id"),
    ("designations", "created_by"),
    ("employees", "employee_id"),
    ("employees", "org_id"),
    ("employees", "master_branch_id"),
    ("employees", "dept_id"),
    ("employees", "designation_id"),
    ("employees", "payroll_group_id"),
    ("employees", "created_by"),
    ("employee_bank_details", "bank_detail_id"),
    ("employee_bank_details", "employee_id"),
    ("employee_documents", "document_id"),
    ("employee_documents", "employee_id"),
    ("employee_documents", "uploaded_by"),
    ("employee_emergency_contacts", "emergency_contact_id"),
    ("employee_emergency_contacts", "employee_id"),
    ("employee_references", "reference_id"),
    ("employee_references", "employee_id"),
    ("employee_biometrics", "biometric_id"),
    ("employee_biometrics", "employee_id"),
    ("employee_biometrics", "device_id"),
    ("employee_biometrics", "registered_by"),
    ("employee_punch_branches", "punch_branch_id"),
    ("employee_punch_branches", "employee_id"),
    ("employee_punch_branches", "branch_id"),
    ("employee_punch_branches", "assigned_by"),
    ("employee_attendance_permissions", "att_perm_id"),
    ("employee_attendance_permissions", "employee_id"),
    ("employee_attendance_permissions", "updated_by"),
    ("org_attendance_settings", "setting_id"),
    ("org_attendance_settings", "org_id"),
    ("org_attendance_settings", "branch_id"),
    ("org_attendance_settings", "device_id"),
    ("org_attendance_settings", "updated_by"),
    ("employee_import_logs", "import_log_id"),
    ("employee_import_logs", "org_id"),
    ("employee_import_logs", "initiated_by"),
    ("employee_tags", "tag_id"),
    ("employee_tags", "employee_id"),
    ("employee_tags", "created_by"),
    ("employee_status_history", "status_history_id"),
    ("employee_status_history", "employee_id"),
    ("employee_status_history", "changed_by"),
    # ----- Shift Management (0002) -----
    ("shifts", "shift_id"),
    ("shifts", "org_id"),
    ("shifts", "created_by"),
    ("shift_day_timings", "timing_id"),
    ("shift_day_timings", "shift_id"),
    ("shift_assignments", "assignment_id"),
    ("shift_assignments", "org_id"),
    ("shift_assignments", "employee_id"),
    ("shift_assignments", "shift_id"),
    ("shift_assignments", "assigned_by"),
    ("employee_weekoffs", "weekoff_id"),
    ("employee_weekoffs", "employee_id"),
    ("employee_weekoffs", "updated_by"),
    ("roster", "roster_id"),
    ("roster", "org_id"),
    ("roster", "employee_id"),
    ("roster", "shift_id"),
    ("roster", "created_by"),
    ("roster", "updated_by"),
    ("working_hours_config", "config_id"),
    ("working_hours_config", "org_id"),
    ("working_hours_config", "created_by"),
    ("working_hours_config_history", "history_id"),
    ("working_hours_config_history", "org_id"),
    ("working_hours_config_history", "config_id"),
    ("working_hours_config_history", "changed_by"),
    # ----- Settlements (0006): deferred-FK org_id (no FK constraint) -----
    ("employee_loans_advances", "org_id"),
    ("loan_advance_transactions", "org_id"),
    ("employee_arrears", "org_id"),
    ("arrears_transactions", "org_id"),
    # ----- User Management & RBAC (0007): deferred-FK org_id (no FK constraint) -----
    ("users", "org_id"),
    ("rights_templates", "org_id"),
]


def upgrade() -> None:
    # 1. Drop the FK constraints that span the columns being retyped.
    for name, source_table, _rt, _lc, _rc in _FKS:
        op.drop_constraint(name, source_table, type_="foreignkey")

    # 2. Convert every key column INTEGER -> BIGINT.
    for table, column in _COLUMNS:
        op.alter_column(
            table,
            column,
            existing_type=sa.Integer(),
            type_=sa.BigInteger(),
        )

    # 3. Recreate the FK constraints (unchanged) on the now-BIGINT columns.
    for name, source_table, referred_table, local_cols, remote_cols in _FKS:
        op.create_foreign_key(name, source_table, referred_table, local_cols, remote_cols)


def downgrade() -> None:
    # Reverse: drop FKs, revert columns to INTEGER, recreate FKs.
    for name, source_table, _rt, _lc, _rc in reversed(_FKS):
        op.drop_constraint(name, source_table, type_="foreignkey")

    for table, column in reversed(_COLUMNS):
        op.alter_column(
            table,
            column,
            existing_type=sa.BigInteger(),
            type_=sa.Integer(),
        )

    for name, source_table, referred_table, local_cols, remote_cols in reversed(_FKS):
        op.create_foreign_key(name, source_table, referred_table, local_cols, remote_cols)
