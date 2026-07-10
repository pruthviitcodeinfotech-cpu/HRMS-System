"""Unit tests for the Settlement Management Service layer."""

from __future__ import annotations

import datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.modules.settlements.exceptions import (
    ArrearsNotFoundException,
    EmployeeNotFoundException,
    InsufficientArrearsException,
    InvalidTransactionException,
    LoanAdvanceClosedException,
    LoanAdvanceHasTransactionsException,
    LoanAdvanceNotFoundException,
)
from app.modules.settlements.models import (
    EmployeeArrears,
    EmployeeLoanAdvance,
)
from app.modules.settlements.schemas import (
    LoanAdvanceSearchQuery,
    SettlementStatementQuery,
)
from app.modules.settlements.service import SettlementService


@pytest.fixture
def mock_session() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def settlement_service(mock_session: AsyncMock) -> SettlementService:
    svc = SettlementService(mock_session)
    svc.loans_advances = AsyncMock()
    svc.loan_transactions = AsyncMock()
    svc.arrears = AsyncMock()
    svc.arrears_transactions = AsyncMock()
    svc.settlement_coords = AsyncMock()
    svc.audit = AsyncMock()
    return svc


# --- Helper to mock Employee query response ---
def mock_employee_exists(session: AsyncMock, exists: bool = True) -> None:
    mock_result = MagicMock()
    if exists:
        emp = MagicMock()
        emp.employee_id = 42
        emp.employee_name = "John Doe"
        mock_result.scalar_one_or_none.return_value = emp
    else:
        mock_result.scalar_one_or_none.return_value = None
    session.execute.return_value = mock_result


# --- 1. Employee Loan & Advance Service Tests ----------------------------


@pytest.mark.asyncio
async def test_create_loan_advance_success(
    settlement_service: SettlementService, mock_session: AsyncMock
) -> None:
    mock_employee_exists(mock_session, exists=True)
    loan_data = {
        "employee_id": 42,
        "name": "Festival Advance",
        "type": "advance",
        "principal_amount": Decimal("10000.00"),
        "monthly_installment": Decimal("1000.00"),
        "transaction_date": datetime.date(2026, 7, 10),
        "comment": "Eid festival advance",
    }
    created_loan = EmployeeLoanAdvance(
        id=1,
        org_id=10,
        employee_id=42,
        name="Festival Advance",
        type="advance",
        principal_amount=Decimal("10000.00"),
        monthly_installment=Decimal("1000.00"),
    )
    settlement_service.loans_advances.create.return_value = created_loan

    res = await settlement_service.create_loan_advance(org_id=10, data=loan_data, user_id=101)

    assert res == created_loan
    settlement_service.loans_advances.create.assert_called_once()
    settlement_service.audit.record.assert_called_once()


@pytest.mark.asyncio
async def test_create_loan_advance_employee_not_found(
    settlement_service: SettlementService, mock_session: AsyncMock
) -> None:
    mock_employee_exists(mock_session, exists=False)
    loan_data = {
        "employee_id": 999,
        "name": "Festival Advance",
        "type": "advance",
        "principal_amount": Decimal("10000.00"),
        "monthly_installment": Decimal("1000.00"),
        "transaction_date": datetime.date(2026, 7, 10),
    }

    with pytest.raises(EmployeeNotFoundException):
        await settlement_service.create_loan_advance(org_id=10, data=loan_data, user_id=101)


