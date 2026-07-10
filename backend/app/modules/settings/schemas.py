"""Settings Management — Pydantic request/response schemas (DTOs).

Defines validation, serialization, and structure rules for organization settings,
salary-slip settings, features configurations, and cross-module reference pointers.
"""

from __future__ import annotations

import datetime

from pydantic import Field, field_validator

from app.shared.base.schema import BaseSchema

# ===========================================================================
# 1. Organization / System Settings DTOs
# ===========================================================================


class OrgSettingsResponse(BaseSchema):
    """Response DTO for organization-level settings, with sensitive fields masked."""

    id: int = Field(..., description="Primary key identifier.")
    org_id: int = Field(..., description="Organization tenant context ID.")
    advance_shift_enabled: bool = Field(..., description="Whether advance shifts are enabled.")
    enable_regularization: bool = Field(
        ..., description="Whether attendance regularization is enabled."
    )
    enable_photo_punch: bool = Field(
        ..., description="Whether photo punch verification is enabled."
    )
    device_sync_time: datetime.time = Field(
        ..., description="Scheduled daily device synchronization time."
    )
    sync_code: str = Field(..., description="Sync code used for device registration.")
    pass_code: str = Field(..., description="Sensitive pass code masked in output.")
    updated_by: int | None = Field(
        None, description="ID of the user who last updated this configuration."
    )
    created_at: datetime.datetime = Field(..., description="Creation timestamp.")
    updated_at: datetime.datetime = Field(..., description="Last updated timestamp.")

    @field_validator("pass_code")
    @classmethod
    def _mask_pass_code(cls, v: str) -> str:
        """Always mask sensitive passcode in responses."""
        return "********"


class OrgSettingsUpdateRequest(BaseSchema):
    """Payload for updating organization settings."""

    advance_shift_enabled: bool | None = Field(
        default=None, description="Enable or disable advance shifts."
    )
    enable_regularization: bool | None = Field(
        default=None, description="Enable or disable attendance regularization."
    )
    enable_photo_punch: bool | None = Field(
        default=None, description="Enable or disable photo punch verification."
    )
    device_sync_time: datetime.time | None = Field(
        default=None, description="Scheduled daily device synchronization time."
    )
    sync_code: str | None = Field(
        default=None, max_length=50, description="Device sync synchronization code."
    )
    pass_code: str | None = Field(
        default=None, max_length=20, description="Device pairing pass code."
    )


# ===========================================================================
# 2. Salary-Slip (Payslip) Settings DTOs
# ===========================================================================


class OrgSalarySlipResponse(BaseSchema):
    """Response DTO representing salary slip brand and release settings."""

    id: int = Field(..., description="Primary key identifier.")
    org_id: int = Field(..., description="Organization tenant context ID.")
    company_logo_url: str | None = Field(None, description="URL to organization logo image.")
    company_name: str = Field(..., description="Legal company name printed on payslips.")
    company_address: str = Field(..., description="Company address printed on payslips.")
    company_contact: str = Field(..., description="Contact telephone printed on payslips.")
    company_website_email: str | None = Field(None, description="Company website or support email.")
    auto_release_payslip: bool = Field(
        ..., description="Whether payslips are automatically released on finalization."
    )
    branch_wise_payslip: bool = Field(
        ..., description="Whether payslip releases are managed per branch."
    )
    updated_by: int | None = Field(
        None, description="ID of the user who last updated this configuration."
    )
    created_at: datetime.datetime = Field(..., description="Creation timestamp.")
    updated_at: datetime.datetime = Field(..., description="Last updated timestamp.")


class OrgSalarySlipUpdateRequest(BaseSchema):
    """Payload for updating salary slip settings."""

    company_logo_url: str | None = Field(
        default=None, description="URL of uploaded company logo image."
    )
    company_name: str | None = Field(
        default=None, max_length=200, description="Legal company name."
    )
    company_address: str | None = Field(default=None, description="Company address.")
    company_contact: str | None = Field(
        default=None, max_length=100, description="Company contact details."
    )
    company_website_email: str | None = Field(
        default=None, max_length=200, description="Company email or website URL."
    )
    auto_release_payslip: bool | None = Field(
        default=None, description="Automatically release payslips upon payroll finalization."
    )
    branch_wise_payslip: bool | None = Field(
        default=None, description="Whether to generate branch-isolated payslips."
    )

    @field_validator("company_website_email")
    @classmethod
    def _validate_email(cls, v: str | None) -> str | None:
        """Validate email format if provided and is an email string."""
        if v is not None and v.strip() != "":
            # Validate if it contains '@', otherwise treat as URL/website
            if "@" in v:
                from app.shared.utils.validators import is_valid_email

                normalised = v.strip().lower()
                if not is_valid_email(normalised):
                    raise ValueError("invalid email format")
                return normalised
        return v


# ===========================================================================
# 3. Features & Cross-Module Configuration View DTOs
# ===========================================================================


class ModulePointerSchema(BaseSchema):
    """Reference metadata highlighting an external module owning certain settings."""

    module: str = Field(..., description="Name of the module owning this setting category.")
    description: str = Field(..., description="Brief description of configuration scope.")


class ConfigurationViewResponse(BaseSchema):
    """Combined configurations view returned to client."""

    organization: OrgSettingsResponse | None = Field(
        default=None, description="Primary organization configuration settings."
    )
    salary_slip: OrgSalarySlipResponse | None = Field(
        default=None, description="Organization payslip configuration settings."
    )
    cross_module_pointers: dict[str, ModulePointerSchema] = Field(
        default_factory=dict,
        description="References to settings owned and managed by other modules.",
    )


class FeaturesResponse(BaseSchema):
    """List of fixed settings features toggles status."""

    features: dict[str, bool] = Field(
        ...,
        description="Mapping of fixed system feature toggle keys to their active state.",
    )


class FeatureToggleRequest(BaseSchema):
    """Payload to toggle the active state of a system feature."""

    enabled: bool = Field(
        ..., description="Set to true to enable, or false to disable the feature."
    )
