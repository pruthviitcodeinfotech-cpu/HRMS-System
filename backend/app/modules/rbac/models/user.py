"""User Management & RBAC — user identity and sessions.

Tables: users, user_sessions.

Implements the approved User Management Database Architecture exactly.
All primary keys and foreign keys use BIGINT (project-wide PK convention).
A user account is a login identity, distinct from an employee HR record
(optional link via users.employee_id).

Intra-module FKs (enforced):
    * users.created_by       -> users (self, ON DELETE SET NULL)
    * user_sessions.user_id  -> users (ON DELETE CASCADE)
DEFERRED cross-module FKs (columns only):
    * users.org_id      -> organizations (built PK is `org_id` BIGINT; FK
      constraint deferred pending cross-module wiring).
    * users.employee_id -> employees (built PK is `employee_id` BIGINT; FK
      constraint deferred, ON DELETE SET NULL later).
"""

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import INET
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    org_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("organizations.org_id", name="fk_users_org_id_organizations"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    mobile_country_code: Mapped[str] = mapped_column(
        String(10), nullable=False, server_default=text("'+91'")
    )
    mobile_number: Mapped[str] = mapped_column(String(20), nullable=False)
    password_hash: Mapped[str | None] = mapped_column(String(255))
    is_super_admin: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    # DEFERRED cross-module FK -> employees
    employee_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey(
            "employees.employee_id", name="fk_users_employee_id_employees", ondelete="SET NULL"
        ),
    )
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("users.id", name="fk_users_created_by_users", ondelete="SET NULL"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        UniqueConstraint("org_id", "email", name="uq_users_org_id_email"),
        UniqueConstraint(
            "org_id",
            "mobile_country_code",
            "mobile_number",
            name="uq_users_org_id_mobile_country_code_mobile_number",
        ),
        Index("ix_users_org_id_is_active_deleted_at", "org_id", "is_active", "deleted_at"),
        # rbac/repository.py:93 (employee -> login lookup) and
        # notifications/service.py:589 (WHERE employee_id IN (...)).
        Index("ix_users_employee_id", "employee_id"),
    )

    sessions: Mapped[list["UserSession"]] = relationship(back_populates="user")
    template_assignment: Mapped["UserTemplateAssignment"] = relationship(  # noqa: F821
        back_populates="user",
        uselist=False,
        foreign_keys="UserTemplateAssignment.user_id",
    )
    custom_permissions: Mapped[list["UserCustomPermission"]] = relationship(  # noqa: F821
        back_populates="user", foreign_keys="UserCustomPermission.user_id"
    )
    branch_access: Mapped[list["UserBranchAccess"]] = relationship(  # noqa: F821
        back_populates="user", foreign_keys="UserBranchAccess.user_id"
    )
    department_access: Mapped[list["UserDepartmentAccess"]] = relationship(  # noqa: F821
        back_populates="user", foreign_keys="UserDepartmentAccess.user_id"
    )
    # Multi-org: all organisation memberships for this user (Phase 2).
    org_memberships: Mapped[list["UserOrganizationMembership"]] = relationship(  # noqa: F821
        back_populates="user",
        foreign_keys="UserOrganizationMembership.user_id",
    )


class UserSession(Base):
    __tablename__ = "user_sessions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", name="fk_user_sessions_user_id_users", ondelete="CASCADE"),
        nullable=False,
    )
    session_token: Mapped[str] = mapped_column(String(500), nullable=False)
    device_info: Mapped[str | None] = mapped_column(String(500))
    ip_address: Mapped[str | None] = mapped_column(INET)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))

    __table_args__ = (
        UniqueConstraint("session_token", name="uq_user_sessions_session_token"),
        Index("ix_user_sessions_user_id_is_active", "user_id", "is_active"),
    )

    user: Mapped["User"] = relationship(back_populates="sessions")
