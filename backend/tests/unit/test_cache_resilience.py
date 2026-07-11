"""A Redis outage must degrade to a cache miss, never to a failed request.

Before this, ``cache_get_json`` propagated the ``ConnectionError`` straight out of the
Dashboard and Reports services, so an unreachable Redis turned every cached endpoint
into an unhandled 500 — a cache, which is an optimisation, was a single point of
failure for the product.

The rate-limiter primitives (``counter_incr`` / ``flag_*``) deliberately still raise:
their caller owns the failure policy. That contract is pinned here too, so nobody
"helpfully" makes them swallow errors and silently disables brute-force protection.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app.core.cache.redis import (
    cache_delete,
    cache_get_json,
    cache_set_json,
    counter_incr,
    flag_set,
    flag_ttl,
)


class _DeadRedis:
    """Every operation fails, the way an unreachable Redis does."""

    def __getattr__(self, _name: str):  # noqa: ANN204
        async def _boom(*_args: object, **_kwargs: object) -> None:
            raise ConnectionError("Error 111 connecting to localhost:6379.")

        return _boom


# ---------------------------------------------------------------------------
# The JSON cache helpers must fail OPEN (degrade to a miss).
# ---------------------------------------------------------------------------


async def test_cache_get_returns_none_when_redis_is_down() -> None:
    """A cache outage is indistinguishable from a miss — the caller recomputes."""
    with patch("app.core.cache.redis.get_redis", return_value=_DeadRedis()):
        assert await cache_get_json("dashboard:summary:1") is None


async def test_cache_set_does_not_raise_when_redis_is_down() -> None:
    """Failing to *populate* the cache must not fail a request that already has the answer."""
    with patch("app.core.cache.redis.get_redis", return_value=_DeadRedis()):
        await cache_set_json("dashboard:summary:1", {"headcount": 200}, ttl=60)


async def test_cache_delete_does_not_raise_when_redis_is_down() -> None:
    with patch("app.core.cache.redis.get_redis", return_value=_DeadRedis()):
        await cache_delete("a", "b")


async def test_cache_still_round_trips_when_redis_is_healthy() -> None:
    """The fail-open guard must not swallow real results."""
    store: dict[str, str] = {}
    client = AsyncMock()
    client.get = AsyncMock(side_effect=lambda k: store.get(k))
    client.set = AsyncMock(side_effect=lambda k, v, ex=None: store.__setitem__(k, v))
    with patch("app.core.cache.redis.get_redis", return_value=client):
        await cache_set_json("k", {"a": 1})
        assert await cache_get_json("k") == {"a": 1}


# ---------------------------------------------------------------------------
# The rate-limiter primitives must keep RAISING (the caller owns the policy).
# ---------------------------------------------------------------------------


async def test_rate_limit_primitives_still_propagate_backend_failures() -> None:
    """If these silently swallowed errors, brute-force protection would vanish unnoticed."""
    with patch("app.core.cache.redis.get_redis", return_value=_DeadRedis()):
        with pytest.raises(ConnectionError):
            await counter_incr("ratelimit:login:ip:1.2.3.4", window_seconds=60)
        with pytest.raises(ConnectionError):
            await flag_set("auth:login:lockout:1:abc", ttl_seconds=900)
        with pytest.raises(ConnectionError):
            await flag_ttl("auth:login:lockout:1:abc")
