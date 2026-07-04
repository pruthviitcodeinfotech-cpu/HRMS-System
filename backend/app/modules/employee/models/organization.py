"""Employee Management — organizational-structure models.

Tables: organizations, branches, departments, designations.

Implements the approved Employee Management Database Architecture exactly.
All primary keys and foreign keys use BIGINT (project-wide PK convention).
Cross-module foreign keys (created_by -> users) are represented as plain
columns; those FK constraints are intentionally DEFERRED until the User
Management module exists (see the module migration for details).
"""

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database.base import Base


class Organization(Base):
    __tablename__ = "organizations"

    org_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    org_code: Mapped[str] = mapped_column(String(20), nullable=False)
    org_name: Mapped[str] = mapped_column(String(200), nullable=False)
    contact_phone: Mapped[str | None] = mapped_column(String(20))
    contact_email: Mapped[str | None] = mapped_column(String(150))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )

    __table_args__ = (UniqueConstraint("org_code", name="uq_organizations_org_code"),)

    branches: Mapped[list["Branch"]] = relationship(back_populates="organization")
    departments: Mapped[list["Department"]] = relationship(back_populates="organization")
    designations: Mapped[list["Designation"]] = relationship(back_populates="organization")
    employees: Mapped[list["Employee"]] = relationship(back_populates="organization")  # noqa: F821
    attendance_settings: Mapped[list["OrgAttendanceSetting"]] = relationship(  # noqa: F821
        back_populates="organization"
    )
    import_logs: Mapped[list["EmployeeImportLog"]] = relationship(  # noqa: F821
        back_populates="organization"
    )


class Branch(Base):
    __tablename__ = "branches"

    branch_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    org_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("organizations.org_id", name="fk_branches_org_id_organizations"),
        nullable=False,
    )
    branch_name: Mapped[str] = mapped_column(String(200), nullable=False)
    logo_url: Mapped[str | None] = mapped_column(Text)
    gstin: Mapped[str | None] = mapped_column(String(20))
    mobile_number: Mapped[str | None] = mapped_column(String(20))
    address: Mapped[str | None] = mapped_column(Text)
    landmark: Mapped[str | None] = mapped_column(String(200))
    pin_code: Mapped[str | None] = mapped_column(String(10))
    city: Mapped[str | None] = mapped_column(String(100))
    state: Mapped[str | None] = mapped_column(String(100))
    country: Mapped[str | None] = mapped_column(String(100))
    industry_type: Mapped[str | None] = mapped_column(String(100))
    latitude: Mapped[float | None] = mapped_column(Numeric(10, 7))
    longitude: Mapped[float | None] = mapped_column(Numeric(10, 7))
    allowed_radius_meters: Mapped[int | None] = mapped_column(SmallInteger)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )

    organization: Mapped["Organization"] = relationship(back_populates="branches")
    master_employees: Mapped[list["Employee"]] = relationship(  # noqa: F821
        back_populates="master_branch"
    )
    punch_branches: Mapped[list["EmployeePunchBranch"]] = relationship(  # noqa: F821
        back_populates="branch"
    )
    attendance_settings: Mapped[list["OrgAttendanceSetting"]] = relationship(  # noqa: F821
        back_populates="branch"
    )


class Department(Base):
    __tablename__ = "departments"

    dept_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    org_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("organizations.org_id", name="fk_departments_org_id_organizations"),
        nullable=False,
    )
    dept_name: Mapped[str] = mapped_column(String(150), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
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
            "uq_departments_org_id_dept_name",
            "org_id",
            "dept_name",
            unique=True,
            postgresql_where=text("is_deleted = false"),
        ),
    )

    organization: Mapped["Organization"] = relationship(back_populates="departments")
    employees: Mapped[list["Employee"]] = relationship(back_populates="department")  # noqa: F821


class Designation(Base):
    __tablename__ = "designations"

    designation_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    org_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("organizations.org_id", name="fk_designations_org_id_organizations"),
        nullable=False,
    )
    designation_name: Mapped[str] = mapped_column(String(150), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
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
            "uq_designations_org_id_designation_name",
            "org_id",
            "designation_name",
            unique=True,
            postgresql_where=text("is_deleted = false"),
        ),
    )

    organization: Mapped["Organization"] = relationship(back_populates="designations")
    employees: Mapped[list["Employee"]] = relationship(back_populates="designation")  # noqa: F821
