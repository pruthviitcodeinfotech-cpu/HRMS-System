"""Dashboard Management — Service layer.

Orchestrates calls to the read-only DashboardRepository, enforces RBAC permission
gating, resolves data isolation filters (branch/department scopes) based on caller
privileges, and provides read-through Redis-based caching.
"""

from __future__ import annotations

import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache.redis import cache_get_json, cache_set_json
from app.core.constants.enums import PermissionAction
from app.core.dependencies.auth import CurrentUser
from app.core.exceptions.base import AuthorizationException
from app.modules.dashboard.repository import DashboardRepository
from app.modules.dashboard.schemas import (
    ApprovalDashboardResponse,
    ApprovalRequestBriefSchema,
    ApprovalSummarySchema,
    AttendanceDailyTrendPoint,
    AttendanceDashboardResponse,
    AttendanceSummarySchema,
    ChartResponseSchema,
    ChartSeriesPointSchema,
    DashboardKPIsResponse,
    DashboardStatisticsResponse,
    DashboardSummaryResponse,
    EmployeeDashboardResponse,
    EmployeeDistributionItem,
    EmployeeSummarySchema,
    HardwareDashboardResponse,
    HardwareSummarySchema,
    LeaveDashboardResponse,
    LeaveSummarySchema,
    LeaveTypeBreakdownItem,
    NotificationBriefSchema,
    NotificationDashboardResponse,
    NotificationSummarySchema,
    PayrollDashboardResponse,
    PayrollSummarySchema,
    SettlementDashboardResponse,
    WidgetMetadataSchema,
    WidgetsMetadataResponse,
)
from app.shared.base.service import BaseService
from app.shared.utils.datetime import utcnow

# Feature keys for RBAC permission gating
EMPLOYEE_FEATURE = "employee"
ATTENDANCE_FEATURE = "attendance"
LEAVE_FEATURE = "leave_request"
APPROVAL_FEATURE = "approval"
PAYROLL_FEATURE = "payroll_record"
SETTLEMENT_FEATURE = "settlement"
DEVICE_FEATURE = "device"


