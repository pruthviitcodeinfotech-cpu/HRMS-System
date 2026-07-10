"""Unit tests for the Notification Management Repository layer."""

from __future__ import annotations

import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.sql import Select, Update

from app.core.constants.enums import SortOrder
from app.modules.notifications.models import Notification, NotificationRecipient
from app.modules.notifications.repository import (
    NotificationRecipientRepository,
    NotificationRepository,
)

# --- 1. Notification Repository Tests ---------------------------------------


@pytest.mark.asyncio
async def test_notification_get_by_id_in_org() -> None:
    session = AsyncMock()
    mock_result = MagicMock()
    notification_obj = Notification(
        id=1,
        org_id=10,
        title="Test Title",
        message="Test Msg",
        notification_type="alert",
        priority="high",
    )
    mock_result.scalar_one_or_none.return_value = notification_obj
    session.execute.return_value = mock_result

    repo = NotificationRepository(session)
    res = await repo.get_by_id_in_org(10, 1)

    assert res == notification_obj
    session.execute.assert_called_once()
    stmt = session.execute.call_args[0][0]
    assert isinstance(stmt, Select)


@pytest.mark.asyncio
async def test_notification_get_details_by_id() -> None:
    session = AsyncMock()
    mock_result = MagicMock()
    notification_obj = Notification(id=1, org_id=10)
    # The detail query returns: (Notification, recipient_count, read_count, delivered_count)
    mock_result.first.return_value = (notification_obj, 10, 4, 8)
    session.execute.return_value = mock_result

    repo = NotificationRepository(session)
    res = await repo.get_details_by_id(10, 1)

    assert res is not None
    assert res[0] == notification_obj
    assert res[1] == 10  # recipient_count
    assert res[2] == 4  # read_count
    assert res[3] == 8  # delivered_count


@pytest.mark.asyncio
async def test_notification_get_details_by_id_not_found() -> None:
    session = AsyncMock()
    mock_result = MagicMock()
    mock_result.first.return_value = None
    session.execute.return_value = mock_result

    repo = NotificationRepository(session)
    res = await repo.get_details_by_id(10, 1)
    assert res is None


@pytest.mark.asyncio
async def test_notification_exists_in_org() -> None:
    session = AsyncMock()
    mock_result = MagicMock()
    mock_result.first.return_value = (1,)
    session.execute.return_value = mock_result

    repo = NotificationRepository(session)
    res = await repo.exists_in_org(10, 1)

    assert res is True
    session.execute.assert_called_once()


@pytest.mark.asyncio
async def test_notification_search_and_count() -> None:
    session = AsyncMock()
    mock_result_search = MagicMock()
    mock_result_search.scalars.return_value.all.return_value = ["notif1", "notif2"]
    mock_result_count = MagicMock()
    mock_result_count.scalar_one.return_value = 2
    session.execute.side_effect = [mock_result_search, mock_result_count]

    from datetime import timezone

    date_val = datetime.datetime.now(timezone.utc)  # noqa: UP017

    repo = NotificationRepository(session)
    results = await repo.search(
        org_id=10,
        notification_type="alert",
        priority="low",
        source_module="leave",
        source_entity_type="Request",
        source_entity_id=101,
        date_from=date_val,
        date_to=date_val,
        search="test",
        sort_by="priority",
        sort_order=SortOrder.DESC,
        page=1,
        page_size=10,
    )

    count = await repo.search_count(
        org_id=10,
        notification_type="alert",
        priority="low",
        source_module="leave",
        source_entity_type="Request",
        source_entity_id=101,
        date_from=date_val,
        date_to=date_val,
        search="test",
    )

    assert results == ["notif1", "notif2"]
    assert count == 2
    assert session.execute.call_count == 2


# --- 2. Notification Recipient Repository Tests -----------------------------


@pytest.mark.asyncio
async def test_recipient_get_by_notification_and_user() -> None:
    session = AsyncMock()
    mock_result = MagicMock()
    rec_obj = NotificationRecipient(id=5, org_id=10, notification_id=1, user_id=42)
    mock_result.scalar_one_or_none.return_value = rec_obj
    session.execute.return_value = mock_result

    repo = NotificationRecipientRepository(session)
    res = await repo.get_by_notification_and_user(10, 1, 42)

    assert res == rec_obj


@pytest.mark.asyncio
async def test_recipient_exists_in_org() -> None:
    session = AsyncMock()
    mock_result = MagicMock()
    mock_result.first.return_value = (5,)
    session.execute.return_value = mock_result

    repo = NotificationRecipientRepository(session)
    res = await repo.exists_in_org(10, 5)

    assert res is True


@pytest.mark.asyncio
async def test_recipient_get_assigned_user_ids() -> None:
    session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [42, 101]
    session.execute.return_value = mock_result

    repo = NotificationRecipientRepository(session)
    res = await repo.get_assigned_user_ids(1)

    assert res == {42, 101}


