"""User Management & RBAC — Pydantic v2 request/response DTOs.

Wire contract for the User-Management/RBAC API (see
``docs/User_Management_RBAC_API_Contract.md``): user administration, rights
templates ("roles"), template permissions, the permission catalogue, user↔template
assignment, per-user permission overrides, and branch/department data-scope access.

Reuses the shared foundation (:class:`app.shared.base.schema.BaseSchema`, the paged
envelope, and the shared email validator) and never exposes secrets
(``password_hash`` is write-only on create; ``session_token`` is out of scope).
Field shapes mirror the RBAC tables; validation follows the API contract.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import ConfigDict, Field, field_validator

from app.shared.base.schema import BaseSchema
from app.shared.schemas.pagination import PaginatedResponse
from app.shared.utils.validators import is_valid_email


def _validate_email(value: str) -> str:
    normalised = value.strip().lower()
    if not is_valid_email(normalised):
        raise ValueError("invalid email format")
    return normalised


# ===========================================================================
# Shared building blocks
# ===========================================================================


class DataScopeSchema(BaseSchema):
    """The data-scope layer: branch/department ids a user may access."""

    branch_ids: list[int] = Field(default_factory=list)
    department_ids: list[int] = Field(default_factory=list)


class CrudFlags(BaseSchema):
    """The four CRUD permission flags shared by template & custom permissions."""

    can_create: bool = False
    can_read: bool = False
    can_edit: bool = False
    can_delete: bool = False


# ===========================================================================
# User management — requests
# ===========================================================================


class UserCreateRequest(BaseSchema):
    """Body for ``POST /users`` (create a user account)."""

    # Password must not be whitespace-normalised.
    model_config = ConfigDict(str_strip_whitespace=False)

    name: str = Field(..., min_length=1, max_length=150)
    email: str = Field(..., max_length=255)
    mobile_country_code: str = Field(default="+91", max_length=10)
    mobile_number: str = Field(..., min_length=1, max_length=20)
    employee_id: int | None = Field(default=None, description="Optional linked employee.")
    is_super_admin: bool = Field(default=False, description="Settable only by a super admin.")
    password: str | None = Field(
        default=None, min_length=1, description="Optional initial password."
    )

    @field_validator("email")
    @classmethod
    def _email(cls, value: str) -> str:
        return _validate_email(value)

    @field_validator("name", "mobile_number")
    @classmethod
    def _trim_required(cls, value: str) -> str:
        return value.strip()


class UserUpdateRequest(BaseSchema):
    """Body for ``PATCH /users/{user_id}`` (all fields optional)."""

    name: str | None = Field(default=None, min_length=1, max_length=150)
    email: str | None = Field(default=None, max_length=255)
    mobile_country_code: str | None = Field(default=None, max_length=10)
    mobile_number: str | None = Field(default=None, min_length=1, max_length=20)
    is_super_admin: bool | None = None

    @field_validator("email")
    @classmethod
    def _email(cls, value: str | None) -> str | None:
        return _validate_email(value) if value is not None else None


class AssignEmployeeRequest(BaseSchema):
    """Body for ``PUT /users/{user_id}/employee``."""

    employee_id: int = Field(..., description="Employee to link to this user (same org).")


# ===========================================================================
# User management — responses
# ===========================================================================


class UserSummarySchema(BaseSchema):
    """Compact user row for list endpoints (no secrets)."""

    id: int
    name: str
    email: str
    mobile_country_code: str
    mobile_number: str
    is_active: bool
    is_super_admin: bool
    employee_id: int | None = None
    last_login_at: datetime | None = None
    created_at: datetime


class UserSchema(UserSummarySchema):
    """Full user projection."""

    org_id: int
    updated_at: datetime
    is_deleted: bool = False


class RoleRefSchema(BaseSchema):
    """Lightweight reference to a rights template (role)."""

    id: int
    name: str


class UserDetailSchema(UserSchema):
    """Response for ``GET /users/{user_id}`` — profile + authorization summary."""

    template: RoleRefSchema | None = Field(
        default=None, description="The user's assigned rights template (role), if any."
    )
    data_scope: DataScopeSchema = Field(default_factory=DataScopeSchema)


# ===========================================================================
# Rights templates ("roles")
# ===========================================================================


class TemplatePermissionInput(CrudFlags):
    """A permission row supplied when creating/replacing a template's permissions."""

    feature_key: str = Field(..., min_length=1, max_length=100)
    feature_label: str = Field(..., min_length=1, max_length=150)
    parent_feature_key: str | None = Field(default=None, max_length=100)


class RoleCreateRequest(BaseSchema):
    """Body for ``POST /rights-templates`` (create a role/template)."""

    name: str = Field(..., min_length=1, max_length=150)
    permissions: list[TemplatePermissionInput] = Field(default_factory=list)

    @field_validator("name")
    @classmethod
    def _trim(cls, value: str) -> str:
        return value.strip()


class RoleUpdateRequest(BaseSchema):
    """Body for ``PATCH /rights-templates/{template_id}``."""

    name: str = Field(..., min_length=1, max_length=150)

    @field_validator("name")
    @classmethod
    def _trim(cls, value: str) -> str:
        return value.strip()


class RoleCloneRequest(BaseSchema):
    """Body for ``POST /rights-templates/{template_id}/clone``."""

    name: str = Field(..., min_length=1, max_length=150)

    @field_validator("name")
    @classmethod
    def _trim(cls, value: str) -> str:
        return value.strip()


