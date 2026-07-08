"""Reusable declarative mixins for new ORM models.

These are **opt-in** helpers for future models. Existing models declare their
columns inline and are intentionally left unchanged; nothing here is applied to
them. A new model can compose the mixins it needs::

    class Thing(Base, TimestampMixin, SoftDeleteMixin, TenantMixin):
        __tablename__ = "things"
        id: Mapped[int] = mapped_column(BigInteger, primary_key=True)

Column definitions follow the project conventions: ``BIGINT`` keys, timezone-aware
timestamps defaulting to ``now()``, and boolean/timestamp soft-delete.
"""

from datetime import datetime, timezone

from sqlalchemy import BigInteger, Boolean, DateTime, text
from sqlalchemy.orm import Mapped, mapped_column


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class TimestampMixin:
    """Adds ``created_at`` / ``updated_at`` (timezone-aware, server-defaulted).

    ``updated_at`` also refreshes on UPDATE via SQLAlchemy's ``onupdate`` hook.
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
        onupdate=_utcnow,
    )


class SoftDeleteMixin:
    """Adds boolean ``is_deleted`` plus a nullable ``deleted_at`` timestamp."""

    is_deleted: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class TenantMixin:
    """Adds the multi-tenancy discriminator ``org_id`` (BIGINT, indexed)."""

    org_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
