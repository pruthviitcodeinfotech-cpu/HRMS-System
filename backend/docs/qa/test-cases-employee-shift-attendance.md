# QA Test-Case Specification — Employee, Shift & Attendance Management

**Scope:** Employee Management (32 endpoints), Shift Management (27 endpoints), Attendance Management (27 endpoints).
**Base URL:** `/api/v1` (all paths below are relative to it).
**Source of truth:** `app/modules/{employee,shift,attendance}/{router,schemas,service,exceptions,constants}.py`, `docs/Employee_Management_API_Contract.md`, `docs/Shift_Management_API_Contract.md`, `docs/Attendance_Management_API_Contract.md`.
**Rule:** every error code in this document was grepped and exists in the codebase. Where the **emitted** code differs from the code the contract/exceptions module *documents*, the test asserts the **emitted** code and a defect is raised in [Appendix A](#appendix-a--error-code-drift-defects).

---

## Table of Contents

1. [Test Data / Preconditions](#1-test-data--preconditions)
2. [Response Envelopes](#2-response-envelopes)
3. [Employee Management — TC-EMP-001 … TC-EMP-130](#3-employee-management)
4. [Shift Management — TC-SHF-001 … TC-SHF-107](#4-shift-management)
5. [Attendance Management — TC-ATT-001 … TC-ATT-094](#5-attendance-management)
6. [End-to-End Workflows — TC-ESA-E2E-001 … TC-ESA-E2E-006](#6-end-to-end-workflows)
7. [Appendix A — Error-code drift (defects)](#appendix-a--error-code-drift-defects)
8. [Appendix B — Coverage matrix](#appendix-b--coverage-matrix)

---

## 1. Test Data / Preconditions

Seed once per suite run. All ids below are symbolic; bind them from the seed fixture.

### Tenants

| Symbol | Table | Value |
|---|---|---|
| `ORG_A` | `organizations` | `org_id = 1` — the tenant under test |
| `ORG_B` | `organizations` | `org_id = 2` — the *other* tenant, used for every isolation test |

### Users / principals (JWT `sub`, `org_id`, permission set)

| Symbol | Org | Permissions | Purpose |
|---|---|---|---|
| `ADMIN_USER` | ORG_A | `employee:*`, `employee_salary:*`, `employee_document:*`, `shift:*`, `shift_assignment:*`, `shift_rotation:*`, `weekoff:*`, `roster:*`, `attendance:*`, `attendance_punch:*`, `attendance_penalty:*` | Happy-path actor |
| `HR_USER` | ORG_A | `employee:read` **only** | 403 / sensitive-omission probe |
| `PAYROLL_USER` | ORG_A | `employee:read` + `employee_salary:read` | Salary/bank visibility probe |
| `DOC_USER` | ORG_A | `employee:read` + `employee_document:edit` | Document-upload probe |
| `ORG_B_ADMIN` | ORG_B | same as `ADMIN_USER`, tenant B | Cross-tenant probe |
| `BRANCH_ADMIN` | ORG_A | `employee:read`, data scope = `[BRANCH_1]` | Branch data-scope probe |
| `NO_ORG_USER` | — | any; token carries **no** `org_id` | `TENANT_UNRESOLVED` probe |

### Org hierarchy (ORG_A)

| Symbol | Table | Notes |
|---|---|---|
| `BRANCH_1` / `BRANCH_2` | `branches` | active |
| `BRANCH_INACTIVE` | `branches` | `is_active = false` |
| `DEPT_1` / `DEPT_2` | `departments` | active |
| `DESIG_1` / `DESIG_2` | `designations` | active |
| `BRANCH_B1`, `DEPT_B1`, `DESIG_B1` | ORG_B equivalents | for cross-tenant FK tests |

### Employees

| Symbol | Org | State |
|---|---|---|
| `EMP_001` | ORG_A | `employment_status='active'`, `date_of_joining='2026-01-01'`, salary `Monthly / 50000.00`, has 1 bank detail, 1 document, 1 emergency contact, 1 reference, 1 tag |
| `EMP_002` | ORG_A | `active`, no satellites (clean slate for create tests) |
| `EMP_INACTIVE` | ORG_A | `employment_status='inactive'` |
| `EMP_TERMINATED` | ORG_A | `employment_status='terminated'`, `date_of_leaving` set |
| `EMP_B01` | ORG_B | `active` — must be invisible to every ORG_A caller |

### Shifts / roster (ORG_A)

| Symbol | Table | State |
|---|---|---|
| `SHIFT_GENERAL` | `shifts` | `shift_name='General'`, `shift_type='fixed'`, `is_uniform_time=true`, one `shift_day_timings` row with `day_of_week=NULL`, `09:00`→`18:00` |
| `SHIFT_NIGHT` | `shifts` | overnight, `22:00`→`06:00`, created with `crosses_midnight=true` |
| `SHIFT_PERDAY` | `shifts` | `is_uniform_time=false`, 7 `shift_day_timings` rows (day_of_week 0..6) |
| `SHIFT_DELETED` | `shifts` | `is_deleted=true` (restore tests) |
| `SHIFT_B1` | `shifts` | ORG_B |
| `ASSIGN_001` | `shift_assignments` | `EMP_001` → `SHIFT_GENERAL`, `effective_from='2026-01-01'`, `effective_to=NULL` |
| `ROSTER_001` | `roster` | `EMP_001`, `roster_date='2026-07-01'`, `shift_id=SHIFT_GENERAL` |
| `WEEKOFF_SUN` | `employee_weekoffs` | `EMP_001`, `day_of_week=0`, `weekoff_type='week_off'`, `effective_to=NULL` |

### Attendance (ORG_A)

| Symbol | Table | State |
|---|---|---|
| `DAY_001` | `attendance_days` | `EMP_001`, `attendance_date='2026-07-01'`, `status='present'`, 2 punches |
| `PUNCH_001` | `attendance_punches` | `attendance_day_id = DAY_001`, `punch_type='in'` |
| `PENALTY_001` | `attendance_penalties` | `DAY_001`, `status='active'`, `penalty_unit='amount'`, `penalty_value=500.00` |
| `PENALTY_WAIVED` | `attendance_penalties` | `status='waived'` |
| `DAY_B01` | `attendance_days` | ORG_B |

### Settings toggles (`org_settings`) — **critical**

| Column | Schema default | Test posture |
|---|---|---|
| `enable_regularization` | `false` | ORG_A row **absent or false** by default ⇒ `POST /attendance/corrections` returns **409 REGULARIZATION_DISABLED** out of the box. Tests that need the happy path must first `UPDATE org_settings SET enable_regularization = true WHERE org_id = 1`. |
| `advance_shift_enabled` | `false` | Same shape for `POST /shift-rotations` ⇒ **409 ADVANCE_SHIFT_DISABLED**. |

### Upload fixtures

| Symbol | Content |
|---|---|
| `FILE_PDF_OK` | valid 12 KB `contract.pdf`, `application/pdf` |
| `FILE_PNG_OK` | valid 8 KB `id.png`, `image/png` |
| `FILE_EXE` | `payload.exe`, `application/octet-stream` |
| `FILE_EMPTY` | `empty.pdf`, 0 bytes |
| `FILE_HUGE` | `big.pdf`, `MAX_UPLOAD_SIZE_MB` + 1 MB |
| `FILE_TRAVERSAL` | valid PDF bytes with filename `../../etc/passwd.pdf` |

---

## 2. Response Envelopes

**Success:** `{ "success": true, "message": "...", "data": {...}, "meta": { "request_id": "...", "pagination": {...}? } }`
**Error:** `{ "success": false, "message": "...", "error": { "code": "<CODE>", "message": "...", "details": [...]? }, "meta": {...} }`

Global mappings (`app/core/exceptions/`):

| Situation | HTTP | `error.code` |
|---|---|---|
| No / invalid / expired bearer token | 401 | `AUTH_NOT_AUTHENTICATED` |
| Authenticated, missing feature permission | 403 | `AUTH_FORBIDDEN` |
| Token has no `org_id` | 400 | `TENANT_UNRESOLVED` |
| Pydantic / query-param failure | 422 | `VALIDATION_ERROR` |
| Postgres `23505` unique violation (lost race) | 409 | `CONFLICT` |
| Postgres `23503` FK violation | 409 | `CONFLICT` |
| Postgres `23514` check violation | 422 | `VALIDATION_ERROR` |

Pagination guards: `page ≥ 1`, `1 ≤ page_size ≤ 200` (`MAX_PAGE_SIZE`), defaults `page=1, page_size=25`.

---

## 3. Employee Management

**Permission keys:** `employee` (read/create/edit/delete), `employee_salary` (read), `employee_document` (edit).

### 3.1 List & search — `GET /employees`

| ID | Module / API | Test Scenario | Preconditions | Request / Input | Expected Result | HTTP | Database Verification | Priority |
|---|---|---|---|---|---|---|---|---|
| TC-EMP-001 | Employee / `GET /employees` | List employees, default pagination | `ADMIN_USER`; ≥3 ORG_A employees | `GET /employees` | Success envelope; `data.items[]` of `EmployeeSummarySchema`; `meta.pagination.page=1`, `page_size=25` | 200 | n/a (read-only) | P1 |
| TC-EMP-002 | Employee / `GET /employees` | List NEVER exposes salary, bank details or documents | `ADMIN_USER` (holds `employee_salary:read`) | `GET /employees` | Every item lacks `salary`, `bank_details`, `documents`, `monthly_salary` keys entirely — the summary projection has no such fields even for a privileged caller | 200 | n/a (read-only) | **P0** |
| TC-EMP-003 | Employee / `GET /employees` | Filter by branch | `ADMIN_USER` | `GET /employees?branch_id={BRANCH_1}` | Only employees whose `master_branch_id = BRANCH_1` | 200 | `SELECT count(*) FROM employees WHERE org_id=1 AND master_branch_id=:b AND is_deleted=false` → equals `meta.pagination.total_records` | P1 |
| TC-EMP-004 | Employee / `GET /employees` | Filter by `status` (alias of `employment_status`) | `ADMIN_USER` | `GET /employees?status=terminated` | Only `EMP_TERMINATED` returned | 200 | n/a (read-only) | P2 |
| TC-EMP-005 | Employee / `GET /employees` | Invalid enum value for `status` | `ADMIN_USER` | `GET /employees?status=fired` | Error envelope, `error.code = "VALIDATION_ERROR"` | 422 | n/a (read-only) | P2 |
| TC-EMP-006 | Employee / `GET /employees` | Free-text search on name / code / contact | `ADMIN_USER` | `GET /employees?q=EMP_001_name_fragment` | `EMP_001` present in `data.items` | 200 | n/a (read-only) | P2 |
| TC-EMP-007 | Employee / `GET /employees` | Boundary: `page_size` above `MAX_PAGE_SIZE` | `ADMIN_USER` | `GET /employees?page_size=201` | `error.code = "VALIDATION_ERROR"` (`le=200`) | 422 | n/a (read-only) | P2 |
| TC-EMP-008 | Employee / `GET /employees` | Boundary: `page_size=200` accepted, `page=0` rejected | `ADMIN_USER` | `GET /employees?page_size=200` then `GET /employees?page=0` | First → 200; second → `VALIDATION_ERROR` | 200 / 422 | n/a (read-only) | P2 |
| TC-EMP-009 | Employee / `GET /employees` | Branch data-scope confines results | `BRANCH_ADMIN` (scope `[BRANCH_1]`) | `GET /employees` | Zero items with `master_branch_id = BRANCH_2` | 200 | n/a (read-only) | **P0** |
| TC-EMP-010 | Employee / `GET /employees` | Multi-tenant isolation of the list | `ORG_B_ADMIN` | `GET /employees` | Response contains `EMP_B01` and **no** ORG_A employee | 200 | `SELECT DISTINCT org_id FROM employees WHERE employee_id IN (returned ids)` → `{2}` | **P0** |
| TC-EMP-011 | Employee / `GET /employees` | Unauthenticated | none | `GET /employees` with no `Authorization` header | `error.code = "AUTH_NOT_AUTHENTICATED"` | 401 | n/a (read-only) | **P0** |
| TC-EMP-012 | Employee / `GET /employees` | Authenticated but missing `employee:read` | user with only `shift:read` | `GET /employees` | `error.code = "AUTH_FORBIDDEN"` | 403 | n/a (read-only) | **P0** |
| TC-EMP-013 | Employee / `GET /employees` | Token without `org_id` | `NO_ORG_USER` | `GET /employees` | `error.code = "TENANT_UNRESOLVED"` | 400 | n/a (read-only) | P1 |

### 3.2 Create — `POST /employees`

| ID | Module / API | Test Scenario | Preconditions | Request / Input | Expected Result | HTTP | Database Verification | Priority |
|---|---|---|---|---|---|---|---|---|
| TC-EMP-014 | Employee / `POST /employees` | Onboard employee (happy path) | `ADMIN_USER`; `BRANCH_1`/`DEPT_1`/`DESIG_1` active | `POST /employees` `{"employee_name":"Asha Rao","gender":"Female","mobile_country_code":"+91","mobile_number":"9876543210","email":"asha@acme.test","master_branch_id":1,"dept_id":1,"designation_id":1,"date_of_joining":"2026-07-01","salary_type":"Monthly","monthly_salary":"45000.00"}` | `data.employee_id` present; `data.employee_code` server-generated; `data.employment_status = "active"`; `data.device_enrollment = []` | 201 | `SELECT employee_code, employment_status, org_id FROM employees WHERE employee_id=:id` → non-null code, `active`, `1` | P1 |
| TC-EMP-015 | Employee / `POST /employees` | `employee_code` is server-generated and NOT client-settable | `ADMIN_USER` | Same body **plus** `"employee_code":"HACK-1"` | Extra key is ignored (not in `EmployeeCreateRequest`); stored code follows the server prefix/pad format | 201 | `SELECT employee_code FROM employees WHERE employee_id=:id` → `<> 'HACK-1'` | **P0** |
| TC-EMP-016 | Employee / `POST /employees` | `employment_status` is not client-settable (mass-assignment guard) | `ADMIN_USER` | Body plus `"employment_status":"terminated"` | Ignored; employee created `active` | 201 | `SELECT employment_status FROM employees WHERE employee_id=:id` → `active` | **P0** |
| TC-EMP-017 | Employee / `POST /employees` | Salary is dropped for a caller without `employee_salary:read` | `HR_USER` upgraded with `employee:create` but **no** `employee_salary:read` | Body with `"salary_type":"Monthly","monthly_salary":"99999.00"` | Employee created; salary silently **not persisted**; response `salary = null` | 201 | `SELECT salary_type, monthly_salary, payroll_group_id FROM employees WHERE employee_id=:id` → `NULL, NULL, NULL` | **P0** |
| TC-EMP-018 | Employee / `POST /employees` | Salary persisted for `employee_salary:read` holder | `PAYROLL_USER` + `employee:create` | Body with `"salary_type":"Monthly","monthly_salary":"45000.00"` | `data.salary.monthly_salary = "45000.00"` | 201 | `SELECT monthly_salary FROM employees WHERE employee_id=:id` → `45000.00` | **P0** |
| TC-EMP-019 | Employee / `POST /employees` | Missing required fields | `ADMIN_USER` | `POST /employees` `{"employee_name":"X"}` | `VALIDATION_ERROR`; `error.details[]` names `gender`, `mobile_number`, `master_branch_id`, `dept_id`, `designation_id`, `date_of_joining` | 422 | `SELECT count(*) FROM employees WHERE employee_name='X'` → `0` | P2 |
| TC-EMP-020 | Employee / `POST /employees` | **Wrong enum casing** — `gender` | `ADMIN_USER` | Valid body but `"gender":"male"` (lowercase) | `VALIDATION_ERROR`; allowed values are exactly `Male\|Female\|Other` | 422 | no row inserted | P2 |
| TC-EMP-021 | Employee / `POST /employees` | **Wrong enum casing** — `salary_type` | `ADMIN_USER` | Valid body but `"salary_type":"monthly"` | `VALIDATION_ERROR`; allowed `Monthly\|Hourly\|Compliance` | 422 | no row inserted | P2 |
| TC-EMP-022 | Employee / `POST /employees` | Invalid email format | `ADMIN_USER` | `"email":"not-an-email"` | `VALIDATION_ERROR` (`invalid email format`) | 422 | no row inserted | P2 |
| TC-EMP-023 | Employee / `POST /employees` | Invalid phone (too short / non-numeric) | `ADMIN_USER` | `"mobile_number":"12"` | `VALIDATION_ERROR` (`invalid phone number`, 7–15 digits) | 422 | no row inserted | P2 |
| TC-EMP-024 | Employee / `POST /employees` | Boundary: `employee_name` length 1 (min 2) and 201 (max 200) | `ADMIN_USER` | `"employee_name":"A"` then a 201-char name | Both `VALIDATION_ERROR` | 422 | no rows inserted | P2 |
| TC-EMP-025 | Employee / `POST /employees` | Negative salary | `PAYROLL_USER` + create | `"monthly_salary":"-1.00"` | `VALIDATION_ERROR` (`ge=0`) | 422 | no row inserted | **P0** |
| TC-EMP-026 | Employee / `POST /employees` | Unknown / inactive branch | `ADMIN_USER` | `"master_branch_id":999999` | `error.code = "org_hierarchy_mismatch"` (message names the branch leg) | 422 | no row inserted | P1 |
| TC-EMP-027 | Employee / `POST /employees` | Unknown department | `ADMIN_USER` | `"dept_id":999999` | `error.code = "org_hierarchy_mismatch"` | 422 | no row inserted | P1 |
| TC-EMP-028 | Employee / `POST /employees` | Unknown designation | `ADMIN_USER` | `"designation_id":999999` | `error.code = "org_hierarchy_mismatch"` | 422 | no row inserted | P1 |
| TC-EMP-029 | Employee / `POST /employees` | **Cross-tenant FK**: ORG_B's branch supplied by an ORG_A caller | `ADMIN_USER` | `"master_branch_id":{BRANCH_B1}` | `org_hierarchy_mismatch` — the branch is not visible in ORG_A, so it cannot be borrowed | 422 | `SELECT count(*) FROM employees WHERE org_id=1 AND master_branch_id=:branch_b1` → `0` | **P0** |
| TC-EMP-030 | Employee / `POST /employees` | Self-service user requested without email | `ADMIN_USER` | `"create_self_service_user":true` and `email` omitted | `error.code = "SELF_SERVICE_EMAIL_REQUIRED"` | 422 | `SELECT count(*) FROM users WHERE org_id=1 AND name='...'` → unchanged | P2 |
| TC-EMP-031 | Employee / `POST /employees` | Self-service user with an email already taken | `ADMIN_USER`; a `users` row already holds `dup@acme.test` in ORG_A | `"create_self_service_user":true,"email":"dup@acme.test"` | `error.code = "USER_EMAIL_EXISTS"` | 409 | `SELECT count(*) FROM employees WHERE email='dup@acme.test'` → `0` (whole transaction rolled back) | P1 |
| TC-EMP-032 | Employee / `POST /employees` | Self-service user with a mobile already taken | `ADMIN_USER`; `users` row with that mobile | `"create_self_service_user":true` + duplicate mobile | `error.code = "USER_MOBILE_EXISTS"` | 409 | no `employees` row inserted | P1 |
| TC-EMP-033 | Employee / `POST /employees` | Self-service user created and linked | `ADMIN_USER` | `"create_self_service_user":true,"email":"new@acme.test"` | 201 | 201 | `SELECT count(*) FROM users WHERE org_id=1 AND email='new@acme.test'` → `1` | P1 |
| TC-EMP-034 | Employee / `POST /employees` | **Concurrency**: N identical creates fired simultaneously | `ADMIN_USER`; 10 parallel requests, identical body | Exactly one `201`; the rest fail cleanly. Any `employee_code` race is serialised by the advisory lock — **no 500** and **no duplicate code** | 201 / 409 | 201 + 409 `CONFLICT` | `SELECT employee_code, count(*) FROM employees WHERE org_id=1 GROUP BY 1 HAVING count(*)>1` → `0 rows` | **P0** |

### 3.3 Read one — `GET /employees/{employee_id}`

| ID | Module / API | Test Scenario | Preconditions | Request / Input | Expected Result | HTTP | Database Verification | Priority |
|---|---|---|---|---|---|---|---|---|
| TC-EMP-035 | Employee / `GET /employees/{id}` | Full profile for a privileged caller | `PAYROLL_USER` | `GET /employees/{EMP_001}` | `data.salary.monthly_salary = "50000.00"`; `data.bank_details` has 1 entry with `account_number` + `ifsc_code`; `branch`/`department`/`designation` refs present | 200 | n/a (read-only) | **P0** |
| TC-EMP-036 | Employee / `GET /employees/{id}` | **Sensitive-data gating**: `employee:read` only ⇒ sections OMITTED, not 403 | `HR_USER` | `GET /employees/{EMP_001}` | HTTP **200** (not 403). `data.salary` is `null`; `data.bank_details` is `[]`. All non-sensitive fields (name, code, branch, status) are present | 200 | Row is unchanged and still holds the data: `SELECT monthly_salary FROM employees WHERE employee_id=:emp1` → `50000.00`; `SELECT count(*) FROM employee_bank_details WHERE employee_id=:emp1 AND is_deleted=false` → `1` — i.e. the API omitted, the DB did not lose data | **P0** |
| TC-EMP-037 | Employee / `GET /employees/{id}` | Documents are NOT salary-gated (metadata only, never the storage key) | `HR_USER` | `GET /employees/{EMP_001}` | `data.documents[0]` present with `document_id`, `document_type`, `original_filename`, `file_size_bytes`; **no** `file_url` key anywhere in the payload | 200 | `SELECT file_url FROM employee_documents WHERE document_id=:d` → non-null in DB but absent from the wire | **P0** |
| TC-EMP-038 | Employee / `GET /employees/{id}` | Nested satellites returned | `ADMIN_USER` | `GET /employees/{EMP_001}` | `emergency_contacts`, `references`, `tags`, `status_history` populated | 200 | n/a (read-only) | P1 |
| TC-EMP-039 | Employee / `GET /employees/{id}` | Unknown id | `ADMIN_USER` | `GET /employees/99999999` | Error envelope; **404** with `error.code = "not_found"` (see [DEF-01](#appendix-a--error-code-drift-defects) — `EMPLOYEE_NOT_FOUND` is defined but never raised) | 404 | n/a (read-only) | P1 |
| TC-EMP-040 | Employee / `GET /employees/{id}` | **Multi-tenant**: ORG_A caller fetches an ORG_B employee ⇒ 404, never 403 | `ADMIN_USER` | `GET /employees/{EMP_B01}` | **404** (`not_found`). Must NOT be 403 — a 403 would leak that the id exists | 404 | `SELECT org_id FROM employees WHERE employee_id=:emp_b01` → `2` (row untouched) | **P0** |
| TC-EMP-041 | Employee / `GET /employees/{id}` | Non-integer path param | `ADMIN_USER` | `GET /employees/abc` | `VALIDATION_ERROR` | 422 | n/a (read-only) | P3 |

### 3.4 Update — `PATCH /employees/{employee_id}`

| ID | Module / API | Test Scenario | Preconditions | Request / Input | Expected Result | HTTP | Database Verification | Priority |
|---|---|---|---|---|---|---|---|---|
| TC-EMP-042 | Employee / `PATCH /employees/{id}` | Partial update of a single field | `ADMIN_USER` | `PATCH /employees/{EMP_001}` `{"display_name":"Ash"}` | 200; only that field changes | 200 | `SELECT display_name, employee_name FROM employees WHERE employee_id=:emp1` → `Ash`, name unchanged | P1 |
| TC-EMP-043 | Employee / `PATCH /employees/{id}` | Salary edit is silently dropped without `employee_salary:read` | `HR_USER` + `employee:edit` | `PATCH /employees/{EMP_001}` `{"monthly_salary":"1.00"}` | 200; the salary field is stripped before the write | 200 | `SELECT monthly_salary FROM employees WHERE employee_id=:emp1` → still `50000.00` | **P0** |
| TC-EMP-044 | Employee / `PATCH /employees/{id}` | Org reassignment re-validates the hierarchy | `ADMIN_USER` | `PATCH /employees/{EMP_001}` `{"dept_id":999999}` | `error.code = "org_hierarchy_mismatch"` | 422 | `SELECT dept_id FROM employees WHERE employee_id=:emp1` → unchanged | P1 |
| TC-EMP-045 | Employee / `PATCH /employees/{id}` | Cross-org employee | `ADMIN_USER` | `PATCH /employees/{EMP_B01}` `{"display_name":"x"}` | **404** `not_found` | 404 | `SELECT display_name FROM employees WHERE employee_id=:emp_b01` → unchanged | **P0** |
| TC-EMP-046 | Employee / `PATCH /employees/{id}` | Missing `employee:edit` | `HR_USER` | `PATCH /employees/{EMP_001}` `{"display_name":"x"}` | `AUTH_FORBIDDEN` | 403 | row unchanged | **P0** |
| TC-EMP-047 | Employee / `PATCH /employees/{id}` | Empty body is a no-op, not an error | `ADMIN_USER` | `PATCH /employees/{EMP_001}` `{}` | 200; audit records "Updated fields: none" | 200 | `SELECT updated_at FROM employees WHERE employee_id=:emp1` → row still present, no field changed | P3 |

### 3.5 Status lifecycle — activate / deactivate / terminate / exit / rehire

| ID | Module / API | Test Scenario | Preconditions | Request / Input | Expected Result | HTTP | Database Verification | Priority |
|---|---|---|---|---|---|---|---|---|
| TC-EMP-048 | Employee / `POST /employees/{id}/deactivate` | active → inactive | `ADMIN_USER`; `EMP_001` active | `POST /employees/{EMP_001}/deactivate` `{"reason":"sabbatical","effective_date":"2026-07-11"}` | `data.employment_status = "inactive"` | 200 | `SELECT employment_status FROM employees WHERE employee_id=:emp1` → `inactive`; `SELECT count(*) FROM employee_status_history WHERE employee_id=:emp1` → **increments by 1**; newest row has `previous_status='active'`, `new_status='inactive'`, `changed_by=:actor`, `reason='sabbatical'` | **P0** |
| TC-EMP-049 | Employee / `POST /employees/{id}/activate` | inactive → active | `ADMIN_USER`; `EMP_INACTIVE` | `POST /employees/{EMP_INACTIVE}/activate` `{}` (body optional) | `data.employment_status = "active"` | 200 | `SELECT new_status, previous_status FROM employee_status_history WHERE employee_id=:e ORDER BY status_history_id DESC LIMIT 1` → `('active','inactive')`; `effective_date` defaults to today | P1 |
| TC-EMP-050 | Employee / `POST /employees/{id}/activate` | No-op transition rejected | `ADMIN_USER`; `EMP_001` already active | `POST /employees/{EMP_001}/activate` | `error.code = "EMPLOYEE_STATUS_UNCHANGED"` | 409 | `SELECT count(*) FROM employee_status_history WHERE employee_id=:emp1` → **unchanged** (no history row for a rejected transition) | P1 |
| TC-EMP-051 | Employee / `POST /employees/{id}/terminate` | Terminate sets `date_of_leaving` and writes history | `ADMIN_USER`; `EMP_002` active | `POST /employees/{EMP_002}/terminate` `{"effective_date":"2026-07-31","reason":"resigned"}` | `data.employment_status = "terminated"`; `data.date_of_leaving = "2026-07-31"` | 200 | `SELECT employment_status, date_of_leaving FROM employees WHERE employee_id=:emp2` → `('terminated','2026-07-31')` (leaving date defaults to `effective_date`); `employee_status_history` +1 row `new_status='terminated'` | **P0** |
| TC-EMP-052 | Employee / `POST /employees/{id}/terminate` | Explicit `date_of_leaving` overrides the default | `ADMIN_USER` | `{"effective_date":"2026-07-31","date_of_leaving":"2026-08-15"}` | 200 | 200 | `SELECT date_of_leaving FROM employees WHERE employee_id=:e` → `2026-08-15` | P2 |
| TC-EMP-053 | Employee / `POST /employees/{id}/terminate` | **Terminal**: re-terminate is rejected | `ADMIN_USER`; `EMP_TERMINATED` | `POST /employees/{EMP_TERMINATED}/terminate` `{"effective_date":"2026-08-01"}` | `error.code = "EMPLOYEE_ALREADY_TERMINATED"` | 409 | `SELECT date_of_leaving FROM employees WHERE employee_id=:t` → **unchanged**; `employee_status_history` count unchanged | **P0** |
| TC-EMP-054 | Employee / `POST /employees/{id}/activate` | **Terminal**: a terminated employee cannot be re-activated via `/activate` | `ADMIN_USER`; `EMP_TERMINATED` | `POST /employees/{EMP_TERMINATED}/activate` | `error.code = "EMPLOYEE_ALREADY_TERMINATED"` (only `/rehire` may bring them back) | 409 | `SELECT employment_status FROM employees WHERE employee_id=:t` → still `terminated` | **P0** |
| TC-EMP-055 | Employee / `POST /employees/{id}/rehire` | Rehire a terminated employee, preserving history | `ADMIN_USER`; `EMP_TERMINATED` | `POST /employees/{EMP_TERMINATED}/rehire` `{"date_of_joining":"2026-09-01"}` | `data.employment_status = "active"`; `data.date_of_leaving = null` | 200 | `SELECT employment_status, date_of_joining, date_of_leaving FROM employees WHERE employee_id=:t` → `('active','2026-09-01',NULL)`; `SELECT count(*) FROM employee_status_history WHERE employee_id=:t` → **increments by 1** (prior rows retained), newest `reason='rehire'` | **P0** |
| TC-EMP-056 | Employee / `POST /employees/{id}/rehire` | Rehiring an already-active employee | `ADMIN_USER`; `EMP_001` | `POST /employees/{EMP_001}/rehire` `{"date_of_joining":"2026-09-01"}` | `error.code = "EMPLOYEE_ALREADY_ACTIVE"` | 409 | `date_of_joining` unchanged | P1 |
| TC-EMP-057 | Employee / `POST /employees/{id}/rehire` | Rehire requires `employee:create` (not `edit`) | user with `employee:edit` only | `POST /employees/{EMP_TERMINATED}/rehire` `{...}` | `AUTH_FORBIDDEN` | 403 | status unchanged | P1 |
| TC-EMP-058 | Employee / `POST /employees/{id}/exit` | Deprecated exit alias performs the terminal transition | `ADMIN_USER` (needs `employee:delete`); `EMP_002` active | `POST /employees/{EMP_002}/exit` `{"resignation_date":"2026-07-01","last_working_day":"2026-07-31","reason":"personal"}` | 200; status `terminated`; route flagged `deprecated` in OpenAPI | 200 | `SELECT employment_status, date_of_leaving FROM employees WHERE employee_id=:emp2` → `('terminated','2026-07-31')`; `employee_status_history` +1 | P1 |
| TC-EMP-059 | Employee / `POST /employees/{id}/exit` | `last_working_day` before `resignation_date` | `ADMIN_USER` | `{"resignation_date":"2026-07-31","last_working_day":"2026-07-01"}` | `VALIDATION_ERROR` (schema `model_validator`; the service re-checks with `invalid_exit_dates` for non-HTTP callers) | 422 | no status change, no history row | P2 |
| TC-EMP-060 | Employee / `POST /employees/{id}/exit` | Exiting an already-exited employee | `ADMIN_USER`; `EMP_TERMINATED` | `POST /employees/{EMP_TERMINATED}/exit` `{...valid dates...}` | `error.code = "EMPLOYEE_ALREADY_EXITED"` | 409 | row unchanged | P1 |
| TC-EMP-061 | Employee / `POST /employees/{id}/exit` | Exit requires `employee:delete` | `ADMIN_USER` minus `employee:delete` | `POST /employees/{EMP_002}/exit` | `AUTH_FORBIDDEN` | 403 | row unchanged | P1 |
| TC-EMP-062 | Employee / status endpoints | Cross-org lifecycle call | `ADMIN_USER` | `POST /employees/{EMP_B01}/terminate` `{"effective_date":"2026-07-31"}` | **404** `not_found` (not 403) | 404 | `SELECT employment_status FROM employees WHERE employee_id=:emp_b01` → unchanged `active` | **P0** |

### 3.6 Transfer & promote

| ID | Module / API | Test Scenario | Preconditions | Request / Input | Expected Result | HTTP | Database Verification | Priority |
|---|---|---|---|---|---|---|---|---|
| TC-EMP-063 | Employee / `POST /employees/{id}/transfer` | Transfer branch + department | `ADMIN_USER` | `POST /employees/{EMP_001}/transfer` `{"master_branch_id":{BRANCH_2},"dept_id":{DEPT_2},"effective_date":"2026-08-01","reason":"reorg"}` | 200; both FKs updated in the response | 200 | `SELECT master_branch_id, dept_id FROM employees WHERE employee_id=:emp1` → `(BRANCH_2, DEPT_2)`. **No transfer table exists** — the context is audited: `SELECT count(*) FROM activity_logs WHERE module='Employee Management' AND title='Employee transferred' AND employee_id=:emp1` → `1`, `description` contains `effective 2026-08-01` and `reason: reorg` | P1 |
| TC-EMP-064 | Employee / `POST /employees/{id}/transfer` | Transfer to an unknown branch | `ADMIN_USER` | `{"master_branch_id":999999}` | `error.code = "BRANCH_NOT_FOUND"` | 404 | `SELECT master_branch_id FROM employees WHERE employee_id=:emp1` → unchanged | P1 |
| TC-EMP-065 | Employee / `POST /employees/{id}/transfer` | Transfer to an unknown department | `ADMIN_USER` | `{"dept_id":999999}` | `error.code = "DEPARTMENT_NOT_FOUND"` | 404 | `dept_id` unchanged | P1 |
| TC-EMP-066 | Employee / `POST /employees/{id}/transfer` | Transfer to ORG_B's branch | `ADMIN_USER` | `{"master_branch_id":{BRANCH_B1}}` | `error.code = "BRANCH_NOT_FOUND"` — a foreign tenant's branch is simply not found | 404 | `SELECT master_branch_id FROM employees WHERE employee_id=:emp1` → unchanged | **P0** |
| TC-EMP-067 | Employee / `POST /employees/{id}/transfer` | Neither target supplied | `ADMIN_USER` | `POST /employees/{EMP_001}/transfer` `{"reason":"x"}` | `VALIDATION_ERROR` ("at least one of master_branch_id or dept_id is required") | 422 | row unchanged | P2 |
| TC-EMP-068 | Employee / `POST /employees/{id}/promote` | Promote designation + salary revision | `PAYROLL_USER` + `employee:edit` | `POST /employees/{EMP_001}/promote` `{"designation_id":{DESIG_2},"monthly_salary":"60000.00","effective_date":"2026-08-01","reason":"annual"}` | 200; `data.designation_id = DESIG_2`; `data.salary.monthly_salary = "60000.00"` | 200 | `SELECT designation_id, monthly_salary FROM employees WHERE employee_id=:emp1` → `(DESIG_2, 60000.00)`; activity log row `title='Employee promoted'` with `effective`/`reason` context | **P0** |
| TC-EMP-069 | Employee / `POST /employees/{id}/promote` | **Salary revision ignored** without `employee_salary:read` | `HR_USER` + `employee:edit` | `{"designation_id":{DESIG_2},"monthly_salary":"999999.00"}` | 200; designation changes, salary does not; `data.salary = null` | 200 | `SELECT designation_id, monthly_salary FROM employees WHERE employee_id=:emp1` → `(DESIG_2, 50000.00)` — **money unchanged** | **P0** |
| TC-EMP-070 | Employee / `POST /employees/{id}/promote` | Unknown designation | `ADMIN_USER` | `{"designation_id":999999}` | `error.code = "DESIGNATION_NOT_FOUND"` | 404 | `designation_id` unchanged | P1 |
| TC-EMP-071 | Employee / `POST /employees/{id}/promote` | Negative salary | `PAYROLL_USER` | `{"designation_id":2,"monthly_salary":"-5.00"}` | `VALIDATION_ERROR` (`ge=0`) | 422 | row unchanged | **P0** |

### 3.7 Documents (multipart upload / download / delete)

| ID | Module / API | Test Scenario | Preconditions | Request / Input | Expected Result | HTTP | Database Verification | Priority |
|---|---|---|---|---|---|---|---|---|
| TC-EMP-072 | Employee / `POST /employees/{id}/documents` | Upload a PDF (happy path, `multipart/form-data`) | `DOC_USER` (`employee_document:edit`) | `POST /employees/{EMP_001}/documents` — `Content-Type: multipart/form-data`; parts: `document_type=pan_card`, `file=@FILE_PDF_OK` | 201; `data` = `EmployeeDocumentSchema` with `document_id`, `document_type`, `original_filename="contract.pdf"`, `file_size_bytes=12288`, `uploaded_by=<actor>`. **`file_url` is absent from the response** | 201 | `SELECT file_url, original_filename, file_size_bytes, uploaded_by FROM employee_documents WHERE document_id=:d` → `file_url` matches `^employees/{EMP_001}/[0-9a-f]{32}\.pdf$` (server-generated key, client filename not used as a path component) | **P0** |
| TC-EMP-073 | Employee / `POST /employees/{id}/documents` | **Client-supplied `file_url` is rejected** | `DOC_USER` | `POST /employees/{EMP_001}/documents` with a **JSON** body `{"document_type":"pan_card","file_url":"/etc/passwd"}` | `VALIDATION_ERROR` — the route requires the multipart `file` part; `file_url` is not a field of this endpoint | 422 | `SELECT count(*) FROM employee_documents WHERE employee_id=:emp1 AND file_url='/etc/passwd'` → `0` | **P0** |
| TC-EMP-074 | Employee / `POST /employees/{id}/documents` | **Path traversal in the filename cannot escape the upload dir** | `DOC_USER` | multipart with `file=@FILE_TRAVERSAL` (filename `../../etc/passwd.pdf`) | 201 — the upload succeeds but the name is sanitised and only its extension is honoured | 201 | `SELECT file_url, original_filename FROM employee_documents WHERE document_id=:d` → `file_url` matches `^employees/{EMP_001}/[0-9a-f]{32}\.pdf$` and contains **no** `..`; on disk the file resolves inside `settings.upload_dir`; `/etc/passwd` is untouched | **P0** |
| TC-EMP-075 | Employee / `POST /employees/{id}/documents` | Unsupported extension | `DOC_USER` | multipart `file=@FILE_EXE` | `error.code = "UNSUPPORTED_FILE_TYPE"` (allowlist: pdf, png, jpg, jpeg) | 422 | `SELECT count(*) FROM employee_documents WHERE employee_id=:emp1` → unchanged; nothing written under `upload_dir` | **P0** |
| TC-EMP-076 | Employee / `POST /employees/{id}/documents` | Content-type / extension mismatch | `DOC_USER` | multipart: filename `id.png` but `Content-Type: application/pdf` | `error.code = "UNSUPPORTED_FILE_TYPE"` | 422 | no row inserted | **P0** |
| TC-EMP-077 | Employee / `POST /employees/{id}/documents` | Oversize upload | `DOC_USER` | multipart `file=@FILE_HUGE` | `error.code = "FILE_TOO_LARGE"` (message quotes the MB limit); the stream is abandoned, never fully buffered | 422 | no `employee_documents` row; no partial `.part` file left under `upload_dir` | **P0** |
| TC-EMP-078 | Employee / `POST /employees/{id}/documents` | Empty upload | `DOC_USER` | multipart `file=@FILE_EMPTY` (0 bytes) | `error.code = "EMPTY_UPLOAD"` | 422 | no row inserted | **P0** |
| TC-EMP-079 | Employee / `POST /employees/{id}/documents` | Boundary: file exactly at `MAX_UPLOAD_SIZE_MB` | `DOC_USER` | multipart with a PDF of exactly `max_upload_size_bytes` | 201 (`>` is the rejection predicate, not `>=`) | 201 | `SELECT file_size_bytes FROM employee_documents WHERE document_id=:d` → equals the configured max | P2 |
| TC-EMP-080 | Employee / `POST /employees/{id}/documents` | Invalid `document_type` enum | `DOC_USER` | `document_type=birth_certificate` | `VALIDATION_ERROR` (allowed: `aadhar_card`, `driving_licence`, `pan_card`, `passport_photo`, `other`) | 422 | no row inserted | P2 |
| TC-EMP-081 | Employee / `POST /employees/{id}/documents` | Missing `employee_document:edit` | `HR_USER` | multipart `file=@FILE_PDF_OK` | `AUTH_FORBIDDEN` | 403 | no row inserted; no file written | **P0** |
| TC-EMP-082 | Employee / `POST /employees/{id}/documents` | Orphan cleanup when the metadata write fails | `DOC_USER`; force a DB error inside the transaction | multipart `file=@FILE_PDF_OK` | 5xx / error envelope | 500 | The stored object is deleted again — no file under `upload_dir/employees/{EMP_001}/` and `SELECT count(*) FROM employee_documents WHERE employee_id=:emp1` unchanged | P1 |
| TC-EMP-083 | Employee / `GET /employees/{id}/documents` | List document metadata | `HR_USER` (`employee:read` suffices) | `GET /employees/{EMP_001}/documents` | Array of `EmployeeDocumentSchema`; **no** `file_url` key on any item | 200 | Soft-deleted rows excluded: list length = `SELECT count(*) FROM employee_documents WHERE employee_id=:emp1 AND is_deleted=false` | **P0** |
| TC-EMP-084 | Employee / `GET /employees/{id}/documents/{document_id}` | Download streams the bytes | `HR_USER` | `GET /employees/{EMP_001}/documents/{DOC_1}` | `FileResponse`: `Content-Type: application/pdf`, `Content-Disposition` filename = the stored `original_filename`; body bytes identical to `FILE_PDF_OK` | 200 | n/a (read-only) | P1 |
| TC-EMP-085 | Employee / `GET /employees/{id}/documents/{document_id}` | Unknown document id | `ADMIN_USER` | `GET /employees/{EMP_001}/documents/99999999` | `error.code = "DOCUMENT_NOT_FOUND"` | 404 | n/a (read-only) | P1 |
| TC-EMP-086 | Employee / `GET /employees/{id}/documents/{document_id}` | **Cross-tenant satellite read** — ORG_B's document id | `ADMIN_USER`; `DOC_B1` belongs to `EMP_B01` (ORG_B) | `GET /employees/{EMP_001}/documents/{DOC_B1}` | `error.code = "DOCUMENT_NOT_FOUND"` (404) — the lookup is scoped through the parent employee's `org_id`; the bytes must never stream across tenants | 404 | `SELECT e.org_id FROM employee_documents d JOIN employees e USING(employee_id) WHERE d.document_id=:doc_b1` → `2` (untouched) | **P0** |
| TC-EMP-087 | Employee / `GET /employees/{id}/documents/{document_id}` | Document id belonging to *another employee in the same org* | `ADMIN_USER` | `GET /employees/{EMP_002}/documents/{DOC_1}` (DOC_1 belongs to EMP_001) | `error.code = "DOCUMENT_NOT_FOUND"` | 404 | n/a (read-only) | **P0** |
| TC-EMP-088 | Employee / `GET /employees/{id}/documents/{document_id}` | Metadata row exists but the object is missing on disk | `ADMIN_USER`; delete the file under `upload_dir` | `GET /employees/{EMP_001}/documents/{DOC_1}` | `error.code = "DOCUMENT_NOT_FOUND"` (the storage `FILE_NOT_FOUND` / `INVALID_STORAGE_KEY` is re-mapped, never leaked) | 404 | `SELECT count(*) FROM employee_documents WHERE document_id=:d` → `1` (row retained) | P1 |
| TC-EMP-089 | Employee / `DELETE /employees/{id}/documents/{document_id}` | Soft-delete a document | `ADMIN_USER` | `DELETE /employees/{EMP_001}/documents/{DOC_1}` | Empty body | 204 | `SELECT is_deleted FROM employee_documents WHERE document_id=:doc1` → **`true`** (row RETAINED, not removed); subsequent `GET .../documents` omits it | **P0** |
| TC-EMP-090 | Employee / `DELETE /employees/{id}/documents/{document_id}` | Delete an unknown document | `ADMIN_USER` | `DELETE /employees/{EMP_001}/documents/99999999` | `error.code = "DOCUMENT_NOT_FOUND"` | 404 | no rows changed | P2 |
| TC-EMP-091 | Employee / `POST /employees/{id}/photo` | Set the profile photo path (JSON, metadata only) | `ADMIN_USER` | `POST /employees/{EMP_001}/photo` `{"file_url":"employees/1001/photo.png","mime":"image/png"}` | 200; `data.profile_photo_url` set | 200 | `SELECT profile_photo_url FROM employees WHERE employee_id=:emp1` → `employees/1001/photo.png` | P1 |
| TC-EMP-092 | Employee / `POST /employees/{id}/photo` | Empty `file_url` | `ADMIN_USER` | `{"file_url":""}` | `VALIDATION_ERROR` (`min_length=1`) | 422 | column unchanged | P2 |

### 3.8 Bank details (sensitive)

| ID | Module / API | Test Scenario | Preconditions | Request / Input | Expected Result | HTTP | Database Verification | Priority |
|---|---|---|---|---|---|---|---|---|
| TC-EMP-093 | Employee / `GET /employees/{id}/bank-details` | Privileged read | `PAYROLL_USER` | `GET /employees/{EMP_001}/bank-details` | Array with `account_number`, `ifsc_code`, `is_primary` | 200 | n/a (read-only) | **P0** |
| TC-EMP-094 | Employee / `GET /employees/{id}/bank-details` | **403 without `employee_salary:read`** (this route DOES 403 — unlike the embedded copy, which omits) | `HR_USER` | `GET /employees/{EMP_001}/bank-details` | `error.code = "AUTH_FORBIDDEN"` | **403** | n/a (read-only) | **P0** |
| TC-EMP-095 | Employee / `GET /employees/{id}/bank-details` | Cross-org employee | `PAYROLL_USER` | `GET /employees/{EMP_B01}/bank-details` | **404** `not_found` (not 403) | 404 | n/a (read-only) | **P0** |
| TC-EMP-096 | Employee / `POST /employees/{id}/bank-details` | Add a bank detail | `ADMIN_USER` | `POST /employees/{EMP_002}/bank-details` `{"bank_name":"HDFC","bank_branch_name":"MG Road","account_number":"12345678901","ifsc_code":"HDFC0001234","is_primary":true}` | 201; `data.bank_detail_id` present | 201 | `SELECT bank_name, account_number, ifsc_code, is_primary, is_deleted FROM employee_bank_details WHERE bank_detail_id=:id` → `('HDFC','12345678901','HDFC0001234',true,false)` | P1 |
| TC-EMP-097 | Employee / `POST /employees/{id}/bank-details` | **A new primary demotes the existing primary** | `ADMIN_USER`; `EMP_001` already has a primary row `BD_1` | `POST /employees/{EMP_001}/bank-details` `{"account_number":"999888777","ifsc_code":"ICIC0000123","is_primary":true}` | 201 | 201 | `SELECT count(*) FROM employee_bank_details WHERE employee_id=:emp1 AND is_primary=true AND is_deleted=false` → **`1`**; `SELECT is_primary FROM employee_bank_details WHERE bank_detail_id=:bd1` → `false` | **P0** |
| TC-EMP-098 | Employee / `POST /employees/{id}/bank-details` | Invalid IFSC format | `ADMIN_USER` | `{"ifsc_code":"BADIFSC"}` | `VALIDATION_ERROR` (`invalid IFSC code format` — 4 letters, `0`, 6 alphanumerics) | 422 | no row inserted | P2 |
| TC-EMP-099 | Employee / `POST /employees/{id}/bank-details` | IFSC is normalised to upper-case | `ADMIN_USER` | `{"ifsc_code":"hdfc0001234","account_number":"1234"}` | 201; response shows `HDFC0001234` | 201 | `SELECT ifsc_code FROM employee_bank_details WHERE bank_detail_id=:id` → `HDFC0001234` | P2 |
| TC-EMP-100 | Employee / `POST /employees/{id}/bank-details` | Non-alphanumeric account number | `ADMIN_USER` | `{"account_number":"12-34/56"}` | `VALIDATION_ERROR` (`account number must be alphanumeric`) | 422 | no row inserted | P2 |
| TC-EMP-101 | Employee / `POST /employees/{id}/bank-details` | Account number over 30 chars | `ADMIN_USER` | 31-char numeric account | `VALIDATION_ERROR` (`max_length=30`) | 422 | no row inserted | P2 |
| TC-EMP-102 | Employee / `PATCH /employees/{id}/bank-details/{bank_detail_id}` | Partial update | `ADMIN_USER` | `PATCH .../bank-details/{BD_1}` `{"bank_name":"SBI"}` | 200 | 200 | `SELECT bank_name, account_number FROM employee_bank_details WHERE bank_detail_id=:bd1` → `SBI`, account unchanged | P1 |
| TC-EMP-103 | Employee / `PATCH /employees/{id}/bank-details/{bank_detail_id}` | Promoting a row to primary demotes the other | `ADMIN_USER`; BD_1 primary, BD_2 not | `PATCH .../bank-details/{BD_2}` `{"is_primary":true}` | 200 | 200 | `SELECT bank_detail_id FROM employee_bank_details WHERE employee_id=:emp1 AND is_primary=true AND is_deleted=false` → exactly `{BD_2}` | **P0** |
| TC-EMP-104 | Employee / `PATCH /employees/{id}/bank-details/{bank_detail_id}` | Unknown bank detail | `ADMIN_USER` | `PATCH .../bank-details/99999999` `{"bank_name":"X"}` | `error.code = "BANK_DETAIL_NOT_FOUND"` | 404 | no row changed | P1 |
| TC-EMP-105 | Employee / `PATCH /employees/{id}/bank-details/{bank_detail_id}` | Bank detail of another employee | `ADMIN_USER` | `PATCH /employees/{EMP_002}/bank-details/{BD_1}` | `error.code = "BANK_DETAIL_NOT_FOUND"` | 404 | `SELECT employee_id FROM employee_bank_details WHERE bank_detail_id=:bd1` → still `EMP_001` | **P0** |
| TC-EMP-106 | Employee / `DELETE /employees/{id}/bank-details/{bank_detail_id}` | **Soft delete retains the row** | `ADMIN_USER` | `DELETE /employees/{EMP_001}/bank-details/{BD_1}` | Empty body | 204 | `SELECT is_deleted FROM employee_bank_details WHERE bank_detail_id=:bd1` → **`true`** and the row still exists (`SELECT count(*) … WHERE bank_detail_id=:bd1` → `1`); `GET .../bank-details` no longer lists it | **P0** |
| TC-EMP-107 | Employee / `DELETE /employees/{id}/bank-details/{bank_detail_id}` | Delete an unknown bank detail | `ADMIN_USER` | `DELETE .../bank-details/99999999` | `error.code = "BANK_DETAIL_NOT_FOUND"` | 404 | no change | P2 |

### 3.9 Emergency contacts

| ID | Module / API | Test Scenario | Preconditions | Request / Input | Expected Result | HTTP | Database Verification | Priority |
|---|---|---|---|---|---|---|---|---|
| TC-EMP-108 | Employee / `GET /employees/{id}/emergency-contacts` | List (non-deleted only) | `HR_USER` | `GET /employees/{EMP_001}/emergency-contacts` | Array of `EmployeeEmergencyContactSchema` | 200 | count = `SELECT count(*) FROM employee_emergency_contacts WHERE employee_id=:emp1 AND is_deleted=false` | P1 |
| TC-EMP-109 | Employee / `POST /employees/{id}/emergency-contacts` | Add a contact | `ADMIN_USER` | `POST .../emergency-contacts` `{"contact_country_code":"+91","contact_number":"9998887776","contact_person_name":"Meera","relation":"spouse"}` | 201 | 201 | `SELECT contact_person_name, contact_number, is_deleted FROM employee_emergency_contacts WHERE emergency_contact_id=:id` → `('Meera','9998887776',false)` | P1 |
| TC-EMP-110 | Employee / `POST /employees/{id}/emergency-contacts` | Invalid phone | `ADMIN_USER` | `{"contact_number":"abc","contact_person_name":"M"}` | `VALIDATION_ERROR` | 422 | no row inserted | P2 |
| TC-EMP-111 | Employee / `POST /employees/{id}/emergency-contacts` | Missing `contact_person_name` | `ADMIN_USER` | `{"contact_number":"9998887776"}` | `VALIDATION_ERROR` | 422 | no row inserted | P2 |
| TC-EMP-112 | Employee / `PATCH .../emergency-contacts/{id}` | Partial update | `ADMIN_USER` | `PATCH .../emergency-contacts/{EC_1}` `{"relation":"father"}` | 200 | 200 | `SELECT relation FROM employee_emergency_contacts WHERE emergency_contact_id=:ec1` → `father` | P1 |
| TC-EMP-113 | Employee / `PATCH .../emergency-contacts/{id}` | Unknown contact | `ADMIN_USER` | `PATCH .../emergency-contacts/99999999` `{"relation":"x"}` | `error.code = "EMERGENCY_CONTACT_NOT_FOUND"` | 404 | no change | P1 |
| TC-EMP-114 | Employee / `DELETE .../emergency-contacts/{id}` | Soft delete | `ADMIN_USER` | `DELETE .../emergency-contacts/{EC_1}` | Empty body | 204 | `SELECT is_deleted FROM employee_emergency_contacts WHERE emergency_contact_id=:ec1` → **`true`**; row retained | **P0** |
| TC-EMP-115 | Employee / `DELETE .../emergency-contacts/{id}` | Cross-employee contact id | `ADMIN_USER` | `DELETE /employees/{EMP_002}/emergency-contacts/{EC_1}` | `error.code = "EMERGENCY_CONTACT_NOT_FOUND"` | 404 | `SELECT is_deleted FROM employee_emergency_contacts WHERE emergency_contact_id=:ec1` → still `false` | **P0** |

### 3.10 References

| ID | Module / API | Test Scenario | Preconditions | Request / Input | Expected Result | HTTP | Database Verification | Priority |
|---|---|---|---|---|---|---|---|---|
| TC-EMP-116 | Employee / `GET /employees/{id}/references` | List ordered by `sort_order` | `HR_USER`; 2 references with `sort_order` 2 and 1 | `GET /employees/{EMP_001}/references` | Items ordered ascending by `sort_order` | 200 | count = `SELECT count(*) FROM employee_references WHERE employee_id=:emp1 AND is_deleted=false` | P2 |
| TC-EMP-117 | Employee / `POST /employees/{id}/references` | Add a reference | `ADMIN_USER` | `POST .../references` `{"reference_name":"Dr Rao","reference_country_code":"+91","reference_contact_number":"9871112222","sort_order":1}` | 201 | 201 | `SELECT reference_name, sort_order, is_deleted FROM employee_references WHERE reference_id=:id` → `('Dr Rao',1,false)` | P1 |
| TC-EMP-118 | Employee / `POST /employees/{id}/references` | Boundary: `sort_order` = 0 and 32768 | `ADMIN_USER` | `"sort_order":0` then `32768` | Both `VALIDATION_ERROR` (`ge=1`, `le=32767`) | 422 | no rows inserted | P2 |
| TC-EMP-119 | Employee / `PATCH .../references/{id}` | Partial update | `ADMIN_USER` | `PATCH .../references/{REF_1}` `{"sort_order":3}` | 200 | 200 | `SELECT sort_order FROM employee_references WHERE reference_id=:ref1` → `3` | P1 |
| TC-EMP-120 | Employee / `PATCH .../references/{id}` | Unknown reference | `ADMIN_USER` | `PATCH .../references/99999999` `{"sort_order":2}` | `error.code = "REFERENCE_NOT_FOUND"` | 404 | no change | P1 |
| TC-EMP-121 | Employee / `DELETE .../references/{id}` | Soft delete | `ADMIN_USER` | `DELETE .../references/{REF_1}` | Empty body | 204 | `SELECT is_deleted FROM employee_references WHERE reference_id=:ref1` → **`true`**; row retained | **P0** |
| TC-EMP-122 | Employee / `DELETE .../references/{id}` | Unknown reference | `ADMIN_USER` | `DELETE .../references/99999999` | `error.code = "REFERENCE_NOT_FOUND"` | 404 | no change | P2 |

### 3.11 Tags (hard delete) & status history

| ID | Module / API | Test Scenario | Preconditions | Request / Input | Expected Result | HTTP | Database Verification | Priority |
|---|---|---|---|---|---|---|---|---|
| TC-EMP-123 | Employee / `GET /employees/{id}/tags` | List tags | `HR_USER` | `GET /employees/{EMP_001}/tags` | Array of `EmployeeTagSchema` | 200 | n/a (read-only) | P2 |
| TC-EMP-124 | Employee / `POST /employees/{id}/tags` | Add a tag | `ADMIN_USER` | `POST .../tags` `{"tag_label":"Probation","tag_color":"#FF0000","is_status_tag":true}` | 201 | 201 | `SELECT tag_label, tag_color, is_status_tag, created_by FROM employee_tags WHERE tag_id=:id` → `('Probation','#FF0000',true,<actor>)` | P1 |
| TC-EMP-125 | Employee / `POST /employees/{id}/tags` | `tag_label` over 100 chars / `tag_color` over 10 chars | `ADMIN_USER` | 101-char label; then an 11-char colour | Both `VALIDATION_ERROR` | 422 | no rows inserted | P2 |
| TC-EMP-126 | Employee / `DELETE /employees/{id}/tags/{tag_id}` | **HARD delete** (the table has no `is_deleted` column) | `ADMIN_USER` | `DELETE /employees/{EMP_001}/tags/{TAG_1}` | Empty body | 204 | `SELECT count(*) FROM employee_tags WHERE tag_id=:tag1` → **`0`** — the row is physically gone (contrast with the soft-deleted satellites above) | **P0** |
| TC-EMP-127 | Employee / `DELETE /employees/{id}/tags/{tag_id}` | Unknown tag | `ADMIN_USER` | `DELETE .../tags/99999999` | `error.code = "TAG_NOT_FOUND"` | 404 | no rows removed | P1 |
| TC-EMP-128 | Employee / `DELETE /employees/{id}/tags/{tag_id}` | Tag id owned by another employee | `ADMIN_USER` | `DELETE /employees/{EMP_002}/tags/{TAG_1}` | `error.code = "TAG_NOT_FOUND"` | 404 | `SELECT count(*) FROM employee_tags WHERE tag_id=:tag1` → still `1` | **P0** |
| TC-EMP-129 | Employee / `GET /employees/{id}/status-history` | Read the audit trail of transitions | `HR_USER`; `EMP_001` has been deactivated then activated | `GET /employees/{EMP_001}/status-history` | Chronological array; each item has `previous_status`, `new_status`, `changed_by`, `reason`, `effective_date` | 200 | list length = `SELECT count(*) FROM employee_status_history WHERE employee_id=:emp1` | P1 |
| TC-EMP-130 | Employee / `GET /employees/{id}/status-history` | Cross-org | `ADMIN_USER` | `GET /employees/{EMP_B01}/status-history` | **404** `not_found` | 404 | n/a (read-only) | **P0** |

---

### 3.12 Emergency contacts & references — update / delete

The `PATCH` and `DELETE` routes on both satellites require **`employee:edit`** (not `employee:read`), delete is a
**soft** delete (`is_deleted = true`, the row is retained), and both scope the child row to its parent employee
*and* org via `get_by_id_in_org` — so a valid contact/reference id belonging to a **different employee** is a 404,
not a cross-record edit. `EMERGENCY_CONTACT_NOT_FOUND` and `REFERENCE_NOT_FOUND` are genuinely raised here
(unlike `EMPLOYEE_NOT_FOUND` — see Appendix A / DEF-01).

| ID | Module / API | Test Scenario | Preconditions | Request / Input | Expected Result | HTTP | Database Verification | Priority |
|---|---|---|---|---|---|---|---|---|
| TC-EMP-131 | Employee / `PATCH /employees/{id}/emergency-contacts/{emergency_contact_id}` | Update a contact's phone and relation | `ADMIN_USER`; `EMP_001` has contact `EC_1` | `PATCH .../emergency-contacts/{EC_1}` `{"contact_number":"9876500011","relation":"Brother"}` | 200; the updated contact is echoed | 200 | `SELECT contact_number, relation FROM employee_emergency_contacts WHERE id={EC_1}` → `9876500011`, `Brother`; `is_deleted` still `false` | P1 |
| TC-EMP-132 | Employee / `PATCH /employees/{id}/emergency-contacts/{emergency_contact_id}` | Unknown contact id | `ADMIN_USER` | `PATCH .../emergency-contacts/99999999` | `error.code = "EMERGENCY_CONTACT_NOT_FOUND"` | 404 | Nothing written — `SELECT count(*) FROM employee_emergency_contacts WHERE id=99999999` → `0` | P2 |
| TC-EMP-133 | Employee / `PATCH /employees/{id}/emergency-contacts/{emergency_contact_id}` | **Contact id owned by a different employee** | `ADMIN_USER`; `EC_1` belongs to `EMP_001` | `PATCH /employees/{EMP_002}/emergency-contacts/{EC_1}` | `EMERGENCY_CONTACT_NOT_FOUND` — the row is scoped to its parent employee, so this must not become a cross-record edit | 404 | `SELECT contact_number FROM employee_emergency_contacts WHERE id={EC_1}` → **unchanged** | P0 |
| TC-EMP-134 | Employee / `PATCH /employees/{id}/emergency-contacts/{emergency_contact_id}` | Requires `employee:edit`, not `employee:read` | A user with `employee:read` only | `PATCH .../emergency-contacts/{EC_1}` | `AUTH_FORBIDDEN` | 403 | Row unchanged | P0 |
| TC-EMP-135 | Employee / `DELETE /employees/{id}/emergency-contacts/{emergency_contact_id}` | **Soft** delete — the row is retained, not removed | `ADMIN_USER`; contact `EC_1` | `DELETE .../emergency-contacts/{EC_1}` | 204, empty body | 204 | `SELECT is_deleted FROM employee_emergency_contacts WHERE id={EC_1}` → **`true`** (the row still EXISTS — assert it was not hard-deleted); the contact no longer appears in `GET .../emergency-contacts` | P1 |
| TC-EMP-136 | Employee / `PATCH /employees/{id}/references/{reference_id}` | Update a reference's name and `sort_order` | `ADMIN_USER`; `EMP_001` has reference `REF_1` | `PATCH .../references/{REF_1}` `{"reference_name":"Dr Iyer","sort_order":3}` | 200; the updated reference is echoed | 200 | `SELECT reference_name, sort_order FROM employee_references WHERE id={REF_1}` → `Dr Iyer`, `3` | P1 |
| TC-EMP-137 | Employee / `PATCH /employees/{id}/references/{reference_id}` | **Cross-org**: Org A admin edits an Org B employee's reference | `ADMIN_USER` (ORG_A); `REF_B1` belongs to `EMP_B01` in ORG_B | `PATCH /employees/{EMP_B01}/references/{REF_B1}` | **404**, never 403 — a 403 would confirm the record exists and leak tenant data | 404 | `SELECT reference_name FROM employee_references WHERE id={REF_B1}` → **unchanged**; no ORG_A audit row references it | P0 |
| TC-EMP-138 | Employee / `DELETE /employees/{id}/references/{reference_id}` | Soft delete; then a second delete of the same id | `ADMIN_USER`; reference `REF_1` | `DELETE .../references/{REF_1}` twice | First 204; second `REFERENCE_NOT_FOUND` (the soft-deleted row is filtered out of the lookup) — delete is **not** silently idempotent | 204 → 404 | After the first: `SELECT is_deleted FROM employee_references WHERE id={REF_1}` → `true` and the row still exists. After the second: still exactly one row, `is_deleted=true` (no double-write) | P2 |


## 4. Shift Management

**Permission keys:** `shift`, `shift_assignment`, `shift_rotation`, `weekoff`, `roster` (each with read/create/edit/delete).

### 4.1 Shift master — `POST/GET/PATCH/DELETE /shifts`, `/shifts/{id}/restore`

| ID | Module / API | Test Scenario | Preconditions | Request / Input | Expected Result | HTTP | Database Verification | Priority |
|---|---|---|---|---|---|---|---|---|
| TC-SHF-001 | Shift / `POST /shifts` | Create a uniform fixed shift with one timing | `ADMIN_USER` | `POST /shifts` `{"shift_name":"Morning","shift_type":"fixed","is_uniform_time":true,"has_break_time":true,"day_timings":[{"day_of_week":null,"start_time":"09:00:00","end_time":"18:00:00","break_start_time":"13:00:00","break_end_time":"13:30:00"}]}` | 201; `data.shift_id`; `data.day_timings` has 1 row | 201 | `SELECT shift_name, shift_type, is_deleted, created_by FROM shifts WHERE shift_id=:id` → `('Morning','fixed',false,<actor>)`; `SELECT count(*) FROM shift_day_timings WHERE shift_id=:id AND day_of_week IS NULL` → `1` | P1 |
| TC-SHF-002 | Shift / `POST /shifts` | Create a per-day (advanced) shift, 7 timings | `ADMIN_USER` | `{"shift_name":"Rotating","is_uniform_time":false,"is_advanced_mode":true,"day_timings":[{"day_of_week":0,...},…,{"day_of_week":6,...}]}` | 201 | 201 | `SELECT count(*) FROM shift_day_timings WHERE shift_id=:id` → `7`; `SELECT count(DISTINCT day_of_week) …` → `7` | P1 |
| TC-SHF-003 | Shift / `POST /shifts` | Overnight shift needs `crosses_midnight` | `ADMIN_USER` | `day_timings:[{"start_time":"22:00:00","end_time":"06:00:00"}]` (no flag) | `VALIDATION_ERROR` — "end_time must be after start_time unless crosses_midnight is true" | 422 | `SELECT count(*) FROM shifts WHERE shift_name='Night'` → `0` | P2 |
| TC-SHF-004 | Shift / `POST /shifts` | Overnight shift accepted with `crosses_midnight=true` | `ADMIN_USER` | same timings + `"crosses_midnight":true` | 201 | 201 | `SELECT start_time, end_time FROM shift_day_timings WHERE shift_id=:id` → `('22:00','06:00')`; **`crosses_midnight` is transport-only — it is NOT a column** | P2 |
| TC-SHF-005 | Shift / `POST /shifts` | `end_time == start_time` | `ADMIN_USER` | `{"start_time":"09:00:00","end_time":"09:00:00"}` | `VALIDATION_ERROR` (`<=` is rejected) | 422 | no row inserted | P2 |
| TC-SHF-006 | Shift / `POST /shifts` | `break_end_time` ≤ `break_start_time` | `ADMIN_USER` | `{"break_start_time":"13:30:00","break_end_time":"13:00:00"}` | `VALIDATION_ERROR` ("break_end_time must be after break_start_time") | 422 | no row inserted | P2 |
| TC-SHF-007 | Shift / `POST /shifts` | Duplicate shift name in the same org | `ADMIN_USER`; `SHIFT_GENERAL` named `General` | `POST /shifts` `{"shift_name":"General"}` | **409**, `error.code = "duplicate_shift_name"` (see [DEF-02](#appendix-a--error-code-drift-defects): `SHIFT_NAME_EXISTS` is only emitted by `/restore`) | 409 | `SELECT count(*) FROM shifts WHERE org_id=1 AND shift_name='General' AND is_deleted=false` → `1` | P1 |
| TC-SHF-008 | Shift / `POST /shifts` | The **same** name is allowed in a different tenant | `ORG_B_ADMIN` | `POST /shifts` `{"shift_name":"General"}` | 201 — the uniqueness rule is per-org | 201 | `SELECT org_id FROM shifts WHERE shift_name='General' AND is_deleted=false` → `{1, 2}` | **P0** |
| TC-SHF-009 | Shift / `POST /shifts` | Whitespace-only / empty `shift_name` | `ADMIN_USER` | `{"shift_name":""}` | `VALIDATION_ERROR` (`min_length=1`) | 422 | no row inserted | P2 |
| TC-SHF-010 | Shift / `POST /shifts` | Invalid `shift_type` enum | `ADMIN_USER` | `{"shift_name":"X","shift_type":"Fixed"}` (wrong casing — allowed `fixed\|open`) | `VALIDATION_ERROR` | 422 | no row inserted | P2 |
| TC-SHF-011 | Shift / `POST /shifts` | Missing `shift:create` | user with `shift:read` only | `POST /shifts` `{...}` | `AUTH_FORBIDDEN` | 403 | no row inserted | **P0** |
| TC-SHF-012 | Shift / `POST /shifts` | **Concurrency**: two identical creates in parallel | `ADMIN_USER` | 2 simultaneous `POST /shifts {"shift_name":"Race"}` | Exactly one 201; the loser is a clean **409 `CONFLICT`** (partial unique index → `IntegrityError` mapped, **not a 500**) | 201 / 409 | `SELECT count(*) FROM shifts WHERE org_id=1 AND shift_name='Race' AND is_deleted=false` → **`1`** | **P0** |
| TC-SHF-013 | Shift / `GET /shifts` | List with filters | `ADMIN_USER` | `GET /shifts?q=Gen&shift_type=fixed&is_default=false&page_size=50` | Paginated `ShiftSummarySchema` items; soft-deleted shifts excluded | 200 | list excludes `SHIFT_DELETED`: `SELECT is_deleted FROM shifts WHERE shift_id=:deleted` → `true` and it is absent from `data.items` | P1 |
| TC-SHF-014 | Shift / `GET /shifts` | Multi-tenant isolation | `ORG_B_ADMIN` | `GET /shifts` | Only ORG_B shifts | 200 | `SELECT DISTINCT org_id FROM shifts WHERE shift_id IN (returned)` → `{2}` | **P0** |
| TC-SHF-015 | Shift / `GET /shifts/{shift_id}` | Get a shift with its timings | `ADMIN_USER` | `GET /shifts/{SHIFT_GENERAL}` | `data.day_timings[]` populated | 200 | n/a (read-only) | P1 |
| TC-SHF-016 | Shift / `GET /shifts/{shift_id}` | Unknown / soft-deleted shift | `ADMIN_USER` | `GET /shifts/99999999` | **404**, `error.code = "not_found"` (see [DEF-03](#appendix-a--error-code-drift-defects) — `SHIFT_NOT_FOUND` is emitted by the timings/assignment/roster paths but not by `GET /shifts/{id}`) | 404 | n/a (read-only) | P1 |
| TC-SHF-017 | Shift / `GET /shifts/{shift_id}` | **Cross-tenant** shift id | `ADMIN_USER` | `GET /shifts/{SHIFT_B1}` | **404** (never 403) | 404 | `SELECT org_id FROM shifts WHERE shift_id=:shift_b1` → `2` (untouched) | **P0** |
| TC-SHF-018 | Shift / `PATCH /shifts/{shift_id}` | Partial update | `ADMIN_USER` | `PATCH /shifts/{SHIFT_GENERAL}` `{"shift_color":"#00AA00","remark":"day shift"}` | 200 | 200 | `SELECT shift_color, remark FROM shifts WHERE shift_id=:s` → `('#00AA00','day shift')` | P1 |
| TC-SHF-019 | Shift / `PATCH /shifts/{shift_id}` | Supplying `day_timings` replaces the whole set | `ADMIN_USER`; `SHIFT_PERDAY` has 7 timings | `PATCH /shifts/{SHIFT_PERDAY}` `{"day_timings":[{"day_of_week":1,"start_time":"10:00:00","end_time":"19:00:00"}]}` | 200; `data.day_timings` has exactly 1 row | 200 | `SELECT count(*) FROM shift_day_timings WHERE shift_id=:s` → **`1`** (the other 6 rows are deleted, not merged) | P1 |
| TC-SHF-020 | Shift / `PATCH /shifts/{shift_id}` | Rename onto an existing name | `ADMIN_USER` | `PATCH /shifts/{SHIFT_NIGHT}` `{"shift_name":"General"}` | **409** `duplicate_shift_name` | 409 | `SELECT shift_name FROM shifts WHERE shift_id=:night` → unchanged | P1 |
| TC-SHF-021 | Shift / `PATCH /shifts/{shift_id}` | Renaming to its own name is a no-op, not a conflict | `ADMIN_USER` | `PATCH /shifts/{SHIFT_GENERAL}` `{"shift_name":"General"}` | 200 | 200 | row unchanged | P3 |
| TC-SHF-022 | Shift / `DELETE /shifts/{shift_id}` | Soft-delete an unused shift | `ADMIN_USER`; `SHIFT_UNUSED` with no assignments/roster | `DELETE /shifts/{SHIFT_UNUSED}` | Empty body | 204 | `SELECT is_deleted FROM shifts WHERE shift_id=:s` → **`true`** (row retained); it disappears from `GET /shifts` | P1 |
| TC-SHF-023 | Shift / `DELETE /shifts/{shift_id}` | **Blocked while an open assignment references it** | `ADMIN_USER`; `ASSIGN_001` → `SHIFT_GENERAL`, `effective_to IS NULL` | `DELETE /shifts/{SHIFT_GENERAL}` | **409**, `error.code = "shift_in_use"` (see [DEF-04](#appendix-a--error-code-drift-defects): the contract's `SHIFT_IN_USE` constant is never raised) | 409 | `SELECT is_deleted FROM shifts WHERE shift_id=:s` → **`false`** — the shift survives | **P0** |
| TC-SHF-024 | Shift / `DELETE /shifts/{shift_id}` | Blocked by an upcoming roster entry | `ADMIN_USER`; a `roster` row for `SHIFT_UNUSED` dated today or later, no assignments | `DELETE /shifts/{SHIFT_UNUSED}` | **409** `shift_in_use` | 409 | `SELECT is_deleted FROM shifts WHERE shift_id=:s` → `false` | **P0** |
| TC-SHF-025 | Shift / `DELETE /shifts/{shift_id}` | Missing `shift:delete` | user with `shift:edit` | `DELETE /shifts/{SHIFT_UNUSED}` | `AUTH_FORBIDDEN` | 403 | `is_deleted` unchanged | P1 |
| TC-SHF-026 | Shift / `POST /shifts/{shift_id}/restore` | Restore a soft-deleted shift | `ADMIN_USER`; `SHIFT_DELETED` | `POST /shifts/{SHIFT_DELETED}/restore` | 200; the shift reappears in `GET /shifts` | 200 | `SELECT is_deleted FROM shifts WHERE shift_id=:s` → **`false`** | P1 |
| TC-SHF-027 | Shift / `POST /shifts/{shift_id}/restore` | Restoring a shift that is not deleted | `ADMIN_USER` | `POST /shifts/{SHIFT_GENERAL}/restore` | `error.code = "SHIFT_NOT_DELETED"` | 409 | row unchanged | P1 |
| TC-SHF-028 | Shift / `POST /shifts/{shift_id}/restore` | Its name was taken while it was deleted | `ADMIN_USER`; `SHIFT_DELETED.shift_name='Evening'`, and a new active shift now also uses `Evening` | `POST /shifts/{SHIFT_DELETED}/restore` | `error.code = "SHIFT_NAME_EXISTS"` — restore is refused rather than letting the partial unique index blow up | 409 | `SELECT is_deleted FROM shifts WHERE shift_id=:deleted` → still `true` | **P0** |
| TC-SHF-029 | Shift / `POST /shifts/{shift_id}/restore` | Unknown shift id | `ADMIN_USER` | `POST /shifts/99999999/restore` | `error.code = "SHIFT_NOT_FOUND"` | 404 | n/a | P2 |

### 4.2 Shift day timings

| ID | Module / API | Test Scenario | Preconditions | Request / Input | Expected Result | HTTP | Database Verification | Priority |
|---|---|---|---|---|---|---|---|---|
| TC-SHF-030 | Shift / `GET /shifts/{id}/timings` | List a shift's timings | `ADMIN_USER` | `GET /shifts/{SHIFT_PERDAY}/timings` | 7 `ShiftDayTimingSchema` rows | 200 | count matches `SELECT count(*) FROM shift_day_timings WHERE shift_id=:s` | P1 |
| TC-SHF-031 | Shift / `GET /shifts/{id}/timings` | Unknown shift | `ADMIN_USER` | `GET /shifts/99999999/timings` | `error.code = "SHIFT_NOT_FOUND"` | 404 | n/a (read-only) | P1 |
| TC-SHF-032 | Shift / `PUT /shifts/{id}/timings` | Atomically replace the full timing set | `ADMIN_USER`; `SHIFT_PERDAY` (7 rows) | `PUT /shifts/{SHIFT_PERDAY}/timings` `{"timings":[{"day_of_week":1,"start_time":"09:00:00","end_time":"18:00:00"},{"day_of_week":2,"start_time":"09:00:00","end_time":"18:00:00"}]}` | 200; exactly 2 rows returned | 200 | `SELECT count(*) FROM shift_day_timings WHERE shift_id=:s` → **`2`**; old `timing_id`s no longer exist | P1 |
| TC-SHF-033 | Shift / `PUT /shifts/{id}/timings` | **Uniform shift must get exactly one null-day timing** | `ADMIN_USER`; `SHIFT_GENERAL` has `is_uniform_time=true` | `PUT /shifts/{SHIFT_GENERAL}/timings` `{"timings":[{"day_of_week":1,...},{"day_of_week":2,...}]}` | `VALIDATION_ERROR` — "A uniform-time shift requires exactly one timing with day_of_week null." | 422 | `SELECT count(*) FROM shift_day_timings WHERE shift_id=:s` → unchanged (`1`) — the replace is atomic and rolled back | P1 |
| TC-SHF-034 | Shift / `PUT /shifts/{id}/timings` | Per-day shift with a `null` weekday | `ADMIN_USER`; `SHIFT_PERDAY` | `{"timings":[{"day_of_week":null,"start_time":"09:00:00","end_time":"18:00:00"}]}` | `VALIDATION_ERROR` — "A per-day shift requires day_of_week on every timing." | 422 | timings unchanged | P1 |
| TC-SHF-035 | Shift / `PUT /shifts/{id}/timings` | **Duplicate weekday in the set** | `ADMIN_USER`; `SHIFT_PERDAY` | `{"timings":[{"day_of_week":1,...},{"day_of_week":1,...}]}` | `error.code = "TIMING_DAY_DUPLICATE"` | 409 | `SELECT count(*) FROM shift_day_timings WHERE shift_id=:s AND day_of_week=1` → still `1` | P1 |
| TC-SHF-036 | Shift / `PUT /shifts/{id}/timings` | Empty timing list | `ADMIN_USER` | `{"timings":[]}` | `VALIDATION_ERROR` (`min_length=1`) | 422 | timings unchanged | P2 |
| TC-SHF-037 | Shift / `PATCH /shifts/{id}/timings/{timing_id}` | Patch one timing row | `ADMIN_USER` | `PATCH /shifts/{SHIFT_PERDAY}/timings/{T_MON}` `{"start_time":"10:00:00","end_time":"19:00:00"}` | 200 | 200 | `SELECT start_time, end_time FROM shift_day_timings WHERE timing_id=:t` → `('10:00','19:00')` | P1 |
| TC-SHF-038 | Shift / `PATCH /shifts/{id}/timings/{timing_id}` | Patch a timing onto a weekday another row already holds | `ADMIN_USER` | `PATCH .../timings/{T_MON}` `{"day_of_week":2}` where Tuesday already exists | `error.code = "TIMING_DAY_DUPLICATE"` | 409 | `SELECT day_of_week FROM shift_day_timings WHERE timing_id=:t_mon` → still `1` | P1 |
| TC-SHF-039 | Shift / `PATCH /shifts/{id}/timings/{timing_id}` | Unknown timing id | `ADMIN_USER` | `PATCH /shifts/{SHIFT_PERDAY}/timings/99999999` `{"is_working_day":false}` | `error.code = "TIMING_NOT_FOUND"` | 404 | no row changed | P1 |
| TC-SHF-040 | Shift / `PATCH /shifts/{id}/timings/{timing_id}` | Timing belonging to a **different shift** | `ADMIN_USER` | `PATCH /shifts/{SHIFT_GENERAL}/timings/{T_MON}` (T_MON belongs to `SHIFT_PERDAY`) | `error.code = "TIMING_NOT_FOUND"` | 404 | `SELECT shift_id FROM shift_day_timings WHERE timing_id=:t_mon` → still `SHIFT_PERDAY` | **P0** |
| TC-SHF-041 | Shift / `DELETE /shifts/{id}/timings/{timing_id}` | Delete one timing (hard delete) | `ADMIN_USER` | `DELETE /shifts/{SHIFT_PERDAY}/timings/{T_SUN}` | Empty body | 204 | `SELECT count(*) FROM shift_day_timings WHERE timing_id=:t_sun` → **`0`** | P1 |
| TC-SHF-042 | Shift / `DELETE /shifts/{id}/timings/{timing_id}` | Unknown timing id | `ADMIN_USER` | `DELETE .../timings/99999999` | `error.code = "TIMING_NOT_FOUND"` | 404 | no rows removed | P2 |

### 4.3 Shift assignments

| ID | Module / API | Test Scenario | Preconditions | Request / Input | Expected Result | HTTP | Database Verification | Priority |
|---|---|---|---|---|---|---|---|---|
| TC-SHF-043 | Shift / `POST /shift-assignments` | Assign a shift; the prior open assignment is auto-closed | `ADMIN_USER`; `ASSIGN_001` open from `2026-01-01` | `POST /shift-assignments` `{"employee_id":{EMP_001},"shift_id":{SHIFT_NIGHT},"effective_from":"2026-08-01"}` | 201; the new assignment is returned | 201 | `SELECT effective_to FROM shift_assignments WHERE assignment_id=:assign1` → **`2026-07-31`** (day before the new range); `SELECT count(*) FROM shift_assignments WHERE employee_id=:emp1 AND effective_to IS NULL` → `1` | **P0** |
| TC-SHF-044 | Shift / `POST /shift-assignments` | `effective_from` before the employee's joining date | `ADMIN_USER`; `EMP_001.date_of_joining='2026-01-01'` | `{"employee_id":{EMP_001},"shift_id":{SHIFT_GENERAL},"effective_from":"2025-12-01"}` | **422**, `error.code = "invalid_assignment_date"` | 422 | `SELECT count(*) FROM shift_assignments WHERE employee_id=:emp1 AND effective_from='2025-12-01'` → `0` | P1 |
| TC-SHF-045 | Shift / `POST /shift-assignments` | Duplicate assignment starting on the same date | `ADMIN_USER`; an assignment already starts on `2026-01-01` | `{"employee_id":{EMP_001},"shift_id":{SHIFT_NIGHT},"effective_from":"2026-01-01"}` | **409**, `error.code = "duplicate_assignment"` | 409 | `SELECT count(*) FROM shift_assignments WHERE employee_id=:emp1 AND effective_from='2026-01-01'` → still `1` | P1 |
| TC-SHF-046 | Shift / `POST /shift-assignments` | **Overlap** — the open assignment starts on/after the new range so it cannot be auto-closed | `ADMIN_USER`; open assignment from `2026-08-01` | `{"employee_id":{EMP_001},"shift_id":{SHIFT_GENERAL},"effective_from":"2026-07-01"}` | `error.code = "ASSIGNMENT_OVERLAP"` | 409 | `SELECT count(*) FROM shift_assignments WHERE employee_id=:emp1` → unchanged | **P0** |
| TC-SHF-047 | Shift / `POST /shift-assignments` | `effective_to` before `effective_from` | `ADMIN_USER` | `{"effective_from":"2026-08-01","effective_to":"2026-07-01",...}` | `VALIDATION_ERROR` ("effective_to must be on or after effective_from") | 422 | no row inserted | P2 |
| TC-SHF-048 | Shift / `POST /shift-assignments` | Unknown shift / unknown employee | `ADMIN_USER` | `{"employee_id":{EMP_001},"shift_id":99999999,"effective_from":"2026-08-01"}` then with `employee_id=99999999` | **404** `not_found` in both cases | 404 | no row inserted | P1 |
| TC-SHF-049 | Shift / `POST /shift-assignments` | **Cross-tenant**: assign ORG_B's shift to an ORG_A employee | `ADMIN_USER` | `{"employee_id":{EMP_001},"shift_id":{SHIFT_B1},"effective_from":"2026-08-01"}` | **404** `not_found` — a foreign shift is invisible | 404 | `SELECT count(*) FROM shift_assignments WHERE employee_id=:emp1 AND shift_id=:shift_b1` → `0` | **P0** |
| TC-SHF-050 | Shift / `POST /shift-assignments/bulk` | Bulk assign with mixed outcomes | `ADMIN_USER`; `EMP_001` already has an assignment starting `2026-09-01`, `EMP_002` does not | `POST /shift-assignments/bulk` `{"employee_ids":[{EMP_001},{EMP_002},99999999],"shift_id":{SHIFT_GENERAL},"effective_from":"2026-09-01"}` | **200** (not 201); `data.created_count`, `data.skipped_count`, and a per-item `results[]` with `status` = `created` / `skipped` + `reason` | 200 | `SELECT count(*) FROM shift_assignments WHERE employee_id=:emp2 AND effective_from='2026-09-01'` → `1`; the failing items produced **no** rows and did **not** abort the batch | P1 |
| TC-SHF-051 | Shift / `GET /shift-assignments` | Filter by employee + `active_on` | `ADMIN_USER` | `GET /shift-assignments?employee_id={EMP_001}&active_on=2026-07-15` | Only assignments whose `[effective_from, effective_to]` range covers the date | 200 | n/a (read-only) | P1 |
| TC-SHF-052 | Shift / `GET /shift-assignments` | `date=` (resolve-one) without `employee_id` | `ADMIN_USER` | `GET /shift-assignments?date=2026-07-15` | **422**, `error.code = "validation_error"` ("employee_id is required.") | 422 | n/a (read-only) | P2 |
| TC-SHF-053 | Shift / `PATCH /shift-assignments/{id}` | Patch the shift on an assignment | `ADMIN_USER` | `PATCH /shift-assignments/{ASSIGN_001}` `{"shift_id":{SHIFT_NIGHT}}` | 200 | 200 | `SELECT shift_id FROM shift_assignments WHERE assignment_id=:a` → `SHIFT_NIGHT` | P1 |
| TC-SHF-054 | Shift / `PATCH /shift-assignments/{id}` | Patch a range so it overlaps another assignment | `ADMIN_USER`; two adjacent assignments | `PATCH /shift-assignments/{A2}` `{"effective_from":"<inside A1's range>"}` | `error.code = "ASSIGNMENT_OVERLAP"` | 409 | `SELECT effective_from FROM shift_assignments WHERE assignment_id=:a2` → unchanged | **P0** |
| TC-SHF-055 | Shift / `PATCH /shift-assignments/{id}` | Unknown assignment | `ADMIN_USER` | `PATCH /shift-assignments/99999999` `{"shift_id":1}` | `error.code = "ASSIGNMENT_NOT_FOUND"` | 404 | no change | P1 |
| TC-SHF-056 | Shift / `PATCH /shift-assignments/{id}` | Cross-tenant assignment id | `ADMIN_USER` | `PATCH /shift-assignments/{ASSIGN_B1}` `{"shift_id":1}` | **404** `ASSIGNMENT_NOT_FOUND` (not 403) | 404 | `SELECT shift_id FROM shift_assignments WHERE assignment_id=:assign_b1` → unchanged | **P0** |
| TC-SHF-057 | Shift / `DELETE /shift-assignments/{id}` | **Hard delete** an assignment | `ADMIN_USER` | `DELETE /shift-assignments/{ASSIGN_001}` | Empty body | 204 | `SELECT count(*) FROM shift_assignments WHERE assignment_id=:a` → **`0`** (`shift_assignments` has no soft-delete column) | P1 |
| TC-SHF-058 | Shift / `DELETE /shift-assignments/{id}` | Unknown assignment | `ADMIN_USER` | `DELETE /shift-assignments/99999999` | `error.code = "ASSIGNMENT_NOT_FOUND"` | 404 | no rows removed | P2 |
| TC-SHF-059 | Shift / `GET /employees/{id}/shift-assignments` | Employee assignment history | `ADMIN_USER` | `GET /employees/{EMP_001}/shift-assignments` | Paginated history | 200 | count = `SELECT count(*) FROM shift_assignments WHERE org_id=1 AND employee_id=:emp1` | P1 |
| TC-SHF-060 | Shift / `GET /employees/{id}/shift-assignments` | `current=true` returns only today's assignment | `ADMIN_USER` | `GET /employees/{EMP_001}/shift-assignments?current=true` | 0 or 1 item — the one whose range covers today | 200 | n/a (read-only) | P1 |
| TC-SHF-061 | Shift / `GET /employees/{id}/shift-assignments` | Unknown / cross-org employee | `ADMIN_USER` | `GET /employees/{EMP_B01}/shift-assignments` | **404**, `error.code = "EMPLOYEE_NOT_FOUND"` | 404 | n/a (read-only) | **P0** |

### 4.4 Shift resolve & rotations

| ID | Module / API | Test Scenario | Preconditions | Request / Input | Expected Result | HTTP | Database Verification | Priority |
|---|---|---|---|---|---|---|---|---|
| TC-SHF-062 | Shift / `GET /shifts/resolve` | Resolve a working day | `ADMIN_USER`; `ASSIGN_001` covers the date; no week-off on that weekday | `GET /shifts/resolve?employee_id={EMP_001}&date=2026-07-15` | `data.shift.shift_id = SHIFT_GENERAL`; `data.is_weekly_off = false`; `data.is_working_day = true` | 200 | n/a (read-only) | P1 |
| TC-SHF-063 | Shift / `GET /shifts/resolve` | Resolve a configured weekly off | `ADMIN_USER`; `WEEKOFF_SUN` (`day_of_week=0`, `week_off`) | `GET /shifts/resolve?employee_id={EMP_001}&date=2026-07-12` (a Sunday) | `data.is_weekly_off = true`; `data.is_working_day = false` (the shift may still be returned) | 200 | n/a (read-only) | P1 |
| TC-SHF-064 | Shift / `GET /shifts/resolve` | `is_working_day=false` because the shift's own weekday row says so | `ADMIN_USER`; `SHIFT_PERDAY` has `is_working_day=false` on Saturday; assigned to `EMP_002` | `GET /shifts/resolve?employee_id={EMP_002}&date=<a Saturday>` | `is_weekly_off = false` but `is_working_day = false` — the two signals are combined | 200 | n/a (read-only) | P1 |
| TC-SHF-065 | Shift / `GET /shifts/resolve` | No assignment on the date | `ADMIN_USER`; `EMP_002` has no assignment | `GET /shifts/resolve?employee_id={EMP_002}&date=2026-07-15` | `data.shift = null`; `is_working_day = true` | 200 | n/a (read-only) | P2 |
| TC-SHF-066 | Shift / `GET /shifts/resolve` | Route ordering — `/shifts/resolve` is not swallowed by `/shifts/{shift_id}` | `ADMIN_USER` | `GET /shifts/resolve?employee_id=1&date=2026-07-15` | Resolves; does **not** produce a 422 "shift_id must be an integer" | 200 | n/a (read-only) | P2 |
| TC-SHF-067 | Shift / `GET /shifts/resolve` | Cross-org employee | `ADMIN_USER` | `GET /shifts/resolve?employee_id={EMP_B01}&date=2026-07-15` | **404** `not_found` | 404 | n/a (read-only) | **P0** |
| TC-SHF-068 | Shift / `GET /shifts/resolve` | Missing required `date` | `ADMIN_USER` | `GET /shifts/resolve?employee_id=1` | `VALIDATION_ERROR` | 422 | n/a (read-only) | P2 |
| TC-SHF-069 | Shift / `POST /shift-rotations` | **Settings gate**: rotation refused when `advance_shift_enabled` is false | `ADMIN_USER`; `org_settings` row absent **or** `advance_shift_enabled=false` (the schema default — this fires out of the box) | `POST /shift-rotations` `{"name":"Q3","cadence":"weekly","shift_sequence":[{SHIFT_GENERAL},{SHIFT_NIGHT}],"start_date":"2026-08-01","horizon_days":30,"group_scope":{"employee_ids":[{EMP_001}]}}` | **409**, `error.code = "ADVANCE_SHIFT_DISABLED"` | 409 | `SELECT count(*) FROM roster WHERE org_id=1 AND roster_date BETWEEN '2026-08-01' AND '2026-08-30'` → **`0`** — nothing was generated | **P0** |
| TC-SHF-070 | Shift / `POST /shift-rotations` | Rotation generates roster rows once the toggle is on | `ADMIN_USER`; `UPDATE org_settings SET advance_shift_enabled=true WHERE org_id=1` | same body as TC-SHF-069 | **202 Accepted**; `data.generated_count > 0`; `data.generated_assignments[]` of `RosterEntrySchema` | 202 | `SELECT count(*) FROM roster WHERE org_id=1 AND employee_id=:emp1 AND roster_date BETWEEN '2026-08-01' AND '2026-08-30'` → `30`; rows falling on `WEEKOFF_SUN` have `is_week_off=true AND shift_id IS NULL` | **P0** |
| TC-SHF-071 | Shift / `POST /shift-rotations` | Regeneration is idempotent (existing rows in the window are replaced) | `ADMIN_USER`; toggle on; TC-SHF-070 already ran | re-POST the identical body | 202 | 202 | `SELECT count(*) FROM roster WHERE employee_id=:emp1 AND roster_date BETWEEN '2026-08-01' AND '2026-08-30'` → still **`30`** (not 60) | **P0** |
| TC-SHF-072 | Shift / `POST /shift-rotations` | Unknown shift in `shift_sequence` | `ADMIN_USER`; toggle on | `"shift_sequence":[99999999]` | **422**, `error.code = "invalid_shift"` | 422 | no `roster` rows created | P1 |
| TC-SHF-073 | Shift / `POST /shift-rotations` | Scope matches no active employees | `ADMIN_USER`; toggle on | `"group_scope":{"employee_ids":[]}` and empty branch/dept lists | **422**, `error.code = "empty_rotation_scope"` | 422 | no `roster` rows created | P1 |
| TC-SHF-074 | Shift / `POST /shift-rotations` | Boundary: `horizon_days` 0 and 367 | `ADMIN_USER`; toggle on | `"horizon_days":0` then `367` | Both `VALIDATION_ERROR` (`ge=1`, `le=366`) | 422 | no `roster` rows created | P2 |
| TC-SHF-075 | Shift / `POST /shift-rotations` | Missing `shift_rotation:create` | user with `shift:create` only | valid rotation body | `AUTH_FORBIDDEN` | 403 | no `roster` rows created | P1 |

### 4.5 Weekly offs

| ID | Module / API | Test Scenario | Preconditions | Request / Input | Expected Result | HTTP | Database Verification | Priority |
|---|---|---|---|---|---|---|---|---|
| TC-SHF-076 | Shift / `GET /employees/{id}/weekoffs` | Current weekly-off configuration | `ADMIN_USER` | `GET /employees/{EMP_001}/weekoffs` | Only *current* rows (`effective_to IS NULL`) | 200 | count = `SELECT count(*) FROM employee_weekoffs WHERE employee_id=:emp1 AND effective_to IS NULL` | P1 |
| TC-SHF-077 | Shift / `GET /employees/{id}/weekoffs` | `include_history=true` returns superseded rows too | `ADMIN_USER`; at least one closed row | `GET /employees/{EMP_001}/weekoffs?include_history=true` | Superseded rows (with a non-null `effective_to`) also appear | 200 | count = `SELECT count(*) FROM employee_weekoffs WHERE employee_id=:emp1` | P2 |
| TC-SHF-078 | Shift / `GET /employees/{id}/weekoffs` | Cross-org employee | `ADMIN_USER` | `GET /employees/{EMP_B01}/weekoffs` | **404** `EMPLOYEE_NOT_FOUND` | 404 | n/a (read-only) | **P0** |
| TC-SHF-079 | Shift / `PUT /employees/{id}/weekoffs` | Configure the weekly-off set (bulk replace) | `ADMIN_USER` | `PUT /employees/{EMP_001}/weekoffs` `{"weekoffs":[{"day_of_week":0,"weekoff_type":"week_off","effective_from":"2026-08-01"},{"day_of_week":6,"weekoff_type":"occasional_week_off","occurrence_2nd":true,"occurrence_4th":true,"occurrence_1st":false,"occurrence_3rd":false,"occurrence_5th":false,"effective_from":"2026-08-01"}]}` | 200; the two current rows returned | 200 | `SELECT count(*) FROM employee_weekoffs WHERE employee_id=:emp1 AND effective_to IS NULL` → **`2`**; the previously current Sunday row is **superseded, not deleted**: `SELECT effective_to FROM employee_weekoffs WHERE weekoff_id=:weekoff_sun` → `2026-07-31` (day before the new `effective_from`) | **P0** |
| TC-SHF-080 | Shift / `PUT /employees/{id}/weekoffs` | Weekdays dropped from the config are closed | `ADMIN_USER`; EMP has Sunday + Saturday current | `PUT .../weekoffs` `{"weekoffs":[{"day_of_week":0,...}]}` (Saturday omitted) | 200 | 200 | `SELECT effective_to FROM employee_weekoffs WHERE employee_id=:emp1 AND day_of_week=6` → non-null (closed the day before today), row retained | P1 |
| TC-SHF-081 | Shift / `PUT /employees/{id}/weekoffs` | **Repeated weekday in the request body** | `ADMIN_USER` | `{"weekoffs":[{"day_of_week":0,...},{"day_of_week":0,...}]}` | **409**, `error.code = "WEEKOFF_DAY_EXISTS"` ("supply each weekday at most once") | 409 | `SELECT count(*) FROM employee_weekoffs WHERE employee_id=:emp1 AND day_of_week=0 AND effective_to IS NULL` → still `1` | P1 |
| TC-SHF-082 | Shift / `PUT /employees/{id}/weekoffs` | Invalid `day_of_week` (7) / invalid `weekoff_type` | `ADMIN_USER` | `{"weekoffs":[{"day_of_week":7,"weekoff_type":"week_off"}]}` then `weekoff_type="WeekOff"` | Both `VALIDATION_ERROR` (0–6; `working\|week_off\|occasional_week_off`) | 422 | no rows written | P2 |
| TC-SHF-083 | Shift / `PUT /employees/{id}/weekoffs` | Empty `weekoffs` list | `ADMIN_USER` | `{"weekoffs":[]}` | `VALIDATION_ERROR` (`min_length=1`) | 422 | no rows written | P2 |
| TC-SHF-084 | Shift / `PATCH /employees/{id}/weekoffs/{weekoff_id}` | Patch one weekday's rule | `ADMIN_USER` | `PATCH /employees/{EMP_001}/weekoffs/{WEEKOFF_SUN}` `{"weekoff_type":"working"}` | 200 | 200 | `SELECT weekoff_type, updated_by FROM employee_weekoffs WHERE weekoff_id=:w` → `('working', <actor>)` | P1 |
| TC-SHF-085 | Shift / `PATCH /employees/{id}/weekoffs/{weekoff_id}` | Unknown weekoff id | `ADMIN_USER` | `PATCH .../weekoffs/99999999` `{"weekoff_type":"working"}` | `error.code = "WEEKOFF_NOT_FOUND"` | 404 | no row changed | P1 |
| TC-SHF-086 | Shift / `PATCH /employees/{id}/weekoffs/{weekoff_id}` | `effective_to` before `effective_from` | `ADMIN_USER` | `{"effective_to":"2020-01-01"}` on a row whose `effective_from` is `2026-01-01` | `VALIDATION_ERROR` ("effective_to must be on or after effective_from.") | 422 | row unchanged | P2 |

### 4.6 Roster / shift calendar

| ID | Module / API | Test Scenario | Preconditions | Request / Input | Expected Result | HTTP | Database Verification | Priority |
|---|---|---|---|---|---|---|---|---|
| TC-SHF-087 | Shift / `GET /roster` | Org calendar over a month | `ADMIN_USER` | `GET /roster?month=2026-07` | Paginated `RosterEntrySchema` rows for `2026-07-01 … 2026-07-31` | 200 | total = `SELECT count(*) FROM roster WHERE org_id=1 AND roster_date BETWEEN '2026-07-01' AND '2026-07-31'` | P1 |
| TC-SHF-088 | Shift / `GET /roster` | Range form + filters | `ADMIN_USER` | `GET /roster?date_from=2026-07-01&date_to=2026-07-07&branch_id={BRANCH_1}&shift_id={SHIFT_GENERAL}` | Filtered rows only | 200 | n/a (read-only) | P1 |
| TC-SHF-089 | Shift / `GET /roster` | **Both** `month` and a date pair supplied | `ADMIN_USER` | `GET /roster?month=2026-07&date_from=2026-07-01&date_to=2026-07-07` | `VALIDATION_ERROR` ("supply either month or date_from/date_to, not both") | 422 | n/a (read-only) | P2 |
| TC-SHF-090 | Shift / `GET /roster` | Neither range form supplied | `ADMIN_USER` | `GET /roster` | `VALIDATION_ERROR` ("supply month (YYYY-MM) or both date_from and date_to") | 422 | n/a (read-only) | P2 |
| TC-SHF-091 | Shift / `GET /roster` | Half a date pair; and `date_to` < `date_from`; and a malformed month | `ADMIN_USER` | `?date_from=2026-07-01` · `?date_from=2026-07-07&date_to=2026-07-01` · `?month=2026-13` | All three → `VALIDATION_ERROR` (the last one fails the `^\d{4}-(0[1-9]\|1[0-2])$` pattern) | 422 | n/a (read-only) | P2 |
| TC-SHF-092 | Shift / `GET /roster` | Multi-tenant isolation | `ORG_B_ADMIN` | `GET /roster?month=2026-07` | Only ORG_B roster rows | 200 | `SELECT DISTINCT org_id FROM roster WHERE roster_id IN (returned)` → `{2}` | **P0** |
| TC-SHF-093 | Shift / `PUT /roster` | **Upsert — create** | `ADMIN_USER`; no roster row for `EMP_002` on `2026-07-20` | `PUT /roster` `{"employee_id":{EMP_002},"roster_date":"2026-07-20","shift_id":{SHIFT_GENERAL}}` | 200; `data.created = true`; message "Roster entry created." | 200 | `SELECT count(*) FROM roster WHERE employee_id=:emp2 AND roster_date='2026-07-20'` → `1`, `created_by = <actor>` | P1 |
| TC-SHF-094 | Shift / `PUT /roster` | **Upsert — update** (same `(employee_id, roster_date)` key) | `ADMIN_USER`; TC-SHF-093 already ran | `PUT /roster` `{"employee_id":{EMP_002},"roster_date":"2026-07-20","shift_id":{SHIFT_NIGHT}}` | 200; `data.created = false`; message "Roster entry updated." — note this endpoint **upserts**, so `ROSTER_ENTRY_EXISTS` never fires (see [DEF-05](#appendix-a--error-code-drift-defects)) | 200 | `SELECT count(*), max(shift_id), max(updated_by) FROM roster WHERE employee_id=:emp2 AND roster_date='2026-07-20'` → `(1, SHIFT_NIGHT, <actor>)` — **one** row, not two | **P0** |
| TC-SHF-095 | Shift / `PUT /roster` | A week-off entry cannot carry a shift | `ADMIN_USER` | `{"employee_id":{EMP_002},"roster_date":"2026-07-21","is_week_off":true,"shift_id":{SHIFT_GENERAL}}` | `VALIDATION_ERROR` ("a week-off roster entry cannot carry a shift_id") | 422 | no row written | P1 |
| TC-SHF-096 | Shift / `PUT /roster` | Unknown employee / unknown shift | `ADMIN_USER` | `{"employee_id":99999999,"roster_date":"2026-07-20"}` then `{"shift_id":99999999,...}` | `EMPLOYEE_NOT_FOUND` and `SHIFT_NOT_FOUND` respectively | 404 | no row written | P1 |
| TC-SHF-097 | Shift / `PUT /roster` | Cross-tenant employee | `ADMIN_USER` | `{"employee_id":{EMP_B01},"roster_date":"2026-07-20","shift_id":{SHIFT_GENERAL}}` | **404** `EMPLOYEE_NOT_FOUND` | 404 | `SELECT count(*) FROM roster WHERE employee_id=:emp_b01 AND org_id=1` → `0` | **P0** |
| TC-SHF-098 | Shift / `POST /roster/bulk` | Bulk upsert with mixed outcomes | `ADMIN_USER` | `POST /roster/bulk` `{"entries":[{new},{existing},{employee_id:99999999}]}` | **200**; `created_count`, `updated_count`, `skipped_count` and a `results[]` carrying `status` + `reason` per entry | 200 | `SELECT count(*) FROM roster WHERE employee_id=99999999` → `0`; valid entries persisted; the batch was not aborted | P1 |
| TC-SHF-099 | Shift / `POST /roster/bulk` | Empty `entries` | `ADMIN_USER` | `{"entries":[]}` | `VALIDATION_ERROR` (`min_length=1`) | 422 | no rows written | P2 |
| TC-SHF-100 | Shift / `PATCH /roster/{roster_id}` | Patch a roster entry to a week-off | `ADMIN_USER` | `PATCH /roster/{ROSTER_001}` `{"is_week_off":true,"shift_id":null}` | 200 | 200 | `SELECT is_week_off, shift_id FROM roster WHERE roster_id=:r` → `(true, NULL)` | P1 |
| TC-SHF-101 | Shift / `PATCH /roster/{roster_id}` | Patch that leaves a week-off carrying a shift | `ADMIN_USER` | `PATCH /roster/{ROSTER_001}` `{"is_week_off":true}` while `shift_id` is still set | `VALIDATION_ERROR` ("A week-off roster entry cannot carry a shift.") | 422 | `SELECT is_week_off FROM roster WHERE roster_id=:r` → unchanged | P1 |
| TC-SHF-102 | Shift / `PATCH /roster/{roster_id}` | Unknown / cross-tenant roster id | `ADMIN_USER` | `PATCH /roster/99999999` `{"is_week_off":true}` and `PATCH /roster/{ROSTER_B1}` | `error.code = "ROSTER_NOT_FOUND"` (404) in both cases | 404 | `SELECT is_week_off FROM roster WHERE roster_id=:roster_b1` → unchanged | **P0** |
| TC-SHF-103 | Shift / `DELETE /roster/{roster_id}` | **Hard delete** a roster entry | `ADMIN_USER` | `DELETE /roster/{ROSTER_001}` | Empty body | 204 | `SELECT count(*) FROM roster WHERE roster_id=:r` → **`0`** | P1 |
| TC-SHF-104 | Shift / `DELETE /roster/{roster_id}` | Unknown roster id | `ADMIN_USER` | `DELETE /roster/99999999` | `error.code = "ROSTER_NOT_FOUND"` | 404 | no rows removed | P2 |
| TC-SHF-105 | Shift / `GET /employees/{id}/roster` | One employee's calendar for a month | `ADMIN_USER` | `GET /employees/{EMP_001}/roster?month=2026-08` | Rows for that employee only | 200 | count = `SELECT count(*) FROM roster WHERE org_id=1 AND employee_id=:emp1 AND roster_date BETWEEN '2026-08-01' AND '2026-08-31'` | P1 |
| TC-SHF-106 | Shift / `GET /employees/{id}/roster` | Cross-org employee | `ADMIN_USER` | `GET /employees/{EMP_B01}/roster?month=2026-08` | **404** `EMPLOYEE_NOT_FOUND` | 404 | n/a (read-only) | **P0** |
| TC-SHF-107 | Shift / roster & weekoff routes | Missing `roster:edit` / `weekoff:edit` | user with `roster:read` + `weekoff:read` | `PUT /roster {...}` and `PUT /employees/{EMP_001}/weekoffs {...}` | `AUTH_FORBIDDEN` on both | 403 | no rows written to `roster` / `employee_weekoffs` | **P0** |

---

## 5. Attendance Management

**Permission keys:** `attendance`, `attendance_punch`, `attendance_penalty`.
**Note on the wire format:** several attendance mutations take their inputs as **query parameters**, not a JSON body (`POST /attendance/days`, `POST /attendance/punches`, `POST /attendance/penalties`, `POST /attendance/penalties/{id}/waive`). The requests below reflect the implementation.

### 5.1 Attendance days

| ID | Module / API | Test Scenario | Preconditions | Request / Input | Expected Result | HTTP | Database Verification | Priority |
|---|---|---|---|---|---|---|---|---|
| TC-ATT-001 | Attendance / `POST /attendance/days` | Mark an attendance day manually | `ADMIN_USER` | `POST /attendance/days?employee_id={EMP_002}&attendance_date=2026-07-02&status=present&shift_id={SHIFT_GENERAL}&remarks=manual` | 201; `data.status="present"`, `data.source="manual"`, `data.punches=[]`, `data.penalties=[]` | 201 | `SELECT status, source, marked_by, created_by FROM attendance_days WHERE id=:d` → `('present','manual',<actor>,<actor>)` | P1 |
| TC-ATT-002 | Attendance / `POST /attendance/days` | **Uniqueness: one day per (employee, date)** | `ADMIN_USER`; `DAY_001` exists for `EMP_001` on `2026-07-01` | `POST /attendance/days?employee_id={EMP_001}&attendance_date=2026-07-01&status=absent` | **409**, `error.code = "ATTENDANCE_DAY_EXISTS"` | 409 | `SELECT count(*) FROM attendance_days WHERE org_id=1 AND employee_id=:emp1 AND attendance_date='2026-07-01'` → **`1`**; its `status` is still `present` | **P0** |
| TC-ATT-003 | Attendance / `POST /attendance/days` | Unknown employee | `ADMIN_USER` | `?employee_id=99999999&attendance_date=2026-07-02&status=present` | `error.code = "EMPLOYEE_NOT_FOUND"` | 404 | no row inserted | P1 |
| TC-ATT-004 | Attendance / `POST /attendance/days` | **Cross-tenant employee** | `ADMIN_USER` | `?employee_id={EMP_B01}&attendance_date=2026-07-02&status=present` | **404** `EMPLOYEE_NOT_FOUND` (never 403) | 404 | `SELECT count(*) FROM attendance_days WHERE org_id=1 AND employee_id=:emp_b01` → `0` | **P0** |
| TC-ATT-005 | Attendance / `POST /attendance/days` | Unknown shift | `ADMIN_USER` | `?employee_id={EMP_002}&attendance_date=2026-07-03&status=present&shift_id=99999999` | `error.code = "SHIFT_NOT_FOUND"` | 404 | no row inserted | P1 |
| TC-ATT-006 | Attendance / `POST /attendance/days` | Cross-tenant shift on an in-tenant employee | `ADMIN_USER` | `?employee_id={EMP_002}&attendance_date=2026-07-03&status=present&shift_id={SHIFT_B1}` | **404** `SHIFT_NOT_FOUND` | 404 | `SELECT count(*) FROM attendance_days WHERE shift_id=:shift_b1 AND org_id=1` → `0` | **P0** |
| TC-ATT-007 | Attendance / `POST /attendance/days` | Invalid `status` enum | `ADMIN_USER` | `?...&status=Present` (wrong casing — allowed `present\|absent\|half_day\|week_off\|holiday\|on_leave\|not_marked`) | `VALIDATION_ERROR` | 422 | no row inserted | P2 |
| TC-ATT-008 | Attendance / `POST /attendance/days` | Missing required query params | `ADMIN_USER` | `POST /attendance/days` with no query string | `VALIDATION_ERROR`; `details` names `employee_id`, `attendance_date`, `status` | 422 | no row inserted | P2 |
| TC-ATT-009 | Attendance / `POST /attendance/days` | Missing `attendance:create` | user with `attendance:read` | valid request | `AUTH_FORBIDDEN` | 403 | no row inserted | **P0** |
| TC-ATT-010 | Attendance / `POST /attendance/days` | **Concurrency**: two identical marks in parallel | `ADMIN_USER` | 2 simultaneous `POST /attendance/days?employee_id={EMP_002}&attendance_date=2026-07-05&status=present` | One 201; the loser gets a clean **409** (`ATTENDANCE_DAY_EXISTS` if the pre-check catches it, else `CONFLICT` from the unique index) — **never a 500** | 201 / 409 | `SELECT count(*) FROM attendance_days WHERE employee_id=:emp2 AND attendance_date='2026-07-05'` → **`1`** | **P0** |
| TC-ATT-011 | Attendance / `POST /attendance/manual` | Manual check-in / check-out entry | `ADMIN_USER` | `POST /attendance/manual` `{"employee_id":{EMP_002},"date":"2026-07-06","in_time":"2026-07-06T09:05:00","out_time":"2026-07-06T18:10:00","reason":"forgot to punch"}` | 201; `data.first_punch_in` / `last_punch_out` set; `data.punches` has 2 entries | 201 | `SELECT count(*) FROM attendance_days WHERE employee_id=:emp2 AND attendance_date='2026-07-06'` → `1`; `SELECT count(*), min(punch_type), max(punch_type) FROM attendance_punches WHERE attendance_day_id=:d` → `(2,'in','out')`; `punch_source='manual_entry'` | P1 |
| TC-ATT-012 | Attendance / `POST /attendance/manual` | Shift is resolved and `expected_start/end_time` stamped | `ADMIN_USER`; `EMP_001` assigned `SHIFT_GENERAL` (09:00–18:00) | manual entry for a date covered by the assignment | 201; `data.shift_id = SHIFT_GENERAL` | 201 | `SELECT shift_id, expected_start_time, expected_end_time FROM attendance_days WHERE id=:d` → `(SHIFT_GENERAL,'09:00','18:00')` | P1 |
| TC-ATT-013 | Attendance / `POST /attendance/manual` | `out_time` ≤ `in_time` | `ADMIN_USER` | `{"in_time":"2026-07-06T18:00:00","out_time":"2026-07-06T09:00:00",...}` | `VALIDATION_ERROR` ("out_time must be chronologically after in_time") | 422 | no `attendance_days` / `attendance_punches` rows created | P2 |
| TC-ATT-014 | Attendance / `POST /attendance/manual` | `reason` shorter than 3 chars / longer than 500 | `ADMIN_USER` | `"reason":"ok"` then a 501-char reason | Both `VALIDATION_ERROR` | 422 | no rows created | P2 |
| TC-ATT-015 | Attendance / `POST /attendance/manual` | Duplicate day | `ADMIN_USER`; a day already exists on that date | valid manual body for `2026-07-01` / `EMP_001` | `error.code = "ATTENDANCE_DAY_EXISTS"` | 409 | `SELECT count(*) FROM attendance_days WHERE employee_id=:emp1 AND attendance_date='2026-07-01'` → `1`; **no orphan punches**: `SELECT count(*) FROM attendance_punches WHERE attendance_day_id=:day1` unchanged | **P0** |
| TC-ATT-016 | Attendance / `GET /attendance/days` | Daily grid for a date | `ADMIN_USER` | `GET /attendance/days?date=2026-07-01&branch_id={BRANCH_1}` | Paginated `AttendanceDailySchema` — note the wire aliases: `first_in` ← `first_punch_in`, `last_out` ← `last_punch_out`, `worked_minutes` ← `total_working_minutes` | 200 | total = `SELECT count(*) FROM attendance_days WHERE org_id=1 AND attendance_date='2026-07-01'` (branch-filtered) | P1 |
| TC-ATT-017 | Attendance / `GET /attendance/days` | Missing the required `date` param | `ADMIN_USER` | `GET /attendance/days` | `VALIDATION_ERROR` | 422 | n/a (read-only) | P2 |
| TC-ATT-018 | Attendance / `GET /attendance/days` | Multi-tenant isolation | `ORG_B_ADMIN` | `GET /attendance/days?date=2026-07-01` | Only ORG_B rows | 200 | `SELECT DISTINCT org_id FROM attendance_days WHERE id IN (returned)` → `{2}` | **P0** |
| TC-ATT-019 | Attendance / `GET /attendance/days/{day_id}` | Day detail with nested punches + penalties | `ADMIN_USER` | `GET /attendance/days/{DAY_001}` | `data.punches[]` and `data.penalties[]` eager-loaded | 200 | n/a (read-only) | P1 |
| TC-ATT-020 | Attendance / `GET /attendance/days/{day_id}` | Unknown day | `ADMIN_USER` | `GET /attendance/days/99999999` | `error.code = "ATTENDANCE_DAY_NOT_FOUND"` | 404 | n/a (read-only) | P1 |
| TC-ATT-021 | Attendance / `GET /attendance/days/{day_id}` | **Cross-tenant day id** | `ADMIN_USER` | `GET /attendance/days/{DAY_B01}` | **404** `ATTENDANCE_DAY_NOT_FOUND` (never 403, never the other tenant's punches) | 404 | `SELECT org_id FROM attendance_days WHERE id=:day_b01` → `2` (untouched) | **P0** |
| TC-ATT-022 | Attendance / `PATCH /attendance/days/{day_id}` | Override the day's status and worked minutes | `ADMIN_USER` | `PATCH /attendance/days/{DAY_001}` `{"status":"half_day","total_working_minutes":240,"remarks":"approved"}` | 200; the day reflects the override | 200 | `SELECT status, total_working_minutes, source, marked_by, updated_by FROM attendance_days WHERE id=:day1` → `('half_day',240,'manual',<actor>,<actor>)` — the override always stamps `source='manual'` | **P0** |
| TC-ATT-023 | Attendance / `PATCH /attendance/days/{day_id}` | **Field allowlist**: unknown / protected keys are ignored | `ADMIN_USER` | `PATCH /attendance/days/{DAY_001}` `{"employee_id":{EMP_B01},"org_id":2,"status":"present"}` | 200; only `status` is applied | 200 | `SELECT employee_id, org_id FROM attendance_days WHERE id=:day1` → **unchanged** (`EMP_001`, `1`) — the service copies only the allowlisted fields (`status`, `leave_id`, `remarks`, `shift_id`, and the minute counters) | **P0** |
| TC-ATT-024 | Attendance / `PATCH /attendance/days/{day_id}` | Override with an unknown shift | `ADMIN_USER` | `PATCH /attendance/days/{DAY_001}` `{"shift_id":99999999}` | `error.code = "SHIFT_NOT_FOUND"` | 404 | `SELECT shift_id FROM attendance_days WHERE id=:day1` → unchanged | P1 |
| TC-ATT-025 | Attendance / `PATCH /attendance/days/{day_id}` | Unknown day id | `ADMIN_USER` | `PATCH /attendance/days/99999999` `{"status":"absent"}` | `error.code = "ATTENDANCE_DAY_NOT_FOUND"` | 404 | no row changed | P1 |
| TC-ATT-026 | Attendance / `PATCH /attendance/days/{day_id}` | Missing `attendance:edit` | user with `attendance:read` + `attendance:create` | `PATCH /attendance/days/{DAY_001}` `{"status":"absent"}` | `AUTH_FORBIDDEN` | 403 | `SELECT status FROM attendance_days WHERE id=:day1` → unchanged | **P0** |
| TC-ATT-027 | Attendance / `GET /employees/{id}/attendance/days` | Employee history within a window | `ADMIN_USER` | `GET /employees/{EMP_001}/attendance/days?from=2026-07-01&to=2026-07-31` | Paginated history | 200 | total = `SELECT count(*) FROM attendance_days WHERE org_id=1 AND employee_id=:emp1 AND attendance_date BETWEEN '2026-07-01' AND '2026-07-31'` | P1 |
| TC-ATT-028 | Attendance / `GET /employees/{id}/attendance/calendar` | Monthly calendar cells | `ADMIN_USER` | `GET /employees/{EMP_001}/attendance/calendar?month=7&year=2026` | Array of `AttendanceMonthlyDaySchema` (`attendance_date`, `status`, `first_in`, `worked_minutes`, `is_regularized`, `leave_id`) | 200 | n/a (read-only) | P1 |
| TC-ATT-029 | Attendance / `GET /employees/{id}/attendance/calendar` | Boundary: `month=0` / `month=13` / `year=1899` | `ADMIN_USER` | those three query strings | All `VALIDATION_ERROR` (`1 ≤ month ≤ 12`, `1900 ≤ year ≤ 2100`) | 422 | n/a (read-only) | P2 |
| TC-ATT-030 | Attendance / `GET /employees/{id}/attendance/calendar` | Cross-org employee | `ADMIN_USER` | `GET /employees/{EMP_B01}/attendance/calendar?month=7&year=2026` | **404** `EMPLOYEE_NOT_FOUND` | 404 | n/a (read-only) | **P0** |

### 5.2 Punches

| ID | Module / API | Test Scenario | Preconditions | Request / Input | Expected Result | HTTP | Database Verification | Priority |
|---|---|---|---|---|---|---|---|---|
| TC-ATT-031 | Attendance / `POST /attendance/punches` | Manual punch **lazily creates** the attendance day | `ADMIN_USER`; no day exists for `EMP_002` on `2026-07-08` | `POST /attendance/punches?employee_id={EMP_002}&punch_time=2026-07-08T09:03:00&punch_type=in` | 201; `data.attendance_day_id` points at a newly created day; `data.sequence_no = 1`; `data.punch_source = "manual_entry"` | 201 | `SELECT count(*) FROM attendance_days WHERE employee_id=:emp2 AND attendance_date='2026-07-08'` → `1` (auto-created); `SELECT punch_type, sequence_no, is_valid FROM attendance_punches WHERE id=:p` → `('in',1,true)` | P1 |
| TC-ATT-032 | Attendance / `POST /attendance/punches` | Second punch on the same day increments `sequence_no` | `ADMIN_USER`; TC-ATT-031 ran | `POST /attendance/punches?employee_id={EMP_002}&punch_time=2026-07-08T18:04:00&punch_type=out` | 201; `data.sequence_no = 2` | 201 | `SELECT count(*) FROM attendance_punches WHERE attendance_day_id=:d` → `2`; the day's `last_punch_out` / `total_working_minutes` are recomputed (`> 0`) | P1 |
| TC-ATT-033 | Attendance / `POST /attendance/punches` | Invalid `punch_type` | `ADMIN_USER` | `?punch_type=IN` (allowed `in\|out\|break_in\|break_out`) | `VALIDATION_ERROR` | 422 | no punch inserted | P2 |
| TC-ATT-034 | Attendance / `POST /attendance/punches` | GPS boundary values | `ADMIN_USER` | `?latitude=91&longitude=0` then `?latitude=12.9716&longitude=77.5946` | First `VALIDATION_ERROR` (`-90 ≤ lat ≤ 90`); second 201 | 422 / 201 | `SELECT latitude, longitude FROM attendance_punches WHERE id=:p` → `(12.971600, 77.594600)` | P2 |
| TC-ATT-035 | Attendance / `POST /attendance/punches` | Cross-tenant employee | `ADMIN_USER` | `?employee_id={EMP_B01}&punch_time=…&punch_type=in` | **404** `EMPLOYEE_NOT_FOUND` | 404 | `SELECT count(*) FROM attendance_punches WHERE employee_id=:emp_b01 AND org_id=1` → `0` | **P0** |
| TC-ATT-036 | Attendance / `POST /attendance/punches` | Missing `attendance_punch:create` | user with `attendance:*` but no `attendance_punch` perms | valid punch request | `AUTH_FORBIDDEN` | 403 | no punch inserted, **no day auto-created** | **P0** |
| TC-ATT-037 | Attendance / `GET /attendance/punches` | List raw punch logs in a window | `ADMIN_USER` | `GET /attendance/punches?from=2026-07-01&to=2026-07-31&employee_id={EMP_001}` | Paginated `AttendancePunchSchema` | 200 | total = `SELECT count(*) FROM attendance_punches WHERE org_id=1 AND employee_id=:emp1 AND punch_time::date BETWEEN '2026-07-01' AND '2026-07-31'` | P1 |
| TC-ATT-038 | Attendance / `GET /attendance/punches` | Missing the required `from` / `to` | `ADMIN_USER` | `GET /attendance/punches` | `VALIDATION_ERROR` | 422 | n/a (read-only) | P2 |
| TC-ATT-039 | Attendance / `GET /attendance/days/{day_id}/punches` | Chronological punches for a day | `ADMIN_USER` | `GET /attendance/days/{DAY_001}/punches` | Punches ordered by `sequence_no` | 200 | count = `SELECT count(*) FROM attendance_punches WHERE attendance_day_id=:day1` | P1 |
| TC-ATT-040 | Attendance / `GET /attendance/days/{day_id}/punches` | Unknown / cross-tenant day | `ADMIN_USER` | `GET /attendance/days/{DAY_B01}/punches` | **404** `ATTENDANCE_DAY_NOT_FOUND` — the other tenant's punches are never returned | 404 | n/a (read-only) | **P0** |
| TC-ATT-041 | Attendance / `GET /employees/{id}/attendance/punches` | Punch timeline for an employee | `ADMIN_USER` | `GET /employees/{EMP_001}/attendance/punches?from=2026-07-01&to=2026-07-31` | Chronological array | 200 | n/a (read-only) | P1 |
| TC-ATT-042 | Attendance / `GET /employees/{id}/attendance/punches` | Cross-org employee | `ADMIN_USER` | `GET /employees/{EMP_B01}/attendance/punches?from=…&to=…` | **404** `EMPLOYEE_NOT_FOUND` | 404 | n/a (read-only) | **P0** |

### 5.3 Penalties (money — all P0/P1)

| ID | Module / API | Test Scenario | Preconditions | Request / Input | Expected Result | HTTP | Database Verification | Priority |
|---|---|---|---|---|---|---|---|---|
| TC-ATT-043 | Attendance / `POST /attendance/penalties` | Apply a penalty | `ADMIN_USER` | `POST /attendance/penalties?employee_id={EMP_001}&attendance_day_id={DAY_001}&penalty_type=late_coming&penalty_unit=amount&penalty_value=500.00&remarks=late%2030m` | 201; `data.status = "active"`, `data.applied_by = <actor>` | 201 | `SELECT penalty_type, penalty_unit, penalty_value, status, applied_by, is_deleted FROM attendance_penalties WHERE id=:p` → `('late_coming','amount',500.00,'active',<actor>,false)` | **P0** |
| TC-ATT-044 | Attendance / `POST /attendance/penalties` | Negative `penalty_value` | `ADMIN_USER` | `&penalty_value=-1` | `VALIDATION_ERROR` ("Penalty value cannot be negative.") | 422 | `SELECT count(*) FROM attendance_penalties WHERE attendance_day_id=:day1` → unchanged | **P0** |
| TC-ATT-045 | Attendance / `POST /attendance/penalties` | Invalid `penalty_type` / `penalty_unit` enums | `ADMIN_USER` | `&penalty_type=late` then `&penalty_unit=rupees` | Both `VALIDATION_ERROR` (types: `late_coming\|early_going\|absent_without_notice\|other`; units: `amount\|days\|hours`) | 422 | no row inserted | P2 |
| TC-ATT-046 | Attendance / `POST /attendance/penalties` | **The attendance day must belong to the named employee** | `ADMIN_USER`; `DAY_001` belongs to `EMP_001` | `?employee_id={EMP_002}&attendance_day_id={DAY_001}&…` | **404** ("Attendance day matching employee context not found.", generic `NOT_FOUND`) — you cannot fine one employee against another's day | 404 | `SELECT count(*) FROM attendance_penalties WHERE employee_id=:emp2` → `0` | **P0** |
| TC-ATT-047 | Attendance / `POST /attendance/penalties` | Cross-tenant attendance day | `ADMIN_USER` | `?employee_id={EMP_001}&attendance_day_id={DAY_B01}&…` | **404** | 404 | `SELECT count(*) FROM attendance_penalties WHERE attendance_day_id=:day_b01` → `0` | **P0** |
| TC-ATT-048 | Attendance / `POST /attendance/penalties` | Missing `attendance_penalty:create` | user without penalty perms | valid request | `AUTH_FORBIDDEN` | 403 | no row inserted | **P0** |
| TC-ATT-049 | Attendance / `GET /attendance/penalties` | List with filters | `ADMIN_USER` | `GET /attendance/penalties?employee_id={EMP_001}&status=active&page_size=50` | Paginated `AttendancePenaltySchema` | 200 | total = `SELECT count(*) FROM attendance_penalties WHERE org_id=1 AND employee_id=:emp1 AND status='active' AND is_deleted=false` | P1 |
| TC-ATT-050 | Attendance / `GET /attendance/penalties/{penalty_id}` | Penalty detail | `ADMIN_USER` | `GET /attendance/penalties/{PENALTY_001}` | Full penalty record | 200 | n/a (read-only) | P1 |
| TC-ATT-051 | Attendance / `GET /attendance/penalties/{penalty_id}` | Unknown / soft-deleted penalty | `ADMIN_USER` | `GET /attendance/penalties/99999999` | `error.code = "PENALTY_NOT_FOUND"` | 404 | n/a (read-only) | P1 |
| TC-ATT-052 | Attendance / `GET /attendance/penalties/{penalty_id}` | Cross-tenant penalty | `ADMIN_USER` | `GET /attendance/penalties/{PENALTY_B01}` | **404** `PENALTY_NOT_FOUND` | 404 | n/a (read-only) | **P0** |
| TC-ATT-053 | Attendance / `POST /attendance/penalties/{id}/waive` | Waive an active penalty | `ADMIN_USER` | `POST /attendance/penalties/{PENALTY_001}/waive?remarks=first%20offence` | 200; `data.status = "waived"`; `data.remarks` carries the appended waive note | 200 | `SELECT status, remarks FROM attendance_penalties WHERE id=:p1` → `status='waived'`, remarks contain `Waived: first offence`; the row is **retained** | **P0** |
| TC-ATT-054 | Attendance / `POST /attendance/penalties/{id}/waive` | **Waiving twice is rejected** | `ADMIN_USER`; `PENALTY_WAIVED` | `POST /attendance/penalties/{PENALTY_WAIVED}/waive` | **409**, `error.code = "PENALTY_ALREADY_WAIVED"` | 409 | `SELECT status, remarks FROM attendance_penalties WHERE id=:pw` → **unchanged** (no second waive note appended) | **P0** |
| TC-ATT-055 | Attendance / `POST /attendance/penalties/{id}/waive` | Unknown penalty | `ADMIN_USER` | `POST /attendance/penalties/99999999/waive` | `error.code = "PENALTY_NOT_FOUND"` | 404 | no row changed | P1 |
| TC-ATT-056 | Attendance / `POST /attendance/penalties/{id}/waive` | Missing `attendance_penalty:edit` | user with `attendance_penalty:read` | `POST /attendance/penalties/{PENALTY_001}/waive` | `AUTH_FORBIDDEN` | 403 | `SELECT status FROM attendance_penalties WHERE id=:p1` → still `active` — **money is not written off without the permission** | **P0** |
| TC-ATT-057 | Attendance / `POST /attendance/penalties/{id}/waive` | Cross-tenant waive attempt | `ADMIN_USER` | `POST /attendance/penalties/{PENALTY_B01}/waive` | **404** `PENALTY_NOT_FOUND` | 404 | `SELECT status FROM attendance_penalties WHERE id=:penalty_b01` → still `active` | **P0** |
| TC-ATT-058 | Attendance / `GET /employees/{id}/attendance/penalties` | Employee penalty history (active + waived) | `ADMIN_USER` | `GET /employees/{EMP_001}/attendance/penalties` | Both active and waived penalties returned | 200 | count = `SELECT count(*) FROM attendance_penalties WHERE org_id=1 AND employee_id=:emp1` | P1 |

### 5.4 Corrections / regularization

| ID | Module / API | Test Scenario | Preconditions | Request / Input | Expected Result | HTTP | Database Verification | Priority |
|---|---|---|---|---|---|---|---|---|
| TC-ATT-059 | Attendance / `POST /attendance/corrections` | **Settings gate — fires out of the box** | `ADMIN_USER`; `org_settings` row absent **or** `enable_regularization = false` (the schema DEFAULT) | `POST /attendance/corrections` `{"employee_id":{EMP_001},"date":"2026-07-01","requested_in":"2026-07-01T09:00:00","requested_out":"2026-07-01T18:00:00","reason":"biometric failure"}` | **409**, `error.code = "REGULARIZATION_DISABLED"` | 409 | `SELECT count(*) FROM attendance_regularization_requests WHERE employee_id=:emp1 AND attendance_date='2026-07-01'` → **`0`**; `SELECT count(*) FROM approval_requests WHERE request_type='attendance' AND employee_id=:emp1` → **`0`** — neither row is created | **P0** |
| TC-ATT-060 | Attendance / `POST /attendance/corrections` | Correction accepted once the toggle is on | `ADMIN_USER`; `UPDATE org_settings SET enable_regularization = true WHERE org_id = 1`; `DAY_001` exists | same body as TC-ATT-059 | **201**; `data.status = "pending"`; `data.new_punch_time = "09:00 - 18:00"` | 201 | `SELECT status, employee_reason FROM attendance_regularization_requests WHERE id=:r` → `('pending','biometric failure')`; **and** a paired polymorphic row: `SELECT request_type, reference_id, status FROM approval_requests WHERE reference_id=:r` → `('attendance', :r, 'pending')` | **P0** |
| TC-ATT-061 | Attendance / `POST /attendance/corrections` | No attendance day on the requested date | `ADMIN_USER`; toggle on; no day on `2026-07-09` | body with `"date":"2026-07-09"` | `error.code = "ATTENDANCE_DAY_NOT_FOUND"` | 404 | no `attendance_regularization_requests` row | P1 |
| TC-ATT-062 | Attendance / `POST /attendance/corrections` | `requested_out` ≤ `requested_in` | `ADMIN_USER`; toggle on | `"requested_in":"…T18:00:00","requested_out":"…T09:00:00"` | `VALIDATION_ERROR` ("requested_out must be chronologically after requested_in") | 422 | no rows created | P2 |
| TC-ATT-063 | Attendance / `POST /attendance/corrections` | Cross-tenant employee | `ADMIN_USER`; toggle on | `"employee_id":{EMP_B01}` | **404** `EMPLOYEE_NOT_FOUND` | 404 | no rows created in either table | **P0** |
| TC-ATT-064 | Attendance / `POST /attendance/corrections` | The gate is evaluated **per tenant** | ORG_A `enable_regularization = true`, ORG_B `false` | `ORG_B_ADMIN` posts a valid correction for `EMP_B01` | **409 `REGULARIZATION_DISABLED`** for ORG_B even though ORG_A is enabled | 409 | `SELECT count(*) FROM attendance_regularization_requests WHERE employee_id=:emp_b01` → `0` | **P0** |
| TC-ATT-065 | Attendance / `PUT /attendance/corrections/{request_id}/approve` | Approve a pending correction — the day is updated and flagged regularized | `ADMIN_USER`; the request from TC-ATT-060 (approval id `AR_1`) | `PUT /attendance/corrections/{AR_1}/approve` `{"decision":"approved","comment":"verified"}` | 200; message `Regularization request status updated to approved.` | 200 | `SELECT status, reviewed_by, reviewed_at FROM approval_requests WHERE id=:ar1` → `('approved',<actor>,not null)`; `SELECT status FROM attendance_regularization_requests WHERE id=:r` → `approved`; `SELECT is_regularized, first_punch_in, last_punch_out FROM attendance_days WHERE id=:day1` → `is_regularized = true` and the punch window matches the request | **P0** |
| TC-ATT-066 | Attendance / `PUT /attendance/corrections/{request_id}/approve` | Reject a pending correction — the day is NOT modified | `ADMIN_USER`; a fresh pending request `AR_2` | `PUT /attendance/corrections/{AR_2}/approve` `{"decision":"rejected","comment":"no evidence"}` | 200 | 200 | `SELECT status, reject_remarks FROM approval_requests WHERE id=:ar2` → `('rejected','no evidence')`; `SELECT is_regularized, total_working_minutes FROM attendance_days WHERE id=:day` → **unchanged** | **P0** |
| TC-ATT-067 | Attendance / `PUT /attendance/corrections/{request_id}/approve` | **Double decision rejected** | `ADMIN_USER`; `AR_1` already approved | `PUT /attendance/corrections/{AR_1}/approve` `{"decision":"rejected"}` | **409**, `error.code = "request_already_processed"` | 409 | `SELECT status FROM approval_requests WHERE id=:ar1` → still `approved`; `attendance_days` unchanged | **P0** |
| TC-ATT-068 | Attendance / `PUT /attendance/corrections/{request_id}/approve` | Invalid `decision` value | `ADMIN_USER` | `{"decision":"maybe"}` | `VALIDATION_ERROR` (allowed `pending\|approved\|rejected`) | 422 | no row changed | P2 |
| TC-ATT-069 | Attendance / `PUT /attendance/corrections/{request_id}/approve` | Unknown request id | `ADMIN_USER` | `PUT /attendance/corrections/99999999/approve` `{"decision":"approved"}` | **404** ("Approval request not found.") | 404 | no row changed | P1 |
| TC-ATT-070 | Attendance / `PUT /attendance/corrections/{request_id}/approve` | **Cross-tenant approval id** | `ADMIN_USER` | `PUT /attendance/corrections/{AR_B1}/approve` `{"decision":"approved"}` | **404** — the approval lookup is org-scoped, so ORG_A cannot approve ORG_B's regularization | 404 | `SELECT status FROM approval_requests WHERE id=:ar_b1` → still `pending` | **P0** |
| TC-ATT-071 | Attendance / `PUT /attendance/corrections/{request_id}/approve` | Missing `attendance:edit` | user with `attendance:read` + `attendance:create` | valid approve body | `AUTH_FORBIDDEN` | 403 | `SELECT status FROM approval_requests WHERE id=:ar` → still `pending` | **P0** |

### 5.5 Summaries, reports, missing punches, lock, recompute

| ID | Module / API | Test Scenario | Preconditions | Request / Input | Expected Result | HTTP | Database Verification | Priority |
|---|---|---|---|---|---|---|---|---|
| TC-ATT-072 | Attendance / `GET /attendance/summary/daily` | Daily summary counters | `ADMIN_USER` | `GET /attendance/summary/daily?date=2026-07-01&branch_id={BRANCH_1}` | Counter object (present / absent / half-day / on-leave …) | 200 | counters reconcile with `SELECT status, count(*) FROM attendance_days WHERE org_id=1 AND attendance_date='2026-07-01' GROUP BY status` | P1 |
| TC-ATT-073 | Attendance / `GET /attendance/summary/monthly` | Monthly consolidated summary | `ADMIN_USER` | `GET /attendance/summary/monthly?month=7&year=2026&employee_id={EMP_001}` | Array of per-employee monthly aggregates | 200 | totals reconcile with `SELECT sum(total_working_minutes), sum(overtime_minutes) FROM attendance_days WHERE employee_id=:emp1 AND attendance_date BETWEEN '2026-07-01' AND '2026-07-31'` | P1 |
| TC-ATT-074 | Attendance / `GET /attendance/summary/monthly` | Boundary: `month=13`, `year=2101` | `ADMIN_USER` | those query strings | `VALIDATION_ERROR` | 422 | n/a (read-only) | P2 |
| TC-ATT-075 | Attendance / `GET /attendance/reports/employee` | Employee report over a range | `ADMIN_USER` | `GET /attendance/reports/employee?employee_id={EMP_001}&from=2026-07-01&to=2026-07-31` | `data.summary` (days present/absent/half-day/on-leave, working, overtime, late, early minutes) + `data.records[]` | 200 | `data.summary.days_present` = `SELECT count(*) FROM attendance_days WHERE employee_id=:emp1 AND status='present' AND attendance_date BETWEEN …` | P1 |
| TC-ATT-076 | Attendance / `GET /attendance/reports/employee` | Cross-org employee | `ADMIN_USER` | `?employee_id={EMP_B01}&from=…&to=…` | **404** `EMPLOYEE_NOT_FOUND` — no ORG_B attendance may leak through a report | 404 | n/a (read-only) | **P0** |
| TC-ATT-077 | Attendance / `GET /attendance/reports/department` | Department report | `ADMIN_USER` | `GET /attendance/reports/department?department={DEPT_1}&from=2026-07-01&to=2026-07-31` | Consolidated aggregate (note the query alias is `department`, not `department_id`) | 200 | n/a (read-only) | P1 |
| TC-ATT-078 | Attendance / `GET /attendance/reports/branch` | Branch report | `ADMIN_USER` | `GET /attendance/reports/branch?branch={BRANCH_1}&from=2026-07-01&to=2026-07-31` | Consolidated aggregate (alias `branch`) | 200 | n/a (read-only) | P1 |
| TC-ATT-079 | Attendance / `GET /attendance/reports/shift` | Shift-wise report | `ADMIN_USER` | `GET /attendance/reports/shift?shift={SHIFT_GENERAL}&from=2026-07-01&to=2026-07-31` | Consolidated aggregate (alias `shift`) | 200 | rows counted only where `attendance_days.shift_id = SHIFT_GENERAL` | P1 |
| TC-ATT-080 | Attendance / reports | Missing the required `from` / `to` on any report | `ADMIN_USER` | `GET /attendance/reports/branch?branch=1` | `VALIDATION_ERROR` | 422 | n/a (read-only) | P2 |
| TC-ATT-081 | Attendance / reports & summaries | Missing `attendance:read` | user with `attendance_punch:read` only | any report endpoint | `AUTH_FORBIDDEN` | 403 | n/a (read-only) | **P0** |
| TC-ATT-082 | Attendance / `GET /attendance/missing-punches` | Flag days with an unpaired punch | `ADMIN_USER`; `EMP_002` has a single `in` punch on `2026-07-10` and no `out` | `GET /attendance/missing-punches?from=2026-07-01&to=2026-07-31` | Item for `EMP_002` on `2026-07-10` with `punch_type="in"` and `missing_type="out"`; `employee_code` and `employee_name` populated | 200 | the flagged day satisfies `SELECT count(*) FROM attendance_punches WHERE attendance_day_id=:d AND punch_type='out'` → `0` | P1 |
| TC-ATT-083 | Attendance / `GET /attendance/missing-punches` | Complete days are not flagged | `ADMIN_USER`; `DAY_001` has both `in` and `out` | same request | `DAY_001` / `EMP_001` is **absent** from the results | 200 | n/a (read-only) | P1 |
| TC-ATT-084 | Attendance / `GET /attendance/missing-punches` | Branch filter + pagination | `ADMIN_USER` | `?from=…&to=…&branch_id={BRANCH_2}&page=1&page_size=10` | Only that branch's employees | 200 | n/a (read-only) | P2 |
| TC-ATT-085 | Attendance / `POST /attendance/lock` | Freeze a period | `ADMIN_USER` | `POST /attendance/lock` `{"period_start":"2026-06-01","period_end":"2026-06-30","scope":"company","reason":"payroll run"}` | 200; `data = true` | 200 | **There is no `attendance_locks` table** — the operation is a no-op that only audits (see [DEF-06](#appendix-a--error-code-drift-defects)). Verify: `SELECT count(*) FROM activity_logs WHERE title='Attendance Lock Triggered' AND org_id=1` → increments by 1, and **no** `attendance_days` row has changed (`is_locked` is not persisted; the schema always serialises it as `false`) | P1 |
| TC-ATT-086 | Attendance / `POST /attendance/lock` | `scope=branch` without `branch_id` | `ADMIN_USER` | `{"period_start":"2026-06-01","period_end":"2026-06-30","scope":"branch"}` | `VALIDATION_ERROR` ("branch_id is required when scope is branch") | 422 | no audit row written | P2 |
| TC-ATT-087 | Attendance / `POST /attendance/lock` | `period_end` before `period_start` | `ADMIN_USER` | `{"period_start":"2026-06-30","period_end":"2026-06-01","scope":"company"}` | `VALIDATION_ERROR` | 422 | no audit row written | P2 |
| TC-ATT-088 | Attendance / `POST /attendance/lock` | **A locked period does not actually block mutations** (regression guard) | `ADMIN_USER`; TC-ATT-085 ran for June | `PATCH /attendance/days/{JUNE_DAY}` `{"status":"absent"}` | The edit **succeeds** (200) because locking is not enforced. Track against [DEF-06](#appendix-a--error-code-drift-defects); flip this to "expect 409" when locking is implemented | 200 | `SELECT status FROM attendance_days WHERE id=:june_day` → `absent` — demonstrating the gap | P1 |
| TC-ATT-089 | Attendance / `POST /attendance/{employee_id}/recompute` | Recompute a day's metrics from its punches | `ADMIN_USER`; `DAY_001` has punches `09:30` → `18:30` but stale counters | `POST /attendance/{EMP_001}/recompute` `{"date":"2026-07-01"}` | 200; `data.total_working_minutes` recomputed; `expected_start_time` / `expected_end_time` refreshed from the resolved shift | 200 | `SELECT total_working_minutes, late_minutes, expected_start_time FROM attendance_days WHERE id=:day1` → recomputed values (e.g. `540`, `30` late against a `09:00` shift start) | **P0** |
| TC-ATT-090 | Attendance / `POST /attendance/{employee_id}/recompute` | Recompute is idempotent | `ADMIN_USER` | run TC-ATT-089 twice | Identical `data` both times | 200 | second run leaves `total_working_minutes` / `late_minutes` unchanged | P1 |
| TC-ATT-091 | Attendance / `POST /attendance/{employee_id}/recompute` | No attendance day on that date | `ADMIN_USER` | `POST /attendance/{EMP_001}/recompute` `{"date":"2030-01-01"}` | `error.code = "ATTENDANCE_DAY_NOT_FOUND"` | 404 | no row created | P1 |
| TC-ATT-092 | Attendance / `POST /attendance/{employee_id}/recompute` | Cross-org employee | `ADMIN_USER` | `POST /attendance/{EMP_B01}/recompute` `{"date":"2026-07-01"}` | **404** `EMPLOYEE_NOT_FOUND` | 404 | `SELECT total_working_minutes FROM attendance_days WHERE id=:day_b01` → unchanged | **P0** |
| TC-ATT-093 | Attendance / all endpoints | Unauthenticated | none | `GET /attendance/days?date=2026-07-01` with no token | `AUTH_NOT_AUTHENTICATED` | 401 | n/a (read-only) | **P0** |
| TC-ATT-094 | Attendance / all endpoints | Token without `org_id` | `NO_ORG_USER` | `GET /attendance/days?date=2026-07-01` | `TENANT_UNRESOLVED` | 400 | n/a (read-only) | P1 |

---

## 6. End-to-End Workflows

| ID | Module / API | Test Scenario | Preconditions | Request / Input | Expected Result | HTTP | Database Verification | Priority |
|---|---|---|---|---|---|---|---|---|
| TC-ESA-E2E-001 | Employee → Shift → Attendance | **Full lifecycle**: onboard → assign shift → punch → correct → transfer → terminate | `ADMIN_USER`; `enable_regularization = true` for ORG_A | 1. `POST /employees` (new hire, joining `2026-07-01`) → 201 · 2. `PUT /employees/{id}/weekoffs` (Sunday off) → 200 · 3. `POST /shift-assignments` (`SHIFT_GENERAL`, from `2026-07-01`) → 201 · 4. `POST /attendance/punches` in @`09:30`, out @`18:30` on `2026-07-02` → 201 ×2 · 5. `POST /attendance/corrections` (in `09:00`) → 201 · 6. `PUT /attendance/corrections/{id}/approve` `{"decision":"approved"}` → 200 · 7. `POST /employees/{id}/transfer` (`BRANCH_2`) → 200 · 8. `POST /employees/{id}/terminate` (`2026-07-31`) → 200 | Every step succeeds in order with the statuses shown | 201/200 | `employees`: `employment_status='terminated'`, `date_of_leaving='2026-07-31'`, `master_branch_id=BRANCH_2` · `employee_status_history`: ≥2 rows for the employee · `shift_assignments`: 1 row · `attendance_days`: 1 row for `2026-07-02` with `is_regularized=true` and `first_punch_in='09:00'` · `attendance_punches`: 2 rows · `approval_requests`: 1 row `status='approved'` | **P0** |
| TC-ESA-E2E-002 | Shift → Attendance | Roster / weekly-off drives shift resolution and the attendance day | `ADMIN_USER`; `advance_shift_enabled=true` | 1. `POST /shift-rotations` over a 14-day horizon → 202 · 2. `GET /shifts/resolve?employee_id=…&date=<a Sunday in range>` · 3. `POST /attendance/punches` on that Sunday | Step 2 returns `is_weekly_off=true`, `is_working_day=false`; step 3 still records the punch and creates the day (a punch on a week-off is not blocked) | 202 / 200 / 201 | `roster` rows on the employee's week-off carry `is_week_off=true AND shift_id IS NULL`; the auto-created `attendance_days` row for that Sunday has `shift_id IS NULL` | P1 |
| TC-ESA-E2E-003 | Employee (sensitive data) | Two callers, one employee: the salary/bank surface differs by permission | `HR_USER` and `PAYROLL_USER`; `EMP_001` | Both call `GET /employees/{EMP_001}` and `GET /employees/{EMP_001}/bank-details` | `HR_USER`: detail → **200** with `salary=null`, `bank_details=[]`; standalone bank-details → **403 `AUTH_FORBIDDEN`**. `PAYROLL_USER`: both → **200** with the real values. Neither call mutates anything | 200 / 403 | `SELECT monthly_salary FROM employees WHERE employee_id=:emp1` → `50000.00` (unchanged); `SELECT count(*) FROM employee_bank_details WHERE employee_id=:emp1 AND is_deleted=false` → unchanged | **P0** |
| TC-ESA-E2E-004 | Cross-module tenant isolation sweep | An ORG_A admin cannot touch ANY ORG_B object by id | `ADMIN_USER` | Fire, in one pass: `GET /employees/{EMP_B01}` · `GET /employees/{EMP_001}/documents/{DOC_B1}` · `GET /shifts/{SHIFT_B1}` · `PATCH /shift-assignments/{ASSIGN_B1}` · `PATCH /roster/{ROSTER_B1}` · `GET /attendance/days/{DAY_B01}` · `POST /attendance/penalties/{PENALTY_B01}/waive` · `PUT /attendance/corrections/{AR_B1}/approve` | **Every one returns 404** with its module's not-found code. **Zero 403s** (a 403 would confirm the id exists) and zero 200s | 404 ×8 | For each ORG_B row, re-select and assert it is byte-for-byte unchanged; `SELECT count(*) FROM <table> WHERE org_id=1 AND id=<orgB id>` → `0` in every case | **P0** |
| TC-ESA-E2E-005 | Settings → Attendance / Shift gates | Both org-level toggles behave as blocking gates and are per-tenant | `ADMIN_USER`; ORG_A settings row deleted (⇒ both toggles fall back to the schema default `false`) | 1. `POST /attendance/corrections` → **409 `REGULARIZATION_DISABLED`** · 2. `POST /shift-rotations` → **409 `ADVANCE_SHIFT_DISABLED`** · 3. enable both in `org_settings` · 4. repeat 1 and 2 | Steps 1–2 blocked; steps 4 succeed (201 / 202) | 409 → 201/202 | Before: `attendance_regularization_requests` and `roster` gain **0** rows. After enabling: both gain rows. The absence of an `org_settings` row must behave exactly like `false`, not crash | **P0** |
| TC-ESA-E2E-006 | Terminated employee — downstream behaviour | Confirm what a terminal status does *not* cascade | `ADMIN_USER`; `EMP_001` terminated with `date_of_leaving='2026-07-31'` | `GET /employees/{EMP_001}` · `GET /employees/{EMP_001}/shift-assignments` · `POST /shift-assignments` with `effective_from='2026-09-01'` · `POST /attendance/punches` dated after termination | Document the actual behaviour: the employee is still readable (200); the existing assignment rows are retained; new assignments/punches for a terminated employee are **not currently blocked** — record the observed status codes | 200 | `SELECT employment_status FROM employees WHERE employee_id=:emp1` → `terminated`; `SELECT count(*) FROM shift_assignments WHERE employee_id=:emp1` → retained. Raise a product question if post-termination assignment/punching must be refused — no rule enforces it today | P1 |

---

## Appendix A — Error-code drift (defects)

Every code asserted above was grepped and exists in the codebase. These six items are places where the **emitted** code does not match the code the exceptions module / contract *documents*. The test cases assert what the API actually returns today; each line is a defect to be triaged.

| # | Endpoint(s) | Contract / exception class says | Actually emitted | Evidence | Impact |
|---|---|---|---|---|---|
| DEF-01 | Every employee route resolving `{employee_id}` | `EMPLOYEE_NOT_FOUND` (`EmployeeNotFoundException`, `app/modules/employee/exceptions.py:14`) | `not_found` | `EmployeeNotFoundException` is **exported but never raised**; `EmployeeService._get_active_employee` / `_load_detail` raise `NotFoundException(code="not_found")` (`service.py:1246`, `1390`). Note the Shift and Attendance modules *do* emit `EMPLOYEE_NOT_FOUND` for the same entity — so the same missing employee yields **two different codes** depending on the module. | Clients cannot branch on a stable code. P1 |
| DEF-02 | `POST /shifts`, `PATCH /shifts/{id}` | `SHIFT_NAME_EXISTS` | `duplicate_shift_name` | `shift/service.py:156`, `:196`. `ShiftNameExistsException` is raised **only** by `restore_shift` (`:290`). | Two codes for one rule. P2 |
| DEF-03 | `GET /shifts/{id}`, `PATCH /shifts/{id}`, `DELETE /shifts/{id}`, `POST /shift-assignments` | `SHIFT_NOT_FOUND` | `not_found` | These paths use `_get_active_shift` / `_load_shift_detail` (`code="not_found"`, `:1314`, `:1332`), while `_require_shift` (`:1265`) — used by the timings and roster paths — correctly raises `SHIFT_NOT_FOUND`. Same duplication for `_get_active_employee` vs `_require_employee`. | Inconsistent 404 codes within one module. P1 |
| DEF-04 | `DELETE /shifts/{id}` | `SHIFT_IN_USE` | `shift_in_use` | `shift/service.py:257`, `:262`. `ShiftInUseException` is **never raised**. | Case-sensitive clients break. P2 |
| DEF-05 | `PUT /roster` | `ROSTER_ENTRY_EXISTS` | *never emitted* | `PUT /roster` is an **upsert** (`upsert_roster_entry` → `_write_roster_entry`), so a pre-existing `(employee_id, roster_date)` is updated, not rejected. `RosterEntryExistsException` is dead code. | Either the contract or the code is wrong — needs a product decision. P2 |
| DEF-06 | `POST /attendance/lock` | Freezes the period; `attendance_days.is_locked` reflects it | Returns `true`, writes an audit row, **changes nothing** | `attendance/service.py:1380` — *"no-op as there is no DB backing for locks"*. There is no `attendance_locks` table and `is_locked` is a schema-only field that always serialises `false`. Post-payroll days remain editable (TC-ATT-088). | **Data-integrity risk**: attendance can be edited after payroll is run. P0 — this is the most serious item in this appendix. |

Secondary observations (not code drift, but worth recording):

* `POST /employees/{id}/documents` persists `expires_at` **nowhere** — the field is accepted by `EmployeeDocumentCreateRequest` and silently dropped (no column in the approved schema). A client that sets an expiry gets a 201 and no expiry.
* `POST /shift-rotations` is declared `202 Accepted` but runs **synchronously** in-request; a large `horizon_days × employees` product will block the worker.
* `POST /shift-assignments/bulk` and `POST /roster/bulk` return **200**, not 201/207, even when they create rows.

## Appendix B — Coverage matrix

| Dimension | Employee | Shift | Attendance |
|---|---|---|---|
| Endpoints in scope | 32 | 27 | 27 |
| Endpoints with ≥1 case | 32 | 27 | 27 |
| Test cases | 130 | 107 | 94 |
| Functional (happy path) | ✔ every endpoint | ✔ every endpoint | ✔ every endpoint |
| Validation (missing / invalid / boundary / enum casing) | TC-EMP-019…028, 098…101, 118, 125 | TC-SHF-003…010, 033…036, 047, 074, 082…083, 089…091 | TC-ATT-007…008, 013…014, 029, 033…034, 044…045, 062, 068, 074, 086…087 |
| Authentication (401) | TC-EMP-011 | inherited (same dependency) | TC-ATT-093 |
| Authorization — missing permission (403) | TC-EMP-012, 046, 057, 061, 081, 094 | TC-SHF-011, 025, 075, 107 | TC-ATT-009, 026, 036, 048, 056, 071, 081 |
| Authorization — wrong org (404, never 403) | TC-EMP-010, 040, 045, 062, 066, 086, 095, 130 | TC-SHF-014, 017, 049, 056, 061, 067, 078, 092, 097, 102, 106 | TC-ATT-004, 006, 018, 021, 030, 035, 040, 042, 047, 052, 057, 063, 070, 076, 092 |
| Business rules | status lifecycle, primary-bank uniqueness, salary gating, soft vs hard delete | name uniqueness, in-use delete guard, assignment auto-close & overlap, weekoff supersede, uniform/per-day timing rules | day uniqueness, penalty waiver, correction approval, settings gates |
| Settings gates (P0) | — | TC-SHF-069…071 (`ADVANCE_SHIFT_DISABLED`) | TC-ATT-059, 060, 064 (`REGULARIZATION_DISABLED`) |
| Concurrency | TC-EMP-034 | TC-SHF-012 | TC-ATT-010 |
| File-upload security | TC-EMP-072…082 | — | — |
| DB verification | every mutating case asserts a concrete `SELECT` | idem | idem |
| End-to-end | TC-ESA-E2E-001, 003, 004, 006 | TC-ESA-E2E-002, 004, 005 | TC-ESA-E2E-001, 002, 004, 005 |

**Total: 331 executable test cases** (130 Employee + 107 Shift + 94 Attendance) plus 6 end-to-end workflows.
