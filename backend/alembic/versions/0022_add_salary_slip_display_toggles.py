"""Add salary slip display toggles to org_salary_slip_settings table

Revision ID: 0022_salary_slip_toggles
Revises: 0021_holiday_templates_ci_unique_index
Create Date: 2026-07-24
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0022_salary_slip_toggles"
down_revision = "0021_holiday_tmpl_ci_idx"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("org_salary_slip_settings", sa.Column("show_pf", sa.Boolean(), server_default=sa.text("true"), nullable=False))
    op.add_column("org_salary_slip_settings", sa.Column("show_esic", sa.Boolean(), server_default=sa.text("true"), nullable=False))
    op.add_column("org_salary_slip_settings", sa.Column("show_leave_balance", sa.Boolean(), server_default=sa.text("true"), nullable=False))
    op.add_column("org_salary_slip_settings", sa.Column("show_bank_details", sa.Boolean(), server_default=sa.text("true"), nullable=False))
    op.add_column("org_salary_slip_settings", sa.Column("show_pan", sa.Boolean(), server_default=sa.text("true"), nullable=False))
    op.add_column("org_salary_slip_settings", sa.Column("show_uan", sa.Boolean(), server_default=sa.text("true"), nullable=False))


def downgrade() -> None:
    op.drop_column("org_salary_slip_settings", "show_uan")
    op.drop_column("org_salary_slip_settings", "show_pan")
    op.drop_column("org_salary_slip_settings", "show_bank_details")
    op.drop_column("org_salary_slip_settings", "show_leave_balance")
    op.drop_column("org_salary_slip_settings", "show_esic")
    op.drop_column("org_salary_slip_settings", "show_pf")
