"""Settings Management — Repository / data-access layer.

Handles all organization and salary slip settings queries and updates,
cross-module configuration checks, and settings modification history logging.
"""

from __future__ import annotations

import datetime
from typing import Any

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.settings.models import OrgSalarySlipSettings, OrgSettings
from app.shared.base.repository import BaseRepository


class OrgSettingsRepository(BaseRepository[OrgSettings]):
    """Repository for managing organization system and device settings."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, OrgSettings)

    async def get_by_org_id(self, org_id: int) -> OrgSettings | None:
        """Fetch the single settings row for the given organization."""
        stmt = select(OrgSettings).where(OrgSettings.org_id == org_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def exists_in_org(self, org_id: int) -> bool:
        """Check if settings row exists for the given organization."""
        return await self.exists(filters={"org_id": org_id})

    async def search(self, org_id: int, **filters: Any) -> list[OrgSettings]:
        """Search organization settings under tenant context.

        Since organization settings are unique per organization, this query
        will return at most one record.
        """
        stmt = select(OrgSettings).where(OrgSettings.org_id == org_id)
        for key, val in filters.items():
            if val is not None:
                stmt = stmt.where(getattr(OrgSettings, key) == val)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def reset_to_defaults(
        self, org_id: int, updated_by: int | None = None
    ) -> OrgSettings | None:
        """Reset organization settings to defaults (toggles and time)."""
        settings = await self.get_by_org_id(org_id)
        if not settings:
            return None

        settings.advance_shift_enabled = False
        settings.enable_regularization = False
        settings.enable_photo_punch = False
        settings.device_sync_time = datetime.time(16, 51, 0)
        settings.updated_by = updated_by
        settings.updated_at = datetime.datetime.now(datetime.timezone.utc)  # noqa: UP017

        self.session.add(settings)
        await self.session.flush()
        await self.session.refresh(settings)
        return settings


class OrgSalarySlipSettingsRepository(BaseRepository[OrgSalarySlipSettings]):
    """Repository for managing organization salary slip (payslip) settings."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, OrgSalarySlipSettings)

    async def get_by_org_id(self, org_id: int) -> OrgSalarySlipSettings | None:
        """Fetch the salary slip settings row for the given organization."""
        stmt = select(OrgSalarySlipSettings).where(OrgSalarySlipSettings.org_id == org_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def exists_in_org(self, org_id: int) -> bool:
        """Check if salary slip settings exist for the given organization."""
        return await self.exists(filters={"org_id": org_id})


class SettingsCrossModuleRepository:
    """Repository helper to check external configurations and activity logs."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def cross_module_exists(self, table_name: str, org_id: int) -> bool:
        """Check if a row exists in an external settings table for the organization."""
        stmt = text(f"SELECT 1 FROM {table_name} WHERE org_id = :org_id LIMIT 1")
        result = await self.session.execute(stmt, {"org_id": org_id})
        return result.first() is not None

    async def attendance_settings_exists(self, org_id: int) -> bool:
        """Check if full attendance settings exist in the Employee module."""
        return await self.cross_module_exists("org_attendance_settings", org_id)

    async def payroll_settings_exists(self, org_id: int) -> bool:
        """Check if payroll calculation settings exist in the Payroll module."""
        return await self.cross_module_exists("payroll_settings", org_id)

    async def leave_settings_exists(self, org_id: int) -> bool:
        """Check if leave cycle settings exist in the Leave module."""
        return await self.cross_module_exists("leave_settings", org_id)

    async def get_settings_history(
        self,
        org_id: int,
        page: int | None = None,
        page_size: int | None = None,
    ) -> list[Any]:
        """Fetch settings modification logs from the audit module."""
        from app.modules.audit.models import ActivityLog
        from app.shared.utils.query import apply_pagination

        stmt = (
            select(ActivityLog)
            .where(ActivityLog.org_id == org_id)
            .where(ActivityLog.module == "settings")
            .order_by(ActivityLog.logged_at.desc())
        )
        if page is not None and page_size is not None:
            stmt = apply_pagination(stmt, page=page, page_size=page_size)

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_settings_history_count(self, org_id: int) -> int:
        """Count the settings modification logs from the audit module."""
        from app.modules.audit.models import ActivityLog

        stmt = (
            select(func.count())
            .select_from(ActivityLog)
            .where(ActivityLog.org_id == org_id)
            .where(ActivityLog.module == "settings")
        )
        result = await self.session.execute(stmt)
        return int(result.scalar_one())
