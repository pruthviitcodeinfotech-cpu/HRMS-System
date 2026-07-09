"""Multi-tenant context middleware.

Binds the resolved tenant (``org_id``) into the request context so downstream
layers (repositories, logging) can enforce org-scoping. Resolution order:

    1. ``request.state.org_id`` set by an auth dependency (from the access token), or
    2. the ``X-Org-ID`` header (used pre-authentication, e.g. at login — see the
       Authentication API Contract's open question on tenant resolution).

This middleware only *propagates* the value; it does not authenticate. Endpoints
still enforce that the principal belongs to the resolved org.
"""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.core.middleware.request_context import set_current_org_id

ORG_ID_HEADER = "X-Org-ID"


class TenantMiddleware(BaseHTTPMiddleware):
    """Resolve and bind ``org_id`` for the duration of the request."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        org_id = getattr(request.state, "org_id", None)
        if org_id is None:
            header_value = request.headers.get(ORG_ID_HEADER)
            if header_value and header_value.isdigit():
                org_id = int(header_value)
                request.state.org_id = org_id
        if org_id is not None:
            set_current_org_id(int(org_id))
        return await call_next(request)
