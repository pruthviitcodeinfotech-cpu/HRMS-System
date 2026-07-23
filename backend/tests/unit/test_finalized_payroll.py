"""Unit tests for Finalized Payroll History module schemas, snapshots, and exceptions."""

from datetime import date, datetime
from decimal import Decimal

from app.core.exceptions.base import NotFoundException
from app.modules.payroll.exceptions import (
    PayrollFinalizationNotFoundException,
    PayrollValidationException,
)
from app.modules.payroll.schemas import (
    PayrollFinalizationCancelSchema,
    PayrollFinalizationCreateSchema,
    PayrollFinalizationEmployeeSchema,
    PayrollFinalizationListResponse,
    PayrollFinalizationPaySchema,
    PayrollFinalizationResponseSchema,
)


def test_finalization_create_schema():
    """Verify PayrollFinalizationCreateSchema initialization and defaults."""
    payload = PayrollFinalizationCreateSchema(
        payroll_group_id=1,
        from_date=date(2026, 7, 1),
        to_date=date(2026, 7, 31),
        remarks="July 2026 Finalization",
    )
    assert payload.payroll_group_id == 1
    assert payload.from_date == date(2026, 7, 1)
    assert payload.to_date == date(2026, 7, 31)
    assert payload.payroll_module == "Monthly Payroll"
    assert payload.remarks == "July 2026 Finalization"


def test_finalization_pay_schema():
    """Verify PayrollFinalizationPaySchema serialization."""
    pay_payload = PayrollFinalizationPaySchema(
        paid_amount=Decimal("150000.50"),
        paid_on=datetime(2026, 7, 31, 12, 0, 0),
        payment_method="Direct Deposit",
        remarks="Bank Disbursed",
    )
    assert pay_payload.paid_amount == Decimal("150000.50")
    assert pay_payload.payment_method == "Direct Deposit"
    assert pay_payload.remarks == "Bank Disbursed"


def test_finalization_cancel_schema():
    """Verify PayrollFinalizationCancelSchema initialization."""
    cancel_payload = PayrollFinalizationCancelSchema(reason="Date range error")
    assert cancel_payload.reason == "Date range error"


def test_finalization_employee_snapshot_schema():
    """Verify PayrollFinalizationEmployeeSchema frozen snapshot structure."""
    now = datetime.now()
    emp_snapshot_data = {
        "id": 101,
        "payroll_finalization_id": 5,
        "employee_id": 235,
        "employee_code": "QAEMP235",
        "employee_name": "QA Employee 235",
        "attendance_summary": {
            "total_days": 31,
            "full_days": 25,
            "half_days": 0,
            "off_days": 6,
        },
        "earnings_summary": {
            "gross_wages": 50000.00,
            "gross_earnings": 50000.00,
        },
        "deduction_summary": {
            "penalties_amount": 0.00,
            "loan_deduction": 2000.00,
        },
        "loan_amount": Decimal("2000.00"),
        "arrears_amount": Decimal("0.00"),
        "net_salary": Decimal("48000.00"),
        "json_snapshot": {"status": "frozen"},
        "created_at": now,
    }
    schema = PayrollFinalizationEmployeeSchema.model_validate(emp_snapshot_data)
    assert schema.id == 101
    assert schema.employee_id == 235
    assert schema.net_salary == Decimal("48000.00")
    assert schema.loan_amount == Decimal("2000.00")
    assert schema.json_snapshot == {"status": "frozen"}


def test_finalization_response_schema_with_employees():
    """Verify PayrollFinalizationResponseSchema envelope serialization."""
    now = datetime.now()
    data = {
        "id": 5,
        "org_id": 1,
        "payroll_group_id": 2,
        "payroll_group_name": "Monthly with compliance",
        "from_date": date(2026, 7, 1),
        "to_date": date(2026, 7, 31),
        "payroll_module": "Monthly Payroll",
        "employee_count": 1,
        "gross_amount": Decimal("50000.00"),
        "deduction_amount": Decimal("2000.00"),
        "net_payable": Decimal("48000.00"),
        "finalized_amount": Decimal("48000.00"),
        "paid_amount": Decimal("48000.00"),
        "paid_on": now,
        "status": "Paid",
        "finalized_by": 1,
        "finalized_on": now,
        "remarks": "Fully Paid",
        "created_at": now,
        "updated_at": now,
        "employees": [
            {
                "id": 101,
                "payroll_finalization_id": 5,
                "employee_id": 235,
                "employee_code": "QAEMP235",
                "employee_name": "QA Employee 235",
                "loan_amount": Decimal("2000.00"),
                "arrears_amount": Decimal("0.00"),
                "net_salary": Decimal("48000.00"),
                "json_snapshot": {},
                "created_at": now,
            }
        ],
    }
    resp = PayrollFinalizationResponseSchema.model_validate(data)
    assert resp.id == 5
    assert resp.payroll_group_name == "Monthly with compliance"
    assert resp.status == "Paid"
    assert len(resp.employees) == 1
    assert resp.employees[0].employee_name == "QA Employee 235"


def test_finalized_payroll_exceptions():
    """Verify PayrollValidationException and PayrollFinalizationNotFoundException."""
    val_err = PayrollValidationException("Cannot pay cancelled payroll.")
    assert val_err.code == "PAYROLL_VALIDATION_ERROR"
    assert val_err.message == "Cannot pay cancelled payroll."

    not_found_err = PayrollFinalizationNotFoundException()
    assert not_found_err.code == "PAYROLL_FINALIZATION_NOT_FOUND"
    assert isinstance(not_found_err, NotFoundException)
