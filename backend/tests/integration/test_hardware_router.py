"""Integration tests for the Hardware / Biometric Management router."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.main import create_app
from app.modules.hardware.constants import DeviceProtocol, DeviceStatus
from app.modules.hardware.dependencies import get_hardware_service
from app.modules.hardware.router import router as hardware_router
from app.modules.hardware.schemas import (
    BiometricDeviceConfigurationSchema,
    BiometricDeviceHealthSchema,
    BiometricDeviceListResponse,
    BiometricDeviceSchema,
    BiometricDeviceStatusSchema,
)
from tests.conftest import API_PREFIX

_NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


@pytest.fixture
def mock_hardware_service() -> AsyncMock:
    """Mock stand-in for BiometricDeviceService."""
    return AsyncMock()


@pytest.fixture
def hardware_app():
    """Mounts the hardware router on the production app factory."""
    application = create_app()
    application.include_router(hardware_router, prefix=API_PREFIX)
    return application


@pytest_asyncio.fixture
async def hardware_client(hardware_app, mock_hardware_service: AsyncMock):
    """An async HTTP client bound to the app with the hardware service mocked."""
    hardware_app.dependency_overrides[get_hardware_service] = lambda: mock_hardware_service
    transport = ASGITransport(app=hardware_app)
    async with AsyncClient(transport=transport, base_url="http://test") as http_client:
        yield http_client
    hardware_app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Response Builders
# ---------------------------------------------------------------------------

def _device_detail() -> BiometricDeviceSchema:
    return BiometricDeviceSchema(
        id=1,
        org_id=10,
        device_name="Device A",
        device_code="CODE-A",
        serial_number="SN123",
        model="K90",
        manufacturer="eSSL",
        ip_address="192.168.1.100",
        port=5005,
        protocol=DeviceProtocol.TCP_IP,
        domain=None,
        mac_address="00:11:22:33:44:55",
        adms_enabled=False,
        adms_server=None,
        adms_port=None,
        cloud_id=None,
        timezone="UTC",
        status=DeviceStatus.OFFLINE,
        last_seen_at=_NOW,
        last_sync_at=_NOW,
        firmware_version="v1.0",
        software_version="v2.0",
        total_users=0,
        total_fingerprints=0,
        total_faces=0,
        total_cards=0,
        total_logs=0,
        installation_location="Main Entrance",
        remarks="N/A",
        is_active=True,
        created_by=1,
        updated_by=1,
        created_at=_NOW,
        updated_at=_NOW,
    )


def _device_list() -> BiometricDeviceListResponse:
    return BiometricDeviceListResponse.build(
        items=[_device_detail()], page=1, page_size=25, total_records=1
    )


def _device_config() -> BiometricDeviceConfigurationSchema:
    return BiometricDeviceConfigurationSchema(
        ip_address="192.168.1.100",
        port=5005,
        protocol=DeviceProtocol.TCP_IP,
        domain=None,
        mac_address="00:11:22:33:44:55",
        adms_enabled=False,
        adms_server=None,
        adms_port=None,
        cloud_id=None,
        timezone="UTC",
        communication_key_set=False,
        sync_key_set=False,
    )


def _device_status() -> BiometricDeviceStatusSchema:
    return BiometricDeviceStatusSchema(
        status=DeviceStatus.OFFLINE,
        last_seen_at=_NOW,
        last_sync_at=_NOW,
        is_active=True,
    )


def _device_health() -> BiometricDeviceHealthSchema:
    return BiometricDeviceHealthSchema(
        status=DeviceStatus.OFFLINE,
        is_active=True,
        firmware_version="v1.0",
        software_version="v2.0",
        last_seen_at=_NOW,
        last_sync_at=_NOW,
        stats={
            "total_users": 0,
            "total_fingerprints": 0,
            "total_faces": 0,
            "total_cards": 0,
            "total_logs": 0,
        },
    )


# ===========================================================================
# Endpoints Integration Tests (Happy Path)
# ===========================================================================

@pytest.mark.asyncio
async def test_register_device_201(
    hardware_client: AsyncClient, mock_hardware_service: AsyncMock, super_admin_headers
) -> None:
    mock_hardware_service.register_device.return_value = _device_detail()
    payload = {
        "device_name": "Device A",
        "device_code": "CODE-A",
        "serial_number": "SN123",
    }
    resp = await hardware_client.post(
        f"{API_PREFIX}/devices", json=payload, headers=super_admin_headers
    )
    assert resp.status_code == 201
    assert resp.json()["data"]["device_name"] == "Device A"


@pytest.mark.asyncio
async def test_list_devices_200(
    hardware_client: AsyncClient, mock_hardware_service: AsyncMock, super_admin_headers
) -> None:
    mock_hardware_service.list_devices.return_value = _device_list()
    resp = await hardware_client.get(
        f"{API_PREFIX}/devices?search=Device&page=1&page_size=25", headers=super_admin_headers
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["pagination"]["total_records"] == 1


@pytest.mark.asyncio
async def test_get_device_200(
    hardware_client: AsyncClient, mock_hardware_service: AsyncMock, super_admin_headers
) -> None:
    mock_hardware_service.get_device.return_value = _device_detail()
    resp = await hardware_client.get(f"{API_PREFIX}/devices/1", headers=super_admin_headers)
    assert resp.status_code == 200
    assert resp.json()["data"]["id"] == 1


@pytest.mark.asyncio
async def test_update_device_200(
    hardware_client: AsyncClient, mock_hardware_service: AsyncMock, super_admin_headers
) -> None:
    mock_hardware_service.update_device.return_value = _device_detail()
    resp = await hardware_client.patch(
        f"{API_PREFIX}/devices/1", json={"device_name": "New Name"}, headers=super_admin_headers
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_delete_device_204(
    hardware_client: AsyncClient, mock_hardware_service: AsyncMock, super_admin_headers
) -> None:
    mock_hardware_service.delete_device.return_value = None
    resp = await hardware_client.delete(f"{API_PREFIX}/devices/1", headers=super_admin_headers)
    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_get_device_configuration_200(
    hardware_client: AsyncClient, mock_hardware_service: AsyncMock, super_admin_headers
) -> None:
    mock_hardware_service.get_device_configuration.return_value = _device_config()
    resp = await hardware_client.get(f"{API_PREFIX}/devices/1/configuration", headers=super_admin_headers)
    assert resp.status_code == 200
    assert resp.json()["data"]["communication_key_set"] is False


@pytest.mark.asyncio
async def test_update_device_configuration_200(
    hardware_client: AsyncClient, mock_hardware_service: AsyncMock, super_admin_headers
) -> None:
    mock_hardware_service.update_device_configuration.return_value = _device_config()
    resp = await hardware_client.patch(
        f"{API_PREFIX}/devices/1/configuration", json={"ip_address": "10.0.0.1"}, headers=super_admin_headers
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_assign_device_to_branch_200(
    hardware_client: AsyncClient, mock_hardware_service: AsyncMock, super_admin_headers
) -> None:
    mock_hardware_service.assign_device_to_branch.return_value = _device_detail()
    resp = await hardware_client.put(
        f"{API_PREFIX}/devices/1/branch", json={"branch_id": 2}, headers=super_admin_headers
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_enable_device_200(
    hardware_client: AsyncClient, mock_hardware_service: AsyncMock, super_admin_headers
) -> None:
    mock_hardware_service.enable_device.return_value = _device_detail()
    resp = await hardware_client.post(f"{API_PREFIX}/devices/1/enable", headers=super_admin_headers)
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_disable_device_200(
    hardware_client: AsyncClient, mock_hardware_service: AsyncMock, super_admin_headers
) -> None:
    mock_hardware_service.disable_device.return_value = _device_detail()
    resp = await hardware_client.post(f"{API_PREFIX}/devices/1/disable", headers=super_admin_headers)
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_get_device_status_200(
    hardware_client: AsyncClient, mock_hardware_service: AsyncMock, super_admin_headers
) -> None:
    mock_hardware_service.get_device_status.return_value = _device_status()
    resp = await hardware_client.get(f"{API_PREFIX}/devices/1/status", headers=super_admin_headers)
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_report_heartbeat_200(
    hardware_client: AsyncClient, mock_hardware_service: AsyncMock, super_admin_headers
) -> None:
    mock_hardware_service.report_heartbeat.return_value = _device_detail()
    resp = await hardware_client.put(
        f"{API_PREFIX}/devices/1/heartbeat", json={"status": "online"}, headers=super_admin_headers
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_get_device_health_200(
    hardware_client: AsyncClient, mock_hardware_service: AsyncMock, super_admin_headers
) -> None:
    mock_hardware_service.get_device_health.return_value = _device_health()
    resp = await hardware_client.get(f"{API_PREFIX}/devices/1/health", headers=super_admin_headers)
    assert resp.status_code == 200


# ===========================================================================
# Authorization and Validation Errors
# ===========================================================================

@pytest.mark.asyncio
async def test_register_device_forbidden_without_permission(
    hardware_client: AsyncClient, make_access_token
) -> None:
    token = make_access_token(is_super_admin=False, permissions=[])
    resp = await hardware_client.post(
        f"{API_PREFIX}/devices",
        json={"device_name": "Device A", "device_code": "CODE-A", "serial_number": "SN123"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_register_device_missing_fields_422(
    hardware_client: AsyncClient, super_admin_headers
) -> None:
    resp = await hardware_client.post(
        f"{API_PREFIX}/devices",
        json={"device_name": "Device A"},
        headers=super_admin_headers,
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_list_devices_org_context_unresolved(
    hardware_client: AsyncClient, make_access_token
) -> None:
    # Build token with org_id = None
    token = make_access_token(is_super_admin=True, org_id=None)
    resp = await hardware_client.get(
        f"{API_PREFIX}/devices",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "TENANT_UNRESOLVED"


@pytest.mark.asyncio
async def test_list_devices_branch_scoped(
    hardware_client: AsyncClient, mock_hardware_service: AsyncMock, make_access_token
) -> None:
    mock_hardware_service.list_devices.return_value = _device_list()
    # Build token with specific branch access
    token = make_access_token(
        is_super_admin=False,
        permissions=[{"feature_key": "device", "can_read": True}],
        branch_ids=[2],
    )
    resp = await hardware_client.get(
        f"{API_PREFIX}/devices",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    # Service should be called with allowed_branch_ids=[2]
    mock_hardware_service.list_devices.assert_awaited_once()
    assert mock_hardware_service.list_devices.call_args[1]["allowed_branch_ids"] == [2]

