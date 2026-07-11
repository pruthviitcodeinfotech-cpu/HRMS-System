"""Unit tests for the background job system (queue, tasks, scheduler, worker).

No live Redis and no database: the arq pool is faked (the autouse ``fake_redis`` fixture
in ``conftest`` already keeps the cache off a real server), sessions come from a fake
factory that records every session it hands out, and the module services are stubbed.

The tests pin the four properties that make the job system trustworthy:

* every job opens its **own** session and never touches a request-scoped one;
* ``run_leave_accrual`` is **idempotent** — a second run credits nothing;
* ``send_payslip_email`` **no-ops** (rather than crashing) when SMTP is unconfigured;
* a failed enqueue on a report export **falls back in-process** instead of losing it;
* the worker registry is **complete** — a job cannot be shipped unregistered.
"""

from __future__ import annotations

import inspect
from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.config.settings import Settings
from app.infrastructure.email.client import SmtpEmailClient
from app.jobs import queue as queue_module
from app.jobs import tasks as tasks_module
from app.jobs import worker as worker_module
from app.jobs.queue import JobName, QueueUnavailableException, enqueue
from app.jobs.tasks import (
    generate_report_export,
    run_leave_accrual,
    send_payslip_email,
    sync_device,
)
from app.modules.reports.service import ReportsService

# ===========================================================================
# Fakes
# ===========================================================================


class FakeSession:
    """Stand-in ``AsyncSession``: an async context manager that records its lifecycle."""

    def __init__(self, index: int) -> None:
        self.index = index
        self.closed = False
        self.commits = 0

    async def __aenter__(self) -> FakeSession:
        return self

    async def __aexit__(self, *_exc: object) -> None:
        self.closed = True

    async def commit(self) -> None:
        self.commits += 1

    async def rollback(self) -> None:  # pragma: no cover - defensive
        return None

    async def close(self) -> None:  # pragma: no cover - defensive
        self.closed = True


class FakeSessionFactory:
    """``async_sessionmaker`` stand-in that hands out a fresh :class:`FakeSession`."""

    def __init__(self) -> None:
        self.sessions: list[FakeSession] = []

    def __call__(self) -> FakeSession:
        session = FakeSession(len(self.sessions))
        self.sessions.append(session)
        return session


#: A session that belongs to an HTTP request. No job may ever use it — it is closed by
#: ``get_db`` the moment the handler returns.
REQUEST_SESSION = FakeSession(index=-1)


@pytest.fixture
def factory() -> FakeSessionFactory:
    """A fake session factory, passed to jobs through the worker ``ctx``."""
    return FakeSessionFactory()


@pytest.fixture
def ctx(factory: FakeSessionFactory) -> dict[str, Any]:
    """The arq job context the worker builds on startup."""
    return {"session_factory": factory}


