"""Unit tests for DesignationService.

Covers:
  - list_designations returns employee_count from repository
  - delete_designation success path (soft-delete + audit)
  - delete_designation blocked when active employees exist (DesignationInUseException)
  - delete_designation raises DesignationNotFoundException for unknown ids
"""
from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.modules.organization.exceptions import (
    DesignationInUseException,
    DesignationNotFoundException,
)
from app.modules.organization.schemas import DesignationCreateRequest, DesignationSearchQuery
from app.modules.organization.service import DesignationService


@pytest.fixture
def mock_session() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def designation_service(mock_session) -> DesignationService:
    svc = DesignationService(mock_session)
    svc.designations = AsyncMock()
    svc.users = AsyncMock()
    svc.audit = AsyncMock()
    return svc


def _desig(
    designation_id: int = 1,
    name: str = "Engineering Lead",
    is_active: bool = True,
    is_deleted: bool = False,
    employee_count: int = 0,
) -> SimpleNamespace:
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    return SimpleNamespace(
        designation_id=designation_id,
        org_id=1,
        designation_name=name,
        is_active=is_active,
        is_deleted=is_deleted,
        created_by=2,
        created_at=now,
        updated_at=now,
        employee_count=employee_count,
    )


# ---------------------------------------------------------------------------
# list_designations — employee_count propagation
# ---------------------------------------------------------------------------


async def test_list_designations_returns_employee_count(designation_service) -> None:
    d1 = _desig(1, "Engineering Lead", employee_count=7)
    d2 = _desig(2, "Sales Manager", employee_count=0)

    designation_service.designations.search.return_value = [d1, d2]
    designation_service.designations.search_count.return_value = 2

    query = DesignationSearchQuery(page=1, page_size=25)
    result = await designation_service.list_designations(org_id=1, query=query)

    assert result.pagination.total_records == 2
    assert result.items[0].designation_id == 1
    assert result.items[0].employee_count == 7
    assert result.items[1].designation_id == 2
    assert result.items[1].employee_count == 0


# ---------------------------------------------------------------------------
# delete_designation — success
# ---------------------------------------------------------------------------


async def test_delete_designation_success(designation_service) -> None:
    desig = _desig(1, "Engineering Lead")
    designation_service.designations.get_by_id_in_org.return_value = desig
    designation_service.designations.has_active_employees.return_value = False
    designation_service.users.get_active_by_id.return_value = SimpleNamespace(name="Admin")

    async def fake_update(obj, updates):
        for k, v in updates.items():
            setattr(obj, k, v)
        return obj

    designation_service.designations.update.side_effect = fake_update

    result = await designation_service.delete_designation(org_id=1, actor_id=2, designation_id=1)

    assert result.is_deleted is True
    designation_service.designations.update.assert_awaited_once_with(desig, {"is_deleted": True})
    designation_service.audit.record.assert_awaited_once()


# ---------------------------------------------------------------------------
# delete_designation — blocked when in use
# ---------------------------------------------------------------------------


async def test_delete_designation_in_use_raises_error(designation_service) -> None:
    desig = _desig(1, "Engineering Lead")
    designation_service.designations.get_by_id_in_org.return_value = desig
    designation_service.designations.has_active_employees.return_value = True

    with pytest.raises(DesignationInUseException):
        await designation_service.delete_designation(org_id=1, actor_id=2, designation_id=1)

    designation_service.designations.update.assert_not_awaited()
    designation_service.audit.record.assert_not_awaited()


# ---------------------------------------------------------------------------
# delete_designation — not found
# ---------------------------------------------------------------------------


async def test_delete_designation_not_found_raises_error(designation_service) -> None:
    designation_service.designations.get_by_id_in_org.return_value = None

    with pytest.raises(DesignationNotFoundException):
        await designation_service.delete_designation(org_id=1, actor_id=2, designation_id=99)

    designation_service.designations.update.assert_not_awaited()
    designation_service.audit.record.assert_not_awaited()
