"""Base entity conventions shared by all ORM models.

Re-exports the declarative :class:`~app.core.database.base.Base` (the single
metadata/naming-convention root) together with the opt-in mixins, so modules can
import their persistence building blocks from one place::

    from app.shared.base.model import Base, TimestampMixin, SoftDeleteMixin, TenantMixin
"""

from app.core.database.base import Base
from app.core.database.mixins import SoftDeleteMixin, TenantMixin, TimestampMixin

__all__ = ["Base", "TimestampMixin", "SoftDeleteMixin", "TenantMixin"]
