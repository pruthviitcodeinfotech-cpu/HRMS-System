"""Notifications Management — data-access layer (async SQLAlchemy).

Defines the repository classes for Notification definitions and user Recipient state.
Only database operations are handled here — no business rules are evaluated.
"""

from __future__ import annotations

import datetime

from sqlalchemy import and_, case, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.constants.enums import SortOrder
from app.modules.notifications.models import Notification, NotificationRecipient
from app.shared.base.repository import BaseRepository
from app.shared.utils.query import apply_sorting

# ===========================================================================
# 1. Notification Definition Repository
# ===========================================================================


class NotificationRepository(BaseRepository[Notification]):
    """CRUD, search, and details lookup for Notification definitions."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Notification)

    async def get_by_id_in_org(self, org_id: int, notification_id: int) -> Notification | None:
        """Fetch a notification by ID scoped to org_id."""
        stmt = select(Notification).where(
            Notification.id == notification_id,
            Notification.org_id == org_id,
        )
        return (await self.session.execute(stmt.limit(1))).scalar_one_or_none()

    async def get_details_by_id(
        self, org_id: int, notification_id: int
    ) -> tuple[Notification, int, int, int] | None:
        """Fetch a notification along with recipient counts (total, read, delivered)."""
        stmt = select(
            Notification,
            select(func.count(NotificationRecipient.id))
            .where(NotificationRecipient.notification_id == notification_id)
            .scalar_subquery()
            .label("recipient_count"),
            select(func.count(NotificationRecipient.id))
            .where(
                and_(
                    NotificationRecipient.notification_id == notification_id,
                    NotificationRecipient.read_at.isnot(None),
                )
            )
            .scalar_subquery()
            .label("read_count"),
            select(func.count(NotificationRecipient.id))
            .where(
                and_(
                    NotificationRecipient.notification_id == notification_id,
                    NotificationRecipient.delivered_at.isnot(None),
                )
            )
            .scalar_subquery()
            .label("delivered_count"),
        ).where(
            Notification.id == notification_id,
            Notification.org_id == org_id,
        )
        result = (await self.session.execute(stmt.limit(1))).first()
        if not result:
            return None
        return (result[0], result[1], result[2], result[3])

    async def exists_in_org(self, org_id: int, notification_id: int) -> bool:
        """Check if a notification exists within the organization."""
        stmt = select(Notification.id).where(
            Notification.id == notification_id,
            Notification.org_id == org_id,
        )
        return (await self.session.execute(stmt.limit(1))).first() is not None

    def _build_search_query(
        self,
        org_id: int,
        notification_type: str | None = None,
        priority: str | None = None,
        source_module: str | None = None,
        source_entity_type: str | None = None,
        source_entity_id: int | None = None,
        date_from: datetime.datetime | None = None,
        date_to: datetime.datetime | None = None,
        search: str | None = None,
    ) -> select:
        stmt = select(Notification)
        conds = [Notification.org_id == org_id]

        if notification_type is not None:
            conds.append(Notification.notification_type == notification_type)
        if priority is not None:
            conds.append(Notification.priority == priority)
        if source_module is not None:
            conds.append(Notification.source_module == source_module)
        if source_entity_type is not None:
            conds.append(Notification.source_entity_type == source_entity_type)
        if source_entity_id is not None:
            conds.append(Notification.source_entity_id == source_entity_id)
        if date_from is not None:
            conds.append(Notification.created_at >= date_from)
        if date_to is not None:
            conds.append(Notification.created_at <= date_to)
        if search:
            search_pattern = f"%{search.strip()}%"
            conds.append(
                Notification.title.ilike(search_pattern)
                | Notification.message.ilike(search_pattern)
            )

        return stmt.where(and_(*conds))

    async def search(
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
    ) -> list[Notification]:
        """Search and filter organization notifications with pagination and sorting."""
        stmt = self._build_search_query(
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
        stmt = apply_sorting(
            stmt,
            Notification,
            sort_by,
            sort_order,
            allowed={"created_at", "priority", "notification_type"},
            default_sort_by="created_at",
        )
        stmt = stmt.limit(page_size).offset((page - 1) * page_size)
        return list((await self.session.execute(stmt)).scalars().all())

    async def search_count(
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
    ) -> int:
        """Return the count of notifications matching the search criteria."""
        base_stmt = self._build_search_query(
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
        stmt = select(func.count()).select_from(base_stmt.subquery())
        return int((await self.session.execute(stmt)).scalar_one())


# ===========================================================================
# 2. Notification Recipient State Repository
# ===========================================================================


class NotificationRecipientRepository(BaseRepository[NotificationRecipient]):
    """CRUD, status updates, bulk actions, and search for user NotificationRecipients."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, NotificationRecipient)

    async def get_by_notification_and_user(
        self, org_id: int, notification_id: int, user_id: int
    ) -> NotificationRecipient | None:
        """Fetch a recipient record by notification and user IDs, scoped to org_id."""
        stmt = select(NotificationRecipient).where(
            NotificationRecipient.notification_id == notification_id,
            NotificationRecipient.user_id == user_id,
            NotificationRecipient.org_id == org_id,
        )
        return (await self.session.execute(stmt.limit(1))).scalar_one_or_none()

    async def exists_in_org(self, org_id: int, recipient_id: int) -> bool:
        """Check if a recipient record exists within the organization."""
        stmt = select(NotificationRecipient.id).where(
            NotificationRecipient.id == recipient_id,
            NotificationRecipient.org_id == org_id,
        )
        return (await self.session.execute(stmt.limit(1))).first() is not None

    async def get_assigned_user_ids(self, notification_id: int) -> set[int]:
        """Fetch all user IDs currently assigned to a notification."""
        stmt = select(NotificationRecipient.user_id).where(
            NotificationRecipient.notification_id == notification_id
        )
        result = await self.session.execute(stmt)
        return set(result.scalars().all())

    def _build_search_query(
        self,
        notification_id: int,
        org_id: int,
        delivered: bool | None = None,
        read: bool | None = None,
    ) -> select:
        stmt = select(NotificationRecipient).where(
            NotificationRecipient.notification_id == notification_id,
            NotificationRecipient.org_id == org_id,
        )
        if delivered is not None:
            if delivered:
                stmt = stmt.where(NotificationRecipient.delivered_at.isnot(None))
            else:
                stmt = stmt.where(NotificationRecipient.delivered_at.is_(None))
        if read is not None:
            if read:
                stmt = stmt.where(NotificationRecipient.read_at.isnot(None))
            else:
                stmt = stmt.where(NotificationRecipient.read_at.is_(None))
        return stmt

    async def search(
        self,
        notification_id: int,
        org_id: int,
        *,
        delivered: bool | None = None,
        read: bool | None = None,
        page: int = 1,
        page_size: int = 25,
    ) -> list[NotificationRecipient]:
        """Return a paginated list of recipients for a notification."""
        stmt = self._build_search_query(
            notification_id=notification_id,
            org_id=org_id,
            delivered=delivered,
            read=read,
        )
        stmt = stmt.order_by(NotificationRecipient.created_at.desc())
        stmt = stmt.limit(page_size).offset((page - 1) * page_size)
        return list((await self.session.execute(stmt)).scalars().all())

    def _build_user_notifications_query(
        self,
        org_id: int,
        user_id: int,
        status: str | None = None,
        archived: bool = False,
        notification_type: str | None = None,
        priority: str | None = None,
        source_module: str | None = None,
        include_expired: bool = False,
    ) -> select:
        stmt = (
            select(NotificationRecipient)
            .join(Notification, Notification.id == NotificationRecipient.notification_id)
            .where(
                NotificationRecipient.org_id == org_id,
                NotificationRecipient.user_id == user_id,
                NotificationRecipient.deleted_at.is_(None),
            )
        )

        if status == "unread":
            stmt = stmt.where(NotificationRecipient.read_at.is_(None))
        elif status == "read":
            stmt = stmt.where(NotificationRecipient.read_at.isnot(None))

        if archived:
            stmt = stmt.where(NotificationRecipient.archived_at.isnot(None))
        else:
            stmt = stmt.where(NotificationRecipient.archived_at.is_(None))

        if notification_type is not None:
            stmt = stmt.where(Notification.notification_type == notification_type)
        if priority is not None:
            stmt = stmt.where(Notification.priority == priority)
        if source_module is not None:
            stmt = stmt.where(Notification.source_module == source_module)

        if not include_expired:
            from datetime import timezone

            now = datetime.datetime.now(timezone.utc)  # noqa: UP017
            stmt = stmt.where(Notification.expires_at.is_(None) | (Notification.expires_at > now))

        return stmt

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
    ) -> list[NotificationRecipient]:
        """Fetch user notifications center list with pagination and eager-loading."""
        stmt = self._build_user_notifications_query(
            org_id=org_id,
            user_id=user_id,
            status=status,
            archived=archived,
            notification_type=notification_type,
            priority=priority,
            source_module=source_module,
            include_expired=include_expired,
        )
        stmt = stmt.order_by(Notification.created_at.desc())
        stmt = stmt.options(joinedload(NotificationRecipient.notification))
        stmt = stmt.limit(page_size).offset((page - 1) * page_size)
        return list((await self.session.execute(stmt)).scalars().all())

    async def get_user_notifications_count(
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
    ) -> int:
        """Count user notifications matching center criteria."""
        base_stmt = self._build_user_notifications_query(
            org_id=org_id,
            user_id=user_id,
            status=status,
            archived=archived,
            notification_type=notification_type,
            priority=priority,
            source_module=source_module,
            include_expired=include_expired,
        )
        stmt = select(func.count()).select_from(base_stmt.subquery())
        return int((await self.session.execute(stmt)).scalar_one())

    async def get_user_notification_counts(self, org_id: int, user_id: int) -> dict[str, int]:
        """Return dict with unread_count, archived_count, and total_count for the user."""
        stmt = select(
            func.coalesce(
                func.sum(case((NotificationRecipient.deleted_at.is_(None), 1), else_=0)),
                0,
            ).label("total_count"),
            func.coalesce(
                func.sum(
                    case(
                        (
                            and_(
                                NotificationRecipient.deleted_at.is_(None),
                                NotificationRecipient.read_at.is_(None),
                            ),
                            1,
                        ),
                        else_=0,
                    )
                ),
                0,
            ).label("unread_count"),
            func.coalesce(
                func.sum(
                    case(
                        (
                            and_(
                                NotificationRecipient.deleted_at.is_(None),
                                NotificationRecipient.archived_at.isnot(None),
                            ),
                            1,
                        ),
                        else_=0,
                    )
                ),
                0,
            ).label("archived_count"),
        ).where(
            NotificationRecipient.org_id == org_id,
            NotificationRecipient.user_id == user_id,
        )
        result = (await self.session.execute(stmt)).first()
        if not result:
            return {"total_count": 0, "unread_count": 0, "archived_count": 0}
        return {
            "total_count": int(result[0]),
            "unread_count": int(result[1]),
            "archived_count": int(result[2]),
        }

    async def bulk_mark_read(
        self,
        org_id: int,
        user_id: int,
        notification_ids: list[int] | None = None,
        all_unread: bool = False,
    ) -> int:
        """Mark multiple or all unread notifications as read. Returns affected row count."""
        from datetime import timezone

        now = datetime.datetime.now(timezone.utc)  # noqa: UP017

        stmt = (
            update(NotificationRecipient)
            .where(
                NotificationRecipient.org_id == org_id,
                NotificationRecipient.user_id == user_id,
                NotificationRecipient.read_at.is_(None),
                NotificationRecipient.deleted_at.is_(None),
            )
            .values(read_at=now)
        )

        if not all_unread and notification_ids:
            stmt = stmt.where(NotificationRecipient.notification_id.in_(notification_ids))

        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.rowcount

    async def bulk_archive(
        self,
        org_id: int,
        user_id: int,
        notification_ids: list[int],
    ) -> int:
        """Archive multiple notifications. Returns affected row count."""
        from datetime import timezone

        now = datetime.datetime.now(timezone.utc)  # noqa: UP017

        stmt = (
            update(NotificationRecipient)
            .where(
                NotificationRecipient.org_id == org_id,
                NotificationRecipient.user_id == user_id,
                NotificationRecipient.notification_id.in_(notification_ids),
                NotificationRecipient.deleted_at.is_(None),
            )
            .values(archived_at=now)
        )

        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.rowcount

    async def bulk_delete(
        self,
        org_id: int,
        user_id: int,
        notification_ids: list[int],
    ) -> int:
        """Soft-delete multiple notifications. Returns affected row count."""
        from datetime import timezone

        now = datetime.datetime.now(timezone.utc)  # noqa: UP017

        stmt = (
            update(NotificationRecipient)
            .where(
                NotificationRecipient.org_id == org_id,
                NotificationRecipient.user_id == user_id,
                NotificationRecipient.notification_id.in_(notification_ids),
                NotificationRecipient.deleted_at.is_(None),
            )
            .values(deleted_at=now)
        )

        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.rowcount
