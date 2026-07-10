"""Settlements module-specific exception types.

Maps to the error codes defined in the approved Settlement Management API Contract.
"""

from __future__ import annotations

from app.core.exceptions.base import ConflictException, NotFoundException, ValidationException


class LoanAdvanceNotFoundException(NotFoundException):
    """Raised when a loan/advance registry is not found."""

    code = "LOAN_ADVANCE_NOT_FOUND"
    message = "Loan/advance registry not found."


class LoanAdvanceClosedException(ConflictException):
    """Raised when trying to update or transact on a closed loan/advance registry."""

    code = "LOAN_ADVANCE_CLOSED"
    message = "Loan/advance registry is closed."


class LoanAdvanceHasTransactionsException(ConflictException):
    """Raised when trying to delete a loan/advance registry that already has ledger entries."""

    code = "LOAN_ADVANCE_HAS_TRANSACTIONS"
    message = "Loan/advance registry cannot be deleted because it has transactions."


class ArrearsNotFoundException(NotFoundException):
    """Raised when an employee's arrears record is not found."""

    code = "ARREARS_NOT_FOUND"
    message = "Arrears record not found."


class InsufficientArrearsException(ConflictException):
    """Raised when a debit transaction exceeds outstanding arrears."""

    code = "INSUFFICIENT_ARREARS"
    message = "Insufficient arrears available."


class EmployeeNotFoundException(NotFoundException):
    """Raised when a referenced employee is not found."""

    code = "EMPLOYEE_NOT_FOUND"
    message = "Employee not found."


class InvalidTransactionException(ValidationException):
    """Raised when a transaction payload or business rule validation fails."""

    code = "INVALID_TRANSACTION"
    message = "Invalid ledger transaction."


class EmployeeNotExitedException(ConflictException):
    """Full & Final settlement was attempted for an employee who has not exited."""

    code = "EMPLOYEE_NOT_EXITED"
    message = "Full & Final settlement requires the employee to have exited."


class PayrollNotFinalizedException(ConflictException):
    """No finalized payroll run covers the employee's last working day."""

    code = "PAYROLL_NOT_FINALIZED"
    message = (
        "Full & Final settlement requires a finalized payroll run covering the "
        "employee's last working day."
    )


class SettlementAlreadyFinalizedException(ConflictException):
    """The employee's Full & Final settlement has already been finalized."""

    code = "SETTLEMENT_ALREADY_FINALIZED"
    message = "Full & Final settlement has already been finalized for this employee."
