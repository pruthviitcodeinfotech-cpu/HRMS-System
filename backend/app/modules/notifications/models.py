"""Notifications ORM models.

Tables: notifications, notification_recipients.

The module owns only the in-app notification message table and the per-user
recipient state table. Delivery providers, templates, preferences, websocket
state, and background jobs are intentionally outside this database layer.
"""

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database.base import Base


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    org_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "organizations.org_id",
            name="fk_notifications_org_id_organizations",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    notification_type: Mapped[str] = mapped_column(String(50), nullable=False)
    priority: Mapped[str] = mapped_column(String(20), nullable=False)
    source_module: Mapped[str | None] = mapped_column(String(100))
    source_entity_type: Mapped[str | None] = mapped_column(String(100))
    source_entity_id: Mapped[int | None] = mapped_column(BigInteger)
    created_by: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey(
            "users.id",
            name="fk_notifications_created_by_users",
            ondelete="SET NULL",
        ),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        Index("ix_notifications_org_id_created_at", "org_id", "created_at"),
        Index(
            "ix_notifications_org_id_source_module_source_entity_type_source_entity_id",
            "org_id",
            "source_module",
            "source_entity_type",
            "source_entity_id",
        ),
    )

    organization: Mapped["Organization"] = relationship("Organization")  # noqa: F821
    creator: Mapped["User"] = relationship("User", foreign_keys=[created_by])  # noqa: F821
    recipients: Mapped[list["NotificationRecipient"]] = relationship(
        back_populates="notification"
    )


class NotificationRecipient(Base):
    __tablename__ = "notification_recipients"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    notification_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "notifications.id",
            name="fk_notification_recipients_notification_id_notifications",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    org_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "organizations.org_id",
            name="fk_notification_recipients_org_id_organizations",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "users.id",
            name="fk_notification_recipients_user_id_users",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )

    __table_args__ = (
        UniqueConstraint(
            "notification_id",
            "user_id",
            name="uq_notification_recipients_notification_id_user_id",
        ),
        Index(
            "ix_notification_recipients_org_id_user_id_deleted_at",
            "org_id",
            "user_id",
            "deleted_at",
        ),
        Index(
            "ix_notification_recipients_org_id_user_id_read_at",
            "org_id",
            "user_id",
            "read_at",
        ),
        Index(
            "ix_notification_recipients_user_id_created_at",
            "user_id",
            "created_at",
        ),
    )

    notification: Mapped["Notification"] = relationship(
        "Notification", back_populates="recipients"
    )
    organization: Mapped["Organization"] = relationship("Organization")  # noqa: F821
    user: Mapped["User"] = relationship("User")  # noqa: F821
