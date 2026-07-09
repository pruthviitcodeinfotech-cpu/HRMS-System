"""Shared, cross-cutting enumerations and constants.

Only genuinely reusable values live here — values not owned by any single business
module. Module-specific enums (e.g. leave/payroll status sets) stay in their own
``modules/<name>/constants.py`` and are NOT duplicated here.
"""

from enum import Enum


class Environment(str, Enum):
    """Deployment environment (``ENVIRONMENT`` setting)."""

    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TEST = "test"


class LogFormat(str, Enum):
    """Log rendering format (``LOG_FORMAT`` setting)."""

    JSON = "json"
    CONSOLE = "console"


class StorageBackend(str, Enum):
    """File-storage backend (``STORAGE_BACKEND`` setting)."""

    LOCAL = "local"
    S3 = "s3"


class SortOrder(str, Enum):
    """Generic sort direction used by list endpoints."""

    ASC = "asc"
    DESC = "desc"


class PermissionAction(str, Enum):
    """The four CRUD actions of the project's RBAC feature-permission model.

    Mirrors the ``can_create``/``can_read``/``can_edit``/``can_delete`` flags on
    ``rights_template_permissions`` / ``user_custom_permissions``.
    """

    CREATE = "create"
    READ = "read"
    EDIT = "edit"
    DELETE = "delete"


# --- Pagination defaults (shared across every list endpoint) -----------------
DEFAULT_PAGE = 1
DEFAULT_PAGE_SIZE = 25
MIN_PAGE_SIZE = 1
MAX_PAGE_SIZE = 200

# --- Request context ---------------------------------------------------------
REQUEST_ID_HEADER = "X-Request-ID"
"""Response/echo header carrying the per-request correlation id."""
