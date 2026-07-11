"""Approval Management — Pydantic request/response schemas (DTOs).

Defines validation and serialization rules for approval request envelopes,
sub-record details, action payloads, timelines, and aggregates.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import Field, model_validator

from app.modules.approvals.constants import ApprovalStatus, RequestType
from app.shared.base.schema import BaseSchema
from app.shared.schemas.pagination import PaginatedResponse


class ApprovalRequestSchema(BaseSchema):
    """Response schema for representing an approval request envelope."""

    id: int = Field(..., description="Unique approval request ID.")
    org_id: int = Field(..., description="Organization ID.")
    request_type: RequestType = Field(..., description="Type of request: attendance, leave, "
        "login_reset.")
    request_subtype: str | None = Field(
        default=None, description="Optional subtype categorization."
    )
    reference_id: int = Field(..., description="Polymorphic reference ID of the source request.")
    employee_id: int = Field(..., description="Subject employee ID.")
    status: ApprovalStatus = Field(..., description="Current workflow status: pending, approved, "
        "rejected.")
    requested_at: datetime = Field(..., description="Timestamp when request was raised.")
    reviewed_at: datetime | None = Field(
        default=None, description="Timestamp when decision was applied."
    )
    reviewed_by: int | None = Field(default=None, description="User ID of reviewer.")
    reject_remarks: str | None = Field(
        default=None, description="Remarks for rejection / approval."
    )
    created_at: datetime = Field(..., description="Record creation timestamp.")


class ApprovalListResponse(PaginatedResponse[ApprovalRequestSchema]):
    """Paginated list response for approval request envelopes."""


class LoginResetRequestSchema(BaseSchema):
    """Response schema for a login credential reset detail record."""

    id: int = Field(..., description="Unique reset request ID.")
    employee_id: int = Field(..., description="Subject employee ID.")
    request_subtype: str | None = Field(default=None, description="Subtype description.")
    request_description: str = Field(..., description="Details of credential reset requested.")
    status: ApprovalStatus = Field(..., description="Status of request.")
    applied_on: datetime = Field(..., description="Submission timestamp.")
    reviewed_at: datetime | None = Field(default=None, description="Review timestamp.")
    reviewed_by: int | None = Field(default=None, description="User ID of reviewer.")
    reject_remarks: str | None = Field(default=None, description="Remarks/reasons for outcome.")
    created_at: datetime = Field(..., description="Creation timestamp.")
    updated_at: datetime = Field(..., description="Update timestamp.")


class ApprovalDetailsSchema(BaseSchema):
    """Details schema enclosing the envelope and resolved polymorphic source details."""

    approval: ApprovalRequestSchema = Field(..., description="The approval envelope record.")
    source: dict[str, Any] | None = Field(default=None, description="Resolved polymorphic source "
        "record fields.")


class ApprovalStatusSchema(BaseSchema):
    """Response schema representing current approval status and metadata."""

    status: ApprovalStatus = Field(..., description="Status: pending, approved, rejected.")
    reviewed_by: int | None = Field(default=None, description="User ID of reviewer.")
    reviewed_at: datetime | None = Field(default=None, description="Review timestamp.")
    reject_remarks: str | None = Field(default=None, description="Rejection remarks / comments.")


class ApprovalTimelineEventSchema(BaseSchema):
    """A single state event in the approval trail."""

    event: str = Field(..., description="Event name/type.")
    at: datetime = Field(..., description="Timestamp when the event occurred.")
    by: int | None = Field(default=None, description="User or employee ID associated with event.")
    remarks: str | None = Field(default=None, description="Associated remarks or notes.")


class ApprovalPendingCountSchema(BaseSchema):
    """Pending counts aggregation response schema."""

    pending_count: int = Field(..., description="Total count of pending requests.")
    by_request_type: dict[str, int] = Field(..., description="Counts breakdown grouped by request "
        "type.")


class ApproveRequestInput(BaseSchema):
    """Payload for approving a pending request."""

    remarks: str | None = Field(
        default=None, max_length=500, description="Optional reviewer remarks."
    )


class RejectRequestInput(BaseSchema):
    """Payload for rejecting a pending request."""

    reject_remarks: str = Field(..., max_length=500, description="Mandatory remarks explaining "
        "rejection.")

    @model_validator(mode="after")
    def validate_non_empty(self) -> RejectRequestInput:
        if not self.reject_remarks.strip():
            raise ValueError("reject_remarks must not be empty or whitespace.")
        return self


class BulkApproveRequestInput(BaseSchema):
    """Payload for approving multiple requests in bulk."""

    approval_ids: list[int] = Field(..., description="IDs of approvals to approve.")
    remarks: str | None = Field(
        default=None, max_length=500, description="Optional remarks for approval."
    )

    @model_validator(mode="after")
    def validate_ids(self) -> BulkApproveRequestInput:
        if not self.approval_ids:
            raise ValueError("approval_ids must contain at least one ID.")
        return self


class BulkRejectRequestInput(BaseSchema):
    """Payload for rejecting multiple requests in bulk."""

    approval_ids: list[int] = Field(..., description="IDs of approvals to reject.")
    reject_remarks: str = Field(..., max_length=500, description="Mandatory remarks for rejection.")

    @model_validator(mode="after")
    def validate_ids_and_remarks(self) -> BulkRejectRequestInput:
        if not self.approval_ids:
            raise ValueError("approval_ids must contain at least one ID.")
        if not self.reject_remarks.strip():
            raise ValueError("reject_remarks must not be empty or whitespace.")
        return self


class BulkActionItemError(BaseSchema):
    """Error detail for a failed bulk item action."""

    code: str = Field(..., description="Stable error code.")
    message: str = Field(..., description="Human-readable error description.")


class BulkActionItemResultSchema(BaseSchema):
    """Outcome for a single bulk item action."""

    id: int = Field(..., description="ID of approval request.")
    success: bool = Field(..., description="True if action succeeded, False otherwise.")
    error: BulkActionItemError | None = Field(default=None, description="Error detail if failed.")


class BulkActionResponseSchema(BaseSchema):
    """Overall outcome of a bulk approval/rejection request."""

    results: list[
        BulkActionItemResultSchema
    ] = Field(..., description="Outcomes of each requested action.")


__all__ = [
    "ApprovalRequestSchema",
    "ApprovalListResponse",
    "LoginResetRequestSchema",
    "ApprovalDetailsSchema",
    "ApprovalStatusSchema",
    "ApprovalTimelineEventSchema",
    "ApprovalPendingCountSchema",
    "ApproveRequestInput",
    "RejectRequestInput",
    "BulkApproveRequestInput",
    "BulkRejectRequestInput",
    "BulkActionItemError",
    "BulkActionItemResultSchema",
    "BulkActionResponseSchema",
]
