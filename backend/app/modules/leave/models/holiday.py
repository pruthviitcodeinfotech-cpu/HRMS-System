"""Leave & Holiday Management — holiday template models.

Tables: holiday_templates, holiday_template_items, employee_holiday_assignments.

Implements the approved Leave & Holiday Management Database Architecture exactly
(BIGINT `id` primary keys).

Intra-module FKs (enforced): template_id / previous_template_id -> holiday_templates.
DEFERRED cross-module FKs (columns only):
    * employee_id -> employees (see leave.py module docstring)
    * created_by / updated_by / assigned_by -> users (User Management)
"""

from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    SmallInteger,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database.base import Base


class HolidayTemplate(Base):
    __tablename__ = "holiday_templates"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    org_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    holiday_count: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, server_default=text("0")
    )
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    # DEFERRED cross-module FKs -> users.id
    created_by: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("users.id", name="fk_holiday_templates_created_by_users"),
    )
    updated_by: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("users.id", name="fk_holiday_templates_updated_by_users"),
    )

    __table_args__ = (
        Index(
            "uq_holiday_templates_org_id_name_ci",
            "org_id",
            text("lower(name)"),
            unique=True,
            postgresql_where=text("is_deleted = false"),
        ),
    )

    items: Mapped[list["HolidayTemplateItem"]] = relationship(back_populates="template")
    assignments: Mapped[list["EmployeeHolidayAssignment"]] = relationship(
        back_populates="template",
        foreign_keys="EmployeeHolidayAssignment.template_id",
    )


class HolidayTemplateItem(Base):
    __tablename__ = "holiday_template_items"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    template_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "holiday_templates.id", name="fk_holiday_template_items_template_id_holiday_templates"
        ),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    day_of_week: Mapped[str | None] = mapped_column(String(15))
    duration_days: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, server_default=text("1")
    )
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    # DEFERRED cross-module FK -> users.id
    created_by: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("users.id", name="fk_holiday_template_items_created_by_users"),
    )

    __table_args__ = (
        Index("ix_holiday_template_items_template_id_start_date", "template_id", "start_date"),
        CheckConstraint(
            "end_date >= start_date",
            name="ck_holiday_template_items_end_date_after_start_date",
        ),
    )

    template: Mapped["HolidayTemplate"] = relationship(back_populates="items")


class EmployeeHolidayAssignment(Base):
    __tablename__ = "employee_holiday_assignments"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    # DEFERRED cross-module FK -> employees
    employee_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    template_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey(
            "holiday_templates.id",
            name="fk_employee_holiday_assignments_template_id_holiday_templates",
        ),
    )
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    # DEFERRED cross-module FK -> users.id (NOT NULL per the architecture)
    assigned_by: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", name="fk_employee_holiday_assignments_assigned_by_users"),
        nullable=False,
    )
    previous_template_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey(
            "holiday_templates.id",
            name="fk_emp_holiday_assign_prev_template_id_holiday_templates",
        ),
    )

    __table_args__ = (
        UniqueConstraint("employee_id", name="uq_employee_holiday_assignments_employee_id"),
        # "which employees are on this holiday template?" — the uq leads with
        # employee_id and cannot serve a template_id lookup.
        Index("ix_employee_holiday_assignments_template_id", "template_id"),
    )

    template: Mapped["HolidayTemplate"] = relationship(
        back_populates="assignments", foreign_keys=[template_id]
    )
