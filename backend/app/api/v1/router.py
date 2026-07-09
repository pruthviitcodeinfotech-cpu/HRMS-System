"""API v1 router — aggregates all implemented module routers for version 1.

Each module router declares contract-relative paths (``/employees``, ``/users``,
``/auth/...``); this aggregator collects them under a single ``api_router`` that
:func:`app.main.create_app` mounts at ``settings.api_v1_prefix``. Modules are added
here as they are implemented.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.modules.auth.router import router as auth_router
from app.modules.employee.router import router as employee_router
from app.modules.rbac.router import router as rbac_router
from app.modules.shift.router import router as shift_router
from app.modules.approvals.router import router as approvals_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(rbac_router)
api_router.include_router(employee_router)
api_router.include_router(shift_router)
api_router.include_router(approvals_router)

__all__ = ["api_router"]

