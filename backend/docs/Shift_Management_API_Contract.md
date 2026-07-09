# Shift Management API Contract

> Module: `app/modules/shift`
> API Version: `v1` — all routes under `API_V1_PREFIX` (`/api/v1`).
> Status: **Contract only** (no FastAPI/SQLAlchemy/Pydantic/service/repository code).
> Sources of truth: `docs/architecture.md` (Backend Architecture), migration `0002_shift_management`
> (+ `0009`, `0016`), the shift models (`shift/models/shift.py`, `assignment.py`, `working_hours.py`),
> `shift/constants.py`, and the approved Authentication, User-Management/RBAC, and Employee contracts.

Covers shift definitions, per-day timings, weekly-off configuration, shift assignment (dated), and the
per-employee/per-date roster (Shift Calendar). **Excludes** Authentication, RBAC, Employee, Attendance,
Leave, Approval, Payroll, Settlements, Notifications, Settings, Hardware, Dashboard, Reports.

---

## 1. Module Overview

### Purpose
Define shifts and their timings, configure employees' weekly-off patterns, assign shifts to employees over
dated periods, and maintain the per-employee daily roster (calendar).

### Responsibilities
- Shift master (`shifts`) + per-day timings (`shift_day_timings`).
- Weekly-off configuration per employee (`employee_weekoffs`).
- Shift assignment with effective date ranges + history (`shift_assignments`).
- Daily roster / shift calendar (`roster`).

### Dependencies
| Dependency | Location | Used for |
|---|---|---|
| Auth/permission deps | `core/dependencies/auth.py` | `current_user`, `current_org`, `require_permission` |
| Tenant middleware | `core/middleware/tenant.py` | `org_id` scoping |
| RBAC data scope | `rbac` | branch/department access filters employee-related lists |
| Employee module (service) | `employee` | validate `employee_id` exists/active in org |
| Response/pagination schemas | `shared/schemas/` | envelope + paginated lists |
| Activity Log (audit) | `audit` | records administrative mutations |

**Tables owned & in scope:** `shifts`, `shift_day_timings`, `shift_assignments`, `employee_weekoffs`,
`roster`.
**Owned by this module but OUT of scope here:** `working_hours_config`, `working_hours_config_history`
(org working-hours settings — see §12 Q3).

### Module boundaries
- Owns shift/scheduling data. References `organizations`/`employees` by ID (FKs enforced in `0002`) but does
  not own them. `created_by`/`assigned_by`/`updated_by` → users are deferred reference columns.
- **Shift Rotation is not modeled** in the schema — no rotation-pattern entity exists (see §12 Q1).

---

## 2. Authorization Model

Standard two-layer RBAC: feature permission (CRUD on a `feature_key`) × data scope (branch/department
access). Super admins bypass feature checks; tenant isolation (`org_id`) always applies. All endpoints
require `Authorization: Bearer <access_token>`.

**Proposed feature keys** (to be registered in `core/security/permissions.py` — see §12 Q4):
`shift` (master + timings), `shift_assignment`, `weekoff`, `roster`. Employee-related lists (assignments,
week-offs, roster) are additionally filtered by the caller's branch/department data scope (super admin
exempt).

---

## 3. Request & Response Standards

Reuses the shared envelope + pagination from the Backend Architecture.
- **Success:** `{ "success": true, "data": {…}, "error": null, "meta": { "request_id": "…" } }`
- **Error:** `{ "success": false, "data": null, "error": { "code", "message", "details"? }, "meta": {…} }`
- **Paginated:** `data.items` + `page`, `page_size`, `total`.
- BIGINT integer IDs; timezone-aware ISO-8601 timestamps; `TIME` fields as `HH:MM`/`HH:MM:SS`; dates as
  `YYYY-MM-DD`; empty lists → `items: []`; ORM never returned directly.

### Pagination / Filtering / Sorting
- `page` (≥1, default 1), `page_size` (bounded default).
- Filters/sorts are explicit allowlists per endpoint; invalid field → `422`.
- Repository applies `org_id` (and data scope) before optional filters.

Common omitted errors (all protected endpoints): `401 AUTH_NOT_AUTHENTICATED`, `403 AUTH_FORBIDDEN`,
`422 VALIDATION_ERROR`.

---

