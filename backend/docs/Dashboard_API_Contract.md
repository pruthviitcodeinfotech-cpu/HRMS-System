# Dashboard API Contract

> Module: `app/modules/dashboard`
> API Version: `v1` — all routes under `API_V1_PREFIX` (`/api/v1`).
> Status: **Contract only** (no FastAPI/SQLAlchemy/Pydantic/service/repository code).
> Sources of truth: `docs/architecture.md` (Backend Architecture), all module migrations `0001`–`0016`, the
> approved module API Contracts, and the module models.

**Read-only, owns no tables.** The Dashboard aggregates and presents data from Employee, Attendance, Leave,
Approval, Payroll, Settlement, Hardware, Notification, and Activity Log. **No Create/Update/Delete** — every
endpoint is `GET`. It does not duplicate business APIs; it only computes read projections over existing
tables.

> **Scope notes (schema-grounded).**
> - **Hardware "Failed Synchronizations"** is **not supported** — there is no sync-log table (only
>   `biometric_devices.last_sync_at`). Omitted; see §8 Q1.
> - **Settlement "Pending/Completed Settlements"** is reframed to the real schema (loans/advances + arrears):
>   *pending* = active loans/advances + outstanding arrears; *completed* = closed loans/advances. There is no
>   F&F-settlement entity (§8 Q2).

---

## 1. Module Overview

### Purpose
Provide KPI cards, per-module summaries, and chart series for the admin dashboard, computed live (with
caching) from the owning modules' tables.

### Dependencies (read-only sources)
| Source module | Tables read | Widgets/charts |
|---|---|---|
| Employee | `employees`, `branches`, `departments`, `designations` | Total/Active/New employees, distribution, growth |
| Attendance | `attendance_days` | Present/Absent/Late/Early today, attendance trend, dept/branch-wise |
| Leave | `leave_requests` | Requests/Pending/Approved/Rejected, leave trend |
| Approval | `approval_requests` | Pending approvals, summary, recent |
| Payroll | `payroll_salary_cycles`, `finalized_payroll_runs`, `payroll_computed_rows` | Current cycle, status, summary, trend |
| Settlement | `employee_loans_advances`, `employee_arrears` | Active/closed loans-advances, outstanding arrears |
| Hardware | `biometric_devices` | Online/Offline devices, last sync |
| Notification | `notification_recipients` | Unread, recent |
| Activity Log | `activity_logs` | Recent activity feed |
| Foundation | `core/dependencies/auth.py`, tenant middleware, `rbac` (data scope), `core/cache/redis` | auth, org scope, data scope, caching |

### Module boundaries
- Read-only; no writes; no business logic beyond aggregation/projection.
- Every widget respects the **source module's read permission** and **branch/department data scope** (§2).

---

## 2. Authorization & Data Scope

All endpoints require `Authorization: Bearer <access_token>`. Super admins bypass feature checks; tenant
isolation (`org_id`) always applies.

- **Access:** `dashboard:read` grants the dashboard surface. Each **widget's data** is additionally gated by
  the corresponding **source-module read permission** (e.g. the payroll widget requires `payroll_record:read`,
  the leave widget `leave_request:read`, devices `device:read`, notifications = self). Widgets the caller
  cannot read are **omitted** (not errored).
- **Data scope:** employee-derived metrics (attendance, leave, employee counts, dept/branch charts) are
  filtered by the caller's `user_branch_access` / `user_department_access` (super admin exempt). Counts
  therefore reflect the caller's visible scope.

Proposed feature key (register in `core/security/permissions.py` — §8 Q4): `dashboard` (read-only).

---

## 3. Request & Response Standards

Reuses the shared envelope (`data`/`error`/`meta.request_id`). BIGINT integer IDs; dates `YYYY-MM-DD`;
timezone-aware timestamps; counts are integers; money as decimals. Chart series return
`{ labels: [...], series: [{ name, points: [...] }] }`.

**Common query parameters:** `date` (single-day metrics, default = today, org timezone), `date_from`/`date_to`
or `period` (`today|week|month|quarter|year`) for trends, `interval` (`day|week|month`) for charts,
`branch_id`, `dept_id` (within data scope). Invalid params → `422`.

Common omitted errors: `401 AUTH_NOT_AUTHENTICATED`, `403 AUTH_FORBIDDEN`, `422 VALIDATION_ERROR`.

---

## 4. Dashboard Overview (`/api/v1/dashboard`) — feature key `dashboard`

| # | Endpoint | Method | URL | Purpose |
|---|---|---|---|---|
| 1 | Dashboard Summary | GET | `/dashboard/summary` | Headline KPIs across all permitted modules |
| 2 | Dashboard Widgets | GET | `/dashboard/widgets` | Metadata: which widgets the caller can see |
| 3 | Dashboard KPIs | GET | `/dashboard/kpis` | The KPI number set (see §KPI List) |
| 4 | Dashboard Statistics | GET | `/dashboard/statistics` | Broader per-module stat blocks |

