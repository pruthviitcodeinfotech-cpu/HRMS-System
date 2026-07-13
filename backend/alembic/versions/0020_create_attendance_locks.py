"""create attendance locks table

Revision ID: 0020_create_attendance_locks
Revises:     0019_user_org_memberships
Create Date: 2026-07-13
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0020_create_attendance_locks"
down_revision: Union[str, None] = "0019_user_org_memberships"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "attendance_locks",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("org_id", sa.BigInteger(), nullable=False),
        sa.Column("lock_month", sa.Integer(), nullable=False),
        sa.Column("lock_year", sa.Integer(), nullable=False),
        sa.Column("lock_type", sa.String(length=20), nullable=False),
        sa.Column("branch_id", sa.BigInteger(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default=sa.text("'locked'")),
        sa.Column("locked_by", sa.BigInteger(), nullable=False),
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("reason", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        # Primary key
        sa.PrimaryKeyConstraint("id", name="pk_attendance_locks"),
        # Foreign keys
        sa.ForeignKeyConstraint(
            ["org_id"],
            ["organizations.org_id"],
            name="fk_attendance_locks_org_id_organizations",
        ),
        sa.ForeignKeyConstraint(
            ["branch_id"],
            ["branches.branch_id"],
            name="fk_attendance_locks_branch_id_branches",
        ),
        sa.ForeignKeyConstraint(
            ["locked_by"],
            ["users.id"],
            name="fk_attendance_locks_locked_by_users",
        ),
        # Check constraints
        sa.CheckConstraint(
            "lock_type IN ('company', 'branch')",
            name="ck_attendance_locks_lock_type",
        ),
        sa.CheckConstraint(
            "status IN ('locked', 'unlocked')",
            name="ck_attendance_locks_status",
        ),
        sa.CheckConstraint(
            "lock_month >= 1 AND lock_month <= 12",
            name="ck_attendance_locks_lock_month_valid",
        ),
        sa.CheckConstraint(
            "lock_year >= 1900 AND lock_year <= 2100",
            name="ck_attendance_locks_lock_year_valid",
        ),
    )

    # Unique index for company lock (branch_id is null)
    op.create_index(
        "uq_attendance_locks_company_lock",
        "attendance_locks",
        ["org_id", "lock_year", "lock_month"],
        unique=True,
        postgresql_where=sa.text("branch_id IS NULL"),
    )

    # Unique index for branch lock (branch_id is not null)
    op.create_index(
        "uq_attendance_locks_branch_lock",
        "attendance_locks",
        ["org_id", "lock_year", "lock_month", "branch_id"],
        unique=True,
        postgresql_where=sa.text("branch_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_attendance_locks_branch_lock", table_name="attendance_locks")
    op.drop_index("uq_attendance_locks_company_lock", table_name="attendance_locks")
    op.drop_table("attendance_locks")
