"""System Administration — HTTP router."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants.enums import PermissionAction as A
from app.core.dependencies.auth import (
    CurrentUser,
    get_current_active_user,
    require_permission,
)
from app.core.dependencies.branch import BranchIdDep
from app.core.dependencies.db import get_db
from app.core.middleware.request_context import get_request_id
from app.modules.system.schemas import (
    AuditDashboardSummaryResponse,
    BackgroundJobLogSchema,
    SlowApiMetricSchema,
    SystemHealthResponse,
)
from app.modules.system.service import SystemService
from app.shared.schemas.response import SuccessResponse, success_response

router = APIRouter(prefix="/system", tags=["System Administration"])
_FEATURE_KEY = "system"


def _get_system_service(session: AsyncSession = Depends(get_db)) -> SystemService:
    return SystemService(session)


SystemServiceDep = Annotated[SystemService, Depends(_get_system_service)]
CurrentUserDep = Annotated[CurrentUser, Depends(get_current_active_user)]
OrgIdDep = Annotated[int, Depends(lambda user=Depends(get_current_active_user): user.org_id)]


def _ok(data: Any, message: str = "Success") -> dict[str, Any]:
    return success_response(data=data, message=message, request_id=get_request_id())


# =========================================================================
# 1. System Health Dashboard
# =========================================================================


@router.get(
    "/health",
    response_model=SuccessResponse[SystemHealthResponse],
    summary="Get System Health Dashboard",
    dependencies=[Depends(require_permission(_FEATURE_KEY, A.READ))],
)
async def get_system_health(
    service: SystemServiceDep,
) -> dict[str, Any]:
    """Return aggregated system infrastructure health (API, DB, Redis, Scheduler, Jobs)."""
    result = await service.get_system_health()
    return _ok(result)


# =========================================================================
# 2. Audit Dashboard
# =========================================================================


@router.get(
    "/audit/summary",
    response_model=SuccessResponse[AuditDashboardSummaryResponse],
    summary="Get Audit Dashboard Summary",
    dependencies=[Depends(require_permission(_FEATURE_KEY, A.READ))],
)
async def get_audit_summary(
    service: SystemServiceDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Return 24-hour audit analytics summary (activities, logins, security events)."""
    result = await service.get_audit_summary(org_id)
    return _ok(result)


# =========================================================================
# 3. Background Jobs Monitoring & Retry
# =========================================================================


@router.get(
    "/jobs",
    response_model=SuccessResponse[list[BackgroundJobLogSchema]],
    summary="List Background Jobs",
    dependencies=[Depends(require_permission(_FEATURE_KEY, A.READ))],
)
async def list_background_jobs(
    service: SystemServiceDep,
    status_filter: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=200),
) -> dict[str, Any]:
    """List background job execution logs."""
    result = await service.list_background_jobs(status_filter=status_filter, limit=limit)
    return _ok(result)


@router.post(
    "/jobs/{job_id}/retry",
    response_model=SuccessResponse[BackgroundJobLogSchema],
    summary="Retry Failed Background Job",
    dependencies=[Depends(require_permission(_FEATURE_KEY, A.EDIT))],
)
async def retry_failed_job(
    job_id: str,
    service: SystemServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Re-queue a failed background job for execution."""
    result = await service.retry_failed_job(job_id=job_id, actor_id=current_user.user_id, org_id=org_id)
    return _ok(result, "Background job re-queued for execution.")


# =========================================================================
# 4. Performance & Slow API Monitoring
# =========================================================================


@router.get(
    "/performance/slow-apis",
    response_model=SuccessResponse[list[SlowApiMetricSchema]],
    summary="Get Slow API Performance Metrics",
    dependencies=[Depends(require_permission(_FEATURE_KEY, A.READ))],
)
async def get_slow_apis(
    service: SystemServiceDep,
    limit: int = Query(default=20, ge=1, le=100),
) -> dict[str, Any]:
    """Return top slow API execution metrics."""
    result = await service.get_slow_api_metrics(limit=limit)
    return _ok(result)
