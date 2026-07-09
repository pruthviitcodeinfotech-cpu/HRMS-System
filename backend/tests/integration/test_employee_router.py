"""Integration tests for the Employee Management router.

Exercises the real app + real auth/permission dependencies with only
``EmployeeService`` mocked. Covers the happy-path CRUD / list / exit / rehire
endpoints (as a super admin, who bypasses the feature-permission guards), plus
permission enforcement, unauthenticated access, salary-scope gating, and
validation failures.

The employee router is not yet mounted in the production app factory (consistent
with the other module routers), so a module-local ``employee_app`` / ``employee_client``
fixture mounts it and overrides the service dependency — reusing the shared token
and header fixtures from :mod:`tests.conftest`.
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.main import create_app
from app.modules.employee.router import get_employee_service
from app.modules.employee.router import router as employee_router
from app.modules.employee.schemas import (
    EmployeeCreateResponse,
    EmployeeDetailSchema,
    EmployeeDocumentSchema,
    EmployeeListResponse,
    EmployeeSummarySchema,
)
from tests.conftest import API_PREFIX

_NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Fixtures (module-local: mount the employee router + mock its service)
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_employee_service() -> AsyncMock:
    """An ``AsyncMock`` standing in for :class:`EmployeeService`."""
    return AsyncMock()


@pytest.fixture
def employee_app():
    """The production app factory with the employee router mounted at the API prefix."""
    application = create_app()
    application.include_router(employee_router, prefix=API_PREFIX)
    return application


@pytest_asyncio.fixture
async def employee_client(employee_app, mock_employee_service: AsyncMock):
    """An async HTTP client bound to the app, with ``EmployeeService`` mocked."""
    employee_app.dependency_overrides[get_employee_service] = lambda: mock_employee_service
    transport = ASGITransport(app=employee_app)
    async with AsyncClient(transport=transport, base_url="http://test") as http_client:
        yield http_client
    employee_app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Response builders
# ---------------------------------------------------------------------------


def _detail() -> EmployeeDetailSchema:
    return EmployeeDetailSchema(
        employee_id=1,
        org_id=1,
        employee_code="EMP00001",
        employee_name="Jane Doe",
        mobile_country_code="+91",
        mobile_number="9876543210",
        gender="Female",
        master_branch_id=1,
        dept_id=1,
        designation_id=1,
        employment_status="active",
        created_at=_NOW,
        updated_at=_NOW,
    )


def _create_response() -> EmployeeCreateResponse:
    return EmployeeCreateResponse(**_detail().model_dump())


def _summary() -> EmployeeSummarySchema:
    return EmployeeSummarySchema(
        employee_id=1,
        org_id=1,
        employee_code="EMP00001",
        employee_name="Jane Doe",
        mobile_country_code="+91",
        mobile_number="9876543210",
        gender="Female",
        master_branch_id=1,
        dept_id=1,
        designation_id=1,
        employment_status="active",
        created_at=_NOW,
    )


def _list_response() -> EmployeeListResponse:
    return EmployeeListResponse.build(
        items=[_summary()], page=1, page_size=25, total_records=1
    )


def _valid_create_body() -> dict[str, object]:
    return {
        "employee_name": "Jane Doe",
        "gender": "Female",
        "mobile_number": "9876543210",
        "master_branch_id": 1,
        "dept_id": 1,
        "designation_id": 1,
        "date_of_joining": "2026-01-01",
    }


# ===========================================================================
# Happy path (super admin bypasses permission guards)
# ===========================================================================
async def test_list_employees_200(
    employee_client: AsyncClient, mock_employee_service: AsyncMock, super_admin_headers
) -> None:
    mock_employee_service.list_employees.return_value = _list_response()
    resp = await employee_client.get(
        f"{API_PREFIX}/employees?q=jane&branch_id=1&page=1&page_size=25",
        headers=super_admin_headers,
    )
    assert resp.status_code == 200
    body = resp.json()["data"]
    assert body["pagination"]["total_records"] == 1
    assert len(body["items"]) == 1


async def test_create_employee_201(
    employee_client: AsyncClient, mock_employee_service: AsyncMock, super_admin_headers
) -> None:
    mock_employee_service.create_employee.return_value = _create_response()
    resp = await employee_client.post(
        f"{API_PREFIX}/employees", json=_valid_create_body(), headers=super_admin_headers
    )
    assert resp.status_code == 201
    assert resp.json()["data"]["employee_code"] == "EMP00001"


async def test_get_employee_200(
    employee_client: AsyncClient, mock_employee_service: AsyncMock, super_admin_headers
) -> None:
    mock_employee_service.get_employee.return_value = _detail()
    resp = await employee_client.get(f"{API_PREFIX}/employees/1", headers=super_admin_headers)
    assert resp.status_code == 200
    assert resp.json()["data"]["employee_id"] == 1


async def test_update_employee_200(
    employee_client: AsyncClient, mock_employee_service: AsyncMock, super_admin_headers
) -> None:
    mock_employee_service.update_employee.return_value = _detail()
    resp = await employee_client.put(
        f"{API_PREFIX}/employees/1",
        json={"employee_name": "Jane R. Doe"},
        headers=super_admin_headers,
    )
    assert resp.status_code == 200


async def test_exit_employee_200(
    employee_client: AsyncClient, mock_employee_service: AsyncMock, super_admin_headers
) -> None:
    mock_employee_service.exit_employee.return_value = _detail()
    resp = await employee_client.post(
        f"{API_PREFIX}/employees/1/exit",
        json={
            "resignation_date": "2026-03-01",
            "last_working_day": "2026-03-30",
            "reason": "resigned",
        },
        headers=super_admin_headers,
    )
    assert resp.status_code == 200


async def test_rehire_employee_200(
    employee_client: AsyncClient, mock_employee_service: AsyncMock, super_admin_headers
) -> None:
    mock_employee_service.rehire_employee.return_value = _detail()
    resp = await employee_client.post(
        f"{API_PREFIX}/employees/1/rehire",
        json={"date_of_joining": "2026-06-01"},
        headers=super_admin_headers,
    )
    assert resp.status_code == 200


# ===========================================================================
# Authorization
# ===========================================================================
async def test_create_employee_forbidden_without_permission(
    employee_client: AsyncClient, make_access_token
) -> None:
    token = make_access_token(is_super_admin=False, permissions=[])
    resp = await employee_client.post(
        f"{API_PREFIX}/employees",
        json=_valid_create_body(),
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "AUTH_FORBIDDEN"


async def test_create_employee_allowed_with_permission(
    employee_client: AsyncClient, mock_employee_service: AsyncMock, make_access_token
) -> None:
    mock_employee_service.create_employee.return_value = _create_response()
    token = make_access_token(
        is_super_admin=False,
        permissions=[{"feature_key": "employee", "can_create": True, "can_read": True}],
    )
    resp = await employee_client.post(
        f"{API_PREFIX}/employees",
        json=_valid_create_body(),
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201


async def test_list_employees_requires_authentication(employee_client: AsyncClient) -> None:
    resp = await employee_client.get(f"{API_PREFIX}/employees")
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "AUTH_NOT_AUTHENTICATED"


# ===========================================================================
# Salary-scope gating (employee.salary.view)
# ===========================================================================
async def test_get_employee_salary_visible_flag_forwarded(
    employee_client: AsyncClient, mock_employee_service: AsyncMock, make_access_token
) -> None:
    """The salary permission is translated into ``include_salary=True`` for the service."""
    mock_employee_service.get_employee.return_value = _detail()
    token = make_access_token(
        is_super_admin=False,
        permissions=[
            {"feature_key": "employee", "can_read": True},
            {"feature_key": "employee_salary", "can_read": True},
        ],
    )
    resp = await employee_client.get(
        f"{API_PREFIX}/employees/1", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 200
    assert mock_employee_service.get_employee.await_args.kwargs["include_salary"] is True


async def test_get_employee_salary_hidden_without_permission(
    employee_client: AsyncClient, mock_employee_service: AsyncMock, make_access_token
) -> None:
    mock_employee_service.get_employee.return_value = _detail()
    token = make_access_token(
        is_super_admin=False, permissions=[{"feature_key": "employee", "can_read": True}]
    )
    resp = await employee_client.get(
        f"{API_PREFIX}/employees/1", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 200
    assert mock_employee_service.get_employee.await_args.kwargs["include_salary"] is False


# ===========================================================================
# Validation failures (422)
# ===========================================================================
async def test_create_employee_invalid_email_422(
    employee_client: AsyncClient, super_admin_headers
) -> None:
    body = _valid_create_body() | {"email": "not-an-email"}
    resp = await employee_client.post(
        f"{API_PREFIX}/employees", json=body, headers=super_admin_headers
    )
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "VALIDATION_ERROR"


async def test_create_employee_missing_required_422(
    employee_client: AsyncClient, super_admin_headers
) -> None:
    body = _valid_create_body()
    del body["employee_name"]
    resp = await employee_client.post(
        f"{API_PREFIX}/employees", json=body, headers=super_admin_headers
    )
    assert resp.status_code == 422


async def test_exit_employee_invalid_dates_422(
    employee_client: AsyncClient, super_admin_headers
) -> None:
    resp = await employee_client.post(
        f"{API_PREFIX}/employees/1/exit",
        json={"resignation_date": "2026-03-10", "last_working_day": "2026-03-01"},
        headers=super_admin_headers,
    )
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "VALIDATION_ERROR"


# ===========================================================================
# Documents & photo (newly served by this module)
# ===========================================================================
async def test_add_document_201(
    employee_client: AsyncClient, mock_employee_service: AsyncMock, super_admin_headers
) -> None:
    mock_employee_service.add_document.return_value = EmployeeDocumentSchema(
        document_id=5,
        document_type="pan_card",
        file_url="s3://bucket/doc.pdf",
        original_filename="pan.pdf",
        file_size_bytes=1024,
        uploaded_by=1,
        created_at=_NOW,
        updated_at=_NOW,
    )
    resp = await employee_client.post(
        f"{API_PREFIX}/employees/1/documents",
        json={"document_type": "pan_card", "file_url": "s3://bucket/doc.pdf"},
        headers=super_admin_headers,
    )
    assert resp.status_code == 201
    assert resp.json()["data"]["document_id"] == 5


async def test_set_photo_200(
    employee_client: AsyncClient, mock_employee_service: AsyncMock, super_admin_headers
) -> None:
    mock_employee_service.set_photo.return_value = _detail()
    resp = await employee_client.post(
        f"{API_PREFIX}/employees/1/photo",
        json={"file_url": "s3://bucket/photo.jpg"},
        headers=super_admin_headers,
    )
    assert resp.status_code == 200


async def test_add_document_forbidden_without_permission(
    employee_client: AsyncClient, make_access_token
) -> None:
    token = make_access_token(is_super_admin=False, permissions=[])
    resp = await employee_client.post(
        f"{API_PREFIX}/employees/1/documents",
        json={"document_type": "pan_card", "file_url": "s3://x"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "AUTH_FORBIDDEN"
