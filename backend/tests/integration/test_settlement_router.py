"""Integration tests for the Settlement Management router."""

from __future__ import annotations

import datetime
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.core.dependencies.auth import assert_session_live
from app.main import create_app
from app.modules.settlements.constants import (
    LoanAdvanceStatus,
    LoanAdvanceType,
    TransactionSource,
    TransactionType,
)
from app.modules.settlements.dependencies import get_settlement_service
from app.modules.settlements.router import router as settlements_router
from app.modules.settlements.schemas import (
    ArrearsTransactionListResponse,
    ArrearsTransactionSchema,
    EmployeeArrearsListResponse,
    EmployeeArrearsSchema,
    LoanAdvanceListResponse,
    LoanAdvanceSchema,
    LoanAdvanceTransactionListResponse,
    LoanAdvanceTransactionSchema,
    SettlementHistoryResponse,
)
from tests.conftest import API_PREFIX

_DATE = datetime.date(2026, 1, 1)
_NOW = datetime.datetime(2026, 1, 1, 12, 0, 0)


@pytest.fixture
def mock_settlement_service() -> AsyncMock:
    """Mock stand-in for SettlementService."""
    return AsyncMock()


@pytest.fixture
def settlement_app():
    """Mounts the settlements router on the production app factory."""
    application = create_app()
    application.include_router(settlements_router, prefix=API_PREFIX)
    return application


@pytest_asyncio.fixture
async def settlement_client(settlement_app, mock_settlement_service: AsyncMock):
    """An async HTTP client bound to the app with the settlement service mocked."""
    # The auth dependency re-validates the session against the DB on every request;
    # router tests exercise the HTTP layer without a database, so stub that check.
    settlement_app.dependency_overrides[assert_session_live] = lambda: None
    settlement_app.dependency_overrides[get_settlement_service] = lambda: mock_settlement_service
    transport = ASGITransport(app=settlement_app)
    async with AsyncClient(transport=transport, base_url="http://test") as http_client:
        yield http_client
    settlement_app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Response Builders
# ---------------------------------------------------------------------------


def _loan_detail() -> LoanAdvanceSchema:
    return LoanAdvanceSchema(
        id=1,
        org_id=10,
        employee_id=42,
        name="Wedding Advance",
        type=LoanAdvanceType.ADVANCE,
        principal_amount=Decimal("5000.00"),
        monthly_installment=Decimal("500.00"),
        total_debit=Decimal("0.00"),
        outstanding_amount=Decimal("5000.00"),
        transaction_date=_DATE,
        status=LoanAdvanceStatus.ACTIVE,
        comment="No interest",
        created_by=1,
        updated_by=None,
        created_at=_NOW,
        updated_at=_NOW,
    )


def _loan_tx_detail() -> LoanAdvanceTransactionSchema:
    return LoanAdvanceTransactionSchema(
        id=2,
        org_id=10,
        loan_advance_id=1,
        employee_id=42,
        transaction_date=_DATE,
        transaction_type=TransactionType.CREDIT,
        amount=Decimal("5000.00"),
        installment_amount=None,
        type_label=LoanAdvanceType.ADVANCE,
        comment="Initial credit",
        source=TransactionSource.MANUAL,
        payroll_run_id=None,
        created_by=1,
        created_at=_NOW,
    )


def _arrears_detail() -> EmployeeArrearsSchema:
    return EmployeeArrearsSchema(
        id=5,
        org_id=10,
        employee_id=42,
        arrears_created=Decimal("1500.00"),
        arrears_paid=Decimal("500.00"),
        outstanding_arrears=Decimal("1000.00"),
        created_at=_NOW,
        updated_at=_NOW,
    )


def _arrears_tx_detail() -> ArrearsTransactionSchema:
    return ArrearsTransactionSchema(
        id=6,
        org_id=10,
        employee_arrears_id=5,
        employee_id=42,
        transaction_date=_DATE,
        transaction_type=TransactionType.CREDIT,
        amount=Decimal("1500.00"),
        outstanding_before=Decimal("0.00"),
        outstanding_after=Decimal("1500.00"),
        comment="Salary adjustments",
        source=TransactionSource.MANUAL,
        payroll_run_id=None,
        created_by=1,
        created_at=_NOW,
    )


# ===========================================================================
# Endpoints Integration Tests (Happy Path)
# ===========================================================================


