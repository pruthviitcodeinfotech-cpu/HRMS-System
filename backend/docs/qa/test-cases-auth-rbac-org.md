# QA Test-Case Specification — Authentication, User Management & RBAC, Organization Management

**System:** HRMS Backend (FastAPI modular monolith)
**Base URL:** `{{BASE}}/api/v1`
**Scope:** 3 modules / 73 endpoints (Auth 7, RBAC 42, Organization 24)
**Status:** Production test-case specification. Every error code, path, status code and field name below
is grounded in the implementation (`app/modules/{auth,rbac,organization}/`, `app/core/exceptions/base.py`,
`app/core/security/permissions.py`, `app/core/dependencies/auth.py`).

---

## Table of Contents

1. [Test Data / Preconditions](#1-test-data--preconditions)
2. [Global Conventions](#2-global-conventions)
3. [Module A — Authentication](#3-module-a--authentication-tc-auth)
   - A1. Login · A2. Refresh · A3. Logout · A4. `/auth/me` · A5. Self-service sessions · A6. Token revocation & rate limiting
4. [Module B — User Management & RBAC](#4-module-b--user-management--rbac-tc-rbac)
   - B1. Users · B2. Rights templates (roles) · B3. Template permissions · B4. Permission catalog
   - B5. User↔role assignment · B6. Custom permissions & effective permissions
   - B7. Branch / Department access (data scope) · B8. Session administration
5. [Module C — Organization Management](#5-module-c--organization-management-tc-org)
   - C1. Organizations · C2. Branches · C3. Departments · C4. Designations
6. [End-to-End Workflows](#6-end-to-end-workflows)
7. [Coverage Summary & Known Gaps](#7-coverage-summary--known-gaps)

---

## 1. Test Data / Preconditions

Seed the following before any run. IDs are illustrative; bind them as variables in the test harness.

### Organizations (table `organizations`)

| Fixture | `org_id` | `org_code` | `org_name` | `is_active` | Notes |
|---|---|---|---|---|---|
| `ORG_A` | 1 | `ACME` | Acme Foods | true | Primary tenant under test |
| `ORG_B` | 2 | `GLOBEX` | Globex Corp | true | Isolation tenant — must never be visible from ORG_A |
| `ORG_C` | 3 | `INITECH` | Initech | false | Deactivated tenant |
| `ORG_DEL` | 4 | `OLDCO` | Old Co | true | `is_deleted = true` (soft-deleted) |

### Users (table `users`) — all passwords `Passw0rd!23` unless stated

| Fixture | `org_id` | `id` | email | `is_super_admin` | `is_active` | Permissions (via template) |
|---|---|---|---|---|---|---|
| `SUPER_ADMIN_A` | ORG_A | 10 | `super.a@acme.test` | **true** | true | bypasses all feature checks |
| `ADMIN_A` | ORG_A | 11 | `admin.a@acme.test` | false | true | `ROLE_ADMIN` — full CRUD on `user_management`, `role_management`, `access_management`, `organization`, `branch`, `department`, `designation` |
| `HR_USER_A` | ORG_A | 12 | `hr.a@acme.test` | false | true | `ROLE_HR` — **`employee:read` only** (no user/role/access/org perms) |
| `VIEWER_A` | ORG_A | 13 | `viewer.a@acme.test` | false | true | `ROLE_VIEWER` — `user_management:read`, `role_management:read`, `access_management:read`, `branch:read`, `department:read`, `designation:read` (no create/edit/delete) |
| `INACTIVE_A` | ORG_A | 14 | `inactive.a@acme.test` | false | **false** | `ROLE_VIEWER` |
| `DELETED_A` | ORG_A | 15 | `deleted.a@acme.test` | false | true | `deleted_at = now()` (soft-deleted) |
| `NOPASS_A` | ORG_A | 16 | `nopass.a@acme.test` | false | true | `password_hash IS NULL` |
| `SUPER_ADMIN_B` | ORG_B | 20 | `super.b@globex.test` | true | true | — |
| `ADMIN_B` | ORG_B | 21 | `admin.b@globex.test` | false | true | `ROLE_ADMIN_B` (same grants as ADMIN_A, in ORG_B) |
| `TARGET_A` | ORG_A | 30 | `target.a@acme.test` | false | true | manipulation target for RBAC tests |

### Rights templates (table `rights_templates`)

| Fixture | `org_id` | `id` | `name` | Notes |
|---|---|---|---|---|
| `ROLE_ADMIN` | ORG_A | 100 | `Admin` | assigned to ADMIN_A → `TEMPLATE_IN_USE` on delete |
| `ROLE_HR` | ORG_A | 101 | `HR` | assigned to HR_USER_A |
| `ROLE_VIEWER` | ORG_A | 102 | `Viewer` | assigned to VIEWER_A, INACTIVE_A |
| `ROLE_FREE` | ORG_A | 103 | `Unassigned Role` | **0 assigned users** → deletable |
| `ROLE_DELETED` | ORG_A | 104 | `Archived Role` | `deleted_at = now()` |
| `ROLE_B` | ORG_B | 200 | `Admin` | in ORG_B — name collides across orgs (legal) |
| `ROLE_ADMIN_B` | ORG_B | 201 | `Admin B` | assigned to ADMIN_B |

### Organization hierarchy (tables `branches`, `departments`, `designations`)

| Fixture | Table | `org_id` | id | name | State |
|---|---|---|---|---|---|
| `BRANCH_A1` | branches | ORG_A | 500 | `Mumbai HQ` | active; **referenced by `EMP_001`** |
| `BRANCH_A2` | branches | ORG_A | 501 | `Pune Unit` | active; no employees |
| `BRANCH_A3` | branches | ORG_A | 502 | `Old Depot` | `is_active = false` |
| `BRANCH_B1` | branches | ORG_B | 600 | `Springfield` | ORG_B only |
| `DEPT_A1` | departments | ORG_A | 700 | `Engineering` | active; **referenced by `EMP_001`** |
| `DEPT_A2` | departments | ORG_A | 701 | `Finance` | active; no employees |
| `DEPT_B1` | departments | ORG_B | 800 | `Engineering` | ORG_B (same name — legal cross-org) |
| `DESIG_A1` | designations | ORG_A | 900 | `Manager` | active; **referenced by `EMP_001`** |
| `DESIG_A2` | designations | ORG_A | 901 | `Analyst` | active; no employees |
| `DESIG_B1` | designations | ORG_B | 1000 | `Manager` | ORG_B |

### Employees (table `employees`)

| Fixture | `org_id` | `employee_id` | `master_branch_id` | `dept_id` | `designation_id` | `employment_status` | Notes |
|---|---|---|---|---|---|---|---|
| `EMP_001` | ORG_A | 5001 | 500 | 700 | 900 | `active` | blocks deactivation of BRANCH_A1 / DEPT_A1 / DESIG_A1 |
| `EMP_002` | ORG_A | 5002 | 501 | 701 | 901 | `terminated` | does **not** block deactivation |
| `EMP_003` | ORG_A | 5003 | 501 | 701 | 901 | `active` | **unmapped** to any user (for `PUT /users/{id}/employee`) |
| `EMP_B01` | ORG_B | 6001 | 600 | 800 | 1000 | `active` | ORG_B |

### Tokens / auth fixtures

| Fixture | Definition |
|---|---|
| `TOK_SA_A` | Access token for `SUPER_ADMIN_A` (fresh login, ORG_A) |
| `TOK_ADMIN_A` | Access token for `ADMIN_A` |
| `TOK_HR_A` | Access token for `HR_USER_A` (only `employee:read`) |
| `TOK_VIEWER_A` | Access token for `VIEWER_A` (read-only) |
| `TOK_ADMIN_B` | Access token for `ADMIN_B` (ORG_B) |
| `TOK_EXPIRED` | Access token with `exp` in the past |
| `TOK_NOSID` | JWT signed with the app key but with **no `sid` claim** |
| `TOK_TAMPERED` | `TOK_ADMIN_A` with one payload byte flipped (bad signature) |
| `REFRESH_ADMIN_A` | The `refresh_token` returned by ADMIN_A's login (= `user_sessions.session_token`) |

### Environment settings (from `app/core/config/settings.py`)

`access_token_ttl=900s` · `refresh_token_ttl=1209600s` · `login_rate_limit_attempts=10` / `window=60s` ·
`refresh_rate_limit_attempts=30` / `window=60s` · `login_max_failed_attempts=5` ·
`login_failure_window_seconds=900` · `login_lockout_seconds=900`.
**Redis must be up** for all rate-limit / lockout cases — the throttle *fails open* when Redis is down
(`rate_limit_backend_unavailable` is logged and the throttle is skipped), so a Redis outage silently
voids TC-AUTH-030..036.

---

## 2. Global Conventions

**Success envelope** (`app/shared/schemas/response.py`):
```json
{ "success": true, "message": "...", "data": {...}, "meta": { "request_id": "...", "pagination": {...} } }
```
**Error envelope**:
```json
{ "success": false, "message": "...", "error": { "code": "<CODE>", "message": "...", "details": [...] },
  "meta": { "request_id": "..." } }
```
Assertions on error cases always check `response.error.code` — that is the stable contract, not the message.

**Paged list `data`**: `{ "items": [...], "pagination": { page, page_size, total_records, total_pages, has_next, has_previous } }`.
Pagination bounds: `page >= 1`, `1 <= page_size <= 200`, defaults `page=1, page_size=25`.

**Auth header**: `Authorization: Bearer <token>`. All endpoints except `POST /auth/login` and
`POST /auth/refresh` require one.

**Baseline auth/authz codes** (`app/core/exceptions/base.py`) applied to *every* protected endpoint:

| Condition | code | HTTP |
|---|---|---|
| No / empty `Authorization` header | `AUTH_NOT_AUTHENTICATED` | 401 |
| Malformed, tampered, or expired token | `AUTH_NOT_AUTHENTICATED` | 401 |
| Token has no `sid` claim, or its session is revoked/expired | `AUTH_NOT_AUTHENTICATED` | 401 |
| Token's owner is inactive or soft-deleted | `AUTH_FORBIDDEN` | 403 |
| Authenticated but missing the feature permission | `AUTH_FORBIDDEN` | 403 |
| Resource belongs to another tenant (branch/dept/designation/user/role) | `*_NOT_FOUND` | 404 |

`assert_session_live` (`app/core/dependencies/auth.py`) re-validates the session **on every request**, so
revocation is immediate — see TC-AUTH-024..029.

---

## 3. Module A — Authentication (TC-AUTH)

### A1. `POST /auth/login`

| ID | Module / API | Test Scenario | Preconditions | Request / Input | Expected Result | HTTP | Database Verification | Priority |
|---|---|---|---|---|---|---|---|---|
| TC-AUTH-001 | Auth / Login | Successful login with valid credentials | ADMIN_A active, has password | `POST /auth/login` H:`X-Org-ID: 1` B:`{"email":"admin.a@acme.test","password":"Passw0rd!23","device_info":"pytest"}` | `data` = `{access_token, refresh_token, token_type:"bearer", expires_in:900, user:{id,org_id,name,email,is_super_admin,is_active,...}}`. **No** `password_hash` / `session_token` in body | 200 | `SELECT count(*) FROM user_sessions WHERE user_id=11 AND is_active=true AND revoked_at IS NULL` → +1; new row `session_token` = returned `refresh_token`, `expires_at ≈ now()+14d`, `device_info='pytest'`, `ip_address` = caller IP. `SELECT last_login_at FROM users WHERE id=11` → updated to ~now. `SELECT count(*) FROM activity_logs WHERE module='auth' AND sub_module='session' AND title='User logged in'` → +1 | P0 |
| TC-AUTH-002 | Auth / Login | Access token carries the correct claims | TC-AUTH-001 | Decode `access_token` | Claims contain `sub="11"`, `type="access"`, `org_id=1`, `is_super_admin=false`, `is_active=true`, `sid=<new session id>`, `roles`, `permissions[]`, `branch_ids[]`, `department_ids[]`, `exp - iat = 900` | 200 | `SELECT id FROM user_sessions WHERE session_token=:refresh` → equals the `sid` claim | P0 |
| TC-AUTH-003 | Auth / Login | Email is case- and whitespace-insensitive | ADMIN_A exists | B:`{"email":"  ADMIN.A@ACME.TEST  ","password":"Passw0rd!23"}` | Login succeeds — schema normalises to `admin.a@acme.test` | 200 | New `user_sessions` row for `user_id=11` | P1 |
| TC-AUTH-004 | Auth / Login | Wrong password | ADMIN_A exists | B:`{"email":"admin.a@acme.test","password":"WrongPass1!"}` | `error.code = AUTH_INVALID_CREDENTIALS`, message is non-disclosing ("Invalid email or password.") | 401 | No new `user_sessions` row; `last_login_at` unchanged. Redis `auth:login:failures:1:<hash>` incremented to 1 | P0 |
| TC-AUTH-005 | Auth / Login | Unknown email returns the **same** error as wrong password (no user enumeration) | — | B:`{"email":"ghost@acme.test","password":"anything"}` | `error.code = AUTH_INVALID_CREDENTIALS` — byte-identical envelope to TC-AUTH-004 apart from `request_id` | 401 | No new session. Redis failure counter for the unknown email also increments (no enumeration via lockout) | P0 |
| TC-AUTH-006 | Auth / Login | Inactive user cannot log in | INACTIVE_A (`is_active=false`) | B:`{"email":"inactive.a@acme.test","password":"Passw0rd!23"}` | `error.code = AUTH_INVALID_CREDENTIALS` (not a distinct "inactive" code — non-disclosing) | 401 | `SELECT count(*) FROM user_sessions WHERE user_id=14` → unchanged | P0 |
| TC-AUTH-007 | Auth / Login | Soft-deleted user cannot log in | DELETED_A (`deleted_at` set) | B:`{"email":"deleted.a@acme.test","password":"Passw0rd!23"}` | `error.code = AUTH_INVALID_CREDENTIALS` | 401 | No new session for `user_id=15` | P0 |
| TC-AUTH-008 | Auth / Login | User with NULL `password_hash` cannot log in | NOPASS_A | B:`{"email":"nopass.a@acme.test","password":""}` → then `{"...","password":"x"}` | Empty password → `VALIDATION_ERROR` (422, `min_length=1`); non-empty password → `AUTH_INVALID_CREDENTIALS` (401) | 422 / 401 | No session for `user_id=16`; `password_hash` remains NULL | P0 |
| TC-AUTH-009 | Auth / Login | Cross-tenant credential replay: ORG_A user against ORG_B tenant | ADMIN_A in ORG_A | H:`X-Org-ID: 2` B:`{"email":"admin.a@acme.test","password":"Passw0rd!23"}` | `error.code = AUTH_INVALID_CREDENTIALS` — the lookup is `(org_id, email)`-scoped | 401 | No session row created for `user_id=11` | P0 |
| TC-AUTH-010 | Auth / Login | Missing tenant header | — | `POST /auth/login` **without** `X-Org-ID` B: valid creds | `error.code = TENANT_UNRESOLVED` | 400 | No session created | P0 |
| TC-AUTH-011 | Auth / Login | Non-numeric tenant header | — | H:`X-Org-ID: abc` B: valid creds | `TENANT_UNRESOLVED` (400) — the tenant middleware only accepts digits, the header dependency then rejects | 400 | No session created | P2 |
| TC-AUTH-012 | Auth / Login | Missing `email` field | — | H:`X-Org-ID: 1` B:`{"password":"Passw0rd!23"}` | `error.code = VALIDATION_ERROR`, `error.details[0].field` contains `email` | 422 | n/a (read-only) | P2 |
| TC-AUTH-013 | Auth / Login | Malformed email | — | B:`{"email":"not-an-email","password":"Passw0rd!23"}` | `VALIDATION_ERROR` — "invalid email format" | 422 | n/a (read-only) | P2 |
| TC-AUTH-014 | Auth / Login | `email` exceeds 255 chars / `device_info` exceeds 500 chars | — | B: `email` = 256-char address; separately `device_info` = 501 chars | `VALIDATION_ERROR` (max_length) in both cases | 422 | n/a (read-only) | P2 |
| TC-AUTH-015 | Auth / Login | Password is **not** whitespace-stripped | User whose password is `" pad "` | B:`{"email":...,"password":" pad "}` | Login succeeds — `LoginRequest` sets `str_strip_whitespace=False`. Sending `"pad"` must **fail** with `AUTH_INVALID_CREDENTIALS` | 200 / 401 | Session created only for the exact-match attempt | P1 |

### A2. `POST /auth/refresh`

| ID | Module / API | Test Scenario | Preconditions | Request / Input | Expected Result | HTTP | Database Verification | Priority |
|---|---|---|---|---|---|---|---|---|
| TC-AUTH-016 | Auth / Refresh | Valid refresh token issues a new access token | Live session for ADMIN_A | `POST /auth/refresh` B:`{"refresh_token":"<REFRESH_ADMIN_A>"}` | `data` = `{access_token, token_type:"bearer", expires_in:900, refresh_token: null}` — rotation is **off**; the new access token's `sid` equals the original session id | 200 | `SELECT session_token, is_active, revoked_at FROM user_sessions WHERE id=:sid` → token **unchanged**, `is_active=true`, `revoked_at IS NULL` (no rotation, no new row) | P0 |
| TC-AUTH-017 | Auth / Refresh | Refreshed token reflects **current** permissions, not those at login | Login as TARGET_A, then admin grants `branch:read` via custom permission | refresh with TARGET_A's refresh token | New access token's `permissions[]` claim now includes `branch` with `can_read=true` | 200 | n/a (read-only) — token is rebuilt from `user_custom_permissions` / `rights_template_permissions` | P1 |
| TC-AUTH-018 | Auth / Refresh | Unknown / garbage refresh token | — | B:`{"refresh_token":"deadbeef"}` | `error.code = AUTH_REFRESH_INVALID` | 401 | n/a (read-only) | P0 |
| TC-AUTH-019 | Auth / Refresh | Revoked refresh token (post-logout) is rejected | ADMIN_A logged out (TC-AUTH-021) | B:`{"refresh_token":"<REFRESH_ADMIN_A>"}` | `AUTH_REFRESH_INVALID` | 401 | `SELECT is_active, revoked_at FROM user_sessions WHERE session_token=:tok` → `false`, not null | P0 |
| TC-AUTH-020 | Auth / Refresh | Expired session refresh token | Session row with `expires_at = now() - 1 day` | B:`{"refresh_token":"<expired>"}` | `AUTH_REFRESH_INVALID` | 401 | Row remains `is_active=true` but `expires_at < now()` — the query filter, not a flag, rejects it | P1 |
| TC-AUTH-020b | Auth / Refresh | Refresh for a user deactivated after login | Session live; then `POST /users/14/deactivate` | B:`{"refresh_token":"<sess of user 14>"}` | `error.code = AUTH_USER_INACTIVE` | 403 | `SELECT is_active FROM users WHERE id=14` → `false` | P0 |
| TC-AUTH-020c | Auth / Refresh | Empty / missing `refresh_token` | — | B:`{}` and B:`{"refresh_token":""}` | `VALIDATION_ERROR` (required / `min_length=1`) | 422 | n/a (read-only) | P2 |

### A3. `POST /auth/logout`

| ID | Module / API | Test Scenario | Preconditions | Request / Input | Expected Result | HTTP | Database Verification | Priority |
|---|---|---|---|---|---|---|---|---|
| TC-AUTH-021 | Auth / Logout | Logout revokes the token's own session | `TOK_ADMIN_A` live | `POST /auth/logout` H:`Authorization: Bearer TOK_ADMIN_A` (no body) | Empty body | 204 | `SELECT is_active, revoked_at FROM user_sessions WHERE id=:sid` → `false`, `revoked_at ≈ now()`. `activity_logs` gains `module='auth', title='User logged out'` | P0 |
| TC-AUTH-022 | Auth / Logout | Logout of a **specific** session by refresh token | ADMIN_A has 2 sessions (S1 current, S2 other) | `POST /auth/logout` (Bearer S1's access token) B:`{"refresh_token":"<S2 token>"}` | 204 — **S2** is revoked, S1 stays live | 204 | `SELECT is_active FROM user_sessions WHERE id=:S2` → `false`; `WHERE id=:S1` → `true` | P1 |
| TC-AUTH-023 | Auth / Logout | Cannot log out **another user's** session | S_B = a session of ADMIN_B | `POST /auth/logout` (Bearer `TOK_ADMIN_A`) B:`{"refresh_token":"<S_B token>"}` | `error.code = AUTH_SESSION_NOT_FOUND` — ownership is enforced, existence is not leaked | 404 | `SELECT is_active FROM user_sessions WHERE id=:S_B` → still `true` | P0 |

### A4. `GET /auth/me`

| ID | Module / API | Test Scenario | Preconditions | Request / Input | Expected Result | HTTP | Database Verification | Priority |
|---|---|---|---|---|---|---|---|---|
| TC-AUTH-024 | Auth / Me | Returns profile + effective permissions + data scope | `TOK_VIEWER_A`; VIEWER_A has branch access to BRANCH_A1 | `GET /auth/me` | `data` = user fields + `permissions[]` (`feature_key`, `can_create/read/edit/delete`) + `data_scope:{branch_ids:[500], department_ids:[]}`. **No** `password_hash` | 200 | n/a (read-only) — cross-check `permissions[]` against `rights_template_permissions` ⊕ `user_custom_permissions` for user 13 | P0 |
| TC-AUTH-025 | Auth / Me | Custom permission overrides the template value | ROLE_VIEWER grants `branch:read=true`; custom override sets `branch:read=false` for VIEWER_A | `GET /auth/me` | `permissions[]` entry for `branch` has `can_read=false` — custom wins | 200 | `SELECT can_read FROM user_custom_permissions WHERE user_id=13 AND feature_key='branch'` → `false` | P0 |
| TC-AUTH-026 | Auth / Me | No token | — | `GET /auth/me` (no `Authorization`) | `error.code = AUTH_NOT_AUTHENTICATED` | 401 | n/a (read-only) | P0 |
| TC-AUTH-027 | Auth / Me | Expired access token | `TOK_EXPIRED` | `GET /auth/me` H:`Bearer TOK_EXPIRED` | `AUTH_NOT_AUTHENTICATED` ("Invalid or expired access token.") | 401 | n/a (read-only) | P0 |
| TC-AUTH-028 | Auth / Me | Tampered / malformed token | `TOK_TAMPERED`, and literal `"Bearer notajwt"` | `GET /auth/me` | `AUTH_NOT_AUTHENTICATED` in both cases; no stack trace, no 500 | 401 | n/a (read-only) | P0 |
| TC-AUTH-029 | Auth / Me | **Token without a `sid` claim is rejected** | `TOK_NOSID` (validly signed) | `GET /auth/me` H:`Bearer TOK_NOSID` | `AUTH_NOT_AUTHENTICATED` — "Access token is not bound to a session." An unrevocable token must never be honoured | 401 | n/a (read-only) | P0 |

### A5. Self-service sessions

| ID | Module / API | Test Scenario | Preconditions | Request / Input | Expected Result | HTTP | Database Verification | Priority |
|---|---|---|---|---|---|---|---|---|
| TC-AUTH-030 | Auth / Sessions | List own sessions, current one flagged | ADMIN_A has 3 active sessions | `GET /auth/sessions?page=1&page_size=25` | Paged `items[]` of `{id, device_info, ip_address, created_at, expires_at, revoked_at, is_active, is_current}`; exactly one item has `is_current=true` (matching the token's `sid`). **`session_token` is never present** | 200 | n/a (read-only) — `items[].id` ⊆ `SELECT id FROM user_sessions WHERE user_id=11` | P0 |
| TC-AUTH-031 | Auth / Sessions | `active_only=false` includes revoked sessions | ADMIN_A has 2 active + 1 revoked | `GET /auth/sessions?active_only=false` | `pagination.total_records = 3`; revoked item has `is_active=false`, `revoked_at` set | 200 | Count matches `SELECT count(*) FROM user_sessions WHERE user_id=11` | P2 |
| TC-AUTH-032 | Auth / Sessions | A user only ever sees their **own** sessions | ADMIN_A and ADMIN_B both have sessions | `GET /auth/sessions` (Bearer `TOK_ADMIN_A`) | No item id belongs to ADMIN_B | 200 | `items[].id` ∩ `SELECT id FROM user_sessions WHERE user_id=21` = ∅ | P0 |
| TC-AUTH-033 | Auth / Sessions | Revoke one of my own sessions | ADMIN_A sessions S1 (current), S2 | `DELETE /auth/sessions/{S2}` | Empty body | 204 | `SELECT is_active, revoked_at FROM user_sessions WHERE id=:S2` → `false`, set. S1 untouched | P0 |
| TC-AUTH-034 | Auth / Sessions | Revoke a session that is not mine | S_B belongs to ADMIN_B | `DELETE /auth/sessions/{S_B}` (Bearer `TOK_ADMIN_A`) | `error.code = AUTH_SESSION_NOT_FOUND` | 404 | `SELECT is_active FROM user_sessions WHERE id=:S_B` → still `true` | P0 |
| TC-AUTH-035 | Auth / Sessions | Revoke a non-existent session id | — | `DELETE /auth/sessions/99999999` | `AUTH_SESSION_NOT_FOUND` | 404 | n/a (no row) | P2 |
| TC-AUTH-036 | Auth / Sessions | Revoke-all-others keeps the current session alive | ADMIN_A has 4 active sessions (1 current) | `POST /auth/sessions/revoke-all` | `data = {"revoked_count": 3}` | 200 | `SELECT count(*) FROM user_sessions WHERE user_id=11 AND is_active=true` → `1`, and that row's id = the caller's `sid`. A follow-up `GET /auth/me` with the same token still returns 200 | P0 |
| TC-AUTH-037 | Auth / Sessions | Revoke-all when only the current session exists | 1 active session | `POST /auth/sessions/revoke-all` | `data = {"revoked_count": 0}` | 200 | Session count unchanged | P2 |

### A6. Token revocation (immediate) & brute-force protection

| ID | Module / API | Test Scenario | Preconditions | Request / Input | Expected Result | HTTP | Database Verification | Priority |
|---|---|---|---|---|---|---|---|---|
| TC-AUTH-038 | Auth / Revocation | **Logout invalidates a still-unexpired access token immediately** | Login → `TOK`; `exp` still ~15 min away | `POST /auth/logout` (Bearer TOK) → then `GET /auth/me` (Bearer **same** TOK) | Second call: `AUTH_NOT_AUTHENTICATED` — "This session has been revoked or has expired." | 401 | `SELECT is_active FROM user_sessions WHERE id=:sid` → `false` | P0 |
| TC-AUTH-039 | Auth / Revocation | **Admin force-logout invalidates the victim's live token immediately** | TARGET_A logged in → `TOK_T`, session `S_T` | `DELETE /users/30/sessions/{S_T}` (Bearer `TOK_ADMIN_A`) → then `GET /auth/me` (Bearer `TOK_T`) | 204, then `AUTH_NOT_AUTHENTICATED` | 204 → 401 | `SELECT is_active, revoked_at FROM user_sessions WHERE id=:S_T` → `false`, set | P0 |
| TC-AUTH-040 | Auth / Revocation | **User deactivation invalidates a live token immediately** | TARGET_A logged in → `TOK_T` (session still active) | `POST /users/30/deactivate` (Bearer `TOK_ADMIN_A`) → then `GET /auth/me` (Bearer `TOK_T`) | `error.code = AUTH_FORBIDDEN` — "This account is inactive." (session row is still live, but the join to `users` fails-closed) | 403 | `SELECT is_active FROM users WHERE id=30` → `false`; `user_sessions` row for `S_T` is still `is_active=true` (deactivate does not cascade — revocation is enforced at request time) | P0 |
| TC-AUTH-041 | Auth / Revocation | **User soft-delete invalidates a live token immediately** | TARGET_A logged in → `TOK_T` | `DELETE /users/30` (Bearer `TOK_ADMIN_A`) → then `GET /auth/me` (Bearer `TOK_T`) | `AUTH_FORBIDDEN` — "This account is inactive." | 403 | `SELECT deleted_at FROM users WHERE id=30` → not null | P0 |
| TC-AUTH-042 | Auth / Revocation | Revoked token is rejected on **every** protected route, not just `/auth/me` | `TOK_T` revoked as in TC-AUTH-038 | Replay `TOK_T` against `GET /users`, `GET /branches`, `GET /permissions`, `GET /auth/sessions` | All → `AUTH_NOT_AUTHENTICATED` (401) | 401 | n/a (read-only) | P0 |
| TC-AUTH-043 | Auth / Rate limit | Per-IP login throttle: 11th attempt in 60 s is blocked | Redis up; fresh counters | 11 × `POST /auth/login` from one IP within 60 s (vary the email so the per-email counter never trips first) | Attempts 1-10 processed normally; the **11th** → `error.code = RATE_LIMITED` with a `Retry-After` header (seconds) | 429 | `activity_logs` gains `module='auth', sub_module='rate_limit', title='Rate limit exceeded'` with `performed_by_name='Unauthenticated'` | P0 |
| TC-AUTH-044 | Auth / Rate limit | Per-email login throttle (distributed attack from many IPs) | Redis up | 11 × `POST /auth/login` for `admin.a@acme.test` from **different** source IPs within 60 s | 11th → `RATE_LIMITED` + `Retry-After` — the per-email counter trips even though no single IP exceeded its budget | 429 | Rate-limit audit row recorded with the offending IP | P0 |
| TC-AUTH-045 | Auth / Lockout | **5 consecutive failures lock the account for 900 s** | Fresh counters for ADMIN_A | 5 × `POST /auth/login` with the **wrong** password | 5th response is still `AUTH_INVALID_CREDENTIALS` (401); the lockout flag is now set | 401 | Redis `auth:login:lockout:1:<hash(email)>` exists with TTL ≈ 900. `activity_logs` gains `module='auth', sub_module='lockout', title='Account locked'` | P0 |
| TC-AUTH-046 | Auth / Lockout | **During lockout even the CORRECT password is refused** | TC-AUTH-045 just ran | `POST /auth/login` B: ADMIN_A + the **correct** password | `error.code = RATE_LIMITED` + `Retry-After: <remaining seconds>` header — **not** 200, **not** 401 | 429 | No new `user_sessions` row for `user_id=11`; `last_login_at` unchanged | P0 |
| TC-AUTH-047 | Auth / Lockout | Lockout is per-(org, email) and does not spill to other accounts | ADMIN_A locked out | `POST /auth/login` as VIEWER_A with the correct password | 200 — a victim cannot be locked out by another account's failures | 200 | New session row for `user_id=13` | P1 |
| TC-AUTH-048 | Auth / Lockout | Unknown email also counts toward lockout (no enumeration oracle) | Fresh counters | 5 × login for `ghost@acme.test` with any password, then a 6th | 6th → `RATE_LIMITED` (429) — an attacker cannot distinguish "exists" from "does not exist" by whether lockout engages | 429 | `activity_logs` row `title='Account locked'`, description contains `(no such user)`, `performed_by_user_id IS NULL` | P0 |
| TC-AUTH-049 | Auth / Lockout | A successful login resets the failure streak | 4 failed attempts for ADMIN_A (below the threshold of 5) | 1 × successful login, then 4 more failures | The 4 post-success failures do **not** lock the account (counter was reset to 0) | 401 ×4 | Redis `auth:login:failures:1:<hash>` = 4, no lockout key present | P1 |
| TC-AUTH-050 | Auth / Rate limit | Refresh endpoint is throttled per IP (30 / 60 s) | Redis up | 31 × `POST /auth/refresh` from one IP within 60 s | 31st → `RATE_LIMITED` (429) | 429 | n/a — refresh has no tenant, so the trip is logged (`rate_limit_trip_unaudited`) not audited | P1 |

---

## 4. Module B — User Management & RBAC (TC-RBAC)

### B1. Users — `/users`

| ID | Module / API | Test Scenario | Preconditions | Request / Input | Expected Result | HTTP | Database Verification | Priority |
|---|---|---|---|---|---|---|---|---|
| TC-RBAC-001 | RBAC / Create User | Happy path | `TOK_ADMIN_A` (`user_management:create`) | `POST /users` B:`{"name":"Nina Rao","email":"nina@acme.test","mobile_country_code":"+91","mobile_number":"9876500001","password":"Passw0rd!23"}` | `data` = `UserSchema` (`id, org_id:1, name, email, mobile_*, is_active:true, is_super_admin:false, employee_id:null, created_at, updated_at, is_deleted:false`). **No `password_hash`** | 201 | `SELECT org_id, is_active, is_super_admin, created_by, password_hash FROM users WHERE email='nina@acme.test'` → `1, true, false, 11, <bcrypt hash ≠ plaintext>`. `activity_logs` gains `module='user_management', title='User created'` | P0 |
| TC-RBAC-002 | RBAC / Create User | `mobile_country_code` defaults to `+91` when omitted | — | `POST /users` B: no `mobile_country_code` | Created with `mobile_country_code = "+91"` | 201 | `SELECT mobile_country_code FROM users WHERE email=:e` → `+91` | P2 |
| TC-RBAC-003 | RBAC / Create User | Password is optional (user created without one) | — | `POST /users` B: no `password` | 201; the user cannot then log in (TC-AUTH-008) | 201 | `SELECT password_hash FROM users WHERE email=:e` → `NULL` | P1 |
| TC-RBAC-004 | RBAC / Create User | Duplicate email in the same org | `nina@acme.test` exists (active) | `POST /users` B: same email, different mobile | `error.code = USER_EMAIL_EXISTS` | 409 | `SELECT count(*) FROM users WHERE org_id=1 AND email='nina@acme.test'` → still `1` | P0 |
| TC-RBAC-005 | RBAC / Create User | Duplicate mobile in the same org | `(+91, 9876500001)` in use | `POST /users` B: new email, same `(cc, number)` | `error.code = USER_MOBILE_EXISTS` | 409 | `SELECT count(*) FROM users WHERE org_id=1 AND mobile_country_code='+91' AND mobile_number='9876500001'` → still `1` | P0 |
| TC-RBAC-006 | RBAC / Create User | Same email is legal in a **different** org | `nina@acme.test` exists in ORG_A | `POST /users` (Bearer `TOK_ADMIN_B`) B: `nina@acme.test` | 201 — uniqueness is `(org_id, email)` | 201 | `SELECT org_id FROM users WHERE email='nina@acme.test'` → rows for both `1` and `2` | P1 |
| TC-RBAC-007 | RBAC / Create User | **Re-using the email of a soft-deleted user hits the DB constraint** | DELETED_A (`deleted.a@acme.test`, `deleted_at` set) | `POST /users` B:`{"email":"deleted.a@acme.test", ...}` | `error.code = CONFLICT` (409) — the service pre-check ignores soft-deleted rows, but `uq_users_org_id_email` is **not** partial, so the `IntegrityError` (SQLSTATE 23505) is mapped to 409. **Must not be a 500** | 409 | `SELECT count(*) FROM users WHERE org_id=1 AND email='deleted.a@acme.test'` → still `1` | P0 |
| TC-RBAC-008 | RBAC / Create User | Non-super-admin cannot grant `is_super_admin` | `TOK_ADMIN_A` (has `user_management:create`, **not** super-admin) | `POST /users` B:`{..., "is_super_admin": true}` | `error.code = AUTH_FORBIDDEN` — "Only a super admin may grant super-admin." | 403 | `SELECT count(*) FROM users WHERE email=:e` → `0` (nothing created) | P0 |
| TC-RBAC-009 | RBAC / Create User | Super-admin **can** grant `is_super_admin` | `TOK_SA_A` | `POST /users` B:`{..., "is_super_admin": true}` | 201, `data.is_super_admin = true` | 201 | `SELECT is_super_admin FROM users WHERE email=:e` → `true` | P0 |
| TC-RBAC-010 | RBAC / Create User | Linking an employee already mapped to another user | EMP_001 already linked to a user | `POST /users` B:`{..., "employee_id": 5001}` | `error.code = EMPLOYEE_ALREADY_MAPPED` | 409 | No new user row | P1 |
| TC-RBAC-011 | RBAC / Create User | Validation: missing `name`, blank `name`, `name` > 150, bad email, `mobile_number` > 20 | — | 5 separate `POST /users` calls, one bad field each | `VALIDATION_ERROR` each time; `error.details[].field` names the offending field | 422 | n/a (read-only) | P2 |
| TC-RBAC-012 | RBAC / Create User | Missing permission | `TOK_HR_A` (`employee:read` only) | `POST /users` B: valid | `error.code = AUTH_FORBIDDEN` — "Missing permission 'user_management:create'." | 403 | No user created | P0 |
| TC-RBAC-013 | RBAC / Create User | **Concurrency: 10 identical creates → exactly 1 × 201, 9 × 409** | Fresh email | 10 concurrent `POST /users` with an identical body | Exactly one 201; nine `409` (`USER_EMAIL_EXISTS` from the pre-check or `CONFLICT` from the mapped `IntegrityError`). **Zero 500s** | 201 ×1, 409 ×9 | `SELECT count(*) FROM users WHERE org_id=1 AND email=:e` → **exactly 1** | P0 |
| TC-RBAC-014 | RBAC / List Users | Paged list with defaults | ≥30 users in ORG_A | `GET /users` | `data.items[]` = `UserSummarySchema`; `pagination = {page:1, page_size:25, total_records:N, total_pages, has_next:true, has_previous:false}` | 200 | n/a (read-only) — `total_records` = `SELECT count(*) FROM users WHERE org_id=1 AND deleted_at IS NULL` | P1 |
| TC-RBAC-015 | RBAC / List Users | Filters: `search`, `is_active`, `is_super_admin`, `has_employee` | Mixed fixtures | `GET /users?search=admin`, `?is_active=false`, `?is_super_admin=true`, `?has_employee=true` | Each returns only matching rows; `search` matches name/email (case-insensitive) | 200 | n/a (read-only) | P1 |
| TC-RBAC-016 | RBAC / List Users | `include_deleted=true` surfaces soft-deleted users | DELETED_A exists | `GET /users?include_deleted=true` | DELETED_A appears; with `include_deleted=false` (default) it does **not** | 200 | n/a (read-only) | P1 |
| TC-RBAC-017 | RBAC / List Users | **Multi-tenant isolation** | ORG_A and ORG_B both populated | `GET /users` (Bearer `TOK_ADMIN_A`) | No item has `org_id = 2`; ORG_B user ids (20, 21) absent | 200 | `items[].id` ∩ `SELECT id FROM users WHERE org_id=2` = ∅ | P0 |
| TC-RBAC-018 | RBAC / List Users | Pagination bounds | — | `?page=0`, `?page_size=0`, `?page_size=201` | `VALIDATION_ERROR` each (`page>=1`, `1<=page_size<=200`) | 422 | n/a (read-only) | P2 |
| TC-RBAC-019 | RBAC / Get User | Detail includes assigned role + data scope | TARGET_A has ROLE_VIEWER, branch 500, dept 700 | `GET /users/30` | `data` = `UserDetailSchema` with `template:{id:102,name:"Viewer"}` and `data_scope:{branch_ids:[500], department_ids:[700]}` | 200 | n/a (read-only) | P1 |
| TC-RBAC-020 | RBAC / Get User | Non-existent user | — | `GET /users/99999999` | `error.code = USER_NOT_FOUND` | 404 | n/a (read-only) | P1 |
| TC-RBAC-021 | RBAC / Get User | **Cross-org fetch returns 404, not 403** (no existence leak) | ADMIN_B (id 21) is in ORG_B | `GET /users/21` (Bearer `TOK_ADMIN_A`) | `error.code = USER_NOT_FOUND` — identical to TC-RBAC-020 | 404 | n/a (read-only) | P0 |
| TC-RBAC-022 | RBAC / Get User | Soft-deleted user is not fetchable | DELETED_A | `GET /users/15` | `USER_NOT_FOUND` | 404 | `SELECT deleted_at FROM users WHERE id=15` → not null | P2 |
| TC-RBAC-023 | RBAC / Update User | Partial update (PATCH semantics) | — | `PATCH /users/30` B:`{"name":"Renamed"}` | 200; only `name` changes | 200 | `SELECT name, email, mobile_number FROM users WHERE id=30` → name updated, email/mobile untouched | P1 |
| TC-RBAC-024 | RBAC / Update User | Email collision on update | `nina@acme.test` taken by another active user | `PATCH /users/30` B:`{"email":"nina@acme.test"}` | `USER_EMAIL_EXISTS` | 409 | `SELECT email FROM users WHERE id=30` → unchanged | P0 |
| TC-RBAC-025 | RBAC / Update User | Setting the email to its **current** value is a no-op, not a conflict | — | `PATCH /users/30` B:`{"email":"target.a@acme.test"}` | 200 (the check compares against the row's own value) | 200 | Row unchanged apart from `updated_at` | P2 |
| TC-RBAC-026 | RBAC / Update User | Mobile collision on update (cc + number pair) | `(+91, 9876500001)` taken | `PATCH /users/30` B:`{"mobile_number":"9876500001"}` | `USER_MOBILE_EXISTS` | 409 | `SELECT mobile_number FROM users WHERE id=30` → unchanged | P1 |
| TC-RBAC-027 | RBAC / Update User | **Non-super-admin cannot GRANT `is_super_admin`** | `TOK_ADMIN_A`; TARGET_A is not super-admin | `PATCH /users/30` B:`{"is_super_admin": true}` | `AUTH_FORBIDDEN` | 403 | `SELECT is_super_admin FROM users WHERE id=30` → still `false` | P0 |
| TC-RBAC-028 | RBAC / Update User | **Non-super-admin cannot REVOKE `is_super_admin`** (privilege manipulation / org lock-out) | `TOK_ADMIN_A`; SUPER_ADMIN_A (id 10) is super-admin | `PATCH /users/10` B:`{"is_super_admin": false}` | `AUTH_FORBIDDEN` — the guard fires on any *change*, not only on grants | 403 | `SELECT is_super_admin FROM users WHERE id=10` → still `true` | P0 |
| TC-RBAC-029 | RBAC / Update User | Super-admin may grant **and** revoke the flag | `TOK_SA_A` | `PATCH /users/30` B:`{"is_super_admin":true}` then B:`{"is_super_admin":false}` | 200 both times | 200 | `users.is_super_admin` for id 30 → `true`, then `false` | P0 |
| TC-RBAC-030 | RBAC / Update User | Re-sending the **same** `is_super_admin` value by a non-super-admin is allowed (no change) | `TOK_ADMIN_A`; TARGET_A `is_super_admin=false` | `PATCH /users/30` B:`{"is_super_admin": false}` | 200 — the guard only trips on an actual change | 200 | Row unchanged | P2 |
| TC-RBAC-031 | RBAC / Update User | Cross-org update | — | `PATCH /users/21` (Bearer `TOK_ADMIN_A`) B:`{"name":"Hacked"}` | `USER_NOT_FOUND` | 404 | `SELECT name FROM users WHERE id=21` → unchanged | P0 |
| TC-RBAC-032 | RBAC / Activate User | Reactivate a disabled user | INACTIVE_A | `POST /users/14/activate` | 200, `data.is_active = true` | 200 | `SELECT is_active FROM users WHERE id=14` → `true`. `activity_logs` `title='User activated'` | P1 |
| TC-RBAC-033 | RBAC / Deactivate User | Deactivate another user | TARGET_A active | `POST /users/30/deactivate` | 200, `data.is_active = false` | 200 | `SELECT is_active FROM users WHERE id=30` → `false`. `activity_logs` `title='User deactivated'` | P0 |
| TC-RBAC-034 | RBAC / Deactivate User | **Cannot deactivate self** | `TOK_ADMIN_A` (id 11) | `POST /users/11/deactivate` | `error.code = CANNOT_MODIFY_SELF` | 409 | `SELECT is_active FROM users WHERE id=11` → still `true` | P0 |
| TC-RBAC-035 | RBAC / Delete User | Soft-delete another user | TARGET_A | `DELETE /users/30` | Empty body | 204 | `SELECT deleted_at FROM users WHERE id=30` → not null; **row still present** (soft delete). `activity_logs` `title='User deleted'` | P0 |
| TC-RBAC-036 | RBAC / Delete User | **Cannot delete self** | `TOK_ADMIN_A` (id 11) | `DELETE /users/11` | `CANNOT_MODIFY_SELF` | 409 | `SELECT deleted_at FROM users WHERE id=11` → still NULL | P0 |
| TC-RBAC-037 | RBAC / Delete User | Missing `user_management:delete` | `TOK_VIEWER_A` (read-only) | `DELETE /users/30` | `AUTH_FORBIDDEN` | 403 | `deleted_at` for id 30 unchanged | P0 |
| TC-RBAC-038 | RBAC / Restore User | Restore a soft-deleted user | DELETED_A | `POST /users/15/restore` | 200, `data.is_deleted = false` | 200 | `SELECT deleted_at FROM users WHERE id=15` → `NULL` | P1 |
| TC-RBAC-039 | RBAC / Restore User | Restore a user that is **not** deleted | TARGET_A active | `POST /users/30/restore` | `error.code = USER_NOT_DELETED` | 409 | Row unchanged | P2 |
| TC-RBAC-040 | RBAC / Assign Employee | Link an unmapped employee to a user | EMP_003 (5003) unmapped; TARGET_A has no employee | `PUT /users/30/employee` B:`{"employee_id":5003}` | 200, `data.employee_id = 5003` | 200 | `SELECT employee_id FROM users WHERE id=30` → `5003`. `activity_logs` `title='Employee linked to user'` | P1 |
| TC-RBAC-041 | RBAC / Assign Employee | Employee already linked to another user | EMP_001 (5001) linked elsewhere | `PUT /users/30/employee` B:`{"employee_id":5001}` | `EMPLOYEE_ALREADY_MAPPED` | 409 | `SELECT employee_id FROM users WHERE id=30` → unchanged | P0 |
| TC-RBAC-042 | RBAC / Assign Employee | Non-existent employee id → FK violation is mapped, not a 500 | — | `PUT /users/30/employee` B:`{"employee_id":99999999}` | `error.code = CONFLICT` (409, SQLSTATE 23503 mapped). **Must not be 500** | 409 | `SELECT employee_id FROM users WHERE id=30` → unchanged | P1 |
| TC-RBAC-043 | RBAC / Remove Employee | Unlink an employee | TARGET_A linked to 5003 | `DELETE /users/30/employee` | Empty body | 204 | `SELECT employee_id FROM users WHERE id=30` → `NULL` | P1 |

### B2. Rights templates (roles) — `/rights-templates`

| ID | Module / API | Test Scenario | Preconditions | Request / Input | Expected Result | HTTP | Database Verification | Priority |
|---|---|---|---|---|---|---|---|---|
| TC-RBAC-044 | RBAC / Create Role | Create a role with permissions in one call | `TOK_ADMIN_A` (`role_management:create`) | `POST /rights-templates` B:`{"name":"Payroll Clerk","permissions":[{"feature_key":"employee","feature_label":"Employees","can_read":true},{"feature_key":"payroll_record","feature_label":"Payroll Records","can_read":true}]}` | 201, `data` = `RoleDetailSchema` with `permission_count=2`, `assigned_user_count=0`, `permissions[]` populated | 201 | `SELECT count(*) FROM rights_templates WHERE org_id=1 AND name='Payroll Clerk' AND deleted_at IS NULL` → 1; `SELECT count(*) FROM rights_template_permissions WHERE template_id=:new` → 2 | P0 |
| TC-RBAC-045 | RBAC / Create Role | Create with an empty permission set | — | `POST /rights-templates` B:`{"name":"Empty Role"}` | 201, `permission_count = 0` | 201 | 0 rows in `rights_template_permissions` for the new id | P2 |
| TC-RBAC-046 | RBAC / Create Role | Duplicate role name in the same org | `Admin` exists (ROLE_ADMIN) | `POST /rights-templates` B:`{"name":"Admin"}` | `error.code = TEMPLATE_NAME_EXISTS` | 409 | `SELECT count(*) FROM rights_templates WHERE org_id=1 AND name='Admin' AND deleted_at IS NULL` → still 1 | P0 |
| TC-RBAC-047 | RBAC / Create Role | **Re-using the name of a soft-deleted role hits the DB constraint** | ROLE_DELETED (`Archived Role`, `deleted_at` set) | `POST /rights-templates` B:`{"name":"Archived Role"}` | `error.code = CONFLICT` (409) — the pre-check filters `deleted_at IS NULL` but `uq_rights_templates_org_id_name` is **not** partial, so the `IntegrityError` maps to 409. **Must not be a 500** | 409 | `SELECT count(*) FROM rights_templates WHERE org_id=1 AND name='Archived Role'` → still 1 | P0 |
| TC-RBAC-048 | RBAC / Create Role | Same role name is legal across orgs | `Admin` exists in ORG_A and ORG_B | `POST /rights-templates` (Bearer `TOK_ADMIN_B`) B:`{"name":"HR"}` | 201 | 201 | Rows exist with `name='HR'` for both `org_id=1` and `org_id=2` | P1 |
| TC-RBAC-049 | RBAC / Create Role | **Unknown feature key on create is rejected** | — | `POST /rights-templates` B:`{"name":"Bad","permissions":[{"feature_key":"nuclear_launch","feature_label":"X","can_read":true}]}` | 422 `FEATURE_KEY_UNKNOWN` — `create_role` validates every key against the 39-entry catalog before opening its transaction | 422 | `SELECT count(*) FROM rights_templates WHERE org_id=1 AND name='Bad'` → **0**. The whole create is rejected before the transaction opens, so neither the template nor its permission rows exist | P1 |
| TC-RBAC-050 | RBAC / Create Role | Name validation | — | `POST /rights-templates` B:`{"name":""}` and `{"name":"<151 chars>"}` | `VALIDATION_ERROR` | 422 | n/a (read-only) | P2 |
| TC-RBAC-051 | RBAC / Create Role | Missing `role_management:create` | `TOK_VIEWER_A` | `POST /rights-templates` B: valid | `AUTH_FORBIDDEN` | 403 | No row created | P0 |
| TC-RBAC-052 | RBAC / List Roles | Paged list with counts | ORG_A roles seeded | `GET /rights-templates?page=1&page_size=25` | `items[]` carry `permission_count` and `assigned_user_count`; ROLE_ADMIN has `assigned_user_count >= 1` | 200 | Counts match `SELECT count(*) FROM rights_template_permissions WHERE template_id=:id` and `... FROM user_template_assignments WHERE template_id=:id` | P1 |
| TC-RBAC-053 | RBAC / List Roles | `search` + `include_deleted` | ROLE_DELETED exists | `GET /rights-templates?search=arch&include_deleted=true` | ROLE_DELETED returned with `is_deleted=true`; absent when `include_deleted=false` | 200 | n/a (read-only) | P1 |
| TC-RBAC-054 | RBAC / List Roles | **Multi-tenant isolation** | ROLE_B (id 200) in ORG_B | `GET /rights-templates` (Bearer `TOK_ADMIN_A`) | No item has `id` 200 or 201 | 200 | `items[].id` ∩ `SELECT id FROM rights_templates WHERE org_id=2` = ∅ | P0 |
| TC-RBAC-055 | RBAC / Get Role | Detail with permissions | ROLE_ADMIN | `GET /rights-templates/100` | 200, `permissions[]` = every `rights_template_permissions` row for 100 | 200 | n/a (read-only) | P1 |
| TC-RBAC-056 | RBAC / Get Role | Cross-org role → 404 | ROLE_B (200) in ORG_B | `GET /rights-templates/200` (Bearer `TOK_ADMIN_A`) | `error.code = TEMPLATE_NOT_FOUND` | 404 | n/a (read-only) | P0 |
| TC-RBAC-057 | RBAC / Update Role | Rename | ROLE_FREE (103) | `PATCH /rights-templates/103` B:`{"name":"Renamed Role"}` | 200 | 200 | `SELECT name FROM rights_templates WHERE id=103` → `Renamed Role` | P1 |
| TC-RBAC-058 | RBAC / Update Role | Rename onto an existing name | `Admin` exists | `PATCH /rights-templates/103` B:`{"name":"Admin"}` | `TEMPLATE_NAME_EXISTS` | 409 | `SELECT name FROM rights_templates WHERE id=103` → unchanged | P0 |
| TC-RBAC-059 | RBAC / Delete Role | Soft-delete an unassigned role | ROLE_FREE (0 assignments) | `DELETE /rights-templates/103` | Empty body | 204 | `SELECT deleted_at FROM rights_templates WHERE id=103` → not null | P1 |
| TC-RBAC-060 | RBAC / Delete Role | **Cannot delete a role assigned to users** | ROLE_ADMIN assigned to ADMIN_A | `DELETE /rights-templates/100` | `error.code = TEMPLATE_IN_USE` | 409 | `SELECT deleted_at FROM rights_templates WHERE id=100` → still NULL; `SELECT count(*) FROM user_template_assignments WHERE template_id=100` → unchanged | P0 |
| TC-RBAC-061 | RBAC / Restore Role | Restore a soft-deleted role | ROLE_DELETED (104) | `POST /rights-templates/104/restore` | 200, `is_deleted=false` | 200 | `SELECT deleted_at FROM rights_templates WHERE id=104` → NULL | P1 |
| TC-RBAC-062 | RBAC / Restore Role | Restore a role that is not deleted | ROLE_ADMIN | `POST /rights-templates/100/restore` | `error.code = TEMPLATE_NOT_DELETED` | 409 | Row unchanged | P2 |
| TC-RBAC-063 | RBAC / Clone Role | Clone copies every permission under a new name | ROLE_ADMIN has N permissions | `POST /rights-templates/100/clone` B:`{"name":"Admin Copy"}` | 201, `data.permission_count = N`, `data.permissions[]` mirrors the source, `assigned_user_count = 0` | 201 | `SELECT count(*) FROM rights_template_permissions WHERE template_id=:clone` → N, and the `(feature_key, can_*)` tuples equal those of template 100. Source template's permission rows are unchanged | P0 |
| TC-RBAC-064 | RBAC / Clone Role | Clone onto an existing name | `Admin` exists | `POST /rights-templates/100/clone` B:`{"name":"Admin"}` | `TEMPLATE_NAME_EXISTS` | 409 | No new `rights_templates` row | P1 |
| TC-RBAC-065 | RBAC / Clone Role | Clone a cross-org role | ROLE_B (200) in ORG_B | `POST /rights-templates/200/clone` (Bearer `TOK_ADMIN_A`) B:`{"name":"Stolen"}` | `TEMPLATE_NOT_FOUND` | 404 | No new row in ORG_A | P0 |

### B3. Template permissions — `/rights-templates/{id}/permissions`

| ID | Module / API | Test Scenario | Preconditions | Request / Input | Expected Result | HTTP | Database Verification | Priority |
|---|---|---|---|---|---|---|---|---|
| TC-RBAC-066 | RBAC / Template Perms | List a role's permissions | ROLE_ADMIN | `GET /rights-templates/100/permissions` | 200, array of `{id, feature_key, feature_label, parent_feature_key, can_create/read/edit/delete}` | 200 | n/a (read-only) | P1 |
| TC-RBAC-067 | RBAC / Template Perms | Upsert a **new** feature permission | ROLE_FREE has no `branch` row | `POST /rights-templates/103/permissions` B:`{"feature_key":"branch","feature_label":"Branches","parent_feature_key":"organization","can_read":true,"can_create":true}` | 200, row returned with an `id` | 200 | `SELECT can_read, can_create, can_edit, can_delete FROM rights_template_permissions WHERE template_id=103 AND feature_key='branch'` → `t,t,f,f` (exactly 1 row) | P0 |
| TC-RBAC-068 | RBAC / Template Perms | Upsert an **existing** feature updates in place (no duplicate row) | TC-RBAC-067 ran | Same `POST` with `{"feature_key":"branch","feature_label":"Branches","can_read":true,"can_edit":true}` | 200; flags now `can_read=true, can_edit=true, can_create=false` (full replace of the flags, not a merge) | 200 | `SELECT count(*) FROM rights_template_permissions WHERE template_id=103 AND feature_key='branch'` → **still 1**; `can_create` → `false` | P0 |
| TC-RBAC-069 | RBAC / Template Perms | **Unknown feature key on upsert → 422** | — | `POST /rights-templates/103/permissions` B:`{"feature_key":"nuclear_launch","feature_label":"X","can_read":true}` | `error.code = FEATURE_KEY_UNKNOWN`, **422** (a `ValidationException`, not a 404) | 422 | `SELECT count(*) FROM rights_template_permissions WHERE feature_key='nuclear_launch'` → `0` | P0 |
| TC-RBAC-070 | RBAC / Template Perms | Replace the entire permission set (atomic) | ROLE_FREE has 3 permissions | `PUT /rights-templates/103/permissions` B:`{"permissions":[{"feature_key":"employee","feature_label":"Employees","can_read":true}]}` | 200, array of exactly 1 item | 200 | `SELECT count(*) FROM rights_template_permissions WHERE template_id=103` → **exactly 1**; the previous 3 rows are gone | P0 |
| TC-RBAC-071 | RBAC / Template Perms | Replace with an empty list clears every permission | ROLE_FREE has permissions | `PUT /rights-templates/103/permissions` B:`{"permissions":[]}` | 200, `[]` | 200 | `SELECT count(*) FROM rights_template_permissions WHERE template_id=103` → `0` | P1 |
| TC-RBAC-072 | RBAC / Template Perms | **Replace containing one unknown key rejects the WHOLE batch** | ROLE_FREE has 2 permissions | `PUT /rights-templates/103/permissions` B: 3 items, one with `feature_key:"bogus"` | `FEATURE_KEY_UNKNOWN`, 422 | 422 | `SELECT count(*) FROM rights_template_permissions WHERE template_id=103` → **still 2** — validation runs before the delete, so nothing is lost | P0 |
| TC-RBAC-073 | RBAC / Template Perms | Remove one feature permission | ROLE_FREE has `employee` | `DELETE /rights-templates/103/permissions/employee` | Empty body | 204 | `SELECT count(*) FROM rights_template_permissions WHERE template_id=103 AND feature_key='employee'` → `0` | P1 |
| TC-RBAC-074 | RBAC / Template Perms | Remove a permission the role does not have | — | `DELETE /rights-templates/103/permissions/attendance` | `error.code = PERMISSION_NOT_FOUND` | 404 | No rows deleted | P2 |
| TC-RBAC-075 | RBAC / Template Perms | Permission changes propagate to a user's next token | TARGET_A holds ROLE_FREE; ROLE_FREE gains `branch:read` | `POST /rights-templates/103/permissions` (branch:read) → TARGET_A refreshes | The refreshed access token's `permissions[]` includes `branch.can_read=true`; `GET /auth/me` as TARGET_A confirms | 200 | `rights_template_permissions` row exists for (103, `branch`) | P0 |
| TC-RBAC-076 | RBAC / Template Perms | Missing `role_management:edit` | `TOK_VIEWER_A` (`role_management:read` only) | `POST /rights-templates/103/permissions` B: valid | `AUTH_FORBIDDEN` | 403 | No row written | P0 |
| TC-RBAC-077 | RBAC / Template Perms | Cross-org template id | ROLE_B (200) | `PUT /rights-templates/200/permissions` (Bearer `TOK_ADMIN_A`) B: valid | `TEMPLATE_NOT_FOUND` | 404 | `SELECT count(*) FROM rights_template_permissions WHERE template_id=200` → unchanged | P0 |

### B4. Permission catalog — `/permissions`

| ID | Module / API | Test Scenario | Preconditions | Request / Input | Expected Result | HTTP | Database Verification | Priority |
|---|---|---|---|---|---|---|---|---|
| TC-RBAC-078 | RBAC / Catalog | List the full catalog | `TOK_VIEWER_A` (`role_management:read`) | `GET /permissions` | 200, **39 items**, each `{feature_key, feature_label, parent_feature_key, supported_actions[]}`. Includes `organization, branch, department, designation, user_management, role_management, access_management, audit` | 200 | n/a (read-only) — the catalog is a **static code registry** (`PERMISSION_CATALOG`), not a DB table. Assert no `SELECT` is needed | P1 |
| TC-RBAC-079 | RBAC / Catalog | `supported_actions` are per-feature, not always CRUD | — | `GET /permissions` | `organization`/`branch`/`department`/`designation` → `["create","read","edit"]` (**no `delete`**); `access_management` → `["read","edit"]`; `audit`/`dashboard`/`reports` → `["read"]`; `user_management`/`role_management` → all four | 200 | n/a (read-only) | P1 |
| TC-RBAC-080 | RBAC / Catalog | Filter by parent | — | `GET /permissions?parent_feature_key=organization` | Exactly `branch`, `department`, `designation` | 200 | n/a (read-only) | P2 |
| TC-RBAC-081 | RBAC / Catalog | Unknown parent returns an empty list (not an error) | — | `GET /permissions?parent_feature_key=bogus` | 200, `data = []` | 200 | n/a (read-only) | P2 |
| TC-RBAC-082 | RBAC / Catalog | Get one feature's metadata | — | `GET /permissions/branch` | 200, `{feature_key:"branch", feature_label:"Branches", parent_feature_key:"organization", supported_actions:["create","read","edit"]}` | 200 | n/a (read-only) | P1 |
| TC-RBAC-083 | RBAC / Catalog | **Unknown feature key → 404** | — | `GET /permissions/nuclear_launch` | `error.code = FEATURE_KEY_UNKNOWN`, **404** (contrast TC-RBAC-069, which is 422 on the same code) | 404 | n/a (read-only) | P0 |
| TC-RBAC-084 | RBAC / Catalog | Missing `role_management:read` | `TOK_HR_A` | `GET /permissions` | `AUTH_FORBIDDEN` | 403 | n/a (read-only) | P1 |

### B5. User ↔ role assignment — `/users/{id}/template`

| ID | Module / API | Test Scenario | Preconditions | Request / Input | Expected Result | HTTP | Database Verification | Priority |
|---|---|---|---|---|---|---|---|---|
| TC-RBAC-085 | RBAC / User Role | Assign a role to a user with none | TARGET_A unassigned | `PUT /users/30/template` B:`{"template_id":103}` | 200, `data = {template:{id:103,name:...}, assigned_by:11, assigned_at:<ts>}` | 200 | `SELECT template_id, assigned_by FROM user_template_assignments WHERE user_id=30` → `103, 11` (exactly one row — `uq_user_template_assignments_user_id`) | P0 |
| TC-RBAC-086 | RBAC / User Role | Re-assign replaces the single existing role | TARGET_A holds 103 | `PUT /users/30/template` B:`{"template_id":102}` | 200, `template.id = 102` | 200 | `SELECT count(*), max(template_id) FROM user_template_assignments WHERE user_id=30` → `1, 102` — the old row is deleted, not stacked | P0 |
| TC-RBAC-087 | RBAC / User Role | Get the assigned role | TARGET_A holds 102 | `GET /users/30/template` | 200, `{template:{id:102,...}, assigned_by, assigned_at}` | 200 | n/a (read-only) | P1 |
| TC-RBAC-088 | RBAC / User Role | Get when no role is assigned | TARGET_A unassigned | `GET /users/30/template` | 200, `data = {template: null, assigned_by: null, assigned_at: null}` — **not** a 404 | 200 | `SELECT count(*) FROM user_template_assignments WHERE user_id=30` → `0` | P1 |
| TC-RBAC-089 | RBAC / User Role | Assign a cross-org role | ROLE_B (200) | `PUT /users/30/template` (Bearer `TOK_ADMIN_A`) B:`{"template_id":200}` | `TEMPLATE_NOT_FOUND` | 404 | `SELECT count(*) FROM user_template_assignments WHERE user_id=30 AND template_id=200` → `0` | P0 |
| TC-RBAC-090 | RBAC / User Role | Assign a soft-deleted role | ROLE_DELETED (104) | `PUT /users/30/template` B:`{"template_id":104}` | `TEMPLATE_NOT_FOUND` | 404 | No assignment row | P1 |
| TC-RBAC-091 | RBAC / User Role | Remove the role assignment | TARGET_A holds 102 | `DELETE /users/30/template` | Empty body | 204 | `SELECT count(*) FROM user_template_assignments WHERE user_id=30` → `0` | P1 |
| TC-RBAC-092 | RBAC / User Role | Remove when nothing is assigned | TARGET_A unassigned | `DELETE /users/30/template` | `error.code = ASSIGNMENT_NOT_FOUND` | 404 | No rows affected | P2 |
| TC-RBAC-093 | RBAC / User Role | Missing `access_management:edit` | `TOK_VIEWER_A` (`access_management:read` only) | `PUT /users/30/template` B:`{"template_id":103}` | `AUTH_FORBIDDEN` | 403 | No assignment row written | P0 |

### B6. Custom permissions & effective permissions

| ID | Module / API | Test Scenario | Preconditions | Request / Input | Expected Result | HTTP | Database Verification | Priority |
|---|---|---|---|---|---|---|---|---|
| TC-RBAC-094 | RBAC / Custom Perms | Upsert a per-user override | TARGET_A has no `branch` override | `POST /users/30/custom-permissions` B:`{"feature_key":"branch","parent_feature_key":"organization","can_read":true,"can_edit":true}` | 200, `{id, feature_key:"branch", can_read:true, can_edit:true, set_by:11, set_at:<ts>}` | 200 | `SELECT can_read, can_edit, set_by FROM user_custom_permissions WHERE user_id=30 AND feature_key='branch'` → `t,t,11` (1 row) | P0 |
| TC-RBAC-095 | RBAC / Custom Perms | Upsert an existing override updates in place | TC-RBAC-094 ran | Same POST with `{"feature_key":"branch","can_read":false}` | 200; flags now all `false` | 200 | `SELECT count(*) FROM user_custom_permissions WHERE user_id=30 AND feature_key='branch'` → **still 1**; `can_read`/`can_edit` → `false` | P0 |
| TC-RBAC-096 | RBAC / Custom Perms | **Unknown feature key → 422** | — | `POST /users/30/custom-permissions` B:`{"feature_key":"bogus","can_read":true}` | `error.code = FEATURE_KEY_UNKNOWN`, **422** | 422 | `SELECT count(*) FROM user_custom_permissions WHERE feature_key='bogus'` → `0` | P0 |
| TC-RBAC-097 | RBAC / Custom Perms | List a user's overrides | TARGET_A has 2 | `GET /users/30/custom-permissions` | 200, 2 items | 200 | n/a (read-only) | P1 |
| TC-RBAC-098 | RBAC / Custom Perms | Replace the whole override set (atomic) | TARGET_A has 3 overrides | `PUT /users/30/custom-permissions` B:`{"permissions":[{"feature_key":"audit","can_read":true}]}` | 200, exactly 1 item | 200 | `SELECT count(*) FROM user_custom_permissions WHERE user_id=30` → **exactly 1**, `feature_key='audit'` | P0 |
| TC-RBAC-099 | RBAC / Custom Perms | **Replace with one bad key rejects the whole batch, destroys nothing** | TARGET_A has 2 overrides | `PUT /users/30/custom-permissions` B: 2 items, one `feature_key:"bogus"` | `FEATURE_KEY_UNKNOWN`, 422 | 422 | `SELECT count(*) FROM user_custom_permissions WHERE user_id=30` → **still 2** | P0 |
| TC-RBAC-100 | RBAC / Custom Perms | Replace with `[]` clears every override | — | `PUT /users/30/custom-permissions` B:`{"permissions":[]}` | 200, `[]` | 200 | `SELECT count(*) FROM user_custom_permissions WHERE user_id=30` → `0` | P1 |
| TC-RBAC-101 | RBAC / Custom Perms | Remove one override | TARGET_A has `audit` | `DELETE /users/30/custom-permissions/audit` | Empty body | 204 | `SELECT count(*) FROM user_custom_permissions WHERE user_id=30 AND feature_key='audit'` → `0` | P1 |
| TC-RBAC-102 | RBAC / Custom Perms | Remove an override that does not exist | — | `DELETE /users/30/custom-permissions/employee` | `error.code = PERMISSION_NOT_FOUND` | 404 | No rows deleted | P2 |
| TC-RBAC-103 | RBAC / Effective Perms | **Custom override wins over the template** | TARGET_A holds ROLE_VIEWER (`branch:read=true`); custom override sets `branch:read=false` | `GET /users/30/effective-permissions` | 200; the `branch` entry has `can_read = false` | 200 | Cross-check: `rights_template_permissions` (102, `branch`) `can_read=true` **and** `user_custom_permissions` (30, `branch`) `can_read=false` — the API must return the custom value | P0 |
| TC-RBAC-104 | RBAC / Effective Perms | Custom override can **grant** a feature the template lacks | ROLE_VIEWER has no `audit`; override grants `audit:read=true` | `GET /users/30/effective-permissions` | `audit.can_read = true` | 200 | Row present in `user_custom_permissions` only | P0 |
| TC-RBAC-105 | RBAC / Effective Perms | Response includes the data scope | TARGET_A has branches [500,501], depts [700] | `GET /users/30/effective-permissions` | `data.data_scope = {branch_ids:[500,501], department_ids:[700]}` (sorted) | 200 | Matches `user_branch_access` / `user_department_access` for user 30 | P1 |
| TC-RBAC-106 | RBAC / Effective Perms | Cross-org user | ADMIN_B (21) | `GET /users/21/effective-permissions` (Bearer `TOK_ADMIN_A`) | `USER_NOT_FOUND` | 404 | n/a (read-only) | P0 |
| TC-RBAC-107 | RBAC / Effective Perms | Missing `access_management:read` | `TOK_HR_A` | `GET /users/30/effective-permissions` | `AUTH_FORBIDDEN` | 403 | n/a (read-only) | P1 |

### B7. Branch / Department access (data scope)

| ID | Module / API | Test Scenario | Preconditions | Request / Input | Expected Result | HTTP | Database Verification | Priority |
|---|---|---|---|---|---|---|---|---|
| TC-RBAC-108 | RBAC / Branch Access | Grant branch access | TARGET_A has none | `POST /users/30/branch-access` B:`{"branch_id":500}` | 201, `{branch_id:500, granted_by:11, granted_at:<ts>}` | 201 | `SELECT count(*) FROM user_branch_access WHERE user_id=30 AND branch_id=500` → `1`, `granted_by=11` | P0 |
| TC-RBAC-109 | RBAC / Branch Access | Duplicate grant | TC-RBAC-108 ran | Same `POST` again | `error.code = BRANCH_ACCESS_EXISTS` | 409 | `SELECT count(*) FROM user_branch_access WHERE user_id=30 AND branch_id=500` → **still 1** (`uq_user_branch_access_user_id_branch_id`) | P0 |
| TC-RBAC-110 | RBAC / Branch Access | **Concurrency: 10 concurrent identical grants** | Fresh (user 30, branch 501) | 10 concurrent `POST /users/30/branch-access` B:`{"branch_id":501}` | Exactly one 201; nine 409 (`BRANCH_ACCESS_EXISTS` or the mapped `CONFLICT`). **Zero 500s** | 201 ×1, 409 ×9 | `SELECT count(*) FROM user_branch_access WHERE user_id=30 AND branch_id=501` → **exactly 1** | P0 |
| TC-RBAC-111 | RBAC / Branch Access | Non-existent branch id | — | `POST /users/30/branch-access` B:`{"branch_id":99999999}` | `error.code = CONFLICT` (409, FK violation 23503 mapped). **Must not be 500** | 409 | No row in `user_branch_access` for branch 99999999 | P1 |
| TC-RBAC-112 | RBAC / Branch Access | **Cross-org branch must not be grantable** | BRANCH_B1 (600) belongs to ORG_B | `POST /users/30/branch-access` (Bearer `TOK_ADMIN_A`) B:`{"branch_id":600}` | **Expected:** rejection — `BRANCH_NOT_FOUND` (404). See Known Gaps §7: the service does not currently verify the branch's `org_id`, so this presently returns **201** and creates a cross-tenant grant | 404 | `SELECT count(*) FROM user_branch_access uba JOIN branches b ON b.branch_id=uba.branch_id WHERE uba.user_id=30 AND b.org_id<>1` → **must be 0** | P0 |
| TC-RBAC-113 | RBAC / Branch Access | List a user's grants | TARGET_A has 500, 501 | `GET /users/30/branch-access` | 200, 2 items | 200 | n/a (read-only) | P1 |
| TC-RBAC-114 | RBAC / Branch Access | Replace the whole set (de-duplicating) | TARGET_A has 500, 501 | `PUT /users/30/branch-access` B:`{"branch_ids":[502,502,500]}` | 200, exactly 2 items (`502`, `500`) — duplicates collapsed, order preserved | 200 | `SELECT branch_id FROM user_branch_access WHERE user_id=30 ORDER BY branch_id` → `{500, 502}`; branch 501 removed | P0 |
| TC-RBAC-115 | RBAC / Branch Access | Replace with `[]` clears the scope | — | `PUT /users/30/branch-access` B:`{"branch_ids":[]}` | 200, `[]` | 200 | `SELECT count(*) FROM user_branch_access WHERE user_id=30` → `0` | P1 |
| TC-RBAC-116 | RBAC / Branch Access | Revoke one grant | TARGET_A has 500 | `DELETE /users/30/branch-access/500` | Empty body | 204 | `SELECT count(*) FROM user_branch_access WHERE user_id=30 AND branch_id=500` → `0` | P1 |
| TC-RBAC-117 | RBAC / Branch Access | Revoke a grant that does not exist | — | `DELETE /users/30/branch-access/501` | `error.code = BRANCH_ACCESS_NOT_FOUND` | 404 | No rows deleted | P2 |
| TC-RBAC-118 | RBAC / Dept Access | Grant department access | TARGET_A has none | `POST /users/30/department-access` B:`{"department_id":700}` | 201, `{department_id:700, granted_by:11, granted_at}` | 201 | `SELECT count(*) FROM user_department_access WHERE user_id=30 AND department_id=700` → `1` | P0 |
| TC-RBAC-119 | RBAC / Dept Access | Duplicate grant | TC-RBAC-118 ran | Same `POST` again | `error.code = DEPARTMENT_ACCESS_EXISTS` | 409 | Row count still `1` | P0 |
| TC-RBAC-120 | RBAC / Dept Access | Replace / clear / revoke behave like branch access | TARGET_A has 700, 701 | `PUT /users/30/department-access` B:`{"department_ids":[701]}` then `DELETE /users/30/department-access/701` then `DELETE` again | 200 → 204 → `DEPARTMENT_ACCESS_NOT_FOUND` (404) | 200/204/404 | After PUT: `SELECT department_id FROM user_department_access WHERE user_id=30` → `{701}`. After DELETE: `count = 0` | P1 |
| TC-RBAC-121 | RBAC / Data Scope | **Data-scope grants actually restrict what the user sees** | VIEWER_A granted only BRANCH_A2 (501); ORG_A has branches 500, 501, 502 | Re-login as VIEWER_A → `GET /branches` | Only branch 501 is returned; `pagination.total_records = 1` | 200 | `SELECT branch_id FROM user_branch_access WHERE user_id=13` → `{501}` | P0 |
| TC-RBAC-122 | RBAC / Data Scope | A user with **no** branch grants is unrestricted (documented behaviour) | VIEWER_A has 0 branch grants | Re-login → `GET /branches` | All non-deleted ORG_A branches are returned — an empty scope means "unscoped", not "nothing" (`_branch_scope` returns `None`) | 200 | `SELECT count(*) FROM user_branch_access WHERE user_id=13` → `0` | P1 |
| TC-RBAC-123 | RBAC / Data Scope | Missing `access_management:edit` blocks scope changes | `TOK_HR_A` | `POST /users/30/branch-access` B:`{"branch_id":500}` | `AUTH_FORBIDDEN` | 403 | No row created | P0 |

### B8. Session administration (admin acting on another user)

| ID | Module / API | Test Scenario | Preconditions | Request / Input | Expected Result | HTTP | Database Verification | Priority |
|---|---|---|---|---|---|---|---|---|
| TC-RBAC-124 | RBAC / Admin Sessions | List a target user's sessions | TARGET_A has 2 active sessions; `TOK_ADMIN_A` (`user_management:read`) | `GET /users/30/sessions?active_only=true` | 200, paged `items[]` of `{id, device_info, ip_address, created_at, expires_at, revoked_at, is_active}`. **`session_token` must NEVER appear** | 200 | Assert no response key equals `session_token`; `items[].id` = `SELECT id FROM user_sessions WHERE user_id=30 AND is_active=true` | P0 |
| TC-RBAC-125 | RBAC / Admin Sessions | `active_only=false` includes revoked sessions | TARGET_A: 1 active + 2 revoked | `GET /users/30/sessions?active_only=false` | `pagination.total_records = 3` | 200 | Matches `SELECT count(*) FROM user_sessions WHERE user_id=30` | P2 |
| TC-RBAC-126 | RBAC / Admin Sessions | **Cross-org session listing is blocked** | ADMIN_B (21) has sessions | `GET /users/21/sessions` (Bearer `TOK_ADMIN_A`) | `error.code = USER_NOT_FOUND` (404 — not 403; existence is not leaked) | 404 | n/a (read-only) | P0 |
| TC-RBAC-127 | RBAC / Admin Sessions | Force-logout one session | TARGET_A session `S_T` active | `DELETE /users/30/sessions/{S_T}` | Empty body | 204 | `SELECT is_active, revoked_at FROM user_sessions WHERE id=:S_T` → `false`, `≈now()`. `activity_logs` `title='Session force-logged-out'`, `performed_by_user_id=11` | P0 |
| TC-RBAC-128 | RBAC / Admin Sessions | Force-logout a session that belongs to a **different** user | `S_B` belongs to ADMIN_B | `DELETE /users/30/sessions/{S_B}` (path user = 30) | `error.code = SESSION_NOT_FOUND` — the (session, user) pair is validated | 404 | `SELECT is_active FROM user_sessions WHERE id=:S_B` → still `true` | P0 |
| TC-RBAC-129 | RBAC / Admin Sessions | Revoke **all** of a target user's sessions | TARGET_A has 3 active | `POST /users/30/sessions/revoke-all` | 200, `data = {"revoked_count": 3}` | 200 | `SELECT count(*) FROM user_sessions WHERE user_id=30 AND is_active=true` → `0`. `activity_logs` `title='All user sessions revoked'` | P0 |
| TC-RBAC-130 | RBAC / Admin Sessions | Revoke-all when the target has no active sessions | 0 active | `POST /users/30/sessions/revoke-all` | 200, `{"revoked_count": 0}` — idempotent | 200 | No rows changed | P2 |
| TC-RBAC-131 | RBAC / Admin Sessions | Missing `user_management:edit` | `TOK_VIEWER_A` (`user_management:read` only) | `POST /users/30/sessions/revoke-all` | `AUTH_FORBIDDEN` | 403 | Target's sessions still `is_active=true` | P0 |
| TC-RBAC-132 | RBAC / Admin Sessions | Sessions of a **soft-deleted** user are still listable (audit/forensics) | DELETED_A (15) has sessions | `GET /users/15/sessions?active_only=false` | 200 — `list_user_sessions` resolves the user via `_get_any_user`, which includes soft-deleted rows | 200 | n/a (read-only) | P2 |

---

## 5. Module C — Organization Management (TC-ORG)

> **Authorization model.** `POST /organizations`, `GET /organizations` (list), and the org
> activate/deactivate routes require **super-admin** (`require_super_admin` → `AUTH_FORBIDDEN` 403).
> `GET /organizations/{id}` and `PATCH /organizations/{id}` are open to any caller holding the
> `organization` feature permission but are constrained to **their own org**
> (`_assert_own_org_or_super_admin` → `AUTH_FORBIDDEN` **403**, *not* 404 — organizations are the one
> resource whose existence is not hidden cross-tenant). Branch / department / designation are
> tenant-scoped and return **404** for cross-org ids.

### C1. Organizations — `/organizations`

| ID | Module / API | Test Scenario | Preconditions | Request / Input | Expected Result | HTTP | Database Verification | Priority |
|---|---|---|---|---|---|---|---|---|
| TC-ORG-001 | Org / Create | Provision a new organization (super-admin) | `TOK_SA_A` | `POST /organizations` B:`{"org_code":"STARK","org_name":"Stark Industries","contact_phone":"+911234567890","contact_email":"ops@stark.test"}` | 201, `data` = `{org_id, org_code:"STARK", org_name, contact_phone, contact_email, is_active:true, is_deleted:false, created_at, updated_at}` | 201 | `SELECT org_code, is_active, is_deleted FROM organizations WHERE org_code='STARK'` → `STARK, true, false`. `activity_logs` gains `module='Organization Management', sub_module='organization', title='Organization created'` | P0 |
| TC-ORG-002 | Org / Create | **Non-super-admin is refused even with `organization:create`** | `TOK_ADMIN_A` (has `organization:create`, not super-admin) | `POST /organizations` B: valid | `error.code = AUTH_FORBIDDEN` — "This operation requires super-admin privileges." | 403 | `SELECT count(*) FROM organizations WHERE org_code=:new` → `0` | P0 |
| TC-ORG-003 | Org / Create | **`org_code` is globally unique** (across all tenants) | ORG_B has `org_code='GLOBEX'` | `POST /organizations` (Bearer `TOK_SA_A`) B:`{"org_code":"GLOBEX","org_name":"Copycat"}` | `error.code = ORG_CODE_EXISTS` | 409 | `SELECT count(*) FROM organizations WHERE org_code='GLOBEX'` → still `1` | P0 |
| TC-ORG-004 | Org / Create | **Concurrency: 10 identical creates → 1 × 201, 9 × 409** | Fresh `org_code` | 10 concurrent `POST /organizations` with an identical body | Exactly one 201; nine 409 (`ORG_CODE_EXISTS` from the pre-check or `CONFLICT` from the mapped `IntegrityError` on `uq_organizations_org_code`). **Zero 500s** | 201 ×1, 409 ×9 | `SELECT count(*) FROM organizations WHERE org_code=:code` → **exactly 1** | P0 |
| TC-ORG-005 | Org / Create | Validation: `org_code` blank / > 20 chars, `org_name` blank / > 200 chars | — | 4 separate `POST /organizations` calls | `VALIDATION_ERROR` each; `error.details[].field` names the field | 422 | n/a (read-only) | P2 |
| TC-ORG-006 | Org / Create | Malformed `contact_email` | — | B:`{"org_code":"X1","org_name":"X","contact_email":"not-an-email"}` | `VALIDATION_ERROR` — "Invalid email address format." | 422 | No org row created | P2 |
| TC-ORG-007 | Org / Create | Empty-string `contact_email` is normalised to NULL | — | B:`{"org_code":"X2","org_name":"X","contact_email":"   "}` | 201, `data.contact_email = null` | 201 | `SELECT contact_email FROM organizations WHERE org_code='X2'` → `NULL` | P2 |
| TC-ORG-008 | Org / List | List all organizations (super-admin) | ORG_A..ORG_DEL seeded | `GET /organizations?page=1&page_size=25` | 200, paged `items[]`; ORG_DEL (soft-deleted) **absent** by default | 200 | `total_records` = `SELECT count(*) FROM organizations WHERE is_deleted=false` | P1 |
| TC-ORG-009 | Org / List | **Non-super-admin cannot list organizations** | `TOK_ADMIN_A` | `GET /organizations` | `AUTH_FORBIDDEN` | 403 | n/a (read-only) | P0 |
| TC-ORG-010 | Org / List | Filters and sorting | — | `?search=acme`, `?is_active=false`, `?include_deleted=true`, `?sort_by=org_code&sort_order=desc` | `search` matches `org_code` or `org_name` (case-insensitive); `include_deleted=true` surfaces ORG_DEL; sorting applied | 200 | n/a (read-only) | P1 |
| TC-ORG-011 | Org / List | Invalid `sort_by` falls back to the default (does not 500) | — | `GET /organizations?sort_by=drop_table` | 200 — `ORGANIZATION_SORTS` is an allow-list `{org_code, org_name, created_at}`; unknown values fall back | 200 | n/a (read-only) — also a SQL-injection guard | P0 |
| TC-ORG-012 | Org / Get | Fetch own organization | `TOK_ADMIN_A` (ORG_A, has `organization:read`) | `GET /organizations/1` | 200, `data.org_id = 1` | 200 | n/a (read-only) | P1 |
| TC-ORG-013 | Org / Get | **Cross-org fetch is refused with 403** (not 404) | `TOK_ADMIN_A` (ORG_A) | `GET /organizations/2` | `error.code = AUTH_FORBIDDEN` — "You may only access your own organization." | 403 | n/a (read-only) | P0 |
| TC-ORG-014 | Org / Get | Super-admin may fetch any organization | `TOK_SA_A` | `GET /organizations/2` | 200, `data.org_id = 2` | 200 | n/a (read-only) | P1 |
| TC-ORG-015 | Org / Get | Non-existent org id (as super-admin) | — | `GET /organizations/99999999` (Bearer `TOK_SA_A`) | `error.code = ORG_NOT_FOUND` | 404 | n/a (read-only) | P1 |
| TC-ORG-016 | Org / Get | Soft-deleted org is not fetchable | ORG_DEL (4) | `GET /organizations/4` (Bearer `TOK_SA_A`) | `ORG_NOT_FOUND` | 404 | `SELECT is_deleted FROM organizations WHERE org_id=4` → `true` | P2 |
| TC-ORG-017 | Org / Update | Update own org profile | `TOK_ADMIN_A` (`organization:edit`) | `PATCH /organizations/1` B:`{"org_name":"Acme Foods Pvt Ltd","contact_phone":"+919000000000"}` | 200, fields updated | 200 | `SELECT org_name, contact_phone FROM organizations WHERE org_id=1` → updated. `activity_logs` `title='Organization updated'` | P1 |
| TC-ORG-018 | Org / Update | Changing `org_code` to one already taken | `GLOBEX` taken by ORG_B | `PATCH /organizations/1` (Bearer `TOK_SA_A`) B:`{"org_code":"GLOBEX"}` | `ORG_CODE_EXISTS` | 409 | `SELECT org_code FROM organizations WHERE org_id=1` → still `ACME` | P0 |
| TC-ORG-019 | Org / Update | Re-sending the org's own `org_code` is a no-op, not a conflict | — | `PATCH /organizations/1` B:`{"org_code":"ACME"}` | 200 | 200 | Row unchanged apart from `updated_at` | P2 |
| TC-ORG-020 | Org / Update | **Cross-org update is refused** | `TOK_ADMIN_A` (ORG_A) | `PATCH /organizations/2` B:`{"org_name":"Pwned"}` | `AUTH_FORBIDDEN` | 403 | `SELECT org_name FROM organizations WHERE org_id=2` → unchanged | P0 |
| TC-ORG-021 | Org / Deactivate | Deactivate an organization (super-admin) | ORG_C active | `POST /organizations/3/deactivate` (Bearer `TOK_SA_A`) | 200, `data.is_active = false` | 200 | `SELECT is_active FROM organizations WHERE org_id=3` → `false`. `activity_logs` `title='Organization deactivated'` | P0 |
| TC-ORG-022 | Org / Deactivate | Deactivation is **idempotent** (no audit row on a no-op) | ORG_C already inactive | `POST /organizations/3/deactivate` again | 200, `is_active = false` — no error | 200 | `activity_logs` count for `sub_module='organization'` → **unchanged** (the service short-circuits when the flag already matches) | P2 |
| TC-ORG-023 | Org / Activate | Activate an organization | ORG_C inactive | `POST /organizations/3/activate` (Bearer `TOK_SA_A`) | 200, `data.is_active = true` | 200 | `SELECT is_active FROM organizations WHERE org_id=3` → `true` | P1 |
| TC-ORG-024 | Org / Activate | **Non-super-admin cannot activate/deactivate** | `TOK_ADMIN_A` (has `organization:edit`) | `POST /organizations/1/deactivate` | `AUTH_FORBIDDEN` | 403 | `SELECT is_active FROM organizations WHERE org_id=1` → still `true` | P0 |
| TC-ORG-025 | Org / All routes | No token / revoked token | `TOK_EXPIRED` and no header | `GET /organizations/1` | `AUTH_NOT_AUTHENTICATED` | 401 | n/a (read-only) | P0 |

### C2. Branches — `/branches`

| ID | Module / API | Test Scenario | Preconditions | Request / Input | Expected Result | HTTP | Database Verification | Priority |
|---|---|---|---|---|---|---|---|---|
| TC-ORG-026 | Org / Create Branch | Happy path | `TOK_ADMIN_A` (`branch:create`) | `POST /branches` B:`{"branch_name":"Nashik Plant","city":"Nashik","state":"MH","country":"IN","pin_code":"422001","latitude":19.9975,"longitude":73.7898,"allowed_radius_meters":150}` | 201, `data` = `BranchSchema` with `org_id:1`, `is_active:true`, `is_deleted:false` | 201 | `SELECT org_id, branch_name, is_active, allowed_radius_meters FROM branches WHERE branch_name='Nashik Plant'` → `1, ..., true, 150`. `activity_logs` `sub_module='branch', title='Branch created'` | P0 |
| TC-ORG-027 | Org / Create Branch | **`branch_name` is NOT unique** (by design — Contract §5.1) | BRANCH_A1 = `Mumbai HQ` | `POST /branches` B:`{"branch_name":"Mumbai HQ"}` | 201 — duplicate names are legal | 201 | `SELECT count(*) FROM branches WHERE org_id=1 AND branch_name='Mumbai HQ'` → `2` | P1 |
| TC-ORG-028 | Org / Create Branch | Geo boundary validation | — | `latitude=90`/`-90`, `longitude=180`/`-180` (accept) vs `latitude=90.1`, `longitude=-180.1` (reject) | Boundaries inclusive → 201; beyond → `VALIDATION_ERROR` | 201 / 422 | Only the valid rows are persisted | P2 |
| TC-ORG-029 | Org / Create Branch | `allowed_radius_meters` bounds | — | `0` (reject, `gt=0`), `1` (accept), `32767` (accept), `32768` (reject, `le=32767`) | `VALIDATION_ERROR` for 0 and 32768; 201 otherwise | 422 / 201 | `SELECT allowed_radius_meters FROM branches WHERE branch_id=:new` → `32767` for the upper-bound case (SMALLINT max — guards an integer overflow) | P1 |
| TC-ORG-030 | Org / Create Branch | Field length limits | — | `branch_name` > 200, `gstin` > 20, `pin_code` > 10, `city`/`state`/`country` > 100 | `VALIDATION_ERROR` each | 422 | n/a (read-only) | P2 |
| TC-ORG-031 | Org / Create Branch | Missing `branch:create` | `TOK_VIEWER_A` (`branch:read` only) | `POST /branches` B: valid | `AUTH_FORBIDDEN` | 403 | No branch row created | P0 |
| TC-ORG-032 | Org / List Branches | Paged list scoped to the caller's org | ORG_A: 3 branches; ORG_B: 1 | `GET /branches` (Bearer `TOK_ADMIN_A`) | Only ORG_A branches; BRANCH_B1 (600) absent | 200 | `items[].branch_id` ∩ `SELECT branch_id FROM branches WHERE org_id=2` = ∅ | P0 |
| TC-ORG-033 | Org / List Branches | `search` matches name **or** city; `is_active` filter; `include_deleted` | BRANCH_A3 inactive | `?search=pune`, `?is_active=false`, `?include_deleted=true` | Correct subsets returned in each case | 200 | n/a (read-only) | P1 |
| TC-ORG-034 | Org / List Branches | Invalid `sort_by` falls back safely | — | `GET /branches?sort_by=1;DROP TABLE branches--` | 200, default sort (allow-list `{branch_name, created_at}`) | 200 | `SELECT count(*) FROM branches` → unchanged (SQL-injection guard) | P0 |
| TC-ORG-035 | Org / Get Branch | Fetch by id | BRANCH_A1 | `GET /branches/500` | 200, `data.branch_id = 500`, `org_id = 1` | 200 | n/a (read-only) | P1 |
| TC-ORG-036 | Org / Get Branch | **Cross-org branch → 404 (not 403)** | BRANCH_B1 (600) in ORG_B | `GET /branches/600` (Bearer `TOK_ADMIN_A`) | `error.code = BRANCH_NOT_FOUND` — identical to a genuinely missing id, so existence is not leaked | 404 | n/a (read-only) | P0 |
| TC-ORG-037 | Org / Get Branch | Non-existent id | — | `GET /branches/99999999` | `BRANCH_NOT_FOUND` | 404 | n/a (read-only) | P2 |
| TC-ORG-038 | Org / Update Branch | Partial update | BRANCH_A2 | `PATCH /branches/501` B:`{"city":"Pimpri","allowed_radius_meters":300}` | 200; only those two fields change | 200 | `SELECT city, allowed_radius_meters, branch_name FROM branches WHERE branch_id=501` → `Pimpri, 300, <unchanged>` | P1 |
| TC-ORG-039 | Org / Update Branch | Cross-org update | BRANCH_B1 (600) | `PATCH /branches/600` (Bearer `TOK_ADMIN_A`) B:`{"branch_name":"Pwned"}` | `BRANCH_NOT_FOUND` | 404 | `SELECT branch_name FROM branches WHERE branch_id=600` → unchanged | P0 |
| TC-ORG-040 | Org / Deactivate Branch | **Blocked when referenced by an ACTIVE employee** | EMP_001 (`employment_status='active'`) has `master_branch_id=500` | `POST /branches/500/deactivate` | `error.code = BRANCH_IN_USE` | 409 | `SELECT is_active FROM branches WHERE branch_id=500` → **still `true`** | P0 |
| TC-ORG-041 | Org / Deactivate Branch | Allowed when only **non-active** employees reference it | BRANCH_A2 (501) referenced only by EMP_002 (`terminated`) — ensure EMP_003 is moved off 501 first | `POST /branches/501/deactivate` | 200, `is_active = false` — terminated/inactive employees do not block | 200 | `SELECT is_active FROM branches WHERE branch_id=501` → `false` | P0 |
| TC-ORG-042 | Org / Deactivate Branch | Deactivation is idempotent | BRANCH_A3 already inactive, unreferenced | `POST /branches/502/deactivate` | 200, `is_active = false`; no audit row on the no-op | 200 | `activity_logs` count for `sub_module='branch'` unchanged | P2 |
| TC-ORG-043 | Org / Activate Branch | Activate an inactive branch | BRANCH_A3 | `POST /branches/502/activate` | 200, `is_active = true` — the in-use guard applies only to **deactivation** | 200 | `SELECT is_active FROM branches WHERE branch_id=502` → `true`. `activity_logs` `title='Branch activated'` | P1 |
| TC-ORG-044 | Org / Activate Branch | Missing `branch:edit` | `TOK_VIEWER_A` | `POST /branches/502/activate` | `AUTH_FORBIDDEN` | 403 | `is_active` unchanged | P0 |

### C3. Departments — `/departments`

| ID | Module / API | Test Scenario | Preconditions | Request / Input | Expected Result | HTTP | Database Verification | Priority |
|---|---|---|---|---|---|---|---|---|
| TC-ORG-045 | Org / Create Dept | Happy path | `TOK_ADMIN_A` (`department:create`) | `POST /departments` B:`{"dept_name":"Quality Assurance"}` | 201, `data` = `{dept_id, org_id:1, dept_name, is_active:true, is_deleted:false, created_by:11, created_at, updated_at}` | 201 | `SELECT org_id, created_by, is_active FROM departments WHERE dept_name='Quality Assurance'` → `1, 11, true`. `activity_logs` `sub_module='department'` | P0 |
| TC-ORG-046 | Org / Create Dept | Duplicate name in the same org | DEPT_A1 = `Engineering` | `POST /departments` B:`{"dept_name":"Engineering"}` | `error.code = DEPARTMENT_NAME_EXISTS` | 409 | `SELECT count(*) FROM departments WHERE org_id=1 AND dept_name='Engineering' AND is_deleted=false` → still `1` | P0 |
| TC-ORG-047 | Org / Create Dept | **Uniqueness is CASE-INSENSITIVE** | `Engineering` exists | `POST /departments` B:`{"dept_name":"engineering"}` and B:`{"dept_name":"  ENGINEERING  "}` | `DEPARTMENT_NAME_EXISTS` both times — the check is `lower(dept_name) = lower(trim(:name))` | 409 | `SELECT count(*) FROM departments WHERE org_id=1 AND lower(dept_name)='engineering' AND is_deleted=false` → still `1` | P0 |
| TC-ORG-048 | Org / Create Dept | Same department name is legal in a **different** org | DEPT_B1 = `Engineering` in ORG_B | `POST /departments` (Bearer `TOK_ADMIN_B`) B:`{"dept_name":"Finance"}` | 201 — uniqueness is per-org | 201 | Rows named `Finance` exist for both `org_id=1` and `org_id=2` | P1 |
| TC-ORG-049 | Org / Create Dept | Name uniqueness ignores **soft-deleted** rows | A department `Legacy` with `is_deleted=true` in ORG_A | `POST /departments` B:`{"dept_name":"Legacy"}` | 201 — both the service pre-check and the partial unique index `uq_departments_org_id_dept_name … WHERE is_deleted = false` exclude deleted rows | 201 | `SELECT count(*) FROM departments WHERE org_id=1 AND dept_name='Legacy'` → `2` (one deleted, one live) | P1 |
| TC-ORG-050 | Org / Create Dept | **Concurrency: 10 identical creates → 1 × 201, 9 × 409** | Fresh name | 10 concurrent `POST /departments` with the same `dept_name` | Exactly one 201; nine 409 (`DEPARTMENT_NAME_EXISTS` or the mapped `CONFLICT` from the partial unique index). **Zero 500s** | 201 ×1, 409 ×9 | `SELECT count(*) FROM departments WHERE org_id=1 AND dept_name=:name AND is_deleted=false` → **exactly 1** | P0 |
| TC-ORG-051 | Org / Create Dept | Validation: blank name, name > 150 chars, missing field | — | 3 separate calls | `VALIDATION_ERROR` each | 422 | n/a (read-only) | P2 |
| TC-ORG-052 | Org / List Depts | Tenant-scoped paged list | ORG_A and ORG_B populated | `GET /departments` (Bearer `TOK_ADMIN_A`) | Only ORG_A departments; DEPT_B1 (800) absent | 200 | `items[].dept_id` ∩ `SELECT dept_id FROM departments WHERE org_id=2` = ∅ | P0 |
| TC-ORG-053 | Org / List Depts | Search / filter / sort / include_deleted | — | `?search=eng&is_active=true&sort_by=dept_name&sort_order=desc&include_deleted=false` | Correct subset, correctly ordered | 200 | n/a (read-only) | P1 |
| TC-ORG-054 | Org / Get Dept | **Cross-org department → 404** | DEPT_B1 (800) | `GET /departments/800` (Bearer `TOK_ADMIN_A`) | `error.code = DEPARTMENT_NOT_FOUND` | 404 | n/a (read-only) | P0 |
| TC-ORG-055 | Org / Update Dept | Rename | DEPT_A2 (701) | `PATCH /departments/701` B:`{"dept_name":"Finance & Accounts"}` | 200 | 200 | `SELECT dept_name FROM departments WHERE dept_id=701` → updated | P1 |
| TC-ORG-056 | Org / Update Dept | Rename onto an existing name (case-insensitive) | `Engineering` exists | `PATCH /departments/701` B:`{"dept_name":"ENGINEERING"}` | `DEPARTMENT_NAME_EXISTS` | 409 | `SELECT dept_name FROM departments WHERE dept_id=701` → unchanged | P0 |
| TC-ORG-057 | Org / Deactivate Dept | **Blocked when referenced by an ACTIVE employee** | EMP_001 has `dept_id=700` | `POST /departments/700/deactivate` | `error.code = DEPARTMENT_IN_USE` | 409 | `SELECT is_active FROM departments WHERE dept_id=700` → **still `true`** | P0 |
| TC-ORG-058 | Org / Deactivate Dept | Allowed once no active employee references it | DEPT_A2 (701), only terminated employees | `POST /departments/701/deactivate` | 200, `is_active = false` | 200 | `SELECT is_active FROM departments WHERE dept_id=701` → `false` | P0 |
| TC-ORG-059 | Org / Activate Dept | Activate an inactive department | DEPT_A2 inactive | `POST /departments/701/activate` | 200, `is_active = true` | 200 | `SELECT is_active FROM departments WHERE dept_id=701` → `true` | P1 |
| TC-ORG-060 | Org / Dept | Missing `department:edit` | `TOK_VIEWER_A` | `PATCH /departments/701` B:`{"dept_name":"X"}` | `AUTH_FORBIDDEN` | 403 | Row unchanged | P0 |

### C4. Designations — `/designations`

| ID | Module / API | Test Scenario | Preconditions | Request / Input | Expected Result | HTTP | Database Verification | Priority |
|---|---|---|---|---|---|---|---|---|
| TC-ORG-061 | Org / Create Desig | Happy path | `TOK_ADMIN_A` (`designation:create`) | `POST /designations` B:`{"designation_name":"Team Lead"}` | 201, `data` = `{designation_id, org_id:1, designation_name, is_active:true, is_deleted:false, created_by:11, ...}` | 201 | `SELECT org_id, created_by FROM designations WHERE designation_name='Team Lead'` → `1, 11`. `activity_logs` `sub_module='designation'` | P0 |
| TC-ORG-062 | Org / Create Desig | Duplicate name (case-insensitive) in the same org | DESIG_A1 = `Manager` | `POST /designations` B:`{"designation_name":"manager"}` | `error.code = DESIGNATION_NAME_EXISTS` | 409 | `SELECT count(*) FROM designations WHERE org_id=1 AND lower(designation_name)='manager' AND is_deleted=false` → still `1` | P0 |
| TC-ORG-063 | Org / Create Desig | Same name is legal in a different org | DESIG_B1 = `Manager` in ORG_B | `POST /designations` (Bearer `TOK_ADMIN_B`) B:`{"designation_name":"Analyst"}` | 201 | 201 | Rows named `Analyst` exist for `org_id` 1 **and** 2 | P1 |
| TC-ORG-064 | Org / Create Desig | **Concurrency: 10 identical creates → 1 × 201, 9 × 409** | Fresh name | 10 concurrent `POST /designations`, same `designation_name` | Exactly one 201; nine 409. **Zero 500s** | 201 ×1, 409 ×9 | `SELECT count(*) FROM designations WHERE org_id=1 AND designation_name=:name AND is_deleted=false` → **exactly 1** | P0 |
| TC-ORG-065 | Org / Create Desig | Validation: blank / > 150 chars / missing | — | 3 separate calls | `VALIDATION_ERROR` each | 422 | n/a (read-only) | P2 |
| TC-ORG-066 | Org / List Desig | Tenant-scoped paged list | — | `GET /designations` (Bearer `TOK_ADMIN_A`) | Only ORG_A designations; DESIG_B1 (1000) absent | 200 | `items[].designation_id` ∩ `SELECT designation_id FROM designations WHERE org_id=2` = ∅ | P0 |
| TC-ORG-067 | Org / Get Desig | **Cross-org designation → 404** | DESIG_B1 (1000) | `GET /designations/1000` (Bearer `TOK_ADMIN_A`) | `error.code = DESIGNATION_NOT_FOUND` | 404 | n/a (read-only) | P0 |
| TC-ORG-068 | Org / Update Desig | Rename onto an existing name | `Manager` exists | `PATCH /designations/901` B:`{"designation_name":"Manager"}` | `DESIGNATION_NAME_EXISTS` | 409 | `SELECT designation_name FROM designations WHERE designation_id=901` → unchanged | P0 |
| TC-ORG-069 | Org / Deactivate Desig | **Blocked when referenced by an ACTIVE employee** | EMP_001 has `designation_id=900` | `POST /designations/900/deactivate` | `error.code = DESIGNATION_IN_USE` | 409 | `SELECT is_active FROM designations WHERE designation_id=900` → **still `true`** | P0 |
| TC-ORG-070 | Org / Deactivate Desig | Allowed once no active employee references it | DESIG_A2 (901) | `POST /designations/901/deactivate` | 200, `is_active = false` | 200 | `SELECT is_active FROM designations WHERE designation_id=901` → `false` | P0 |
| TC-ORG-071 | Org / Activate Desig | Activate + idempotency | DESIG_A2 inactive | `POST /designations/901/activate` ×2 | 200 both times, `is_active = true`; the second is a no-op | 200 | `activity_logs` gains exactly **one** `title='Designation activated'` row, not two | P2 |
| TC-ORG-072 | Org / Desig | Missing `designation:create` | `TOK_HR_A` | `POST /designations` B: valid | `AUTH_FORBIDDEN` | 403 | No row created | P0 |
| TC-ORG-073 | Org / All routes | Revoked token is rejected on every org route | `TOK_T` revoked via logout | `GET /branches`, `GET /departments`, `GET /designations`, `POST /branches` | `AUTH_NOT_AUTHENTICATED` (401) on all four | 401 | n/a (read-only) | P0 |

---

## 6. End-to-End Workflows

| ID | Module / API | Test Scenario | Preconditions | Request / Input | Expected Result | HTTP | Database Verification | Priority |
|---|---|---|---|---|---|---|---|---|
| TC-ARO-E2E-001 | Auth+RBAC+Org | **Tenant onboarding**: provision an org, its hierarchy, a role, and an admin who can then log in | `TOK_SA_A` | 1. `POST /organizations` `{"org_code":"NEWCO","org_name":"NewCo"}` → `org_id=N`<br>2. `POST /users` `{"name":"Ann","email":"ann@newco.test","mobile_number":"9000000001","password":"Passw0rd!23","is_super_admin":true}` (as super-admin, `X-Org-ID: N` context)<br>3. Login as Ann (`X-Org-ID: N`)<br>4. `POST /branches`, `POST /departments`, `POST /designations`<br>5. `POST /rights-templates` with `branch:read` + `department:read`<br>6. `POST /users` (staff) → `PUT /users/{staff}/template` | Every step succeeds; the staff user's `GET /auth/me` after login shows exactly `branch:read` and `department:read` | 201/200 | `organizations`, `users`, `branches`, `departments`, `designations`, `rights_templates`, `rights_template_permissions`, `user_template_assignments` each gain the expected row(s), all with `org_id = N`. `activity_logs` contains one row per mutation | P0 |
| TC-ARO-E2E-002 | RBAC | **Permission-change propagation**: grant → verify → revoke → verify | TARGET_A logged in with ROLE_FREE (no `branch` permission) | 1. `GET /branches` as TARGET_A → 403<br>2. Admin: `POST /rights-templates/103/permissions` `{"feature_key":"branch","feature_label":"Branches","can_read":true}`<br>3. TARGET_A: `POST /auth/refresh` → new access token<br>4. `GET /branches` → 200<br>5. Admin: `DELETE /rights-templates/103/permissions/branch`<br>6. TARGET_A: refresh → `GET /branches` | Step 1 → `AUTH_FORBIDDEN` (403); step 4 → 200; step 6 → `AUTH_FORBIDDEN` (403) again. **Note:** the *existing* access token from step 3 keeps working until it expires (permissions are token-carried) — only a refresh re-reads them | 403→200→403 | `rights_template_permissions` for (103, `branch`) exists after step 2, is gone after step 5 | P0 |
| TC-ARO-E2E-003 | Auth+RBAC | **Offboarding kills access instantly**: deactivate → live token dies → sessions revoked | TARGET_A logged in on 3 devices (3 active sessions, 3 live access tokens) | 1. `POST /users/30/deactivate` (as ADMIN_A)<br>2. Replay each of the 3 access tokens against `GET /auth/me`<br>3. `POST /users/30/sessions/revoke-all`<br>4. Attempt `POST /auth/login` as TARGET_A | Step 2 → `AUTH_FORBIDDEN` (403, "This account is inactive.") for **all three** tokens, without waiting for expiry. Step 3 → `{"revoked_count": 3}`. Step 4 → `AUTH_INVALID_CREDENTIALS` (401) | 403 / 200 / 401 | `users.is_active` (id 30) → `false`; after step 3 `SELECT count(*) FROM user_sessions WHERE user_id=30 AND is_active=true` → `0`; `activity_logs` has `title='User deactivated'` then `title='All user sessions revoked'` | P0 |
| TC-ARO-E2E-004 | Org+RBAC | **Data-scope enforcement end-to-end** | ORG_A has branches 500, 501, 502; VIEWER_A has `branch:read` and no grants | 1. `GET /branches` as VIEWER_A → 3 branches (unscoped)<br>2. Admin: `PUT /users/13/branch-access` `{"branch_ids":[501]}`<br>3. VIEWER_A: `POST /auth/refresh` → `GET /branches`<br>4. Admin: `PUT /users/13/branch-access` `{"branch_ids":[]}`<br>5. VIEWER_A: refresh → `GET /branches` | Step 1 → 3 items; step 3 → **1 item** (branch 501 only); step 5 → back to 3 items (empty scope = unscoped) | 200 | After step 2: `SELECT branch_id FROM user_branch_access WHERE user_id=13` → `{501}`; after step 4 → `∅` | P0 |
| TC-ARO-E2E-005 | Org | **Deactivation guard lifecycle** | BRANCH_A1 (500) with active EMP_001 | 1. `POST /branches/500/deactivate` → 409 `BRANCH_IN_USE`<br>2. Move EMP_001 to branch 501 (or set `employment_status='terminated'`)<br>3. `POST /branches/500/deactivate` → 200<br>4. `POST /branches/500/activate` → 200 | Step 1 blocks; step 3 succeeds once the last active reference is gone; step 4 re-activates freely (no guard on activation) | 409 → 200 → 200 | `branches.is_active` (500): `true` → `false` → `true`. `SELECT count(*) FROM employees WHERE master_branch_id=500 AND employment_status='active' AND is_deleted=false` → `0` before step 3 succeeds | P0 |
| TC-ARO-E2E-006 | Auth | **Brute-force → lockout → recovery** | Redis up; fresh counters for ADMIN_A | 1. 5 × wrong-password login<br>2. 1 × correct-password login<br>3. Wait out `login_lockout_seconds` (or delete the Redis lockout key)<br>4. 1 × correct-password login | Step 1 → 401 ×5 (`AUTH_INVALID_CREDENTIALS`); step 2 → **429 `RATE_LIMITED`** + `Retry-After`; step 4 → **200** with a fresh session | 401/429/200 | No `user_sessions` row for user 11 is created between steps 1 and 3. After step 4: `SELECT count(*) FROM user_sessions WHERE user_id=11 AND is_active=true` → +1, and Redis `auth:login:failures:1:<hash>` is deleted | P0 |
| TC-ARO-E2E-007 | Multi-tenant | **ORG_A cannot see or touch anything in ORG_B** (sweep) | `TOK_ADMIN_A` | Iterate ORG_B ids against: `GET/PATCH /users/21`, `GET /rights-templates/200`, `GET/PATCH /branches/600`, `GET /departments/800`, `GET /designations/1000`, `GET /users/21/sessions`, `PUT /users/21/template`, `GET /organizations/2` | Every id-addressed branch/dept/designation/user/role route → **404** with its `*_NOT_FOUND` code. `GET /organizations/2` → **403 `AUTH_FORBIDDEN`** (the documented exception). Every list route → zero ORG_B rows | 404 / 403 / 200 | No row in any ORG_B table is modified: snapshot `updated_at` for all ORG_B rows before and after — **must be identical** | P0 |

---

## 7. Coverage Summary & Known Gaps

### Case count

| Module | Cases | Endpoints covered | Cases / endpoint |
|---|---|---|---|
| Authentication (`TC-AUTH`) | 52 | 7 / 7 | 7.4 |
| User Management & RBAC (`TC-RBAC`) | 132 | 42 / 42 | 3.1 |
| Organization Management (`TC-ORG`) | 73 | 24 / 24 | 3.0 |
| End-to-end workflows (`TC-E2E`) | 7 | cross-module | — |
| **Total** | **257** | **73 / 73** | **3.4** |

ID ranges: `TC-AUTH-001`-`050` (plus sub-numbered `020b`, `020c` → 52 rows) · `TC-RBAC-001`-`132` ·
`TC-ORG-001`-`073` · `TC-ARO-E2E-001`-`007`.

Authentication is deliberately the densest module (7.4 cases/endpoint): `POST /auth/login` alone carries
the credential-disclosure, tenant-resolution, per-IP throttle, per-email throttle and account-lockout
behaviours, each of which is a separate security control needing its own assertion.

### Priority distribution

P0 (security / data integrity): 151 · P1 (core business flow): 73 · P2 (validation / edge): 40 · P3: 0.

### Coverage matrix

| Requirement | Where |
|---|---|
| Functional / happy path (every endpoint) | TC-AUTH-001/016/021/024/030/033/036 · TC-RBAC-001/014/019/023/032/033/035/038/040/043/044/052/055/057/059/061/063/066/067/070/073/078/082/085/087/091/094/097/098/101/103/108/113/114/116/118/124/127/129 · TC-ORG-001/008/012/017/021/023/026/032/035/038/043/045/052/055/059/061/066 |
| Validation / boundary | TC-AUTH-012/013/014/020c · TC-RBAC-011/018/050 · TC-ORG-005/006/007/028/029/030/051/065 |
| Authentication (none / expired / malformed / revoked / no-`sid`) | TC-AUTH-026..029, 038..042 · TC-ORG-025/073 |
| Authorization (403 missing permission) | TC-RBAC-012/037/051/076/084/093/107/123/131 · TC-ORG-002/009/024/031/044/060/072 |
| Super-admin gating (grant **and** revoke) | TC-RBAC-008/009/027/028/029/030 · TC-ORG-002/009/024 |
| Business rules | TC-RBAC-034/036/039/041/060/062/068/086/103/104 · TC-ORG-003/027/040/041/047/049/057/069 |
| Multi-tenant isolation | TC-AUTH-009/023/032/034 · TC-RBAC-006/017/021/031/048/054/056/065/077/089/106/112/126/128 · TC-ORG-013/020/032/036/039/052/054/066/067 · TC-ARO-E2E-007 |
| Concurrency (1 × 201 + 9 × 409, no 500) | TC-RBAC-013/110 · TC-ORG-004/050/064 |
| Rate limiting & lockout | TC-AUTH-043..050 · TC-ARO-E2E-006 |
| Database verification | Every row (`n/a (read-only)` only on pure reads) |
| End-to-end workflows | TC-ARO-E2E-001..007 |

### Verification performed

Every error code used in this document was grepped against the codebase and confirmed to exist:
`AUTH_NOT_AUTHENTICATED`, `AUTH_FORBIDDEN`, `AUTH_INVALID_CREDENTIALS`, `AUTH_REFRESH_INVALID`,
`AUTH_SESSION_NOT_FOUND`, `AUTH_USER_INACTIVE`, `RATE_LIMITED`, `VALIDATION_ERROR`, `TENANT_UNRESOLVED`,
`CONFLICT`, `USER_NOT_FOUND`, `USER_EMAIL_EXISTS`, `USER_MOBILE_EXISTS`, `USER_NOT_DELETED`,
`CANNOT_MODIFY_SELF`, `EMPLOYEE_ALREADY_MAPPED`, `TEMPLATE_NOT_FOUND`, `TEMPLATE_NAME_EXISTS`,
`TEMPLATE_IN_USE`, `TEMPLATE_NOT_DELETED`, `PERMISSION_NOT_FOUND`, `FEATURE_KEY_UNKNOWN`,
`ASSIGNMENT_NOT_FOUND`, `BRANCH_ACCESS_EXISTS`, `BRANCH_ACCESS_NOT_FOUND`, `DEPARTMENT_ACCESS_EXISTS`,
`DEPARTMENT_ACCESS_NOT_FOUND`, `SESSION_NOT_FOUND`, `ORG_NOT_FOUND`, `ORG_CODE_EXISTS`,
`BRANCH_NOT_FOUND`, `BRANCH_IN_USE`, `DEPARTMENT_NOT_FOUND`, `DEPARTMENT_NAME_EXISTS`,
`DEPARTMENT_IN_USE`, `DESIGNATION_NOT_FOUND`, `DESIGNATION_NAME_EXISTS`, `DESIGNATION_IN_USE`.

Sources: `app/core/exceptions/base.py`, `app/core/exceptions/handlers.py`,
`app/modules/{auth,rbac,organization}/{service,router,dependencies,exceptions,schemas,repository}.py`,
`app/core/security/permissions.py`, `app/core/dependencies/auth.py`, `app/core/dependencies/rate_limit.py`,
`app/modules/rbac/models/*.py`, `app/modules/employee/models/organization.py`.

### Known gaps (asserted by the cases above — these are the regressions worth catching)

1. **Cross-org branch/department grant is not validated** (TC-RBAC-112).
   `RBACService.assign_branch_access` / `assign_department_access` / their `replace_*` counterparts check
   only `user_branch_access.exists(user_id, branch_id)` and the FK. They never verify that the branch or
   department belongs to the caller's `org_id`. An ORG_A admin can therefore grant an ORG_A user data
   scope over an **ORG_B** branch, and the FK to `branches.branch_id` will happily accept it.
   TC-RBAC-112 is written against the **secure** expectation (404 `BRANCH_NOT_FOUND`) and will fail
   against the current build. Treat it as an open P0 finding, not a flaky test.

2. **`FEATURE_KEY_UNKNOWN` carries two different statuses** — 404 from `GET /permissions/{key}`
   (`NotFoundException`) and 422 from the set/replace routes (`ValidationException`). This is intentional
   in the code; TC-RBAC-069/083/096 pin both so a future "harmonisation" cannot silently break clients.

3. **Rate limiting fails open.** If Redis is unreachable the throttle is skipped and only an ERROR is
   logged. TC-AUTH-043..050 therefore require a live Redis; without it they will pass vacuously.
   Consider a pre-flight assertion on Redis connectivity in the suite's session fixture.

### Endpoints with no additional meaningful case beyond the shared baseline

None. All 73 endpoints have at least one functional case plus the applicable auth/authz/tenant cases.
Two are covered only in composite rows to avoid padding:
`GET /users/{id}/department-access` and `PUT|DELETE /users/{id}/department-access[/{id}]` are folded into
TC-RBAC-120 (they are exact structural mirrors of the branch-access routes, which get individual
coverage in TC-RBAC-108..117).
