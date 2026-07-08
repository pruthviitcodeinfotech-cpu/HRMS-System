# Attendance Management API Contract

> Module: `app/modules/attendance`
> API Version: `v1` — all routes under `API_V1_PREFIX` (`/api/v1`).
> Status: **Contract only** (no FastAPI/SQLAlchemy/Pydantic/service/repository code).
> Sources of truth: `docs/architecture.md` (Backend Architecture), migration `0015_attendance_core`
> (+ `0016`), the attendance models (`attendance/models.py`), and the approved Authentication,
> User-Management/RBAC, Employee, and Shift API Contracts.

Covers the three attendance-owned tables — `attendance_days`, `attendance_punches`, `attendance_penalties` —
plus read-only summaries and reports computed over them. **Excludes** Authentication, RBAC, Employee, Shift,
Leave, Approval, Payroll, Settlements, Notifications, Settings, Hardware, and the generic Dashboard/Reports
modules. Cross-module tables (employees, shifts, leave_requests, biometric_devices, users, payroll) are
**referenced/read only**, never written here.

---

## 1. Module Overview

### Purpose
Record and expose daily attendance (`attendance_days`), the immutable punch log (`attendance_punches`), and
attendance-driven penalties (`attendance_penalties`); provide attendance-scoped summaries and reports.

### Responsibilities
- Daily attendance summary rows: read, and admin manual mark/override (`source='manual'`, `marked_by`).
- Punch log: read, and admin manual punch entry (`punch_source='manual_entry'`). Punches are append-only.
- Penalties: apply, list, waive, history.
- Attendance-scoped aggregations (counts, working hours) and employee/department/branch/shift reports.

### Dependencies
| Dependency | Location / Module | Used for |
|---|---|---|
| Auth/permission deps | `core/dependencies/auth.py` | `current_user`, `current_org`, `require_permission` |
| Tenant middleware | `core/middleware/tenant.py` | `org_id` scoping |
| RBAC data scope | `rbac` | branch/department access filters employee-related reads |
| Employee module (service) | `employee` | resolve employee, and branch/department membership for reports |
| Shift module (read) | `shift` | `shift_id`, expected shift times on a day |
| Leave (read) | `leave` | `leave_id` link when `status='on_leave'` |
| Hardware (read) | `hardware` | `device_id` on device-sourced punches |
| Approval | `approvals` | regularization (`attendance_regularization_requests`) — **out of scope**, sets `is_regularized`/`is_valid` |
| Payroll | `payroll` | `payroll_reference_id` populated when a penalty is consumed — **deferred**, out of scope |
| Response/pagination schemas | `shared/schemas/` | envelope + paginated lists |
| Activity Log (audit) | `audit` | records manual marks, punches, penalty apply/waive |

**Tables owned:** `attendance_days`, `attendance_punches`, `attendance_penalties`.

### Module boundaries
- Owns attendance data only. Regularization requests live in the **Approval** module; `attendance_days.is_regularized`
  and `attendance_punches.is_valid` are set by that flow and are **read-only** here.
- Automatic attendance/summary computation from raw punches is a **service/background-job** concern (not an
  API surface); this contract exposes the resulting rows plus admin manual overrides.

---

## 2. Authorization Model

Two-layer RBAC: feature permission (CRUD on a `feature_key`) × data scope (branch/department access). Super
admins bypass feature checks; tenant isolation (`org_id`) always applies. All endpoints require
`Authorization: Bearer <access_token>`.

**Proposed feature keys** (to be registered in `core/security/permissions.py` — see §12 Q4):
`attendance` (days + summaries + reports), `attendance_punch`, `attendance_penalty`. All employee-related
reads are additionally filtered by the caller's branch/department data scope (super admin exempt).

---

## 3. Request & Response Standards

Reuses the shared envelope + pagination.
- **Success:** `{ "success": true, "data": {…}, "error": null, "meta": { "request_id": "…" } }`
- **Error:** `{ "success": false, "data": null, "error": { "code", "message", "details"? }, "meta": {…} }`
- **Paginated:** `data.items` + `page`, `page_size`, `total`.
- BIGINT integer IDs; timezone-aware ISO-8601 timestamps (`punch_time`, `first_punch_in`, `last_punch_out`);
  dates `YYYY-MM-DD`; `TIME` as `HH:MM[:SS]`; durations returned as **minutes** (integers) as stored; empty
  lists → `items: []`.

### Pagination / Filtering / Sorting
- `page` (≥1, default 1), `page_size` (bounded). Filters/sorts are explicit allowlists; invalid field →
  `422`. Repository applies `org_id` + data scope before optional filters. Wide date spans must page.

