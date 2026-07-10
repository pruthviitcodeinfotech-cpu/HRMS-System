"""Notifications Management — Pydantic request/response schemas (DTOs).

Defines validation, serialization, and structure rules for notifications,
notification recipients, bulk operations, timelines, and search queries.
"""

from __future__ import annotations

import datetime

from pydantic import Field, field_validator, model_validator

from app.shared.base.schema import BaseSchema
from app.shared.schemas.pagination import PaginatedResponse, PaginationRequest

# ===========================================================================
# 1. Notifications — Request/Query Schemas (DTOs)
# ===========================================================================


class NotificationCreateRequest(BaseSchema):
    """Payload for creating/registering a new notification manually (admin/system)."""

    title: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Title of the notification.",
    )
    message: str = Field(..., min_length=1, description="Message body content.")
    notification_type: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Category of the notification.",
    )
    priority: str = Field(
        ...,
        min_length=1,
        max_length=20,
        description="Priority level (e.g. low, normal, high).",
    )
    source_module: str | None = Field(
        default=None,
        max_length=100,
        description="Module origin of the notification.",
    )
    source_entity_type: str | None = Field(
        default=None,
        max_length=100,
        description="Type of related database entity.",
    )
    source_entity_id: int | None = Field(
        default=None,
        description="Database ID of the related entity.",
    )
    expires_at: datetime.datetime | None = Field(
        default=None,
        description="Expiry timestamp after which notification is hidden.",
    )
    recipient_user_ids: list[int] | None = Field(
        default=None,
        description="Optional target users to assign notification to.",
    )

    @field_validator("expires_at")
    @classmethod
    def _validate_expiry(cls, v: datetime.datetime | None) -> datetime.datetime | None:
        """Ensure expires_at is in the future relative to UTC."""
        if v is not None:
            from datetime import timezone

            now = datetime.datetime.now(timezone.utc)
            if v.tzinfo is None:
                v = v.replace(tzinfo=timezone.utc)
            if v <= now:
                raise ValueError("expires_at must be in the future")
        return v


class NotificationSearchQuery(PaginationRequest):
    """Query parameters for searching / filtering organization notifications (admin view)."""

    notification_type: str | None = Field(
        default=None,
        description="Filter by notification category.",
    )
    priority: str | None = Field(
        default=None,
        description="Filter by priority.",
    )
    source_module: str | None = Field(
        default=None,
        description="Filter by originating module.",
    )
    source_entity_type: str | None = Field(
        default=None,
        description="Filter by related entity type.",
    )
    source_entity_id: int | None = Field(
        default=None,
        description="Filter by related entity ID.",
    )
    date_from: datetime.datetime | None = Field(
        default=None,
        description="Filter notifications created after this time.",
    )
    date_to: datetime.datetime | None = Field(
        default=None,
        description="Filter notifications created before this time.",
    )
    search: str | None = Field(
        default=None,
        description="Search term matching title or message contents.",
    )


# ===========================================================================
# 2. Recipient Management — Request/Query Schemas (DTOs)
# ===========================================================================


class NotificationAssignRequest(BaseSchema):
    """Payload for manually assigning target recipient users to an existing notification."""

    user_ids: list[int] = Field(..., min_length=1, description="List of user IDs to assign.")


class NotificationRecipientSearchQuery(PaginationRequest):
    """Query parameters for filtering recipient lists and their delivery status."""

    delivered: bool | None = Field(default=None, description="Filter by delivery status.")
    read: bool | None = Field(default=None, description="Filter by read status.")


# ===========================================================================
# 3. User Notification Center — Query/Request Schemas (DTOs)
# ===========================================================================


class MyNotificationSearchQuery(PaginationRequest):
    """Query parameters for the authenticated user to view their notification center."""

    status: str | None = Field(
        default=None,
        description="Filter by read status: 'unread' or 'read'.",
    )
    archived: bool = Field(
        default=False,
        description="Filter by archive status. Default false (excludes archived).",
    )
    notification_type: str | None = Field(
        default=None,
        description="Filter by notification category.",
    )
    priority: str | None = Field(default=None, description="Filter by priority.")
    source_module: str | None = Field(default=None, description="Filter by originating module.")
    include_expired: bool = Field(
        default=False,
        description="Include notifications that have expired. Default false.",
    )

    @field_validator("status")
    @classmethod
    def _validate_status(cls, v: str | None) -> str | None:
        if v is not None and v not in ("unread", "read"):
            raise ValueError("status must be 'unread' or 'read'")
        return v


class NotificationBulkActionRequest(BaseSchema):
    """Payload for performing bulk read, archive, or delete operations on own notifications."""

    notification_ids: list[int] | None = Field(
        default=None,
        description="Specific notification IDs to target.",
    )
    all_unread: bool | None = Field(
        default=None,
        description="Apply action to all unread notifications.",
    )

    @model_validator(mode="after")
    def _validate_bulk_scope(self) -> NotificationBulkActionRequest:
        """Ensure either notification_ids is provided or all_unread is true."""
        if not self.notification_ids and not self.all_unread:
            raise ValueError("Either notification_ids or all_unread must be provided.")
        return self


# ===========================================================================
# 4. Response Schemas (DTOs)
# ===========================================================================


