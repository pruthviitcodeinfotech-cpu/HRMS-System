"""Unit tests for the Notification Management Service layer."""

from __future__ import annotations

import datetime
from datetime import timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.modules.notifications.exceptions import (
    NotificationNotFoundException,
    NotificationValidationException,
    RecipientNotFoundException,
    UserNotFoundException,
)
from app.modules.notifications.models import Notification, NotificationRecipient
from app.modules.notifications.service import NotificationService
from app.modules.rbac.models import User


@pytest.mark.asyncio
async def test_create_notification_success() -> None:
    session = AsyncMock()
    service = NotificationService(session)

    # Mock user repository search/get
    service.users.get_active_by_id = AsyncMock(return_value=User(id=42, org_id=10))

    # Mock notification creation
    created_notif = Notification(
        id=1,
        org_id=10,
        title="Test Notification",
        message="A test message",
        notification_type="system",
        priority="high",
        created_at=datetime.datetime.now(timezone.utc),  # noqa: UP017
    )
    service.notifications.create = AsyncMock(return_value=created_notif)
    service.recipients.create = AsyncMock()
    service.audit.record = AsyncMock()

    res = await service.create_notification(
        org_id=10,
        caller_user_id=101,
        title="Test Notification",
        message="A test message",
        notification_type="system",
        priority="high",
        recipient_user_ids=[42],
    )

    assert res == created_notif
    service.notifications.create.assert_called_once()
    service.recipients.create.assert_called_once()
    service.audit.record.assert_called_once()


@pytest.mark.asyncio
async def test_create_notification_validation_failures() -> None:
    session = AsyncMock()
    service = NotificationService(session)

    # Empty fields
    with pytest.raises(NotificationValidationException):
        await service.create_notification(10, 101, "", "msg", "type", "priority")

    with pytest.raises(NotificationValidationException):
        await service.create_notification(10, 101, "title", "", "type", "priority")

    with pytest.raises(NotificationValidationException):
        await service.create_notification(10, 101, "title", "msg", "", "priority")

    with pytest.raises(NotificationValidationException):
        await service.create_notification(10, 101, "title", "msg", "type", "")

    # Expired in past
    past_time = datetime.datetime.now(timezone.utc) - datetime.timedelta(days=1)  # noqa: UP017
    with pytest.raises(NotificationValidationException):
        await service.create_notification(
            10, 101, "title", "msg", "type", "priority", expires_at=past_time
        )


@pytest.mark.asyncio
async def test_create_notification_user_not_found() -> None:
    session = AsyncMock()
    service = NotificationService(session)

    # User does not exist/inactive
    service.users.get_active_by_id = AsyncMock(return_value=None)

    with pytest.raises(UserNotFoundException):
        await service.create_notification(
            10, 101, "title", "msg", "type", "priority", recipient_user_ids=[999]
        )


@pytest.mark.asyncio
async def test_list_notifications() -> None:
    session = AsyncMock()
    service = NotificationService(session)

    service.notifications.search = AsyncMock(return_value=["n1", "n2"])
    service.notifications.search_count = AsyncMock(return_value=2)

    res = await service.list_notifications(10, page=1, page_size=10)

    assert res.items == ["n1", "n2"]
    assert res.pagination.total_records == 2


@pytest.mark.asyncio
async def test_get_notification_details_success() -> None:
    session = AsyncMock()
    service = NotificationService(session)

    notif = Notification(
        id=1,
        org_id=10,
        title="Title",
        message="Message",
        notification_type="alert",
        priority="low",
        created_at=datetime.datetime.now(timezone.utc),  # noqa: UP017
    )
    service.notifications.get_details_by_id = AsyncMock(return_value=(notif, 10, 4, 8))

    details = await service.get_notification_details(10, 1)

    assert details["id"] == 1
    assert details["recipient_count"] == 10
    assert details["read_count"] == 4
    assert details["delivered_count"] == 8


@pytest.mark.asyncio
async def test_get_notification_details_not_found() -> None:
    session = AsyncMock()
    service = NotificationService(session)
    service.notifications.get_details_by_id = AsyncMock(return_value=None)

    with pytest.raises(NotificationNotFoundException):
        await service.get_notification_details(10, 1)


