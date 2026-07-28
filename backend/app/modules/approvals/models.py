"""Approval Requests — ORM models.

Tables OWNED by this module:
    * approval_requests               (unified polymorphic approval hub)
    * attendance_regularization_requests
    * login_reset_requests

Implements the approved Approval Requests Database Architecture exactly
(BIGINT `id` primary keys).

NOT created here (reused, owned elsewhere):
    * leave_requests  -> Leave & Holiday Management module (already built)
    * employees, attendance_records, employee_leave_balances,
      employee_mobile_logins -> their respective modules

DEFERRED cross-module FOREIGN KEYS (columns created, constraints deferred):
    * employee_id -> employees (Employee Management is built, but its approved
      schema uses employees.employee_id (INTEGER) while this module's approved
      schema references employees.id (BIGINT); deferred pending the project-wide
      primary-key convention decision).
    * reviewed_by -> users (User Management, not yet built).

approval_requests.reference_id is a POLYMORPHIC logical FK (its target table is
determined by request_type). Per the approved architecture it carries NO
database-level FK constraint.
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
    Integer,
    String,
    Text,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database.base import Base


class ApprovalRequest(Base):
    __tablename__ = "approval_requests"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    org_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    branch_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("branches.branch_id", name="fk_approval_requests_branch_id_branches"),
        nullable=False,
    )
    request_type: Mapped[str] = mapped_column(String(20), nullable=False)
    request_subtype: Mapped[str | None] = mapped_column(String(50))
    # Polymorphic logical FK (no DB constraint) -> source table by request_type
    reference_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    # DEFERRED cross-module FK -> employees
    employee_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    status: Mapped[str] = mapped_column(
        String(10), nullable=False, server_default=text("'pending'")
    )
    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # DEFERRED cross-module FK -> users.id
    reviewed_by: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("users.id", name="fk_approval_requests_reviewed_by_users"),
    )
    reject_remarks: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )

    __table_args__ = (
        Index("ix_approval_requests_org_id_status", "org_id", "status"),
        Index(
            "ix_approval_requests_org_id_status_request_type",
            "org_id",
            "status",
            "request_type",
        ),
        Index("ix_approval_requests_branch_id_status", "branch_id", "status"),
        Index("ix_approval_requests_employee_id_status", "employee_id", "status"),
        CheckConstraint(
            "request_type IN ('attendance', 'leave', 'login_reset')",
            name="ck_approval_requests_request_type",
        ),
        CheckConstraint(
            "status IN ('pending', 'approved', 'rejected')",
            name="ck_approval_requests_status",
        ),
    )


class AttendanceRegularizationRequest(Base):
    __tablename__ = "attendance_regularization_requests"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    branch_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("branches.branch_id", name="fk_attendance_regularization_requests_branch_id_branches"),
        nullable=False,
    )
    # DEFERRED cross-module FK -> employees
    employee_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    attendance_date: Mapped[date] = mapped_column(Date, nullable=False)
    old_punch_time: Mapped[str | None] = mapped_column(String(20))
    new_punch_time: Mapped[str] = mapped_column(String(20), nullable=False)
    employee_reason: Mapped[str | None] = mapped_column(Text)
    category: Mapped[str | None] = mapped_column(String(50))
    attachment_url: Mapped[str | None] = mapped_column(String(500))
    requested_in: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    requested_out: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    sla_due_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_escalated: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    escalation_level: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    applied_on: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'pending'")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )

    __table_args__ = (
        Index(
            "ix_att_regularization_reqs_employee_id_attendance_date",
            "employee_id",
            "attendance_date",
        ),
        Index("ix_attendance_regularization_requests_status", "status"),
        Index("ix_att_regularization_reqs_branch_id_status", "branch_id", "status"),
        CheckConstraint(
            "status IN ('pending', 'approved', 'rejected', 'cancelled', 'withdrawn')",
            name="ck_attendance_regularization_requests_status",
        ),
    )


class LoginResetRequest(Base):
    __tablename__ = "login_reset_requests"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    branch_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("branches.branch_id", name="fk_login_reset_requests_branch_id_branches"),
        nullable=False,
    )
    # DEFERRED cross-module FK -> employees
    employee_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    request_subtype: Mapped[str | None] = mapped_column(String(50))
    request_description: Mapped[str] = mapped_column(
        String(255), nullable=False, server_default=text("'Login Reset Request'")
    )
    status: Mapped[str] = mapped_column(
        String(10), nullable=False, server_default=text("'pending'")
    )
    applied_on: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # DEFERRED cross-module FK -> users.id
    reviewed_by: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("users.id", name="fk_login_reset_requests_reviewed_by_users"),
    )
    reject_remarks: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )

    __table_args__ = (
        Index("ix_login_reset_requests_employee_id_status", "employee_id", "status"),
        Index("ix_login_reset_requests_status", "status"),
        Index("ix_login_reset_requests_branch_id_status", "branch_id", "status"),
        CheckConstraint(
            "status IN ('pending', 'approved', 'rejected')",
            name="ck_login_reset_requests_status",
        ),
    )
