"""Hardware — biometric device registry model.

Table: biometric_devices.

A device master / registry for ADMS-compatible biometric attendance devices
(e.g. eSSL K90 Pro). This is DATABASE STRUCTURE ONLY — no ADMS/eSSL
communication, sync, or device logic. The table may hold zero rows initially;
it exists so other modules can reference a physical device.

It is the target of two previously-DEFERRED foreign keys (wired in migration
0013): employee_biometrics.device_id and org_attendance_settings.device_id.

Project standards applied: BIGINT PK/FKs; VARCHAR + CHECK (not native ENUM;
see constants.py); org_id -> organizations.org_id; FKs bound to real PKs. Per
house convention, cross-module enforced FKs are columns/constraints only — NO
ORM relationships to Organization/Branch/User and no reverse relationships.

Enforced FKs (all target tables already exist): org_id -> organizations
(RESTRICT), branch_id -> branches (SET NULL), created_by/updated_by -> users
(SET NULL).
"""

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import INET
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database.base import Base

_STATUS_CHECK = "status IN ('online', 'offline', 'disabled', 'maintenance')"
_PROTOCOL_CHECK = "protocol IN ('tcp_ip', 'adms', 'usb')"


class BiometricDevice(Base):
    __tablename__ = "biometric_devices"

    # ----- Identity -----
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    org_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "organizations.org_id",
            name="fk_biometric_devices_org_id_organizations",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    branch_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey(
            "branches.branch_id",
            name="fk_biometric_devices_branch_id_branches",
            ondelete="SET NULL",
        ),
    )
    device_name: Mapped[str] = mapped_column(String(150), nullable=False)
    device_code: Mapped[str] = mapped_column(String(50), nullable=False)
    serial_number: Mapped[str] = mapped_column(String(100), nullable=False)
    model: Mapped[str | None] = mapped_column(String(100))
    manufacturer: Mapped[str | None] = mapped_column(String(100))

    # ----- Network -----
    ip_address: Mapped[str | None] = mapped_column(INET)
    port: Mapped[int | None] = mapped_column(Integer)  # data column (not a key)
    protocol: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'tcp_ip'")
    )
    domain: Mapped[str | None] = mapped_column(String(255))
    mac_address: Mapped[str | None] = mapped_column(String(17))

    # ----- ADMS Configuration -----
    adms_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    adms_server: Mapped[str | None] = mapped_column(String(255))
    adms_port: Mapped[int | None] = mapped_column(Integer)  # data column (not a key)
    cloud_id: Mapped[str | None] = mapped_column(String(100))
    communication_key: Mapped[str | None] = mapped_column(String(255))
    sync_key: Mapped[str | None] = mapped_column(String(255))
    timezone: Mapped[str | None] = mapped_column(String(50))

    # ----- Device Status -----
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'offline'")
    )
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    firmware_version: Mapped[str | None] = mapped_column(String(50))
    software_version: Mapped[str | None] = mapped_column(String(50))

    # ----- Statistics (data columns) -----
    total_users: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    total_fingerprints: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    total_faces: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    total_cards: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    total_logs: Mapped[int] = mapped_column(BigInteger, nullable=False, server_default=text("0"))

    # ----- Location -----
    installation_location: Mapped[str | None] = mapped_column(String(255))
    remarks: Mapped[str | None] = mapped_column(Text)

    # ----- Audit -----
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    created_by: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("users.id", name="fk_biometric_devices_created_by_users", ondelete="SET NULL"),
    )
    updated_by: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("users.id", name="fk_biometric_devices_updated_by_users", ondelete="SET NULL"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )

    __table_args__ = (
        UniqueConstraint("serial_number", name="uq_biometric_devices_serial_number"),
        UniqueConstraint("org_id", "device_code", name="uq_biometric_devices_org_id_device_code"),
        CheckConstraint(_STATUS_CHECK, name="ck_biometric_devices_status"),
        CheckConstraint(_PROTOCOL_CHECK, name="ck_biometric_devices_protocol"),
        CheckConstraint(
            "port IS NULL OR (port BETWEEN 1 AND 65535)", name="ck_biometric_devices_port"
        ),
        CheckConstraint(
            "adms_port IS NULL OR (adms_port BETWEEN 1 AND 65535)",
            name="ck_biometric_devices_adms_port",
        ),
        CheckConstraint(
            "total_users >= 0 AND total_fingerprints >= 0 AND total_faces >= 0 "
            "AND total_cards >= 0 AND total_logs >= 0",
            name="ck_biometric_devices_stats_non_negative",
        ),
        Index("ix_biometric_devices_org_id", "org_id"),
        Index("ix_biometric_devices_branch_id", "branch_id"),
        Index("ix_biometric_devices_org_id_status", "org_id", "status"),
    )
