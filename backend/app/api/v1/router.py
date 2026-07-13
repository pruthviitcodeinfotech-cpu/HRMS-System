"""API v1 router — aggregates all implemented module routers for version 1.

Each module router declares contract-relative paths (``/employees``, ``/users``,
``/auth/...``); this aggregator collects them under a single ``api_router`` that
:func:`app.main.create_app` mounts at ``settings.api_v1_prefix``.

Ordering matters. Routers are included in the order below and FastAPI matches routes
in registration order, so a module that owns a static path must be registered before
any module that declares a colliding path parameter at the same depth. ``organization``
is registered first because it owns the tenant hierarchy every other module references.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.modules.approvals.router import router as approvals_router
from app.modules.attendance.router import router as attendance_router
from app.modules.audit.router import router as audit_router
from app.modules.auth.router import router as auth_router
from app.modules.dashboard.router import router as dashboard_router
from app.modules.employee.router import router as employee_router
from app.modules.hardware.router import router as hardware_router
from app.modules.jobs.router import router as jobs_router
from app.modules.leave.router import router as leave_router
from app.modules.notifications.router import router as notifications_router
from app.modules.organization.router import router as organization_router
from app.modules.payroll.router import router as payroll_router
from app.modules.rbac.router import router as rbac_router
from app.modules.reports.router import router as reports_router
from app.modules.settings.router import router as settings_router
from app.modules.settlements.router import router as settlements_router
from app.modules.shift.router import router as shift_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(rbac_router)
api_router.include_router(organization_router)
api_router.include_router(employee_router)
api_router.include_router(shift_router)
api_router.include_router(attendance_router)
api_router.include_router(leave_router)
api_router.include_router(approvals_router)
api_router.include_router(payroll_router)
api_router.include_router(hardware_router)
api_router.include_router(settlements_router)
api_router.include_router(notifications_router)
api_router.include_router(settings_router)
api_router.include_router(audit_router)
api_router.include_router(dashboard_router)
api_router.include_router(reports_router)
api_router.include_router(jobs_router)

__all__ = ["api_router"]
