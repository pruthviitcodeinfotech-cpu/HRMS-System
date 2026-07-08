# Payroll Management API Contract

> Module: `app/modules/payroll`
> API Version: `v1` — all routes under `API_V1_PREFIX` (`/api/v1`).
> Status: **Contract only** (no FastAPI/SQLAlchemy/Pydantic/service/repository code).
> Sources of truth: `docs/architecture.md` (Backend Architecture), migration `0005_payroll`
> (+ `0008`, `0016`), the payroll models (`payroll/models/settings.py`, `run.py`, `adjustments.py`),
> `payroll/constants.py`, and the approved Authentication, RBAC, Employee, Shift, Attendance, Leave, and
> Approval API Contracts.

Covers payroll configuration, payroll groups ("salary structures"), group assignment, cycles, processing
(compute → finalize → payment), computed records, payslips (rendered), and attendance adjustments.
**Excludes** Authentication, RBAC, Employee, Shift, Attendance, Leave, Approval, Settlements, Notifications,
Settings, Hardware, Dashboard, Reports.

> **Scope notes (per approved decisions):**
> - **Salary Components are NOT supported** — no schema exists (the Backend Architecture defers salary
>   components until their schema is finalized). Omitted here (§13 Q1).
> - **"Salary Structure"** maps to **Payroll Groups** (`payroll_groups`) + employee **group assignment**
>   (`employee_payroll_group_assignments`) + **column settings** (`payroll_column_settings`). There is no
>   component-based structure.
> - **Lifecycle** maps to `is_finalized`/`finalized_payroll_runs`/`is_definalized`/`payment_status`. There is
>   **no** separate open/close, locked, or "approved" state (§13 Q2).
> - **Payslips** are rendered from `payroll_computed_rows` (no payslip table).

---

## 1. Module Overview

### Purpose
Configure payroll (org settings + payroll groups), assign employees to groups, define cycles, compute payroll
per employee, finalize/unlock runs, track payment, render payslips, and record bulk attendance adjustments.

### Responsibilities
- Payroll config (`payroll_settings`, one per org) and groups (`payroll_groups`) + column settings
  (`payroll_column_settings`).
- Employee → group assignment (`employee_payroll_group_assignments`, one per employee, history via
  `previous_group_id`).
- Cycles (`payroll_salary_cycles`), computation (`payroll_computed_rows`), finalization
  (`finalized_payroll_runs`), payment status.
- Attendance adjustments feeding payroll (`attendance_adjustments`, `attendance_adjustment_penalties`,
  `attendance_adjustment_extra_hours`).

### Dependencies
| Dependency | Location / Module | Used for |
|---|---|---|
| Auth/permission deps | `core/dependencies/auth.py` | `current_user`, `current_org`, `require_permission` |
| Tenant middleware | `core/middleware/tenant.py` | `org_id` scoping |
| RBAC data scope | `rbac` | branch/department access on employee-related reads |
| Employee (service) | `employee` | validate `employee_id`, `monthly_salary`/`salary_type` inputs |
| Attendance (read) | `attendance` | attendance days/summaries as computation inputs |
| Leave (read) | `leave` | paid-leave inputs to computation |
| Settlements (read) | `settlements` | `loan_advance_deduction`, `arrears_amount` inputs |
| Settings (read) | `settings` | `org_salary_slip_settings` payslip layout — **out of scope**, referenced |
| Notifications | `notifications` | Email Payslip delivery — **out of scope**, flagged (§13 Q4) |
| Storage | `infrastructure/storage/` | payslip PDF rendering/download |
| Response/pagination schemas | `shared/schemas/` | envelope + paginated lists |
| Activity Log (audit) | `audit` | records config/processing/finalize/payment/adjustment actions |

**Tables owned:** `payroll_settings`, `payroll_groups`, `employee_payroll_group_assignments`,
`payroll_salary_cycles`, `payroll_column_settings`, `finalized_payroll_runs`, `payroll_computed_rows`,
`attendance_adjustments`, `attendance_adjustment_penalties`, `attendance_adjustment_extra_hours`.

### Module boundaries
- Owns payroll data. Computation **reads** attendance/leave/settlements via their services (or a background
  job); those modules' write APIs are not duplicated here.