@pytest.mark.asyncio
async def test_assign_recipients_success() -> None:
    session = AsyncMock()
    service = NotificationService(session)

    service.notifications.exists_in_org = AsyncMock(return_value=True)
    service.recipients.get_assigned_user_ids = AsyncMock(return_value={42})
    service.users.get_active_by_id = AsyncMock(
        side_effect=lambda uid, org: User(id=uid, org_id=org) if uid in (42, 101) else None
    )
    service.recipients.create = AsyncMock()
    service.audit.record = AsyncMock()

    results = await service.assign_recipients(
        org_id=10,
        notification_id=1,
        user_ids=[42, 101, 999],
        caller_user_id=5,
    )

    assert len(results) == 3
    assert results[0]["user_id"] == 42
    assert results[0]["assigned"] is False
    assert results[0]["status"] == "already_assigned"

    assert results[1]["user_id"] == 101
    assert results[1]["assigned"] is True
    assert results[1]["status"] == "created"

    assert results[2]["user_id"] == 999
    assert results[2]["assigned"] is False
    assert results[2]["status"] == "user_not_found"

    service.recipients.create.assert_called_once()
    service.audit.record.assert_called_once()


@pytest.mark.asyncio
async def test_list_recipients() -> None:
    session = AsyncMock()
    service = NotificationService(session)

    service.notifications.exists_in_org = AsyncMock(return_value=True)
    service.recipients.search = AsyncMock(return_value=["r1"])
    count_result = MagicMock()
    count_result.scalar_one.return_value = 1
    session.execute.return_value = count_result

    res = await service.list_recipients(10, 1)
    assert res.items == ["r1"]
    assert res.pagination.total_records == 1


@pytest.mark.asyncio
async def test_get_user_notifications() -> None:
    session = AsyncMock()
    service = NotificationService(session)

    notif = Notification(
        id=1,
        org_id=10,
        title="Title",
        message="Msg",
        notification_type="type",
        priority="high",
        created_at=datetime.datetime.now(timezone.utc),  # noqa: UP017
    )
    rec = NotificationRecipient(
        id=5,
        notification_id=1,
        org_id=10,
        user_id=42,
        delivered_at=datetime.datetime.now(timezone.utc),  # noqa: UP017
    )
    rec.notification = notif

    service.recipients.get_user_notifications = AsyncMock(return_value=[rec])
    service.recipients.get_user_notifications_count = AsyncMock(return_value=1)

    res = await service.get_user_notifications(10, 42)
    assert len(res.items) == 1
    assert res.items[0]["title"] == "Title"
    assert res.items[0]["delivered_at"] == rec.delivered_at


@pytest.mark.asyncio
async def test_get_user_notification_success() -> None:
    session = AsyncMock()
    service = NotificationService(session)

    notif = Notification(
        id=1,
        org_id=10,
        title="Title",
        message="Msg",
        notification_type="type",
        priority="high",
        created_at=datetime.datetime.now(timezone.utc),  # noqa: UP017
    )
    rec = NotificationRecipient(
        id=5,
        notification_id=1,
        org_id=10,
        user_id=42,
        delivered_at=None,
    )
    rec.notification = notif

    service.recipients.get_by_notification_and_user = AsyncMock(return_value=rec)
    service.recipients.update = AsyncMock(
        side_effect=lambda obj, vals: setattr(obj, "delivered_at", vals["delivered_at"]) or obj
    )

    res = await service.get_user_notification(10, 1, 42)

    assert res["delivered_at"] is not None
    service.recipients.update.assert_called_once()


@pytest.mark.asyncio
async def test_user_actions_mark_read_and_unread() -> None:
    session = AsyncMock()
    service = NotificationService(session)

    rec = NotificationRecipient(id=5, org_id=10, notification_id=1, user_id=42, read_at=None)
    service.recipients.get_by_notification_and_user = AsyncMock(return_value=rec)
    service.recipients.update = AsyncMock()

    # Mark Read
    await service.mark_read(10, 1, 42)
    service.recipients.update.assert_called_once()

    # Reset and Mark Unread
    rec.read_at = datetime.datetime.now(timezone.utc)  # noqa: UP017
    service.recipients.update.reset_mock()
    await service.mark_unread(10, 1, 42)
    service.recipients.update.assert_called_once()
    assert service.recipients.update.call_args[0][1]["read_at"] is None


@pytest.mark.asyncio
async def test_user_actions_archive_and_unarchive() -> None:
    session = AsyncMock()
    service = NotificationService(session)

    rec = NotificationRecipient(id=5, org_id=10, notification_id=1, user_id=42, archived_at=None)
    service.recipients.get_by_notification_and_user = AsyncMock(return_value=rec)
    service.recipients.update = AsyncMock()

    # Archive
    await service.archive_notification(10, 1, 42)
    service.recipients.update.assert_called_once()

    # Unarchive
    rec.archived_at = datetime.datetime.now(timezone.utc)  # noqa: UP017
    service.recipients.update.reset_mock()
    await service.unarchive_notification(10, 1, 42)
    service.recipients.update.assert_called_once()
    assert service.recipients.update.call_args[0][1]["archived_at"] is None


