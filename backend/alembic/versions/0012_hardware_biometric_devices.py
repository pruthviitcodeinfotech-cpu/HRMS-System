"""hardware — biometric devices

Creates the Hardware module's device registry: biometric_devices. A master table
for ADMS-compatible biometric attendance devices (e.g. eSSL K90 Pro). Database
structure ONLY — no ADMS/eSSL communication, sync, or device logic. The table
may hold zero rows initially; it exists so other modules can reference a device.

It is the target of two previously-deferred FKs, wired in the follow-up
migration 0013.

Project standards: BIGINT PK/FKs; VARCHAR + CHECK (not native ENUM); org_id ->
organizations.org_id; FKs bound to real PKs. Enforced FKs (targets already
exist): org_id -> organizations (RESTRICT), branch_id -> branches (SET NULL),
created_by/updated_by -> users (SET NULL).

Revision ID: 0012_hardware_biometric_devices
Revises: 0011_settings
Create Date: 2026-07-06
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0012_hardware_biometric_devices"
down_revision: Union[str, None] = "0011_settings"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "biometric_devices",
        # ----- Identity -----
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("org_id", sa.BigInteger(), nullable=False),
        sa.Column("branch_id", sa.BigInteger(), nullable=True),
        sa.Column("device_name", sa.String(length=150), nullable=False),
        sa.Column("device_code", sa.String(length=50), nullable=False),
        sa.Column("serial_number", sa.String(length=100), nullable=False),
        sa.Column("model", sa.String(length=100), nullable=True),
        sa.Column("manufacturer", sa.String(length=100), nullable=True),
        # ----- Network -----
        sa.Column("ip_address", postgresql.INET(), nullable=True),
        sa.Column("port", sa.Integer(), nullable=True),
        sa.Column("protocol", sa.String(length=20), server_default=sa.text("'tcp_ip'"), nullable=False),
        sa.Column("domain", sa.String(length=255), nullable=True),
        sa.Column("mac_address", sa.String(length=17), nullable=True),
        # ----- ADMS Configuration -----
        sa.Column("adms_enabled", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("adms_server", sa.String(length=255), nullable=True),
        sa.Column("adms_port", sa.Integer(), nullable=True),
        sa.Column("cloud_id", sa.String(length=100), nullable=True),
        sa.Column("communication_key", sa.String(length=255), nullable=True),
        sa.Column("sync_key", sa.String(length=255), nullable=True),
        sa.Column("timezone", sa.String(length=50), nullable=True),
        # ----- Device Status -----
        sa.Column("status", sa.String(length=20), server_default=sa.text("'offline'"), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_sync_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("firmware_version", sa.String(length=50), nullable=True),
        sa.Column("software_version", sa.String(length=50), nullable=True),
        # ----- Statistics -----
        sa.Column("total_users", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("total_fingerprints", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("total_faces", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("total_cards", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("total_logs", sa.BigInteger(), server_default=sa.text("0"), nullable=False),
        # ----- Location -----
        sa.Column("installation_location", sa.String(length=255), nullable=True),
        sa.Column("remarks", sa.Text(), nullable=True),
        # ----- Audit -----
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_by", sa.BigInteger(), nullable=True),
        sa.Column("updated_by", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_biometric_devices"),
        sa.ForeignKeyConstraint(
            ["org_id"], ["organizations.org_id"],
            name="fk_biometric_devices_org_id_organizations",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["branch_id"], ["branches.branch_id"],
            name="fk_biometric_devices_branch_id_branches",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"], ["users.id"],
            name="fk_biometric_devices_created_by_users",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["updated_by"], ["users.id"],
            name="fk_biometric_devices_updated_by_users",
            ondelete="SET NULL",
        ),
        sa.UniqueConstraint("serial_number", name="uq_biometric_devices_serial_number"),
        sa.UniqueConstraint("org_id", "device_code", name="uq_biometric_devices_org_id_device_code"),
        sa.CheckConstraint(
            "status IN ('online', 'offline', 'disabled', 'maintenance')",
            name="ck_biometric_devices_status",
        ),
        sa.CheckConstraint(
            "protocol IN ('tcp_ip', 'adms', 'usb')", name="ck_biometric_devices_protocol"
        ),
        sa.CheckConstraint(
            "port IS NULL OR (port BETWEEN 1 AND 65535)", name="ck_biometric_devices_port"
        ),
        sa.CheckConstraint(
            "adms_port IS NULL OR (adms_port BETWEEN 1 AND 65535)",
            name="ck_biometric_devices_adms_port",
        ),
        sa.CheckConstraint(
            "total_users >= 0 AND total_fingerprints >= 0 AND total_faces >= 0 "
            "AND total_cards >= 0 AND total_logs >= 0",
            name="ck_biometric_devices_stats_non_negative",
        ),
    )
    op.create_index("ix_biometric_devices_org_id", "biometric_devices", ["org_id"])
    op.create_index("ix_biometric_devices_branch_id", "biometric_devices", ["branch_id"])
    op.create_index("ix_biometric_devices_org_id_status", "biometric_devices", ["org_id", "status"])


def downgrade() -> None:
    op.drop_index("ix_biometric_devices_org_id_status", table_name="biometric_devices")
    op.drop_index("ix_biometric_devices_branch_id", table_name="biometric_devices")
    op.drop_index("ix_biometric_devices_org_id", table_name="biometric_devices")
    op.drop_table("biometric_devices")