Common omitted errors (all protected endpoints): `401 AUTH_NOT_AUTHENTICATED`, `403 AUTH_FORBIDDEN`,
`422 VALIDATION_ERROR`.

**Enumerations (VARCHAR + CHECK):**
`attendance_days.status` ∈ `present, absent, half_day, week_off, holiday, on_leave, not_marked`;
`attendance_days.source` ∈ `biometric, mobile, web, manual, system`;
`attendance_punches.punch_type` ∈ `in, out, break_in, break_out`;
`attendance_punches.punch_source` ∈ `biometric_device, mobile_app, web_portal, manual_entry`;
`attendance_penalties.penalty_type` ∈ `late_coming, early_going, absent_without_notice, other`;
`attendance_penalties.penalty_unit` ∈ `amount, days, hours`;
`attendance_penalties.status` ∈ `active, waived`.

---

## 4. Attendance Days (`/api/v1/attendance/days`) — feature key `attendance`

`attendance_days` fields: `id`, `org_id`, `employee_id` (FK employees), `attendance_date` (date),
`shift_id` (FK shifts, nullable), `expected_start_time`/`expected_end_time` (TIME), `status` (CHECK, default
`not_marked`), `first_punch_in`/`last_punch_out` (timestamptz), `total_working_minutes`,
`total_break_minutes`, `overtime_minutes`, `late_minutes`, `early_leaving_minutes` (int ≥0, default 0),
`leave_id` (FK leave_requests, nullable), `is_regularized` (bool, read-only), `source` (CHECK, default
`system`), `marked_by` (FK users, nullable), `remarks`, `created_at`/`updated_at`, `created_by`/`updated_by`.
**Unique `(employee_id, attendance_date)`**; index `(org_id, attendance_date)`.

| # | Endpoint | Method | URL | Permission |
|---|---|---|---|---|
| 1 | Mark / Create Attendance (manual) | POST | `/attendance/days` | `attendance:create` |
| 2 | Override Attendance (manual) | PATCH | `/attendance/days/{day_id}` | `attendance:edit` |
| 3 | List / Search / Filter Attendance | GET | `/attendance/days` | `attendance:read` |
| 4 | Get Attendance Details | GET | `/attendance/days/{day_id}` | `attendance:read` |
| 5 | Employee Attendance History | GET | `/employees/{employee_id}/attendance/days` | `attendance:read` |
| 6 | Attendance Calendar View | GET | `/employees/{employee_id}/attendance/calendar` | `attendance:read` |

**1. Mark / Create Attendance** — `{ "employee_id", "attendance_date", "status", "shift_id"?, "leave_id"?, "remarks"?, "total_working_minutes"?, … }`.
Sets `source='manual'`, `marked_by=caller`.
- **Validation:** employee exists/active in org; `attendance_date` valid; `status` ∈ CHECK set; minute fields
  ≥0; if `status='on_leave'`, `leave_id` should reference an approved leave (or null); `shift_id` non-deleted
  in org if present.
