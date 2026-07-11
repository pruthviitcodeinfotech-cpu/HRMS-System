"""Shift Management module-specific exception types.

Maps to the error codes defined in the approved Shift Management API Contract
(§11 Error Handling): stable machine-readable codes rendered through the shared
error envelope by the global handlers.
"""

from __future__ import annotations

from app.core.exceptions.base import (
    ConflictException,
    NotFoundException,
)


class ShiftNotFoundException(NotFoundException):
    """Raised when a shift is not found (or soft-deleted) within the org."""

    code = "SHIFT_NOT_FOUND"
    message = "Shift not found."


class ShiftNameExistsException(ConflictException):
    """Raised when a shift name is already used by a non-deleted shift in the org."""

    code = "SHIFT_NAME_EXISTS"
    message = "Shift name already in use."


class ShiftInUseException(ConflictException):
    """Raised when deleting a shift that is referenced by assignments or roster rows."""

    code = "SHIFT_IN_USE"
    message = "Shift is in use and cannot be deleted."


class ShiftNotDeletedException(ConflictException):
    """Raised when restoring a shift that is not soft-deleted."""

    code = "SHIFT_NOT_DELETED"
    message = "Shift is not deleted."


class TimingNotFoundException(NotFoundException):
    """Raised when a shift day-timing row is not found for the shift."""

    code = "TIMING_NOT_FOUND"
    message = "Shift timing not found."


class TimingDayDuplicateException(ConflictException):
    """Raised when a timing set repeats a ``day_of_week`` for the same shift."""

    code = "TIMING_DAY_DUPLICATE"
    message = "A timing already exists for this day of week."


class WeekoffNotFoundException(NotFoundException):
    """Raised when a weekly-off row is not found for the employee."""

    code = "WEEKOFF_NOT_FOUND"
    message = "Weekly-off configuration not found."


class WeekoffDayExistsException(ConflictException):
    """Raised on a duplicate *current* weekly-off row for a weekday."""

    code = "WEEKOFF_DAY_EXISTS"
    message = "A current weekly-off configuration already exists for this weekday."


class AssignmentNotFoundException(NotFoundException):
    """Raised when a shift assignment is not found within the org."""

    code = "ASSIGNMENT_NOT_FOUND"
    message = "Shift assignment not found."


class AssignmentOverlapException(ConflictException):
    """Raised when an assignment's effective range overlaps another for the employee."""

    code = "ASSIGNMENT_OVERLAP"
    message = "The assignment period overlaps an existing assignment."


class RosterNotFoundException(NotFoundException):
    """Raised when a roster entry is not found within the org."""

    code = "ROSTER_NOT_FOUND"
    message = "Roster entry not found."


class RosterEntryExistsException(ConflictException):
    """Raised when a roster entry already exists for the employee/date pair."""

    code = "ROSTER_ENTRY_EXISTS"
    message = "A roster entry already exists for this employee and date."


class EmployeeNotFoundException(NotFoundException):
    """Raised when a referenced employee is not found or inactive in the org."""

    code = "EMPLOYEE_NOT_FOUND"
    message = "Employee not found."


__all__ = [
    "ShiftNotFoundException",
    "ShiftNameExistsException",
    "ShiftInUseException",
    "ShiftNotDeletedException",
    "TimingNotFoundException",
    "TimingDayDuplicateException",
    "WeekoffNotFoundException",
    "WeekoffDayExistsException",
    "AssignmentNotFoundException",
    "AssignmentOverlapException",
    "RosterNotFoundException",
    "RosterEntryExistsException",
    "EmployeeNotFoundException",
]
