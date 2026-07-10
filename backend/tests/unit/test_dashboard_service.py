"""Unit tests for ``DashboardService`` business logic (repositories mocked)."""

from __future__ import annotations

import datetime
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest

from app.core.dependencies.auth import CurrentUser
from app.core.exceptions.base import AuthorizationException
from app.core.security.permissions import build_effective_permissions
from app.modules.dashboard.dependencies import get_dashboard_service
from app.modules.dashboard.service import DashboardService

_NOW = datetime.datetime(2026, 7, 10, 10, 0, 0, tzinfo=datetime.UTC)


def _principal(
    *, is_super_admin: bool = False, org_id: int = 1, branch_ids=(), department_ids=(), perms=None
) -> CurrentUser:
    permissions = build_effective_permissions(
        is_super_admin=is_super_admin,
        feature_rows=perms or [],
        branch_ids=list(branch_ids),
        department_ids=list(department_ids),
    )
    return CurrentUser(
        user_id=1,
        org_id=org_id,
        is_super_admin=is_super_admin,
        is_active=True,
        permissions=permissions,
    )


def _perm(feature_key: str, **flags: bool) -> dict[str, object]:
    base = {
        "feature_key": feature_key,
        "can_create": False,
        "can_read": False,
        "can_edit": False,
        "can_delete": False,
    }
    base.update(flags)
    return base


@pytest.fixture
def mock_cache():
    """Mock Redis cache get/set functions."""
    with (
        patch("app.modules.dashboard.service.cache_get_json", new_callable=AsyncMock) as mock_get,
        patch("app.modules.dashboard.service.cache_set_json", new_callable=AsyncMock) as mock_set,
    ):
        mock_get.return_value = None
        yield mock_get, mock_set


@pytest.fixture
def dashboard_service():
    """Create DashboardService instance with mocked repository."""
    session = AsyncMock()
    service = DashboardService(session)
    service.repo = AsyncMock()
    return service


# ===========================================================================
# 1. Widget Metadata tests
# ===========================================================================


def test_get_widgets_metadata(dashboard_service) -> None:
    # Super Admin has access to all widgets
    user_sa = _principal(is_super_admin=True)
    res = dashboard_service.get_widgets_metadata(org_id=1, user=user_sa)
    for widget in res.widgets:
        assert widget.permitted is True

    # Regular user has limited permissions
    user_reg = _principal(
        is_super_admin=False,
        perms=[
            _perm("employee", can_read=True),
            _perm("attendance", can_read=True),
        ],
    )
    res = dashboard_service.get_widgets_metadata(org_id=1, user=user_reg)
    widget_map = {w.widget_key: w.permitted for w in res.widgets}
    assert widget_map["employee"] is True
    assert widget_map["attendance"] is True
    assert widget_map["leave"] is False
    assert widget_map["approvals"] is False
    assert widget_map["payroll"] is False
    assert widget_map["settlements"] is False
    assert widget_map["devices"] is False


# ===========================================================================
# 2. Combined Summary Dashboard tests
# ===========================================================================


@pytest.mark.asyncio
async def test_get_summary_success(dashboard_service, mock_cache) -> None:
    mock_get, mock_set = mock_cache
    user = _principal(
        is_super_admin=False,
        perms=[
            _perm("employee", can_read=True),
            _perm("attendance", can_read=True),
            _perm("leave_request", can_read=True),
            _perm("approval", can_read=True),
            _perm("payroll_record", can_read=True),
            _perm("device", can_read=True),
        ],
    )

    dashboard_service.repo.get_employee_summary.return_value = {
        "total_employees": 100,
        "active_employees": 95,
        "new_employees": 5,
    }
    dashboard_service.repo.get_attendance_summary.return_value = {
        "present_today": 80,
        "absent_today": 10,
        "late_arrivals": 5,
        "early_exits": 2,
        "on_leave_today": 3,
    }
    dashboard_service.repo.get_leave_summary.return_value = {
        "total_requests": 10,
        "pending": 2,
    }
    dashboard_service.repo.get_pending_approvals_summary.return_value = {
        "pending_approvals": 4,
    }
    dashboard_service.repo.get_payroll_summary.return_value = {
        "status": "draft",
    }
    dashboard_service.repo.get_hardware_dashboard.return_value = {
        "online_devices": 4,
        "offline_devices": 1,
    }
    dashboard_service.repo.get_notification_dashboard.return_value = {
        "unread_count": 3,
        "recent": [],
    }

    res = await dashboard_service.get_summary(org_id=1, user=user)

    assert res.employees.total_employees == 100
    assert res.attendance.present_today == 80
    assert res.leave.pending_leaves == 2
    assert res.approvals.pending_approvals == 4
    assert res.payroll.current_payroll_status == "draft"
    assert res.devices.online_devices == 4
    assert res.notifications.unread_notifications == 3

    mock_get.assert_awaited_once()
    mock_set.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_summary_cache_hit(dashboard_service, mock_cache) -> None:
    mock_get, mock_set = mock_cache
    user = _principal(is_super_admin=True)

    cached_data = {
        "employees": {"total_employees": 10, "active_employees": 9, "new_employees": 1},
        "attendance": None,
        "leave": None,
        "approvals": None,
        "payroll": None,
        "devices": None,
        "notifications": {"unread_notifications": 0},
        "generated_at": "2026-07-10T10:00:00",
    }
    mock_get.return_value = cached_data

    res = await dashboard_service.get_summary(org_id=1, user=user)
    assert res.employees.total_employees == 10
    assert res.attendance is None
    dashboard_service.repo.get_employee_summary.assert_not_called()
    mock_get.assert_awaited_once()
    mock_set.assert_not_called()


