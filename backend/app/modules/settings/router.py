"""Settings Management — HTTP routes (thin controllers).

Maps every endpoint in the approved Settings Management API Contract onto FastAPI
handlers. Controllers resolve dependencies, call SettingsService, and return
standard SuccessResponse envelopes. No business logic lives here.

Sections:
  1. GET  /settings                               — Combined configuration view
  2. GET  /settings/organization                  — Get org settings
  3. PATCH /settings/organization                 — Update org settings
  4. POST  /settings/organization/reset           — Reset org settings
  5. GET  /settings/salary-slip                   — Get salary-slip settings
  6. PATCH /settings/salary-slip                  — Update salary-slip settings
  7. GET  /settings/features                      — View feature toggles
  8. PATCH /settings/features/{feature_key}       — Enable / disable feature
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, status

from app.core.constants.enums import PermissionAction as A
from app.core.dependencies.auth import (
    CurrentUser,
    get_current_active_user,
    require_permission,
)
from app.core.exceptions.base import AppException
from app.core.middleware.request_context import get_request_id
from app.modules.settings.dependencies import SettingsServiceDep
from app.modules.settings.schemas import (
    ConfigurationViewResponse,
    FeaturesResponse,
    FeatureToggleRequest,
    ModulePointerSchema,
    OrgSalarySlipResponse,
    OrgSalarySlipUpdateRequest,
    OrgSettingsResponse,
    OrgSettingsUpdateRequest,
)
from app.shared.schemas.response import SuccessResponse, success_response

router = APIRouter(prefix="/settings", tags=["Settings Management"])

# Feature-permission key (§2 of the API contract)
_FEATURE_KEY = "settings"


# ---------------------------------------------------------------------------
# Common helpers
# ---------------------------------------------------------------------------

CurrentUserDep = Annotated[CurrentUser, Depends(get_current_active_user)]


def get_org_id(
    current_user: Annotated[CurrentUser, Depends(get_current_active_user)],
) -> int:
    """Return caller's tenant org_id or raise 400 TENANT_UNRESOLVED."""
    if current_user.org_id is None:
        exc = AppException("Organization context is required.", code="TENANT_UNRESOLVED")
        exc.status_code = status.HTTP_400_BAD_REQUEST
        raise exc
    return current_user.org_id


OrgIdDep = Annotated[int, Depends(get_org_id)]


def _ok(data: Any, message: str = "OK") -> dict[str, Any]:
    """Wrap response data in the shared SuccessResponse envelope."""
    return success_response(data=data, message=message, request_id=get_request_id())


# ===========================================================================
# 1. GET /settings  — Combined Configuration View
# ===========================================================================


