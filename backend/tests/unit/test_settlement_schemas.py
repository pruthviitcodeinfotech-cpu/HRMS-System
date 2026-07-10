"""Unit tests for the Settlement Management Pydantic request-schema validation.

Exercises the Pydantic v2 validators for loans, advances, arrears, and combined settlement queries.
"""

from __future__ import annotations

import datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.modules.settlements.constants import (
    LoanAdvanceType,
    TransactionType,
)
from app.modules.settlements.schemas import (
    ArrearsTransactionCreateRequest,
    LoanAdvanceCreateRequest,
    LoanAdvanceSearchQuery,
    LoanAdvanceTransactionCreateRequest,
    LoanAdvanceUpdateRequest,
    SettlementHistoryQuery,
    SettlementStatementQuery,
)

# --- 1. Loan / Advance Request Schemas -------------------------------------


def test_loan_advance_create_valid() -> None:
    req = LoanAdvanceCreateRequest(
        employee_id=42,
        name="Emergency Loan",
        type=LoanAdvanceType.LOAN,
        principal_amount=Decimal("50000.00"),
        monthly_installment=Decimal("5000.00"),
        transaction_date=datetime.date(2026, 7, 10),
        comment="Approved by CEO",
    )
    assert req.employee_id == 42
    assert req.principal_amount == Decimal("50000.00")
    assert req.monthly_installment == Decimal("5000.00")


def test_loan_advance_create_invalid_amounts() -> None:
    # Principal amount must be > 0
    with pytest.raises(ValidationError):
        LoanAdvanceCreateRequest(
            employee_id=42,
            name="Emergency Loan",
            type=LoanAdvanceType.LOAN,
            principal_amount=Decimal("-10.00"),
            monthly_installment=Decimal("5000.00"),
            transaction_date=datetime.date(2026, 7, 10),
        )

    # Monthly installment must be > 0
    with pytest.raises(ValidationError):
        LoanAdvanceCreateRequest(
            employee_id=42,
            name="Emergency Loan",
            type=LoanAdvanceType.LOAN,
            principal_amount=Decimal("50000.00"),
            monthly_installment=Decimal("0.00"),
            transaction_date=datetime.date(2026, 7, 10),
        )


def test_loan_advance_create_installment_exceeds_principal() -> None:
    # Installment cannot exceed principal
    with pytest.raises(ValidationError):
        LoanAdvanceCreateRequest(
            employee_id=42,
            name="Salary Advance",
            type=LoanAdvanceType.ADVANCE,
            principal_amount=Decimal("1000.00"),
            monthly_installment=Decimal("1200.00"),
            transaction_date=datetime.date(2026, 7, 10),
        )


def test_loan_advance_update_valid() -> None:
    req = LoanAdvanceUpdateRequest(
        name="Updated Name",
        monthly_installment=Decimal("2500.00"),
    )
    assert req.name == "Updated Name"
    assert req.monthly_installment == Decimal("2500.00")


def test_loan_advance_update_invalid() -> None:
    with pytest.raises(ValidationError):
        LoanAdvanceUpdateRequest(monthly_installment=Decimal("-5.00"))


# --- 2. Loan / Advance Search & Query Schemas -----------------------------


def test_loan_advance_search_date_range() -> None:
    # Valid date range
    query = LoanAdvanceSearchQuery(
        date_from=datetime.date(2026, 1, 1),
        date_to=datetime.date(2026, 1, 31),
    )
    assert query.date_from == datetime.date(2026, 1, 1)

    # Invalid range: to_date before from_date
    with pytest.raises(ValidationError):
        LoanAdvanceSearchQuery(
            date_from=datetime.date(2026, 2, 1),
            date_to=datetime.date(2026, 1, 31),
        )


# --- 3. Loan / Advance Ledger Transactions ---------------------------------


def test_loan_advance_transaction_create_valid() -> None:
    req = LoanAdvanceTransactionCreateRequest(
        transaction_date=datetime.date(2026, 7, 10),
        transaction_type=TransactionType.DEBIT,
        amount=Decimal("5000.00"),
        installment_amount=Decimal("4500.00"),
        type_label=LoanAdvanceType.LOAN,
        comment="Repayment",
    )
    assert req.amount == Decimal("5000.00")
    assert req.installment_amount == Decimal("4500.00")


def test_loan_advance_transaction_create_invalid() -> None:
    with pytest.raises(ValidationError):
        LoanAdvanceTransactionCreateRequest(
            transaction_date=datetime.date(2026, 7, 10),
            transaction_type=TransactionType.DEBIT,
            amount=Decimal("-100.00"),
            type_label=LoanAdvanceType.LOAN,
        )


# --- 4. Arrears Ledger Transactions ----------------------------------------


def test_arrears_transaction_create_valid() -> None:
    req = ArrearsTransactionCreateRequest(
        transaction_date=datetime.date(2026, 7, 10),
        transaction_type=TransactionType.CREDIT,
        amount=Decimal("1500.00"),
        comment="Arrears addition",
    )
    assert req.amount == Decimal("1500.00")


def test_arrears_transaction_create_invalid() -> None:
    with pytest.raises(ValidationError):
        ArrearsTransactionCreateRequest(
            transaction_date=datetime.date(2026, 7, 10),
            transaction_type=TransactionType.CREDIT,
            amount=Decimal("0.00"),
        )


# --- 5. Settlement Statement and History Queries --------------------------


def test_settlement_statement_query_date_range() -> None:
    # Valid range
    query = SettlementStatementQuery(
        date_from=datetime.date(2026, 1, 1),
        date_to=datetime.date(2026, 1, 31),
    )
    assert query.date_from == datetime.date(2026, 1, 1)

    # Invalid range
    with pytest.raises(ValidationError):
        SettlementStatementQuery(
            date_from=datetime.date(2026, 2, 1),
            date_to=datetime.date(2026, 1, 31),
        )


def test_settlement_history_query_date_range() -> None:
    with pytest.raises(ValidationError):
        SettlementHistoryQuery(
            date_from=datetime.date(2026, 2, 1),
            date_to=datetime.date(2026, 1, 31),
        )
