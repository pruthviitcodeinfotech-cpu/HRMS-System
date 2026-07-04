"""Settings — org-level configuration models.

Tables: org_settings, org_salary_slip_settings.

Implements the approved Settings Database Architecture. All settings are
org-scoped (exactly one row per organisation, enforced by UNIQUE(org_id)).

NOT created here: `org_payroll_settings` — the approved architecture explicitly
states it is "reused from the Payroll module — shown for reference, not
redefined". In this build that table already exists as `payroll_settings`
(Payroll module, migration 0005); Settings does not duplicate it.

Project-standard resolutions (per project conventions, confirmed):
    * id / org_id are BIGINT (the PDF's INT is superseded by the project-wide
      BIGINT PK/FK standardization, migration 0009).
    * FKs bind to the ACTUAL built primary keys: org_id -> organizations.org_id,
      updated_by -> users.id (the PDF's `organizations.id` is naming drift).

Confirmed with the product owner:
    * The stray `CHECK (off_day_multiplier >= 0)` listed under org_settings is a
      copy-paste artifact from org_payroll_settings (org_settings has no such
      column) and is intentionally omitted.
    * `org_salary_slip_settings.created_at` is added for consistency with
      org_settings (the PDF omitted it; treated as an oversight).

Enforced cross-module FKs (both target tables already exist): org_id ->
organizations (RESTRICT), updated_by -> users (SET NULL). Nothing deferred.
"""

from datetime import datetime, time

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    String,
    Text,
    Time,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database.base import Base


class OrgSettings(Base):
    __tablename__ = "org_settings"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    org_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "organizations.org_id",
            name="fk_org_settings_org_id_organizations",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    # Shifts & Time Management
    advance_shift_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    # Attendance Management
    enable_regularization: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    enable_photo_punch: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    # Hardware Management
    device_sync_time: Mapped[time] = mapped_column(
        Time, nullable=False, server_default=text("'16:51:00'")
    )
    # Organization Management
    sync_code: Mapped[str] = mapped_column(String(50), nullable=False)
    pass_code: Mapped[str] = mapped_column(String(20), nullable=False)
    # Enforced FK -> users.id (SET NULL on delete); users module already built.
    updated_by: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("users.id", name="fk_org_settings_updated_by_users", ondelete="SET NULL"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )

    __table_args__ = (UniqueConstraint("org_id", name="uq_org_settings_org_id"),)


class OrgSalarySlipSettings(Base):
    __tablename__ = "org_salary_slip_settings"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    org_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "organizations.org_id",
            name="fk_org_salary_slip_settings_org_id_organizations",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    company_logo_url: Mapped[str | None] = mapped_column(Text)
    company_name: Mapped[str] = mapped_column(String(200), nullable=False)
    company_address: Mapped[str] = mapped_column(Text, nullable=False)
    company_contact: Mapped[str] = mapped_column(String(100), nullable=False)
    company_website_email: Mapped[str | None] = mapped_column(String(200))
    auto_release_payslip: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true")
    )
    branch_wise_payslip: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    # Enforced FK -> users.id (SET NULL on delete); users module already built.
    updated_by: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey(
            "users.id",
            name="fk_org_salary_slip_settings_updated_by_users",
            ondelete="SET NULL",
        ),
    )
    # created_at added for consistency with org_settings (PDF omitted it).
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )

    __table_args__ = (
        UniqueConstraint("org_id", name="uq_org_salary_slip_settings_org_id"),
    )
