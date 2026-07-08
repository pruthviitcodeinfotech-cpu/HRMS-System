"""Generic async repository (Repository Pattern).

:class:`BaseRepository` provides the reusable CRUD + query surface every module
repository inherits. It is deliberately thin: data access only, no business rules.
All methods operate on a caller-supplied :class:`~sqlalchemy.ext.asyncio.AsyncSession`
so the service layer owns the transaction boundary.

Subclass it with the concrete model::

    class EmployeeRepository(BaseRepository[Employee]):
        def __init__(self, session: AsyncSession) -> None:
            super().__init__(session, Employee)
"""

from __future__ import annotations

from typing import Any, Generic, TypeVar

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants.enums import SortOrder
from app.core.database.base import Base
from app.shared.utils.query import apply_filters, apply_pagination, apply_sorting

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """Reusable async data-access base for a single ORM model."""

    def __init__(self, session: AsyncSession, model: type[ModelType]) -> None:
        self.session = session
        self.model = model

    # --- Reads ---------------------------------------------------------------
    async def get_by_id(self, entity_id: int) -> ModelType | None:
        """Return the row with primary key ``entity_id``, or ``None``."""
        return await self.session.get(self.model, entity_id)

    async def list(
        self,
        *,
        filters: dict[str, Any] | None = None,
        sort_by: str | None = None,
        sort_order: SortOrder | str = SortOrder.ASC,
        page: int | None = None,
        page_size: int | None = None,
        allowed_sort: set[str] | None = None,
    ) -> list[ModelType]:
        """Return rows matching ``filters``, optionally sorted and paginated."""
        stmt = apply_filters(select(self.model), self.model, filters)
        stmt = apply_sorting(
            stmt, self.model, sort_by, sort_order, allowed=allowed_sort
        )
        if page is not None and page_size is not None:
            stmt = apply_pagination(stmt, page=page, page_size=page_size)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count(self, *, filters: dict[str, Any] | None = None) -> int:
        """Return the number of rows matching ``filters``."""
        stmt = apply_filters(select(func.count()).select_from(self.model), self.model, filters)
        result = await self.session.execute(stmt)
        return int(result.scalar_one())

    async def exists(self, *, filters: dict[str, Any] | None = None) -> bool:
        """Return whether any row matches ``filters``."""
        stmt = apply_filters(select(self.model.__table__.c[0]), self.model, filters).limit(1)
        result = await self.session.execute(stmt)
        return result.first() is not None

    # --- Writes --------------------------------------------------------------
    async def create(self, data: dict[str, Any]) -> ModelType:
        """Insert and return a new instance built from ``data`` (flushed, not committed)."""
        instance = self.model(**data)
        self.session.add(instance)
        await self.session.flush()
        await self.session.refresh(instance)
        return instance

    async def update(self, instance: ModelType, data: dict[str, Any]) -> ModelType:
        """Apply ``data`` to ``instance`` and flush the change."""
        for key, value in data.items():
            setattr(instance, key, value)
        self.session.add(instance)
        await self.session.flush()
        await self.session.refresh(instance)
        return instance

    async def delete(self, instance: ModelType) -> None:
        """Hard-delete ``instance`` (flushed, not committed).

        Modules with a soft-delete column should instead ``update`` the
        ``is_deleted`` / ``deleted_at`` fields.
        """
        await self.session.delete(instance)
        await self.session.flush()