- Finalized runs and finalized computed rows are immutable until unlocked (definalized).

---

## 2. Authorization Model

Two-layer RBAC: feature permission (CRUD on `feature_key`) × data scope (branch/department access on
`employee_id`). Super admins bypass feature checks; tenant isolation (`org_id`) always applies. All endpoints
require `Authorization: Bearer <access_token>`.

**Proposed feature keys** (register in `core/security/permissions.py` — §13 Q5): `payroll_config`,
`payroll_group`, `payroll_cycle`, `payroll_processing`, `payroll_record`, `payroll_adjustment`.
Employee-related reads are additionally branch/department data-scoped. Self-service payslip view (own record)
may be permitted (§13 Q6).

---

## 3. Request & Response Standards

Reuses the shared envelope + pagination.
- **Success/Error/Paginated** envelopes as in prior contracts (`data`/`error`/`meta.request_id`;
  `data.items`+`page`+`page_size`+`total`).
- BIGINT integer IDs; money as decimal strings/numbers per `Numeric` precision (e.g. `to_pay` `Numeric(12,2)`);
  dates `YYYY-MM-DD`; timezone-aware timestamps; empty lists → `items: []`.

### Pagination / Filtering / Sorting
`page` (≥1, default 1), `page_size` (bounded). Filter/sort allowlists per endpoint; invalid field → `422`.
Repository applies `org_id` + data scope before optional filters.

**Enumerations:** `payroll_groups.payroll_type` ∈ `monthly_without_compliance, monthly_with_compliance,
hourly_payroll` (DB CHECK); `employee_payroll_group_assignments.salary_type` ∈ `monthly, hourly` (DB CHECK);
`finalized_payroll_runs.payment_status` ∈ `pending, paid, partial` (DB CHECK);
`attendance_adjustments.adjusted_status`/`original_status` ∈ `FD, HD, A, WO, LWP` (DB CHECK);
`adjustment_source` ∈ `spreadsheet, quick_action` (app-level).

Common omitted errors (all protected endpoints): `401 AUTH_NOT_AUTHENTICATED`, `403 AUTH_FORBIDDEN`,
`422 VALIDATION_ERROR`.

---

## 4. Payroll Configuration (`/api/v1/payroll/settings`) — feature key `payroll_config`

`payroll_settings` (org-level, **one row per org**): `working_hour_type`, `full_day_working_hours`/
`half_day_working_hours` (TIME), `attendance_mode`, `off_day_compensation`, `off_day_wage_multiplier`,
`daily_wage_formula`, `overtime_type`, `overtime_hourly_multiplier`, `overtime_buffer_period`,
`overtime_period_interval`, `full_day_penalty_enabled`/`half_day_penalty_enabled`/
`late_coming_penalty_enabled`, `grace_time`, `updated_by`.

| # | Endpoint | Method | URL | Permission |
|---|---|---|---|---|
| 1 | Get Payroll Configuration | GET | `/payroll/settings` | `payroll_config:read` |
| 2 | Update Payroll Configuration | PUT | `/payroll/settings` | `payroll_config:edit` |

- **2. Update** — upsert the single org row. **Validation:** multipliers ≥ 0; TIME fields valid; booleans
  typed. `200`.

---

## 5. Payroll Groups ("Salary Structures") (`/api/v1/payroll/groups`) — feature key `payroll_group`

`payroll_groups`: `name` (≤150, **unique per org among non-deleted**), `payroll_type` (CHECK), `is_default`,
`is_deleted`, timestamps, `created_by`/`updated_by`.

| # | Endpoint | Method | URL | Permission |
|---|---|---|---|---|
| 3 | Create Payroll Group | POST | `/payroll/groups` | `payroll_group:create` |
| 4 | List Payroll Groups | GET | `/payroll/groups` | `payroll_group:read` |
| 5 | Get Payroll Group Details | GET | `/payroll/groups/{group_id}` | `payroll_group:read` |
| 6 | Update Payroll Group | PATCH | `/payroll/groups/{group_id}` | `payroll_group:edit` |
| 7 | Delete Payroll Group (soft) | DELETE | `/payroll/groups/{group_id}` | `payroll_group:delete` |
| 8 | Assign Group to Employee | PUT | `/employees/{employee_id}/payroll-group` | `payroll_group:edit` |
| 9 | View Employee Group Assignment (+ history) | GET | `/employees/{employee_id}/payroll-group` | `payroll_group:read` |
| 10 | List Group Column Settings | GET | `/payroll/groups/{group_id}/columns` | `payroll_group:read` |
| 11 | Replace Group Column Settings | PUT | `/payroll/groups/{group_id}/columns` | `payroll_group:edit` |