## 4. Shift Master (`/api/v1/shifts`) — feature key `shift`

`shifts` fields: `shift_name` (req ≤150, **unique per org among non-deleted**), `shift_type`
(CHECK `fixed|open`, default `fixed`), `is_open_shift` (bool), `is_default` (bool), `is_uniform_time`
(bool, default true), `has_break_time` (bool), `shift_color` (≤30), `remark` (text), `is_advanced_mode`
(bool), `is_deleted`, `created_by` (deferred→users).

> **Note:** `shifts` has **no `is_active`** column. Enable/disable is expressed only via soft delete
> (`is_deleted`). Activate/Deactivate is therefore **not supported**; Delete (soft) + Restore are provided
> (see §12 Q2).

| # | Endpoint | Method | URL | Permission |
|---|---|---|---|---|
| 1 | Create Shift | POST | `/shifts` | `shift:create` |
| 2 | List / Search Shifts | GET | `/shifts` | `shift:read` |
| 3 | Get Shift Details | GET | `/shifts/{shift_id}` | `shift:read` |
| 4 | Update Shift | PATCH | `/shifts/{shift_id}` | `shift:edit` |
| 5 | Delete Shift (soft) | DELETE | `/shifts/{shift_id}` | `shift:delete` |
| 6 | Restore Shift | POST | `/shifts/{shift_id}/restore` | `shift:edit` |

**1. Create Shift** — body = shift fields; optionally inline `timings` (see §5).
- **Validation:** `shift_name` req, unique per org (non-deleted) → `409 SHIFT_NAME_EXISTS`; `shift_type` ∈
  `fixed,open`; booleans well-typed; `shift_color` ≤30. If `is_uniform_time=true`, at most one timing with
  `day_of_week=NULL`; if false, per-day timings (see §5 rules).
- **Business rules:** only one `is_default=true` shift per org (app-level guard).
- **Success:** `201` → shift (with timings if provided). **Status:** 201, 409, 422.

**2. List / Search Shifts** — **Query:** `page`, `page_size`, `search` (shift_name), `shift_type`,
`is_default`, `is_open_shift`, `include_deleted` (default false), `sort_by` (`shift_name|created_at`),
`sort_dir`. **Success:** `200` paginated shift summaries.

**3. Get Shift Details** — `200` → shift + its `day_timings`. `404 SHIFT_NOT_FOUND`.

**4. Update Shift** — PATCH any master field; `shift_name` uniqueness re-checked. `200`; `404`,
`409 SHIFT_NAME_EXISTS`.

**5. Delete Shift (soft)** — sets `is_deleted=true`. **Blocked** if referenced by active assignments or roster
entries → `409 SHIFT_IN_USE`. `204`; `404 SHIFT_NOT_FOUND`.

**6. Restore Shift** — clears `is_deleted`. `200`; `404`, `409 SHIFT_NOT_DELETED`.

---

## 5. Shift Timings (`/api/v1/shifts/{shift_id}/timings`) — feature key `shift`

`shift_day_timings` fields: `day_of_week` (SMALLINT 0=Sun..6=Sat, **nullable** — a single row with
`day_of_week=NULL` represents a uniform timing), `start_time`, `end_time`, `break_start_time`,
`break_end_time` (all TIME, nullable), `duration_minutes` (int), `is_working_day` (bool, default true).
**Unique `(shift_id, day_of_week)`.**

| # | Endpoint | Method | URL | Permission |
|---|---|---|---|---|
| 7 | List Shift Timings | GET | `/shifts/{shift_id}/timings` | `shift:read` |
| 8 | Replace Shift Timings | PUT | `/shifts/{shift_id}/timings` | `shift:edit` |
| 9 | Update One Timing | PATCH | `/shifts/{shift_id}/timings/{timing_id}` | `shift:edit` |
| 10 | Delete One Timing | DELETE | `/shifts/{shift_id}/timings/{timing_id}` | `shift:edit` |

- **Timing item:** `{ "day_of_week"?, "start_time"?, "end_time"?, "break_start_time"?, "break_end_time"?, "duration_minutes"?, "is_working_day"? }`.
- **8. Replace** — `{ "timings": [ item, … ] }` replaces the shift's full timing set atomically.
- **Validation / Business rules:**
  - If the shift's `is_uniform_time=true`: exactly **one** timing with `day_of_week=NULL`.
  - If `is_uniform_time=false`: at most one row **per** `day_of_week` (0–6); `(shift_id, day_of_week)` unique →
    `409 TIMING_DAY_DUPLICATE`.
  - `end_time` should be after `start_time`; break window within the shift window (app-level).
  - `has_break_time=false` ⇒ break fields omitted.