@router.get(
    "",
    response_model=SuccessResponse[ConfigurationViewResponse],
    summary="View Configuration (combined)",
    description=(
        "Returns both owned settings blocks (organization + salary_slip) "
        "plus read-only pointers to cross-module settings."
    ),
    dependencies=[Depends(require_permission(_FEATURE_KEY, A.READ))],
)
async def view_configuration(
    service: SettingsServiceDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Return the full combined settings configuration view for the organization."""
    raw = await service.get_configuration_view(org_id)

    # Build typed DTO — either value may be None (row not yet initialized)
    org_dto = (
        OrgSettingsResponse.model_validate(raw["organization"]) if raw["organization"] else None
    )
    slip_dto = (
        OrgSalarySlipResponse.model_validate(raw["salary_slip"]) if raw["salary_slip"] else None
    )
    pointers = {k: ModulePointerSchema(**v) for k, v in raw["cross_module_pointers"].items()}
    view = ConfigurationViewResponse(
        organization=org_dto,
        salary_slip=slip_dto,
        cross_module_pointers=pointers,
    )
    return _ok(view, "Configuration retrieved.")


# ===========================================================================
# 2. GET /settings/organization  — Get Organization Settings
# ===========================================================================


@router.get(
    "/organization",
    response_model=SuccessResponse[OrgSettingsResponse],
    summary="Get Organization / System Settings",
    description="Retrieve the organization system and device settings row.",
    dependencies=[Depends(require_permission(_FEATURE_KEY, A.READ))],
)
async def get_org_settings(
    service: SettingsServiceDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Return org_settings for the tenant; 404 if not yet initialized."""
    settings = await service.get_org_settings(org_id)
    return _ok(OrgSettingsResponse.model_validate(settings))


# ===========================================================================
# 3. PATCH /settings/organization  — Update Organization Settings
# ===========================================================================


@router.patch(
    "/organization",
    response_model=SuccessResponse[OrgSettingsResponse],
    summary="Update Organization / System Settings",
    description=(
        "Patch (upsert) the organization settings row. "
        "Only provided fields are updated; sync_code and pass_code are required on first create."
    ),
    dependencies=[Depends(require_permission(_FEATURE_KEY, A.EDIT))],
)
async def update_org_settings(
    payload: OrgSettingsUpdateRequest,
    service: SettingsServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Apply partial updates to the org settings; upserts if row is absent."""
    settings = await service.update_org_settings(
        org_id=org_id,
        caller_user_id=current_user.user_id,
        caller_name=str(current_user.user_id),
        advance_shift_enabled=payload.advance_shift_enabled,
        enable_regularization=payload.enable_regularization,
        enable_photo_punch=payload.enable_photo_punch,
        device_sync_time=payload.device_sync_time,
        sync_code=payload.sync_code,
        pass_code=payload.pass_code,
    )
    return _ok(OrgSettingsResponse.model_validate(settings), "Settings updated.")


# ===========================================================================
# 4. POST /settings/organization/reset  — Reset Organization Settings
# ===========================================================================


@router.post(
    "/organization/reset",
    response_model=SuccessResponse[OrgSettingsResponse],
    summary="Reset Organization Settings",
    description=(
        "Re-apply schema defaults to the toggle and device_sync_time fields. "
        "sync_code and pass_code are never reset."
    ),
    dependencies=[Depends(require_permission(_FEATURE_KEY, A.EDIT))],
)
async def reset_org_settings(
    service: SettingsServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Reset toggle/time fields to defaults; sync_code/pass_code are untouched."""
    settings = await service.reset_org_settings(
        org_id=org_id,
        caller_user_id=current_user.user_id,
        caller_name=str(current_user.user_id),
    )
    return _ok(OrgSettingsResponse.model_validate(settings), "Settings reset to defaults.")


# ===========================================================================
# 5. GET /settings/salary-slip  — Get Salary-Slip Settings
# ===========================================================================


@router.get(
    "/salary-slip",
    response_model=SuccessResponse[OrgSalarySlipResponse],
    summary="Get Salary-Slip Settings",
    description="Retrieve the organization salary slip / payslip settings row.",
    dependencies=[Depends(require_permission(_FEATURE_KEY, A.READ))],
)
async def get_salary_slip_settings(
    service: SettingsServiceDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Return org_salary_slip_settings for the tenant; 404 if not initialized."""
    slip = await service.get_salary_slip_settings(org_id)
    return _ok(OrgSalarySlipResponse.model_validate(slip))


# ===========================================================================
# 6. PATCH /settings/salary-slip  — Update Salary-Slip Settings
# ===========================================================================


@router.patch(
    "/salary-slip",
    response_model=SuccessResponse[OrgSalarySlipResponse],
    summary="Update Salary-Slip Settings",
    description=(
        "Patch (upsert) the salary slip settings row. "
        "company_name, company_address, and company_contact are required on first create."
    ),
    dependencies=[Depends(require_permission(_FEATURE_KEY, A.EDIT))],
)
async def update_salary_slip_settings(
    payload: OrgSalarySlipUpdateRequest,
    service: SettingsServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Apply partial updates to salary-slip settings; upserts if row is absent."""
    slip = await service.update_salary_slip_settings(
        org_id=org_id,
        caller_user_id=current_user.user_id,
        caller_name=str(current_user.user_id),
        company_logo_url=payload.company_logo_url,
        company_name=payload.company_name,
        company_address=payload.company_address,
        company_contact=payload.company_contact,
        company_website_email=payload.company_website_email,
        auto_release_payslip=payload.auto_release_payslip,
        branch_wise_payslip=payload.branch_wise_payslip,
    )
    return _ok(OrgSalarySlipResponse.model_validate(slip), "Salary slip settings updated.")


# ===========================================================================
# 7. GET /settings/features  — View Feature Toggles
# ===========================================================================


@router.get(
    "/features",
    response_model=SuccessResponse[FeaturesResponse],
    summary="View Enabled Features",
    description=(
        "Return the current state of all fixed boolean feature toggles "
        "across org_settings and org_salary_slip_settings."
    ),
    dependencies=[Depends(require_permission(_FEATURE_KEY, A.READ))],
)
async def get_features(
    service: SettingsServiceDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Return {feature_key: bool} for all five fixed feature toggles."""
    features = await service.get_features(org_id)
    return _ok(FeaturesResponse(features=features))


# ===========================================================================
# 8. PATCH /settings/features/{feature_key}  — Enable / Disable Feature
# ===========================================================================


@router.patch(
    "/features/{feature_key}",
    response_model=SuccessResponse[FeaturesResponse],
    summary="Enable / Disable Feature",
    description=(
        "Toggle a specific boolean feature on or off. "
        "feature_key must be one of the five fixed keys. "
        "Returns 404 UNKNOWN_FEATURE for unrecognized keys."
    ),
    dependencies=[Depends(require_permission(_FEATURE_KEY, A.EDIT))],
)
async def set_feature(
    feature_key: str,
    payload: FeatureToggleRequest,
    service: SettingsServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Enable or disable a fixed feature toggle by key."""
    updated = await service.set_feature(
        org_id=org_id,
        caller_user_id=current_user.user_id,
        caller_name=str(current_user.user_id),
        feature_key=feature_key,
        enabled=payload.enabled,
    )
    action = "enabled" if payload.enabled else "disabled"
    return _ok(
        FeaturesResponse(features=updated),
        f"Feature '{feature_key}' {action}.",
    )