- **1. Summary** — `200` → `{ employees:{...}, attendance:{...}, leave:{...}, approvals:{...}, payroll:{...}, devices:{...}, notifications:{...} }` — only blocks the caller may read, each scoped. Cacheable.
- **2. Widgets** — `200` → `[{ widget_key, title, permitted: bool, source_module }]` — drives the UI layout.
- **3. KPIs** — `200` → the flat KPI map (§KPI List). **4. Statistics** — richer breakdowns (distributions, ratios).

---

## 5. Per-Module Dashboards (`/api/v1/dashboard/*`) — feature key `dashboard` + source read

Each returns all that module's metrics in one response (avoids many tiny endpoints).

| # | Endpoint | Method | URL | Metrics (fields) |
|---|---|---|---|---|
| 5 | Employee Dashboard | GET | `/dashboard/employees` | `total_employees`, `active_employees`, `inactive_employees`, `new_employees` (joined in period), `distribution` by `department`/`branch`/`designation`/`employment_status` |
| 6 | Attendance Dashboard | GET | `/dashboard/attendance` | `present_today`, `absent_today`, `half_day_today`, `on_leave_today`, `late_arrivals` (`late_minutes>0`), `early_exits` (`early_leaving_minutes>0`), `not_marked`, `trend` (per-day) |
| 7 | Leave Dashboard | GET | `/dashboard/leave` | `total_requests`, `pending`, `approved`, `rejected` (by `leave_requests.status`), optional by-type breakdown |
| 8 | Approval Dashboard | GET | `/dashboard/approvals` | `pending_approvals`, `by_request_type` (attendance/leave/login_reset), `approved_recent`, `rejected_recent`, `recent` list |
| 9 | Payroll Dashboard | GET | `/dashboard/payroll` | `current_cycle` (latest `payroll_salary_cycles`, `is_finalized`), `status` (finalized/pending), `finalized_amount`, `payment_status` breakdown, `headcount` |
| 10 | Settlement Dashboard | GET | `/dashboard/settlements` | `active_loans_advances`, `closed_loans_advances`, `total_outstanding_loans_advances`, `total_outstanding_arrears` (reframed — §8 Q2) |
| 11 | Hardware Dashboard | GET | `/dashboard/devices` | `online_devices`, `offline_devices`, `disabled_devices`, `maintenance_devices`, `last_device_sync` (max `last_sync_at`) |
| 12 | Notification Dashboard | GET | `/dashboard/notifications` | `unread_count` (caller's `read_at IS NULL`), `recent` (caller's latest) |

- **6. Attendance** — "today" uses `attendance_date = :date`; `trend` groups `attendance_days` by date over
  `period`. Data-scoped by branch/dept.
- **8. Approval** — `pending` = `approval_requests.status='pending'` within the caller's approval scope;
  `recent` = latest decided (`reviewed_at desc`).
- **10. Settlement** — `active`/`closed` from `employee_loans_advances.status`; arrears from
  `employee_arrears.outstanding_arrears`. **No F&F settlement metric.**
- **11. Hardware** — counts by `biometric_devices.status`; `last_device_sync` = `MAX(last_sync_at)`.
  **"Failed Synchronizations" is not available** (no sync-log — §8 Q1).
