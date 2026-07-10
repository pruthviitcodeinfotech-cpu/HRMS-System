"""Activity Log / Audit — Pydantic request/response schemas (DTOs).

Defines the read-only query and response contracts for the append-only
``activity_logs`` audit trail (contract §3–§6). The ``ActionType`` / ``ActionFrom``
value sets — which exist only at the DB-model level via CHECK constraints — are
surfaced here as typed request filters and response fields so clients get
validated enums (invalid values → ``422``).

Field-naming note: per project convention no field is named ``date`` with a
``date`` annotation; the module uses ``import datetime`` + ``datetime.date`` /
``datetime.time`` / ``datetime.datetime`` throughout.
"""

from __future__ import annotations

import datetime
from enum import Enum

from pydantic import Field

from app.core.constants.enums import SortOrder
from app.modules.audit.constants import ActionFrom, ActionType
from app.shared.base.schema import BaseSchema
from app.shared.schemas.pagination import PaginatedResponse, PaginationRequest


class SecurityEventType(str, Enum):
    """Approximate security-event categories mapped over ``activity_logs`` (§6)."""

    PERMISSION_CHANGE = "permission_change"
    ROLE_ASSIGNMENT = "role_assignment"
    ACCOUNT_STATUS_CHANGE = "account_status_change"


# ===========================================================================
# Request query schemas
# ===========================================================================


class ActivityLogSearchQuery(PaginationRequest):
    """Full filter/sort set for the list/search/module-wise endpoint (§3, §4)."""

    module: str | None = Field(default=None, max_length=100, description="Filter by module.")
    sub_module: str | None = Field(default=None, max_length=150, description="Sub-module filter.")
    action_type: ActionType | None = Field(default=None, description="Filter by action type.")
    action_from: ActionFrom | None = Field(default=None, description="Filter by platform.")
    employee_id: int | None = Field(default=None, description="Filter by employee subject.")
    performed_by_user_id: int | None = Field(default=None, description="Filter by acting user.")
    date_from: datetime.date | None = Field(default=None, description="Lower bound on log_date.")
    date_to: datetime.date | None = Field(default=None, description="Upper bound on log_date.")
    search: str | None = Field(default=None, description="Free-text on title/description.")
    sort_by: str | None = Field(default=None, description="logged_at (default) | log_date.")
    sort_order: SortOrder = Field(default=SortOrder.DESC, description="asc | desc.")


class SubjectActivityLogQuery(PaginationRequest):
    """Filters for the per-employee / per-user change-history views (§5)."""

    module: str | None = Field(default=None, max_length=100, description="Filter by module.")
    sub_module: str | None = Field(default=None, max_length=150, description="Sub-module filter.")
    action_type: ActionType | None = Field(default=None, description="Filter by action type.")
    date_from: datetime.date | None = Field(default=None, description="Lower bound on log_date.")
    date_to: datetime.date | None = Field(default=None, description="Upper bound on log_date.")
    sort_by: str | None = Field(default=None, description="logged_at (default) | log_date.")
    sort_order: SortOrder = Field(default=SortOrder.DESC, description="asc | desc.")


class SecurityEventQuery(PaginationRequest):
    """Filters for the approximate security-event timeline (§6)."""

    event: SecurityEventType | None = Field(default=None, description="Security-event category.")
    employee_id: int | None = Field(default=None, description="Filter by employee subject.")
    performed_by_user_id: int | None = Field(default=None, description="Filter by acting user.")
    date_from: datetime.date | None = Field(default=None, description="Lower bound on log_date.")
    date_to: datetime.date | None = Field(default=None, description="Upper bound on log_date.")


# ===========================================================================
# Response schemas
# ===========================================================================


class ActivityLogListItem(BaseSchema):
    """Compact audit row for list responses (§4.1)."""

    id: int = Field(..., description="Audit row id (BIGINT).")
    module: str = Field(..., description="Originating module.")
    sub_module: str | None = Field(default=None, description="Sub-module.")
    title: str = Field(..., description="Short event title.")
    action_type: ActionType = Field(..., description="Mutation action type.")
    employee_id: int | None = Field(default=None, description="Audited employee id (subject).")
    employee_name: str | None = Field(default=None, description="Employee name snapshot.")
    performed_by_user_id: int | None = Field(default=None, description="Acting user id.")
    performed_by_name: str = Field(..., description="Acting user name snapshot.")
    log_date: datetime.date = Field(..., description="Event date.")
    log_time: datetime.time = Field(..., description="Event time.")
    logged_at: datetime.datetime = Field(..., description="Timezone-aware event timestamp.")
    action_from: ActionFrom = Field(..., description="Originating platform.")


class ActivityLogDetail(ActivityLogListItem):
    """Full audit row for the detail endpoint (§4.2) — adds description/payroll_date."""

    org_id: int = Field(..., description="Owning organization/tenant id.")
    description: str = Field(..., description="Full event description.")
    payroll_date: datetime.date | None = Field(default=None, description="Related payroll date.")


class ActivityLogListResponse(PaginatedResponse[ActivityLogListItem]):
    """Paginated list response for audit rows."""


__all__ = [
    "SecurityEventType",
    "ActivityLogSearchQuery",
    "SubjectActivityLogQuery",
    "SecurityEventQuery",
    "ActivityLogListItem",
    "ActivityLogDetail",
    "ActivityLogListResponse",
]
