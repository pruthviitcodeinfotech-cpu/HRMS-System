"""Hardware / Biometric Management — data-access repository (async SQLAlchemy).

Provides database operations for biometric devices, including CRUD, search,
filtering, unique validation exists checks, branch assignments, employee mappings,
and connectivity status/heartbeat logs.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants.enums import SortOrder
from app.modules.hardware.constants import DeviceProtocol, DeviceStatus
from app.modules.hardware.models import BiometricDevice
from app.shared.base.repository import BaseRepository
from app.shared.utils.query import apply_sorting


class BiometricDeviceRepository(BaseRepository[BiometricDevice]):
    """Repository class handling data operations for Biometric Devices."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, BiometricDevice)

    # --- Device Lookups & Scoping ---

    async def get_by_id_in_org(self, org_id: int, device_id: int) -> BiometricDevice | None:
        """Retrieve a biometric device by its ID, scoped to a specific organization."""
        stmt = select(BiometricDevice).where(
            BiometricDevice.id == device_id,
            BiometricDevice.org_id == org_id,
        )
        result = await self.session.execute(stmt.limit(1))
        return result.scalar_one_or_none()

    async def get_by_serial_number(self, serial_number: str) -> BiometricDevice | None:
        """Retrieve a biometric device by its globally unique serial number."""
        stmt = select(BiometricDevice).where(BiometricDevice.serial_number == serial_number)
        result = await self.session.execute(stmt.limit(1))
        return result.scalar_one_or_none()

    async def get_by_device_code(self, org_id: int, device_code: str) -> BiometricDevice | None:
        """Retrieve a biometric device by its organization-unique device code."""
        stmt = select(BiometricDevice).where(
            BiometricDevice.org_id == org_id,
            BiometricDevice.device_code == device_code,
        )
        result = await self.session.execute(stmt.limit(1))
        return result.scalar_one_or_none()

    # --- Exists & Constraint Validation ---

    async def exists_in_org(self, org_id: int, device_id: int) -> bool:
        """Check if a biometric device exists within a specific organization."""
        stmt = select(BiometricDevice.id).where(
            BiometricDevice.id == device_id,
            BiometricDevice.org_id == org_id,
        )
        result = await self.session.execute(stmt.limit(1))
        return result.first() is not None

    async def serial_number_exists(self, serial_number: str, exclude_id: int | None = None) -> bool:
        """Check if a serial number is registered to any device (excluding a specific ID)."""
        stmt = select(BiometricDevice.id).where(BiometricDevice.serial_number == serial_number)
        if exclude_id is not None:
            stmt = stmt.where(BiometricDevice.id != exclude_id)
        result = await self.session.execute(stmt.limit(1))
        return result.first() is not None

    async def device_code_exists(self, org_id: int, device_code: str, exclude_id: int | None = None) -> bool:
        """Check if a device code is registered in an organization (excluding a specific ID)."""
        stmt = select(BiometricDevice.id).where(
            BiometricDevice.org_id == org_id,
            BiometricDevice.device_code == device_code,
        )
        if exclude_id is not None:
            stmt = stmt.where(BiometricDevice.id != exclude_id)
        result = await self.session.execute(stmt.limit(1))
        return result.first() is not None

    async def is_device_in_use(self, device_id: int) -> bool:
        """Verify if a biometric device is in use (has dependent relations).

        Checks references in:
        1. employee_biometrics.device_id
        2. org_attendance_settings.device_id
        3. attendance_punches.device_id
        """
        from app.modules.attendance.models import AttendancePunch
        from app.modules.employee.models.satellites import EmployeeBiometric, OrgAttendanceSetting

        # 1. Employee Biometrics check (active templates)
        eb_stmt = select(EmployeeBiometric.biometric_id).where(
            EmployeeBiometric.device_id == device_id,
            EmployeeBiometric.is_deleted.is_(False),
        ).limit(1)
        if (await self.session.execute(eb_stmt)).first() is not None:
            return True

        # 2. Org/Branch settings check
        oas_stmt = select(OrgAttendanceSetting.setting_id).where(
            OrgAttendanceSetting.device_id == device_id
        ).limit(1)
        if (await self.session.execute(oas_stmt)).first() is not None:
            return True

        # 3. Attendance punches check
        ap_stmt = select(AttendancePunch.id).where(
            AttendancePunch.device_id == device_id
        ).limit(1)
        if (await self.session.execute(ap_stmt)).first() is not None:
            return True

        return False

    # --- Device Assignments & Mapping ---

    async def assign_branch(self, device: BiometricDevice, branch_id: int | None) -> BiometricDevice:
        """Assign or unassign a biometric device to a specific branch."""
        return await self.update(device, {"branch_id": branch_id})

    async def get_employee_mappings(self, device_id: int) -> list[Any]:
        """Fetch all active employee biometric mappings associated with a specific device."""
        from app.modules.employee.models.satellites import EmployeeBiometric

        stmt = select(EmployeeBiometric).where(
            EmployeeBiometric.device_id == device_id,
            EmployeeBiometric.is_deleted.is_(False),
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    # --- Status, Heartbeat, and Sync ---

    async def update_status(
        self,
        device: BiometricDevice,
        *,
        status: DeviceStatus | str | None = None,
        last_seen_at: datetime | None = None,
        last_sync_at: datetime | None = None,
        firmware_version: str | None = None,
        software_version: str | None = None,
        total_users: int | None = None,
        total_fingerprints: int | None = None,
        total_faces: int | None = None,
        total_cards: int | None = None,
        total_logs: int | None = None,
    ) -> BiometricDevice:
        """Update connectivity status, heartbeat metadata, and hardware capacity statistics."""
        update_data = {}
        if status is not None:
            update_data["status"] = status
        if last_seen_at is not None:
            update_data["last_seen_at"] = last_seen_at
        if last_sync_at is not None:
            update_data["last_sync_at"] = last_sync_at
        if firmware_version is not None:
            update_data["firmware_version"] = firmware_version
        if software_version is not None:
            update_data["software_version"] = software_version
        if total_users is not None:
            update_data["total_users"] = total_users
        if total_fingerprints is not None:
            update_data["total_fingerprints"] = total_fingerprints
        if total_faces is not None:
            update_data["total_faces"] = total_faces
        if total_cards is not None:
            update_data["total_cards"] = total_cards
        if total_logs is not None:
            update_data["total_logs"] = total_logs

        return await self.update(device, update_data)

    async def update_last_sync(self, device: BiometricDevice, last_sync_at: datetime, total_logs: int | None = None) -> BiometricDevice:
        """Update last sync timestamp and total logs count on synchronization."""
        update_data = {"last_sync_at": last_sync_at}
        if total_logs is not None:
            update_data["total_logs"] = total_logs
        return await self.update(device, update_data)

    # --- Search, Filtering, and Pagination ---

    @staticmethod
    def _search_conditions(
        org_id: int,
        *,
        search: str | None = None,
        status: DeviceStatus | str | None = None,
        protocol: DeviceProtocol | str | None = None,
        branch_id: int | None = None,
        is_active: bool | None = None,
        adms_enabled: bool | None = None,
        allowed_branch_ids: list[int] | None = None,
    ) -> list[Any]:
        """Build a list of SQLAlchemy filters for device searching."""
        conds = [BiometricDevice.org_id == org_id]

        if is_active is not None:
            conds.append(BiometricDevice.is_active == is_active)

        if adms_enabled is not None:
            conds.append(BiometricDevice.adms_enabled == adms_enabled)

        if status is not None:
            conds.append(BiometricDevice.status == status)

        if protocol is not None:
            conds.append(BiometricDevice.protocol == protocol)

        if branch_id is not None:
            conds.append(BiometricDevice.branch_id == branch_id)

        if allowed_branch_ids is not None:
            conds.append(BiometricDevice.branch_id.in_(allowed_branch_ids))

        if search:
            search_term = f"%{search.strip()}%"
            conds.append(
                or_(
                    BiometricDevice.device_name.ilike(search_term),
                    BiometricDevice.device_code.ilike(search_term),
                    BiometricDevice.serial_number.ilike(search_term),
                )
            )

        return conds

    async def search(
        self,
        org_id: int,
        *,
        search: str | None = None,
        status: DeviceStatus | str | None = None,
        protocol: DeviceProtocol | str | None = None,
        branch_id: int | None = None,
        is_active: bool | None = None,
        adms_enabled: bool | None = None,
        allowed_branch_ids: list[int] | None = None,
        sort_by: str | None = "device_name",
        sort_order: SortOrder | str = SortOrder.ASC,
        page: int = 1,
        page_size: int = 25,
    ) -> list[BiometricDevice]:
        """Search, filter, sort, and paginate registered biometric devices."""
        conds = self._search_conditions(
            org_id,
            search=search,
            status=status,
            protocol=protocol,
            branch_id=branch_id,
            is_active=is_active,
            adms_enabled=adms_enabled,
            allowed_branch_ids=allowed_branch_ids,
        )
        stmt = select(BiometricDevice).where(and_(*conds))
        stmt = apply_sorting(
            stmt,
            BiometricDevice,
            sort_by,
            sort_order,
            allowed={"device_name", "created_at", "last_seen_at"},
            default_sort_by="device_name",
        )
        stmt = stmt.limit(page_size).offset((page - 1) * page_size)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def search_count(
        self,
        org_id: int,
        *,
        search: str | None = None,
        status: DeviceStatus | str | None = None,
        protocol: DeviceProtocol | str | None = None,
        branch_id: int | None = None,
        is_active: bool | None = None,
        adms_enabled: bool | None = None,
        allowed_branch_ids: list[int] | None = None,
    ) -> int:
        """Get the count of registered biometric devices matching the query filters."""
        conds = self._search_conditions(
            org_id,
            search=search,
            status=status,
            protocol=protocol,
            branch_id=branch_id,
            is_active=is_active,
            adms_enabled=adms_enabled,
            allowed_branch_ids=allowed_branch_ids,
        )
        stmt = select(func.count()).select_from(BiometricDevice).where(and_(*conds))
        result = await self.session.execute(stmt)
        return int(result.scalar_one())
