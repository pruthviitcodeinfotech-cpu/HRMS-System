"""Authentication module — Pydantic v2 request/response DTOs.

These schemas are the wire contract for the Authentication API (see
``docs/Authentication_API_Contract.md``): login, refresh, logout, current user
(``/me``), and session administration. They reuse the shared foundation
(:class:`app.shared.base.schema.BaseSchema`, the paginated envelope, and the
shared validators) and never expose secrets (``password_hash`` / ``session_token``
are intentionally absent). No repository/service/router logic lives here.

Field shapes mirror the RBAC ``users`` / ``user_sessions`` tables; validation
follows the API contract (email format, non-empty password, length bounds). The
concrete password-complexity policy is an open question in the contract, so only
non-emptiness is enforced here.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import ConfigDict, Field, field_validator

from app.shared.base.schema import BaseSchema
from app.shared.schemas.pagination import PaginatedResponse
from app.shared.utils.validators import is_valid_email

# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------


class LoginRequest(BaseSchema):
    """Credentials for ``POST /auth/login``.

    ``password`` is never stripped/normalised (whitespace can be significant);
    ``email`` is trimmed and lower-cased for case-insensitive lookup.
    """

    # Do not strip the password; other string fields are handled per-validator.
    model_config = ConfigDict(str_strip_whitespace=False)

    email: str = Field(..., max_length=255, description="Login email (unique per org).")
    password: str = Field(..., min_length=1, description="Plaintext password (verified server-side).")
    device_info: str | None = Field(
        default=None, max_length=500, description="Optional device/user-agent label."
    )

    @field_validator("email")
    @classmethod
    def _normalise_email(cls, value: str) -> str:
        normalised = value.strip().lower()
        if not is_valid_email(normalised):
            raise ValueError("invalid email format")
        return normalised

    @field_validator("device_info")
    @classmethod
    def _trim_device_info(cls, value: str | None) -> str | None:
        if value is None:
            return None
        trimmed = value.strip()
        return trimmed or None


class RefreshTokenRequest(BaseSchema):
    """Body for ``POST /auth/refresh``."""

    refresh_token: str = Field(..., min_length=1, description="A valid, non-expired refresh token.")


class LogoutRequest(BaseSchema):
    """Body for ``POST /auth/logout`` (authenticated).

    When ``refresh_token`` is omitted, the session referenced by the access token
    is revoked; when provided, that specific session (owned by the caller) is
    revoked instead.
    """

    refresh_token: str | None = Field(
        default=None, min_length=1, description="Optional refresh token / session to revoke."
    )


# ---------------------------------------------------------------------------
# Token schemas
# ---------------------------------------------------------------------------


class TokenResponse(BaseSchema):
    """Full token payload returned by login (access + refresh)."""

    access_token: str = Field(..., description="Short-lived JWT access token.")
    refresh_token: str = Field(..., description="Long-lived refresh token (bound to a session).")
    token_type: str = Field(default="bearer", description="Auth scheme for the access token.")
    expires_in: int = Field(..., ge=1, description="Access-token lifetime in seconds.")


class AccessTokenResponse(BaseSchema):
    """Token payload returned by refresh (new access token; refresh optional)."""

    access_token: str = Field(..., description="Newly issued JWT access token.")
    token_type: str = Field(default="bearer", description="Auth scheme for the access token.")
    expires_in: int = Field(..., ge=1, description="Access-token lifetime in seconds.")
    refresh_token: str | None = Field(
        default=None, description="Present only when refresh-token rotation is enabled."
    )


class TokenClaims(BaseSchema):
    """Decoded JWT claims (as produced/consumed by the security layer).

    Mirrors the claim set emitted by :mod:`app.core.security.jwt`. Useful for the
    service layer to build/validate tokens; not returned to clients directly.
    """

    sub: str = Field(..., description="Subject — the user id (string form).")
    type: str = Field(..., description="Token type: 'access' or 'refresh'.")
    jti: str = Field(..., description="Unique token id.")
    iat: int = Field(..., description="Issued-at (epoch seconds).")
    exp: int = Field(..., description="Expiry (epoch seconds).")
    org_id: int | None = Field(default=None, description="Tenant id claim.")
    is_super_admin: bool = Field(default=False, description="Super-admin bypass flag.")
    is_active: bool = Field(default=True, description="Account-active flag at issuance.")
    sid: str | None = Field(default=None, description="Session reference (user_sessions token).")
    roles: list[str] = Field(default_factory=list, description="Role/template names.")

    @property
    def user_id(self) -> int:
        """The subject parsed as an integer user id."""
        return int(self.sub)


# ---------------------------------------------------------------------------
# User / current-user schemas
# ---------------------------------------------------------------------------


class AuthUserSchema(BaseSchema):
    """Public projection of a ``users`` row (no secrets)."""

    id: int
    org_id: int
    name: str
    email: str
    mobile_country_code: str
    mobile_number: str
    is_super_admin: bool
    is_active: bool
    employee_id: int | None = None
    last_login_at: datetime | None = None


class FeaturePermissionSchema(BaseSchema):
    """A single feature's effective CRUD flags (template ⊕ custom overrides)."""

    feature_key: str
    can_create: bool = False
    can_read: bool = False
    can_edit: bool = False
    can_delete: bool = False


class DataScopeSchema(BaseSchema):
    """The data-scope layer: branch/department access for the current user."""

    branch_ids: list[int] = Field(default_factory=list)
    department_ids: list[int] = Field(default_factory=list)


class CurrentUserSchema(AuthUserSchema):
    """Response for ``GET /auth/me`` — profile plus effective authorization context."""

    permissions: list[FeaturePermissionSchema] = Field(default_factory=list)
    data_scope: DataScopeSchema = Field(default_factory=DataScopeSchema)


class LoginResponse(BaseSchema):
    """Response body for ``POST /auth/login`` — tokens plus the authenticated user."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = Field(..., ge=1)
    user: AuthUserSchema


# ---------------------------------------------------------------------------
# Session administration schemas
# ---------------------------------------------------------------------------


class SessionSchema(BaseSchema):
    """A single ``user_sessions`` row as seen by its owner (``session_token`` hidden)."""

    id: int
    device_info: str | None = None
    ip_address: str | None = None
    created_at: datetime
    expires_at: datetime | None = None
    revoked_at: datetime | None = None
    is_active: bool
    is_current: bool = Field(
        default=False, description="True for the session bound to the calling access token."
    )


class SessionListResponse(PaginatedResponse[SessionSchema]):
    """Paginated list of the caller's sessions (reuses the shared paged envelope)."""


class RevokeAllSessionsResponse(BaseSchema):
    """Result of ``POST /auth/sessions/revoke-all``."""

    revoked_count: int = Field(..., ge=0, description="Number of sessions revoked.")


__all__ = [
    "LoginRequest",
    "RefreshTokenRequest",
    "LogoutRequest",
    "TokenResponse",
    "AccessTokenResponse",
    "TokenClaims",
    "AuthUserSchema",
    "FeaturePermissionSchema",
    "DataScopeSchema",
    "CurrentUserSchema",
    "LoginResponse",
    "SessionSchema",
    "SessionListResponse",
    "RevokeAllSessionsResponse",
]
