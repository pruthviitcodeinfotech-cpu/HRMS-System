"""Hardware / Biometric Management — service layer (business logic, transaction orchestration).

Implements device registration, configuration updates, branch assignments, connectivity
status heartbeats, diagnostics, and synchronization checkpoints.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions.base import ConflictException, NotFoundException
from app.modules.audit.constants import ActionType
from app.modules.audit.service import AuditService
from app.modules.employee.repository import BranchRepository
from app.modules.hardware.constants import DeviceProtocol, DeviceStatus
from app.modules.hardware.models import BiometricDevice
from app.modules.hardware.repository import BiometricDeviceRepository
from app.modules.hardware.schemas import (
    BiometricDeviceAssignBranchRequest,
    BiometricDeviceConfigureRequest,
    BiometricDeviceConfigurationSchema,
    BiometricDeviceHeartbeatRequest,
    BiometricDeviceHealthSchema,
    BiometricDeviceListResponse,
    BiometricDeviceRegisterRequest,
    BiometricDeviceSchema,
    BiometricDeviceSearchQuery,
    BiometricDeviceStatusSchema,
)
from app.modules.rbac.repository import UserRepository
from app.shared.base.service import BaseService
from app.shared.utils.datetime import utcnow

_AUDIT_MODULE = "Hardware / Biometric Management"


class BiometricDeviceService(BaseService):
    """Business logic orchestrator for biometric and hardware devices."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)
        self.devices = BiometricDeviceRepository(session)
        self.branches = BranchRepository(session)
        self.users = UserRepository(session)
        self.audit = AuditService(session)

    # --- Core CRUD operations ---

    async def register_device(
        self, *, org_id: int, actor_id: int, data: BiometricDeviceRegisterRequest
    ) -> BiometricDeviceSchema:
        """Register a new biometric device within an organization."""
        # 1. Enforce serial number global uniqueness
        if await self.devices.serial_number_exists(data.serial_number):
            raise ConflictException(
                "Device serial number already exists.",
                code="DEVICE_SERIAL_EXISTS",
            )

        # 2. Enforce device code uniqueness per organisation/tenant boundary
        if await self.devices.device_code_exists(org_id, data.device_code):
            raise ConflictException(
                "Device code already exists in this organization.",
                code="DEVICE_CODE_EXISTS",
            )

        # 3. Validate target branch scoping
        if data.branch_id is not None:
            if not await self.branches.exists_active(org_id, data.branch_id):
                raise NotFoundException(
                    "Branch not found.",
                    code="BRANCH_NOT_FOUND",
                )

        payload = data.model_dump()
        payload["org_id"] = org_id
        payload["created_by"] = actor_id
        payload["updated_by"] = actor_id
        payload["status"] = DeviceStatus.OFFLINE.value

        async with self.transaction():
            device = await self.devices.create(payload)
            await self._audit(
                org_id=org_id,
                actor_id=actor_id,
                action_type=ActionType.INSERT,
                title="Device registered",
                description=f"Registered device '{device.device_name}' with serial number '{device.serial_number}'.",
            )

        return BiometricDeviceSchema.model_validate(device)

    async def list_devices(
        self,
        *,
        org_id: int,
        query: BiometricDeviceSearchQuery,
        allowed_branch_ids: list[int] | None = None,
    ) -> BiometricDeviceListResponse:
        """Search, filter, and paginate biometric devices with RBAC branch data scoping."""
        # Restrict search by branch scoping if caller is restricted
        effective_allowed_branches = allowed_branch_ids
        if query.branch_id is not None:
            if allowed_branch_ids is not None:
                if query.branch_id not in allowed_branch_ids:
                    return BiometricDeviceListResponse.build(
                        items=[],
                        page=query.page,
                        page_size=query.page_size,
                        total_records=0,
                    )
            effective_allowed_branches = [query.branch_id]

        rows = await self.devices.search(
            org_id,
            search=query.search,
            status=query.status,
            protocol=query.protocol,
            branch_id=None,  # Filter handled inside allowed_branch_ids scoping
            is_active=query.is_active,
            adms_enabled=query.adms_enabled,
            allowed_branch_ids=effective_allowed_branches,
            sort_by=query.sort_by,
            sort_order=query.sort_order or "asc",
            page=query.page,
            page_size=query.page_size,
        )

        total = await self.devices.search_count(
            org_id,
            search=query.search,
            status=query.status,
            protocol=query.protocol,
            branch_id=None,
            is_active=query.is_active,
            adms_enabled=query.adms_enabled,
            allowed_branch_ids=effective_allowed_branches,
        )

        items = [BiometricDeviceSchema.model_validate(row) for row in rows]
        return BiometricDeviceListResponse.build(
            items=items,
            page=query.page,
            page_size=query.page_size,
            total_records=total,
        )

    async def get_device(self, *, org_id: int, device_id: int) -> BiometricDeviceSchema:
        """Retrieve full details of a biometric device."""
        device = await self._get_device_or_404(org_id, device_id)
        return BiometricDeviceSchema.model_validate(device)

    async def update_device(
        self, *, org_id: int, actor_id: int, device_id: int, data: BiometricDeviceUpdateRequest
    ) -> BiometricDeviceSchema:
        """Update identity, network, and location details of a device."""
        device = await self._get_device_or_404(org_id, device_id)
        updates = data.model_dump(exclude_unset=True)

        if "serial_number" in updates and updates["serial_number"] != device.serial_number:
            if await self.devices.serial_number_exists(updates["serial_number"], exclude_id=device_id):
                raise ConflictException(
                    "Device serial number already exists.",
                    code="DEVICE_SERIAL_EXISTS",
                )

        if "device_code" in updates and updates["device_code"] != device.device_code:
            if await self.devices.device_code_exists(org_id, updates["device_code"], exclude_id=device_id):
                raise ConflictException(
                    "Device code already exists in this organization.",
                    code="DEVICE_CODE_EXISTS",
                )

        if "branch_id" in updates and updates["branch_id"] is not None:
            if not await self.branches.exists_active(org_id, updates["branch_id"]):
                raise NotFoundException(
                    "Branch not found.",
                    code="BRANCH_NOT_FOUND",
                )

        updates["updated_by"] = actor_id

        async with self.transaction():
            device = await self.devices.update(device, updates)
            await self._audit(
                org_id=org_id,
                actor_id=actor_id,
                action_type=ActionType.UPDATE,
                title="Device updated",
                description=f"Updated device '{device.device_name}'.",
            )

        return BiometricDeviceSchema.model_validate(device)

    async def delete_device(self, *, org_id: int, actor_id: int, device_id: int) -> None:
        """Delete a biometric device from the registry."""
        device = await self._get_device_or_404(org_id, device_id)

        # Enforce referential integrity checks (cannot delete if punches, mappings or settings reference it)
        if await self.devices.is_device_in_use(device_id):
            raise ConflictException(
                "Device is in use and cannot be deleted.",
                code="DEVICE_IN_USE",
            )

        async with self.transaction():
            await self.devices.delete(device)
            await self._audit(
                org_id=org_id,
                actor_id=actor_id,
                action_type=ActionType.DELETE,
                title="Device deleted",
                description=f"Deleted device '{device.device_name}' with serial number '{device.serial_number}'.",
            )

    # --- Device Configuration & Management ---

    async def get_device_configuration(
        self, *, org_id: int, device_id: int
    ) -> BiometricDeviceConfigurationSchema:
        """Retrieve network and ADMS configuration details (secrets redacted)."""
        device = await self._get_device_or_404(org_id, device_id)
        return BiometricDeviceConfigurationSchema.model_validate(device)

    async def update_device_configuration(
        self,
        *,
        org_id: int,
        actor_id: int,
        device_id: int,
        data: BiometricDeviceConfigureRequest,
    ) -> BiometricDeviceConfigurationSchema:
        """Update network parameters, ADMS settings, and write-only security keys."""
        device = await self._get_device_or_404(org_id, device_id)
        updates = data.model_dump(exclude_unset=True)
        updates["updated_by"] = actor_id

        async with self.transaction():
            device = await self.devices.update(device, updates)
            await self._audit(
                org_id=org_id,
                actor_id=actor_id,
                action_type=ActionType.UPDATE,
                title="Device configuration updated",
                description=f"Updated network/ADMS configuration for device '{device.device_name}'.",
            )

        return BiometricDeviceConfigurationSchema.model_validate(device)

    async def assign_device_to_branch(
        self,
        *,
        org_id: int,
        actor_id: int,
        device_id: int,
        data: BiometricDeviceAssignBranchRequest,
    ) -> BiometricDeviceSchema:
        """Assign or unassign a biometric device to/from a branch."""
        device = await self._get_device_or_404(org_id, device_id)

        if data.branch_id is not None:
            if not await self.branches.exists_active(org_id, data.branch_id):
                raise NotFoundException(
                    "Branch not found.",
                    code="BRANCH_NOT_FOUND",
                )

        async with self.transaction():
            device = await self.devices.assign_branch(device, data.branch_id)
            desc = (
                f"Assigned device '{device.device_name}' to branch ID {data.branch_id}."
                if data.branch_id
                else f"Unassigned device '{device.device_name}' from branch."
            )
            await self._audit(
                org_id=org_id,
                actor_id=actor_id,
                action_type=ActionType.ASSIGN,
                title="Device branch assignment updated",
                description=desc,
            )

        return BiometricDeviceSchema.model_validate(device)

    async def enable_device(
        self, *, org_id: int, actor_id: int, device_id: int
    ) -> BiometricDeviceSchema:
        """Enable a biometric device (administrative active flag)."""
        device = await self._get_device_or_404(org_id, device_id)
        if device.is_active:
            return BiometricDeviceSchema.model_validate(device)

        async with self.transaction():
            device = await self.devices.update(device, {"is_active": True, "updated_by": actor_id})
            await self._audit(
                org_id=org_id,
                actor_id=actor_id,
                action_type=ActionType.UPDATE,
                title="Device enabled",
                description=f"Enabled device '{device.device_name}'.",
            )

        return BiometricDeviceSchema.model_validate(device)

    async def disable_device(
        self, *, org_id: int, actor_id: int, device_id: int
    ) -> BiometricDeviceSchema:
        """Disable a biometric device (administrative active flag)."""
        device = await self._get_device_or_404(org_id, device_id)
        if not device.is_active:
            return BiometricDeviceSchema.model_validate(device)

        async with self.transaction():
            device = await self.devices.update(device, {"is_active": False, "updated_by": actor_id})
            await self._audit(
                org_id=org_id,
                actor_id=actor_id,
                action_type=ActionType.UPDATE,
                title="Device disabled",
                description=f"Disabled device '{device.device_name}'.",
            )

        return BiometricDeviceSchema.model_validate(device)

    # --- Status, Heartbeat, and Diagnostics ---

    async def get_device_status(
        self, *, org_id: int, device_id: int
    ) -> BiometricDeviceStatusSchema:
        """Get the connectivity status and heartbeat timestamps of a device."""
        device = await self._get_device_or_404(org_id, device_id)
        return BiometricDeviceStatusSchema.model_validate(device)

    async def report_heartbeat(
        self,
        *,
        org_id: int,
        device_id: int,
        data: BiometricDeviceHeartbeatRequest,
    ) -> BiometricDeviceSchema:
        """Report connectivity stats, firmware version, and device capacity statistics from reporting agent."""
        device = await self._get_device_or_404(org_id, device_id)

        async with self.transaction():
            device = await self.devices.update_status(
                device,
                status=data.status,
                last_seen_at=data.last_seen_at or utcnow(),
                last_sync_at=data.last_sync_at,
                firmware_version=data.firmware_version,
                software_version=data.software_version,
                total_users=data.total_users,
                total_fingerprints=data.total_fingerprints,
                total_faces=data.total_faces,
                total_cards=data.total_cards,
                total_logs=data.total_logs,
            )

        return BiometricDeviceSchema.model_validate(device)

    async def get_device_health(
        self, *, org_id: int, device_id: int
    ) -> BiometricDeviceHealthSchema:
        """Retrieve diagnostic health, capacity metrics, and device software/firmware details."""
        device = await self._get_device_or_404(org_id, device_id)
        return BiometricDeviceHealthSchema.model_validate(device)

    async def get_employee_mappings(self, *, org_id: int, device_id: int) -> list[Any]:
        """Retrieve active employee biometric template mappings for a device."""
        await self._get_device_or_404(org_id, device_id)
        return await self.devices.get_employee_mappings(device_id)

    # --- Connectivity Validation & Synchronization Placeholders ---

    async def validate_connectivity(self, *, org_id: int, device_id: int) -> bool:
        """Check and validate live network connectivity to the physical biometric device.

        Performs connection diagnostics according to the configured protocol.
        """
        device = await self._get_device_or_404(org_id, device_id)
        if not device.is_active:
            return False

        status = DeviceStatus.OFFLINE
        if device.protocol == DeviceProtocol.TCP_IP and device.ip_address and device.port:
            try:
                import socket

                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(2.0)
                    s.connect((device.ip_address, device.port))
                status = DeviceStatus.ONLINE
            except Exception:
                status = DeviceStatus.OFFLINE
        else:
            # Passive ADMS connection check
            if device.last_seen_at and (utcnow() - device.last_seen_at).total_seconds() < 300:
                status = DeviceStatus.ONLINE

        async with self.transaction():
            await self.devices.update_status(device, status=status, last_seen_at=utcnow())

        return status == DeviceStatus.ONLINE

    async def sync_device(self, *, org_id: int, device_id: int) -> None:
        """Trigger synchronization of device configurations and registers.

        Validation checkpoint only. Actual physical device communication (ADMS/MQTT)
        is processed asynchronously by the integration/Attendance module.
        """
        device = await self._get_device_or_404(org_id, device_id)

        async with self.transaction():
            await self.devices.update_last_sync(device, last_sync_at=utcnow())

    async def sync_punches(self, *, org_id: int, device_id: int) -> None:
        """Trigger ingestion of punch logs from the biometric device.

        Validation checkpoint only. Punch synchronization and database recording
        are executed asynchronously by the integration/Attendance module.
        """
        device = await self._get_device_or_404(org_id, device_id)

        async with self.transaction():
            await self.devices.update_last_sync(device, last_sync_at=utcnow())

    # --- Internal Helpers ---

    async def _get_device_or_404(self, org_id: int, device_id: int) -> BiometricDevice:
        """Retrieve a device and enforce tenant boundary validation."""
        device = await self.devices.get_by_id_in_org(org_id, device_id)
        if device is None:
            raise NotFoundException("Device not found.", code="DEVICE_NOT_FOUND")
        return device

    async def _actor_name(self, org_id: int, actor_id: int) -> str:
        """Resolve display name of the acting user for audit logs."""
        user = await self.users.get_active_by_id(actor_id, org_id)
        name = getattr(user, "name", None)
        return name if isinstance(name, str) and name else f"user #{actor_id}"

    async def _audit(
        self,
        *,
        org_id: int,
        actor_id: int,
        action_type: ActionType,
        title: str,
        description: str,
    ) -> None:
        """Log audit entry for state change."""
        await self.audit.record(
            org_id=org_id,
            module=_AUDIT_MODULE,
            action_type=action_type,
            title=title,
            description=description,
            performed_by_user_id=actor_id,
            performed_by_name=await self._actor_name(org_id, actor_id),
        )


__all__ = ["BiometricDeviceService"]