@pytest.fixture(autouse=True)
def no_audit(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    """Stub ``AuditService`` inside the tasks module (audit writes need a real session)."""
    audit_cls = MagicMock()
    audit_cls.return_value = AsyncMock()
    monkeypatch.setattr(tasks_module, "AuditService", audit_cls)
    return audit_cls


@pytest.fixture(autouse=True)
def reset_queue_pool(monkeypatch: pytest.MonkeyPatch) -> None:
    """Never let a test reuse (or create) a real arq pool."""
    monkeypatch.setattr(queue_module, "_pool", None, raising=False)


def make_payslip(*, is_finalized: bool = False) -> SimpleNamespace:
    """A stand-in :class:`PayslipResponseSchema`."""
    return SimpleNamespace(
        row_id=7,
        employee_id=42,
        employee_name="Asha Rao",
        employee_code="E-042",
        cycle_from=date(2026, 6, 1),
        cycle_to=date(2026, 6, 30),
        earnings=[SimpleNamespace(key="gross", label="Gross Wages", value=Decimal("50000"))],
        deductions=[SimpleNamespace(key="loans", label="Loan", value=Decimal("2000"))],
        net_pay=Decimal("48000"),
        payment_method="bank_transfer",
        is_finalized=is_finalized,
    )


def unconfigured_email_client() -> SmtpEmailClient:
    """An email client with no ``SMTP_HOST`` (the default in dev/CI)."""
    return SmtpEmailClient(Settings(smtp_host=""))


# ===========================================================================
# 1. Every job opens its own session
# ===========================================================================


@pytest.mark.asyncio
async def test_send_payslip_email_opens_its_own_session(
    ctx: dict[str, Any], factory: FakeSessionFactory, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The job builds ``PayrollService`` on a session it created, not a request session."""
    seen: list[object] = []

    def _payroll_service(session: object) -> AsyncMock:
        seen.append(session)
        service = AsyncMock()
        service.view_payslip.return_value = make_payslip()
        service.employees.get_by_id.return_value = SimpleNamespace(email="asha@example.com")
        return service

    monkeypatch.setattr(tasks_module, "PayrollService", _payroll_service)
    monkeypatch.setattr(tasks_module, "get_email_client", unconfigured_email_client)

    await send_payslip_email(ctx, org_id=1, row_id=7, actor_id=3)

    assert len(factory.sessions) == 1, "the job must open exactly one session of its own"
    assert seen == [factory.sessions[0]]
    assert seen[0] is not REQUEST_SESSION
    assert factory.sessions[0].closed is True, "the job must close the session it opened"


@pytest.mark.asyncio
async def test_sync_device_opens_its_own_session(
    ctx: dict[str, Any], factory: FakeSessionFactory, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``sync_device`` builds the hardware service on its own session."""
    seen: list[object] = []

    def _device_service(session: object) -> AsyncMock:
        seen.append(session)
        return AsyncMock()

    monkeypatch.setattr(tasks_module, "BiometricDeviceService", _device_service)

    result = await sync_device(ctx, org_id=1, device_id=9)

    assert result == {"org_id": 1, "device_id": 9, "synced": True}
    assert seen == [factory.sessions[0]]
    assert seen[0] is not REQUEST_SESSION


@pytest.mark.asyncio
async def test_generate_report_export_opens_its_own_session(
    ctx: dict[str, Any], factory: FakeSessionFactory, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The export job runs on a worker-owned session (the bug ``_spawn_export`` warns of)."""
    seen: list[object] = []

    def _reports_service(session: object) -> AsyncMock:
        seen.append(session)
        return AsyncMock()

    monkeypatch.setattr(tasks_module, "ReportsService", _reports_service)

    result = await generate_report_export(
        ctx,
        org_id=1,
        job_id="abc123",
        report_name="employee_master",
        repo_method="get_employee_master",
        repo_kwargs={"page": 1, "page_size": 2000},
        format_type="csv",
    )

    assert result == {"export_job_id": "abc123", "org_id": 1}
    assert seen == [factory.sessions[0]]
    assert seen[0] is not REQUEST_SESSION


@pytest.mark.parametrize(
    "job",
    [send_payslip_email, run_leave_accrual, sync_device, generate_report_export],
)
def test_no_job_accepts_a_session_argument(job: Any) -> None:
    """A job can never be *handed* a session — it only ever makes its own.

    A ``session``/``db`` parameter would let a caller pass the request-scoped session
    into the queue, which is exactly the failure this design rules out.
    """
    params = set(inspect.signature(job).parameters)
    assert not params & {"session", "db", "async_session"}
    assert next(iter(inspect.signature(job).parameters)) == "ctx"


@pytest.mark.asyncio
async def test_job_falls_back_to_the_global_session_factory(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """With no factory on ``ctx`` (e.g. a manual run), the job still opens its own session."""
    factory = FakeSessionFactory()
    monkeypatch.setattr(tasks_module, "get_session_factory", lambda: factory)
    monkeypatch.setattr(tasks_module, "BiometricDeviceService", lambda session: AsyncMock())

    await sync_device({}, org_id=1, device_id=2)

    assert len(factory.sessions) == 1


# ===========================================================================
# 2. Leave accrual is idempotent
# ===========================================================================


def make_leave_service(*, allocation_days: Decimal = Decimal("12.00")) -> AsyncMock:
    """A real-ish ``LeaveService`` whose repositories are backed by in-memory dicts."""
    from app.modules.leave.service import LeaveService

    service = LeaveService(AsyncMock())
    leave_type = SimpleNamespace(
        id=5,
        auto_allocation_count=allocation_days,
        allocation_frequency="yearly",
    )
    balance = SimpleNamespace(
        allocated=Decimal("0.00"),
        closing_balance=Decimal("0.00"),
    )
    allocations: dict[tuple[int, int, int, str | None], object] = {}

    async def _get_for_cycle(
        employee_id: int, leave_type_id: int, cycle_year: int, *, cycle_period: str | None = None
    ) -> object | None:
        return allocations.get((employee_id, leave_type_id, cycle_year, cycle_period))

    async def _create_allocation(data: dict[str, Any]) -> object:
        key = (
            data["employee_id"],
            data["leave_type_id"],
            data["cycle_year"],
            data["cycle_period"],
        )
        allocations[key] = SimpleNamespace(**data)
        return allocations[key]

    async def _update_balance(instance: Any, data: dict[str, Any]) -> Any:
        for field, value in data.items():
            setattr(instance, field, value)
        return instance

    service.allocations = AsyncMock()
    service.allocations.get_for_cycle = AsyncMock(side_effect=_get_for_cycle)
    service.allocations.create = AsyncMock(side_effect=_create_allocation)
    service.balances = AsyncMock()
    service.balances.get_by_employee_type_year = AsyncMock(return_value=balance)
    service.balances.update = AsyncMock(side_effect=_update_balance)
    service.leave_types = AsyncMock()
    service.leave_types.search = AsyncMock(return_value=[leave_type])
    service.settings = AsyncMock()
    service.settings.get_by_org_id = AsyncMock(
        return_value=SimpleNamespace(leave_cycle="calendar_year", cycle_start_month=1)
    )
    service.audit = AsyncMock()
    service._list_active_employee_ids = AsyncMock(return_value=[42])  # noqa: SLF001

    service.test_balance = balance  # type: ignore[attr-defined]
    service.test_allocations = allocations  # type: ignore[attr-defined]
    return service


@pytest.mark.asyncio
async def test_run_leave_accrual_is_idempotent(
    ctx: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Running the accrual twice credits the employee exactly once."""
    service = make_leave_service()
    monkeypatch.setattr(tasks_module, "LeaveService", lambda session: service)

    first = await run_leave_accrual(ctx, org_id=1, as_of=date(2026, 7, 11))
    second = await run_leave_accrual(ctx, org_id=1, as_of=date(2026, 7, 11))

    assert first["allocated"] == 1
    assert first["skipped"] == 0
    assert second["allocated"] == 0, "a second run must not allocate again"
    assert second["skipped"] == 1

    assert service.balances.update.await_count == 1, "the balance must be credited once"
    assert service.allocations.create.await_count == 1
    assert service.test_balance.allocated == Decimal("12.00")
    assert service.test_balance.closing_balance == Decimal("12.00")
    assert len(service.test_allocations) == 1


@pytest.mark.asyncio
async def test_leave_accrual_records_an_allocation_event_per_cycle() -> None:
    """The allocation row carries the cycle + source that make the run auditable."""
    service = make_leave_service()

    await service.run_auto_allocation(1, as_of=date(2026, 7, 11))

    (allocation,) = service.test_allocations.values()
    assert allocation.cycle_year == 2026
    assert allocation.cycle_period is None  # yearly leave type
    assert allocation.allocation_source == "auto"
    assert allocation.allocated_days == Decimal("12.00")


@pytest.mark.asyncio
async def test_leave_accrual_skips_leave_types_with_no_auto_allocation() -> None:
    """A leave type configured with zero auto-allocation is never credited."""
    service = make_leave_service(allocation_days=Decimal("0.00"))

    result = await service.run_auto_allocation(1, as_of=date(2026, 7, 11))

    assert result["allocated"] == 0
    assert service.balances.update.await_count == 0


# ===========================================================================
# 3. Payslip email no-ops when SMTP is unconfigured
# ===========================================================================


@pytest.mark.asyncio
async def test_send_payslip_email_noops_when_smtp_unconfigured(
    ctx: dict[str, Any], monkeypatch: pytest.MonkeyPatch, no_audit: MagicMock
) -> None:
    """No SMTP host: the job returns cleanly instead of raising (and never retries)."""
    service = AsyncMock()
    service.view_payslip.return_value = make_payslip()
    service.employees.get_by_id.return_value = SimpleNamespace(email="asha@example.com")
    monkeypatch.setattr(tasks_module, "PayrollService", lambda session: service)
    monkeypatch.setattr(tasks_module, "get_email_client", unconfigured_email_client)

    result = await send_payslip_email(ctx, org_id=1, row_id=7, actor_id=3)

    assert result == {"sent": False, "reason": "smtp_not_configured", "row_id": 7}
    no_audit.assert_not_called()


@pytest.mark.asyncio
async def test_send_payslip_email_noops_when_employee_has_no_email(
    ctx: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    """An employee with no email address is a no-op, not a failure."""
    service = AsyncMock()
    service.view_payslip.return_value = make_payslip()
    service.employees.get_by_id.return_value = SimpleNamespace(email=None)
    monkeypatch.setattr(tasks_module, "PayrollService", lambda session: service)
    monkeypatch.setattr(
        tasks_module, "get_email_client", lambda: SmtpEmailClient(Settings(smtp_host="mail.local"))
    )

    result = await send_payslip_email(ctx, org_id=1, row_id=7)

    assert result["sent"] is False
    assert result["reason"] == "no_recipient"


@pytest.mark.asyncio
async def test_unconfigured_email_client_send_returns_false_without_smtp(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``SmtpEmailClient.send`` never opens a socket when there is no host configured."""
    import smtplib

    def _explode(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("SMTP must not be contacted when unconfigured")

    monkeypatch.setattr(smtplib, "SMTP", _explode)
    client = unconfigured_email_client()

    assert client.is_configured is False
    assert await client.send(to="a@b.c", subject="s", text_body="t") is False


@pytest.mark.asyncio
async def test_send_payslip_email_sends_and_audits_when_configured(
    ctx: dict[str, Any], monkeypatch: pytest.MonkeyPatch, no_audit: MagicMock
) -> None:
    """With SMTP configured the payslip is rendered, sent, and audited."""
    service = AsyncMock()
    service.view_payslip.return_value = make_payslip(is_finalized=True)
    service.employees.get_by_id.return_value = SimpleNamespace(email="asha@example.com")
    service.download_payslip_pdf.return_value = b"%PDF-1.4 payslip"
    monkeypatch.setattr(tasks_module, "PayrollService", lambda session: service)

    client = AsyncMock()
    client.is_configured = True
    client.send.return_value = True
    monkeypatch.setattr(tasks_module, "get_email_client", lambda: client)

    result = await send_payslip_email(ctx, org_id=1, row_id=7, actor_id=3)

    assert result == {"sent": True, "row_id": 7, "employee_id": 42}
    kwargs = client.send.await_args.kwargs
    assert kwargs["to"] == "asha@example.com"
    assert "Payslip" in kwargs["subject"]
    assert "48000" in kwargs["text_body"]
    assert kwargs["attachments"][0].filename == "payslip_7.pdf"
    no_audit.return_value.record.assert_awaited_once()


@pytest.mark.asyncio
async def test_send_payslip_email_audits_and_reraises_on_delivery_failure(
    ctx: dict[str, Any], monkeypatch: pytest.MonkeyPatch, no_audit: MagicMock
) -> None:
    """A configured-but-failing SMTP server fails the job (so arq retries it)."""
    from app.infrastructure.email.client import EmailDeliveryException

    service = AsyncMock()
    service.view_payslip.return_value = make_payslip()
    service.employees.get_by_id.return_value = SimpleNamespace(email="asha@example.com")
    monkeypatch.setattr(tasks_module, "PayrollService", lambda session: service)

    client = AsyncMock()
    client.is_configured = True
    client.send.side_effect = EmailDeliveryException()
    monkeypatch.setattr(tasks_module, "get_email_client", lambda: client)

    with pytest.raises(EmailDeliveryException):
        await send_payslip_email(ctx, org_id=1, row_id=7)

    no_audit.return_value.record.assert_awaited_once()
    assert "Failed" in no_audit.return_value.record.await_args.kwargs["title"]


# ===========================================================================
# 4. Enqueue: Redis-down policy, and the reports export fallback
# ===========================================================================


@pytest.mark.asyncio
async def test_enqueue_returns_the_job_id(monkeypatch: pytest.MonkeyPatch) -> None:
    """The happy path hands the job to arq and returns its id."""
    pool = AsyncMock()
    pool.enqueue_job.return_value = SimpleNamespace(job_id="job-1")
    monkeypatch.setattr(queue_module, "create_pool", AsyncMock(return_value=pool))

    job_id = await enqueue(JobName.SYNC_DEVICE, org_id=1, device_id=2)

    assert job_id == "job-1"
    pool.enqueue_job.assert_awaited_once_with("sync_device", org_id=1, device_id=2)


@pytest.mark.asyncio
async def test_enqueue_raises_app_exception_when_redis_is_down(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Redis down: a clear 503 AppException, never a bare ConnectionError, never a lie."""
    from redis.exceptions import ConnectionError as RedisConnectionError

    monkeypatch.setattr(
        queue_module, "create_pool", AsyncMock(side_effect=RedisConnectionError("down"))
    )

    with pytest.raises(QueueUnavailableException) as exc_info:
        await enqueue(JobName.SEND_PAYSLIP_EMAIL, org_id=1, row_id=7)

    assert exc_info.value.status_code == 503
    assert exc_info.value.code == "QUEUE_UNAVAILABLE"


@pytest.mark.asyncio
async def test_enqueue_raises_when_arq_drops_the_job(monkeypatch: pytest.MonkeyPatch) -> None:
    """A dropped enqueue (arq returns None) is a failure, not a silent success."""
    pool = AsyncMock()
    pool.enqueue_job.return_value = None
    monkeypatch.setattr(queue_module, "create_pool", AsyncMock(return_value=pool))

    with pytest.raises(QueueUnavailableException):
        await enqueue(JobName.RUN_LEAVE_ACCRUAL, org_id=1)


@pytest.mark.asyncio
async def test_report_export_is_enqueued(monkeypatch: pytest.MonkeyPatch) -> None:
    """A large export goes to the durable queue, not to an in-process task."""
    service = ReportsService(AsyncMock())
    enqueue_mock = AsyncMock(return_value="job-9")
    spawn = MagicMock()
    monkeypatch.setattr("app.modules.reports.service.enqueue", enqueue_mock)
    monkeypatch.setattr(service, "_spawn_export", spawn)

    path = await service._dispatch_export(  # noqa: SLF001
        job_id="exp-1",
        org_id=1,
        report_name="employee_master",
        repo_method="get_employee_master",
        repo_kwargs={"page": 1, "page_size": 2000},
        format_type="csv",
    )

    assert path == "queued"
    spawn.assert_not_called()
    assert enqueue_mock.await_args.args[0] is JobName.GENERATE_REPORT_EXPORT
    assert enqueue_mock.await_args.kwargs["job_id"] == "exp-1"


@pytest.mark.asyncio
async def test_report_export_falls_back_in_process_when_enqueue_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A queue outage must degrade the export, not lose it."""
    service = ReportsService(AsyncMock())
    spawn = MagicMock()
    monkeypatch.setattr(
        "app.modules.reports.service.enqueue",
        AsyncMock(side_effect=QueueUnavailableException()),
    )
    monkeypatch.setattr(service, "_spawn_export", spawn)

    path = await service._dispatch_export(  # noqa: SLF001
        job_id="exp-2",
        org_id=1,
        report_name="employee_master",
        repo_method="get_employee_master",
        repo_kwargs={"page": 1, "page_size": 2000},
        format_type="csv",
    )

    assert path == "in_process", "the export must still run when the queue is down"
    spawn.assert_called_once()
    assert spawn.call_args.kwargs["job_id"] == "exp-2"
    assert spawn.call_args.kwargs["repo_method"] == "get_employee_master"


@pytest.mark.asyncio
async def test_email_payslip_endpoint_actually_enqueues(monkeypatch: pytest.MonkeyPatch) -> None:
    """The endpoint's ``{"queued": true}`` is now backed by a real enqueue."""
    from app.modules.payroll import router as payroll_router

    enqueue_mock = AsyncMock(return_value="job-77")
    monkeypatch.setattr(payroll_router, "enqueue", enqueue_mock)

    service = AsyncMock()
    service.view_payslip.return_value = make_payslip()

    response = await payroll_router.email_payslip(
        row_id=7,
        service=service,
        current_user=SimpleNamespace(user_id=3),
        org_id=1,
    )

    enqueue_mock.assert_awaited_once_with(
        JobName.SEND_PAYSLIP_EMAIL, org_id=1, row_id=7, actor_id=3
    )
    assert response["data"]["queued"] is True
    assert response["data"]["job_id"] == "job-77"


# ===========================================================================
# 5. Worker registry completeness
# ===========================================================================


def _task_coroutines() -> dict[str, Any]:
    """Every job-shaped coroutine in ``app.jobs.tasks`` (public, async, takes ``ctx``)."""
    found: dict[str, Any] = {}
    for name, obj in vars(tasks_module).items():
        if name.startswith("_") or not inspect.iscoroutinefunction(obj):
            continue
        if obj.__module__ != tasks_module.__name__:
            continue
        params = list(inspect.signature(obj).parameters)
        if params and params[0] == "ctx":
            found[name] = obj
    return found


def test_worker_registers_every_task() -> None:
    """A job defined in ``tasks`` but missing from ``WorkerSettings.functions`` is a bug.

    Without this guard a new job enqueues fine and then fails in the worker with
    "function not found" — at runtime, in production, silently until someone reads the
    dead-letter log.
    """
    registered = {f.__name__ for f in worker_module.WorkerSettings.functions}
    defined = set(_task_coroutines())

    assert defined == registered, (
        "app.jobs.tasks and WorkerSettings.functions disagree: "
        f"unregistered={sorted(defined - registered)}, unknown={sorted(registered - defined)}"
    )


def test_every_job_name_is_registered_on_the_worker() -> None:
    """Every enqueueable :class:`JobName` maps to a function the worker can run."""
    registered = {f.__name__ for f in worker_module.WorkerSettings.functions}

    for job_name in JobName:
        assert job_name.value in registered, f"{job_name} is not registered on the worker"
        assert hasattr(tasks_module, job_name.value)


def test_worker_registers_the_cron_jobs() -> None:
    """The scheduled work (nightly accrual, periodic device sync) is registered."""
    cron_names = {job.name for job in worker_module.WorkerSettings.cron_jobs}

    assert cron_names == {"cron:run_leave_accrual_all_orgs", "cron:sync_all_devices"}


def test_worker_settings_are_driven_by_config() -> None:
    """Concurrency, retries, and result TTL come from settings, not from arq defaults."""
    from app.core.config.settings import settings

    assert worker_module.WorkerSettings.max_jobs == settings.worker_concurrency
    assert worker_module.WorkerSettings.max_tries == settings.job_max_tries
    assert worker_module.WorkerSettings.job_timeout == settings.job_timeout_seconds
    assert worker_module.WorkerSettings.keep_result == settings.job_result_ttl_seconds
    assert worker_module.WorkerSettings.redis_settings.port == 6379


def test_scheduler_can_be_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    """``SCHEDULER_ENABLED=false`` yields a worker that drains the queue but runs no cron."""
    from app.core.config.settings import settings as app_settings
    from app.jobs.scheduler import build_cron_jobs

    monkeypatch.setattr(app_settings, "scheduler_enabled", False)

    assert build_cron_jobs() == []


def test_device_sync_cron_honours_the_configured_interval(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The device-sync cadence follows ``DEVICE_SYNC_INTERVAL_MINUTES``."""
    from app.core.config.settings import settings as app_settings
    from app.jobs.scheduler import build_cron_jobs

    monkeypatch.setattr(app_settings, "scheduler_enabled", True)
    monkeypatch.setattr(app_settings, "device_sync_interval_minutes", 30)

    device_sync = next(
        job for job in build_cron_jobs() if job.name == "cron:sync_all_devices"
    )
    assert device_sync.minute == {0, 30}


@pytest.mark.asyncio
async def test_worker_startup_publishes_the_session_factory(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The worker hands jobs a session *factory* on ``ctx`` — never a live session."""
    factory = FakeSessionFactory()
    monkeypatch.setattr(worker_module, "get_session_factory", lambda: factory)
    worker_ctx: dict[str, Any] = {}

    await worker_module.startup(worker_ctx)

    assert worker_ctx["session_factory"] is factory
    assert not any(isinstance(value, FakeSession) for value in worker_ctx.values())
