"""Unit tests for Enterprise Loan & Advance Management."""

from __future__ import annotations

import datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.modules.settlements.schemas import (
    LoanEarlyClosureRequest,
    LoanRequestCreate,
)
from app.modules.settlements.service import SettlementService

_ORG_ID = 10
_EMP_ID = 101
_USER_ID = 42
_NOW = datetime.datetime(2026, 7, 29, 10, 0, 0, tzinfo=datetime.timezone.utc)


def _make_service() -> SettlementService:
    session = AsyncMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    svc = SettlementService(session)
    svc.loans_advances = AsyncMock()
    svc.loan_transactions = AsyncMock()
    svc.audit = AsyncMock()
    svc._validate_employee = AsyncMock()
    return svc


@pytest.mark.asyncio
async def test_request_loan_creates_pending_loan() -> None:
    """Submit a new personal loan request and verify installment calculation."""
    svc = _make_service()

    payload = LoanRequestCreate(
        name="Personal Loan Request",
        category="personal_loan",
        principal_amount=Decimal("120000.00"),
        tenure_months=12,
        interest_rate=Decimal("10.00"),
        interest_type="flat",
        comment="Medical expenses",
    )

    loan = await svc.request_loan(
        org_id=_ORG_ID, employee_id=_EMP_ID, user_id=_USER_ID, data=payload
    )

    assert loan.org_id == _ORG_ID
    assert loan.employee_id == _EMP_ID
    assert loan.category == "personal_loan"
    assert loan.principal_amount == Decimal("120000.00")
    assert loan.approval_status == "pending_approval"
    # Monthly installment = (120000 + 12000) / 12 = 11000.00
    assert loan.monthly_installment == Decimal("11000.00")
    svc.audit.record.assert_called_once()


@pytest.mark.asyncio
async def test_disburse_loan_generates_schedules() -> None:
    """Disburse approved loan and verify schedule generation."""
    svc = _make_service()

    mock_loan = SimpleNamespace(
        id=5,
        org_id=_ORG_ID,
        employee_id=_EMP_ID,
        type="loan",
        principal_amount=Decimal("60000.00"),
        monthly_installment=Decimal("5000.00"),
        tenure_months=12,
        total_debit=Decimal("0.00"),
        approval_status="pending_approval",
        status="active",
        disbursed_at=None,
        updated_by=None,
    )
    svc.loans_advances.get_by_id.return_value = mock_loan

    res = await svc.disburse_loan(org_id=_ORG_ID, loan_id=5, user_id=_USER_ID)

    assert res.approval_status == "disbursed"
    assert res.disbursed_at is not None
    assert res.total_debit == Decimal("60000.00")
    svc.audit.record.assert_called_once()


@pytest.mark.asyncio
async def test_early_closure_settles_balance() -> None:
    """Settle outstanding loan balance early."""
    svc = _make_service()

    mock_loan = SimpleNamespace(
        id=5,
        org_id=_ORG_ID,
        employee_id=_EMP_ID,
        type="loan",
        outstanding_amount=Decimal("30000.00"),
        status="active",
        approval_status="disbursed",
        updated_by=None,
    )
    svc.loans_advances.get_by_id.return_value = mock_loan

    mock_scalars = MagicMock()
    mock_scalars.scalars.return_value.all.return_value = []
    svc.session.execute.return_value = mock_scalars

    payload = LoanEarlyClosureRequest(
        payoff_amount=Decimal("28000.00"),
        discount_amount=Decimal("2000.00"),
        comment="Full early payoff discount",
    )

    res = await svc.early_closure(
        org_id=_ORG_ID, loan_id=5, user_id=_USER_ID, data=payload
    )

    assert res.outstanding_amount == Decimal("0.00")
    assert res.status == "closed"
    assert res.approval_status == "closed"
    svc.audit.record.assert_called_once()
