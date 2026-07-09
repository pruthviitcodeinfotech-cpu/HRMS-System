# PROJECT_CONTEXT.md

> Complete engineering handoff for the **HRMS / Payroll** backend. Written so another AI engineer can continue development with **zero prior conversation history**. Where something is uncertain or unverified, it is called out explicitly rather than guessed.

---

## 1. Project Overview

- **What it is:** An enterprise **HR & Payroll Management System (HRMS)** backend — a multi-tenant SaaS-style service covering the full employee lifecycle: organization structure, employee master records, attendance (incl. eSSL biometric devices), leave, shifts, payroll, settlements, reporting, notifications, and audit.
- **Why it exists:** To be the single source of truth for employee identity and employment state, and the central hub every downstream module (Attendance, Leave, Payroll, Shift, Device mapping, Reports) resolves back to. Built for a restaurant/retail-style workforce (Petpooja-style payroll domain).
- **Main goals:**
  - Modular monolith where each business capability is a self-contained vertical slice.
  - Strict layering: `router → service → repository → db`.
  - Multi-tenant isolation (`org_id` scoping on every query).
  - Two-layer authorization: RBAC feature-permissions × data-scope (branch/department).
  - Schema-first: DB migrations for **all** modules already exist; module code is being filled in module-by-module.
- **Current development stage:** **Foundation + first business modules complete.** Fully implemented modules: **`auth`, `rbac` (User Management), `employee` (Employee Management)**, plus a minimal shared **`audit`** service. All other modules have **DB models + migrations built** but **service/repository/router are still stubs**. The **Employee Management module was just fully built and hardened** in the most recent work; the next planned module is **Shift Management**.

> ⚠️ **Note on stored "memory":** An auto-memory note from early in the project describes this as an "analyst engagement, understand-only, module-by-module PDF review." That is **outdated** — the project has moved into full implementation. Treat the code as the source of truth.

---

## 2. Tech Stack

| Area | Choice |
|---|---|
| **Language** | Python **3.11+** |
| **Framework** | **FastAPI** (async) |
| **ORM** | **SQLAlchemy 2.x** (async, `Mapped[]` / `mapped_column`) |
| **Migrations** | **Alembic** |
| **DB driver** | `asyncpg` (async runtime), `psycopg2-binary` (sync, for Alembic tooling) |
| **Database** | **PostgreSQL** (Postgres-specific features used: partial unique indexes, `JSONB`, advisory locks) |
| **Validation / DTOs** | **Pydantic v2** + `pydantic-settings` |
| **Auth** | **JWT** (`python-jose[cryptography]`, HS256) + refresh tokens; passwords via `passlib[bcrypt]` |
| **Cache / broker / queue** | **Redis** (`redis` asyncio) |
| **Real-time** | WebSockets (`websockets`) — planned, `WS_PATH=/ws` |
| **Background jobs** | Redis-backed queue (library **intentionally undecided** — arq/celery TBD) |
| **Templating** | Jinja2 (email/pdf, future) |
| **HTTP client** | `httpx` (also used in tests) |
| **Logging** | `structlog` (JSON or console) |
| **File uploads** | Pre-signed object-storage pattern; `STORAGE_BACKEND=local|s3` |
| **Package manager** | **pip** + `pyproject.toml` (PEP 621). Optional `dev` extras group. |
| **Dev tools** | `pytest`, `pytest-asyncio` (asyncio_mode=auto), `pytest-cov`, `faker`, `ruff`, `black` (line-length 100), `mypy` (strict-ish, `disallow_untyped_defs`), `pre-commit` |
| **Task runner** | `Makefile` |

**Folder structure overview (top level):**
```
PAYROLL/
  backend/            <- the app (all work happens here)
    app/
      core/           framework foundation (config, db, security, middleware, logging, exceptions, dependencies, constants, cache)
      shared/         reusable domain building blocks (base classes, response envelope, pagination, utils)
      api/            HTTP surface + versioning (api/router.py, api/v1/router.py)
      modules/        business capabilities (one folder per module)
    alembic/          migrations (versions 0001..0016) + env.py
    tests/            unit/ and integration/
    pyproject.toml, Makefile, alembic.ini, .env.example, README.md
```
(There is no frontend in this repo. The architecture PDFs reference a React/Tailwind frontend, but it is **not present here**.)

---

## 3. Current Architecture

**Style:** Modular monolith, package-by-feature. Each module under `app/modules/<name>/` is a vertical slice with an identical internal layout.

### Backend request flow
```
HTTP request
  → FastAPI route (app/modules/<m>/router.py)          # thin controller
      → auth dependency (get_current_active_user)       # decode JWT → CurrentUser
      → permission guard (require_permission(feat, act)) # RBAC feature check
      → get_org_id dependency                            # tenant resolution
      → Service (app/modules/<m>/service.py)             # business rules + transaction boundary
          → Repository (app/modules/<m>/repository.py)   # the ONLY place SQL lives; org-scoped
              → AsyncSession (Postgres)
      ← Pydantic response schema (DTO)                   # never return ORM objects
  ← success_response() envelope { success, message, data, meta }
```

- **Routers** are thin: resolve dependencies, call the service, wrap the result in the standard envelope. **No business logic, no try/except** — typed exceptions bubble to global handlers.
- **Services** own business rules, cross-reference validation, and the **transaction boundary** (`async with self.transaction()`). They must **not** touch the DB directly — only via repositories.
- **Repositories** are the only place queries live; every query is `org_id`-scoped and soft-delete-aware.
- **Models** are SQLAlchemy ORM entities; a module owns its own tables.
- **DTOs (schemas)** map ORM ↔ wire; ORM objects are never returned from the API.

### Authentication flow
1. `POST /auth/login` (auth module) validates credentials (bcrypt), issues **access token** (15 min) + **refresh token** (14 days).
2. Access token carries claims: `sub` (user_id), `org_id`, `is_super_admin`, `is_active`, `sid` (session), `roles`, `permissions` (resolved feature rows), `branch_ids`, `department_ids`.
3. On each request `get_current_user` decodes the token into a `CurrentUser` principal **without a DB read** (permissions are baked into the token at login by the RBAC resolver).
4. `require_permission(feature_key, action)` checks the principal's `EffectivePermissions`; super-admins bypass.

### API flow / versioning
- `app/api/v1/router.py` aggregates module routers (`auth`, `rbac`, `employee`) into `api_router`.
- `app/main.py::create_app()` mounts `api_router` at `settings.api_v1_prefix` (`/api/v1`).
- Response envelope is standardized via `app/shared/schemas/response.py`.

### Middleware / cross-cutting (in `app/core/middleware/`)
- Request-context (request id, current user/org id via contextvars), logging, error handling, tenant middleware. Registered by `register_middleware(app)` and `register_exception_handlers(app)` in `create_app()`.

