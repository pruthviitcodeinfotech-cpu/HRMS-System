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


class EmployeeNotFoundException(NotFoundException):
    """The referenced employee does not exist in the caller's organization."""

    code = "EMPLOYEE_NOT_FOUND"
    message = "The requested employee was not found."


class ShiftNotFoundException(NotFoundException):
    """The referenced shift does not exist in the caller's organization."""

    code = "SHIFT_NOT_FOUND"
    message = "The requested shift was not found."
