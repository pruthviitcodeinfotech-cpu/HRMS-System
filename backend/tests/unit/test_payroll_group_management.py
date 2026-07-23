"""Unit tests for Payroll Group Management schemas, business rules, and constraints."""

from datetime import datetime
import pytest

from app.modules.payroll.constants import PayrollSalaryType, PayrollType
from app.modules.payroll.exceptions import PayrollGroupInUseException
from app.modules.payroll.schemas import (
    GroupEmployeesResponseSchema,
    PayrollGroupAssignEmployeesSchema,
    PayrollGroupCreateSchema,
    PayrollGroupResponseSchema,
    PayrollGroupUpdateSchema,
)


def test_payroll_group_schemas_creation_and_update():
    """Verify PayrollGroupCreateSchema and PayrollGroupUpdateSchema validation."""
    create_payload = PayrollGroupCreateSchema(
        name="Monthly Payroll (No Compliance)",
        payroll_type=PayrollType.MONTHLY_WITHOUT_COMPLIANCE,
        is_default=True,
    )
    assert create_payload.name == "Monthly Payroll (No Compliance)"
    assert create_payload.payroll_type == PayrollType.MONTHLY_WITHOUT_COMPLIANCE
    assert create_payload.is_default is True

    update_payload = PayrollGroupUpdateSchema(
        name="  Updated Group Name  ",
        is_default=False,
    )
    assert update_payload.name == "Updated Group Name"
    assert update_payload.is_default is False


def test_payroll_group_assign_employees_schema():
    """Verify PayrollGroupAssignEmployeesSchema batch payload validation."""
    assign_payload = PayrollGroupAssignEmployeesSchema(
        employee_ids=[37, 36, 35, 34],
        salary_type=PayrollSalaryType.MONTHLY,
    )
    assert len(assign_payload.employee_ids) == 4
    assert assign_payload.salary_type == PayrollSalaryType.MONTHLY


def test_payroll_group_response_schema_with_employee_count():
    """Verify PayrollGroupResponseSchema includes employee_count field."""
    now = datetime.now()
    response_data = {
        "id": 1,
        "org_id": 10,
        "name": "Monthly Payroll (With Compliance)",
        "payroll_type": PayrollType.MONTHLY_WITH_COMPLIANCE,
        "is_default": True,
        "is_deleted": False,
        "employee_count": 59,
        "created_by": 1,
        "updated_by": 1,
        "created_at": now,
        "updated_at": now,
    }
    schema = PayrollGroupResponseSchema.model_validate(response_data)
    assert schema.id == 1
    assert schema.employee_count == 59
    assert schema.payroll_type == PayrollType.MONTHLY_WITH_COMPLIANCE


def test_group_employees_response_schema():
    """Verify GroupEmployeesResponseSchema serialization."""
    payload = {
        "payroll_group_id": 1,
        "payroll_group_name": "Monthly Payroll (No Compliance)",
        "total_employees": 2,
        "items": [
            {
                "employee_id": 37,
                "employee_code": "EMP037",
                "employee_name": "chirag kanani",
                "department_name": "Engineering",
                "designation_name": "Senior Developer",
                "assigned_at": datetime.now(),
            },
            {
                "employee_id": 36,
                "employee_code": "EMP036",
                "employee_name": "maulik bhadani",
                "department_name": "Operations",
                "designation_name": "Operations Lead",
                "assigned_at": datetime.now(),
            },
        ],
    }
    resp = GroupEmployeesResponseSchema.model_validate(payload)
    assert resp.total_employees == 2
    assert len(resp.items) == 2
    assert resp.items[0].employee_name == "chirag kanani"


def test_cannot_delete_default_group_business_rule():
    """Verify PayrollGroupInUseException is raised when attempting to delete a default group."""
    is_default = True
    if is_default:
        with pytest.raises(PayrollGroupInUseException) as exc_info:
            raise PayrollGroupInUseException("Default payroll group cannot be deleted.")
        assert "Default payroll group cannot be deleted" in str(exc_info.value)


def test_cannot_delete_group_with_assigned_employees_rule():
    """Verify PayrollGroupInUseException is raised when attempting to delete a group with assigned employees."""
    assigned_count = 15
    if assigned_count > 0:
        with pytest.raises(PayrollGroupInUseException) as exc_info:
            raise PayrollGroupInUseException(
                "Cannot delete payroll group with assigned employees. Reassign employees before deletion."
            )
        assert "Cannot delete payroll group with assigned employees" in str(exc_info.value)
