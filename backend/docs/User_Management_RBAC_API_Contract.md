# User Management & RBAC API Contract

> Module: `app/modules/rbac`
> API Version: `v1` — all routes under `API_V1_PREFIX` (`/api/v1`).
> Status: **Contract only** (no FastAPI/SQLAlchemy/Pydantic/service/repository code).
> Sources of truth: `docs/architecture.md` (Backend Architecture), migration `0007_user_management_rbac`
> (+ `0009`, `0016`), the RBAC SQLAlchemy models (`rbac/models/user.py`, `rights.py`, `access.py`),
> and the approved `docs/Authentication_API_Contract.md`.

This contract covers **user administration and authorization management only**. Authentication flows
(login, logout, refresh, token validation, session self-service) live in the Authentication API Contract
and are **not** duplicated here.

---

## 1. Module Overview

### Purpose
Administer user accounts and the two-layer authorization model: **feature permissions** (rights templates
+ per-user overrides) and **data scope** (branch/department access). Provides admin CRUD over users,
rights templates, template↔permission mapping, user↔template assignment, per-user permission overrides,
branch/department access grants, and administrative session control.

### Responsibilities
- User lifecycle: create, read, update, activate/deactivate, soft-delete/restore, employee mapping.
- Rights templates (this project's "roles"): create, read, update, soft-delete/restore, clone.
- Template permissions: list, add/update, remove, replace (`rights_template_permissions`).
- Feature-permission catalog: expose the registered `feature_key` catalog (read-only).
- User authorization: assign/replace/remove a user's template; manage per-user custom permission overrides.
- Data scope: grant/revoke/list user branch and department access.
- Administrative session control: view/revoke another user's sessions (`user_sessions`).

### Dependencies
| Dependency | Location | Used for |
|---|---|---|
| Auth/permission dependencies | `core/dependencies/auth.py` | `current_user`, `current_org`, `require_permission` |
| Permission registry | `core/security/permissions.py` | `feature_key` catalog (see §3, §11 Q1) |
| Password hashing | `core/security/password.py` | initial credential on user create (see §11 Q3) |
| DB session | `core/dependencies/db.py` | one async session per request |
| Tenant middleware | `core/middleware/tenant.py` | `org_id` scoping |
| Response/pagination schemas | `shared/schemas/` | standard envelope + paginated lists |
| Employee module (service) | `employee` | validate `employee_id`, `branch_id`, `department_id` targets |
| Activity Log (audit) | `audit` | record administrative mutations (see §10) |

**Schema tables owned/used:** `users`, `user_sessions`, `rights_templates`, `rights_template_permissions`,
`user_template_assignments`, `user_custom_permissions`, `user_branch_access`, `user_department_access`.
Cross-module (read/validate only, never written here): `organizations`, `employees`, `branches`,
`departments`.

### Module boundaries
- Owns the 8 RBAC tables above. Does **not** own `employees`/`branches`/`departments` — it references their
  IDs (FKs resolved in `0007`/`0016`) and validates existence via the employee module's service, never by
  querying its tables directly.
- Does **not** implement authentication (token issuance/validation, login, session self-service).
- Password self-service (change/forgot/reset) is **not** in this contract (see §11 Q3).

### Relationship with Authentication
| Concern | Owner |
|---|---|
| Verify credentials, issue/refresh JWT, validate tokens, self-service sessions | **Authentication** contract |
| Who a user is, whether active/deleted, their template/overrides/scope | **This** (User Mgmt & RBAC) contract |
| `current_user` / `require_permission` dependencies consume RBAC data | shared `core/` — populated from this module's tables |
| Admin session control (revoke *another* user's sessions) | **This** contract (distinct from Auth self-service) |

---

## 2. Domain Model Mapping (read this first)

The requested generic terms map onto the approved schema as follows. **No new tables are introduced.**

| Requested concept | Actual schema object | Notes |
|---|---|---|
| Role | `rights_templates` | The project has **no** `roles` table; a "role" **is** a rights template. |
| Assign Role / Replace/List User Roles | `user_template_assignments` | `UNIQUE(user_id)` → **exactly one** template per user. "User roles" is therefore singular. |
| Role permissions | `rights_template_permissions` | Per-`feature_key` CRUD flags (`can_create/read/edit/delete`). |
| Permission (catalog) | `core/security/permissions.py` registry | Feature-key catalog is **code**, not a DB table (read-only list). |
| Per-user overrides | `user_custom_permissions` | Layer on top of the assigned template (custom-over-template). |
| Branch/Department access | `user_branch_access` / `user_department_access` | Data-scope layer. |
| Lock / Unlock User | *(none)* | **Not supported** — no lock columns exist. See §11 Q2. Use Activate/Deactivate. |
| Activate/Deactivate Role | *(none)* | `rights_templates` has no `is_active`; only soft-delete/restore. See §11 Q4. |

---

## 3. Authorization & Permission Model

**Two layers** (per architecture):
1. **Feature permission** — CRUD on a `feature_key`, resolved as *template ⊕ user custom overrides* (custom
   wins). Enforced by `require_permission`.
2. **Data scope** — branch/department access limits which rows a user may see/act on.

**Super admin** (`users.is_super_admin = true`) bypasses feature checks; **tenant isolation (`org_id`) always
applies**. Creating/modifying a super-admin user, or granting `is_super_admin`, requires the caller to be a
super admin (business rule §9).

**Proposed feature keys for this module** (exact strings to be registered in `permissions.py` — see §11 Q1):
- `user_management` — user records, employee mapping, administrative sessions.
- `role_management` — rights templates and their permissions.
- `access_management` — user↔template assignment, custom permission overrides, branch/department access.

All endpoints below require a valid access token (`Authorization: Bearer <token>`) unless stated. Callers
must also pass tenant context per the tenant middleware.

---

## 4. Request & Response Standards

Reuses the shared envelope defined in the Backend Architecture / Authentication contract.

**Success**
```json
{ "success": true, "data": { }, "error": null, "meta": { "request_id": "..." } }
```
**Error**
```json
{ "success": false, "data": null,
  "error": { "code": "USER_EMAIL_EXISTS", "message": "…", "details": [ { "field": "email", "message": "…" } ] },
  "meta": { "request_id": "..." } }
```
**Paginated list** — collection under `data.items` with `page`, `page_size`, `total`.

**Conventions:** BIGINT integer IDs (no UUIDs); timezone-aware ISO-8601 timestamps; empty lists return
`items: []`; ORM models never returned directly; `password_hash` and `session_token` are **never** returned.

### Pagination / Searching / Filtering / Sorting (list endpoints)
- `page` (int ≥ 1, default 1), `page_size` (bounded, module default).
- `search` — free-text, `org_id`-scoped (users: name/email/mobile_number; templates: name).
- Filters are explicit allowlists per endpoint; invalid filter/sort field → `422`.
- `sort_by` (allowlisted) + `sort_dir` (`asc|desc`). Repository applies `org_id` before optional filters.

---

## 5. API Endpoints

Common headers for all protected endpoints: `Authorization: Bearer <access_token>`; `Content-Type:
application/json` (for bodies). Common errors omitted from each table for brevity: `401 AUTH_NOT_AUTHENTICATED`
(missing/invalid token), `403 AUTH_FORBIDDEN` (lacks permission/scope), `422 VALIDATION_ERROR`.

### 5.1 User Management (`/api/v1/users`)

| # | Endpoint | Method | URL | Permission |
|---|---|---|---|---|
| 1 | Create User | POST | `/users` | `user_management:create` |
| 2 | List Users | GET | `/users` | `user_management:read` |
| 3 | Get User Details (admin profile) | GET | `/users/{user_id}` | `user_management:read` |
| 4 | Update User | PATCH | `/users/{user_id}` | `user_management:edit` |
| 5 | Activate User | POST | `/users/{user_id}/activate` | `user_management:edit` |
| 6 | Deactivate User | POST | `/users/{user_id}/deactivate` | `user_management:edit` |
| 7 | Delete User (soft) | DELETE | `/users/{user_id}` | `user_management:delete` |
| 8 | Restore User | POST | `/users/{user_id}/restore` | `user_management:edit` |
| 9 | Assign Employee to User | PUT | `/users/{user_id}/employee` | `user_management:edit` |
| 10 | Remove Employee Mapping | DELETE | `/users/{user_id}/employee` | `user_management:edit` |

**1. Create User** — POST `/users`
- **Body:** `{ "name", "email", "mobile_country_code"?, "mobile_number", "employee_id"?, "is_super_admin"?, "password"? }`
- **Validation:** `name` req ≤150; `email` req, valid, ≤255, unique per `org_id`; `mobile_country_code` ≤10
  (default `+91`); `mobile_number` req ≤20, unique per (`org_id`,`mobile_country_code`,`mobile_number`);
  `employee_id` optional, must exist in org (and not already mapped — business rule §9); `is_super_admin`
  bool default false (**only super admin may set true**); `password` optional (hashed → `password_hash`;
  if omitted the account has no password and cannot log in — see §11 Q3).
- **Success:** `201` → created user object (no `password_hash`).
- **Errors:** `409 USER_EMAIL_EXISTS`, `409 USER_MOBILE_EXISTS`, `404 EMPLOYEE_NOT_FOUND`,
  `409 EMPLOYEE_ALREADY_MAPPED`, `403 FORBIDDEN` (non-super-admin setting `is_super_admin`).
- **Status:** 201, 409, 404, 403, 422.

**2. List Users** — GET `/users`
- **Query:** `page`, `page_size`, `search`, `is_active` (bool), `is_super_admin` (bool),
  `has_employee` (bool), `include_deleted` (bool, default false), `sort_by` (`name|created_at|last_login_at`),
  `sort_dir`.
- **Success:** `200` paginated users (each: id, name, email, mobile, is_active, is_super_admin, employee_id,
  last_login_at, created_at). No secrets.
- **Status:** 200, 422.

**3. Get User Details** — GET `/users/{user_id}`
- **Path:** `user_id` (int).
- **Success:** `200` → full admin profile: user fields + assigned template (id/name or null) + branch/department
  access summary + `is_deleted` flag. Optionally `?expand=effective_permissions` to include resolved perms.
- **Errors:** `404 USER_NOT_FOUND` (outside tenant or nonexistent).
- **Status:** 200, 404.

**4. Update User** — PATCH `/users/{user_id}`
- **Body (all optional):** `{ "name", "email", "mobile_country_code", "mobile_number", "is_super_admin" }`.
- **Validation:** same field rules as create; uniqueness re-checked on change; `is_super_admin` change requires
  super admin; **password is not changed here** (see §11 Q3).
- **Success:** `200` → updated user.
- **Errors:** `404 USER_NOT_FOUND`, `409 USER_EMAIL_EXISTS`, `409 USER_MOBILE_EXISTS`, `403 FORBIDDEN`.
- **Status:** 200, 404, 409, 403, 422.

**5/6. Activate / Deactivate User** — POST `/users/{user_id}/activate` | `/deactivate`
- Sets `is_active` true/false. **No body.**
- **Business rules:** cannot deactivate self (`409 CANNOT_MODIFY_SELF`); deactivating does **not** revoke
  sessions automatically unless combined with §5.9.
- **Success:** `200` → user with new `is_active`. Idempotent (already-in-state returns `200`).
- **Errors:** `404 USER_NOT_FOUND`, `409 CANNOT_MODIFY_SELF`.
- **Status:** 200, 404, 409.

**7. Delete User (soft)** — DELETE `/users/{user_id}`
- Sets `deleted_at = now()` (soft delete). **No hard delete.**
- **Business rules:** cannot delete self; deleted users are excluded from default lists and rejected at login.
- **Success:** `204 No Content`.
- **Errors:** `404 USER_NOT_FOUND`, `409 USER_ALREADY_DELETED`, `409 CANNOT_MODIFY_SELF`.
- **Status:** 204, 404, 409.

**8. Restore User** — POST `/users/{user_id}/restore`
- Clears `deleted_at`.
- **Success:** `200` → restored user.
- **Errors:** `404 USER_NOT_FOUND`, `409 USER_NOT_DELETED`.
- **Status:** 200, 404, 409.

**9. Assign Employee to User** — PUT `/users/{user_id}/employee`
- **Body:** `{ "employee_id": <int> }` → sets `users.employee_id`.
- **Validation:** employee must exist in org; not already mapped to another user (business rule §9).
- **Success:** `200` → user with `employee_id`.
- **Errors:** `404 USER_NOT_FOUND`, `404 EMPLOYEE_NOT_FOUND`, `409 EMPLOYEE_ALREADY_MAPPED`.
- **Status:** 200, 404, 409.

**10. Remove Employee Mapping** — DELETE `/users/{user_id}/employee`
- Sets `users.employee_id = NULL`.
- **Success:** `204`.
- **Errors:** `404 USER_NOT_FOUND`.
- **Status:** 204, 404.

### 5.2 Rights Templates — "Roles" (`/api/v1/rights-templates`)

| # | Endpoint | Method | URL | Permission |
|---|---|---|---|---|
| 11 | Create Template | POST | `/rights-templates` | `role_management:create` |
| 12 | List Templates | GET | `/rights-templates` | `role_management:read` |
| 13 | Get Template Details | GET | `/rights-templates/{template_id}` | `role_management:read` |
| 14 | Update Template | PATCH | `/rights-templates/{template_id}` | `role_management:edit` |
| 15 | Delete Template (soft) | DELETE | `/rights-templates/{template_id}` | `role_management:delete` |
| 16 | Restore Template | POST | `/rights-templates/{template_id}/restore` | `role_management:edit` |
| 17 | Clone Template | POST | `/rights-templates/{template_id}/clone` | `role_management:create` |

**11. Create Template** — `{ "name", "permissions"? }`. `name` req ≤150, unique per org. Optional inline
`permissions` array (see §5.3 item shape). `201` → template. Errors: `409 TEMPLATE_NAME_EXISTS`.

**12. List Templates** — Query: `page`, `page_size`, `search` (name), `include_deleted`,
`sort_by` (`name|created_at`), `sort_dir`. `200` paginated (id, name, permission_count, assigned_user_count,
created_at).

**13. Get Template Details** — `200` → template + its `permissions` list.
Errors: `404 TEMPLATE_NOT_FOUND`.

**14. Update Template** — `{ "name" }`. Renames; uniqueness re-checked. `200`.
Errors: `404 TEMPLATE_NOT_FOUND`, `409 TEMPLATE_NAME_EXISTS`.

**15. Delete Template (soft)** — sets `deleted_at`. **Blocked if assigned to any user**
(`409 TEMPLATE_IN_USE`) since `user_template_assignments.template_id` is `ON DELETE RESTRICT`. `204`.
Errors: `404 TEMPLATE_NOT_FOUND`, `409 TEMPLATE_IN_USE`.

**16. Restore Template** — clears `deleted_at`. `200`. Errors: `404`, `409 TEMPLATE_NOT_DELETED`.

**17. Clone Template** — `{ "name" }` → new template copying all `rights_template_permissions` rows.
`201` → new template. Errors: `404 TEMPLATE_NOT_FOUND`, `409 TEMPLATE_NAME_EXISTS`.

### 5.3 Template Permission Management (`rights_template_permissions`)

| # | Endpoint | Method | URL | Permission |
|---|---|---|---|---|
| 18 | List Template Permissions | GET | `/rights-templates/{template_id}/permissions` | `role_management:read` |
| 19 | Add/Update Permission | POST | `/rights-templates/{template_id}/permissions` | `role_management:edit` |
| 20 | Remove Permission | DELETE | `/rights-templates/{template_id}/permissions/{feature_key}` | `role_management:edit` |
| 21 | Replace All Permissions | PUT | `/rights-templates/{template_id}/permissions` | `role_management:edit` |

**Permission item shape:** `{ "feature_key", "feature_label", "parent_feature_key"?, "can_create", "can_read", "can_edit", "can_delete" }`.

- **18. List** → `200` array of permission rows for the template.
- **19. Add/Update** (upsert one feature) → body = one permission item. Enforces `UNIQUE(template_id,
  feature_key)` (upsert). `feature_key` must exist in the catalog (`422 FEATURE_KEY_UNKNOWN`). `200`/`201`.
- **20. Remove** → deletes the row for `{feature_key}`. `204`. Errors: `404 PERMISSION_NOT_FOUND`.
- **21. Replace All** → body `{ "permissions": [ item, … ] }` replaces the full set atomically. `200`.
- Common errors: `404 TEMPLATE_NOT_FOUND`, `422 FEATURE_KEY_UNKNOWN`.

### 5.4 Permission Catalog (read-only, from `permissions.py`)

| # | Endpoint | Method | URL | Permission |
|---|---|---|---|---|
| 22 | List Permissions (catalog) | GET | `/permissions` | `role_management:read` |
| 23 | View Permission Details | GET | `/permissions/{feature_key}` | `role_management:read` |

- **22.** `200` → registered feature catalog: `[{ feature_key, feature_label, parent_feature_key, supported_actions }]`.
  Optional `?parent_feature_key=` filter to fetch a subtree. This is a **code registry**, not a DB table
  (see §11 Q1).
- **23.** `200` → one feature's metadata. `404 FEATURE_KEY_UNKNOWN`.

### 5.5 User Role (Template) Assignment (`user_template_assignments`, one per user)

| # | Endpoint | Method | URL | Permission |
|---|---|---|---|---|
| 24 | Get User's Assigned Template | GET | `/users/{user_id}/template` | `access_management:read` |
| 25 | Assign / Replace User Template | PUT | `/users/{user_id}/template` | `access_management:edit` |
| 26 | Remove User Template | DELETE | `/users/{user_id}/template` | `access_management:edit` |

- **24. Get** → `200` → `{ "template": { id, name, assigned_by, assigned_at } | null }`. (This is the "List
  User Roles" equivalent — singular by schema.)
- **25. Assign/Replace** → `{ "template_id" }`. Creates or replaces the single `user_template_assignments`
  row (`UNIQUE(user_id)`); `assigned_by` = caller. `200`. Errors: `404 USER_NOT_FOUND`,
  `404 TEMPLATE_NOT_FOUND`.
- **26. Remove** → deletes the assignment. `204`. Errors: `404 ASSIGNMENT_NOT_FOUND`.

### 5.6 User Custom Permissions — overrides (`user_custom_permissions`)

| # | Endpoint | Method | URL | Permission |
|---|---|---|---|---|
| 27 | List User Custom Permissions | GET | `/users/{user_id}/custom-permissions` | `access_management:read` |
| 28 | Add/Update Custom Permission | POST | `/users/{user_id}/custom-permissions` | `access_management:edit` |
| 29 | Remove Custom Permission | DELETE | `/users/{user_id}/custom-permissions/{feature_key}` | `access_management:edit` |
| 30 | Replace Custom Permissions | PUT | `/users/{user_id}/custom-permissions` | `access_management:edit` |
| 31 | Get Effective Permissions | GET | `/users/{user_id}/effective-permissions` | `access_management:read` |

**Custom permission item:** `{ "feature_key", "parent_feature_key"?, "can_create", "can_read", "can_edit", "can_delete" }` (`set_by` = caller, `set_at` = now).

- **27.** `200` → override rows. **28.** upsert one (`UNIQUE(user_id, feature_key)`); `422 FEATURE_KEY_UNKNOWN`.
  **29.** `204`; `404 PERMISSION_NOT_FOUND`. **30.** replace full override set atomically; `200`.
- **31. Effective Permissions** → `200` → resolved *template ⊕ overrides* (custom wins), the same set the
  Authentication `/auth/me` returns — provided here for admins inspecting another user.
- Common errors: `404 USER_NOT_FOUND`.

### 5.7 Branch Access Management (`user_branch_access`)

| # | Endpoint | Method | URL | Permission |
|---|---|---|---|---|
| 32 | List User Branch Access | GET | `/users/{user_id}/branch-access` | `access_management:read` |
| 33 | Assign Branch Access | POST | `/users/{user_id}/branch-access` | `access_management:edit` |
| 34 | Replace Branch Access | PUT | `/users/{user_id}/branch-access` | `access_management:edit` |
| 35 | Remove Branch Access | DELETE | `/users/{user_id}/branch-access/{branch_id}` | `access_management:edit` |

- **32.** `200` → `[{ branch_id, granted_by, granted_at }]`.
- **33.** `{ "branch_id" }` — branch must exist in org; `UNIQUE(user_id, branch_id)` → `409
  BRANCH_ACCESS_EXISTS`; `404 BRANCH_NOT_FOUND`. `201`.
- **34.** `{ "branch_ids": [ … ] }` replaces the full set atomically. `200`.
- **35.** `204`; `404 BRANCH_ACCESS_NOT_FOUND`.
- Common: `404 USER_NOT_FOUND`.

### 5.8 Department Access Management (`user_department_access`)

| # | Endpoint | Method | URL | Permission |
|---|---|---|---|---|
| 36 | List User Department Access | GET | `/users/{user_id}/department-access` | `access_management:read` |
| 37 | Assign Department Access | POST | `/users/{user_id}/department-access` | `access_management:edit` |
| 38 | Replace Department Access | PUT | `/users/{user_id}/department-access` | `access_management:edit` |
| 39 | Remove Department Access | DELETE | `/users/{user_id}/department-access/{department_id}` | `access_management:edit` |

- Mirrors §5.7. `department_id` references `departments.dept_id`; `UNIQUE(user_id, department_id)` →
  `409 DEPARTMENT_ACCESS_EXISTS`; `404 DEPARTMENT_NOT_FOUND`; `404 DEPARTMENT_ACCESS_NOT_FOUND`.

### 5.9 Session Administration (admin — `user_sessions`)

Distinct from Authentication self-service: these act on **another** user's sessions and require permission.

| # | Endpoint | Method | URL | Permission |
|---|---|---|---|---|
| 40 | View User Active Sessions | GET | `/users/{user_id}/sessions` | `user_management:read` |
| 41 | Force Logout (revoke one session) | DELETE | `/users/{user_id}/sessions/{session_id}` | `user_management:edit` |
| 42 | Revoke All User Sessions | POST | `/users/{user_id}/sessions/revoke-all` | `user_management:edit` |

- **40.** Query `page`, `page_size`, `active_only` (default true). `200` paginated sessions (id, device_info,
  ip_address, created_at, expires_at, is_active). **`session_token` never returned.**
- **41.** Revokes one session (`is_active=false`, `revoked_at=now`) belonging to the target user. `204`;
  `404 SESSION_NOT_FOUND`.
- **42.** Revokes all of the target user's sessions. `200` → `{ "revoked_count": <int> }`. Useful after
  deactivate/delete.
- Common: `404 USER_NOT_FOUND`.

---

## 6. Standard Features

### Pagination / Search / Filter / Sort
Per §4. Allowlisted filter/sort fields per endpoint; invalid field → `422`. All lists `org_id`-scoped.

### Bulk Operations
Not defined in the approved architecture. If later approved, they should follow a standard shape
(`POST /users/bulk-deactivate` etc. with an `ids: [int]` body and a per-item result envelope). **Flagged as
out of scope unless approved** — not invented here (§11 Q5).

### Validation Rules (summary)
| Field | Rule |
|---|---|
| `email` | required, RFC email, ≤255, unique per `org_id` |
| `mobile_number` (+`mobile_country_code`) | required, ≤20 (+≤10), unique per `org_id` |
| `name` | required, ≤150 |
| `is_super_admin` | boolean; settable only by a super admin |
| `template name` | required, ≤150, unique per `org_id` |
| `feature_key` | must exist in the permission catalog; ≤100 |
| `feature_label` | required for template permissions, ≤150 |
| CRUD flags | booleans, default false |
| `employee_id` / `branch_id` / `department_id` | must exist within the caller's `org_id` |

### Business Rules
- Tenant isolation on every endpoint; cross-org access returns `404` within scope.
- `is_super_admin` grant/modification requires a super-admin caller.
- A user cannot deactivate/delete their own account.
- Do not remove/deactivate the org's **last** super admin (guard) — `409 LAST_SUPER_ADMIN`.
- Soft-delete a template only if it has no active assignments (`409 TEMPLATE_IN_USE`).
- One template per user (schema-enforced); assigning replaces the existing one.
- Employee↔user mapping treated as 1:1 (business rule; not DB-enforced — §11 Q6).

### Permission Matrix
| Feature key | create | read | edit | delete |
|---|---|---|---|---|
| `user_management` | Create User | List/Get Users, View Sessions | Update, Activate/Deactivate, Restore, Employee map, Force Logout, Revoke Sessions | Delete User |
| `role_management` | Create/Clone Template | List/Get Templates, List/Get Permission catalog, List Template Permissions | Update Template, Restore, add/remove/replace Template Permissions | Delete Template |
| `access_management` | — | Get user template, custom perms, branch/dept access, effective permissions | Assign/Replace/Remove user template, custom perms, branch/dept access | — |

Super admins bypass the feature checks above; tenant isolation still applies.

### Error Handling
Standard error envelope (§4) via `core/exceptions/handlers.py`. Module error codes:
`USER_NOT_FOUND`(404), `USER_EMAIL_EXISTS`(409), `USER_MOBILE_EXISTS`(409), `USER_ALREADY_DELETED`(409),
`USER_NOT_DELETED`(409), `CANNOT_MODIFY_SELF`(409), `LAST_SUPER_ADMIN`(409), `EMPLOYEE_NOT_FOUND`(404),
`EMPLOYEE_ALREADY_MAPPED`(409), `TEMPLATE_NOT_FOUND`(404), `TEMPLATE_NAME_EXISTS`(409), `TEMPLATE_IN_USE`(409),
`TEMPLATE_NOT_DELETED`(409), `PERMISSION_NOT_FOUND`(404), `FEATURE_KEY_UNKNOWN`(422), `ASSIGNMENT_NOT_FOUND`(404),
`BRANCH_NOT_FOUND`(404), `BRANCH_ACCESS_EXISTS`(409), `BRANCH_ACCESS_NOT_FOUND`(404), `DEPARTMENT_NOT_FOUND`(404),
`DEPARTMENT_ACCESS_EXISTS`(409), `DEPARTMENT_ACCESS_NOT_FOUND`(404), `SESSION_NOT_FOUND`(404),
`VALIDATION_ERROR`(422), plus shared `AUTH_NOT_AUTHENTICATED`(401), `AUTH_FORBIDDEN`(403). Error codes are
proposed identifiers to be registered in the module's `exceptions.py`.

### Audit Logging
All administrative mutations (create/update/activate/deactivate/delete/restore user; template CRUD; permission
and access grants/revocations; forced session revocation) are recorded in the **Activity Log** module
(`action_type` ∈ Insert/Update/Delete/Assign/Bulk Assign; `action_from` per platform). Passwords, hashes,
tokens are redacted. Application logs carry correlation id, actor `user_id`, `org_id`.

### Security Considerations
- Every route enforces `require_permission` + tenant scope; `is_super_admin` escalation guarded.
- `password_hash` and `session_token` never leave the API.
- Initial passwords (if provided on create) hashed via `core/security/password.py`; never logged.
- Admin session revocation lets operators contain compromised accounts.
- Deactivate/delete should be paired with §5.9 revoke to terminate live sessions.
- Rate limiting applies to sensitive admin mutations per the security baseline.

---

## 7. Open Questions

1. **Feature-key catalog (Q1).** `core/security/permissions.py` is a stub; the concrete `feature_key`
   catalog and the exact feature keys for this module (`user_management` / `role_management` /
   `access_management` proposed here) are not yet defined. Confirm the catalog and key names.
2. **Lock / Unlock User (Q2).** Not supported — no lock columns exist (`is_locked`/`locked_until`/
   `failed_attempts`). Only Activate/Deactivate (`is_active`) and Delete/Restore (`deleted_at`) are provided.
   Confirm no true lock semantics are required (else a schema change is needed).
3. **Password lifecycle (Q3).** Self-service Change Password was deferred to "the User module" by the
   Authentication contract, but this task excludes auth-type endpoints (change/forgot/reset). As a result no
   contract currently owns password change/reset, and there is **no reset-token/OTP table** in the schema.
   Create User accepts an optional initial `password`; **admin password reset and self-service change/reset
   are not specified here.** Decide which module owns them and whether new schema is needed.
4. **Activate/Deactivate Role (Q4).** `rights_templates` has no `is_active`; only soft-delete/restore is
   offered. Confirm that is sufficient (else add a status column).
5. **Bulk operations (Q5).** Not in the approved architecture; omitted rather than invented. Confirm if a
   bulk pattern should be added.
6. **Employee↔User cardinality (Q6).** `users.employee_id` has **no** unique constraint, so the DB permits
   several users mapping the same employee. `EMPLOYEE_ALREADY_MAPPED` is a proposed **business rule** (1:1).
   Confirm 1:1 (and whether to enforce via a partial unique index) or allow many.
7. **Envelope key names (Q7).** `shared/schemas/response.py` is a stub; final envelope field names must match
   once implemented (same open item as the Auth contract).
