"""Unit tests for the DashboardRepository layer."""

from __future__ import annotations

import datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.modules.dashboard.repository import DashboardRepository


def _mock_scalar(value) -> MagicMock:
    res = MagicMock()
    res.scalar.return_value = value
    res.scalar_one_or_none.return_value = value
    return res


def _mock_result_all(rows: list) -> MagicMock:
    res = MagicMock()
    res.all.return_value = rows
    res.first.return_value = rows[0] if rows else None
    return res


@pytest.mark.asyncio
async def test_get_employee_summary() -> None:
    session = AsyncMock()
    # 3 execute calls in total: total, active, new hires
    session.execute.side_effect = [
        _mock_scalar(100),  # total
        _mock_scalar(90),  # active
        _mock_scalar(5),  # new
    ]

    repo = DashboardRepository(session)
    res = await repo.get_employee_summary(
        org_id=1,
        branch_ids=[10, 20],
        dept_ids=[30],
        date_from=datetime.date(2026, 7, 1),
        date_to=datetime.date(2026, 7, 10),
    )

    assert res == {
        "total_employees": 100,
        "active_employees": 90,
        "new_employees": 5,
    }
    assert session.execute.call_count == 3


@pytest.mark.asyncio
async def test_get_employee_distribution() -> None:
    session = AsyncMock()
    # 4 execute calls: department, branch, designation, status
    session.execute.side_effect = [
        _mock_result_all([("HR", 10), ("IT", 90)]),
        _mock_result_all([("HQ", 60), ("Branch A", 40)]),
        _mock_result_all([("Developer", 80), ("Manager", 20)]),
        _mock_result_all([("active", 90), ("probation", 10)]),
    ]

    repo = DashboardRepository(session)
    res = await repo.get_employee_distribution(org_id=1, branch_ids=[10], dept_ids=[20])

    assert res == {
        "department": [{"name": "HR", "count": 10}, {"name": "IT", "count": 90}],
        "branch": [{"name": "HQ", "count": 60}, {"name": "Branch A", "count": 40}],
        "designation": [{"name": "Developer", "count": 80}, {"name": "Manager", "count": 20}],
        "employment_status": [{"name": "active", "count": 90}, {"name": "probation", "count": 10}],
    }
    assert session.execute.call_count == 4


@pytest.mark.asyncio
async def test_get_attendance_summary() -> None:
    session = AsyncMock()
    # 1 execute call returning list of (status, late_minutes, early_leaving_minutes)
    session.execute.return_value = _mock_result_all(
        [
            ("present", 15, 0),
            ("absent", None, None),
            ("half_day", 0, 10),
            ("on_leave", None, None),
            (None, None, None),
        ]
    )

    repo = DashboardRepository(session)
    res = await repo.get_attendance_summary(
        org_id=1, target_date=datetime.date(2026, 7, 10), branch_ids=[10], dept_ids=[20]
    )

    assert res == {
        "present_today": 1,
        "absent_today": 1,
        "half_day_today": 1,
        "on_leave_today": 1,
        "late_arrivals": 1,
        "early_exits": 1,
        "not_marked": 1,
    }


@pytest.mark.asyncio
async def test_get_attendance_trend() -> None:
    session = AsyncMock()
    # 1 execute call returning (date, present_count, absent_count, late_count)
    session.execute.return_value = _mock_result_all(
        [
            (datetime.date(2026, 7, 1), 50, 5, 2),
            (datetime.date(2026, 7, 2), 52, 3, 1),
        ]
    )

    repo = DashboardRepository(session)
    res = await repo.get_attendance_trend(
        org_id=1,
        date_from=datetime.date(2026, 7, 1),
        date_to=datetime.date(2026, 7, 2),
        branch_ids=[10],
    )

    assert res == [
        {"date": datetime.date(2026, 7, 1), "present": 50, "absent": 5, "late": 2},
        {"date": datetime.date(2026, 7, 2), "present": 52, "absent": 3, "late": 1},
    ]


