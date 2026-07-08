"""Reusable security primitives: password hashing, JWT, RBAC permission model."""

from app.core.security.jwt import (
    ACCESS_TOKEN_TYPE,
    REFRESH_TOKEN_TYPE,
    TokenError,
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_token,
)
from app.core.security.password import hash_password, needs_rehash, verify_password
from app.core.security.permissions import (
    EffectivePermissions,
    FeaturePermission,
    build_effective_permissions,
)

__all__ = [
    "ACCESS_TOKEN_TYPE",
    "REFRESH_TOKEN_TYPE",
    "TokenError",
    "create_access_token",
    "create_refresh_token",
    "decode_token",
    "verify_token",
    "hash_password",
    "verify_password",
    "needs_rehash",
    "EffectivePermissions",
    "FeaturePermission",
    "build_effective_permissions",
]
