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

from datetime import date, datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.core.dependencies.auth import assert_session_live
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
from app.modules.employee.service import DocumentDownload, EmployeeService
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
    # The auth dependency re-validates the session against the DB on every request;
    # router tests exercise the HTTP layer without a database, so stub that check.
    employee_app.dependency_overrides[assert_session_live] = lambda: None
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
# Sensitive sections of GET /employees/{id} — bank details (regression)
#
# The embedded ``bank_details`` list must honour the SAME gate as the standalone
# ``GET /employees/{id}/bank-details`` route (employee:read + employee_salary:read).
# These drive the real detail projection (``EmployeeService._build_detail``) through the
# router so the assertions are on the actual response body, not just a forwarded flag.
# ===========================================================================
def _orm_employee() -> SimpleNamespace:
    """A stand-in eager-loaded ``employees`` row carrying sensitive satellites."""
    bank_row = SimpleNamespace(
        bank_detail_id=3,
        bank_name="HDFC",
        bank_branch_name="MG Road",
        account_number="1234567890",
        ifsc_code="HDFC0001234",
        is_primary=True,
        created_at=_NOW,
        updated_at=_NOW,
    )
    document_row = SimpleNamespace(
        document_id=5,
        document_type="pan_card",
        file_url="employees/1/deadbeef.pdf",
        original_filename="pan.pdf",
        file_size_bytes=1024,
        uploaded_by=1,
        created_at=_NOW,
        updated_at=_NOW,
    )
    return SimpleNamespace(
        employee_id=1,
        org_id=1,
        employee_code="EMP00001",
        employee_name="Jane Doe",
        display_name=None,
        employee_uid=None,
        gender="Female",
        mobile_country_code="+91",
        mobile_number="9876543210",
        email="jane@example.com",
        address=None,
        master_branch_id=1,
        dept_id=1,
        designation_id=1,
        employee_type=None,
        date_of_joining=date(2026, 1, 1),
        date_of_birth=None,
        date_of_leaving=None,
        door_lock_permission=False,
        pf_account_number=None,
        uan_number=None,
        esic_ip_number=None,
        salary_type="Monthly",
        monthly_salary=Decimal("50000.00"),
        payroll_group_id=None,
        employment_status="active",
        profile_photo_url=None,
        is_deleted=False,
        created_by=1,
        created_at=_NOW,
        updated_at=_NOW,
        master_branch=SimpleNamespace(branch_id=1, branch_name="HQ"),
        department=SimpleNamespace(dept_id=1, dept_name="Engineering"),
        designation=SimpleNamespace(designation_id=1, designation_name="Engineer"),
        bank_details=[bank_row],
        documents=[document_row],
        emergency_contacts=[],
        references=[],
        biometrics=[],
        punch_branches=[],
        attendance_permission=None,
        tags=[],
        status_history=[],
    )


def _real_projection(mock_employee_service: AsyncMock) -> None:
    """Make the mocked service build the *real* detail projection from the flags."""

    async def _get_employee(
        *, org_id: int, employee_id: int, include_salary: bool, include_bank_details: bool
    ) -> EmployeeDetailSchema:
        return EmployeeService._build_detail(
            _orm_employee(),
            include_salary=include_salary,
            include_bank_details=include_bank_details,
        )

    mock_employee_service.get_employee.side_effect = _get_employee


async def test_get_employee_omits_bank_details_without_salary_permission(
    employee_client: AsyncClient, mock_employee_service: AsyncMock, make_access_token
) -> None:
    """employee:read alone must NOT return account numbers via the employee detail."""
    _real_projection(mock_employee_service)
    token = make_access_token(
        is_super_admin=False, permissions=[{"feature_key": "employee", "can_read": True}]
    )
    resp = await employee_client.get(
        f"{API_PREFIX}/employees/1", headers={"Authorization": f"Bearer {token}"}
    )

    assert resp.status_code == 200
    body = resp.json()["data"]
    assert body["employee_id"] == 1  # the employee itself is still readable
    assert body["bank_details"] == []
    assert body["salary"] is None
    assert "1234567890" not in resp.text
    assert "HDFC0001234" not in resp.text
    assert mock_employee_service.get_employee.await_args.kwargs["include_bank_details"] is False


async def test_get_employee_includes_bank_details_with_salary_permission(
    employee_client: AsyncClient, mock_employee_service: AsyncMock, make_access_token
) -> None:
    """employee:read + employee_salary:read — the same pair the standalone route needs."""
    _real_projection(mock_employee_service)
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
    body = resp.json()["data"]
    assert [row["account_number"] for row in body["bank_details"]] == ["1234567890"]
    assert body["bank_details"][0]["ifsc_code"] == "HDFC0001234"
    assert body["salary"]["monthly_salary"] == "50000.00"
    assert mock_employee_service.get_employee.await_args.kwargs["include_bank_details"] is True


