# HRMS Backend — Cross-Cutting & End-to-End Test Cases

Scenarios that span modules or exercise the platform itself. The per-module suites cover
their own endpoints; **this file covers the seams**, which is where the defects that
reached production in this codebase actually lived.

Every case here is derived from behaviour verified against a live PostgreSQL 16 and a
live Redis — not from the contract. Where a case exists because a real bug was found,
that is stated, because a test whose purpose is understood is a test that survives
refactoring.

- [Test Data / Preconditions](#test-data--preconditions)
- [E2E-1 · Tenant bootstrap → employee onboarding](#e2e-1--tenant-bootstrap--employee-onboarding)
- [E2E-2 · Leave → Approval → Balance → Notification](#e2e-2--leave--approval--balance--notification)
- [E2E-3 · Attendance → Payroll → Finalize → Payslip](#e2e-3--attendance--payroll--finalize--payslip)
- [E2E-4 · Exit → F&F Settlement](#e2e-4--exit--ff-settlement)
- [E2E-5 · Employee lifecycle](#e2e-5--employee-lifecycle)
- [SEC · Authentication & session revocation](#sec--authentication--session-revocation)
- [TEN · Multi-tenant isolation](#ten--multi-tenant-isolation)
- [CON · Concurrency & transactions](#con--concurrency--transactions)
- [RES · Dependency failure & resilience](#res--dependency-failure--resilience)
- [AUD · Audit completeness](#aud--audit-completeness)
- [JOB · Background jobs](#job--background-jobs)
- [OPS · Health, readiness & configuration](#ops--health-readiness--configuration)
- [DAT · Schema & data integrity](#dat--schema--data-integrity)

---

## Test Data / Preconditions

Shared fixtures referenced throughout. Two tenants exist at all times — a single-tenant
fixture cannot catch an isolation defect.

| Fixture | Definition |
|---|---|
| `ORG_A` | `organizations.org_id = 1`, `org_code='ACME'`, active |
| `ORG_B` | `organizations.org_id = 2`, `org_code='RIVAL'`, active |
| `SA_A` / `SA_B` | Super-admin user in each org. `is_super_admin=true` |
| `HR_A` | Org A user, permissions: `employee:read` **only** (no `employee_salary`) |
| `PAY_A` | Org A user, permissions: `employee:read`, `employee_salary:read`, `payroll_record:read` |
| `EMP_001` | Org A employee, active, `monthly_salary=31000.00`, linked user `USR_E1` |
| `EMP_NOUSER` | Org A employee with **no** linked user row (`users.employee_id IS NULL`) |
| `BR_HQ`, `DEPT_ENG`, `DESIG_ENG` | Org A branch / department / designation |
| `SHIFT_GEN` | Org A shift, 09:00–18:00 |
| `LT_CL` | Org A leave type "Casual", `is_paid=true` |
| `PG_STD` | Org A payroll group, `monthly_without_compliance` |

**Auth**: every request carries `Authorization: Bearer <token>`. `POST /auth/login`
additionally requires the `X-Org-ID` header (pre-auth tenant resolution) — without it,
`TENANT_UNRESOLVED`.

**Cross-org convention**: fetching another org's resource by id returns **404**, never
403. Returning 403 would confirm the row exists and leak tenant data.

---

## E2E-1 · Tenant bootstrap → employee onboarding

| ID | Module / API | Test Scenario | Preconditions | Request / Input | Expected Result | HTTP | Database Verification | Priority |
|---|---|---|---|---|---|---|---|---|
| TC-E2E-001 | Organization | Bootstrap a tenant from empty | `SA_A`, no branches/depts | `POST /branches {"branch_name":"HQ"}` → `POST /departments {"dept_name":"Engineering"}` → `POST /designations {"designation_name":"Engineer"}` | Each created; ids returned | 201 ×3 | `SELECT count(*) FROM branches WHERE org_id=1` → 1; same for `departments`, `designations` | P1 |
| TC-E2E-002 | Organization | Duplicate department name (case-insensitive) rejected | TC-E2E-001 done | `POST /departments {"dept_name":"engineering"}` | `DEPARTMENT_NAME_EXISTS` | 409 | `SELECT count(*) FROM departments WHERE org_id=1` → still 1 | P1 |
| TC-E2E-003 | Employee | Onboard an employee into the new hierarchy | TC-E2E-001 | `POST /employees {"employee_name":"Bob","mobile_number":"9111111111","gender":"Male","master_branch_id":BR_HQ,"dept_id":DEPT_ENG,"designation_id":DESIG_ENG,"date_of_joining":"2026-01-01","monthly_salary":"31000.00","salary_type":"Monthly","create_self_service_user":true}` | Employee created with a generated `employee_code` | 201 | `SELECT employee_id FROM employees WHERE org_id=1` → 1 row; `SELECT id FROM users WHERE employee_id=:e` → 1 row (self-service user auto-provisioned) | P1 |
| TC-E2E-004 | Employee | Onboarding with a branch from another org is rejected | `ORG_B` has `BR_B` | `POST /employees {... "master_branch_id": BR_B ...}` | `BRANCH_NOT_FOUND` — the cross-org FK is not resolvable in this tenant | 404 | `SELECT count(*) FROM employees WHERE org_id=1` → unchanged | **P0** |
| TC-E2E-005 | Employee | Enum casing is exact | — | `POST /employees {... "gender":"male" ...}` (lowercase) | `VALIDATION_ERROR`, field `gender`, "Input should be 'Male', 'Female' or 'Other'" | 422 | No row written | P2 |
| TC-E2E-006 | Organization | Cannot deactivate a department that has active employees | TC-E2E-003 | `POST /departments/{DEPT_ENG}/deactivate` | `DEPARTMENT_IN_USE` | 409 | `SELECT is_active FROM departments WHERE dept_id=:d` → still `true` | P1 |

---

## E2E-2 · Leave → Approval → Balance → Notification

The single most important chain in the product. Before Phase 2 the approval envelope was
never created, so **every leave request in the system was permanently stuck `pending`**.
These cases exist so that cannot silently recur.

| ID | Module / API | Test Scenario | Preconditions | Request / Input | Expected Result | HTTP | Database Verification | Priority |
|---|---|---|---|---|---|---|---|---|
| TC-E2E-010 | Leave | Apply for leave creates the approval envelope | `LT_CL`, leave settings set, `EMP_001` credited 10 days | `POST /leave-requests {"employee_id":EMP_001,"leave_type_id":LT_CL,"start_date":"2026-07-06","end_date":"2026-07-07","duration_days":2,"reason":"Family"}` | Leave request created, `status='pending'` | 201 | **Both rows, one transaction**: `SELECT status FROM leave_requests WHERE id=:l` → `pending`; `SELECT id FROM approval_requests WHERE request_type='leave' AND reference_id=:l` → **exactly 1 row** | **P0** |
| TC-E2E-011 | Approval | Approving the envelope flips the leave request | TC-E2E-010 | `POST /approvals/{env_id}/approve {}` | Approval decided | 200 | `SELECT status, reviewed_by, reviewed_at FROM leave_requests WHERE id=:l` → `approved`, reviewer set, timestamp set | **P0** |
| TC-E2E-012 | Leave | Approval deducts the balance | TC-E2E-011 | (assertion only) | — | — | `SELECT used, closing_balance FROM employee_leave_balances WHERE employee_id=:e AND leave_type_id=:t` → `used=2`, `closing_balance=8` (was 0 / 10) | **P0** |
| TC-E2E-013 | Notification | Approval notifies the employee's linked user | TC-E2E-011, `EMP_001` has `USR_E1` | (assertion only) | — | — | `SELECT count(*) FROM notification_recipients WHERE user_id=USR_E1` → ≥ 1 | P1 |
| TC-E2E-014 | Notification | An employee with no linked user does not break the approval | `EMP_NOUSER` has a pending leave envelope | `POST /approvals/{env}/approve {}` | Approval **succeeds** — the missing recipient is skipped silently, it must never fail the business operation | 200 | `SELECT status FROM leave_requests WHERE id=:l` → `approved`; `notification_recipients` gains no row | P1 |
| TC-E2E-015 | Leave | Overlapping application writes nothing | TC-E2E-011 (2026-07-06..07 approved) | `POST /leave-requests {... same dates ...}` | `LEAVE_OVERLAP` | 409 | **No partial write**: `SELECT count(*) FROM leave_requests` unchanged **and** `SELECT count(*) FROM approval_requests` unchanged (no orphan envelope) | **P0** |
| TC-E2E-016 | Leave | Insufficient balance writes nothing | Balance = 1 day | `POST /leave-requests {... "duration_days":5 ...}` | `INSUFFICIENT_BALANCE` | 409 | `leave_requests` and `approval_requests` counts both unchanged | **P0** |
| TC-E2E-017 | Approval | Rejecting the envelope does not deduct the balance | Fresh pending envelope, balance 10 | `POST /approvals/{env}/reject {"reject_remarks":"Not approved"}` | Rejected | 200 | `SELECT status FROM leave_requests WHERE id=:l` → `rejected`; `SELECT used FROM employee_leave_balances ...` → **unchanged (0)** | **P0** |
| TC-E2E-018 | Approval | A decided approval cannot be decided again | TC-E2E-011 | `POST /approvals/{env}/approve {}` (repeat) | `APPROVAL_ALREADY_DECIDED` | 409 | `SELECT used FROM employee_leave_balances ...` → still 2 — **the balance is NOT double-deducted** | **P0** |
| TC-E2E-019 | Leave | Self-service: omitting `employee_id` resolves the caller | Caller is `USR_E1` (linked to `EMP_001`) | `POST /leave-requests {"leave_type_id":LT_CL,"start_date":...,"duration_days":1}` (no `employee_id`) | Created for `EMP_001` | 201 | `SELECT employee_id FROM leave_requests WHERE id=:l` → `EMP_001` | P1 |
| TC-E2E-020 | Leave | A caller with no linked employee gets 422, not 500 | Caller `SA_A` has `users.employee_id IS NULL` | `POST /leave-requests {...}` (no `employee_id`) | `EMPLOYEE_ID_REQUIRED` — a bare `ValueError` here would surface as a 500 | 422 | No row written | P1 |

---

## E2E-3 · Attendance → Payroll → Finalize → Payslip

| ID | Module / API | Test Scenario | Preconditions | Request / Input | Expected Result | HTTP | Database Verification | Priority |
|---|---|---|---|---|---|---|---|---|
| TC-E2E-030 | Payroll | Generate payroll from attendance | `EMP_001` assigned to `PG_STD`; 28 `attendance_days` marked `present` for the cycle | `POST /payroll/processing/generate {"payroll_group_id":PG_STD,"cycle_from":"2026-07-01","cycle_to":"2026-07-31"}` | `results[0].success=true` | 200 | `SELECT gross_wages, to_pay, is_finalized FROM payroll_computed_rows WHERE employee_id=:e` → computed, `is_finalized=false` | **P0** |
| TC-E2E-031 | Payroll | **Query count does not scale with headcount** | 100, then 800 employees in `PG_STD` | Same generate call at each size | Both succeed | 200 | Instrument `before_cursor_execute`: statement count is **constant (~18)** at both sizes. A count that grows with N is an N+1 regression — this exact defect shipped at 2,206 queries for 200 employees | **P0** |
| TC-E2E-032 | Payroll | Finalize locks the rows | TC-E2E-030 | `POST /payroll/processing/finalize {"payroll_group_id":PG_STD,"cycle_from":...,"cycle_to":...}` | Run created with `finalized_amount` | 201 | `SELECT is_finalized, finalized_run_id FROM payroll_computed_rows WHERE employee_id=:e` → `true`, run id set; `SELECT count(*) FROM finalized_payroll_runs` → 1 | **P0** |
| TC-E2E-033 | Payroll | Finalize with zero computed rows | Cycle with no generated rows | `POST /payroll/processing/finalize {...}` | `CONFLICT` — "No payroll records generated to finalize" | 409 | `SELECT count(*) FROM finalized_payroll_runs` → unchanged | P1 |
| TC-E2E-034 | Payroll | Re-generating a finalized period is a per-item failure, not a 4xx | TC-E2E-032 | `POST /payroll/processing/generate {same cycle}` | **200** with `results[0].success=false, error_code='PAYROLL_ALREADY_FINALIZED'` — the batch endpoint reports per-employee outcomes | 200 | `SELECT to_pay FROM payroll_computed_rows WHERE employee_id=:e` → **unchanged** (the locked row was not recomputed) | **P0** |
| TC-E2E-035 | Payroll | Finalize debits an active loan | `EMP_001` has an active loan, `outstanding=500.00`, `monthly_installment=100.00`; computed row has `loan_advance_deduction=100.00` | `POST /payroll/processing/finalize {...}` | Finalized | 201 | `SELECT outstanding_amount, status FROM employee_loans_advances WHERE id=:l` → `400.00`, `'active'`; `SELECT amount, payroll_run_id FROM loan_advance_transactions WHERE loan_advance_id=:l` → `100.00`, run id | **P0** |
| TC-E2E-036 | Payroll | Payslip requires salary permission | TC-E2E-032; caller `HR_A` (no `payroll_record:read`) | `GET /payroll/records/{row_id}/payslip` | `AUTH_FORBIDDEN` | 403 | n/a (read-only) | **P0** |
| TC-E2E-037 | Payroll | Payslip is visible with the right permission | Caller `PAY_A` | `GET /payroll/records/{row_id}/payslip` | Payslip returned with earnings/deductions | 200 | n/a (read-only) | P1 |
| TC-E2E-038 | Notification | Finalizing payroll notifies affected employees | TC-E2E-032 | (assertion only) | — | — | `SELECT count(*) FROM notification_recipients WHERE user_id=USR_E1` → increased | P1 |

---

## E2E-4 · Exit → F&F Settlement

The settlement debits the employee's loan **and** arrears ledgers. It is gated three ways
and must be idempotent, because running it twice would debit twice.

| ID | Module / API | Test Scenario | Preconditions | Request / Input | Expected Result | HTTP | Database Verification | Priority |
|---|---|---|---|---|---|---|---|---|
| TC-E2E-050 | Settlement | **Gate 1** — cannot settle an employee who has not exited | `EMP_001` is `active` | `POST /employees/{EMP_001}/settlement-finalize` | `EMPLOYEE_NOT_EXITED` | 409 | `SELECT count(*) FROM loan_advance_transactions WHERE employee_id=:e` → **unchanged** — no ledger was touched | **P0** |
| TC-E2E-051 | Employee | Terminate the employee | `EMP_001` active | `POST /employees/{EMP_001}/terminate {"effective_date":"2026-07-15","date_of_leaving":"2026-07-15","reason":"Relocation"}` | Terminated | 200 | `SELECT employment_status, date_of_leaving FROM employees WHERE employee_id=:e` → `terminated`, `2026-07-15`; `SELECT count(*) FROM employee_status_history WHERE employee_id=:e` → +1 | P1 |
| TC-E2E-052 | Settlement | **Gate 2** — cannot settle without a finalized payroll covering the last working day | `EMP_001` terminated; **no** finalized run covers 2026-07-15 | `POST /employees/{EMP_001}/settlement-finalize` | `PAYROLL_NOT_FINALIZED` | 409 | Ledgers untouched: `loan_advance_transactions` and `arrears_transactions` counts unchanged | **P0** |
| TC-E2E-053 | Settlement | Settle successfully once both gates are satisfied | Terminated + a finalized run covering 2026-07-15 | `POST /employees/{EMP_001}/settlement-finalize` | Settlement finalized | 200 | `SELECT settlement_finalized_at, settlement_finalized_by FROM employees WHERE employee_id=:e` → **NOT NULL**; active loans closed (`status='closed'`, `outstanding_amount=0.00`); arrears paid out | **P0** |
| TC-E2E-054 | Settlement | **Gate 3 — idempotency**: a second finalize must not re-debit | TC-E2E-053 | `POST /employees/{EMP_001}/settlement-finalize` (repeat) | `SETTLEMENT_ALREADY_FINALIZED` | 409 | `SELECT count(*) FROM loan_advance_transactions WHERE employee_id=:e` → **identical to after TC-E2E-053**. The ledger must not be debited twice | **P0** |
| TC-E2E-055 | Employee | Re-terminating a terminated employee | TC-E2E-051 | `POST /employees/{EMP_001}/terminate {...}` | `EMPLOYEE_ALREADY_TERMINATED` — `terminated` is a terminal state | 409 | `SELECT count(*) FROM employee_status_history WHERE employee_id=:e` → unchanged | P1 |

---

## E2E-5 · Employee lifecycle

| ID | Module / API | Test Scenario | Preconditions | Request / Input | Expected Result | HTTP | Database Verification | Priority |
|---|---|---|---|---|---|---|---|---|
| TC-E2E-060 | Employee | Deactivate → reactivate round trip | `EMP_001` active | `POST /employees/{e}/deactivate` then `/activate` | Both succeed | 200 ×2 | `employment_status` → `inactive` → `active`; `SELECT count(*) FROM employee_status_history WHERE employee_id=:e` → **+2** (every transition is recorded) | P1 |
| TC-E2E-061 | Employee | Transfer moves the branch FK | `BR_ANNEX` exists | `POST /employees/{e}/transfer {"master_branch_id":BR_ANNEX,"reason":"Team move","effective_date":"2026-07-01"}` | Transferred | 200 | `SELECT master_branch_id FROM employees WHERE employee_id=:e` → `BR_ANNEX`. The reason/date are captured in `activity_logs` only — there is no transfer table | P1 |
| TC-E2E-062 | Employee | Satellite soft delete retains the row | Bank detail exists | `DELETE /employees/{e}/bank-details/{id}` | No content | 204 | `SELECT is_deleted FROM employee_bank_details WHERE bank_detail_id=:id` → **`true`, row still present**. A hard delete here would break auditability | P1 |
| TC-E2E-063 | Employee | Tags are HARD deleted | Tag exists | `DELETE /employees/{e}/tags/{id}` | No content | 204 | `SELECT count(*) FROM employee_tags WHERE tag_id=:id` → **0**. `employee_tags` has no `is_deleted` column — verify the contract distinction is honoured | P2 |

---

## SEC · Authentication & session revocation

An access token is a bearer credential that stays cryptographically valid until it
expires. Every case below asserts that the **server**, not the clock, decides whether it
still works. Before Phase 3 none of this held: a terminated employee kept API access for
up to 15 minutes.

| ID | Module / API | Test Scenario | Preconditions | Request / Input | Expected Result | HTTP | Database Verification | Priority |
|---|---|---|---|---|---|---|---|---|
| TC-SEC-001 | Auth | Login issues tokens and opens a session | `SA_A` exists | `POST /auth/login {"email":...,"password":...}` + `X-Org-ID: 1` | `access_token`, `refresh_token`, user profile | 200 | `SELECT count(*) FROM user_sessions WHERE user_id=:u AND is_active` → +1 | P1 |
| TC-SEC-002 | Auth | Login without `X-Org-ID` | — | `POST /auth/login {...}` (no header) | `TENANT_UNRESOLVED` | 400 | No session row | P2 |
| TC-SEC-003 | Auth | Wrong password is non-disclosing | — | `POST /auth/login {"email":"a1@acme.test","password":"wrong"}` | `AUTH_INVALID_CREDENTIALS` — the message must be identical for an unknown email, so it cannot be used to enumerate users | 401 | No session row | **P0** |
| TC-SEC-004 | Auth | **Logout revokes the token immediately** | Valid token `T` | `POST /auth/logout` then `GET /employees` with the SAME `T` | First 204, then **401**. `T` is still unexpired and correctly signed — the server refuses it because the session is gone | 204, then 401 | `SELECT is_active, revoked_at FROM user_sessions WHERE id=:sid` → `false`, timestamp set | **P0** |
| TC-SEC-005 | RBAC | **Admin force-logout kills another user's live token** | `USR_E1` logged in with token `T2` | `DELETE /users/{USR_E1}/sessions/{sid}` (as `SA_A`), then `GET /employees` with `T2` | 204, then **401** | 204, 401 | `SELECT is_active FROM user_sessions WHERE id=:sid` → `false` | **P0** |
| TC-SEC-006 | RBAC | **Deactivating a user kills their live token** | `USR_E1` holds a valid token `T2` | `POST /users/{USR_E1}/deactivate`, then `GET /employees` with `T2` | Token rejected — this is the terminated-employee lockout | 401/403 | `SELECT is_active FROM users WHERE id=:u` → `false` | **P0** |
| TC-SEC-007 | RBAC | Soft-deleting a user kills their live token | As above, `DELETE /users/{USR_E1}` | `GET /employees` with `T2` | Rejected | 401/403 | `SELECT deleted_at FROM users WHERE id=:u` → NOT NULL | **P0** |
| TC-SEC-008 | Auth | A token with no `sid` claim is refused | Hand-craft a correctly-signed JWT omitting `sid` | `GET /employees` | Rejected — an unrevocable token is not acceptable, so this fails closed | 401 | n/a | **P0** |
| TC-SEC-009 | Auth | Expired token | Signed token with `exp` in the past | `GET /employees` | `AUTH_TOKEN_INVALID` | 401 | n/a | P1 |
| TC-SEC-010 | Auth | Malformed / garbage token | `Authorization: Bearer not-a-jwt` | `GET /employees` | Rejected | 401 | n/a | P1 |
| TC-SEC-011 | Auth | A **refresh** token cannot be used as an **access** token | Valid refresh token `R` | `GET /employees` with `Bearer R` | Rejected — the `type` claim is verified | 401 | n/a | **P0** |
| TC-SEC-012 | Auth | No `Authorization` header | — | `GET /employees` | `AUTH_NOT_AUTHENTICATED` | 401 | n/a | P1 |
| TC-SEC-013 | Auth | **Login throttle** (per IP + per email) | Rate limiting enabled, Redis up | 11 × `POST /auth/login` with a wrong password from one IP | The 11th returns `RATE_LIMITED` with a `Retry-After` header | 429 | `SELECT count(*) FROM activity_logs WHERE module='auth' AND sub_module='rate_limit'` → ≥ 1 (the trip is audited) | **P0** |
| TC-SEC-014 | Auth | **Account lockout rejects the CORRECT password** | 5 consecutive failed logins for `SA_A` | `POST /auth/login` with the **correct** password | `RATE_LIMITED` — the credential check is never reached | 429 | `SELECT count(*) FROM user_sessions WHERE user_id=:u AND created_at > :t` → **0** (no session opened) | **P0** |
| TC-SEC-015 | Auth | A successful login resets the failure counter | 4 failed attempts, then 1 success | 5th attempt with the correct password, then 4 more failures | The 5th succeeds; the streak restarts, so no lockout at attempt 6 | 200 | Session row created | P1 |
| TC-SEC-016 | Auth | Throttling one account does not lock out another | `SA_A` locked out | `POST /auth/login` as `HR_A` from a different IP | Succeeds — the counters are keyed per-IP **and** per-identifier so one victim cannot be starved by another's attacker | 200 | Session created for `HR_A` | **P0** |
| TC-SEC-017 | RBAC | Non-super-admin cannot **grant** super-admin | Caller has `user_management:edit` but is not super-admin | `PATCH /users/{id} {"is_super_admin": true}` | `AUTH_FORBIDDEN` | 403 | `SELECT is_super_admin FROM users WHERE id=:u` → unchanged | **P0** |
| TC-SEC-018 | RBAC | Non-super-admin cannot **revoke** super-admin | Target is super-admin | `PATCH /users/{id} {"is_super_admin": false}` | `AUTH_FORBIDDEN` — gating only the grant would let any user-editor strip the org's admin and lock the tenant out of itself | 403 | `SELECT is_super_admin FROM users WHERE id=:u` → still `true` | **P0** |
| TC-SEC-019 | RBAC | Granting an unknown feature key | Rights template exists | `PUT /rights-templates/{template_id}/permissions {"items":[{"feature_key":"not_a_real_key","can_read":true}]}` | `FEATURE_KEY_UNKNOWN` — the key is validated against the 39-entry catalog in `app/core/security/permissions.py` | 422 | `SELECT count(*) FROM rights_template_permissions WHERE template_id=:t` → unchanged | P1 |
| TC-SEC-020 | Employee | **Bank details are omitted, not 403'd, without salary permission** | Caller `HR_A` (`employee:read` only) | `GET /employees/{EMP_001}` | **200** with `bank_details: []` and `salary: null`. The account number and IFSC appear nowhere in the response body. The employee record is still readable — it degrades, it does not deny | 200 | `SELECT account_number FROM employee_bank_details WHERE employee_id=:e` → the row **exists** in the DB; assert it is absent from the response | **P0** |
| TC-SEC-021 | Employee | Bank details visible with salary permission | Caller `PAY_A` | `GET /employees/{EMP_001}` | `bank_details` populated, `salary` populated | 200 | n/a (read-only) | P1 |
| TC-SEC-022 | Employee | The standalone bank-details route **does** 403 | Caller `HR_A` | `GET /employees/{EMP_001}/bank-details` | `AUTH_FORBIDDEN` | 403 | n/a | **P0** |
| TC-SEC-023 | Employee | The LIST endpoint never exposes salary or bank details | Caller `PAY_A` (even with permission) | `GET /employees` | The summary schema has no salary/bank/document fields at all | 200 | Assert `account_number` and `monthly_salary` appear nowhere in the response body | **P0** |
| TC-SEC-024 | Employee | Path traversal in an upload filename | — | `POST /employees/{e}/documents` multipart, filename `../../../etc/passwd` | Rejected or sanitised — the stored key is server-generated (`employees/{id}/{uuid}.pdf`) and cannot escape `upload_dir` | 422 / 201 with a safe key | `SELECT file_key FROM employee_documents WHERE ...` → matches `^employees/\d+/[0-9a-f]{32}\.pdf$`; **no** file exists outside `upload_dir` | **P0** |
| TC-SEC-025 | Employee | Disallowed file type | — | `POST /employees/{e}/documents` multipart, `evil.sh` | `UNSUPPORTED_FILE_TYPE` | 422 | No `employee_documents` row; no file on disk | **P0** |
| TC-SEC-026 | Employee | Oversize upload | File > `MAX_UPLOAD_SIZE_MB` | `POST /employees/{e}/documents` | `FILE_TOO_LARGE` | 422 | No row, no file | P1 |
| TC-SEC-027 | Hardware | Device secrets are write-only | Device registered with `communication_key` | `GET /devices/{id}` | The key is **absent** from the response (only a boolean indicating it is set) | 200 | `SELECT communication_key FROM biometric_devices WHERE id=:d` → set in the DB; assert it does not appear in the response body | **P0** |
| TC-SEC-028 | Settings | Sync/pass codes are masked | Settings configured | `GET /settings` | `sync_code` / `pass_code` masked, never plaintext | 200 | Assert the raw values from `org_settings` do not appear in the body | **P0** |
| TC-SEC-029 | Cross-cutting | No secret ever appears in a log or audit row | Run the full E2E suite | (assertion only) | — | — | `SELECT count(*) FROM activity_logs WHERE description ILIKE '%password%' OR description ILIKE '%$2b$%' OR description ILIKE '%Bearer %'` → **0**; grep the captured stdout for the same | **P0** |

---

## TEN · Multi-tenant isolation

Every case runs the mutation as `ORG_A` and the assertion as `ORG_B`. **A 403 here is a
failure, not a pass** — it confirms the row exists.

| ID | Module / API | Test Scenario | Preconditions | Request / Input | Expected Result | HTTP | Database Verification | Priority |
|---|---|---|---|---|---|---|---|---|
| TC-TEN-001 | Employee | Org B cannot list Org A's employees | Org A has 800 employees, Org B has 0 | `GET /employees` as `SA_B` | `pagination.total_records = 0` | 200 | `SELECT count(*) FROM employees WHERE org_id=1` → 800 (they exist; B just cannot see them) | **P0** |
| TC-TEN-002 | Employee | Org B cannot fetch an Org A employee by id | — | `GET /employees/{EMP_001}` as `SA_B` | **404**, not 403 | 404 | n/a | **P0** |
| TC-TEN-003 | Employee | Org B cannot mutate an Org A employee | — | `PATCH /employees/{EMP_001} {"employee_name":"Hacked"}` as `SA_B` | 404 | 404 | `SELECT employee_name FROM employees WHERE employee_id=:e` → unchanged | **P0** |
| TC-TEN-004 | Payroll | Org B sees zero of Org A's payroll records | Org A has finalized rows | `GET /payroll/records` as `SA_B` | `total_records = 0` | 200 | n/a | **P0** |
| TC-TEN-005 | Audit | Org B sees **only its own** audit rows | Org A has 23 `activity_logs` rows; Org B has 1 (its own login) | `GET /activity-logs` as `SA_B` | `total_records` equals `SELECT count(*) FROM activity_logs WHERE org_id=2` — **and is strictly less than Org A's count**. B legitimately sees its own rows; it must see none of A's | 200 | Compare API total against the org-scoped DB count | **P0** |
| TC-TEN-006 | Leave | Org B cannot approve an Org A leave request | Org A envelope pending | `POST /approvals/{env}/approve` as `SA_B` | 404 | 404 | `SELECT status FROM leave_requests WHERE id=:l` → still `pending` | **P0** |
| TC-TEN-007 | Settlement | Org B cannot settle an Org A employee | — | `POST /employees/{EMP_001}/settlement-finalize` as `SA_B` | 404 | 404 | Ledgers untouched | **P0** |
| TC-TEN-008 | Reports | An export job id from Org A is not downloadable by Org B | Org A created export job `J` | `GET /reports/exports/{J}/download` as `SA_B` | Denied — the job must be org-scoped, not merely unguessable | 404 | n/a | **P0** |
| TC-TEN-009 | Notification | A user cannot read another user's notification | `USR_E1` has notification `N` | `GET /me/notifications/{N}` as a different user | 404 | 404 | n/a | **P0** |
| TC-TEN-010 | Hardware | Org B cannot see Org A's devices | — | `GET /devices` as `SA_B` | `total_records = 0` | 200 | n/a | **P0** |
| TC-TEN-011 | Organization | `org_code` is globally unique across tenants | Org A is `ACME` | `POST /organizations {"org_code":"ACME", ...}` as a platform super-admin | `ORG_CODE_EXISTS` | 409 | `SELECT count(*) FROM organizations WHERE org_code='ACME'` → 1 | P1 |
| TC-TEN-012 | Cross-cutting | **Sweep**: every list endpoint is org-scoped | Both orgs seeded | For each of the 361 endpoints that returns a list, call it as `SA_B` | No response contains an Org A id | 200 | Parameterise over the route table — a new list endpoint that forgets `org_id` is caught automatically | **P0** |

---

## CON · Concurrency & transactions

| ID | Module / API | Test Scenario | Preconditions | Request / Input | Expected Result | HTTP | Database Verification | Priority |
|---|---|---|---|---|---|---|---|---|
| TC-CON-001 | Organization | **A lost uniqueness race is a 409, not a 500** | No department named `RaceDept` | 10 concurrent `POST /departments {"dept_name":"RaceDept"}` | Exactly **1 × 201** and **9 × 409 CONFLICT**. Services pre-check uniqueness, but the check and the insert are not atomic — the loser must lose at the database and be *mapped*, not crash. Measured before the fix: 1 × 201 and **9 × 500** | 201 / 409 | `SELECT count(*) FROM departments WHERE dept_name='RaceDept'` → **exactly 1** | **P0** |
| TC-CON-002 | Employee | Concurrent identical employee codes | — | 10 concurrent `POST /employees` with the same `employee_code` | 1 × 201, 9 × 409 | 201 / 409 | Exactly 1 row | **P0** |
| TC-CON-003 | Cross-cutting | No 5xx under a write race | TC-CON-001/002 | (assertion only) | — | — | Assert `500` appears in **no** response | **P0** |
| TC-CON-004 | Employee | A failed create rolls back completely | — | `POST /employees {... "master_branch_id": 99999 ...}` (nonexistent FK) | Rejected | 4xx | `SELECT count(*) FROM employees` → **unchanged**; no orphan `users` row from the self-service provisioning half of the transaction | **P0** |
| TC-CON-005 | Approval | Bulk approve isolates each item | 3 pending envelopes, one of which will fail | `POST /approvals/bulk-approve {"approval_ids":[a,b,c]}` | Per-item results; the good ones succeed | 200 | The two valid leave requests are `approved`; the failing one is untouched. One bad item must not poison the transaction (each is wrapped in a SAVEPOINT) | **P0** |
| TC-CON-006 | Cross-cutting | 50 concurrent reads | Seeded DB | 50 × `GET /employees?page_size=25` in parallel | All 200 — no connection-pool exhaustion, no session shared across tasks | 200 ×50 | n/a | P1 |
| TC-CON-007 | Cross-cutting | 60 mixed concurrent read/write | — | 30 × `GET /employees/{id}` + 30 × `GET /attendance/days` in parallel | All 200 | 200 ×60 | n/a | P1 |
| TC-CON-008 | Payroll | Concurrent finalize of the same cycle | Computed rows exist | 2 concurrent `POST /payroll/processing/finalize` for the same cycle | One 201; the other `PAYROLL_ALREADY_FINALIZED` or 409 — **never two runs** | 201 / 409 | `SELECT count(*) FROM finalized_payroll_runs WHERE payroll_group_id=:g AND cycle_from=:f` → **exactly 1** | **P0** |
| TC-CON-009 | Settlement | Concurrent F&F finalize | Employee eligible | 2 concurrent `POST /employees/{e}/settlement-finalize` | One succeeds; the other `SETTLEMENT_ALREADY_FINALIZED` | 200 / 409 | `SELECT count(*) FROM loan_advance_transactions WHERE employee_id=:e AND source='settlement'` → the ledger is debited **exactly once** | **P0** |

---

## RES · Dependency failure & resilience

| ID | Module / API | Test Scenario | Preconditions | Request / Input | Expected Result | HTTP | Database Verification | Priority |
|---|---|---|---|---|---|---|---|---|
| TC-RES-001 | Dashboard | **Redis down must not 500 the dashboard** | Redis unreachable; DB up; `ENVIRONMENT=development` | `GET /dashboard/summary` | **200**, served from the database. A cache is an optimisation; it must never be a single point of failure. Measured before the fix: an unhandled `ConnectionError` → 500 | 200 | n/a (read-only) | **P0** |
| TC-RES-002 | Reports | Redis down does not 500 a report | As above | `GET /reports/employees/master` | 200 | 200 | n/a | **P0** |
| TC-RES-003 | Cross-cutting | A cache outage is logged, not swallowed silently | Redis down | Any cached endpoint | Response 200 | 200 | An ERROR log line `cache_backend_unavailable` is emitted — degraded but *pageable* | P1 |
| TC-RES-004 | Auth | Redis down fails the login throttle **open** (dev) | Redis down | 20 rapid failed logins | No 429 — the throttle is skipped so a Redis blip cannot lock every user out of the product | 401 ×20 | An ERROR log `rate_limit_backend_unavailable` is emitted. **This is the alert that means brute-force protection is off** | **P0** |
| TC-RES-005 | Ops | Production **refuses to start** without Redis | `ENVIRONMENT=production`, `RATE_LIMIT_ENABLED=true`, Redis down | Start the app | Startup **fails** with `Refusing to start: redis is unreachable ... because it backs login rate limiting and the account lockout` | n/a (no listener) | n/a | **P0** |
| TC-RES-006 | Ops | Production starts when Redis is healthy | Same, Redis up | Start the app | Starts | 200 on `/health` | n/a | P1 |
| TC-RES-007 | Ops | Development starts **without** Redis | `ENVIRONMENT=development`, Redis down | `make run` | Starts, warns — a laptop with no Redis must still get a working API | 200 | n/a | P1 |
| TC-RES-008 | Ops | Production refuses to start without a database | DB unreachable | Start the app | Startup fails | n/a | n/a | **P0** |

---

## AUD · Audit completeness

Every mutation writes an `activity_logs` row **inside the mutation's own transaction** —
a rolled-back mutation must leave no audit row, and a successful one must always leave one.

| ID | Module / API | Test Scenario | Preconditions | Request / Input | Expected Result | HTTP | Database Verification | Priority |
|---|---|---|---|---|---|---|---|---|
| TC-XAU-001 | Cross-cutting | Every mutating endpoint writes an audit row | Seeded tenant | For each of the ~180 mutating endpoints: capture `count(activity_logs)`, call it, re-capture | Count increases by ≥ 1 | 2xx | `SELECT count(*) FROM activity_logs WHERE org_id=1` increments. Parameterise over the route table so a new endpoint that forgets to audit is caught | **P0** |
| TC-XAU-002 | Cross-cutting | A **failed** mutation writes **no** audit row | — | A create that fails validation or a business rule | Rejected | 4xx | `SELECT count(*) FROM activity_logs` → **unchanged**. The audit write is inside the transaction, so a rollback must take it with it | **P0** |
| TC-XAU-003 | RBAC | Auth and RBAC mutations are audited | Login, then `POST /rights-templates`, then `PUT /users/{user_id}/template` | (assertions) | — | — | `SELECT count(*) FROM activity_logs WHERE module IN ('auth','rbac','user_management')` → ≥ 3. These are the rows the security report reads; before Phase 2 **RBAC and Auth wrote zero**, so that report was structurally always empty | **P0** |
| TC-XAU-004 | Audit | The audit log is append-only | — | `POST /activity-logs`, `PATCH /activity-logs/{id}`, `DELETE /activity-logs/{id}` | All **405 Method Not Allowed** — no such routes exist | 405 | Row count unchanged | **P0** |
| TC-XAU-005 | Audit | Unknown sort field is rejected | — | `GET /activity-logs?sort_by=password` | `VALIDATION_ERROR` — the sort field is allow-listed (`logged_at`, `log_date`) | 422 | n/a | P1 |
| TC-XAU-006 | Audit | `security-events` is not shadowed by `{log_id}` | — | `GET /activity-logs/security-events` | **200** with events — not a 422 from trying to parse `security-events` as an integer id. A static route declared after a parameterised sibling becomes unreachable; this exact defect shipped twice | 200 | n/a | P1 |
| TC-XAU-007 | Audit | Audit rows record the actor | Any mutation by `SA_A` | `GET /activity-logs` | The row carries `performed_by_user_id` and `performed_by_name` | 200 | `SELECT performed_by_user_id FROM activity_logs ORDER BY id DESC LIMIT 1` → `SA_A`'s id | P1 |

---

## JOB · Background jobs

| ID | Module / API | Test Scenario | Preconditions | Request / Input | Expected Result | HTTP | Database Verification | Priority |
|---|---|---|---|---|---|---|---|---|
| TC-JOB-001 | Payroll | Payslip email actually enqueues | Redis up, worker running | `POST /payroll/records/{row}/payslip/email` | **202** with a real `job_id`. Before Phase 5 this returned `{"queued": true}` and queued nothing | 202 | The arq queue depth increases; after the worker runs, the job completes | P1 |
| TC-JOB-002 | Jobs | A job opens its **own** database session | Worker running | Enqueue `sync_device` | The job completes and mutates the DB | — | `SELECT last_sync_at FROM biometric_devices WHERE id=:d` → stamped. A job must never reuse a request-scoped session, which `get_db` closes the instant the handler returns | **P0** |
| TC-JOB-003 | Jobs | Leave accrual is **idempotent** | Accrual cron | Run `run_leave_accrual` twice for the same cycle | The second run credits nothing | — | `SELECT allocated FROM employee_leave_balances WHERE employee_id=:e` → **unchanged** after the second run; `employee_leave_allocations` gains no duplicate row. arq retries on failure, so a non-idempotent accrual would double-credit | **P0** |
| TC-JOB-004 | Jobs | Payslip email no-ops cleanly when SMTP is unconfigured | `SMTP_HOST=""` | Run `send_payslip_email` | Returns `{"sent": false, "reason": "smtp_not_configured"}` — logs, does not crash, does not retry-storm | — | n/a | P1 |
| TC-JOB-005 | Jobs | Enqueue fails loudly when Redis is down | Redis down | `POST /payroll/records/{row}/payslip/email` | `QueueUnavailableException` → **503**, not a fake job id. A caller that was told "queued" made a promise; a vanished job is untraceable | 503 | No job row | P1 |
| TC-JOB-006 | Reports | A large export falls back in-process if enqueue fails | Redis down, large report | `GET /reports/employees/master?format=csv` (large) | The export still completes — it degrades to the in-process path rather than being lost | 202/200 | The export artefact is produced | P1 |
| TC-JOB-007 | Jobs | Every job function is registered | — | Import `app.jobs.worker` | `WorkerSettings.functions` contains all 6 jobs; `cron_jobs` contains both schedules. A new job that is never registered is silently dead code | — | n/a | P1 |

---

## OPS · Health, readiness & configuration

| ID | Module / API | Test Scenario | Preconditions | Request / Input | Expected Result | HTTP | Database Verification | Priority |
|---|---|---|---|---|---|---|---|---|
| TC-OPS-001 | Ops | Liveness touches no dependency | Redis **and** DB down | `GET /health` | **200** — liveness means "is the process wedged?". If it probed Redis, a blip would restart every pod and turn a degraded system into an outage | 200 | n/a | **P0** |
| TC-OPS-002 | Ops | Readiness is 503 when the database is down | DB down | `GET /health/ready` | **503** with `checks.database.status = "error"` — the load balancer drains this instance without killing it | 503 | n/a | **P0** |
| TC-OPS-003 | Ops | Readiness stays ready (degraded) without Redis in dev | Redis down, dev | `GET /health/ready` | **200**, `checks.redis.status="error"`, `required=false`, `impact="cache bypassed; login rate limiting disabled"` | 200 | n/a | P1 |
| TC-OPS-004 | Ops | Readiness is 503 without Redis in production | Redis down, prod | `GET /health/ready` | **503**, `checks.redis.required = true` | 503 | n/a | **P0** |
| TC-OPS-005 | Ops | `/docs` is disabled in production | `ENVIRONMENT=production` | `GET /docs`, `GET /redoc`, `GET /api/v1/openapi.json` | All **404** — they enumerate every endpoint and schema for an attacker and are useless to a client that has the contract | 404 | n/a | **P0** |
| TC-OPS-006 | Ops | Production refuses placeholder secrets | `ENVIRONMENT=production`, `JWT_SECRET=change-me` | Start the app | Startup fails: "Insecure configuration for ENVIRONMENT=production: JWT_SECRET is still the placeholder value" | n/a | n/a | **P0** |
| TC-OPS-007 | Ops | Production refuses a wildcard CORS/Host | `ALLOWED_ORIGINS=""` in prod | Start the app | Startup fails | n/a | n/a | **P0** |
| TC-OPS-008 | Ops | Every request is traceable by `request_id` | — | Any request | The `X-Request-ID` response header matches the `request_id` in every log line for that request | 200 | Correlate the log stream on a single id | P1 |
| TC-OPS-009 | Ops | Backup → destroy → restore round trip | Seeded DB | `./scripts/backup.sh`, `TRUNCATE`, `./scripts/restore.sh <dump> hrms_restored` | Data fully restored | n/a | Row counts identical; `SELECT sum(to_pay) FROM payroll_computed_rows` **identical** (money survives, not just row counts); alembic head, FK count and index count all intact | **P0** |
| TC-OPS-010 | Ops | `restore.sh` refuses to overwrite the live database | — | `./scripts/restore.sh <dump> <LIVE_DB_NAME>` | Exits non-zero and refuses. Restoring in place is how a recoverable incident becomes an unrecoverable one | rc=1 | The live DB is untouched | **P0** |

---

## DAT · Schema & data integrity

| ID | Module / API | Test Scenario | Preconditions | Request / Input | Expected Result | HTTP | Database Verification | Priority |
|---|---|---|---|---|---|---|---|---|
| TC-DAT-001 | Schema | Migrations apply from scratch | Empty PostgreSQL | `alembic upgrade head` | Succeeds | n/a | 67 tables, 131 FK constraints, head = `0018_fk_supporting_indexes` | **P0** |
| TC-DAT-002 | Schema | Migrations roll back and re-apply | TC-DAT-001 | `alembic downgrade -1` then `upgrade head` | Succeeds | n/a | Schema identical before and after | P1 |
| TC-DAT-003 | Schema | **Autogenerate wants no changes** | Migrations at head | `alembic revision --autogenerate` | An **empty** migration. A non-empty one means the models and the database disagree — for most of this project's life autogenerate would have emitted `drop_constraint` for **36 foreign keys**, silently destroying referential integrity | n/a | `compare_metadata()` returns `[]` | **P0** |
| TC-DAT-004 | Schema | No identifier exceeds 63 characters | — | Inspect all constraint/index names | All ≤ 63. PostgreSQL truncates beyond that; migration `0003` originally shipped a 79-char name and **could never have been applied to a real PostgreSQL** — the whole chain was unrunnable and nobody noticed, because it had only ever been tested against mocks | n/a | Assert over `Base.metadata` and the migration files | **P0** |
| TC-DAT-005 | Schema | Foreign keys are enforced at the database | — | `DELETE FROM organizations WHERE org_id=1` (raw SQL, org has employees) | PostgreSQL raises an `IntegrityError` | n/a | The delete is refused — referential integrity does not depend on the application layer | **P0** |
| TC-DAT-006 | Schema | Soft-deleted rows are excluded from reads | An employee with `is_deleted=true` | `GET /employees` | The row is absent | 200 | The row still exists in `employees`; it is filtered, not removed | P1 |
| TC-DAT-007 | Schema | Decimal precision is preserved | Payroll computed | `GET /payroll/records/{id}` | `gross_wages` is exact to 2dp — no float drift | 200 | `SELECT gross_wages FROM payroll_computed_rows WHERE id=:r` → e.g. `3100.00`, not `3099.999...`. Money is `NUMERIC`, never `float` | **P0** |
