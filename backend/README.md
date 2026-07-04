# HRMS Backend

Enterprise HR & Payroll Management System — backend service.

- **Language:** Python 3.11+
- **Framework:** FastAPI (async)
- **Database:** PostgreSQL + SQLAlchemy (async) + Alembic
- **Validation:** Pydantic
- **Auth:** JWT + Refresh Tokens
- **Cache / Event Broker:** Redis
- **Real-time:** WebSockets
- **Background Jobs:** Redis-backed queue + scheduler
- **Testing:** Pytest
- **Architecture:** Modular Monolith (package-by-feature)

> **Status:** Backend Foundation Phase — project structure only. No business
> modules, models, APIs, or authentication are implemented yet.

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

## Getting started (once dependencies are added)

```bash
make install     # install dependencies
cp .env.example .env
make run         # start the API (uvicorn app.main:app --reload)
make worker      # start the background worker
make migrate     # apply database migrations
make test        # run the test suite
make lint        # ruff + mypy
make format      # black + ruff --fix
```

See [`docs/architecture.md`](docs/architecture.md) for the full architecture reference.
