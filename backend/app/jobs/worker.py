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
    deliver_notification,
    generate_report_export,
    run_leave_accrual,
    run_leave_accrual_all_orgs,
    send_email,
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
    deliver_notification,
    send_email,
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


async def on_job_start(ctx: dict[str, Any]) -> None:
    """Hook run by the worker when a job starts execution."""
    import json
    import datetime
    from arq.jobs import Job

    job_id = ctx["job_id"]
    redis = ctx["redis"]
    job = Job(job_id, redis)
    try:
        job_info = await job.info()
        if job_info:
            raw_status = await redis.get(f"job_status:{job_id}")
            if raw_status:
                status_data = json.loads(raw_status)
            else:
                status_data = {
                    "job_id": job_id,
                    "job_name": job_info.function,
                    "enqueue_time": job_info.enqueue_time.isoformat(),
                }

            status_data.update({
                "status": "running",
                "start_time": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "try_count": ctx["job_try"],
            })
            await redis.setex(f"job_status:{job_id}", 86400, json.dumps(status_data))
            _logger.info("job_started", job_id=job_id, job_name=job_info.function, try_count=ctx["job_try"])
    except Exception as exc:
        _logger.error("on_job_start_tracking_failed", job_id=job_id, error=str(exc))


async def after_job_end(ctx: dict[str, Any]) -> None:
    """Hook run by the worker after a job finishes execution."""
    import json
    import datetime
    from arq.jobs import Job

    job_id = ctx["job_id"]
    redis = ctx["redis"]
    job = Job(job_id, redis)
    try:
        res_info = await job.result_info()
        if res_info:
            raw_status = await redis.get(f"job_status:{job_id}")
            if raw_status:
                status_data = json.loads(raw_status)
            else:
                status_data = {
                    "job_id": job_id,
                    "job_name": res_info.function,
                    "enqueue_time": res_info.enqueue_time.isoformat(),
                }

            if res_info.success:
                status_data.update({
                    "status": "completed",
                    "complete_time": res_info.finish_time.isoformat(),
                    "try_count": res_info.job_try,
                    "error": None,
                })
                _logger.info(
                    "job_completed",
                    job_id=job_id,
                    job_name=res_info.function,
                    duration=(res_info.finish_time - res_info.start_time).total_seconds(),
                )
            else:
                status_data.update({
                    "status": "failed",
                    "complete_time": res_info.finish_time.isoformat(),
                    "try_count": res_info.job_try,
                    "error": str(res_info.result),
                })
                _logger.error(
                    "job_failed",
                    job_id=job_id,
                    job_name=res_info.function,
                    error=str(res_info.result),
                )

            await redis.setex(f"job_status:{job_id}", 86400, json.dumps(status_data))
    except Exception as exc:
        _logger.error("after_job_end_tracking_failed", job_id=job_id, error=str(exc))


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
    on_job_start = on_job_start
    after_job_end = after_job_end


def main() -> None:
    """Start the worker (blocks until interrupted)."""
    run_worker(WorkerSettings)  # type: ignore[arg-type]


if __name__ == "__main__":
    main()