# ===========================================================================
# 3. Flat KPIs & Statistics tests
# ===========================================================================


@pytest.mark.asyncio
async def test_get_kpis(dashboard_service, mock_cache) -> None:
    mock_get, mock_set = mock_cache
    user = _principal(
        is_super_admin=False,
        perms=[
            _perm("employee", can_read=True),
            _perm("attendance", can_read=True),
            _perm("leave_request", can_read=True),
            _perm("approval", can_read=True),
            _perm("payroll_record", can_read=True),
            _perm("settlement", can_read=True),
            _perm("device", can_read=True),
        ],
    )

    dashboard_service.repo.get_employee_summary.return_value = {
        "total_employees": 100,
        "active_employees": 95,
        "new_employees": 5,
    }
    dashboard_service.repo.get_attendance_summary.return_value = {
        "present_today": 80,
        "absent_today": 10,
        "late_arrivals": 5,
        "early_exits": 2,
        "on_leave_today": 3,
    }
    dashboard_service.repo.get_leave_summary.return_value = {"pending": 2}
    dashboard_service.repo.get_pending_approvals_summary.return_value = {"pending_approvals": 4}
    dashboard_service.repo.get_payroll_summary.return_value = {"status": "draft"}
    dashboard_service.repo.get_settlement_summary.return_value = {
        "active_loans_advances": 2,
        "closed_loans_advances": 1,
        "total_outstanding_loans_advances": Decimal("1000.00"),
        "total_outstanding_arrears": Decimal("500.00"),
    }
    dashboard_service.repo.get_hardware_dashboard.return_value = {
        "online_devices": 4,
        "offline_devices": 1,
    }
    dashboard_service.repo.get_notification_dashboard.return_value = {
        "unread_count": 3,
        "recent": [],
    }

    res = await dashboard_service.get_kpis(org_id=1, user=user)
    assert res.total_employees == 100
    assert res.present_today == 80
    assert res.pending_leaves == 2
    assert res.total_outstanding_loans_advances == Decimal("1000.00")
    assert res.total_outstanding_arrears == Decimal("500.00")


@pytest.mark.asyncio
async def test_get_statistics(dashboard_service, mock_cache) -> None:
    mock_get, mock_set = mock_cache
    user = _principal(
        is_super_admin=False,
        perms=[
            _perm("employee", can_read=True),
            _perm("attendance", can_read=True),
            _perm("leave_request", can_read=True),
            _perm("device", can_read=True),
        ],
    )

    dashboard_service.repo.get_employee_summary.return_value = {"total_employees": 100}
    dashboard_service.repo.get_employee_distribution.return_value = {
        "employment_status": [{"name": "terminated", "count": 2}]
    }
    dashboard_service.repo.get_attendance_summary.return_value = {
        "present_today": 80,
        "half_day_today": 5,
        "absent_today": 10,
        "on_leave_today": 3,
        "not_marked": 2,
        "late_arrivals": 0,
        "early_exits": 0,
    }
    dashboard_service.repo.get_leave_summary.return_value = {
        "approved": 8,
        "rejected": 2,
    }
    dashboard_service.repo.get_hardware_dashboard.return_value = {
        "online_devices": 4,
        "offline_devices": 1,
        "disabled_devices": 0,
        "maintenance_devices": 0,
    }

    res = await dashboard_service.get_statistics(org_id=1, user=user)
    assert res.employee_turnover_rate == 2.0
    assert res.attendance_rate_today == 85.0
    assert res.leave_approval_rate == 80.0
    assert res.device_uptime_rate == 80.0


