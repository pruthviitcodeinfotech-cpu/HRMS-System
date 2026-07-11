"""Employee Management — module-specific exception types.

Each type specialises a shared :mod:`app.core.exceptions.base` exception so the
registered handlers map it to the right HTTP status and the contract's stable
machine-readable ``code`` (Employee-Management API Contract §12) without any
router-level ``HTTPException``.
"""

from __future__ import annotations

from app.core.exceptions.base import ConflictException, NotFoundException


class EmployeeNotFoundException(NotFoundException):
    """The referenced employee does not exist in the caller's organisation."""

    code = "EMPLOYEE_NOT_FOUND"
    message = "The requested employee was not found."


class EmployeeAlreadyTerminatedException(ConflictException):
    """The employee is already terminated — ``terminated`` is a terminal status."""

    code = "EMPLOYEE_ALREADY_TERMINATED"
    message = "The employee has already been terminated."


class BranchNotFoundException(NotFoundException):
    """The referenced branch does not exist (or is inactive) in the caller's organisation."""

    code = "BRANCH_NOT_FOUND"
    message = "The requested branch was not found."


class DepartmentNotFoundException(NotFoundException):
    """The referenced department does not exist (or is inactive) in the caller's organisation."""

    code = "DEPARTMENT_NOT_FOUND"
    message = "The requested department was not found."


class DesignationNotFoundException(NotFoundException):
    """The referenced designation does not exist (or is inactive) in the caller's organisation."""

    code = "DESIGNATION_NOT_FOUND"
    message = "The requested designation was not found."


class DocumentNotFoundException(NotFoundException):
    """The referenced employee document does not exist for this employee/org."""

    code = "DOCUMENT_NOT_FOUND"
    message = "The requested document was not found."


class BankDetailNotFoundException(NotFoundException):
    """The referenced bank detail does not exist for this employee/org."""

    code = "BANK_DETAIL_NOT_FOUND"
    message = "The requested bank detail was not found."


class EmergencyContactNotFoundException(NotFoundException):
    """The referenced emergency contact does not exist for this employee/org."""

    code = "EMERGENCY_CONTACT_NOT_FOUND"
    message = "The requested emergency contact was not found."


class ReferenceNotFoundException(NotFoundException):
    """The referenced employee reference does not exist for this employee/org."""

    code = "REFERENCE_NOT_FOUND"
    message = "The requested reference was not found."


class TagNotFoundException(NotFoundException):
    """The referenced employee tag does not exist for this employee/org."""

    code = "TAG_NOT_FOUND"
    message = "The requested tag was not found."


__all__ = [
    "EmployeeNotFoundException",
    "EmployeeAlreadyTerminatedException",
    "BranchNotFoundException",
    "DepartmentNotFoundException",
    "DesignationNotFoundException",
    "DocumentNotFoundException",
    "BankDetailNotFoundException",
    "EmergencyContactNotFoundException",
    "ReferenceNotFoundException",
    "TagNotFoundException",
]
