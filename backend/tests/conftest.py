"""Shared pytest fixtures for the HRMS backend test suite.

Provides the reusable infrastructure the Authentication tests build on:

    * ``app``               — the production app factory with the auth router mounted.
    * ``client``            — an httpx ``AsyncClient`` over the ASGI app, with the
                              ``AuthService`` dependency overridden by a mock so
                              integration tests exercise the *router + real auth
                              dependency* without a database.
    * ``mock_auth_service`` — an ``AsyncMock`` standing in for ``AuthService``.
    * ``service``           — a real ``AuthService`` with mocked repositories, for
                              unit-testing business logic in isolation.
    * token / user helpers  — valid, expired, and fake-user builders.

No production code is modified; the app factory is reused as-is and the auth
router is included at the API prefix only for the test app instance.
"""

from __future__ import annotations

import math
import time
from collections.abc import AsyncIterator, Callable
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.core.cache import redis as redis_cache
from app.core.config.settings import settings
from app.core.dependencies.auth import assert_session_live
from app.core.security.jwt import create_access_token
from app.core.security.password import hash_password
from app.jobs import queue as job_queue
from app.main import create_app
from app.modules.auth.dependencies import get_auth_service
from app.modules.auth.router import router as auth_router
from app.modules.rbac.router import get_rbac_service
from app.modules.rbac.router import router as rbac_router

API_PREFIX = settings.api_v1_prefix
TEST_PASSWORD = "Secret123"


class FakeRedis:
    """Minimal in-memory stand-in for the async Redis client.

    ``fakeredis`` is not a project dependency (and adding one for this is not worth
    it), so the handful of commands the rate limiter and account lockout use —
    ``get/set/incr/expire/ttl/delete`` — are implemented here directly. Keys expire
    lazily against a monotonic clock, which is enough for TTL assertions.
    """

    def __init__(self) -> None:
        self.store: dict[str, str] = {}
        self.expiry: dict[str, float] = {}

    def _purge(self, key: str) -> None:
        deadline = self.expiry.get(key)
        if deadline is not None and deadline <= time.monotonic():
            self.store.pop(key, None)
            self.expiry.pop(key, None)

    async def get(self, key: str) -> str | None:
        self._purge(key)
        return self.store.get(key)

    async def set(self, key: str, value: object, ex: int | None = None) -> bool:
        self.store[key] = str(value)
        if ex:
            self.expiry[key] = time.monotonic() + ex
        else:
            self.expiry.pop(key, None)
        return True

    async def incr(self, key: str, amount: int = 1) -> int:
        self._purge(key)
        value = int(self.store.get(key, "0")) + amount
        self.store[key] = str(value)
        return value

    async def expire(self, key: str, seconds: int) -> bool:
        self._purge(key)
        if key not in self.store:
            return False
        self.expiry[key] = time.monotonic() + seconds
        return True

    async def ttl(self, key: str) -> int:
        self._purge(key)
        if key not in self.store:
            return -2  # no such key
        deadline = self.expiry.get(key)
        if deadline is None:
            return -1  # exists, no expiry
        return max(0, math.ceil(deadline - time.monotonic()))

    async def delete(self, *keys: str) -> int:
        removed = 0
        for key in keys:
            self.expiry.pop(key, None)
            if self.store.pop(key, None) is not None:
                removed += 1
        return removed

    async def aclose(self) -> None:
        return None


class FakeArqPool:
    """Minimal in-memory stand-in for the arq job pool (``ArqRedis``).

    The same idea as :class:`FakeRedis`, one layer up: it records what was enqueued
    instead of talking to a broker. ``enqueue`` only needs ``enqueue_job`` returning
    something with a ``job_id``.
    """

    def __init__(self) -> None:
        self.jobs: list[tuple[str, dict]] = []

    async def enqueue_job(self, function_name: str, **kwargs: object) -> SimpleNamespace:
        job_id = f"fake-job-{len(self.jobs)}"
        self.jobs.append((function_name, dict(kwargs)))
        return SimpleNamespace(job_id=job_id)

    async def aclose(self) -> None:
        return None


@pytest.fixture(autouse=True)
def fake_redis(monkeypatch: pytest.MonkeyPatch) -> FakeRedis:
    """Swap the process-wide Redis client for an in-memory fake, per test.

    Autouse so rate-limit / lockout counters never leak between tests (and so the
    suite never opens a real Redis connection). ``get_redis()`` returns the cached
    module-level ``_client`` when one is set, so patching it is enough.
    """
    fake = FakeRedis()
    monkeypatch.setattr(redis_cache, "_client", fake, raising=False)
    return fake


@pytest.fixture(autouse=True)
def fake_queue(monkeypatch: pytest.MonkeyPatch) -> FakeArqPool:
    """Swap the arq job pool for an in-memory fake, per test.

    Autouse for the same reason as ``fake_redis``: a service that enqueues (the payslip
    email, a large report export) must not dial a broker from a unit test. ``enqueue()``
    reuses the cached module-level ``_pool`` when one is set, so patching it is enough —
    ``create_pool`` is never reached. Tests that need to *observe* what was enqueued can
    request this fixture and read ``.jobs``.
    """
    fake = FakeArqPool()
    monkeypatch.setattr(job_queue, "_pool", fake, raising=False)
    return fake


@pytest.fixture
def app():
    """The production FastAPI app with the auth + rbac routers mounted at the API prefix."""
    application = create_app()
    application.include_router(auth_router, prefix=API_PREFIX)
    application.include_router(rbac_router, prefix=API_PREFIX)
    return application


@pytest.fixture
def mock_auth_service() -> AsyncMock:
    """An ``AsyncMock`` used to stub :class:`AuthService` in integration tests."""
    return AsyncMock()