@pytest.mark.asyncio
async def test_create_loan_advance_invalid_amounts(
    settlement_service: SettlementService, mock_session: AsyncMock
) -> None:
    mock_employee_exists(mock_session, exists=True)
    # Case 1: negative principal
    with pytest.raises(InvalidTransactionException):
        await settlement_service.create_loan_advance(
            org_id=10,
            data={
                "employee_id": 42,
                "name": "Festival Advance",
                "type": "advance",
                "principal_amount": Decimal("-1000.00"),
                "monthly_installment": Decimal("100.00"),
                "transaction_date": datetime.date(2026, 7, 10),
            },
            user_id=101,
        )

    # Case 2: monthly_installment > principal
    with pytest.raises(InvalidTransactionException):
        await settlement_service.create_loan_advance(
            org_id=10,
            data={
                "employee_id": 42,
                "name": "Festival Advance",
                "type": "advance",
                "principal_amount": Decimal("1000.00"),
                "monthly_installment": Decimal("2000.00"),
                "transaction_date": datetime.date(2026, 7, 10),
            },
            user_id=101,
        )


@pytest.mark.asyncio
async def test_get_loan_advance_success(
    settlement_service: SettlementService,
) -> None:
    loan_obj = EmployeeLoanAdvance(id=1, org_id=10, employee_id=42)
    settlement_service.loans_advances.get_by_id_in_org.return_value = loan_obj

    res = await settlement_service.get_loan_advance(10, 1)
    assert res == loan_obj


@pytest.mark.asyncio
async def test_get_loan_advance_not_found(
    settlement_service: SettlementService,
) -> None:
    settlement_service.loans_advances.get_by_id_in_org.return_value = None
    with pytest.raises(LoanAdvanceNotFoundException):
        await settlement_service.get_loan_advance(10, 1)


@pytest.mark.asyncio
async def test_search_loans_advances(
    settlement_service: SettlementService,
) -> None:
    settlement_service.loans_advances.search.return_value = ["loan1", "loan2"]
    settlement_service.loans_advances.search_count.return_value = 2

    query = LoanAdvanceSearchQuery(employee_id=42, page=1, page_size=10, sort_by="transaction_date")
    res = await settlement_service.search_loans_advances(10, query)

    assert res.items == ["loan1", "loan2"]
    assert res.pagination.total_records == 2


@pytest.mark.asyncio
async def test_update_loan_advance_success(
    settlement_service: SettlementService,
) -> None:
    loan_obj = EmployeeLoanAdvance(
        id=1,
        org_id=10,
        employee_id=42,
        status="active",
        principal_amount=Decimal("5000.00"),
    )
    settlement_service.loans_advances.get_by_id_in_org.return_value = loan_obj
    settlement_service.loans_advances.update.return_value = loan_obj

    res = await settlement_service.update_loan_advance(
        10, 1, {"name": "New Name", "monthly_installment": 500}, 101
    )
    assert res == loan_obj
    settlement_service.audit.record.assert_called_once()


@pytest.mark.asyncio
async def test_update_loan_advance_closed_error(
    settlement_service: SettlementService,
) -> None:
    loan_obj = EmployeeLoanAdvance(id=1, org_id=10, employee_id=42, status="closed")
    settlement_service.loans_advances.get_by_id_in_org.return_value = loan_obj

    with pytest.raises(LoanAdvanceClosedException):
        await settlement_service.update_loan_advance(10, 1, {"name": "New Name"}, 101)


@pytest.mark.asyncio
async def test_update_loan_advance_invalid_installment(
    settlement_service: SettlementService,
) -> None:
    loan_obj = EmployeeLoanAdvance(
        id=1,
        org_id=10,
        employee_id=42,
        status="active",
        principal_amount=Decimal("5000.00"),
    )
    settlement_service.loans_advances.get_by_id_in_org.return_value = loan_obj

    with pytest.raises(InvalidTransactionException):
        await settlement_service.update_loan_advance(10, 1, {"monthly_installment": 6000}, 101)


@pytest.mark.asyncio
async def test_close_loan_advance_success(
    settlement_service: SettlementService,
) -> None:
    loan_obj = EmployeeLoanAdvance(id=1, org_id=10, employee_id=42, status="active")
    settlement_service.loans_advances.get_by_id_in_org.return_value = loan_obj
    settlement_service.loans_advances.update.return_value = loan_obj

    res = await settlement_service.close_loan_advance(10, 1, 101)
    assert res == loan_obj
    settlement_service.audit.record.assert_called_once()


