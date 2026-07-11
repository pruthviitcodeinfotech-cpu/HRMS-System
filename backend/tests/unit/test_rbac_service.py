"""Unit tests for ``RBACService`` business logic (repositories mocked).

Covers user CRUD, role CRUD, template & custom permission mapping, user↔role
assignment, branch/department access, effective-permission calculation, and the
conflict/authorization/validation failure paths.
"""

from __future__ import annotations

from datetime import UTC
from types import SimpleNamespace

import pytest

from app.core.exceptions.base import (
    AuthorizationException,
    ConflictException,
    NotFoundException,
    ValidationException,
)
from app.modules.rbac.schemas import (
    AssignRoleRequest,
    CustomPermissionInput,
    RoleCloneRequest,
    RoleCreateRequest,
    RoleUpdateRequest,
    TemplatePermissionInput,
    UserCreateRequest,
    UserUpdateRequest,
)


def _perm_row(feature_key: str, perm_id: int = 1, **flags: bool) -> SimpleNamespace:
    base = {"can_create": False, "can_read": False, "can_edit": False, "can_delete": False}
    base.update(flags)
    # Mirrors ``RightsTemplatePermission``: ``id``, ``feature_label`` and
    # ``parent_feature_key`` are real columns that ``clone_role`` copies onto the
    # cloned template and that ``TemplatePermissionSchema`` requires.
    return SimpleNamespace(
        id=perm_id,
        feature_key=feature_key,
        feature_label=feature_key.replace("_", " ").title(),
        parent_feature_key=None,
        **base,
    )


# --- User CRUD -------------------------------------------------------------
async def test_create_user_success(rbac_service, make_user) -> None:
    rbac_service.users.email_exists.return_value = False
    rbac_service.users.mobile_exists.return_value = False
    rbac_service.users.create.return_value = make_user()
    data = UserCreateRequest(name="U", email="u@e.com", mobile_number="900", password="Secret123")

    result = await rbac_service.create_user(
        org_id=1, actor_id=99, actor_is_super_admin=True, data=data
    )
    assert result.email == "user@example.com"
    rbac_service.users.create.assert_awaited_once()
    rbac_service.audit.record.assert_awaited_once()


async def test_create_user_email_conflict(rbac_service) -> None:
    rbac_service.users.email_exists.return_value = True
    data = UserCreateRequest(name="U", email="u@e.com", mobile_number="900")
    with pytest.raises(ConflictException) as exc:
        await rbac_service.create_user(org_id=1, actor_id=1, actor_is_super_admin=True, data=data)
    assert exc.value.code == "USER_EMAIL_EXISTS"


async def test_create_user_super_admin_gated(rbac_service) -> None:
    data = UserCreateRequest(name="U", email="u@e.com", mobile_number="900", is_super_admin=True)
    with pytest.raises(AuthorizationException):
        await rbac_service.create_user(
            org_id=1, actor_id=1, actor_is_super_admin=False, data=data
        )


async def test_create_user_employee_already_mapped(rbac_service) -> None:
    rbac_service.users.email_exists.return_value = False
    rbac_service.users.mobile_exists.return_value = False
    rbac_service.users.employee_is_mapped.return_value = True
    data = UserCreateRequest(name="U", email="u@e.com", mobile_number="900", employee_id=5)
    with pytest.raises(ConflictException) as exc:
        await rbac_service.create_user(org_id=1, actor_id=1, actor_is_super_admin=True, data=data)
    assert exc.value.code == "EMPLOYEE_ALREADY_MAPPED"


async def test_update_user_email_conflict(rbac_service, make_user) -> None:
    rbac_service.users.get_active_by_id.return_value = make_user(email="old@e.com")
    rbac_service.users.email_exists.return_value = True
    data = UserUpdateRequest(email="new@e.com")
    with pytest.raises(ConflictException):
        await rbac_service.update_user(
            org_id=1, actor_is_super_admin=True, user_id=1, data=data
        )


async def test_deactivate_self_blocked(rbac_service, make_user) -> None:
    with pytest.raises(ConflictException) as exc:
        await rbac_service.deactivate_user(org_id=1, actor_id=1, user_id=1)
    assert exc.value.code == "CANNOT_MODIFY_SELF"


async def test_delete_self_blocked(rbac_service) -> None:
    with pytest.raises(ConflictException) as exc:
        await rbac_service.delete_user(org_id=1, actor_id=7, user_id=7)
    assert exc.value.code == "CANNOT_MODIFY_SELF"


async def test_delete_user_success(rbac_service, make_user) -> None:
    rbac_service.users.get_active_by_id.return_value = make_user(id=2)
    await rbac_service.delete_user(org_id=1, actor_id=1, user_id=2)
    rbac_service.users.update.assert_awaited_once()
    rbac_service.audit.record.assert_awaited_once()


