# Activity Log / Audit Management API Contract

> Module: `app/modules/audit`
> API Version: `v1` — all routes under `API_V1_PREFIX` (`/api/v1`).
> Status: **Contract only** (no FastAPI/SQLAlchemy/Pydantic/service/repository code).
> Sources of truth: `docs/architecture.md` (Backend Architecture), migration `0010_activity_log`
> (+ `0016`), the audit model (`audit/models.py`), `audit/constants.py`, and the approved prior contracts.

Covers the single append-only audit table (`activity_logs`) — one immutable row per **data-mutation** event
across all HRMS modules. **Read-only**: rows are written internally by other modules' services (the audit
module exposes no create/update/delete API). **Excludes** Authentication, RBAC, Employee, Shift, Attendance,
Leave, Approval, Payroll, Settlements, Hardware, Notifications, Settings, Dashboard, Reports.

> **Scope note (per approved decisions):** `activity_logs.action_type` is CHECK-constrained to
> **`Insert | Update | Delete | Assign | Bulk Assign`** — it logs **data mutations only**, not authentication
> or security events. Therefore **Login/Logout/Failed-Login History and Active Sessions are NOT supported**
> here (no auth-event logging; sessions belong to Auth/RBAC session admin) — §9 Q1. **Security Events** are an
> **approximate filtered view** of `activity_logs` (by module + action_type); **Password Change History** has
> no events — §9 Q2. There is **no generic entity reference** (no `entity_type`/`entity_id`), so change
> history is **employee/module-centric + actor-filtered** — §9 Q3. **Export is excluded** (report/export
> infrastructure) — §9 Q4.

---

## 1. Module Overview

### Purpose
Expose a read-only, tenant-scoped audit trail of data-mutation events (who did what, to whom, when, from which
platform) across all modules.

### Responsibilities
- Read/search/filter `activity_logs`; per-employee and per-user views; module-wise history; a security-event
  filtered view.

### Dependencies
| Dependency | Location / Module | Used for |
|---|---|---|
| Auth/permission deps | `core/dependencies/auth.py` | `current_user`, `current_org`, `require_permission` |
| Tenant middleware | `core/middleware/tenant.py` | `org_id` scoping |
| RBAC | `rbac` | `audit` read permission; branch/department scope (via `employee_id`) |
| Employee / Users (read) | `employee`, `rbac` | `employee_id`/`performed_by_user_id` references (names are snapshots) |
| Response/pagination schemas | `shared/schemas/` | envelope + paginated lists |
| **All modules (writers)** | every module's service | INSERT `activity_logs` rows on mutation (not this contract's API) |

**Table owned:** `activity_logs` (only). Append-only (INSERT + SELECT; no UPDATE/DELETE — a DB-privilege
concern, not exposed via API).

### Module boundaries
- **Read-only surface.** Log rows are produced by the writing modules' services; there is no public write API.
- Names (`employee_name`, `performed_by_name`) are **denormalised snapshots** preserved even if the referenced
  employee/user is renamed or deleted (FKs are `SET NULL`).
- FKs: `org_id`→organizations (RESTRICT), `employee_id`→employees (SET NULL), `performed_by_user_id`→users
  (SET NULL).

---

## 2. Authorization Model

Feature permission × tenant scope. Super admins bypass; tenant isolation (`org_id`) always applies. All
endpoints require `Authorization: Bearer <access_token>`.

**Proposed feature key** (register in `core/security/permissions.py` — §9 Q5): `audit` (**read-only**). Audit
access is sensitive and typically restricted to admins/compliance roles. Employee-centric views are
additionally branch/department data-scoped via `employee_id` (super admin exempt).

---

## 3. Request & Response Standards

Reuses the shared envelope + pagination (`data`/`error`/`meta.request_id`; `data.items`+`page`+`page_size`+
`total`). BIGINT integer IDs; timezone-aware `logged_at`; `log_date`/`log_time` separate; empty lists →
`items: []`.