- **3–7.** `name` unique per org (non-deleted) → `409 PAYROLL_GROUP_NAME_EXISTS`; `payroll_type` ∈ CHECK set;
  one `is_default` per org (app-level). Soft-delete blocked if assigned to employees or referenced by
  cycles/runs → `409 PAYROLL_GROUP_IN_USE`.
- **8. Assign** — `{ "payroll_group_id", "salary_type" }`. `employee_payroll_group_assignments` has
  **`UNIQUE(employee_id)`** → one group per employee; prior group recorded in `previous_group_id`,
  `assigned_by=caller`. `salary_type` ∈ `monthly,hourly`. `200`; `404 EMPLOYEE_NOT_FOUND`/
  `PAYROLL_GROUP_NOT_FOUND`.
- **9.** `200` → `{ payroll_group_id, previous_group_id, salary_type, assigned_by, assigned_at }` (the
  "Salary Structure History" is the current + previous group).
- **10–11. Column Settings** (`payroll_column_settings`) — `{ "columns": [ { column_key, column_label, is_visible, display_order }, … ] }`;
  unique `(group, column_key)`. Drives payslip/report column layout.

---

## 6. Payroll Cycles (`/api/v1/payroll/cycles`) — feature key `payroll_cycle`

`payroll_salary_cycles`: `payroll_group_id` (FK), `cycle_date`, `is_finalized`, `created_by`.
**Unique `(payroll_group_id, cycle_date)`**.

| # | Endpoint | Method | URL | Permission |
|---|---|---|---|---|
| 12 | Create Payroll Cycle | POST | `/payroll/cycles` | `payroll_cycle:create` |
| 13 | List Payroll Cycles | GET | `/payroll/cycles` | `payroll_cycle:read` |
| 14 | Update Payroll Cycle | PATCH | `/payroll/cycles/{cycle_id}` | `payroll_cycle:edit` |

- **12.** `{ "payroll_group_id", "cycle_date" }`; unique per group+date (`409 CYCLE_EXISTS`). `201`.
- **13.** filters `payroll_group_id`, `is_finalized`, date range. `200` paginated.
- **14.** update `cycle_date` **only while `is_finalized=false`** (`409 CYCLE_FINALIZED`).
- **Open/Close mapping:** there is no separate open/close status. A cycle is **open** while
  `is_finalized=false` and **closed** once finalized (via Processing §7); reopening = unlock/definalize the
  run (§13 Q2).

---

## 7. Payroll Processing (`/api/v1/payroll/processing`, `/payroll/finalized-runs`)

Feature key `payroll_processing` (mutations) / `payroll_record` (reads). Computation reads attendance/leave/
settlements (service or background job).

| # | Endpoint | Method | URL | Permission |
|---|---|---|---|---|
| 15 | Generate Payroll | POST | `/payroll/processing/generate` | `payroll_processing:edit` |
| 16 | Recalculate Payroll | POST | `/payroll/processing/recalculate` | `payroll_processing:edit` |
| 17 | Preview Payroll | POST | `/payroll/processing/preview` | `payroll_processing:read` |
| 18 | Finalize Payroll (Lock) | POST | `/payroll/processing/finalize` | `payroll_processing:edit` |
| 19 | Unlock / Definalize Payroll | POST | `/payroll/finalized-runs/{run_id}/definalize` | `payroll_processing:edit` |
| 20 | Record Payment | POST | `/payroll/finalized-runs/{run_id}/payment` | `payroll_processing:edit` |
| 21 | List Finalized Runs | GET | `/payroll/finalized-runs` | `payroll_record:read` |
| 22 | Get Finalized Run Details | GET | `/payroll/finalized-runs/{run_id}` | `payroll_record:read` |