@pytest.mark.asyncio
async def test_delete_loan_advance_success(
    settlement_service: SettlementService,
) -> None:
    loan_obj = EmployeeLoanAdvance(id=1, org_id=10, employee_id=42)
    settlement_service.loans_advances.get_by_id_in_org.return_value = loan_obj
    settlement_service.loans_advances.has_transactions.return_value = False

    await settlement_service.delete_loan_advance(10, 1, 101)
    settlement_service.loans_advances.delete.assert_called_once()
    settlement_service.audit.record.assert_called_once()


@pytest.mark.asyncio
async def test_delete_loan_advance_has_transactions_error(
    settlement_service: SettlementService,
) -> None:
    loan_obj = EmployeeLoanAdvance(id=1, org_id=10, employee_id=42)
    settlement_service.loans_advances.get_by_id_in_org.return_value = loan_obj
    settlement_service.loans_advances.has_transactions.return_value = True

    with pytest.raises(LoanAdvanceHasTransactionsException):
        await settlement_service.delete_loan_advance(10, 1, 101)


# --- 2. Loan & Advance Transactions Service Tests ------------------------


@pytest.mark.asyncio
async def test_add_loan_advance_transaction_debit(
    settlement_service: SettlementService,
) -> None:
    loan_obj = EmployeeLoanAdvance(
        id=1,
        org_id=10,
        employee_id=42,
        status="active",
        outstanding_amount=Decimal("500.00"),
        total_debit=Decimal("100.00"),
        type="loan",
    )
    settlement_service.loans_advances.get_by_id_in_org.return_value = loan_obj
    settlement_service.loan_transactions.create.return_value = "new_tx"

    tx_data = {
        "amount": 200,
        "transaction_type": "debit",
        "transaction_date": datetime.date(2026, 7, 10),
        "type_label": "loan",
    }
    res = await settlement_service.add_loan_advance_transaction(10, 1, tx_data, 101)

    assert res == "new_tx"
    assert loan_obj.outstanding_amount == Decimal("300.00")
    assert loan_obj.total_debit == Decimal("300.00")
    assert loan_obj.status == "active"


@pytest.mark.asyncio
async def test_add_loan_advance_transaction_debit_autoclose(
    settlement_service: SettlementService,
) -> None:
    loan_obj = EmployeeLoanAdvance(
        id=1,
        org_id=10,
        employee_id=42,
        status="active",
        outstanding_amount=Decimal("500.00"),
        total_debit=Decimal("100.00"),
        type="loan",
    )
    settlement_service.loans_advances.get_by_id_in_org.return_value = loan_obj
    settlement_service.loan_transactions.create.return_value = "new_tx"

    tx_data = {
        "amount": 500,
        "transaction_type": "debit",
        "transaction_date": datetime.date(2026, 7, 10),
        "type_label": "loan",
    }
    res = await settlement_service.add_loan_advance_transaction(10, 1, tx_data, 101)

    assert res == "new_tx"
    assert loan_obj.outstanding_amount == Decimal("0.00")
    assert loan_obj.status == "closed"


@pytest.mark.asyncio
async def test_add_loan_advance_transaction_repayment_exceeds(
    settlement_service: SettlementService,
) -> None:
    loan_obj = EmployeeLoanAdvance(
        id=1,
        org_id=10,
        employee_id=42,
        status="active",
        outstanding_amount=Decimal("500.00"),
        type="loan",
    )
    settlement_service.loans_advances.get_by_id_in_org.return_value = loan_obj

    tx_data = {
        "amount": 600,
        "transaction_type": "debit",
        "transaction_date": datetime.date(2026, 7, 10),
        "type_label": "loan",
    }
    with pytest.raises(InvalidTransactionException):
        await settlement_service.add_loan_advance_transaction(10, 1, tx_data, 101)