async def test_restore_user_not_deleted(rbac_service, make_user) -> None:
    rbac_service.users.get_by_id.return_value = make_user(deleted_at=None)
    with pytest.raises(ConflictException) as exc:
        await rbac_service.restore_user(org_id=1, user_id=1)
    assert exc.value.code == "USER_NOT_DELETED"


async def test_get_user_not_found(rbac_service) -> None:
    rbac_service.users.get_active_by_id.return_value = None
    with pytest.raises(NotFoundException):
        await rbac_service.get_user(org_id=1, user_id=404)


# --- Role CRUD -------------------------------------------------------------
async def test_create_role_success(rbac_service, make_role) -> None:
    rbac_service.roles.name_exists.return_value = False
    rbac_service.roles.create.return_value = make_role()
    rbac_service.roles.get_active_by_id.return_value = make_role()
    rbac_service.template_perms.list_for_template.return_value = []
    data = RoleCreateRequest(name="Manager")
    result = await rbac_service.create_role(org_id=1, actor_id=1, data=data)
    assert result.name == "Administrator"


async def test_create_role_name_conflict(rbac_service) -> None:
    rbac_service.roles.name_exists.return_value = True
    with pytest.raises(ConflictException) as exc:
        await rbac_service.create_role(org_id=1, actor_id=1, data=RoleCreateRequest(name="Dup"))
    assert exc.value.code == "TEMPLATE_NAME_EXISTS"


async def test_update_role_name_conflict(rbac_service, make_role) -> None:
    rbac_service.roles.get_active_by_id.return_value = make_role(name="Old")
    rbac_service.roles.name_exists.return_value = True
    with pytest.raises(ConflictException):
        await rbac_service.update_role(
            org_id=1, actor_id=1, template_id=1, data=RoleUpdateRequest(name="New")
        )


async def test_delete_role_in_use(rbac_service, make_role) -> None:
    rbac_service.roles.get_active_by_id.return_value = make_role()
    rbac_service.roles.has_assignments.return_value = True
    with pytest.raises(ConflictException) as exc:
        await rbac_service.delete_role(org_id=1, template_id=1)
    assert exc.value.code == "TEMPLATE_IN_USE"


async def test_clone_role_copies_permissions(rbac_service, make_role) -> None:
    rbac_service.roles.get_active_by_id.side_effect = [make_role(id=1), make_role(id=2)]
    rbac_service.roles.name_exists.return_value = False
    rbac_service.template_perms.list_for_template.side_effect = [
        [_perm_row("employee", can_read=True)],  # source perms
        [_perm_row("employee", can_read=True)],  # clone detail read
    ]
    rbac_service.roles.create.return_value = make_role(id=2, name="Clone")
    result = await rbac_service.clone_role(
        org_id=1, actor_id=1, template_id=1, data=RoleCloneRequest(name="Clone")
    )
    assert result.id == 2
    rbac_service.template_perms.create.assert_awaited()


# --- Template (role) permission mapping ------------------------------------
async def test_set_template_permission_creates(rbac_service, make_role) -> None:
    rbac_service.roles.get_active_by_id.return_value = make_role()
    rbac_service.template_perms.get_for_feature.return_value = None
    rbac_service.template_perms.create.return_value = SimpleNamespace(
        id=1, feature_key="employee", feature_label="Employee", parent_feature_key=None,
        can_create=True, can_read=True, can_edit=False, can_delete=False,
    )
    item = TemplatePermissionInput(feature_key="employee", feature_label="Employee", can_read=True)
    result = await rbac_service.set_template_permission(org_id=1, template_id=1, item=item)
    assert result.feature_key == "employee"
    rbac_service.template_perms.create.assert_awaited_once()


async def test_remove_template_permission_not_found(rbac_service, make_role) -> None:
    rbac_service.roles.get_active_by_id.return_value = make_role()
    rbac_service.template_perms.delete_for_feature.return_value = 0
    with pytest.raises(NotFoundException) as exc:
        await rbac_service.remove_template_permission(
            org_id=1, template_id=1, feature_key="ghost"
        )
    assert exc.value.code == "PERMISSION_NOT_FOUND"


# --- User role mapping -----------------------------------------------------
async def test_assign_role_replaces(rbac_service, make_user, make_role) -> None:
    rbac_service.users.get_active_by_id.return_value = make_user()
    rbac_service.roles.get_active_by_id.return_value = make_role()
    rbac_service.assignments.get_for_user.return_value = SimpleNamespace(
        template_id=1, assigned_by=9, assigned_at=None
    )
    rbac_service.roles.get_by_id.return_value = make_role()
    await rbac_service.assign_role(
        org_id=1, actor_id=9, user_id=1, data=AssignRoleRequest(template_id=1)
    )
    rbac_service.assignments.delete_for_user.assert_awaited_once()
    rbac_service.assignments.create.assert_awaited_once()
    rbac_service.audit.record.assert_awaited_once()


