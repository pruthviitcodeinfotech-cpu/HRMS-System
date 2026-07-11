# Phase 7 — Test Execution & QA Validation Report

**Target:** HRMS backend @ current working tree (last commit `659b0d2`)
**Method:** every result below comes from a real HTTP request against the live ASGI app, backed by a **real PostgreSQL 16** (pgserver), all Alembic migrations applied, two tenants seeded, with database state asserted through a **separate** connection. No mocks. No backend code was modified in this phase (verified: zero tracked files touched after the phase began).

> Docker is unavailable in this environment (no docker group / sudo / rootless support). PostgreSQL 16 via `pgserver` and Redis via the unit suite's `redislite` are used as faithful substitutes — the same setup that surfaced most of this project's real bugs in earlier phases.

---

## 1. Execution summary

| Stream | Executed | Passed | Failed | Blocked |
|---|---|---|---|---|
| **Live-DB QA execution** (this phase) | **347** | **336** | **7** | **4** |
| Automated regression suite (`pytest`) | 1,068 | 1,068 | 0 | — |

**Live-DB pass rate: 336 / 343 executable = 97.9%** (blocked excluded from the denominator).

### What "347 executed" means against the 1,384 documented cases

The 1,384 Phase-6 cases include large validation matrices (every field × every boundary × enum-casing) that are permutations of one rule. Phase 7 executed **347 representative cases covering every module and every distinct behaviour class** — happy path, authentication, RBAC enforcement, multi-tenant isolation, business rules, soft/hard delete, concurrency, audit, and all known defect cases — plus the 1,068-test automated suite which independently exercises the security, cache-resilience, integrity-handling, health-probe, and schema-parity layers. Cases not individually re-run are additional permutations of rules already executed here or in the automated suite.

---

## 2. Module-wise execution report

| Module group | Executed | Passed | Failed | Blocked | Notes |
|---|---|---|---|---|---|
| Auth · RBAC · Organization | 64 | 63 | 1 | 0 | Limited-permission user provisioned live; RBAC 403s real |
| Employee · Shift · Attendance | 77 | 76 | 1 | 0 | Soft-vs-hard delete verified in DB; settings gates 409 |
| Leave · Approval · Payroll · Settlement | 128 | 125 | 3 | 0 | Full money flow + ledger integrity + F&F idempotency |
| Hardware · Notif · Settings · Audit · Dashboard · Reports | 53 | 49 | 2 | 2 | Export cases blocked (need Redis) |
| Sensitive-data (RBAC field omission) | 5 | 5 | 0 | 0 | Salary/bank hidden from unprivileged callers |
| Cross-cutting (security/tenancy/concurrency/ops/audit) | 20 | 18 | 0 | 2 | Token revocation + concurrency 409 confirmed live |
| **Total** | **347** | **336** | **7** | **4** | |

### Highlights confirmed under live execution
- **Token revocation is immediate** — a logged-out but still-unexpired JWT is rejected on the very next request (TC-SEC-014).
- **Concurrency is safe** — 8 simultaneous duplicate creates yield exactly one 201 and seven 409s, **zero 500s**; DB confirms one row (TC-CON-001/002).
- **Tenant isolation holds on reads** — cross-org fetches return **404, never 403**, across branches, employees, payroll, leave, settlements, audit.
- **Money-flow integrity** — approve deducts leave balance exactly once (409 on double-approve, no negative balance); payroll finalize debits loan/arrears ledgers once, de-finalize reverses, re-finalize debits once again; F&F is idempotent (replay leaves one auto-repayment txn, not two).
- **Audit is append-only** — POST/PUT/PATCH/DELETE on `/activity-logs` all return 405; mutations write org-scoped rows.
- **Sensitive data is protected** — an `employee:read`-only user gets 200 but salary and bank account are omitted from the payload; the standalone bank-details route 403s.

---

## 3. Defect report

Seven cases failed. Five are genuine backend defects; two are contract (spec-vs-code) mismatches. **Two of the five defects are NEW** — found only because Phase 7 executed the code; the static Phase-6 review could not see them.

