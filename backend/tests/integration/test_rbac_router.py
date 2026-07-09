"""Integration tests for the User Management & RBAC router.

Exercises the real app + real auth/permission dependencies with only
``RBACService`` mocked. Covers happy-path CRUD/mapping/access endpoints (as a
super admin, who bypasses the feature-permission guards), plus permission
enforcement, unauthorized access, and validation failures.
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock

from httpx import AsyncClient

from app.modules.rbac.schemas import (
    BranchAccessSchema,
    EffectivePermissionsSchema,
    RoleDetailSchema,
    UserRoleSchema,
    UserSchema,
)
from tests.conftest import API_PREFIX

_NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _user_schema() -> UserSchema:
    return UserSchema(
        id=1, org_id=1, name="Test User", email="user@example.com",
        mobile_country_code="+91", mobile_number="9876543210", is_active=True,
        is_super_admin=False, employee_id=None, last_login_at=None,
        created_at=_NOW, updated_at=_NOW, is_deleted=False,
    )


# --- User CRUD (super admin bypasses permission guards) --------------------
async def test_create_user_201(
    client: AsyncClient, mock_rbac_service: AsyncMock, super_admin_headers: dict[str, str]
) -> None:
    mock_rbac_service.create_user.return_value = _user_schema()
    resp = await client.post(
        f"{API_PREFIX}/users",
        json={"email": "user@example.com", "name": "Test User", "mobile_number": "9876543210"},
        headers=super_admin_headers,
    )
    assert resp.status_code == 201
    assert resp.json()["data"]["email"] == "user@example.com"


async def test_get_user_200(
    client: AsyncClient, mock_rbac_service: AsyncMock, super_admin_headers: dict[str, str]
) -> None:
    from app.modules.rbac.schemas import UserDetailSchema

    mock_rbac_service.get_user.return_value = UserDetailSchema(**_user_schema().model_dump())
    resp = await client.get(f"{API_PREFIX}/users/1", headers=super_admin_headers)
    assert resp.status_code == 200
    assert resp.json()["data"]["id"] == 1


async def test_delete_user_204(
    client: AsyncClient, mock_rbac_service: AsyncMock, super_admin_headers: dict[str, str]
) -> None:
    mock_rbac_service.delete_user.return_value = None
    resp = await client.delete(f"{API_PREFIX}/users/2", headers=super_admin_headers)
    assert resp.status_code == 204


# --- Role CRUD -------------------------------------------------------------
async def test_create_role_201(
    client: AsyncClient, mock_rbac_service: AsyncMock, super_admin_headers: dict[str, str]
) -> None:
    mock_rbac_service.create_role.return_value = RoleDetailSchema(
        id=1, name="Manager", created_at=_NOW, updated_at=_NOW, permissions=[]
    )
    resp = await client.post(
        f"{API_PREFIX}/rights-templates", json={"name": "Manager"}, headers=super_admin_headers
    )
    assert resp.status_code == 201
    assert resp.json()["data"]["name"] == "Manager"


# --- User role & permission mapping ----------------------------------------
async def test_assign_role_200(
    client: AsyncClient, mock_rbac_service: AsyncMock, super_admin_headers: dict[str, str]
) -> None:
    mock_rbac_service.assign_role.return_value = UserRoleSchema(template=None)
    resp = await client.put(
        f"{API_PREFIX}/users/1/template", json={"template_id": 1}, headers=super_admin_headers
    )
    assert resp.status_code == 200


async def test_assign_branch_access_201(
    client: AsyncClient, mock_rbac_service: AsyncMock, super_admin_headers: dict[str, str]
) -> None:
    mock_rbac_service.assign_branch_access.return_value = BranchAccessSchema(branch_id=3)
    resp = await client.post(
        f"{API_PREFIX}/users/1/branch-access", json={"branch_id": 3}, headers=super_admin_headers
    )
    assert resp.status_code == 201
    assert resp.json()["data"]["branch_id"] == 3


async def test_effective_permissions_200(
    client: AsyncClient, mock_rbac_service: AsyncMock, super_admin_headers: dict[str, str]
) -> None:
    mock_rbac_service.get_effective_permissions.return_value = EffectivePermissionsSchema()
    resp = await client.get(
        f"{API_PREFIX}/users/1/effective-permissions", headers=super_admin_headers
    )
    assert resp.status_code == 200
    assert "permissions" in resp.json()["data"]


# --- Permission enforcement (authorization failure) ------------------------
async def test_create_user_forbidden_without_permission(
    client: AsyncClient, make_access_token
) -> None:
    """A non-super-admin without user_management:create is rejected with 403."""
    token = make_access_token(is_super_admin=False, permissions=[])
    resp = await client.post(
        f"{API_PREFIX}/users",
        json={"email": "user@example.com", "name": "U", "mobile_number": "900"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "AUTH_FORBIDDEN"


async def test_create_user_allowed_with_permission(
    client: AsyncClient, mock_rbac_service: AsyncMock, make_access_token
) -> None:
    """A user holding user_management:create passes the guard (no super admin)."""
    mock_rbac_service.create_user.return_value = _user_schema()
    token = make_access_token(
        is_super_admin=False,
        permissions=[{"feature_key": "user_management", "can_create": True, "can_read": True}],
    )
    resp = await client.post(
        f"{API_PREFIX}/users",
        json={"email": "user@example.com", "name": "U", "mobile_number": "900"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201


# --- Unauthorized access ---------------------------------------------------
async def test_list_users_requires_authentication(client: AsyncClient) -> None:
    resp = await client.get(f"{API_PREFIX}/users")
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "AUTH_NOT_AUTHENTICATED"


# --- Validation failure ----------------------------------------------------
async def test_create_user_invalid_email_422(
    client: AsyncClient, super_admin_headers: dict[str, str]
) -> None:
    resp = await client.post(
        f"{API_PREFIX}/users",
        json={"email": "not-an-email", "name": "U", "mobile_number": "900"},
        headers=super_admin_headers,
    )
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "VALIDATION_ERROR"


async def test_create_role_missing_name_422(
    client: AsyncClient, super_admin_headers: dict[str, str]
) -> None:
    resp = await client.post(
        f"{API_PREFIX}/rights-templates", json={}, headers=super_admin_headers
    )
    assert resp.status_code == 422