# ===========================================================================
# 4. Individual Dashboard tests
# ===========================================================================


@pytest.mark.asyncio
async def test_get_employee_dashboard_success(dashboard_service, mock_cache) -> None:
    mock_get, mock_set = mock_cache
    user = _principal(is_super_admin=False, perms=[_perm("employee", can_read=True)])

    dashboard_service.repo.get_employee_summary.return_value = {
        "total_employees": 100,
        "active_employees": 95,
        "new_employees": 5,
    }
    dashboard_service.repo.get_employee_distribution.return_value = {
        "department": [{"name": "IT", "count": 95}]
    }

    res = await dashboard_service.get_employee_dashboard(org_id=1, user=user)
    assert res.total_employees == 100
    assert res.active_employees == 95
    assert res.inactive_employees == 5
    assert res.new_employees == 5
    assert res.distribution["department"][0].name == "IT"
    assert res.distribution["department"][0].count == 95


@pytest.mark.asyncio
async def test_get_employee_dashboard_unauthorized(dashboard_service) -> None:
    user = _principal(is_super_admin=False)
    with pytest.raises(AuthorizationException):
        await dashboard_service.get_employee_dashboard(org_id=1, user=user)


@pytest.mark.asyncio
async def test_get_attendance_dashboard_success(dashboard_service, mock_cache) -> None:
    mock_get, mock_set = mock_cache
    user = _principal(is_super_admin=False, perms=[_perm("attendance", can_read=True)])

    dashboard_service.repo.get_attendance_summary.return_value = {
        "present_today": 80,
        "absent_today": 10,
        "half_day_today": 2,
        "on_leave_today": 3,
        "late_arrivals": 5,
        "early_exits": 1,
        "not_marked": 4,
    }
    dashboard_service.repo.get_attendance_trend.return_value = [
        {"date": datetime.date(2026, 7, 9), "present": 85, "absent": 10, "late": 5}
    ]

    res = await dashboard_service.get_attendance_dashboard(org_id=1, user=user)
    assert res.present_today == 80
    assert len(res.trend) == 1
    assert res.trend[0].date == datetime.date(2026, 7, 9)


@pytest.mark.asyncio
async def test_get_attendance_dashboard_unauthorized(dashboard_service) -> None:
    user = _principal(is_super_admin=False)
    with pytest.raises(AuthorizationException):
        await dashboard_service.get_attendance_dashboard(org_id=1, user=user)


@pytest.mark.asyncio
async def test_get_leave_dashboard_success(dashboard_service, mock_cache) -> None:
    mock_get, mock_set = mock_cache
    user = _principal(is_super_admin=False, perms=[_perm("leave_request", can_read=True)])

    dashboard_service.repo.get_leave_summary.return_value = {
        "total_requests": 50,
        "pending": 10,
        "approved": 35,
        "rejected": 5,
    }
    dashboard_service.repo.get_leave_type_breakdown.return_value = [
        {"leave_type": "Casual Leave", "count": 15}
    ]

    res = await dashboard_service.get_leave_dashboard(org_id=1, user=user)
    assert res.total_requests == 50
    assert len(res.by_type) == 1
    assert res.by_type[0].leave_type == "Casual Leave"


@pytest.mark.asyncio
async def test_get_leave_dashboard_unauthorized(dashboard_service) -> None:
    user = _principal(is_super_admin=False)
    with pytest.raises(AuthorizationException):
        await dashboard_service.get_leave_dashboard(org_id=1, user=user)


@pytest.mark.asyncio
async def test_get_approval_dashboard_success(dashboard_service, mock_cache) -> None:
    mock_get, mock_set = mock_cache
    user = _principal(is_super_admin=False, perms=[_perm("approval", can_read=True)])

    dashboard_service.repo.get_pending_approvals_summary.return_value = {
        "pending_approvals": 5,
        "by_request_type": {"leave": 3, "attendance_regularization": 2},
    }
    dashboard_service.repo.get_recent_approvals.return_value = [
        {
            "id": 1,
            "request_type": "leave",
            "status": "approved",
            "requester_name": "John Doe",
            "submitted_at": _NOW,
        }
    ]

    res = await dashboard_service.get_approval_dashboard(org_id=1, user=user)
    assert res.pending_approvals == 5
    assert res.approved_recent == 1
    assert len(res.recent) == 1
    assert res.recent[0].requester_name == "John Doe"


