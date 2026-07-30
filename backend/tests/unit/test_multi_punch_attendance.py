"""Unit tests for multi-punch attendance engine enhancements and live status rules.

Verifies:
- Multiple IN/OUT punch pairs and working duration sum: Σ (OUT - IN)
- Break time accumulation between sessions: Σ (Next IN - Previous OUT)
- First punch and last punch tracking (IN or OUT)
- Overtime calculation: max(Working Hours - Shift Duration, 0)
- Rule 12 timeline verification
- Today's Live Status rules: No employee marked ABSENT during the day (0 punches -> not_marked, punches -> present/FD/HD)
- Past Date Finalization rules: 12:00 AM midnight finalization marks unpunched/under-worked past days as ABSENT
"""

from datetime import date, datetime, time, timezone, timedelta
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.modules.attendance.models import AttendanceDay, AttendancePunch
from app.modules.attendance.service import AttendanceService
from app.modules.attendance.constants import PunchType, AttendanceDayStatus
from app.shared.utils.datetime import utcnow


def make_datetime(hour: int, minute: int, day_offset: int = 0) -> datetime:
    return datetime(2026, 7, 30, hour, minute, tzinfo=timezone.utc)


def make_punch(punch_id: int, day_id: int, ptype: str, ptime: datetime, seq: int) -> AttendancePunch:
    punch = MagicMock(spec=AttendancePunch)
    punch.id = punch_id
    punch.attendance_day_id = day_id
    punch.punch_type = ptype
    punch.punch_time = ptime
    punch.sequence_no = seq
    punch.is_valid = True
    return punch


@pytest.mark.asyncio
async def test_timeline_example_rule_12():
    """Test attendance timeline example from Business Rule 12:
    09:00 IN, 12:30 OUT (3h30m)
    01:00 IN, 05:30 OUT (4h30m)
    06:00 IN, 08:15 OUT (2h15m)

    Expected Results:
    - Working: 10h15m (615 minutes)
    - Break: 1h (60 minutes)
    - Shift: 8h (480 minutes)
    - Overtime: 2h15m (135 minutes)
    """
    mock_session = AsyncMock()
    service = AttendanceService(mock_session)

    day = MagicMock(spec=AttendanceDay)
    day.id = 100
    day.org_id = 1
    day.employee_id = 42
    day.attendance_date = date(2026, 7, 30)
    day.expected_start_time = time(9, 0)
    day.expected_end_time = time(17, 0)  # 8 hours shift
    day.status = "not_marked"
    day.source = "system"
    day.leave_id = None

    punches = [
        make_punch(1, 100, PunchType.IN.value, make_datetime(9, 0), 1),
        make_punch(2, 100, PunchType.OUT.value, make_datetime(12, 30), 2),
        make_punch(3, 100, PunchType.IN.value, make_datetime(13, 0), 3),
        make_punch(4, 100, PunchType.OUT.value, make_datetime(17, 30), 4),
        make_punch(5, 100, PunchType.IN.value, make_datetime(18, 0), 5),
        make_punch(6, 100, PunchType.OUT.value, make_datetime(20, 15), 6),
    ]

    service.punches.get_for_day = AsyncMock(return_value=punches)
    service.days.update = AsyncMock()

    await service._recompute_day_metrics(org_id=1, day=day)

    # Verify update arguments
    assert service.days.update.called
    update_data = service.days.update.call_args[0][1]

    assert update_data["first_punch_in"] == make_datetime(9, 0)
    assert update_data["last_punch_out"] == make_datetime(20, 15)
    assert update_data["total_working_minutes"] == 615  # 10h15m
    assert update_data["total_break_minutes"] == 60     # 1h00m
    assert update_data["overtime_minutes"] == 135       # 2h15m (615 - 480)
    assert update_data["status"] == AttendanceDayStatus.PRESENT.value


@pytest.mark.asyncio
async def test_multiple_breaks_rule_5():
    """Test Business Rule 5:
    09:00 IN, 01:00 OUT (4h)
    01:30 IN, 05:00 OUT (3h30m)
    05:15 IN, 07:00 OUT (1h45m)

    Expected Results:
    - Working: 9h15m (555 minutes)
    - Break: 45m (45 minutes)
    - Shift: 8h (480 minutes)
    - Overtime: 1h15m (75 minutes)
    """
    mock_session = AsyncMock()
    service = AttendanceService(mock_session)

    day = MagicMock(spec=AttendanceDay)
    day.id = 101
    day.org_id = 1
    day.employee_id = 43
    day.attendance_date = date(2026, 7, 30)
    day.expected_start_time = time(9, 0)
    day.expected_end_time = time(17, 0)
    day.status = "not_marked"
    day.source = "system"
    day.leave_id = None

    punches = [
        make_punch(1, 101, PunchType.IN.value, make_datetime(9, 0), 1),
        make_punch(2, 101, PunchType.OUT.value, make_datetime(13, 0), 2),
        make_punch(3, 101, PunchType.IN.value, make_datetime(13, 30), 3),
        make_punch(4, 101, PunchType.OUT.value, make_datetime(17, 0), 4),
        make_punch(5, 101, PunchType.IN.value, make_datetime(17, 15), 5),
        make_punch(6, 101, PunchType.OUT.value, make_datetime(19, 0), 6),
    ]

    service.punches.get_for_day = AsyncMock(return_value=punches)
    service.days.update = AsyncMock()

    await service._recompute_day_metrics(org_id=1, day=day)

    update_data = service.days.update.call_args[0][1]

    assert update_data["first_punch_in"] == make_datetime(9, 0)
    assert update_data["last_punch_out"] == make_datetime(19, 0)
    assert update_data["total_working_minutes"] == 555  # 9h15m
    assert update_data["total_break_minutes"] == 45     # 45m
    assert update_data["overtime_minutes"] == 75        # 1h15m (555 - 480)


