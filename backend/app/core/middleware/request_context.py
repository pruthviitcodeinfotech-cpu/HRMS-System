"""Per-request correlation context (request id + user id + org id).

Stores request-scoped values in ``contextvars`` so any layer (logging, services)
can read them without threading them through call signatures. The
:class:`RequestContextMiddleware` assigns/echoes the ``X-Request-ID`` header and
resets the context after each request.
"""

from __future__ import annotations

from contextvars import ContextVar
from uuid import uuid4

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.core.constants.enums import REQUEST_ID_HEADER

_request_id_ctx: ContextVar[str | None] = ContextVar("request_id", default=None)
_user_id_ctx: ContextVar[int | None] = ContextVar("user_id", default=None)
_org_id_ctx: ContextVar[int | None] = ContextVar("org_id", default=None)


def get_request_id() -> str | None:
    """Return the current request's correlation id (``None`` outside a request)."""
    return _request_id_ctx.get()


def set_request_id(request_id: str) -> None:
    _request_id_ctx.set(request_id)


def get_current_user_id() -> int | None:
    """Return the authenticated user id bound to the current request."""
    return _user_id_ctx.get()


def set_current_user_id(user_id: int | None) -> None:
    _user_id_ctx.set(user_id)


def get_current_org_id() -> int | None:
    """Return the tenant (org) id bound to the current request."""
    return _org_id_ctx.get()


def set_current_org_id(org_id: int | None) -> None:
    _org_id_ctx.set(org_id)


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Bind a correlation id to each request and echo it on the response."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        request_id = request.headers.get(REQUEST_ID_HEADER) or uuid4().hex
        request.state.request_id = request_id
        id_token = _request_id_ctx.set(request_id)
        user_token = _user_id_ctx.set(None)
        org_token = _org_id_ctx.set(None)
        try:
            response = await call_next(request)
        finally:
            _request_id_ctx.reset(id_token)
            _user_id_ctx.reset(user_token)
            _org_id_ctx.reset(org_token)
        response.headers[REQUEST_ID_HEADER] = request_id
        return response
