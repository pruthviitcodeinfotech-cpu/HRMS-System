"""Reusable pagination request/response schemas.

``PaginationRequest`` captures ``page`` / ``page_size`` (see also the FastAPI
dependency ``app.core.dependencies.pagination``). ``PaginationMeta`` and the
generic ``PaginatedResponse`` describe the standard paged list envelope used by
every list endpoint.
"""

from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel, Field

from app.core.constants.enums import (
    DEFAULT_PAGE,
    DEFAULT_PAGE_SIZE,
    MAX_PAGE_SIZE,
    MIN_PAGE_SIZE,
)

T = TypeVar("T")


class PaginationRequest(BaseModel):
    """Inbound pagination parameters."""

    page: int = Field(default=DEFAULT_PAGE, ge=1, description="1-based page number.")
    page_size: int = Field(
        default=DEFAULT_PAGE_SIZE,
        ge=MIN_PAGE_SIZE,
        le=MAX_PAGE_SIZE,
        description="Items per page.",
    )

    @property
    def offset(self) -> int:
        """SQL OFFSET for this page."""
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        """SQL LIMIT for this page."""
        return self.page_size


class PaginationMeta(BaseModel):
    """Pagination metadata attached to a paged response."""

    page: int
    page_size: int
    total_records: int
    total_pages: int
    has_next: bool
    has_previous: bool

    @classmethod
    def build(cls, *, page: int, page_size: int, total_records: int) -> PaginationMeta:
        """Compute pagination metadata from the page window and total count."""
        total_pages = (total_records + page_size - 1) // page_size if page_size else 0
        return cls(
            page=page,
            page_size=page_size,
            total_records=total_records,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_previous=page > 1,
        )


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paged list envelope: ``{ items, pagination }``."""

    items: list[T]
    pagination: PaginationMeta

    @classmethod
    def build(
        cls,
        *,
        items: list[T],
        page: int,
        page_size: int,
        total_records: int,
    ) -> PaginatedResponse[T]:
        return cls(
            items=items,
            pagination=PaginationMeta.build(
                page=page, page_size=page_size, total_records=total_records
            ),
        )
