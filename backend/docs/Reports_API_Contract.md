# Reports API Contract

> Module: `app/modules/reports`
> API Version: `v1` — all routes under `API_V1_PREFIX` (`/api/v1`).
> Status: **Contract only** (no FastAPI/SQLAlchemy/Pydantic/service/repository code).
> Sources of truth: `docs/architecture.md` (Backend Architecture), all module migrations `0001`–`0016`, the
> approved module API Contracts, and the module models.

**Read-only, owns no tables.** Reports reads existing module tables and returns tabular/summary projections
with optional file export. **No Create/Update/Delete** — every endpoint is `GET` (export jobs excepted, which
are read-derived). It does not duplicate business APIs.

> **Scope notes (apply prior approved decisions).**
> - **Salary Component Report — NOT supported** (no salary-components schema; Payroll contract). Omitted.
> - **Full & Final Settlement Report — reframed** to loans/advances + arrears (no F&F entity; Settlement
>   contract).
> - **Attendance Import Report — NOT supported** (no import-log table; Hardware contract). Omitted.
> - **Login History Report — NOT supported** (`activity_logs` is mutation-only; no login events; Audit
>   contract). Omitted.
> - **Device Sync Report** = `last_sync_at` snapshot only (no sync-history). **Security Event Report** =
>   approximate `activity_logs` filter. See §8.

---

## 1. Module Overview

### Purpose
Generate read-only operational/compliance reports across all HRMS modules, with filtering, sorting,
pagination, and export to CSV/Excel/PDF.

### Dependencies (read-only sources)
| Source | Tables read | Reports |
|---|---|---|
| Employee/Org | `employees`, `organizations`, `branches`, `departments`, `designations`, `employee_status_history` | Employee, Organization reports |
| Attendance | `attendance_days`, `attendance_punches` | Attendance reports |
| Leave | `leave_requests`, `employee_leave_balances`, `leave_balance_adjustments` | Leave reports |
| Approval | `approval_requests` | Approval reports |
| Payroll | `payroll_computed_rows`, `finalized_payroll_runs`, `payroll_groups` | Payroll reports |
| Settlement | `employee_loans_advances`, `loan_advance_transactions`, `employee_arrears`, `arrears_transactions` | Settlement reports |
| Hardware | `biometric_devices` | Device reports |
| Notification | `notifications`, `notification_recipients` | Notification reports |
| Activity Log | `activity_logs` | Audit reports |
| Foundation | auth deps, tenant middleware, `rbac` (data scope), `core/cache/redis`, `infrastructure/storage` (export files) | auth, scope, caching, export |

### Module boundaries
- Read-only; no writes to business tables. Async export jobs write only to Redis/infra (no DB table exists).
- Every report respects the **source module's read permission** and **branch/department data scope**.

---

## 2. Authorization & Data Scope

All endpoints require `Authorization: Bearer <access_token>`. Super admins bypass feature checks; tenant
isolation (`org_id`) always applies.

- **Access:** `reports:read` grants the reports surface. Each report is **additionally gated** by the relevant
  **source-module read permission** (e.g. Payroll reports → `payroll_record:read`; Attendance → `attendance:read`;
  Audit → `audit:read`).
- **Data scope:** employee-derived reports are filtered by the caller's `user_branch_access` /
  `user_department_access` (super admin exempt).

Proposed feature key (register in `core/security/permissions.py` — §8 Q4): `reports` (read-only).

---

## 3. Common Standards

### Common Filters
`date_from`/`date_to` (or `period` = `today|week|month|quarter|year`, or `month=YYYY-MM`), `branch_id`,
`dept_id`, `designation_id`, `employee_id`, plus report-specific status filters. All within the caller's data
scope. Invalid filter/sort field → `422`.

### Date Range Handling
Time-based reports require a bounded range (a **max span**, e.g. 12 months, enforced → `422 RANGE_TOO_LARGE`);
if omitted, a sensible default period applies. Dates are org-timezone `YYYY-MM-DD`.