**Enumerations (DB CHECK):** `action_type` ∈ `Insert, Update, Delete, Assign, Bulk Assign`;
`action_from` ∈ `Web App, Mobile App`.

### Pagination / Filtering / Sorting / Date Range
`page` (≥1, default 1), `page_size` (bounded). **Filterable:** `module`, `sub_module`, `action_type`,
`action_from`, `employee_id`, `performed_by_user_id`, `date_from`/`date_to` (on `log_date` / `logged_at`),
`search` (title/description). **Sortable:** `logged_at` (default `desc`), `log_date`. Invalid filter/sort
field → `422`. Repository applies `org_id` (+ data scope) before optional filters.

Common omitted errors (all protected endpoints): `401 AUTH_NOT_AUTHENTICATED`, `403 AUTH_FORBIDDEN`,
`422 VALIDATION_ERROR`.

---

## 4. Activity / Audit Logs (`/api/v1/activity-logs`) — feature key `audit`

`activity_logs` fields: `module` (≤100), `sub_module` (≤150), `employee_id` + `employee_name` (snapshot),
`title` (≤200), `description` (text), `payroll_date` (nullable), `action_type` (CHECK),
`performed_by_user_id` + `performed_by_name` (snapshot), `log_date`, `log_time`, `logged_at`, `action_from`
(CHECK). *(Activity Logs and Audit Logs are the same table.)*

| # | Endpoint | Method | URL | Permission |
|---|---|---|---|---|
| 1 | List / Search / Filter Logs | GET | `/activity-logs` | `audit:read` |
| 2 | Get Log Details | GET | `/activity-logs/{log_id}` | `audit:read` |
| 3 | Module-wise Audit History | GET | `/activity-logs?module={module}` | `audit:read` |

- **1. List / Search / Filter** — full filter/sort set (§3), incl. **Date Range**, **Module**, **User**
  (`performed_by_user_id`), **Action** (`action_type`) filtering. `200` paginated (id, module, sub_module,
  title, action_type, employee_id/name, performed_by_user_id/name, log_date/time, logged_at, action_from).
- **2. Get Details** — `200` → full row incl. `description`, `payroll_date`. `404 ACTIVITY_LOG_NOT_FOUND`.
- **3. Module-wise** — a documented filter variant of #1 (`?module=`, optional `sub_module`).

---

## 5. Change History Views (`/api/v1`) — feature key `audit`

| # | Endpoint | Method | URL | Permission |
|---|---|---|---|---|
| 4 | Employee Activity / Entity Change History | GET | `/employees/{employee_id}/activity-logs` | `audit:read` |
| 5 | User Activity / User Change History (User Actions) | GET | `/users/{user_id}/activity-logs` | `audit:read` |

- **4. Employee Activity (Entity Change History)** — logs where `employee_id = {employee_id}` (the audited
  subject), optional `module`/`sub_module`/`action_type`/date filters. This is the schema's closest
  "entity change history" — **employee/module-centric**, since there is no generic `entity_id` column
  (§9 Q3). Branch/department data-scoped. `200` paginated. `404 EMPLOYEE_NOT_FOUND`.
- **5. User Activity (User Change History / User Actions)** — logs where
  `performed_by_user_id = {user_id}` (the actor) — i.e., the mutation **actions performed by** that user,
  with optional filters. `200` paginated. `404 USER_NOT_FOUND`.

> **Note:** "User Change History" here means actions **performed by** a user (`performed_by_user_id`). There
> is no target-user column, so changes **to** a user account appear only if that mutation was logged with the
> relevant `module`/`description` (§9 Q3).

---

## 6. Security Events (`/api/v1/activity-logs/security-events`) — feature key `audit`

An **approximate** filtered view of `activity_logs` (no dedicated security-event schema): rows whose `module`
is in a security-related set (e.g. `rbac`, `user`) and/or `action_type ∈ {Assign, Update}`.

| # | Endpoint | Method | URL | Permission |
|---|---|---|---|---|
| 6 | Security Event Timeline | GET | `/activity-logs/security-events` | `audit:read` |

