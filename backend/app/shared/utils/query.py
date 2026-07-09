"""Reusable SQLAlchemy query helpers: filtering, sorting, pagination.

Generic building blocks used by :class:`~app.shared.base.repository.BaseRepository`
and any repository that needs dynamic list queries. Filtering/sorting operate on an
allowlist of real model columns so callers cannot inject arbitrary attributes.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import Select, asc, desc
from sqlalchemy.orm import InstrumentedAttribute

from app.core.constants.enums import SortOrder


def _model_columns(model: type[Any]) -> dict[str, InstrumentedAttribute[Any]]:
    return {c.key: getattr(model, c.key) for c in model.__table__.columns}


def apply_filters(
    stmt: Select[Any], model: type[Any], filters: dict[str, Any] | None
) -> Select[Any]:
    """Apply equality / ``IN`` filters for known columns, ignoring ``None`` values.

    ``filters`` maps column name -> value. A list/tuple/set value becomes an ``IN``
    clause. Unknown column names are ignored (never trusted from client input).
    """
    if not filters:
        return stmt
    columns = _model_columns(model)
    for name, value in filters.items():
        if value is None or name not in columns:
            continue
        column = columns[name]
        if isinstance(value, (list, tuple, set)):
            stmt = stmt.where(column.in_(list(value)))
        else:
            stmt = stmt.where(column == value)
    return stmt


def apply_sorting(
    stmt: Select[Any],
    model: type[Any],
    sort_by: str | None,
    sort_order: SortOrder | str = SortOrder.ASC,
    *,
    allowed: set[str] | None = None,
    default_sort_by: str | None = None,
) -> Select[Any]:
    """Order the statement by ``sort_by`` when it is a permitted column.

    ``allowed`` optionally restricts sortable columns. Falls back to
    ``default_sort_by`` (or leaves ordering untouched) when ``sort_by`` is invalid.
    """
    columns = _model_columns(model)
    field = sort_by if (sort_by in columns and (allowed is None or sort_by in allowed)) else None
    if field is None:
        field = default_sort_by if (default_sort_by in columns) else None
    if field is None:
        return stmt
    order = SortOrder(sort_order) if not isinstance(sort_order, SortOrder) else sort_order
    direction = desc if order is SortOrder.DESC else asc
    return stmt.order_by(direction(columns[field]))


def apply_pagination(stmt: Select[Any], *, page: int, page_size: int) -> Select[Any]:
    """Apply LIMIT/OFFSET for a 1-based ``page`` of ``page_size`` rows."""
    return stmt.limit(page_size).offset((page - 1) * page_size)
