from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.core.exceptions.base import ConflictException
from app.modules.organization.exceptions import (
    DepartmentInUseException,
    DepartmentNotFoundException,
)
from app.modules.organization.service import DepartmentService
from app.modules.organization.schemas import DepartmentCreateRequest, DepartmentUpdateRequest, DepartmentSearchQuery


@pytest.fixture
def mock_session() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def department_service(mock_session) -> DepartmentService:
    svc = DepartmentService(mock_session)
    svc.departments = AsyncMock()
    svc.users = AsyncMock()
    svc.audit = AsyncMock()
    return svc


def _dept(dept_id: int = 1, name: str = "Engineering", is_active: bool = True, is_deleted: bool = False, employee_count: int = 0) -> SimpleNamespace:
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    return SimpleNamespace(
        dept_id=dept_id,
        org_id=1,
        dept_name=name,
        is_active=is_active,
        is_deleted=is_deleted,
        created_by=2,
        created_at=now,
        updated_at=now,
        employee_count=employee_count,
    )


async def test_list_departments(department_service) -> None:
    dept1 = _dept(1, "Engineering", employee_count=5)
    dept2 = _dept(2, "Design", employee_count=0)
    
    department_service.departments.search.return_value = [dept1, dept2]
    department_service.departments.search_count.return_value = 2

    query = DepartmentSearchQuery(page=1, page_size=25)
    result = await department_service.list_departments(org_id=1, query=query)

    assert result.pagination.total_records == 2
    assert result.items[0].dept_id == 1
    assert result.items[0].employee_count == 5
    assert result.items[1].dept_id == 2
    assert result.items[1].employee_count == 0


async def test_delete_department_success(department_service) -> None:
    dept = _dept(1, "Engineering")
    department_service.departments.get_by_id_in_org.return_value = dept
    department_service.departments.has_active_employees.return_value = False
    
    # Mock user details for auditing
    department_service.users.get_active_by_id.return_value = SimpleNamespace(name="Admin User")

    # Mock update to return modified dept
    async def fake_update(obj, updates):
        for k, v in updates.items():
            setattr(obj, k, v)
        return obj
    department_service.departments.update.side_effect = fake_update

    result = await department_service.delete_department(org_id=1, actor_id=2, dept_id=1)
    
    assert result.is_deleted is True
    department_service.departments.update.assert_awaited_once_with(dept, {"is_deleted": True})
    department_service.audit.record.assert_awaited_once()


async def test_delete_department_in_use_raises_error(department_service) -> None:
    dept = _dept(1, "Engineering")
    department_service.departments.get_by_id_in_org.return_value = dept
    department_service.departments.has_active_employees.return_value = True

    with pytest.raises(DepartmentInUseException):
        await department_service.delete_department(org_id=1, actor_id=2, dept_id=1)

    department_service.departments.update.assert_not_awaited()
    department_service.audit.record.assert_not_awaited()


async def test_delete_department_not_found_raises_error(department_service) -> None:
    department_service.departments.get_by_id_in_org.return_value = None

    with pytest.raises(DepartmentNotFoundException):
        await department_service.delete_department(org_id=1, actor_id=2, dept_id=99)

    department_service.departments.update.assert_not_awaited()
    department_service.audit.record.assert_not_awaited()