- **Errors:** `404 SHIFT_NOT_FOUND`, `404 TIMING_NOT_FOUND`, `409 TIMING_DAY_DUPLICATE`.

---

## 6. Weekly Off Configuration (`/api/v1/employees/{employee_id}/weekoffs`) — feature key `weekoff`

`employee_weekoffs` fields: `day_of_week` (SMALLINT, **CHECK 0–6**), `weekoff_type`
(CHECK `working|week_off|occasional_week_off`, default `working`), `occurrence_1st…occurrence_5th` (bool,
default true — which occurrences of that weekday in a month apply), `effective_from`, `effective_to`
(nullable), `updated_by` (deferred→users). **Partial unique `(employee_id, day_of_week)` WHERE
`effective_to IS NULL`** (one *current* config per weekday).

| # | Endpoint | Method | URL | Permission |
|---|---|---|---|---|
| 11 | View Weekly Off Config | GET | `/employees/{employee_id}/weekoffs` | `weekoff:read` |
| 12 | Configure Weekly Off | PUT | `/employees/{employee_id}/weekoffs` | `weekoff:edit` |
| 13 | Update One Weekly Off | PATCH | `/employees/{employee_id}/weekoffs/{weekoff_id}` | `weekoff:edit` |

- **11.** `200` → current config rows (`effective_to IS NULL`); `?include_history=true` returns superseded
  rows too.
- **12. Configure** — `{ "weekoffs": [ { day_of_week (0–6), weekoff_type, occurrence_1st..5th?, effective_from? }, … ] }`.
  Sets/replaces the employee's current weekly-off config (supersedes prior current rows by setting their
  `effective_to`). Enforces the partial-unique current-row rule.
- **13. Update One** — PATCH a single weekday's `weekoff_type`/occurrence flags/`effective_to`.
- **Validation:** `day_of_week` ∈ 0–6 (`ck_employee_weekoffs_day_of_week`); `weekoff_type` ∈ the CHECK set;
  `effective_to ≥ effective_from` when both present.
- **Errors:** `404 EMPLOYEE_NOT_FOUND`, `404 WEEKOFF_NOT_FOUND`, `409 WEEKOFF_DAY_EXISTS`
  (duplicate current row for a weekday).

---

## 7. Shift Assignment (`/api/v1/shift-assignments`) — feature key `shift_assignment`

`shift_assignments` fields: `org_id`, `employee_id` (FK→employees), `shift_id` (FK→shifts), `effective_from`
(req date), `effective_to` (nullable date — open-ended when null), `assigned_by` (deferred→users). Indexed on
`(employee_id, effective_from, effective_to)`. **No unique constraint** → an employee may have multiple
dated assignments (history + future); the *current* one covers today's date.

| # | Endpoint | Method | URL | Permission |
|---|---|---|---|---|
| 14 | Assign Shift to Employee | POST | `/shift-assignments` | `shift_assignment:create` |
| 15 | Bulk Assign Shift | POST | `/shift-assignments/bulk` | `shift_assignment:create` |
| 16 | List Assignments | GET | `/shift-assignments` | `shift_assignment:read` |
| 17 | Update Assignment | PATCH | `/shift-assignments/{assignment_id}` | `shift_assignment:edit` |
| 18 | Remove Assignment | DELETE | `/shift-assignments/{assignment_id}` | `shift_assignment:delete` |
| 19 | View Employee Assignments (current + history) | GET | `/employees/{employee_id}/shift-assignments` | `shift_assignment:read` |

- **14. Assign** — `{ "employee_id", "shift_id", "effective_from", "effective_to"? }`. Employee must exist &
  active in org; shift must exist & non-deleted in org. `201`.
- **15. Bulk Assign** — `{ "employee_ids": [ … ], "shift_id", "effective_from", "effective_to"? }`.
  Creates one assignment per employee; returns a per-item result (created / skipped-with-reason). `200`/`207`.
