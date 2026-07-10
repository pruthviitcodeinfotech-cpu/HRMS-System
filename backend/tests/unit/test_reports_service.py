"""Unit tests for ``ReportsService`` business logic (repositories mocked)."""

from __future__ import annotations

import datetime
from unittest.mock import AsyncMock, patch

import pytest

from app.core.dependencies.auth import CurrentUser
from app.core.exceptions.base import AuthorizationException, NotFoundException
from app.core.security.permissions import build_effective_permissions
from app.modules.reports.schemas import EmployeeMasterReportResponse, ReportQueryRequest
from app.modules.reports.service import ReportsService


def _principal(
    *,
    is_super_admin: bool = False,
    org_id: int = 1,
    branch_ids=(),
    department_ids=(),
    perms=None,
) -> CurrentUser:
    permissions = build_effective_permissions(
        is_super_admin=is_super_admin,
        feature_rows=perms or [],
        branch_ids=list(branch_ids),
        department_ids=list(department_ids),
    )
    return CurrentUser(
        user_id=1,
        org_id=org_id,
        is_super_admin=is_super_admin,
        is_active=True,
        permissions=permissions,
    )


def _perm(feature_key: str, **flags: bool) -> dict[str, object]:
    base = {
        "feature_key": feature_key,
        "can_create": False,
        "can_read": False,
        "can_edit": False,
        "can_delete": False,
    }
    base.update(flags)
    return base


@pytest.fixture
def mock_cache():
    """Mock Redis cache get/set functions."""
    with (
        patch("app.modules.reports.service.cache_get_json", new_callable=AsyncMock) as mock_get,
        patch("app.modules.reports.service.cache_set_json", new_callable=AsyncMock) as mock_set,
    ):
        mock_get.return_value = None
        yield mock_get, mock_set


@pytest.fixture
def reports_service():
    """Create ReportsService instance with mocked repository."""
    session = AsyncMock()
    service = ReportsService(session)
    service.repo = AsyncMock()
    return service


# ===========================================================================
# 1. Authorization & Permission tests
# ===========================================================================


@pytest.mark.asyncio
async def test_missing_reports_permission(reports_service) -> None:
    # User has employee read, but not general reports permission
    user = _principal(perms=[_perm("employee", can_read=True)])
    query = ReportQueryRequest()

    with pytest.raises(AuthorizationException) as exc:
        await reports_service.get_employee_master_report(org_id=1, user=user, query=query)
    assert "Missing permission 'reports:read'" in str(exc.value)


@pytest.mark.asyncio
async def test_missing_source_permission(reports_service) -> None:
    # User has reports read, but not employee read permission
    user = _principal(perms=[_perm("reports", can_read=True)])
    query = ReportQueryRequest()

    with pytest.raises(AuthorizationException) as exc:
        await reports_service.get_employee_master_report(org_id=1, user=user, query=query)
    assert "Missing permission 'employee:read'" in str(exc.value)


# ===========================================================================
# 2. Scope isolation tests
# ===========================================================================


@pytest.mark.asyncio
async def test_scope_isolation_super_admin(reports_service) -> None:
    user = _principal(is_super_admin=True)
    query = ReportQueryRequest(format="json")

    reports_service.repo.get_employee_master_report.return_value = ([], 0)

    res = await reports_service.get_employee_master_report(org_id=1, user=user, query=query)
    assert isinstance(res, EmployeeMasterReportResponse)

    reports_service.repo.get_employee_master_report.assert_called_once_with(
        org_id=1,
        branch_ids=None,
        dept_ids=None,
        sort_by=None,
        sort_dir="asc",
        page=1,
        page_size=25,
        designation_id=None,
        status=None,
    )


@pytest.mark.asyncio
async def test_scope_isolation_scoped_user(reports_service) -> None:
    user = _principal(
        perms=[_perm("reports", can_read=True), _perm("employee", can_read=True)],
        branch_ids=(10, 20),
        department_ids=(30,),
    )
    query = ReportQueryRequest(format="json")

    reports_service.repo.get_employee_master_report.return_value = ([], 0)

    await reports_service.get_employee_master_report(org_id=1, user=user, query=query)

    reports_service.repo.get_employee_master_report.assert_called_once_with(
        org_id=1,
        branch_ids=[10, 20],
        dept_ids=[30],
        sort_by=None,
        sort_dir="asc",
        page=1,
        page_size=25,
        designation_id=None,
        status=None,
    )


@pytest.mark.asyncio
async def test_scope_violation_raises_exception(reports_service) -> None:
    user = _principal(
        perms=[_perm("reports", can_read=True), _perm("employee", can_read=True)],
        branch_ids=(10,),
    )
    # Requesting branch 20 which is not permitted
    query = ReportQueryRequest(branch_id=20)

    with pytest.raises(AuthorizationException) as exc:
        await reports_service.get_employee_master_report(org_id=1, user=user, query=query)
    assert "Missing branch access permission" in str(exc.value)


# ===========================================================================
# 3. Export & Job handling tests
# ===========================================================================


@pytest.mark.asyncio
async def test_synchronous_csv_export(reports_service) -> None:
    user = _principal(
        perms=[_perm("reports", can_read=True), _perm("employee", can_read=True)],
    )
    query = ReportQueryRequest(format="csv")

    mock_row = {"code": "EMP01", "name": "John Doe"}
    reports_service.repo.get_employee_master_report.return_value = ([mock_row], 1)

    res = await reports_service.get_employee_master_report(org_id=1, user=user, query=query)
    assert isinstance(res, dict)
    assert "file_bytes" in res
    assert res["media_type"] == "text/csv"
    assert b"code,name" in res["file_bytes"]
    assert b"EMP01,John Doe" in res["file_bytes"]


@pytest.mark.asyncio
async def test_asynchronous_export_trigger(reports_service, mock_cache) -> None:
    mock_get, mock_set = mock_cache
    user = _principal(
        perms=[_perm("reports", can_read=True), _perm("employee", can_read=True)],
    )
    query = ReportQueryRequest(format="csv")

    # Simulate large result set
    reports_service.repo.get_employee_master_report.return_value = ([], 1500)

    res = await reports_service.get_employee_master_report(org_id=1, user=user, query=query)
    # Should return an ExportJobStatusResponse
    assert res.status == "pending"
    assert res.export_job_id is not None

    mock_set.assert_called_with(
        f"export_job:{res.export_job_id}",
        {
            "export_job_id": res.export_job_id,
            "status": "pending",
            "download_url": None,
            "expires_at": res.expires_at.isoformat(),
        },
        ttl=3600,
    )


@pytest.mark.asyncio
async def test_get_export_job_status_not_found(reports_service, mock_cache) -> None:
    mock_get, mock_set = mock_cache
    mock_get.return_value = None

    with pytest.raises(NotFoundException):
        await reports_service.get_export_job_status(org_id=1, job_id="invalid")


@pytest.mark.asyncio
async def test_get_export_job_status_success(reports_service, mock_cache) -> None:
    mock_get, mock_set = mock_cache
    mock_get.return_value = {
        "export_job_id": "job123",
        "status": "completed",
        "download_url": "/api/v1/reports/exports/job123/download",
        "expires_at": "2026-07-10T11:00:00",
    }

    res = await reports_service.get_export_job_status(org_id=1, job_id="job123")
    assert res.status == "completed"
    assert res.download_url == "/api/v1/reports/exports/job123/download"
    assert res.expires_at == datetime.datetime(2026, 7, 10, 11, 0, 0)
