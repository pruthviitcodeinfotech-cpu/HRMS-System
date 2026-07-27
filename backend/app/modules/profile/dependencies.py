"""User Profile — module-scoped FastAPI dependencies.

Only genuinely profile-specific wiring lives here: constructing the
:class:`~app.modules.profile.service.ProfileService`. The current-principal and
tenant-context dependencies are **reused** from elsewhere rather than duplicated:

    * Current principal ...... ``app.core.dependencies.auth.get_current_active_user``
    * Tenant (``org_id``) .... ``app.modules.organization.dependencies.get_org_id``
    * Current session id ..... ``app.modules.auth.dependencies.get_current_session_id``
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies.auth import CurrentUser, get_current_active_user
from app.core.dependencies.db import get_db
from app.modules.auth.dependencies import get_current_session_id
from app.modules.organization.dependencies import get_org_id
from app.modules.profile.service import ProfileService


async def get_profile_service(db: Annotated[AsyncSession, Depends(get_db)]) -> ProfileService:
    """Provide a :class:`ProfileService` bound to the request-scoped DB session."""
    return ProfileService(db)


ProfileServiceDep = Annotated[ProfileService, Depends(get_profile_service)]
CurrentUserDep = Annotated[CurrentUser, Depends(get_current_active_user)]
OrgIdDep = Annotated[int, Depends(get_org_id)]
CurrentSessionIdDep = Annotated[int | None, Depends(get_current_session_id)]

__all__ = [
    "get_profile_service",
    "ProfileServiceDep",
    "CurrentUserDep",
    "OrgIdDep",
    "CurrentSessionIdDep",
]
