"""Shift Management — org working-hours configuration models.

Tables: working_hours_config, working_hours_config_history.

Implements the approved Shift Management Database Architecture exactly.
All primary keys and foreign keys use BIGINT (project-wide PK convention).

Enforced FKs: org_id -> organizations (Employee Management);
config_id -> working_hours_config (intra-module).
DEFERRED cross-module FKs -> users (User Management):
    working_hours_config.created_by, working_hours_config_history.changed_by.
"""

from datetime import date, datetime, time

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    String,
    Time,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database.base import Base

_ATTENDANCE_MODE_CHECK = (
    "attendance_mode IN ('consider_all_punch', 'first_and_last_punch_only', "
    "'full_day_on_single_punch', 'default_full_day')"
)
_WORKING_HOURS_MODE_CHECK = "working_hours_mode IN ('fixed', 'shift_wise')"


class WorkingHoursConfig(Base):
    __tablename__ = "working_hours_config"

    config_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    org_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("organizations.org_id", name="fk_working_hours_config_org_id_organizations"),
        nullable=False,
    )
    working_hours_mode: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'fixed'")
    )
    full_day_hours: Mapped[time | None] = mapped_column(Time, server_default=text("'08:00'"))
    half_day_hours: Mapped[time | None] = mapped_column(Time, server_default=text("'04:00'"))
    full_day_buffer_period: Mapped[time | None] = mapped_column(
        Time, server_default=text("'00:00'")
    )
    half_day_buffer_period: Mapped[time | None] = mapped_column(
        Time, server_default=text("'00:00'")
    )
    attendance_mode: Mapped[str] = mapped_column(
        String(40), nullable=False, server_default=text("'consider_all_punch'")
    )
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    # DEFERRED cross-module FK -> users.user_id
    created_by: Mapped[int | None] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )

    __table_args__ = (
        CheckConstraint(
            _WORKING_HOURS_MODE_CHECK, name="ck_working_hours_config_working_hours_mode"
        ),
        CheckConstraint(_ATTENDANCE_MODE_CHECK, name="ck_working_hours_config_attendance_mode"),
    )

    history: Mapped[list["WorkingHoursConfigHistory"]] = relationship(back_populates="config")


class WorkingHoursConfigHistory(Base):
    __tablename__ = "working_hours_config_history"

    history_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    org_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "organizations.org_id",
            name="fk_working_hours_config_history_org_id_organizations",
        ),
        nullable=False,
    )
    config_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "working_hours_config.config_id",
            name="fk_working_hours_config_history_config_id_working_hours_config",
        ),
        nullable=False,
    )
    working_hours_mode: Mapped[str] = mapped_column(String(20), nullable=False)
    full_day_hours: Mapped[time | None] = mapped_column(Time)
    half_day_hours: Mapped[time | None] = mapped_column(Time)
    full_day_buffer_period: Mapped[time | None] = mapped_column(Time)
    half_day_buffer_period: Mapped[time | None] = mapped_column(Time)
    attendance_mode: Mapped[str] = mapped_column(String(40), nullable=False)
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[date] = mapped_column(Date, nullable=False)
    # DEFERRED cross-module FK -> users.user_id
    changed_by: Mapped[int | None] = mapped_column(BigInteger)
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )

    __table_args__ = (
        CheckConstraint(
            _WORKING_HOURS_MODE_CHECK, name="ck_working_hours_config_history_working_hours_mode"
        ),
        CheckConstraint(
            _ATTENDANCE_MODE_CHECK, name="ck_working_hours_config_history_attendance_mode"
        ),
    )

    config: Mapped["WorkingHoursConfig"] = relationship(back_populates="history")
