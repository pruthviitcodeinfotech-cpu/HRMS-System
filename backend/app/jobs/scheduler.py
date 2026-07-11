"""Scheduled (cron) task registry.

arq runs cron jobs inside the worker itself — there is no separate beat process — and
guarantees that a job fires **once per matching minute across the whole worker fleet**
(the schedule is coordinated through Redis), so running several workers does not run the
accrual several times.

Registered here:

* **Nightly leave accrual** (``LEAVE_ACCRUAL_CRON_HOUR`` / ``_MINUTE``, default 01:30) —
  credits each active employee's auto-allocation for the current leave cycle, for every
  active org. Idempotent, so a missed or repeated night self-heals on the next run.
* **Periodic device sync** (every ``DEVICE_SYNC_INTERVAL_MINUTES``, default 15) — syncs
  every active biometric device.

Payslip release — the third item named in this module's original docstring — is *not*
scheduled: payroll finalisation is an explicit, audited human action (``POST
/payroll/cycles/{id}/finalize``), and the payslip email it triggers is enqueued from
there. Nothing releases pay on a timer.

Set ``SCHEDULER_ENABLED=false`` to run a worker that drains the queue but registers no
cron jobs.
"""

from __future__ import annotations

from arq import cron
from arq.cron import CronJob

from app.core.config.settings import settings
from app.jobs.tasks import run_leave_accrual_all_orgs, sync_all_devices


def build_cron_jobs() -> list[CronJob]:
    """Return the cron jobs this worker should run (empty when the scheduler is off)."""
    if not settings.scheduler_enabled:
        return []

    device_sync_minutes = {
        minute
        for minute in range(60)
        if minute % settings.device_sync_interval_minutes == 0
    }

    return [
        cron(
            run_leave_accrual_all_orgs,
            hour=settings.leave_accrual_cron_hour,
            minute=settings.leave_accrual_cron_minute,
            run_at_startup=False,
            timeout=settings.job_timeout_seconds,
            max_tries=settings.job_max_tries,
        ),
        cron(
            sync_all_devices,
            minute=device_sync_minutes,
            run_at_startup=False,
            timeout=settings.job_timeout_seconds,
            max_tries=settings.job_max_tries,
        ),
    ]
