"""Unit tests for Phase 2 Process Payroll module."""

from datetime import date
from decimal import Decimal
import pytest
from pydantic import ValidationError

from app.modules.payroll.schemas import (
    PayrollProcessRequestSchema,
    PayrollComputedRowSchema,
)


def test_payroll_process_request_validation():
    """Test date range validation for payroll process requests."""
    # Valid date range
    valid_req = PayrollProcessRequestSchema(
        payroll_group_id=1,
        cycle_from=date(2026, 7, 1),
        cycle_to=date(2026, 7, 22),
    )
    assert valid_req.cycle_from == date(2026, 7, 1)
    assert valid_req.cycle_to == date(2026, 7, 22)

    # Invalid date range (cycle_to before cycle_from)
    with pytest.raises(ValidationError):
        PayrollProcessRequestSchema(
            payroll_group_id=1,
            cycle_from=date(2026, 7, 22),
            cycle_to=date(2026, 7, 1),
        )


def test_payroll_computed_row_financial_schema():
    """Test schema validation and fields of computed row metrics."""
    row = PayrollComputedRowSchema(
        id=1,
        payroll_group_id=1,
        employee_id=10,
        cycle_from=date(2026, 7, 1),
        cycle_to=date(2026, 7, 22),
        total_days=22,
        full_day_count=18,
        half_day_count=1,
        off_day_count=4,
        paid_leave_count=Decimal("0.0"),
        paid_day_count=Decimal("18.5"),
        unpaid_day_count=Decimal("3.5"),
        daily_wage=Decimal("2000.00"),
        gross_wages=Decimal("37000.00"),
        overtime_amount=Decimal("1500.00"),
        penalties_amount=Decimal("500.00"),
        extras_amount=Decimal("800.00"),
        gross_earnings=Decimal("38800.00"),
        loan_advance_deduction=Decimal("2000.00"),
        arrears_amount=Decimal("1000.00"),
        to_pay=Decimal("37800.00"),
        balance_arrears=Decimal("0.00"),
        is_finalized=False,
        computed_at="2026-07-23T10:00:00Z",
    )
    assert row.employee_id == 10
    assert row.paid_day_count == Decimal("18.5")
    assert row.gross_earnings == Decimal("38800.00")
    assert row.to_pay == Decimal("37800.00")
