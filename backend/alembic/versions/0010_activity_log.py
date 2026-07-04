"""activity log

Creates the Activity Log module schema: a single append-only, immutable audit
table `activity_logs` (one row per mutation event across all HRMS modules).

Denormalised snapshots (`employee_name`, `performed_by_name`) preserve historical
display values even after the referenced employee/user is renamed or deleted.

Resolved conflicts vs. the approved PDF (confirmed with the product owner):
    * FK targets bind to the ACTUAL built primary keys — organizations.org_id,
      employees.employee_id, users.id (the PDF's `.id` names do not exist on the
      organizations/employees tables; naming drift).
    * org_id is BIGINT to match organizations.org_id after the project-wide
      BIGINT PK standardization (0009); the PDF's INT would mismatch its target.
    * action_from is VARCHAR + CHECK, not native ENUM (project-wide convention;
      values preserved exactly).
    * performed_by_user_id is NULLABLE with ON DELETE SET NULL (the PDF marked it
      NOT NULL but also SET NULL — contradictory; the module's rule "log entry
      preserved even if user is deleted" requires nullable).

Enforced FOREIGN KEYs (all target tables already exist):
    * org_id               -> organizations.org_id (RESTRICT on delete)
    * employee_id          -> employees.employee_id (SET NULL on delete)
    * performed_by_user_id -> users.id (SET NULL on delete)

NOT expressed here: the append-only guarantee (INSERT + SELECT only, no
UPDATE/DELETE) is enforced at the database role/privilege level per the
architecture, not as a schema object.

Revision ID: 0010_activity_log
Revises: 0009_standardize_bigint_pks
Create Date: 2026-07-04
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0010_activity_log"
down_revision: Union[str, None] = "0009_standardize_bigint_pks"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "activity_logs",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("org_id", sa.BigInteger(), nullable=False),
        sa.Column("module", sa.String(length=100), nullable=False),
        sa.Column("sub_module", sa.String(length=150), nullable=True),
        sa.Column("employee_id", sa.BigInteger(), nullable=True),
        sa.Column("employee_name", sa.String(length=200), nullable=True),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("payroll_date", sa.Date(), nullable=True),
        sa.Column("action_type", sa.String(length=50), nullable=False),
        sa.Column("performed_by_user_id", sa.BigInteger(), nullable=True),
        sa.Column("performed_by_name", sa.String(length=200), nullable=False),
        sa.Column("log_date", sa.Date(), nullable=False),
        sa.Column("log_time", sa.Time(), nullable=False),
        sa.Column(
            "logged_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column(
            "action_from",
            sa.String(length=20),
            server_default=sa.text("'Web App'"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_activity_logs"),
        sa.ForeignKeyConstraint(
            ["org_id"], ["organizations.org_id"],
            name="fk_activity_logs_org_id_organizations",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["employee_id"], ["employees.employee_id"],
            name="fk_activity_logs_employee_id_employees",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["performed_by_user_id"], ["users.id"],
            name="fk_activity_logs_performed_by_user_id_users",
            ondelete="SET NULL",
        ),
        sa.CheckConstraint(
            "action_type IN ('Insert', 'Update', 'Delete', 'Assign', 'Bulk Assign')",
            name="ck_activity_logs_action_type",
        ),
        sa.CheckConstraint(
            "action_from IN ('Web App', 'Mobile App')",
            name="ck_activity_logs_action_from",
        ),
    )
    op.create_index(
        "ix_activity_logs_org_id_logged_at",
        "activity_logs", ["org_id", sa.text("logged_at DESC")],
    )
    op.create_index(
        "ix_activity_logs_org_id_log_date",
        "activity_logs", ["org_id", "log_date"],
    )
    op.create_index(
        "ix_activity_logs_org_id_employee_id",
        "activity_logs", ["org_id", "employee_id"],
    )
    op.create_index(
        "ix_activity_logs_org_id_module",
        "activity_logs", ["org_id", "module"],
    )
    op.create_index(
        "ix_activity_logs_performed_by_user_id",
        "activity_logs", ["performed_by_user_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_activity_logs_performed_by_user_id", table_name="activity_logs")
    op.drop_index("ix_activity_logs_org_id_module", table_name="activity_logs")
    op.drop_index("ix_activity_logs_org_id_employee_id", table_name="activity_logs")
    op.drop_index("ix_activity_logs_org_id_log_date", table_name="activity_logs")
    op.drop_index("ix_activity_logs_org_id_logged_at", table_name="activity_logs")
    op.drop_table("activity_logs")