@pytest.mark.asyncio
async def test_get_approval_dashboard_unauthorized(dashboard_service) -> None:
    user = _principal(is_super_admin=False)
    with pytest.raises(AuthorizationException):
        await dashboard_service.get_approval_dashboard(org_id=1, user=user)


@pytest.mark.asyncio
async def test_get_payroll_dashboard_success(dashboard_service, mock_cache) -> None:
    mock_get, mock_set = mock_cache
    user = _principal(is_super_admin=False, perms=[_perm("payroll_record", can_read=True)])

    dashboard_service.repo.get_payroll_summary.return_value = {
        "current_cycle_id": 1,
        "current_cycle_name": "July 2026",
        "is_finalized": False,
        "status": "processing",
        "finalized_amount": Decimal("150000.00"),
        "payment_status_breakdown": {"paid": 0, "unpaid": 95},
        "headcount": 95,
    }

    res = await dashboard_service.get_payroll_dashboard(org_id=1, user=user)
    assert res.current_cycle_id == 1
    assert res.finalized_amount == Decimal("150000.00")


@pytest.mark.asyncio
async def test_get_payroll_dashboard_unauthorized(dashboard_service) -> None:
    user = _principal(is_super_admin=False)
    with pytest.raises(AuthorizationException):
        await dashboard_service.get_payroll_dashboard(org_id=1, user=user)


@pytest.mark.asyncio
async def test_get_settlement_dashboard_success(dashboard_service, mock_cache) -> None:
    mock_get, mock_set = mock_cache
    user = _principal(is_super_admin=False, perms=[_perm("settlement", can_read=True)])

    dashboard_service.repo.get_settlement_summary.return_value = {
        "active_loans_advances": 5,
        "closed_loans_advances": 12,
        "total_outstanding_loans_advances": Decimal("25000.00"),
        "total_outstanding_arrears": Decimal("0.00"),
    }

    res = await dashboard_service.get_settlement_dashboard(org_id=1, user=user)
    assert res.active_loans_advances == 5
    assert res.total_outstanding_loans_advances == Decimal("25000.00")


@pytest.mark.asyncio
async def test_get_settlement_dashboard_unauthorized(dashboard_service) -> None:
    user = _principal(is_super_admin=False)
    with pytest.raises(AuthorizationException):
        await dashboard_service.get_settlement_dashboard(org_id=1, user=user)


@pytest.mark.asyncio
async def test_get_hardware_dashboard_success(dashboard_service, mock_cache) -> None:
    mock_get, mock_set = mock_cache
    user = _principal(is_super_admin=False, perms=[_perm("device", can_read=True)])

    dashboard_service.repo.get_hardware_dashboard.return_value = {
        "online_devices": 5,
        "offline_devices": 1,
        "disabled_devices": 0,
        "maintenance_devices": 0,
        "last_device_sync": _NOW,
    }

    res = await dashboard_service.get_hardware_dashboard(org_id=1, user=user)
    assert res.online_devices == 5
    assert res.last_device_sync == _NOW


@pytest.mark.asyncio
async def test_get_hardware_dashboard_unauthorized(dashboard_service) -> None:
    user = _principal(is_super_admin=False)
    with pytest.raises(AuthorizationException):
        await dashboard_service.get_hardware_dashboard(org_id=1, user=user)


@pytest.mark.asyncio
async def test_get_notification_dashboard(dashboard_service, mock_cache) -> None:
    mock_get, mock_set = mock_cache
    user = _principal(is_super_admin=False)

    dashboard_service.repo.get_notification_dashboard.return_value = {
        "unread_count": 5,
        "recent": [
            {
                "id": 1,
                "title": "Welcome Notification",
                "notification_type": "system",
                "priority": "normal",
                "created_at": _NOW,
            }
        ],
    }

    res = await dashboard_service.get_notification_dashboard(org_id=1, user=user)
    assert res.unread_count == 5
    assert len(res.recent) == 1
    assert res.recent[0].title == "Welcome Notification"


@pytest.mark.asyncio
async def test_get_recent_activity(dashboard_service) -> None:
    user = _principal(is_super_admin=False)
    dashboard_service.repo.get_recent_activities.return_value = [
        {"id": 1, "module": "employee", "title": "Profile Updated"}
    ]

    res = await dashboard_service.get_recent_activity(org_id=1, user=user)
    assert len(res) == 1
    assert res[0]["title"] == "Profile Updated"


