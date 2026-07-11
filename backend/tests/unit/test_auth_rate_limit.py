"""Unit tests for the auth brute-force controls.

Two independent mechanisms are covered:

    * the reusable request throttle (:mod:`app.core.dependencies.rate_limit`) —
      fixed-window counters keyed by client IP *and* by the submitted identifier;
    * the consecutive-failure **account lockout** enforced by ``AuthService.login``.

The autouse ``fake_redis`` fixture (``tests/conftest``) swaps the process-wide Redis
client for an in-memory dict, so every test starts with empty counters and the suite
never touches a real Redis.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from starlette.datastructures import Headers
from starlette.requests import Request

from app.core.cache import redis as redis_cache
from app.core.config.settings import settings
from app.core.dependencies.rate_limit import (
    UNKNOWN_CLIENT,
    client_ip,
    hash_identifier,
    rate_limit,
    read_body_field,
)
from app.core.exceptions.base import AuthenticationException, RateLimitException
from app.modules.auth.service import _failure_key, _lockout_key
from tests.conftest import TEST_PASSWORD


def _request(
    body: bytes = b"", *, client: tuple[str, int] | None = ("1.2.3.4", 5000), **headers: str
) -> Request:
    """Build a Starlette ``Request`` with the body already cached (as FastAPI does)."""
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/api/v1/auth/login",
        "headers": Headers({"content-type": "application/json", **headers}).raw,
        "client": client,
    }
    request = Request(scope)
    request._body = body  # noqa: SLF001 - FastAPI caches the body before dependencies run
    return request


# --- Key / client helpers ---------------------------------------------------
def test_client_ip_uses_peer_address() -> None:
    assert client_ip(_request()) == "1.2.3.4"


def test_client_ip_ignores_x_forwarded_for() -> None:
    """A forged `X-Forwarded-For` must not mint a fresh rate-limit bucket."""
    request = _request(**{"x-forwarded-for": "9.9.9.9"})
    assert client_ip(request) == "1.2.3.4"


def test_client_ip_without_peer_falls_back() -> None:
    assert client_ip(_request(client=None)) == UNKNOWN_CLIENT


def test_hash_identifier_is_stable_and_normalised() -> None:
    assert hash_identifier("User@Example.com ") == hash_identifier("user@example.com")
    assert "user@example.com" not in hash_identifier("user@example.com")


async def test_read_body_field_tolerates_garbage() -> None:
    assert await read_body_field(_request(b"not json"), "email") is None
    assert await read_body_field(_request(b""), "email") is None
    assert await read_body_field(_request(b'{"email": "a@b.co"}'), "email") == "a@b.co"


# --- Throttle dependency ----------------------------------------------------
async def test_rate_limit_allows_up_to_the_limit_then_rejects() -> None:
    dependency = rate_limit("test", 3, 60)
    for _ in range(3):
        assert await dependency(_request()) is None

    with pytest.raises(RateLimitException) as exc:
        await dependency(_request())
    assert exc.value.code == "RATE_LIMITED"
    assert exc.value.status_code == 429
    assert int(exc.value.headers["Retry-After"]) > 0


async def test_rate_limit_counters_are_per_ip() -> None:
    dependency = rate_limit("test", 2, 60)
    for _ in range(3):
        try:
            await dependency(_request(client=("1.1.1.1", 1)))
        except RateLimitException:
            pass
    # A different IP has its own budget.
    assert await dependency(_request(client=("2.2.2.2", 1))) is None


async def test_rate_limit_counts_identifier_across_ips() -> None:
    """The identifier counter stops a distributed attack on one account."""
    dependency = rate_limit("test", 2, 60, identifier_field="email")
    body = b'{"email": "victim@example.com"}'
    await dependency(_request(body, client=("1.1.1.1", 1)))
    await dependency(_request(body, client=("2.2.2.2", 1)))

    with pytest.raises(RateLimitException):
        await dependency(_request(body, client=("3.3.3.3", 1)))  # 3rd IP, same email


async def test_rate_limit_fails_open_when_redis_is_down(monkeypatch: pytest.MonkeyPatch) -> None:
    """A Redis outage must not take authentication down (documented tradeoff)."""

    class BrokenRedis:
        async def incr(self, *_a: object, **_k: object) -> int:
            raise ConnectionError("redis is down")

    monkeypatch.setattr(redis_cache, "_client", BrokenRedis())
    dependency = rate_limit("test", 1, 60)
    for _ in range(5):
        assert await dependency(_request()) is None


async def test_rate_limit_can_be_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "rate_limit_enabled", False)
    dependency = rate_limit("test", 1, 60)
    for _ in range(5):
        assert await dependency(_request()) is None


# --- Account lockout (AuthService.login) ------------------------------------
async def _fail_login(service, email: str) -> None:
    with pytest.raises(AuthenticationException):
        await service.login(org_id=1, email=email, password="wrong-password")


async def test_repeated_failures_lock_the_account(service, fake_user) -> None:
    """After N failed attempts, even the CORRECT password is rejected with 429."""
    service.users.get_by_email.return_value = fake_user
    service.sessions.create_session.return_value = SimpleNamespace(id=10)

    for _ in range(settings.login_max_failed_attempts):
        await _fail_login(service, fake_user.email)

    with pytest.raises(RateLimitException) as exc:
        await service.login(org_id=1, email=fake_user.email, password=TEST_PASSWORD)
    assert exc.value.code == "RATE_LIMITED"
    assert exc.value.status_code == 429
    assert int(exc.value.headers["Retry-After"]) > 0
    # The correct password never reached the credential check.
    service.sessions.create_session.assert_not_awaited()


async def test_lockout_is_audited(service, fake_user) -> None:
    service.users.get_by_email.return_value = fake_user
    for _ in range(settings.login_max_failed_attempts):
        await _fail_login(service, fake_user.email)

    kwargs = service.audit.record.await_args.kwargs
    assert kwargs["module"] == "auth"
    assert kwargs["sub_module"] == "lockout"
    assert kwargs["title"] == "Account locked"
    assert kwargs["org_id"] == fake_user.org_id
    # Never leak the secret that was tried.
    assert "wrong-password" not in kwargs["description"]


async def test_lockout_applies_to_unknown_emails(service) -> None:
    """Unknown addresses are counted too, else lockout leaks which emails exist."""
    service.users.get_by_email.return_value = None
    for _ in range(settings.login_max_failed_attempts):
        await _fail_login(service, "ghost@example.com")

    with pytest.raises(RateLimitException):
        await service.login(org_id=1, email="ghost@example.com", password="x")
    assert service.audit.record.await_args.kwargs["performed_by_user_id"] is None


async def test_failures_below_the_threshold_do_not_lock(service, fake_user) -> None:
    service.users.get_by_email.return_value = fake_user
    service.sessions.create_session.return_value = SimpleNamespace(id=10)

    for _ in range(settings.login_max_failed_attempts - 1):
        await _fail_login(service, fake_user.email)

    result = await service.login(org_id=1, email=fake_user.email, password=TEST_PASSWORD)
    assert result.access_token


async def test_successful_login_resets_the_failure_counter(
    service, fake_user, fake_redis
) -> None:
    """A good login clears the streak, so the next failure starts from zero."""
    service.users.get_by_email.return_value = fake_user
    service.sessions.create_session.return_value = SimpleNamespace(id=10)

    for _ in range(settings.login_max_failed_attempts - 1):
        await _fail_login(service, fake_user.email)
    assert await fake_redis.get(_failure_key(1, fake_user.email)) is not None

    await service.login(org_id=1, email=fake_user.email, password=TEST_PASSWORD)
    assert await fake_redis.get(_failure_key(1, fake_user.email)) is None
    assert await fake_redis.get(_lockout_key(1, fake_user.email)) is None

    # The streak restarts: one more failure must not re-trip the lockout.
    await _fail_login(service, fake_user.email)
    result = await service.login(org_id=1, email=fake_user.email, password=TEST_PASSWORD)
    assert result.access_token


async def test_login_lockout_fails_open_when_redis_is_down(
    service, fake_user, monkeypatch: pytest.MonkeyPatch
) -> None:
    """With Redis down, login still works and still rejects bad credentials."""

    class BrokenRedis:
        async def incr(self, *_a: object, **_k: object) -> int:
            raise ConnectionError("redis is down")

        async def ttl(self, *_a: object, **_k: object) -> int:
            raise ConnectionError("redis is down")

        async def delete(self, *_a: object, **_k: object) -> int:
            raise ConnectionError("redis is down")

    monkeypatch.setattr(redis_cache, "_client", BrokenRedis())
    service.users.get_by_email.return_value = fake_user
    service.sessions.create_session.return_value = SimpleNamespace(id=10)

    for _ in range(settings.login_max_failed_attempts + 2):
        await _fail_login(service, fake_user.email)

    result = await service.login(org_id=1, email=fake_user.email, password=TEST_PASSWORD)
    assert result.access_token


# --- Rate-limit trip auditing (AuthService.record_rate_limit_event) ----------
async def test_record_rate_limit_event_writes_auth_audit_row(service) -> None:
    await service.record_rate_limit_event(
        org_id=1, scope="login", ip_address="1.2.3.4", identifier="user@example.com"
    )
    assert isinstance(service.audit, AsyncMock)
    kwargs = service.audit.record.await_args.kwargs
    assert kwargs["module"] == "auth"
    assert kwargs["sub_module"] == "rate_limit"
    assert kwargs["action_type"].value == "Insert"
    assert "1.2.3.4" in kwargs["description"]
    assert kwargs["performed_by_user_id"] is None
