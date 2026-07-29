"""Unit tests for Enterprise System Administration Module."""

from __future__ import annotations

import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.modules.system.service import SystemService

_ORG_ID = 10
_USER_ID = 42
_NOW = datetime.datetime(2026, 7, 29, 10, 0, 0, tzinfo=datetime.timezone.utc)


def _make_service() -> SystemService:
    session = AsyncMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    svc = SystemService(session)
    svc.audit = AsyncMock()
    return svc


@pytest.mark.asyncio
async def test_get_system_health() -> None:
    """GET /system/health returns infrastructure component health statuses."""
    svc = _make_service()

    mock_scalars = MagicMock()
    mock_scalars.scalar.return_value = 1
    mock_scalars.scalar_one.return_value = 0
    svc.session.execute = AsyncMock(return_value=mock_scalars)

    res = await svc.get_system_health()

    assert res.status in ("ok", "degraded", "down")
    assert res.api.status == "ok"
    assert res.database.status == "ok"
    assert res.failed_jobs_count == 0


@pytest.mark.asyncio
async def test_get_audit_summary() -> None:
    """GET /system/audit/summary aggregates 24-hour audit and login stats."""
    svc = _make_service()

    mock_scalars = MagicMock()
    mock_scalars.scalar_one.side_effect = [150, 25, 5]
    svc.session.execute = AsyncMock(return_value=mock_scalars)

    res = await svc.get_audit_summary(org_id=_ORG_ID)

    assert res.total_activities == 150
    assert res.total_logins_24h == 25
    assert res.security_events_count == 5


@pytest.mark.asyncio
async def test_retry_failed_job() -> None:
    """POST /system/jobs/{job_id}/retry re-queues failed background job."""
    svc = _make_service()

    mock_job = SimpleNamespace(
        id=1,
        job_id="job-uuid-101",
        job_name="payroll_nightly_job",
        status="failed",
        error_message="Timeout",
        retry_count=1,
        created_at=_NOW,
        updated_at=_NOW,
    )

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_job
    svc.session.execute = AsyncMock(return_value=mock_result)

    res = await svc.retry_failed_job(job_id="job-uuid-101", actor_id=_USER_ID, org_id=_ORG_ID)

    assert res.job_id == "job-uuid-101"
    assert res.status == "queued"
    assert res.retry_count == 2
    svc.audit.record.assert_called_once()
