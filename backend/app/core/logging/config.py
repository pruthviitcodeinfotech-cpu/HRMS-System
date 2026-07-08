"""Structured logging configuration (structlog).

``configure_logging()`` wires structlog + the stdlib logging root once at startup.
Every log event is automatically enriched with the request correlation id and the
authenticated user id from the request context, and rendered as JSON or a
human-friendly console format per ``LOG_FORMAT``.
"""

from __future__ import annotations

import logging
from typing import Any

import structlog

from app.core.config.settings import settings
from app.core.constants.enums import LogFormat
from app.core.middleware.request_context import get_current_user_id, get_request_id


def _add_request_context(
    _logger: Any, _method: str, event_dict: dict[str, Any]
) -> dict[str, Any]:
    """structlog processor: inject request_id / user_id when available."""
    request_id = get_request_id()
    if request_id is not None:
        event_dict.setdefault("request_id", request_id)
    user_id = get_current_user_id()
    if user_id is not None:
        event_dict.setdefault("user_id", user_id)
    return event_dict


def configure_logging() -> None:
    """Configure structlog and the stdlib logging root. Idempotent."""
    level = getattr(logging, settings.log_level, logging.INFO)

    shared_processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        _add_request_context,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    if settings.log_format is LogFormat.JSON:
        renderer: Any = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=False)

    structlog.configure(
        processors=[*shared_processors, renderer],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    logging.basicConfig(level=level, format="%(message)s")
    logging.getLogger("uvicorn.access").handlers.clear()


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Return a bound structlog logger."""
    return structlog.get_logger(name)
