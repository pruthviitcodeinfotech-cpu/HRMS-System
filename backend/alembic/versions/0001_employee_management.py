"""employee management

Creates the Employee Management module schema: organizations, branches,
departments, designations, employees, and the employee satellite/config tables.

Cross-module FOREIGN KEY constraints are intentionally DEFERRED (columns are
created, constraints are not) until their owning modules exist:
    * created_by / updated_by / uploaded_by / registered_by / assigned_by /
      initiated_by / changed_by  ->  users            (User Management)
    * employees.payroll_group_id ->  payroll_groups   (Payroll)
    * employee_biometrics.device_id / org_attendance_settings.device_id
                                  ->  biometric_devices (Hardware / Biometric)

Revision ID: 0001_employee_management
Revises:
Create Date: 2026-07-04
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0001_employee_management"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ----- organizations -----------------------------------------------------
    op.create_table(
        "organizations",
        sa.Column("org_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("org_code", sa.String(length=20), nullable=False),
        sa.Column("org_name", sa.String(length=200), nullable=False),
        sa.Column("contact_phone", sa.String(length=20), nullable=True),
        sa.Column("contact_email", sa.String(length=150), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("org_id", name="pk_organizations"),
        sa.UniqueConstraint("org_code", name="uq_organizations_org_code"),
    )

    # ----- branches ----------------------------------------------------------
    op.create_table(
        "branches",
        sa.Column("branch_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("org_id", sa.Integer(), nullable=False),
        sa.Column("branch_name", sa.String(length=200), nullable=False),
        sa.Column("logo_url", sa.Text(), nullable=True),
        sa.Column("gstin", sa.String(length=20), nullable=True),
        sa.Column("mobile_number", sa.String(length=20), nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("landmark", sa.String(length=200), nullable=True),
        sa.Column("pin_code", sa.String(length=10), nullable=True),
        sa.Column("city", sa.String(length=100), nullable=True),
        sa.Column("state", sa.String(length=100), nullable=True),
        sa.Column("country", sa.String(length=100), nullable=True),
        sa.Column("industry_type", sa.String(length=100), nullable=True),
        sa.Column("latitude", sa.Numeric(precision=10, scale=7), nullable=True),
        sa.Column("longitude", sa.Numeric(precision=10, scale=7), nullable=True),
        sa.Column("allowed_radius_meters", sa.SmallInteger(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("branch_id", name="pk_branches"),
        sa.ForeignKeyConstraint(
            ["org_id"], ["organizations.org_id"], name="fk_branches_org_id_organizations"
        ),
    )

    # ----- departments -------------------------------------------------------
    op.create_table(
        "departments",
        sa.Column("dept_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("org_id", sa.Integer(), nullable=False),
        sa.Column("dept_name", sa.String(length=150), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=True),  # deferred FK -> users
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("dept_id", name="pk_departments"),
        sa.ForeignKeyConstraint(
            ["org_id"], ["organizations.org_id"], name="fk_departments_org_id_organizations"
        ),
    )
    op.create_index(
        "uq_departments_org_id_dept_name",
        "departments",
        ["org_id", "dept_name"],
        unique=True,
        postgresql_where=sa.text("is_deleted = false"),
    )

    # ----- designations ------------------------------------------------------
    op.create_table(
        "designations",
        sa.Column("designation_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("org_id", sa.Integer(), nullable=False),
        sa.Column("designation_name", sa.String(length=150), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=True),  # deferred FK -> users
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("designation_id", name="pk_designations"),
        sa.ForeignKeyConstraint(
            ["org_id"], ["organizations.org_id"], name="fk_designations_org_id_organizations"
        ),
    )
    op.create_index(
        "uq_designations_org_id_designation_name",
        "designations",
        ["org_id", "designation_name"],
        unique=True,
        postgresql_where=sa.text("is_deleted = false"),
    )

    # ----- employees ---------------------------------------------------------
    op.create_table(
        "employees",
        sa.Column("employee_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("org_id", sa.Integer(), nullable=False),
        sa.Column("employee_code", sa.String(length=30), nullable=False),
        sa.Column("employee_uid", sa.String(length=50), nullable=True),
        sa.Column("employee_name", sa.String(length=200), nullable=False),
        sa.Column("display_name", sa.String(length=200), nullable=True),
        sa.Column("mobile_country_code", sa.String(length=5), server_default=sa.text("'+91'"), nullable=False),
        sa.Column("mobile_number", sa.String(length=20), nullable=False),
        sa.Column("email", sa.String(length=200), nullable=True),
        sa.Column("gender", sa.String(length=10), nullable=False),
        sa.Column("master_branch_id", sa.Integer(), nullable=False),
        sa.Column("dept_id", sa.Integer(), nullable=False),
        sa.Column("designation_id", sa.Integer(), nullable=False),
        sa.Column("employee_type", sa.String(length=30), nullable=True),
        sa.Column("door_lock_permission", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("pf_account_number", sa.String(length=50), nullable=True),
        sa.Column("uan_number", sa.String(length=12), nullable=True),
        sa.Column("esic_ip_number", sa.String(length=10), nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("date_of_joining", sa.Date(), nullable=True),
        sa.Column("salary_type", sa.String(length=20), nullable=True),
        sa.Column("monthly_salary", sa.Numeric(precision=12, scale=2), server_default=sa.text("0"), nullable=True),
        sa.Column("payroll_group_id", sa.Integer(), nullable=True),  # deferred FK -> payroll_groups
        sa.Column("date_of_birth", sa.Date(), nullable=True),
        sa.Column("date_of_leaving", sa.Date(), nullable=True),
        sa.Column("employment_status", sa.String(length=20), server_default=sa.text("'active'"), nullable=False),
        sa.Column("profile_photo_url", sa.Text(), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=True),  # deferred FK -> users
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("employee_id", name="pk_employees"),
        sa.ForeignKeyConstraint(
            ["org_id"], ["organizations.org_id"], name="fk_employees_org_id_organizations"
        ),
        sa.ForeignKeyConstraint(
            ["master_branch_id"], ["branches.branch_id"], name="fk_employees_master_branch_id_branches"
        ),
        sa.ForeignKeyConstraint(
            ["dept_id"], ["departments.dept_id"], name="fk_employees_dept_id_departments"
        ),
        sa.ForeignKeyConstraint(
            ["designation_id"], ["designations.designation_id"], name="fk_employees_designation_id_designations"
        ),
        sa.CheckConstraint(
            "employment_status IN ('active', 'inactive', 'terminated')",
            name="ck_employees_employment_status",
        ),
        sa.CheckConstraint("gender IN ('Male', 'Female', 'Other')", name="ck_employees_gender"),
        sa.CheckConstraint(
            "salary_type IN ('Monthly', 'Hourly', 'Compliance')", name="ck_employees_salary_type"
        ),
    )
    op.create_index(
        "uq_employees_org_id_employee_code",
        "employees",
        ["org_id", "employee_code"],
        unique=True,
        postgresql_where=sa.text("is_deleted = false"),
    )

    # ----- employee_bank_details --------------------------------------------
    op.create_table(
        "employee_bank_details",
        sa.Column("bank_detail_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("employee_id", sa.Integer(), nullable=False),
        sa.Column("bank_name", sa.String(length=150), nullable=True),
        sa.Column("bank_branch_name", sa.String(length=150), nullable=True),
        sa.Column("account_number", sa.String(length=30), nullable=True),
        sa.Column("ifsc_code", sa.String(length=15), nullable=True),
        sa.Column("is_primary", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("bank_detail_id", name="pk_employee_bank_details"),
        sa.ForeignKeyConstraint(
            ["employee_id"], ["employees.employee_id"],
            name="fk_employee_bank_details_employee_id_employees",
        ),
    )

    # ----- employee_documents ------------------------------------------------
    op.create_table(
        "employee_documents",
        sa.Column("document_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("employee_id", sa.Integer(), nullable=False),
        sa.Column("document_type", sa.String(length=50), nullable=False),
        sa.Column("file_url", sa.Text(), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=True),
        sa.Column("file_size_bytes", sa.Integer(), nullable=True),
        sa.Column("uploaded_by", sa.Integer(), nullable=True),  # deferred FK -> users
        sa.Column("is_deleted", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("document_id", name="pk_employee_documents"),
        sa.ForeignKeyConstraint(
            ["employee_id"], ["employees.employee_id"],
            name="fk_employee_documents_employee_id_employees",
        ),
        sa.CheckConstraint(
            "document_type IN ('aadhar_card', 'driving_licence', 'pan_card', "
            "'passport_photo', 'other')",
            name="ck_employee_documents_document_type",
        ),
    )

    # ----- employee_emergency_contacts --------------------------------------
    op.create_table(
        "employee_emergency_contacts",
        sa.Column("emergency_contact_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("employee_id", sa.Integer(), nullable=False),
        sa.Column("contact_country_code", sa.String(length=5), server_default=sa.text("'+91'"), nullable=False),
        sa.Column("contact_number", sa.String(length=20), nullable=False),
        sa.Column("contact_person_name", sa.String(length=200), nullable=False),
        sa.Column("relation", sa.String(length=100), nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("emergency_contact_id", name="pk_employee_emergency_contacts"),
        sa.ForeignKeyConstraint(
            ["employee_id"], ["employees.employee_id"],
            name="fk_employee_emergency_contacts_employee_id_employees",
        ),
    )

    # ----- employee_references ----------------------------------------------
    op.create_table(
        "employee_references",
        sa.Column("reference_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("employee_id", sa.Integer(), nullable=False),
        sa.Column("reference_name", sa.String(length=200), nullable=False),
        sa.Column("reference_country_code", sa.String(length=5), server_default=sa.text("'+91'"), nullable=False),
        sa.Column("reference_contact_number", sa.String(length=20), nullable=False),
        sa.Column("sort_order", sa.SmallInteger(), server_default=sa.text("1"), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("reference_id", name="pk_employee_references"),
        sa.ForeignKeyConstraint(
            ["employee_id"], ["employees.employee_id"],
            name="fk_employee_references_employee_id_employees",
        ),
    )

    # ----- employee_biometrics ----------------------------------------------
    op.create_table(
        "employee_biometrics",
        sa.Column("biometric_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("employee_id", sa.Integer(), nullable=False),
        sa.Column("device_id", sa.Integer(), nullable=False),  # deferred FK -> biometric_devices
        sa.Column("biometric_type", sa.String(length=30), server_default=sa.text("'fingerprint'"), nullable=False),
        sa.Column("biometric_template", sa.Text(), nullable=True),
        sa.Column("registered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("registered_by", sa.Integer(), nullable=True),  # deferred FK -> users
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("biometric_id", name="pk_employee_biometrics"),
        sa.ForeignKeyConstraint(
            ["employee_id"], ["employees.employee_id"],
            name="fk_employee_biometrics_employee_id_employees",
        ),
    )
    op.create_index(
        "uq_employee_biometrics_employee_id_device_id_biometric_type",
        "employee_biometrics",
        ["employee_id", "device_id", "biometric_type"],
        unique=True,
        postgresql_where=sa.text("is_deleted = false"),
    )

    # ----- employee_punch_branches ------------------------------------------
    op.create_table(
        "employee_punch_branches",
        sa.Column("punch_branch_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("employee_id", sa.Integer(), nullable=False),
        sa.Column("branch_id", sa.Integer(), nullable=False),
        sa.Column("assigned_by", sa.Integer(), nullable=True),  # deferred FK -> users
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("punch_branch_id", name="pk_employee_punch_branches"),
        sa.ForeignKeyConstraint(
            ["employee_id"], ["employees.employee_id"],
            name="fk_employee_punch_branches_employee_id_employees",
        ),
        sa.ForeignKeyConstraint(
            ["branch_id"], ["branches.branch_id"],
            name="fk_employee_punch_branches_branch_id_branches",
        ),
        sa.UniqueConstraint(
            "employee_id", "branch_id", name="uq_employee_punch_branches_employee_id_branch_id"
        ),
    )

    # ----- employee_attendance_permissions ----------------------------------
    op.create_table(
        "employee_attendance_permissions",
        sa.Column("att_perm_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("employee_id", sa.Integer(), nullable=False),
        sa.Column("attendance_method", sa.String(length=20), server_default=sa.text("'hardware_device'"), nullable=False),
        sa.Column("mobile_attendance_enabled", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("geofencing_enabled", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("auto_punch_out_enabled", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("updated_by", sa.Integer(), nullable=True),  # deferred FK -> users
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("att_perm_id", name="pk_employee_attendance_permissions"),
        sa.ForeignKeyConstraint(
            ["employee_id"], ["employees.employee_id"],
            name="fk_employee_attendance_permissions_employee_id_employees",
        ),
        sa.UniqueConstraint("employee_id", name="uq_employee_attendance_permissions_employee_id"),
        sa.CheckConstraint(
            "attendance_method IN ('hardware_device', 'mobile_app', 'both')",
            name="ck_employee_attendance_permissions_attendance_method",
        ),
    )

    # ----- org_attendance_settings ------------------------------------------
    op.create_table(
        "org_attendance_settings",
        sa.Column("setting_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("org_id", sa.Integer(), nullable=False),
        sa.Column("branch_id", sa.Integer(), nullable=True),
        sa.Column("device_id", sa.Integer(), nullable=True),  # deferred FK -> biometric_devices
        sa.Column("mobile_attendance_enabled", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("geofencing_enabled", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("auto_punch_out_enabled", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("biometric_attempt_count", sa.SmallInteger(), server_default=sa.text("7"), nullable=False),
        sa.Column("updated_by", sa.Integer(), nullable=True),  # deferred FK -> users
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("setting_id", name="pk_org_attendance_settings"),
        sa.ForeignKeyConstraint(
            ["org_id"], ["organizations.org_id"],
            name="fk_org_attendance_settings_org_id_organizations",
        ),
        sa.ForeignKeyConstraint(
            ["branch_id"], ["branches.branch_id"],
            name="fk_org_attendance_settings_branch_id_branches",
        ),
        sa.UniqueConstraint(
            "org_id", "branch_id", "device_id",
            name="uq_org_attendance_settings_org_id_branch_id_device_id",
        ),
    )

    # ----- employee_import_logs ---------------------------------------------
    op.create_table(
        "employee_import_logs",
        sa.Column("import_log_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("org_id", sa.Integer(), nullable=False),
        sa.Column("import_type", sa.String(length=30), server_default=sa.text("'create'"), nullable=False),
        sa.Column("file_url", sa.Text(), nullable=True),
        sa.Column("original_filename", sa.String(length=255), nullable=True),
        sa.Column("total_rows", sa.Integer(), nullable=True),
        sa.Column("success_rows", sa.Integer(), nullable=True),
        sa.Column("failed_rows", sa.Integer(), nullable=True),
        sa.Column("error_details", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("status", sa.String(length=20), server_default=sa.text("'pending'"), nullable=False),
        sa.Column("initiated_by", sa.Integer(), nullable=True),  # deferred FK -> users
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("import_log_id", name="pk_employee_import_logs"),
        sa.ForeignKeyConstraint(
            ["org_id"], ["organizations.org_id"],
            name="fk_employee_import_logs_org_id_organizations",
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'processing', 'completed', 'failed')",
            name="ck_employee_import_logs_status",
        ),
        sa.CheckConstraint(
            "import_type IN ('create', 'update')",
            name="ck_employee_import_logs_import_type",
        ),
    )

    # ----- employee_tags -----------------------------------------------------
    op.create_table(
        "employee_tags",
        sa.Column("tag_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("employee_id", sa.Integer(), nullable=False),
        sa.Column("tag_label", sa.String(length=100), nullable=False),
        sa.Column("tag_color", sa.String(length=10), nullable=True),
        sa.Column("is_status_tag", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=True),  # deferred FK -> users
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("tag_id", name="pk_employee_tags"),
        sa.ForeignKeyConstraint(
            ["employee_id"], ["employees.employee_id"],
            name="fk_employee_tags_employee_id_employees",
        ),
    )

    # ----- employee_status_history ------------------------------------------
    op.create_table(
        "employee_status_history",
        sa.Column("status_history_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("employee_id", sa.Integer(), nullable=False),
        sa.Column("previous_status", sa.String(length=20), nullable=True),
        sa.Column("new_status", sa.String(length=20), nullable=False),
        sa.Column("changed_by", sa.Integer(), nullable=True),  # deferred FK -> users
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("effective_date", sa.Date(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("status_history_id", name="pk_employee_status_history"),
        sa.ForeignKeyConstraint(
            ["employee_id"], ["employees.employee_id"],
            name="fk_employee_status_history_employee_id_employees",
        ),
        sa.CheckConstraint(
            "new_status IN ('active', 'inactive', 'terminated')",
            name="ck_employee_status_history_new_status",
        ),
    )


def downgrade() -> None:
    # Drop in reverse dependency order. Table drops cascade their own indexes.
    op.drop_table("employee_status_history")
    op.drop_table("employee_tags")
    op.drop_table("employee_import_logs")
    op.drop_table("org_attendance_settings")
    op.drop_table("employee_attendance_permissions")
    op.drop_table("employee_punch_branches")
    op.drop_index(
        "uq_employee_biometrics_employee_id_device_id_biometric_type",
        table_name="employee_biometrics",
    )
    op.drop_table("employee_biometrics")
    op.drop_table("employee_references")
    op.drop_table("employee_emergency_contacts")
    op.drop_table("employee_documents")
    op.drop_table("employee_bank_details")
    op.drop_index("uq_employees_org_id_employee_code", table_name="employees")
    op.drop_table("employees")
    op.drop_index("uq_designations_org_id_designation_name", table_name="designations")
    op.drop_table("designations")
    op.drop_index("uq_departments_org_id_dept_name", table_name="departments")
    op.drop_table("departments")
    op.drop_table("branches")
    op.drop_table("organizations")
