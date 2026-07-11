"""Integration tests for the Dashboard Management router."""

from __future__ import annotations

import datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.core.dependencies.auth import assert_session_live
from app.modules.dashboard.dependencies import get_dashboard_service
from app.modules.dashboard.schemas import (
    ApprovalDashboardResponse,
    AttendanceDashboardResponse,
    ChartResponseSchema,
    DashboardKPIsResponse,
    DashboardStatisticsResponse,
    DashboardSummaryResponse,
    EmployeeDashboardResponse,
    HardwareDashboardResponse,
    LeaveDashboardResponse,
    NotificationDashboardResponse,
    PayrollDashboardResponse,
    SettlementDashboardResponse,
    WidgetsMetadataResponse,
)
from tests.conftest import API_PREFIX

_NOW = datetime.datetime(2026, 7, 10, 10, 0, 0, tzinfo=datetime.UTC)


@pytest.fixture
def mock_dashboard_service() -> AsyncMock:
    """Mock stand-in for DashboardService."""
    mock = AsyncMock()
    # get_widgets_metadata is a synchronous service method; mock it as MagicMock
    mock.get_widgets_metadata = MagicMock()
    return mock


@pytest_asyncio.fixture
async def dashboard_client(app, mock_dashboard_service: AsyncMock):
    """An async HTTP client bound to the app with the dashboard service mocked.

    Dynamically registers the dashboard router if it is not already mounted.
    """
    from app.modules.dashboard.router import router as dashboard_router

    prefix = "/api/v1/dashboard"
    router_included = any(getattr(route, "path", "").startswith(prefix) for route in app.routes)
    if not router_included:
        app.include_router(dashboard_router, prefix="/api/v1")

    # The auth dependency re-validates the session against the DB on every request;

    # router tests exercise the HTTP layer without a database, so stub that check.

    app.dependency_overrides[assert_session_live] = lambda: None

    app.dependency_overrides[get_dashboard_service] = lambda: mock_dashboard_service
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as http_client:
        yield http_client
    app.dependency_overrides.clear()


# =========================================================================
# 1. Main Summaries & Statistics
# =========================================================================


@pytest.mark.asyncio
async def test_get_summary(
    dashboard_client: AsyncClient,
    mock_dashboard_service: AsyncMock,
    super_admin_headers: dict[str, str],
) -> None:
    mock_dashboard_service.get_summary.return_value = DashboardSummaryResponse()
    resp = await dashboard_client.get(
        f"{API_PREFIX}/dashboard/summary", headers=super_admin_headers
    )
    assert resp.status_code == 200
    assert "data" in resp.json()
    mock_dashboard_service.get_summary.assert_called_once()


