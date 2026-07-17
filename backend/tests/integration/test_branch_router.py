from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.core.dependencies.auth import assert_session_live
from app.modules.organization.dependencies import get_branch_service
from app.modules.organization.exceptions import (
    BranchInUseException,
    BranchNotFoundException,
)
from app.modules.organization.schemas import BranchSchema
from tests.conftest import API_PREFIX

_NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


@pytest.fixture
def mock_branch_service() -> AsyncMock:
    return AsyncMock()


@pytest_asyncio.fixture
async def branch_client(app, mock_branch_service: AsyncMock):
    app.dependency_overrides[assert_session_live] = lambda: None
    app.dependency_overrides[get_branch_service] = lambda: mock_branch_service
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as http_client:
        yield http_client
    app.dependency_overrides.clear()


def _schema(branch_id: int = 1, name: str = "HQ", employee_count: int = 0) -> BranchSchema:
    return BranchSchema(
        branch_id=branch_id,
        org_id=1,
        branch_name=name,
        logo_url=None,
        gstin="27AAACG1234A1Z1",
        mobile_number="9876543210",
        address="123 Main St",
        landmark="Near Central Park",
        pin_code="400001",
        city="Mumbai",
        state="Maharashtra",
        country="India",
        industry_type="IT",
        latitude=19.076,
        longitude=72.8777,
        allowed_radius_meters=100,
        is_active=True,
        is_deleted=False,
        employee_count=employee_count,
        created_at=_NOW,
        updated_at=_NOW,
    )


async def test_delete_branch_200(
    branch_client: AsyncClient, mock_branch_service: AsyncMock, super_admin_headers
) -> None:
    mock_branch_service.delete_branch.return_value = _schema(1, "HQ")
    resp = await branch_client.delete(
        f"{API_PREFIX}/branches/1",
        headers=super_admin_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["branch_id"] == 1
    mock_branch_service.delete_branch.assert_awaited_once_with(
        org_id=1, actor_id=1, branch_id=1
    )


async def test_delete_branch_in_use_409(
    branch_client: AsyncClient, mock_branch_service: AsyncMock, super_admin_headers
) -> None:
    mock_branch_service.delete_branch.side_effect = BranchInUseException()
    resp = await branch_client.delete(
        f"{API_PREFIX}/branches/1",
        headers=super_admin_headers,
    )
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "BRANCH_IN_USE"


async def test_delete_branch_not_found_404(
    branch_client: AsyncClient, mock_branch_service: AsyncMock, super_admin_headers
) -> None:
    mock_branch_service.delete_branch.side_effect = BranchNotFoundException()
    resp = await branch_client.delete(
        f"{API_PREFIX}/branches/99",
        headers=super_admin_headers,
    )
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "BRANCH_NOT_FOUND"


async def test_delete_branch_forbidden_without_permission(
    branch_client: AsyncClient, make_access_token
) -> None:
    token = make_access_token(is_super_admin=False, permissions=[])
    resp = await branch_client.delete(
        f"{API_PREFIX}/branches/1",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "AUTH_FORBIDDEN"


async def test_delete_branch_allowed_with_permission(
    branch_client: AsyncClient, mock_branch_service: AsyncMock, make_access_token
) -> None:
    mock_branch_service.delete_branch.return_value = _schema(1, "HQ")
    token = make_access_token(
        is_super_admin=False,
        permissions=[{"feature_key": "branch", "can_delete": True}],
    )
    resp = await branch_client.delete(
        f"{API_PREFIX}/branches/1",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