| ID | Sev | Module | Defect (actual vs expected) | Evidence |
|---|---|---|---|---|
| **P7-01** | **Critical** | RBAC | **Cross-tenant scope grant.** An org1 admin granting branch-access over an **org2** branch returns **201** (expected 404). `assign_branch_access` scopes the *user* but never validates the branch's `org_id`. | TC-RBAC-112: `POST /users/{u}/branch-access {branch_id:<org2>}` → 201; SQL confirms a cross-tenant `user_branch_access` row was written (`cross_tenant_rows=1`). |
| **P7-02** | **High** *(NEW)* | Payroll | **Preview endpoint is non-functional.** `POST /payroll/processing/preview` always returns **422**. It computes un-persisted rows (`id=None`) but `PayrollPreviewResponseSchema.items` requires `id: int`, so the response can't serialize. | TC-PAY-038: 422 `items.0.id: Input should be a valid integer`; DB confirms 0 rows persisted (correct) but caller gets no preview. Verified in source: `schemas.py:307` (`id: int`) vs `service.py:1002` (transient `PayrollComputedRow`). |
| **P7-03** | **High** *(NEW)* | Hardware | **INET field breaks device reads.** Any device with a non-null `ip_address` causes register **and** `GET /devices` **and** `GET /devices/{id}` to return **422**. The model column is `INET`; asyncpg returns an `ipaddress` object; the *response* schemas (`BiometricDeviceSchema`, `BiometricDeviceConfigurationSchema`) declare `str` with no coercer — the request schemas have one, the response schemas don't. | TC-HW-001 + independent probe: a single IP-bearing row makes both list and detail 422. Row still commits, so data is stranded behind a broken read. |
| **P7-04** | **High** | Attendance | **Attendance lock is a no-op that reports success.** `POST /attendance/lock` returns 200 and writes an audit row reading "Attendance Lock Triggered", but there is no `attendance_locks` table and nothing is persisted — a "locked" day is still freely editable. | TC-ATT-088: lock → 200; `to_regclass('attendance_locks')` → NULL; `PATCH` on the locked day → 200, status changed. The audit trail asserts a control that does not exist. |
| **P7-05** | **Medium** | Settings | **Device sync code returned in plaintext.** `GET /settings/organization` masks `pass_code` but returns `sync_code` unmasked to any `settings:read` holder. | TC-SET-005: `pass_code="********"`, `sync_code="SYNC-A-123"`. `schemas.py`: masking validator on `pass_code` only. |
| P7-06 | Low | Leave | **Contract mismatch.** Self-service apply with no linked employee and omitted `employee_id` returns **404 `EMPLOYEE_NOT_FOUND`**; spec expects **422 `EMPLOYEE_ID_REQUIRED`**. No data impact — request correctly rejected, only the code/status differ. | TC-LVE-040: 404 vs 422; no rows written. |
| P7-07 | Low | Approvals | **Contract mismatch.** `POST /approvals/bulk-approve` with an empty `approval_ids: []` returns **422** (non-empty-list validator); spec expects **200 with `results: []`**. Backend behaviour is defensible; the spec should likely change. | TC-APR-042: 422 "must contain at least one ID". |

### Carried finding (could not be executed live)
- **Reports export tenant leak (Phase-6 DEF-4/5, High).** `get_export_job_status`/`get_export_file` accept `org_id` and never use it; Redis keys carry no tenant component. **Statically re-confirmed in source**, but the live cross-tenant read/download (TC-RPT-039/040) is **BLOCKED** because the export store requires Redis, which is not wired into the inline harness. Remains an open High finding; the exploit path needs the 128-bit `uuid4` job id to leak (it cannot be guessed).

### Severity tally
Critical 1 · High 3 (+1 carried) · Medium 1 · Low 2.

---

## 4. Blocked cases (4) — none are silent passes

| Case | Reason |
|---|---|
| TC-RES-001 (cache fail-open) | Simulating Redis-down inline would require unwiring Redis from the running app. **Covered by `tests/unit/test_cache_resilience.py` — 5/5 passing** in the automated run. |
| TC-JOB-001 (background jobs) | Requires the arq worker process + Redis queue, not run in an inline harness. |
| TC-RPT-039 / TC-RPT-040 (export tenant leak) | Requires a Redis-backed export store. Defect statically confirmed; live execution deferred. |

---

## 5. Overall QA status

**Core platform: healthy.** Authentication, session revocation, RBAC enforcement, multi-tenant read isolation, the leave→approval→balance and attendance→payroll→finalize→settlement money flows, ledger integrity, soft/hard-delete semantics, concurrency safety, and audit append-only behaviour all pass under real execution with database-level assertions. The automated regression suite is fully green (1,068/1,068).

**But there is one Critical and three High defects that block production**, two of which (payroll preview, INET device reads) are new and were invisible to static review. The Critical is a genuine cross-tenant write — the most serious class of bug for a multi-tenant system.

## 6. Recommendation

### ⚠️ Requires Fixes — not ready for production.

Fix before release, in priority order:
1. **P7-01 (Critical)** — validate `org_id` on branch/department scope grants. One `WHERE org_id = :caller_org` check; the column already exists.
2. **P7-02, P7-03 (High)** — add the INET→str coercer to the device *response* schemas, and relax `PayrollComputedRowSchema.id` to `int | None` (or give preview its own schema). Both are localized serialization fixes.
3. **P7-04 (High)** — either implement attendance locking (a backing table + an enforced check) or remove the endpoint; do not ship a control that only writes a misleading audit row.
4. **P7-05 (Medium)** — mask `sync_code` like `pass_code`.
5. **Carried export leak (High)** — persist `org_id` in the export job payload and compare on read; then execute TC-RPT-039/040 against Redis to close them.
6. **P7-06, P7-07 (Low)** — reconcile the two contract mismatches (adjust either code or spec).

None of these are architectural. All are localized, low-risk changes. A re-run of this phase's harnesses (all preserved and re-runnable) will verify each fix.