async def test_remove_role_not_assigned(rbac_service, make_user) -> None:
    rbac_service.users.get_active_by_id.return_value = make_user()
    rbac_service.assignments.delete_for_user.return_value = 0
    with pytest.raises(NotFoundException) as exc:
        await rbac_service.remove_role(org_id=1, user_id=1)
    assert exc.value.code == "ASSIGNMENT_NOT_FOUND"
    # Nothing was removed, so no audit row must be written.
    rbac_service.audit.record.assert_not_awaited()


async def test_remove_role_success_audits(rbac_service, make_user) -> None:
    rbac_service.users.get_active_by_id.return_value = make_user()
    rbac_service.assignments.delete_for_user.return_value = 1
    await rbac_service.remove_role(org_id=1, user_id=1)
    rbac_service.audit.record.assert_awaited_once()


# --- Custom permission mapping ---------------------------------------------
async def test_set_custom_permission_updates(rbac_service, make_user) -> None:
    rbac_service.users.get_active_by_id.return_value = make_user()
    existing = SimpleNamespace(
        id=1, feature_key="leave_request", parent_feature_key=None, set_by=2, set_at=None,
        can_create=False, can_read=False, can_edit=False, can_delete=False,
    )
    rbac_service.custom_perms.get_for_feature.return_value = existing
    rbac_service.custom_perms.update.return_value = existing
    item = CustomPermissionInput(feature_key="leave_request", can_read=True)
    await rbac_service.set_custom_permission(org_id=1, actor_id=2, user_id=1, item=item)
    rbac_service.custom_perms.update.assert_awaited_once()
    rbac_service.custom_perms.create.assert_not_awaited()


# --- Branch / department access --------------------------------------------
async def test_assign_branch_access_conflict(rbac_service, make_user) -> None:
    rbac_service.users.get_active_by_id.return_value = make_user()
    rbac_service.branch_access.exists.return_value = True
    with pytest.raises(ConflictException) as exc:
        await rbac_service.assign_branch_access(org_id=1, actor_id=1, user_id=1, branch_id=3)
    assert exc.value.code == "BRANCH_ACCESS_EXISTS"


async def test_remove_department_access_not_found(rbac_service, make_user) -> None:
    rbac_service.users.get_active_by_id.return_value = make_user()
    rbac_service.dept_access.delete_for_department.return_value = 0
    with pytest.raises(NotFoundException) as exc:
        await rbac_service.remove_department_access(org_id=1, user_id=1, department_id=3)
    assert exc.value.code == "DEPARTMENT_ACCESS_NOT_FOUND"


async def test_replace_branch_access_dedupes(rbac_service, make_user) -> None:
    rbac_service.users.get_active_by_id.return_value = make_user()
    rbac_service.branch_access.create.side_effect = [
        SimpleNamespace(branch_id=1, granted_by=1, granted_at=None),
        SimpleNamespace(branch_id=2, granted_by=1, granted_at=None),
    ]
    result = await rbac_service.replace_branch_access(
        org_id=1, actor_id=1, user_id=1, branch_ids=[1, 2, 2, 1]
    )
    assert len(result) == 2  # duplicates removed
    rbac_service.branch_access.delete_all_for_user.assert_awaited_once()


# --- Effective permissions -------------------------------------------------
async def test_effective_permissions_maps_resolver_output(rbac_service, make_user) -> None:
    """get_effective_permissions delegates the merge to the injected resolver."""
    from unittest.mock import AsyncMock

    from app.core.security.permissions import build_effective_permissions

    rbac_service.users.get_active_by_id.return_value = make_user()
    rbac_service._resolver = AsyncMock()
    rbac_service._resolver.resolve.return_value = build_effective_permissions(
        is_super_admin=False,
        feature_rows=[{"feature_key": "employee", "can_read": True, "can_edit": True}],
        branch_ids=[10],
        department_ids=[5],
    )

    result = await rbac_service.get_effective_permissions(org_id=1, user_id=1)
    perm = next(p for p in result.permissions if p.feature_key == "employee")
    assert perm.can_edit is True
    assert result.data_scope.branch_ids == [10]
    assert result.data_scope.department_ids == [5]


# --- Permission catalog ------------------------------------------------------
async def test_catalog_lookup_known_key(rbac_service) -> None:
    entry = await rbac_service.get_permission_catalog_entry(feature_key="employee")
    assert entry.feature_key == "employee"
    assert "read" in entry.supported_actions


