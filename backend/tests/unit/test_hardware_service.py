"""Unit tests for ``BiometricDeviceService`` business logic (repositories mocked)."""

from __future__ import annotations

from datetime import datetime, timezone
from datetime import time as dt_time
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.exceptions.base import ConflictException, NotFoundException
from app.modules.hardware.constants import DeviceProtocol, DeviceStatus
from app.modules.hardware.schemas import (
    BiometricDeviceAssignBranchRequest,
    BiometricDeviceConfigureRequest,
    BiometricDeviceHeartbeatRequest,
    BiometricDeviceRegisterRequest,
    BiometricDeviceSearchQuery,
    BiometricDeviceUpdateRequest,
)
from app.modules.hardware.service import BiometricDeviceService

_NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _device(**overrides: Any) -> SimpleNamespace:
    base = {
        "id": 1,
        "org_id": 10,
        "branch_id": None,
        "device_name": "Device A",
        "device_code": "CODE-A",
        "serial_number": "SN123",
        "model": "K90",
        "manufacturer": "eSSL",
        "ip_address": "192.168.1.100",
        "port": 5005,
        "protocol": DeviceProtocol.TCP_IP,
        "domain": None,
        "mac_address": "00:11:22:33:44:55",
        "adms_enabled": False,
        "adms_server": None,
        "adms_port": None,
        "cloud_id": None,
        "communication_key": None,
        "sync_key": None,
        "timezone": "UTC",
        "status": DeviceStatus.OFFLINE,
        "last_seen_at": _NOW,
        "last_sync_at": _NOW,
        "firmware_version": "v1.0",
        "software_version": "v2.0",
        "total_users": 0,
        "total_fingerprints": 0,
        "total_faces": 0,
        "total_cards": 0,
        "total_logs": 0,
        "installation_location": "Main Entrance",
        "remarks": "N/A",
        "is_active": True,
        "created_by": 1,
        "updated_by": 1,
        "created_at": _NOW,
        "updated_at": _NOW,
    }
    base.update(overrides)
    return SimpleNamespace(**base)


@pytest.fixture
def hardware_service() -> BiometricDeviceService:
    """Fixture to build a mock-injected BiometricDeviceService."""
    session = AsyncMock()
    svc = BiometricDeviceService(session)

    # Inject mock repositories
    for repo_name in ("devices", "branches", "users", "audit", "org_settings"):
        setattr(svc, repo_name, AsyncMock())

    # Set mock method defaults
    svc.devices.serial_number_exists.return_value = False
    svc.devices.device_code_exists.return_value = False
    svc.devices.get_by_id_in_org.return_value = _device()
    svc.devices.create.return_value = _device()
    svc.devices.update.return_value = _device()
    svc.devices.assign_branch.return_value = _device()
    svc.devices.update_status.return_value = _device()
    svc.devices.update_last_sync.return_value = _device()
    svc.devices.is_device_in_use.return_value = False
    svc.devices.get_employee_mappings.return_value = []
    
    svc.branches.exists_active.return_value = True
    svc.users.get_active_by_id.return_value = SimpleNamespace(name="Test User")
    # Org without a settings row by default -> schema defaults apply.
    svc.org_settings.get_by_org_id.return_value = None

    return svc


# ===========================================================================
# CRUD Tests
# ===========================================================================

@pytest.mark.asyncio
async def test_register_device_success(hardware_service: BiometricDeviceService) -> None:
    data = BiometricDeviceRegisterRequest(
        device_name="Device A",
        device_code="CODE-A",
        serial_number="SN123",
        branch_id=1,
    )

    result = await hardware_service.register_device(org_id=10, actor_id=1, data=data)

    assert result.device_name == "Device A"
    hardware_service.devices.create.assert_awaited_once()
    hardware_service.audit.record.assert_awaited_once()


@pytest.mark.asyncio
async def test_register_device_serial_exists(hardware_service: BiometricDeviceService) -> None:
    hardware_service.devices.serial_number_exists.return_value = True
    data = BiometricDeviceRegisterRequest(
        device_name="Device A",
        device_code="CODE-A",
        serial_number="SN123",
    )

    with pytest.raises(ConflictException) as exc:
        await hardware_service.register_device(org_id=10, actor_id=1, data=data)

    assert exc.value.code == "DEVICE_SERIAL_EXISTS"


