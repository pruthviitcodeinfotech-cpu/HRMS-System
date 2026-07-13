"""Attendance Management — module-specific exception types.

Each type specialises a shared :mod:`app.core.exceptions.base` exception so the
registered handlers map it to the right HTTP status and the contract's stable
machine-readable ``code`` without any router-level ``HTTPException``.
"""

from __future__ import annotations

from app.core.exceptions.base import ConflictException, NotFoundException


class AttendanceDayNotFoundException(NotFoundException):
    """The referenced attendance day does not exist in the caller's organization."""

    code = "ATTENDANCE_DAY_NOT_FOUND"
    message = "The requested attendance day was not found."


class AttendanceDayExistsException(ConflictException):
    """An attendance day already exists for the employee/date pair."""

    code = "ATTENDANCE_DAY_EXISTS"
    message = "An attendance day already exists for this employee on this date."


class PenaltyNotFoundException(NotFoundException):
    """The referenced attendance penalty does not exist in the caller's organization."""

    code = "PENALTY_NOT_FOUND"
    message = "The requested penalty was not found."


class PenaltyAlreadyWaivedException(ConflictException):
    """The penalty has already been waived and cannot be waived again."""

    code = "PENALTY_ALREADY_WAIVED"
    message = "This penalty has already been waived."


class RegularizationDisabledException(ConflictException):
    """The organization has turned attendance regularization off in Settings."""

    code = "REGULARIZATION_DISABLED"
    message = "Attendance regularization is disabled for this organization."


class EmployeeNotFoundException(NotFoundException):
    """The referenced employee does not exist in the caller's organization."""

    code = "EMPLOYEE_NOT_FOUND"
    message = "The requested employee was not found."


class ShiftNotFoundException(NotFoundException):
    """The referenced shift does not exist in the caller's organization."""

    code = "SHIFT_NOT_FOUND"
    message = "The requested shift was not found."


class AttendancePeriodLockedException(ConflictException):
    """The attendance period is locked for mutations."""

    code = "ATTENDANCE_PERIOD_LOCKED"
    message = "Attendance period is locked."

    def __init__(self, month: int, year: int, message: str | None = None, **kwargs) -> None:
        import calendar
        month_name = calendar.month_name[month]
        msg = message or f"Attendance for {month_name} {year} is locked."
        super().__init__(message=msg, **kwargs)

