"""Approval Requests module: constants and enums.

Enums mirror the CHECK-constraint value sets in the approved Approval Requests
Database Architecture. Native PostgreSQL ENUM types are intentionally NOT used —
the architecture models these as VARCHAR columns with CHECK constraints, and
that is preserved.
"""

from enum import Enum


class RequestType(str, Enum):
    """approval_requests.request_type. (Enforced by DB CHECK.)"""

    ATTENDANCE = "attendance"
    LEAVE = "leave"
    LOGIN_RESET = "login_reset"


class ApprovalStatus(str, Enum):
    """status on approval_requests / attendance_regularization_requests /
    login_reset_requests. (Enforced by DB CHECK on each table.)"""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
