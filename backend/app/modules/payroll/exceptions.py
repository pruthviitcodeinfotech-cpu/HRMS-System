"""Payroll Management exception definitions."""

from app.core.exceptions.base import (
    ConflictException,
    NotFoundException,
)


class PayrollGroupNotFoundException(NotFoundException):
    """Raised when a payroll group cannot be found."""
    code = "PAYROLL_GROUP_NOT_FOUND"
    message = "Payroll group not found."


class PayrollGroupNameExistsException(ConflictException):
    """Raised when a payroll group name already exists."""
    code = "PAYROLL_GROUP_NAME_EXISTS"
    message = "Payroll group name already exists."


class PayrollGroupInUseException(ConflictException):
    """Raised when trying to delete or modify a payroll group that is in use."""
    code = "PAYROLL_GROUP_IN_USE"
    message = "Payroll group is currently in use."


class CycleNotFoundException(NotFoundException):
    """Raised when a payroll cycle cannot be found."""
    code = "CYCLE_NOT_FOUND"
    message = "Payroll cycle not found."


class CycleExistsException(ConflictException):
    """Raised when a payroll cycle already exists."""
    code = "CYCLE_EXISTS"
    message = "Payroll cycle already exists."


class CycleFinalizedException(ConflictException):
    """Raised when trying to edit a finalized cycle."""
    code = "CYCLE_FINALIZED"
    message = "Payroll cycle is finalized."


class ComputedRowNotFoundException(NotFoundException):
    """Raised when a computed row cannot be found."""
    code = "COMPUTED_ROW_NOT_FOUND"
    message = "Computed payroll record not found."


class FinalizedRunNotFoundException(NotFoundException):
    """Raised when a finalized run cannot be found."""
    code = "FINALIZED_RUN_NOT_FOUND"
    message = "Finalized payroll run not found."


class PayrollAlreadyFinalizedException(ConflictException):
    """Raised when payroll is already finalized for a period."""
    code = "PAYROLL_ALREADY_FINALIZED"
    message = "Payroll for this period is already finalized."


class PayrollNotFinalizedException(ConflictException):
    """Raised when payroll is not finalized."""
    code = "PAYROLL_NOT_FINALIZED"
    message = "Payroll for this period is not finalized."


class AdjustmentNotFoundException(NotFoundException):
    """Raised when an attendance adjustment cannot be found."""
    code = "ADJUSTMENT_NOT_FOUND"
    message = "Attendance adjustment not found."


class AdjustmentExistsException(ConflictException):
    """Raised when an attendance adjustment already exists."""
    code = "ADJUSTMENT_EXISTS"
    message = "Attendance adjustment already exists for this date."


class EmployeeNotFoundException(NotFoundException):
    """Raised when an employee is not found."""
    code = "EMPLOYEE_NOT_FOUND"
    message = "Employee not found."
