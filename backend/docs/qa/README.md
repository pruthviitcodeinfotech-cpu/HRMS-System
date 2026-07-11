# HRMS Backend — API Test Case Specification

A production QA specification covering all **16 modules / 361 endpoints** of the HRMS
backend. Written to be executed by a QA engineer or automated by a test harness, without
needing to read the source.

## Suites

| Suite | Modules | Endpoints | Cases |
|---|---|---|---|
| [Auth · RBAC · Organization](test-cases-auth-rbac-org.md) | Authentication, User Management & RBAC, Organization/Branch/Department/Designation | 73 | 264 |
| [Employee · Shift · Attendance](test-cases-employee-shift-attendance.md) | Employee Management, Shift Management, Attendance Management | 86 | 345 |
| [Leave · Approval · Payroll · Settlement](test-cases-leave-approval-payroll-settlement.md) | The money and workflow core | 98 | 350 |
| [Hardware · Notification · Settings · Audit · Dashboard · Reports](test-cases-hardware-notif-settings-audit-dashboard-reports.md) | Devices, notifications, settings, audit trail, analytics | 104 | 300 |
| [Cross-cutting & E2E](test-cases-cross-cutting.md) | The seams: workflows, security, tenancy, concurrency, resilience, jobs, ops, schema | — | 125 |
| **Total** | **16 modules** | **361** | **1,384** |

**Coverage: 361 / 361 endpoints (100%).** Every endpoint path and every `error.code` cited in these
documents was mechanically checked to exist in the codebase, and case IDs are globally unique.
Priorities: 451 P0 · 430 P1 · 284 P2 · 10 P3.

## Defects found while writing these cases

Grounding the cases in the source surfaced real bugs. Each was **verified against the code** before being
listed; claims that did not survive checking were dropped rather than shipped. Cases marked *"fails today"*
are written against the **correct** expectation — they are open findings, not flaky tests.

| # | Sev | Location | Defect |
|---|---|---|---|
| 1 | **P0** | `rbac/service.py` — `assign_branch_access`, `assign_department_access`, `replace_*` | The *user* is tenant-scoped via `_get_active_user(org_id, user_id)`, but `branch_id` / `department_id` go straight into the insert with **only an FK** to catch them. An ORG_A admin can grant an ORG_A user data scope over an **ORG_B branch**. `branches.org_id` exists, so the check is possible — it is simply never made. (TC-RBAC-112) |
| 2 | **P0** | `attendance/service.py::lock_attendance` | **The lock is a no-op that reports success.** Its own docstring says *"no-op as there is no DB backing for locks"*: there is no `attendance_locks` table, `is_locked` is never persisted, and the method writes an audit row reading *"Attendance Lock Triggered"* and returns `True`. Operators believe attendance is frozen after payroll; the days stay editable and the audit trail asserts the opposite. (TC-ATT-088) |
| 3 | **P0** | `settings/schemas.py::OrgSettingsResponse` | `pass_code` has a masking validator; **`sync_code` does not** and is returned in plaintext to anyone with `settings:read`. The device sync code is a credential. (TC-SET-005) |
| 4 | **P1** | `reports/service.py` — `get_export_job_status`, `get_export_file` | Both accept `org_id` and **never use it**. The Redis keys are `export_job:{job_id}` / `export_file:{job_id}` with no tenant component, and the payload stores no `org_id`. Any org holding `reports:read` can poll and download another tenant's completed export — including a payroll salary register. **Exploitability:** the id is `uuid4().hex` (128 bits), so it cannot be brute-forced; it must *leak* (access logs, referrer, browser history, a forwarded `download_url`). This is genuine broken access control — the only thing separating Org B from Org A's salary register is the secrecy of a URL. One-line fix: persist `org_id` in the payload and compare it on read. (TC-RPT-039/040) |
| 5 | **P1** | `reports/router.py::download_export_file` | Guarded only by `reports:read` — it never re-checks the **source-module** permission of the report that produced the file, so a user correctly 403'd on `/reports/payroll/register` can still download its export. Same root cause as #4: the endpoint performs no ownership check at all. (TC-RPT-041) |
| 6 | P2 | Employee / Shift modules | **Error-code drift.** `EMPLOYEE_NOT_FOUND` is defined but never raised — Employee emits a generic `not_found` while *Shift* and *Attendance* emit `EMPLOYEE_NOT_FOUND` for the same condition: two codes for one error. Same pattern for `SHIFT_NOT_FOUND` and `ShiftInUseException`. The cases assert what the API **actually emits**; Appendix A records the drift. |
| 7 | P2 | `notifications`, `hardware` | `ALREADY_ASSIGNED` is defined but never raised (`assign_recipients` returns 200 with a per-item status). Device serial uniqueness is **global, not per-org** — Org B gets a 409 on an Org A serial, a cross-tenant existence oracle. |