@pytest.fixture
def mock_rbac_service() -> AsyncMock:
    """An ``AsyncMock`` used to stub :class:`RBACService` in integration tests."""
    return AsyncMock()


@pytest_asyncio.fixture
async def client(
    app, mock_auth_service: AsyncMock, mock_rbac_service: AsyncMock
) -> AsyncIterator[AsyncClient]:
    """An async HTTP client bound to the app, with the module services mocked."""
    # The auth dependency re-validates the session against the DB on every request;
    # router tests exercise the HTTP layer without a database, so stub that check.
    app.dependency_overrides[assert_session_live] = lambda: None
    app.dependency_overrides[get_auth_service] = lambda: mock_auth_service
    app.dependency_overrides[get_rbac_service] = lambda: mock_rbac_service
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as http_client:
        yield http_client
    app.dependency_overrides.clear()


@pytest.fixture
def make_access_token() -> Callable[..., str]:
    """Factory building a valid signed access token with configurable claims."""

    def _make(
        user_id: int = 1,
        *,
        org_id: int = 1,
        is_super_admin: bool = False,
        is_active: bool = True,
        session_id: str | None = "10",
        permissions: list[dict] | None = None,
        branch_ids: list[int] | None = None,
        department_ids: list[int] | None = None,
    ) -> str:
        return create_access_token(
            user_id,
            extra_claims={
                "org_id": org_id,
                "is_super_admin": is_super_admin,
                "is_active": is_active,
                "sid": session_id,
                "roles": ["super_admin"] if is_super_admin else [],
                "permissions": permissions or [],
                "branch_ids": branch_ids or [],
                "department_ids": department_ids or [],
            },
        )

    return _make


@pytest.fixture
def auth_headers(make_access_token: Callable[..., str]) -> dict[str, str]:
    """Authorization header carrying a valid access token for user 1."""
    return {"Authorization": f"Bearer {make_access_token()}"}


@pytest.fixture
def expired_token() -> str:
    """A correctly-signed but already-expired access token."""
    from jose import jwt

    now = datetime.now(UTC)
    payload = {
        "sub": "1",
        "type": "access",
        "jti": "expired-jti",
        "iat": int((now - timedelta(hours=2)).timestamp()),
        "exp": int((now - timedelta(hours=1)).timestamp()),
        "is_active": True,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


@pytest.fixture
def fake_user() -> SimpleNamespace:
    """A stand-in ``users`` row with a real bcrypt hash of ``TEST_PASSWORD``."""
    return SimpleNamespace(
        id=1,
        org_id=1,
        name="Test User",
        email="user@example.com",
        mobile_country_code="+91",
        mobile_number="9876543210",
        password_hash=hash_password(TEST_PASSWORD),
        is_super_admin=False,
        is_active=True,
        employee_id=None,
        last_login_at=None,
    )


@pytest.fixture
def service() -> object:
    """A real :class:`AuthService` whose repositories are replaced with mocks.

    Lets unit tests drive the business logic while stubbing all data access. The
    permission/scope reads default to empty lists so ``login`` / ``refresh`` /
    ``get_current_user`` can resolve authorization without extra setup.
    """
    from app.modules.auth.service import AuthService

    svc = AuthService(AsyncMock())
    svc.users = AsyncMock()
    svc.sessions = AsyncMock()
    svc.audit = AsyncMock()
    svc.users.get_template_permissions.return_value = []
    svc.users.get_custom_permissions.return_value = []
    svc.users.get_branch_ids.return_value = []
    svc.users.get_department_ids.return_value = []
    return svc


@pytest.fixture
def super_admin_headers(make_access_token: Callable[..., str]) -> dict[str, str]:
    """Authorization header for a super admin (bypasses feature-permission guards)."""
    return {"Authorization": f"Bearer {make_access_token(is_super_admin=True)}"}


@pytest.fixture
def rbac_service() -> object:
    """A real :class:`RBACService` with every repository replaced by an ``AsyncMock``.

    Count/flag reads used when serializing roles default to sensible values so the
    schema builders work without per-test setup.
    """
    from app.modules.rbac.service import RBACService

    svc = RBACService(AsyncMock())
    for attr in (
        "users",
        "roles",
        "template_perms",
        "assignments",
        "custom_perms",
        "branch_access",
        "dept_access",
        "sessions",
    ):
        setattr(svc, attr, AsyncMock())
    svc.audit = AsyncMock()
    svc.roles.permission_count.return_value = 0
    svc.roles.assigned_user_count.return_value = 0
    return svc


@pytest.fixture
def make_user() -> Callable[..., SimpleNamespace]:
    """Factory for a stand-in ``users`` ORM row (all fields the schemas read)."""

    def _make(**overrides: object) -> SimpleNamespace:
        now = datetime.now(UTC)
        base = {
            "id": 1,
            "org_id": 1,
            "name": "Test User",
            "email": "user@example.com",
            "mobile_country_code": "+91",
            "mobile_number": "9876543210",
            "password_hash": None,
            "is_super_admin": False,
            "is_active": True,
            "employee_id": None,
            "last_login_at": None,
            "created_at": now,
            "updated_at": now,
            "deleted_at": None,
        }
        base.update(overrides)
        return SimpleNamespace(**base)

    return _make


@pytest.fixture
def make_role() -> Callable[..., SimpleNamespace]:
    """Factory for a stand-in ``rights_templates`` ORM row."""

    def _make(**overrides: object) -> SimpleNamespace:
        now = datetime.now(UTC)
        base = {
            "id": 1,
            "org_id": 1,
            "name": "Administrator",
            "created_at": now,
            "updated_at": now,
            "deleted_at": None,
        }
        base.update(overrides)
        return SimpleNamespace(**base)

    return _make