@pytest.mark.asyncio
async def test_user_actions_delete() -> None:
    session = AsyncMock()
    service = NotificationService(session)

    rec = NotificationRecipient(id=5, org_id=10, notification_id=1, user_id=42, deleted_at=None)
    service.recipients.get_by_notification_and_user = AsyncMock(return_value=rec)
    service.recipients.update = AsyncMock()

    await service.delete_notification(10, 1, 42)
    service.recipients.update.assert_called_once()
    assert service.recipients.update.call_args[0][1]["deleted_at"] is not None


@pytest.mark.asyncio
async def test_bulk_operations() -> None:
    session = AsyncMock()
    service = NotificationService(session)

    service.recipients.bulk_mark_read = AsyncMock(return_value=5)
    service.recipients.bulk_archive = AsyncMock(return_value=3)
    service.recipients.bulk_delete = AsyncMock(return_value=2)

    assert await service.bulk_mark_read(10, 42, [1, 2], False) == 5
    assert await service.bulk_archive(10, 42, [1, 2]) == 3
    assert await service.bulk_delete(10, 42, [1, 2]) == 2


@pytest.mark.asyncio
async def test_get_notification_timeline() -> None:
    session = AsyncMock()
    service = NotificationService(session)

    created_at = datetime.datetime(2026, 7, 10, 10, 0, 0, tzinfo=timezone.utc)  # noqa: UP017
    read_at = datetime.datetime(2026, 7, 10, 10, 15, 0, tzinfo=timezone.utc)  # noqa: UP017

    rec = NotificationRecipient(
        id=5,
        org_id=10,
        notification_id=1,
        user_id=42,
        created_at=created_at,
        delivered_at=created_at,
        read_at=read_at,
        archived_at=None,
        deleted_at=None,
    )
    service.recipients.get_by_notification_and_user = AsyncMock(return_value=rec)

    timeline = await service.get_notification_timeline(10, 1, 42)

    assert len(timeline) == 3
    assert timeline[0]["event"] == "created"
    assert timeline[1]["event"] == "delivered"
    assert timeline[2]["event"] == "read"


@pytest.mark.asyncio
async def test_user_actions_not_found() -> None:
    session = AsyncMock()
    service = NotificationService(session)
    service.recipients.get_by_notification_and_user = AsyncMock(return_value=None)

    with pytest.raises(RecipientNotFoundException):
        await service.mark_read(10, 1, 42)

    with pytest.raises(RecipientNotFoundException):
        await service.mark_unread(10, 1, 42)

    with pytest.raises(RecipientNotFoundException):
        await service.archive_notification(10, 1, 42)

    with pytest.raises(RecipientNotFoundException):
        await service.unarchive_notification(10, 1, 42)

    with pytest.raises(RecipientNotFoundException):
        await service.delete_notification(10, 1, 42)

    with pytest.raises(RecipientNotFoundException):
        await service.get_notification_timeline(10, 1, 42)


@pytest.mark.asyncio
async def test_get_notification_service() -> None:
    from app.modules.notifications.dependencies import get_notification_service

    db_mock = AsyncMock()
    service = await get_notification_service(db_mock)
    assert service.session == db_mock


@pytest.mark.asyncio
async def test_create_notification_naive_expiry() -> None:
    session = AsyncMock()
    service = NotificationService(session)
    service.users.get_active_by_id = AsyncMock(return_value=User(id=42, org_id=10))

    created_notif = Notification(
        id=1,
        org_id=10,
        title="Test Notification",
        message="A test message",
        notification_type="system",
        priority="high",
        created_at=datetime.datetime.now(timezone.utc),  # noqa: UP017
    )
    service.notifications.create = AsyncMock(return_value=created_notif)
    service.recipients.create = AsyncMock()
    service.audit.record = AsyncMock()

    naive_expiry = datetime.datetime.now() + datetime.timedelta(days=1)
    res = await service.create_notification(
        org_id=10,
        caller_user_id=1,
        title="Test Notification",
        message="A test message",
        notification_type="system",
        priority="high",
        expires_at=naive_expiry,
    )
    assert res == created_notif


@pytest.mark.asyncio
async def test_assign_recipients_notification_not_found() -> None:
    session = AsyncMock()
    service = NotificationService(session)
    service.notifications.exists_in_org = AsyncMock(return_value=False)

    with pytest.raises(NotificationNotFoundException):
        await service.assign_recipients(10, 1, [42], 1)