class DashboardService(BaseService):
    """Orchestrator for dashboard aggregations and metrics with caching and RBAC gating."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)
        self.repo = DashboardRepository(session)

    def _resolve_data_scopes(self, user: CurrentUser) -> tuple[list[int] | None, list[int] | None]:
        """Resolve branch and department list scopes for the user.

        Super admins have unrestricted access, yielding (None, None).
        """
        if user.is_super_admin:
            return None, None
        return list(user.permissions.branch_ids), list(user.permissions.department_ids)

    def get_widgets_metadata(self, org_id: int, user: CurrentUser) -> WidgetsMetadataResponse:
        """Return metadata configuration of all widgets along with access permissions."""
        widgets = [
            WidgetMetadataSchema(
                widget_key="summary",
                title="Summary",
                permitted=True,
                source_module="dashboard",
            ),
            WidgetMetadataSchema(
                widget_key="kpis",
                title="KPIs",
                permitted=True,
                source_module="dashboard",
            ),
            WidgetMetadataSchema(
                widget_key="statistics",
                title="Statistics",
                permitted=True,
                source_module="dashboard",
            ),
            WidgetMetadataSchema(
                widget_key="employee",
                title="Employee Card",
                permitted=user.permissions.has_permission(EMPLOYEE_FEATURE, PermissionAction.READ),
                source_module="employee",
            ),
            WidgetMetadataSchema(
                widget_key="attendance",
                title="Attendance Card",
                permitted=user.permissions.has_permission(ATTENDANCE_FEATURE, PermissionAction.READ),
                source_module="attendance",
            ),
            WidgetMetadataSchema(
                widget_key="leave",
                title="Leave Card",
                permitted=user.permissions.has_permission(LEAVE_FEATURE, PermissionAction.READ),
                source_module="leave",
            ),
            WidgetMetadataSchema(
                widget_key="approvals",
                title="Approval Card",
                permitted=user.permissions.has_permission(APPROVAL_FEATURE, PermissionAction.READ),
                source_module="approval",
            ),
            WidgetMetadataSchema(
                widget_key="payroll",
                title="Payroll Card",
                permitted=user.permissions.has_permission(PAYROLL_FEATURE, PermissionAction.READ),
                source_module="payroll",
            ),
            WidgetMetadataSchema(
                widget_key="settlements",
                title="Settlement Card",
                permitted=user.permissions.has_permission(SETTLEMENT_FEATURE, PermissionAction.READ),
                source_module="settlement",
            ),
            WidgetMetadataSchema(
                widget_key="devices",
                title="Hardware Card",
                permitted=user.permissions.has_permission(DEVICE_FEATURE, PermissionAction.READ),
                source_module="hardware",
            ),
            WidgetMetadataSchema(
                widget_key="notifications",
                title="Notification Card",
                permitted=True,
                source_module="notification",
            ),
            WidgetMetadataSchema(
                widget_key="recent_activity",
                title="Recent Activity Card",
                permitted=True,
                source_module="audit",
            ),
        ]
        return WidgetsMetadataResponse(widgets=widgets)

    async def get_summary(
        self, org_id: int, user: CurrentUser, target_date: datetime.date | None = None
    ) -> DashboardSummaryResponse:
        """Fetch unified overview metrics for all authorized modules."""
        t_date = target_date or utcnow().date()
        branch_ids, dept_ids = self._resolve_data_scopes(user)

        branch_part = ",".join(map(str, sorted(branch_ids))) if branch_ids else "all"
        dept_part = ",".join(map(str, sorted(dept_ids))) if dept_ids else "all"
        cache_key = f"dashboard:{org_id}:widget:summary:b_{branch_part}:d_{dept_part}:{t_date.isoformat()}"

        cached = await cache_get_json(cache_key)
        if cached:
            return DashboardSummaryResponse.model_validate(cached)

        # 1. Employees
        employees_data = None
        if user.permissions.has_permission(EMPLOYEE_FEATURE, PermissionAction.READ):
            date_from = t_date.replace(day=1)
            res = await self.repo.get_employee_summary(org_id, branch_ids, dept_ids, date_from, t_date)
            employees_data = EmployeeSummarySchema(
                total_employees=res["total_employees"],
                active_employees=res["active_employees"],
                new_employees=res["new_employees"],
            )

        # 2. Attendance
        attendance_data = None
        if user.permissions.has_permission(ATTENDANCE_FEATURE, PermissionAction.READ):
            res = await self.repo.get_attendance_summary(org_id, t_date, branch_ids, dept_ids)
            attendance_data = AttendanceSummarySchema(
                present_today=res["present_today"],
                absent_today=res["absent_today"],
                late_arrivals=res["late_arrivals"],
                early_exits=res["early_exits"],
                on_leave_today=res["on_leave_today"],
            )

        # 3. Leave
        leave_data = None
        if user.permissions.has_permission(LEAVE_FEATURE, PermissionAction.READ):
            date_from = t_date.replace(day=1)
            if t_date.month == 12:
                date_to = datetime.date(t_date.year + 1, 1, 1) - datetime.timedelta(days=1)
            else:
                date_to = datetime.date(t_date.year, t_date.month + 1, 1) - datetime.timedelta(days=1)
            res = await self.repo.get_leave_summary(org_id, branch_ids, dept_ids, date_from, date_to)
            leave_data = LeaveSummarySchema(
                total_requests=res["total_requests"],
                pending_leaves=res["pending"],
            )

        # 4. Approvals
        approvals_data = None
        if user.permissions.has_permission(APPROVAL_FEATURE, PermissionAction.READ):
            res = await self.repo.get_pending_approvals_summary(org_id, branch_ids, dept_ids)
            approvals_data = ApprovalSummarySchema(
                pending_approvals=res["pending_approvals"],
            )

        # 5. Payroll
        payroll_data = None
        if user.permissions.has_permission(PAYROLL_FEATURE, PermissionAction.READ):
            res = await self.repo.get_payroll_summary(org_id)
            payroll_data = PayrollSummarySchema(
                current_payroll_status=res["status"],
            )

        # 6. Devices
        devices_data = None
        if user.permissions.has_permission(DEVICE_FEATURE, PermissionAction.READ):
            res = await self.repo.get_hardware_dashboard(org_id)
            devices_data = HardwareSummarySchema(
                online_devices=res["online_devices"],
                offline_devices=res["offline_devices"],
            )

        # 7. Notifications
        res_notif = await self.repo.get_notification_dashboard(org_id, user.user_id, limit=1)
        notifications_data = NotificationSummarySchema(
            unread_notifications=res_notif["unread_count"],
        )

        response_obj = DashboardSummaryResponse(
            employees=employees_data,
            attendance=attendance_data,
            leave=leave_data,
            approvals=approvals_data,
            payroll=payroll_data,
            devices=devices_data,
            notifications=notifications_data,
            generated_at=utcnow(),
        )

        await cache_set_json(cache_key, response_obj.model_dump())
        return response_obj

    async def get_kpis(
        self, org_id: int, user: CurrentUser, target_date: datetime.date | None = None
    ) -> DashboardKPIsResponse:
        """Fetch flat headliner KPIs across the authorized modules."""
        t_date = target_date or utcnow().date()
        branch_ids, dept_ids = self._resolve_data_scopes(user)

        branch_part = ",".join(map(str, sorted(branch_ids))) if branch_ids else "all"
        dept_part = ",".join(map(str, sorted(dept_ids))) if dept_ids else "all"
        cache_key = f"dashboard:{org_id}:widget:kpis:b_{branch_part}:d_{dept_part}:{t_date.isoformat()}"

        cached = await cache_get_json(cache_key)
        if cached:
            return DashboardKPIsResponse.model_validate(cached)

        # Defaults
        total_employees = 0
        active_employees = 0
        new_employees = 0
        present_today = 0
        absent_today = 0
        late_arrivals = 0
        early_exits = 0
        on_leave_today = 0
        pending_leaves = 0
        pending_approvals = 0
        current_payroll_status = "N/A"
        total_outstanding_loans_advances = Decimal("0.00")
        total_outstanding_arrears = Decimal("0.00")
        online_devices = 0
        offline_devices = 0
        unread_notifications = 0

        # 1. Employees
        if user.permissions.has_permission(EMPLOYEE_FEATURE, PermissionAction.READ):
            date_from = t_date.replace(day=1)
            res = await self.repo.get_employee_summary(org_id, branch_ids, dept_ids, date_from, t_date)
            total_employees = res["total_employees"]
            active_employees = res["active_employees"]
            new_employees = res["new_employees"]

        # 2. Attendance
        if user.permissions.has_permission(ATTENDANCE_FEATURE, PermissionAction.READ):
            res = await self.repo.get_attendance_summary(org_id, t_date, branch_ids, dept_ids)
            present_today = res["present_today"]
            absent_today = res["absent_today"]
            late_arrivals = res["late_arrivals"]
            early_exits = res["early_exits"]
            on_leave_today = res["on_leave_today"]

        # 3. Leave
        if user.permissions.has_permission(LEAVE_FEATURE, PermissionAction.READ):
            date_from = t_date.replace(day=1)
            if t_date.month == 12:
                date_to = datetime.date(t_date.year + 1, 1, 1) - datetime.timedelta(days=1)
            else:
                date_to = datetime.date(t_date.year, t_date.month + 1, 1) - datetime.timedelta(days=1)
            res = await self.repo.get_leave_summary(org_id, branch_ids, dept_ids, date_from, date_to)
            pending_leaves = res["pending"]

        # 4. Approvals
        if user.permissions.has_permission(APPROVAL_FEATURE, PermissionAction.READ):
            res = await self.repo.get_pending_approvals_summary(org_id, branch_ids, dept_ids)
            pending_approvals = res["pending_approvals"]

        # 5. Payroll
        if user.permissions.has_permission(PAYROLL_FEATURE, PermissionAction.READ):
            res = await self.repo.get_payroll_summary(org_id)
            current_payroll_status = res["status"]

        # 6. Settlements
        if user.permissions.has_permission(SETTLEMENT_FEATURE, PermissionAction.READ):
            res = await self.repo.get_settlement_summary(org_id)
            total_outstanding_loans_advances = res.get("total_outstanding_loans_advances") or Decimal("0.00")
            total_outstanding_arrears = res.get("total_outstanding_arrears") or Decimal("0.00")

        # 7. Devices
        if user.permissions.has_permission(DEVICE_FEATURE, PermissionAction.READ):
            res = await self.repo.get_hardware_dashboard(org_id)
            online_devices = res["online_devices"]
            offline_devices = res["offline_devices"]

        # 8. Notifications
        res_notif = await self.repo.get_notification_dashboard(org_id, user.user_id, limit=1)
        unread_notifications = res_notif["unread_count"]

        response_obj = DashboardKPIsResponse(
            total_employees=total_employees,
            active_employees=active_employees,
            new_employees=new_employees,
            present_today=present_today,
            absent_today=absent_today,
            late_arrivals=late_arrivals,
            early_exits=early_exits,
            on_leave_today=on_leave_today,
            pending_leaves=pending_leaves,
            pending_approvals=pending_approvals,
            current_payroll_status=current_payroll_status,
            total_outstanding_loans_advances=total_outstanding_loans_advances,
            total_outstanding_arrears=total_outstanding_arrears,
            online_devices=online_devices,
            offline_devices=offline_devices,
            unread_notifications=unread_notifications,
            generated_at=utcnow(),
        )

        await cache_set_json(cache_key, response_obj.model_dump())
        return response_obj

    async def get_statistics(
        self, org_id: int, user: CurrentUser, target_date: datetime.date | None = None
    ) -> DashboardStatisticsResponse:
        """Fetch computed dashboard statistics and ratios."""
        t_date = target_date or utcnow().date()
        branch_ids, dept_ids = self._resolve_data_scopes(user)

        branch_part = ",".join(map(str, sorted(branch_ids))) if branch_ids else "all"
        dept_part = ",".join(map(str, sorted(dept_ids))) if dept_ids else "all"
        cache_key = f"dashboard:{org_id}:widget:statistics:b_{branch_part}:d_{dept_part}:{t_date.isoformat()}"

        cached = await cache_get_json(cache_key)
        if cached:
            return DashboardStatisticsResponse.model_validate(cached)

        employee_turnover_rate = 0.0
        attendance_rate_today = 0.0
        leave_approval_rate = 0.0
        device_uptime_rate = 0.0

        # 1. Turnover rate (Employee permission)
        if user.permissions.has_permission(EMPLOYEE_FEATURE, PermissionAction.READ):
            res_summary = await self.repo.get_employee_summary(org_id, branch_ids, dept_ids)
            total = res_summary["total_employees"]
            res_dist = await self.repo.get_employee_distribution(org_id, branch_ids, dept_ids)
            statuses = res_dist.get("employment_status", [])
            terminated_count = next((item["count"] for item in statuses if item["name"] == "terminated"), 0)
            employee_turnover_rate = (terminated_count / total) * 100.0 if total > 0 else 0.0

        # 2. Attendance rate (Attendance permission)
        if user.permissions.has_permission(ATTENDANCE_FEATURE, PermissionAction.READ):
            res = await self.repo.get_attendance_summary(org_id, t_date, branch_ids, dept_ids)
            present = res["present_today"]
            half_day = res.get("half_day_today", 0)
            absent = res["absent_today"]
            on_leave = res["on_leave_today"]
            not_marked = res.get("not_marked", 0)

            total_active = present + half_day + absent + on_leave + not_marked
            present_count = present + half_day
            attendance_rate_today = (present_count / total_active) * 100.0 if total_active > 0 else 0.0

        # 3. Leave approval rate (Leave permission)
        if user.permissions.has_permission(LEAVE_FEATURE, PermissionAction.READ):
            date_from = t_date.replace(day=1)
            if t_date.month == 12:
                date_to = datetime.date(t_date.year + 1, 1, 1) - datetime.timedelta(days=1)
            else:
                date_to = datetime.date(t_date.year, t_date.month + 1, 1) - datetime.timedelta(days=1)
            res = await self.repo.get_leave_summary(org_id, branch_ids, dept_ids, date_from, date_to)
            approved = res["approved"]
            rejected = res["rejected"]
            total_decided = approved + rejected
            leave_approval_rate = (approved / total_decided) * 100.0 if total_decided > 0 else 0.0

        # 4. Device uptime rate (Device permission)
        if user.permissions.has_permission(DEVICE_FEATURE, PermissionAction.READ):
            res = await self.repo.get_hardware_dashboard(org_id)
            online = res["online_devices"]
            offline = res["offline_devices"]
            disabled = res.get("disabled_devices", 0)
            maintenance = res.get("maintenance_devices", 0)
            total_devices = online + offline + disabled + maintenance
            device_uptime_rate = (online / total_devices) * 100.0 if total_devices > 0 else 0.0

        response_obj = DashboardStatisticsResponse(
            employee_turnover_rate=employee_turnover_rate,
            attendance_rate_today=attendance_rate_today,
            leave_approval_rate=leave_approval_rate,
            device_uptime_rate=device_uptime_rate,
            generated_at=utcnow(),
        )

        await cache_set_json(cache_key, response_obj.model_dump())
        return response_obj

    async def get_employee_dashboard(
        self, org_id: int, user: CurrentUser, target_date: datetime.date | None = None
    ) -> EmployeeDashboardResponse:
        """Fetch metrics and category distributions for Employee Dashboard."""
        if not user.permissions.has_permission(EMPLOYEE_FEATURE, PermissionAction.READ):
            raise AuthorizationException("Missing permission 'employee:read'.")

        t_date = target_date or utcnow().date()
        branch_ids, dept_ids = self._resolve_data_scopes(user)

        branch_part = ",".join(map(str, sorted(branch_ids))) if branch_ids else "all"
        dept_part = ",".join(map(str, sorted(dept_ids))) if dept_ids else "all"
        cache_key = f"dashboard:{org_id}:widget:employee:b_{branch_part}:d_{dept_part}:{t_date.isoformat()}"

        cached = await cache_get_json(cache_key)
        if cached:
            return EmployeeDashboardResponse.model_validate(cached)

        # date_from is start of current month, date_to is t_date
        date_from = t_date.replace(day=1)
        summary = await self.repo.get_employee_summary(org_id, branch_ids, dept_ids, date_from, t_date)
        dist = await self.repo.get_employee_distribution(org_id, branch_ids, dept_ids)

        total_employees = summary["total_employees"]
        active_employees = summary["active_employees"]
        inactive_employees = total_employees - active_employees
        new_employees = summary["new_employees"]

        formatted_dist = {}
        for category, items in dist.items():
            formatted_dist[category] = [
                EmployeeDistributionItem(name=item["name"] or "Unknown", count=item["count"])
                for item in items
            ]

        response_obj = EmployeeDashboardResponse(
            total_employees=total_employees,
            active_employees=active_employees,
            inactive_employees=inactive_employees,
            new_employees=new_employees,
            distribution=formatted_dist,
            generated_at=utcnow(),
        )

        await cache_set_json(cache_key, response_obj.model_dump())
        return response_obj

    async def get_attendance_dashboard(
        self, org_id: int, user: CurrentUser, target_date: datetime.date | None = None
    ) -> AttendanceDashboardResponse:
        """Fetch today's attendance summary and historical daily trend."""
        if not user.permissions.has_permission(ATTENDANCE_FEATURE, PermissionAction.READ):
            raise AuthorizationException("Missing permission 'attendance:read'.")

        t_date = target_date or utcnow().date()
        branch_ids, dept_ids = self._resolve_data_scopes(user)

        branch_part = ",".join(map(str, sorted(branch_ids))) if branch_ids else "all"
        dept_part = ",".join(map(str, sorted(dept_ids))) if dept_ids else "all"
        cache_key = f"dashboard:{org_id}:widget:attendance:b_{branch_part}:d_{dept_part}:{t_date.isoformat()}"

        cached = await cache_get_json(cache_key)
        if cached:
            return AttendanceDashboardResponse.model_validate(cached)

        summary = await self.repo.get_attendance_summary(org_id, t_date, branch_ids, dept_ids)

        # Fetch trend for the past 30 days
        date_from = t_date - datetime.timedelta(days=30)
        trend_data = await self.repo.get_attendance_trend(org_id, date_from, t_date, branch_ids, dept_ids)

        trend = [
            AttendanceDailyTrendPoint(
                date=item["date"],
                present=item["present"],
                absent=item["absent"],
                late=item["late"],
            )
            for item in trend_data
        ]

        response_obj = AttendanceDashboardResponse(
            present_today=summary["present_today"],
            absent_today=summary["absent_today"],
            half_day_today=summary.get("half_day_today", 0),
            on_leave_today=summary["on_leave_today"],
            late_arrivals=summary["late_arrivals"],
            early_exits=summary["early_exits"],
            not_marked=summary.get("not_marked", 0),
            trend=trend,
            generated_at=utcnow(),
        )

        await cache_set_json(cache_key, response_obj.model_dump())
        return response_obj

    async def get_leave_dashboard(
        self, org_id: int, user: CurrentUser, target_date: datetime.date | None = None
    ) -> LeaveDashboardResponse:
        """Fetch leave request summary and breakdown by type for the current month."""
        if not user.permissions.has_permission(LEAVE_FEATURE, PermissionAction.READ):
            raise AuthorizationException("Missing permission 'leave_request:read'.")

        t_date = target_date or utcnow().date()
        branch_ids, dept_ids = self._resolve_data_scopes(user)

        branch_part = ",".join(map(str, sorted(branch_ids))) if branch_ids else "all"
        dept_part = ",".join(map(str, sorted(dept_ids))) if dept_ids else "all"
        cache_key = f"dashboard:{org_id}:widget:leave:b_{branch_part}:d_{dept_part}:{t_date.isoformat()}"

        cached = await cache_get_json(cache_key)
        if cached:
            return LeaveDashboardResponse.model_validate(cached)

        date_from = t_date.replace(day=1)
        if t_date.month == 12:
            date_to = datetime.date(t_date.year + 1, 1, 1) - datetime.timedelta(days=1)
        else:
            date_to = datetime.date(t_date.year, t_date.month + 1, 1) - datetime.timedelta(days=1)

        summary = await self.repo.get_leave_summary(org_id, branch_ids, dept_ids, date_from, date_to)
        breakdown_data = await self.repo.get_leave_type_breakdown(org_id, branch_ids, dept_ids, date_from, date_to)

        by_type = [
            LeaveTypeBreakdownItem(leave_type=item["leave_type"] or "Unknown", count=item["count"])
            for item in breakdown_data
        ]

        response_obj = LeaveDashboardResponse(
            total_requests=summary["total_requests"],
            pending=summary["pending"],
            approved=summary["approved"],
            rejected=summary["rejected"],
            by_type=by_type,
            generated_at=utcnow(),
        )

        await cache_set_json(cache_key, response_obj.model_dump())
        return response_obj

    async def get_approval_dashboard(
        self, org_id: int, user: CurrentUser
    ) -> ApprovalDashboardResponse:
        """Fetch pending approval counts, types, and recent approval logs."""
        if not user.permissions.has_permission(APPROVAL_FEATURE, PermissionAction.READ):
            raise AuthorizationException("Missing permission 'approval:read'.")

        branch_ids, dept_ids = self._resolve_data_scopes(user)

        branch_part = ",".join(map(str, sorted(branch_ids))) if branch_ids else "all"
        dept_part = ",".join(map(str, sorted(dept_ids))) if dept_ids else "all"
        cache_key = f"dashboard:{org_id}:widget:approval:b_{branch_part}:d_{dept_part}"

        cached = await cache_get_json(cache_key)
        if cached:
            return ApprovalDashboardResponse.model_validate(cached)

        summary = await self.repo.get_pending_approvals_summary(org_id, branch_ids, dept_ids)

        # Fetch the last 100 resolved approvals to count approved/rejected in recent decisions
        resolved_recent = await self.repo.get_recent_approvals(
            org_id, limit=100, branch_ids=branch_ids, dept_ids=dept_ids
        )
        approved_recent = sum(1 for r in resolved_recent if r["status"] == "approved")
        rejected_recent = sum(1 for r in resolved_recent if r["status"] == "rejected")

        # Take top 5 for the brief list
        recent_briefs = [
            ApprovalRequestBriefSchema(
                id=item["id"],
                request_type=item["request_type"],
                status=item["status"],
                requester_name=item["requester_name"] or "Unknown",
                submitted_at=item["submitted_at"],
            )
            for item in resolved_recent[:5]
        ]

        response_obj = ApprovalDashboardResponse(
            pending_approvals=summary["pending_approvals"],
            by_request_type=summary["by_request_type"],
            approved_recent=approved_recent,
            rejected_recent=rejected_recent,
            recent=recent_briefs,
            generated_at=utcnow(),
        )

        await cache_set_json(cache_key, response_obj.model_dump())
        return response_obj

    async def get_payroll_dashboard(
        self, org_id: int, user: CurrentUser
    ) -> PayrollDashboardResponse:
        """Fetch current payroll run cost breakdown and execution state."""
        if not user.permissions.has_permission(PAYROLL_FEATURE, PermissionAction.READ):
            raise AuthorizationException("Missing permission 'payroll_record:read'.")

        cache_key = f"dashboard:{org_id}:widget:payroll"

        cached = await cache_get_json(cache_key)
        if cached:
            return PayrollDashboardResponse.model_validate(cached)

        res = await self.repo.get_payroll_summary(org_id)

        response_obj = PayrollDashboardResponse(
            current_cycle_id=res["current_cycle_id"],
            current_cycle_name=res["current_cycle_name"],
            is_finalized=res["is_finalized"],
            status=res["status"],
            finalized_amount=res["finalized_amount"],
            payment_status_breakdown=res["payment_status_breakdown"],
            headcount=res["headcount"],
            generated_at=utcnow(),
        )

        await cache_set_json(cache_key, response_obj.model_dump())
        return response_obj

    async def get_settlement_dashboard(
        self, org_id: int, user: CurrentUser
    ) -> SettlementDashboardResponse:
        """Fetch outstanding loan balances and closed settlements summary."""
        if not user.permissions.has_permission(SETTLEMENT_FEATURE, PermissionAction.READ):
            raise AuthorizationException("Missing permission 'settlement:read'.")

        cache_key = f"dashboard:{org_id}:widget:settlement"

        cached = await cache_get_json(cache_key)
        if cached:
            return SettlementDashboardResponse.model_validate(cached)

        res = await self.repo.get_settlement_summary(org_id)

        response_obj = SettlementDashboardResponse(
            active_loans_advances=res["active_loans_advances"],
            closed_loans_advances=res["closed_loans_advances"],
            total_outstanding_loans_advances=res.get("total_outstanding_loans_advances") or Decimal("0.00"),
            total_outstanding_arrears=res.get("total_outstanding_arrears") or Decimal("0.00"),
            generated_at=utcnow(),
        )

        await cache_set_json(cache_key, response_obj.model_dump())
        return response_obj

    async def get_hardware_dashboard(
        self, org_id: int, user: CurrentUser
    ) -> HardwareDashboardResponse:
        """Fetch biometric device connection statuses and last sync logs."""
        if not user.permissions.has_permission(DEVICE_FEATURE, PermissionAction.READ):
            raise AuthorizationException("Missing permission 'device:read'.")

        cache_key = f"dashboard:{org_id}:widget:hardware"

        cached = await cache_get_json(cache_key)
        if cached:
            return HardwareDashboardResponse.model_validate(cached)

        res = await self.repo.get_hardware_dashboard(org_id)

        response_obj = HardwareDashboardResponse(
            online_devices=res["online_devices"],
            offline_devices=res["offline_devices"],
            disabled_devices=res.get("disabled_devices", 0),
            maintenance_devices=res.get("maintenance_devices", 0),
            last_device_sync=res["last_device_sync"],
            generated_at=utcnow(),
        )

        await cache_set_json(cache_key, response_obj.model_dump())
        return response_obj

    async def get_notification_dashboard(
        self, org_id: int, user: CurrentUser, limit: int = 5
    ) -> NotificationDashboardResponse:
        """Fetch unread notifications count and recent notification items for the caller."""
        cache_key = f"dashboard:{org_id}:widget:notification:u_{user.user_id}:l_{limit}"

        cached = await cache_get_json(cache_key)
        if cached:
            return NotificationDashboardResponse.model_validate(cached)

        res = await self.repo.get_notification_dashboard(org_id, user.user_id, limit=limit)

        recent = [
            NotificationBriefSchema(
                id=item["id"],
                title=item["title"],
                notification_type=item["notification_type"],
                priority=item["priority"],
                created_at=item["created_at"],
            )
            for item in res["recent"]
        ]

        response_obj = NotificationDashboardResponse(
            unread_count=res["unread_count"],
            recent=recent,
            generated_at=utcnow(),
        )

        await cache_set_json(cache_key, response_obj.model_dump())
        return response_obj

    async def get_recent_activity(
        self, org_id: int, user: CurrentUser, limit: int = 10
    ) -> list[dict[str, Any]]:
        """Fetch recent activity logs within the branch and department scopes."""
        branch_ids, dept_ids = self._resolve_data_scopes(user)
        # Always read-only query, no special feature-level permission gating needed beyond dashboard:read
        return await self.repo.get_recent_activities(
            org_id, limit=limit, branch_ids=branch_ids, dept_ids=dept_ids
        )

    # ===========================================================================
    # Chart Projections
    # ===========================================================================

    async def get_attendance_trend_chart(
        self, org_id: int, user: CurrentUser, days: int = 30
    ) -> ChartResponseSchema:
        """Fetch past N days daily attendance counts trend."""
        if not user.permissions.has_permission(ATTENDANCE_FEATURE, PermissionAction.READ):
            raise AuthorizationException("Missing permission 'attendance:read'.")

        branch_ids, dept_ids = self._resolve_data_scopes(user)

        branch_part = ",".join(map(str, sorted(branch_ids))) if branch_ids else "all"
        dept_part = ",".join(map(str, sorted(dept_ids))) if dept_ids else "all"
        cache_key = f"dashboard:{org_id}:chart:attendance-trend:b_{branch_part}:d_{dept_part}:days_{days}"

        cached = await cache_get_json(cache_key)
        if cached:
            return ChartResponseSchema.model_validate(cached)

        date_to = utcnow().date()
        date_from = date_to - datetime.timedelta(days=days)

        trend_data = await self.repo.get_attendance_trend(
            org_id, date_from, date_to, branch_ids, dept_ids
        )

        labels = [item["date"].strftime("%Y-%m-%d") for item in trend_data]
        series = [
            ChartSeriesPointSchema(name="Present", points=[float(item["present"]) for item in trend_data]),
            ChartSeriesPointSchema(name="Absent", points=[float(item["absent"]) for item in trend_data]),
            ChartSeriesPointSchema(name="Late", points=[float(item["late"]) for item in trend_data]),
        ]

        response_obj = ChartResponseSchema(
            labels=labels,
            series=series,
            generated_at=utcnow(),
        )

        await cache_set_json(cache_key, response_obj.model_dump())
        return response_obj

    async def get_employee_growth_chart(
        self, org_id: int, user: CurrentUser, months: int = 6
    ) -> ChartResponseSchema:
        """Fetch past N months cumulative active headcount growth trend."""
        if not user.permissions.has_permission(EMPLOYEE_FEATURE, PermissionAction.READ):
            raise AuthorizationException("Missing permission 'employee:read'.")

        branch_ids, dept_ids = self._resolve_data_scopes(user)

        branch_part = ",".join(map(str, sorted(branch_ids))) if branch_ids else "all"
        dept_part = ",".join(map(str, sorted(dept_ids))) if dept_ids else "all"
        cache_key = f"dashboard:{org_id}:chart:employee-growth:b_{branch_part}:d_{dept_part}:months_{months}"

        cached = await cache_get_json(cache_key)
        if cached:
            return ChartResponseSchema.model_validate(cached)

        date_to = utcnow().date()
        year = date_to.year
        month = date_to.month - months
        while month <= 0:
            month += 12
            year -= 1
        date_from = datetime.date(year, month, 1)

        res = await self.repo.get_employee_growth_chart(
            org_id, date_from, date_to, branch_ids, dept_ids
        )

        series = [
            ChartSeriesPointSchema(name=s["name"], points=[float(p) for p in s["points"]])
            for s in res["series"]
        ]

        response_obj = ChartResponseSchema(
            labels=res["labels"],
            series=series,
            generated_at=utcnow(),
        )

        await cache_set_json(cache_key, response_obj.model_dump())
        return response_obj

    async def get_leave_trend_chart(
        self, org_id: int, user: CurrentUser, months: int = 6
    ) -> ChartResponseSchema:
        """Fetch past N months daily count of leave requests by status."""
        if not user.permissions.has_permission(LEAVE_FEATURE, PermissionAction.READ):
            raise AuthorizationException("Missing permission 'leave_request:read'.")

        branch_ids, dept_ids = self._resolve_data_scopes(user)

        branch_part = ",".join(map(str, sorted(branch_ids))) if branch_ids else "all"
        dept_part = ",".join(map(str, sorted(dept_ids))) if dept_ids else "all"
        cache_key = f"dashboard:{org_id}:chart:leave-trend:b_{branch_part}:d_{dept_part}:months_{months}"

        cached = await cache_get_json(cache_key)
        if cached:
            return ChartResponseSchema.model_validate(cached)

        date_to = utcnow().date()
        year = date_to.year
        month = date_to.month - months
        while month <= 0:
            month += 12
            year -= 1
        date_from = datetime.date(year, month, 1)

        res = await self.repo.get_leave_trend_chart(
            org_id, date_from, date_to, branch_ids, dept_ids
        )

        series = [
            ChartSeriesPointSchema(name=s["name"], points=[float(p) for p in s["points"]])
            for s in res["series"]
        ]

        response_obj = ChartResponseSchema(
            labels=res["labels"],
            series=series,
            generated_at=utcnow(),
        )

        await cache_set_json(cache_key, response_obj.model_dump())
        return response_obj

    async def get_payroll_trend_chart(
        self, org_id: int, user: CurrentUser, limit: int = 6
    ) -> ChartResponseSchema:
        """Fetch trend of finalized payroll costs over the past N runs."""
        if not user.permissions.has_permission(PAYROLL_FEATURE, PermissionAction.READ):
            raise AuthorizationException("Missing permission 'payroll_record:read'.")

        cache_key = f"dashboard:{org_id}:chart:payroll-trend:limit_{limit}"

        cached = await cache_get_json(cache_key)
        if cached:
            return ChartResponseSchema.model_validate(cached)

        res = await self.repo.get_payroll_trend_chart(org_id, limit=limit)

        series = [
            ChartSeriesPointSchema(name=s["name"], points=[float(p) for p in s["points"]])
            for s in res["series"]
        ]

        response_obj = ChartResponseSchema(
            labels=res["labels"],
            series=series,
            generated_at=utcnow(),
        )

        await cache_set_json(cache_key, response_obj.model_dump())
        return response_obj

    async def get_dept_attendance_chart(
        self, org_id: int, user: CurrentUser, target_date: datetime.date | None = None
    ) -> ChartResponseSchema:
        """Fetch today's attendance rates broken down by department."""
        if not user.permissions.has_permission(ATTENDANCE_FEATURE, PermissionAction.READ):
            raise AuthorizationException("Missing permission 'attendance:read'.")

        t_date = target_date or utcnow().date()
        branch_ids, dept_ids = self._resolve_data_scopes(user)

        branch_part = ",".join(map(str, sorted(branch_ids))) if branch_ids else "all"
        dept_part = ",".join(map(str, sorted(dept_ids))) if dept_ids else "all"
        cache_key = f"dashboard:{org_id}:chart:dept-attendance:b_{branch_part}:d_{dept_part}:{t_date.isoformat()}"

        cached = await cache_get_json(cache_key)
        if cached:
            return ChartResponseSchema.model_validate(cached)

        res = await self.repo.get_department_attendance_chart(
            org_id, t_date, branch_ids, dept_ids
        )

        series = [
            ChartSeriesPointSchema(name=s["name"], points=[float(p) for p in s["points"]])
            for s in res["series"]
        ]

        response_obj = ChartResponseSchema(
            labels=res["labels"],
            series=series,
            generated_at=utcnow(),
        )

        await cache_set_json(cache_key, response_obj.model_dump())
        return response_obj

    async def get_branch_attendance_chart(
        self, org_id: int, user: CurrentUser, target_date: datetime.date | None = None
    ) -> ChartResponseSchema:
        """Fetch today's attendance rates broken down by branch."""
        if not user.permissions.has_permission(ATTENDANCE_FEATURE, PermissionAction.READ):
            raise AuthorizationException("Missing permission 'attendance:read'.")

        t_date = target_date or utcnow().date()
        branch_ids, dept_ids = self._resolve_data_scopes(user)

        branch_part = ",".join(map(str, sorted(branch_ids))) if branch_ids else "all"
        dept_part = ",".join(map(str, sorted(dept_ids))) if dept_ids else "all"
        cache_key = f"dashboard:{org_id}:chart:branch-attendance:b_{branch_part}:d_{dept_part}:{t_date.isoformat()}"

        cached = await cache_get_json(cache_key)
        if cached:
            return ChartResponseSchema.model_validate(cached)

        res = await self.repo.get_branch_attendance_chart(
            org_id, t_date, branch_ids, dept_ids
        )

        series = [
            ChartSeriesPointSchema(name=s["name"], points=[float(p) for p in s["points"]])
            for s in res["series"]
        ]

        response_obj = ChartResponseSchema(
            labels=res["labels"],
            series=series,
            generated_at=utcnow(),
        )

        await cache_set_json(cache_key, response_obj.model_dump())
        return response_obj
