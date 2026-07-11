"""Unit tests for ``EmployeeService`` business logic (repositories mocked).

Covers employee CRUD, search/pagination, employment-status management
(activate / deactivate / exit / rehire), branch / department / designation
assignment, reporting-manager assignment, cross-reference validation, and the
conflict / not-found / validation failure paths. All data access is mocked, so
these exercise the service logic in isolation.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.core.exceptions.base import (
    ConflictException,
    NotFoundException,
    ValidationException,
)
from app.modules.employee.schemas import (
    EmployeeBankDetailCreateRequest,
    EmployeeBankDetailUpdateRequest,
    EmployeeCreateRequest,
    EmployeeDocumentCreateRequest,
    EmployeeExitRequest,
    EmployeeListQuery,
    EmployeePhotoUploadRequest,
    EmployeePromoteRequest,
    EmployeeRehireRequest,
    EmployeeTagCreateRequest,
    EmployeeTerminateRequest,
    EmployeeTransferRequest,
    EmployeeUpdateRequest,
)

_NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Fixtures / builders
# ---------------------------------------------------------------------------


def _employee(**overrides: object) -> SimpleNamespace:
    """A stand-in ``employees`` ORM row with all columns + eager relationships."""
    base: dict[str, object] = {
        "employee_id": 1,
        "org_id": 1,
        "employee_code": "EMP00001",
        "employee_name": "Jane Doe",
        "display_name": None,
        "employee_uid": None,
        "gender": "Female",
        "mobile_country_code": "+91",
        "mobile_number": "9876543210",
        "email": "jane@example.com",
        "address": None,
        "master_branch_id": 1,
        "dept_id": 1,
        "designation_id": 1,
        "employee_type": None,
        "date_of_joining": date(2026, 1, 1),
        "date_of_birth": None,
        "date_of_leaving": None,
        "door_lock_permission": False,
        "pf_account_number": None,
        "uan_number": None,
        "esic_ip_number": None,
        "salary_type": "Monthly",
        "monthly_salary": Decimal("50000.00"),
        "payroll_group_id": None,
        "employment_status": "active",
        "profile_photo_url": None,
        "is_deleted": False,
        "created_by": 1,
        "created_at": _NOW,
        "updated_at": _NOW,
        # eager-loaded relationships
        "master_branch": SimpleNamespace(branch_id=1, branch_name="HQ"),
        "department": SimpleNamespace(dept_id=1, dept_name="Engineering"),
        "designation": SimpleNamespace(designation_id=1, designation_name="Engineer"),
        "bank_details": [],
        "documents": [],
        "emergency_contacts": [],
        "references": [],
        "biometrics": [],
        "punch_branches": [],
        "attendance_permission": None,
        "tags": [],
        "status_history": [],
    }
    base.update(overrides)
    return SimpleNamespace(**base)


@pytest.fixture
def make_employee():
    """Factory returning a fresh stand-in employee row."""
    return _employee


@pytest.fixture
def employee_service():
    """A real :class:`EmployeeService` with every repository replaced by an ``AsyncMock``."""
    from app.modules.employee.service import EmployeeService

    svc = EmployeeService(AsyncMock())
    for attr in (
        "employees",
        "branches",
        "departments",
        "designations",
        "users",
        "status_history",
        "documents",
        "bank_details",
        "emergency_contacts",
        "references",
        "tags",
        "audit",
    ):
        setattr(svc, attr, AsyncMock())
    # Sensible defaults: valid org FKs, race-free code allocation, no collisions.
    svc.branches.exists_active.return_value = True
    svc.departments.exists_active.return_value = True
    svc.designations.exists_active.return_value = True
    svc.employees.allocate_employee_code.return_value = "EMP00001"
    svc.employees.create.return_value = _employee()
    svc.employees.get_detail.return_value = _employee()
    svc.employees.get_active_by_id.return_value = _employee()
    svc.users.email_exists.return_value = False
    svc.users.mobile_exists.return_value = False
    svc.users.get_active_by_id.return_value = SimpleNamespace(name="HR Admin")
    return svc


def _create_payload(**overrides: object) -> EmployeeCreateRequest:
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
    return EmployeeCreateRequest(**base)


# ===========================================================================
# Create employee
# ===========================================================================
async def test_create_employee_success(employee_service) -> None:
    result = await employee_service.create_employee(
        org_id=1, actor_id=9, data=_create_payload(device_ids=[1, 2])
    )
    assert result.employee_code == "EMP00001"
    assert [d.device_id for d in result.device_enrollment] == [1, 2]
    assert all(d.enrollment_status == "Pending" for d in result.device_enrollment)
    employee_service.employees.create.assert_awaited_once()


async def test_create_employee_invalid_branch(employee_service) -> None:
    employee_service.branches.exists_active.return_value = False
    with pytest.raises(ValidationException) as exc:
        await employee_service.create_employee(org_id=1, actor_id=1, data=_create_payload())
    assert exc.value.code == "org_hierarchy_mismatch"


async def test_create_employee_invalid_department(employee_service) -> None:
    employee_service.departments.exists_active.return_value = False
    with pytest.raises(ValidationException) as exc:
        await employee_service.create_employee(org_id=1, actor_id=1, data=_create_payload())
    assert exc.value.code == "org_hierarchy_mismatch"


async def test_create_employee_invalid_designation(employee_service) -> None:
    employee_service.designations.exists_active.return_value = False
    with pytest.raises(ValidationException) as exc:
        await employee_service.create_employee(org_id=1, actor_id=1, data=_create_payload())
    assert exc.value.code == "org_hierarchy_mismatch"


async def test_create_employee_self_service_requires_email(employee_service) -> None:
    data = _create_payload(email=None, create_self_service_user=True)
    with pytest.raises(ValidationException) as exc:
        await employee_service.create_employee(org_id=1, actor_id=1, data=data)
    assert exc.value.code == "SELF_SERVICE_EMAIL_REQUIRED"


async def test_create_employee_self_service_email_conflict(employee_service) -> None:
    employee_service.users.email_exists.return_value = True
    data = _create_payload(email="jane@example.com", create_self_service_user=True)
    with pytest.raises(ConflictException) as exc:
        await employee_service.create_employee(org_id=1, actor_id=1, data=data)
    assert exc.value.code == "USER_EMAIL_EXISTS"


async def test_create_employee_self_service_creates_user(employee_service) -> None:
    data = _create_payload(email="jane@example.com", create_self_service_user=True)
    await employee_service.create_employee(org_id=1, actor_id=1, data=data)
    employee_service.users.create.assert_awaited_once()


async def test_create_employee_salary_gated_out(employee_service) -> None:
    """When the caller cannot set salary, salary fields are excluded from the write."""
    data = _create_payload(salary_type="Monthly", monthly_salary=Decimal("40000"))
    await employee_service.create_employee(
        org_id=1, actor_id=1, data=data, can_set_salary=False
    )
    payload = employee_service.employees.create.await_args.args[0]
    assert "salary_type" not in payload
    assert "monthly_salary" not in payload


async def test_create_employee_uses_concurrency_safe_code_allocation(employee_service) -> None:
    """The auto-generated code comes from the race-free repository allocator."""
    employee_service.employees.allocate_employee_code.return_value = "EMP00007"
    await employee_service.create_employee(org_id=1, actor_id=1, data=_create_payload())
    employee_service.employees.allocate_employee_code.assert_awaited_once()
    payload = employee_service.employees.create.await_args.args[0]
    assert payload["employee_code"] == "EMP00007"


async def test_create_employee_writes_audit(employee_service) -> None:
    """Every create emits an audit row."""
    await employee_service.create_employee(org_id=1, actor_id=9, data=_create_payload())
    employee_service.audit.record.assert_awaited_once()
    kwargs = employee_service.audit.record.await_args.kwargs
    assert kwargs["module"] == "Employee Management"
    assert kwargs["action_type"].value == "Insert"


# ===========================================================================
# Update employee
# ===========================================================================
async def test_update_employee_success(employee_service) -> None:
    result = await employee_service.update_employee(
        org_id=1, actor_id=1, employee_id=1, data=EmployeeUpdateRequest(employee_name="New Name")
    )
    assert result.employee_id == 1
    updates = employee_service.employees.update.await_args.args[1]
    assert updates == {"employee_name": "New Name"}


async def test_update_employee_not_found(employee_service) -> None:
    employee_service.employees.get_active_by_id.return_value = None
    with pytest.raises(NotFoundException):
        await employee_service.update_employee(
            org_id=1, actor_id=1, employee_id=404, data=EmployeeUpdateRequest(employee_name="X Y")
        )


async def test_update_employee_org_reassignment_revalidates(employee_service) -> None:
    employee_service.departments.exists_active.return_value = False
    with pytest.raises(ValidationException) as exc:
        await employee_service.update_employee(
            org_id=1, actor_id=1, employee_id=1, data=EmployeeUpdateRequest(dept_id=99)
        )
    assert exc.value.code == "org_hierarchy_mismatch"


async def test_update_employee_salary_gated_out(employee_service) -> None:
    await employee_service.update_employee(
        org_id=1,
        actor_id=1,
        employee_id=1,
        data=EmployeeUpdateRequest(monthly_salary=Decimal("100")),
        can_set_salary=False,
    )
    updates = employee_service.employees.update.await_args.args[1]
    assert "monthly_salary" not in updates


# ===========================================================================
# Get / list / search / pagination
# ===========================================================================
async def test_get_employee_not_found(employee_service) -> None:
    employee_service.employees.get_detail.return_value = None
    with pytest.raises(NotFoundException):
        await employee_service.get_employee(org_id=1, employee_id=404)


async def test_get_employee_salary_included_when_permitted(employee_service) -> None:
    result = await employee_service.get_employee(org_id=1, employee_id=1, include_salary=True)
    assert result.salary is not None
    assert result.salary.monthly_salary == Decimal("50000.00")


async def test_get_employee_salary_hidden_by_default(employee_service) -> None:
    result = await employee_service.get_employee(org_id=1, employee_id=1, include_salary=False)
    assert result.salary is None


async def test_list_employees_pagination_and_search(employee_service) -> None:
    employee_service.employees.search.return_value = [_employee()]
    employee_service.employees.search_count.return_value = 1
    query = EmployeeListQuery(page=2, page_size=10, q="jane", branch_id=1, status="active")

    result = await employee_service.list_employees(org_id=1, query=query, branch_scope=[1])

    assert result.pagination.page == 2
    assert result.pagination.total_records == 1
    assert len(result.items) == 1
    # The branch scope and filters are forwarded to the repository search.
    kwargs = employee_service.employees.search.await_args.kwargs
    assert kwargs["branch_scope"] == [1]
    assert kwargs["search"] == "jane"
    assert kwargs["status"] == "active"


async def test_search_employees_is_list_alias(employee_service) -> None:
    employee_service.employees.search.return_value = []
    employee_service.employees.search_count.return_value = 0
    result = await employee_service.search_employees(
        org_id=1, query=EmployeeListQuery(page=1, page_size=25)
    )
    assert result.items == []


# ===========================================================================
# Employment-status management
# ===========================================================================
async def test_activate_employee_success(employee_service) -> None:
    employee_service.employees.get_active_by_id.return_value = _employee(
        employment_status="inactive"
    )
    await employee_service.activate_employee(org_id=1, actor_id=9, employee_id=1)
    updates = employee_service.employees.update.await_args.args[1]
    assert updates["employment_status"] == "active"
    employee_service.status_history.create.assert_awaited_once()


async def test_deactivate_employee_success(employee_service) -> None:
    await employee_service.deactivate_employee(org_id=1, actor_id=9, employee_id=1)
    updates = employee_service.employees.update.await_args.args[1]
    assert updates["employment_status"] == "inactive"


async def test_change_status_noop_conflict(employee_service) -> None:
    """Transitioning to the current status is rejected as a conflict."""
    with pytest.raises(ConflictException) as exc:
        await employee_service.activate_employee(org_id=1, actor_id=9, employee_id=1)
    assert exc.value.code == "EMPLOYEE_STATUS_UNCHANGED"


async def test_exit_employee_success(employee_service) -> None:
    data = EmployeeExitRequest(
        resignation_date=date(2026, 3, 1), last_working_day=date(2026, 3, 30), reason="resigned"
    )
    await employee_service.exit_employee(org_id=1, actor_id=9, employee_id=1, data=data)
    updates = employee_service.employees.update.await_args.args[1]
    assert updates["employment_status"] == "terminated"
    assert updates["date_of_leaving"] == date(2026, 3, 30)
    employee_service.status_history.create.assert_awaited_once()


async def test_exit_employee_already_exited(employee_service) -> None:
    employee_service.employees.get_active_by_id.return_value = _employee(
        employment_status="terminated"
    )
    data = EmployeeExitRequest(
        resignation_date=date(2026, 3, 1), last_working_day=date(2026, 3, 30)
    )
    with pytest.raises(ConflictException) as exc:
        await employee_service.exit_employee(org_id=1, actor_id=9, employee_id=1, data=data)
    assert exc.value.code == "EMPLOYEE_ALREADY_EXITED"


async def test_rehire_employee_success(employee_service) -> None:
    employee_service.employees.get_active_by_id.return_value = _employee(
        employment_status="terminated"
    )
    data = EmployeeRehireRequest(date_of_joining=date(2026, 6, 1))
    await employee_service.rehire_employee(org_id=1, actor_id=9, employee_id=1, data=data)
    updates = employee_service.employees.update.await_args.args[1]
    assert updates["employment_status"] == "active"
    assert updates["date_of_joining"] == date(2026, 6, 1)
    assert updates["date_of_leaving"] is None


async def test_rehire_employee_already_active(employee_service) -> None:
    data = EmployeeRehireRequest(date_of_joining=date(2026, 6, 1))
    with pytest.raises(ConflictException) as exc:
        await employee_service.rehire_employee(org_id=1, actor_id=9, employee_id=1, data=data)
    assert exc.value.code == "EMPLOYEE_ALREADY_ACTIVE"


# ===========================================================================
# Org assignment
# ===========================================================================
async def test_assign_branch_success(employee_service) -> None:
    await employee_service.assign_branch(org_id=1, actor_id=9, employee_id=1, branch_id=5)
    updates = employee_service.employees.update.await_args.args[1]
    assert updates == {"master_branch_id": 5}


async def test_assign_branch_invalid(employee_service) -> None:
    employee_service.branches.exists_active.return_value = False
    with pytest.raises(ValidationException) as exc:
        await employee_service.assign_branch(org_id=1, actor_id=9, employee_id=1, branch_id=5)
    assert exc.value.code == "org_hierarchy_mismatch"


async def test_assign_department_success(employee_service) -> None:
    await employee_service.assign_department(org_id=1, actor_id=9, employee_id=1, dept_id=7)
    updates = employee_service.employees.update.await_args.args[1]
    assert updates == {"dept_id": 7}


async def test_assign_department_invalid(employee_service) -> None:
    employee_service.departments.exists_active.return_value = False
    with pytest.raises(ValidationException) as exc:
        await employee_service.assign_department(org_id=1, actor_id=9, employee_id=1, dept_id=7)
    assert exc.value.code == "org_hierarchy_mismatch"


async def test_assign_designation_success(employee_service) -> None:
    await employee_service.assign_designation(
        org_id=1, actor_id=9, employee_id=1, designation_id=3
    )
    updates = employee_service.employees.update.await_args.args[1]
    assert updates == {"designation_id": 3}


async def test_assign_designation_invalid(employee_service) -> None:
    employee_service.designations.exists_active.return_value = False
    with pytest.raises(ValidationException) as exc:
        await employee_service.assign_designation(
            org_id=1, actor_id=9, employee_id=1, designation_id=3
        )
    assert exc.value.code == "org_hierarchy_mismatch"


# ===========================================================================
# Reporting-manager assignment
# ===========================================================================
async def test_assign_reporting_manager_self_rejected(employee_service) -> None:
    with pytest.raises(ConflictException) as exc:
        await employee_service.assign_reporting_manager(
            org_id=1, actor_id=9, employee_id=1, manager_employee_id=1
        )
    assert exc.value.code == "REPORTING_MANAGER_SELF"


async def test_assign_reporting_manager_not_found(employee_service) -> None:
    employee_service.employees.get_reporting_manager.return_value = None
    with pytest.raises(NotFoundException):
        await employee_service.assign_reporting_manager(
            org_id=1, actor_id=9, employee_id=1, manager_employee_id=2
        )


async def test_assign_reporting_manager_unsupported_by_schema(employee_service) -> None:
    """A valid manager reference is validated, then refused (no schema column)."""
    employee_service.employees.get_reporting_manager.return_value = _employee(employee_id=2)
    with pytest.raises(ValidationException) as exc:
        await employee_service.assign_reporting_manager(
            org_id=1, actor_id=9, employee_id=1, manager_employee_id=2
        )
    assert exc.value.code == "REPORTING_MANAGER_NOT_SUPPORTED"


# ===========================================================================
# Documents / photo
# ===========================================================================
async def test_add_document_success(employee_service) -> None:
    row = SimpleNamespace(
        document_id=5,
        document_type="pan_card",
        file_url="s3://bucket/doc.pdf",
        original_filename="pan.pdf",
        file_size_bytes=1024,
        uploaded_by=9,
        created_at=_NOW,
        updated_at=_NOW,
    )
    employee_service.documents.create.return_value = row
    data = EmployeeDocumentCreateRequest(document_type="pan_card", file_url="s3://bucket/doc.pdf")
    result = await employee_service.add_document(
        org_id=1, actor_id=9, employee_id=1, data=data
    )
    assert result.document_id == 5
    employee_service.documents.create.assert_awaited_once()
    employee_service.audit.record.assert_awaited_once()


async def test_add_document_employee_not_found(employee_service) -> None:
    employee_service.employees.get_active_by_id.return_value = None
    data = EmployeeDocumentCreateRequest(document_type="pan_card", file_url="s3://x")
    with pytest.raises(NotFoundException) as exc:
        await employee_service.add_document(org_id=1, actor_id=9, employee_id=404, data=data)
    assert exc.value.code == "not_found"


async def test_set_photo_success(employee_service) -> None:
    data = EmployeePhotoUploadRequest(file_url="s3://bucket/photo.jpg")
    await employee_service.set_photo(org_id=1, actor_id=9, employee_id=1, data=data)
    updates = employee_service.employees.update.await_args.args[1]
    assert updates == {"profile_photo_url": "s3://bucket/photo.jpg"}
    employee_service.audit.record.assert_awaited_once()


# ===========================================================================
# Audit integration on mutations
# ===========================================================================
async def test_update_writes_audit(employee_service) -> None:
    await employee_service.update_employee(
        org_id=1, actor_id=9, employee_id=1, data=EmployeeUpdateRequest(employee_name="New Name")
    )
    assert employee_service.audit.record.await_args.kwargs["action_type"].value == "Update"


async def test_exit_writes_audit(employee_service) -> None:
    data = EmployeeExitRequest(
        resignation_date=date(2026, 3, 1), last_working_day=date(2026, 3, 30)
    )
    await employee_service.exit_employee(org_id=1, actor_id=9, employee_id=1, data=data)
    employee_service.audit.record.assert_awaited_once()


async def test_exit_invalid_dates_service_guard(employee_service) -> None:
    """The service re-checks the exit-date rule and emits the contract code."""
    data = EmployeeExitRequest.model_construct(
        resignation_date=date(2026, 3, 30), last_working_day=date(2026, 3, 1), reason=None
    )
    with pytest.raises(ValidationException) as exc:
        await employee_service.exit_employee(org_id=1, actor_id=9, employee_id=1, data=data)
    assert exc.value.code == "invalid_exit_dates"


# ===========================================================================
# Status lifecycle — terminate (#31) and the terminal-status rule (§9)
# ===========================================================================
async def test_activate_terminated_employee_conflict_409(employee_service) -> None:
    """`terminated` is terminal: terminated → active via activate is a 409."""
    employee_service.employees.get_active_by_id.return_value = _employee(
        employment_status="terminated"
    )
    with pytest.raises(ConflictException) as exc:
        await employee_service.activate_employee(org_id=1, actor_id=9, employee_id=1)
    assert exc.value.code == "EMPLOYEE_ALREADY_TERMINATED"
    assert exc.value.status_code == 409
    employee_service.employees.update.assert_not_awaited()
    employee_service.status_history.create.assert_not_awaited()


async def test_deactivate_terminated_employee_conflict_409(employee_service) -> None:
    """`terminated` is terminal: terminated → inactive is also rejected."""
    employee_service.employees.get_active_by_id.return_value = _employee(
        employment_status="terminated"
    )
    with pytest.raises(ConflictException) as exc:
        await employee_service.deactivate_employee(org_id=1, actor_id=9, employee_id=1)
    assert exc.value.code == "EMPLOYEE_ALREADY_TERMINATED"


async def test_activate_records_effective_date_in_history(employee_service) -> None:
    """Activate forwards the requested effective date into the history row."""
    employee_service.employees.get_active_by_id.return_value = _employee(
        employment_status="inactive"
    )
    await employee_service.activate_employee(
        org_id=1, actor_id=9, employee_id=1, effective_date=date(2026, 4, 1), reason="rejoined"
    )
    history = employee_service.status_history.create.await_args.args[0]
    assert history["effective_date"] == date(2026, 4, 1)
    assert history["previous_status"] == "inactive"
    assert history["new_status"] == "active"
    assert history["reason"] == "rejoined"


async def test_terminate_employee_success(employee_service) -> None:
    """Terminate sets status + date_of_leaving and appends the history row."""
    data = EmployeeTerminateRequest(
        effective_date=date(2026, 5, 1), date_of_leaving=date(2026, 5, 15), reason="misconduct"
    )
    await employee_service.terminate_employee(org_id=1, actor_id=9, employee_id=1, data=data)
    updates = employee_service.employees.update.await_args.args[1]
    assert updates["employment_status"] == "terminated"
    assert updates["date_of_leaving"] == date(2026, 5, 15)
    history = employee_service.status_history.create.await_args.args[0]
    assert history["previous_status"] == "active"
    assert history["new_status"] == "terminated"
    assert history["effective_date"] == date(2026, 5, 1)
    employee_service.audit.record.assert_awaited_once()


async def test_terminate_defaults_date_of_leaving_to_effective_date(employee_service) -> None:
    data = EmployeeTerminateRequest(effective_date=date(2026, 5, 1))
    await employee_service.terminate_employee(org_id=1, actor_id=9, employee_id=1, data=data)
    updates = employee_service.employees.update.await_args.args[1]
    assert updates["date_of_leaving"] == date(2026, 5, 1)


async def test_terminate_already_terminated_conflict_409(employee_service) -> None:
    employee_service.employees.get_active_by_id.return_value = _employee(
        employment_status="terminated"
    )
    data = EmployeeTerminateRequest(effective_date=date(2026, 5, 1))
    with pytest.raises(ConflictException) as exc:
        await employee_service.terminate_employee(org_id=1, actor_id=9, employee_id=1, data=data)
    assert exc.value.code == "EMPLOYEE_ALREADY_TERMINATED"
    assert exc.value.status_code == 409


# ===========================================================================
# Transfer (#32) / Promote (#33)
# ===========================================================================
async def test_transfer_employee_updates_fks_and_audits(employee_service) -> None:
    data = EmployeeTransferRequest(
        master_branch_id=5, dept_id=7, effective_date=date(2026, 4, 1), reason="restructure"
    )
    await employee_service.transfer_employee(org_id=1, actor_id=9, employee_id=1, data=data)
    updates = employee_service.employees.update.await_args.args[1]
    assert updates == {"master_branch_id": 5, "dept_id": 7}
    # Context (reason / effective date) is captured in the Activity Log only (§9).
    description = employee_service.audit.record.await_args.kwargs["description"]
    assert "2026-04-01" in description
    assert "restructure" in description
    employee_service.status_history.create.assert_not_awaited()


async def test_transfer_employee_unknown_branch_404(employee_service) -> None:
    employee_service.branches.exists_active.return_value = False
    data = EmployeeTransferRequest(master_branch_id=99)
    with pytest.raises(NotFoundException) as exc:
        await employee_service.transfer_employee(org_id=1, actor_id=9, employee_id=1, data=data)
    assert exc.value.code == "BRANCH_NOT_FOUND"


async def test_transfer_employee_unknown_department_404(employee_service) -> None:
    employee_service.departments.exists_active.return_value = False
    data = EmployeeTransferRequest(dept_id=99)
    with pytest.raises(NotFoundException) as exc:
        await employee_service.transfer_employee(org_id=1, actor_id=9, employee_id=1, data=data)
    assert exc.value.code == "DEPARTMENT_NOT_FOUND"


def test_transfer_request_requires_a_target() -> None:
    with pytest.raises(ValueError):
        EmployeeTransferRequest(reason="no targets")


async def test_promote_employee_success(employee_service) -> None:
    data = EmployeePromoteRequest(designation_id=3, monthly_salary=Decimal("60000"))
    await employee_service.promote_employee(org_id=1, actor_id=9, employee_id=1, data=data)
    updates = employee_service.employees.update.await_args.args[1]
    assert updates == {"designation_id": 3, "monthly_salary": Decimal("60000")}
    employee_service.audit.record.assert_awaited_once()


async def test_promote_employee_salary_gated_out(employee_service) -> None:
    """Without the salary permission the designation changes but pay does not."""
    data = EmployeePromoteRequest(designation_id=3, monthly_salary=Decimal("60000"))
    await employee_service.promote_employee(
        org_id=1, actor_id=9, employee_id=1, data=data, can_set_salary=False
    )
    updates = employee_service.employees.update.await_args.args[1]
    assert updates == {"designation_id": 3}


async def test_promote_employee_unknown_designation_404(employee_service) -> None:
    employee_service.designations.exists_active.return_value = False
    data = EmployeePromoteRequest(designation_id=99)
    with pytest.raises(NotFoundException) as exc:
        await employee_service.promote_employee(org_id=1, actor_id=9, employee_id=1, data=data)
    assert exc.value.code == "DESIGNATION_NOT_FOUND"


# ===========================================================================
# Bank details (§8.1)
# ===========================================================================
def _bank_row(**overrides: object) -> SimpleNamespace:
    base: dict[str, object] = {
        "bank_detail_id": 3,
        "employee_id": 1,
        "bank_name": "HDFC",
        "bank_branch_name": "MG Road",
        "account_number": "1234567890",
        "ifsc_code": "HDFC0001234",
        "is_primary": True,
        "is_deleted": False,
        "created_at": _NOW,
        "updated_at": _NOW,
    }
    base.update(overrides)
    return SimpleNamespace(**base)


async def test_add_bank_detail_primary_demotes_existing(employee_service) -> None:
    employee_service.bank_details.create.return_value = _bank_row()
    data = EmployeeBankDetailCreateRequest(
        bank_name="HDFC", account_number="1234567890", ifsc_code="HDFC0001234", is_primary=True
    )
    result = await employee_service.add_bank_detail(
        org_id=1, actor_id=9, employee_id=1, data=data
    )
    assert result.bank_detail_id == 3
    employee_service.bank_details.unset_primary.assert_awaited_once_with(1)
    payload = employee_service.bank_details.create.await_args.args[0]
    assert payload["employee_id"] == 1
    assert payload["is_primary"] is True
    employee_service.audit.record.assert_awaited_once()


async def test_add_bank_detail_non_primary_keeps_existing_primary(employee_service) -> None:
    employee_service.bank_details.create.return_value = _bank_row(is_primary=False)
    data = EmployeeBankDetailCreateRequest(bank_name="HDFC", is_primary=False)
    await employee_service.add_bank_detail(org_id=1, actor_id=9, employee_id=1, data=data)
    employee_service.bank_details.unset_primary.assert_not_awaited()


async def test_update_bank_detail_not_found_404(employee_service) -> None:
    employee_service.bank_details.get_by_id_in_org.return_value = None
    with pytest.raises(NotFoundException) as exc:
        await employee_service.update_bank_detail(
            org_id=1,
            actor_id=9,
            employee_id=1,
            bank_detail_id=404,
            data=EmployeeBankDetailUpdateRequest(bank_name="ICICI"),
        )
    assert exc.value.code == "BANK_DETAIL_NOT_FOUND"


async def test_delete_bank_detail_is_soft(employee_service) -> None:
    """Delete sets is_deleted=true (soft) rather than removing the row."""
    row = _bank_row()
    employee_service.bank_details.get_by_id_in_org.return_value = row
    await employee_service.delete_bank_detail(
        org_id=1, actor_id=9, employee_id=1, bank_detail_id=3
    )
    updates = employee_service.bank_details.update.await_args.args[1]
    assert updates == {"is_deleted": True}
    employee_service.bank_details.delete.assert_not_awaited()
    employee_service.audit.record.assert_awaited_once()


# ===========================================================================
# Tags (§8.4 — hard delete) and status history (§8.5)
# ===========================================================================
async def test_delete_tag_is_hard(employee_service) -> None:
    row = SimpleNamespace(tag_id=4, tag_label="Star", is_status_tag=False)
    employee_service.tags.get_by_id_in_org.return_value = row
    await employee_service.delete_tag(org_id=1, actor_id=9, employee_id=1, tag_id=4)
    employee_service.tags.delete.assert_awaited_once_with(row)
    employee_service.tags.update.assert_not_awaited()


async def test_add_tag_stamps_creator(employee_service) -> None:
    employee_service.tags.create.return_value = SimpleNamespace(
        tag_id=4,
        tag_label="Star",
        tag_color="#ff0000",
        is_status_tag=False,
        created_by=9,
        created_at=_NOW,
        updated_at=_NOW,
    )
    data = EmployeeTagCreateRequest(tag_label="Star", tag_color="#ff0000")
    result = await employee_service.add_tag(org_id=1, actor_id=9, employee_id=1, data=data)
    assert result.created_by == 9
    payload = employee_service.tags.create.await_args.args[0]
    assert payload["created_by"] == 9


async def test_list_status_history_scoped_to_employee(employee_service) -> None:
    employee_service.status_history.list_for_employee.return_value = [
        SimpleNamespace(
            status_history_id=1,
            previous_status=None,
            new_status="active",
            changed_by=9,
            reason=None,
            effective_date=date(2026, 1, 1),
            created_at=_NOW,
        )
    ]
    result = await employee_service.list_status_history(org_id=1, employee_id=1)
    assert len(result) == 1
    assert result[0].new_status == "active"
    employee_service.status_history.list_for_employee.assert_awaited_once_with(1, 1)
