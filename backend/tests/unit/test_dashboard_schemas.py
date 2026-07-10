"""Unit tests for the Dashboard Management Pydantic schemas validation."""

from __future__ import annotations

import datetime
from decimal import Decimal

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
    SettlementSummarySchema,
    WidgetMetadataSchema,
    WidgetsMetadataResponse,
)

_NOW = datetime.datetime(2026, 7, 10, 10, 0, 0, tzinfo=datetime.timezone.utc)  # noqa: UP017


def test_chart_schemas() -> None:
    point = ChartSeriesPointSchema(name="Present", points=[10.0, 12.0, 15.0])
    assert point.name == "Present"
    assert point.points == [10.0, 12.0, 15.0]

    chart = ChartResponseSchema(
        labels=["Mon", "Tue", "Wed"],
        series=[point],
        generated_at=_NOW,
    )
    assert chart.labels == ["Mon", "Tue", "Wed"]
    assert len(chart.series) == 1
    assert chart.series[0].name == "Present"
    assert chart.generated_at == _NOW


def test_widget_metadata_schemas() -> None:
    widget = WidgetMetadataSchema(
        widget_key="employee_summary",
        title="Employee Summary",
        permitted=True,
        source_module="employee",
    )
    assert widget.widget_key == "employee_summary"
    assert widget.permitted is True

    response = WidgetsMetadataResponse(widgets=[widget])
    assert len(response.widgets) == 1
    assert response.widgets[0].widget_key == "employee_summary"


def test_dashboard_summary_response() -> None:
    emp_summary = EmployeeSummarySchema(total_employees=100, active_employees=95, new_employees=5)
    att_summary = AttendanceSummarySchema(
        present_today=80, absent_today=10, late_arrivals=5, early_exits=2, on_leave_today=5
    )
    leave_summary = LeaveSummarySchema(total_requests=10, pending_leaves=2)
    app_summary = ApprovalSummarySchema(pending_approvals=3)
    pay_summary = PayrollSummarySchema(current_payroll_status="draft")
    set_summary = SettlementSummarySchema(
        total_outstanding_loans_advances=Decimal("5000.00"),
        total_outstanding_arrears=Decimal("1500.50"),
    )
    hw_summary = HardwareSummarySchema(online_devices=4, offline_devices=1)
    notif_summary = NotificationSummarySchema(unread_notifications=5)

    summary = DashboardSummaryResponse(
        employees=emp_summary,
        attendance=att_summary,
        leave=leave_summary,
        approvals=app_summary,
        payroll=pay_summary,
        devices=hw_summary,
        notifications=notif_summary,
        generated_at=_NOW,
    )

    assert summary.employees == emp_summary
    assert summary.attendance == att_summary
    assert summary.leave == leave_summary
    assert summary.approvals == app_summary
    assert summary.payroll == pay_summary
    assert summary.payroll.current_payroll_status == "draft"
    assert summary.devices == hw_summary
    assert summary.notifications == notif_summary
    assert summary.generated_at == _NOW
    assert set_summary.total_outstanding_loans_advances == Decimal("5000.00")


def test_dashboard_kpis_response() -> None:
    kpi = DashboardKPIsResponse(
        total_employees=100,
        active_employees=95,
        new_employees=5,
        present_today=80,
        absent_today=10,
        late_arrivals=5,
        early_exits=2,
        on_leave_today=5,
        pending_leaves=2,
        pending_approvals=3,
        current_payroll_status="finalized",
        total_outstanding_loans_advances=Decimal("10000.00"),
        total_outstanding_arrears=Decimal("500.00"),
        online_devices=4,
        offline_devices=1,
        unread_notifications=5,
        generated_at=_NOW,
    )

    assert kpi.total_employees == 100
    assert kpi.active_employees == 95
    assert kpi.new_employees == 5
    assert kpi.present_today == 80
    assert kpi.absent_today == 10
    assert kpi.late_arrivals == 5
    assert kpi.early_exits == 2
    assert kpi.on_leave_today == 5
    assert kpi.pending_leaves == 2
    assert kpi.pending_approvals == 3
    assert kpi.current_payroll_status == "finalized"
    assert kpi.total_outstanding_loans_advances == Decimal("10000.00")
    assert kpi.total_outstanding_arrears == Decimal("500.00")
    assert kpi.online_devices == 4
    assert kpi.offline_devices == 1
    assert kpi.unread_notifications == 5
    assert kpi.generated_at == _NOW


def test_dashboard_statistics_response() -> None:
    stats = DashboardStatisticsResponse(
        employee_turnover_rate=1.5,
        attendance_rate_today=84.2,
        leave_approval_rate=90.0,
        device_uptime_rate=80.0,
        generated_at=_NOW,
    )

    assert stats.employee_turnover_rate == 1.5
    assert stats.attendance_rate_today == 84.2
    assert stats.leave_approval_rate == 90.0
    assert stats.device_uptime_rate == 80.0
    assert stats.generated_at == _NOW


