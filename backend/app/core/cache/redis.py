"""Async Redis client provider and small cache helpers.

Exposes a lazily-created, process-wide ``redis.asyncio`` client (cache, pub/sub,
event broker, job queue all share the same connection pool) plus thin JSON
get/set/delete helpers with a default TTL from settings.
"""

from __future__ import annotations

import json
from typing import Any

import redis.asyncio as aioredis
import structlog

from app.core.config.settings import settings

# structlog directly, not app.core.logging: this module is imported by ``app.main``
# before the logging package, and ``app.core.logging.config`` pulls in the middleware
# package — importing it here would close an import cycle. ``get_logger`` is a thin
# wrapper over ``structlog.get_logger`` anyway, so the behaviour is identical.
_logger = structlog.get_logger("cache")
_client: aioredis.Redis | None = None

#: A cache is an *optimisation*, not a source of truth. If Redis is unreachable the
#: correct behaviour is to serve the request from the database, not to fail it — a
#: Redis blip must never take a dashboard or a report offline. The JSON helpers below
#: therefore swallow backend errors and log them at ERROR so the outage is still
#: pageable. (The rate-limiter primitives at the bottom of this module deliberately do
#: NOT swallow: their caller owns the failure policy — see rate_limit.py.)
_CACHE_UNAVAILABLE = "cache_backend_unavailable"


def get_redis() -> aioredis.Redis:
    """Return the process-wide async Redis client, creating it on first use."""
    global _client
    if _client is None:
        _client = aioredis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
        )
    return _client


async def close_redis() -> None:
    """Close the Redis connection pool (call on application shutdown)."""
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None


async def cache_get_json(key: str) -> Any | None:
    """Return the JSON-decoded value at ``key``, or ``None`` if absent **or unreachable**.

    A cache miss and a cache outage are indistinguishable to the caller by design: both
    mean "no cached value, compute it". That is what keeps a Redis failure from turning
    a working endpoint into a 500.
    """
    try:
        raw = await get_redis().get(key)
    except Exception as exc:  # noqa: BLE001 - any backend failure degrades to a miss
        _logger.error(_CACHE_UNAVAILABLE, operation="get", key=key, error=str(exc))
        return None
    return json.loads(raw) if raw is not None else None


async def cache_set_json(key: str, value: Any, *, ttl: int | None = None) -> None:
    """JSON-encode and store ``value`` at ``key`` with a TTL (defaults to config).

    Best-effort: a failure to *populate* the cache must not fail the request that
    already computed the answer.
    """
    expire = ttl if ttl is not None else settings.cache_ttl_seconds
    try:
        await get_redis().set(key, json.dumps(value, default=str), ex=expire or None)
    except Exception as exc:  # noqa: BLE001 - writing the cache is never load-bearing
        _logger.error(_CACHE_UNAVAILABLE, operation="set", key=key, error=str(exc))


async def cache_delete(*keys: str) -> None:
    """Delete one or more cache keys (best-effort; a stale entry expires on its TTL)."""
    if not keys:
        return
    try:
        await get_redis().delete(*keys)
    except Exception as exc:  # noqa: BLE001
        _logger.error(_CACHE_UNAVAILABLE, operation="delete", keys=list(keys), error=str(exc))


# ---------------------------------------------------------------------------
# Counter / flag primitives (backing store for the rate limiter & lockout)
# ---------------------------------------------------------------------------
# These raise on a Redis failure — the *caller* decides the failure policy (the
# auth brute-force controls in :mod:`app.core.dependencies.rate_limit` fail open
# and log loudly; see the tradeoff note there).


async def counter_incr(key: str, *, window_seconds: int) -> tuple[int, int]:
    """Increment a fixed-window counter at ``key``; return ``(count, ttl_seconds)``.

    The window opens on the first increment (the TTL is armed when the counter is
    created) and the whole counter disappears when it elapses.
    """
    client = get_redis()
    count = int(await client.incr(key))
    if count == 1:
        await client.expire(key, window_seconds)
        return count, window_seconds
    ttl = int(await client.ttl(key))
    if ttl < 0:  # no TTL (e.g. the key survived a crash mid-increment) — re-arm it.
        await client.expire(key, window_seconds)
        ttl = window_seconds
    return count, ttl


async def flag_set(key: str, *, ttl_seconds: int) -> None:
    """Set a self-expiring boolean flag at ``key`` (used for the account lockout)."""
    await get_redis().set(key, "1", ex=ttl_seconds)


async def flag_ttl(key: str) -> int:
    """Return the remaining TTL of ``key`` in seconds (``-2`` when it does not exist)."""
    return int(await get_redis().ttl(key))
