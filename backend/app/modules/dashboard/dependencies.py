"""Dashboard Management — module-scoped FastAPI dependencies."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies.db import get_db
from app.modules.dashboard.service import DashboardService


async def get_dashboard_service(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DashboardService:
    """Provide a DashboardService instance bound to the request-scoped DB session."""
    return DashboardService(db)


DashboardServiceDep = Annotated[DashboardService, Depends(get_dashboard_service)]

__all__ = [
    "get_dashboard_service",
    "DashboardServiceDep",
]
