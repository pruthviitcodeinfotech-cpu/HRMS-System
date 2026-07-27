"""Unit tests for Phase 1.1 — Branch Architecture Fixes.

Verifies:
1. Department creation requires a mandatory branch_id.
2. Designation creation requires a mandatory branch_id.
3. Department name uniqueness is enforced per branch (same name allowed across different branches).
4. Designation name uniqueness is enforced per branch (same name allowed across different branches).
5. Branch name uniqueness is enforced per organization (same name allowed across different orgs).
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.modules.organization.exceptions import (
    BranchNameExistsException,
    BranchNotFoundException,
    BranchRequiredException,
    DepartmentNameExistsException,
    DesignationNameExistsException,
)
from app.modules.organization.schemas import (
    BranchCreateRequest,
    BranchUpdateRequest,
    DepartmentCreateRequest,
    DepartmentUpdateRequest,
    DesignationCreateRequest,
    DesignationUpdateRequest,
)
from app.modules.organization.service import (
    BranchService,
    DepartmentService,
    DesignationService,
)


@pytest.fixture
def session() -> AsyncMock:
    sess = AsyncMock()
    sess.add = MagicMock()
    sess.flush = AsyncMock()
    sess.refresh = AsyncMock()
    sess.commit = AsyncMock()
    sess.rollback = AsyncMock()
    return sess


# ===========================================================================
# 1. Branch Duplicate Prevention Tests (Issue 5)
# ===========================================================================


@pytest.mark.asyncio
async def test_create_branch_duplicate_name_raises_conflict(session: AsyncMock) -> None:
    svc = BranchService(session)
    svc.branches.name_exists = AsyncMock(return_value=True)

    payload = BranchCreateRequest(branch_name="Surat")

    with pytest.raises(BranchNameExistsException):
        await svc.create_branch(org_id=1, actor_id=10, data=payload)

    svc.branches.name_exists.assert_awaited_once_with(1, "Surat")


@pytest.mark.asyncio
async def test_create_branch_success(session: AsyncMock) -> None:
    svc = BranchService(session)
    svc.branches.name_exists = AsyncMock(return_value=False)

    mock_branch = MagicMock(
        branch_id=101,
        org_id=1,
        branch_name="Surat",
        logo_url=None,
        gstin=None,
        mobile_number=None,
        address=None,
        landmark=None,
        pin_code=None,
        city="Surat",
        state=None,
        country=None,
        industry_type=None,
        latitude=None,
        longitude=None,
        allowed_radius_meters=None,
        is_active=True,
        is_deleted=False,
        employee_count=0,
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
    )
    svc.branches.create = AsyncMock(return_value=mock_branch)
    svc._audit = AsyncMock()

    payload = BranchCreateRequest(branch_name="Surat", city="Surat")
    res = await svc.create_branch(org_id=1, actor_id=10, data=payload)

    assert res.branch_id == 101
    assert res.branch_name == "Surat"


# ===========================================================================
# 2. Department Mandatory branch_id & Uniqueness Tests (Issues 1 & 3)
# ===========================================================================


@pytest.mark.asyncio
async def test_create_department_missing_branch_id_raises_error(session: AsyncMock) -> None:
    svc = DepartmentService(session)

    payload = DepartmentCreateRequest(dept_name="Engineering")

    with pytest.raises(BranchRequiredException):
        await svc.create_department(org_id=1, actor_id=10, data=payload, branch_id=None)


@pytest.mark.asyncio
async def test_create_department_invalid_branch_id_raises_404(session: AsyncMock) -> None:
    svc = DepartmentService(session)
    svc.branches.get_by_id_in_org = AsyncMock(return_value=None)

    payload = DepartmentCreateRequest(branch_id=999, dept_name="Engineering")

    with pytest.raises(BranchNotFoundException):
        await svc.create_department(org_id=1, actor_id=10, data=payload)

    svc.branches.get_by_id_in_org.assert_awaited_once_with(1, 999)


@pytest.mark.asyncio
async def test_create_department_duplicate_name_in_same_branch_raises_conflict(session: AsyncMock) -> None:
    svc = DepartmentService(session)
    svc.branches.get_by_id_in_org = AsyncMock(return_value=MagicMock(branch_id=5))
    svc.departments.name_exists = AsyncMock(return_value=True)

    payload = DepartmentCreateRequest(branch_id=5, dept_name="Engineering")

    with pytest.raises(DepartmentNameExistsException):
        await svc.create_department(org_id=1, actor_id=10, data=payload)

    svc.departments.name_exists.assert_awaited_once_with(5, "Engineering")


@pytest.mark.asyncio
async def test_create_department_success(session: AsyncMock) -> None:
    svc = DepartmentService(session)
    svc.branches.get_by_id_in_org = AsyncMock(return_value=MagicMock(branch_id=5))
    svc.departments.name_exists = AsyncMock(return_value=False)

    mock_dept = MagicMock(
        dept_id=201,
        org_id=1,
        branch_id=5,
        dept_name="Engineering",
        is_active=True,
        is_deleted=False,
        created_by=10,
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
        employee_count=0,
    )
    svc.departments.create = AsyncMock(return_value=mock_dept)
    svc._audit = AsyncMock()

    payload = DepartmentCreateRequest(branch_id=5, dept_name="Engineering")
    res = await svc.create_department(org_id=1, actor_id=10, data=payload)

    assert res.dept_id == 201
    assert res.branch_id == 5
    assert res.dept_name == "Engineering"


# ===========================================================================
# 3. Designation Mandatory branch_id & Uniqueness Tests (Issues 2 & 4)
# ===========================================================================


@pytest.mark.asyncio
async def test_create_designation_missing_branch_id_raises_error(session: AsyncMock) -> None:
    svc = DesignationService(session)

    payload = DesignationCreateRequest(designation_name="Software Engineer")

    with pytest.raises(BranchRequiredException):
        await svc.create_designation(org_id=1, actor_id=10, data=payload, branch_id=None)


@pytest.mark.asyncio
async def test_create_designation_invalid_branch_id_raises_404(session: AsyncMock) -> None:
    svc = DesignationService(session)
    svc.branches.get_by_id_in_org = AsyncMock(return_value=None)

    payload = DesignationCreateRequest(branch_id=888, designation_name="Software Engineer")

    with pytest.raises(BranchNotFoundException):
        await svc.create_designation(org_id=1, actor_id=10, data=payload)

    svc.branches.get_by_id_in_org.assert_awaited_once_with(1, 888)


@pytest.mark.asyncio
async def test_create_designation_duplicate_name_in_same_branch_raises_conflict(session: AsyncMock) -> None:
    svc = DesignationService(session)
    svc.branches.get_by_id_in_org = AsyncMock(return_value=MagicMock(branch_id=5))
    svc.designations.name_exists = AsyncMock(return_value=True)

    payload = DesignationCreateRequest(branch_id=5, designation_name="Software Engineer")

    with pytest.raises(DesignationNameExistsException):
        await svc.create_designation(org_id=1, actor_id=10, data=payload)

    svc.designations.name_exists.assert_awaited_once_with(5, "Software Engineer")


@pytest.mark.asyncio
async def test_create_designation_success(session: AsyncMock) -> None:
    svc = DesignationService(session)
    svc.branches.get_by_id_in_org = AsyncMock(return_value=MagicMock(branch_id=5))
    svc.designations.name_exists = AsyncMock(return_value=False)

    mock_desig = MagicMock(
        designation_id=301,
        org_id=1,
        branch_id=5,
        designation_name="Software Engineer",
        is_active=True,
        is_deleted=False,
        created_by=10,
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
        employee_count=0,
    )
    svc.designations.create = AsyncMock(return_value=mock_desig)
    svc._audit = AsyncMock()

    payload = DesignationCreateRequest(branch_id=5, designation_name="Software Engineer")
    res = await svc.create_designation(org_id=1, actor_id=10, data=payload)

    assert res.designation_id == 301
    assert res.branch_id == 5
    assert res.designation_name == "Software Engineer"
