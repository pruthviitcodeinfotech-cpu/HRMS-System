"""Background worker entrypoint (arq over Redis).

Run it with ``make worker`` (``python -m app.jobs.worker``), or with arq's own CLI
(``arq app.jobs.worker.WorkerSettings``) — both drive the same :class:`WorkerSettings`.

The worker is a *separate process* from the API. It shares the settings, the models, and
the services, but it owns its own database engine: :func:`startup` builds the session
factory once and hands it to every job through ``ctx`` (each job still opens and closes
its own session from it — see :mod:`app.jobs.tasks`), and :func:`shutdown` disposes the
pool so the process exits without leaking connections.

Adding a job? Register it in :data:`FUNCTIONS` *and* in
:class:`~app.jobs.queue.JobName`. ``tests/unit/test_jobs.py`` fails if the two disagree,
so a job cannot be shipped unregistered (which would make every enqueue of it fail at
runtime with "function not found").
"""

from __future__ import annotations

from typing import Any

from arq import run_worker
from arq.connections import RedisSettings
from arq.cron import CronJob
from arq.typing import WorkerCoroutine

from app.core.cache.redis import close_redis
from app.core.config.settings import settings
from app.core.database.session import dispose_engine, get_session_factory
from app.core.logging import configure_logging, get_logger
from app.jobs.queue import close_queue_pool, get_redis_settings
from app.jobs.scheduler import build_cron_jobs
from app.jobs.tasks import (
    generate_report_export,
    run_leave_accrual,
    run_leave_accrual_all_orgs,
    send_payslip_email,
    sync_all_devices,
    sync_device,
)

_logger = get_logger("jobs.worker")

#: Every job the worker can execute. The enqueueable ones are mirrored by
#: :class:`app.jobs.queue.JobName`; the two ``*_all_*`` fan-out coroutines are the cron
#: entrypoints (arq registers cron functions separately, but listing them here also makes
#: them enqueueable on demand — e.g. to force a sweep without waiting for the schedule).
FUNCTIONS: list[WorkerCoroutine] = [
    send_payslip_email,
    run_leave_accrual,
    sync_device,
    generate_report_export,
    run_leave_accrual_all_orgs,
    sync_all_devices,
]


def job_name(function: WorkerCoroutine) -> str:
    """Return the name arq registers a job function under."""
    return getattr(function, "__name__", str(function))


async def startup(ctx: dict[str, Any]) -> None:
    """Worker startup: configure logging and publish the DB session factory on ``ctx``."""
    configure_logging()
    ctx["session_factory"] = get_session_factory()
    _logger.info(
        "worker_starting",
        environment=settings.environment.value,
        max_jobs=settings.worker_concurrency,
        functions=[job_name(f) for f in FUNCTIONS],
        scheduler_enabled=settings.scheduler_enabled,
    )


async def shutdown(ctx: dict[str, Any]) -> None:
    """Worker shutdown: dispose the DB engine and close the Redis clients."""
    ctx.pop("session_factory", None)
    await dispose_engine()
    await close_queue_pool()
    await close_redis()
    _logger.info("worker_stopped")


class WorkerSettings:
    """arq worker configuration (``arq app.jobs.worker.WorkerSettings``)."""

    functions: list[WorkerCoroutine] = FUNCTIONS
    cron_jobs: list[CronJob] = build_cron_jobs()
    redis_settings: RedisSettings = get_redis_settings()
    max_jobs: int = settings.worker_concurrency
    job_timeout: int = settings.job_timeout_seconds
    max_tries: int = settings.job_max_tries
    keep_result: int = settings.job_result_ttl_seconds
    on_startup = startup
    on_shutdown = shutdown


def main() -> None:
    """Start the worker (blocks until interrupted)."""
    run_worker(WorkerSettings)  # type: ignore[arg-type]


if __name__ == "__main__":
    main()
