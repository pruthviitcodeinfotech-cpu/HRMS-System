"""Shift Management — shift definition models.

Tables: shifts, shift_day_timings.

Implements the approved Shift Management Database Architecture exactly.
All primary keys and foreign keys use BIGINT (project-wide PK convention);
duration_minutes keeps its original INTEGER type (data column, not a key).

Enforced cross-module FK: shifts.org_id -> organizations (Employee Management).
DEFERRED cross-module FK: shifts.created_by -> users (User Management).
"""

from datetime import datetime, time

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    Time,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database.base import Base


class Shift(Base):
    __tablename__ = "shifts"

    shift_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    org_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("organizations.org_id", name="fk_shifts_org_id_organizations"),
        nullable=False,
    )
    shift_name: Mapped[str] = mapped_column(String(150), nullable=False)
    shift_type: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'fixed'")
    )
    is_open_shift: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    is_uniform_time: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true")
    )
    has_break_time: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    shift_color: Mapped[str | None] = mapped_column(String(30))
    remark: Mapped[str | None] = mapped_column(Text)
    is_advanced_mode: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    # DEFERRED cross-module FK -> users.id
    created_by: Mapped[int | None] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )

    __table_args__ = (
        Index(
            "uq_shifts_org_id_shift_name",
            "org_id",
            "shift_name",
            unique=True,
            postgresql_where=text("is_deleted = false"),
        ),
        CheckConstraint("shift_type IN ('fixed', 'open')", name="ck_shifts_shift_type"),
    )

    day_timings: Mapped[list["ShiftDayTiming"]] = relationship(back_populates="shift")
    assignments: Mapped[list["ShiftAssignment"]] = relationship(back_populates="shift")  # noqa: F821
    roster_entries: Mapped[list["Roster"]] = relationship(back_populates="shift")  # noqa: F821


class ShiftDayTiming(Base):
    __tablename__ = "shift_day_timings"

    timing_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    shift_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("shifts.shift_id", name="fk_shift_day_timings_shift_id_shifts"),
        nullable=False,
    )
    # Nullable: a single row with day_of_week = NULL represents a uniform timing.
    day_of_week: Mapped[int | None] = mapped_column(SmallInteger)
    start_time: Mapped[time | None] = mapped_column(Time)
    end_time: Mapped[time | None] = mapped_column(Time)
    break_start_time: Mapped[time | None] = mapped_column(Time)
    break_end_time: Mapped[time | None] = mapped_column(Time)
    duration_minutes: Mapped[int | None] = mapped_column(Integer)  # data column (not a key)
    is_working_day: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true")
    )

    __table_args__ = (
        UniqueConstraint(
            "shift_id", "day_of_week", name="uq_shift_day_timings_shift_id_day_of_week"
        ),
    )

    shift: Mapped["Shift"] = relationship(back_populates="day_timings")
