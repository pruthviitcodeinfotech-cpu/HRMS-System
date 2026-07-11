"""User Management & RBAC — data-scoping access tables.

Tables: user_branch_access, user_department_access.

Implements the approved User Management Database Architecture exactly (BIGINT
`id`). These are the second authorization layer: they restrict which branches /
departments' data a user may see, independent of feature permissions.

Intra-module FKs (enforced): user_id / granted_by -> users.
DEFERRED cross-module FKs (columns only):
    * branch_id     -> branches   (built PK `branch_id` INT vs this module's
      `branches.id` BIGINT; deferred, ON DELETE RESTRICT later).
    * department_id -> departments (built PK `dept_id` INT vs `departments.id`
      BIGINT; deferred, ON DELETE RESTRICT later).
"""

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Index,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database.base import Base


class UserBranchAccess(Base):
    __tablename__ = "user_branch_access"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", name="fk_user_branch_access_user_id_users", ondelete="CASCADE"),
        nullable=False,
    )
    # DEFERRED cross-module FK -> branches
    branch_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    granted_by: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", name="fk_user_branch_access_granted_by_users"),
        nullable=False,
    )
    granted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )

    __table_args__ = (
        UniqueConstraint("user_id", "branch_id", name="uq_user_branch_access_user_id_branch_id"),
        # FK -> branches ON DELETE RESTRICT. The uq above leads with user_id, so it
        # cannot serve the branch_id probe PostgreSQL runs on every branch delete.
        Index("ix_user_branch_access_branch_id", "branch_id"),
    )

    user: Mapped["User"] = relationship(  # noqa: F821
        back_populates="branch_access", foreign_keys=[user_id]
    )


class UserDepartmentAccess(Base):
    __tablename__ = "user_department_access"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", name="fk_user_department_access_user_id_users", ondelete="CASCADE"),
        nullable=False,
    )
    # DEFERRED cross-module FK -> departments
    department_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    granted_by: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", name="fk_user_department_access_granted_by_users"),
        nullable=False,
    )
    granted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )

    __table_args__ = (
        UniqueConstraint(
            "user_id", "department_id", name="uq_user_department_access_user_id_department_id"
        ),
        # FK -> departments ON DELETE RESTRICT. The uq above leads with user_id, so it
        # cannot serve the department_id probe run on every department delete.
        Index("ix_user_department_access_department_id", "department_id"),
    )

    user: Mapped["User"] = relationship(  # noqa: F821
        back_populates="department_access", foreign_keys=[user_id]
    )
