"""Unit tests for the Employee-Management request-schema validation.

Exercises the Pydantic v2 validators independently of the service: required
fields, email/phone normalisation, salary bounds, the exit-date rule, the
mass-assignment guard, and the list-query defaults.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.modules.employee.constants import EmploymentStatus
from app.modules.employee.schemas import (
    EmployeeCreateRequest,
    EmployeeExitRequest,
    EmployeeListQuery,
)


def _create(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "employee_name": "Jane Doe",
        "gender": "Female",
        "mobile_number": "9876543210",
        "master_branch_id": 1,
        "dept_id": 1,
        "designation_id": 1,
        "date_of_joining": date(2026, 1, 1),
    }
    base.update(overrides)
    return base


# --- Create request --------------------------------------------------------
def test_create_request_valid_normalises_contact() -> None:
    req = EmployeeCreateRequest(**_create(email="JANE@Example.COM", mobile_number="+91 98765-43210"))
    assert req.email == "jane@example.com"
    assert req.mobile_number == "+919876543210"


def test_create_request_missing_name_rejected() -> None:
    payload = _create()
    payload.pop("employee_name")
    with pytest.raises(ValidationError):
        EmployeeCreateRequest(**payload)


def test_create_request_invalid_email_rejected() -> None:
    with pytest.raises(ValidationError):
        EmployeeCreateRequest(**_create(email="not-an-email"))


def test_create_request_invalid_phone_rejected() -> None:
    with pytest.raises(ValidationError):
        EmployeeCreateRequest(**_create(mobile_number="abc"))


def test_create_request_negative_salary_rejected() -> None:
    with pytest.raises(ValidationError):
        EmployeeCreateRequest(**_create(monthly_salary=Decimal("-1")))


def test_create_request_ignores_uncontrolled_fields() -> None:
    """Mass-assignment guard: server-controlled fields are not settable by the client."""
    req = EmployeeCreateRequest(
        **_create(employee_code="HACK", employment_status="terminated", is_deleted=True)
    )
    assert not hasattr(req, "employee_code")
    assert not hasattr(req, "employment_status")
    assert not hasattr(req, "is_deleted")


# --- Exit request ----------------------------------------------------------
def test_exit_request_last_working_day_before_resignation_rejected() -> None:
    with pytest.raises(ValidationError):
        EmployeeExitRequest(
            resignation_date=date(2026, 3, 10), last_working_day=date(2026, 3, 1)
        )


def test_exit_request_valid_dates_accepted() -> None:
    req = EmployeeExitRequest(
        resignation_date=date(2026, 3, 1), last_working_day=date(2026, 3, 30), reason="resigned"
    )
    assert req.last_working_day == date(2026, 3, 30)


# --- List query ------------------------------------------------------------
def test_list_query_defaults() -> None:
    query = EmployeeListQuery()
    assert query.page == 1
    assert query.branch_id is None
    assert query.status is None


def test_list_query_status_enum_coercion() -> None:
    query = EmployeeListQuery(status="terminated")
    assert query.status is EmploymentStatus.TERMINATED


def test_list_query_rejects_bad_page() -> None:
    with pytest.raises(ValidationError):
        EmployeeListQuery(page=0)
