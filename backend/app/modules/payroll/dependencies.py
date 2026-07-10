"""Payroll Management — module-scoped FastAPI dependencies."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies.db import get_db
from app.modules.payroll.service import PayrollService


async def get_payroll_service(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PayrollService:
    """Provide a PayrollService instance bound to the request-scoped DB session."""
    return PayrollService(db)


PayrollServiceDep = Annotated[PayrollService, Depends(get_payroll_service)]

__all__ = [
    "get_payroll_service",
    "PayrollServiceDep",
]