async def test_get_employee_documents_readable_with_employee_read(
    employee_client: AsyncClient, mock_employee_service: AsyncMock, make_access_token
) -> None:
    """Documents are governed by employee:read (contract §7/§11) — metadata only, no path."""
    _real_projection(mock_employee_service)
    token = make_access_token(
        is_super_admin=False, permissions=[{"feature_key": "employee", "can_read": True}]
    )
    resp = await employee_client.get(
        f"{API_PREFIX}/employees/1", headers={"Authorization": f"Bearer {token}"}
    )

    assert resp.status_code == 200
    documents = resp.json()["data"]["documents"]
    assert [doc["document_id"] for doc in documents] == [5]
    assert "file_url" not in documents[0]
    assert "employees/1/deadbeef.pdf" not in resp.text


async def test_list_employees_never_exposes_bank_details_or_salary(
    employee_client: AsyncClient, mock_employee_service: AsyncMock, make_access_token
) -> None:
    """The list projection (EmployeeSummarySchema) carries no sensitive sections at all."""
    mock_employee_service.list_employees.return_value = _list_response()
    token = make_access_token(
        is_super_admin=False,
        permissions=[
            {"feature_key": "employee", "can_read": True},
            {"feature_key": "employee_salary", "can_read": True},
        ],
    )
    resp = await employee_client.get(
        f"{API_PREFIX}/employees", headers={"Authorization": f"Bearer {token}"}
    )

    assert resp.status_code == 200
    row = resp.json()["data"]["items"][0]
    for sensitive in ("bank_details", "salary", "monthly_salary", "documents"):
        assert sensitive not in row


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
    """Upload is ``multipart/form-data``; the binary reaches the service untouched."""
    seen: dict[str, object] = {}

    async def _add_document(*, upload, data, **_kwargs):
        seen["filename"] = upload.filename
        seen["content_type"] = upload.content_type
        seen["content"] = await upload.read()
        seen["document_type"] = data.document_type.value
        return _document()

    mock_employee_service.add_document.side_effect = _add_document

    resp = await employee_client.post(
        f"{API_PREFIX}/employees/1/documents",
        data={"document_type": "pan_card"},
        files={"file": ("pan.pdf", b"%PDF-1.4", "application/pdf")},
        headers=super_admin_headers,
    )

    assert resp.status_code == 201
    body = resp.json()["data"]
    assert body["document_id"] == 5
    # Metadata only — the storage key is never exposed (contract §7 #34).
    assert "file_url" not in body
    assert seen == {
        "filename": "pan.pdf",
        "content_type": "application/pdf",
        "content": b"%PDF-1.4",
        "document_type": "pan_card",
    }


async def test_add_document_rejects_client_supplied_path(
    employee_client: AsyncClient, mock_employee_service: AsyncMock, super_admin_headers
) -> None:
    """A JSON body naming a file path is no longer an accepted upload at all."""
    resp = await employee_client.post(
        f"{API_PREFIX}/employees/1/documents",
        json={"document_type": "pan_card", "file_url": "../../etc/passwd"},
        headers=super_admin_headers,
    )
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "VALIDATION_ERROR"
    mock_employee_service.add_document.assert_not_awaited()


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
        data={"document_type": "pan_card"},
        files={"file": ("pan.pdf", b"%PDF-1.4", "application/pdf")},
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
    assert "file_url" not in resp.json()["data"][0]


async def test_download_document_streams_stored_file(
    employee_client: AsyncClient,
    mock_employee_service: AsyncMock,
    super_admin_headers,
    tmp_path,
) -> None:
    """The download route streams the stored bytes, not a client-supplied URL."""
    stored = tmp_path / "deadbeef.pdf"
    stored.write_bytes(b"%PDF-1.4 payload")
    mock_employee_service.open_document.return_value = DocumentDownload(
        path=stored,
        filename="pan.pdf",
        content_type="application/pdf",
        document=_document(),
    )
    resp = await employee_client.get(
        f"{API_PREFIX}/employees/1/documents/5", headers=super_admin_headers
    )
    assert resp.status_code == 200
    assert resp.content == b"%PDF-1.4 payload"
    assert resp.headers["content-type"] == "application/pdf"
    assert "pan.pdf" in resp.headers["content-disposition"]


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