### How it all connects
`main.py` builds the app → registers middleware + exception handlers + `/health` + the v1 api_router. Each module router depends on `get_db` (request-scoped `AsyncSession`), auth dependencies, and constructs its Service with that session. The Service instantiates its Repositories (and cross-module collaborators like RBAC `UserRepository` and `AuditService`) on the **same session**, so all writes in one request share one transaction.

---

## 4. Folder Structure

```
backend/app/
  core/
    config/          settings.py (pydantic-settings, env-driven), Environment/LogFormat/StorageBackend enums
    constants/       enums.py (SortOrder, PermissionAction, page-size defaults, Environment, etc.)
    database/        base.py (declarative Base), session.py (async engine/session factory), mixins.py
    security/        jwt.py (create/verify tokens), password.py (bcrypt), permissions.py (EffectivePermissions model)
    dependencies/    auth.py (CurrentUser, get_current_user, require_permission, require_role),
                     db.py (get_db request session), pagination.py (PaginationParams)
    middleware/      request_context, logging, error_handler, tenant
    exceptions/      base.py (AppException hierarchy), handlers.py (render to envelope)
    logging/         structlog config
    cache/           redis.py (async redis client + close_redis)
  shared/
    base/            model.py (Base, TimestampMixin, SoftDeleteMixin, TenantMixin),
                     repository.py (BaseRepository[Model]), service.py (BaseService), schema.py (BaseSchema, TimestampSchema)
    schemas/         pagination.py (PaginationRequest/Meta, PaginatedResponse[T]), response.py (SuccessResponse/ErrorResponse + builders)
    utils/           validators.py, datetime.py (utcnow), ids.py, query.py (apply_filters/sorting/pagination), strings.py, files.py
  api/
    router.py        (top-level stub, currently unused)
    v1/router.py     api_router: includes auth + rbac + employee routers  ← REGISTER NEW MODULES HERE
  modules/<name>/    router.py, schemas.py, models(.py or /), repository.py, service.py,
                     dependencies.py, exceptions.py, constants.py, events.py, tasks.py
backend/alembic/versions/   0001..0016 migrations
backend/tests/
    conftest.py                 shared fixtures (app, client, tokens, mock services)
    unit/                       test_*_service.py, test_*_schemas.py, test_*_security.py, test_*_authorization.py
    integration/                test_*_router.py
```

Each module may **promote** `models.py`/`service.py`/`repository.py`/`schemas.py` to a **package folder** with `__init__.py` re-exports when it grows (employee already did this for `models/`). Imports never change.

---

## 5. Features Already Completed

### Foundation
- [x] **App factory & lifecycle** — `app/main.py::create_app()`; lifespan closes Redis + disposes DB engine. Mounts `/health` and the v1 api_router.
- [x] **Config (12-factor)** — `app/core/config/settings.py`, cached `settings` singleton; `.env.example` documents every var.
- [x] **Async DB layer** — `app/core/database/session.py` (engine + session factory), `get_db` request-scoped session dependency.
- [x] **Shared base classes** — `BaseSchema`, `BaseRepository[Model]`, `BaseService`, response envelope, pagination.
- [x] **Exception hierarchy + global handlers** — typed `AppException`s render to a uniform error envelope.
- [x] **Structured logging, middleware stack, Redis cache client.**

### Authentication (`app/modules/auth/`) — **complete**
- [x] Login, JWT access/refresh issue + verify, sessions. `AuthService` (336 lines), `AuthUserRepository[User]`, `UserSessionRepository[UserSession]`.
- [x] Token claims carry resolved permissions + data scope so guards need no per-request DB read.
- Implementation detail: password hashing via `app/core/security/password.py` (bcrypt); tokens via `app/core/security/jwt.py` (HS256, `ACCESS_TOKEN_TYPE`).

### User Management & RBAC (`app/modules/rbac/`) — **complete**
- [x] Users CRUD, rights templates ("roles"), template permissions, per-user custom permission overrides, user↔template assignment (one role per user), branch/department data-scope grants, effective-permission calculation.
- [x] `RBACService` (707 lines), 7 repositories, `PermissionResolver` (merges template ⊕ custom overrides), full router + tests.
- Tables: `users`, `rights_templates`, `rights_template_permissions`, `user_template_assignments`, `user_custom_permissions`, `user_branch_access`, `user_department_access`.

### Employee Management (`app/modules/employee/`) — **complete + hardened** (most recent work)
- [x] **Schemas** (`schemas.py`, 28 classes): all request/response DTOs for the API contract. Field names mirror the ORM columns (see §11). Reuses shared foundation + validators.
- [x] **Repository** (`repository.py`): `EmployeeRepository` (+ `Branch`/`Department`/`Designation` repos). CRUD, `search`/`search_count` (filter+search+pagination), lookups, exists-checks, `soft_delete`, and **`allocate_employee_code`** (concurrency-safe, advisory-lock).
- [x] **Service** (`service.py`, 816 lines): `EmployeeService` — create, update, get, list/search, activate/deactivate, change_status, exit, rehire, assign_branch/department/designation, assign_reporting_manager, add_document, set_photo. No direct DB access.
- [x] **Router** (`router.py`): 8 of 9 contract endpoints (device-mapping deferred by design). Auth + RBAC guards, salary-scope gating, branch data-scope, standardized envelope, OpenAPI docs.
- [x] **Audit integration** — every mutation writes an `activity_logs` row atomically.
- [x] **Registered** in `app/api/v1/router.py` and reachable at `/api/v1/employees...`.
- [x] **Tests** — 69 tests (unit service, unit schemas, integration router).

### Audit (`app/modules/audit/`) — **minimal service complete**
- [x] `ActivityLog` model + `ActionType`/`ActionFrom` constants (were pre-built).
- [x] **`AuditService.record()`** (just implemented) — append-only writer via shared `BaseRepository`, participates in the caller's transaction.

---

## 6. Features Partially Completed

### Employee Management — the 3 "known gaps" (all by-design, not defects)
- **Device-mapping endpoint** (`POST /employees/{id}/device-mapping`): **deferred**. Its `device_user_id` (device-local numeric id) has **no column in the employee schema** — it belongs to the **Hardware/Device module** (`employee_device_mapping` bridge + enrollment service, Module 04). Request/response schemas exist for the owning module to reuse. Do **not** implement it in the employee module (would duplicate ownership).
- **Reporting-manager assignment** (`assign_reporting_manager`): the `employees` table has **no `reporting_manager_id` column** and no self-referential FK. The method fully validates the manager reference (active, same-org, not self) then raises `422 REPORTING_MANAGER_NOT_SUPPORTED` rather than silently discarding it. Persisting it requires a schema change (out of scope).
- **Org-hierarchy consistency**: the contract wants `designation ⊂ department ⊂ branch` (422 `org_hierarchy_mismatch`). The models model branch/department/designation as **independent org children with no inter-FK links**, so the enforceable rule is **same-org active membership** of all three legs. Failure surfaces `org_hierarchy_mismatch`.

