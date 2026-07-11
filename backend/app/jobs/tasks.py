"""Background job bodies (the *consumer* half of the queue).

Every coroutine here is an arq task: it takes the worker ``ctx`` as its first argument
and plain, serialisable values after it. Three rules hold for all of them.

**1. A job owns its session.** Each task opens a *fresh* ``AsyncSession`` from
``get_session_factory()`` and closes it. A job must never be handed the session of the
request that enqueued it: by the time the worker runs (a different process, possibly
minutes later), ``get_db`` has long since committed and closed it, and an
``AsyncSession`` is neither reusable after close nor concurrency-safe. This exact bug is
what the ``_spawn_export`` comment in the reports service warns about.

**2. A job is idempotent.** arq retries a failed job (``JOB_MAX_TRIES``), and a worker
that dies mid-run leaves the job to be re-run, so every task must tolerate being
executed twice:

* ``send_payslip_email`` — no DB mutation beyond its audit row. Delivery is
  at-least-once: a crash between "SMTP accepted the message" and "audit committed"
  re-sends on retry. Duplicating a payslip email is strictly better than dropping one.
* ``run_leave_accrual`` — guarded by the allocation event row
  (``employee + leave_type + cycle_year + cycle_period``); the second run credits
  nothing. See ``LeaveService.allocate_leave``.
* ``sync_device`` — writes ``last_sync_at = now``, which is naturally idempotent.
* ``generate_report_export`` — keyed by the caller's ``job_id``; a re-run recomputes and
  overwrites the same cache entries with the same content.

**3. A job that mutates, audits.** Mutating tasks write an ``activity_logs`` row through
``AuditService`` on success and on failure. ``generate_report_export`` is the exception
and writes none: it only reads and renders, so there is no business mutation to record.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.database.session import get_session_factory
from app.core.logging import get_logger
from app.infrastructure.email.client import EmailAttachment, get_email_client
from app.modules.audit.constants import ActionType
from app.modules.audit.service import AuditService
from app.modules.employee.models.organization import Organization
from app.modules.hardware.models import BiometricDevice
from app.modules.hardware.service import BiometricDeviceService
from app.modules.leave.service import LeaveService
from app.modules.payroll.schemas import PayslipResponseSchema
from app.modules.payroll.service import PayrollService
from app.modules.reports.service import ReportsService

_logger = get_logger("jobs.tasks")

#: ``performed_by_name`` for audit rows written by a job with no human actor.
_SYSTEM_ACTOR = "System (scheduled job)"


def _session_factory(ctx: dict[str, Any]) -> async_sessionmaker[AsyncSession]:
    """Return the session factory for a job run.

    The worker puts the factory in ``ctx`` on startup (see :mod:`app.jobs.worker`); the
    fallback keeps a task runnable outside a worker (tests, a REPL). Either way the task
    *makes its own session* from a factory — it is never given one.
    """
    factory = ctx.get("session_factory")
    if factory is None:
        factory = get_session_factory()
    return factory


async def _audit(
    session: AsyncSession,
    *,
    org_id: int,
    module: str,
    sub_module: str,
    action_type: ActionType,
    title: str,
    description: str,
    actor_id: int | None = None,
    employee_id: int | None = None,
) -> None:
    """Write one audit row for a job and commit it."""
    await AuditService(session).record(
        org_id=org_id,
        module=module,
        sub_module=sub_module,
        action_type=action_type,
        title=title,
        description=description,
        performed_by_user_id=actor_id,
        performed_by_name=_SYSTEM_ACTOR if actor_id is None else f"User {actor_id}",
        employee_id=employee_id,
    )
    await session.commit()


# ===========================================================================
# 1. Payslip email
# ===========================================================================


def render_payslip_email(payslip: PayslipResponseSchema) -> tuple[str, str, str]:
    """Render a payslip into ``(subject, text_body, html_body)``."""
    name = payslip.employee_name or f"Employee {payslip.employee_id}"
    period = f"{payslip.cycle_from.isoformat()} to {payslip.cycle_to.isoformat()}"
    subject = f"Payslip for {period}"

    def _lines(items: list[Any]) -> list[tuple[str, str]]:
        return [(item.label, f"{item.value}") for item in items]

    earnings = _lines(payslip.earnings)
    deductions = _lines(payslip.deductions)

    text = "\n".join(
        [
            f"Hello {name},",
            "",
            f"Your payslip for {period} is ready.",
            "",
            "Earnings:",
            *[f"  {label}: {value}" for label, value in earnings],
            "",
            "Deductions:",
            *[f"  {label}: {value}" for label, value in deductions],
            "",
            f"Net pay: {payslip.net_pay}",
            f"Payment method: {payslip.payment_method or 'N/A'}",
            "",
            "This is an automated message; please do not reply.",
        ]
    )

    def _rows(items: list[tuple[str, str]]) -> str:
        return "".join(
            f"<tr><td>{label}</td><td align='right'>{value}</td></tr>" for label, value in items
        )

    html = (
        f"<p>Hello {name},</p>"
        f"<p>Your payslip for <strong>{period}</strong> is ready.</p>"
        f"<h4>Earnings</h4><table>{_rows(earnings)}</table>"
        f"<h4>Deductions</h4><table>{_rows(deductions)}</table>"
        f"<p><strong>Net pay: {payslip.net_pay}</strong></p>"
        "<p style='color:#888'>This is an automated message; please do not reply.</p>"
    )
    return subject, text, html


async def send_payslip_email(
    ctx: dict[str, Any],
    org_id: int,
    row_id: int,
    actor_id: int | None = None,
) -> dict[str, Any]:
    """Render the payslip for a computed payroll row and email it to the employee.

    No-ops cleanly (``{"sent": False}``) when SMTP is unconfigured or the employee has no
    email address — neither is a failure the worker should retry. A *configured* SMTP
    server that refuses the message raises, so arq retries the job.
    """
    async with _session_factory(ctx)() as session:
        service = PayrollService(session)
        payslip = await service.view_payslip(org_id=org_id, row_id=row_id)
        employee = await service.employees.get_by_id(payslip.employee_id)
        recipient = (employee.email or "").strip() if employee else ""

        client = get_email_client()
        if not client.is_configured or not recipient:
            reason = "smtp_not_configured" if not client.is_configured else "no_recipient"
            _logger.warning(
                "payslip_email_skipped", org_id=org_id, row_id=row_id, reason=reason
            )
            return {"sent": False, "reason": reason, "row_id": row_id}

        subject, text_body, html_body = render_payslip_email(payslip)
        attachments: list[EmailAttachment] = []
        if payslip.is_finalized:
            pdf = await service.download_payslip_pdf(org_id=org_id, row_id=row_id)
            attachments.append(
                EmailAttachment(filename=f"payslip_{row_id}.pdf", content=pdf)
            )

        try:
            sent = await client.send(
                to=recipient,
                subject=subject,
                text_body=text_body,
                html_body=html_body,
                attachments=attachments,
            )
        except Exception as exc:
            await _audit(
                session,
                org_id=org_id,
                module="payroll",
                sub_module="payslip",
                action_type=ActionType.UPDATE,
                title="Email Payslip Failed",
                description=(
                    f"Failed to email payslip for row {row_id} to {recipient}: {exc}"
                ),
                actor_id=actor_id,
                employee_id=payslip.employee_id,
            )
            raise

        await _audit(
            session,
            org_id=org_id,
            module="payroll",
            sub_module="payslip",
            action_type=ActionType.UPDATE,
            title="Email Payslip",
            description=f"Emailed payslip for row {row_id} to {recipient}",
            actor_id=actor_id,
            employee_id=payslip.employee_id,
        )
        return {"sent": sent, "row_id": row_id, "employee_id": payslip.employee_id}


# ===========================================================================
# 2. Leave accrual
# ===========================================================================


async def run_leave_accrual(
    ctx: dict[str, Any],
    org_id: int,
    as_of: date | None = None,
) -> dict[str, Any]:
    """Credit the configured auto-allocation to every active employee of ``org_id``.

    Idempotent: ``LeaveService.run_auto_allocation`` skips any employee/leave-type that
    already has an allocation event for the cycle, so a re-run (or an arq retry after a
    partial failure) credits only what is missing and never double-credits.
    """
    async with _session_factory(ctx)() as session:
        service = LeaveService(session)
        try:
            result = await service.run_auto_allocation(org_id, as_of=as_of)
        except Exception as exc:
            await _audit(
                session,
                org_id=org_id,
                module="leave",
                sub_module="leave_allocation",
                action_type=ActionType.INSERT,
                title="Leave Accrual Failed",
                description=f"Auto-allocation run failed for org {org_id}: {exc}",
            )
            raise

        _logger.info("leave_accrual_completed", **result)
        # Per-employee allocations are audited inside ``allocate_leave``; the run-level
        # summary row makes the scheduled execution itself visible in the trail.
        await _audit(
            session,
            org_id=org_id,
            module="leave",
            sub_module="leave_allocation",
            action_type=ActionType.INSERT,
            title="Leave Accrual Run",
            description=(
                f"Auto-allocation for cycle {result['cycle_year']}: "
                f"{result['allocated']} allocated, {result['skipped']} already allocated "
                f"({result['employees']} employees x {result['leave_types']} leave types)"
            ),
        )
        return result


async def run_leave_accrual_all_orgs(ctx: dict[str, Any]) -> dict[str, Any]:
    """Cron entrypoint: run the leave accrual for every active organization."""
    async with _session_factory(ctx)() as session:
        stmt = select(Organization.org_id).where(
            Organization.is_deleted.is_(False),
            Organization.is_active.is_(True),
        )
        org_ids = list((await session.execute(stmt)).scalars().all())

    allocated = 0
    failed: list[int] = []
    for org_id in org_ids:
        try:
            result = await run_leave_accrual(ctx, org_id)
        except Exception as exc:  # noqa: BLE001 - one bad org must not stop the rest
            _logger.error("leave_accrual_org_failed", org_id=org_id, error=str(exc))
            failed.append(org_id)
            continue
        allocated += int(result["allocated"])

    return {"orgs": len(org_ids), "allocated": allocated, "failed": failed}


# ===========================================================================
# 3. Device sync
# ===========================================================================


async def sync_device(ctx: dict[str, Any], org_id: int, device_id: int) -> dict[str, Any]:
    """Sync one biometric device (delegates to ``BiometricDeviceService.sync_device``).

    Idempotent: the sync stamps ``last_sync_at`` with the current time, so re-running it
    converges on the same state.
    """
    async with _session_factory(ctx)() as session:
        service = BiometricDeviceService(session)
        try:
            await service.sync_device(org_id=org_id, device_id=device_id)
        except Exception as exc:
            await _audit(
                session,
                org_id=org_id,
                module="hardware",
                sub_module="biometric_device",
                action_type=ActionType.UPDATE,
                title="Device Sync Failed",
                description=f"Sync failed for device {device_id}: {exc}",
            )
            raise

        await _audit(
            session,
            org_id=org_id,
            module="hardware",
            sub_module="biometric_device",
            action_type=ActionType.UPDATE,
            title="Device Sync",
            description=f"Synced biometric device {device_id}",
        )
        return {"org_id": org_id, "device_id": device_id, "synced": True}


async def sync_all_devices(ctx: dict[str, Any]) -> dict[str, Any]:
    """Cron entrypoint: sync every active biometric device across all organizations."""
    async with _session_factory(ctx)() as session:
        # ``biometric_devices`` has no soft-delete column — deregistering a device removes
        # the row — so ``is_active`` is the only liveness flag to filter on here.
        stmt = select(BiometricDevice.org_id, BiometricDevice.id).where(
            BiometricDevice.is_active.is_(True)
        )
        devices = [(row[0], row[1]) for row in (await session.execute(stmt)).all()]

    synced = 0
    failed: list[int] = []
    for org_id, device_id in devices:
        try:
            await sync_device(ctx, org_id, device_id)
        except Exception as exc:  # noqa: BLE001 - an unreachable device must not stop the sweep
            _logger.error(
                "device_sync_failed", org_id=org_id, device_id=device_id, error=str(exc)
            )
            failed.append(device_id)
            continue
        synced += 1

    return {"devices": len(devices), "synced": synced, "failed": failed}


# ===========================================================================
# 4. Report export
# ===========================================================================


async def generate_report_export(
    ctx: dict[str, Any],
    org_id: int,
    job_id: str,
    report_name: str,
    repo_method: str,
    repo_kwargs: dict[str, Any],
    format_type: str,
) -> dict[str, Any]:
    """Run a large report export and publish the file to the cache under ``job_id``.

    The durable replacement for the reports service's in-process ``asyncio.create_task``:
    same rendering logic (``ReportsService._run_async_export``), but it survives an API
    restart and is retried on failure. Read-only, so it writes no audit row.
    """
    async with _session_factory(ctx)() as session:
        await ReportsService(session).run_export_job(
            job_id=job_id,
            org_id=org_id,
            report_name=report_name,
            repo_method=repo_method,
            repo_kwargs=repo_kwargs,
            format_type=format_type,
        )
        return {"export_job_id": job_id, "org_id": org_id}
