"""ASGI application entrypoint and app factory for the HRMS backend.

Foundation phase: this file only defines the assembly points. Cross-cutting
concerns and module routers are wired here incrementally as they are built.
No routes, models, authentication, or business logic are implemented yet.

Run (once dependencies are installed):
    uvicorn app.main:app --reload
"""

from fastapi import FastAPI


def create_app() -> FastAPI:
    """Build and configure the FastAPI application.

    Wiring is added incrementally during implementation:
        - register logging (app.core.logging.config)
        - register middleware (app.core.middleware)
        - register exception handlers (app.core.exceptions.handlers)
        - initialise database / redis / websocket manager on startup
        - mount the API router (app.api.router)
    """
    app = FastAPI(
        title="HRMS Backend",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # TODO (implementation phase): register_logging()
    # TODO (implementation phase): register_middleware(app)
    # TODO (implementation phase): register_exception_handlers(app)
    # TODO (implementation phase): register_events(app)
    # TODO (implementation phase): app.include_router(api_router)

    return app


app = create_app()