### Async device enrollment
- Create returns `device_enrollment: [{device_id, enrollment_status: "Pending"}]` **placeholders** only. Actual device I/O (eSSL K90 Pro / ADMS USERINFO command queueing) is owned by the Hardware module and is **not** performed by the employee service.

### All other business modules
- Models + migrations built (schema-first); **service/repository/router are stubs** (1-line docstrings). Modules in this state: `shift`, `attendance`, `leave`, `approvals`, `payroll`, `settlements`, `notifications`, `hardware`, `settings`. `reports`, `dashboard`, `organization` are placeholder dirs (organization tables actually live under the `employee` module).

---

## 7. Remaining Tasks (prioritized roadmap)

### Priority 1 — Shift Management module (next planned)
- **Description:** Implement Shift Management following the exact same layered pattern as Employee (schemas → repository → service → router → tests → register). Depends on the employee master + org assignment (both done).
- **Files involved:** `app/modules/shift/{schemas,repository,service,router}.py` (currently stubs); models already exist: `app/modules/shift/models/{shift,working_hours,assignment}.py`. Register in `app/api/v1/router.py`. Migration `0002_shift_management.py` already applied.
- **Complexity:** Medium–High. **Dependencies:** employee module (done), RBAC (done).

### Priority 2 — Hardware/Device module (unblocks two employee deferrals)
- **Description:** Implement device management + `employee_device_mapping` (device-mapping endpoint) + async enrollment/USERINFO queueing. This is what the employee device-mapping endpoint is deferred to.
- **Files:** `app/modules/hardware/*` (models exist; service/repo/router stubs). Migration `0012`/`0013` applied.
- **Complexity:** High (eSSL ADMS protocol specifics are **UNSPECIFIED** in the contract — raw byte format needs validation against a real K90 Pro unit). **Dependencies:** employee.

### Priority 3 — Attendance, Leave, Payroll, Settlements, Notifications, Settings
- **Description:** Fill in each stub module. Attendance resolves punches to `employee_id` via device mapping; Leave/Payroll are keyed on employee; exit drives payroll pro-rata/F&F.
- **Files:** respective `app/modules/<m>/*`; models + migrations exist.
- **Complexity:** High for Payroll/Attendance, Medium for others. **Dependencies:** employee, hardware, shift.