### Sorting & Pagination
`sort_by` (allowlisted per report), `sort_dir` (`asc|desc`); `page` (≥1), `page_size` (bounded). Tabular
responses: `{ items:[...], page, page_size, total, generated_at }`. Summary responses: aggregate objects.

### Export Rules
- Query `format` = `json` (default) | `csv` | `excel` | `pdf`.
- **Bounded** result sets (≤ a configured row threshold) stream **synchronously** → `200` with the file
  (`Content-Disposition: attachment`). **Large** exports return an **async job** → `202 Accepted` with
  `{ export_job_id, status: "pending" }`.
- Poll job status: **`GET /reports/exports/{export_job_id}`** → `{ status: pending|processing|completed|failed, download_url?, expires_at? }`.
  Job state and the rendered file live in **Redis + storage** (no DB export table exists — §8 Q3).
- **PDF** is offered only for **formatted** reports (payslips, registers, summaries); tabular data reports
  offer CSV/Excel (see **Export Matrix**).

### Response envelope
Shared envelope for JSON (`data`/`error`/`meta.request_id`); file responses are raw streams with headers.

Common omitted errors: `401 AUTH_NOT_AUTHENTICATED`, `403 AUTH_FORBIDDEN`, `422 VALIDATION_ERROR`.

---

## 4. Report Endpoints (all `GET`, read-only)

### 4.1 Employee Reports (`/api/v1/reports/employees`) — `employee:read`
| # | Report | URL | Key columns / filters |
|---|---|---|---|
| 1 | Employee Master | `/reports/employees/master` | code, name, mobile, email, branch, dept, designation, type, DOJ, status |
| 2 | Employee Joining | `/reports/employees/joining` | filter `date_of_joining` range; joiners per period |
| 3 | Employee Status | `/reports/employees/status` | `employment_status` + `employee_status_history` (transitions) |
| 4 | Department-wise | `/reports/employees/by-department` | grouped by `dept_id` (count + roster) |
| 5 | Designation-wise | `/reports/employees/by-designation` | grouped by `designation_id` |
| 6 | Branch-wise | `/reports/employees/by-branch` | grouped by `master_branch_id` |

### 4.2 Attendance Reports (`/api/v1/reports/attendance`) — `attendance:read`
| # | Report | URL | Key columns / derivation |
|---|---|---|---|
| 7 | Daily Attendance | `/reports/attendance/daily` | `attendance_date=:date`; status/punches per employee |
| 8 | Monthly Attendance | `/reports/attendance/monthly` | `month=YYYY-MM`; per-employee day grid + totals |
| 9 | Employee Attendance | `/reports/attendance/employee` | `employee_id` + range |
| 10 | Late Coming | `/reports/attendance/late-coming` | `late_minutes > 0` |
| 11 | Early Going | `/reports/attendance/early-going` | `early_leaving_minutes > 0` |
| 12 | Missing Punch | `/reports/attendance/missing-punch` | **derived**: `first_punch_in` present & `last_punch_out` NULL (or odd punch count) |
| 13 | Overtime | `/reports/attendance/overtime` | `overtime_minutes > 0` |
| 14 | Attendance Summary | `/reports/attendance/summary` | counts by status + working/OT minutes over range |

### 4.3 Leave Reports (`/api/v1/reports/leave`) — `leave_request:read` / `leave_balance:read`
| # | Report | URL | Source |
|---|---|---|---|
| 15 | Leave Balance | `/reports/leave/balance` | `employee_leave_balances` (opening/allocated/used/closing) per type/cycle |
| 16 | Leave Request | `/reports/leave/requests` | `leave_requests` (dates, type, status) |
| 17 | Leave Approval | `/reports/leave/approvals` | `leave_requests` where status ∈ approved/rejected + `reviewed_by` |
| 18 | Leave Summary | `/reports/leave/summary` | counts by status/type over range |

### 4.4 Approval Reports (`/api/v1/reports/approvals`) — `approval:read`
| # | Report | URL | Source / computation |
|---|---|---|---|
| 19 | Pending Approval | `/reports/approvals/pending` | `approval_requests.status='pending'` |
| 20 | Approval History | `/reports/approvals/history` | decided requests (approved/rejected) |
| 21 | Approval Performance | `/reports/approvals/performance` | **computed**: time-to-decision (`reviewed_at − requested_at`), throughput by `reviewed_by` |