Common body for 15–18: `{ "payroll_group_id", "cycle_from", "cycle_to", "employee_ids"? }`.

- **15. Generate** — computes/persists `payroll_computed_rows` (unique `(group, employee, cycle_from,
  cycle_to)`) for the group's active employees. `200`/`207` per-item result. Skips already-finalized rows.
- **16. Recalculate** — recomputes existing rows for the period; **only while not finalized**
  (`409 PAYROLL_ALREADY_FINALIZED`).
- **17. Preview** — computes **without persisting**; returns the would-be rows for review. `200`.
- **18. Finalize (Lock)** — creates a `finalized_payroll_runs` row (`cycle_from`, `cycle_to`,
  `payroll_module`, `finalized_amount`, `finalized_by`), sets the period's `payroll_computed_rows.is_finalized=true`
  + `finalized_run_id`, and marks the cycle `is_finalized`. Finalized rows become immutable.
  `201`; `409 PAYROLL_ALREADY_FINALIZED`.
- **19. Unlock/Definalize** — sets `finalized_payroll_runs.is_definalized=true`, `definalized_by`/`_at`;
  clears `is_finalized` on its rows to allow recompute. `200`; `409 PAYROLL_NOT_FINALIZED`.
- **20. Record Payment** — `{ "paid_amount", "payment_status" (pending|paid|partial), "paid_at"? }` on the
  run. `200`.
- **21/22.** List/Get finalized runs (filters: group, cycle range, payment_status).
- **Errors:** `404 PAYROLL_GROUP_NOT_FOUND`, `404 FINALIZED_RUN_NOT_FOUND`, `409 PAYROLL_ALREADY_FINALIZED`,
  `409 PAYROLL_NOT_FINALIZED`.

> **Approve Payroll** is **not** a distinct schema state — Finalize is the commit. Omitted (§13 Q3).

---

## 8. Payroll Records (`/api/v1/payroll/records`) — feature key `payroll_record`

`payroll_computed_rows` (per employee per cycle): counts (`total_days`, `full_day_count`, `half_day_count`,
`off_day_count`, `paid_leave_count`, `paid_day_count`, `unpaid_day_count`), amounts (`daily_wage`,
`gross_wages`, `overtime_amount`, `penalties_amount`, `extras_amount`, `gross_earnings`,
`loan_advance_deduction`, `arrears_amount`, `to_pay`, `balance_arrears`), `payment_method`, `is_finalized`,
`finalized_run_id`, `computed_at`. **Unique `(group, employee, cycle_from, cycle_to)`**.

| # | Endpoint | Method | URL | Permission |
|---|---|---|---|---|
| 23 | List Payroll Records | GET | `/payroll/records` | `payroll_record:read` |
| 24 | Get Payroll Details | GET | `/payroll/records/{row_id}` | `payroll_record:read` |
| 25 | Payroll Summary | GET | `/payroll/records/summary` | `payroll_record:read` |
| 26 | Employee Payroll History | GET | `/employees/{employee_id}/payroll` | `payroll_record:read` |

- **23.** filters `payroll_group_id`, `cycle_from`/`cycle_to`, `employee_id`, `is_finalized`, `branch_id`,
  `dept_id`; sort by `cycle_from`, `to_pay`. Data-scoped. `200` paginated.
- **24.** `200` → full computed row. `404 COMPUTED_ROW_NOT_FOUND`.
- **25. Summary** — query `payroll_group_id` + `cycle_from`/`cycle_to`. `200` → aggregates
  (`headcount`, `total_gross_earnings`, `total_to_pay`, `total_overtime`, `total_penalties`,
  `total_deductions`).
- **26. Employee History** — the employee's computed rows across cycles. `404 EMPLOYEE_NOT_FOUND`.

---

## 9. Payslips (`/api/v1/payroll/records/{row_id}/payslip`) — feature key `payroll_record`

A payslip is **rendered** from a `payroll_computed_rows` row (layout from `payroll_column_settings`; org
branding from `org_salary_slip_settings` in the Settings module). **No payslip table.**

