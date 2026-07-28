"""User Profile — HTTP routes (thin controllers).

Self-service identity endpoints: every route acts on the caller's own row —
there is no ``user_id`` path parameter and no RBAC feature-permission gate,
mirroring ``GET /auth/me``. Only the mobile number and the profile photo are
editable; everything else in the response is a read-only projection of
User / Employee / Organization / Branch / RightsTemplate.
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, File, UploadFile

from app.core.middleware.request_context import get_request_id
from app.modules.profile.dependencies import (
    CurrentSessionIdDep,
    CurrentUserDep,
    OrgIdDep,
    ProfileServiceDep,
)
from app.modules.profile.schemas import (
    ActiveSessionSchema,
    ChangePasswordRequest,
    ChangePasswordResponse,
    EmergencyContactUpdateRequest,
    PreferencesUpdateRequest,
    ProfilePhotoResponse,
    ProfileSchema,
    ProfileUpdateRequest,
    SignatureResponse,
    TwoFactorSetupResponse,
    TwoFactorVerifyRequest,
)
from app.shared.schemas.response import SuccessResponse, success_response

router = APIRouter(prefix="/profile", tags=["Profile"])


def _ok(data: Any, message: str = "OK") -> dict[str, Any]:
    """Wrap controller response data in the standard SuccessResponse envelope."""
    return success_response(data=data, message=message, request_id=get_request_id())


@router.get(
    "",
    response_model=SuccessResponse[ProfileSchema],
    summary="Get My Profile",
)
async def get_profile(
    service: ProfileServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Return the caller's own identity, organization, branch, and role."""
    result = await service.get_profile(user_id=current_user.user_id, org_id=org_id)
    return _ok(result)


@router.put(
    "",
    response_model=SuccessResponse[ProfileSchema],
    summary="Update My Profile",
)
async def update_profile(
    payload: ProfileUpdateRequest,
    service: ProfileServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Update the caller's mobile number (the only editable field here)."""
    result = await service.update_profile(
        user_id=current_user.user_id, org_id=org_id, data=payload
    )
    return _ok(result, "Profile updated successfully.")


@router.put(
    "/change-password",
    response_model=SuccessResponse[ChangePasswordResponse],
    summary="Change Password",
)
async def change_password(
    payload: ChangePasswordRequest,
    service: ProfileServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
    session_id: CurrentSessionIdDep,
) -> dict[str, Any]:
    """Change the caller's own password after verifying the current one.

    Every other active session is logged out as a side effect (contract:
    "Logout all other sessions after password change") — the session making this
    request is left alone so the caller isn't logged out of their own device.
    """
    result = await service.change_password(
        user_id=current_user.user_id,
        org_id=org_id,
        data=payload,
        current_session_id=session_id,
    )
    return _ok(result, "Password changed successfully.")


@router.put(
    "/photo",
    response_model=SuccessResponse[ProfilePhotoResponse],
    summary="Update Profile Photo",
)
async def update_profile_photo(
    service: ProfileServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
    file: Annotated[UploadFile, File(description="The photo binary (png/jpg/jpeg).")],
) -> dict[str, Any]:
    """Upload a new profile photo (``multipart/form-data``; stored on the linked employee)."""
    result = await service.update_profile_photo(
        user_id=current_user.user_id, org_id=org_id, upload=file
    )
    return _ok(result, "Profile photo updated successfully.")


@router.put(
    "/emergency-contact",
    response_model=SuccessResponse[ProfileSchema],
    summary="Update Emergency Contact",
)
async def update_emergency_contact(
    payload: EmergencyContactUpdateRequest,
    service: ProfileServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Update emergency contact details."""
    result = await service.update_emergency_contact(
        user_id=current_user.user_id, org_id=org_id, data=payload
    )
    return _ok(result, "Emergency contact updated successfully.")


@router.put(
    "/preferences",
    response_model=SuccessResponse[ProfileSchema],
    summary="Update Preferences",
)
async def update_preferences(
    payload: PreferencesUpdateRequest,
    service: ProfileServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Update language, timezone, theme, or notification preferences."""
    result = await service.update_preferences(
        user_id=current_user.user_id, org_id=org_id, data=payload
    )
    return _ok(result, "Preferences updated successfully.")


@router.post(
    "/signature",
    response_model=SuccessResponse[SignatureResponse],
    summary="Upload Signature Image",
)
async def upload_signature(
    service: ProfileServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
    file: Annotated[UploadFile, File(description="Signature image (png/jpg/jpeg).")],
) -> dict[str, Any]:
    """Upload a digital signature image for legal/HR documents."""
    result = await service.upload_signature(
        user_id=current_user.user_id, org_id=org_id, file=file
    )
    return _ok(result, "Signature uploaded successfully.")


@router.get(
    "/sessions",
    response_model=SuccessResponse[list[ActiveSessionSchema]],
    summary="Get Active Sessions",
)
async def get_active_sessions(
    service: ProfileServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
    session_id: CurrentSessionIdDep,
) -> dict[str, Any]:
    """List caller's active device sessions."""
    result = await service.get_active_sessions(
        user_id=current_user.user_id, org_id=org_id, current_session_id=session_id
    )
    return _ok(result)


@router.post(
    "/sessions/{target_session_id}/revoke",
    response_model=SuccessResponse[None],
    summary="Revoke Session",
)
async def revoke_session(
    target_session_id: int,
    service: ProfileServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Revoke a specific active device session."""
    await service.revoke_session(
        user_id=current_user.user_id, org_id=org_id, session_id=target_session_id
    )
    return _ok(None, "Session revoked successfully.")


@router.post(
    "/sessions/revoke-others",
    response_model=SuccessResponse[int],
    summary="Revoke All Other Sessions",
)
async def revoke_all_other_sessions(
    service: ProfileServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
    session_id: CurrentSessionIdDep,
) -> dict[str, Any]:
    """Logout all active device sessions except the current session."""
    count = await service.revoke_all_other_sessions(
        user_id=current_user.user_id, org_id=org_id, current_session_id=session_id
    )
    return _ok(count, f"Revoked {count} other active session(s).")


@router.post(
    "/2fa/setup",
    response_model=SuccessResponse[TwoFactorSetupResponse],
    summary="Setup 2FA",
)
async def setup_2fa(
    service: ProfileServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Initiate TOTP 2FA secret generation."""
    result = await service.setup_2fa(user_id=current_user.user_id, org_id=org_id)
    return _ok(result, "2FA setup initiated.")


@router.post(
    "/2fa/enable",
    response_model=SuccessResponse[None],
    summary="Enable 2FA",
)
async def enable_2fa(
    payload: TwoFactorVerifyRequest,
    service: ProfileServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Verify 6-digit TOTP code and enable 2FA."""
    await service.enable_2fa(
        user_id=current_user.user_id, org_id=org_id, code=payload.code
    )
    return _ok(None, "2FA enabled successfully.")


@router.post(
    "/2fa/disable",
    response_model=SuccessResponse[None],
    summary="Disable 2FA",
)
async def disable_2fa(
    service: ProfileServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Disable 2FA for caller's account."""
    await service.disable_2fa(user_id=current_user.user_id, org_id=org_id)
    return _ok(None, "2FA disabled successfully.")


__all__ = ["router"]
