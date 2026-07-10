"""Unit tests for the ReportsRepository layer."""

from __future__ import annotations

import datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.modules.reports.repository import ReportsRepository


def _mock_scalar(value) -> MagicMock:
    res = MagicMock()
    res.scalar.return_value = value
    res.scalar_one.return_value = value
    res.scalar_one_or_none.return_value = value
    return res


def _mock_result_all(rows: list) -> MagicMock:
    res = MagicMock()
    res.all.return_value = rows
    res.first.return_value = rows[0] if rows else None
    return res


class MockRow:
    """Mock row returning key-value mapping."""

    def __init__(self, **kwargs) -> None:
        self.__dict__.update(kwargs)
        self._mapping = kwargs

    def __getitem__(self, index):
        if isinstance(index, int):
            return list(self._mapping.values())[index]
        return self._mapping[index]


@pytest.mark.asyncio
async def test_get_employee_master_report() -> None:
    session = AsyncMock()
    # 1st call for total count, 2nd call for roster rows
    mock_count = _mock_scalar(10)
    mock_rows = _mock_result_all(
        [
            MockRow(
                code="EMP001",
                name="John Doe",
                mobile="1234567890",
                email="john@example.com",
                branch="HQ",
                department="Engineering",
                designation="Software Engineer",
                employee_type="full_time",
                date_of_joining=datetime.date(2026, 1, 1),
                status="active",
            )
        ]
    )
    session.execute.side_effect = [mock_count, mock_rows]

    repo = ReportsRepository(session)
    items, total = await repo.get_employee_master_report(
        org_id=1,
        branch_ids=[1],
        dept_ids=[2],
        designation_id=3,
        employee_type="full_time",
        status="active",
        sort_by="name",
        sort_dir="asc",
    )

    assert total == 10
    assert len(items) == 1
    assert items[0]["code"] == "EMP001"
    assert items[0]["name"] == "John Doe"


@pytest.mark.asyncio
async def test_get_employee_joining_report() -> None:
    session = AsyncMock()
    mock_count = _mock_scalar(5)
    mock_rows = _mock_result_all(
        [
            MockRow(
                code="EMP002",
                name="Jane Doe",
                branch="HQ",
                department="HR",
                designation="HR Manager",
                date_of_joining=datetime.date(2026, 2, 1),
            )
        ]
    )
    session.execute.side_effect = [mock_count, mock_rows]

    repo = ReportsRepository(session)
    items, total = await repo.get_employee_joining_report(
        org_id=1,
        date_from=datetime.date(2026, 1, 1),
        date_to=datetime.date(2026, 12, 31),
    )

    assert total == 5
    assert len(items) == 1
    assert items[0]["name"] == "Jane Doe"


@pytest.mark.asyncio
async def test_get_daily_attendance_report() -> None:
    session = AsyncMock()
    mock_count = _mock_scalar(15)
    mock_rows = _mock_result_all(
        [
            MockRow(
                employee_code="EMP001",
                employee_name="John Doe",
                attendance_date=datetime.date(2026, 7, 10),
                status="present",
                first_punch_in=datetime.datetime(2026, 7, 10, 9, 0),
                last_punch_out=datetime.datetime(2026, 7, 10, 18, 0),
                work_hours=9.0,
                late_minutes=0,
                early_leaving_minutes=0,
            )
        ]
    )
    session.execute.side_effect = [mock_count, mock_rows]

    repo = ReportsRepository(session)
    items, total = await repo.get_daily_attendance_report(
        org_id=1,
        target_date=datetime.date(2026, 7, 10),
        status="present",
    )

    assert total == 15
    assert len(items) == 1
    assert items[0]["status"] == "present"
    assert items[0]["work_hours"] == 9.0


@pytest.mark.asyncio
async def test_get_payroll_summary_report() -> None:
    session = AsyncMock()
    mock_row = MagicMock()
    mock_row.first.return_value = (
        Decimal("100000.00"),
        Decimal("10000.00"),
        Decimal("90000.00"),
        10,
    )
    session.execute.return_value = mock_row

    repo = ReportsRepository(session)
    res = await repo.get_payroll_summary_report(
        org_id=1,
        payroll_group_id=2,
        salary_cycle_id=3,
    )

    assert res["gross_sum"] == Decimal("100000.00")
    assert res["deductions_sum"] == Decimal("10000.00")
    assert res["net_payable_sum"] == Decimal("90000.00")
    assert res["total_headcount"] == 10