| # | Endpoint | Method | URL | Permission |
|---|---|---|---|---|
| 27 | View Payslip (generate on demand) | GET | `/payroll/records/{row_id}/payslip` | `payroll_record:read` |
| 28 | Download Payslip | GET | `/payroll/records/{row_id}/payslip/download` | `payroll_record:read` |
| 29 | Email Payslip | POST | `/payroll/records/{row_id}/payslip/email` | `payroll_record:edit` |

- **27.** `200` → rendered payslip payload (earnings/deductions/net from the computed row + visible columns).
- **28.** `200` → PDF stream (via storage/render). Typically restricted to finalized rows (business rule).
- **29. Email Payslip** — **delegates to the Notifications/email infrastructure** (out of core scope,
  flagged §13 Q4). `202 Accepted` (queued). `404 COMPUTED_ROW_NOT_FOUND`.
- Self-service: an employee may view/download **their own** payslip (§13 Q6).

---

## 10. Payroll Adjustments (`/api/v1/payroll/adjustments`) — feature key `payroll_adjustment`

Bulk attendance adjustments feeding computation. `attendance_adjustments` (status): `attendance_date`,
`original_status`, `adjusted_status` (CHECK `FD|HD|A|WO|LWP`), `is_forced_overwrite`, `has_punch_error`,
`adjustment_source` (`spreadsheet|quick_action`), `adjusted_by`. **Unique `(employee_id, attendance_date)`**.
Components: `attendance_adjustment_penalties` (`penalty_amount`, `remark`, `is_removed`) and
`attendance_adjustment_extra_hours` (`extra_hours`, `remark`, **unique `(employee_id, attendance_date)`**).

| # | Endpoint | Method | URL | Permission |
|---|---|---|---|---|
| 30 | Add / Upsert Adjustment | POST | `/payroll/adjustments` | `payroll_adjustment:create` |
| 31 | Update Adjustment | PATCH | `/payroll/adjustments/{adjustment_id}` | `payroll_adjustment:edit` |
| 32 | Delete Adjustment | DELETE | `/payroll/adjustments/{adjustment_id}` | `payroll_adjustment:delete` |
| 33 | List / Adjustment History | GET | `/payroll/adjustments` | `payroll_adjustment:read` |
| 34 | Add Adjustment Penalty | POST | `/payroll/adjustments/penalties` | `payroll_adjustment:create` |
| 35 | Add Adjustment Extra Hours | POST | `/payroll/adjustments/extra-hours` | `payroll_adjustment:create` |

- **30.** `{ "employee_id", "attendance_date", "adjusted_status", "original_status"?, "adjustment_source"?, "is_forced_overwrite"?, "has_punch_error"? }`.
  Unique per `(employee, date)` → `409 ADJUSTMENT_EXISTS` (or upsert). `adjusted_status` ∈ CHECK set.
  `adjusted_by=caller`.
- **31/32.** Update/hard-delete an adjustment (no soft-delete column on `attendance_adjustments`).
- **33.** filters `employee_id`, `date_from`/`date_to`, `adjustment_source`; data-scoped. Includes penalties
  and extra-hours for the range (adjustment history).
- **34. Penalty** — `{ "employee_id", "attendance_date", "penalty_amount", "remark"? }`; removal via
  `is_removed` (PATCH). Multiple penalties per `(employee, date)` allowed.
- **35. Extra Hours** — `{ "employee_id", "attendance_date", "extra_hours", "remark"? }`; unique per
  `(employee, date)` → `409`.
- **Business rule:** adjustments for a period already **finalized** should be blocked/require definalize
  (`409 PAYROLL_ALREADY_FINALIZED`).
- **Errors:** `404 ADJUSTMENT_NOT_FOUND`, `404 EMPLOYEE_NOT_FOUND`, `409 ADJUSTMENT_EXISTS`.

---

## 11. Business Rules (summary)

- **Tenant isolation** on all operations; employee-related reads are branch/department data-scoped.
- **Group:** `name` unique per org (non-deleted); one default per org; soft-delete blocked while in use.
- **Assignment:** one payroll group per employee; reassignment records `previous_group_id`.
- **Cycle:** unique per `(group, cycle_date)`; editable only while not finalized.
- **Processing:** compute writes `payroll_computed_rows` (unique per group/employee/cycle); recalé only while
  not finalized; **Finalize** creates the run + locks rows; **Definalize** unlocks; payment via
  `payment_status`. Finalized rows are immutable.