@pytest.mark.asyncio
async def test_create_loan_advance_201(
    settlement_client: AsyncClient, mock_settlement_service: AsyncMock, super_admin_headers
) -> None:
    mock_settlement_service.create_loan_advance.return_value = _loan_detail()
    payload = {
        "employee_id": 42,
        "name": "Wedding Advance",
        "type": "advance",
        "principal_amount": "5000.00",
        "monthly_installment": "500.00",
        "transaction_date": "2026-01-01",
    }
    resp = await settlement_client.post(
        f"{API_PREFIX}/loans-advances", json=payload, headers=super_admin_headers
    )
    assert resp.status_code == 201
    assert resp.json()["data"]["name"] == "Wedding Advance"


@pytest.mark.asyncio
async def test_search_loans_advances_200(
    settlement_client: AsyncClient, mock_settlement_service: AsyncMock, super_admin_headers
) -> None:
    mock_settlement_service.search_loans_advances.return_value = LoanAdvanceListResponse.build(
        items=[_loan_detail()],
        page=1,
        page_size=20,
        total_records=1,
    )
    resp = await settlement_client.get(
        f"{API_PREFIX}/loans-advances?employee_id=42&page=1&page_size=20",
        headers=super_admin_headers,
    )
    assert resp.status_code == 200
    assert len(resp.json()["data"]["items"]) == 1


