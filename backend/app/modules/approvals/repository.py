"""Approval Management — data-access layer (async SQLAlchemy).

Provides repository classes for:
- ApprovalRequest (unified approval workflow logs)
- AttendanceRegularizationRequest (manual corrections)
- LoginResetRequest (credential reset requests)

Operates entirely on existing database models and inherits from BaseRepository.
"""

from __future__ import annotations

from datetime import date as dt_date, datetime, time, timezone
from typing import Any

from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants.enums import SortOrder
from app.modules.approvals.constants import ApprovalStatus, RequestType
from app.modules.approvals.models import (
    ApprovalRequest,
    AttendanceRegularizationRequest,
    LoginResetRequest,
)
from app.modules.employee.models.employee import Employee
from app.modules.leave.models import LeaveRequest
from app.shared.base.repository import BaseRepository
from app.shared.utils.query import apply_pagination, apply_sorting


class ApprovalRequestRepository(BaseRepository[ApprovalRequest]):
    """CRUD operations, filtering, sorting, pagination, and dashboard stats for ApprovalRequest."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, ApprovalRequest)

    async def get_by_id_in_org(self, org_id: int, approval_id: int) -> ApprovalRequest | None:
        """Retrieve a specific approval request scoped to the organization ID."""
        stmt = select(ApprovalRequest).where(
            ApprovalRequest.id == approval_id,
            ApprovalRequest.org_id == org_id,
        )
        return (await self.session.execute(stmt.limit(1))).scalar_one_or_none()

    @staticmethod
    def _search_conditions(
        org_id: int,
        *,
        status: ApprovalStatus | list[ApprovalStatus] | None = None,
        request_type: RequestType | None = None,
        request_subtype: str | None = None,
        employee_id: int | None = None,
        date_from: dt_date | None = None,
        date_to: dt_date | None = None,
    ) -> list[Any]:
        """Build the query conditions based on filters."""
        conds = [ApprovalRequest.org_id == org_id]

        if status is not None:
            if isinstance(status, list):
                conds.append(ApprovalRequest.status.in_([s.value for s in status]))
            else:
                conds.append(ApprovalRequest.status == status.value)

        if request_type is not None:
            conds.append(ApprovalRequest.request_type == request_type.value)

        if request_subtype is not None:
            conds.append(ApprovalRequest.request_subtype == request_subtype)

        if employee_id is not None:
            conds.append(ApprovalRequest.employee_id == employee_id)

        if date_from is not None:
            dt_min = datetime.combine(date_from, time.min).replace(tzinfo=timezone.utc)
            conds.append(ApprovalRequest.requested_at >= dt_min)

        if date_to is not None:
            dt_max = datetime.combine(date_to, time.max).replace(tzinfo=timezone.utc)
            conds.append(ApprovalRequest.requested_at <= dt_max)

        return conds

    async def search(
        self,
        org_id: int,
        *,
        status: ApprovalStatus | list[ApprovalStatus] | None = None,
        request_type: RequestType | None = None,
        request_subtype: str | None = None,
        employee_id: int | None = None,
        date_from: dt_date | None = None,
        date_to: dt_date | None = None,
        branch_id: int | None = None,
        dept_id: int | None = None,
        sort_by: str | None = "requested_at",
        sort_order: SortOrder | str = SortOrder.DESC,
        page: int = 1,
        page_size: int = 25,
    ) -> list[ApprovalRequest]:
        """Search and filter approval requests, incorporating employee branch/department scoping."""
        conds = self._search_conditions(
            org_id,
            status=status,
            request_type=request_type,
            request_subtype=request_subtype,
            employee_id=employee_id,
            date_from=date_from,
            date_to=date_to,
        )

        stmt = select(ApprovalRequest)

        # Join employee if branch or department filtering is requested
        if branch_id is not None or dept_id is not None:
            stmt = stmt.join(Employee, Employee.employee_id == ApprovalRequest.employee_id)
            if branch_id is not None:
                conds.append(Employee.master_branch_id == branch_id)
            if dept_id is not None:
                conds.append(Employee.dept_id == dept_id)
            conds.append(Employee.is_deleted.is_(False))

        stmt = stmt.where(and_(*conds))
        stmt = apply_sorting(
            stmt,
            ApprovalRequest,
            sort_by=sort_by,
            sort_order=sort_order,
            allowed={"requested_at", "reviewed_at", "status"},
            default_sort_by="requested_at",
        )
        stmt = apply_pagination(stmt, page=page, page_size=page_size)

        return list((await self.session.execute(stmt)).scalars().all())

    async def search_count(
        self,
        org_id: int,
        *,
        status: ApprovalStatus | list[ApprovalStatus] | None = None,
        request_type: RequestType | None = None,
        request_subtype: str | None = None,
        employee_id: int | None = None,
        date_from: dt_date | None = None,
        date_to: dt_date | None = None,
        branch_id: int | None = None,
        dept_id: int | None = None,
    ) -> int:
        """Count approval requests matching the search and filter criteria."""
        conds = self._search_conditions(
            org_id,
            status=status,
            request_type=request_type,
            request_subtype=request_subtype,
            employee_id=employee_id,
            date_from=date_from,
            date_to=date_to,
        )

        stmt = select(func.count()).select_from(ApprovalRequest)

        # Join employee if branch or department filtering is requested
        if branch_id is not None or dept_id is not None:
            stmt = stmt.join(Employee, Employee.employee_id == ApprovalRequest.employee_id)
            if branch_id is not None:
                conds.append(Employee.master_branch_id == branch_id)
            if dept_id is not None:
                conds.append(Employee.dept_id == dept_id)
            conds.append(Employee.is_deleted.is_(False))

        stmt = stmt.where(and_(*conds))
        return int((await self.session.execute(stmt)).scalar_one())

    async def get_source_record(
        self, request_type: RequestType | str, reference_id: int
    ) -> LeaveRequest | AttendanceRegularizationRequest | LoginResetRequest | None:
        """Resolve and retrieve the underlying source record based on type and polymorphic reference ID."""
        type_val = request_type.value if isinstance(request_type, RequestType) else request_type

        if type_val == RequestType.LEAVE:
            stmt = select(LeaveRequest).where(LeaveRequest.id == reference_id)
            return (await self.session.execute(stmt.limit(1))).scalar_one_or_none()

        if type_val == RequestType.ATTENDANCE:
            stmt = select(AttendanceRegularizationRequest).where(
                AttendanceRegularizationRequest.id == reference_id
            )
            return (await self.session.execute(stmt.limit(1))).scalar_one_or_none()

        if type_val == RequestType.LOGIN_RESET:
            stmt = select(LoginResetRequest).where(LoginResetRequest.id == reference_id)
            return (await self.session.execute(stmt.limit(1))).scalar_one_or_none()

        return None

    async def get_pending_counts_by_type(
        self, org_id: int, *, branch_id: int | None = None, dept_id: int | None = None
    ) -> dict[str, int]:
        """Aggregate counts of pending approvals scoped by org and data scope, grouped by request type."""
        conds = [
            ApprovalRequest.org_id == org_id,
            ApprovalRequest.status == ApprovalStatus.PENDING.value,
        ]

        stmt = select(ApprovalRequest.request_type, func.count()).select_from(ApprovalRequest)

        if branch_id is not None or dept_id is not None:
            stmt = stmt.join(Employee, Employee.employee_id == ApprovalRequest.employee_id)
            if branch_id is not None:
                conds.append(Employee.master_branch_id == branch_id)
            if dept_id is not None:
                conds.append(Employee.dept_id == dept_id)
            conds.append(Employee.is_deleted.is_(False))

        stmt = stmt.where(and_(*conds)).group_by(ApprovalRequest.request_type)
        results = (await self.session.execute(stmt)).all()

        counts = {t.value: 0 for t in RequestType}
        for req_type, count in results:
            counts[req_type] = count
        return counts

    async def get_recent_decisions(
        self,
        org_id: int,
        *,
        decision: ApprovalStatus,
        request_type: RequestType | None = None,
        branch_id: int | None = None,
        dept_id: int | None = None,
        limit: int = 10,
    ) -> list[ApprovalRequest]:
        """Fetch recent decided approval requests scoped by org and data scope, sorted by review time."""
        conds = [
            ApprovalRequest.org_id == org_id,
            ApprovalRequest.status == decision.value,
        ]

        if request_type is not None:
            conds.append(ApprovalRequest.request_type == request_type.value)

        stmt = select(ApprovalRequest)

        if branch_id is not None or dept_id is not None:
            stmt = stmt.join(Employee, Employee.employee_id == ApprovalRequest.employee_id)
            if branch_id is not None:
                conds.append(Employee.master_branch_id == branch_id)
            if dept_id is not None:
                conds.append(Employee.dept_id == dept_id)
            conds.append(Employee.is_deleted.is_(False))

        stmt = stmt.where(and_(*conds)).order_by(desc(ApprovalRequest.reviewed_at)).limit(limit)
        return list((await self.session.execute(stmt)).scalars().all())


class AttendanceRegularizationRequestRepository(BaseRepository[AttendanceRegularizationRequest]):
    """Repository operations for AttendanceRegularizationRequest."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, AttendanceRegularizationRequest)

    async def has_pending_request(self, employee_id: int, attendance_date: dt_date) -> bool:
        """Check if an active pending correction request exists for the employee and date."""
        stmt = select(AttendanceRegularizationRequest.id).where(
            AttendanceRegularizationRequest.employee_id == employee_id,
            AttendanceRegularizationRequest.attendance_date == attendance_date,
            AttendanceRegularizationRequest.status == ApprovalStatus.PENDING.value,
        )
        return (await self.session.execute(stmt.limit(1))).first() is not None


class LoginResetRequestRepository(BaseRepository[LoginResetRequest]):
    """Repository operations for LoginResetRequest."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, LoginResetRequest)

    async def has_pending_request(self, employee_id: int) -> bool:
        """Check if an active pending login reset request exists for the employee."""
        stmt = select(LoginResetRequest.id).where(
            LoginResetRequest.employee_id == employee_id,
            LoginResetRequest.status == ApprovalStatus.PENDING.value,
        )
        return (await self.session.execute(stmt.limit(1))).first() is not None
