"""Authentication module — HTTP routes (thin controllers).

Maps the Authentication API Contract onto FastAPI endpoints. Controllers only:
resolve dependencies, call :class:`~app.modules.auth.service.AuthService`, and wrap
the result in the standard success envelope. **No business logic** lives here, and
no ``try/except`` is needed — the service raises typed
:class:`~app.core.exceptions.base.AppException`s that the globally-registered
handlers render into the standard error envelope.
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, Request, status

from app.core.dependencies.pagination import PaginationParams, pagination_params
from app.core.middleware.request_context import get_request_id
from app.modules.auth.dependencies import (
    AuthServiceDep,
    CurrentSessionIdDep,
    CurrentUserDep,
    OrgIdDep,
)
from app.modules.auth.schemas import (
    AccessTokenResponse,
    CurrentUserSchema,
    LoginRequest,
    LoginResponse,
    LogoutRequest,
    RefreshTokenRequest,
    RevokeAllSessionsResponse,
    SessionListResponse,
)
from app.shared.schemas.response import SuccessResponse, success_response

router = APIRouter(prefix="/auth", tags=["Authentication"])


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/login",
    response_model=SuccessResponse[LoginResponse],
    status_code=status.HTTP_200_OK,
    summary="Login",
    description="Authenticate by email + password and issue access + refresh tokens.",
)
async def login(
    payload: LoginRequest,
    service: AuthServiceDep,
    org_id: OrgIdDep,
    request: Request,
) -> dict[str, Any]:
    """Verify credentials, open a session, and return tokens + the user profile."""
    result = await service.login(
        org_id=org_id,
        email=payload.email,
        password=payload.password,
        device_info=payload.device_info,
        ip_address=request.client.host if request.client else None,
    )
    return success_response(data=result, message="Login successful.", request_id=get_request_id())


@router.post(
    "/refresh",
    response_model=SuccessResponse[AccessTokenResponse],
    status_code=status.HTTP_200_OK,
    summary="Refresh Access Token",
    description="Exchange a valid refresh token for a new short-lived access token.",
)
async def refresh_token(payload: RefreshTokenRequest, service: AuthServiceDep) -> dict[str, Any]:
    """Issue a new access token from a valid refresh token."""
    result = await service.refresh_token(refresh_token=payload.refresh_token)
    return success_response(data=result, message="Token refreshed.", request_id=get_request_id())


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Logout",
    description="Revoke the current session (or a specific refresh token owned by the caller).",
)
async def logout(
    service: AuthServiceDep,
    current_user: CurrentUserDep,
    session_id: CurrentSessionIdDep,
    payload: LogoutRequest | None = None,
) -> None:
    """Revoke a session. Returns ``204 No Content``."""
    await service.logout(
        user_id=current_user.user_id,
        session_id=session_id,
        refresh_token=payload.refresh_token if payload else None,
    )


@router.get(
    "/me",
    response_model=SuccessResponse[CurrentUserSchema],
    status_code=status.HTTP_200_OK,
    summary="Get Current User",
    description="Return the authenticated user's profile plus effective permissions and data scope.",
)
async def get_me(service: AuthServiceDep, current_user: CurrentUserDep) -> dict[str, Any]:
    """Return the ``/me`` payload for the authenticated principal."""
    result = await service.get_current_user(user_id=current_user.user_id)
    return success_response(data=result, request_id=get_request_id())


@router.get(
    "/sessions",
    response_model=SuccessResponse[SessionListResponse],
    status_code=status.HTTP_200_OK,
    summary="List Sessions",
    description="List the caller's own sessions (paginated).",
)
async def list_sessions(
    service: AuthServiceDep,
    current_user: CurrentUserDep,
    current_session_id: CurrentSessionIdDep,
    pagination: Annotated[PaginationParams, Depends(pagination_params)],
    active_only: Annotated[bool, Query(description="Return only active sessions.")] = True,
) -> dict[str, Any]:
    """Return a paginated list of the caller's sessions."""
    result = await service.list_sessions(
        user_id=current_user.user_id,
        current_session_id=current_session_id,
        active_only=active_only,
        page=pagination.page,
        page_size=pagination.page_size,
    )
    return success_response(data=result, request_id=get_request_id())


@router.delete(
    "/sessions/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke a Session",
    description="Revoke one of the caller's sessions by id.",
)
async def revoke_session(
    session_id: int,
    service: AuthServiceDep,
    current_user: CurrentUserDep,
) -> None:
    """Revoke a single owned session. Returns ``204 No Content``."""
    await service.revoke_session(user_id=current_user.user_id, session_id=session_id)


@router.post(
    "/sessions/revoke-all",
    response_model=SuccessResponse[RevokeAllSessionsResponse],
    status_code=status.HTTP_200_OK,
    summary="Revoke All Other Sessions",
    description="Revoke every session for the caller except the current one.",
)
async def revoke_all_other_sessions(
    service: AuthServiceDep,
    current_user: CurrentUserDep,
    current_session_id: CurrentSessionIdDep,
) -> dict[str, Any]:
    """Revoke all of the caller's sessions except the current one."""
    result = await service.revoke_all_other_sessions(
        user_id=current_user.user_id,
        current_session_id=current_session_id,
    )
    return success_response(data=result, request_id=get_request_id())
