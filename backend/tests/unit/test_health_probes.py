"""Liveness, readiness, and production startup validation.

The distinctions pinned here are the ones that decide whether a Redis blip is a
degradation or an outage:

* **Liveness must not touch a dependency.** If it did, an unreachable Redis would fail
  the probe, the orchestrator would restart every pod, and a degraded system would
  become a total outage.
* **Readiness must fail when the database is gone** (503, so the load balancer drains
  the instance) but stay ready when only Redis is gone *outside* production, where the
  cache falls back to the database.
* **Production must refuse to start without Redis**, because Redis backs the login
  throttle and the account lockout: without it, brute-force protection silently
  vanishes while the app looks perfectly healthy.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app.core.config.settings import Environment, settings
from app.core.health import (
    DependencyUnavailableError,
    readiness,
    redis_is_required,
    validate_startup_dependencies,
)


def _db(ok: bool):
    return patch(
        "app.core.health.check_database",
        AsyncMock(return_value=(True, None) if ok else (False, "connection refused")),
    )


def _redis(ok: bool):
    return patch(
        "app.core.health.check_redis",
        AsyncMock(return_value=(True, None) if ok else (False, "connection refused")),
    )


@pytest.fixture
def production(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "environment", Environment.PRODUCTION)
    monkeypatch.setattr(settings, "rate_limit_enabled", True)


# ---------------------------------------------------------------------------
# Readiness
# ---------------------------------------------------------------------------


async def test_ready_when_everything_is_up() -> None:
    with _db(True), _redis(True):
        ready, report = await readiness()
    assert ready is True
    assert report["checks"]["database"]["status"] == "ok"
    assert report["checks"]["redis"]["status"] == "ok"


async def test_not_ready_when_the_database_is_down() -> None:
    """No database means this instance cannot serve anything — drain it."""
    with _db(False), _redis(True):
        ready, report = await readiness()
    assert ready is False
    assert report["checks"]["database"]["status"] == "error"


async def test_still_ready_without_redis_outside_production() -> None:
    """A Redis outage degrades (cache bypassed, throttle off) — it does not un-ready."""
    with _db(True), _redis(False):
        ready, report = await readiness()
    assert ready is True
    assert report["checks"]["redis"]["status"] == "error"
    assert report["checks"]["redis"]["required"] is False
    assert "rate limiting disabled" in report["checks"]["redis"]["impact"]


async def test_not_ready_without_redis_in_production(production) -> None:
    with _db(True), _redis(False):
        ready, report = await readiness()
    assert ready is False
    assert report["checks"]["redis"]["required"] is True


# ---------------------------------------------------------------------------
# Redis is mandatory in production (and only where it actually matters)
# ---------------------------------------------------------------------------


def test_redis_is_required_in_production(production) -> None:
    assert redis_is_required() is True


def test_redis_is_not_required_in_development() -> None:
    assert redis_is_required() is False


def test_redis_is_not_required_if_rate_limiting_is_off(
    production, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Redis is mandatory *because* it backs rate limiting — not as dogma."""
    monkeypatch.setattr(settings, "rate_limit_enabled", False)
    assert redis_is_required() is False


# ---------------------------------------------------------------------------
# Startup validation
# ---------------------------------------------------------------------------


async def test_production_refuses_to_start_without_redis(production) -> None:
    with _db(True), _redis(False):
        with pytest.raises(DependencyUnavailableError) as exc:
            await validate_startup_dependencies()
    assert "redis is unreachable" in str(exc.value)
    assert "rate limiting" in str(exc.value)


async def test_production_refuses_to_start_without_a_database(production) -> None:
    with _db(False), _redis(True):
        with pytest.raises(DependencyUnavailableError):
            await validate_startup_dependencies()


async def test_production_starts_when_dependencies_are_healthy(production) -> None:
    with _db(True), _redis(True):
        await validate_startup_dependencies()  # must not raise


async def test_development_starts_without_redis() -> None:
    """`make run` must work on a laptop with no Redis — warn, do not crash."""
    with _db(True), _redis(False):
        await validate_startup_dependencies()  # must not raise