- **16. List Assignments** — **Query:** `page`, `page_size`, `employee_id`, `shift_id`, `active_on`
  (date — returns assignments whose range covers it), `sort_by` (`effective_from|created_at`), `sort_dir`.
  Data-scoped. `200` paginated.
- **17. Update** — PATCH `shift_id` / `effective_from` / `effective_to`. `200`; `404 ASSIGNMENT_NOT_FOUND`.
- **18. Remove** — hard delete (no `is_deleted` on this table). `204`; `404 ASSIGNMENT_NOT_FOUND`.
- **19. View Employee Assignments** — `200` → the employee's assignments; `?current=true` returns only the
  active one; default returns all (history). This is the **Shift Assignment History** view.
- **Business rules:** overlapping active date ranges for the same employee are **not** DB-enforced; a business
  guard should reject overlaps or auto-close the prior open-ended assignment (§9). `effective_to ≥
  effective_from`.
- **Errors:** `404 EMPLOYEE_NOT_FOUND`, `404 SHIFT_NOT_FOUND`, `404 ASSIGNMENT_NOT_FOUND`,
  `409 ASSIGNMENT_OVERLAP`.

---

## 8. Shift Calendar / Roster (`/api/v1/roster`) — feature key `roster`

`roster` fields: `org_id`, `employee_id` (FK→employees), `roster_date` (req date), `shift_id` (nullable
FK→shifts), `is_week_off` (bool, default false), `created_by`/`updated_by` (deferred→users).
**Unique `(employee_id, roster_date)`** (one entry per employee per day); indexed `(org_id, roster_date)`.

| # | Endpoint | Method | URL | Permission |
|---|---|---|---|---|
| 20 | View Shift Calendar (org; date range / month) | GET | `/roster` | `roster:read` |
| 21 | Employee Shift Calendar | GET | `/employees/{employee_id}/roster` | `roster:read` |
| 22 | Set Roster Entry (upsert) | PUT | `/roster` | `roster:edit` |
| 23 | Bulk Set Roster | POST | `/roster/bulk` | `roster:edit` |
| 24 | Update Roster Entry | PATCH | `/roster/{roster_id}` | `roster:edit` |
| 25 | Delete Roster Entry | DELETE | `/roster/{roster_id}` | `roster:delete` |

- **20. View Shift Calendar** — **Query (one range form required):** `date_from` + `date_to`, **or** `month`
  (`YYYY-MM`) — the latter is the **Monthly Shift Schedule**. Optional `branch_id`, `dept_id`, `employee_id`,
  `shift_id`, plus `page`/`page_size`. Data-scoped by branch/department access. `200` → roster entries
  (employee, date, shift, is_week_off). Wide date spans must page.
- **21. Employee Shift Calendar** — `date_from`+`date_to` **or** `month`. `200` → that employee's roster.
  `404 EMPLOYEE_NOT_FOUND`.
- **22. Set Roster Entry (upsert)** — `{ "employee_id", "roster_date", "shift_id"?, "is_week_off"? }`.
  Upserts on `(employee_id, roster_date)`. `shift_id` must be non-deleted in org; `is_week_off=true` typically
  implies `shift_id=null`. `200`/`201`.
- **23. Bulk Set Roster** — `{ "entries": [ { employee_id, roster_date, shift_id?, is_week_off? }, … ] }`.
  Upserts many entries; per-item result. `200`/`207`.
- **24. Update Roster Entry** — PATCH `shift_id`/`is_week_off`. `200`; `404 ROSTER_NOT_FOUND`.
- **25. Delete Roster Entry** — hard delete (no `is_deleted`). `204`; `404 ROSTER_NOT_FOUND`.
- **Validation/Business rules:** `roster_date` valid; one entry per employee/day (`409 ROSTER_ENTRY_EXISTS`
  on non-upsert create paths); a week-off entry should not also carry a shift (app-level).
- **Errors:** `404 EMPLOYEE_NOT_FOUND`, `404 SHIFT_NOT_FOUND`, `404 ROSTER_NOT_FOUND`,
  `409 ROSTER_ENTRY_EXISTS`.

---

## 9. Business Rules (summary)

