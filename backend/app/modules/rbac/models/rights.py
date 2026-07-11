"""User Management & RBAC — rights templates, permissions, assignments.

Tables: rights_templates, rights_template_permissions,
user_template_assignments, user_custom_permissions.

Implements the approved User Management Database Architecture exactly.
All primary keys and foreign keys use BIGINT (project-wide PK convention).
Permission checks resolve custom-over-template at runtime; super admins
bypass. `feature_key` is a free-text machine identifier (the RBAC feature
catalogue) — the architecture defines NO CHECK constraint on it.

Intra-module FKs (enforced): all reference users / rights_templates.
DEFERRED cross-module FK (columns only):
    * rights_templates.org_id -> organizations (see user.py module docstring).
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
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database.base import Base


class RightsTemplate(Base):
    __tablename__ = "rights_templates"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    org_id: Mapped[int] = mapped_column(BigInteger, nullable=False)  # deferred FK -> organizations
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    created_by: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", name="fk_rights_templates_created_by_users"),
        nullable=False,
    )
    updated_by: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("users.id", name="fk_rights_templates_updated_by_users"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        UniqueConstraint("org_id", "name", name="uq_rights_templates_org_id_name"),
        Index("ix_rights_templates_org_id_deleted_at", "org_id", "deleted_at"),
    )

    permissions: Mapped[list["RightsTemplatePermission"]] = relationship(
        back_populates="rights_template"
    )
    assignments: Mapped[list["UserTemplateAssignment"]] = relationship(
        back_populates="rights_template",
        foreign_keys="UserTemplateAssignment.template_id",
    )


class RightsTemplatePermission(Base):
    __tablename__ = "rights_template_permissions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    template_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "rights_templates.id",
            name="fk_rights_template_permissions_template_id_rights_templates",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    feature_key: Mapped[str] = mapped_column(String(100), nullable=False)
    feature_label: Mapped[str] = mapped_column(String(150), nullable=False)
    parent_feature_key: Mapped[str | None] = mapped_column(String(100))
    can_create: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    can_read: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    can_edit: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    can_delete: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))

    __table_args__ = (
        # Unique already provides the (template_id, feature_key) lookup index.
        UniqueConstraint(
            "template_id",
            "feature_key",
            name="uq_rights_template_permissions_template_id_feature_key",
        ),
    )

    rights_template: Mapped["RightsTemplate"] = relationship(back_populates="permissions")


class UserTemplateAssignment(Base):
    __tablename__ = "user_template_assignments"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "users.id", name="fk_user_template_assignments_user_id_users", ondelete="CASCADE"
        ),
        nullable=False,
    )
    template_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "rights_templates.id",
            name="fk_user_template_assignments_template_id_rights_templates",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    assigned_by: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", name="fk_user_template_assignments_assigned_by_users"),
        nullable=False,
    )
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )

    __table_args__ = (
        UniqueConstraint("user_id", name="uq_user_template_assignments_user_id"),
    )

    user: Mapped["User"] = relationship(  # noqa: F821
        back_populates="template_assignment", foreign_keys=[user_id]
    )
    rights_template: Mapped["RightsTemplate"] = relationship(
        back_populates="assignments", foreign_keys=[template_id]
    )


class UserCustomPermission(Base):
    __tablename__ = "user_custom_permissions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", name="fk_user_custom_permissions_user_id_users", ondelete="CASCADE"),
        nullable=False,
    )
    feature_key: Mapped[str] = mapped_column(String(100), nullable=False)
    parent_feature_key: Mapped[str | None] = mapped_column(String(100))
    can_create: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    can_read: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    can_edit: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    can_delete: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    set_by: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", name="fk_user_custom_permissions_set_by_users"),
        nullable=False,
    )
    set_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )

    __table_args__ = (
        # Unique already provides the (user_id, feature_key) lookup index.
        UniqueConstraint(
            "user_id", "feature_key", name="uq_user_custom_permissions_user_id_feature_key"
        ),
    )

    user: Mapped["User"] = relationship(  # noqa: F821
        back_populates="custom_permissions", foreign_keys=[user_id]
    )