@pytest.mark.asyncio
async def test_recipient_search() -> None:
    session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = ["rec1", "rec2"]
    session.execute.return_value = mock_result

    repo = NotificationRecipientRepository(session)
    results = await repo.search(
        notification_id=1,
        org_id=10,
        delivered=True,
        read=False,
        page=1,
        page_size=20,
    )

    assert results == ["rec1", "rec2"]


@pytest.mark.asyncio
async def test_recipient_search_delivered_false_read_true() -> None:
    session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    session.execute.return_value = mock_result

    repo = NotificationRecipientRepository(session)
    results = await repo.search(
        notification_id=1,
        org_id=10,
        delivered=False,
        read=True,
        page=1,
        page_size=20,
    )
    assert results == []


@pytest.mark.asyncio
async def test_recipient_get_user_notifications_and_count() -> None:
    session = AsyncMock()
    mock_search = MagicMock()
    mock_search.scalars.return_value.all.return_value = ["rec1"]
    mock_count = MagicMock()
    mock_count.scalar_one.return_value = 1
    session.execute.side_effect = [mock_search, mock_count]

    repo = NotificationRecipientRepository(session)
    results = await repo.get_user_notifications(
        org_id=10,
        user_id=42,
        status="unread",
        archived=True,
        notification_type="system",
        priority="high",
        source_module="payroll",
        include_expired=False,
        page=1,
        page_size=10,
    )

    count = await repo.get_user_notifications_count(
        org_id=10,
        user_id=42,
        status="unread",
        archived=True,
        notification_type="system",
        priority="high",
        source_module="payroll",
        include_expired=False,
    )

    assert results == ["rec1"]
    assert count == 1


@pytest.mark.asyncio
async def test_recipient_get_user_notifications_read_not_archived() -> None:
    session = AsyncMock()
    mock_search = MagicMock()
    mock_search.scalars.return_value.all.return_value = []
    mock_count = MagicMock()
    mock_count.scalar_one.return_value = 0
    session.execute.side_effect = [mock_search, mock_count]

    repo = NotificationRecipientRepository(session)
    results = await repo.get_user_notifications(
        org_id=10,
        user_id=42,
        status="read",
        archived=False,
        page=1,
        page_size=10,
    )
    count = await repo.get_user_notifications_count(
        org_id=10,
        user_id=42,
        status="read",
        archived=False,
    )
    assert results == []
    assert count == 0


@pytest.mark.asyncio
async def test_recipient_get_user_notification_counts() -> None:
    session = AsyncMock()
    mock_result = MagicMock()
    # (total_count, unread_count, archived_count)
    mock_result.first.return_value = (15, 3, 2)
    session.execute.return_value = mock_result

    repo = NotificationRecipientRepository(session)
    counts = await repo.get_user_notification_counts(10, 42)

    assert counts["total_count"] == 15
    assert counts["unread_count"] == 3
    assert counts["archived_count"] == 2


@pytest.mark.asyncio
async def test_recipient_get_user_notification_counts_empty() -> None:
    session = AsyncMock()
    mock_result = MagicMock()
    mock_result.first.return_value = None
    session.execute.return_value = mock_result

    repo = NotificationRecipientRepository(session)
    counts = await repo.get_user_notification_counts(10, 42)

    assert counts["total_count"] == 0
    assert counts["unread_count"] == 0
    assert counts["archived_count"] == 0


@pytest.mark.asyncio
async def test_recipient_bulk_mark_read() -> None:
    session = AsyncMock()
    mock_result = MagicMock()
    mock_result.rowcount = 5
    session.execute.return_value = mock_result

    repo = NotificationRecipientRepository(session)
    affected = await repo.bulk_mark_read(
        org_id=10,
        user_id=42,
        notification_ids=[1, 2, 3],
        all_unread=False,
    )

    assert affected == 5
    session.execute.assert_called_once()
    stmt = session.execute.call_args[0][0]
    assert isinstance(stmt, Update)


@pytest.mark.asyncio
async def test_recipient_bulk_archive() -> None:
    session = AsyncMock()
    mock_result = MagicMock()
    mock_result.rowcount = 3
    session.execute.return_value = mock_result

    repo = NotificationRecipientRepository(session)
    affected = await repo.bulk_archive(
        org_id=10,
        user_id=42,
        notification_ids=[1, 2],
    )

    assert affected == 3
    session.execute.assert_called_once()


@pytest.mark.asyncio
async def test_recipient_bulk_delete() -> None:
    session = AsyncMock()
    mock_result = MagicMock()
    mock_result.rowcount = 2
    session.execute.return_value = mock_result

    repo = NotificationRecipientRepository(session)
    affected = await repo.bulk_delete(
        org_id=10,
        user_id=42,
        notification_ids=[1],
    )

    assert affected == 2
    session.execute.assert_called_once()
