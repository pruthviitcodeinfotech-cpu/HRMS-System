"""Async Redis client provider and small cache helpers.

Exposes a lazily-created, process-wide ``redis.asyncio`` client (cache, pub/sub,
event broker, job queue all share the same connection pool) plus thin JSON
get/set/delete helpers with a default TTL from settings.
"""

from __future__ import annotations

import json
from typing import Any

import redis.asyncio as aioredis

from app.core.config.settings import settings

_client: aioredis.Redis | None = None


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
    """Return the JSON-decoded value at ``key`` (or ``None`` if absent)."""
    raw = await get_redis().get(key)
    return json.loads(raw) if raw is not None else None


async def cache_set_json(key: str, value: Any, *, ttl: int | None = None) -> None:
    """JSON-encode and store ``value`` at ``key`` with a TTL (defaults to config)."""
    expire = ttl if ttl is not None else settings.cache_ttl_seconds
    await get_redis().set(key, json.dumps(value, default=str), ex=expire or None)


async def cache_delete(*keys: str) -> None:
    """Delete one or more cache keys."""
    if keys:
        await get_redis().delete(*keys)
