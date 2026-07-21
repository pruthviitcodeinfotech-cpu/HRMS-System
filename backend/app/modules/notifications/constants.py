"""notifications: Module constants, enums, and RBAC permission keys.

``notification_type`` and ``priority`` are free-text in the database (no CHECK
constraint); the enums below are the application-level catalog referenced by
the approved Notification Management API Contract (§10 Q2). System-generated
emissions from other business modules must use these values.
"""

try:
    from enum import StrEnum
except ImportError:
    from enum import Enum

    class StrEnum(str, Enum):
        pass


class NotificationType(StrEnum):
    """Application-level catalog of ``notifications.notification_type`` values."""

    APPROVAL = "approval"
    PAYROLL = "payroll"


class NotificationPriority(StrEnum):
    """Application-level catalog of ``notifications.priority`` values."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
