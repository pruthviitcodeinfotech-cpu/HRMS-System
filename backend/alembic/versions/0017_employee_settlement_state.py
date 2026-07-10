"""Record when an employee's Full & Final settlement was finalized.

Finalizing an F&F settlement debits the employee's loan and arrears ledgers. Before this
migration nothing recorded that it had happened, so the operation was not idempotent: a
second call would re-run against whatever ledger rows remained. These two columns are the
settlement's completion marker and make ``finalize_ff_settlement`` safely repeatable.

They also carry the Employee-Exit -> Settlement and Payroll -> Settlement gates: the
service refuses to finalize unless the employee has exited and a finalized payroll run
covers their last working day.

Revision ID: 0017_employee_settlement_state
Revises: 0016_resolve_remaining_deferred_fks
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0017_employee_settlement_state"
down_revision: Union[str, None] = "0016_resolve_remaining_deferred_fks"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "employees",
        sa.Column("settlement_finalized_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "employees",
        sa.Column("settlement_finalized_by", sa.BigInteger(), nullable=True),
    )
    op.create_foreign_key(
        "fk_employees_settlement_finalized_by_users",
        "employees",
        "users",
        ["settlement_finalized_by"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_employees_settlement_finalized_at",
        "employees",
        ["settlement_finalized_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_employees_settlement_finalized_at", table_name="employees")
    op.drop_constraint(
        "fk_employees_settlement_finalized_by_users", "employees", type_="foreignkey"
    )
    op.drop_column("employees", "settlement_finalized_by")
    op.drop_column("employees", "settlement_finalized_at")
