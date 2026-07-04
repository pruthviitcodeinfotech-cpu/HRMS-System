# Modules

Each capability under `modules/` is a **self-contained vertical slice**. Every
module follows the **same internal structure** so any developer can work in any
module and new modules can be added mechanically.

## Standard module layout

```
modules/<name>/
├── __init__.py
├── router.py         # Thin controllers: HTTP mapping only, no business logic
├── schemas.py        # Pydantic DTOs (request/response) — the API contract
├── models.py         # SQLAlchemy ORM entities OWNED by this module
├── repository.py     # Data access: the only place queries live (org-scoped)
├── service.py        # Business rules, orchestration, transaction boundaries
├── dependencies.py   # Module-scoped FastAPI dependencies
├── exceptions.py     # Domain-specific exception types
├── constants.py      # Enums, statuses, and RBAC permission keys
├── events.py         # Domain events emitted/consumed by this module
└── tasks.py          # Background/async tasks owned by this module
```

## Rules

1. **Layering:** `router → service → repository → db`. Routers stay thin;
   business rules live only in services; queries live only in repositories.
2. **DTO ≠ ORM:** never return SQLAlchemy models from the API — map through `schemas`.
3. **Ownership:** a module owns its own tables. Do **not** query another module's
   tables or repositories directly — call its **service** or react to its **events**.
4. **Multi-tenancy:** every query is scoped by `org_id` (enforced via base
   repository + tenant middleware).
5. **Consistency over cleverness:** keep the standard layout even when a file is
   small. Empty/near-empty files are fine.

## Scaling a module

A complex module (e.g., `payroll`) may **promote any file to a package folder**
using `__init__.py` re-exports, so imports never change:

```
payroll/
├── models/          (was models.py)
├── services/        (was service.py)
├── repositories/    (was repository.py)
└── schemas/         (was schemas.py)
```

## Adding a new module

1. Copy the standard layout into `modules/<new>/`.
2. Implement `models`, `schemas`, `repository`, `service`, `router`.
3. Register the router in `app/api/v1/router.py`.
4. Register permission keys in `app/core/security/permissions.py`.
5. Generate an Alembic migration for the new tables.

Nothing in existing modules changes.

## Current modules

| Module | Responsibility |
|---|---|
| `auth` | Login, JWT issue/refresh, sessions |
| `rbac` | Rights templates, permissions, branch/department scoping |
| `organization` | Organizations, branches, departments, designations |
| `employee` | Employee master + sub-records (bank, docs, biometrics, etc.) |
| `shift` | Shifts, assignments, weekoffs, roster, working-hours config |
| `attendance` | Punches, attendance records, regularization, mobile logins |
| `leave` | Leave types, allocations, balances, holidays |
| `approvals` | Unified approval inbox (polymorphic hub) |
| `payroll` | Groups, process, adjustments, compliance, salary components, finalization |
| `settlements` | Loans/advances and arrears ledgers |
| `reports` | Static reports (read-only projections) |
| `dashboard` | KPI aggregation (read-only) |
| `notifications` | Notification domain (in-app bell, dispatch) |
| `audit` | Activity log (append-only) |
| `hardware` | Biometric devices, sync, face-app pairing |
| `settings` | Org settings, salary-slip settings, payroll settings |