# --- 3. Arrears Service Tests --------------------------------------------


@pytest.mark.asyncio
async def test_get_employee_arrears_success(
    settlement_service: SettlementService, mock_session: AsyncMock
) -> None:
    mock_employee_exists(mock_session, exists=True)
    arr_obj = EmployeeArrears(id=1, org_id=10, employee_id=42)
    settlement_service.arrears.get_by_employee_id.return_value = arr_obj

    res = await settlement_service.get_employee_arrears(10, 42)
    assert res == arr_obj


@pytest.mark.asyncio
async def test_get_employee_arrears_not_found(
    settlement_service: SettlementService, mock_session: AsyncMock
) -> None:
    mock_employee_exists(mock_session, exists=True)
    settlement_service.arrears.get_by_employee_id.return_value = None

    with pytest.raises(ArrearsNotFoundException):
        await settlement_service.get_employee_arrears(10, 42)


@pytest.mark.asyncio
async def test_add_arrears_transaction_credit(
    settlement_service: SettlementService, mock_session: AsyncMock
) -> None:
    mock_employee_exists(mock_session, exists=True)
    # Header exists
    arr_obj = EmployeeArrears(
        id=1,
        org_id=10,
        employee_id=42,
        arrears_created=Decimal("100.00"),
        arrears_paid=Decimal("0.00"),
        outstanding_arrears=Decimal("100.00"),
    )
    settlement_service.arrears.get_by_employee_id.return_value = arr_obj
    settlement_service.arrears_transactions.create.return_value = "arr_tx"

    tx_data = {
        "amount": 150,
        "transaction_type": "credit",
        "transaction_date": datetime.date(2026, 7, 10),
    }
    res = await settlement_service.add_arrears_transaction(10, 42, tx_data, 101)

    assert res == "arr_tx"
    assert arr_obj.arrears_created == Decimal("250.00")
    assert arr_obj.outstanding_arrears == Decimal("250.00")


@pytest.mark.asyncio
async def test_add_arrears_transaction_insufficient_debit(
    settlement_service: SettlementService, mock_session: AsyncMock
) -> None:
    mock_employee_exists(mock_session, exists=True)
    arr_obj = EmployeeArrears(
        id=1,
        org_id=10,
        employee_id=42,
        arrears_created=Decimal("100.00"),
        arrears_paid=Decimal("0.00"),
        outstanding_arrears=Decimal("100.00"),
    )
    settlement_service.arrears.get_by_employee_id.return_value = arr_obj

    tx_data = {
        "amount": 200,
        "transaction_type": "debit",
        "transaction_date": datetime.date(2026, 7, 10),
    }
    with pytest.raises(InsufficientArrearsException):
        await settlement_service.add_arrears_transaction(10, 42, tx_data, 101)


# --- 4. Statement, History & Summary Tests --------------------------------


@pytest.mark.asyncio
async def test_get_settlement_statement(
    settlement_service: SettlementService, mock_session: AsyncMock
) -> None:
    mock_employee_exists(mock_session, exists=True)

    loan1 = EmployeeLoanAdvance(
        id=1, org_id=10, employee_id=42, outstanding_amount=Decimal("500.00"), status="active"
    )
    mock_execute_res = MagicMock()
    mock_execute_res.scalars.return_value.all.return_value = [loan1]
    mock_session.execute.return_value = mock_execute_res

    arr_obj = EmployeeArrears(
        id=2, org_id=10, employee_id=42, outstanding_arrears=Decimal("300.00")
    )
    settlement_service.arrears.get_by_employee_id.return_value = arr_obj

    settlement_service.settlement_coords.get_combined_history.return_value = [
        {"kind": "loan", "amount": 100}
    ]

    query = SettlementStatementQuery(
        date_from=datetime.date(2026, 7, 1), date_to=datetime.date(2026, 7, 15)
    )
    res = await settlement_service.get_settlement_statement(10, 42, query)

    assert res["employee_id"] == 42
    assert res["total_outstanding_loans_advances"] == Decimal("500.00")
    assert res["total_outstanding_arrears"] == Decimal("300.00")
    assert len(res["ledger"]) == 1


