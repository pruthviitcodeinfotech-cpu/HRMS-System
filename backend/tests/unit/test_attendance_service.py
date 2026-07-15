"""Unit tests for Attendance Lock / Unlock service logic."""

from __future__ import annotations

import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.modules.attendance.exceptions import AttendancePeriodLockedException
from app.modules.attendance.schemas import (
    AttendanceLockRequest,
    AttendanceUnlockRequest,
)
from app.modules.attendance.service import AttendanceService

_ORG_ID = 10
_USER_ID = 99
_NOW = datetime.datetime(2026, 7, 10, 10, 0, 0, tzinfo=datetime.UTC)


def _make_service() -> AttendanceService:
    svc = AttendanceService(AsyncMock())
    svc.locks = AsyncMock()
    svc.employees = AsyncMock()
    svc.users = AsyncMock()
    svc.audit = AsyncMock()
    return svc


@pytest.mark.asyncio
async def test_lock_attendance_success() -> None:
    svc = _make_service()
    svc.users.get_active_by_id = AsyncMock(return_value=SimpleNamespace(name="Admin"))
    svc.locks.is_locked = AsyncMock(return_value=False)

    lock_record = SimpleNamespace(
        id=1,
        org_id=_ORG_ID,
        lock_month=2,
        lock_year=2026,
        lock_type="company",
        branch_id=None,
        status="locked",
        locked_by=_USER_ID,
        locked_at=_NOW,
        reason="Monthly closing",
        created_at=_NOW,
        updated_at=_NOW,
    )
    svc.locks.create_lock = AsyncMock(return_value=lock_record)

    req = AttendanceLockRequest(
        period_start=datetime.date(2026, 2, 1),
        period_end=datetime.date(2026, 2, 28),
        scope="company",
        branch_id=None,
        reason="Monthly closing",
    )
    result = await svc.lock_attendance(org_id=_ORG_ID, actor_id=_USER_ID, data=req)

    assert result is True
    svc.locks.create_lock.assert_called_once_with(
        org_id=_ORG_ID,
        month=2,
        year=2026,
        lock_type="company",
        branch_id=None,
        locked_by=_USER_ID,
        reason="Monthly closing",
        status="locked",
    )
    svc.audit.record.assert_called_once()


@pytest.mark.asyncio
async def test_lock_attendance_already_locked() -> None:
    svc = _make_service()
    svc.locks.is_locked = AsyncMock(return_value=True)

    req = AttendanceLockRequest(
        period_start=datetime.date(2026, 2, 1),
        period_end=datetime.date(2026, 2, 28),
        scope="company",
        branch_id=None,
        reason="Monthly closing",
    )
    with pytest.raises(AttendancePeriodLockedException):
        await svc.lock_attendance(org_id=_ORG_ID, actor_id=_USER_ID, data=req)


@pytest.mark.asyncio
async def test_unlock_attendance_success() -> None:
    svc = _make_service()
    svc.users.get_active_by_id = AsyncMock(return_value=SimpleNamespace(name="Admin"))
    svc.locks.unlock = AsyncMock(return_value=True)

    req = AttendanceUnlockRequest(
        period_start=datetime.date(2026, 2, 1),
        period_end=datetime.date(2026, 2, 28),
        scope="company",
        branch_id=None,
        reason="Monthly unlocking",
    )
    result = await svc.unlock_attendance(org_id=_ORG_ID, actor_id=_USER_ID, data=req)

    assert result is True
    svc.locks.unlock.assert_called_once_with(
        org_id=_ORG_ID,
        month=2,
        year=2026,
        branch_id=None,
    )
    svc.audit.record.assert_called_once()


@pytest.mark.asyncio
async def test_check_period_locked_not_locked() -> None:
    svc = _make_service()
    svc.locks.is_locked = AsyncMock(return_value=False)

    # Should not raise exception
    await svc.check_period_locked(
        org_id=_ORG_ID,
        date_val=datetime.date(2026, 2, 15),
        employee_id=5,
    )
    svc.locks.is_locked.assert_called_once()


