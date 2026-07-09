"""ASGI application entrypoint and app factory for the HRMS backend.

The app factory wires the shared foundation: structured logging, the middleware
stack, global exception handlers, and resource lifecycle (Redis + DB engine). No
business routers are mounted yet — modules register their routers on
``app.api.v1.router`` and it is included here once implemented.

Run (once dependencies are installed):
    uvicorn app.main:app --reload
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.cache.redis import close_redis
from app.core.config.settings import settings
from app.core.database.session import dispose_engine
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging, get_logger
from app.core.middleware import register_middleware

_logger = get_logger("app")


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Application startup/shutdown lifecycle."""
    _logger.info("app_starting", environment=settings.environment.value)
    yield
    await close_redis()
    await dispose_engine()
    _logger.info("app_stopped")


def create_app() -> FastAPI:
    """Build and configure the FastAPI application."""
    configure_logging()

    app = FastAPI(
        title="HRMS Backend",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url=f"{settings.api_v1_prefix}/openapi.json",
        lifespan=lifespan,
    )

    register_middleware(app)
    register_exception_handlers(app)

    @app.get("/health", tags=["system"], summary="Liveness/readiness probe")
    async def health() -> dict[str, str]:
        """Lightweight health check (no dependencies touched)."""
        return {"status": "ok", "environment": settings.environment.value}

    # Module routers are aggregated in the v1 router and mounted at the API prefix.
    from app.api.v1.router import api_router

    app.include_router(api_router, prefix=settings.api_v1_prefix)

    return app


app = create_app()