### 4.5 Payroll Reports (`/api/v1/reports/payroll`) — `payroll_record:read`
| # | Report | URL | Source |
|---|---|---|---|
| 22 | Payroll Register | `/reports/payroll/register` | `payroll_computed_rows` per group/cycle (all amounts) |
| 23 | Salary Register | `/reports/payroll/salary-register` | computed rows, salary-focused columns |
| 24 | Payroll Summary | `/reports/payroll/summary` | totals (gross, deductions, to_pay, headcount) per cycle |
| 25 | Payslip Report | `/reports/payroll/payslips` | rendered computed rows (PDF) |
| — | Salary Component | *(omitted)* | **NOT supported** — no components schema (§8 Q1) |

### 4.6 Settlement Reports (`/api/v1/reports/settlements`) — `loan_advance:read` / `arrears:read`
| # | Report | URL | Source (reframed) |
|---|---|---|---|
| 26 | Settlement Ledger (Loans/Advances & Arrears) | `/reports/settlements/ledger` | `loan_advance_transactions` + `arrears_transactions` |
| 27 | Settlement Summary | `/reports/settlements/summary` | active/closed loans-advances + outstanding arrears |
| — | Full & Final Settlement | *(reframed)* | **No F&F entity** — the above is the supported form (§8 Q2) |

### 4.7 Hardware Reports (`/api/v1/reports/devices`) — `device:read`
| # | Report | URL | Source |
|---|---|---|---|
| 28 | Device Status | `/reports/devices/status` | `biometric_devices.status`, branch, last_seen |
| 29 | Device Health | `/reports/devices/health` | status, firmware/software, stats, last_seen |
| 30 | Device Sync | `/reports/devices/sync` | `last_sync_at` **snapshot only** (no sync history — §8 Q1) |
| — | Attendance Import | *(omitted)* | **NOT supported** — no import-log table (§8 Q1) |

### 4.8 Notification Reports (`/api/v1/reports/notifications`) — `notification:read`
| # | Report | URL | Source |
|---|---|---|---|
| 31 | Notification Delivery | `/reports/notifications/delivery` | `notification_recipients.delivered_at` |
| 32 | Notification Read | `/reports/notifications/read` | `read_at` (read/unread) |
| 33 | Notification Summary | `/reports/notifications/summary` | counts (sent/delivered/read) per period/type |

### 4.9 Activity Log / Audit Reports (`/api/v1/reports/audit`) — `audit:read`
| # | Report | URL | Source |
|---|---|---|---|
| 34 | User Activity | `/reports/audit/user-activity` | `activity_logs` by `performed_by_user_id` |
| 35 | Audit Trail | `/reports/audit/trail` | `activity_logs` (module/action/date filters) |
| 36 | Security Event | `/reports/audit/security-events` | **approximate** `activity_logs` filter (module rbac/user + action Assign/Update) |
| — | Login History | *(omitted)* | **NOT supported** — no login events (§8 Q1) |

### 4.10 Organization Reports (`/api/v1/reports/organization`) — `employee:read`
| # | Report | URL | Source |
|---|---|---|---|
| 37 | Branch Summary | `/reports/organization/branch-summary` | employees/headcount per `branch` |
| 38 | Department Summary | `/reports/organization/department-summary` | headcount per `department` |
| 39 | Workforce Summary | `/reports/organization/workforce-summary` | org totals + distribution (status/type/branch/dept) |

### 4.11 Export Jobs
| # | Endpoint | Method | URL | Purpose |
|---|---|---|---|---|
| 40 | Get Export Job Status | GET | `/reports/exports/{export_job_id}` | Poll async export (status + download_url) |

Every report endpoint accepts `?format=json|csv|excel|pdf` (per the Export Matrix) and the common
filter/sort/pagination params. Each returns `200` (JSON or synchronous file) or `202` (async export job);
errors `403` (missing source permission), `422` (bad params / range too large), `404 EXPORT_JOB_NOT_FOUND`.

