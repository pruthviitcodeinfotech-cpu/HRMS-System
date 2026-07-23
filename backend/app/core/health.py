"""Liveness / readiness probes and startup dependency validation.

Three distinct questions, three distinct answers — conflating them is how a rolling
deploy takes a service down:

* **Liveness** (``/health``) — "is the process alive?" Touches nothing. A failing
  liveness probe means *restart me*, so it must never depend on an external service:
  a Redis outage restarting every pod turns a degraded system into an outage.
* **Readiness** (``/health/ready``) — "can I serve traffic?" Checks the database and,
  where it is mandatory, Redis. A failing readiness probe means *take me out of the
  load-balancer pool* — the pod stays up and recovers on its own.
* **Startup validation** — run once in the lifespan. In production a missing database
  or Redis is a misconfiguration, and the honest thing is to refuse to start rather
  than serve traffic that silently misbehaves (an unreachable Redis disables rate
  limiting entirely — see :mod:`app.core.dependencies.rate_limit`).
"""

from __future__ import annotations

import asyncio
from typing import Any

from sqlalchemy import text

from app.core.config.settings import settings
from app.core.database.session import get_session_factory
from app.core.logging.config import get_logger

_logger = get_logger("health")

#: A probe must never hang a request or a deploy behind a wedged dependency.
_PROBE_TIMEOUT_SECONDS = 3.0


class DependencyUnavailableError(RuntimeError):
    """A dependency required to serve traffic is unreachable."""


async def check_database() -> tuple[bool, str | None]:
    """Return ``(healthy, error)`` for the database."""
    try:
        async def _exec():
            async with get_session_factory()() as session:
                await session.execute(text("SELECT 1"))
        await asyncio.wait_for(_exec(), timeout=_PROBE_TIMEOUT_SECONDS)
        return True, None
    except Exception as exc:  # noqa: BLE001 - any failure means "not ready"
        return False, str(exc)


async def check_redis() -> tuple[bool, str | None]:
    """Return ``(healthy, error)`` for Redis."""
    from app.core.cache.redis import get_redis

    try:
        await asyncio.wait_for(get_redis().ping(), timeout=_PROBE_TIMEOUT_SECONDS)
        return True, None
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)


def redis_is_required() -> bool:
    """Whether Redis must be reachable for this deployment to be considered healthy.

    Redis backs the login throttle, account lockout, caching, and background jobs.
    In production, if require_redis_in_production is enabled, Redis connectivity is strictly required.
    """
    return settings.is_production and settings.require_redis_in_production


async def readiness() -> tuple[bool, dict[str, Any]]:
    """Probe every dependency; return ``(ready, report)``."""
    (db_ok, db_err), (redis_ok, redis_err) = await asyncio.gather(
        check_database(), check_redis()
    )
    redis_required = redis_is_required()

    checks: dict[str, Any] = {
        "database": {"status": "ok" if db_ok else "error", "required": True},
        "redis": {
            "status": "ok" if redis_ok else "error",
            "required": redis_required,
        },
    }
    if db_err:
        checks["database"]["error"] = db_err
    if redis_err:
        checks["redis"]["error"] = redis_err
        if not redis_required:
            # Degraded, not unready: caches fall back to the database and the auth
            # throttle fails open. Surfaced so monitoring can alert on it.
            checks["redis"]["impact"] = "cache bypassed; login rate limiting disabled"

    ready = db_ok and (redis_ok or not redis_required)
    return ready, {"ready": ready, "environment": settings.environment.value, "checks": checks}


async def validate_startup_dependencies() -> None:
    """Fail fast on a misconfigured production deployment.

    Outside production this only warns: a developer running ``make run`` without Redis
    should get a working API, not a startup crash.
    """
    _logger.info(
        "redis_config_validation_started",
        redis_url=settings.redis_url,
        require_redis_in_production=settings.require_redis_in_production,
        environment=settings.environment.value,
    )

    problems: list[str] = []

    # 1. Validate configuration values
    if not (settings.redis_url.startswith("redis://") or settings.redis_url.startswith("rediss://")):
        problems.append(
            f"Invalid REDIS_URL scheme: '{settings.redis_url}'. Must start with redis:// or rediss://"
        )

    db_ok, db_err = await check_database()
    redis_ok, redis_err = await check_redis()

    if not db_ok:
        problems.append(f"database is unreachable ({db_err})")

    redis_required = redis_is_required()
    if not redis_ok:
        err_msg = (
            f"redis is unreachable ({redis_err}) and is required in production "
            "because require_redis_in_production is enabled"
        )
        if redis_required:
            problems.append(err_msg)
            _logger.error(
                "redis_connectivity_check_failed",
                error=redis_err,
                required=True,
                environment=settings.environment.value,
            )
        else:
            _logger.warning(
                "redis_connectivity_check_failed",
                error=redis_err,
                required=False,
                environment=settings.environment.value,
            )
    else:
        _logger.info(
            "redis_connectivity_check_passed",
            redis_url=settings.redis_url,
            environment=settings.environment.value,
        )

    if not problems:
        _logger.info("redis_config_validation_passed")
        return

    if settings.is_production:
        _logger.error("startup_dependency_check_failed", problems=problems)
        raise DependencyUnavailableError(
            "Refusing to start: " + "; ".join(problems) + "."
        )

    _logger.warning("startup_dependency_check_failed", problems=problems)
