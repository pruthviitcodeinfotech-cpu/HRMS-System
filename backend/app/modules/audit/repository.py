"""Activity Log / Audit — data-access repository (async SQLAlchemy, read-only).

Provides org-scoped SELECT/COUNT queries over the append-only ``activity_logs``
table: the general list/search/filter surface (§4), the per-employee and per-user
change-history lookups (§5), and the approximate security-event view (§6).

The audit trail is append-only; this repository intentionally exposes **no**
create/update/delete helpers — writes are performed exclusively by
:class:`~app.modules.audit.service.AuditService` (the shared ``record`` writer).
Every query is scoped by ``org_id`` first: the audit trail is cross-tenant
sensitive and no read may omit the tenant filter.
"""

from __future__ import annotations

import datetime
from typing import Any

from sqlalchemy import and_, asc, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants.enums import SortOrder
from app.modules.audit.constants import ActionFrom, ActionType
from app.modules.audit.models import ActivityLog
from app.shared.base.repository import BaseRepository

# Sort allowlist (contract §3): only these two columns may be sorted on.
SORTABLE_FIELDS: dict[str, Any] = {
    "logged_at": ActivityLog.logged_at,
    "log_date": ActivityLog.log_date,
}

# Modules considered "security related" for the approximate security-event view (§6).
SECURITY_MODULES: tuple[str, ...] = ("rbac", "user")


