"""Hardware module: constants and enums.

The biometric_devices table constrains `status` and `protocol` to fixed value
sets. Per the project-wide convention these are stored as VARCHAR + CHECK (not
native PostgreSQL ENUM); these enums are the single source of truth for the
allowed CHECK values.
"""

from enum import Enum


class DeviceStatus(str, Enum):
    """biometric_devices.status. (Enforced by DB CHECK; default 'offline'.)"""

    ONLINE = "online"
    OFFLINE = "offline"
    DISABLED = "disabled"
    MAINTENANCE = "maintenance"


class DeviceProtocol(str, Enum):
    """biometric_devices.protocol. (Enforced by DB CHECK; default 'tcp_ip'.)"""

    TCP_IP = "tcp_ip"
    ADMS = "adms"
    USB = "usb"
