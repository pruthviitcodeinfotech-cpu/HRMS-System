"""Leave & Holiday Management module: constants and enums.

Enums mirror the value sets defined in the approved Leave & Holiday Management
Database Architecture. Where the architecture defines a CHECK constraint, the
enum is the single source of truth for that DB-level check; where it does not,
the enum is for application use only (noted per enum). Native PostgreSQL ENUM
types are intentionally NOT used — the architecture models these as VARCHAR
columns with (optional) CHECK constraints, and that is preserved.
"""

from enum import Enum


class LeaveCycle(str, Enum):
    """leave_settings.leave_cycle. (No DB CHECK per the architecture.)"""

    CALENDAR_YEAR = "calendar_year"
    FINANCIAL_YEAR = "financial_year"


class AllocationFrequency(str, Enum):
    """leave_types.allocation_frequency. (Enforced by DB CHECK.)"""

    MONTHLY = "monthly"
    YEARLY = "yearly"


class CarryForwardFrequency(str, Enum):
    """leave_types.carry_forward_frequency. (Enforced by DB CHECK.)"""

    MONTHLY = "monthly"
    YEARLY = "yearly"


class EncashmentFrequency(str, Enum):
    """leave_types.encashment_frequency (nullable). (Enforced by DB CHECK.)"""

    MONTHLY = "monthly"
    YEARLY = "yearly"


class AllocationSource(str, Enum):
    """employee_leave_allocations.allocation_source. (No DB CHECK per the architecture.)"""

    AUTO = "auto"
    MANUAL = "manual"


class AdjustmentType(str, Enum):
    """leave_balance_adjustments.adjustment_type. (No DB CHECK per the architecture.)"""

    BULK_ADJUST = "bulk_adjust"
    BULK_UPDATE = "bulk_update"
    MANUAL = "manual"


class LeaveRequestStatus(str, Enum):
    """leave_requests.status. (Enforced by DB CHECK.)"""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