- **Payslip** rendered from a computed row; download typically restricted to finalized rows.
- **Adjustments** unique per `(employee, date)` (status & extra-hours); blocked for finalized periods.
- **Salary Components** unsupported; **Approve Payroll** not a distinct state (Finalize is the commit).

---

## 12. Permission Matrix

| Feature key | create | read | edit | delete |
|---|---|---|---|---|
| `payroll_config` | — | Get settings | Update settings | — |
| `payroll_group` | Create group | List/Get, assignment, columns | Update, Assign, Replace columns | Delete (soft) |
| `payroll_cycle` | Create cycle | List cycles | Update cycle | — |
| `payroll_processing` | — | Preview | Generate, Recalculate, Finalize, Definalize, Record Payment | — |
| `payroll_record` | — | List/Get records, Summary, Employee history, Finalized runs, View/Download payslip | Email payslip | — |
| `payroll_adjustment` | Add adjustment/penalty/extra-hours | List/History | Update | Delete |

Super admins bypass feature checks; tenant isolation always applies; employee reads are data-scoped;
self-service payslip view permitted for own record (§13 Q6).

---

## 13. Error Handling, Security & Open Questions

**Error envelope** via `core/exceptions/handlers.py`. Module error codes (proposed, `payroll/exceptions.py`):
`PAYROLL_GROUP_NOT_FOUND`(404), `PAYROLL_GROUP_NAME_EXISTS`(409), `PAYROLL_GROUP_IN_USE`(409),
`CYCLE_NOT_FOUND`(404), `CYCLE_EXISTS`(409), `CYCLE_FINALIZED`(409), `COMPUTED_ROW_NOT_FOUND`(404),
`FINALIZED_RUN_NOT_FOUND`(404), `PAYROLL_ALREADY_FINALIZED`(409), `PAYROLL_NOT_FINALIZED`(409),
`ADJUSTMENT_NOT_FOUND`(404), `ADJUSTMENT_EXISTS`(409), `EMPLOYEE_NOT_FOUND`(404), `VALIDATION_ERROR`(422),
plus shared `AUTH_NOT_AUTHENTICATED`(401)/`AUTH_FORBIDDEN`(403).

**HTTP status codes used:** 200, 201, 202, 207, 400, 401, 403, 404, 409, 422.

**Security considerations:** every route enforces `require_permission` + tenant scope + branch/department data
scope; payroll amounts and payslips are sensitive — restricted to permitted roles and the employee's own
record; finalize/definalize/payment and adjustments recorded in the Activity Log (actor, before/after,
amounts); no secrets/PII in logs; timestamps timezone-aware; rate limiting on processing/finalize/email
endpoints.

### Open Questions
1. **Salary Components (Q1) — NOT supported.** No schema exists (architecture-deferred). Omitted. Confirm the
   plan/timeline for the salary-components schema before contracting it.
2. **Cycle open/close & reopen (Q2).** Modeled via `is_finalized`/definalize (no distinct open/close status).
   Confirm this is acceptable.
3. **Approve Payroll (Q3).** No approval state exists; Finalize is the commit. Confirm no separate payroll
   approval step is required (else a status/schema change is needed).
4. **Email Payslip (Q4).** Delegated to the Notifications/email infrastructure (out of core scope). Confirm
   ownership and whether payslip PDFs are persisted (storage) or rendered on demand.
5. **Feature-key catalog (Q5).** `permissions.py` is a stub; confirm the six proposed payroll keys.
6. **Self-service payslip (Q6).** Confirm employees may view/download their **own** payslips/records
   (resolved via `users.employee_id`).
7. **Computation source-of-truth (Q7).** Generate/Recalculate read attendance/leave/settlements; whether this
   is synchronous or a background job (and the exact inputs) is a service concern outside this contract —
   confirm the trigger.
8. **Payroll settings vs Settings module (Q8).** `payroll_settings` is payroll-owned but configuration-like;
   confirm it belongs in this contract (included here) vs a Settings contract.
9. **Envelope key names (Q9).** `shared/schemas/response.py` is a stub; final envelope field names must match
   once implemented (same open item as prior contracts).
