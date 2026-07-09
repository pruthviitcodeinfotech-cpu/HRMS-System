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

## Repository and service standards

Repositories are the only layer allowed to build SQLAlchemy queries. Each
repository method must receive the request-scoped database session and must
apply `org_id` scoping for tenant-owned data. Repositories return ORM models or
primitive query results to services only; they do not return API DTOs and do not
perform HTTP, permission, or request parsing work.

Services own use-case orchestration, transaction boundaries, domain validation,
and calls to other modules' services or the event bus. A service may call one or
more repositories inside one transaction. Services must not depend on FastAPI
request objects and must not directly query another module's tables.

Routers depend on schemas, dependencies, and services only. Routers translate
HTTP input into DTOs and query parameters, call a service, then return response
schemas wrapped in the standard response envelope.

## Dependency injection

Common request dependencies live in `core/dependencies/`. Module-specific
dependencies live in `modules/<name>/dependencies.py`.

Required dependency responsibilities:

- `get_db`: yields one async SQLAlchemy session per request.
- `current_user`: validates the access token and returns the authenticated user
  context.
- `current_org`: resolves the tenant/org context from the authenticated user or
  tenant middleware.
- `require_permission`: checks RBAC feature permission and branch/department
  data scope before the router calls the service.
- Pagination/filter dependencies: parse and validate common query parameters.

Dependencies may read request metadata, headers, tokens, and query parameters.
Business rules remain in services.

## Database session and transactions

The application uses SQLAlchemy async sessions backed by PostgreSQL. A request
gets exactly one request-scoped session from `core/dependencies/db.py`.

Session rules:

- Routers do not commit or rollback directly.
- Services define transaction boundaries for write operations.
- Read-only operations do not commit.
- Failed requests roll back through the database dependency or exception
  middleware.
- Repository methods do not create sessions.
- Background jobs create their own scoped session per job.
- WebSocket handlers create short-lived sessions per database operation, not one
  long-lived session for the socket lifetime.

Migrations are the only supported way to change database schema. All migrations
must use deterministic names for primary keys, foreign keys, unique constraints,
checks, and indexes, matching `core/database/base.py`.

## Authentication and RBAC flow

Authentication uses JWT access tokens and refresh tokens. Access tokens protect
API and WebSocket entry points. Refresh tokens are used only to issue new access
tokens and may be revoked through user session state.

Authorization has two layers:

- Feature permission: CRUD-style permission keys from
  `core/security/permissions.py`, rights templates, and user overrides.
- Data scope: branch and department access from the RBAC module.

Super admins may bypass feature checks, but tenant isolation still applies.
Inactive users, deleted users, revoked sessions, and invalid tokens must be
rejected before service logic runs.

## API standards

All public HTTP APIs are versioned under `/api/v1`. Routers are grouped by
module and expose resource-oriented endpoints.

Response rules:

- Responses use the shared success/error envelope from `shared/schemas`.
- ORM models are never returned directly.
- List endpoints return paginated response schemas.
- Timestamps are timezone-aware ISO-8601 values.
- IDs are represented as integers.
- Empty list responses return an empty `items` list, not `null`.

HTTP status rules:

- `200 OK`: successful read/update/action with response body.
- `201 Created`: successful creation.
- `204 No Content`: successful delete/archive operation when no body is needed.
- `400 Bad Request`: malformed request or invalid state transition.
- `401 Unauthorized`: missing or invalid authentication.
- `403 Forbidden`: authenticated but not permitted.
- `404 Not Found`: resource not found within the current tenant scope.
- `409 Conflict`: unique constraint or business conflict.
- `422 Unprocessable Entity`: Pydantic validation error.

## Error handling

Application exceptions live in `core/exceptions/`. Module-specific exceptions
live in `modules/<name>/exceptions.py` and should map to a stable application
error code.

Error responses must include:

- `success = false`
- machine-readable error code
- human-readable message
- optional field-level details
- request/correlation id when available

