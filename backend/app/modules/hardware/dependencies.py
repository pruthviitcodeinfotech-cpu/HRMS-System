"""Hardware / Biometric Management — module-scoped FastAPI dependencies."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies.db import get_db
from app.modules.hardware.service import BiometricDeviceService


async def get_hardware_service(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> BiometricDeviceService:
    """Provide a BiometricDeviceService instance bound to the request-scoped DB session."""
    return BiometricDeviceService(db)


HardwareServiceDep = Annotated[BiometricDeviceService, Depends(get_hardware_service)]

__all__ = [
    "get_hardware_service",
    "HardwareServiceDep",
]