### Cross-cutting follow-ups (any time)
- Decide + wire the **background-job library** (arq vs celery) — intentionally left open (`pyproject.toml` note). Needed for async device enrollment, notifications dispatch, payroll runs.
- Consider a real **DB sequence** for employee codes when a migration window is available (currently advisory-lock; see §16).
- Implement a proper audit **read** API + AuditService retention (the audit module's router/schemas/repository are still stubs).

---

## 8. Important Files

| File | Purpose / responsibilities | Key classes/functions | Relationships |
|---|---|---|---|
| `app/main.py` | App factory + lifespan; mounts v1 api_router at `/api/v1`. | `create_app()`, `lifespan()`, `app` | imports `app/api/v1/router.py` |
| `app/api/v1/router.py` | Aggregates module routers. **Register new modules here.** | `api_router` | includes auth/rbac/employee routers |
| `app/core/config/settings.py` | All config, env-driven, cached singleton. | `Settings`, `get_settings()`, `settings` | used everywhere |
| `app/core/dependencies/auth.py` | Auth/authz FastAPI deps. | `CurrentUser`, `get_current_active_user`, `require_permission`, `require_role` | used by every protected router |
| `app/core/security/jwt.py` | Token issue/verify. | `create_access_token`, `verify_token`, `ACCESS_TOKEN_TYPE` | auth service, tests |
| `app/core/security/permissions.py` | Effective-permission mechanism. | `EffectivePermissions`, `FeaturePermission`, `build_effective_permissions` | auth deps, rbac resolver |
| `app/shared/base/repository.py` | Generic async CRUD/query base. | `BaseRepository[Model]` (get_by_id/list/count/exists/create/update/delete) | every module repo |
| `app/shared/base/service.py` | Transaction boundary + guards. | `BaseService` (transaction, ensure_found, ensure_unique, paginate) | every module service |
| `app/shared/base/schema.py` | DTO base config. | `BaseSchema` (from_attributes, extra=ignore), `TimestampSchema` | every DTO |
| `app/shared/schemas/response.py` | Standard envelope + builders. | `SuccessResponse`, `ErrorResponse`, `success_response()` | every router |
| `app/shared/schemas/pagination.py` | Paging DTOs. | `PaginationRequest`, `PaginationMeta`, `PaginatedResponse[T]` | list endpoints |
| `app/shared/utils/query.py` | Dynamic query helpers (allowlist-based). | `apply_filters`, `apply_sorting`, `apply_pagination` | repositories |
| `app/shared/utils/validators.py` | Pure validators. | `is_valid_email`, `is_valid_phone`, `normalize_phone`, `password_issues` | schemas |
| `app/modules/employee/models/{employee,organization,satellites}.py` | Employee + org + satellite tables. | `Employee`, `Branch`, `Department`, `Designation`, 11 satellites | source of truth for field names |
| `app/modules/employee/schemas.py` | Employee DTOs (28 classes). | `EmployeeCreateRequest/UpdateRequest/…`, `EmployeeDetailSchema`, `EmployeeListResponse` | service, router |
| `app/modules/employee/repository.py` | Employee data access. | `EmployeeRepository.allocate_employee_code` (advisory lock), `search`/`search_count`, 3 org repos | service |
| `app/modules/employee/service.py` | Employee business logic (816 lines). | `EmployeeService` (all lifecycle methods, `_validate_org_hierarchy`, `_audit`, `_next_employee_code`) | repos, RBAC UserRepository, AuditService |
| `app/modules/employee/router.py` | 8 employee endpoints. | route handlers + `_can_view_salary`, `_branch_scope` | service |
| `app/modules/audit/service.py` | Append-only audit writer. | `AuditService.record()` | uses `ActivityLog` model + `BaseRepository` |
| `app/modules/rbac/service.py` | User/RBAC business logic (707 lines). | `RBACService`, `PermissionResolver` | rbac repos |
| `tests/conftest.py` | Shared fixtures. | `app`, `client`, `make_access_token`, `super_admin_headers`, `rbac_service` | all tests |

---

## 9. Database Schema

**Conventions (project-wide, confirmed):**
- **All primary/foreign keys are `BIGINT`** (migration `0009_standardize_bigint_pks.py` standardized this; earlier PDFs said UUID — that is drift, ignore it).
- **Enumerated columns are `VARCHAR` + `CHECK` constraints**, NOT native Postgres `ENUM` types. The Python `Enum`s in each module's `constants.py` are the single source of truth for allowed values.
- **Soft delete:** employee-area tables use a boolean `is_deleted`; the RBAC `users`/roles area uses `deleted_at` timestamp. (Two different conventions — be careful.)
- **Multi-tenancy:** tables carry `org_id`; every query is org-scoped.
- **Timestamps:** `created_at` / `updated_at` `TIMESTAMPTZ` with `server_default now()`.
- **Migrations exist for ALL modules:** `alembic/versions/0001..0016` (schema-first). Deferred cross-module FKs are added in later "resolve_deferred_fks" migrations (`0008`, `0013`, `0016`).

### Employee module tables (owned by `app/modules/employee/models/`)

**`organizations`** (organization.py): `org_id` PK, `org_code` (unique), `org_name`, `contact_phone`, `contact_email`, `is_active`, `is_deleted`, timestamps.
**`branches`**: `branch_id` PK, `org_id` FK, `branch_name`, `logo_url`, `gstin`, `mobile_number`, address fields, `latitude`/`longitude` (Numeric 10,7), `allowed_radius_meters`, `is_active`, `is_deleted`.
**`departments`**: `dept_id` PK, `org_id` FK, `dept_name`, `is_active`, `is_deleted`, `created_by` (deferred→users). Partial unique index `(org_id, dept_name) WHERE is_deleted=false`.
**`designations`**: `designation_id` PK, `org_id` FK, `designation_name`, similar to departments.

**`employees`** (employee.py) — the master record:
- `employee_id` PK, `org_id` FK, `employee_code` (auto-gen, immutable), `employee_uid`, `employee_name`, `display_name`.
- Contact: `mobile_country_code` (default '+91'), `mobile_number`, `email`.
- `gender` (CHECK: Male/Female/Other), `master_branch_id` FK, `dept_id` FK, `designation_id` FK, `employee_type`.
- `door_lock_permission`, `pf_account_number`, `uan_number`, `esic_ip_number`, `address`.
- `date_of_joining`, `salary_type` (CHECK: Monthly/Hourly/Compliance), `monthly_salary` (Numeric 12,2), `payroll_group_id` (**deferred FK** → payroll_groups).
- `date_of_birth`, `date_of_leaving`, `employment_status` (CHECK: **active/inactive/terminated**, default 'active'), `profile_photo_url`.
- `is_deleted`, `created_by` (**deferred FK** → users), timestamps.
- Partial unique index `uq_employees_org_id_employee_code (org_id, employee_code) WHERE is_deleted=false`.
- Relationships: organization, master_branch, department, designation, and satellites (below).

**Satellite tables** (satellites.py, all FK → `employees.employee_id`):
`employee_bank_details`, `employee_documents` (document_type CHECK: aadhar_card/driving_licence/pan_card/passport_photo/other; `file_url`, `original_filename`, `file_size_bytes`, `uploaded_by`), `employee_emergency_contacts`, `employee_references`, `employee_biometrics` (device_id **deferred FK**, biometric_type, template), `employee_punch_branches`, `employee_attendance_permissions` (attendance_method CHECK: hardware_device/mobile_app/both), `org_attendance_settings`, `employee_import_logs` (JSONB error_details; status/import_type CHECKs), `employee_tags`, `employee_status_history` (previous/new_status, changed_by, reason, effective_date).

### Audit table (`app/modules/audit/models.py`)
**`activity_logs`** — append-only, immutable, one row per mutation across all modules: `id` PK, `org_id` FK (RESTRICT), `module`, `sub_module`, `employee_id` FK (SET NULL) + `employee_name` snapshot, `title`, `description`, `payroll_date`, `action_type` (CHECK: Insert/Update/Delete/Assign/Bulk Assign), `performed_by_user_id` FK (SET NULL, nullable) + `performed_by_name` snapshot (NOT NULL), `log_date`, `log_time`, `logged_at`, `action_from` (CHECK: Web App/Mobile App, default 'Web App'). Several indexes on `(org_id, …)`.

### RBAC / User tables (`app/modules/rbac/models.py`, owned with `auth`)
`users` (deleted_at soft-delete, `employee_id` link, `is_super_admin`), `rights_templates`, `rights_template_permissions`, `user_template_assignments`, `user_custom_permissions`, `user_branch_access`, `user_department_access`. Auth also owns `user_sessions`.

### Other modules
Models exist for `shift` (shifts, working_hours, assignments), `attendance`, `leave`, `approvals`, `payroll`, `settlements`, `notifications`, `hardware` (biometric_devices), `settings`. See each module's `models(.py|/)` and the corresponding migration.

---

## 10. API Documentation

**Prefix:** `/api/v1`. **Envelope:** every success returns `{ success, message, data, meta }`; errors `{ success:false, message, error:{ code, message, details }, meta }`.
**Currently mounted routers:** `auth`, `rbac`, `employee` (see `app/api/v1/router.py`).

### Employee Management endpoints (all under `app/modules/employee/router.py`)

| Method | Route | Auth? | Permission (feature:action) | Status | Request body | Response `data` | Service method |
|---|---|---|---|---|---|---|---|
| GET | `/employees` | Yes | `employee:read` | 200 | query: `branch_id`, `department_id`, `status`, `q`, `page`, `page_size` | `EmployeeListResponse` (paged `EmployeeSummarySchema`) | `list_employees` |
| POST | `/employees` | Yes | `employee:create` | **201** | `EmployeeCreateRequest` | `EmployeeCreateResponse` (+ `device_enrollment`) | `create_employee` |
| GET | `/employees/{id}` | Yes | `employee:read` (+ `employee_salary:read` for salary block) | 200 | — | `EmployeeDetailSchema` | `get_employee` |
| PUT | `/employees/{id}` | Yes | `employee:edit` | 200 | `EmployeeUpdateRequest` (partial) | `EmployeeDetailSchema` | `update_employee` |
| POST | `/employees/{id}/exit` | Yes | `employee:delete` | 200 | `EmployeeExitRequest` `{resignation_date, last_working_day, reason?}` | `EmployeeDetailSchema` | `exit_employee` |
| POST | `/employees/{id}/rehire` | Yes | `employee:create` | 200 | `EmployeeRehireRequest` `{date_of_joining}` | `EmployeeDetailSchema` | `rehire_employee` |
| POST | `/employees/{id}/documents` | Yes | `employee_document:edit` | **201** | `EmployeeDocumentCreateRequest` `{document_type, file_url, original_filename?, file_size_bytes?, mime?, expires_at?}` | `EmployeeDocumentSchema` | `add_document` |
| POST | `/employees/{id}/photo` | Yes | `employee:edit` | 200 | `EmployeePhotoUploadRequest` `{file_url, mime?}` | `EmployeeDetailSchema` | `set_photo` |
| ~~POST~~ | `/employees/{id}/device-mapping` | — | — | — | (deferred to Hardware module) | — | — |

**Business logic per endpoint** (see §11 for rules): create validates org FKs + allocates code + optional self-service user + audit; update partial + re-validates org triple on reassignment + audit; exit sets `terminated` + `date_of_leaving` + status history + audit; rehire reactivates + audit; documents/photo write + audit; list applies filters/search/pagination + branch data-scope.

**Auth & RBAC endpoints:** implemented under `app/modules/auth/router.py` and `app/modules/rbac/router.py` (users CRUD, roles/templates, permissions, branch/department access, effective-permissions). See those files for the full list.

**Feature-permission key mapping** (contract dotted codes → project `feature_key`×action):
- `employee.view` → `employee:read`; `employee.create` → `employee:create`; `employee.edit` → `employee:edit`; `employee.exit` → `employee:delete`; `employee.salary.view` → `employee_salary:read`; `employee.document.manage` → `employee_document:edit`.

---

## 11. Business Logic

### Employee field-name reconciliation (CRITICAL — models are source of truth)
The generic architecture PDFs use illustrative names; the **actual columns** are:
`full_name`→**`employee_name`**, `dob`→**`date_of_birth`**, `phone`→**`mobile_number`** + **`mobile_country_code`**, `branch_id`→**`master_branch_id`**, `department_id`→**`dept_id`**, `joining_date`→**`date_of_joining`**, `last_working_day`→**`date_of_leaving`**. `employment_status` values are **active/inactive/terminated** (NOT Probation/On Notice/Exited). Schemas mirror the real columns so `from_attributes` ORM binding works.

### Validation rules (employee)
- `employee_name`: required, 2–200 chars. `email`: normalized+validated (lowercased). `mobile_number`: normalized (`normalize_phone`) + validated (7–15 digits, optional `+`). `monthly_salary`: `ge=0`, `max_digits=12`, `decimal_places=2`.
- **Mass-assignment guard:** `employee_code`, `employment_status`, `is_deleted` are **not client-settable** (schema `extra="ignore"` drops them; lifecycle drives status; code is auto-generated).
- **Exit dates:** `last_working_day ≥ resignation_date`. Enforced **twice**: schema `model_validator` (fast, 422 `VALIDATION_ERROR` via HTTP) AND a service guard (`ValidationException code="invalid_exit_dates"` for non-HTTP callers). Both intentionally retained.

### Permissions / data-scope
- Two-layer: **feature permission** (`feature_key`×CRUD) × **data scope** (`branch_ids`/`department_ids`). Super-admin bypasses feature checks.
- **Salary segregation:** the nested `salary` block on `EmployeeDetailSchema` is only populated/settable when the caller holds `employee_salary:read` (router computes `_can_view_salary` → passes `include_salary`/`can_set_salary`).
- **Branch data-scope on list:** `_branch_scope(current_user)` → `None` for super-admin or unrestricted roles (org-wide), or the caller's `branch_ids` for a Branch Admin.

### Workflows
- **Create:** validate org hierarchy → allocate `employee_code` (advisory lock) → INSERT → optional self-service user (RBAC) → audit (Insert) → return detail + `device_enrollment` placeholders. All inside one transaction.
- **Employment-status lifecycle:** `active ↔ inactive` (activate/deactivate), `→ terminated` (exit; sets `date_of_leaving = last_working_day`, writes `employee_status_history`), `terminated → active` (rehire; new `date_of_joining`, clears `date_of_leaving`, preserves history). No-op transitions raise `409 EMPLOYEE_STATUS_UNCHANGED`.
- **Org assignment:** assign_branch/department/designation each re-validate the full active + same-org hierarchy first, then update, then audit (Assign).
- **Employee code generation:** `EMP` + zero-padded 5-digit running number, allocated **inside** the creating transaction via `pg_advisory_xact_lock(hashtext('employee_code:{org}:{prefix}'))`. Highest existing suffix (incl. soft-deleted, so codes are never reused) + 1. Race-free without a DB sequence.
- **Audit:** every mutation (create/update/status/exit/rehire/assign/document/photo) writes one `activity_logs` row in the **same transaction** (atomic; rolls back together). Actor display name resolved best-effort via RBAC `UserRepository`.

### Edge cases / error codes (contract-aligned)
`org_hierarchy_mismatch` (422, org FK missing/inactive), `invalid_exit_dates` (422), `not_found` (404), `EMPLOYEE_ALREADY_EXITED`/`EMPLOYEE_ALREADY_ACTIVE`/`EMPLOYEE_STATUS_UNCHANGED` (409), `REPORTING_MANAGER_SELF` (409), `REPORTING_MANAGER_NOT_SUPPORTED` (422), `SELF_SERVICE_EMAIL_REQUIRED` (422), `USER_EMAIL_EXISTS`/`USER_MOBILE_EXISTS` (409). Contract codes `duplicate_employee_code`/`device_user_id_taken`/`device_enrollment_deferred` are not emitted here (auto-gen is race-free; device mapping deferred).

---

## 12. Authentication & Authorization

- **Login flow:** `POST /auth/login` → `AuthService` validates bcrypt password → issues access + refresh tokens. Permissions/data-scope are resolved by the RBAC `PermissionResolver` and **baked into the access token** at login.
- **Token flow:** `create_access_token(user_id, extra_claims={...})` (HS256). Claims: `sub`, `type`, `jti`, `iat`, `exp`, `org_id`, `is_super_admin`, `is_active`, `sid`, `roles`, `permissions` (list of `{feature_key, can_create/read/edit/delete}`), `branch_ids`, `department_ids`. Access TTL 900 s (15 min); refresh TTL 1 209 600 s (14 days).
- **Middleware / deps:** `get_current_user` (decode Bearer token → `CurrentUser`, no DB read) → `get_current_active_user` (rejects inactive) → `require_permission(feature_key, action)` / `require_role(*roles)`.
- **`CurrentUser`** (`app/core/dependencies/auth.py`): `user_id`, `org_id`, `is_super_admin`, `is_active`, `session_id`, `roles`, `permissions: EffectivePermissions`. `.require(feature, action)` raises `AuthorizationException` (403) if not permitted.
- **Protected routes:** declare `dependencies=[Depends(require_permission(...))]`. Tenant resolved by module-local `get_org_id` (400 `TENANT_UNRESOLVED` if the token lacks `org_id`).
- **Refresh tokens / sessions:** `user_sessions` table + `UserSessionRepository`; refresh endpoint in the auth router. `sid` claim ties a token to a session.
- **Session admin & lock/unlock:** NOT implemented (RBAC contract open question — `users` has no lock column, only `is_active` + `deleted_at`).

---

## 13. Environment Variables

From `.env.example` (copy to `.env`; never commit secrets). Field names map case-insensitively (`DATABASE_URL` → `settings.database_url`).

| Variable | Purpose |
|---|---|
| `APP_NAME` | App display name. |
| `ENVIRONMENT` | `development` \| `staging` \| `production`. |
| `DEBUG` | Debug flag. |
| `API_V1_PREFIX` | API mount prefix (default `/api/v1`). |
| `SECRET_KEY` | App secret (generic). |
| `HOST`, `PORT` | Uvicorn bind. |
| `ALLOWED_ORIGINS` | CORS origins (comma-separated → `settings.cors_origins`). |
| `ALLOWED_HOSTS` | Trusted hosts (`*` = all). |
| `DATABASE_URL` | Async DSN `postgresql+asyncpg://…`. Alembic uses the sync rewrite (`+psycopg2`). |
| `DB_POOL_SIZE`, `DB_MAX_OVERFLOW`, `DB_ECHO`, `DB_POOL_PRE_PING` | SQLAlchemy pool tuning. |
| `REDIS_URL` | Cache/broker/queue. |
| `CACHE_TTL_SECONDS` | Default cache TTL. |
| `JWT_SECRET` | **Token signing secret** (do not expose). |
| `JWT_ALGORITHM` | Default `HS256`. |
| `ACCESS_TOKEN_TTL` | Access token seconds (900). |
| `REFRESH_TOKEN_TTL` | Refresh token seconds (1209600). |
| `SMTP_HOST/PORT/USER/PASSWORD`, `EMAIL_FROM` | Email (future). |
| `STORAGE_BACKEND` | `local` \| `s3` (pre-signed uploads). |
| `UPLOAD_DIR`, `MAX_UPLOAD_SIZE_MB` | Upload config. |
| `QUEUE_BACKEND`, `WORKER_CONCURRENCY` | Background jobs. |
| `LOG_LEVEL`, `LOG_FORMAT` | `INFO`… ; `json` \| `console`. |
| `WS_PATH` | WebSocket path (default `/ws`). |

---

## 14. External Services

| Service | How used | Status |
|---|---|---|
| **PostgreSQL** | Primary datastore (async via asyncpg; Alembic via psycopg2). | Active. |
| **Redis** | Cache, event broker, and job queue backend. | Client wired (`app/core/cache/redis.py`); queue lib undecided. |
| **eSSL K90 Pro biometric devices (ADMS `/iclock/*`)** | Attendance punches + user enrollment (USERINFO) over the ADMS protocol; SN-whitelist auth (no JWT). | **Not implemented** — Hardware module stub. Raw byte format is **UNSPECIFIED** and must be validated against a real device. |
| **Object storage (S3/GCS/MinIO)** | Pre-signed URL uploads for employee photos/documents (binary stays out of the DB; DB stores paths only). | Pattern assumed; signing endpoint (`/upload/presign`) **not yet enumerated**. |
| **SMTP** | Transactional email. | Config present; not wired. |
| **JWT (python-jose)** | Auth tokens. | Active. |

No third-party webhooks or SDKs beyond the above are integrated yet.

---

## 15. Current Bugs

- **No known functional bugs** in the implemented modules (auth, rbac, employee, audit). All changed files byte-compile; AST cross-checks (service methods, exception codes, imports, routes) are clean.
- ⚠️ **Unverified at runtime:** the test suite could **not be executed** in the working sandbox (`pytest` and `redis` are not installed there, and cold-importing the app hits a **pre-existing package-init import-order sensitivity** — the same one the rbac module exhibits — plus a missing `redis` module). Tests were verified structurally only. **Before trusting green, run `pytest` in a real environment with deps installed.**
- **Import-order caveat:** importing certain modules "cold" (e.g. `python -c "import app.modules.rbac.schemas"`) can raise a circular-import error from `app.core.logging`/`middleware`/`exceptions`. Importing through the app factory (`app.main`) resolves it. Not a runtime bug in the served app, but be aware when writing isolated scripts.

---

## 16. Technical Debt

- **Employee code via advisory lock, not a DB sequence.** `pg_advisory_xact_lock` is race-free and schema-free, but a dedicated Postgres `SEQUENCE` (via migration) is the ideal long-term solution (contract §18). It is also **PostgreSQL-specific** (as are partial unique indexes, `JSONB` — the whole project is Postgres-only).
- **Two soft-delete conventions** coexist: `is_deleted` (employee area) vs `deleted_at` (users/roles). Easy to trip over.
- **Audit read-side is unimplemented** — only `AuditService.record()` exists; the audit module's router/schemas/repository are stubs. No retention/pruning policy yet.
- **`ensure_found` vs explicit `NotFoundException`:** the employee service now raises `NotFoundException(code="not_found")` directly (to match the contract code) instead of `BaseService.ensure_found`, which defaults to code `NOT_FOUND`. Minor inconsistency across modules.
- **Exit-date validation duplicated** (schema + service) by design — acceptable but worth knowing.
- **Background-job library undecided** — blocks truly async work (device enrollment, notifications, payroll runs) which are currently synchronous placeholders.
- **Security:** self-service users are created with `password_hash=None` (invite flow) — the invite/set-password flow itself is not yet built. Object-storage pre-sign endpoint not defined.
- **`app/api/router.py`** (top-level) is an unused stub; only `app/api/v1/router.py` is wired.

---

## 17. Decisions Made During Development

1. **Models are the source of truth over the API-contract PDFs.** The generic PDFs use UUID PKs and names like `full_name`/`phone`; the built schema uses BIGINT PKs and `employee_name`/`mobile_number`. Schemas mirror the **real columns** so `from_attributes` ORM binding works. *Rejected:* following the PDF names (would break ORM mapping and misrepresent the DB).
2. **VARCHAR + CHECK instead of native Postgres ENUM.** Keeps the whole schema consistent and migration-friendly; Python `Enum`s in `constants.py` are the single source of allowed values. *Rejected:* native `ENUM` types (harder to alter).
3. **Advisory lock for employee-code generation.** A DB sequence would require a migration (forbidden during hardening); count-then-check had a TOCTOU race. Transaction-scoped advisory lock is race-free and schema-free. *Rejected:* DB sequence (migration), insert-retry-on-IntegrityError (needs savepoints, aborts the txn).
4. **Device-mapping endpoint deferred to the Hardware module.** `device_user_id` has no column in the employee schema; it belongs to `employee_device_mapping` (Module 04). Implementing it in employee would duplicate ownership. *Rejected:* faking it against `employee_biometrics`.
5. **Reporting-manager: validate-then-refuse.** No `reporting_manager_id` column exists; rather than silently discard the input, the service validates the reference and raises `REPORTING_MANAGER_NOT_SUPPORTED`. *Rejected:* adding a column (schema change out of scope); silently no-op'ing (misleads the caller).
6. **Salary segregation via a nested optional block**, populated only with `employee_salary:read`. Keeps pay data off the base projection.
7. **Minimal `AuditService` reusing the existing `ActivityLog` model**, participating in the caller's transaction (flush-only). *Rejected:* a full audit module rewrite (out of scope); a separate audit transaction (would not be atomic with the mutation).
8. **Router registration via the intended `app/api/v1/router.py` aggregator** (auth+rbac+employee) rather than mounting only employee — makes the app runnable end-to-end (you need auth to get a token to call employee).
9. **RBAC precedent for documented omissions:** the rbac router documents endpoints it doesn't serve; the employee router followed the same pattern for the (now resolved) deferrals.

---

## 18. Conversation Context (most important section)

The Employee Management module was built **layer-by-layer across several focused steps**, each treating the prior layers as source of truth: **Schemas → Repository → Service → Router → Tests → Verification → Hardening.** Key discussions, discoveries, and constraints:

- **Field-name mismatch discovery:** early on, the API-contract PDF (`HRMS_Complete_API_Contract.pdf` §7) and a higher-level architecture PDF (`Module03_Employee_Management_Architecture.pdf`) used generic names and even UUID PKs that **did not match** the implemented models. Decision: the **models win**; schemas mirror real columns. This recurs everywhere — do not "fix" schema names to match the PDFs.
- **Source documents:** approved DB-architecture PDFs live in `~/Downloads` (e.g. `Employee_Management_Module_Database_Schema.pdf`, `HRMS_Complete_API_Contract.pdf`, `Module03_Employee_Management_Architecture.pdf`). Read them for verbatim specs, but reconcile against the actual models/migrations.
- **Reporting manager reality check:** grepped the entire codebase — there is **no** manager/reporting/supervisor column or table anywhere. Confirmed the validate-then-refuse approach is the only honest option without a schema change.
- **Org-hierarchy consistency limitation:** the models have **no FK links** between designation→department→branch (all are independent children of `org`). So the contract's strict subset consistency (422 `org_hierarchy_mismatch`) is enforced as "all three exist, are active, and belong to the same org."
- **Audit "service" was a stub:** the task said "integrate AuditService" but `audit/service.py` was a 1-line stub while the `ActivityLog` model + constants were fully built. Decision: implement a minimal `AuditService.record()` reusing the model (not a full module rewrite).
- **Concurrency-safe code — sequence forbidden:** hardening explicitly forbade schema/migration changes, so a DB sequence was off the table → advisory lock chosen.
- **Router wasn't mounted anywhere** (nor were auth/rbac in production `main.py`) — the `app/api/v1/router.py` aggregator existed but was empty; `main.py` had a commented placeholder. Hardening wired both.
- **Test execution constraint (recurring):** the working sandbox has **no `pytest`, no `redis`, no virtualenv**. Cold imports also hit a **pre-existing circular-import** in `app.core.logging`/`middleware`/`exceptions` (the completed rbac module fails identically). So all verification was done via **`py_compile` + AST cross-checks** (asserting service methods exist, exception codes match test assertions, imports resolve, model attributes exist, route inventory). **Assume tests are unrun until executed in CI.**
- **Assumptions made:** PostgreSQL is the only target DB (advisory locks, `JSONB`, partial indexes used freely). Self-service user creation reuses the RBAC `UserRepository` with `password_hash=None` (invite flow). Device enrollment is async and owned elsewhere.
- **Lessons learned:** keep DTO field names identical to ORM columns; put concurrency/DB primitives in the **repository** (not the service) to preserve "no direct DB access in services"; audit writes must share the caller's transaction; follow the rbac module as the canonical style reference.

---

## 19. Current Working State

**If someone runs the project today (with deps + Postgres + Redis available):**
- `create_app()` builds the FastAPI app, registers middleware + exception handlers, exposes `GET /health`, and mounts `/api/v1` with the **auth, rbac, and employee** routers. OpenAPI docs at `/docs`, `/redoc`, `/api/v1/openapi.json`.
- **Works:** health check; full auth (login, JWT issue/verify/refresh); full RBAC (users, roles, permissions, scopes, effective permissions); full Employee Management (list/search/paginate, create with auto code + audit, get with salary gating, update, exit, rehire, documents, photo); every employee mutation writes an `activity_logs` row; employee codes are allocated race-free.
- **Doesn't work / not present:** all other business modules (shift, attendance, leave, payroll, settlements, notifications, hardware, settings, reports, dashboard) are **stubs** — no endpoints; device-mapping endpoint (deferred); reporting-manager persistence (returns 422 by design); background jobs (no queue lib); email; object-storage pre-sign endpoint; audit read API; frontend (none in repo).
- **Limitations:** requires Postgres + Redis running; migrations must be applied first; the app must be imported via the factory (not cold sub-module imports).

---

## 20. Immediate Next Steps (exact order)

1. **Set up a runnable environment & confirm green tests.** Create a venv, `pip install -e ".[dev]"`, `cp .env.example .env`, start Postgres + Redis, `make migrate`, then `make test`. **This is step zero** — resolve any runtime issues the sandbox couldn't surface (esp. confirm the employee module's advisory-lock code + audit writes work against a real Postgres).
2. **Verify the Employee module end-to-end** against a live DB: create → get (with/without salary permission) → update → exit → rehire → document → photo; confirm `activity_logs` rows appear and `employee_code` increments per org.
3. **Build Shift Management** (Priority 1) following the employee pattern: implement `shift/schemas.py` → `shift/repository.py` → `shift/service.py` → `shift/router.py` → tests, then **register in `app/api/v1/router.py`**. Models already exist (`shift/models/`). Read the shift DB-architecture PDF + `HRMS_Complete_API_Contract.pdf` for the contract; reconcile names against the models (as with employee).
4. **Then Hardware/Device module** to unblock the employee device-mapping endpoint and real biometric enrollment.
5. **Decide the background-job library** (arq recommended for async/FastAPI) and wire it for enrollment/notifications/payroll.