@pytest.mark.asyncio
async def test_register_device_code_exists(hardware_service: BiometricDeviceService) -> None:
    hardware_service.devices.device_code_exists.return_value = True
    data = BiometricDeviceRegisterRequest(
        device_name="Device A",
        device_code="CODE-A",
        serial_number="SN123",
    )

    with pytest.raises(ConflictException) as exc:
        await hardware_service.register_device(org_id=10, actor_id=1, data=data)

    assert exc.value.code == "DEVICE_CODE_EXISTS"


@pytest.mark.asyncio
async def test_register_device_branch_not_found(hardware_service: BiometricDeviceService) -> None:
    hardware_service.branches.exists_active.return_value = False
    data = BiometricDeviceRegisterRequest(
        device_name="Device A",
        device_code="CODE-A",
        serial_number="SN123",
        branch_id=999,
    )

    with pytest.raises(NotFoundException) as exc:
        await hardware_service.register_device(org_id=10, actor_id=1, data=data)

    assert exc.value.code == "BRANCH_NOT_FOUND"


@pytest.mark.asyncio
async def test_list_devices_success(hardware_service: BiometricDeviceService) -> None:
    hardware_service.devices.search.return_value = [_device()]
    hardware_service.devices.search_count.return_value = 1
    query = BiometricDeviceSearchQuery(page=1, page_size=25)

    result = await hardware_service.list_devices(org_id=10, query=query, allowed_branch_ids=[1, 2])

    assert result.pagination.total_records == 1
    assert len(result.items) == 1
    hardware_service.devices.search.assert_awaited_once()


@pytest.mark.asyncio
async def test_list_devices_branch_restricted(hardware_service: BiometricDeviceService) -> None:
    query = BiometricDeviceSearchQuery(branch_id=99, page=1, page_size=25)
    
    # User only has access to branch 1, 2
    result = await hardware_service.list_devices(org_id=10, query=query, allowed_branch_ids=[1, 2])
    
    assert result.pagination.total_records == 0
    assert len(result.items) == 0


@pytest.mark.asyncio
async def test_get_device_success(hardware_service: BiometricDeviceService) -> None:
    result = await hardware_service.get_device(org_id=10, device_id=1)
    assert result.id == 1


@pytest.mark.asyncio
async def test_get_device_not_found(hardware_service: BiometricDeviceService) -> None:
    hardware_service.devices.get_by_id_in_org.return_value = None
    with pytest.raises(NotFoundException):
        await hardware_service.get_device(org_id=10, device_id=404)


@pytest.mark.asyncio
async def test_update_device_success(hardware_service: BiometricDeviceService) -> None:
    data = BiometricDeviceUpdateRequest(device_name="Updated Name")
    result = await hardware_service.update_device(org_id=10, actor_id=1, device_id=1, data=data)

    assert result.id == 1
    hardware_service.devices.update.assert_awaited_once()


@pytest.mark.asyncio
async def test_update_device_not_found(hardware_service: BiometricDeviceService) -> None:
    hardware_service.devices.get_by_id_in_org.return_value = None
    data = BiometricDeviceUpdateRequest(device_name="Updated Name")

    with pytest.raises(NotFoundException):
        await hardware_service.update_device(org_id=10, actor_id=1, device_id=404, data=data)


@pytest.mark.asyncio
async def test_delete_device_success(hardware_service: BiometricDeviceService) -> None:
    await hardware_service.delete_device(org_id=10, actor_id=1, device_id=1)
    hardware_service.devices.delete.assert_awaited_once()


@pytest.mark.asyncio
async def test_delete_device_in_use(hardware_service: BiometricDeviceService) -> None:
    hardware_service.devices.is_device_in_use.return_value = True
    with pytest.raises(ConflictException) as exc:
        await hardware_service.delete_device(org_id=10, actor_id=1, device_id=1)

    assert exc.value.code == "DEVICE_IN_USE"


