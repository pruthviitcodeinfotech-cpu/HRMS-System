"""Unit tests for the Hardware / Biometric Management request and response schemas."""

from __future__ import annotations

from datetime import datetime, timezone
import pytest
from pydantic import ValidationError

from app.modules.hardware.constants import DeviceProtocol, DeviceStatus
from app.modules.hardware.schemas import (
    BiometricDeviceAssignBranchRequest,
    BiometricDeviceConfigurationSchema,
    BiometricDeviceConfigureRequest,
    BiometricDeviceHealthSchema,
    BiometricDeviceHeartbeatRequest,
    BiometricDeviceRegisterRequest,
    BiometricDeviceSchema,
    BiometricDeviceSearchQuery,
    BiometricDeviceUpdateRequest,
)


def test_ip_address_validation() -> None:
    # Valid IPv4
    req = BiometricDeviceRegisterRequest(
        device_name="Main Entry",
        device_code="D001",
        serial_number="SN1234567890",
        ip_address="192.168.1.100",
    )
    assert req.ip_address == "192.168.1.100"

    # Valid IPv6
    req = BiometricDeviceRegisterRequest(
        device_name="Main Entry",
        device_code="D001",
        serial_number="SN1234567890",
        ip_address="2001:db8::1",
    )
    assert req.ip_address == "2001:db8::1"

    # Invalid IP
    with pytest.raises(ValidationError) as exc:
        BiometricDeviceRegisterRequest(
            device_name="Main Entry",
            device_code="D001",
            serial_number="SN1234567890",
            ip_address="256.0.0.1",
        )
    assert "Invalid IP address format." in str(exc.value)


def test_mac_address_validation() -> None:
    # Valid colon-separated MAC
    req = BiometricDeviceRegisterRequest(
        device_name="Main Entry",
        device_code="D001",
        serial_number="SN1234567890",
        mac_address="00:1A:2B:3C:4D:5E",
    )
    assert req.mac_address == "00:1A:2B:3C:4D:5E"

    # Valid hyphen-separated MAC
    req = BiometricDeviceRegisterRequest(
        device_name="Main Entry",
        device_code="D001",
        serial_number="SN1234567890",
        mac_address="00-1a-2b-3c-4d-5e",
    )
    assert req.mac_address == "00-1a-2b-3c-4d-5e"

    # Invalid MAC
    with pytest.raises(ValidationError) as exc:
        BiometricDeviceRegisterRequest(
            device_name="Main Entry",
            device_code="D001",
            serial_number="SN1234567890",
            mac_address="001A2B3C4D5E",
        )
    assert "Invalid MAC address format." in str(exc.value)


def test_timezone_validation() -> None:
    # Valid timezone
    req = BiometricDeviceRegisterRequest(
        device_name="Main Entry",
        device_code="D001",
        serial_number="SN1234567890",
        timezone="Asia/Kolkata",
    )
    assert req.timezone == "Asia/Kolkata"

    # Invalid timezone
    with pytest.raises(ValidationError) as exc:
        BiometricDeviceRegisterRequest(
            device_name="Main Entry",
            device_code="D001",
            serial_number="SN1234567890",
            timezone="Invalid/Timezone",
        )
    assert "Invalid timezone name" in str(exc.value)


def test_port_validation() -> None:
    # Valid port range
    req = BiometricDeviceRegisterRequest(
        device_name="Main Entry",
        device_code="D001",
        serial_number="SN1234567890",
        port=8080,
        adms_port=5000,
    )
    assert req.port == 8080
    assert req.adms_port == 5000

    # Invalid port range (too low)
    with pytest.raises(ValidationError):
        BiometricDeviceRegisterRequest(
            device_name="Main Entry",
            device_code="D001",
            serial_number="SN1234567890",
            port=0,
        )

    # Invalid port range (too high)
    with pytest.raises(ValidationError):
        BiometricDeviceRegisterRequest(
            device_name="Main Entry",
            device_code="D001",
            serial_number="SN1234567890",
            port=65536,
        )


