"""Base service (Service Pattern) utilities.

:class:`BaseService` gives module services a shared home for the transaction
boundary, common guard helpers, and pagination assembly. It holds **no business
logic** — concrete services subclass it and inject their repositories.

    class EmployeeService(BaseService):
        def __init__(self, session: AsyncSession) -> None:
            super().__init__(session)
            self.employees = EmployeeRepository(session)
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any, TypeVar

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions.base import ConflictException, NotFoundException
from app.shared.schemas.pagination import PaginatedResponse

T = TypeVar("T")


class BaseService:
    """Reusable base for module services (owns the transaction boundary)."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    @asynccontextmanager
    async def transaction(self) -> AsyncIterator[None]:
        """Run a block inside a transaction: commit on success, rollback on error.

        Use for multi-step writes that must be atomic::

            async with self.transaction():
                await repo_a.create(...)
                await repo_b.update(...)
        """
        try:
            yield
            await self.session.commit()
        except Exception:
            await self.session.rollback()
            raise

    async def commit(self) -> None:
        """Commit the current unit of work."""
        await self.session.commit()

    # --- Common guards -------------------------------------------------------
    @staticmethod
    def ensure_found(instance: T | None, *, message: str = "Resource not found.") -> T:
        """Return ``instance`` or raise :class:`NotFoundException` if it is ``None``."""
        if instance is None:
            raise NotFoundException(message)
        return instance

    @staticmethod
    def ensure_unique(exists: bool, *, message: str = "Resource already exists.") -> None:
        """Raise :class:`ConflictException` when ``exists`` is truthy."""
        if exists:
            raise ConflictException(message)

    # --- Pagination assembly -------------------------------------------------
    @staticmethod
    def paginate(
        items: list[Any],
        *,
        page: int,
        page_size: int,
        total_records: int,
    ) -> PaginatedResponse[Any]:
        """Wrap ``items`` and the total count in a :class:`PaginatedResponse`."""
        return PaginatedResponse.build(
            items=items, page=page, page_size=page_size, total_records=total_records
        )
