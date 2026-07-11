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
    EmployeeBankDetailSchema,
    EmployeeCreateResponse,
    EmployeeDetailSchema,
    EmployeeDocumentSchema,
    EmployeeListResponse,
    EmployeeStatusHistorySchema,
    EmployeeSummarySchema,
    EmployeeTagSchema,
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
    resp = await employee_client.patch(
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


# ===========================================================================
# Status lifecycle (#29–#31) and org moves (#32–#33)
# ===========================================================================
async def test_activate_employee_200_empty_body(
    employee_client: AsyncClient, mock_employee_service: AsyncMock, super_admin_headers
) -> None:
    """Activate accepts an omitted body (effective_date / reason are optional)."""
    mock_employee_service.activate_employee.return_value = _detail()
    resp = await employee_client.post(
        f"{API_PREFIX}/employees/1/activate", headers=super_admin_headers
    )
    assert resp.status_code == 200
    kwargs = mock_employee_service.activate_employee.await_args.kwargs
    assert kwargs["employee_id"] == 1
    assert kwargs["reason"] is None


async def test_deactivate_employee_200_with_body(
    employee_client: AsyncClient, mock_employee_service: AsyncMock, super_admin_headers
) -> None:
    mock_employee_service.deactivate_employee.return_value = _detail()
    resp = await employee_client.post(
        f"{API_PREFIX}/employees/1/deactivate",
        json={"effective_date": "2026-04-01", "reason": "sabbatical"},
        headers=super_admin_headers,
    )
    assert resp.status_code == 200
    kwargs = mock_employee_service.deactivate_employee.await_args.kwargs
    assert kwargs["reason"] == "sabbatical"


async def test_terminate_employee_200(
    employee_client: AsyncClient, mock_employee_service: AsyncMock, super_admin_headers
) -> None:
    mock_employee_service.terminate_employee.return_value = _detail()
    resp = await employee_client.post(
        f"{API_PREFIX}/employees/1/terminate",
        json={"effective_date": "2026-05-01", "date_of_leaving": "2026-05-15", "reason": "x"},
        headers=super_admin_headers,
    )
    assert resp.status_code == 200


async def test_terminate_employee_requires_effective_date_422(
    employee_client: AsyncClient, super_admin_headers
) -> None:
    resp = await employee_client.post(
        f"{API_PREFIX}/employees/1/terminate", json={}, headers=super_admin_headers
    )
    assert resp.status_code == 422


async def test_transfer_employee_200(
    employee_client: AsyncClient, mock_employee_service: AsyncMock, super_admin_headers
) -> None:
    mock_employee_service.transfer_employee.return_value = _detail()
    resp = await employee_client.post(
        f"{API_PREFIX}/employees/1/transfer",
        json={"master_branch_id": 2, "reason": "restructure"},
        headers=super_admin_headers,
    )
    assert resp.status_code == 200


async def test_transfer_employee_without_target_422(
    employee_client: AsyncClient, super_admin_headers
) -> None:
    resp = await employee_client.post(
        f"{API_PREFIX}/employees/1/transfer",
        json={"reason": "no target"},
        headers=super_admin_headers,
    )
    assert resp.status_code == 422


async def test_promote_employee_forwards_salary_permission(
    employee_client: AsyncClient, mock_employee_service: AsyncMock, make_access_token
) -> None:
    """Without employee_salary read, the promote salary change is gated out."""
    mock_employee_service.promote_employee.return_value = _detail()
    token = make_access_token(
        is_super_admin=False,
        permissions=[{"feature_key": "employee", "can_read": True, "can_edit": True}],
    )
    resp = await employee_client.post(
        f"{API_PREFIX}/employees/1/promote",
        json={"designation_id": 3, "monthly_salary": "60000"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert mock_employee_service.promote_employee.await_args.kwargs["can_set_salary"] is False


async def test_lifecycle_forbidden_without_edit_permission(
    employee_client: AsyncClient, make_access_token
) -> None:
    token = make_access_token(
        is_super_admin=False,
        permissions=[{"feature_key": "employee", "can_read": True}],
    )
    for path, body in (
        ("activate", None),
        ("deactivate", None),
        ("terminate", {"effective_date": "2026-05-01"}),
        ("transfer", {"master_branch_id": 2}),
        ("promote", {"designation_id": 3}),
    ):
        resp = await employee_client.post(
            f"{API_PREFIX}/employees/1/{path}",
            json=body,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403, path
        assert resp.json()["error"]["code"] == "AUTH_FORBIDDEN"


# ===========================================================================
# Documents (#35–#37)
# ===========================================================================
def _document() -> EmployeeDocumentSchema:
    return EmployeeDocumentSchema(
        document_id=5,
        document_type="pan_card",
        file_url="s3://bucket/doc.pdf",
        original_filename="pan.pdf",
        file_size_bytes=1024,
        uploaded_by=1,
        created_at=_NOW,
        updated_at=_NOW,
    )


async def test_list_documents_200(
    employee_client: AsyncClient, mock_employee_service: AsyncMock, super_admin_headers
) -> None:
    mock_employee_service.list_documents.return_value = [_document()]
    resp = await employee_client.get(
        f"{API_PREFIX}/employees/1/documents", headers=super_admin_headers
    )
    assert resp.status_code == 200
    assert resp.json()["data"][0]["document_id"] == 5


async def test_get_document_200(
    employee_client: AsyncClient, mock_employee_service: AsyncMock, super_admin_headers
) -> None:
    mock_employee_service.get_document.return_value = _document()
    resp = await employee_client.get(
        f"{API_PREFIX}/employees/1/documents/5", headers=super_admin_headers
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["file_url"] == "s3://bucket/doc.pdf"


async def test_delete_document_204(
    employee_client: AsyncClient, mock_employee_service: AsyncMock, super_admin_headers
) -> None:
    mock_employee_service.delete_document.return_value = None
    resp = await employee_client.delete(
        f"{API_PREFIX}/employees/1/documents/5", headers=super_admin_headers
    )
    assert resp.status_code == 204


# ===========================================================================
# Bank details (#38–#41) — reads gated by employee_salary read as well
# ===========================================================================
def _bank_detail() -> EmployeeBankDetailSchema:
    return EmployeeBankDetailSchema(
        bank_detail_id=3,
        bank_name="HDFC",
        bank_branch_name="MG Road",
        account_number="1234567890",
        ifsc_code="HDFC0001234",
        is_primary=True,
        created_at=_NOW,
        updated_at=_NOW,
    )


async def test_list_bank_details_requires_salary_permission(
    employee_client: AsyncClient, mock_employee_service: AsyncMock, make_access_token
) -> None:
    """employee:read alone is NOT enough to read account numbers (sensitive)."""
    mock_employee_service.list_bank_details.return_value = [_bank_detail()]
    token = make_access_token(
        is_super_admin=False,
        permissions=[{"feature_key": "employee", "can_read": True}],
    )
    resp = await employee_client.get(
        f"{API_PREFIX}/employees/1/bank-details",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "AUTH_FORBIDDEN"


async def test_list_bank_details_200_with_salary_permission(
    employee_client: AsyncClient, mock_employee_service: AsyncMock, make_access_token
) -> None:
    mock_employee_service.list_bank_details.return_value = [_bank_detail()]
    token = make_access_token(
        is_super_admin=False,
        permissions=[
            {"feature_key": "employee", "can_read": True},
            {"feature_key": "employee_salary", "can_read": True},
        ],
    )
    resp = await employee_client.get(
        f"{API_PREFIX}/employees/1/bank-details",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["data"][0]["account_number"] == "1234567890"


async def test_add_bank_detail_201(
    employee_client: AsyncClient, mock_employee_service: AsyncMock, super_admin_headers
) -> None:
    mock_employee_service.add_bank_detail.return_value = _bank_detail()
    resp = await employee_client.post(
        f"{API_PREFIX}/employees/1/bank-details",
        json={"bank_name": "HDFC", "account_number": "1234567890", "ifsc_code": "HDFC0001234"},
        headers=super_admin_headers,
    )
    assert resp.status_code == 201
    assert resp.json()["data"]["bank_detail_id"] == 3


async def test_add_bank_detail_invalid_ifsc_422(
    employee_client: AsyncClient, super_admin_headers
) -> None:
    resp = await employee_client.post(
        f"{API_PREFIX}/employees/1/bank-details",
        json={"ifsc_code": "BAD"},
        headers=super_admin_headers,
    )
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "VALIDATION_ERROR"


async def test_update_bank_detail_200(
    employee_client: AsyncClient, mock_employee_service: AsyncMock, super_admin_headers
) -> None:
    mock_employee_service.update_bank_detail.return_value = _bank_detail()
    resp = await employee_client.patch(
        f"{API_PREFIX}/employees/1/bank-details/3",
        json={"bank_name": "ICICI"},
        headers=super_admin_headers,
    )
    assert resp.status_code == 200


async def test_delete_bank_detail_204(
    employee_client: AsyncClient, mock_employee_service: AsyncMock, super_admin_headers
) -> None:
    mock_employee_service.delete_bank_detail.return_value = None
    resp = await employee_client.delete(
        f"{API_PREFIX}/employees/1/bank-details/3", headers=super_admin_headers
    )
    assert resp.status_code == 204


# ===========================================================================
# Emergency contacts (#42–#45) and references (#46–#49)
# ===========================================================================
async def test_add_emergency_contact_201(
    employee_client: AsyncClient, mock_employee_service: AsyncMock, super_admin_headers
) -> None:
    mock_employee_service.add_emergency_contact.return_value = {
        "emergency_contact_id": 7,
        "contact_country_code": "+91",
        "contact_number": "9876500000",
        "contact_person_name": "John Doe",
        "relation": "spouse",
        "address": None,
        "created_at": _NOW.isoformat(),
        "updated_at": _NOW.isoformat(),
    }
    resp = await employee_client.post(
        f"{API_PREFIX}/employees/1/emergency-contacts",
        json={"contact_number": "9876500000", "contact_person_name": "John Doe"},
        headers=super_admin_headers,
    )
    assert resp.status_code == 201
    assert resp.json()["data"]["emergency_contact_id"] == 7


async def test_add_emergency_contact_missing_name_422(
    employee_client: AsyncClient, super_admin_headers
) -> None:
    resp = await employee_client.post(
        f"{API_PREFIX}/employees/1/emergency-contacts",
        json={"contact_number": "9876500000"},
        headers=super_admin_headers,
    )
    assert resp.status_code == 422


async def test_add_reference_201(
    employee_client: AsyncClient, mock_employee_service: AsyncMock, super_admin_headers
) -> None:
    mock_employee_service.add_reference.return_value = {
        "reference_id": 8,
        "reference_name": "Jane Ref",
        "reference_country_code": "+91",
        "reference_contact_number": "9876511111",
        "sort_order": 1,
        "created_at": _NOW.isoformat(),
        "updated_at": _NOW.isoformat(),
    }
    resp = await employee_client.post(
        f"{API_PREFIX}/employees/1/references",
        json={"reference_name": "Jane Ref", "reference_contact_number": "9876511111"},
        headers=super_admin_headers,
    )
    assert resp.status_code == 201


async def test_delete_reference_204(
    employee_client: AsyncClient, mock_employee_service: AsyncMock, super_admin_headers
) -> None:
    mock_employee_service.delete_reference.return_value = None
    resp = await employee_client.delete(
        f"{API_PREFIX}/employees/1/references/8", headers=super_admin_headers
    )
    assert resp.status_code == 204


# ===========================================================================
# Tags (#50–#52) and status history (#53)
# ===========================================================================
async def test_add_and_delete_tag(
    employee_client: AsyncClient, mock_employee_service: AsyncMock, super_admin_headers
) -> None:
    mock_employee_service.add_tag.return_value = EmployeeTagSchema(
        tag_id=4,
        tag_label="Star",
        tag_color="#ff0000",
        is_status_tag=False,
        created_by=1,
        created_at=_NOW,
        updated_at=_NOW,
    )
    resp = await employee_client.post(
        f"{API_PREFIX}/employees/1/tags",
        json={"tag_label": "Star", "tag_color": "#ff0000"},
        headers=super_admin_headers,
    )
    assert resp.status_code == 201
    assert resp.json()["data"]["tag_id"] == 4

    mock_employee_service.delete_tag.return_value = None
    resp = await employee_client.delete(
        f"{API_PREFIX}/employees/1/tags/4", headers=super_admin_headers
    )
    assert resp.status_code == 204


async def test_list_status_history_200(
    employee_client: AsyncClient, mock_employee_service: AsyncMock, super_admin_headers
) -> None:
    mock_employee_service.list_status_history.return_value = [
        EmployeeStatusHistorySchema(
            status_history_id=1,
            previous_status=None,
            new_status="active",
            changed_by=1,
            reason=None,
            effective_date="2026-01-01",
            created_at=_NOW,
        )
    ]
    resp = await employee_client.get(
        f"{API_PREFIX}/employees/1/status-history", headers=super_admin_headers
    )
    assert resp.status_code == 200
    assert resp.json()["data"][0]["new_status"] == "active"
