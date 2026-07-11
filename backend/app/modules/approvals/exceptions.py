"""Approval Management exception definitions."""

from app.core.exceptions.base import (
    AuthorizationException,
    ConflictException,
    NotFoundException,
    ValidationException,
)


class ApprovalNotFoundException(NotFoundException):
    """Raised when an approval request cannot be found or is out of organization scope."""
    code = "APPROVAL_NOT_FOUND"
    message = "Approval request not found."


class ApprovalAlreadyDecidedException(ConflictException):
    """Raised when trying to approve/reject an already decided request."""
    code = "APPROVAL_ALREADY_DECIDED"
    message = "Approval request has already been decided."


class RejectRemarksRequiredException(ValidationException):
    """Raised when rejecting a request without providing reject remarks."""
    code = "REJECT_REMARKS_REQUIRED"
    message = "Rejection remarks are required."


class ApprovalForbiddenScopeException(AuthorizationException):
    """Raised when a user attempts to access or decide a request outside their branch/department
    data scope."""
    code = "APPROVAL_FORBIDDEN_SCOPE"
    message = "You do not have permission to access approvals in this data scope."


class SelfApprovalNotAllowedException(ConflictException):
    """Raised when an employee attempts to approve their own request."""
    code = "SELF_APPROVAL_NOT_ALLOWED"
    message = "Approving your own request is not permitted."
