"""Payroll module: constants and enums.

Enums mirror the value sets in the approved Payroll Database Architecture. Only
the enums marked "DB CHECK" are enforced at the database level (the approved
architecture defines CHECK constraints for those columns only); the rest are for
application use. Native PostgreSQL ENUM types are intentionally NOT used — the
architecture models these as VARCHAR columns.
"""

from enum import Enum


class PayrollType(str, Enum):
    """payroll_groups.payroll_type. (Enforced by DB CHECK.)"""

    MONTHLY_WITHOUT_COMPLIANCE = "monthly_without_compliance"
    MONTHLY_WITH_COMPLIANCE = "monthly_with_compliance"
    HOURLY_PAYROLL = "hourly_payroll"


class PayrollSalaryType(str, Enum):
    """employee_payroll_group_assignments.salary_type. (Enforced by DB CHECK.)"""

    MONTHLY = "monthly"
    HOURLY = "hourly"


class AdjustedStatus(str, Enum):
    """attendance_adjustments.adjusted_status (and original_status). (Enforced by DB CHECK.)"""

    FULL_DAY = "FD"
    HALF_DAY = "HD"
    ABSENT = "A"
    WEEK_OFF = "WO"
    LEAVE_WITHOUT_PAY = "LWP"


class PaymentStatus(str, Enum):
    """finalized_payroll_runs.payment_status. (Enforced by DB CHECK.)"""

    PENDING = "pending"
    PAID = "paid"
    PARTIAL = "partial"


class AdjustmentSource(str, Enum):
    """attendance_adjustments.adjustment_source. (App-only; no DB CHECK per the architecture.)"""

    SPREADSHEET = "spreadsheet"
    QUICK_ACTION = "quick_action"


class WorkingHourType(str, Enum):
    """payroll_settings.working_hour_type. (App-only; no DB CHECK per the architecture.)"""

    FIXED = "fixed"
    SHIFT_WISE = "shift_wise"


class AttendanceMode(str, Enum):
    """payroll_settings.attendance_mode. (App-only; no DB CHECK per the architecture.)"""

    CONSIDER_ALL_PUNCH = "consider_all_punch"
    FIRST_AND_LAST_PUNCH_ONLY = "first_and_last_punch_only"
    FULL_DAY_ON_SINGLE_PUNCH = "full_day_on_single_punch"
    DEFAULT_FULL_DAY = "default_full_day"
