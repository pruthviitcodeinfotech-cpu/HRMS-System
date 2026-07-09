"""FastAPI dependencies: pagination and sorting query parameters.

Exposes ``page`` / ``page_size`` and ``sort_by`` / ``sort_order`` as reusable
query-parameter dependencies so every list endpoint accepts them consistently.
"""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import Query

from app.core.constants.enums import (
    DEFAULT_PAGE,
    DEFAULT_PAGE_SIZE,
    MAX_PAGE_SIZE,
    MIN_PAGE_SIZE,
    SortOrder,
)


@dataclass(frozen=True)
class PaginationParams:
    """Resolved pagination query parameters."""

    page: int
    page_size: int

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        return self.page_size


@dataclass(frozen=True)
class SortParams:
    """Resolved sort query parameters."""

    sort_by: str | None
    sort_order: SortOrder


def pagination_params(
    page: int = Query(DEFAULT_PAGE, ge=1, description="1-based page number."),
    page_size: int = Query(
        DEFAULT_PAGE_SIZE,
        ge=MIN_PAGE_SIZE,
        le=MAX_PAGE_SIZE,
        description="Items per page.",
    ),
) -> PaginationParams:
    """Dependency returning validated :class:`PaginationParams`."""
    return PaginationParams(page=page, page_size=page_size)


def sort_params(
    sort_by: str | None = Query(None, description="Column to sort by."),
    sort_order: SortOrder = Query(SortOrder.ASC, description="Sort direction."),
) -> SortParams:
    """Dependency returning validated :class:`SortParams`."""
    return SortParams(sort_by=sort_by, sort_order=sort_order)
