"""Shift Management module: constants and enums.

These enums mirror the CHECK-constraint value sets defined in the approved Shift
Management Database Architecture. They are the single source of truth for the
allowed values enforced at the database level (see the models package). Native
PostgreSQL ENUM types are intentionally NOT used — the approved architecture
models these as VARCHAR columns with CHECK constraints, and that is preserved.
"""

from enum import Enum, IntEnum


class ShiftType(str, Enum):
    """shifts.shift_type."""

    FIXED = "fixed"
    OPEN = "open"


class WeekoffType(str, Enum):
    """employee_weekoffs.weekoff_type."""

    WORKING = "working"
    WEEK_OFF = "week_off"
    OCCASIONAL_WEEK_OFF = "occasional_week_off"


class WorkingHoursMode(str, Enum):
    """working_hours_config.working_hours_mode / *_history.working_hours_mode."""

    FIXED = "fixed"
    SHIFT_WISE = "shift_wise"


class AttendanceMode(str, Enum):
    """working_hours_config.attendance_mode / *_history.attendance_mode."""

    CONSIDER_ALL_PUNCH = "consider_all_punch"
    FIRST_AND_LAST_PUNCH_ONLY = "first_and_last_punch_only"
    FULL_DAY_ON_SINGLE_PUNCH = "full_day_on_single_punch"
    DEFAULT_FULL_DAY = "default_full_day"


class DayOfWeek(IntEnum):
    """Day-of-week ordinal used by shift_day_timings.day_of_week and
    employee_weekoffs.day_of_week.

    The approved architecture stores this as SMALLINT (0 = Sunday ... 6 =
    Saturday). employee_weekoffs enforces it at the DB with a CHECK
    (day_of_week BETWEEN 0 AND 6); shift_day_timings.day_of_week is nullable and
    has no CHECK per the specification. This IntEnum is for application use only.
    """

    SUNDAY = 0
    MONDAY = 1
    TUESDAY = 2
    WEDNESDAY = 3
    THURSDAY = 4
    FRIDAY = 5
    SATURDAY = 6
