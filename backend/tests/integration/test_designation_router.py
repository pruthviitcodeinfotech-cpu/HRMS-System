"""Integration tests for the Designation router.

Covers:
  - GET  /designations          — 200, pagination, employee_count in response
  - DELETE /designations/{id}   — 200 success
  - DELETE /designations/{id}   — 409 in-use
  - DELETE /designations/{id}   — 404 not found
  - DELETE /designations/{id}   — 403 without designation:delete permission
  - DELETE /designations/{id}   — 200 with designation:delete permission
"""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.core.dependencies.auth import assert_session_live
from app.modules.organization.dependencies import get_designation_service
from app.modules.organization.exceptions import (
    DesignationInUseException,
    DesignationNotFoundException,
)
from app.modules.organization.schemas import DesignationListResponse, DesignationSchema
from tests.conftest import API_PREFIX

_NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


@pytest.fixture
def mock_designation_service() -> AsyncMock:
    return AsyncMock()


@pytest_asyncio.fixture
async def designation_client(app, mock_designation_service: AsyncMock):
    app.dependency_overrides[assert_session_live] = lambda: None
    app.dependency_overrides[get_designation_service] = lambda: mock_designation_service
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as http_client:
        yield http_client
    app.dependency_overrides.clear()


def _schema(
    designation_id: int = 1,
    name: str = "Engineering Lead",
    employee_count: int = 0,
) -> DesignationSchema:
    return DesignationSchema(
        designation_id=designation_id,
        org_id=1,
        designation_name=name,
        is_active=True,
        is_deleted=False,
        created_by=2,
        created_at=_NOW,
        updated_at=_NOW,
        employee_count=employee_count,
    )


# ---------------------------------------------------------------------------
# GET /designations — employee_count in list response
# ---------------------------------------------------------------------------


async def test_list_designations_200(
    designation_client: AsyncClient, mock_designation_service: AsyncMock, super_admin_headers
) -> None:
    mock_designation_service.list_designations.return_value = DesignationListResponse.build(
        items=[_schema(1, "Engineering Lead", 5), _schema(2, "Sales Manager", 0)],
        page=1,
        page_size=25,
        total_records=2,
    )
    resp = await designation_client.get(
        f"{API_PREFIX}/designations?page=1&page_size=25",
        headers=super_admin_headers,
    )
    assert resp.status_code == 200
    body = resp.json()["data"]
    assert body["pagination"]["total_records"] == 2
    assert len(body["items"]) == 2
    assert body["items"][0]["designation_id"] == 1
    assert body["items"][0]["employee_count"] == 5
    assert body["items"][1]["designation_id"] == 2
    assert body["items"][1]["employee_count"] == 0


# ---------------------------------------------------------------------------
# DELETE /designations/{id} — success
# ---------------------------------------------------------------------------


async def test_delete_designation_200(
    designation_client: AsyncClient, mock_designation_service: AsyncMock, super_admin_headers
) -> None:
    mock_designation_service.delete_designation.return_value = _schema(1, "Engineering Lead")
    resp = await designation_client.delete(
        f"{API_PREFIX}/designations/1",
        headers=super_admin_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["designation_id"] == 1
    mock_designation_service.delete_designation.assert_awaited_once_with(
        org_id=1, actor_id=1, designation_id=1
    )


# ---------------------------------------------------------------------------
# DELETE /designations/{id} — 409 in use
# ---------------------------------------------------------------------------


async def test_delete_designation_in_use_409(
    designation_client: AsyncClient, mock_designation_service: AsyncMock, super_admin_headers
) -> None:
    mock_designation_service.delete_designation.side_effect = DesignationInUseException()
    resp = await designation_client.delete(
        f"{API_PREFIX}/designations/1",
        headers=super_admin_headers,
    )
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "DESIGNATION_IN_USE"


# ---------------------------------------------------------------------------
# DELETE /designations/{id} — 404 not found
# ---------------------------------------------------------------------------


async def test_delete_designation_not_found_404(
    designation_client: AsyncClient, mock_designation_service: AsyncMock, super_admin_headers
) -> None:
    mock_designation_service.delete_designation.side_effect = DesignationNotFoundException()
    resp = await designation_client.delete(
        f"{API_PREFIX}/designations/99",
        headers=super_admin_headers,
    )
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "DESIGNATION_NOT_FOUND"


# ---------------------------------------------------------------------------
# DELETE /designations/{id} — 403 without designation:delete permission
# ---------------------------------------------------------------------------


async def test_delete_designation_forbidden_without_permission(
    designation_client: AsyncClient, make_access_token
) -> None:
    token = make_access_token(is_super_admin=False, permissions=[])
    resp = await designation_client.delete(
        f"{API_PREFIX}/designations/1",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "AUTH_FORBIDDEN"


# ---------------------------------------------------------------------------
# DELETE /designations/{id} — 200 with designation:delete permission
# ---------------------------------------------------------------------------


async def test_delete_designation_allowed_with_permission(
    designation_client: AsyncClient, mock_designation_service: AsyncMock, make_access_token
) -> None:
    mock_designation_service.delete_designation.return_value = _schema(1, "Engineering Lead")
    token = make_access_token(
        is_super_admin=False,
        permissions=[{"feature_key": "designation", "can_delete": True}],
    )
    resp = await designation_client.delete(
        f"{API_PREFIX}/designations/1",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