@pytest.mark.asyncio
async def test_get_leave_summary() -> None:
    session = AsyncMock()
    # 1 execute call returning (status, count)
    session.execute.return_value = _mock_result_all(
        [
            ("pending", 3),
            ("approved", 10),
            ("rejected", 2),
        ]
    )

    repo = DashboardRepository(session)
    res = await repo.get_leave_summary(
        org_id=1,
        branch_ids=[10],
        dept_ids=[20],
        date_from=datetime.date(2026, 7, 1),
        date_to=datetime.date(2026, 7, 10),
    )

    assert res == {
        "total_requests": 15,
        "pending": 3,
        "approved": 10,
        "rejected": 2,
    }


@pytest.mark.asyncio
async def test_get_leave_type_breakdown() -> None:
    session = AsyncMock()
    session.execute.return_value = _mock_result_all(
        [
            ("Casual Leave", 8),
            ("Sick Leave", 4),
        ]
    )

    repo = DashboardRepository(session)
    res = await repo.get_leave_type_breakdown(
        org_id=1,
        date_from=datetime.date(2026, 7, 1),
        date_to=datetime.date(2026, 7, 10),
    )

    assert res == [
        {"leave_type": "Casual Leave", "count": 8},
        {"leave_type": "Sick Leave", "count": 4},
    ]


@pytest.mark.asyncio
async def test_get_pending_approvals_summary() -> None:
    session = MagicMock()
    session.execute = AsyncMock()
    session.execute.return_value = _mock_result_all(
        [
            ("attendance", 2),
            ("leave", 4),
        ]
    )

    repo = DashboardRepository(session)
    res = await repo.get_pending_approvals_summary(org_id=1)

    assert res == {
        "pending_approvals": 6,
        "by_request_type": {
            "attendance": 2,
            "leave": 4,
            "login_reset": 0,
        },
    }


@pytest.mark.asyncio
async def test_get_recent_approvals() -> None:
    session = AsyncMock()
    session.execute.return_value = _mock_result_all(
        [
            (123, "leave", "approved", "Jane Doe", datetime.datetime(2026, 7, 10, 9, 30)),
        ]
    )

    repo = DashboardRepository(session)
    res = await repo.get_recent_approvals(org_id=1, limit=5)

    assert res == [
        {
            "id": 123,
            "request_type": "leave",
            "status": "approved",
            "requester_name": "Jane Doe",
            "submitted_at": datetime.datetime(2026, 7, 10, 9, 30),
        }
    ]


@pytest.mark.asyncio
async def test_get_payroll_summary_empty() -> None:
    session = AsyncMock()
    session.execute.return_value = _mock_result_all([])

    repo = DashboardRepository(session)
    res = await repo.get_payroll_summary(org_id=1)

    assert res["current_cycle_id"] is None
    assert res["status"] == "draft"


@pytest.mark.asyncio
async def test_get_payroll_summary_finalized() -> None:
    session = AsyncMock()
    # First: cycle query
    # Second: finalized run query
    # Third: computed row headcount count query
    cycle_row = (10, datetime.date(2026, 7, 31), True, 20)

    from unittest.mock import MagicMock

    run_mock = MagicMock()
    run_mock.id = 5
    run_mock.finalized_amount = Decimal("500000.00")
    run_mock.payment_status = "paid"

    session.execute.side_effect = [
        _mock_result_all([cycle_row]),
        _mock_scalar(run_mock),
        _mock_scalar(95),
    ]

    repo = DashboardRepository(session)
    res = await repo.get_payroll_summary(org_id=1)

    assert res == {
        "current_cycle_id": 10,
        "current_cycle_name": "July 2026",
        "is_finalized": True,
        "status": "finalized",
        "finalized_amount": Decimal("500000.00"),
        "payment_status_breakdown": {"paid": 95, "unpaid": 0},
        "headcount": 95,
    }