# ===========================================================================
# 5. Chart Projections tests
# ===========================================================================


@pytest.mark.asyncio
async def test_get_attendance_trend_chart_success(dashboard_service, mock_cache) -> None:
    mock_get, mock_set = mock_cache
    user = _principal(is_super_admin=False, perms=[_perm("attendance", can_read=True)])

    dashboard_service.repo.get_attendance_trend.return_value = [
        {"date": datetime.date(2026, 7, 9), "present": 10, "absent": 1, "late": 2}
    ]

    res = await dashboard_service.get_attendance_trend_chart(org_id=1, user=user)
    assert res.labels == ["2026-07-09"]
    assert res.series[0].name == "Present"
    assert res.series[0].points == [10.0]


@pytest.mark.asyncio
async def test_get_attendance_trend_chart_unauthorized(dashboard_service) -> None:
    user = _principal(is_super_admin=False)
    with pytest.raises(AuthorizationException):
        await dashboard_service.get_attendance_trend_chart(org_id=1, user=user)


@pytest.mark.asyncio
async def test_get_employee_growth_chart_success(dashboard_service, mock_cache) -> None:
    mock_get, mock_set = mock_cache
    user = _principal(is_super_admin=False, perms=[_perm("employee", can_read=True)])

    dashboard_service.repo.get_employee_growth_chart.return_value = {
        "labels": ["2026-06", "2026-07"],
        "series": [{"name": "Active", "points": [50.0, 55.0]}],
    }

    res = await dashboard_service.get_employee_growth_chart(org_id=1, user=user)
    assert res.labels == ["2026-06", "2026-07"]
    assert res.series[0].points == [50.0, 55.0]


@pytest.mark.asyncio
async def test_get_employee_growth_chart_unauthorized(dashboard_service) -> None:
    user = _principal(is_super_admin=False)
    with pytest.raises(AuthorizationException):
        await dashboard_service.get_employee_growth_chart(org_id=1, user=user)


@pytest.mark.asyncio
async def test_get_leave_trend_chart_success(dashboard_service, mock_cache) -> None:
    mock_get, mock_set = mock_cache
    user = _principal(is_super_admin=False, perms=[_perm("leave_request", can_read=True)])

    dashboard_service.repo.get_leave_trend_chart.return_value = {
        "labels": ["2026-06", "2026-07"],
        "series": [{"name": "Pending", "points": [1.0, 2.0]}],
    }

    res = await dashboard_service.get_leave_trend_chart(org_id=1, user=user)
    assert res.labels == ["2026-06", "2026-07"]
    assert res.series[0].points == [1.0, 2.0]


@pytest.mark.asyncio
async def test_get_leave_trend_chart_unauthorized(dashboard_service) -> None:
    user = _principal(is_super_admin=False)
    with pytest.raises(AuthorizationException):
        await dashboard_service.get_leave_trend_chart(org_id=1, user=user)


@pytest.mark.asyncio
async def test_get_payroll_trend_chart_success(dashboard_service, mock_cache) -> None:
    mock_get, mock_set = mock_cache
    user = _principal(is_super_admin=False, perms=[_perm("payroll_record", can_read=True)])

    dashboard_service.repo.get_payroll_trend_chart.return_value = {
        "labels": ["June", "July"],
        "series": [{"name": "Cost", "points": [150000.0, 155000.0]}],
    }

    res = await dashboard_service.get_payroll_trend_chart(org_id=1, user=user)
    assert res.labels == ["June", "July"]
    assert res.series[0].points == [150000.0, 155000.0]


@pytest.mark.asyncio
async def test_get_payroll_trend_chart_unauthorized(dashboard_service) -> None:
    user = _principal(is_super_admin=False)
    with pytest.raises(AuthorizationException):
        await dashboard_service.get_payroll_trend_chart(org_id=1, user=user)


@pytest.mark.asyncio
async def test_get_dept_attendance_chart_success(dashboard_service, mock_cache) -> None:
    mock_get, mock_set = mock_cache
    user = _principal(is_super_admin=False, perms=[_perm("attendance", can_read=True)])

    dashboard_service.repo.get_department_attendance_chart.return_value = {
        "labels": ["IT", "HR"],
        "series": [{"name": "Present", "points": [95.0, 90.0]}],
    }

    res = await dashboard_service.get_dept_attendance_chart(org_id=1, user=user)
    assert res.labels == ["IT", "HR"]
    assert res.series[0].points == [95.0, 90.0]


