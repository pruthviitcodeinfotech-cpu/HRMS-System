"""Activity Log — audit trail model.

Table: activity_logs.

Implements the approved Activity Log Database Architecture exactly (single
append-only, immutable audit table; one row per mutation event across all HRMS
modules). Names (`employee_name`, `performed_by_name`) are denormalised
snapshots stored at write time so the log preserves historical display values
even after the referenced employee/user is renamed or deleted.

Resolved conflicts vs. the PDF (confirmed with the product owner):
    * FK targets bind to the ACTUAL built primary keys — organizations.org_id,
      employees.employee_id, users.id (the PDF's `.id` names are naming drift;
      those columns do not exist on the organizations/employees tables).
    * org_id is BIGINT (matches organizations.org_id after the project-wide
      BIGINT PK standardization; the PDF's INT would mismatch its FK target).
    * action_from is VARCHAR + CHECK, not native ENUM (project-wide convention;
      values preserved exactly — see constants.py).
    * performed_by_user_id is NULLABLE with ON DELETE SET NULL (the PDF marked it
      NOT NULL but also SET NULL — contradictory; the module's explicit rule
      "log entry preserved even if user is deleted" requires nullable).

Append-only enforcement (INSERT + SELECT only; no UPDATE/DELETE) is a DB
role/privilege concern per the architecture and is intentionally NOT expressed
as a schema object here.

Enforced FKs (all target tables already exist): org_id -> organizations
(RESTRICT), employee_id -> employees (SET NULL), performed_by_user_id -> users
(SET NULL). There are NO physical FKs from other module tables into
activity_logs — writing modules insert rows as a logical relationship.
"""

from datetime import date, datetime, time

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    Time,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database.base import Base


class ActivityLog(Base):
    __tablename__ = "activity_logs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    org_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "organizations.org_id",
            name="fk_activity_logs_org_id_organizations",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    module: Mapped[str] = mapped_column(String(100), nullable=False)
    sub_module: Mapped[str | None] = mapped_column(String(150))
    employee_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey(
            "employees.employee_id",
            name="fk_activity_logs_employee_id_employees",
            ondelete="SET NULL",
        ),
    )
    employee_name: Mapped[str | None] = mapped_column(String(200))
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    payroll_date: Mapped[date | None] = mapped_column(Date)
    action_type: Mapped[str] = mapped_column(String(50), nullable=False)
    # Nullable + ON DELETE SET NULL: logs survive user deletion (name snapshotted).
    performed_by_user_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey(
            "users.id",
            name="fk_activity_logs_performed_by_user_id_users",
            ondelete="SET NULL",
        ),
    )
    performed_by_name: Mapped[str] = mapped_column(String(200), nullable=False)
    log_date: Mapped[date] = mapped_column(Date, nullable=False)
    log_time: Mapped[time] = mapped_column(Time, nullable=False)
    logged_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    action_from: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'Web App'")
    )

    __table_args__ = (
        Index(
            "ix_activity_logs_org_id_logged_at",
            "org_id",
            text("logged_at DESC"),
        ),
        Index("ix_activity_logs_org_id_log_date", "org_id", "log_date"),
        Index("ix_activity_logs_org_id_employee_id", "org_id", "employee_id"),
        Index("ix_activity_logs_org_id_module", "org_id", "module"),
        Index("ix_activity_logs_performed_by_user_id", "performed_by_user_id"),
        CheckConstraint(
            "action_type IN ('Insert', 'Update', 'Delete', 'Assign', 'Bulk Assign')",
            name="ck_activity_logs_action_type",
        ),
        CheckConstraint(
            "action_from IN ('Web App', 'Mobile App')",
            name="ck_activity_logs_action_from",
        ),
    )
