# HRMS Backend — Architecture Reference

## Style

**Modular Monolith, package-by-feature.** Cross-cutting foundation lives in
`core/`, `shared/`, and `infrastructure/`. Each business capability is a
self-contained vertical slice under `modules/`.

## Layers

```
router (HTTP)  →  service (business rules, tx)  →  repository (data access)  →  DB
```

- **Routers** are thin: HTTP mapping, auth/permission dependencies, validation, delegation.
- **Services** own business rules, invariants, orchestration, and transaction boundaries.
- **Repositories** own all queries and enforce `org_id` scoping.
- **Schemas (Pydantic DTOs)** are the only shapes crossing the API boundary; ORM models never leak out.

## Cross-cutting foundation

| Area | Location |
|---|---|
| Config (env-driven) | `core/config/` |
| Database (async engine/session, mixins) | `core/database/` |
| Security (JWT/refresh, hashing, permissions) | `core/security/` |
| Middleware (context, logging, tenant, errors) | `core/middleware/` |
| Exceptions + handlers | `core/exceptions/` |
| Dependencies (db, auth, pagination) | `core/dependencies/` |
| Domain-event bus | `core/events/` |
| Base classes + response envelopes + utils | `shared/` |
| Email / storage / websockets / notifications | `infrastructure/` |
| Background + scheduled jobs | `jobs/` |

## Request flow

```
Client → ASGI → middleware (correlation-id, logging, tenant)
       → api/v1 router → module router
       → deps: authenticate (JWT) → authorize (RBAC + scope) → validate (Pydantic) → db session
       → service (business rules, tx) → repository (org-scoped) → PostgreSQL
       → response schema → envelope → logging → Client
```

Errors bubble to `core/exceptions/handlers.py` → standard error envelope + rollback.

## Real-time & async

- **WebSockets:** `infrastructure/websockets/` (auth on connect, per-org rooms,
  push via connection manager on domain events).
- **Background/scheduled jobs:** `jobs/` (Redis-backed). Modules define work in
  their `tasks.py`; the worker/scheduler execute it (device sync, payroll
  compute, payslip auto-release, report export).

## Multi-tenancy

Every table carries `org_id`. Tenancy is enforced centrally via the tenant
middleware + `TenantMixin` + base-repository scoping so queries cannot cross orgs.

## RBAC

Two-layer authorization: feature-level CRUD permissions (rights templates +
per-user overrides) × branch/department data scoping. Permission keys are
registered in `core/security/permissions.py`.

## Module boundaries

A module owns its own tables. Modules interact only through each other's
**service interfaces** or the **event bus** — never another module's repository
or tables.

## Adding a module

1. Copy the standard layout to `modules/<new>/`.
2. Implement models/schemas/repository/service/router.
3. Register the router in `api/v1/router.py`.
4. Register permission keys in `core/security/permissions.py`.
5. Generate an Alembic migration.

Existing modules are untouched.

## Open decisions (Foundation Phase)

- **Background-job library:** `jobs/` is queue-agnostic. Recommend **ARQ**
  (async-native, Redis) or **Celery** (mature ecosystem). To be confirmed.
- **Compliance & salary components** will live inside the `payroll` module as
  promoted sub-packages once their schema is finalized.
