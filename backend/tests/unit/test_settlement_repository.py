"""Unit tests for the Settlement Management Repository layer."""

from __future__ import annotations

import datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.sql import Select

from app.core.constants.enums import SortOrder
from app.modules.settlements.models import (
    EmployeeArrears,
    EmployeeLoanAdvance,
)
from app.modules.settlements.repository import (
    ArrearsTransactionRepository,
    EmployeeArrearsRepository,
    EmployeeLoanAdvanceRepository,
    LoanAdvanceTransactionRepository,
    SettlementRepository,
)

# --- 1. Employee Loan & Advance Repository Tests --------------------------


@pytest.mark.asyncio
async def test_loan_advance_get_by_id_in_org() -> None:
    session = AsyncMock()
    mock_result = MagicMock()
    loan_obj = EmployeeLoanAdvance(id=1, org_id=10, employee_id=42, name="Test Loan")
    mock_result.scalar_one_or_none.return_value = loan_obj
    session.execute.return_value = mock_result

    repo = EmployeeLoanAdvanceRepository(session)
    res = await repo.get_by_id_in_org(10, 1)

    assert res == loan_obj
    session.execute.assert_called_once()
    stmt = session.execute.call_args[0][0]
    assert isinstance(stmt, Select)


@pytest.mark.asyncio
async def test_loan_advance_exists_in_org() -> None:
    session = AsyncMock()
    mock_result = MagicMock()
    mock_result.first.return_value = (1,)
    session.execute.return_value = mock_result

    repo = EmployeeLoanAdvanceRepository(session)
    res = await repo.exists_in_org(10, 1)

    assert res is True
    session.execute.assert_called_once()


@pytest.mark.asyncio
async def test_loan_advance_has_transactions() -> None:
    session = AsyncMock()
    mock_result = MagicMock()
    mock_result.first.return_value = (101,)
    session.execute.return_value = mock_result

    repo = EmployeeLoanAdvanceRepository(session)
    res = await repo.has_transactions(1)

    assert res is True
    session.execute.assert_called_once()


@pytest.mark.asyncio
async def test_loan_advance_search_and_count() -> None:
    session = AsyncMock()
    mock_result_search = MagicMock()
    mock_result_search.scalars.return_value.all.return_value = ["loan1", "loan2"]
    mock_result_count = MagicMock()
    mock_result_count.scalar_one.return_value = 2
    session.execute.side_effect = [mock_result_search, mock_result_count]

    repo = EmployeeLoanAdvanceRepository(session)
    results = await repo.search(
        org_id=10,
        employee_id=42,
        type="loan",
        status="active",
        date_from=datetime.date(2026, 1, 1),
        date_to=datetime.date(2026, 12, 31),
        search="Emergency",
        branch_id=1,
        dept_id=2,
        sort_by="outstanding_amount",
        sort_order=SortOrder.DESC,
        page=1,
        page_size=25,
    )

    count = await repo.search_count(
        org_id=10,
        employee_id=42,
        type="loan",
        status="active",
        date_from=datetime.date(2026, 1, 1),
        date_to=datetime.date(2026, 12, 31),
        search="Emergency",
        branch_id=1,
        dept_id=2,
    )

    assert results == ["loan1", "loan2"]
    assert count == 2
    assert session.execute.call_count == 2


# --- 2. Loan & Advance Transaction Repository Tests ------------------------


@pytest.mark.asyncio
async def test_loan_transaction_search_and_count() -> None:
    session = AsyncMock()
    mock_result_search = MagicMock()
    mock_result_search.scalars.return_value.all.return_value = ["tx1", "tx2"]
    mock_result_count = MagicMock()
    mock_result_count.scalar_one.return_value = 2
    session.execute.side_effect = [mock_result_search, mock_result_count]

    repo = LoanAdvanceTransactionRepository(session)
    results = await repo.search(
        loan_advance_id=1,
        transaction_type="debit",
        source="manual",
        date_from=datetime.date(2026, 1, 1),
        date_to=datetime.date(2026, 12, 31),
        sort_by="amount",
        sort_order=SortOrder.ASC,
        page=1,
        page_size=10,
    )

    count = await repo.search_count(
        loan_advance_id=1,
        transaction_type="debit",
        source="manual",
        date_from=datetime.date(2026, 1, 1),
        date_to=datetime.date(2026, 12, 31),
    )

    assert results == ["tx1", "tx2"]
    assert count == 2
    assert session.execute.call_count == 2


# --- 3. Employee Arrears Repository Tests ----------------------------------


