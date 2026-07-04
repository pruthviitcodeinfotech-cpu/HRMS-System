"""user management and rbac

Creates the User Management & RBAC module schema: users, rights_templates,
rights_template_permissions, user_template_assignments, user_custom_permissions,
user_branch_access, user_department_access, user_sessions.

This module's approved architecture uses BIGINT `id` primary keys and INT
`org_id`. It defines no CHECK constraints and no enum types.

Intra-module FKs (enforced) — target users / rights_templates, with the
ON DELETE rules from the approved architecture (CASCADE/RESTRICT/SET NULL).

DEFERRED cross-module FOREIGN KEY constraints (columns created, constraints not):
    * users.org_id / rights_templates.org_id -> organizations (built PK `org_id`
      INT vs this module's `organizations.id`; deferred pending naming/PK
      convention). Columns are INTEGER.
    * users.employee_id            -> employees (built PK `employee_id` INT vs
      `employees.id` BIGINT); deferred. Column is BIGINT.
    * user_branch_access.branch_id -> branches (built PK `branch_id` INT vs
      `branches.id` BIGINT); deferred. Column is BIGINT.
    * user_department_access.department_id -> departments (built PK `dept_id` INT
      vs `departments.id` BIGINT); deferred. Column is BIGINT.

Revision ID: 0007_user_management_rbac
Revises: 0006_settlements
Create Date: 2026-07-04
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0007_user_management_rbac"
down_revision: Union[str, None] = "0006_settlements"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ----- users (self-referential created_by) -------------------------------
    op.create_table(
        "users",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("org_id", sa.Integer(), nullable=False),  # deferred FK -> organizations
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("mobile_country_code", sa.String(length=10), server_default=sa.text("'+91'"), nullable=False),
        sa.Column("mobile_number", sa.String(length=20), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=True),
        sa.Column("is_super_admin", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("employee_id", sa.BigInteger(), nullable=True),  # deferred FK -> employees
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
        sa.ForeignKeyConstraint(
            ["created_by"], ["users.id"], name="fk_users_created_by_users", ondelete="SET NULL"
        ),
        sa.UniqueConstraint("org_id", "email", name="uq_users_org_id_email"),
        sa.UniqueConstraint(
            "org_id", "mobile_country_code", "mobile_number",
            name="uq_users_org_id_mobile_country_code_mobile_number",
        ),
    )
    op.create_index(
        "ix_users_org_id_is_active_deleted_at", "users", ["org_id", "is_active", "deleted_at"]
    )

    # ----- rights_templates --------------------------------------------------
    op.create_table(
        "rights_templates",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("org_id", sa.Integer(), nullable=False),  # deferred FK -> organizations
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("created_by", sa.BigInteger(), nullable=False),
        sa.Column("updated_by", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_rights_templates"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], name="fk_rights_templates_created_by_users"),
        sa.ForeignKeyConstraint(["updated_by"], ["users.id"], name="fk_rights_templates_updated_by_users"),
        sa.UniqueConstraint("org_id", "name", name="uq_rights_templates_org_id_name"),
    )
    op.create_index("ix_rights_templates_org_id_deleted_at", "rights_templates", ["org_id", "deleted_at"])

    # ----- rights_template_permissions ---------------------------------------
    op.create_table(
        "rights_template_permissions",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("template_id", sa.BigInteger(), nullable=False),
        sa.Column("feature_key", sa.String(length=100), nullable=False),
        sa.Column("feature_label", sa.String(length=150), nullable=False),
        sa.Column("parent_feature_key", sa.String(length=100), nullable=True),
        sa.Column("can_create", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("can_read", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("can_edit", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("can_delete", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_rights_template_permissions"),
        sa.ForeignKeyConstraint(
            ["template_id"], ["rights_templates.id"],
            name="fk_rights_template_permissions_template_id_rights_templates",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "template_id", "feature_key",
            name="uq_rights_template_permissions_template_id_feature_key",
        ),
    )

    # ----- user_template_assignments -----------------------------------------
    op.create_table(
        "user_template_assignments",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("template_id", sa.BigInteger(), nullable=False),
        sa.Column("assigned_by", sa.BigInteger(), nullable=False),
        sa.Column("assigned_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_user_template_assignments"),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_user_template_assignments_user_id_users", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["template_id"], ["rights_templates.id"],
            name="fk_user_template_assignments_template_id_rights_templates", ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["assigned_by"], ["users.id"], name="fk_user_template_assignments_assigned_by_users"
        ),
        sa.UniqueConstraint("user_id", name="uq_user_template_assignments_user_id"),
    )

    # ----- user_custom_permissions -------------------------------------------
    op.create_table(
        "user_custom_permissions",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("feature_key", sa.String(length=100), nullable=False),
        sa.Column("parent_feature_key", sa.String(length=100), nullable=True),
        sa.Column("can_create", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("can_read", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("can_edit", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("can_delete", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("set_by", sa.BigInteger(), nullable=False),
        sa.Column("set_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_user_custom_permissions"),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_user_custom_permissions_user_id_users", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["set_by"], ["users.id"], name="fk_user_custom_permissions_set_by_users"
        ),
        sa.UniqueConstraint(
            "user_id", "feature_key", name="uq_user_custom_permissions_user_id_feature_key"
        ),
    )

    # ----- user_branch_access ------------------------------------------------
    op.create_table(
        "user_branch_access",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("branch_id", sa.BigInteger(), nullable=False),  # deferred FK -> branches
        sa.Column("granted_by", sa.BigInteger(), nullable=False),
        sa.Column("granted_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_user_branch_access"),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_user_branch_access_user_id_users", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["granted_by"], ["users.id"], name="fk_user_branch_access_granted_by_users"
        ),
        sa.UniqueConstraint("user_id", "branch_id", name="uq_user_branch_access_user_id_branch_id"),
    )

    # ----- user_department_access --------------------------------------------
    op.create_table(
        "user_department_access",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("department_id", sa.BigInteger(), nullable=False),  # deferred FK -> departments
        sa.Column("granted_by", sa.BigInteger(), nullable=False),
        sa.Column("granted_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_user_department_access"),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_user_department_access_user_id_users", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["granted_by"], ["users.id"], name="fk_user_department_access_granted_by_users"
        ),
        sa.UniqueConstraint(
            "user_id", "department_id", name="uq_user_department_access_user_id_department_id"
        ),
    )

    # ----- user_sessions -----------------------------------------------------
    op.create_table(
        "user_sessions",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("session_token", sa.String(length=500), nullable=False),
        sa.Column("device_info", sa.String(length=500), nullable=True),
        sa.Column("ip_address", postgresql.INET(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_user_sessions"),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_user_sessions_user_id_users", ondelete="CASCADE"
        ),
        sa.UniqueConstraint("session_token", name="uq_user_sessions_session_token"),
    )
    op.create_index("ix_user_sessions_user_id_is_active", "user_sessions", ["user_id", "is_active"])


def downgrade() -> None:
    op.drop_index("ix_user_sessions_user_id_is_active", table_name="user_sessions")
    op.drop_table("user_sessions")
    op.drop_table("user_department_access")
    op.drop_table("user_branch_access")
    op.drop_table("user_custom_permissions")
    op.drop_table("user_template_assignments")
    op.drop_table("rights_template_permissions")
    op.drop_index("ix_rights_templates_org_id_deleted_at", table_name="rights_templates")
    op.drop_table("rights_templates")
    op.drop_index("ix_users_org_id_is_active_deleted_at", table_name="users")
    op.drop_table("users")
