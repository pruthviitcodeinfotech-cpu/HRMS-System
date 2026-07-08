"""UUID and random-token/identifier generators."""

from __future__ import annotations

import secrets
from uuid import UUID, uuid4


def new_uuid() -> UUID:
    """Return a new random UUID4."""
    return uuid4()


def new_uuid_hex() -> str:
    """Return a new random UUID4 as a 32-char hex string (no dashes)."""
    return uuid4().hex


def is_valid_uuid(value: str) -> bool:
    """Return ``True`` if ``value`` is a well-formed UUID string."""
    try:
        UUID(str(value))
        return True
    except (ValueError, AttributeError, TypeError):
        return False


def random_token(n_bytes: int = 32) -> str:
    """Return a cryptographically-secure URL-safe random token."""
    return secrets.token_urlsafe(n_bytes)


def random_numeric_code(length: int = 6) -> str:
    """Return a zero-padded numeric code (e.g. for OTP-style codes)."""
    if length < 1:
        raise ValueError("length must be >= 1")
    upper = 10**length
    return str(secrets.randbelow(upper)).zfill(length)