# --- 5. F&F Settlement Tests ---------------------------------------------


@pytest.mark.asyncio
async def test_calculate_ff_settlement(
    settlement_service: SettlementService, mock_session: AsyncMock
) -> None:
    mock_employee_exists(mock_session, exists=True)
    settlement_service.settlement_coords.get_employee_settlement_summary.return_value = {
        "total_outstanding_loans_advances": Decimal("1000.00"),
        "total_outstanding_arrears": Decimal("400.00"),
    }

    res = await settlement_service.calculate_ff_settlement(10, 42)
    assert res["outstanding_loans_advances"] == Decimal("1000.00")
    assert res["outstanding_arrears"] == Decimal("400.00")
    assert res["net_amount_due"] == Decimal("600.00")


@pytest.mark.asyncio
async def test_approve_ff_settlement(
    settlement_service: SettlementService, mock_session: AsyncMock
) -> None:
    mock_employee_exists(mock_session, exists=True)
    res = await settlement_service.approve_ff_settlement(10, 42, 101)
    assert res["status"] == "approved"
    settlement_service.audit.record.assert_called_once()


@pytest.mark.asyncio
async def test_finalize_ff_settlement(
    settlement_service: SettlementService, mock_session: AsyncMock
) -> None:
    mock_employee_exists(mock_session, exists=True)

    loan1 = EmployeeLoanAdvance(
        id=1,
        org_id=10,
        employee_id=42,
        outstanding_amount=Decimal("500.00"),
        status="active",
        type="loan",
        total_debit=Decimal("0.00"),
    )
    mock_execute_res = MagicMock()
    mock_execute_res.scalars.return_value.all.return_value = [loan1]
    mock_session.execute.return_value = mock_execute_res

    arr_obj = EmployeeArrears(
        id=2,
        org_id=10,
        employee_id=42,
        outstanding_arrears=Decimal("300.00"),
        arrears_paid=Decimal("0.00"),
    )
    settlement_service.arrears.get_by_employee_id.return_value = arr_obj

    res = await settlement_service.finalize_ff_settlement(10, 42, 101)

    assert res["loans_cleared_count"] == 1
    assert res["arrears_cleared_amount"] == Decimal("300.00")
    assert loan1.outstanding_amount == Decimal("0.00")
    assert loan1.status == "closed"
    assert arr_obj.outstanding_arrears == Decimal("0.00")
    assert arr_obj.arrears_paid == Decimal("300.00")
    settlement_service.audit.record.assert_called_once()


# --- 6. Additional Edge Cases & List Queries Tests ------------------------


@pytest.mark.asyncio
async def test_close_loan_advance_already_closed_error(
    settlement_service: SettlementService,
) -> None:
    loan_obj = EmployeeLoanAdvance(id=1, org_id=10, employee_id=42, status="closed")
    settlement_service.loans_advances.get_by_id_in_org.return_value = loan_obj

    with pytest.raises(LoanAdvanceClosedException):
        await settlement_service.close_loan_advance(10, 1, 101)


@pytest.mark.asyncio
async def test_add_loan_advance_transaction_closed_error(
    settlement_service: SettlementService,
) -> None:
    loan_obj = EmployeeLoanAdvance(id=1, org_id=10, employee_id=42, status="closed")
    settlement_service.loans_advances.get_by_id_in_org.return_value = loan_obj

    with pytest.raises(LoanAdvanceClosedException):
        await settlement_service.add_loan_advance_transaction(10, 1, {"amount": 100}, 101)


