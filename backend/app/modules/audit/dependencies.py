"""Activity Log / Audit — module-scoped FastAPI dependencies."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies.db import get_db
from app.modules.audit.service import AuditService


async def get_audit_service(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AuditService:
    """Provide an AuditService instance bound to the request-scoped DB session."""
    return AuditService(db)


AuditServiceDep = Annotated[AuditService, Depends(get_audit_service)]

__all__ = [
    "get_audit_service",
    "AuditServiceDep",
]
