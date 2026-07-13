"""multi-org membership — user_organization_memberships table

Creates the ``user_organization_memberships`` junction table that is the
foundation of Multi-Organization Switching (Phase 2).  The table records the
many-to-many relationship between users and organizations, allowing a single
user identity to participate in multiple tenants.

Why the existing schema is untouched
─────────────────────────────────────
``users.org_id`` (the home-org column and FK) is *not* removed.  Dozens of
existing queries, unique constraints, and FK chains rely on it.  This migration
adds a parallel membership table on top without disrupting any existing object.

Backfill
────────
After table creation the migration inserts one ``is_primary=true`` membership
row for every existing user using ``INSERT … ON CONFLICT DO NOTHING``.  This
ensures that:
  * The membership table is the authoritative source for "which orgs does user X
    belong to?" from day one.
  * The migration is idempotent and safe to re-run (e.g. on a staging
    environment that already ran the migration).

Indexes created
───────────────
  * ``ix_user_org_memberships_org_id_is_active`` — "list all members of org X"
  * ``ix_user_org_memberships_user_id_is_active`` — "list all orgs for user Y"
    (hot path for token issuance and /my-organizations)

Revision ID: 0019_user_org_memberships
Revises:     0018_fk_supporting_indexes
Create Date: 2026-07-13
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0019_user_org_memberships"
down_revision: Union[str, None] = "0018_fk_supporting_indexes"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ----- user_organization_memberships -------------------------------------
    op.create_table(
        "user_organization_memberships",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("org_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "is_primary",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column("invited_by", sa.BigInteger(), nullable=True),
        sa.Column(
            "invited_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        # Primary key
        sa.PrimaryKeyConstraint("id", name="pk_user_org_memberships"),
        # Intra-module FKs
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_user_org_memberships_user_id_users",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["org_id"],
            ["organizations.org_id"],
            name="fk_user_org_memberships_org_id_organizations",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["invited_by"],
            ["users.id"],
            name="fk_user_org_memberships_invited_by_users",
            ondelete="SET NULL",
        ),
        # Prevent duplicate memberships for the same (user, org) pair.
        sa.UniqueConstraint(
            "user_id",
            "org_id",
            name="uq_user_org_memberships_user_id_org_id",
        ),
    )

    # Org-level lookup: "list all members of org X"
    op.create_index(
        "ix_user_org_memberships_org_id_is_active",
        "user_organization_memberships",
        ["org_id", "is_active"],
    )
    # User-level lookup: "list all orgs for user Y" (hot path)
    op.create_index(
        "ix_user_org_memberships_user_id_is_active",
        "user_organization_memberships",
        ["user_id", "is_active"],
    )

    # ----- Backfill: seed one primary membership per existing user -----------
    # Uses a raw INSERT … SELECT so the operation is a single server-side
    # statement regardless of user count.  ON CONFLICT DO NOTHING makes the
    # migration idempotent.
    op.execute(
        sa.text(
            """
            INSERT INTO user_organization_memberships
                (user_id, org_id, is_primary, is_active, invited_by,
                 invited_at, accepted_at)
            SELECT
                id,
                org_id,
                true,
                true,
                NULL,
                created_at,
                created_at
            FROM users
            ON CONFLICT (user_id, org_id) DO NOTHING
            """
        )
    )


def downgrade() -> None:
    # No need to undo the backfill — dropping the table removes all rows.
    op.drop_index(
        "ix_user_org_memberships_user_id_is_active",
        table_name="user_organization_memberships",
    )
    op.drop_index(
        "ix_user_org_memberships_org_id_is_active",
        table_name="user_organization_memberships",
    )
    op.drop_table("user_organization_memberships")
