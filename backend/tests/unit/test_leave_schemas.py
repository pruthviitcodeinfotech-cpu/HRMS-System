"""Unit tests for the Leave Management Pydantic request-schema validation.

Exercises the Pydantic v2 validators independently: leave type rules (encashment limit,
frequencies), leave settings start month bounds, credit/debit amount constraints,
and leave request date order.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.modules.leave.constants import (
    AllocationFrequency,
    CarryForwardFrequency,
    EncashmentFrequency,
)
from app.modules.leave.schemas import (
    HolidayTemplateItemCreateRequest,
    HolidayTemplateItemUpdateRequest,
    LeaveBalanceAdjustRequest,
    LeaveCreditDebitRequest,
    LeaveRequestCreateRequest,
    LeaveRequestUpdateRequest,
    LeaveSettingsUpdateRequest,
    LeaveTypeCreateRequest,
    LeaveTypeUpdateRequest,
)

# --- 1. Leave Type Schemas -------------------------------------------------


def test_leave_type_create_encashment_limit_required() -> None:
    # Encashment enabled but limit missing -> ValidationError
    with pytest.raises(ValidationError):
        LeaveTypeCreateRequest(
            name="Privilege Leave",
            alias="PL",
            auto_allocation_count=Decimal("15.00"),
            encashment_enabled=True,
            encashment_limit=None,
        )


def test_leave_type_create_valid() -> None:
    req = LeaveTypeCreateRequest(
        name="Casual Leave",
        alias="CL",
        auto_allocation_count=Decimal("12.00"),
        encashment_enabled=False,
    )
    assert req.name == "Casual Leave"
    assert req.carry_forward_count == Decimal("0.00")


def test_leave_type_update_encashment_validation() -> None:
    # If encashment_enabled is True, encashment_limit must be set
    with pytest.raises(ValidationError):
        LeaveTypeUpdateRequest(
            encashment_enabled=True,
            encashment_limit=None,
        )


# --- 2. Leave Settings Schemas ---------------------------------------------


def test_leave_settings_start_month_bounds() -> None:
    for bad in (0, 13):
        with pytest.raises(ValidationError):
            LeaveSettingsUpdateRequest(cycle_start_month=bad)

    req = LeaveSettingsUpdateRequest(cycle_start_month=4)
    assert req.cycle_start_month == 4


# --- 3. Credit/Debit/Adjust Request Schemas --------------------------------


def test_credit_debit_days_must_be_positive() -> None:
    for bad in (Decimal("0"), Decimal("-1.5")):
        with pytest.raises(ValidationError):
            LeaveCreditDebitRequest(
                leave_type_id=1,
                cycle_year=2026,
                days=bad,
            )

    req = LeaveCreditDebitRequest(
        leave_type_id=1,
        cycle_year=2026,
        days=Decimal("2.5"),
    )
    assert req.days == Decimal("2.5")


def test_adjust_new_balance_non_negative() -> None:
    with pytest.raises(ValidationError):
        LeaveBalanceAdjustRequest(
            leave_type_id=1,
            cycle_year=2026,
            new_balance=Decimal("-0.5"),
        )

    req = LeaveBalanceAdjustRequest(
        leave_type_id=1,
        cycle_year=2026,
        new_balance=Decimal("0.00"),
    )
    assert req.new_balance == Decimal("0.00")


# --- 4. Leave Request Schemas ----------------------------------------------


def test_leave_request_create_date_range() -> None:
    with pytest.raises(ValidationError):
        LeaveRequestCreateRequest(
            leave_type_id=1,
            start_date=date(2026, 2, 10),
            end_date=date(2026, 2, 5),
            duration_days=Decimal("1.0"),
        )


def test_leave_request_update_date_range() -> None:
    with pytest.raises(ValidationError):
        LeaveRequestUpdateRequest(
            start_date=date(2026, 2, 10),
            end_date=date(2026, 2, 5),
        )


# --- 5. Holiday Item Schemas -----------------------------------------------


def test_holiday_item_create_date_range() -> None:
    with pytest.raises(ValidationError):
        HolidayTemplateItemCreateRequest(
            name="New Year",
            start_date=date(2026, 1, 2),
            end_date=date(2026, 1, 1),
        )


def test_holiday_item_update_date_range() -> None:
    with pytest.raises(ValidationError):
        HolidayTemplateItemUpdateRequest(
            start_date=date(2026, 1, 2),
            end_date=date(2026, 1, 1),
        )