---

## 5. Report Inventory
- **Employee (6):** Master, Joining, Status, Dept-wise, Designation-wise, Branch-wise
- **Attendance (8):** Daily, Monthly, Employee, Late Coming, Early Going, Missing Punch, Overtime, Summary
- **Leave (4):** Balance, Request, Approval, Summary
- **Approval (3):** Pending, History, Performance
- **Payroll (4):** Register, Salary Register, Summary, Payslip *(Salary Component omitted)*
- **Settlement (2):** Ledger, Summary *(F&F reframed)*
- **Hardware (3):** Status, Health, Sync *(Attendance Import omitted)*
- **Notification (3):** Delivery, Read, Summary
- **Audit (3):** User Activity, Audit Trail, Security Event *(Login History omitted)*
- **Organization (3):** Branch Summary, Department Summary, Workforce Summary
- **Total: 39 reports** + 1 export-status endpoint.

## 6. Export Matrix
| Report category | CSV | Excel | PDF |
|---|---|---|---|
| Employee, Attendance, Leave, Approval, Notification, Audit, Organization (tabular) | ✅ | ✅ | ➖ (summary/formatted variants only) |
| Payroll Register / Salary Register / Summary | ✅ | ✅ | ✅ |
| Payslip Report | ➖ | ➖ | ✅ |
| Settlement Ledger / Summary | ✅ | ✅ | ✅ (statement) |
| Device Status / Health / Sync | ✅ | ✅ | ➖ |

`json` is always available (default). Large exports run as async jobs (§3 Export Rules).

## 7. Permission Matrix
| Feature key | read |
|---|---|
| `reports` | All report GETs + export — **each report additionally gated by its source-module read permission and branch/department data scope** |

Super admins bypass feature checks; tenant isolation always applies; no write operations exist.

### Caching Strategy
Redis read-through: keys include environment + module + `org_id` + caller-scope + report + params; TTL from
config (short for volatile reports). Large/export results are not long-cached; rendered export files are stored
with a short expiry (`download_url`/`expires_at`).

### Performance Considerations
Leverages existing indexes (`attendance_days (org_id, attendance_date)`, `approval_requests (org_id, status)`,
`payroll_computed_rows (payroll_group_id, cycle_from, cycle_to)`, `activity_logs (org_id, logged_at desc)`,
`biometric_devices (org_id, status)`, etc.); mandatory bounded date ranges; server-side aggregation; pagination
for tabular reports; **async export** for large result sets so requests never block; no row-by-row rendering
for summaries.

### Error Handling
`VALIDATION_ERROR`(422), `RANGE_TOO_LARGE`(422), `EXPORT_JOB_NOT_FOUND`(404), `UNSUPPORTED_FORMAT`(422),
plus shared `AUTH_NOT_AUTHENTICATED`(401)/`AUTH_FORBIDDEN`(403). **Status codes:** 200, 202, 400, 401, 403,
404, 422.

---

## 8. Open Questions
1. **Unsupported reports (Q1).** Salary Component (no components schema), Attendance Import (no import-log),
   and Login History (no login events) are **omitted**; Device Sync is `last_sync_at` snapshot only; Security
   Event is an approximate `activity_logs` filter. These mirror the approved prior contracts. Confirm whether
   any need new schema.
2. **Settlement report scope (Q2).** Reframed to loans/advances + arrears (no F&F entity). Confirm the
   intended settlement report columns.
3. **Export infrastructure (Q3).** Async export job state + rendered files live in Redis/storage (no DB export
   table exists). Confirm whether an export-history/audit table is required (would need new schema) and the
   file retention policy.
4. **Feature-key & per-report gating (Q4).** `permissions.py` is a stub; confirm the `reports` key and that
   each report is additionally gated by its source-module read permission.
5. **Row/range thresholds (Q5).** Confirm the sync-vs-async row threshold, the max date-range span, and
   default `page_size` per report family.
6. **Envelope key names (Q6).** `shared/schemas/response.py` is a stub; final envelope field names must match
   once implemented (same open item as prior contracts).