# ===========================================================================
# Configuration & Assignment Tests
# ===========================================================================

@pytest.mark.asyncio
async def test_get_device_configuration(hardware_service: BiometricDeviceService) -> None:
    result = await hardware_service.get_device_configuration(org_id=10, device_id=1)
    assert result.communication_key_set is False
    # No org_settings row -> schema defaults (mirror the column defaults).
    assert result.device_sync_time == dt_time(16, 51)
    assert result.sync_code_set is False
    assert result.pass_code_set is False


@pytest.mark.asyncio
async def test_get_device_configuration_merges_org_settings(
    hardware_service: BiometricDeviceService,
) -> None:
    """org_settings supplies device_sync_time and code booleans (raw codes never exposed)."""
    hardware_service.org_settings.get_by_org_id.return_value = SimpleNamespace(
        device_sync_time=dt_time(4, 30),
        sync_code="SYNC-123",
        pass_code="PASS-9",
    )

    result = await hardware_service.get_device_configuration(org_id=10, device_id=1)

    assert result.device_sync_time == dt_time(4, 30)
    assert result.sync_code_set is True
    assert result.pass_code_set is True
    assert not hasattr(result, "sync_code")
    assert not hasattr(result, "pass_code")


@pytest.mark.asyncio
async def test_update_device_configuration(hardware_service: BiometricDeviceService) -> None:
    data = BiometricDeviceConfigureRequest(
        ip_address="10.0.0.1",
        port=5000,
        protocol=DeviceProtocol.TCP_IP,
    )
    result = await hardware_service.update_device_configuration(
        org_id=10, actor_id=1, device_id=1, data=data
    )
    assert result is not None
    hardware_service.devices.update.assert_awaited_once()


@pytest.mark.asyncio
async def test_assign_device_to_branch(hardware_service: BiometricDeviceService) -> None:
    data = BiometricDeviceAssignBranchRequest(branch_id=2)
    result = await hardware_service.assign_device_to_branch(
        org_id=10, actor_id=1, device_id=1, data=data
    )
    assert result is not None
    hardware_service.devices.assign_branch.assert_awaited_once()


@pytest.mark.asyncio
async def test_enable_and_disable_device(hardware_service: BiometricDeviceService) -> None:
    # 1. Enable
    hardware_service.devices.get_by_id_in_org.return_value = _device(is_active=False)
    await hardware_service.enable_device(org_id=10, actor_id=1, device_id=1)
    hardware_service.devices.update.assert_awaited_once_with(
        hardware_service.devices.get_by_id_in_org.return_value, {"is_active": True, "updated_by": 1}
    )

    # 2. Disable
    hardware_service.devices.update.reset_mock()
    hardware_service.devices.get_by_id_in_org.return_value = _device(is_active=True)
    await hardware_service.disable_device(org_id=10, actor_id=1, device_id=1)
    hardware_service.devices.update.assert_awaited_once_with(
        hardware_service.devices.get_by_id_in_org.return_value, {"is_active": False, "updated_by": 1}
    )


# ===========================================================================
# Status, Sync & Connectivity Tests
# ===========================================================================

@pytest.mark.asyncio
async def test_get_device_status(hardware_service: BiometricDeviceService) -> None:
    result = await hardware_service.get_device_status(org_id=10, device_id=1)
    assert result.status == DeviceStatus.OFFLINE


@pytest.mark.asyncio
async def test_report_heartbeat(hardware_service: BiometricDeviceService) -> None:
    data = BiometricDeviceHeartbeatRequest(
        status=DeviceStatus.ONLINE,
        firmware_version="v1.1",
        total_users=10,
    )
    result = await hardware_service.report_heartbeat(org_id=10, device_id=1, data=data)
    assert result is not None
    hardware_service.devices.update_status.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_device_health(hardware_service: BiometricDeviceService) -> None:
    result = await hardware_service.get_device_health(org_id=10, device_id=1)
    assert result.stats.total_users == 0


