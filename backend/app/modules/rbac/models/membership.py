"""User Management & RBAC — multi-organization membership model.

Table: user_organization_memberships.

This table is the foundation of Multi-Organization Switching (Phase 2).
It captures the many-to-many relationship between users and organizations,
allowing a single user identity to hold memberships in multiple tenants while
leaving all existing tables (users, user_template_assignments, user_custom_permissions,
user_branch_access, user_department_access) completely unchanged.

Design notes
────────────
* ``users.org_id`` (the home-org FK) is intentionally NOT removed. All existing
  queries, constraints, and foreign-key chains that rely on it continue to work.
* A user's membership in their home org is represented here as ``is_primary=True``.
  The backfill migration inserts one such row for every existing user so the
  membership table is always the authoritative list of org memberships.
* ``is_active=False`` means the membership has been deactivated (user removed from
  org) but the row is kept for audit history.
* RBAC data (rights-template assignment, custom permissions, branch/department
  scope) for the *target* org is stored in the existing RBAC tables, keyed only
  by ``user_id``.  An admin must provision those records to grant meaningful
  access in the non-primary org.

Intra-module FKs (enforced):
    * user_id       -> users.id            ON DELETE CASCADE
    * org_id        -> organizations.org_id ON DELETE CASCADE
    * invited_by    -> users.id            ON DELETE SET NULL
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database.base import Base


class UserOrganizationMembership(Base):
    """Junction table: one row = one user's membership in one organization."""

    __tablename__ = "user_organization_memberships"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)

    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "users.id",
            name="fk_user_org_memberships_user_id_users",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    org_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "organizations.org_id",
            name="fk_user_org_memberships_org_id_organizations",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    # True for the membership that corresponds to users.org_id (home org).
    # There must be exactly one primary membership per user (enforced at
    # service layer, not DB level, to avoid a complex partial-unique index).
    is_primary: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )

    # False = membership revoked; row kept for audit.
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true")
    )

    # Who added this user to the org (NULL = system / migration backfill).
    invited_by: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey(
            "users.id",
            name="fk_user_org_memberships_invited_by_users",
            ondelete="SET NULL",
        ),
    )

    # When the invitation was created (defaults to row-creation time).
    invited_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )

    # When the user accepted / was auto-approved (NULL = pending or N/A).
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        # Each (user, org) pair is unique — prevents duplicate memberships.
        UniqueConstraint(
            "user_id",
            "org_id",
            name="uq_user_org_memberships_user_id_org_id",
        ),
        # Org-level lookup: "list all members of org X" — used by admin UIs.
        Index("ix_user_org_memberships_org_id_is_active", "org_id", "is_active"),
        # User-level lookup: "list all orgs this user belongs to" (hot path
        # for GET /auth/my-organizations and token issuance after org switch).
        Index("ix_user_org_memberships_user_id_is_active", "user_id", "is_active"),
    )

    # ORM relationships — back_populates wired in user.py via string reference.
    user: Mapped["User"] = relationship(  # noqa: F821
        back_populates="org_memberships",
        foreign_keys=[user_id],
    )