@pytest.mark.asyncio
async def test_get_dept_attendance_chart_unauthorized(dashboard_service) -> None:
    user = _principal(is_super_admin=False)
    with pytest.raises(AuthorizationException):
        await dashboard_service.get_dept_attendance_chart(org_id=1, user=user)


@pytest.mark.asyncio
async def test_get_branch_attendance_chart_success(dashboard_service, mock_cache) -> None:
    mock_get, mock_set = mock_cache
    user = _principal(is_super_admin=False, perms=[_perm("attendance", can_read=True)])

    dashboard_service.repo.get_branch_attendance_chart.return_value = {
        "labels": ["HQ", "Branch A"],
        "series": [{"name": "Present", "points": [98.0, 92.0]}],
    }

    res = await dashboard_service.get_branch_attendance_chart(org_id=1, user=user)
    assert res.labels == ["HQ", "Branch A"]
    assert res.series[0].points == [98.0, 92.0]


@pytest.mark.asyncio
async def test_get_branch_attendance_chart_unauthorized(dashboard_service) -> None:
    user = _principal(is_super_admin=False)
    with pytest.raises(AuthorizationException):
        await dashboard_service.get_branch_attendance_chart(org_id=1, user=user)


# ===========================================================================
# 4. Additional Coverage (DI, Cache Hits, December logic, Large Period logic)
# ===========================================================================


@pytest.mark.asyncio
async def test_get_dashboard_service_di() -> None:
    session = AsyncMock()
    service = await get_dashboard_service(session)
    assert isinstance(service, DashboardService)


@pytest.mark.asyncio
async def test_get_summary_december(dashboard_service, mock_cache) -> None:
    mock_get, mock_set = mock_cache
    user = _principal(is_super_admin=True)
    december_date = datetime.date(2026, 12, 15)

    dashboard_service.repo.get_employee_summary.return_value = {
        "total_employees": 100,
        "active_employees": 95,
        "new_employees": 5,
    }
    dashboard_service.repo.get_attendance_summary.return_value = {
        "present_today": 80,
        "absent_today": 10,
        "late_arrivals": 5,
        "early_exits": 2,
        "on_leave_today": 3,
    }
    dashboard_service.repo.get_leave_summary.return_value = {
        "total_requests": 10,
        "pending": 2,
    }
    dashboard_service.repo.get_pending_approvals_summary.return_value = {
        "pending_approvals": 4,
    }
    dashboard_service.repo.get_payroll_summary.return_value = {
        "status": "draft",
    }
    dashboard_service.repo.get_hardware_dashboard.return_value = {
        "online_devices": 4,
        "offline_devices": 1,
    }
    dashboard_service.repo.get_notification_dashboard.return_value = {
        "unread_count": 3,
        "recent": [],
    }

    res = await dashboard_service.get_summary(org_id=1, user=user, target_date=december_date)
    assert res.employees.total_employees == 100
    # Verify leave date_to calculation for December
    dashboard_service.repo.get_leave_summary.assert_called_with(
        1, None, None, datetime.date(2026, 12, 1), datetime.date(2026, 12, 31)
    )


@pytest.mark.asyncio
async def test_get_kpis_december(dashboard_service, mock_cache) -> None:
    mock_get, mock_set = mock_cache
    user = _principal(is_super_admin=True)
    december_date = datetime.date(2026, 12, 15)

    dashboard_service.repo.get_employee_summary.return_value = {
        "total_employees": 0,
        "active_employees": 0,
        "new_employees": 0,
    }
    dashboard_service.repo.get_attendance_summary.return_value = {
        "present_today": 0,
        "absent_today": 0,
        "late_arrivals": 0,
        "early_exits": 0,
        "on_leave_today": 0,
    }
    dashboard_service.repo.get_leave_summary.return_value = {"total_requests": 0, "pending": 0}
    dashboard_service.repo.get_pending_approvals_summary.return_value = {"pending_approvals": 0}
    dashboard_service.repo.get_payroll_summary.return_value = {"status": "draft"}
    dashboard_service.repo.get_settlement_summary.return_value = {
        "total_outstanding_loans_advances": Decimal(0),
        "total_outstanding_arrears": Decimal(0),
    }
    dashboard_service.repo.get_hardware_dashboard.return_value = {
        "online_devices": 0,
        "offline_devices": 0,
    }
    dashboard_service.repo.get_notification_dashboard.return_value = {"unread_count": 0}

    await dashboard_service.get_kpis(org_id=1, user=user, target_date=december_date)
    dashboard_service.repo.get_leave_summary.assert_called_with(
        1, None, None, datetime.date(2026, 12, 1), datetime.date(2026, 12, 31)
    )


