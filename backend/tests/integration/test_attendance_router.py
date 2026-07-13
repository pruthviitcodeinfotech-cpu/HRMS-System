"""Integration tests for the Attendance Lock / Unlock endpoints.

Exercises the HTTP layer, authentication, routing, and response schemas,
stubbing the dependency on AttendanceService.
"""

from __future__ import annotations

import datetime
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.core.dependencies.auth import assert_session_live
from app.main import create_app
from app.modules.attendance.router import get_attendance_service
from app.modules.attendance.router import router as attendance_router
from app.modules.attendance.schemas import AttendanceLockSchema
from tests.conftest import API_PREFIX

_NOW = datetime.datetime(2026, 7, 10, 10, 0, 0, tzinfo=datetime.UTC)


@pytest.fixture
def mock_attendance_service() -> AsyncMock:
    """An ``AsyncMock`` standing in for :class:`AttendanceService`."""
    return AsyncMock()


@pytest.fixture
def attendance_app():
    """The production app factory with the attendance router mounted."""
    application = create_app()
    application.include_router(attendance_router, prefix=API_PREFIX)
    return application


@pytest_asyncio.fixture
async def attendance_client(attendance_app, mock_attendance_service: AsyncMock):
    """An async HTTP client bound to the app, with ``AttendanceService`` mocked."""
    attendance_app.dependency_overrides[assert_session_live] = lambda: None
    attendance_app.dependency_overrides[get_attendance_service] = lambda: mock_attendance_service

    transport = ASGITransport(app=attendance_app)
    async with AsyncClient(transport=transport, base_url="http://test") as http_client:
        yield http_client
    attendance_app.dependency_overrides.clear()


# ===========================================================================
# HTTP Endpoint Verification
# ===========================================================================


async def test_lock_attendance_endpoint(
    attendance_client: AsyncClient, mock_attendance_service: AsyncMock, super_admin_headers
) -> None:
    mock_attendance_service.lock_attendance.return_value = True

    resp = await attendance_client.post(
        f"{API_PREFIX}/attendance/lock",
        json={
            "period_start": "2026-02-01",
            "period_end": "2026-02-28",
            "scope": "company",
            "branch_id": None,
            "reason": "Monthly closing",
        },
        headers=super_admin_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["data"] is True
    mock_attendance_service.lock_attendance.assert_awaited_once()


async def test_unlock_attendance_endpoint(
    attendance_client: AsyncClient, mock_attendance_service: AsyncMock, super_admin_headers
) -> None:
    mock_attendance_service.unlock_attendance.return_value = True

    resp = await attendance_client.post(
        f"{API_PREFIX}/attendance/unlock",
        json={
            "period_start": "2026-02-01",
            "period_end": "2026-02-28",
            "scope": "company",
            "branch_id": None,
            "reason": "Monthly unlocking",
        },
        headers=super_admin_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["data"] is True
    mock_attendance_service.unlock_attendance.assert_awaited_once()


async def test_list_attendance_locks_endpoint(
    attendance_client: AsyncClient, mock_attendance_service: AsyncMock, super_admin_headers
) -> None:
    lock_schema = AttendanceLockSchema(
        id=1,
        org_id=1,
        lock_month=2,
        lock_year=2026,
        lock_type="company",
        branch_id=None,
        status="locked",
        locked_by=99,
        locked_at=_NOW,
        reason="Monthly closing",
        created_at=_NOW,
        updated_at=_NOW,
    )
    mock_attendance_service.get_locked_periods.return_value = [lock_schema]

    resp = await attendance_client.get(
        f"{API_PREFIX}/attendance/locks",
        headers=super_admin_headers,
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert len(data) == 1
    assert data[0]["lock_month"] == 2
    assert data[0]["status"] == "locked"
    mock_attendance_service.get_locked_periods.assert_awaited_once()
