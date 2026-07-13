"""Notifications Management — service layer (business logic & orchestration).

Implements the business logic defined in the approved Notification Management API Contract.
All database access is performed strictly via repositories.
"""

from __future__ import annotations

import datetime
from collections.abc import Sequence
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants.enums import SortOrder
from app.modules.audit.constants import ActionType
from app.modules.audit.service import AuditService
from app.modules.notifications.constants import NotificationPriority
from app.modules.notifications.exceptions import (
    NotificationNotFoundException,
    NotificationValidationException,
    RecipientNotFoundException,
    UserNotFoundException,
)
from app.modules.notifications.models import Notification, NotificationRecipient
from app.modules.notifications.repository import (
    NotificationRecipientRepository,
    NotificationRepository,
)
from app.modules.rbac.models import User
from app.modules.rbac.repository import UserRepository
from app.shared.base.service import BaseService
from app.shared.schemas.pagination import PaginatedResponse
from app.shared.utils.datetime import utcnow


class NotificationService(BaseService):
    """Notifications Management business rules engine and service."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)
        self.notifications = NotificationRepository(session)
        self.recipients = NotificationRecipientRepository(session)
        self.users = UserRepository(session)
        self.audit = AuditService(session)

    # =========================================================================
    # 1. Admin Management — Notifications
    # =========================================================================

    async def create_notification(
        self,
        org_id: int,
        caller_user_id: int,
        title: str,
        message: str,
        notification_type: str,
        priority: str,
        source_module: str | None = None,
        source_entity_type: str | None = None,
        source_entity_id: int | None = None,
        expires_at: datetime.datetime | None = None,
        recipient_user_ids: list[int] | None = None,
    ) -> Notification:
        """Create a notification definition and optionally assign to target users."""
        from datetime import timezone

        # 1. Validation
        if not title.strip():
            raise NotificationValidationException("Notification title cannot be empty.")
        if not message.strip():
            raise NotificationValidationException("Notification message cannot be empty.")
        if not notification_type.strip():
            raise NotificationValidationException("Notification type cannot be empty.")
        if not priority.strip():
            raise NotificationValidationException("Notification priority cannot be empty.")

        if expires_at is not None:
            now = datetime.datetime.now(timezone.utc)  # noqa: UP017
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)  # noqa: UP017
            if expires_at <= now:
                raise NotificationValidationException("expires_at must be in the future.")

        # Validate target users if provided
        if recipient_user_ids:
            for uid in recipient_user_ids:
                u = await self.users.get_active_by_id(uid, org_id)
                if not u:
                    raise UserNotFoundException(f"User {uid} not found or inactive in this org.")

        async with self.transaction():
            # 2. Insert notification definition
            notification = await self.notifications.create(
                {
                    "org_id": org_id,
                    "title": title.strip(),
                    "message": message.strip(),
                    "notification_type": notification_type.strip(),
                    "priority": priority.strip(),
                    "source_module": source_module,
                    "source_entity_type": source_entity_type,
                    "source_entity_id": source_entity_id,
                    "created_by": caller_user_id,
                    "expires_at": expires_at,
                }
            )

            # 3. Create recipients
            if recipient_user_ids:
                for uid in recipient_user_ids:
                    await self.recipients.create(
                        {
                            "org_id": org_id,
                            "notification_id": notification.id,
                            "user_id": uid,
                            "delivered_at": None,
                        }
                    )

            # 4. Audit Log
            await self.audit.record(
                org_id=org_id,
                module="notifications",
                sub_module="notification",
                action_type=ActionType.INSERT,
                title="Create Notification",
                description=(
                    f"Created notification '{notification.title}' (ID: {notification.id}) "
                    f"assigned to {len(recipient_user_ids or [])} recipients."
                ),
                performed_by_user_id=caller_user_id,
                performed_by_name=f"User {caller_user_id}",
            )

        # 5. Enqueue delivery job
        if recipient_user_ids:
            try:
                from app.jobs.queue import enqueue, JobName
                await enqueue(JobName.DELIVER_NOTIFICATION, org_id=org_id, notification_id=notification.id)
            except Exception as exc:
                from app.core.logging import get_logger
                get_logger("notifications").warning(
                    "failed_to_enqueue_notification_delivery",
                    notification_id=notification.id,
                    error=str(exc),
                )

        return notification

    async def list_notifications(
        self,
        org_id: int,
        *,
        notification_type: str | None = None,
        priority: str | None = None,
        source_module: str | None = None,
        source_entity_type: str | None = None,
        source_entity_id: int | None = None,
        date_from: datetime.datetime | None = None,
        date_to: datetime.datetime | None = None,
        search: str | None = None,
        sort_by: str | None = "created_at",
        sort_order: str | SortOrder = SortOrder.DESC,
        page: int = 1,
        page_size: int = 25,
    ) -> PaginatedResponse[Notification]:
        """List, search, and filter notifications within the organization boundary."""
        items = await self.notifications.search(
            org_id=org_id,
            notification_type=notification_type,
            priority=priority,
            source_module=source_module,
            source_entity_type=source_entity_type,
            source_entity_id=source_entity_id,
            date_from=date_from,
            date_to=date_to,
            search=search,
            sort_by=sort_by,
            sort_order=sort_order,
            page=page,
            page_size=page_size,
        )
        total = await self.notifications.search_count(
            org_id=org_id,
            notification_type=notification_type,
            priority=priority,
            source_module=source_module,
            source_entity_type=source_entity_type,
            source_entity_id=source_entity_id,
            date_from=date_from,
            date_to=date_to,
            search=search,
        )
        return self.paginate(items, page=page, page_size=page_size, total_records=total)

    async def get_notification_details(self, org_id: int, notification_id: int) -> dict[str, Any]:
        """Fetch notification definition details plus delivery aggregates."""
        details = await self.notifications.get_details_by_id(org_id, notification_id)
        if not details:
            raise NotificationNotFoundException()

        notification, recipient_count, read_count, delivered_count = details
        return {
            "id": notification.id,
            "org_id": notification.org_id,
            "title": notification.title,
            "message": notification.message,
            "notification_type": notification.notification_type,
            "priority": notification.priority,
            "source_module": notification.source_module,
            "source_entity_type": notification.source_entity_type,
            "source_entity_id": notification.source_entity_id,
            "created_by": notification.created_by,
            "created_at": notification.created_at,
            "expires_at": notification.expires_at,
            "recipient_count": recipient_count,
            "read_count": read_count,
            "delivered_count": delivered_count,
        }

    # =========================================================================
    # 2. Admin Management — Recipient Operations
    # =========================================================================

    async def assign_recipients(
        self,
        org_id: int,
        notification_id: int,
        user_ids: list[int],
        caller_user_id: int,
    ) -> list[dict[str, Any]]:
        """Idempotently assign recipient users to an existing notification definition."""
        from datetime import timezone

        # Ensure notification exists in org context
        exists = await self.notifications.exists_in_org(org_id, notification_id)
        if not exists:
            raise NotificationNotFoundException()

        results = []
        assigned_user_ids = await self.recipients.get_assigned_user_ids(notification_id)

        async with self.transaction():
            for uid in user_ids:
                # Validate user belongs to org
                u = await self.users.get_active_by_id(uid, org_id)
                if not u:
                    results.append(
                        {
                            "user_id": uid,
                            "assigned": False,
                            "status": "user_not_found",
                            "message": f"User {uid} not found or inactive in this organization.",
                        }
                    )
                    continue

                if uid in assigned_user_ids:
                    results.append(
                        {
                            "user_id": uid,
                            "assigned": False,
                            "status": "already_assigned",
                            "message": "User is already assigned to this notification.",
                        }
                    )
                else:
                    await self.recipients.create(
                        {
                            "org_id": org_id,
                            "notification_id": notification_id,
                            "user_id": uid,
                            "delivered_at": None,
                        }
                    )
                    results.append(
                        {
                            "user_id": uid,
                            "assigned": True,
                            "status": "created",
                            "message": "User assigned successfully.",
                        }
                    )

            # Audit log if any assignments succeeded
            new_success_count = sum(1 for r in results if r["assigned"])
            if new_success_count > 0:
                await self.audit.record(
                    org_id=org_id,
                    module="notifications",
                    sub_module="recipient",
                    action_type=ActionType.INSERT,
                    title="Assign Recipients",
                    description=(
                        f"Assigned {new_success_count} new recipient users "
                        f"to notification {notification_id}."
                    ),
                    performed_by_user_id=caller_user_id,
                    performed_by_name=f"User {caller_user_id}",
                )

        # Enqueue delivery job if any new recipient was assigned
        if new_success_count > 0:
            try:
                from app.jobs.queue import enqueue, JobName
                await enqueue(JobName.DELIVER_NOTIFICATION, org_id=org_id, notification_id=notification_id)
            except Exception as exc:
                from app.core.logging import get_logger
                get_logger("notifications").warning(
                    "failed_to_enqueue_notification_delivery",
                    notification_id=notification_id,
                    error=str(exc),
                )

        return results

    async def list_recipients(
        self,
        org_id: int,
        notification_id: int,
        *,
        delivered: bool | None = None,
        read: bool | None = None,
        page: int = 1,
        page_size: int = 25,
    ) -> PaginatedResponse[NotificationRecipient]:
        """List recipients of a notification with delivery and read filters."""
        exists = await self.notifications.exists_in_org(org_id, notification_id)
        if not exists:
            raise NotificationNotFoundException()

        items = await self.recipients.search(
            notification_id=notification_id,
            org_id=org_id,
            delivered=delivered,
            read=read,
            page=page,
            page_size=page_size,
        )
        # Re-use search with count mapping
        stmt = self.recipients._build_search_query(
            notification_id=notification_id, org_id=org_id, delivered=delivered, read=read
        )
        from sqlalchemy import func, select

        stmt_count = select(func.count()).select_from(stmt.subquery())
        total = int((await self.session.execute(stmt_count)).scalar_one())

        return self.paginate(items, page=page, page_size=page_size, total_records=total)

    # =========================================================================
    # 3. User Notification Center (Self-Service)
    # =========================================================================

    async def get_user_notifications(
        self,
        org_id: int,
        user_id: int,
        *,
        status: str | None = None,
        archived: bool = False,
        notification_type: str | None = None,
        priority: str | None = None,
        source_module: str | None = None,
        include_expired: bool = False,
        page: int = 1,
        page_size: int = 25,
    ) -> PaginatedResponse[dict[str, Any]]:
        """List, filter, and paginate caller's notifications for My Notification Center."""
        recipients = await self.recipients.get_user_notifications(
            org_id=org_id,
            user_id=user_id,
            status=status,
            archived=archived,
            notification_type=notification_type,
            priority=priority,
            source_module=source_module,
            include_expired=include_expired,
            page=page,
            page_size=page_size,
        )
        total = await self.recipients.get_user_notifications_count(
            org_id=org_id,
            user_id=user_id,
            status=status,
            archived=archived,
            notification_type=notification_type,
            priority=priority,
            source_module=source_module,
            include_expired=include_expired,
        )

        flat_list = []
        for r in recipients:
            n = r.notification
            flat_list.append(
                {
                    "id": n.id,
                    "org_id": n.org_id,
                    "title": n.title,
                    "message": n.message,
                    "notification_type": n.notification_type,
                    "priority": n.priority,
                    "source_module": n.source_module,
                    "source_entity_type": n.source_entity_type,
                    "source_entity_id": n.source_entity_id,
                    "created_at": n.created_at,
                    "expires_at": n.expires_at,
                    "delivered_at": r.delivered_at,
                    "read_at": r.read_at,
                    "archived_at": r.archived_at,
                }
            )

        return self.paginate(flat_list, page=page, page_size=page_size, total_records=total)

    async def get_user_notification_counts(self, org_id: int, user_id: int) -> dict[str, int]:
        """Return counts representing unread, archived, and total active notifications."""
        return await self.recipients.get_user_notification_counts(org_id, user_id)

    async def get_user_notification(
        self, org_id: int, notification_id: int, user_id: int
    ) -> dict[str, Any]:
        """Fetch a single notification definition merged with recipient state."""
        r = await self.recipients.get_by_notification_and_user(org_id, notification_id, user_id)
        if not r or r.deleted_at is not None:
            raise RecipientNotFoundException()

        # Update delivered_at on first read/fetch
        if r.delivered_at is None:
            from datetime import timezone

            async with self.transaction():
                r = await self.recipients.update(
                    r,
                    {"delivered_at": datetime.datetime.now(timezone.utc)},  # noqa: UP017
                )

        n = r.notification
        return {
            "id": n.id,
            "org_id": n.org_id,
            "title": n.title,
            "message": n.message,
            "notification_type": n.notification_type,
            "priority": n.priority,
            "source_module": n.source_module,
            "source_entity_type": n.source_entity_type,
            "source_entity_id": n.source_entity_id,
            "created_at": n.created_at,
            "expires_at": n.expires_at,
            "delivered_at": r.delivered_at,
            "read_at": r.read_at,
            "archived_at": r.archived_at,
        }

    # =========================================================================
    # 4. User Notification Center Toggles (Self-Service Actions)
    # =========================================================================

    async def mark_read(self, org_id: int, notification_id: int, user_id: int) -> None:
        """Mark a single notification as read (sets read_at timestamp)."""
        from datetime import timezone

        r = await self.recipients.get_by_notification_and_user(org_id, notification_id, user_id)
        if not r or r.deleted_at is not None:
            raise RecipientNotFoundException()

        if r.read_at is None:
            async with self.transaction():
                await self.recipients.update(
                    r,
                    {"read_at": datetime.datetime.now(timezone.utc)},  # noqa: UP017
                )

    async def mark_unread(self, org_id: int, notification_id: int, user_id: int) -> None:
        """Mark a single notification as unread (clears read_at timestamp)."""
        r = await self.recipients.get_by_notification_and_user(org_id, notification_id, user_id)
        if not r or r.deleted_at is not None:
            raise RecipientNotFoundException()

        if r.read_at is not None:
            async with self.transaction():
                await self.recipients.update(r, {"read_at": None})

    async def archive_notification(self, org_id: int, notification_id: int, user_id: int) -> None:
        """Archive a single notification (sets archived_at timestamp)."""
        from datetime import timezone

        r = await self.recipients.get_by_notification_and_user(org_id, notification_id, user_id)
        if not r or r.deleted_at is not None:
            raise RecipientNotFoundException()

        if r.archived_at is None:
            async with self.transaction():
                await self.recipients.update(
                    r,
                    {"archived_at": datetime.datetime.now(timezone.utc)},  # noqa: UP017
                )

    async def unarchive_notification(self, org_id: int, notification_id: int, user_id: int) -> None:
        """Unarchive a single notification (clears archived_at timestamp)."""
        r = await self.recipients.get_by_notification_and_user(org_id, notification_id, user_id)
        if not r or r.deleted_at is not None:
            raise RecipientNotFoundException()

        if r.archived_at is not None:
            async with self.transaction():
                await self.recipients.update(r, {"archived_at": None})

    async def delete_notification(self, org_id: int, notification_id: int, user_id: int) -> None:
        """Soft-delete a notification for the recipient (sets deleted_at timestamp)."""
        from datetime import timezone

        r = await self.recipients.get_by_notification_and_user(org_id, notification_id, user_id)
        if not r or r.deleted_at is not None:
            raise RecipientNotFoundException()

        async with self.transaction():
            await self.recipients.update(
                r,
                {"deleted_at": datetime.datetime.now(timezone.utc)},  # noqa: UP017
            )

    # =========================================================================
    # 5. Bulk Actions (Self-Service)
    # =========================================================================

    async def bulk_mark_read(
        self,
        org_id: int,
        user_id: int,
        notification_ids: list[int] | None = None,
        all_unread: bool = False,
    ) -> int:
        """Mark multiple or all unread notifications as read. Returns affected count."""
        if not notification_ids and not all_unread:
            raise NotificationValidationException(
                "Either notification_ids or all_unread must be provided."
            )

        async with self.transaction():
            return await self.recipients.bulk_mark_read(
                org_id=org_id,
                user_id=user_id,
                notification_ids=notification_ids,
                all_unread=all_unread,
            )

    async def bulk_archive(self, org_id: int, user_id: int, notification_ids: list[int]) -> int:
        """Archive multiple notifications. Returns affected count."""
        if not notification_ids:
            raise NotificationValidationException("notification_ids list cannot be empty.")

        async with self.transaction():
            return await self.recipients.bulk_archive(
                org_id=org_id, user_id=user_id, notification_ids=notification_ids
            )

    async def bulk_delete(self, org_id: int, user_id: int, notification_ids: list[int]) -> int:
        """Soft-delete multiple notifications. Returns affected count."""
        if not notification_ids:
            raise NotificationValidationException("notification_ids list cannot be empty.")

        async with self.transaction():
            return await self.recipients.bulk_delete(
                org_id=org_id, user_id=user_id, notification_ids=notification_ids
            )

    # =========================================================================
    # 6. Notification Recipient State Timeline
    # =========================================================================

    async def get_notification_timeline(
        self, org_id: int, notification_id: int, user_id: int
    ) -> list[dict[str, Any]]:
        """Return the recipient's lifecycle event history timestamps."""
        r = await self.recipients.get_by_notification_and_user(org_id, notification_id, user_id)
        if not r:
            raise RecipientNotFoundException()

        events = []
        if r.created_at is not None:
            events.append({"event": "created", "at": r.created_at})
        if r.delivered_at is not None:
            events.append({"event": "delivered", "at": r.delivered_at})
        if r.read_at is not None:
            events.append({"event": "read", "at": r.read_at})
        if r.archived_at is not None:
            events.append({"event": "archived", "at": r.archived_at})
        if r.deleted_at is not None:
            events.append({"event": "deleted", "at": r.deleted_at})

        return sorted(events, key=lambda x: x["at"])

    # =========================================================================
    # 7. System-Generated Emission (cross-module orchestration)
    # =========================================================================

    async def resolve_user_ids_for_employees(
        self, org_id: int, employee_ids: Sequence[int]
    ) -> list[int]:
        """Resolve employees' linked, non-deleted user ids within ``org_id`` in one query.

        Employees without a linked user account are silently omitted — emitting
        modules use the (possibly empty) result to decide whether a system
        notification has any recipient at all.
        """
        if not employee_ids:
            return []
        stmt = select(User.id).where(
            User.org_id == org_id,
            User.employee_id.in_(list(employee_ids)),
            User.deleted_at.is_(None),
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def emit_system_notification(
        self,
        org_id: int,
        *,
        recipient_user_ids: Sequence[int],
        title: str,
        message: str,
        notification_type: str,
        priority: str = NotificationPriority.NORMAL.value,
        source_module: str | None = None,
        source_entity_type: str | None = None,
        source_entity_id: int | None = None,
        created_by: int | None = None,
    ) -> Notification | None:
        """Create a system-generated notification inside the caller's transaction.

        Unlike :meth:`create_notification`, this opens **no** transaction boundary:
        the emitting business service owns the transaction, so the notification
        commits (or rolls back) atomically with the business mutation it announces.
        Returns ``None`` without writing anything when ``recipient_user_ids`` is
        empty (e.g. the subject employee has no linked user account).
        """
        if not recipient_user_ids:
            return None

        notification = await self.notifications.create(
            {
                "org_id": org_id,
                "title": title,
                "message": message,
                "notification_type": notification_type,
                "priority": priority,
                "source_module": source_module,
                "source_entity_type": source_entity_type,
                "source_entity_id": source_entity_id,
                "created_by": created_by,
            }
        )

        for uid in dict.fromkeys(recipient_user_ids):  # dedupe, preserving order
            await self.recipients.create(
                {
                    "org_id": org_id,
                    "notification_id": notification.id,
                    "user_id": uid,
                    "delivered_at": None,
                }
            )

        try:
            from app.jobs.queue import enqueue, JobName
            await enqueue(JobName.DELIVER_NOTIFICATION, org_id=org_id, notification_id=notification.id)
        except Exception as exc:
            from app.core.logging import get_logger
            get_logger("notifications").warning(
                "failed_to_enqueue_system_notification_delivery",
                notification_id=notification.id,
                error=str(exc),
            )

        return notification
