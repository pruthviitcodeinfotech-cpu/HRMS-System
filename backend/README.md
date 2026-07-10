# HRMS Backend

Enterprise HR & Payroll Management System — backend service.

- **Language:** Python 3.12 (exactly — see [`docs/environment.md`](docs/environment.md))
- **Framework:** FastAPI (async)
- **Database:** PostgreSQL + SQLAlchemy (async) + Alembic
- **Validation:** Pydantic
- **Auth:** JWT + Refresh Tokens
- **Cache / Event Broker:** Redis
- **Real-time:** WebSockets
- **Background Jobs:** Redis-backed queue + scheduler
- **Testing:** Pytest
- **Architecture:** Modular Monolith (package-by-feature)

> **Status:** 12 modules are implemented and mounted (222 endpoints under `/api/v1`).
> The `payroll`, `leave`, `audit`, and `organization` routers are still placeholders and
> are deliberately not mounted; their service layers exist but have no HTTP surface.

## Layout

```
app/
  core/            Framework foundation (config, db, security, middleware, events)
  shared/          Reusable domain building blocks (base classes, envelopes, utils)
  api/             HTTP surface + versioning (v1, v2, ...)
  infrastructure/  External adapters (email, storage, websockets, notifications)
  jobs/            Background + scheduled work
  modules/         Business capabilities (each a self-contained vertical slice)
alembic/           Database migrations
tests/             Unit / integration / e2e test suite
```

Every folder under `app/modules/` follows the same internal structure — see
[`app/modules/README.md`](app/modules/README.md).

## Getting started

Requires **Python 3.12** and [`uv`](https://docs.astral.sh/uv/). Dependencies are frozen in
`uv.lock`; `make install` reproduces the exact environment used by Docker and CI.

```bash
make install     # frozen install into ./.venv (uv sync --frozen --extra dev)
cp .env.example .env
make run         # start the API on :8000
make migrate     # apply database migrations
make test        # run the test suite
make lint        # ruff + mypy
make format      # black + ruff --fix
make lock        # regenerate uv.lock + requirements*.txt after editing pyproject.toml
```

Or with Docker:

```bash
docker compose up --build    # db + redis + api on :8000
```

See [`docs/environment.md`](docs/environment.md) for the supported Python version and the
dependency workflow, and [`docs/architecture.md`](docs/architecture.md) for the full
architecture reference.