async def test_catalog_lookup_unknown_key_404(rbac_service) -> None:
    with pytest.raises(NotFoundException) as exc:
        await rbac_service.get_permission_catalog_entry(feature_key="nonexistent")
    assert exc.value.code == "FEATURE_KEY_UNKNOWN"
    assert exc.value.status_code == 404


async def test_catalog_list_and_parent_filter(rbac_service) -> None:
    full = await rbac_service.list_permission_catalog()
    keys = {item.feature_key for item in full}
    assert {"employee", "user_management", "role_management", "access_management"} <= keys

    subtree = await rbac_service.list_permission_catalog(parent_feature_key="employee")
    assert {item.feature_key for item in subtree} == {"employee_salary", "employee_document"}


async def test_set_template_permission_unknown_key_422(rbac_service, make_role) -> None:
    rbac_service.roles.get_active_by_id.return_value = make_role()
    item = TemplatePermissionInput(
        feature_key="nonexistent", feature_label="Ghost", can_read=True
    )
    with pytest.raises(ValidationException) as exc:
        await rbac_service.set_template_permission(org_id=1, template_id=1, item=item)
    assert exc.value.code == "FEATURE_KEY_UNKNOWN"
    rbac_service.template_perms.create.assert_not_awaited()


async def test_replace_custom_permissions_unknown_key_422(rbac_service, make_user) -> None:
    rbac_service.users.get_active_by_id.return_value = make_user()
    items = [CustomPermissionInput(feature_key="nonexistent", can_read=True)]
    with pytest.raises(ValidationException) as exc:
        await rbac_service.replace_custom_permissions(
            org_id=1, actor_id=1, user_id=1, items=items
        )
    assert exc.value.code == "FEATURE_KEY_UNKNOWN"
    rbac_service.custom_perms.delete_all_for_user.assert_not_awaited()


# --- Session administration --------------------------------------------------
def _session_row(session_id: int = 5, user_id: int = 2) -> SimpleNamespace:
    from datetime import datetime

    return SimpleNamespace(
        id=session_id,
        user_id=user_id,
        device_info="pytest",
        ip_address="127.0.0.1",
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
        expires_at=None,
        revoked_at=None,
        is_active=True,
    )


async def test_list_user_sessions(rbac_service, make_user) -> None:
    rbac_service.users.get_by_id.return_value = make_user(id=2)
    rbac_service.sessions.list_for_user.return_value = [_session_row()]
    rbac_service.sessions.count_for_user.return_value = 1
    result = await rbac_service.list_user_sessions(org_id=1, user_id=2)
    assert result.items[0].id == 5
    assert result.pagination.total_records == 1


async def test_force_logout_revokes_target_session(rbac_service, make_user) -> None:
    rbac_service.users.get_by_id.return_value = make_user(id=2)
    row = _session_row(session_id=5, user_id=2)
    rbac_service.sessions.get_for_user.return_value = row
    await rbac_service.force_logout_session(org_id=1, actor_id=9, user_id=2, session_id=5)
    rbac_service.sessions.get_for_user.assert_awaited_once_with(5, 2)
    rbac_service.sessions.revoke.assert_awaited_once()
    assert rbac_service.sessions.revoke.await_args.args[0] is row
    rbac_service.audit.record.assert_awaited_once()


async def test_force_logout_session_not_found(rbac_service, make_user) -> None:
    rbac_service.users.get_by_id.return_value = make_user(id=2)
    rbac_service.sessions.get_for_user.return_value = None
    with pytest.raises(NotFoundException) as exc:
        await rbac_service.force_logout_session(org_id=1, actor_id=9, user_id=2, session_id=99)
    assert exc.value.code == "SESSION_NOT_FOUND"


async def test_force_logout_cross_org_user_404(rbac_service, make_user) -> None:
    """A target user belonging to another org is invisible: 404 USER_NOT_FOUND."""
    rbac_service.users.get_by_id.return_value = make_user(id=2, org_id=999)
    with pytest.raises(NotFoundException) as exc:
        await rbac_service.force_logout_session(org_id=1, actor_id=9, user_id=2, session_id=5)
    assert exc.value.code == "USER_NOT_FOUND"
    rbac_service.sessions.revoke.assert_not_awaited()


async def test_revoke_all_user_sessions_counts_and_audits(rbac_service, make_user) -> None:
    rbac_service.users.get_by_id.return_value = make_user(id=2)
    rbac_service.sessions.revoke_all_for_user.return_value = 3
    result = await rbac_service.revoke_all_user_sessions(org_id=1, actor_id=9, user_id=2)
    assert result.revoked_count == 3
    rbac_service.audit.record.assert_awaited_once()