@pytest.mark.asyncio
async def test_get_employee_mappings(hardware_service: BiometricDeviceService) -> None:
    result = await hardware_service.get_employee_mappings(org_id=10, device_id=1)
    assert result == []
    hardware_service.devices.get_employee_mappings.assert_awaited_once_with(1)


@pytest.mark.asyncio
async def test_validate_connectivity(hardware_service: BiometricDeviceService) -> None:
    # 1. Active but no IP: ADMS mode checks seen time
    hardware_service.devices.get_by_id_in_org.return_value = _device(
        is_active=True,
        protocol=DeviceProtocol.ADMS,
        last_seen_at=datetime.now(timezone.utc),
    )
    is_online = await hardware_service.validate_connectivity(org_id=10, device_id=1)
    assert is_online is True

    # 2. Inactive device returns False
    hardware_service.devices.get_by_id_in_org.return_value = _device(is_active=False)
    is_online = await hardware_service.validate_connectivity(org_id=10, device_id=1)
    assert is_online is False


@pytest.mark.asyncio
async def test_sync_device_and_punches(hardware_service: BiometricDeviceService) -> None:
    await hardware_service.sync_device(org_id=10, device_id=1)
    hardware_service.devices.update_last_sync.assert_awaited_once()

    hardware_service.devices.update_last_sync.reset_mock()
    await hardware_service.sync_punches(org_id=10, device_id=1)
    hardware_service.devices.update_last_sync.assert_awaited_once()


@pytest.mark.asyncio
async def test_list_devices_by_branch_id(hardware_service: BiometricDeviceService) -> None:
    hardware_service.devices.search.return_value = [_device()]
    hardware_service.devices.search_count.return_value = 1
    query = BiometricDeviceSearchQuery(branch_id=1, page=1, page_size=25)

    result = await hardware_service.list_devices(org_id=10, query=query, allowed_branch_ids=[1, 2])
    assert result.pagination.total_records == 1


@pytest.mark.asyncio
async def test_update_device_serial_exists(hardware_service: BiometricDeviceService) -> None:
    hardware_service.devices.serial_number_exists.return_value = True
    data = BiometricDeviceUpdateRequest(serial_number="SN-EXISTING")

    with pytest.raises(ConflictException) as exc:
        await hardware_service.update_device(org_id=10, actor_id=1, device_id=1, data=data)
    assert exc.value.code == "DEVICE_SERIAL_EXISTS"


@pytest.mark.asyncio
async def test_update_device_code_exists(hardware_service: BiometricDeviceService) -> None:
    hardware_service.devices.device_code_exists.return_value = True
    data = BiometricDeviceUpdateRequest(device_code="CODE-EXISTING")

    with pytest.raises(ConflictException) as exc:
        await hardware_service.update_device(org_id=10, actor_id=1, device_id=1, data=data)
    assert exc.value.code == "DEVICE_CODE_EXISTS"


@pytest.mark.asyncio
async def test_update_device_branch_not_found(hardware_service: BiometricDeviceService) -> None:
    hardware_service.branches.exists_active.return_value = False
    data = BiometricDeviceUpdateRequest(branch_id=999)

    with pytest.raises(NotFoundException) as exc:
        await hardware_service.update_device(org_id=10, actor_id=1, device_id=1, data=data)
    assert exc.value.code == "BRANCH_NOT_FOUND"


@pytest.mark.asyncio
async def test_assign_device_to_branch_not_found(hardware_service: BiometricDeviceService) -> None:
    hardware_service.branches.exists_active.return_value = False
    data = BiometricDeviceAssignBranchRequest(branch_id=999)

    with pytest.raises(NotFoundException) as exc:
        await hardware_service.assign_device_to_branch(org_id=10, actor_id=1, device_id=1, data=data)
    assert exc.value.code == "BRANCH_NOT_FOUND"


@pytest.mark.asyncio
async def test_enable_device_already_active(hardware_service: BiometricDeviceService) -> None:
    hardware_service.devices.get_by_id_in_org.return_value = _device(is_active=True)
    res = await hardware_service.enable_device(org_id=10, actor_id=1, device_id=1)
    assert res.is_active is True
    hardware_service.devices.update.assert_not_awaited()