- **Business rules:** one row per `(employee_id, attendance_date)` → duplicate returns
  `409 ATTENDANCE_DAY_EXISTS` (use Override #2). May trigger a downstream recompute (service concern).
- **Success:** `201` → attendance-day object. **Status:** 201, 404, 409, 422.

**2. Override Attendance** — PATCH `status`, minute fields, `shift_id`, `leave_id`, `remarks`; sets
`source='manual'`, `marked_by`, `updated_by`. `is_regularized` is **not** settable here. `200`;
`404 ATTENDANCE_DAY_NOT_FOUND`, `422`.

**3. List / Search / Filter** — **Query:** `page`, `page_size`, `date` (single day → **Daily Attendance**),
`month` (`YYYY-MM` → **Monthly Attendance**), `date_from`/`date_to`, `employee_id`, `status`, `source`,
`shift_id`, `branch_id`, `dept_id`, `is_regularized`, `min_late_minutes`, `sort_by`
(`attendance_date|employee_id|total_working_minutes`), `sort_dir`. Data-scoped. `200` paginated. Exactly one
date form (`date` | `month` | `date_from`+`date_to`) required for broad org-wide queries.

**4. Get Attendance Details** — `200` → the day + optional `?expand=punches,penalties`.
`404 ATTENDANCE_DAY_NOT_FOUND`.

**5. Employee Attendance History** — `date_from`+`date_to` **or** `month`. `200` paginated per-day rows for
one employee. `404 EMPLOYEE_NOT_FOUND`.

**6. Attendance Calendar View** — `month` (`YYYY-MM`) or `date_from`+`date_to`. `200` → per-date
`{ attendance_date, status, shift_id, total_working_minutes, is_regularized }` for the employee (calendar
grid source). `404 EMPLOYEE_NOT_FOUND`.

> **Delete attendance day:** not exposed (attendance is system-of-record; corrections go through Override or
> the Approval regularization flow). Confirm in §12 Q3.

---

## 5. Attendance Punches (`/api/v1/attendance/punches`) — feature key `attendance_punch`

`attendance_punches` fields: `id`, `org_id`, `employee_id`, `attendance_day_id` (FK attendance_days),
`punch_type` (CHECK), `punch_time` (timestamptz), `sequence_no` (smallint >0), `punch_source` (CHECK),
`device_id` (FK biometric_devices, nullable), `latitude`/`longitude` (Numeric(9,6)), `is_valid` (bool,
default true, read-only here), `created_at`/`updated_at`, `created_by` (FK users, nullable). Indexes:
`(attendance_day_id, sequence_no)`, `(employee_id, punch_time)`, `(device_id, punch_time)`.

| # | Endpoint | Method | URL | Permission |
|---|---|---|---|---|
| 7 | Add Manual Punch | POST | `/attendance/punches` | `attendance_punch:create` |
| 8 | List Punches | GET | `/attendance/punches` | `attendance_punch:read` |
| 9 | Get Day Punches | GET | `/attendance/days/{day_id}/punches` | `attendance_punch:read` |
| 10 | Employee Punch Timeline / History | GET | `/employees/{employee_id}/attendance/punches` | `attendance_punch:read` |

**7. Add Manual Punch** — `{ "employee_id", "punch_time", "punch_type", "latitude"?, "longitude"? }`.
Server sets `punch_source='manual_entry'`, `created_by=caller`, resolves `attendance_day_id` from the punch
date (creating the day row if absent), and assigns `sequence_no`.
- **Validation:** `punch_type` ∈ CHECK set; `punch_time` valid; employee exists/active in org.
- **Business rules:** punches are **append-only and immutable** — no update/delete endpoint. Adding a punch
  does **not** itself recompute the day summary (a service/job does). `is_valid` is managed only by the
  Approval regularization flow. `device_id` stays null for manual entries.
- **Success:** `201` → punch object. **Status:** 201, 404, 422.

**8. List Punches** — **Query:** `page`, `page_size`, `employee_id`, `attendance_day_id`, `date_from`/`date_to`,
`punch_type`, `punch_source`, `is_valid`, `device_id`, `sort_by` (`punch_time`), `sort_dir`. Data-scoped.
`200` paginated.

**9. Get Day Punches** — `200` → ordered punches for the day (`sequence_no`). `404 ATTENDANCE_DAY_NOT_FOUND`.

**10. Employee Punch Timeline** — `date_from`+`date_to` (or `date`). `200` → the employee's punches ordered by
`punch_time` (Punch History = same data). `404 EMPLOYEE_NOT_FOUND`.

---

## 6. Attendance Penalties (`/api/v1/attendance/penalties`) — feature key `attendance_penalty`

`attendance_penalties` fields: `id`, `org_id`, `employee_id`, `attendance_day_id` (FK attendance_days),
`penalty_type` (CHECK), `penalty_unit` (CHECK), `penalty_value` (Numeric(10,2) ≥0), `status` (CHECK
`active|waived`, default `active`), `applied_by` (FK users), `payroll_reference_id` (deferred, nullable),
`remarks`, `created_at`/`updated_at`, `is_deleted` (bool, default false). Indexes: `(employee_id, status)`,
`(attendance_day_id)`, `(payroll_reference_id)`.

| # | Endpoint | Method | URL | Permission |
|---|---|---|---|---|
| 11 | Apply Penalty | POST | `/attendance/penalties` | `attendance_penalty:create` |
| 12 | List Penalties | GET | `/attendance/penalties` | `attendance_penalty:read` |
| 13 | Get Penalty Details | GET | `/attendance/penalties/{penalty_id}` | `attendance_penalty:read` |
| 14 | Waive Penalty | POST | `/attendance/penalties/{penalty_id}/waive` | `attendance_penalty:edit` |
| 15 | Employee Penalty History | GET | `/employees/{employee_id}/attendance/penalties` | `attendance_penalty:read` |

**11. Apply Penalty** — `{ "employee_id", "attendance_day_id", "penalty_type", "penalty_unit", "penalty_value", "remarks"? }`.
Sets `applied_by=caller`, `status='active'`.
- **Validation:** `attendance_day_id` exists in org & belongs to `employee_id`; `penalty_type`/`penalty_unit`
  ∈ CHECK sets; `penalty_value` ≥ 0.
- **Success:** `201`. **Status:** 201, 404, 422.

**12. List Penalties** — **Query:** `page`, `page_size`, `employee_id`, `attendance_day_id`, `status`,
`penalty_type`, `date_from`/`date_to`, `include_deleted` (default false), `sort_by` (`created_at`), `sort_dir`.
Data-scoped. `200` paginated.

**13. Get Penalty Details** — `200`. `404 PENALTY_NOT_FOUND`.

**14. Waive Penalty** — sets `status='waived'` (`remarks?`). Idempotent; already-waived → `409
PENALTY_ALREADY_WAIVED` (or `200` no-op — implementation choice, documented as `409`). Waive **≠** delete
(`is_deleted` reserved). `200`; `404 PENALTY_NOT_FOUND`.

**15. Employee Penalty History** — `200` → the employee's penalties (active + waived; `is_deleted` excluded by
default). `404 EMPLOYEE_NOT_FOUND`.

