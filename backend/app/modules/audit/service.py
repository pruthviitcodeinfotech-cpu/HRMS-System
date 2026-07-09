"""Activity Log — service layer (append-only audit writer).

A minimal, shared audit recorder used by every module to write one immutable
``activity_logs`` row per mutation event (contract: "All mutations call the audit
hook"). It reuses the approved :class:`~app.modules.audit.models.ActivityLog` model
and the ``ActionType`` / ``ActionFrom`` value sets — no schema is introduced here.

Transaction ownership: :meth:`record` only *flushes* the row through the shared
:class:`~app.shared.base.repository.BaseRepository`; the **calling** service owns
the commit, so an audit row is written atomically with the business mutation it
describes (both roll back together on failure).
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.audit.constants import ActionFrom, ActionType
from app.modules.audit.models import ActivityLog
from app.shared.base.repository import BaseRepository
from app.shared.utils.datetime import utcnow


class AuditService:
    """Append-only writer for the shared ``activity_logs`` audit trail."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.logs: BaseRepository[ActivityLog] = BaseRepository(session, ActivityLog)

    async def record(
        self,
        *,
        org_id: int,
        module: str,
        action_type: ActionType | str,
        title: str,
        description: str,
        performed_by_name: str,
        performed_by_user_id: int | None = None,
        employee_id: int | None = None,
        employee_name: str | None = None,
        sub_module: str | None = None,
        action_from: ActionFrom | str = ActionFrom.WEB_APP,
    ) -> ActivityLog:
        """Write a single immutable audit row (flushed, not committed).

        ``performed_by_name`` / ``employee_name`` are denormalised snapshots stored
        at write time so the log preserves historical display values. Enum arguments
        accept either the enum member or its string value.
        """
        now = utcnow()
        return await self.logs.create(
            {
                "org_id": org_id,
                "module": module,
                "sub_module": sub_module,
                "employee_id": employee_id,
                "employee_name": employee_name,
                "title": title,
                "description": description,
                "action_type": getattr(action_type, "value", action_type),
                "performed_by_user_id": performed_by_user_id,
                "performed_by_name": performed_by_name,
                "log_date": now.date(),
                "log_time": now.time(),
                "action_from": getattr(action_from, "value", action_from),
            }
        )


__all__ = ["AuditService"]
