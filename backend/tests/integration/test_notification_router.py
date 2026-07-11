"""Integration tests for the Notification Management router."""

from __future__ import annotations

import datetime
from datetime import timezone
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.core.dependencies.auth import assert_session_live
from app.modules.notifications.dependencies import get_notification_service
from app.modules.notifications.schemas import (
    MyNotificationListResponse,
    MyNotificationSchema,
    NotificationDetailsSchema,
    NotificationListResponse,
    NotificationRecipientListResponse,
    NotificationRecipientSchema,
    NotificationSchema,
)
from tests.conftest import API_PREFIX

_NOW = datetime.datetime(2026, 7, 10, 10, 0, 0, tzinfo=timezone.utc)  # noqa: UP017


@pytest.fixture
def mock_notification_service() -> AsyncMock:
    """Mock stand-in for NotificationService."""
    return AsyncMock()


@pytest_asyncio.fixture
async def notification_client(app, mock_notification_service: AsyncMock):
    """An async HTTP client bound to the app with the notification service mocked."""
    # The auth dependency re-validates the session against the DB on every request;
    # router tests exercise the HTTP layer without a database, so stub that check.
    app.dependency_overrides[assert_session_live] = lambda: None
    app.dependency_overrides[get_notification_service] = lambda: mock_notification_service
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as http_client:
        yield http_client
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Helpers / Response Builders
# ---------------------------------------------------------------------------


def _notif_schema() -> NotificationSchema:
    return NotificationSchema(
        id=1,
        org_id=1,
        title="Test Notification",
        message="A test message.",
        notification_type="alert",
        priority="high",
        created_at=_NOW,
    )


def _notif_details_schema() -> NotificationDetailsSchema:
    return NotificationDetailsSchema(
        id=1,
        org_id=1,
        title="Test Notification",
        message="A test message.",
        notification_type="alert",
        priority="high",
        created_at=_NOW,
        recipient_count=10,
        read_count=4,
        delivered_count=8,
    )


def _recipient_schema() -> NotificationRecipientSchema:
    return NotificationRecipientSchema(
        id=5,
        notification_id=1,
        org_id=1,
        user_id=42,
        created_at=_NOW,
    )


def _my_notif_schema() -> MyNotificationSchema:
    return MyNotificationSchema(
        id=1,
        org_id=1,
        title="Test Notification",
        message="A test message.",
        notification_type="alert",
        priority="high",
        created_at=_NOW,
        delivered_at=_NOW,
    )


# ---------------------------------------------------------------------------
# 1. Admin Management — Notifications (Feature permissions required)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_notification_201(
    notification_client: AsyncClient,
    mock_notification_service: AsyncMock,
    super_admin_headers: dict[str, str],
) -> None:
    mock_notification_service.create_notification.return_value = _notif_schema()
    payload = {
        "title": "Test Notification",
        "message": "A test message.",
        "notification_type": "alert",
        "priority": "high",
        "recipient_user_ids": [42],
    }
    resp = await notification_client.post(
        f"{API_PREFIX}/notifications", json=payload, headers=super_admin_headers
    )
    assert resp.status_code == 201
    assert resp.json()["data"]["title"] == "Test Notification"


@pytest.mark.asyncio
async def test_list_notifications_200(
    notification_client: AsyncClient,
    mock_notification_service: AsyncMock,
    super_admin_headers: dict[str, str],
) -> None:
    mock_notification_service.list_notifications.return_value = NotificationListResponse.build(
        items=[_notif_schema()],
        page=1,
        page_size=25,
        total_records=1,
    )
    resp = await notification_client.get(
        f"{API_PREFIX}/notifications?page=1&page_size=25", headers=super_admin_headers
    )
    assert resp.status_code == 200
    assert len(resp.json()["data"]["items"]) == 1


