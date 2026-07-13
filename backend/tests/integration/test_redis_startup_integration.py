"""Integration tests for Redis Production Enforcement startup lifecycle.

Verifies that the FastAPI lifespan startup behaves correctly depending on
the environment settings and Redis availability.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI

from app.core.config.settings import Environment, settings
from app.core.health import DependencyUnavailableError
from app.main import create_app


def _db(ok: bool):
    return patch(
        "app.core.health.check_database",
        AsyncMock(return_value=(True, None) if ok else (False, "connection refused")),
    )


def _redis(ok: bool):
    return patch(
        "app.core.health.check_redis",
        AsyncMock(return_value=(True, None) if ok else (False, "connection failed")),
    )


@pytest.fixture
def app() -> FastAPI:
    """Creates a fresh FastAPI instance with lifespans configured."""
    return create_app()


@pytest.mark.asyncio
async def test_app_lifespan_starts_when_everything_healthy(app: FastAPI) -> None:
    with _db(True), _redis(True):
        async with app.router.lifespan_context(app):
            pass  # Starts and stops without raising error


@pytest.mark.asyncio
async def test_app_lifespan_fails_in_production_when_redis_down(
    app: FastAPI, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "environment", Environment.PRODUCTION)
    monkeypatch.setattr(settings, "require_redis_in_production", True)

    with _db(True), _redis(False):
        with pytest.raises(DependencyUnavailableError) as exc_info:
            async with app.router.lifespan_context(app):
                pass
        assert "redis is unreachable" in str(exc_info.value)
        assert "require_redis_in_production is enabled" in str(exc_info.value)


@pytest.mark.asyncio
async def test_app_lifespan_warns_in_production_when_redis_down_but_not_enforced(
    app: FastAPI, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "environment", Environment.PRODUCTION)
    monkeypatch.setattr(settings, "require_redis_in_production", False)

    with _db(True), _redis(False):
        async with app.router.lifespan_context(app):
            pass  # Should warn but start successfully


@pytest.mark.asyncio
async def test_app_lifespan_starts_in_development_when_redis_down(
    app: FastAPI, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "environment", Environment.DEVELOPMENT)

    with _db(True), _redis(False):
        async with app.router.lifespan_context(app):
            pass  # Should warn but start successfully
