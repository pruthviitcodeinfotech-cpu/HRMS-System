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

from app.core.exceptions.base import (
    AuthorizationException,
    NotFoundException,
    ValidationException,
)
from app.modules.audit.constants import ActionFrom, ActionType
from app.modules.audit.models import ActivityLog
from app.modules.audit.repository import SORTABLE_FIELDS, ActivityLogRepository
from app.modules.audit.schemas import (
    ActivityLogDetail,
    ActivityLogListItem,
    ActivityLogListResponse,
    ActivityLogSearchQuery,
    SecurityEventQuery,
    SubjectActivityLogQuery,
)
from app.modules.employee.repository import EmployeeRepository
from app.modules.rbac.repository import UserRepository
from app.shared.base.repository import BaseRepository
from app.shared.utils.datetime import utcnow


class AuditService:
    """Append-only writer + read surface for the shared ``activity_logs`` trail.

    The ``record`` method (below) is the append-only writer that every other
    module's service depends on and MUST NOT change. The remaining methods add the
    read-only query surface (contract §4–§6); the audit trail exposes no
    create/update/delete API.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.logs: BaseRepository[ActivityLog] = BaseRepository(session, ActivityLog)
        self.activity: ActivityLogRepository = ActivityLogRepository(session)
        self.employees = EmployeeRepository(session)
        self.users = UserRepository(session)

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

    # =======================================================================
    # Read surface (contract §4–§6) — org-scoped, read-only
    # =======================================================================

    @staticmethod
    def _validate_sort(sort_by: str | None) -> None:
        """Reject an unknown ``sort_by`` with a 422 (contract §3/§10)."""
        if sort_by is not None and sort_by not in SORTABLE_FIELDS:
            allowed = ", ".join(sorted(SORTABLE_FIELDS))
            raise ValidationException(
                f"Invalid sort field '{sort_by}'. Allowed: {allowed}.",
                details=[{"field": "sort_by", "message": f"Allowed: {allowed}."}],
            )

    async def list_logs(
        self, *, org_id: int, query: ActivityLogSearchQuery
    ) -> ActivityLogListResponse:
        """List / search / filter audit rows within the tenant (§4.1, §4.3)."""
        self._validate_sort(query.sort_by)

        rows = await self.activity.search(
            org_id,
            module=query.module,
            sub_module=query.sub_module,
            action_type=query.action_type,
            action_from=query.action_from,
            employee_id=query.employee_id,
            performed_by_user_id=query.performed_by_user_id,
            date_from=query.date_from,
            date_to=query.date_to,
            search=query.search,
            sort_by=query.sort_by,
            sort_order=query.sort_order,
            page=query.page,
            page_size=query.page_size,
        )
        total = await self.activity.search_count(
            org_id,
            module=query.module,
            sub_module=query.sub_module,
            action_type=query.action_type,
            action_from=query.action_from,
            employee_id=query.employee_id,
            performed_by_user_id=query.performed_by_user_id,
            date_from=query.date_from,
            date_to=query.date_to,
            search=query.search,
        )
        return self._to_list_response(rows, query.page, query.page_size, total)

    async def get_log(self, *, org_id: int, log_id: int) -> ActivityLogDetail:
        """Return a full audit row or raise ACTIVITY_LOG_NOT_FOUND (§4.2)."""
        row = await self.activity.get_by_id_in_org(org_id, log_id)
        if row is None:
            raise NotFoundException(
                "Activity log not found.", code="ACTIVITY_LOG_NOT_FOUND"
            )
        return ActivityLogDetail.model_validate(row)

    async def list_employee_logs(
        self,
        *,
        org_id: int,
        employee_id: int,
        query: SubjectActivityLogQuery,
        allowed_branch_ids: list[int] | None = None,
    ) -> ActivityLogListResponse:
        """Change history for one employee subject (§5.4), branch/dept data-scoped."""
        self._validate_sort(query.sort_by)

        employee = await self.employees.get_active_by_id(employee_id, org_id)
        if employee is None:
            raise NotFoundException("Employee not found.", code="EMPLOYEE_NOT_FOUND")

        # Branch/department data scope: restricted callers may only read logs for
        # employees within their allowed branches (super admins pass unrestricted).
        if allowed_branch_ids is not None and employee.master_branch_id not in allowed_branch_ids:
            raise AuthorizationException(
                "You do not have access to this employee's activity."
            )

        rows = await self.activity.search(
            org_id,
            module=query.module,
            sub_module=query.sub_module,
            action_type=query.action_type,
            employee_id=employee_id,
            date_from=query.date_from,
            date_to=query.date_to,
            sort_by=query.sort_by,
            sort_order=query.sort_order,
            page=query.page,
            page_size=query.page_size,
        )
        total = await self.activity.search_count(
            org_id,
            module=query.module,
            sub_module=query.sub_module,
            action_type=query.action_type,
            employee_id=employee_id,
            date_from=query.date_from,
            date_to=query.date_to,
        )
        return self._to_list_response(rows, query.page, query.page_size, total)

    async def list_user_logs(
        self, *, org_id: int, user_id: int, query: SubjectActivityLogQuery
    ) -> ActivityLogListResponse:
        """Actions performed BY one user (§5.5)."""
        self._validate_sort(query.sort_by)

        user = await self.users.get_active_by_id(user_id, org_id)
        if user is None:
            raise NotFoundException("User not found.", code="USER_NOT_FOUND")

        rows = await self.activity.search(
            org_id,
            module=query.module,
            sub_module=query.sub_module,
            action_type=query.action_type,
            performed_by_user_id=user_id,
            date_from=query.date_from,
            date_to=query.date_to,
            sort_by=query.sort_by,
            sort_order=query.sort_order,
            page=query.page,
            page_size=query.page_size,
        )
        total = await self.activity.search_count(
            org_id,
            module=query.module,
            sub_module=query.sub_module,
            action_type=query.action_type,
            performed_by_user_id=user_id,
            date_from=query.date_from,
            date_to=query.date_to,
        )
        return self._to_list_response(rows, query.page, query.page_size, total)

    async def list_security_events(
        self, *, org_id: int, query: SecurityEventQuery
    ) -> ActivityLogListResponse:
        """Approximate security-event timeline (§6), chronological ``logged_at desc``."""
        event = query.event.value if query.event is not None else None
        rows = await self.activity.search_security_events(
            org_id,
            event=event,
            employee_id=query.employee_id,
            performed_by_user_id=query.performed_by_user_id,
            date_from=query.date_from,
            date_to=query.date_to,
            page=query.page,
            page_size=query.page_size,
        )
        total = await self.activity.search_security_events_count(
            org_id,
            event=event,
            employee_id=query.employee_id,
            performed_by_user_id=query.performed_by_user_id,
            date_from=query.date_from,
            date_to=query.date_to,
        )
        return self._to_list_response(rows, query.page, query.page_size, total)

    @staticmethod
    def _to_list_response(
        rows: list[ActivityLog], page: int, page_size: int, total: int
    ) -> ActivityLogListResponse:
        """Assemble a paginated list envelope of compact audit items."""
        items = [ActivityLogListItem.model_validate(row) for row in rows]
        return ActivityLogListResponse.build(
            items=items, page=page, page_size=page_size, total_records=total
        )


__all__ = ["AuditService"]