@pytest.mark.asyncio
async def test_get_payroll_summary_processing() -> None:
    session = AsyncMock()
    cycle_row = (10, datetime.date(2026, 7, 31), False, 20)

    session.execute.side_effect = [
        _mock_result_all([cycle_row]),
        _mock_scalar(None),
        _mock_scalar(88),
    ]

    repo = DashboardRepository(session)
    res = await repo.get_payroll_summary(org_id=1)

    assert res == {
        "current_cycle_id": 10,
        "current_cycle_name": "July 2026",
        "is_finalized": False,
        "status": "processing",
        "finalized_amount": Decimal("0.00"),
        "payment_status_breakdown": {"paid": 0, "unpaid": 88},
        "headcount": 88,
    }


@pytest.mark.asyncio
async def test_get_settlement_summary() -> None:
    session = AsyncMock()
    session.execute.side_effect = [
        _mock_scalar(5),  # active count
        _mock_scalar(3),  # closed count
        _mock_scalar(Decimal("12500.00")),  # outstanding loans
        _mock_scalar(Decimal("3200.00")),  # outstanding arrears
    ]

    repo = DashboardRepository(session)
    res = await repo.get_settlement_summary(org_id=1)

    assert res == {
        "active_loans_advances": 5,
        "closed_loans_advances": 3,
        "total_outstanding_loans_advances": Decimal("12500.00"),
        "total_outstanding_arrears": Decimal("3200.00"),
    }


@pytest.mark.asyncio
async def test_get_hardware_dashboard() -> None:
    session = AsyncMock()
    sync_date = datetime.datetime(2026, 7, 10, 10, 0, tzinfo=datetime.timezone.utc)  # noqa: UP017
    session.execute.side_effect = [
        _mock_result_all([("online", 4), ("offline", 1)]),
        _mock_scalar(sync_date),
    ]

    repo = DashboardRepository(session)
    res = await repo.get_hardware_dashboard(org_id=1)

    assert res == {
        "online_devices": 4,
        "offline_devices": 1,
        "disabled_devices": 0,
        "maintenance_devices": 0,
        "last_device_sync": sync_date,
    }


@pytest.mark.asyncio
async def test_get_notification_dashboard() -> None:
    session = AsyncMock()
    notif_date = datetime.datetime(2026, 7, 10, 10, 0, tzinfo=datetime.timezone.utc)  # noqa: UP017
    session.execute.side_effect = [
        _mock_scalar(3),
        _mock_result_all(
            [
                (10, "Test Notification", "alert", "high", notif_date),
            ]
        ),
    ]

    repo = DashboardRepository(session)
    res = await repo.get_notification_dashboard(org_id=1, user_id=99)

    assert res == {
        "unread_count": 3,
        "recent": [
            {
                "id": 10,
                "title": "Test Notification",
                "notification_type": "alert",
                "priority": "high",
                "created_at": notif_date,
            }
        ],
    }


@pytest.mark.asyncio
async def test_get_recent_activities() -> None:
    session = AsyncMock()
    log_date = datetime.datetime(2026, 7, 10, 10, 0, tzinfo=datetime.timezone.utc)  # noqa: UP017
    session.execute.return_value = _mock_result_all(
        [
            (1, "employee", "profile", "Profile Updated", "Changed address", "Admin", log_date),
        ]
    )

    repo = DashboardRepository(session)
    res = await repo.get_recent_activities(org_id=1, limit=5, branch_ids=[10])

    assert res == [
        {
            "id": 1,
            "module": "employee",
            "sub_module": "profile",
            "title": "Profile Updated",
            "description": "Changed address",
            "performed_by_name": "Admin",
            "logged_at": log_date,
        }
    ]


@pytest.mark.asyncio
async def test_get_employee_growth_chart() -> None:
    session = AsyncMock()
    session.execute.return_value = _mock_result_all(
        [
            ("2026-05", 10),
            ("2026-06", 15),
            ("2026-07", 5),
        ]
    )

    repo = DashboardRepository(session)
    res = await repo.get_employee_growth_chart(
        org_id=1,
        date_from=datetime.date(2026, 6, 1),
        date_to=datetime.date(2026, 7, 1),
    )

    assert res["labels"] == ["2026-06", "2026-07"]
    assert res["series"][0]["points"] == [25.0, 30.0]


