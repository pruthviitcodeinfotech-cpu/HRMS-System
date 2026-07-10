"""Settlement Management — module-scoped FastAPI dependencies."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies.db import get_db
from app.modules.settlements.service import SettlementService


async def get_settlement_service(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SettlementService:
    """Provide a SettlementService instance bound to the request-scoped DB session."""
    return SettlementService(db)


SettlementServiceDep = Annotated[SettlementService, Depends(get_settlement_service)]

__all__ = [
    "get_settlement_service",
    "SettlementServiceDep",
]
