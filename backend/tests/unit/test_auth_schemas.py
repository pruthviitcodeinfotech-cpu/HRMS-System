"""Unit tests for Authentication request/response schema validation."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.modules.auth.schemas import LoginRequest, TokenClaims


def test_login_request_valid_normalises_email() -> None:
    req = LoginRequest(email="  User@Example.COM ", password="Secret123")
    assert req.email == "user@example.com"  # trimmed + lower-cased
    assert req.password == "Secret123"


def test_login_request_password_not_stripped() -> None:
    req = LoginRequest(email="user@example.com", password="  spaced  ")
    assert req.password == "  spaced  "  # whitespace preserved (significant)


def test_login_request_invalid_email_raises() -> None:
    with pytest.raises(ValidationError):
        LoginRequest(email="not-an-email", password="Secret123")


def test_login_request_empty_password_raises() -> None:
    with pytest.raises(ValidationError):
        LoginRequest(email="user@example.com", password="")


def test_login_request_device_info_blank_becomes_none() -> None:
    req = LoginRequest(email="user@example.com", password="Secret123", device_info="   ")
    assert req.device_info is None


def test_token_claims_user_id_helper() -> None:
    claims = TokenClaims(sub="99", type="access", jti="j", iat=1, exp=2, org_id=3)
    assert claims.user_id == 99