> **Delete penalty:** `is_deleted` exists but deletion is reserved (waive is the normal path); a soft-delete
> endpoint under `attendance_penalty:delete` may be added if required — see §12 Q3.

---

## 7. Attendance Summaries (Dashboard) (`/api/v1/attendance/summary`) — feature key `attendance` (read)

Read-only aggregations computed over `attendance_days` for the caller's org (and data scope). One endpoint
returns **all** requested counts as fields (rather than one endpoint per count).

| # | Endpoint | Method | URL | Permission |
|---|---|---|---|---|
| 16 | Daily Summary | GET | `/attendance/summary/daily` | `attendance:read` |
| 17 | Monthly Summary | GET | `/attendance/summary/monthly` | `attendance:read` |

**16. Daily Summary** — **Query:** `date` (req), optional `branch_id`, `dept_id`, `shift_id`.
- **Response `data`:** `{ date, present_count, absent_count, half_day_count, leave_count, week_off_count,
  holiday_count, not_marked_count, late_count, early_exit_count, total_working_minutes, total_overtime_minutes,
  headcount }`.
  - `present_count`/`absent_count`/`half_day_count` ← `status`; `leave_count` ← `status='on_leave'`;
    `late_count` ← `late_minutes > 0`; `early_exit_count` ← `early_leaving_minutes > 0`;
    Working Hours Summary ← `SUM(total_working_minutes)`.
- `200`. **Status:** 200, 422.

**17. Monthly Summary** — **Query:** `month` (`YYYY-MM`, req), optional `employee_id`, `branch_id`, `dept_id`,
`shift_id`. Returns per-employee (or org-wide) monthly aggregates: the same count fields summed across the
month plus `days_present`, `days_absent`, `days_half`, `days_leave`, `total_working_minutes`,
`total_overtime_minutes`, `total_late_minutes`, `total_early_leaving_minutes`. `200`.

> These map the requested "Present Count / Absent Count / Late Count / Early Exit Count / Half Day Count /
> Leave Count / Working Hours Summary" to **fields of the summary responses** (all derived from
> `attendance_days`), not separate endpoints.

---

## 8. Attendance Reports (`/api/v1/attendance/reports`) — feature key `attendance` (read)

Read-only, computed over `attendance_days` joined (via the employee module) to branch/department/shift.
Date range required; wide spans paginate. Export is **not** included (see §12 Q1).

| # | Endpoint | Method | URL | Permission |
|---|---|---|---|---|
| 18 | Employee Attendance Report | GET | `/attendance/reports/employee` | `attendance:read` |
| 19 | Department Attendance Report | GET | `/attendance/reports/department` | `attendance:read` |
| 20 | Branch Attendance Report | GET | `/attendance/reports/branch` | `attendance:read` |
| 21 | Shift-wise Attendance Report | GET | `/attendance/reports/shift` | `attendance:read` |

- **18. Employee** — `employee_id` (req), `date_from`+`date_to` (or `month`). Per-day rows + totals for one
  employee. `404 EMPLOYEE_NOT_FOUND`.
- **19. Department** — `dept_id` (req) + date range. Aggregates per employee within the department (department
  membership resolved via the employee module). `404 DEPARTMENT_NOT_FOUND`.
- **20. Branch** — `branch_id` (req) + date range. Aggregates per employee within the branch.
  `404 BRANCH_NOT_FOUND`.
- **21. Shift-wise** — `shift_id` (req) + date range. Aggregates grouped by shift (`attendance_days.shift_id`).
  `404 SHIFT_NOT_FOUND`.
