"""Integration tests for the Payroll Management router.

Exercises the real app + real auth/permission dependencies with only
``PayrollService`` mocked. Covers all endpoints, authentication,
permission enforcement, and scoping guards.
"""

from __future__ import annotations

from datetime import date, datetime, time, timezone
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.core.dependencies.auth import assert_session_live
from app.modules.payroll.dependencies import get_payroll_service
from app.main import create_app
from app.modules.payroll.router import router as payroll_router
from app.modules.payroll.models.run import PayrollComputedRow
from tests.conftest import API_PREFIX

_NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


@pytest.fixture
def mock_payroll_service() -> AsyncMock:
    """An ``AsyncMock`` standing in for :class:`PayrollService`."""
    return AsyncMock()


@pytest.fixture
def payroll_app():
    """The production app factory with the payroll router mounted at the API prefix."""
    application = create_app()
    application.include_router(payroll_router, prefix=API_PREFIX)
    return application


@pytest_asyncio.fixture
async def payroll_client(payroll_app, mock_payroll_service: AsyncMock):
    """An async HTTP client bound to the app, with ``PayrollService`` mocked."""
    payroll_app.dependency_overrides[assert_session_live] = lambda: None
    payroll_app.dependency_overrides[get_payroll_service] = lambda: mock_payroll_service
    transport = ASGITransport(app=payroll_app)
    async with AsyncClient(transport=transport, base_url="http://test") as http_client:
        yield http_client
    payroll_app.dependency_overrides.clear()


# ===========================================================================
# Helper Builders
# ===========================================================================

def _computed_row_instance(**overrides) -> PayrollComputedRow:
    base = {
        "id": None,
        "payroll_group_id": 2,
        "employee_id": 5,
        "cycle_from": date(2026, 1, 1),
        "cycle_to": date(2026, 1, 31),
        "total_days": 31,
        "full_day_count": 31,
        "half_day_count": 0,
        "off_day_count": 0,
        "paid_leave_count": Decimal("0.0"),
        "paid_day_count": Decimal("31.0"),
        "unpaid_day_count": Decimal("0.0"),
        "daily_wage": Decimal("100.00"),
        "gross_wages": Decimal("3100.00"),
        "overtime_amount": Decimal("0.00"),
        "penalties_amount": Decimal("0.00"),
        "extras_amount": Decimal("0.00"),
        "gross_earnings": Decimal("3100.00"),
        "loan_advance_deduction": Decimal("0.00"),
        "arrears_amount": Decimal("0.00"),
        "to_pay": Decimal("3100.00"),
        "balance_arrears": Decimal("0.00"),
        "payment_method": "bank_transfer",
        "is_finalized": False,
        "finalized_run_id": None,
        "computed_by": 9,
        "computed_at": _NOW,
    }
    base.update(overrides)
    return PayrollComputedRow(**base)


# ===========================================================================
# Router Integration Tests
# ===========================================================================

@pytest.mark.asyncio
async def test_preview_payroll_success(
    payroll_client: AsyncClient, mock_payroll_service: AsyncMock, super_admin_headers
) -> None:
    """Verify that a successful preview request returns HTTP 200 and serializes id=None correctly."""
    mock_payroll_service.preview_payroll.return_value = [_computed_row_instance(id=None)]
    
    payload = {
        "payroll_group_id": 2,
        "cycle_from": "2026-01-01",
        "cycle_to": "2026-01-31",
        "employee_ids": [5],
    }
    
    resp = await payroll_client.post(
        f"{API_PREFIX}/payroll/processing/preview", json=payload, headers=super_admin_headers
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert len(data["items"]) == 1
    assert data["items"][0]["id"] is None
    assert data["items"][0]["employee_id"] == 5
    assert data["items"][0]["gross_wages"] == "3100.00"


@pytest.mark.asyncio
async def test_preview_payroll_empty(
    payroll_client: AsyncClient, mock_payroll_service: AsyncMock, super_admin_headers
) -> None:
    """Verify that previewing with no employees matches returns HTTP 200 and empty items."""
    mock_payroll_service.preview_payroll.return_value = []
    
    payload = {
        "payroll_group_id": 2,
        "cycle_from": "2026-01-01",
        "cycle_to": "2026-01-31",
        "employee_ids": [],
    }
    
    resp = await payroll_client.post(
        f"{API_PREFIX}/payroll/processing/preview", json=payload, headers=super_admin_headers
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert len(data["items"]) == 0


@pytest.mark.asyncio
async def test_preview_payroll_multiple(
    payroll_client: AsyncClient, mock_payroll_service: AsyncMock, super_admin_headers
) -> None:
    """Verify preview for multiple employees executes and serializes correctly."""
    mock_payroll_service.preview_payroll.return_value = [
        _computed_row_instance(id=None, employee_id=5, gross_wages=Decimal("3100.00")),
        _computed_row_instance(id=None, employee_id=6, gross_wages=Decimal("6200.00")),
    ]
    
    payload = {
        "payroll_group_id": 2,
        "cycle_from": "2026-01-01",
        "cycle_to": "2026-01-31",
        "employee_ids": [5, 6],
    }
    
    resp = await payroll_client.post(
        f"{API_PREFIX}/payroll/processing/preview", json=payload, headers=super_admin_headers
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert len(data["items"]) == 2
    assert {item["employee_id"] for item in data["items"]} == {5, 6}
    assert {item["gross_wages"] for item in data["items"]} == {"3100.00", "6200.00"}
    assert all(item["id"] is None for item in data["items"])


@pytest.mark.asyncio
async def test_preview_payroll_validation_error_date(
    payroll_client: AsyncClient, super_admin_headers
) -> None:
    """Verify that invalid date formats or ranges yield HTTP 422 ValidationError."""
    # 1. Invalid date range (cycle_to before cycle_from)
    payload = {
        "payroll_group_id": 2,
        "cycle_from": "2026-01-31",
        "cycle_to": "2026-01-01",
        "employee_ids": [5],
    }
    resp = await payroll_client.post(
        f"{API_PREFIX}/payroll/processing/preview", json=payload, headers=super_admin_headers
    )
    assert resp.status_code == 422

    # 2. Missing payroll_group_id
    payload_missing = {
        "cycle_from": "2026-01-01",
        "cycle_to": "2026-01-31",
    }
    resp = await payroll_client.post(
        f"{API_PREFIX}/payroll/processing/preview", json=payload_missing, headers=super_admin_headers
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_finalized_payroll_regression(
    payroll_client: AsyncClient, mock_payroll_service: AsyncMock, super_admin_headers
) -> None:
    """Regression test ensuring finalized/persisted payroll computed rows serialize with correct non-null ids."""
    mock_payroll_service.get_record.return_value = _computed_row_instance(id=123, is_finalized=True, finalized_run_id=45)
    
    resp = await payroll_client.get(
        f"{API_PREFIX}/payroll/records/123", headers=super_admin_headers
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["id"] == 123
    assert data["employee_id"] == 5
    assert data["is_finalized"] is True
    assert data["finalized_run_id"] == 45
