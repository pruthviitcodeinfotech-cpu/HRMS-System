"""Datetime utilities (timezone-aware, UTC-first).

All timestamps in the system are timezone-aware and stored/compared in UTC.
"""

from __future__ import annotations

from datetime import date, datetime, time, timezone


def utcnow() -> datetime:
    """Return the current time as a timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)


def to_utc(value: datetime) -> datetime:
    """Return ``value`` as UTC. Naive datetimes are assumed to already be UTC."""
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def to_iso(value: datetime | date | time | None) -> str | None:
    """Return the ISO-8601 string for ``value`` (or ``None``)."""
    return value.isoformat() if value is not None else None


def start_of_day(value: date) -> datetime:
    """Return the UTC datetime at 00:00:00 of ``value``."""
    return datetime(value.year, value.month, value.day, tzinfo=timezone.utc)


def end_of_day(value: date) -> datetime:
    """Return the UTC datetime at 23:59:59.999999 of ``value``."""
    return datetime(value.year, value.month, value.day, 23, 59, 59, 999999, tzinfo=timezone.utc)