@pytest.mark.asyncio
async def test_list_recipients_notification_not_found() -> None:
    session = AsyncMock()
    service = NotificationService(session)
    service.notifications.exists_in_org = AsyncMock(return_value=False)

    with pytest.raises(NotificationNotFoundException):
        await service.list_recipients(10, 1)


@pytest.mark.asyncio
async def test_get_user_notification_not_found() -> None:
    session = AsyncMock()
    service = NotificationService(session)
    service.recipients.get_by_notification_and_user = AsyncMock(return_value=None)

    with pytest.raises(RecipientNotFoundException):
        await service.get_user_notification(10, 1, 42)


@pytest.mark.asyncio
async def test_bulk_mark_read_validation_error() -> None:
    session = AsyncMock()
    service = NotificationService(session)

    with pytest.raises(NotificationValidationException):
        await service.bulk_mark_read(10, 42, notification_ids=None, all_unread=False)


@pytest.mark.asyncio
async def test_bulk_archive_empty_list() -> None:
    session = AsyncMock()
    service = NotificationService(session)

    with pytest.raises(NotificationValidationException):
        await service.bulk_archive(10, 42, [])


@pytest.mark.asyncio
async def test_bulk_delete_empty_list() -> None:
    session = AsyncMock()
    service = NotificationService(session)

    with pytest.raises(NotificationValidationException):
        await service.bulk_delete(10, 42, [])


@pytest.mark.asyncio
async def test_get_notification_timeline_with_archived_and_deleted() -> None:
    session = AsyncMock()
    service = NotificationService(session)

    now = datetime.datetime.now(timezone.utc)  # noqa: UP017
    rec = NotificationRecipient(
        id=5,
        org_id=10,
        notification_id=1,
        user_id=42,
        created_at=now,
        delivered_at=now,
        read_at=now,
        archived_at=now,
        deleted_at=now,
    )
    service.recipients.get_by_notification_and_user = AsyncMock(return_value=rec)

    timeline = await service.get_notification_timeline(10, 1, 42)
    assert len(timeline) == 5
    assert timeline[3]["event"] == "archived"
    assert timeline[4]["event"] == "deleted"


# ===========================================================================
# System-generated emission (cross-module orchestration)
# ===========================================================================


@pytest.mark.asyncio
async def test_emit_system_notification_creates_definition_and_recipients() -> None:
    """Emission writes the definition plus one recipient row per (deduped) user,
    without opening its own transaction (the caller owns the boundary)."""
    session = AsyncMock()
    service = NotificationService(session)

    created_notif = Notification(
        id=7,
        org_id=10,
        title="Request Approved",
        message="Your leave request was approved.",
        notification_type="approval",
        priority="normal",
    )
    service.notifications.create = AsyncMock(return_value=created_notif)
    service.recipients.create = AsyncMock()

    res = await service.emit_system_notification(
        10,
        recipient_user_ids=[42, 43, 42],  # duplicate must collapse
        title="Request Approved",
        message="Your leave request was approved.",
        notification_type="approval",
        source_module="approvals",
        source_entity_type="approval_request",
        source_entity_id=1,
        created_by=9,
    )

    assert res == created_notif
    payload = service.notifications.create.await_args.args[0]
    assert payload["notification_type"] == "approval"
    assert payload["source_module"] == "approvals"
    assert payload["created_by"] == 9
    assert service.recipients.create.await_count == 2
    recipient_ids = [
        c.args[0]["user_id"] for c in service.recipients.create.await_args_list
    ]
    assert recipient_ids == [42, 43]
    # Caller owns the transaction: the emission itself never commits.
    session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_emit_system_notification_skips_without_recipients() -> None:
    session = AsyncMock()
    service = NotificationService(session)
    service.notifications.create = AsyncMock()
    service.recipients.create = AsyncMock()

    res = await service.emit_system_notification(
        10,
        recipient_user_ids=[],
        title="T",
        message="M",
        notification_type="approval",
    )

    assert res is None
    service.notifications.create.assert_not_awaited()
    service.recipients.create.assert_not_awaited()


@pytest.mark.asyncio
async def test_resolve_user_ids_for_employees_empty_input_short_circuits() -> None:
    session = AsyncMock()
    service = NotificationService(session)

    assert await service.resolve_user_ids_for_employees(10, []) == []
    session.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_resolve_user_ids_for_employees_returns_scalar_ids() -> None:
    session = AsyncMock()
    result = MagicMock()
    result.scalars.return_value.all.return_value = [42, 43]
    session.execute = AsyncMock(return_value=result)
    service = NotificationService(session)

    res = await service.resolve_user_ids_for_employees(10, [5, 6])
    assert res == [42, 43]
    session.execute.assert_awaited_once()