class NotificationSchema(BaseSchema):
    """Represents a standard notification definition."""

    id: int = Field(..., description="ID of the notification.")
    org_id: int = Field(..., description="Organization tenant context ID.")
    title: str = Field(..., description="Title of the notification.")
    message: str = Field(..., description="Message body content.")
    notification_type: str = Field(..., description="Category of the notification.")
    priority: str = Field(..., description="Priority level.")
    source_module: str | None = None
    source_entity_type: str | None = None
    source_entity_id: int | None = None
    created_by: int | None = None
    created_at: datetime.datetime
    expires_at: datetime.datetime | None = None


class NotificationDetailsSchema(NotificationSchema):
    """Response containing detailed notification details plus delivery aggregates."""

    recipient_count: int = Field(0, description="Total target recipients assigned.")
    read_count: int = Field(0, description="Total recipients who marked this notification read.")
    delivered_count: int = Field(0, description="Total recipients who received this notification.")


class NotificationRecipientSchema(BaseSchema):
    """Represents a recipient user record and their interaction state."""

    id: int = Field(..., description="Recipient record ID.")
    notification_id: int = Field(..., description="ID of the assigned notification.")
    org_id: int = Field(..., description="Organization tenant context ID.")
    user_id: int = Field(..., description="User ID of the recipient.")
    delivered_at: datetime.datetime | None = None
    read_at: datetime.datetime | None = None
    archived_at: datetime.datetime | None = None
    deleted_at: datetime.datetime | None = None
    created_at: datetime.datetime


class NotificationRecipientAssignmentResult(BaseSchema):
    """Represents the individual outcome of assigning a recipient user."""

    user_id: int = Field(..., description="ID of the target user.")
    assigned: bool = Field(..., description="Whether the assignment succeeded.")
    status: str = Field(..., description="Stable result code (e.g. 'created', 'already_assigned').")
    message: str | None = Field(default=None, description="Human-friendly status explanation.")


class NotificationAssignResponse(BaseSchema):
    """Response wrapper for a multi-status recipient assignment operation."""

    results: list[NotificationRecipientAssignmentResult] = Field(default_factory=list)


class MyNotificationSchema(BaseSchema):
    """Represents a notification record merged with the caller's recipient state."""

    id: int = Field(..., description="Notification ID.")
    org_id: int = Field(..., description="Organization tenant context ID.")
    title: str = Field(..., description="Title of the notification.")
    message: str = Field(..., description="Message body content.")
    notification_type: str = Field(..., description="Category of the notification.")
    priority: str = Field(..., description="Priority level.")
    source_module: str | None = None
    source_entity_type: str | None = None
    source_entity_id: int | None = None
    created_at: datetime.datetime = Field(..., description="Notification creation timestamp.")
    expires_at: datetime.datetime | None = None

    # Caller recipient state fields
    delivered_at: datetime.datetime | None = None
    read_at: datetime.datetime | None = None
    archived_at: datetime.datetime | None = None


class MyNotificationCountResponse(BaseSchema):
    """Counters representing the current state of my notification center."""

    unread_count: int = Field(0, description="Total active unread notifications.")
    archived_count: int = Field(0, description="Total active archived notifications.")
    total_count: int = Field(0, description="Total active non-deleted notifications.")


class NotificationBulkActionResponse(BaseSchema):
    """Outcome of bulk update operations."""

    affected_count: int = Field(..., description="Number of recipient rows affected.")


class NotificationTimelineEventSchema(BaseSchema):
    """A single state change timestamp event along the notification's recipient lifecycle."""

    event: str = Field(
        ...,
        description="Event action: 'created', 'delivered', 'read', 'archived', or 'deleted'.",
    )
    at: datetime.datetime = Field(..., description="Event occurrence timestamp.")

    @field_validator("event")
    @classmethod
    def _validate_event_type(cls, v: str) -> str:
        allowed = ("created", "delivered", "read", "archived", "deleted")
        if v not in allowed:
            raise ValueError(f"event must be one of: {', '.join(allowed)}")
        return v


# ===========================================================================
# 5. Paginated Response Envelopes
# ===========================================================================


class NotificationListResponse(PaginatedResponse[NotificationSchema]):
    """Paginated list response containing notification headers (admin)."""


class NotificationRecipientListResponse(PaginatedResponse[NotificationRecipientSchema]):
    """Paginated list response containing recipient user records."""


class MyNotificationListResponse(PaginatedResponse[MyNotificationSchema]):
    """Paginated list response for the user's notification center."""


__all__ = [
    "NotificationCreateRequest",
    "NotificationSearchQuery",
    "NotificationAssignRequest",
    "NotificationRecipientSearchQuery",
    "MyNotificationSearchQuery",
    "NotificationBulkActionRequest",
    "NotificationSchema",
    "NotificationDetailsSchema",
    "NotificationRecipientSchema",
    "NotificationRecipientAssignmentResult",
    "NotificationAssignResponse",
    "MyNotificationSchema",
    "MyNotificationCountResponse",
    "NotificationBulkActionResponse",
    "NotificationTimelineEventSchema",
    "NotificationListResponse",
    "NotificationRecipientListResponse",
    "MyNotificationListResponse",
]
