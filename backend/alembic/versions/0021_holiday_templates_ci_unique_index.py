"""holiday_templates: replace case-sensitive unique index with case-insensitive partial unique index on lower(name)

Problem:
    The previous index `uq_holiday_templates_org_id_name` was a btree on (org_id, name)
    WHERE is_deleted = false. It was case-SENSITIVE, meaning 'Year 2026' and 'year 2026'
    were considered different names and both allowed to exist simultaneously.

    The service layer `name_exists()` correctly used `func.lower()` to enforce
    case-insensitive uniqueness at the Python level, but the DB index did not enforce it,
    causing inconsistency.

Fix:
    Drop the old case-sensitive index and create a new case-insensitive functional index on
    `lower(name)` — still scoped to active (is_deleted = false) templates only.
    Soft-deleted templates do NOT participate in uniqueness validation, allowing a template
    with a previously used name to be re-created after deletion.

Revision ID: 0021_holiday_templates_ci_unique_index
Revises:     0020_create_attendance_locks
Create Date: 2026-07-20
"""

from collections.abc import Sequence
from typing import Union

from alembic import op

# -----------------------------------------------------------------------
revision: str = "0021_holiday_tmpl_ci_idx"
down_revision: Union[str, None] = "0020_create_attendance_locks"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None
# -----------------------------------------------------------------------


def upgrade() -> None:
    # Drop old case-sensitive partial unique index
    op.drop_index(
        "uq_holiday_templates_org_id_name",
        table_name="holiday_templates",
        if_exists=True,
    )

    # Create new case-insensitive partial unique index on lower(name)
    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS uq_holiday_templates_org_id_name_ci
        ON holiday_templates (org_id, lower(name))
        WHERE is_deleted = false
    """)


def downgrade() -> None:
    # Remove the case-insensitive index
    op.drop_index(
        "uq_holiday_templates_org_id_name_ci",
        table_name="holiday_templates",
        if_exists=True,
    )

    # Restore the original case-sensitive partial unique index
    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS uq_holiday_templates_org_id_name
        ON holiday_templates (org_id, name)
        WHERE is_deleted = false
    """)