Unhandled exceptions are logged with stack traces and converted to a generic
internal-server-error response. Internal exception details, SQL, secrets, and
tokens must never be returned to clients.

## Validation

Validation is layered:

- Pydantic schemas validate API shape, required fields, types, and simple value
  constraints.
- Dependencies validate authentication, tenant context, permissions, pagination,
  filtering, and sorting parameters.
- Services validate domain rules, state transitions, ownership, and cross-entity
  invariants.
- Database constraints enforce referential integrity, uniqueness, and final data
  invariants.

Database validation must not replace service validation for user-facing business
errors. Services should raise clear module exceptions before database constraint
errors whenever the condition can be known in advance.

## Logging and observability

Application logging is structured through `core/logging/`. Every request should
carry a correlation id from middleware. Logs should include environment, module,
request id, user id when available, org id when available, route, method,
status, duration, and error code.

Sensitive values must be redacted, including passwords, JWTs, refresh tokens,
session tokens, OTPs, SMTP credentials, and uploaded file contents.

Audit/business mutation history belongs in the Activity Log module. Application
logs are operational telemetry; they are not the source of truth for HR audit
history.

## Configuration

Configuration is environment-driven through `core/config/settings.py` and
`.env.example`. The concrete settings object must validate required values at
startup and fail fast when required production settings are missing.

Configuration groups:

- app/environment/debug
- database URL and pool settings
- Redis URL and cache TTL
- JWT secrets and token TTLs
- CORS allowed origins
- email settings
- storage/upload settings
- worker/job settings
- logging format and level
- WebSocket path/settings

Production must not run with development secrets, `DEBUG=true`, or wildcard
CORS unless explicitly approved for an internal environment.

## Pagination, filtering, and sorting

List endpoints use consistent pagination parameters:

- `page`: 1-based page number.
- `page_size`: bounded page size with a module-safe default.

Filtering and sorting rules:

- Filters must be explicit allowlists per endpoint.
- Sorting fields must be explicit allowlists per endpoint.
- Sort direction is `asc` or `desc`.
- Free-text search, when supported, must be scoped by `org_id`.
- Repository methods must apply tenant filters before optional filters.
- Invalid filter or sort fields return `422`.

Large exports or reports should not bypass pagination in normal API responses;
they should use report/export flows when needed.

## File uploads

File upload handling lives behind `infrastructure/storage/`. Modules store file
metadata and file URLs/keys, not raw file bytes in relational tables.

Upload rules:

- Enforce maximum size from configuration.
- Allow only endpoint-specific content types/extensions.
- Generate server-side storage names; do not trust client filenames.
- Preserve original filename only as metadata when needed.
- Store files under tenant/module-aware paths or keys.
- Validate file presence, size, extension, and content type before storage.
- Do not expose local filesystem paths in API responses.

Future S3 or object-storage support must be implemented behind the same storage
client interface.

## Background jobs

Background and scheduled work lives in `jobs/`, with module job definitions in
`modules/<name>/tasks.py`. Job execution must not change the HTTP API contract.

Job rules:

- Jobs create their own database session and transaction scope.
- Jobs are idempotent where practical.
- Jobs log correlation/job ids and module context.
- Failed jobs are retried only when the operation is safe to retry.
- Long-running jobs should store progress/status in module-owned tables only
  when the module architecture requires it.
- Jobs communicate user-facing results through module services/events, not by
  directly calling routers.

The queue implementation remains behind `jobs/queue.py` so the project can use
the selected Redis-backed worker library without leaking it into modules.

## WebSockets

WebSockets live in `infrastructure/websockets/`. Socket connections authenticate
on connect using the same user/session rules as HTTP APIs.

WebSocket rules:

- Connections are grouped by org and user.
- A connection must not receive events from another org.
- Message payloads use documented schemas; ORM models are not sent directly.
- Database work inside WebSocket handlers uses short-lived sessions.
- Redis pub/sub should be used when multiple API/worker processes need to push
  events to connected clients.
- Disconnects, expired tokens, revoked sessions, and permission changes must be
  handled gracefully.