@pytest.mark.asyncio
async def test_get_leave_trend_chart() -> None:
    session = AsyncMock()
    session.execute.return_value = _mock_result_all(
        [
            (datetime.date(2026, 7, 1), "pending", 2),
            (datetime.date(2026, 7, 1), "approved", 3),
            (datetime.date(2026, 7, 2), "approved", 1),
        ]
    )

    repo = DashboardRepository(session)
    res = await repo.get_leave_trend_chart(
        org_id=1,
        date_from=datetime.date(2026, 7, 1),
        date_to=datetime.date(2026, 7, 3),
    )

    assert res["labels"] == ["2026-07-01", "2026-07-02", "2026-07-03"]
    # Series: Pending, Approved, Rejected
    assert res["series"][0]["points"] == [2.0, 0.0, 0.0]
    assert res["series"][1]["points"] == [3.0, 1.0, 0.0]
    assert res["series"][2]["points"] == [0.0, 0.0, 0.0]


@pytest.mark.asyncio
async def test_get_payroll_trend_chart() -> None:
    session = AsyncMock()
    session.execute.return_value = _mock_result_all(
        [
            (datetime.date(2026, 6, 1), Decimal("150000.00")),
            (datetime.date(2026, 7, 1), Decimal("155000.00")),
        ]
    )

    repo = DashboardRepository(session)
    res = await repo.get_payroll_trend_chart(org_id=1, limit=6)

    assert res["labels"] == ["June 2026", "July 2026"]
    assert res["series"][0]["points"] == [150000.0, 155000.0]


@pytest.mark.asyncio
async def test_get_department_attendance_chart() -> None:
    session = AsyncMock()
    session.execute.return_value = _mock_result_all(
        [
            ("IT", "present", 45),
            ("IT", "absent", 5),
            ("HR", "present", 8),
        ]
    )

    repo = DashboardRepository(session)
    res = await repo.get_department_attendance_chart(
        org_id=1, target_date=datetime.date(2026, 7, 10)
    )

    assert res["labels"] == ["HR", "IT"]
    # Series: Present, Absent
    assert res["series"][0]["points"] == [8.0, 45.0]
    assert res["series"][1]["points"] == [0.0, 5.0]


@pytest.mark.asyncio
async def test_get_branch_attendance_chart() -> None:
    session = AsyncMock()
    session.execute.return_value = _mock_result_all(
        [
            ("HQ", "present", 90),
            ("Branch A", "absent", 2),
        ]
    )

    repo = DashboardRepository(session)
    res = await repo.get_branch_attendance_chart(org_id=1, target_date=datetime.date(2026, 7, 10))

    assert res["labels"] == ["Branch A", "HQ"]
    # Series: Present, Absent
    assert res["series"][0]["points"] == [0.0, 90.0]
    assert res["series"][1]["points"] == [2.0, 0.0]


@pytest.mark.asyncio
async def test_get_payroll_summary_finalized_pending_and_partial() -> None:
    session = AsyncMock()
    cycle_row = (10, datetime.date(2026, 7, 31), True, 20)

    # Test "pending" status
    run_mock_pending = MagicMock()
    run_mock_pending.id = 5
    run_mock_pending.finalized_amount = Decimal("500000.00")
    run_mock_pending.payment_status = "pending"

    session.execute.side_effect = [
        _mock_result_all([cycle_row]),
        _mock_scalar(run_mock_pending),
        _mock_scalar(95),
    ]
    repo = DashboardRepository(session)
    res_pending = await repo.get_payroll_summary(org_id=1)
    assert res_pending["payment_status_breakdown"] == {"paid": 0, "unpaid": 95}

    # Test "partial" status
    run_mock_partial = MagicMock()
    run_mock_partial.id = 5
    run_mock_partial.finalized_amount = Decimal("500000.00")
    run_mock_partial.payment_status = "partial"

    session.execute.side_effect = [
        _mock_result_all([cycle_row]),
        _mock_scalar(run_mock_partial),
        _mock_scalar(95),
    ]
    res_partial = await repo.get_payroll_summary(org_id=1)
    assert res_partial["payment_status_breakdown"] == {"paid": 47, "unpaid": 48}


