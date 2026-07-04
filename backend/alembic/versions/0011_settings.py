"""settings

Creates the Settings module schema: org_settings and org_salary_slip_settings.
All settings are org-scoped (exactly one row per organisation, UNIQUE(org_id)).

NOT created: `org_payroll_settings` — the approved architecture states it is
reused from the Payroll module (shown for reference, not redefined). In this
build it already exists as `payroll_settings` (migration 0005). Not duplicated.

Project-standard resolutions:
    * id / org_id are BIGINT (project-wide BIGINT PK/FK standard, 0009); the
      PDF's INT is superseded.
    * FKs bind to the ACTUAL built primary keys: org_id -> organizations.org_id,
      updated_by -> users.id (the PDF's `organizations.id` is naming drift).

Confirmed with the product owner:
    * The stray `CHECK (off_day_multiplier >= 0)` listed under org_settings is a
      copy-paste artifact (org_settings has no such column) — omitted.
    * `org_salary_slip_settings.created_at` added for consistency with
      org_settings (the PDF omitted it).

Enforced cross-module FOREIGN KEYs (both target tables already exist):
    * org_id     -> organizations.org_id (RESTRICT on delete)
    * updated_by -> users.id (SET NULL on delete)

Revision ID: 0011_settings
Revises: 0010_activity_log
Create Date: 2026-07-04
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0011_settings"
down_revision: Union[str, None] = "0010_activity_log"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ----- org_settings ------------------------------------------------------
    op.create_table(
        "org_settings",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("org_id", sa.BigInteger(), nullable=False),
        sa.Column("advance_shift_enabled", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("enable_regularization", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("enable_photo_punch", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("device_sync_time", sa.Time(), server_default=sa.text("'16:51:00'"), nullable=False),
        sa.Column("sync_code", sa.String(length=50), nullable=False),
        sa.Column("pass_code", sa.String(length=20), nullable=False),
        sa.Column("updated_by", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_org_settings"),
        sa.UniqueConstraint("org_id", name="uq_org_settings_org_id"),
        sa.ForeignKeyConstraint(
            ["org_id"], ["organizations.org_id"],
            name="fk_org_settings_org_id_organizations",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["updated_by"], ["users.id"],
            name="fk_org_settings_updated_by_users",
            ondelete="SET NULL",
        ),
    )

    # ----- org_salary_slip_settings ------------------------------------------
    op.create_table(
        "org_salary_slip_settings",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("org_id", sa.BigInteger(), nullable=False),
        sa.Column("company_logo_url", sa.Text(), nullable=True),
        sa.Column("company_name", sa.String(length=200), nullable=False),
        sa.Column("company_address", sa.Text(), nullable=False),
        sa.Column("company_contact", sa.String(length=100), nullable=False),
        sa.Column("company_website_email", sa.String(length=200), nullable=True),
        sa.Column("auto_release_payslip", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("branch_wise_payslip", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("updated_by", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_org_salary_slip_settings"),
        sa.UniqueConstraint("org_id", name="uq_org_salary_slip_settings_org_id"),
        sa.ForeignKeyConstraint(
            ["org_id"], ["organizations.org_id"],
            name="fk_org_salary_slip_settings_org_id_organizations",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["updated_by"], ["users.id"],
            name="fk_org_salary_slip_settings_updated_by_users",
            ondelete="SET NULL",
        ),
    )


def downgrade() -> None:
    op.drop_table("org_salary_slip_settings")
    op.drop_table("org_settings")
