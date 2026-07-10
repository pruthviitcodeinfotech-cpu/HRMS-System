"""Settings Management — module-scoped FastAPI dependencies."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies.db import get_db
from app.modules.settings.service import SettingsService


async def get_settings_service(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SettingsService:
    """Provide a SettingsService instance bound to the request-scoped DB session."""
    return SettingsService(db)


SettingsServiceDep = Annotated[SettingsService, Depends(get_settings_service)]

__all__ = [
    "get_settings_service",
    "SettingsServiceDep",
]
