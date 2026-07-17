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
from fastapi.responses import JSONResponse

from app.core.cache.redis import close_redis
from app.core.config.settings import settings
from app.core.database.session import dispose_engine
from app.core.exceptions import register_exception_handlers
from app.core.health import readiness, validate_startup_dependencies
from app.core.logging import configure_logging, get_logger
from app.core.middleware import register_middleware

_logger = get_logger("app")


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Application startup/shutdown lifecycle."""
    _logger.info("app_starting", environment=settings.environment.value)
    # In production an unreachable database or Redis is a misconfiguration: refuse to
    # start rather than serve traffic that silently misbehaves. Outside production this
    # only warns, so `make run` still works without Redis.
    await validate_startup_dependencies()
    _logger.info("app_started", environment=settings.environment.value)
    yield
    await close_redis()
    await dispose_engine()
    _logger.info("app_stopped")


def create_app() -> FastAPI:
    """Build and configure the FastAPI application."""
    configure_logging()

    # The interactive docs enumerate every endpoint and schema. That is a gift to an
    # attacker and of no use to a production client, which has the contract already.
    expose_docs = not settings.is_production
    app = FastAPI(
        title="HRMS Backend",
        version="0.1.0",
        docs_url="/docs" if expose_docs else None,
        redoc_url="/redoc" if expose_docs else None,
        openapi_url=f"{settings.api_v1_prefix}/openapi.json" if expose_docs else None,
        lifespan=lifespan,
    )

    register_middleware(app)
    register_exception_handlers(app)

    @app.get("/health", tags=["system"], summary="Liveness probe")
    async def health() -> dict[str, str]:
        """Liveness: is the process alive? Touches no dependency.

        Deliberately does NOT check the database or Redis. A liveness failure means
        "restart me" — wiring it to an external service would make a Redis blip
        restart every pod, turning a degraded system into an outage.
        """
        return {"status": "ok", "environment": settings.environment.value}

    @app.get("/health/ready", tags=["system"], summary="Readiness probe")
    async def health_ready() -> JSONResponse:
        """Readiness: can this instance serve traffic?

        Checks the database, and Redis where it is mandatory. Returns ``503`` when not
        ready so the load balancer drains this instance without killing it.
        """
        ready, report = await readiness()
        return JSONResponse(status_code=200 if ready else 503, content=report)

    # Module routers are aggregated in the v1 router and mounted at the API prefix.
    from app.api.v1.router import api_router

    app.include_router(api_router, prefix=settings.api_v1_prefix)

    from app.modules.adms.router import router as adms_router

    app.include_router(adms_router, prefix="/iclock")

    return app


app = create_app()
