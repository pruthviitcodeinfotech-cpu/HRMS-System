"""Integration tests for the Shift Management router.

Exercises the real app + real auth/permission dependencies with only
``ShiftService`` mocked. Covers the happy-path shift CRUD / assignment / rotation /
weekly-off endpoints (as a super admin, who bypasses the feature-permission guards),
plus permission enforcement, unauthenticated access, and validation failures.

A module-local ``shift_app`` / ``shift_client`` fixture mounts the shift router and
overrides its service dependency, reusing the shared token/header fixtures from
:mod:`tests.conftest`.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.main import create_app
from app.modules.shift.router import get_shift_service
from app.modules.shift.router import router as shift_router
from app.modules.shift.schemas import (
    ShiftAssignmentListResponse,
    ShiftAssignmentSchema,
    ShiftDetailSchema,
    ShiftListResponse,
    ShiftResolveResponse,
    ShiftRotationResponse,
    ShiftSummarySchema,
    WeeklyOffListResponse,
    WeeklyOffSchema,
)
from tests.conftest import API_PREFIX

_NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Fixtures (module-local: mount the shift router + mock its service)
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_shift_service() -> AsyncMock:
    """An ``AsyncMock`` standing in for :class:`ShiftService`."""
    return AsyncMock()


@pytest.fixture
def shift_app():
    """The production app factory with the shift router mounted at the API prefix."""
    application = create_app()
    application.include_router(shift_router, prefix=API_PREFIX)
    return application


@pytest_asyncio.fixture
async def shift_client(shift_app, mock_shift_service: AsyncMock):
    """An async HTTP client bound to the app, with ``ShiftService`` mocked."""
    shift_app.dependency_overrides[get_shift_service] = lambda: mock_shift_service
    transport = ASGITransport(app=shift_app)
    async with AsyncClient(transport=transport, base_url="http://test") as http_client:
        yield http_client
    shift_app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Response builders
# ---------------------------------------------------------------------------


def _shift_detail() -> ShiftDetailSchema:
    return ShiftDetailSchema(
        shift_id=1,
        org_id=1,
        shift_name="Morning",
        shift_type="fixed",
        created_at=_NOW,
        updated_at=_NOW,
    )


def _shift_list() -> ShiftListResponse:
    summary = ShiftSummarySchema(
        shift_id=1, org_id=1, shift_name="Morning", shift_type="fixed", created_at=_NOW
    )
    return ShiftListResponse.build(items=[summary], page=1, page_size=25, total_records=1)


def _assignment() -> ShiftAssignmentSchema:
    return ShiftAssignmentSchema(
        assignment_id=1,
        org_id=1,
        employee_id=5,
        shift_id=1,
        effective_from=date(2026, 2, 1),
        created_at=_NOW,
        updated_at=_NOW,
    )


def _weekoff() -> WeeklyOffSchema:
    return WeeklyOffSchema(
        weekoff_id=1,
        employee_id=5,
        day_of_week=0,
        weekoff_type="week_off",
        updated_at=_NOW,
        created_at=_NOW,
    )


def _create_body() -> dict[str, object]:
    return {"shift_name": "Morning", "shift_type": "fixed"}


# ===========================================================================
# Happy path (super admin bypasses permission guards)
# ===========================================================================
async def test_list_shifts_200(
    shift_client: AsyncClient, mock_shift_service: AsyncMock, super_admin_headers
) -> None:
    mock_shift_service.list_shifts.return_value = _shift_list()
    resp = await shift_client.get(
        f"{API_PREFIX}/shifts?q=morn&page=1&page_size=25", headers=super_admin_headers
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["pagination"]["total_records"] == 1


async def test_create_shift_201(
    shift_client: AsyncClient, mock_shift_service: AsyncMock, super_admin_headers
) -> None:
    mock_shift_service.create_shift.return_value = _shift_detail()
    resp = await shift_client.post(
        f"{API_PREFIX}/shifts", json=_create_body(), headers=super_admin_headers
    )
    assert resp.status_code == 201
    assert resp.json()["data"]["shift_name"] == "Morning"


async def test_get_shift_200(
    shift_client: AsyncClient, mock_shift_service: AsyncMock, super_admin_headers
) -> None:
    mock_shift_service.get_shift.return_value = _shift_detail()
    resp = await shift_client.get(f"{API_PREFIX}/shifts/1", headers=super_admin_headers)
    assert resp.status_code == 200
    assert resp.json()["data"]["shift_id"] == 1


async def test_resolve_shift_200(
    shift_client: AsyncClient, mock_shift_service: AsyncMock, super_admin_headers
) -> None:
    """`/shifts/resolve` must match before `/shifts/{shift_id}`."""
    mock_shift_service.resolve_shift.return_value = ShiftResolveResponse(
        shift=None, is_weekly_off=True, is_working_day=False
    )
    resp = await shift_client.get(
        f"{API_PREFIX}/shifts/resolve?employee_id=5&date=2026-03-01", headers=super_admin_headers
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["is_weekly_off"] is True
    mock_shift_service.resolve_shift.assert_awaited_once()


async def test_update_shift_200(
    shift_client: AsyncClient, mock_shift_service: AsyncMock, super_admin_headers
) -> None:
    mock_shift_service.update_shift.return_value = _shift_detail()
    resp = await shift_client.put(
        f"{API_PREFIX}/shifts/1", json={"shift_name": "Evening"}, headers=super_admin_headers
    )
    assert resp.status_code == 200


async def test_delete_shift_204(
    shift_client: AsyncClient, mock_shift_service: AsyncMock, super_admin_headers
) -> None:
    mock_shift_service.delete_shift.return_value = None
    resp = await shift_client.delete(f"{API_PREFIX}/shifts/1", headers=super_admin_headers)
    assert resp.status_code == 204


async def test_assign_shift_201(
    shift_client: AsyncClient, mock_shift_service: AsyncMock, super_admin_headers
) -> None:
    mock_shift_service.assign_shift.return_value = _assignment()
    resp = await shift_client.post(
        f"{API_PREFIX}/shifts/1/assign",
        json={"employee_id": 5, "effective_from": "2026-02-01"},
        headers=super_admin_headers,
    )
    assert resp.status_code == 201
    assert resp.json()["data"]["assignment_id"] == 1


async def test_list_shift_assignments_200(
    shift_client: AsyncClient, mock_shift_service: AsyncMock, super_admin_headers
) -> None:
    mock_shift_service.list_assignments.return_value = ShiftAssignmentListResponse.build(
        items=[_assignment()], page=1, page_size=25, total_records=1
    )
    resp = await shift_client.get(
        f"{API_PREFIX}/shift-assignments?employee_id=5", headers=super_admin_headers
    )
    assert resp.status_code == 200
    assert len(resp.json()["data"]["items"]) == 1


async def test_generate_rotation_202(
    shift_client: AsyncClient, mock_shift_service: AsyncMock, super_admin_headers
) -> None:
    mock_shift_service.generate_rotation.return_value = ShiftRotationResponse(
        generated_count=3, generated_assignments=[]
    )
    resp = await shift_client.post(
        f"{API_PREFIX}/shift-rotations",
        json={
            "name": "Rot",
            "cadence": "daily",
            "shift_sequence": [1, 2],
            "start_date": "2026-02-01",
            "horizon_days": 3,
        },
        headers=super_admin_headers,
    )
    assert resp.status_code == 202
    assert resp.json()["data"]["generated_count"] == 3


async def test_get_weekly_offs_200(
    shift_client: AsyncClient, mock_shift_service: AsyncMock, super_admin_headers
) -> None:
    mock_shift_service.get_weekly_offs.return_value = WeeklyOffListResponse.build(
        items=[_weekoff()], page=1, page_size=25, total_records=1
    )
    resp = await shift_client.get(
        f"{API_PREFIX}/weekly-offs?employee_id=5", headers=super_admin_headers
    )
    assert resp.status_code == 200


async def test_set_weekly_off_200(
    shift_client: AsyncClient, mock_shift_service: AsyncMock, super_admin_headers
) -> None:
    mock_shift_service.set_weekly_off.return_value = _weekoff()
    resp = await shift_client.put(
        f"{API_PREFIX}/weekly-offs",
        json={"employee_id": 5, "day_of_week": 0, "weekoff_type": "week_off"},
        headers=super_admin_headers,
    )
    assert resp.status_code == 200


# ===========================================================================
# Authorization
# ===========================================================================
async def test_create_shift_forbidden_without_permission(
    shift_client: AsyncClient, make_access_token
) -> None:
    token = make_access_token(is_super_admin=False, permissions=[])
    resp = await shift_client.post(
        f"{API_PREFIX}/shifts",
        json=_create_body(),
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "AUTH_FORBIDDEN"


async def test_create_shift_allowed_with_permission(
    shift_client: AsyncClient, mock_shift_service: AsyncMock, make_access_token
) -> None:
    mock_shift_service.create_shift.return_value = _shift_detail()
    token = make_access_token(
        is_super_admin=False,
        permissions=[{"feature_key": "shift", "can_create": True, "can_read": True}],
    )
    resp = await shift_client.post(
        f"{API_PREFIX}/shifts",
        json=_create_body(),
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201


async def test_list_shifts_requires_authentication(shift_client: AsyncClient) -> None:
    resp = await shift_client.get(f"{API_PREFIX}/shifts")
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "AUTH_NOT_AUTHENTICATED"


# ===========================================================================
# Validation failures (422)
# ===========================================================================
async def test_create_shift_missing_name_422(
    shift_client: AsyncClient, super_admin_headers
) -> None:
    resp = await shift_client.post(
        f"{API_PREFIX}/shifts", json={"shift_type": "fixed"}, headers=super_admin_headers
    )
    assert resp.status_code == 422


async def test_assign_shift_missing_employee_422(
    shift_client: AsyncClient, super_admin_headers
) -> None:
    resp = await shift_client.post(
        f"{API_PREFIX}/shifts/1/assign",
        json={"effective_from": "2026-02-01"},
        headers=super_admin_headers,
    )
    assert resp.status_code == 422


async def test_set_weekly_off_both_targets_422(
    shift_client: AsyncClient, super_admin_headers
) -> None:
    resp = await shift_client.put(
        f"{API_PREFIX}/weekly-offs",
        json={"employee_id": 5, "department_id": 3, "day_of_week": 0},
        headers=super_admin_headers,
    )
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "VALIDATION_ERROR"


async def test_get_weekly_offs_both_targets_422(
    shift_client: AsyncClient, super_admin_headers
) -> None:
    """The query-DTO exactly-one validator surfaces as 422."""
    resp = await shift_client.get(
        f"{API_PREFIX}/weekly-offs?employee_id=5&department_id=3", headers=super_admin_headers
    )
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "VALIDATION_ERROR"


async def test_generate_rotation_empty_sequence_422(
    shift_client: AsyncClient, super_admin_headers
) -> None:
    resp = await shift_client.post(
        f"{API_PREFIX}/shift-rotations",
        json={
            "name": "Rot",
            "cadence": "daily",
            "shift_sequence": [],
            "start_date": "2026-02-01",
            "horizon_days": 3,
        },
        headers=super_admin_headers,
    )
    assert resp.status_code == 422
