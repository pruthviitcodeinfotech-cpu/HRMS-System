"""A lost uniqueness race is a 409, not a 500.

Services pre-check uniqueness before inserting, but the check and the insert are not
atomic. Two concurrent identical requests both pass the check and one loses at the
database. Before this handler existed, that loser got an unhandled ``IntegrityError``
-> ``500 INTERNAL_ERROR``.

Measured against a real PostgreSQL: 10 concurrent identical `POST /departments`
produced **1 x 201 and 9 x 500**. With the handler: 1 x 201 and 9 x 409.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.exc import IntegrityError

from app.core.exceptions import register_exception_handlers


def _integrity_error(sqlstate: str, constraint: str = "uq_departments_org_id_dept_name"):
    orig = SimpleNamespace(sqlstate=sqlstate, pgcode=sqlstate, constraint_name=constraint)
    return IntegrityError("INSERT ...", {}, orig)


@pytest.fixture
def client_raising():
    """An app whose endpoint raises whatever IntegrityError the test asks for."""

    def _build(exc: IntegrityError) -> AsyncClient:
        app = FastAPI()
        register_exception_handlers(app)

        @app.post("/boom")
        async def _boom() -> None:
            raise exc

        return AsyncClient(transport=ASGITransport(app=app), base_url="http://t")

    return _build


async def test_unique_violation_is_409_conflict(client_raising) -> None:
    async with client_raising(_integrity_error("23505")) as c:
        r = await c.post("/boom")
    assert r.status_code == 409
    body = r.json()
    assert body["error"]["code"] == "CONFLICT"
    assert body["success"] is False


async def test_foreign_key_violation_is_409(client_raising) -> None:
    async with client_raising(_integrity_error("23503")) as c:
        r = await c.post("/boom")
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "CONFLICT"


async def test_not_null_violation_is_422(client_raising) -> None:
    async with client_raising(_integrity_error("23502")) as c:
        r = await c.post("/boom")
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "VALIDATION_ERROR"


async def test_check_violation_is_422(client_raising) -> None:
    async with client_raising(_integrity_error("23514")) as c:
        r = await c.post("/boom")
    assert r.status_code == 422


async def test_unknown_sqlstate_still_conflicts_not_500(client_raising) -> None:
    """Any integrity violation is a client-visible conflict — never a server fault."""
    async with client_raising(_integrity_error("99999")) as c:
        r = await c.post("/boom")
    assert r.status_code == 409


async def test_driver_message_is_never_leaked(client_raising) -> None:
    """The driver text can carry SQL and column values — it must not reach the client."""
    exc = IntegrityError(
        'INSERT INTO users (email, password_hash) VALUES ("a@b.c", "$2b$12$secret")',
        {},
        SimpleNamespace(sqlstate="23505", pgcode="23505", constraint_name="uq_users_email"),
    )
    async with client_raising(exc) as c:
        r = await c.post("/boom")
    text = r.text
    assert "password_hash" not in text
    assert "$2b$12$" not in text
    assert "INSERT INTO" not in text