**Where to begin:** open `app/modules/employee/` as the reference implementation and `app/modules/rbac/` as the style template. Mirror their layering exactly for shift.

---

## 21. Commands

All via `Makefile` (targets: `install`, `run`, `worker`, `migrate`, `revision`, `test`, `lint`, `format`). From `backend/`:

```bash
# Install (dev deps)
make install                      # or: pip install -e ".[dev]"
cp .env.example .env              # then edit secrets

# Run
make run                          # uvicorn app.main:app --reload
make worker                       # background worker (once a queue lib is chosen)

# Database / migrations (Alembic)
make migrate                      # apply migrations (alembic upgrade head)
make revision m="add shift x"     # autogenerate a new migration
# (Alembic uses settings.sync_database_url — the +psycopg2 rewrite)

# Test
make test                         # pytest
pytest tests/unit/test_employee_service.py -v
pytest tests/ --cov=app.modules.employee --cov-report=term-missing

# Quality
make lint                         # ruff + mypy
make format                       # black + ruff --fix
```
No Docker/deployment config is present in the repo yet.

---

## 22. Dependencies (why each exists)

**Runtime:** `fastapi` (web framework), `uvicorn[standard]` (ASGI server), `sqlalchemy[asyncio]` (async ORM), `alembic` (migrations), `asyncpg` (async PG driver), `psycopg2-binary` (sync PG for Alembic), `pydantic` + `pydantic-settings` (validation + config), `python-jose[cryptography]` (JWT), `passlib[bcrypt]` (password hashing), `redis` (cache/broker/queue), `python-multipart` (form/file uploads), `jinja2` (templating), `httpx` (HTTP client + test transport), `structlog` (structured logging), `websockets` (real-time, future).
**Dev:** `pytest`, `pytest-asyncio` (asyncio_mode=auto), `pytest-cov`, `faker` (test data), `ruff` (lint), `black` (format, line-length 100), `mypy` (type check), `pre-commit`.
**Intentionally absent:** a background-job library (arq/celery) — an explicit open decision noted in `pyproject.toml`.

