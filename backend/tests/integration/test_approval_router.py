"""Integration tests for the Approval Management router.

Exercises the real app + real auth/permission dependencies with only
``ApprovalService`` mocked. Covers all happy path read, action, timeline,
and aggregate endpoints, plus authentication, permission enforcement,
scoping guards, and validation failures.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.core.dependencies.auth import assert_session_live
from app.main import create_app
from app.modules.approvals.router import get_approval_service
from app.modules.approvals.router import router as approvals_router
from app.modules.approvals.schemas import (
    ApprovalDetailsSchema,
    ApprovalListResponse,
    ApprovalPendingCountSchema,
    ApprovalRequestSchema,
    ApprovalStatusSchema,
    ApprovalTimelineEventSchema,
    BulkActionResponseSchema,
)
from tests.conftest import API_PREFIX

_NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Fixtures (module-local: mount approvals router + mock its service)
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_approval_service() -> AsyncMock:
    """An ``AsyncMock`` standing in for :class:`ApprovalService`."""
    service = AsyncMock()
    # ``BaseService.paginate`` is synchronous; an AsyncMock child would return a
    # coroutine and the router would serialise that instead of the page.
    service.paginate = MagicMock()
    return service


@pytest.fixture
def approval_app():
    """The production app factory with the approvals router mounted at the API prefix."""
    application = create_app()
    application.include_router(approvals_router, prefix=API_PREFIX)
    return application


@pytest_asyncio.fixture
async def approval_client(approval_app, mock_approval_service: AsyncMock):
    """An async HTTP client bound to the app, with ``ApprovalService`` mocked."""
    # The auth dependency re-validates the session against the DB on every request;
    # router tests exercise the HTTP layer without a database, so stub that check.
    approval_app.dependency_overrides[assert_session_live] = lambda: None
    approval_app.dependency_overrides[get_approval_service] = lambda: mock_approval_service
    transport = ASGITransport(app=approval_app)
    async with AsyncClient(transport=transport, base_url="http://test") as http_client:
        yield http_client
    approval_app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Response builders
# ---------------------------------------------------------------------------


def _approval_req() -> ApprovalRequestSchema:
    return ApprovalRequestSchema(
        id=1,
        org_id=1,
        request_type="leave",
        request_subtype="annual",
        reference_id=100,
        employee_id=5,
        status="pending",
        requested_at=_NOW,
        reviewed_at=None,
        reviewed_by=None,
        reject_remarks=None,
        created_at=_NOW,
    )


def _approval_list() -> ApprovalListResponse:
    return ApprovalListResponse.build(
        items=[_approval_req()], page=1, page_size=25, total_records=1
    )


def _approval_details() -> ApprovalDetailsSchema:
    return ApprovalDetailsSchema(
        approval=_approval_req(),
        source={"id": 100, "reason": "Holiday"},
    )


# ===========================================================================
# Happy path (super admin bypasses permission guards)
# ===========================================================================


async def test_list_approvals_200(
    approval_client: AsyncClient, mock_approval_service: AsyncMock, super_admin_headers
) -> None:
    mock_approval_service.approvals.search.return_value = [_approval_req()]
    mock_approval_service.approvals.search_count.return_value = 1
    mock_approval_service.paginate.return_value = _approval_list()

    resp = await approval_client.get(
        f"{API_PREFIX}/approvals?status=pending&page=1&page_size=25",
        headers=super_admin_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["pagination"]["total_records"] == 1


async def test_list_pending_approvals_200(
    approval_client: AsyncClient, mock_approval_service: AsyncMock, super_admin_headers
) -> None:
    mock_approval_service.list_pending_approvals.return_value = _approval_list()
    resp = await approval_client.get(
        f"{API_PREFIX}/approvals/pending", headers=super_admin_headers
    )
    assert resp.status_code == 200
    assert len(resp.json()["data"]["items"]) == 1


async def test_get_approval_history_200(
    approval_client: AsyncClient, mock_approval_service: AsyncMock, super_admin_headers
) -> None:
    mock_approval_service.get_approval_history.return_value = _approval_list()
    resp = await approval_client.get(
        f"{API_PREFIX}/approvals/history?request_type=leave", headers=super_admin_headers
    )
    assert resp.status_code == 200


async def test_get_approval_details_200(
    approval_client: AsyncClient, mock_approval_service: AsyncMock, super_admin_headers
) -> None:
    mock_approval_service.get_approval_details.return_value = _approval_details()
    resp = await approval_client.get(
        f"{API_PREFIX}/approvals/1", headers=super_admin_headers
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["approval"]["id"] == 1


async def test_get_approval_status_200(
    approval_client: AsyncClient, mock_approval_service: AsyncMock, super_admin_headers
) -> None:
    mock_approval_service.get_approval_status.return_value = ApprovalStatusSchema(
        status="pending"
    )
    resp = await approval_client.get(
        f"{API_PREFIX}/approvals/1/status", headers=super_admin_headers
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["status"] == "pending"


async def test_get_approval_timeline_200(
    approval_client: AsyncClient, mock_approval_service: AsyncMock, super_admin_headers
) -> None:
    mock_approval_service.get_approval_timeline.return_value = [
        ApprovalTimelineEventSchema(event="requested", at=_NOW, by=5)
    ]
    resp = await approval_client.get(
        f"{API_PREFIX}/approvals/1/timeline", headers=super_admin_headers
    )
    assert resp.status_code == 200
    assert len(resp.json()["data"]) == 1


async def test_approve_request_200(
    approval_client: AsyncClient, mock_approval_service: AsyncMock, super_admin_headers
) -> None:
    mock_approval_service.approve_request.return_value = _approval_req()
    resp = await approval_client.post(
        f"{API_PREFIX}/approvals/1/approve",
        json={"remarks": "Approved!"},
        headers=super_admin_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["id"] == 1


async def test_reject_request_200(
    approval_client: AsyncClient, mock_approval_service: AsyncMock, super_admin_headers
) -> None:
    mock_approval_service.reject_request.return_value = _approval_req()
    resp = await approval_client.post(
        f"{API_PREFIX}/approvals/1/reject",
        json={"reject_remarks": "Not approved."},
        headers=super_admin_headers,
    )
    assert resp.status_code == 200


async def test_bulk_approve_200(
    approval_client: AsyncClient, mock_approval_service: AsyncMock, super_admin_headers
) -> None:
    mock_approval_service.bulk_approve.return_value = [
        {"id": 1, "success": True, "error": None}
    ]
    resp = await approval_client.post(
        f"{API_PREFIX}/approvals/bulk-approve",
        json={"approval_ids": [1]},
        headers=super_admin_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["results"][0]["success"] is True


async def test_bulk_reject_200(
    approval_client: AsyncClient, mock_approval_service: AsyncMock, super_admin_headers
) -> None:
    mock_approval_service.bulk_reject.return_value = [
        {"id": 1, "success": True, "error": None}
    ]
    resp = await approval_client.post(
        f"{API_PREFIX}/approvals/bulk-reject",
        json={"approval_ids": [1], "reject_remarks": "Rejected all"},
        headers=super_admin_headers,
    )
    assert resp.status_code == 200


async def test_get_pending_approval_count_200(
    approval_client: AsyncClient, mock_approval_service: AsyncMock, super_admin_headers
) -> None:
    mock_approval_service.get_pending_approval_count.return_value = ApprovalPendingCountSchema(
        pending_count=1, by_request_type={"leave": 1}
    )
    resp = await approval_client.get(
        f"{API_PREFIX}/approvals/summary/pending-count", headers=super_admin_headers
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["pending_count"] == 1


async def test_get_my_pending_approvals_200(
    approval_client: AsyncClient, mock_approval_service: AsyncMock, super_admin_headers
) -> None:
    mock_approval_service.get_my_pending_approvals.return_value = _approval_list()
    resp = await approval_client.get(
        f"{API_PREFIX}/approvals/my-pending", headers=super_admin_headers
    )
    assert resp.status_code == 200


async def test_get_recent_decisions_200(
    approval_client: AsyncClient, mock_approval_service: AsyncMock, super_admin_headers
) -> None:
    mock_approval_service.get_recent_decisions.return_value = [_approval_req()]
    resp = await approval_client.get(
        f"{API_PREFIX}/approvals/recent?decision=approved", headers=super_admin_headers
    )
    assert resp.status_code == 200


# ===========================================================================
# Authorization and scope guards
# ===========================================================================


async def test_list_approvals_requires_authentication(approval_client: AsyncClient) -> None:
    resp = await approval_client.get(f"{API_PREFIX}/approvals")
    assert resp.status_code == 401


async def test_approve_request_forbidden_without_permission(
    approval_client: AsyncClient, make_access_token
) -> None:
    token = make_access_token(is_super_admin=False, permissions=[])
    resp = await approval_client.post(
        f"{API_PREFIX}/approvals/1/approve",
        json={"remarks": "ok"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


async def test_approve_request_allowed_with_permission(
    approval_client: AsyncClient, mock_approval_service: AsyncMock, make_access_token
) -> None:
    mock_approval_service.approvals.get_by_id_in_org.return_value = _approval_req()
    mock_approval_service.approve_request.return_value = _approval_req()
    token = make_access_token(
        is_super_admin=False,
        permissions=[{"feature_key": "approval", "can_edit": True, "can_read": True}],
        branch_ids=[10],
        department_ids=[20],
    )
    # Mock employee branch/dept lookup to match the token
    mock_approval_service.employees.get_active_by_id.return_value = SimpleNamespace(
        employee_id=5, org_id=1, master_branch_id=10, dept_id=20
    )

    resp = await approval_client.post(
        f"{API_PREFIX}/approvals/1/approve",
        json={"remarks": "ok"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200


async def test_approve_request_out_of_scope_forbidden(
    approval_client: AsyncClient, mock_approval_service: AsyncMock, make_access_token
) -> None:
    mock_approval_service.approvals.get_by_id_in_org.return_value = _approval_req()
    token = make_access_token(
        is_super_admin=False,
        permissions=[{"feature_key": "approval", "can_edit": True, "can_read": True}],
        branch_ids=[10],
        department_ids=[20],
    )
    # Subject employee belongs to branch 999 (not 10)
    mock_approval_service.employees.get_active_by_id.return_value = SimpleNamespace(
        employee_id=5, org_id=1, master_branch_id=999, dept_id=20
    )

    resp = await approval_client.post(
        f"{API_PREFIX}/approvals/1/approve",
        json={"remarks": "ok"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "APPROVAL_FORBIDDEN_SCOPE"


# ===========================================================================
# Validation failures (422)
# ===========================================================================


async def test_approve_request_invalid_remarks_422(
    approval_client: AsyncClient, super_admin_headers
) -> None:
    resp = await approval_client.post(
        f"{API_PREFIX}/approvals/1/approve",
        json={"remarks": 1234},  # Remarks should be a string or null
        headers=super_admin_headers,
    )
    assert resp.status_code == 422


async def test_reject_request_missing_body_422(
    approval_client: AsyncClient, super_admin_headers
) -> None:
    resp = await approval_client.post(
        f"{API_PREFIX}/approvals/1/reject",
        json={},  # Reject remarks are mandatory
        headers=super_admin_headers,
    )
    assert resp.status_code == 422