- All are **data-scoped** by branch/department access and return paginated summary rows + a `totals` block.

---

## 9. Business Rules (summary)

- **Tenant isolation:** every operation scoped to `org_id`; cross-org → `404` within scope.
- **Data scope:** all employee-related reads/reports filtered by branch/department access (super admin exempt).
- **One day per employee:** `(employee_id, attendance_date)` unique; manual create conflicts → override.
- **Manual mark/override** sets `source='manual'`, `marked_by`; may trigger recompute (service).
- **Punches immutable/append-only:** no edit/delete; `sequence_no` server-assigned; `attendance_day_id`
  resolved from punch date; manual punch does not itself recompute the day.
- **`is_regularized` / `is_valid`** are set only by the Approval regularization flow — read-only here.
- **Penalties:** `penalty_value ≥ 0`; enums from CHECK sets; waive sets `status='waived'` (≠ delete);
  `payroll_reference_id` populated only when consumed by Payroll (out of scope).
- **Summaries/reports** are read-only; counts derived strictly from `attendance_days` fields.

---

## 10. Permission Matrix

| Feature key | create | read | edit | delete |
|---|---|---|---|---|
| `attendance` | Mark/Create Attendance | List/Search, Get, Employee history, Calendar, Daily/Monthly summary, all Reports | Override Attendance | *(not exposed, §12 Q3)* |
| `attendance_punch` | Add Manual Punch | List, Day punches, Employee timeline | — (immutable) | — (immutable) |
| `attendance_penalty` | Apply Penalty | List, Get, Employee history | Waive Penalty | *(reserved, §12 Q3)* |

Super admins bypass feature checks; tenant isolation always applies; employee-related reads are data-scoped.

---

## 11. Error Handling & Security

**Error envelope** via `core/exceptions/handlers.py`. Module error codes (proposed, to be registered in
`attendance/exceptions.py`): `ATTENDANCE_DAY_NOT_FOUND`(404), `ATTENDANCE_DAY_EXISTS`(409),
`PUNCH_NOT_FOUND`(404), `PENALTY_NOT_FOUND`(404), `PENALTY_ALREADY_WAIVED`(409), `EMPLOYEE_NOT_FOUND`(404),
`SHIFT_NOT_FOUND`(404), `DEPARTMENT_NOT_FOUND`(404), `BRANCH_NOT_FOUND`(404), `INVALID_ENUM_VALUE`(422),
`VALIDATION_ERROR`(422), plus shared `AUTH_NOT_AUTHENTICATED`(401)/`AUTH_FORBIDDEN`(403).

**HTTP status codes used:** 200, 201, 400, 401, 403, 404, 409, 422.

**Security considerations:** every route enforces `require_permission` + tenant scope + branch/department data
scope on employee reads; manual marks, punches, and penalty apply/waive are recorded in the Activity Log
(actor, org, before/after); geo coordinates and device data are returned only to permitted roles; timestamps
timezone-aware; no secrets/PII in logs; rate limiting per the security baseline on manual-write and
summary/report endpoints.

---

## 12. Open Questions

1. **Export (Q1) — excluded.** "Export Attendance Report" is not specified here; CSV/Excel export belongs to
   the shared report/export infrastructure (per architecture). Confirm which module owns attendance export.
2. **Cross-module report placement (Q2).** Department/Branch/Shift reports join `attendance_days` to employee
   branch/department membership via the employee module. Confirm this is acceptable within the attendance
   module (vs. the generic Reports module) — the summaries/reports here are attendance-scoped reads by your
   decision.
3. **Delete semantics (Q3).** Attendance-day delete is not exposed; penalty delete (`is_deleted`) is reserved
   (waive is the path). Confirm whether soft-delete endpoints are required for either.
4. **Feature-key catalog (Q4).** `permissions.py` is a stub; confirm the proposed keys
   (`attendance`/`attendance_punch`/`attendance_penalty`).
5. **Manual mark & recompute interaction (Q5).** Manual create/override and manual punch may need to trigger
   a summary recompute. That is a service/background-job behavior, intentionally outside this API contract —
   confirm the expected trigger (synchronous on write vs async job).
6. **`on_leave` linkage (Q6).** Marking `status='on_leave'` should reference an approved `leave_id`
   (leave_requests). Confirm whether the attendance API validates/looks up the leave, or whether that link is
   set only by the Leave/Approval flow.
7. **Envelope key names (Q7).** `shared/schemas/response.py` is a stub; final envelope field names must match
   once implemented (same open item as prior contracts).