@pytest.mark.asyncio
async def test_check_period_locked_raises() -> None:
    svc = _make_service()
    svc.locks.is_locked = AsyncMock(return_value=True)

    with pytest.raises(AttendancePeriodLockedException):
        await svc.check_period_locked(
            org_id=_ORG_ID,
            date_val=datetime.date(2026, 2, 15),
            employee_id=5,
        )


@pytest.mark.asyncio
async def test_get_locked_periods() -> None:
    svc = _make_service()
    lock_record = SimpleNamespace(
        id=1,
        org_id=_ORG_ID,
        lock_month=2,
        lock_year=2026,
        lock_type="company",
        branch_id=None,
        status="locked",
        locked_by=_USER_ID,
        locked_at=_NOW,
        reason="Monthly closing",
        created_at=_NOW,
        updated_at=_NOW,
    )
    svc.locks.get_locked_periods = AsyncMock(return_value=[lock_record])

    result = await svc.get_locked_periods(org_id=_ORG_ID)
    assert len(result) == 1
    assert result[0].lock_month == 2
    svc.locks.get_locked_periods.assert_called_once_with(_ORG_ID)


def test_attendance_daily_schema_new_fields() -> None:
    from app.modules.attendance.schemas import AttendanceDailySchema

    # 1. Test validation from dict
    data_dict = {
        "employee_id": 1,
        "status": "present",
        "first_punch_in": datetime.datetime(2026, 7, 15, 9, 0, 0),
        "last_punch_out": datetime.datetime(2026, 7, 15, 18, 0, 0),
        "total_working_minutes": 540,
        "total_break_minutes": 60,
        "overtime_minutes": 30,
        "is_locked": False,
        "employee": {
            "employee_code": "EMP001",
            "employee_name": "John Doe",
            "department": {
                "dept_name": "Engineering"
            },
            "designation": {
                "designation_name": "Software Engineer"
            }
        }
    }
    schema = AttendanceDailySchema.model_validate(data_dict)
    assert schema.employee_code == "EMP001"
    assert schema.employee_name == "John Doe"
    assert schema.department_name == "Engineering"
    assert schema.designation == "Software Engineer"
    assert schema.first_punch == datetime.datetime(2026, 7, 15, 9, 0, 0)
    assert schema.last_punch == datetime.datetime(2026, 7, 15, 18, 0, 0)
    assert schema.working_hours == 9.0
    assert schema.break_hours == 1.0
    assert schema.overtime == 0.5

    # 2. Test validation from ORM-like object (using SimpleNamespace)
    class DummyRelation:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)

    dummy_dept = DummyRelation(dept_name="Sales")
    dummy_desg = DummyRelation(designation_name="Executive")
    dummy_employee = DummyRelation(
        employee_code="EMP002",
        employee_name="Jane Smith",
        department=dummy_dept,
        designation=dummy_desg
    )
    dummy_day = DummyRelation(
        employee_id=2,
        status="present",
        first_punch_in=datetime.datetime(2026, 7, 15, 9, 30, 0),
        last_punch_out=datetime.datetime(2026, 7, 15, 17, 30, 0),
        total_working_minutes=480,
        total_break_minutes=30,
        overtime_minutes=0,
        is_locked=True,
        employee=dummy_employee
    )
    schema_orm = AttendanceDailySchema.model_validate(dummy_day)
    assert schema_orm.employee_code == "EMP002"
    assert schema_orm.employee_name == "Jane Smith"
    assert schema_orm.department_name == "Sales"
    assert schema_orm.designation == "Executive"
    assert schema_orm.first_punch == datetime.datetime(2026, 7, 15, 9, 30, 0)
    assert schema_orm.last_punch == datetime.datetime(2026, 7, 15, 17, 30, 0)
    assert schema_orm.working_hours == 8.0
    assert schema_orm.break_hours == 0.5
    assert schema_orm.overtime == 0.0

