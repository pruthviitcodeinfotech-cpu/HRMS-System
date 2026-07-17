"""ADMS (iClock) data-access repository."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.hardware.models import BiometricDevice
from app.shared.base.repository import BaseRepository


class ADMSRepository(BaseRepository[BiometricDevice]):
    """Repository handling database operations for ADMS / Biometric Devices."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, BiometricDevice)

    async def get_by_serial_number(self, serial_number: str) -> BiometricDevice | None:
        """Retrieve a biometric device by its unique serial number."""
        stmt = select(BiometricDevice).where(BiometricDevice.serial_number == serial_number)
        result = await self.session.execute(stmt.limit(1))
        return result.scalar_one_or_none()

    async def get_first_active_org_id(self) -> int | None:
        """Fetch the ID of the first active organization in the database."""
        from app.modules.employee.models.organization import Organization

        stmt = select(Organization.org_id).where(Organization.is_active.is_(True)).limit(1)
        result = await self.session.execute(stmt)
        return result.scalar()