One reported defect was **refuted** and removed: `POST /rights-templates` *does* validate feature keys
(`create_role` calls `_require_known_feature_keys`), and `clone_role` copies an already-validated template.
That test case had been written to expect the bug, and would have failed against correct code.

## Column definitions

Every case is one table row:

| Column | Meaning |
|---|---|
| **ID** | Stable identifier — `TC-<MODULE>-<NNN>`. Cite it in bug reports. |
| **Module / API** | The module and, where relevant, the endpoint under test |
| **Test Scenario** | What is being proven, in one line |
| **Preconditions** | The fixture state required before the request |
| **Request / Input** | The actual method, path and body — executable as written |
| **Expected Result** | The response shape and the **exact error code** |
| **HTTP** | The exact status code |
| **Database Verification** | The SQL assertion on the resulting state. `n/a (read-only)` where nothing is written |
| **Priority** | P0 → P3 (below) |

### The Database Verification column is the point

An API test that only checks a status code proves the endpoint *replied*, not that it
*worked*. Several defects in this codebase returned a perfectly good `200` while writing
nothing, writing twice, or writing to the wrong tenant. Every case that mutates state
therefore asserts against the database, and every case that *rejects* a mutation asserts
that **nothing was written**.

### Priorities

| | Meaning | Fail = |
|---|---|---|
| **P0** | Security, tenant isolation, data integrity, money | Block the release |
| **P1** | Core business flow | Block the release |
| **P2** | Validation, edge cases | Fix before GA |
| **P3** | Cosmetic, non-functional | Backlog |

Anything touching a balance, a ledger, a payslip, a permission or another tenant's data
is **P0** by definition.

## Conventions these cases assume

These are properties of the implementation, verified against a live PostgreSQL 16 and a
live Redis. A case that contradicts one of them is a bug in the case, not the code.

| Convention | Behaviour |
|---|---|
| **Cross-tenant read** | **404**, never 403. A 403 confirms the row exists and leaks tenant data. |
| **Response envelope** | Every response is `{success, message, data, error, meta}`. Errors carry a stable machine-readable `code`. |
| **Token revocation** | Every authenticated request re-validates its session against the database. Logout, admin force-logout, deactivation and soft-delete invalidate a still-unexpired JWT **immediately**. |
| **Uniqueness races** | The pre-check is not atomic with the insert. The loser of a race gets **409 CONFLICT** (a mapped `IntegrityError`), never a 500. |
| **Salary visibility** | `GET /employees/{id}` *omits* `bank_details` and `salary` without `employee_salary:read` — it returns 200, it does not 403. The standalone bank-details route **does** 403. |
| **Batch endpoints** | Payroll generate and bulk approve return **200 with per-item success/failure**, not a 4xx, when individual items fail. |
| **Cache failure** | Redis down degrades to a database read (200), never a 500. |
| **Audit** | Every mutation writes an `activity_logs` row **inside its own transaction** — a rolled-back mutation leaves no audit row. |

## Running the suite

There is no shared harness in-tree; these are specifications. To automate:

1. Seed **two** tenants (`ORG_A`, `ORG_B`). A single-tenant fixture cannot catch an
   isolation defect, and isolation defects are the P0s.
2. Drive the real ASGI app over HTTP against a real PostgreSQL — not a mock. Every
   database-layer bug in this project's history (identifier length limits, `MissingGreenlet`
   on lazy relationship loads, `IntegrityError` mapping, INET type coercion) was invisible
   to mocks and obvious against a real database.
3. Assert the **Database Verification** column with a second connection, outside the
   application's session.

## Coverage summary

| Dimension | Where |
|---|---|
| Functional (happy path, every endpoint) | Per-module suites |
| Validation (missing / invalid / boundary / enum casing) | Per-module suites |
| Authentication (absent, expired, malformed, **revoked**) | `TC-SEC-001..016` |
| Authorization / RBAC (403 missing permission, 404 wrong org) | Per-module + `TC-SEC-017..023` |
| Business rules | Per-module suites |
| Edge cases | Per-module suites |
| Error scenarios | Per-module suites |
| **Multi-tenant isolation** | `TC-TEN-001..012` + every module |
| **Database verification** | Every mutating case |
| **End-to-end workflows** | `TC-E2E-001..063` |
| Concurrency & transactions | `TC-CON-001..009` |
| Dependency failure / resilience | `TC-RES-001..008` |
| Audit completeness | `TC-XAU-001..007` |
| Background jobs | `TC-JOB-001..007` |
| Health, readiness, configuration | `TC-OPS-001..010` |
| Schema & data integrity | `TC-DAT-001..007` |
