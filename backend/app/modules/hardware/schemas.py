"""Hardware / Biometric Management — Pydantic request/response schemas (DTOs).

Defines validation, serialization, and structure rules for biometric devices,
their network/ADMS configurations, branch assignments, connectivity status,
heartbeat logs, and health stats.
"""

from __future__ import annotations

import re
import socket
from datetime import datetime
from datetime import time as dt_time
from typing import Any

from pydantic import Field, field_validator, model_validator

from app.modules.hardware.constants import DeviceProtocol, DeviceStatus
from app.shared.base.schema import BaseSchema
from app.shared.schemas.pagination import PaginatedResponse, PaginationRequest

# ===========================================================================
# Validation Helpers
# ===========================================================================

MAC_REGEX = re.compile(r"^([0-9a-fA-F]{2}[:-]){5}[0-9a-fA-F]{2}$")


def _validate_ip_address(v: str | None) -> str | None:
    """Validate that the given string is a valid IPv4 or IPv6 address."""
    if not v:
        return v
    try:
        socket.inet_pton(socket.AF_INET, v)
        return v
    except socket.error:
        try:
            socket.inet_pton(socket.AF_INET6, v)
            return v
        except socket.error:
            raise ValueError("Invalid IP address format.")


def _validate_mac_address(v: str | None) -> str | None:
    """Validate that the given string is a valid MAC address (XX:XX:XX:XX:XX:XX or XX-XX-XX-XX-XX-XX)."""
    if not v:
        return v
    if not MAC_REGEX.match(v):
        raise ValueError("Invalid MAC address format. Expected XX:XX:XX:XX:XX:XX or XX-XX-XX-XX-XX-XX.")
    return v


def _validate_timezone(v: str | None) -> str | None:
    """Validate that the given string is a valid IANA timezone name."""
    if not v:
        return v
    try:
        from zoneinfo import ZoneInfo
        ZoneInfo(v)
        return v
    except Exception:
        raise ValueError(f"Invalid timezone name: '{v}'. Must be a valid IANA timezone.")


# ===========================================================================
# Hardware — Request Schemas (DTOs)
# ===========================================================================


class BiometricDeviceRegisterRequest(BaseSchema):
    """Payload for registering a new biometric device."""

    device_name: str = Field(..., min_length=1, max_length=150, description="Human-readable name for the device.")
    device_code: str = Field(..., min_length=1, max_length=50, description="Unique code identifier per organization.")
    serial_number: str = Field(..., min_length=1, max_length=100, description="Globally unique hardware serial number.")
    model: str | None = Field(default=None, max_length=100, description="Hardware model (e.g. eSSL K90 Pro).")
    manufacturer: str | None = Field(default=None, max_length=100, description="Manufacturer name (e.g. eSSL).")
    branch_id: int | None = Field(default=None, description="Initial branch assignment ID.")

    # Network settings
    ip_address: str | None = Field(default=None, description="Static or dynamic IP address of the device.")
    port: int | None = Field(default=None, ge=1, le=65535, description="Network port for direct connection.")
    protocol: DeviceProtocol = Field(default=DeviceProtocol.TCP_IP, description="Communication protocol.")
    domain: str | None = Field(default=None, max_length=255, description="Domain name if applicable.")
    mac_address: str | None = Field(default=None, max_length=17, description="Device MAC address.")

    # ADMS Configuration
    adms_enabled: bool = Field(default=False, description="Whether ADMS sync is enabled.")
    adms_server: str | None = Field(default=None, max_length=255, description="ADMS server address.")
    adms_port: int | None = Field(default=None, ge=1, le=65535, description="ADMS port.")
    cloud_id: str | None = Field(default=None, max_length=100, description="Cloud/Device identifier used by ADMS.")
    communication_key: str | None = Field(default=None, max_length=255, repr=False, description="Write-only key for API requests.")
    sync_key: str | None = Field(default=None, max_length=255, repr=False, description="Write-only key for data sync.")
    timezone: str | None = Field(default=None, max_length=50, description="Timezone name configured on the device.")

    # Location
    installation_location: str | None = Field(default=None, max_length=255, description="Specific location of install.")
    remarks: str | None = Field(default=None, description="General notes or observations.")

    # Validators
    @field_validator("ip_address")
    @classmethod
    def _validate_ip(cls, v: str | None) -> str | None:
        return _validate_ip_address(v)

    @field_validator("mac_address")
    @classmethod
    def _validate_mac(cls, v: str | None) -> str | None:
        return _validate_mac_address(v)

    @field_validator("timezone")
    @classmethod
    def _validate_tz(cls, v: str | None) -> str | None:
        return _validate_timezone(v)


