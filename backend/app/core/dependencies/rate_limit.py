"""Redis-backed request throttling for auth-sensitive endpoints.

:func:`rate_limit` is a **dependency factory**: it returns a FastAPI dependency
that rejects a caller with :class:`~app.core.exceptions.base.RateLimitException`
(``429 RATE_LIMITED``, per the Authentication API Contract §7/§8) once they exceed
``attempts`` requests inside ``window_seconds``.

Two independent counters
------------------------
Each request increments up to **two** fixed-window counters:

    * one keyed by the **client IP** — stops a single host hammering the endpoint;
    * one keyed by the **submitted identifier** (``identifier_field``, e.g. the
      login email) — stops a distributed attack from grinding one account.

Both are required. An IP-only limit lets a botnet brute-force one account from
many hosts; an identifier-only limit lets one host enumerate many accounts. They
are separate keys so a noisy IP can never exhaust another user's budget (and vice
versa) — neither counter can lock out a victim it does not belong to.

Failure policy: **fail open, log loudly**
-----------------------------------------
When Redis is unreachable the throttle is skipped and an ``ERROR`` is logged
(``rate_limit_backend_unavailable``). This is a deliberate tradeoff:

    * *Failing closed* would turn any Redis blip into a total authentication
      outage — nobody, including administrators responding to the incident, could
      log in. A cache dependency would become a single point of failure for the
      whole product.
    * *Failing open* degrades to the pre-existing security posture (password
      verification is still constant-cost and non-disclosing, credentials are
      still required) for the duration of the outage, and the ``ERROR`` log is a
      pageable signal.

The exposure window is therefore bounded by how fast Redis is restored, and the
loss is a *defence-in-depth* layer rather than the primary control. That is the
better side of the tradeoff for this system. **Every** Redis touch below routes
through the ``safe_*`` helpers so this policy is applied consistently — including
by the account-lockout logic in :class:`app.modules.auth.service.AuthService`,
which imports them from here.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Awaitable, Callable

from fastapi import Request

from app.core.cache.redis import cache_delete, counter_incr, flag_set, flag_ttl
from app.core.config.settings import settings
from app.core.exceptions.base import RateLimitException
from app.core.logging.config import get_logger

_logger = get_logger("rate_limit")

#: Client-IP placeholder when the ASGI server does not expose a peer address.
UNKNOWN_CLIENT = "unknown"

_BACKEND_UNAVAILABLE = "rate_limit_backend_unavailable"


# ---------------------------------------------------------------------------
# Key helpers
# ---------------------------------------------------------------------------
def client_ip(request: Request) -> str:
    """Return the peer address of ``request``.

    Uses the transport-level peer (``request.client.host``) only. ``X-Forwarded-For``
    is **deliberately not trusted**: any client can forge it, and honouring it while
    the app is directly reachable would let an attacker rotate the header to get an
    unlimited number of fresh rate-limit buckets (or frame another IP). When this
    service is deployed behind a reverse proxy / load balancer, the peer address
    becomes the proxy's, so the deployment must either run Uvicorn with
    ``--proxy-headers`` + ``--forwarded-allow-ips=<proxy ip>`` (which rewrites
    ``request.client`` from the trusted proxy's header) or add an equivalent trusted
    middleware. Only then may ``X-Forwarded-For`` be consulted, and only its
    proxy-appended entry.
    """
    return request.client.host if request.client else UNKNOWN_CLIENT


def hash_identifier(value: str) -> str:
    """Return a short, stable digest of ``value`` (case/whitespace-insensitive).

    Identifiers (emails) are hashed rather than embedded verbatim so the cache does
    not accumulate plaintext PII in its keyspace.
    """
    return hashlib.sha256(value.strip().lower().encode("utf-8")).hexdigest()[:32]


def counter_key(scope: str, bucket: str, value: str) -> str:
    """Build the Redis key for one counter, e.g. ``ratelimit:login:ip:1.2.3.4``."""
    return f"ratelimit:{scope}:{bucket}:{value}"


async def read_body_field(request: Request, field: str) -> str | None:
    """Best-effort read of a top-level string ``field`` from the JSON body.

    Safe to call from a dependency: FastAPI has already consumed and cached the
    body by the time dependencies are solved, so this neither blocks nor steals the
    stream from the endpoint. Malformed / non-JSON bodies simply yield ``None``
    (the request will fail validation in the endpoint anyway).
    """
    try:
        body = await request.body()
        if not body:
            return None
        payload = json.loads(body)
    except (json.JSONDecodeError, UnicodeDecodeError, ValueError):
        return None
    if not isinstance(payload, dict):
        return None
    value = payload.get(field)
    return value if isinstance(value, str) and value.strip() else None


# ---------------------------------------------------------------------------
# Fail-open Redis wrappers (see the module docstring for the tradeoff)
# ---------------------------------------------------------------------------
async def safe_counter_incr(key: str, *, window_seconds: int) -> tuple[int, int]:
    """Increment a fixed-window counter; return ``(0, 0)`` if Redis is unavailable."""
    try:
        return await counter_incr(key, window_seconds=window_seconds)
    except Exception as exc:  # noqa: BLE001 - any backend failure must fail open
        _logger.error(_BACKEND_UNAVAILABLE, operation="incr", key=key, error=str(exc))
        return 0, 0


async def safe_flag_set(key: str, *, ttl_seconds: int) -> None:
    """Set a self-expiring flag; a Redis failure is logged and ignored."""
    try:
        await flag_set(key, ttl_seconds=ttl_seconds)
    except Exception as exc:  # noqa: BLE001 - any backend failure must fail open
        _logger.error(_BACKEND_UNAVAILABLE, operation="set", key=key, error=str(exc))


async def safe_flag_ttl(key: str) -> int:
    """Return a flag's remaining TTL; ``-2`` (absent) if Redis is unavailable."""
    try:
        return await flag_ttl(key)
    except Exception as exc:  # noqa: BLE001 - any backend failure must fail open
        _logger.error(_BACKEND_UNAVAILABLE, operation="ttl", key=key, error=str(exc))
        return -2


async def safe_delete(*keys: str) -> None:
    """Delete keys; a Redis failure is logged and ignored."""
    try:
        await cache_delete(*keys)
    except Exception as exc:  # noqa: BLE001 - any backend failure must fail open
        _logger.error(_BACKEND_UNAVAILABLE, operation="delete", key=",".join(keys), error=str(exc))


# ---------------------------------------------------------------------------
# Enforcement
# ---------------------------------------------------------------------------
def rate_limit_exceeded(retry_after: int) -> RateLimitException:
    """Build the ``429 RATE_LIMITED`` error, carrying a ``Retry-After`` header."""
    exc = RateLimitException(
        f"Too many requests. Please try again in {retry_after} second(s)."
    )
    # Rendered by the AppException handler; RFC 9110 §10.2.3 delay-seconds form.
    exc.headers = {"Retry-After": str(retry_after)}  # type: ignore[attr-defined]
    return exc


async def enforce_counter(*, key: str, attempts: int, window_seconds: int) -> None:
    """Increment ``key`` and raise ``RateLimitException`` once ``attempts`` is passed."""
    count, ttl = await safe_counter_incr(key, window_seconds=window_seconds)
    if count > attempts:
        retry_after = ttl if ttl > 0 else window_seconds
        _logger.warning("rate_limit_exceeded", key=key, count=count, limit=attempts)
        raise rate_limit_exceeded(retry_after)


def rate_limit(
    key: str,
    attempts: int,
    window_seconds: int,
    *,
    identifier_field: str | None = None,
) -> Callable[[Request], Awaitable[None]]:
    """Build a FastAPI dependency enforcing ``attempts`` per ``window_seconds``.

    Args:
        key: scope name for the counters (e.g. ``"login"``).
        attempts: requests allowed per window, per counter.
        window_seconds: fixed-window length.
        identifier_field: optional top-level JSON body field (e.g. ``"email"``)
            given its own counter, in addition to the per-IP one.

    Returns:
        An async dependency that returns ``None`` or raises ``RateLimitException``.
    """

    async def _enforce_rate_limit(request: Request) -> None:
        if not settings.rate_limit_enabled:
            return
        await enforce_counter(
            key=counter_key(key, "ip", client_ip(request)),
            attempts=attempts,
            window_seconds=window_seconds,
        )
        if identifier_field is not None:
            identifier = await read_body_field(request, identifier_field)
            if identifier is not None:
                await enforce_counter(
                    key=counter_key(key, "id", hash_identifier(identifier)),
                    attempts=attempts,
                    window_seconds=window_seconds,
                )

    return _enforce_rate_limit


__all__ = [
    "UNKNOWN_CLIENT",
    "client_ip",
    "counter_key",
    "enforce_counter",
    "hash_identifier",
    "rate_limit",
    "rate_limit_exceeded",
    "read_body_field",
    "safe_counter_incr",
    "safe_delete",
    "safe_flag_set",
    "safe_flag_ttl",
]