@pytest.mark.asyncio
async def test_disable_device_already_inactive(hardware_service: BiometricDeviceService) -> None:
    hardware_service.devices.get_by_id_in_org.return_value = _device(is_active=False)
    res = await hardware_service.disable_device(org_id=10, actor_id=1, device_id=1)
    assert res.is_active is False
    hardware_service.devices.update.assert_not_awaited()


@pytest.mark.asyncio
async def test_validate_connectivity_tcp_success(hardware_service: BiometricDeviceService) -> None:
    hardware_service.devices.get_by_id_in_org.return_value = _device(
        is_active=True,
        protocol=DeviceProtocol.TCP_IP,
        ip_address="192.168.1.100",
        port=5005,
    )
    from unittest.mock import patch
    with patch("socket.socket") as mock_sock:
        is_online = await hardware_service.validate_connectivity(org_id=10, device_id=1)
        assert is_online is True
        mock_sock.assert_called_once()


@pytest.mark.asyncio
async def test_validate_connectivity_tcp_failure(hardware_service: BiometricDeviceService) -> None:
    hardware_service.devices.get_by_id_in_org.return_value = _device(
        is_active=True,
        protocol=DeviceProtocol.TCP_IP,
        ip_address="192.168.1.100",
        port=5005,
    )
    from unittest.mock import patch
    with patch("socket.socket") as mock_sock:
        mock_sock.return_value.__enter__.return_value.connect.side_effect = Exception("Connect error")
        is_online = await hardware_service.validate_connectivity(org_id=10, device_id=1)
        assert is_online is False


@pytest.mark.asyncio
async def test_get_hardware_service_dependency() -> None:
    from app.modules.hardware.dependencies import get_hardware_service
    db_mock = AsyncMock()
    service = await get_hardware_service(db_mock)
    assert service.session == db_mock


# ===========================================================================
# INET Serialization Schema Tests
# ===========================================================================

def test_device_schema_ip_address_serialization() -> None:
    """Verify that BiometricDeviceSchema and BiometricDeviceConfigurationSchema correctly serialize all ipaddress types."""
    import ipaddress
    from app.modules.hardware.schemas import BiometricDeviceSchema, BiometricDeviceConfigurationSchema
    
    base_data = {
        "id": 1,
        "org_id": 10,
        "branch_id": None,
        "device_name": "Device A",
        "device_code": "CODE-A",
        "serial_number": "SN123",
        "protocol": DeviceProtocol.TCP_IP,
        "adms_enabled": False,
        "status": DeviceStatus.OFFLINE,
        "total_users": 0,
        "total_fingerprints": 0,
        "total_faces": 0,
        "total_cards": 0,
        "total_logs": 0,
        "is_active": True,
        "created_at": _NOW,
        "updated_at": _NOW,
    }

    # Test cases for ip_address values
    test_cases = [
        (None, None),
        ("192.168.1.100", "192.168.1.100"),
        (ipaddress.IPv4Address("192.168.1.100"), "192.168.1.100"),
        (ipaddress.IPv6Address("2001:db8::1"), "2001:db8::1"),
        (ipaddress.IPv4Interface("192.168.1.100/24"), "192.168.1.100/24"),
        (ipaddress.IPv6Interface("2001:db8::1/64"), "2001:db8::1/64"),
    ]

    for ip_val, expected_str in test_cases:
        # Test BiometricDeviceSchema
        device_data = {**base_data, "ip_address": ip_val}
        schema = BiometricDeviceSchema.model_validate(device_data)
        assert schema.ip_address == expected_str

        # Test BiometricDeviceConfigurationSchema
        config_data = {
            "ip_address": ip_val,
            "port": 5005,
            "protocol": DeviceProtocol.TCP_IP,
            "domain": None,
            "mac_address": "00:11:22:33:44:55",
            "adms_enabled": False,
            "adms_server": None,
            "adms_port": None,
            "cloud_id": None,
            "timezone": "UTC",
            "communication_key": None,
            "sync_key": None,
        }
        config_schema = BiometricDeviceConfigurationSchema.model_validate(config_data)
        assert config_schema.ip_address == expected_str