class BiometricDeviceUpdateRequest(BaseSchema):
    """Payload for patching / updating an existing biometric device registry."""

    device_name: str | None = Field(default=None, min_length=1, max_length=150, description="Name for the device.")
    device_code: str | None = Field(default=None, min_length=1, max_length=50, description="Unique code identifier per organization.")
    serial_number: str | None = Field(default=None, min_length=1, max_length=100, description="Hardware serial number.")
    model: str | None = Field(default=None, max_length=100, description="Hardware model.")
    manufacturer: str | None = Field(default=None, max_length=100, description="Manufacturer name.")
    branch_id: int | None = Field(default=None, description="Branch assignment ID.")

    # Network settings
    ip_address: str | None = Field(default=None, description="Static or dynamic IP address.")
    port: int | None = Field(default=None, ge=1, le=65535, description="Network port.")
    protocol: DeviceProtocol | None = Field(default=None, description="Communication protocol.")
    domain: str | None = Field(default=None, max_length=255, description="Domain name.")
    mac_address: str | None = Field(default=None, max_length=17, description="Device MAC address.")

    # ADMS Configuration
    adms_enabled: bool | None = Field(default=None, description="Whether ADMS sync is enabled.")
    adms_server: str | None = Field(default=None, max_length=255, description="ADMS server address.")
    adms_port: int | None = Field(default=None, ge=1, le=65535, description="ADMS port.")
    cloud_id: str | None = Field(default=None, max_length=100, description="Cloud ID.")
    communication_key: str | None = Field(default=None, max_length=255, repr=False, description="Write-only key.")
    sync_key: str | None = Field(default=None, max_length=255, repr=False, description="Write-only key.")
    timezone: str | None = Field(default=None, max_length=50, description="Timezone name.")

    # Location
    installation_location: str | None = Field(default=None, max_length=255, description="Specific location of install.")
    remarks: str | None = Field(default=None, description="General notes.")

    # Validators
    @field_validator("ip_address")
    @classmethod
    def _validate_ip(cls, v: str | None) -> str | None:
        return _validate_ip_address(v)

    @field_validator("mac_address")
    @classmethod
    def _validate_mac(cls, v: str | None) -> str | None:
        return _validate_mac_address(v)

    @field_validator("timezone")
    @classmethod
    def _validate_tz(cls, v: str | None) -> str | None:
        return _validate_timezone(v)


class BiometricDeviceConfigureRequest(BaseSchema):
    """Payload for configuring network + ADMS parameters of a biometric device."""

    ip_address: str | None = Field(default=None, description="Device IP address.")
    port: int | None = Field(default=None, ge=1, le=65535, description="Direct TCP port.")
    protocol: DeviceProtocol | None = Field(default=None, description="Communication protocol.")
    domain: str | None = Field(default=None, max_length=255, description="Device Domain name.")
    mac_address: str | None = Field(default=None, max_length=17, description="MAC address.")

    adms_enabled: bool | None = Field(default=None, description="True to enable ADMS mode.")
    adms_server: str | None = Field(default=None, max_length=255, description="ADMS server URL/Host.")
    adms_port: int | None = Field(default=None, ge=1, le=65535, description="ADMS server port.")
    cloud_id: str | None = Field(default=None, max_length=100, description="Cloud ID.")
    communication_key: str | None = Field(default=None, max_length=255, repr=False, description="Write-only communication security key.")
    sync_key: str | None = Field(default=None, max_length=255, repr=False, description="Write-only synchronization key.")
    timezone: str | None = Field(default=None, max_length=50, description="IANA timezone name.")

    # Validators
    @field_validator("ip_address")
    @classmethod
    def _validate_ip(cls, v: str | None) -> str | None:
        return _validate_ip_address(v)

    @field_validator("mac_address")
    @classmethod
    def _validate_mac(cls, v: str | None) -> str | None:
        return _validate_mac_address(v)

    @field_validator("timezone")
    @classmethod
    def _validate_tz(cls, v: str | None) -> str | None:
        return _validate_timezone(v)


class BiometricDeviceAssignBranchRequest(BaseSchema):
    """Payload to assign or unassign a biometric device to/from a branch."""

    branch_id: int | None = Field(..., description="Branch ID to assign the device to. Provide null to unassign.")


