"""Unit tests for the shared security primitives used by Authentication.

Covers password hashing/verification and JWT create/decode/verify, including
**token expiration** and type-mismatch handling.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from jose import jwt

from app.core.config.settings import settings
from app.core.security.jwt import (
    ACCESS_TOKEN_TYPE,
    REFRESH_TOKEN_TYPE,
    TokenError,
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_token,
)
from app.core.security.password import hash_password, verify_password


# --- Password --------------------------------------------------------------
def test_password_hash_roundtrip() -> None:
    hashed = hash_password("Secret123")
    assert hashed != "Secret123"
    assert verify_password("Secret123", hashed) is True


def test_password_verify_wrong() -> None:
    hashed = hash_password("Secret123")
    assert verify_password("wrong", hashed) is False


def test_password_verify_empty_inputs() -> None:
    assert verify_password("", "x") is False
    assert verify_password("x", "") is False


def test_hash_empty_raises() -> None:
    with pytest.raises(ValueError):
        hash_password("")


# --- JWT create / decode ---------------------------------------------------
def test_access_token_roundtrip() -> None:
    token = create_access_token(42, extra_claims={"org_id": 7})
    claims = decode_token(token)
    assert claims["sub"] == "42"
    assert claims["type"] == ACCESS_TOKEN_TYPE
    assert claims["org_id"] == 7
    assert "jti" in claims and "exp" in claims


def test_verify_token_type_ok() -> None:
    token = create_refresh_token(1)
    claims = verify_token(token, REFRESH_TOKEN_TYPE)
    assert claims["type"] == REFRESH_TOKEN_TYPE


def test_verify_token_type_mismatch_raises() -> None:
    token = create_access_token(1)
    with pytest.raises(TokenError):
        verify_token(token, REFRESH_TOKEN_TYPE)


def test_tampered_token_raises() -> None:
    with pytest.raises(TokenError):
        decode_token("not.a.jwt")


# --- Token expiration ------------------------------------------------------
def test_expired_token_raises() -> None:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": "1",
        "type": ACCESS_TOKEN_TYPE,
        "jti": "x",
        "iat": int((now - timedelta(hours=2)).timestamp()),
        "exp": int((now - timedelta(hours=1)).timestamp()),
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    with pytest.raises(TokenError):
        decode_token(token)


def test_verify_token_expired_raises() -> None:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": "1",
        "type": ACCESS_TOKEN_TYPE,
        "jti": "x",
        "iat": int((now - timedelta(hours=2)).timestamp()),
        "exp": int((now - timedelta(hours=1)).timestamp()),
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    with pytest.raises(TokenError):
        verify_token(token, ACCESS_TOKEN_TYPE)