@pytest.mark.asyncio
async def test_today_no_absent_during_day():
    """Verify that during today's working day:
    1. Employees with 0 punches are marked 'not_marked' (NEVER 'absent').
    2. Employees with active punches (even if under half-day mins) are marked 'present' (NEVER 'absent').
    """
    mock_session = AsyncMock()
    service = AttendanceService(mock_session)

    today = utcnow().date()

    # Case A: 0 punches today
    day_no_punch = MagicMock(spec=AttendanceDay)
    day_no_punch.id = 201
    day_no_punch.org_id = 1
    day_no_punch.employee_id = 50
    day_no_punch.attendance_date = today
    day_no_punch.expected_start_time = time(9, 0)
    day_no_punch.expected_end_time = time(17, 0)
    day_no_punch.status = "not_marked"
    day_no_punch.source = "system"
    day_no_punch.leave_id = None

    service.punches.get_for_day = AsyncMock(return_value=[])
    service.days.update = AsyncMock()

    await service._recompute_day_metrics(org_id=1, day=day_no_punch)
    update_data_a = service.days.update.call_args[0][1]
    assert update_data_a["status"] == AttendanceDayStatus.NOT_MARKED.value

    # Case B: Short punch today (< 4 hours)
    day_short_punch = MagicMock(spec=AttendanceDay)
    day_short_punch.id = 202
    day_short_punch.org_id = 1
    day_short_punch.employee_id = 51
    day_short_punch.attendance_date = today
    day_short_punch.expected_start_time = time(9, 0)
    day_short_punch.expected_end_time = time(17, 0)
    day_short_punch.status = "not_marked"
    day_short_punch.source = "system"
    day_short_punch.leave_id = None

    today_punches = [
        make_punch(1, 202, PunchType.IN.value, datetime.now(timezone.utc) - timedelta(hours=1), 1),
        make_punch(2, 202, PunchType.OUT.value, datetime.now(timezone.utc) - timedelta(minutes=30), 2),
    ]

    service.punches.get_for_day = AsyncMock(return_value=today_punches)
    await service._recompute_day_metrics(org_id=1, day=day_short_punch)
    update_data_b = service.days.update.call_args[0][1]
    assert update_data_b["status"] == AttendanceDayStatus.PRESENT.value


@pytest.mark.asyncio
async def test_past_date_finalized_status_rule():
    """Verify that for finalized past dates (e.g. yesterday):
    1. Employees with 0 punches are finalized as ABSENT.
    2. Employees with worked hours < half day mins are finalized as ABSENT.
    """
    mock_session = AsyncMock()
    service = AttendanceService(mock_session)

    yesterday = utcnow().date() - timedelta(days=1)

    # Case A: 0 punches yesterday
    day_no_punch = MagicMock(spec=AttendanceDay)
    day_no_punch.id = 301
    day_no_punch.org_id = 1
    day_no_punch.employee_id = 60
    day_no_punch.attendance_date = yesterday
    day_no_punch.expected_start_time = time(9, 0)
    day_no_punch.expected_end_time = time(17, 0)
    day_no_punch.status = "not_marked"
    day_no_punch.source = "system"
    day_no_punch.leave_id = None

    service.punches.get_for_day = AsyncMock(return_value=[])
    service.days.update = AsyncMock()

    await service._recompute_day_metrics(org_id=1, day=day_no_punch)
    update_data_a = service.days.update.call_args[0][1]
    assert update_data_a["status"] == AttendanceDayStatus.ABSENT.value

    # Case B: Short punch yesterday (< 4 hours)
    day_short_punch = MagicMock(spec=AttendanceDay)
    day_short_punch.id = 302
    day_short_punch.org_id = 1
    day_short_punch.employee_id = 61
    day_short_punch.attendance_date = yesterday
    day_short_punch.expected_start_time = time(9, 0)
    day_short_punch.expected_end_time = time(17, 0)
    day_short_punch.status = "not_marked"
    day_short_punch.source = "system"
    day_short_punch.leave_id = None

    yest_dt = datetime.combine(yesterday, time(9, 0)).replace(tzinfo=timezone.utc)
    yest_punches = [
        make_punch(1, 302, PunchType.IN.value, yest_dt, 1),
        make_punch(2, 302, PunchType.OUT.value, yest_dt + timedelta(hours=1), 2),
    ]

    service.punches.get_for_day = AsyncMock(return_value=yest_punches)
    await service._recompute_day_metrics(org_id=1, day=day_short_punch)
    update_data_b = service.days.update.call_args[0][1]
    assert update_data_b["status"] == AttendanceDayStatus.ABSENT.value