@pytest.mark.asyncio
async def test_get_attendance_trend_with_dept() -> None:
    session = AsyncMock()
    session.execute.return_value = _mock_result_all([])
    repo = DashboardRepository(session)
    await repo.get_attendance_trend(
        org_id=1,
        date_from=datetime.date(2026, 7, 1),
        date_to=datetime.date(2026, 7, 2),
        dept_ids=[30],
    )
    assert session.execute.call_count == 1


@pytest.mark.asyncio
async def test_get_leave_type_breakdown_with_filters() -> None:
    session = AsyncMock()
    session.execute.return_value = _mock_result_all([])
    repo = DashboardRepository(session)
    await repo.get_leave_type_breakdown(org_id=1, branch_ids=[10], dept_ids=[20])
    assert session.execute.call_count == 1


@pytest.mark.asyncio
async def test_get_pending_approvals_summary_with_filters() -> None:
    session = AsyncMock()
    session.execute.return_value = _mock_result_all([])
    repo = DashboardRepository(session)
    await repo.get_pending_approvals_summary(org_id=1, branch_ids=[10], dept_ids=[20])
    assert session.execute.call_count == 1


@pytest.mark.asyncio
async def test_get_recent_approvals_with_filters() -> None:
    session = AsyncMock()
    session.execute.return_value = _mock_result_all([])
    repo = DashboardRepository(session)
    await repo.get_recent_approvals(org_id=1, limit=5, branch_ids=[10], dept_ids=[20])
    assert session.execute.call_count == 1


@pytest.mark.asyncio
async def test_get_recent_activities_with_dept() -> None:
    session = AsyncMock()
    session.execute.return_value = _mock_result_all([])
    repo = DashboardRepository(session)
    await repo.get_recent_activities(org_id=1, limit=5, dept_ids=[20])
    assert session.execute.call_count == 1


@pytest.mark.asyncio
async def test_get_employee_growth_chart_with_filters_and_empty() -> None:
    session = AsyncMock()
    session.execute.return_value = _mock_result_all([(None, 5)])
    repo = DashboardRepository(session)
    res = await repo.get_employee_growth_chart(
        org_id=1,
        date_from=datetime.date(2026, 6, 1),
        date_to=datetime.date(2026, 7, 1),
        branch_ids=[10],
        dept_ids=[20],
    )
    assert res["labels"] == ["2026-06"]
    assert res["series"][0]["points"] == [0.0]


@pytest.mark.asyncio
async def test_get_leave_trend_chart_with_filters() -> None:
    session = AsyncMock()
    session.execute.return_value = _mock_result_all([])
    repo = DashboardRepository(session)
    await repo.get_leave_trend_chart(
        org_id=1,
        date_from=datetime.date(2026, 7, 1),
        date_to=datetime.date(2026, 7, 3),
        branch_ids=[10],
        dept_ids=[20],
    )
    assert session.execute.call_count == 1


@pytest.mark.asyncio
async def test_get_payroll_trend_chart_empty() -> None:
    session = AsyncMock()
    session.execute.return_value = _mock_result_all([])
    repo = DashboardRepository(session)
    res = await repo.get_payroll_trend_chart(org_id=1)
    assert res["labels"] == ["No Data"]
    assert res["series"][0]["points"] == [0.0]


@pytest.mark.asyncio
async def test_get_department_attendance_chart_with_filters() -> None:
    session = AsyncMock()
    session.execute.return_value = _mock_result_all([])
    repo = DashboardRepository(session)
    await repo.get_department_attendance_chart(
        org_id=1, target_date=datetime.date(2026, 7, 10), branch_ids=[10], dept_ids=[20]
    )
    assert session.execute.call_count == 1


@pytest.mark.asyncio
async def test_get_branch_attendance_chart_with_filters() -> None:
    session = AsyncMock()
    session.execute.return_value = _mock_result_all([])
    repo = DashboardRepository(session)
    await repo.get_branch_attendance_chart(
        org_id=1, target_date=datetime.date(2026, 7, 10), branch_ids=[10], dept_ids=[20]
    )
    assert session.execute.call_count == 1
