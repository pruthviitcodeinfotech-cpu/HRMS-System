"""notifications

Creates the Notifications module schema: notifications and
notification_recipients. The module owns only the canonical notification message
table and the per-user in-app state table.

Project standards: BIGINT PK/FKs; named constraints and indexes; FKs bind to
the real built primary keys. No CHECK constraints are added because the approved
module design did not define validation constraints for these fields.

Enforced FOREIGN KEYs (all target tables already exist):
    * notifications.org_id -> organizations.org_id (RESTRICT)
    * notifications.created_by -> users.id (SET NULL)
    * notification_recipients.notification_id -> notifications.id (CASCADE)
    * notification_recipients.org_id -> organizations.org_id (RESTRICT)
    * notification_recipients.user_id -> users.id (CASCADE)

Revision ID: 0014_notifications
Revises: 0013_resolve_deferred_device_fks
Create Date: 2026-07-07
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0014_notifications"
down_revision: Union[str, None] = "0013_resolve_deferred_device_fks"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "notifications",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("org_id", sa.BigInteger(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("notification_type", sa.String(length=50), nullable=False),
        sa.Column("priority", sa.String(length=20), nullable=False),
        sa.Column("source_module", sa.String(length=100), nullable=True),
        sa.Column("source_entity_type", sa.String(length=100), nullable=True),
        sa.Column("source_entity_id", sa.BigInteger(), nullable=True),
        sa.Column("created_by", sa.BigInteger(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_notifications"),
        sa.ForeignKeyConstraint(
            ["org_id"],
            ["organizations.org_id"],
            name="fk_notifications_org_id_organizations",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["users.id"],
            name="fk_notifications_created_by_users",
            ondelete="SET NULL",
        ),
    )
    op.create_index(
        "ix_notifications_org_id_created_at",
        "notifications",
        ["org_id", "created_at"],
    )
    op.create_index(
        "ix_notifications_org_source_module_entity_type_entity_id",
        "notifications",
        ["org_id", "source_module", "source_entity_type", "source_entity_id"],
    )

    op.create_table(
        "notification_recipients",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("notification_id", sa.BigInteger(), nullable=False),
        sa.Column("org_id", sa.BigInteger(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_notification_recipients"),
        sa.ForeignKeyConstraint(
            ["notification_id"],
            ["notifications.id"],
            name="fk_notification_recipients_notification_id_notifications",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["org_id"],
            ["organizations.org_id"],
            name="fk_notification_recipients_org_id_organizations",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_notification_recipients_user_id_users",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "notification_id",
            "user_id",
            name="uq_notification_recipients_notification_id_user_id",
        ),
    )
    op.create_index(
        "ix_notification_recipients_org_id_user_id_deleted_at",
        "notification_recipients",
        ["org_id", "user_id", "deleted_at"],
    )
    op.create_index(
        "ix_notification_recipients_org_id_user_id_read_at",
        "notification_recipients",
        ["org_id", "user_id", "read_at"],
    )
    op.create_index(
        "ix_notification_recipients_user_id_created_at",
        "notification_recipients",
        ["user_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_notification_recipients_user_id_created_at",
        table_name="notification_recipients",
    )
    op.drop_index(
        "ix_notification_recipients_org_id_user_id_read_at",
        table_name="notification_recipients",
    )
    op.drop_index(
        "ix_notification_recipients_org_id_user_id_deleted_at",
        table_name="notification_recipients",
    )
    op.drop_table("notification_recipients")
    op.drop_index(
        "ix_notifications_org_source_module_entity_type_entity_id",
        table_name="notifications",
    )
    op.drop_index("ix_notifications_org_id_created_at", table_name="notifications")
    op.drop_table("notifications")