@pytest.mark.asyncio
async def test_get_widgets(
    dashboard_client: AsyncClient,
    mock_dashboard_service: AsyncMock,
    super_admin_headers: dict[str, str],
) -> None:
    mock_dashboard_service.get_widgets_metadata.return_value = WidgetsMetadataResponse(widgets=[])
    resp = await dashboard_client.get(
        f"{API_PREFIX}/dashboard/widgets", headers=super_admin_headers
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["widgets"] == []
    mock_dashboard_service.get_widgets_metadata.assert_called_once()


@pytest.mark.asyncio
async def test_get_kpis(
    dashboard_client: AsyncClient,
    mock_dashboard_service: AsyncMock,
    super_admin_headers: dict[str, str],
) -> None:
    mock_dashboard_service.get_kpis.return_value = DashboardKPIsResponse(
        total_employees=10,
        active_employees=9,
        new_employees=1,
        present_today=8,
        absent_today=1,
        late_arrivals=0,
        early_exits=0,
        on_leave_today=1,
        pending_leaves=2,
        pending_approvals=3,
        current_payroll_status="draft",
        total_outstanding_loans_advances=Decimal("100.00"),
        total_outstanding_arrears=Decimal("50.00"),
        online_devices=1,
        offline_devices=0,
        unread_notifications=5,
    )
    resp = await dashboard_client.get(f"{API_PREFIX}/dashboard/kpis", headers=super_admin_headers)
    assert resp.status_code == 200
    assert resp.json()["data"]["total_employees"] == 10
    mock_dashboard_service.get_kpis.assert_called_once()


@pytest.mark.asyncio
async def test_get_statistics(
    dashboard_client: AsyncClient,
    mock_dashboard_service: AsyncMock,
    super_admin_headers: dict[str, str],
) -> None:
    mock_dashboard_service.get_statistics.return_value = DashboardStatisticsResponse(
        employee_turnover_rate=1.5,
        attendance_rate_today=95.0,
        leave_approval_rate=80.0,
        device_uptime_rate=100.0,
    )
    resp = await dashboard_client.get(
        f"{API_PREFIX}/dashboard/statistics", headers=super_admin_headers
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["employee_turnover_rate"] == 1.5
    mock_dashboard_service.get_statistics.assert_called_once()


# =========================================================================
# 2. Individual Module Dashboards
# =========================================================================


@pytest.mark.asyncio
async def test_get_employees_dashboard(
    dashboard_client: AsyncClient,
    mock_dashboard_service: AsyncMock,
    super_admin_headers: dict[str, str],
) -> None:
    mock_dashboard_service.get_employee_dashboard.return_value = EmployeeDashboardResponse(
        total_employees=10,
        active_employees=9,
        inactive_employees=1,
        new_employees=1,
        distribution={},
    )
    resp = await dashboard_client.get(
        f"{API_PREFIX}/dashboard/employees", headers=super_admin_headers
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["total_employees"] == 10
    mock_dashboard_service.get_employee_dashboard.assert_called_once()


@pytest.mark.asyncio
async def test_get_attendance_dashboard(
    dashboard_client: AsyncClient,
    mock_dashboard_service: AsyncMock,
    super_admin_headers: dict[str, str],
) -> None:
    mock_dashboard_service.get_attendance_dashboard.return_value = AttendanceDashboardResponse(
        present_today=8,
        absent_today=1,
        half_day_today=0,
        on_leave_today=1,
        late_arrivals=0,
        early_exits=0,
        not_marked=0,
        trend=[],
    )
    resp = await dashboard_client.get(
        f"{API_PREFIX}/dashboard/attendance", headers=super_admin_headers
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["present_today"] == 8
    mock_dashboard_service.get_attendance_dashboard.assert_called_once()


@pytest.mark.asyncio
async def test_get_leave_dashboard(
    dashboard_client: AsyncClient,
    mock_dashboard_service: AsyncMock,
    super_admin_headers: dict[str, str],
) -> None:
    mock_dashboard_service.get_leave_dashboard.return_value = LeaveDashboardResponse(
        total_requests=5,
        pending=2,
        approved=2,
        rejected=1,
        by_type=[],
    )
    resp = await dashboard_client.get(f"{API_PREFIX}/dashboard/leave", headers=super_admin_headers)
    assert resp.status_code == 200
    assert resp.json()["data"]["total_requests"] == 5
    mock_dashboard_service.get_leave_dashboard.assert_called_once()


@pytest.mark.asyncio
async def test_get_approval_dashboard(
    dashboard_client: AsyncClient,
    mock_dashboard_service: AsyncMock,
    super_admin_headers: dict[str, str],
) -> None:
    mock_dashboard_service.get_approval_dashboard.return_value = ApprovalDashboardResponse(
        pending_approvals=3,
        by_request_type={},
        approved_recent=5,
        rejected_recent=1,
        recent=[],
    )
    resp = await dashboard_client.get(
        f"{API_PREFIX}/dashboard/approvals", headers=super_admin_headers
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["pending_approvals"] == 3
    mock_dashboard_service.get_approval_dashboard.assert_called_once()


@pytest.mark.asyncio
async def test_get_payroll_dashboard(
    dashboard_client: AsyncClient,
    mock_dashboard_service: AsyncMock,
    super_admin_headers: dict[str, str],
) -> None:
    mock_dashboard_service.get_payroll_dashboard.return_value = PayrollDashboardResponse(
        current_cycle_id=1,
        current_cycle_name="July 2026",
        is_finalized=False,
        status="draft",
        finalized_amount=Decimal("15000.00"),
        payment_status_breakdown={},
        headcount=10,
    )
    resp = await dashboard_client.get(
        f"{API_PREFIX}/dashboard/payroll", headers=super_admin_headers
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["headcount"] == 10
    mock_dashboard_service.get_payroll_dashboard.assert_called_once()


@pytest.mark.asyncio
async def test_get_settlement_dashboard(
    dashboard_client: AsyncClient,
    mock_dashboard_service: AsyncMock,
    super_admin_headers: dict[str, str],
) -> None:
    mock_dashboard_service.get_settlement_dashboard.return_value = SettlementDashboardResponse(
        active_loans_advances=1,
        closed_loans_advances=2,
        total_outstanding_loans_advances=Decimal("2000.00"),
        total_outstanding_arrears=Decimal("500.00"),
    )
    resp = await dashboard_client.get(
        f"{API_PREFIX}/dashboard/settlements", headers=super_admin_headers
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["active_loans_advances"] == 1
    mock_dashboard_service.get_settlement_dashboard.assert_called_once()


@pytest.mark.asyncio
async def test_get_hardware_dashboard(
    dashboard_client: AsyncClient,
    mock_dashboard_service: AsyncMock,
    super_admin_headers: dict[str, str],
) -> None:
    mock_dashboard_service.get_hardware_dashboard.return_value = HardwareDashboardResponse(
        online_devices=2,
        offline_devices=0,
        disabled_devices=0,
        maintenance_devices=0,
    )
    resp = await dashboard_client.get(
        f"{API_PREFIX}/dashboard/devices", headers=super_admin_headers
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["online_devices"] == 2
    mock_dashboard_service.get_hardware_dashboard.assert_called_once()


@pytest.mark.asyncio
async def test_get_notification_dashboard(
    dashboard_client: AsyncClient,
    mock_dashboard_service: AsyncMock,
    super_admin_headers: dict[str, str],
) -> None:
    mock_dashboard_service.get_notification_dashboard.return_value = NotificationDashboardResponse(
        unread_count=5,
        recent=[],
    )
    resp = await dashboard_client.get(
        f"{API_PREFIX}/dashboard/notifications?limit=10", headers=super_admin_headers
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["unread_count"] == 5
    mock_dashboard_service.get_notification_dashboard.assert_called_once()


@pytest.mark.asyncio
async def test_get_recent_activity(
    dashboard_client: AsyncClient,
    mock_dashboard_service: AsyncMock,
    super_admin_headers: dict[str, str],
) -> None:
    mock_dashboard_service.get_recent_activity.return_value = [{"activity": "login"}]
    resp = await dashboard_client.get(
        f"{API_PREFIX}/dashboard/recent-activity?limit=5", headers=super_admin_headers
    )
    assert resp.status_code == 200
    assert len(resp.json()["data"]) == 1
    mock_dashboard_service.get_recent_activity.assert_called_once()


# =========================================================================
# 3. Chart Projections
# =========================================================================


@pytest.mark.asyncio
async def test_charts_attendance_trend(
    dashboard_client: AsyncClient,
    mock_dashboard_service: AsyncMock,
    super_admin_headers: dict[str, str],
) -> None:
    mock_dashboard_service.get_attendance_trend_chart.return_value = ChartResponseSchema(
        labels=[], series=[]
    )
    resp = await dashboard_client.get(
        f"{API_PREFIX}/dashboard/charts/attendance-trend?days=15", headers=super_admin_headers
    )
    assert resp.status_code == 200
    mock_dashboard_service.get_attendance_trend_chart.assert_called_once()


@pytest.mark.asyncio
async def test_charts_employee_growth(
    dashboard_client: AsyncClient,
    mock_dashboard_service: AsyncMock,
    super_admin_headers: dict[str, str],
) -> None:
    mock_dashboard_service.get_employee_growth_chart.return_value = ChartResponseSchema(
        labels=[], series=[]
    )
    resp = await dashboard_client.get(
        f"{API_PREFIX}/dashboard/charts/employee-growth?months=12", headers=super_admin_headers
    )
    assert resp.status_code == 200
    mock_dashboard_service.get_employee_growth_chart.assert_called_once()


@pytest.mark.asyncio
async def test_charts_leave_trend(
    dashboard_client: AsyncClient,
    mock_dashboard_service: AsyncMock,
    super_admin_headers: dict[str, str],
) -> None:
    mock_dashboard_service.get_leave_trend_chart.return_value = ChartResponseSchema(
        labels=[], series=[]
    )
    resp = await dashboard_client.get(
        f"{API_PREFIX}/dashboard/charts/leave-trend?months=3", headers=super_admin_headers
    )
    assert resp.status_code == 200
    mock_dashboard_service.get_leave_trend_chart.assert_called_once()


@pytest.mark.asyncio
async def test_charts_payroll_trend(
    dashboard_client: AsyncClient,
    mock_dashboard_service: AsyncMock,
    super_admin_headers: dict[str, str],
) -> None:
    mock_dashboard_service.get_payroll_trend_chart.return_value = ChartResponseSchema(
        labels=[], series=[]
    )
    resp = await dashboard_client.get(
        f"{API_PREFIX}/dashboard/charts/payroll-trend?limit=10", headers=super_admin_headers
    )
    assert resp.status_code == 200
    mock_dashboard_service.get_payroll_trend_chart.assert_called_once()


@pytest.mark.asyncio
async def test_charts_department_attendance(
    dashboard_client: AsyncClient,
    mock_dashboard_service: AsyncMock,
    super_admin_headers: dict[str, str],
) -> None:
    mock_dashboard_service.get_dept_attendance_chart.return_value = ChartResponseSchema(
        labels=[], series=[]
    )
    resp = await dashboard_client.get(
        f"{API_PREFIX}/dashboard/charts/department-attendance", headers=super_admin_headers
    )
    assert resp.status_code == 200
    mock_dashboard_service.get_dept_attendance_chart.assert_called_once()


@pytest.mark.asyncio
async def test_charts_branch_attendance(
    dashboard_client: AsyncClient,
    mock_dashboard_service: AsyncMock,
    super_admin_headers: dict[str, str],
) -> None:
    mock_dashboard_service.get_branch_attendance_chart.return_value = ChartResponseSchema(
        labels=[], series=[]
    )
    resp = await dashboard_client.get(
        f"{API_PREFIX}/dashboard/charts/branch-attendance", headers=super_admin_headers
    )
    assert resp.status_code == 200
    mock_dashboard_service.get_branch_attendance_chart.assert_called_once()


# =========================================================================
# 4. Error Cases, Validation & Authorization
# =========================================================================


@pytest.mark.asyncio
async def test_unresolved_tenant_context(
    dashboard_client: AsyncClient,
    make_access_token,
) -> None:
    # Generate token with org_id = None and super admin to bypass permission gating
    token = make_access_token(is_super_admin=True, org_id=None)
    headers = {"Authorization": f"Bearer {token}"}
    resp = await dashboard_client.get(f"{API_PREFIX}/dashboard/summary", headers=headers)
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "TENANT_UNRESOLVED"
    assert "Organization context is required." in resp.json()["error"]["message"]


@pytest.mark.asyncio
async def test_query_parameter_validation_error(
    dashboard_client: AsyncClient,
    super_admin_headers: dict[str, str],
) -> None:
    # Passing negative limit
    resp1 = await dashboard_client.get(
        f"{API_PREFIX}/dashboard/notifications?limit=-5", headers=super_admin_headers
    )
    assert resp1.status_code == 422

    # Passing string instead of int
    resp2 = await dashboard_client.get(
        f"{API_PREFIX}/dashboard/charts/attendance-trend?days=abc", headers=super_admin_headers
    )
    assert resp2.status_code == 422


@pytest.mark.asyncio
async def test_unauthorized_missing_token(
    dashboard_client: AsyncClient,
) -> None:
    resp = await dashboard_client.get(f"{API_PREFIX}/dashboard/summary")
    assert resp.status_code == 401