- **12. Notification** — self-scoped (the caller's own recipient rows).
- Each `200`; unreadable modules omitted from Summary or return `403` on the dedicated endpoint (per source
  permission).

---

## 6. Charts (`/api/v1/dashboard/charts/*`) — feature key `dashboard` + source read

Only charts backed by existing tables are included.

| # | Endpoint | Method | URL | Source / grouping |
|---|---|---|---|---|
| 13 | Attendance Trend | GET | `/dashboard/charts/attendance-trend` | `attendance_days` by date; series present/absent/late/etc. |
| 14 | Employee Growth | GET | `/dashboard/charts/employee-growth` | `employees.date_of_joining` cumulative by month |
| 15 | Leave Trend | GET | `/dashboard/charts/leave-trend` | `leave_requests` by `applied_on`/period, by status |
| 16 | Payroll Trend | GET | `/dashboard/charts/payroll-trend` | `finalized_payroll_runs.finalized_amount` by cycle |
| 17 | Department-wise Attendance | GET | `/dashboard/charts/department-attendance` | `attendance_days` grouped by employee `dept_id` |
| 18 | Branch-wise Attendance | GET | `/dashboard/charts/branch-attendance` | `attendance_days` grouped by employee `master_branch_id` |

- **Query:** `date_from`/`date_to` or `period`, `interval` (`day|week|month`), `branch_id`/`dept_id`.
- **Response:** `{ labels: [...], series: [{ name, points: [numbers] }], generated_at }`. Data-scoped.
- Wide ranges are bounded/aggregated server-side (§7). `200`; `422` on bad range/interval.

---

## 7. Refresh, Aggregation, Caching & Performance

### Dashboard Refresh Strategy
- Pull-based: clients fetch/poll; responses include `generated_at` and (when cached) a freshness hint.
  Real-time push (WebSocket) for volatile counters is a delivery concern **out of scope** (§8 Q3).
- Suggested client refresh: KPIs/summary ~60s; charts on demand / on filter change.

### Data Aggregation Rules
- All aggregates are **org-scoped** and **branch/department data-scoped** to the caller.
- Counts exclude soft-deleted rows (`is_deleted`/`deleted_at`) and respect status CHECK sets.
- "Today" = `attendance_date`/`log_date` = the org-timezone current date; trends group by the requested
  `interval`; distributions group by dept/branch/designation/status.
- Money/decimals summed at source precision; empty groups return `0`, not `null`.

### Caching Strategy (Redis)
- Per architecture cache rules: keys include **environment + module + org_id + caller-scope + widget +
  period/interval** (permission-sensitive data includes the scope in the key). TTL from config/module
  constants (e.g. summary/KPIs ~60–300s; charts ~300s).
- Caches are **read-through**; invalidation is TTL-based (and/or event-based when a source mutation occurs).
  Redis outage degrades to direct queries for non-critical reads.

### Performance Considerations
- Leverages existing indexes: `attendance_days (org_id, attendance_date)`, `approval_requests (org_id,
  status[, request_type])`, `leave_requests (employee_id, status)` / `(leave_type_id, status)`,
  `biometric_devices (org_id, status)`, `notification_recipients (org_id, user_id, read_at)`,
  `activity_logs (org_id, logged_at desc)`.
- Bounded date ranges; server-side aggregation (no row dumps); "recent" lists are limited/paginated;
  heavy widgets cached; expensive cross-module summaries assembled per-widget so a slow source doesn't block
  others.

---

## KPI List
`total_employees`, `active_employees`, `new_employees`, `present_today`, `absent_today`, `late_arrivals`,
`early_exits`, `on_leave_today`, `pending_leaves`, `pending_approvals`, `current_payroll_status`,
`total_outstanding_loans_advances`, `total_outstanding_arrears`, `online_devices`, `offline_devices`,
`unread_notifications`.

## Widget List
Overview: **Summary**, **KPIs**, **Statistics**, **Widgets metadata**. Cards: **Employee**, **Attendance**,
**Leave**, **Approval**, **Payroll**, **Settlement**, **Hardware**, **Notification**, **Recent Activity**
(from `activity_logs`). Charts: **Attendance Trend**, **Employee Growth**, **Leave Trend**, **Payroll Trend**,
**Department-wise Attendance**, **Branch-wise Attendance**.

## Permission Matrix
| Feature key | read |
|---|---|
| `dashboard` | All dashboard/summary/KPI/statistics/per-module/chart GETs — **each widget additionally gated by its source-module read permission and branch/department data scope** |

Super admins bypass feature checks; tenant isolation always applies; no write operations exist.

## Error Handling
`VALIDATION_ERROR`(422) on bad params; `403 AUTH_FORBIDDEN` on a dedicated widget the caller can't read;
shared `AUTH_NOT_AUTHENTICATED`(401). **Status codes:** 200, 400, 401, 403, 422. (No 201/204 — read-only.)

---

## 8. Open Questions
1. **Hardware Failed Synchronizations (Q1) — NOT supported.** No sync-log/failed-sync table exists (only
   `last_sync_at`). Omitted. Confirm whether a sync-history table is planned (Hardware §Open Questions).
2. **Settlement dashboard mapping (Q2).** Reframed to loans/advances (active/closed) + outstanding arrears —
   there is no F&F-settlement entity. Confirm the intended settlement KPIs.
3. **Real-time refresh (Q3).** Pull/poll + caching is specified; confirm whether any counters need WebSocket
   push (a delivery concern outside this read contract).
4. **Feature-key & per-widget gating (Q4).** `permissions.py` is a stub; confirm the `dashboard` key and the
   rule that each widget is additionally gated by its source-module read permission.
5. **Materialization (Q5).** All aggregates are computed live + cached; confirm whether any need
   precomputed/materialized snapshots (a background job) for scale.
6. **Envelope key names (Q6).** `shared/schemas/response.py` is a stub; final envelope field names must match
   once implemented (same open item as prior contracts).