@pytest.mark.asyncio
async def test_arrears_get_by_employee_id() -> None:
    session = AsyncMock()
    mock_result = MagicMock()
    arrears_obj = EmployeeArrears(
        id=1, org_id=10, employee_id=42, outstanding_arrears=Decimal("500")
    )
    mock_result.scalar_one_or_none.return_value = arrears_obj
    session.execute.return_value = mock_result

    repo = EmployeeArrearsRepository(session)
    res = await repo.get_by_employee_id(10, 42)

    assert res == arrears_obj
    session.execute.assert_called_once()


@pytest.mark.asyncio
async def test_arrears_search_and_count() -> None:
    session = AsyncMock()
    mock_result_search = MagicMock()
    mock_result_search.scalars.return_value.all.return_value = ["arrears1"]
    mock_result_count = MagicMock()
    mock_result_count.scalar_one.return_value = 1
    session.execute.side_effect = [mock_result_search, mock_result_count]

    repo = EmployeeArrearsRepository(session)
    results = await repo.search(
        org_id=10,
        employee_id=42,
        min_outstanding=Decimal("100"),
        branch_id=1,
        dept_id=2,
        sort_by="outstanding_arrears",
        sort_order=SortOrder.DESC,
        page=1,
        page_size=10,
    )

    count = await repo.search_count(
        org_id=10,
        employee_id=42,
        min_outstanding=Decimal("100"),
        branch_id=1,
        dept_id=2,
    )

    assert results == ["arrears1"]
    assert count == 1
    assert session.execute.call_count == 2


# --- 4. Arrears Transaction Repository Tests -------------------------------


@pytest.mark.asyncio
async def test_arrears_transaction_search_and_count() -> None:
    session = AsyncMock()
    mock_result_search = MagicMock()
    mock_result_search.scalars.return_value.all.return_value = ["arr_tx1"]
    mock_result_count = MagicMock()
    mock_result_count.scalar_one.return_value = 1
    session.execute.side_effect = [mock_result_search, mock_result_count]

    repo = ArrearsTransactionRepository(session)
    results = await repo.search(
        employee_id=42,
        transaction_type="credit",
        source="payroll",
        date_from=datetime.date(2026, 1, 1),
        date_to=datetime.date(2026, 12, 31),
        sort_by="transaction_date",
        sort_order=SortOrder.DESC,
        page=1,
        page_size=10,
    )

    count = await repo.search_count(
        employee_id=42,
        transaction_type="credit",
        source="payroll",
        date_from=datetime.date(2026, 1, 1),
        date_to=datetime.date(2026, 12, 31),
    )

    assert results == ["arr_tx1"]
    assert count == 1
    assert session.execute.call_count == 2


# --- 5. Settlement Repository (Combined/Views) Tests -----------------------


@pytest.mark.asyncio
async def test_settlement_combined_history() -> None:
    session = AsyncMock()
    mock_result = MagicMock()
    mock_result.all.return_value = [
        (
            datetime.date(2026, 7, 10),
            "loan",
            "debit",
            Decimal("100.00"),
            Decimal("0.00"),
            "manual",
            "notes",
        ),
        (
            datetime.date(2026, 7, 9),
            "arrears",
            "credit",
            Decimal("50.00"),
            Decimal("50.00"),
            "payroll",
            "arrear",
        ),
    ]
    session.execute.return_value = mock_result

    repo = SettlementRepository(session)
    results = await repo.get_combined_history(
        org_id=10,
        employee_id=42,
        date_from=datetime.date(2026, 7, 1),
        date_to=datetime.date(2026, 7, 15),
        source="manual",
        page=1,
        page_size=10,
    )

    assert len(results) == 2
    assert results[0]["kind"] == "loan"
    assert results[0]["amount"] == Decimal("100.00")
    assert results[1]["kind"] == "arrears"
    assert results[1]["amount"] == Decimal("50.00")


@pytest.mark.asyncio
async def test_settlement_combined_history_count() -> None:
    session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one.return_value = 5
    session.execute.return_value = mock_result

    repo = SettlementRepository(session)
    count = await repo.get_combined_history_count(
        org_id=10,
        employee_id=42,
    )

    assert count == 5


@pytest.mark.asyncio
async def test_settlement_employee_summary() -> None:
    session = AsyncMock()
    mock_loan_result = MagicMock()
    mock_loan_result.first.return_value = (Decimal("1000.00"), Decimal("800.00"), 2)
    mock_arrears_result = MagicMock()
    mock_arrears_result.scalar.return_value = Decimal("300.00")

    session.execute.side_effect = [mock_loan_result, mock_arrears_result]

    repo = SettlementRepository(session)
    summary = await repo.get_employee_settlement_summary(10, 42)

    assert summary["total_active_loans_advances"] == Decimal("1000.00")
    assert summary["total_outstanding_loans_advances"] == Decimal("800.00")
    assert summary["total_outstanding_arrears"] == Decimal("300.00")
    assert summary["count_active"] == 2