---

## 23. Testing Status

- **Config:** `pyproject.toml` → `[tool.pytest.ini_options]` `testpaths=["tests"]`, `asyncio_mode="auto"` (async tests need no decorator).
- **Shared fixtures** (`tests/conftest.py`): `app` (factory + mounts auth/rbac routers), `client` (httpx ASGITransport with mocked services), `make_access_token` / `auth_headers` / `super_admin_headers`, `expired_token`, `fake_user` / `make_user` / `make_role`, real `service`/`rbac_service` with mocked repos.
- **Existing tests:** auth (service, security, schemas), rbac (service, authorization), and their integration routers; **employee: 69 tests** — `tests/unit/test_employee_service.py` (~41), `tests/unit/test_employee_schemas.py` (11), `tests/integration/test_employee_router.py` (17). Cover CRUD, search, pagination, validation, authorization (401/403 + permission-allowed + salary gating), branch/department/designation assignment, reporting-manager (self/not-found/unsupported), exit/rehire, documents, photo, audit-on-mutation, and error cases.
- **Employee integration tests** use a module-local `employee_app`/`employee_client`/`mock_employee_service` fixture that mounts the employee router and overrides `get_employee_service` (the router isn't in conftest's `app` fixture).
- **Missing tests:** repository-layer tests against a real async DB (advisory-lock behavior, org-scoping SQL); end-to-end tests with a live DB; tests for all stub modules.
- **Manual testing:** none possible in the sandbox (no deps). **All employee verification was static** (compile + AST). Run the suite in CI to confirm.

