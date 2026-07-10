"""reports: Module-scoped FastAPI dependencies."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies.db import get_db
from app.modules.reports.service import ReportsService


def get_reports_service(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ReportsService:
    """Dependency provider for ReportsService."""
    return ReportsService(session)


ReportsServiceDep = Annotated[ReportsService, Depends(get_reports_service)]