WebSockets are a delivery surface, not the source of truth. Durable notification
state belongs in the Notifications module tables.

## Redis and caching

Redis is used for cache, pub/sub, and queue-related infrastructure. Cache usage
must be explicit; repositories should not silently cache query results unless a
service-level use case defines the invalidation behavior.

Cache rules:

- Cache keys include environment, module, org id, and resource identity.
- TTLs come from configuration or module constants.
- Mutations invalidate or refresh affected cache keys.
- Permission-sensitive data must include user/scope information in the key.
- Redis outages should degrade gracefully for non-critical cache reads.
- Redis outages must fail fast for features that require Redis consistency
  such as queues or cross-process WebSocket fanout.

## Security baseline

Security controls required for production:

- Strong password hashing through `core/security/password.py`.
- JWT signing secret from environment, never committed.
- Short-lived access tokens and revocable refresh/session state.
- Strict CORS allowlist per environment.
- HTTPS termination in production.
- No secrets, tokens, passwords, or PII in logs.
- Tenant isolation enforced in dependencies and repositories.
- File upload type and size limits.
- Rate limiting for auth-sensitive endpoints.
- Consistent permission checks on every protected route.
- Database credentials and SMTP credentials supplied by secrets management or
  environment variables.

Security-sensitive changes require integration tests for unauthorized,
forbidden, cross-tenant, inactive-user, and revoked-session cases.

## Testing strategy

Tests are organized under `tests/unit`, `tests/integration`, and `tests/e2e`.

Expected coverage:

- Unit tests for services, validators, permission helpers, and pure utilities.
- Repository/integration tests for database queries, constraints, and tenant
  scoping.
- API tests for request/response contracts, auth, permissions, pagination,
  errors, and validation.
- Migration tests or CI migration checks that apply Alembic migrations from base
  to head.
- Background job tests for idempotency and retry-safe behavior.
- WebSocket tests for authentication, org isolation, and message shape.

Test fixtures must provide isolated database state, rollback/cleanup, seeded
org/user/RBAC data, and authenticated clients.

## Coding standards

Code style is enforced with Black, Ruff, and mypy as configured in
`pyproject.toml`.

Project standards:

- Use SQLAlchemy 2.x typed ORM style.
- Use `BIGINT` primary and foreign keys.
- Use deterministic constraint/index names.
- Use Pydantic schemas at API boundaries.
- Keep routers thin.
- Keep queries in repositories.
- Keep domain rules in services.
- Do not return ORM objects from APIs.
- Do not import another module's repository directly.
- Do not add native PostgreSQL enums unless the project convention changes.
- Add Alembic migrations for every schema change.

## Deployment and operations

The Dockerfile and docker-compose file support local development. Production
deployment must run the API, worker, PostgreSQL, Redis, and migration process as
separate operational concerns.

Production requirements:

- Apply Alembic migrations before starting a new application version.
- Run API and worker processes separately.
- Configure health checks for API, database, Redis, and worker readiness.
- Use environment-specific secrets and configuration.
- Disable debug mode.
- Serve behind HTTPS and a production ASGI server/process manager.
- Persist uploads in configured storage.
- Persist PostgreSQL and Redis data according to environment needs.
- Collect structured logs centrally.
- Monitor error rate, latency, worker failures, database pool usage, Redis
  health, and WebSocket connection counts.
- Define rollback procedure for application deploys and failed migrations.

## Adding a module

1. Copy the standard layout to `modules/<new>/`.
2. Implement models/schemas/repository/service/router.
3. Register the router in `api/v1/router.py`.
4. Register permission keys in `core/security/permissions.py`.
5. Generate an Alembic migration.

Existing modules are untouched.

## Open decisions (Foundation Phase)

- **Background-job library:** `jobs/` is queue-agnostic. The API contract must
  not depend on the concrete worker library. Select the Redis-backed worker
  implementation before coding production background jobs.
- **Compliance & salary components** will live inside the `payroll` module as
  promoted sub-packages once their schema is finalized.