---

## 24. Future Improvements

- Replace advisory-lock code allocation with a Settings-driven **DB sequence** per org/branch (configurable prefix + width) once a migration window exists.
- Full **audit read API** + retention/pruning; possibly move audit writes to an async job for hot paths.
- **Object-storage pre-sign endpoint** (`POST /upload/presign`) + concrete S3/GCS/MinIO adapter.
- **Idempotency-Key** header for mutating endpoints (payroll run, leave request) with short-lived Redis dedup.
- **WebSocket** live-attendance channel (envelope currently undefined).
- Distinguish `employee.view_self` from `employee.view` for self-service profile access.
- Unify soft-delete convention across modules.
- CI pipeline (lint + type-check + tests + coverage gate), Dockerfile + compose (Postgres + Redis), and deployment config.
- Invite/set-password flow for self-service users created with `password_hash=None`.

---

## 25. AI Handoff Notes (read before writing code)

**Coding style & conventions**
- Python 3.11+, **full type hints** (`disallow_untyped_defs`), `from __future__ import annotations` at the top of every module.
- `black` line-length **100**; `ruff` (E,F,I,N,UP,B,C4). Match the **existing file's** comment density and idiom.
- Docstrings on modules, classes, and non-trivial methods (see employee/rbac for the house style).
- Use **markdown code-reference style** in prose (`[file.py:42](path#L42)`), but in code just write normal imports.