def test_employee_dashboard_response() -> None:
    dist_dept = EmployeeDistributionItem(name="HR", count=10)
    dist_branch = EmployeeDistributionItem(name="Headquarters", count=50)

    emp_dash = EmployeeDashboardResponse(
        total_employees=100,
        active_employees=95,
        inactive_employees=5,
        new_employees=5,
        distribution={
            "department": [dist_dept],
            "branch": [dist_branch],
        },
        generated_at=_NOW,
    )

    assert emp_dash.total_employees == 100
    assert emp_dash.distribution["department"][0].name == "HR"
    assert emp_dash.distribution["department"][0].count == 10
    assert emp_dash.generated_at == _NOW


def test_attendance_dashboard_response() -> None:
    trend_point = AttendanceDailyTrendPoint(
        date=datetime.date(2026, 7, 9), present=85, absent=10, late=5
    )

    att_dash = AttendanceDashboardResponse(
        present_today=80,
        absent_today=10,
        half_day_today=2,
        on_leave_today=3,
        late_arrivals=5,
        early_exits=1,
        not_marked=4,
        trend=[trend_point],
        generated_at=_NOW,
    )

    assert att_dash.present_today == 80
    assert att_dash.trend[0].date == datetime.date(2026, 7, 9)
    assert att_dash.trend[0].present == 85
    assert att_dash.generated_at == _NOW


def test_leave_dashboard_response() -> None:
    breakdown = LeaveTypeBreakdownItem(leave_type="Casual Leave", count=15)

    leave_dash = LeaveDashboardResponse(
        total_requests=50,
        pending=10,
        approved=35,
        rejected=5,
        by_type=[breakdown],
        generated_at=_NOW,
    )

    assert leave_dash.total_requests == 50
    assert leave_dash.by_type[0].leave_type == "Casual Leave"
    assert leave_dash.by_type[0].count == 15
    assert leave_dash.generated_at == _NOW


def test_approval_dashboard_response() -> None:
    brief = ApprovalRequestBriefSchema(
        id=1,
        request_type="leave",
        status="pending",
        requester_name="John Doe",
        submitted_at=_NOW,
    )

    app_dash = ApprovalDashboardResponse(
        pending_approvals=5,
        by_request_type={"leave": 3, "attendance_regularization": 2},
        approved_recent=20,
        rejected_recent=2,
        recent=[brief],
        generated_at=_NOW,
    )

    assert app_dash.pending_approvals == 5
    assert app_dash.by_request_type["leave"] == 3
    assert app_dash.recent[0].requester_name == "John Doe"
    assert app_dash.generated_at == _NOW


def test_payroll_dashboard_response() -> None:
    pay_dash = PayrollDashboardResponse(
        current_cycle_id=1,
        current_cycle_name="July 2026",
        is_finalized=False,
        status="processing",
        finalized_amount=Decimal("150000.00"),
        payment_status_breakdown={"paid": 0, "unpaid": 95},
        headcount=95,
        generated_at=_NOW,
    )

    assert pay_dash.current_cycle_id == 1
    assert pay_dash.is_finalized is False
    assert pay_dash.finalized_amount == Decimal("150000.00")
    assert pay_dash.generated_at == _NOW


def test_settlement_dashboard_response() -> None:
    set_dash = SettlementDashboardResponse(
        active_loans_advances=5,
        closed_loans_advances=12,
        total_outstanding_loans_advances=Decimal("25000.00"),
        total_outstanding_arrears=Decimal("0.00"),
        generated_at=_NOW,
    )

    assert set_dash.active_loans_advances == 5
    assert set_dash.total_outstanding_loans_advances == Decimal("25000.00")
    assert set_dash.generated_at == _NOW


def test_hardware_dashboard_response() -> None:
    hw_dash = HardwareDashboardResponse(
        online_devices=5,
        offline_devices=1,
        disabled_devices=0,
        maintenance_devices=0,
        last_device_sync=_NOW,
        generated_at=_NOW,
    )

    assert hw_dash.online_devices == 5
    assert hw_dash.last_device_sync == _NOW
    assert hw_dash.generated_at == _NOW


def test_notification_dashboard_response() -> None:
    brief = NotificationBriefSchema(
        id=1,
        title="Welcome Notification",
        notification_type="system",
        priority="normal",
        created_at=_NOW,
    )

    notif_dash = NotificationDashboardResponse(
        unread_count=5,
        recent=[brief],
        generated_at=_NOW,
    )

    assert notif_dash.unread_count == 5
    assert notif_dash.recent[0].title == "Welcome Notification"
    assert notif_dash.generated_at == _NOW