@pytest.mark.asyncio
async def test_add_loan_advance_transaction_invalid_amount_error(
    settlement_service: SettlementService,
) -> None:
    loan_obj = EmployeeLoanAdvance(id=1, org_id=10, employee_id=42, status="active")
    settlement_service.loans_advances.get_by_id_in_org.return_value = loan_obj

    with pytest.raises(InvalidTransactionException, match="Transaction amount must be positive"):
        await settlement_service.add_loan_advance_transaction(10, 1, {"amount": -100}, 101)


@pytest.mark.asyncio
async def test_add_loan_advance_transaction_invalid_type_error(
    settlement_service: SettlementService,
) -> None:
    loan_obj = EmployeeLoanAdvance(id=1, org_id=10, employee_id=42, status="active")
    settlement_service.loans_advances.get_by_id_in_org.return_value = loan_obj

    with pytest.raises(InvalidTransactionException, match="Transaction type must be"):
        await settlement_service.add_loan_advance_transaction(
            10, 1, {"amount": 100, "transaction_type": "invalid"}, 101
        )


@pytest.mark.asyncio
async def test_add_loan_advance_transaction_credit_success(
    settlement_service: SettlementService,
) -> None:
    loan_obj = EmployeeLoanAdvance(
        id=1,
        org_id=10,
        employee_id=42,
        status="active",
        outstanding_amount=Decimal("500.00"),
        type="loan",
    )
    settlement_service.loans_advances.get_by_id_in_org.return_value = loan_obj
    settlement_service.loan_transactions.create.return_value = "new_tx"

    tx_data = {
        "amount": 200,
        "transaction_type": "credit",
        "transaction_date": datetime.date(2026, 7, 10),
        "type_label": "loan",
    }
    res = await settlement_service.add_loan_advance_transaction(10, 1, tx_data, 101)

    assert res == "new_tx"
    assert loan_obj.outstanding_amount == Decimal("700.00")


@pytest.mark.asyncio
async def test_add_loan_advance_transaction_invalid_installment_revision_error(
    settlement_service: SettlementService,
) -> None:
    loan_obj = EmployeeLoanAdvance(
        id=1,
        org_id=10,
        employee_id=42,
        status="active",
        outstanding_amount=Decimal("500.00"),
        principal_amount=Decimal("1000.00"),
        type="loan",
    )
    settlement_service.loans_advances.get_by_id_in_org.return_value = loan_obj

    tx_data = {
        "amount": 100,
        "transaction_type": "debit",
        "transaction_date": datetime.date(2026, 7, 10),
        "type_label": "loan",
        "installment_amount": 2000,  # Exceeds principal
    }
    with pytest.raises(InvalidTransactionException, match="Invalid revised monthly installment"):
        await settlement_service.add_loan_advance_transaction(10, 1, tx_data, 101)


@pytest.mark.asyncio
async def test_add_arrears_transaction_invalid_amount_error(
    settlement_service: SettlementService, mock_session: MagicMock
) -> None:
    mock_employee_exists(mock_session, exists=True)
    with pytest.raises(InvalidTransactionException, match="Transaction amount must be positive"):
        await settlement_service.add_arrears_transaction(10, 42, {"amount": -100}, 101)


@pytest.mark.asyncio
async def test_add_arrears_transaction_invalid_type_error(
    settlement_service: SettlementService, mock_session: MagicMock
) -> None:
    mock_employee_exists(mock_session, exists=True)
    with pytest.raises(InvalidTransactionException, match="Transaction type must be"):
        await settlement_service.add_arrears_transaction(
            10, 42, {"amount": 100, "transaction_type": "invalid"}, 101
        )