**Architecture conventions (do not violate)**
- **Layering:** `router → service → repository → db`. Routers are thin (no logic, no try/except). **Services never touch the DB directly** — all SQL lives in repositories (put DB primitives like advisory locks in the repository, as employee does).
- **DTO ≠ ORM:** never return SQLAlchemy models from the API; map through `schemas`. Response schemas use `BaseSchema` (`from_attributes=True`, `extra="ignore"`).
- **Ownership:** a module owns its tables. Do **not** query another module's tables/repos directly — call its **service** (as employee calls RBAC's `UserRepository` for the self-service user and `AuditService` for audit) or react to events.
- **Multi-tenancy:** every query is `org_id`-scoped and soft-delete-aware.
- **Transactions:** the service owns the boundary via `async with self.transaction()`; collaborators (audit, satellites) must share the **same session** so writes are atomic.
- **New module checklist:** implement models→schemas→repository→service→router→tests; **register the router in `app/api/v1/router.py`**; add feature-permission keys; ensure a migration exists.

**Important assumptions**
- **PostgreSQL only** (advisory locks, `JSONB`, partial unique indexes). BIGINT PKs everywhere. VARCHAR+CHECK enums (values live in each module's `constants.py`).
- **Models are the source of truth** over the contract PDFs — reconcile names, don't "fix" schemas to match PDFs.
- Field names to remember for employee: `employee_name`, `mobile_number`/`mobile_country_code`, `master_branch_id`, `dept_id`, `date_of_joining`, `date_of_leaving`, `employment_status ∈ {active,inactive,terminated}`.

**Files to modify only with caution**
- `app/core/**` and `app/shared/**` (shared foundation) — changing these ripples across all modules. The hardening task treated these as off-limits unless critical.
- `app/modules/employee/models/**` and `alembic/versions/**` — schema is frozen; do not alter models/migrations without an explicit, migration-backed decision.
- `app/api/v1/router.py` and `app/main.py` — small but load-bearing (registration + factory).

**Common pitfalls**
- **Don't cold-import sub-modules** in scripts (circular import); import via `app.main`. When writing isolated verification, stub the package `__init__` chain or run through the app.
- **No `pytest`/`redis` in the default sandbox** — set up a real env before claiming tests pass. Verify statically (compile + AST) if you can't run them, and **say so**.
- Two soft-delete conventions (`is_deleted` vs `deleted_at`) — check which the table uses.
- Salary is permission-gated — thread `include_salary`/`can_set_salary` from the router, never expose it unconditionally.
- Exit-date rule is enforced in both schema and service — keep both.
- The auth token already carries permissions; guards do **not** hit the DB — keep it that way (re-resolve at login, not per request).

**Recommended order for future work**
1. Stand up the environment and get the existing suite green (esp. employee against real Postgres).
2. Shift Management (Priority 1) — mirror the employee module exactly.
3. Hardware/Device module (unblocks employee device-mapping + real enrollment).
4. Attendance → Leave → Payroll → Settlements → Notifications → Settings.
5. Decide the job queue; wire async work. Add CI + Docker.

**Reference implementations to copy from:** `app/modules/employee/` (most complete, hardened) and `app/modules/rbac/` (canonical style). When in doubt, do what they do.
