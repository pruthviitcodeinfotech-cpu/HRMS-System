"""Attendance module: constants, enums, and permission keys.

These enums mirror the CHECK-constraint value sets defined in the approved
Attendance Database Architecture. They are the single source of truth for
the allowed values enforced at the database level (see models.py).
"""

from enum import Enum


class AttendanceDayStatus(str, Enum):
    """attendance_days.status allowed values."""

    PRESENT = "present"
    ABSENT = "absent"
    HALF_DAY = "half_day"
    WEEK_OFF = "week_off"
    HOLIDAY = "holiday"
    ON_LEAVE = "on_leave"
    NOT_MARKED = "not_marked"


class AttendanceSource(str, Enum):
    """attendance_days.source allowed values."""

    BIOMETRIC = "biometric"
    MOBILE = "mobile"
    WEB = "web"
    MANUAL = "manual"
    SYSTEM = "system"


class PunchType(str, Enum):
    """attendance_punches.punch_type allowed values."""

    IN = "in"
    OUT = "out"
    BREAK_IN = "break_in"
    BREAK_OUT = "break_out"


class PunchSource(str, Enum):
    """attendance_punches.punch_source allowed values."""

    BIOMETRIC_DEVICE = "biometric_device"
    MOBILE_APP = "mobile_app"
    WEB_PORTAL = "web_portal"
    MANUAL_ENTRY = "manual_entry"


class PenaltyType(str, Enum):
    """attendance_penalties.penalty_type allowed values."""

    LATE_COMING = "late_coming"
    EARLY_GOING = "early_going"
    ABSENT_WITHOUT_NOTICE = "absent_without_notice"
    OTHER = "other"


class PenaltyUnit(str, Enum):
    """attendance_penalties.penalty_unit allowed values."""

    AMOUNT = "amount"
    DAYS = "days"
    HOURS = "hours"


class PenaltyStatus(str, Enum):
    """attendance_penalties.status allowed values."""

    ACTIVE = "active"
    WAIVED = "waived"


class ApprovalStatus(str, Enum):
    """approval_requests.status and regularization request status."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class LockScope(str, Enum):
    """attendance_locks.scope allowed values."""

    COMPANY = "company"
    BRANCH = "branch"
