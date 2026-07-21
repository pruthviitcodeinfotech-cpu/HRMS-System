"""Job queue: arq connection settings, the shared pool, and the ``enqueue`` helper.

The queue is `arq <https://arq-docs.helpmanual.io/>`_ over the same Redis instance the
cache and event broker use (``REDIS_URL``). This module is the *producer* half — it is
imported by request handlers and services and deliberately imports **no** models,
services, or the worker, so enqueueing costs nothing but a Redis round-trip. The
*consumer* half (the job bodies) lives in :mod:`app.jobs.tasks`.

Failure policy when Redis is down
---------------------------------
:func:`enqueue` **fails loudly**: it logs at ERROR and raises
:class:`QueueUnavailableException` (503). It never swallows the error and never returns
a fake job id, because a caller that has already told the user "queued" — a payslip
email, an export — has made a promise. A job that silently vanishes is a support ticket
nobody can trace; a 503 the caller can retry is not. This is the opposite of the cache
policy in :mod:`app.core.cache.redis` (which degrades to a miss), and deliberately so:
a cache read has a correct fallback (recompute), an enqueue does not.

Callers that *do* have a correct fallback may catch :class:`QueueUnavailableException`
and take it — the reports export runs the work in-process rather than losing it (see
``ReportsService._dispatch_export``). Callers without one let it propagate to the user.
"""

from __future__ import annotations

try:
    from enum import StrEnum
except ImportError:
    from enum import Enum

    class StrEnum(str, Enum):
        pass
from typing import Any

from arq import create_pool
from arq.connections import ArqRedis, RedisSettings

from app.core.config.settings import settings
from app.core.exceptions.base import AppException
from app.core.logging import get_logger

_logger = get_logger("jobs.queue")

#: Process-wide arq pool (a Redis connection pool). Created on first enqueue.
_pool: ArqRedis | None = None


class QueueUnavailableException(AppException):
    """The background queue could not be reached, so the job was NOT enqueued.

    Raised instead of leaking a raw ``redis.exceptions.ConnectionError`` so the global
    handler renders the standard envelope and the caller sees an honest, retryable 503
    rather than a 500 (or, worse, a success response for work that was never queued).
    """

    code = "QUEUE_UNAVAILABLE"
    status_code = 503
    message = "The background job queue is unavailable. Please retry in a moment."


class JobName(StrEnum):
    """Every enqueueable job.

    The values are the arq function names, which are the ``__name__`` of the coroutines
    in :mod:`app.jobs.tasks`. ``tests/unit/test_jobs.py`` asserts this enum, the task
    module, and ``WorkerSettings.functions`` agree, so a job cannot be added on one side
    and silently forgotten on the other.
    """

    SEND_PAYSLIP_EMAIL = "send_payslip_email"
    RUN_LEAVE_ACCRUAL = "run_leave_accrual"
    SYNC_DEVICE = "sync_device"
    GENERATE_REPORT_EXPORT = "generate_report_export"
    DELIVER_NOTIFICATION = "deliver_notification"
    SEND_EMAIL = "send_email"


def get_redis_settings() -> RedisSettings:
    """Build arq's :class:`RedisSettings` from ``REDIS_URL``."""
    return RedisSettings.from_dsn(settings.redis_url)


async def get_queue_pool() -> ArqRedis:
    """Return the process-wide arq pool, creating it on first use.

    Raises:
        QueueUnavailableException: Redis is unreachable.
    """
    global _pool
    if _pool is None:
        try:
            _pool = await create_pool(get_redis_settings())
        except Exception as exc:  # noqa: BLE001 - any backend failure is "queue is down"
            _logger.error("queue_unavailable", operation="connect", error=str(exc))
            raise QueueUnavailableException() from exc
    return _pool


async def close_queue_pool() -> None:
    """Close the arq pool (call on process shutdown)."""
    global _pool
    if _pool is not None:
        await _pool.aclose()
        _pool = None


async def enqueue(job_name: JobName | str, **kwargs: Any) -> str:
    """Enqueue ``job_name`` with ``kwargs`` and return the arq job id.

    Keyword arguments are serialised by arq and handed to the task coroutine, so they
    must be simple values (ints, strings, dates, plain dicts) — **never** an ORM
    instance, an ``AsyncSession``, or anything else bound to the calling request. Each
    job opens its own session from the arguments it is given.

    Raises:
        QueueUnavailableException: Redis is unreachable, or the job was not accepted.
    """
    import json
    import datetime
    name = str(job_name)
    pool = await get_queue_pool()
    try:
        job = await pool.enqueue_job(name, **kwargs)
    except Exception as exc:  # noqa: BLE001 - a failed enqueue must never look queued
        _logger.error("queue_enqueue_failed", job=name, error=str(exc))
        raise QueueUnavailableException() from exc

    if job is None:
        # arq returns None when a job with the same ``_job_id`` is already queued or
        # running. We never pass ``_job_id``, so reaching here means Redis dropped the
        # write — report it as a failure rather than pretending the work is queued.
        _logger.error("queue_enqueue_dropped", job=name)
        raise QueueUnavailableException(
            "The background job could not be queued. Please retry in a moment."
        )

    # Track pending status in Redis
    status_data = {
        "job_id": job.job_id,
        "job_name": name,
        "status": "pending",
        "enqueue_time": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "try_count": 0,
        "error": None,
    }
    try:
        await pool.setex(f"job_status:{job.job_id}", 86400, json.dumps(status_data))
    except Exception as exc:
        _logger.error("queue_status_tracking_failed", job_id=job.job_id, error=str(exc))

    _logger.info("job_enqueued", job=name, job_id=job.job_id)
    return job.job_id
