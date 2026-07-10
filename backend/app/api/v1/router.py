"""API v1 router — aggregates all implemented module routers for version 1.

Each module router declares contract-relative paths (``/employees``, ``/users``,
``/auth/...``); this aggregator collects them under a single ``api_router`` that
:func:`app.main.create_app` mounts at ``settings.api_v1_prefix``. Modules are added
here as they are implemented.

Not yet mounted, because their routers are still placeholders with no endpoints:
``payroll``, ``leave``, ``audit``, ``organization``. They are wired in once their
controllers exist — mounting an empty router would silently advertise a module
that serves nothing.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.modules.approvals.router import router as approvals_router
from app.modules.attendance.router import router as attendance_router
from app.modules.auth.router import router as auth_router
from app.modules.dashboard.router import router as dashboard_router
from app.modules.employee.router import router as employee_router
from app.modules.hardware.router import router as hardware_router
from app.modules.notifications.router import router as notifications_router
from app.modules.rbac.router import router as rbac_router
from app.modules.reports.router import router as reports_router
from app.modules.settings.router import router as settings_router
from app.modules.settlements.router import router as settlements_router
from app.modules.shift.router import router as shift_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(rbac_router)
api_router.include_router(employee_router)
api_router.include_router(shift_router)
api_router.include_router(attendance_router)
api_router.include_router(approvals_router)
api_router.include_router(hardware_router)
api_router.include_router(settlements_router)
api_router.include_router(notifications_router)
api_router.include_router(settings_router)
api_router.include_router(dashboard_router)
api_router.include_router(reports_router)

__all__ = ["api_router"]