class TemplatePermissionSchema(CrudFlags):
    """A persisted ``rights_template_permissions`` row."""

    id: int
    feature_key: str
    feature_label: str
    parent_feature_key: str | None = None


class RoleSchema(BaseSchema):
    """Summary row for a rights template (role)."""

    id: int
    name: str
    permission_count: int = 0
    assigned_user_count: int = 0
    created_at: datetime
    updated_at: datetime
    is_deleted: bool = False


class RoleDetailSchema(RoleSchema):
    """Response for ``GET /rights-templates/{template_id}`` — role + its permissions."""

    permissions: list[TemplatePermissionSchema] = Field(default_factory=list)


# ===========================================================================
# Template permission management
# ===========================================================================


class ReplaceTemplatePermissionsRequest(BaseSchema):
    """Body for ``PUT /rights-templates/{template_id}/permissions``."""

    permissions: list[TemplatePermissionInput] = Field(default_factory=list)


# ===========================================================================
# Permission catalogue (read-only, from the permission registry)
# ===========================================================================


class PermissionCatalogItemSchema(BaseSchema):
    """A registered feature in the permission catalogue."""

    feature_key: str
    feature_label: str
    parent_feature_key: str | None = None
    supported_actions: list[str] = Field(default_factory=lambda: ["create", "read", "edit", "delete"])


# ===========================================================================
# User ↔ template assignment (user role)
# ===========================================================================


class AssignRoleRequest(BaseSchema):
    """Body for ``PUT /users/{user_id}/template`` (assign/replace the user's role)."""

    template_id: int


class UserRoleSchema(BaseSchema):
    """Response for ``GET /users/{user_id}/template`` — the single assigned template."""

    template: RoleRefSchema | None = None
    assigned_by: int | None = None
    assigned_at: datetime | None = None


# ===========================================================================
# Per-user custom permission overrides
# ===========================================================================


class CustomPermissionInput(CrudFlags):
    """A per-user permission override supplied on create/replace."""

    feature_key: str = Field(..., min_length=1, max_length=100)
    parent_feature_key: str | None = Field(default=None, max_length=100)


class ReplaceCustomPermissionsRequest(BaseSchema):
    """Body for ``PUT /users/{user_id}/custom-permissions``."""

    permissions: list[CustomPermissionInput] = Field(default_factory=list)


class CustomPermissionSchema(CrudFlags):
    """A persisted ``user_custom_permissions`` row."""

    id: int
    feature_key: str
    parent_feature_key: str | None = None
    set_by: int | None = None
    set_at: datetime | None = None


class EffectivePermissionSchema(CrudFlags):
    """A single feature's effective flags (template ⊕ custom overrides)."""

    feature_key: str


class EffectivePermissionsSchema(BaseSchema):
    """Response for ``GET /users/{user_id}/effective-permissions``."""

    permissions: list[EffectivePermissionSchema] = Field(default_factory=list)
    data_scope: DataScopeSchema = Field(default_factory=DataScopeSchema)


# ===========================================================================
# Branch / department access (data scope)
# ===========================================================================


class AssignBranchAccessRequest(BaseSchema):
    """Body for ``POST /users/{user_id}/branch-access``."""

    branch_id: int


class ReplaceBranchAccessRequest(BaseSchema):
    """Body for ``PUT /users/{user_id}/branch-access``."""

    branch_ids: list[int] = Field(default_factory=list)


class BranchAccessSchema(BaseSchema):
    """A persisted ``user_branch_access`` grant."""

    branch_id: int
    granted_by: int | None = None
    granted_at: datetime | None = None


class AssignDepartmentAccessRequest(BaseSchema):
    """Body for ``POST /users/{user_id}/department-access``."""

    department_id: int


class ReplaceDepartmentAccessRequest(BaseSchema):
    """Body for ``PUT /users/{user_id}/department-access``."""

    department_ids: list[int] = Field(default_factory=list)


class DepartmentAccessSchema(BaseSchema):
    """A persisted ``user_department_access`` grant."""

    department_id: int
    granted_by: int | None = None
    granted_at: datetime | None = None


# ===========================================================================
# Paginated list responses (reuse the shared paged envelope)
# ===========================================================================


class UserListResponse(PaginatedResponse[UserSummarySchema]):
    """Paginated ``GET /users`` result."""


class RoleListResponse(PaginatedResponse[RoleSchema]):
    """Paginated ``GET /rights-templates`` result."""


__all__ = [
    "DataScopeSchema",
    "CrudFlags",
    "UserCreateRequest",
    "UserUpdateRequest",
    "AssignEmployeeRequest",
    "UserSummarySchema",
    "UserSchema",
    "UserDetailSchema",
    "RoleRefSchema",
    "TemplatePermissionInput",
    "RoleCreateRequest",
    "RoleUpdateRequest",
    "RoleCloneRequest",
    "TemplatePermissionSchema",
    "RoleSchema",
    "RoleDetailSchema",
    "ReplaceTemplatePermissionsRequest",
    "PermissionCatalogItemSchema",
    "AssignRoleRequest",
    "UserRoleSchema",
    "CustomPermissionInput",
    "ReplaceCustomPermissionsRequest",
    "CustomPermissionSchema",
    "EffectivePermissionSchema",
    "EffectivePermissionsSchema",
    "AssignBranchAccessRequest",
    "ReplaceBranchAccessRequest",
    "BranchAccessSchema",
    "AssignDepartmentAccessRequest",
    "ReplaceDepartmentAccessRequest",
    "DepartmentAccessSchema",
    "UserListResponse",
    "RoleListResponse",
]
