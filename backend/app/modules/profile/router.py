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
    ChangePasswordRequest,
    ChangePasswordResponse,
    ProfilePhotoResponse,
    ProfileSchema,
    ProfileUpdateRequest,
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
    """Upload a new profile photo (``multipart/form-data``; stored on the linked employee).

    Requires the caller's user account to be linked to an employee record — that is
    where ``profile_photo_url`` lives (the ``users`` table has no such column).
    """
    result = await service.update_profile_photo(
        user_id=current_user.user_id, org_id=org_id, upload=file
    )
    return _ok(result, "Profile photo updated successfully.")


__all__ = ["router"]
