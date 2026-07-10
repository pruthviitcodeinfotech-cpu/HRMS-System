"""Unit tests for the Notification Management Pydantic request-schema validation.

Exercises the Pydantic v2 validators for notifications, recipients, search queries,
bulk action scopes, and timeline event schemas.
"""

from __future__ import annotations

import datetime
from datetime import timezone

import pytest
from pydantic import ValidationError

from app.modules.notifications.schemas import (
    MyNotificationSearchQuery,
    NotificationAssignRequest,
    NotificationBulkActionRequest,
    NotificationCreateRequest,
    NotificationRecipientSearchQuery,
    NotificationSearchQuery,
    NotificationTimelineEventSchema,
)

# --- 1. Notification Create Request Tests -----------------------------------


def test_notification_create_valid() -> None:
    future_time = datetime.datetime.now(timezone.utc) + datetime.timedelta(days=1)  # noqa: UP017
    req = NotificationCreateRequest(
        title="System Maintenance",
        message="The system will be down for 2 hours.",
        notification_type="system",
        priority="high",
        source_module="infrastructure",
        expires_at=future_time,
        recipient_user_ids=[1, 2, 3],
    )
    assert req.title == "System Maintenance"
    assert req.expires_at == future_time
    assert req.recipient_user_ids == [1, 2, 3]


def test_notification_create_invalid_expiry() -> None:
    # expires_at must be in the future
    past_time = datetime.datetime.now(timezone.utc) - datetime.timedelta(days=1)  # noqa: UP017
    with pytest.raises(ValidationError, match="expires_at must be in the future"):
        NotificationCreateRequest(
            title="System Maintenance",
            message="The system will be down for 2 hours.",
            notification_type="system",
            priority="high",
            expires_at=past_time,
        )


def test_notification_create_naive_expiry() -> None:
    # A naive datetime should automatically get tzinfo=timezone.utc applied
    future_time_naive = datetime.datetime.now() + datetime.timedelta(days=1)
    req = NotificationCreateRequest(
        title="System Maintenance",
        message="The system will be down for 2 hours.",
        notification_type="system",
        priority="high",
        expires_at=future_time_naive,
    )
    assert req.expires_at is not None
    assert req.expires_at.tzinfo == timezone.utc  # noqa: UP017


# --- 2. Notification Search Query Tests ------------------------------------


def test_notification_search_query_valid() -> None:
    query = NotificationSearchQuery(
        notification_type="alert",
        priority="low",
        search="test search",
    )
    assert query.notification_type == "alert"
    assert query.priority == "low"
    assert query.search == "test search"


# --- 3. Recipient Assignment & Search Request Tests ------------------------


def test_notification_assign_request_valid() -> None:
    req = NotificationAssignRequest(user_ids=[42, 101])
    assert req.user_ids == [42, 101]


def test_notification_assign_request_invalid() -> None:
    # Must have at least 1 user ID
    with pytest.raises(ValidationError):
        NotificationAssignRequest(user_ids=[])


def test_recipient_search_query_valid() -> None:
    query = NotificationRecipientSearchQuery(delivered=True, read=False)
    assert query.delivered is True
    assert query.read is False


# --- 4. User Notification Center Query Tests -------------------------------


def test_my_notification_search_query_valid() -> None:
    query = MyNotificationSearchQuery(status="unread", archived=True)
    assert query.status == "unread"
    assert query.archived is True


def test_my_notification_search_query_invalid_status() -> None:
    with pytest.raises(ValidationError, match="status must be 'unread' or 'read'"):
        MyNotificationSearchQuery(status="invalid_status")


# --- 5. Bulk Action Request Tests ------------------------------------------


def test_bulk_action_request_valid_ids() -> None:
    req = NotificationBulkActionRequest(notification_ids=[1, 2, 3])
    assert req.notification_ids == [1, 2, 3]
    assert req.all_unread is None


def test_bulk_action_request_valid_all_unread() -> None:
    req = NotificationBulkActionRequest(all_unread=True)
    assert req.all_unread is True
    assert req.notification_ids is None


def test_bulk_action_request_invalid_empty() -> None:
    # Neither notification_ids nor all_unread is provided
    with pytest.raises(
        ValidationError,
        match="Either notification_ids or all_unread must be provided",
    ):
        NotificationBulkActionRequest()


# --- 6. Notification Timeline Event Tests ----------------------------------


def test_timeline_event_schema_valid() -> None:
    now = datetime.datetime.now(timezone.utc)  # noqa: UP017
    req = NotificationTimelineEventSchema(event="read", at=now)
    assert req.event == "read"
    assert req.at == now


def test_timeline_event_schema_invalid_event() -> None:
    now = datetime.datetime.now(timezone.utc)  # noqa: UP017
    with pytest.raises(ValidationError, match="event must be one of"):
        NotificationTimelineEventSchema(event="clicked", at=now)