def test_heartbeat_request_validation() -> None:
    # Valid statistics values
    req = BiometricDeviceHeartbeatRequest(
        status=DeviceStatus.ONLINE,
        total_users=10,
        total_fingerprints=20,
    )
    assert req.status == DeviceStatus.ONLINE
    assert req.total_users == 10
    assert req.total_fingerprints == 20

    # Invalid statistics (negative)
    with pytest.raises(ValidationError):
        BiometricDeviceHeartbeatRequest(
            total_users=-1,
        )


def test_configuration_schema_key_resolution() -> None:
    # Keys set (dict input)
    cfg = BiometricDeviceConfigurationSchema.model_validate(
        {
            "protocol": "adms",
            "adms_enabled": True,
            "communication_key": "somekey",
            "sync_key": "sync",
        }
    )
    assert cfg.communication_key_set is True
    assert cfg.sync_key_set is True

    # Keys not set (dict input)
    cfg = BiometricDeviceConfigurationSchema.model_validate(
        {
            "protocol": "adms",
            "adms_enabled": True,
            "communication_key": None,
            "sync_key": "",
        }
    )
    assert cfg.communication_key_set is False
    assert cfg.sync_key_set is False

    # Object representation mock
    class DummyDevice:
        def __init__(self):
            self.protocol = DeviceProtocol.ADMS
            self.adms_enabled = True
            self.communication_key = "abc"
            self.sync_key = None
            self.ip_address = "192.168.1.1"
            self.port = 80
            self.domain = None
            self.mac_address = None
            self.adms_server = None
            self.adms_port = None
            self.cloud_id = None
            self.timezone = None

    dummy = DummyDevice()
    cfg_obj = BiometricDeviceConfigurationSchema.model_validate(dummy)
    assert cfg_obj.communication_key_set is True
    assert cfg_obj.sync_key_set is False
    assert cfg_obj.ip_address == "192.168.1.1"


def test_health_schema_stats_nesting() -> None:
    now = datetime.now(timezone.utc)
    # Dict input with stats missing, checking nesting logic
    health = BiometricDeviceHealthSchema.model_validate(
        {
            "status": "online",
            "is_active": True,
            "last_seen_at": now,
            "total_users": 100,
            "total_fingerprints": 200,
            "total_faces": 5,
            "total_cards": 50,
            "total_logs": 1000,
        }
    )
    assert health.stats.total_users == 100
    assert health.stats.total_fingerprints == 200
    assert health.stats.total_faces == 5
    assert health.stats.total_cards == 50
    assert health.stats.total_logs == 1000

    # Object representation mock
    class DummyDeviceHealth:
        def __init__(self):
            self.status = DeviceStatus.ONLINE
            self.is_active = True
            self.firmware_version = "v1.0"
            self.software_version = "v2.0"
            self.last_seen_at = now
            self.last_sync_at = None
            self.total_users = 15
            self.total_fingerprints = 30
            self.total_faces = 0
            self.total_cards = 15
            self.total_logs = 200

    dummy = DummyDeviceHealth()
    health_obj = BiometricDeviceHealthSchema.model_validate(dummy)
    assert health_obj.stats.total_users == 15
    assert health_obj.stats.total_logs == 200
    assert health_obj.firmware_version == "v1.0"


def test_assign_branch_request() -> None:
    req = BiometricDeviceAssignBranchRequest(branch_id=123)
    assert req.branch_id == 123

    # Explicit None allowed
    req_none = BiometricDeviceAssignBranchRequest(branch_id=None)
    assert req_none.branch_id is None

    # Missing field should raise ValidationError
    with pytest.raises(ValidationError):
        BiometricDeviceAssignBranchRequest()


def test_schemas_empty_optional_fields() -> None:
    # Test register request with empty/None optional fields to hit validator bypasses
    req = BiometricDeviceRegisterRequest(
        device_name="Main Entry",
        device_code="D001",
        serial_number="SN1234567890",
        ip_address=None,
        mac_address=None,
        timezone=None,
    )
    assert req.ip_address is None
    assert req.mac_address is None
    assert req.timezone is None

    # Test configure request with empty/None optional fields
    cfg = BiometricDeviceConfigureRequest(
        ip_address=None,
        mac_address=None,
        timezone=None,
    )
    assert cfg.ip_address is None
    assert cfg.mac_address is None
    assert cfg.timezone is None

