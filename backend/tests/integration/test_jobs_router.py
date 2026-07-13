"""Integration tests for the Jobs Management router."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.core.dependencies.auth import assert_session_live
from tests.conftest import API_PREFIX


@pytest_asyncio.fixture
async def jobs_client(app):
    """An async HTTP client bound to the app."""
    app.dependency_overrides[assert_session_live] = lambda: None
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as http_client:
        yield http_client
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_job_status_success(jobs_client: AsyncClient, auth_headers: dict[str, str]) -> None:
    """GET /jobs/{job_id} returns the status from Redis."""
    status_data = {
        "job_id": "test_123",
        "job_name": "deliver_notification",
        "status": "running",
        "enqueue_time": "2026-07-13T10:00:00Z",
        "start_time": "2026-07-13T10:01:00Z",
        "try_count": 1,
        "error": None,
    }
    with patch("app.modules.jobs.router.cache_get_json", return_value=status_data):
        resp = await jobs_client.get(
            f"{API_PREFIX}/jobs/test_123", headers=auth_headers
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["job_id"] == "test_123"
        assert data["status"] == "running"


@pytest.mark.asyncio
async def test_get_job_status_not_found(jobs_client: AsyncClient, auth_headers: dict[str, str]) -> None:
    """GET /jobs/{job_id} returns 404 when job does not exist in Redis."""
    with patch("app.modules.jobs.router.cache_get_json", return_value=None):
        resp = await jobs_client.get(
            f"{API_PREFIX}/jobs/missing_123", headers=auth_headers
        )
        assert resp.status_code == 404
        assert "not found" in resp.json()["message"].lower()
