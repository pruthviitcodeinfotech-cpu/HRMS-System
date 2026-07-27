"""User Profile — Pydantic DTOs.

A self-service projection over rows the user already owns or belongs to
(``users``, ``employees``, ``organizations``, ``branches``, ``rights_templates``).
Only ``mobile_number`` / ``mobile_country_code`` and the profile photo are
editable; every other field on :class:`ProfileSchema` is read-only.
"""

from __future__ import annotations

import re
import string
from datetime import date, datetime

from pydantic import Field, field_validator, model_validator

from app.shared.base.schema import BaseSchema
from app.shared.utils.validators import is_valid_phone, normalize_phone


def _validate_phone(value: str) -> str:
    """Normalise and validate a phone number (7-15 digits, optional ``+``)."""
    normalised = normalize_phone(value)
    if not is_valid_phone(normalised):
        raise ValueError("invalid phone number")
    return normalised


_SPECIAL_CHARS = set(string.punctuation)


def _validate_strong_password(value: str) -> str:
    """Enforce a minimum complexity bar: upper, lower, digit, and special char.

    Length is enforced separately via the field's ``min_length``/``max_length`` so
    the error messages stay distinct and specific.
    """
    problems: list[str] = []
    if not re.search(r"[A-Z]", value):
        problems.append("one uppercase letter")
    if not re.search(r"[a-z]", value):
        problems.append("one lowercase letter")
    if not re.search(r"\d", value):
        problems.append("one digit")
    if not any(ch in _SPECIAL_CHARS for ch in value):
        problems.append("one special character")
    if problems:
        raise ValueError(f"Password must contain at least {', '.join(problems)}.")
    return value


# ===========================================================================
# Read-only summaries embedded in the profile response
# ===========================================================================


class OrganizationSummary(BaseSchema):
    """Compact organization projection embedded in the profile response."""

    org_id: int = Field(..., description="Organization / tenant PK.")
    org_code: str = Field(..., description="Globally unique tenant code.")
    org_name: str = Field(..., description="Organization display name.")
    contact_phone: str | None = Field(default=None, description="Organization contact phone.")
    contact_email: str | None = Field(default=None, description="Organization contact email.")
    is_active: bool = Field(..., description="Whether the tenant is active.")


class BranchSummary(BaseSchema):
    """Compact branch projection embedded in the profile response."""

    branch_id: int = Field(..., description="Branch PK.")
    branch_name: str = Field(..., description="Branch name.")
    address: str | None = Field(default=None, description="Full address.")
    city: str | None = Field(default=None, description="City.")
    state: str | None = Field(default=None, description="State / province.")
    country: str | None = Field(default=None, description="Country.")


class EmployeeSummary(BaseSchema):
    """Compact HR-record projection embedded in the profile response."""

    employee_id: int = Field(..., description="Employee PK.")
    employee_code: str = Field(..., description="Employee code.")
    employee_name: str = Field(..., description="Employee's full name.")
    department_name: str | None = Field(default=None, description="Department name.")
    designation_name: str | None = Field(default=None, description="Designation name.")
    date_of_joining: date | None = Field(default=None, description="Date of joining.")


# ===========================================================================
# GET /profile
# ===========================================================================


class ProfileSchema(BaseSchema):
    """``GET /profile`` — the caller's own identity, org, branch, and role."""

    user_id: int = Field(..., description="User PK.")
    name: str = Field(..., description="Display name.")
    email: str = Field(..., description="Login email (read-only here).")
    mobile_country_code: str = Field(..., description="Mobile country code, e.g. '+91'.")
    mobile_number: str = Field(..., description="Mobile number.")
    is_super_admin: bool = Field(..., description="Whether the account is a platform super-admin.")
    is_active: bool = Field(..., description="Whether the account is active.")
    role_name: str | None = Field(default=None, description="Assigned rights-template name.")
    profile_photo_url: str | None = Field(
        default=None, description="Storage key of the linked employee's profile photo, if any."
    )
    last_login_at: datetime | None = Field(default=None, description="Last successful login.")
    created_at: datetime = Field(..., description="Account creation timestamp.")
    organization: OrganizationSummary = Field(..., description="Owning organization.")
    branch: BranchSummary | None = Field(
        default=None, description="Linked employee's master branch, if any."
    )
    employee: EmployeeSummary | None = Field(
        default=None, description="Linked employee HR record, if any."
    )


# ===========================================================================
# PUT /profile
# ===========================================================================


class ProfileUpdateRequest(BaseSchema):
    """``PUT /profile`` — only the mobile number is editable."""

    mobile_country_code: str | None = Field(
        default=None, max_length=10, description="Mobile country code, e.g. '+91'."
    )
    mobile_number: str | None = Field(
        default=None, min_length=1, max_length=20, description="New mobile number."
    )

    @field_validator("mobile_number")
    @classmethod
    def _phone(cls, value: str | None) -> str | None:
        return _validate_phone(value) if value is not None else None

    @model_validator(mode="after")
    def _require_a_field(self) -> ProfileUpdateRequest:
        if self.mobile_number is None and self.mobile_country_code is None:
            raise ValueError("At least one editable field must be provided.")
        return self


# ===========================================================================
# PUT /profile/change-password
# ===========================================================================


class ChangePasswordRequest(BaseSchema):
    """``PUT /profile/change-password`` — self-service password change."""

    # Not stripped/normalised: whitespace can be a significant part of a password.
    model_config = {**BaseSchema.model_config, "str_strip_whitespace": False}

    current_password: str = Field(..., min_length=1, description="The account's current password.")
    new_password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description=(
            "The new password. Must contain at least one uppercase letter, one "
            "lowercase letter, one digit, and one special character."
        ),
    )
    confirm_password: str = Field(..., min_length=1, description="Must match ``new_password``.")

    @field_validator("new_password")
    @classmethod
    def _strength(cls, value: str) -> str:
        return _validate_strong_password(value)

    @model_validator(mode="after")
    def _validate(self) -> ChangePasswordRequest:
        if self.new_password != self.confirm_password:
            raise ValueError("new_password and confirm_password must match.")
        if self.new_password == self.current_password:
            raise ValueError("New password must be different from the current password.")
        return self


# ===========================================================================
# PUT /profile/photo
# ===========================================================================


class ProfilePhotoResponse(BaseSchema):
    """Response for a successful profile-photo upload."""

    profile_photo_url: str = Field(..., description="Storage key of the stored profile photo.")


class ChangePasswordResponse(BaseSchema):
    """Response for a successful password change."""

    revoked_session_count: int = Field(
        ..., description="Number of other active sessions that were logged out."
    )


__all__ = [
    "OrganizationSummary",
    "BranchSummary",
    "EmployeeSummary",
    "ProfileSchema",
    "ProfileUpdateRequest",
    "ChangePasswordRequest",
    "ChangePasswordResponse",
    "ProfilePhotoResponse",
]