class ActivityLogRepository(BaseRepository[ActivityLog]):
    """Read-only repository for the shared ``activity_logs`` audit trail."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, ActivityLog)

    # --- Lookups -------------------------------------------------------------

    async def get_by_id_in_org(self, org_id: int, log_id: int) -> ActivityLog | None:
        """Retrieve a single audit row by id, scoped to a specific organization."""
        stmt = select(ActivityLog).where(
            ActivityLog.id == log_id,
            ActivityLog.org_id == org_id,
        )
        result = await self.session.execute(stmt.limit(1))
        return result.scalar_one_or_none()

    # --- Filter construction -------------------------------------------------

    @staticmethod
    def _conditions(
        org_id: int,
        *,
        module: str | None = None,
        sub_module: str | None = None,
        action_type: ActionType | str | None = None,
        action_from: ActionFrom | str | None = None,
        employee_id: int | None = None,
        performed_by_user_id: int | None = None,
        date_from: datetime.date | None = None,
        date_to: datetime.date | None = None,
        search: str | None = None,
    ) -> list[Any]:
        """Build the org-scoped SQLAlchemy filter list for a log query."""
        conds: list[Any] = [ActivityLog.org_id == org_id]

        if module is not None:
            conds.append(ActivityLog.module == module)
        if sub_module is not None:
            conds.append(ActivityLog.sub_module == sub_module)
        if action_type is not None:
            conds.append(ActivityLog.action_type == getattr(action_type, "value", action_type))
        if action_from is not None:
            conds.append(ActivityLog.action_from == getattr(action_from, "value", action_from))
        if employee_id is not None:
            conds.append(ActivityLog.employee_id == employee_id)
        if performed_by_user_id is not None:
            conds.append(ActivityLog.performed_by_user_id == performed_by_user_id)
        if date_from is not None:
            conds.append(ActivityLog.log_date >= date_from)
        if date_to is not None:
            conds.append(ActivityLog.log_date <= date_to)
        if search:
            term = f"%{search.strip()}%"
            conds.append(
                or_(
                    ActivityLog.title.ilike(term),
                    ActivityLog.description.ilike(term),
                )
            )

        return conds

    @staticmethod
    def _security_conditions(
        org_id: int,
        *,
        event: str | None = None,
        employee_id: int | None = None,
        performed_by_user_id: int | None = None,
        date_from: datetime.date | None = None,
        date_to: datetime.date | None = None,
    ) -> list[Any]:
        """Build filters for the approximate security-event view (§6).

        ``event`` maps to ``activity_logs`` filters:
          * ``role_assignment``       -> module='rbac', action_type='Assign'
          * ``permission_change``     -> module='rbac', action_type='Update'
          * ``account_status_change`` -> module='user'
          * (unset)                   -> module in the security-related set
        """
        conds: list[Any] = [ActivityLog.org_id == org_id]

        if event == "role_assignment":
            conds.append(ActivityLog.module == "rbac")
            conds.append(ActivityLog.action_type == ActionType.ASSIGN.value)
        elif event == "permission_change":
            conds.append(ActivityLog.module == "rbac")
            conds.append(ActivityLog.action_type == ActionType.UPDATE.value)
        elif event == "account_status_change":
            conds.append(ActivityLog.module == "user")
        else:
            conds.append(ActivityLog.module.in_(SECURITY_MODULES))

        if employee_id is not None:
            conds.append(ActivityLog.employee_id == employee_id)
        if performed_by_user_id is not None:
            conds.append(ActivityLog.performed_by_user_id == performed_by_user_id)
        if date_from is not None:
            conds.append(ActivityLog.log_date >= date_from)
        if date_to is not None:
            conds.append(ActivityLog.log_date <= date_to)

        return conds

    @staticmethod
    def _order_by(stmt: Any, sort_by: str | None, sort_order: SortOrder | str) -> Any:
        """Apply the validated ordering (default ``logged_at desc``)."""
        column = SORTABLE_FIELDS.get(sort_by or "", ActivityLog.logged_at)
        order = sort_order if isinstance(sort_order, SortOrder) else SortOrder(sort_order)
        direction = desc if order is SortOrder.DESC else asc
        # Stable tiebreaker on the primary key for deterministic pagination.
        return stmt.order_by(direction(column), ActivityLog.id.desc())

    # --- Search / Count (§4 list, §5 change-history views) -------------------

    async def search(
        self,
        org_id: int,
        *,
        module: str | None = None,
        sub_module: str | None = None,
        action_type: ActionType | str | None = None,
        action_from: ActionFrom | str | None = None,
        employee_id: int | None = None,
        performed_by_user_id: int | None = None,
        date_from: datetime.date | None = None,
        date_to: datetime.date | None = None,
        search: str | None = None,
        sort_by: str | None = None,
        sort_order: SortOrder | str = SortOrder.DESC,
        page: int = 1,
        page_size: int = 25,
    ) -> list[ActivityLog]:
        """Search, filter, sort, and paginate audit rows within an organization."""
        conds = self._conditions(
            org_id,
            module=module,
            sub_module=sub_module,
            action_type=action_type,
            action_from=action_from,
            employee_id=employee_id,
            performed_by_user_id=performed_by_user_id,
            date_from=date_from,
            date_to=date_to,
            search=search,
        )
        stmt = self._order_by(select(ActivityLog).where(and_(*conds)), sort_by, sort_order)
        stmt = stmt.limit(page_size).offset((page - 1) * page_size)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def search_count(
        self,
        org_id: int,
        *,
        module: str | None = None,
        sub_module: str | None = None,
        action_type: ActionType | str | None = None,
        action_from: ActionFrom | str | None = None,
        employee_id: int | None = None,
        performed_by_user_id: int | None = None,
        date_from: datetime.date | None = None,
        date_to: datetime.date | None = None,
        search: str | None = None,
    ) -> int:
        """Count audit rows matching the filter set within an organization."""
        conds = self._conditions(
            org_id,
            module=module,
            sub_module=sub_module,
            action_type=action_type,
            action_from=action_from,
            employee_id=employee_id,
            performed_by_user_id=performed_by_user_id,
            date_from=date_from,
            date_to=date_to,
            search=search,
        )
        stmt = select(func.count(ActivityLog.id)).where(and_(*conds))
        result = await self.session.execute(stmt)
        return int(result.scalar_one())

    # --- Security events (§6) ------------------------------------------------

    async def search_security_events(
        self,
        org_id: int,
        *,
        event: str | None = None,
        employee_id: int | None = None,
        performed_by_user_id: int | None = None,
        date_from: datetime.date | None = None,
        date_to: datetime.date | None = None,
        page: int = 1,
        page_size: int = 25,
    ) -> list[ActivityLog]:
        """Return the chronological (``logged_at desc``) security-event view."""
        conds = self._security_conditions(
            org_id,
            event=event,
            employee_id=employee_id,
            performed_by_user_id=performed_by_user_id,
            date_from=date_from,
            date_to=date_to,
        )
        stmt = self._order_by(select(ActivityLog).where(and_(*conds)), "logged_at", SortOrder.DESC)
        stmt = stmt.limit(page_size).offset((page - 1) * page_size)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def search_security_events_count(
        self,
        org_id: int,
        *,
        event: str | None = None,
        employee_id: int | None = None,
        performed_by_user_id: int | None = None,
        date_from: datetime.date | None = None,
        date_to: datetime.date | None = None,
    ) -> int:
        """Count rows matching the security-event view."""
        conds = self._security_conditions(
            org_id,
            event=event,
            employee_id=employee_id,
            performed_by_user_id=performed_by_user_id,
            date_from=date_from,
            date_to=date_to,
        )
        stmt = select(func.count(ActivityLog.id)).where(and_(*conds))
        result = await self.session.execute(stmt)
        return int(result.scalar_one())


__all__ = ["ActivityLogRepository", "SORTABLE_FIELDS", "SECURITY_MODULES"]
