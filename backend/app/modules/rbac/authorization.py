"""RBAC authorization — guards and effective-permission resolution.

Builds on the Shared Foundation and does **not** re-implement its checks. The core
primitives already exist and are reused as-is:

    * Permission model + checks .... ``app.core.security.permissions``
      (:class:`EffectivePermissions.has_permission` / ``can_access_branch`` /
      ``can_access_department`` — all with built-in **super-admin bypass**).
    * Feature-permission guard ...... ``require_permission`` (foundation).
    * Role guard .................... ``require_role`` (foundation).
    * Principal ..................... ``CurrentUser`` (carries the resolved
      :class:`EffectivePermissions` from the access token).

This module adds the authorization pieces the foundation does not yet provide and
re-exports the existing guards so callers have a single authorization entry point:

    * :class:`PermissionResolver` — resolve a user's :class:`EffectivePermissions`
      from the RBAC tables (template ⊕ custom overrides + branch/department scope),
      for token issuance or per-request re-resolution.
    * :func:`require_branch_access` / :func:`require_department_access` —
      data-scope route guards.
    * :func:`ensure_same_org` — organization-isolation enforcement.
    * :func:`require_super_admin` — super-admin-only guard.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

# Reused foundation primitives — re-exported, never duplicated.
from app.core.dependencies.auth import (
    CurrentUser,
    get_current_active_user,
    require_permission,
    require_role,
)
from app.core.exceptions.base import AuthorizationException
from app.core.security.permissions import EffectivePermissions, build_effective_permissions
from app.modules.rbac.repository import (
    TemplatePermissionRepository,
    UserBranchAccessRepository,
    UserCustomPermissionRepository,
    UserDepartmentAccessRepository,
    UserTemplateAssignmentRepository,
)

_CRUD_KEYS = ("can_create", "can_read", "can_edit", "can_delete")

CurrentUserDep = Annotated[CurrentUser, Depends(get_current_active_user)]


# ===========================================================================
# Effective permission resolution
# ===========================================================================


class PermissionResolver:
    """Resolve a user's effective authorization from the RBAC tables.

    Produces the shared :class:`EffectivePermissions` object (the same type carried
    on :class:`CurrentUser`), so it is the canonical source when building access-token
    claims at login or re-resolving permissions within a request. It merges the
    user's assigned rights-template permissions with their per-user overrides
    (custom wins) and attaches the branch/department data scope, then delegates to
    the foundation's :func:`build_effective_permissions`.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._assignments = UserTemplateAssignmentRepository(session)
        self._template_perms = TemplatePermissionRepository(session)
        self._custom_perms = UserCustomPermissionRepository(session)
        self._branch_access = UserBranchAccessRepository(session)
        self._dept_access = UserDepartmentAccessRepository(session)

    async def resolve(self, *, user_id: int, is_super_admin: bool) -> EffectivePermissions:
        """Return the merged :class:`EffectivePermissions` for a user."""
        assignment = await self._assignments.get_for_user(user_id)
        template_rows = (
            await self._template_perms.list_for_template(assignment.template_id)
            if assignment is not None
            else []
        )
        custom_rows = await self._custom_perms.list_for_user(user_id)

        merged: dict[str, dict[str, bool]] = {}
        for row in (*template_rows, *custom_rows):  # custom rows applied last (override)
            merged[row.feature_key] = {key: bool(getattr(row, key)) for key in _CRUD_KEYS}

        feature_rows: list[dict[str, object]] = [
            {"feature_key": key, **flags} for key, flags in merged.items()
        ]
        return build_effective_permissions(
            is_super_admin=is_super_admin,
            feature_rows=feature_rows,
            branch_ids=await self._branch_access.branch_ids_for_user(user_id),
            department_ids=await self._dept_access.department_ids_for_user(user_id),
        )


# ===========================================================================
# Organization isolation
# ===========================================================================


def ensure_same_org(current_user: CurrentUser, org_id: int) -> None:
    """Enforce tenant isolation: reject access to another organization's data.

    Applies to **everyone, including super admins** — super-admin bypass covers
    feature/scope checks but never tenant boundaries.

    Raises:
        AuthorizationException: if the caller's org differs from ``org_id``.
    """
    if current_user.org_id is None or current_user.org_id != org_id:
        raise AuthorizationException(
            "Cross-organization access is not allowed.", code="AUTH_FORBIDDEN"
        )


# ===========================================================================
# Super-admin guard
# ===========================================================================


async def require_super_admin(current_user: CurrentUserDep) -> CurrentUser:
    """Route dependency requiring the caller to be a super admin."""
    if not current_user.is_super_admin:
        raise AuthorizationException("Super-admin privileges are required.", code="AUTH_FORBIDDEN")
    return current_user


# ===========================================================================
# Data-scope guards (branch / department)
# ===========================================================================


async def require_branch_access(branch_id: int, current_user: CurrentUserDep) -> CurrentUser:
    """Route dependency enforcing branch-level data scope on a ``{branch_id}`` path.

    Reuses :meth:`EffectivePermissions.can_access_branch` (super admins pass).
    """
    if not current_user.permissions.can_access_branch(branch_id):
        raise AuthorizationException(
            "You do not have access to this branch.", code="AUTH_FORBIDDEN"
        )
    return current_user


async def require_department_access(
    department_id: int, current_user: CurrentUserDep
) -> CurrentUser:
    """Route dependency enforcing department-level data scope on ``{department_id}``.

    Reuses :meth:`EffectivePermissions.can_access_department` (super admins pass).
    """
    if not current_user.permissions.can_access_department(department_id):
        raise AuthorizationException(
            "You do not have access to this department.", code="AUTH_FORBIDDEN"
        )
    return current_user


__all__ = [
    # Effective-permission resolution
    "PermissionResolver",
    # Organization isolation
    "ensure_same_org",
    # Guards added here
    "require_super_admin",
    "require_branch_access",
    "require_department_access",
    # Re-exported foundation guards (single authorization surface — not duplicated)
    "require_permission",
    "require_role",
]
