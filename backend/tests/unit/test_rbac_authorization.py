"""Unit tests for the RBAC authorization module.

Covers effective-permission resolution, organization isolation, the super-admin
guard, and the branch/department data-scope guards.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.core.constants.enums import PermissionAction
from app.core.dependencies.auth import CurrentUser
from app.core.exceptions.base import AuthorizationException
from app.core.security.permissions import build_effective_permissions
from app.modules.rbac.authorization import (
    PermissionResolver,
    ensure_same_org,
    require_branch_access,
    require_department_access,
    require_super_admin,
)


def _principal(
    *, is_super_admin: bool = False, org_id: int = 1, branch_ids=(), department_ids=(), perms=None
) -> CurrentUser:
    permissions = build_effective_permissions(
        is_super_admin=is_super_admin,
        feature_rows=perms or [],
        branch_ids=list(branch_ids),
        department_ids=list(department_ids),
    )
    return CurrentUser(
        user_id=1, org_id=org_id, is_super_admin=is_super_admin, is_active=True,
        permissions=permissions,
    )


def _perm(feature_key: str, **flags: bool) -> SimpleNamespace:
    base = {"can_create": False, "can_read": False, "can_edit": False, "can_delete": False}
    base.update(flags)
    return SimpleNamespace(feature_key=feature_key, **base)


# --- Effective permission resolution --------------------------------------
async def test_permission_resolver_merges_and_scopes() -> None:
    resolver = PermissionResolver(AsyncMock())
    resolver._assignments = AsyncMock()
    resolver._template_perms = AsyncMock()
    resolver._custom_perms = AsyncMock()
    resolver._branch_access = AsyncMock()
    resolver._dept_access = AsyncMock()

    resolver._assignments.get_for_user.return_value = SimpleNamespace(template_id=1)
    resolver._template_perms.list_for_template.return_value = [_perm("employee", can_read=True)]
    resolver._custom_perms.list_for_user.return_value = [
        _perm("employee", can_read=True, can_edit=True)  # override
    ]
    resolver._branch_access.branch_ids_for_user.return_value = [10]
    resolver._dept_access.department_ids_for_user.return_value = [5]

    eff = await resolver.resolve(user_id=1, is_super_admin=False)
    assert eff.has_permission("employee", PermissionAction.EDIT) is True  # custom won
    assert eff.can_access_branch(10) is True
    assert eff.can_access_department(5) is True
    assert eff.can_access_branch(99) is False


async def test_permission_resolver_super_admin_bypass() -> None:
    resolver = PermissionResolver(AsyncMock())
    resolver._assignments = AsyncMock()
    resolver._template_perms = AsyncMock()
    resolver._custom_perms = AsyncMock()
    resolver._branch_access = AsyncMock()
    resolver._dept_access = AsyncMock()
    resolver._assignments.get_for_user.return_value = None
    resolver._custom_perms.list_for_user.return_value = []
    resolver._branch_access.branch_ids_for_user.return_value = []
    resolver._dept_access.department_ids_for_user.return_value = []

    eff = await resolver.resolve(user_id=1, is_super_admin=True)
    assert eff.has_permission("anything", PermissionAction.DELETE) is True
    assert eff.can_access_branch(123) is True


# --- Organization isolation ------------------------------------------------
def test_ensure_same_org_allows_matching() -> None:
    ensure_same_org(_principal(org_id=1), org_id=1)  # no raise


def test_ensure_same_org_rejects_cross_org() -> None:
    with pytest.raises(AuthorizationException):
        ensure_same_org(_principal(org_id=1), org_id=2)


def test_ensure_same_org_rejects_super_admin_cross_org() -> None:
    # Tenant isolation applies even to super admins.
    with pytest.raises(AuthorizationException):
        ensure_same_org(_principal(is_super_admin=True, org_id=1), org_id=2)


# --- Super-admin guard -----------------------------------------------------
async def test_require_super_admin_passes() -> None:
    user = _principal(is_super_admin=True)
    assert await require_super_admin(user) is user


async def test_require_super_admin_rejects() -> None:
    with pytest.raises(AuthorizationException):
        await require_super_admin(_principal(is_super_admin=False))


# --- Branch / department guards -------------------------------------------
async def test_require_branch_access_allows_in_scope() -> None:
    user = _principal(branch_ids=[7])
    assert await require_branch_access(7, user) is user


async def test_require_branch_access_rejects_out_of_scope() -> None:
    with pytest.raises(AuthorizationException):
        await require_branch_access(99, _principal(branch_ids=[7]))


async def test_require_branch_access_super_admin_bypass() -> None:
    user = _principal(is_super_admin=True)
    assert await require_branch_access(99, user) is user


async def test_require_department_access_rejects_out_of_scope() -> None:
    with pytest.raises(AuthorizationException):
        await require_department_access(99, _principal(department_ids=[3]))