- **Tenant isolation:** every operation scoped to caller's `org_id`; cross-org → `404` within scope.
- **Data scope:** assignment/week-off/roster reads filtered by branch/department access (super admin exempt).
- **Shift name** unique per org among non-deleted; **one default shift** per org (app-level).
- **Timings:** uniform ⇒ single `day_of_week=NULL` row; non-uniform ⇒ ≤1 row per weekday (unique
  `(shift_id, day_of_week)`).
- **Weekly off:** `day_of_week` 0–6; one *current* row per weekday (`effective_to IS NULL`).
- **Assignments:** dated ranges; no DB overlap guard — enforce non-overlap or auto-close open ranges at the
  service layer; current = range covering today.
- **Roster:** one entry per `(employee, date)` (upsert); week-off entry excludes a shift.
- **Shift delete** is soft; blocked while referenced by active assignments/roster (`SHIFT_IN_USE`).
- **Shift has no active/inactive state** — only soft delete/restore.

---

## 10. Permission Matrix

| Feature key | create | read | edit | delete |
|---|---|---|---|---|
| `shift` | Create Shift | List/Search, Get, List timings | Update, Restore, Replace/Update/Delete timings | Delete Shift (soft) |
| `shift_assignment` | Assign, Bulk Assign | List, View employee (history) | Update Assignment | Remove Assignment |
| `weekoff` | — | View config | Configure, Update one | — |
| `roster` | (via edit upsert) | View calendar, employee calendar | Set/Bulk-set/Update entry | Delete entry |

Super admins bypass feature checks; tenant isolation always applies; employee-related reads are data-scoped.

---

## 11. Error Handling & Security

**Error envelope** via `core/exceptions/handlers.py`. Module error codes (proposed, to be registered in
`shift/exceptions.py`): `SHIFT_NOT_FOUND`(404), `SHIFT_NAME_EXISTS`(409), `SHIFT_IN_USE`(409),
`SHIFT_NOT_DELETED`(409), `TIMING_NOT_FOUND`(404), `TIMING_DAY_DUPLICATE`(409), `WEEKOFF_NOT_FOUND`(404),
`WEEKOFF_DAY_EXISTS`(409), `ASSIGNMENT_NOT_FOUND`(404), `ASSIGNMENT_OVERLAP`(409), `ROSTER_NOT_FOUND`(404),
`ROSTER_ENTRY_EXISTS`(409), `EMPLOYEE_NOT_FOUND`(404), `VALIDATION_ERROR`(422), plus shared
`AUTH_NOT_AUTHENTICATED`(401)/`AUTH_FORBIDDEN`(403).

**HTTP status codes used:** 200, 201, 204, 207 (bulk multi-status), 400, 401, 403, 404, 409, 422.

**Security considerations:** every route enforces `require_permission` + tenant scope + (for employee-related
reads) branch/department data scope; bulk operations validate each item and never leak cross-org rows; all
mutations recorded in the Activity Log (actor, org, before/after where applicable); timestamps timezone-aware;
no secrets/PII in logs; rate limiting per the security baseline on bulk endpoints.

---

## 12. Open Questions

1. **Shift Rotation (Q1) — NOT supported.** No rotation-pattern/cycle table exists; only per-date `roster`
   scheduling. Create/Update/Delete/Assign Rotation and Rotation History are **omitted**. Confirm whether a
   rotation feature is planned (it would require new schema/migration).
2. **Shift Activate/Deactivate (Q2).** `shifts` has no `is_active`; only soft delete/restore is provided.
   Confirm that is sufficient (else a status column is needed).
3. **Working-hours configuration (Q3).** `working_hours_config` (+history) is shift-module-owned but not in
   this contract's scope; excluded here. Decide which contract (Shift-config or Settings) should cover it.
4. **Feature-key catalog (Q4).** `permissions.py` is a stub; confirm the proposed keys
   (`shift`/`shift_assignment`/`weekoff`/`roster`) and their exact strings.
5. **Assignment overlap policy (Q5).** The DB does not prevent overlapping dated assignments for one employee.
   Confirm the intended rule (reject overlaps vs auto-close the prior open-ended assignment).
6. **Roster generation (Q6).** Roster entries are created manually/bulk here. If auto-generation from
   assignments + week-offs is desired, confirm scope (likely a background job, not an API concern).
7. **Envelope key names (Q7).** `shared/schemas/response.py` is a stub; final envelope field names must match
   once implemented (same open item as prior contracts).
