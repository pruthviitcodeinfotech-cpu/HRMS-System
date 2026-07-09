"""Leave & Holiday Management module-specific exception types.

Maps to the error codes defined in the approved Leave Management API Contract.
"""

from __future__ import annotations

from app.core.exceptions.base import ConflictException, NotFoundException


class LeaveTypeNotFoundException(NotFoundException):
    """Raised when a leave type is not found."""

    code = "LEAVE_TYPE_NOT_FOUND"
    message = "Leave type not found."


class LeaveTypeAliasExistsException(ConflictException):
    """Raised when a leave type with the same alias already exists."""

    code = "LEAVE_TYPE_ALIAS_EXISTS"
    message = "Leave type alias already exists."


class LeaveTypeInUseException(ConflictException):
    """Raised when a leave type cannot be deleted because it is in use."""

    code = "LEAVE_TYPE_IN_USE"
    message = "Leave type is currently in use."


class BalanceNotFoundException(NotFoundException):
    """Raised when an employee's leave balance record is not found."""

    code = "BALANCE_NOT_FOUND"
    message = "Leave balance record not found."


class InsufficientBalanceException(ConflictException):
    """Raised when an employee does not have sufficient leave balance."""

    code = "INSUFFICIENT_BALANCE"
    message = "Insufficient leave balance."


class LeaveRequestNotFoundException(NotFoundException):
    """Raised when a leave request is not found."""

    code = "LEAVE_REQUEST_NOT_FOUND"
    message = "Leave request not found."


class LeaveOverlapException(ConflictException):
    """Raised when a leave request overlaps with another request."""

    code = "LEAVE_OVERLAP"
    message = "Leave request overlaps with another request."


class LeaveNotEditableException(ConflictException):
    """Raised when trying to edit a leave request that is not pending."""

    code = "LEAVE_NOT_EDITABLE"
    message = "Only pending leave requests can be edited."


class LeaveNotCancellableException(ConflictException):
    """Raised when trying to cancel a leave request that is not pending."""

    code = "LEAVE_NOT_CANCELLABLE"
    message = "Only pending leave requests can be cancelled."


class HolidayTemplateNotFoundException(NotFoundException):
    """Raised when a holiday template is not found."""

    code = "HOLIDAY_TEMPLATE_NOT_FOUND"
    message = "Holiday template not found."


class HolidayTemplateNameExistsException(ConflictException):
    """Raised when a holiday template name already exists."""

    code = "HOLIDAY_TEMPLATE_NAME_EXISTS"
    message = "Holiday template name already exists."


class HolidayItemNotFoundException(NotFoundException):
    """Raised when a holiday item is not found."""

    code = "HOLIDAY_ITEM_NOT_FOUND"
    message = "Holiday item not found."


class EmployeeNotFoundException(NotFoundException):
    """Raised when an employee is not found."""

    code = "EMPLOYEE_NOT_FOUND"
    message = "Employee not found."
