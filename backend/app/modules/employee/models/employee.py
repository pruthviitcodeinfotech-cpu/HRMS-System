"""Employee Management — employee master model.

Table: employees.

Implements the approved Employee Management Database Architecture exactly.
All primary keys and foreign keys use BIGINT (project-wide PK convention).
DEFERRED cross-module FKs (plain columns for now):
    - payroll_group_id -> payroll_groups (Payroll module)
    - created_by       -> users          (User Management module)
"""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database.base import Base


class Employee(Base):
    __tablename__ = "employees"

    employee_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    org_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("organizations.org_id", name="fk_employees_org_id_organizations"),
        nullable=False,
    )
    employee_code: Mapped[str] = mapped_column(String(30), nullable=False)
    employee_uid: Mapped[str | None] = mapped_column(String(50))
    employee_name: Mapped[str] = mapped_column(String(200), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(200))
    mobile_country_code: Mapped[str] = mapped_column(
        String(5), nullable=False, server_default=text("'+91'")
    )
    mobile_number: Mapped[str] = mapped_column(String(20), nullable=False)
    email: Mapped[str | None] = mapped_column(String(200))
    gender: Mapped[str] = mapped_column(String(10), nullable=False)
    master_branch_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("branches.branch_id", name="fk_employees_master_branch_id_branches"),
        nullable=False,
    )
    dept_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("departments.dept_id", name="fk_employees_dept_id_departments"),
        nullable=False,
    )
    designation_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("designations.designation_id", name="fk_employees_designation_id_designations"),
        nullable=False,
    )
    employee_type: Mapped[str | None] = mapped_column(String(30))
    door_lock_permission: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    pf_account_number: Mapped[str | None] = mapped_column(String(50))
    uan_number: Mapped[str | None] = mapped_column(String(12))
    esic_ip_number: Mapped[str | None] = mapped_column(String(10))
    address: Mapped[str | None] = mapped_column(Text)
    date_of_joining: Mapped[date | None] = mapped_column(Date)
    salary_type: Mapped[str | None] = mapped_column(String(20))
    monthly_salary: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), server_default=text("0"))
    # DEFERRED cross-module FK -> payroll_groups
    payroll_group_id: Mapped[int | None] = mapped_column(BigInteger)
    date_of_birth: Mapped[date | None] = mapped_column(Date)
    date_of_leaving: Mapped[date | None] = mapped_column(Date)
    employment_status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'active'")
    )
    profile_photo_url: Mapped[str | None] = mapped_column(Text)
    # Stamped when the employee's Full & Final settlement is finalized. That operation
    # debits the loan and arrears ledgers, so it must not run twice — see migration 0017.
    settlement_finalized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    settlement_finalized_by: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey(
            "users.id",
            name="fk_employees_settlement_finalized_by_users",
            ondelete="SET NULL",
        ),
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
            "uq_employees_org_id_employee_code",
            "org_id",
            "employee_code",
            unique=True,
            postgresql_where=text("is_deleted = false"),
        ),
        CheckConstraint(
            "employment_status IN ('active', 'inactive', 'terminated')",
            name="ck_employees_employment_status",
        ),
        CheckConstraint(
            "gender IN ('Male', 'Female', 'Other')",
            name="ck_employees_gender",
        ),
        CheckConstraint(
            "salary_type IN ('Monthly', 'Hourly', 'Compliance')",
            name="ck_employees_salary_type",
        ),
    )

    # Parent relationships (intra-module)
    organization: Mapped["Organization"] = relationship(back_populates="employees")  # noqa: F821
    master_branch: Mapped["Branch"] = relationship(back_populates="master_employees")  # noqa: F821
    department: Mapped["Department"] = relationship(back_populates="employees")  # noqa: F821
    designation: Mapped["Designation"] = relationship(back_populates="employees")  # noqa: F821

    # Child (satellite) relationships
    bank_details: Mapped[list["EmployeeBankDetail"]] = relationship(  # noqa: F821
        back_populates="employee"
    )
    documents: Mapped[list["EmployeeDocument"]] = relationship(  # noqa: F821
        back_populates="employee"
    )
    emergency_contacts: Mapped[list["EmployeeEmergencyContact"]] = relationship(  # noqa: F821
        back_populates="employee"
    )
    references: Mapped[list["EmployeeReference"]] = relationship(  # noqa: F821
        back_populates="employee"
    )
    biometrics: Mapped[list["EmployeeBiometric"]] = relationship(  # noqa: F821
        back_populates="employee"
    )
    punch_branches: Mapped[list["EmployeePunchBranch"]] = relationship(  # noqa: F821
        back_populates="employee"
    )
    attendance_permission: Mapped["EmployeeAttendancePermission"] = relationship(  # noqa: F821
        back_populates="employee", uselist=False
    )
    tags: Mapped[list["EmployeeTag"]] = relationship(back_populates="employee")  # noqa: F821
    status_history: Mapped[list["EmployeeStatusHistory"]] = relationship(  # noqa: F821
        back_populates="employee"
    )
