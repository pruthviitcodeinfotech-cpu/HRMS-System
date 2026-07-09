"""JWT access/refresh token creation and verification (python-jose, HS256).

Reusable token primitives only — no login endpoint, no user lookup. Access and
refresh tokens are distinguished by the ``type`` claim; TTLs come from settings
(``ACCESS_TOKEN_TTL`` / ``REFRESH_TOKEN_TTL``).

Standard claims emitted: ``sub`` (subject / user id), ``type``, ``iat``, ``exp``,
``jti`` (unique token id), plus any custom claims passed by the caller (e.g.
``org_id``, ``is_super_admin``, ``sid`` session reference).
"""

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

from jose import JWTError, jwt

from app.core.config.settings import settings

ACCESS_TOKEN_TYPE = "access"
REFRESH_TOKEN_TYPE = "refresh"


class TokenError(Exception):
    """Raised when a token cannot be decoded, is expired, or is the wrong type."""


def _create_token(
    subject: str | int,
    token_type: str,
    ttl_seconds: int,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": str(subject),
        "type": token_type,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=ttl_seconds)).timestamp()),
        "jti": uuid4().hex,
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_access_token(
    subject: str | int, extra_claims: dict[str, Any] | None = None
) -> str:
    """Create a short-lived access token for ``subject``."""
    return _create_token(subject, ACCESS_TOKEN_TYPE, settings.access_token_ttl, extra_claims)


def create_refresh_token(
    subject: str | int, extra_claims: dict[str, Any] | None = None
) -> str:
    """Create a long-lived refresh token for ``subject``."""
    return _create_token(subject, REFRESH_TOKEN_TYPE, settings.refresh_token_ttl, extra_claims)


def decode_token(token: str) -> dict[str, Any]:
    """Decode and verify a token's signature and expiry.

    Raises:
        TokenError: if the signature is invalid or the token has expired.
    """
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:
        raise TokenError(str(exc)) from exc


def verify_token(token: str, expected_type: str) -> dict[str, Any]:
    """Decode ``token`` and assert its ``type`` claim equals ``expected_type``.

    Raises:
        TokenError: on invalid/expired token or a token-type mismatch.
    """
    claims = decode_token(token)
    if claims.get("type") != expected_type:
        raise TokenError(
            f"invalid token type: expected '{expected_type}', got '{claims.get('type')}'"
        )
    return claims
