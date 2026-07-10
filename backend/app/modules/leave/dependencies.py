"""Leave & Holiday Management — module-scoped FastAPI dependencies."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies.db import get_db
from app.modules.leave.service import LeaveService


async def get_leave_service(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> LeaveService:
    """Provide a LeaveService instance bound to the request-scoped DB session."""
    return LeaveService(db)


LeaveServiceDep = Annotated[LeaveService, Depends(get_leave_service)]

__all__ = [
    "get_leave_service",
    "LeaveServiceDep",
]
