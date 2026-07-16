from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.core.dependencies.auth import assert_session_live
from app.modules.organization.dependencies import get_department_service
from app.modules.organization.exceptions import (
    DepartmentInUseException,
    DepartmentNotFoundException,
)
from app.modules.organization.schemas import DepartmentListResponse, DepartmentSchema
from tests.conftest import API_PREFIX

_NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


@pytest.fixture
def mock_department_service() -> AsyncMock:
    return AsyncMock()


@pytest_asyncio.fixture
async def department_client(app, mock_department_service: AsyncMock):
    app.dependency_overrides[assert_session_live] = lambda: None
    app.dependency_overrides[get_department_service] = lambda: mock_department_service
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as http_client:
        yield http_client
    app.dependency_overrides.clear()


def _schema(dept_id: int = 1, name: str = "Engineering", employee_count: int = 0) -> DepartmentSchema:
    return DepartmentSchema(
        dept_id=dept_id,
        org_id=1,
        dept_name=name,
        is_active=True,
        is_deleted=False,
        created_by=2,
        created_at=_NOW,
        updated_at=_NOW,
        employee_count=employee_count,
    )


async def test_list_departments_200(
    department_client: AsyncClient, mock_department_service: AsyncMock, super_admin_headers
) -> None:
    mock_department_service.list_departments.return_value = DepartmentListResponse.build(
        items=[_schema(1, "Engineering", 5)], page=1, page_size=25, total_records=1
    )
    resp = await department_client.get(
        f"{API_PREFIX}/departments?page=1&page_size=25",
        headers=super_admin_headers,
    )
    assert resp.status_code == 200
    body = resp.json()["data"]
    assert body["pagination"]["total_records"] == 1
    assert len(body["items"]) == 1
    assert body["items"][0]["dept_id"] == 1
    assert body["items"][0]["employee_count"] == 5


async def test_delete_department_200(
    department_client: AsyncClient, mock_department_service: AsyncMock, super_admin_headers
) -> None:
    mock_department_service.delete_department.return_value = _schema(1, "Engineering")
    resp = await department_client.delete(
        f"{API_PREFIX}/departments/1",
        headers=super_admin_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["dept_id"] == 1
    mock_department_service.delete_department.assert_awaited_once_with(
        org_id=1, actor_id=1, dept_id=1
    )


async def test_delete_department_in_use_409(
    department_client: AsyncClient, mock_department_service: AsyncMock, super_admin_headers
) -> None:
    mock_department_service.delete_department.side_effect = DepartmentInUseException()
    resp = await department_client.delete(
        f"{API_PREFIX}/departments/1",
        headers=super_admin_headers,
    )
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "DEPARTMENT_IN_USE"


async def test_delete_department_not_found_404(
    department_client: AsyncClient, mock_department_service: AsyncMock, super_admin_headers
) -> None:
    mock_department_service.delete_department.side_effect = DepartmentNotFoundException()
    resp = await department_client.delete(
        f"{API_PREFIX}/departments/99",
        headers=super_admin_headers,
    )
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "DEPARTMENT_NOT_FOUND"


async def test_delete_department_forbidden_without_permission(
    department_client: AsyncClient, make_access_token
) -> None:
    token = make_access_token(is_super_admin=False, permissions=[])
    resp = await department_client.delete(
        f"{API_PREFIX}/departments/1",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "AUTH_FORBIDDEN"


async def test_delete_department_allowed_with_permission(
    department_client: AsyncClient, mock_department_service: AsyncMock, make_access_token
) -> None:
    mock_department_service.delete_department.return_value = _schema(1, "Engineering")
    token = make_access_token(
        is_super_admin=False,
        permissions=[{"feature_key": "department", "can_delete": True}],
    )
    resp = await department_client.delete(
        f"{API_PREFIX}/departments/1",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