- **Query:** `event` filter (`permission_change` | `role_assignment` | `account_status_change`), plus
  `date_from`/`date_to`, `performed_by_user_id`, `employee_id`. Maps to `activity_logs` filters:
  - **Role Assignment History** → `action_type='Assign'`, `module='rbac'`.
  - **Permission Changes** → `module='rbac'`, `action_type='Update'`.
  - **Account Status Changes** → `module='user'` (activate/deactivate), by `description`/`sub_module`.
- `200` paginated, chronological (`logged_at desc`).
- **Password Change History** is **not supported** — password changes are not recorded as `activity_logs`
  events (§9 Q2). This filtering is best-effort over free-text `module`/`sub_module`/`description`; a precise
  security-event taxonomy would need dedicated schema.

---

## 7. Business Rules

- **Read-only & immutable:** the audit trail is append-only; no create/update/delete via API. Writes are
  performed by each module's service on mutation.
- **Tenant isolation:** all queries scoped to `org_id`; employee-centric views branch/department data-scoped.
- **Snapshots:** `employee_name`/`performed_by_name` are historical snapshots; FK references may be `NULL`
  after the employee/user is deleted, but the names persist.
- **No auth/security event schema:** login/logout/failed-login/session and password-change events are not in
  this table (§9).

---

## 8. Permission Matrix

| Feature key | read | create/edit/delete |
|---|---|---|
| `audit` | List/Search/Filter, Get details, Module-wise, Employee activity, User activity, Security events | — (append-only; no write API) |

Super admins bypass feature checks; tenant isolation always applies; employee-centric views are
branch/department data-scoped.

---

## 9. Error Handling, Retention, Security & Open Questions

**Error envelope** via `core/exceptions/handlers.py`. Module error codes (proposed, `audit/exceptions.py`):
`ACTIVITY_LOG_NOT_FOUND`(404), `EMPLOYEE_NOT_FOUND`(404), `USER_NOT_FOUND`(404), `VALIDATION_ERROR`(422),
plus shared `AUTH_NOT_AUTHENTICATED`(401)/`AUTH_FORBIDDEN`(403). **Status codes:** 200, 400, 401, 403, 404,
422.

**Audit Data Retention:** **not defined** in the schema/architecture (no retention/TTL column or policy). If
a retention policy is required (archival/purge), it needs a defined policy + a background job — flagged §9 Q6.

**Security Considerations:** audit data is sensitive — restricted to the `audit` permission (admin/compliance);
the trail is immutable (no mutation API); tenant-scoped; snapshot names intentionally preserved; no additional
secrets/PII beyond the logged `title`/`description` (writers must avoid logging secrets); reads are rate-limited
and the endpoints support paging to bound large scans.

### Open Questions
1. **Auth-event sections (Q1) — NOT supported.** Login/Logout/Failed-Login History and Active Sessions are
   not in `activity_logs` (mutation-only) and sessions are Auth/RBAC-owned (`user_sessions`, exposed via the
   Auth session-admin contract). Omitted. Confirm whether auth-event auditing is planned (needs new schema).
2. **Security Events & Password Change History (Q2).** Security Events are an approximate filtered view;
   Password Change History has no events. Confirm whether a dedicated security-event taxonomy/schema is
   required.
3. **Entity/User change history (Q3).** No generic entity reference exists; Entity Change History is
   employee/module-centric and User Change History = actions performed by a user. Confirm this is acceptable
   (else add `entity_type`/`entity_id` columns).
4. **Export (Q4) — excluded.** Belongs to the Reports/export infrastructure. Confirm ownership of audit export.
5. **Feature-key catalog (Q5).** `permissions.py` is a stub; confirm the read-only `audit` key.
6. **Retention policy (Q6).** No retention is defined; confirm whether an archival/purge policy + job is
   required.
7. **Envelope key names (Q7).** `shared/schemas/response.py` is a stub; final envelope field names must match
   once implemented (same open item as prior contracts).
