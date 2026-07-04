"""Activity Log module: constants and enums.

The approved Activity Log Database Architecture declares `action_from` as a
native ENUM('Web App', 'Mobile App') and constrains `action_type` via a CHECK.
To keep the whole HRMS schema consistent (this project uses VARCHAR + CHECK for
enumerated columns, not native PostgreSQL ENUM types), both value sets are
implemented as CHECK constraints — the allowed values are preserved exactly.
These enums are the single source of truth for those checks.
"""

from enum import Enum


class ActionType(str, Enum):
    """activity_logs.action_type. (Enforced by DB CHECK.)

    UI-display operation vocabulary (distinct from RBAC's create/read/edit/delete).
    """

    INSERT = "Insert"
    UPDATE = "Update"
    DELETE = "Delete"
    ASSIGN = "Assign"
    BULK_ASSIGN = "Bulk Assign"


class ActionFrom(str, Enum):
    """activity_logs.action_from. (Enforced by DB CHECK; default 'Web App'.)

    Platform from which the action was performed.
    """

    WEB_APP = "Web App"
    MOBILE_APP = "Mobile App"
