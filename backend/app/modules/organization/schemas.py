"""Organization / Branch / Department / Designation — Pydantic DTOs.

Request schemas enforce the field-level validation rules from API Contract §4/§5
and §10 (lengths, geo ranges, email format). Response schemas are ORM-backed
(``from_attributes``) and never expose SQLAlchemy models directly.

``email-validator`` is not a project dependency, so ``contact_email`` is validated
with a conservative regex rather than :class:`pydantic.EmailStr`.
"""

from __future__ import annotations

import re
from datetime import datetime
from decimal import Decimal

from pydantic import Field, field_validator

from app.modules.organization.constants import (
    BRANCH_SORTS,
    DEPARTMENT_SORTS,
    DESIGNATION_SORTS,
    ORGANIZATION_SORTS,
)
from app.shared.base.schema import BaseSchema
from app.shared.schemas.pagination import PaginatedResponse, PaginationRequest

_EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _validate_email(v: str | None) -> str | None:
    """Validate a contact email address (best-effort, no DNS lookup)."""
    if v is None:
        return v
    v = v.strip()
    if not v:
        return None
    if not _EMAIL_REGEX.match(v):
        raise ValueError("Invalid email address format.")
    return v


# ===========================================================================
# Organization (§4)
# ===========================================================================


class OrganizationCreateRequest(BaseSchema):
    """Payload for provisioning a new organization (super-admin)."""

    org_code: str = Field(..., min_length=1, max_length=20, description="Globally unique code.")
    org_name: str = Field(..., min_length=1, max_length=200, description="Display name.")
    contact_phone: str | None = Field(default=None, max_length=20, description="Contact phone.")
    contact_email: str | None = Field(default=None, max_length=150, description="Contact email.")

    @field_validator("contact_email")
    @classmethod
    def _email(cls, v: str | None) -> str | None:
        return _validate_email(v)


class OrganizationUpdateRequest(BaseSchema):
    """Payload for updating an organization profile (PATCH — all optional)."""

    org_code: str | None = Field(
        default=None, min_length=1, max_length=20, description="Unique code."
    )
    org_name: str | None = Field(
        default=None, min_length=1, max_length=200, description="Display name."
    )
    contact_phone: str | None = Field(default=None, max_length=20, description="Contact phone.")
    contact_email: str | None = Field(default=None, max_length=150, description="Contact email.")

    @field_validator("contact_email")
    @classmethod
    def _email(cls, v: str | None) -> str | None:
        return _validate_email(v)


class OrganizationSchema(BaseSchema):
    """Full organization detail response."""

    org_id: int = Field(..., description="Organization / tenant PK.")
    org_code: str = Field(..., description="Globally unique tenant code.")
    org_name: str = Field(..., description="Organization display name.")
    contact_phone: str | None = Field(default=None, description="Primary contact phone.")
    contact_email: str | None = Field(default=None, description="Primary contact email.")
    is_active: bool = Field(..., description="Whether the tenant is active.")
    is_deleted: bool = Field(..., description="Soft-delete flag.")
    created_at: datetime = Field(..., description="Creation timestamp.")
    updated_at: datetime = Field(..., description="Last update timestamp.")


class OrganizationListResponse(PaginatedResponse[OrganizationSchema]):
    """Paginated list response for organizations."""


class OrganizationSearchQuery(PaginationRequest):
    """Query parameters for listing organizations."""

    search: str | None = Field(default=None, description="Free-text search on code / name.")
    is_active: bool | None = Field(default=None, description="Filter by active flag.")
    include_deleted: bool = Field(default=False, description="Include soft-deleted rows.")
    sort_by: str | None = Field(
        default=None, description=f"Sort field, one of {sorted(ORGANIZATION_SORTS)}."
    )
    sort_order: str | None = Field(default=None, description="Sort order: asc, desc.")


# ===========================================================================
# Branch (§5.1)
# ===========================================================================