class BiometricDeviceHeartbeatRequest(BaseSchema):
    """Payload sent by device agent or integration worker to report connectivity status & metrics."""

    status: DeviceStatus | None = Field(default=None, description="Current connectivity status.")
    last_seen_at: datetime | None = Field(default=None, description="Timestamp of status ping.")
    last_sync_at: datetime | None = Field(default=None, description="Timestamp of last log ingestion.")
    firmware_version: str | None = Field(default=None, max_length=50, description="Firmware version.")
    software_version: str | None = Field(default=None, max_length=50, description="Software version.")

    total_users: int | None = Field(default=None, ge=0, description="Total active registered users.")
    total_fingerprints: int | None = Field(default=None, ge=0, description="Total registered templates.")
    total_faces: int | None = Field(default=None, ge=0, description="Total registered face templates.")
    total_cards: int | None = Field(default=None, ge=0, description="Total registered RFID cards.")
    total_logs: int | None = Field(default=None, ge=0, description="Total punches recorded on the device.")


class BiometricDeviceSearchQuery(PaginationRequest):
    """Query parameters for searching / filtering registered devices."""

    search: str | None = Field(default=None, description="Free-text search on name, code, or serial.")
    status: DeviceStatus | None = Field(default=None, description="Filter by connectivity status.")
    protocol: DeviceProtocol | None = Field(default=None, description="Filter by protocol.")
    branch_id: int | None = Field(default=None, description="Filter by branch assignment.")
    is_active: bool | None = Field(default=None, description="Filter by administrative active flag.")
    adms_enabled: bool | None = Field(default=None, description="Filter by ADMS enabled mode.")
    sort_by: str | None = Field(default=None, description="Field to sort by (device_name, created_at, last_seen_at).")
    sort_order: str | None = Field(default=None, description="Sort order: asc, desc.")


# ===========================================================================
# Hardware — Response Schemas (DTOs)
# ===========================================================================


class BiometricDeviceSchema(BaseSchema):
    """Full biometric device registry detail response schema (secrets redacted)."""

    id: int = Field(..., description="Unique device PK.")
    org_id: int = Field(..., description="Organization/Tenant ID.")
    branch_id: int | None = Field(default=None, description="Assigned branch ID.")
    device_name: str = Field(..., description="Name for the device.")
    device_code: str = Field(..., description="Unique code identifier per organization.")
    serial_number: str = Field(..., description="Hardware serial number.")
    model: str | None = Field(default=None, description="Hardware model.")
    manufacturer: str | None = Field(default=None, description="Manufacturer name.")

    # Network
    ip_address: str | None = Field(default=None, description="Device IP address.")
    port: int | None = Field(default=None, description="Direct connection port.")
    protocol: DeviceProtocol = Field(..., description="Communication protocol.")
    domain: str | None = Field(default=None, description="Domain name.")
    mac_address: str | None = Field(default=None, description="MAC address.")

    # ADMS Config
    adms_enabled: bool = Field(..., description="ADMS state.")
    adms_server: str | None = Field(default=None, description="ADMS server.")
    adms_port: int | None = Field(default=None, description="ADMS port.")
    cloud_id: str | None = Field(default=None, description="Cloud ID.")
    timezone: str | None = Field(default=None, description="IANA timezone name.")

    # Connectivity / Status
    status: DeviceStatus = Field(..., description="Connectivity status.")
    last_seen_at: datetime | None = Field(default=None, description="Last seen ping time.")
    last_sync_at: datetime | None = Field(default=None, description="Last punch ingestion time.")
    firmware_version: str | None = Field(default=None, description="Firmware version.")
    software_version: str | None = Field(default=None, description="Software version.")

    # Stats
    total_users: int = Field(..., description="Registered users.")
    total_fingerprints: int = Field(..., description="Registered fingerprints.")
    total_faces: int = Field(..., description="Registered faces.")
    total_cards: int = Field(..., description="Registered cards.")
    total_logs: int = Field(..., description="Total log count.")

    # Location
    installation_location: str | None = Field(default=None, description="Specific location.")
    remarks: str | None = Field(default=None, description="General notes.")

    # Audit
    is_active: bool = Field(..., description="Whether device is administratively enabled.")
    created_by: int | None = Field(default=None, description="Creator user ID.")
    updated_by: int | None = Field(default=None, description="Last updater user ID.")
    created_at: datetime = Field(..., description="Registry creation timestamp.")
    updated_at: datetime = Field(..., description="Last registry update timestamp.")


class BiometricDeviceListResponse(PaginatedResponse[BiometricDeviceSchema]):
    """Paginated list response for biometric devices."""


# Fields not resolved from the device row itself: the ``*_key_set`` booleans are
# derived from the write-only keys, and the org-settings fields are merged in by
# the service (Settings module `org_settings`), so ORM-object resolution must not
# stomp their defaults with ``None``.
_COMPUTED_CONFIGURATION_FIELDS = (
    "communication_key_set",
    "sync_key_set",
    "device_sync_time",
    "sync_code_set",
    "pass_code_set",
)