@pytest.mark.asyncio
async def test_get_loan_advance_200(
    settlement_client: AsyncClient, mock_settlement_service: AsyncMock, super_admin_headers
) -> None:
    mock_settlement_service.get_loan_advance.return_value = _loan_detail()
    mock_settlement_service.list_loan_advance_transactions.return_value = (
        LoanAdvanceTransactionListResponse.build(
            items=[_loan_tx_detail()],
            page=1,
            page_size=20,
            total_records=1,
        )
    )
    resp = await settlement_client.get(
        f"{API_PREFIX}/loans-advances/1", headers=super_admin_headers
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["id"] == 1
    assert len(resp.json()["data"]["transactions"]) == 1


@pytest.mark.asyncio
async def test_update_loan_advance_200(
    settlement_client: AsyncClient, mock_settlement_service: AsyncMock, super_admin_headers
) -> None:
    mock_settlement_service.update_loan_advance.return_value = _loan_detail()
    resp = await settlement_client.patch(
        f"{API_PREFIX}/loans-advances/1",
        json={"name": "Updated Name"},
        headers=super_admin_headers,
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_close_loan_advance_200(
    settlement_client: AsyncClient, mock_settlement_service: AsyncMock, super_admin_headers
) -> None:
    mock_settlement_service.close_loan_advance.return_value = _loan_detail()
    resp = await settlement_client.post(
        f"{API_PREFIX}/loans-advances/1/close", headers=super_admin_headers
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_delete_loan_advance_204(
    settlement_client: AsyncClient, mock_settlement_service: AsyncMock, super_admin_headers
) -> None:
    mock_settlement_service.delete_loan_advance.return_value = None
    resp = await settlement_client.delete(
        f"{API_PREFIX}/loans-advances/1", headers=super_admin_headers
    )
    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_add_loan_advance_transaction_201(
    settlement_client: AsyncClient, mock_settlement_service: AsyncMock, super_admin_headers
) -> None:
    mock_settlement_service.add_loan_advance_transaction.return_value = _loan_tx_detail()
    payload = {
        "transaction_date": "2026-01-01",
        "transaction_type": "credit",
        "amount": "5000.00",
        "type_label": "advance",
    }
    resp = await settlement_client.post(
        f"{API_PREFIX}/loans-advances/1/transactions", json=payload, headers=super_admin_headers
    )
    assert resp.status_code == 201


@pytest.mark.asyncio
async def test_list_loan_advance_transactions_200(
    settlement_client: AsyncClient, mock_settlement_service: AsyncMock, super_admin_headers
) -> None:
    mock_settlement_service.list_loan_advance_transactions.return_value = (
        LoanAdvanceTransactionListResponse.build(
            items=[_loan_tx_detail()],
            page=1,
            page_size=20,
            total_records=1,
        )
    )
    resp = await settlement_client.get(
        f"{API_PREFIX}/loans-advances/1/transactions?page=1&page_size=20",
        headers=super_admin_headers,
    )
    assert resp.status_code == 200
    assert len(resp.json()["data"]["items"]) == 1


@pytest.mark.asyncio
async def test_get_employee_arrears_200(
    settlement_client: AsyncClient, mock_settlement_service: AsyncMock, super_admin_headers
) -> None:
    mock_settlement_service.get_employee_arrears.return_value = _arrears_detail()
    resp = await settlement_client.get(
        f"{API_PREFIX}/employees/42/arrears", headers=super_admin_headers
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["id"] == 5


@pytest.mark.asyncio
async def test_list_employee_arrears_200(
    settlement_client: AsyncClient, mock_settlement_service: AsyncMock, super_admin_headers
) -> None:
    mock_settlement_service.list_employee_arrears.return_value = EmployeeArrearsListResponse.build(
        items=[_arrears_detail()],
        page=1,
        page_size=20,
        total_records=1,
    )
    resp = await settlement_client.get(
        f"{API_PREFIX}/arrears?page=1&page_size=20", headers=super_admin_headers
    )
    assert resp.status_code == 200
    assert len(resp.json()["data"]["items"]) == 1


@pytest.mark.asyncio
async def test_add_arrears_transaction_201(
    settlement_client: AsyncClient, mock_settlement_service: AsyncMock, super_admin_headers
) -> None:
    mock_settlement_service.add_arrears_transaction.return_value = _arrears_tx_detail()
    payload = {
        "transaction_date": "2026-01-01",
        "transaction_type": "credit",
        "amount": "1500.00",
    }
    resp = await settlement_client.post(
        f"{API_PREFIX}/employees/42/arrears/transactions", json=payload, headers=super_admin_headers
    )
    assert resp.status_code == 201


@pytest.mark.asyncio
async def test_list_arrears_transactions_200(
    settlement_client: AsyncClient, mock_settlement_service: AsyncMock, super_admin_headers
) -> None:
    mock_settlement_service.list_arrears_transactions.return_value = (
        ArrearsTransactionListResponse.build(
            items=[_arrears_tx_detail()],
            page=1,
            page_size=20,
            total_records=1,
        )
    )
    resp = await settlement_client.get(
        f"{API_PREFIX}/employees/42/arrears/transactions?page=1&page_size=20",
        headers=super_admin_headers,
    )
    assert resp.status_code == 200
    assert len(resp.json()["data"]["items"]) == 1


@pytest.mark.asyncio
async def test_get_settlement_history_200(
    settlement_client: AsyncClient, mock_settlement_service: AsyncMock, super_admin_headers
) -> None:
    mock_settlement_service.get_settlement_history.return_value = SettlementHistoryResponse.build(
        items=[],
        page=1,
        page_size=20,
        total_records=0,
    )
    resp = await settlement_client.get(
        f"{API_PREFIX}/employees/42/settlement-history?page=1&page_size=20",
        headers=super_admin_headers,
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_get_settlement_statement_200(
    settlement_client: AsyncClient, mock_settlement_service: AsyncMock, super_admin_headers
) -> None:
    mock_settlement_service.get_settlement_statement.return_value = {
        "employee_id": 42,
        "org_id": 10,
        "loans_advances": [],
        "total_outstanding_loans_advances": Decimal("0.00"),
        "arrears": None,
        "total_outstanding_arrears": Decimal("0.00"),
        "ledger": [],
    }
    resp = await settlement_client.get(
        f"{API_PREFIX}/employees/42/settlement-statement", headers=super_admin_headers
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_download_settlement_statement_200(
    settlement_client: AsyncClient, mock_settlement_service: AsyncMock, super_admin_headers
) -> None:
    mock_settlement_service.get_settlement_statement.return_value = {
        "employee_id": 42,
        "org_id": 10,
        "loans_advances": [],
        "total_outstanding_loans_advances": Decimal("0.00"),
        "arrears": None,
        "total_outstanding_arrears": Decimal("0.00"),
        "ledger": [],
    }
    resp = await settlement_client.get(
        f"{API_PREFIX}/employees/42/settlement-statement/download", headers=super_admin_headers
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"


@pytest.mark.asyncio
async def test_get_settlement_summary_200(
    settlement_client: AsyncClient, mock_settlement_service: AsyncMock, super_admin_headers
) -> None:
    mock_settlement_service.get_settlement_summary.return_value = {
        "total_active_loans_advances": Decimal("0.00"),
        "total_outstanding_loans_advances": Decimal("0.00"),
        "total_outstanding_arrears": Decimal("0.00"),
        "count_active": 0,
    }
    resp = await settlement_client.get(
        f"{API_PREFIX}/settlements/summary", headers=super_admin_headers
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_preview_ff_settlement_200(
    settlement_client: AsyncClient, mock_settlement_service: AsyncMock, super_admin_headers
) -> None:
    mock_settlement_service.calculate_ff_settlement.return_value = {"calculated": True}
    resp = await settlement_client.get(
        f"{API_PREFIX}/employees/42/settlement-preview", headers=super_admin_headers
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_approve_ff_settlement_200(
    settlement_client: AsyncClient, mock_settlement_service: AsyncMock, super_admin_headers
) -> None:
    mock_settlement_service.approve_ff_settlement.return_value = {"approved": True}
    resp = await settlement_client.post(
        f"{API_PREFIX}/employees/42/settlement-approve", headers=super_admin_headers
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_finalize_ff_settlement_200(
    settlement_client: AsyncClient, mock_settlement_service: AsyncMock, super_admin_headers
) -> None:
    mock_settlement_service.finalize_ff_settlement.return_value = {"finalized": True}
    resp = await settlement_client.post(
        f"{API_PREFIX}/employees/42/settlement-finalize", headers=super_admin_headers
    )
    assert resp.status_code == 200


# ===========================================================================
# Authorization and Validation Errors
# ===========================================================================


@pytest.mark.asyncio
async def test_create_loan_advance_forbidden(
    settlement_client: AsyncClient, make_access_token
) -> None:
    token = make_access_token(is_super_admin=False, permissions=[])
    payload = {
        "employee_id": 42,
        "name": "Wedding Advance",
        "type": "advance",
        "principal_amount": "5000.00",
        "monthly_installment": "500.00",
        "transaction_date": "2026-01-01",
    }
    resp = await settlement_client.post(
        f"{API_PREFIX}/loans-advances",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


# ===========================================================================
# Service Exception Handling Tests
# ===========================================================================


@pytest.mark.asyncio
async def test_get_loan_advance_not_found_404(
    settlement_client: AsyncClient, mock_settlement_service: AsyncMock, super_admin_headers
) -> None:
    from app.modules.settlements.exceptions import LoanAdvanceNotFoundException

    mock_settlement_service.get_loan_advance.side_effect = LoanAdvanceNotFoundException()
    resp = await settlement_client.get(
        f"{API_PREFIX}/loans-advances/999", headers=super_admin_headers
    )
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "LOAN_ADVANCE_NOT_FOUND"


@pytest.mark.asyncio
async def test_update_loan_advance_closed_409(
    settlement_client: AsyncClient, mock_settlement_service: AsyncMock, super_admin_headers
) -> None:
    from app.modules.settlements.exceptions import LoanAdvanceClosedException

    mock_settlement_service.update_loan_advance.side_effect = LoanAdvanceClosedException()
    resp = await settlement_client.patch(
        f"{API_PREFIX}/loans-advances/1",
        json={"name": "New Name"},
        headers=super_admin_headers,
    )
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "LOAN_ADVANCE_CLOSED"


@pytest.mark.asyncio
async def test_delete_loan_advance_has_transactions_409(
    settlement_client: AsyncClient, mock_settlement_service: AsyncMock, super_admin_headers
) -> None:
    from app.modules.settlements.exceptions import LoanAdvanceHasTransactionsException

    mock_settlement_service.delete_loan_advance.side_effect = LoanAdvanceHasTransactionsException()
    resp = await settlement_client.delete(
        f"{API_PREFIX}/loans-advances/1", headers=super_admin_headers
    )
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "LOAN_ADVANCE_HAS_TRANSACTIONS"


@pytest.mark.asyncio
async def test_get_employee_arrears_not_found_404(
    settlement_client: AsyncClient, mock_settlement_service: AsyncMock, super_admin_headers
) -> None:
    from app.modules.settlements.exceptions import ArrearsNotFoundException

    mock_settlement_service.get_employee_arrears.side_effect = ArrearsNotFoundException()
    resp = await settlement_client.get(
        f"{API_PREFIX}/employees/999/arrears", headers=super_admin_headers
    )
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "ARREARS_NOT_FOUND"


@pytest.mark.asyncio
async def test_add_arrears_transaction_insufficient_409(
    settlement_client: AsyncClient, mock_settlement_service: AsyncMock, super_admin_headers
) -> None:
    from app.modules.settlements.exceptions import InsufficientArrearsException

    mock_settlement_service.add_arrears_transaction.side_effect = InsufficientArrearsException()
    payload = {
        "transaction_date": "2026-01-01",
        "transaction_type": "debit",
        "amount": "1000.00",
    }
    resp = await settlement_client.post(
        f"{API_PREFIX}/employees/42/arrears/transactions", json=payload, headers=super_admin_headers
    )
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "INSUFFICIENT_ARREARS"


@pytest.mark.asyncio
async def test_create_loan_advance_employee_not_found_404(
    settlement_client: AsyncClient, mock_settlement_service: AsyncMock, super_admin_headers
) -> None:
    from app.modules.settlements.exceptions import EmployeeNotFoundException

    mock_settlement_service.create_loan_advance.side_effect = EmployeeNotFoundException()
    payload = {
        "employee_id": 999,
        "name": "Wedding Advance",
        "type": "advance",
        "principal_amount": "5000.00",
        "monthly_installment": "500.00",
        "transaction_date": "2026-01-01",
    }
    resp = await settlement_client.post(
        f"{API_PREFIX}/loans-advances", json=payload, headers=super_admin_headers
    )
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "EMPLOYEE_NOT_FOUND"


@pytest.mark.asyncio
async def test_create_loan_advance_invalid_transaction_422(
    settlement_client: AsyncClient, mock_settlement_service: AsyncMock, super_admin_headers
) -> None:
    from app.modules.settlements.exceptions import InvalidTransactionException

    mock_settlement_service.create_loan_advance.side_effect = InvalidTransactionException()
    payload = {
        "employee_id": 42,
        "name": "Wedding Advance",
        "type": "advance",
        "principal_amount": "5000.00",
        "monthly_installment": "500.00",
        "transaction_date": "2026-01-01",
    }
    resp = await settlement_client.post(
        f"{API_PREFIX}/loans-advances", json=payload, headers=super_admin_headers
    )
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "INVALID_TRANSACTION"


# ===========================================================================
# Input Validation / Schema Errors (422)
# ===========================================================================


@pytest.mark.asyncio
async def test_create_loan_advance_missing_fields_422(
    settlement_client: AsyncClient, super_admin_headers
) -> None:
    # Missing principal_amount
    payload = {
        "employee_id": 42,
        "name": "Wedding Advance",
        "type": "advance",
        "monthly_installment": "500.00",
        "transaction_date": "2026-01-01",
    }
    resp = await settlement_client.post(
        f"{API_PREFIX}/loans-advances", json=payload, headers=super_admin_headers
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_loan_advance_invalid_types_422(
    settlement_client: AsyncClient, super_admin_headers
) -> None:
    # principal_amount is not a decimal number string
    payload = {
        "employee_id": 42,
        "name": "Wedding Advance",
        "type": "advance",
        "principal_amount": "abc",
        "monthly_installment": "500.00",
        "transaction_date": "2026-01-01",
    }
    resp = await settlement_client.post(
        f"{API_PREFIX}/loans-advances", json=payload, headers=super_admin_headers
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_search_loans_advances_invalid_pagination_422(
    settlement_client: AsyncClient, super_admin_headers
) -> None:
    # page_size > 200 (max allowed limit)
    resp = await settlement_client.get(
        f"{API_PREFIX}/loans-advances?page_size=250", headers=super_admin_headers
    )
    assert resp.status_code == 422


# ===========================================================================
# Scope & Tenant Isolation / Authorization Checks
# ===========================================================================


@pytest.mark.asyncio
async def test_search_loans_advances_no_auth_401(settlement_client: AsyncClient) -> None:
    resp = await settlement_client.get(f"{API_PREFIX}/loans-advances")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_search_loans_advances_unresolved_tenant_400(
    settlement_client: AsyncClient, make_access_token
) -> None:
    # org_id is None, triggering TENANT_UNRESOLVED
    token = make_access_token(is_super_admin=True, org_id=None)
    resp = await settlement_client.get(
        f"{API_PREFIX}/loans-advances", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "TENANT_UNRESOLVED"