class BranchCreateRequest(BaseSchema):
    """Payload for creating a branch."""

    branch_name: str = Field(..., min_length=1, max_length=200, description="Branch name.")
    logo_url: str | None = Field(default=None, description="Branch logo URL.")
    gstin: str | None = Field(default=None, max_length=20, description="GST identification number.")
    mobile_number: str | None = Field(default=None, max_length=20, description="Contact mobile.")
    address: str | None = Field(default=None, description="Full address.")
    landmark: str | None = Field(default=None, max_length=200, description="Nearby landmark.")
    pin_code: str | None = Field(default=None, max_length=10, description="Postal / PIN code.")
    city: str | None = Field(default=None, max_length=100, description="City.")
    state: str | None = Field(default=None, max_length=100, description="State / province.")
    country: str | None = Field(default=None, max_length=100, description="Country.")
    industry_type: str | None = Field(default=None, max_length=100, description="Industry type.")
    latitude: Decimal | None = Field(
        default=None, ge=Decimal("-90"), le=Decimal("90"), description="Latitude."
    )
    longitude: Decimal | None = Field(
        default=None, ge=Decimal("-180"), le=Decimal("180"), description="Longitude."
    )
    allowed_radius_meters: int | None = Field(
        default=None, gt=0, le=32767, description="Geofence radius (m)."
    )


class BranchUpdateRequest(BaseSchema):
    """Payload for updating a branch (PATCH — all optional)."""

    branch_name: str | None = Field(
        default=None, min_length=1, max_length=200, description="Branch name."
    )
    logo_url: str | None = Field(default=None, description="Branch logo URL.")
    gstin: str | None = Field(default=None, max_length=20, description="GST identification number.")
    mobile_number: str | None = Field(default=None, max_length=20, description="Contact mobile.")
    address: str | None = Field(default=None, description="Full address.")
    landmark: str | None = Field(default=None, max_length=200, description="Nearby landmark.")
    pin_code: str | None = Field(default=None, max_length=10, description="Postal / PIN code.")
    city: str | None = Field(default=None, max_length=100, description="City.")
    state: str | None = Field(default=None, max_length=100, description="State / province.")
    country: str | None = Field(default=None, max_length=100, description="Country.")
    industry_type: str | None = Field(default=None, max_length=100, description="Industry type.")
    latitude: Decimal | None = Field(
        default=None, ge=Decimal("-90"), le=Decimal("90"), description="Latitude."
    )
    longitude: Decimal | None = Field(
        default=None, ge=Decimal("-180"), le=Decimal("180"), description="Longitude."
    )
    allowed_radius_meters: int | None = Field(
        default=None, gt=0, le=32767, description="Geofence radius (m)."
    )


class BranchSchema(BaseSchema):
    """Full branch detail response."""

    branch_id: int = Field(..., description="Branch PK.")
    org_id: int = Field(..., description="Owning organization id.")
    branch_name: str = Field(..., description="Branch name.")
    logo_url: str | None = Field(default=None, description="Branch logo URL.")
    gstin: str | None = Field(default=None, description="GST identification number.")
    mobile_number: str | None = Field(default=None, description="Branch contact mobile.")
    address: str | None = Field(default=None, description="Full address.")
    landmark: str | None = Field(default=None, description="Nearby landmark.")
    pin_code: str | None = Field(default=None, description="Postal / PIN code.")
    city: str | None = Field(default=None, description="City.")
    state: str | None = Field(default=None, description="State / province.")
    country: str | None = Field(default=None, description="Country.")
    industry_type: str | None = Field(default=None, description="Industry type.")
    latitude: Decimal | None = Field(default=None, description="Geo latitude.")
    longitude: Decimal | None = Field(default=None, description="Geo longitude.")
    allowed_radius_meters: int | None = Field(default=None, description="Geofence radius (m).")
    is_active: bool = Field(..., description="Whether the branch is active.")
    is_deleted: bool = Field(..., description="Soft-delete flag.")
    employee_count: int = Field(default=0, description="Count of active employees in this branch.")
    created_at: datetime = Field(..., description="Creation timestamp.")
    updated_at: datetime = Field(..., description="Last update timestamp.")


class BranchListResponse(PaginatedResponse[BranchSchema]):
    """Paginated list response for branches."""


class BranchSearchQuery(PaginationRequest):
    """Query parameters for listing branches."""

    search: str | None = Field(default=None, description="Free-text search on name / city.")
    is_active: bool | None = Field(default=None, description="Filter by active flag.")
    include_deleted: bool = Field(default=False, description="Include soft-deleted rows.")
    sort_by: str | None = Field(
        default=None, description=f"Sort field, one of {sorted(BRANCH_SORTS)}."
    )
    sort_order: str | None = Field(default=None, description="Sort order: asc, desc.")