class BiometricDeviceConfigurationSchema(BaseSchema):
    """Response representing the network and ADMS configuration details of a device (secrets redacted)."""

    ip_address: str | None = Field(default=None, description="Device IP address.")
    port: int | None = Field(default=None, description="Direct connection port.")
    protocol: DeviceProtocol = Field(..., description="Communication protocol.")
    domain: str | None = Field(default=None, description="Domain name.")
    mac_address: str | None = Field(default=None, description="MAC address.")

    adms_enabled: bool = Field(..., description="Whether ADMS is enabled.")
    adms_server: str | None = Field(default=None, description="ADMS server address.")
    adms_port: int | None = Field(default=None, description="ADMS port.")
    cloud_id: str | None = Field(default=None, description="Cloud/ADMS device code.")
    timezone: str | None = Field(default=None, description="IANA timezone name.")

    communication_key_set: bool = Field(default=False, description="True if the communication key is set.")
    sync_key_set: bool = Field(default=False, description="True if the sync key is set.")

    # Org-wide hardware settings (Settings module `org_settings`); defaults apply
    # when the org has no settings row. Codes are exposed as booleans only.
    device_sync_time: dt_time = Field(
        default=dt_time(16, 51),
        description="Org-wide daily device synchronization time (org_settings.device_sync_time).",
    )
    sync_code_set: bool = Field(default=False, description="True if the org sync code is set.")
    pass_code_set: bool = Field(default=False, description="True if the org pass code is set.")

    @model_validator(mode="before")
    @classmethod
    def resolve_keys_set(cls, values: Any) -> Any:
        if not isinstance(values, dict):
            resolved = {}
            for field in cls.model_fields:
                if field not in _COMPUTED_CONFIGURATION_FIELDS:
                    resolved[field] = getattr(values, field, None)
            
            comm_key = getattr(values, "communication_key", None)
            sync_key = getattr(values, "sync_key", None)
            resolved["communication_key_set"] = bool(comm_key)
            resolved["sync_key_set"] = bool(sync_key)
            return resolved
        
        values = dict(values)
        values["communication_key_set"] = bool(values.get("communication_key"))
        values["sync_key_set"] = bool(values.get("sync_key"))
        return values


class BiometricDeviceStatusSchema(BaseSchema):
    """Response showing connectivity status & last communication timestamps of a device."""

    status: DeviceStatus = Field(..., description="Connectivity status.")
    last_seen_at: datetime | None = Field(default=None, description="Last seen ping time.")
    last_sync_at: datetime | None = Field(default=None, description="Last punch ingestion time.")
    is_active: bool = Field(..., description="Administrative active flag.")


class BiometricDeviceStatsSchema(BaseSchema):
    """Embedded stats schema for health reporting."""

    total_users: int = Field(..., description="Registered users.")
    total_fingerprints: int = Field(..., description="Registered fingerprints.")
    total_faces: int = Field(..., description="Registered faces.")
    total_cards: int = Field(..., description="Registered cards.")
    total_logs: int = Field(..., description="Total log count.")


class BiometricDeviceHealthSchema(BaseSchema):
    """Response showing diagnostic health parameters and user/log counts of a device."""

    status: DeviceStatus = Field(..., description="Connectivity status.")
    is_active: bool = Field(..., description="Administrative active flag.")
    firmware_version: str | None = Field(default=None, description="Firmware version.")
    software_version: str | None = Field(default=None, description="Software version.")
    last_seen_at: datetime | None = Field(default=None, description="Last seen ping time.")
    last_sync_at: datetime | None = Field(default=None, description="Last punch ingestion time.")
    stats: BiometricDeviceStatsSchema = Field(..., description="Capacity usage details.")

    @model_validator(mode="before")
    @classmethod
    def nest_stats(cls, values: Any) -> Any:
        if not isinstance(values, dict):
            resolved = {}
            for field in cls.model_fields:
                if field != "stats":
                    resolved[field] = getattr(values, field, None)
            
            resolved["stats"] = {
                "total_users": getattr(values, "total_users", 0),
                "total_fingerprints": getattr(values, "total_fingerprints", 0),
                "total_faces": getattr(values, "total_faces", 0),
                "total_cards": getattr(values, "total_cards", 0),
                "total_logs": getattr(values, "total_logs", 0),
            }
            return resolved
        
        if "stats" not in values:
            values = dict(values)
            values["stats"] = {
                "total_users": values.get("total_users", 0),
                "total_fingerprints": values.get("total_fingerprints", 0),
                "total_faces": values.get("total_faces", 0),
                "total_cards": values.get("total_cards", 0),
                "total_logs": values.get("total_logs", 0),
            }
        return values
