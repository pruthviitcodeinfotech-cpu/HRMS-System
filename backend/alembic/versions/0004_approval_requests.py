"""approval requests

Creates the Approval Requests module schema: approval_requests (unified
polymorphic approval hub), attendance_regularization_requests,
login_reset_requests.

NOT created here (reused, owned elsewhere): leave_requests (Leave & Holiday
Management module, already built).

approval_requests.reference_id is a POLYMORPHIC logical FK (target determined
by request_type) and, per the approved architecture, carries NO DB-level FK.

DEFERRED cross-module FOREIGN KEY constraints (columns created, constraints not):
    * employee_id -> employees (all 3 tables). Employee Management is built, but
      its approved schema uses employees.employee_id (INTEGER) whereas THIS
      module's approved schema references employees.id (BIGINT). Deferred pending
      a project-wide primary-key convention decision. Columns are BIGINT.
    * reviewed_by -> users (approval_requests, login_reset_requests) -- User
      Management not yet built.

Revision ID: 0004_approval_requests
Revises: 0003_leave_holiday_management
Create Date: 2026-07-04
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0004_approval_requests"
down_revision: Union[str, None] = "0003_leave_holiday_management"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ----- approval_requests -------------------------------------------------
    op.create_table(
        "approval_requests",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("org_id", sa.BigInteger(), nullable=False),
        sa.Column("request_type", sa.String(length=20), nullable=False),
        sa.Column("request_subtype", sa.String(length=50), nullable=True),
        sa.Column("reference_id", sa.BigInteger(), nullable=False),  # polymorphic logical FK (no constraint)
        sa.Column("employee_id", sa.BigInteger(), nullable=False),  # deferred FK -> employees
        sa.Column("status", sa.String(length=10), server_default=sa.text("'pending'"), nullable=False),
        sa.Column("requested_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewed_by", sa.BigInteger(), nullable=True),  # deferred FK -> users
        sa.Column("reject_remarks", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_approval_requests"),
        sa.CheckConstraint(
            "request_type IN ('attendance', 'leave', 'login_reset')",
            name="ck_approval_requests_request_type",
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'approved', 'rejected')",
            name="ck_approval_requests_status",
        ),
    )
    op.create_index("ix_approval_requests_org_id_status", "approval_requests", ["org_id", "status"])
    op.create_index(
        "ix_approval_requests_org_id_status_request_type",
        "approval_requests",
        ["org_id", "status", "request_type"],
    )
    op.create_index(
        "ix_approval_requests_employee_id_status", "approval_requests", ["employee_id", "status"]
    )

    # ----- attendance_regularization_requests --------------------------------
    op.create_table(
        "attendance_regularization_requests",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("employee_id", sa.BigInteger(), nullable=False),  # deferred FK -> employees
        sa.Column("attendance_date", sa.Date(), nullable=False),
        sa.Column("old_punch_time", sa.String(length=20), nullable=True),
        sa.Column("new_punch_time", sa.String(length=20), nullable=False),
        sa.Column("employee_reason", sa.Text(), nullable=True),
        sa.Column("applied_on", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("status", sa.String(length=10), server_default=sa.text("'pending'"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_attendance_regularization_requests"),
        sa.CheckConstraint(
            "status IN ('pending', 'approved', 'rejected')",
            name="ck_attendance_regularization_requests_status",
        ),
    )
    op.create_index(
        "ix_att_regularization_reqs_employee_id_attendance_date",
        "attendance_regularization_requests",
        ["employee_id", "attendance_date"],
    )
    op.create_index(
        "ix_attendance_regularization_requests_status",
        "attendance_regularization_requests",
        ["status"],
    )

    # ----- login_reset_requests ----------------------------------------------
    op.create_table(
        "login_reset_requests",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("employee_id", sa.BigInteger(), nullable=False),  # deferred FK -> employees
        sa.Column("request_subtype", sa.String(length=50), nullable=True),
        sa.Column("request_description", sa.String(length=255), server_default=sa.text("'Login Reset Request'"), nullable=False),
        sa.Column("status", sa.String(length=10), server_default=sa.text("'pending'"), nullable=False),
        sa.Column("applied_on", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewed_by", sa.BigInteger(), nullable=True),  # deferred FK -> users
        sa.Column("reject_remarks", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_login_reset_requests"),
        sa.CheckConstraint(
            "status IN ('pending', 'approved', 'rejected')",
            name="ck_login_reset_requests_status",
        ),
    )
    op.create_index(
        "ix_login_reset_requests_employee_id_status", "login_reset_requests", ["employee_id", "status"]
    )


def downgrade() -> None:
    op.drop_index("ix_login_reset_requests_employee_id_status", table_name="login_reset_requests")
    op.drop_table("login_reset_requests")
    op.drop_index(
        "ix_attendance_regularization_requests_status",
        table_name="attendance_regularization_requests",
    )
    op.drop_index(
        "ix_att_regularization_reqs_employee_id_attendance_date",
        table_name="attendance_regularization_requests",
    )
    op.drop_table("attendance_regularization_requests")
    op.drop_index("ix_approval_requests_employee_id_status", table_name="approval_requests")
    op.drop_index("ix_approval_requests_org_id_status_request_type", table_name="approval_requests")
    op.drop_index("ix_approval_requests_org_id_status", table_name="approval_requests")
    op.drop_table("approval_requests")