@pytest.mark.asyncio
async def test_add_arrears_transaction_create_header_success(
    settlement_service: SettlementService, mock_session: MagicMock
) -> None:
    mock_employee_exists(mock_session, exists=True)
    settlement_service.arrears.get_by_employee_id.return_value = None

    arr_header = EmployeeArrears(
        id=1,
        org_id=10,
        employee_id=42,
        arrears_created=Decimal("0.00"),
        arrears_paid=Decimal("0.00"),
        outstanding_arrears=Decimal("0.00"),
    )
    settlement_service.arrears.create.return_value = arr_header
    settlement_service.arrears_transactions.create.return_value = "new_arr_tx"

    tx_data = {
        "amount": 500,
        "transaction_type": "credit",
        "transaction_date": datetime.date(2026, 7, 10),
    }
    res = await settlement_service.add_arrears_transaction(10, 42, tx_data, 101)

    assert res == "new_arr_tx"
    settlement_service.arrears.create.assert_called_once()
    assert arr_header.outstanding_arrears == Decimal("500.00")


@pytest.mark.asyncio
async def test_list_loan_advance_transactions_service(
    settlement_service: SettlementService,
) -> None:
    from app.modules.settlements.schemas import LoanAdvanceTransactionSearchQuery

    loan_obj = EmployeeLoanAdvance(id=1, org_id=10, employee_id=42)
    settlement_service.loans_advances.get_by_id_in_org.return_value = loan_obj

    settlement_service.loan_transactions.search.return_value = ["tx1"]
    settlement_service.loan_transactions.search_count.return_value = 1

    query = LoanAdvanceTransactionSearchQuery(page=1, page_size=20)
    res = await settlement_service.list_loan_advance_transactions(10, 1, query)

    assert res.items == ["tx1"]
    assert res.pagination.total_records == 1


@pytest.mark.asyncio
async def test_list_employee_arrears_service(
    settlement_service: SettlementService,
) -> None:
    from app.modules.settlements.schemas import ArrearsSearchQuery

    settlement_service.arrears.search.return_value = ["arrears1"]
    settlement_service.arrears.search_count.return_value = 1

    query = ArrearsSearchQuery(page=1, page_size=20)
    res = await settlement_service.list_employee_arrears(10, query)

    assert res.items == ["arrears1"]
    assert res.pagination.total_records == 1


@pytest.mark.asyncio
async def test_list_arrears_transactions_service(
    settlement_service: SettlementService, mock_session: MagicMock
) -> None:
    from app.modules.settlements.schemas import ArrearsTransactionSearchQuery

    mock_employee_exists(mock_session, exists=True)
    settlement_service.arrears_transactions.search.return_value = ["tx1"]
    settlement_service.arrears_transactions.search_count.return_value = 1

    query = ArrearsTransactionSearchQuery(page=1, page_size=20)
    res = await settlement_service.list_arrears_transactions(10, 42, query)

    assert res.items == ["tx1"]
    assert res.pagination.total_records == 1


@pytest.mark.asyncio
async def test_get_settlement_history_service(
    settlement_service: SettlementService, mock_session: MagicMock
) -> None:
    from app.modules.settlements.schemas import SettlementHistoryQuery

    mock_employee_exists(mock_session, exists=True)
    settlement_service.settlement_coords.get_combined_history.return_value = ["item1"]
    settlement_service.settlement_coords.get_combined_history_count.return_value = 1

    query = SettlementHistoryQuery(page=1, page_size=20)
    res = await settlement_service.get_settlement_history(10, 42, query)

    assert res.items == ["item1"]
    assert res.pagination.total_records == 1


@pytest.mark.asyncio
async def test_get_settlement_summary_service(
    settlement_service: SettlementService, mock_session: MagicMock
) -> None:
    from app.modules.settlements.schemas import SettlementSummaryQuery

    mock_employee_exists(mock_session, exists=True)
    settlement_service.settlement_coords.get_employee_settlement_summary.return_value = {
        "summary": True
    }

    query = SettlementSummaryQuery(employee_id=42)
    res = await settlement_service.get_settlement_summary(10, query)

    assert res == {"summary": True}