# ===========================================================================
# Department (§5.2)
# ===========================================================================


class DepartmentCreateRequest(BaseSchema):
    """Payload for creating a department."""

    dept_name: str = Field(..., min_length=1, max_length=150, description="Name (unique per org).")


class DepartmentUpdateRequest(BaseSchema):
    """Payload for updating a department (PATCH — all optional)."""

    dept_name: str | None = Field(
        default=None, min_length=1, max_length=150, description="Department name."
    )


class DepartmentSchema(BaseSchema):
    """Full department detail response."""

    dept_id: int = Field(..., description="Department PK.")
    org_id: int = Field(..., description="Owning organization id.")
    dept_name: str = Field(..., description="Department name.")
    is_active: bool = Field(..., description="Whether the department is active.")
    is_deleted: bool = Field(..., description="Soft-delete flag.")
    created_by: int | None = Field(default=None, description="Creator user id.")
    created_at: datetime = Field(..., description="Creation timestamp.")
    updated_at: datetime = Field(..., description="Last update timestamp.")
    employee_count: int = Field(default=0, description="Count of active employees in this department.")


class DepartmentListResponse(PaginatedResponse[DepartmentSchema]):
    """Paginated list response for departments."""


class DepartmentSearchQuery(PaginationRequest):
    """Query parameters for listing departments."""

    search: str | None = Field(default=None, description="Free-text search on department name.")
    is_active: bool | None = Field(default=None, description="Filter by active flag.")
    include_deleted: bool = Field(default=False, description="Include soft-deleted rows.")
    sort_by: str | None = Field(
        default=None, description=f"Sort field, one of {sorted(DEPARTMENT_SORTS)}."
    )
    sort_order: str | None = Field(default=None, description="Sort order: asc, desc.")


# ===========================================================================
# Designation (§5.3)
# ===========================================================================


class DesignationCreateRequest(BaseSchema):
    """Payload for creating a designation."""

    designation_name: str = Field(
        ..., min_length=1, max_length=150, description="Name (unique per org)."
    )


class DesignationUpdateRequest(BaseSchema):
    """Payload for updating a designation (PATCH — all optional)."""

    designation_name: str | None = Field(
        default=None, min_length=1, max_length=150, description="Name."
    )


class DesignationSchema(BaseSchema):
    """Full designation detail response."""

    designation_id: int = Field(..., description="Designation PK.")
    org_id: int = Field(..., description="Owning organization id.")
    designation_name: str = Field(..., description="Designation name.")
    is_active: bool = Field(..., description="Whether the designation is active.")
    is_deleted: bool = Field(..., description="Soft-delete flag.")
    created_by: int | None = Field(default=None, description="Creator user id.")
    created_at: datetime = Field(..., description="Creation timestamp.")
    updated_at: datetime = Field(..., description="Last update timestamp.")
    employee_count: int = Field(default=0, description="Count of active employees in this designation.")


class DesignationListResponse(PaginatedResponse[DesignationSchema]):
    """Paginated list response for designations."""


class DesignationSearchQuery(PaginationRequest):
    """Query parameters for listing designations."""

    search: str | None = Field(default=None, description="Free-text search on designation name.")
    is_active: bool | None = Field(default=None, description="Filter by active flag.")
    include_deleted: bool = Field(default=False, description="Include soft-deleted rows.")
    sort_by: str | None = Field(
        default=None, description=f"Sort field, one of {sorted(DESIGNATION_SORTS)}."
    )
    sort_order: str | None = Field(default=None, description="Sort order: asc, desc.")


__all__ = [
    "OrganizationCreateRequest",
    "OrganizationUpdateRequest",
    "OrganizationSchema",
    "OrganizationListResponse",
    "OrganizationSearchQuery",
    "BranchCreateRequest",
    "BranchUpdateRequest",
    "BranchSchema",
    "BranchListResponse",
    "BranchSearchQuery",
    "DepartmentCreateRequest",
    "DepartmentUpdateRequest",
    "DepartmentSchema",
    "DepartmentListResponse",
    "DepartmentSearchQuery",
    "DesignationCreateRequest",
    "DesignationUpdateRequest",
    "DesignationSchema",
    "DesignationListResponse",
    "DesignationSearchQuery",
]