@pytest.mark.asyncio
async def test_get_notification_details_200(
    notification_client: AsyncClient,
    mock_notification_service: AsyncMock,
    super_admin_headers: dict[str, str],
) -> None:
    mock_notification_service.get_notification_details.return_value = (
        _notif_details_schema().model_dump()
    )
    resp = await notification_client.get(
        f"{API_PREFIX}/notifications/1", headers=super_admin_headers
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["recipient_count"] == 10


# ---------------------------------------------------------------------------
# 2. Admin Management — Recipients
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_assign_recipients_200(
    notification_client: AsyncClient,
    mock_notification_service: AsyncMock,
    super_admin_headers: dict[str, str],
) -> None:
    mock_notification_service.assign_recipients.return_value = [
        {"user_id": 42, "assigned": True, "status": "created", "message": "Success"}
    ]
    payload = {"user_ids": [42]}
    resp = await notification_client.post(
        f"{API_PREFIX}/notifications/1/recipients", json=payload, headers=super_admin_headers
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["results"][0]["user_id"] == 42


@pytest.mark.asyncio
async def test_list_recipients_200(
    notification_client: AsyncClient,
    mock_notification_service: AsyncMock,
    super_admin_headers: dict[str, str],
) -> None:
    mock_notification_service.list_recipients.return_value = (
        NotificationRecipientListResponse.build(
            items=[_recipient_schema()],
            page=1,
            page_size=25,
            total_records=1,
        )
    )
    resp = await notification_client.get(
        f"{API_PREFIX}/notifications/1/recipients?page=1&page_size=25",
        headers=super_admin_headers,
    )
    assert resp.status_code == 200
    assert len(resp.json()["data"]["items"]) == 1


# ---------------------------------------------------------------------------
# 3. User Notification Center (Self-Service)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_my_notifications_200(
    notification_client: AsyncClient,
    mock_notification_service: AsyncMock,
    auth_headers: dict[str, str],
) -> None:
    mock_notification_service.get_user_notifications.return_value = (
        MyNotificationListResponse.build(
            items=[_my_notif_schema()],
            page=1,
            page_size=25,
            total_records=1,
        )
    )
    resp = await notification_client.get(
        f"{API_PREFIX}/me/notifications?page=1&page_size=25", headers=auth_headers
    )
    assert resp.status_code == 200
    assert len(resp.json()["data"]["items"]) == 1


@pytest.mark.asyncio
async def test_get_my_notification_counts_200(
    notification_client: AsyncClient,
    mock_notification_service: AsyncMock,
    auth_headers: dict[str, str],
) -> None:
    mock_notification_service.get_user_notification_counts.return_value = {
        "unread_count": 5,
        "archived_count": 2,
        "total_count": 7,
    }
    resp = await notification_client.get(
        f"{API_PREFIX}/me/notifications/count", headers=auth_headers
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["unread_count"] == 5


@pytest.mark.asyncio
async def test_get_my_notification_200(
    notification_client: AsyncClient,
    mock_notification_service: AsyncMock,
    auth_headers: dict[str, str],
) -> None:
    mock_notification_service.get_user_notification.return_value = _my_notif_schema().model_dump()
    resp = await notification_client.get(f"{API_PREFIX}/me/notifications/1", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["data"]["title"] == "Test Notification"


# ---------------------------------------------------------------------------
# 4. User Notification Center Toggles (Self-Service Actions)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_mark_read_200(
    notification_client: AsyncClient,
    mock_notification_service: AsyncMock,
    auth_headers: dict[str, str],
) -> None:
    mock_notification_service.mark_read.return_value = None
    resp = await notification_client.post(
        f"{API_PREFIX}/me/notifications/1/read", headers=auth_headers
    )
    assert resp.status_code == 200
    mock_notification_service.mark_read.assert_called_once_with(1, 1, 1)


@pytest.mark.asyncio
async def test_mark_unread_200(
    notification_client: AsyncClient,
    mock_notification_service: AsyncMock,
    auth_headers: dict[str, str],
) -> None:
    mock_notification_service.mark_unread.return_value = None
    resp = await notification_client.post(
        f"{API_PREFIX}/me/notifications/1/unread", headers=auth_headers
    )
    assert resp.status_code == 200
    mock_notification_service.mark_unread.assert_called_once_with(1, 1, 1)


@pytest.mark.asyncio
async def test_archive_notification_200(
    notification_client: AsyncClient,
    mock_notification_service: AsyncMock,
    auth_headers: dict[str, str],
) -> None:
    mock_notification_service.archive_notification.return_value = None
    resp = await notification_client.post(
        f"{API_PREFIX}/me/notifications/1/archive", headers=auth_headers
    )
    assert resp.status_code == 200
    mock_notification_service.archive_notification.assert_called_once_with(1, 1, 1)


@pytest.mark.asyncio
async def test_unarchive_notification_200(
    notification_client: AsyncClient,
    mock_notification_service: AsyncMock,
    auth_headers: dict[str, str],
) -> None:
    mock_notification_service.unarchive_notification.return_value = None
    resp = await notification_client.post(
        f"{API_PREFIX}/me/notifications/1/unarchive", headers=auth_headers
    )
    assert resp.status_code == 200
    mock_notification_service.unarchive_notification.assert_called_once_with(1, 1, 1)


@pytest.mark.asyncio
async def test_delete_notification_204(
    notification_client: AsyncClient,
    mock_notification_service: AsyncMock,
    auth_headers: dict[str, str],
) -> None:
    mock_notification_service.delete_notification.return_value = None
    resp = await notification_client.delete(
        f"{API_PREFIX}/me/notifications/1", headers=auth_headers
    )
    assert resp.status_code == 204
    mock_notification_service.delete_notification.assert_called_once_with(1, 1, 1)


# ---------------------------------------------------------------------------
# 5. Bulk Operations (Self-Service)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_bulk_mark_read_200(
    notification_client: AsyncClient,
    mock_notification_service: AsyncMock,
    auth_headers: dict[str, str],
) -> None:
    mock_notification_service.bulk_mark_read.return_value = 5
    payload = {"notification_ids": [1, 2, 3], "all_unread": False}
    resp = await notification_client.post(
        f"{API_PREFIX}/me/notifications/bulk-read", json=payload, headers=auth_headers
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["affected_count"] == 5


@pytest.mark.asyncio
async def test_bulk_archive_200(
    notification_client: AsyncClient,
    mock_notification_service: AsyncMock,
    auth_headers: dict[str, str],
) -> None:
    mock_notification_service.bulk_archive.return_value = 3
    payload = {"notification_ids": [1, 2, 3]}
    resp = await notification_client.post(
        f"{API_PREFIX}/me/notifications/bulk-archive", json=payload, headers=auth_headers
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["affected_count"] == 3


@pytest.mark.asyncio
async def test_bulk_delete_200(
    notification_client: AsyncClient,
    mock_notification_service: AsyncMock,
    auth_headers: dict[str, str],
) -> None:
    mock_notification_service.bulk_delete.return_value = 2
    payload = {"notification_ids": [1, 2, 3]}
    resp = await notification_client.post(
        f"{API_PREFIX}/me/notifications/bulk-delete", json=payload, headers=auth_headers
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["affected_count"] == 2


# ---------------------------------------------------------------------------
# 6. Recipient Timeline / History
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_notification_timeline_200(
    notification_client: AsyncClient,
    mock_notification_service: AsyncMock,
    auth_headers: dict[str, str],
) -> None:
    mock_notification_service.get_notification_timeline.return_value = [
        {"event": "created", "at": _NOW}
    ]
    resp = await notification_client.get(
        f"{API_PREFIX}/me/notifications/1/timeline", headers=auth_headers
    )
    assert resp.status_code == 200
    assert resp.json()["data"][0]["event"] == "created"


@pytest.mark.asyncio
async def test_unresolved_tenant_error(
    notification_client: AsyncClient,
    make_access_token,
) -> None:
    # A user with org_id=None (no tenant context)
    token = make_access_token(org_id=None)
    headers = {"Authorization": f"Bearer {token}"}
    resp = await notification_client.get(f"{API_PREFIX}/me/notifications", headers=headers)
    assert resp.status_code == 400
    assert "Organization context is required." in resp.json()["message"]


@pytest.mark.asyncio
async def test_bulk_archive_empty_list_error(
    notification_client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    payload = {"notification_ids": []}
    resp = await notification_client.post(
        f"{API_PREFIX}/me/notifications/bulk-archive", json=payload, headers=auth_headers
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_bulk_delete_empty_list_error(
    notification_client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    payload = {"notification_ids": []}
    resp = await notification_client.post(
        f"{API_PREFIX}/me/notifications/bulk-delete", json=payload, headers=auth_headers
    )
    assert resp.status_code == 422