@pytest.mark.asyncio
async def test_get_statistics_december(dashboard_service, mock_cache) -> None:
    mock_get, mock_set = mock_cache
    user = _principal(is_super_admin=True)
    december_date = datetime.date(2026, 12, 15)

    dashboard_service.repo.get_employee_summary.return_value = {
        "total_employees": 0,
        "active_employees": 0,
        "new_employees": 0,
    }
    dashboard_service.repo.get_employee_distribution.return_value = {
        "employment_status": []
    }
    dashboard_service.repo.get_attendance_summary.return_value = {
        "present_today": 0,
        "absent_today": 0,
        "late_arrivals": 0,
        "early_exits": 0,
        "on_leave_today": 0,
    }
    dashboard_service.repo.get_leave_summary.return_value = {
        "total_requests": 0,
        "pending": 0,
        "approved": 0,
        "rejected": 0,
    }
    dashboard_service.repo.get_hardware_dashboard.return_value = {
        "online_devices": 0,
        "offline_devices": 0,
    }

    await dashboard_service.get_statistics(org_id=1, user=user, target_date=december_date)
    dashboard_service.repo.get_leave_summary.assert_called_with(
        1, None, None, datetime.date(2026, 12, 1), datetime.date(2026, 12, 31)
    )


@pytest.mark.asyncio
async def test_get_leave_dashboard_december(dashboard_service, mock_cache) -> None:
    mock_get, mock_set = mock_cache
    user = _principal(is_super_admin=True)
    december_date = datetime.date(2026, 12, 15)

    dashboard_service.repo.get_leave_summary.return_value = {
        "total_requests": 0,
        "pending": 0,
        "approved": 0,
        "rejected": 0,
    }
    dashboard_service.repo.get_leave_type_breakdown.return_value = []

    await dashboard_service.get_leave_dashboard(org_id=1, user=user, target_date=december_date)
    dashboard_service.repo.get_leave_summary.assert_called_with(
        1, None, None, datetime.date(2026, 12, 1), datetime.date(2026, 12, 31)
    )


@pytest.mark.asyncio
async def test_growth_and_leave_trends_large_period(dashboard_service, mock_cache) -> None:
    mock_get, mock_set = mock_cache
    user = _principal(is_super_admin=True)

    dashboard_service.repo.get_employee_growth_chart.return_value = {"labels": [], "series": []}
    dashboard_service.repo.get_leave_trend_chart.return_value = {"labels": [], "series": []}

    # Pass months=13 to cover the while month <= 0 loop
    await dashboard_service.get_employee_growth_chart(org_id=1, user=user, months=13)
    await dashboard_service.get_leave_trend_chart(org_id=1, user=user, months=13)
    assert dashboard_service.repo.get_employee_growth_chart.called
    assert dashboard_service.repo.get_leave_trend_chart.called


