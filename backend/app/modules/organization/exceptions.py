"""Organization / Branch / Department / Designation — module-specific exceptions.

Each type specialises a shared :mod:`app.core.exceptions.base` exception so the
registered handlers map it to the right HTTP status and the contract's stable
machine-readable ``code`` (API Contract §12) without any router-level
``HTTPException``.
"""

from __future__ import annotations

from app.core.exceptions.base import ConflictException, NotFoundException, ValidationException


class OrganizationNotFoundException(NotFoundException):
    """The referenced organization does not exist (or is out of the caller's scope)."""

    code = "ORG_NOT_FOUND"
    message = "The requested organization was not found."


class OrganizationCodeExistsException(ConflictException):
    """``org_code`` is already registered (it is globally unique)."""

    code = "ORG_CODE_EXISTS"
    message = "An organization with this code already exists."


class BranchNotFoundException(NotFoundException):
    """The referenced branch does not exist in the caller's organization."""

    code = "BRANCH_NOT_FOUND"
    message = "The requested branch was not found."


class BranchInUseException(ConflictException):
    """The branch is still referenced by active employees and cannot be changed."""

    code = "BRANCH_IN_USE"
    message = "This branch is referenced by active employees and cannot be deactivated."


class BranchNameExistsException(ConflictException):
    """A non-deleted branch with the same name already exists in the organization."""

    code = "BRANCH_NAME_EXISTS"
    message = "A branch with this name already exists in this organization."


class BranchRequiredException(ValidationException):
    """``branch_id`` is mandatory for this operation."""

    code = "BRANCH_ID_REQUIRED"
    message = "branch_id is required."


class DepartmentNotFoundException(NotFoundException):
    """The referenced department does not exist in the caller's organization."""

    code = "DEPARTMENT_NOT_FOUND"
    message = "The requested department was not found."


class DepartmentNameExistsException(ConflictException):
    """A non-deleted department with the same name already exists in the branch."""

    code = "DEPARTMENT_NAME_EXISTS"
    message = "A department with this name already exists in this branch."


class DepartmentInUseException(ConflictException):
    """The department is still referenced by active employees and cannot be changed."""

    code = "DEPARTMENT_IN_USE"
    message = "This department is referenced by active employees and cannot be deactivated."


class DesignationNotFoundException(NotFoundException):
    """The referenced designation does not exist in the caller's organization."""

    code = "DESIGNATION_NOT_FOUND"
    message = "The requested designation was not found."


class DesignationNameExistsException(ConflictException):
    """A non-deleted designation with the same name already exists in the branch."""

    code = "DESIGNATION_NAME_EXISTS"
    message = "A designation with this name already exists in this branch."


class DesignationInUseException(ConflictException):
    """The designation is still referenced by active employees and cannot be changed."""

    code = "DESIGNATION_IN_USE"
    message = "This designation is referenced by active employees and cannot be deactivated."


__all__ = [
    "OrganizationNotFoundException",
    "OrganizationCodeExistsException",
    "BranchNotFoundException",
    "BranchInUseException",
    "BranchNameExistsException",
    "BranchRequiredException",
    "DepartmentNotFoundException",
    "DepartmentNameExistsException",
    "DepartmentInUseException",
    "DesignationNotFoundException",
    "DesignationNameExistsException",
    "DesignationInUseException",
]

