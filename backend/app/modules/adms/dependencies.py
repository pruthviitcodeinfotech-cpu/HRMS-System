"""ADMS (iClock) FastAPI dependencies."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies.db import get_db
from app.modules.adms.service import ADMSService


async def get_adms_service(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ADMSService:
    """Provide an ADMSService instance bound to the request-scoped DB session."""
    return ADMSService(db)


ADMSServiceDep = Annotated[ADMSService, Depends(get_adms_service)]

__all__ = [
    "get_adms_service",
    "ADMSServiceDep",
]
