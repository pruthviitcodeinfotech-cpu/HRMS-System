"""Middleware registration.

``register_middleware(app)`` installs the reusable middleware stack in the correct
order. Starlette runs middleware in the *reverse* order of registration, so the
first ``add_middleware`` call is the outermost layer at runtime. Ordering here
ensures the correlation id is bound before anything logs, and GZip/CORS/TrustedHost
wrap the application as required by the architecture.
"""

from __future__ import annotations

from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.gzip import GZipMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.core.config.settings import settings
from app.core.middleware.error_handler import ExceptionHandlingMiddleware
from app.core.middleware.logging import RequestLoggingMiddleware
from app.core.middleware.request_context import RequestContextMiddleware
from app.core.middleware.tenant import TenantMiddleware

__all__ = ["register_middleware"]


def register_middleware(app: FastAPI) -> None:
    """Install the shared middleware stack on ``app``."""
    # Registered last -> runs innermost. Registered first -> runs outermost.
    app.add_middleware(TenantMiddleware)
    app.add_middleware(RequestLoggingMiddleware)

    # Safety net wrapping the inner stack (the registered exception handlers remain
    # the primary error boundary for route-level exceptions).
    app.add_middleware(ExceptionHandlingMiddleware)

    app.add_middleware(GZipMiddleware, minimum_size=1024)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins or ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID", "X-Response-Time-ms"],
    )

    app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.trusted_hosts)

    # Outermost: correlation id must be bound before any inner layer logs.
    app.add_middleware(RequestContextMiddleware)