@pytest.mark.asyncio
async def test_all_cache_hits(dashboard_service, mock_cache) -> None:
    mock_get, mock_set = mock_cache
    user = _principal(is_super_admin=True)

    # 1. KPIs cache hit
    mock_get.return_value = {
        "total_employees": 50,
        "active_employees": 45,
        "new_employees": 5,
        "present_today": 40,
        "absent_today": 5,
        "late_arrivals": 2,
        "early_exits": 1,
        "on_leave_today": 3,
        "pending_leaves": 4,
        "pending_approvals": 2,
        "current_payroll_status": "finalized",
        "total_outstanding_loans_advances": "1000.00",
        "total_outstanding_arrears": "50.0",
        "online_devices": 3,
        "offline_devices": 1,
        "unread_notifications": 10,
        "generated_at": "2026-07-10T10:00:00Z",
    }
    res_kpis = await dashboard_service.get_kpis(org_id=1, user=user)
    assert res_kpis.total_employees == 50

    # 2. Statistics cache hit
    mock_get.return_value = {
        "employee_turnover_rate": 1.2,
        "attendance_rate_today": 90.0,
        "leave_approval_rate": 80.0,
        "device_uptime_rate": 75.0,
        "generated_at": "2026-07-10T10:00:00Z",
    }
    res_stats = await dashboard_service.get_statistics(org_id=1, user=user)
    assert res_stats.employee_turnover_rate == 1.2

    # 3. Employee Dashboard cache hit
    mock_get.return_value = {
        "total_employees": 50,
        "active_employees": 45,
        "inactive_employees": 5,
        "new_employees": 5,
        "distribution": {},
        "generated_at": "2026-07-10T10:00:00Z",
    }
    res_emp = await dashboard_service.get_employee_dashboard(org_id=1, user=user)
    assert res_emp.total_employees == 50

    # 4. Attendance Dashboard cache hit
    mock_get.return_value = {
        "present_today": 40,
        "absent_today": 5,
        "half_day_today": 2,
        "on_leave_today": 3,
        "late_arrivals": 2,
        "early_exits": 1,
        "not_marked": 0,
        "trend": [],
        "generated_at": "2026-07-10T10:00:00Z",
    }
    res_att = await dashboard_service.get_attendance_dashboard(org_id=1, user=user)
    assert res_att.present_today == 40

    # 5. Leave Dashboard cache hit
    mock_get.return_value = {
        "total_requests": 10,
        "pending": 4,
        "approved": 4,
        "rejected": 2,
        "by_type": [],
        "generated_at": "2026-07-10T10:00:00Z",
    }
    res_leave = await dashboard_service.get_leave_dashboard(org_id=1, user=user)
    assert res_leave.total_requests == 10

    # 6. Approval Dashboard cache hit
    mock_get.return_value = {
        "pending_approvals": 2,
        "by_request_type": {},
        "approved_recent": 10,
        "rejected_recent": 2,
        "recent": [],
        "generated_at": "2026-07-10T10:00:00Z",
    }
    res_app = await dashboard_service.get_approval_dashboard(org_id=1, user=user)
    assert res_app.pending_approvals == 2

    # 7. Payroll Dashboard cache hit
    mock_get.return_value = {
        "current_cycle_id": 1,
        "current_cycle_name": "Cycle",
        "is_finalized": True,
        "status": "finalized",
        "finalized_amount": "50000.00",
        "payment_status_breakdown": {},
        "headcount": 50,
        "generated_at": "2026-07-10T10:00:00Z",
    }
    res_pay = await dashboard_service.get_payroll_dashboard(org_id=1, user=user)
    assert res_pay.headcount == 50

    # 8. Settlement Dashboard cache hit
    mock_get.return_value = {
        "active_loans_advances": 3,
        "closed_loans_advances": 5,
        "total_outstanding_loans_advances": "2000.00",
        "total_outstanding_arrears": "100.0",
        "generated_at": "2026-07-10T10:00:00Z",
    }
    res_settle = await dashboard_service.get_settlement_dashboard(org_id=1, user=user)
    assert res_settle.active_loans_advances == 3

    # 9. Hardware Dashboard cache hit
    mock_get.return_value = {
        "online_devices": 3,
        "offline_devices": 1,
        "disabled_devices": 0,
        "maintenance_devices": 0,
        "last_device_sync": None,
        "generated_at": "2026-07-10T10:00:00Z",
    }
    res_dev = await dashboard_service.get_hardware_dashboard(org_id=1, user=user)
    assert res_dev.online_devices == 3

    # 10. Notification Dashboard cache hit
    mock_get.return_value = {
        "unread_count": 10,
        "recent": [],
        "generated_at": "2026-07-10T10:00:00Z",
    }
    res_notif = await dashboard_service.get_notification_dashboard(org_id=1, user=user, limit=5)
    assert res_notif.unread_count == 10

    # 11. Charts cache hits
    mock_get.return_value = {
        "labels": ["A"],
        "series": [{"name": "S", "points": [1.0]}],
        "generated_at": "2026-07-10T10:00:00Z",
    }
    res_chart1 = await dashboard_service.get_attendance_trend_chart(org_id=1, user=user, days=30)
    assert res_chart1.labels == ["A"]

    res_chart2 = await dashboard_service.get_employee_growth_chart(org_id=1, user=user, months=6)
    assert res_chart2.labels == ["A"]

    res_chart3 = await dashboard_service.get_leave_trend_chart(org_id=1, user=user, months=6)
    assert res_chart3.labels == ["A"]

    res_chart4 = await dashboard_service.get_payroll_trend_chart(org_id=1, user=user, limit=6)
    assert res_chart4.labels == ["A"]

    res_chart5 = await dashboard_service.get_dept_attendance_chart(org_id=1, user=user)
    assert res_chart5.labels == ["A"]

    res_chart6 = await dashboard_service.get_branch_attendance_chart(org_id=1, user=user)
    assert res_chart6.labels == ["A"]
