# Employee Management API Contract

> Module: `app/modules/employee`
> API Version: `v1` — all routes under `API_V1_PREFIX` (`/api/v1`).
> Status: **Contract only** (no FastAPI/SQLAlchemy/Pydantic/service/repository code).
> Sources of truth: `docs/architecture.md` (Backend Architecture), migration `0001_employee_management`
> (+ `0009`, `0016`), the employee models (`employee/models/organization.py`, `employee.py`, `satellites.py`),
> `employee/constants.py`, and the approved Authentication & User-Management/RBAC API Contracts.

Covers organizational structure (organizations, branches, departments, designations) and the employee master
plus HR profile sub-records. **Excludes** Authentication, User Management/RBAC, Attendance, Leave, Payroll,
Shift, Notifications, and Hardware — those live in their own modules.

---

## 1. Module Overview

### Purpose
Manage the organizational hierarchy and the employee master record, including employment details, status
lifecycle, and HR profile sub-records (documents, bank details, emergency contacts, references, tags).

### Responsibilities
- Organization (tenant) records — **platform/super-admin provisioning**.
- Branch, Department, Designation master data (per tenant).
- Employee master: create/read/update, status lifecycle (activate/deactivate/terminate), organizational
  moves (transfer/promote), and profile sub-records.
- Employee documents (upload/list/download/delete) via the storage infrastructure.
- Append-only employee status history.

### Dependencies
| Dependency | Location | Used for |
|---|---|---|
| Auth/permission deps | `core/dependencies/auth.py` | `current_user`, `current_org`, `require_permission` |
| Tenant middleware | `core/middleware/tenant.py` | `org_id` scoping (branches/depts/designations/employees) |
| RBAC data scope | `rbac` (branch/department access) | filters employee/branch visibility |
| Storage | `infrastructure/storage/` | employee document files (URLs/keys, not bytes in DB) |
| Response/pagination schemas | `shared/schemas/` | envelope + paginated lists |
| Activity Log (audit) | `audit` | records administrative mutations, incl. transfer/promote context |

**Tables owned (in scope):** `organizations`, `branches`, `departments`, `designations`, `employees`,
`employee_documents`, `employee_bank_details`, `employee_emergency_contacts`, `employee_references`,
`employee_tags`, `employee_status_history`.

**Owned by this module's migration but OUT of scope here** (belong to Attendance/Hardware/bulk-import
concerns): `employee_biometrics`, `employee_punch_branches`, `employee_attendance_permissions`,
`org_attendance_settings`, `employee_import_logs`.

### Module boundaries
- Owns organizational + employee master data. Does **not** own users, attendance, leave, payroll, or shift
  data. Cross-module columns present on employee tables (`created_by`/`uploaded_by` → users;
  `payroll_group_id` → payroll_groups) are references only; their assignment semantics may belong to those
  modules (see §11).
- Reporting hierarchy is **not modeled** in the schema (see §11 Q1).

---

## 2. Authorization Model

Standard two-layer RBAC (from the User-Management/RBAC contract): **feature permission** (CRUD on a
`feature_key`) × **data scope** (branch/department access). Super admins bypass feature checks; tenant
isolation (`org_id`) always applies. All endpoints require `Authorization: Bearer <access_token>`.

**Proposed feature keys** (to be registered in `core/security/permissions.py` — see §11 Q5):
`organization`, `branch`, `department`, `designation`, `employee`. Employee sub-records, documents, and
status history are governed by the `employee` key (read/edit). Organization endpoints additionally require
**super-admin/platform** rights (org = tenant).

**Data scope:** `employee` and `branch` list/read are filtered by the caller's `user_branch_access` /
`user_department_access` unless the caller is a super admin.

---

## 3. Request & Response Standards

Reuses the shared envelope (success/error) and pagination from the Backend Architecture.

- **Success:** `{ "success": true, "data": {…}, "error": null, "meta": { "request_id": "…" } }`
- **Error:** `{ "success": false, "data": null, "error": { "code", "message", "details"? }, "meta": {…} }`
- **Paginated:** collection under `data.items` with `page`, `page_size`, `total`.
- BIGINT integer IDs (no UUIDs); timezone-aware ISO-8601 timestamps; empty lists → `items: []`; ORM models
  never returned directly.

### Pagination / Search / Filter / Sort (list endpoints)
- `page` (int ≥ 1, default 1), `page_size` (bounded default).
- `search` — `org_id`-scoped free-text (per endpoint's searchable fields).
- Filters/sorts are explicit allowlists; invalid field → `422`. Repository applies `org_id` (and data scope)
  before optional filters.

Common omitted errors (apply to all protected endpoints): `401 AUTH_NOT_AUTHENTICATED`,
`403 AUTH_FORBIDDEN`, `422 VALIDATION_ERROR`.

---

## 4. Organization Management (`/api/v1/organizations`) — platform/super-admin

`organizations` is the tenant root (PK `org_id`; `org_code` **globally unique**; fields: `org_name`,
`contact_phone`, `contact_email`, `is_active`, `is_deleted`). Create/List-all/Activate/Deactivate require
**super-admin**; a tenant admin may **read** and **update the profile of their own** org.

| # | Endpoint | Method | URL | Permission |
|---|---|---|---|---|
| 1 | Create Organization | POST | `/organizations` | super-admin (`organization:create`) |
| 2 | List Organizations | GET | `/organizations` | super-admin (`organization:read`) |
| 3 | Get Organization | GET | `/organizations/{org_id}` | `organization:read` (own org, or super-admin) |
| 4 | Update Organization | PATCH | `/organizations/{org_id}` | `organization:edit` (own org, or super-admin) |
| 5 | Activate Organization | POST | `/organizations/{org_id}/activate` | super-admin (`organization:edit`) |
| 6 | Deactivate Organization | POST | `/organizations/{org_id}/deactivate` | super-admin (`organization:edit`) |

**Field/validation rules:** `org_code` required ≤20, **globally unique** (`409 ORG_CODE_EXISTS`); `org_name`
required ≤200; `contact_phone` ≤20; `contact_email` ≤150, valid email. `is_active` toggled via 5/6.

**Create** → `201` org object. **List** → paginated (query: `page`, `page_size`, `search` on
code/name, `is_active`, `include_deleted`). **Get/Update** → `200`; `404 ORG_NOT_FOUND`. **Activate/Deactivate**
→ `200` (idempotent). Delete is **not exposed** (tenant deletion is a platform operation; `is_deleted` is
reserved) — see §11 Q2.

---

## 5. Branch / Department / Designation Management

These three are tenant-scoped master data (`org_id` from tenant context). All have `is_active` +
`is_deleted`. Each exposes: **Create, List, Get, Update, Activate, Deactivate** (soft-delete via a separate
DELETE is offered where noted). URLs: `/api/v1/branches`, `/api/v1/departments`, `/api/v1/designations`.

### 5.1 Branch (`/branches`) — feature key `branch`

Fields: `branch_name` (req ≤200), `logo_url`, `gstin` (≤20), `mobile_number` (≤20), `address`, `landmark`
(≤200), `pin_code` (≤10), `city`/`state`/`country` (≤100), `industry_type` (≤100), `latitude`/`longitude`
(Numeric(10,7)), `allowed_radius_meters` (smallint), `is_active`, `is_deleted`.

| # | Endpoint | Method | URL |
|---|---|---|---|
| 7 | Create Branch | POST | `/branches` |
| 8 | List Branches | GET | `/branches` |
| 9 | Get Branch | GET | `/branches/{branch_id}` |
| 10 | Update Branch | PATCH | `/branches/{branch_id}` |
| 11 | Activate Branch | POST | `/branches/{branch_id}/activate` |
| 12 | Deactivate Branch | POST | `/branches/{branch_id}/deactivate` |

- **Validation:** `branch_name` required; geo fields optional (`latitude` −90..90, `longitude` −180..180,
  `allowed_radius_meters` > 0 if present). **No DB uniqueness on `branch_name`** — duplicate names are
  permitted unless a business rule forbids (see §9).
- **List query:** `page`, `page_size`, `search` (name/city), `is_active`, `include_deleted`,
  `sort_by` (`branch_name|created_at`), `sort_dir`. Data-scoped by `user_branch_access`.
- **Business rule:** deactivating/soft-deleting a branch referenced by active employees
  (`employees.master_branch_id`) is blocked → `409 BRANCH_IN_USE`.
- **Errors:** `404 BRANCH_NOT_FOUND`, `409 BRANCH_IN_USE`. **Status:** 200/201/404/409/422.

### 5.2 Department (`/departments`) — feature key `department`

Fields: `dept_name` (req ≤150), `is_active`, `is_deleted`, `created_by` (deferred→users). **Partial unique**
`(org_id, dept_name)` WHERE `is_deleted = false`.

| # | Endpoint | Method | URL |
|---|---|---|---|
| 13 | Create Department | POST | `/departments` |
| 14 | List Departments | GET | `/departments` |
| 15 | Get Department | GET | `/departments/{dept_id}` |
| 16 | Update Department | PATCH | `/departments/{dept_id}` |
| 17 | Activate Department | POST | `/departments/{dept_id}/activate` |
| 18 | Deactivate Department | POST | `/departments/{dept_id}/deactivate` |

- **Validation:** `dept_name` required, unique per org among non-deleted → `409 DEPARTMENT_NAME_EXISTS`.
- **Business rule:** block deactivate/delete if referenced by active employees (`dept_id`) → `409 DEPARTMENT_IN_USE`.
- **Errors:** `404 DEPARTMENT_NOT_FOUND`, `409 DEPARTMENT_NAME_EXISTS`, `409 DEPARTMENT_IN_USE`.

### 5.3 Designation (`/designations`) — feature key `designation`

Fields: `designation_name` (req ≤150), `is_active`, `is_deleted`, `created_by`. **Partial unique**
`(org_id, designation_name)` WHERE `is_deleted = false`.

| # | Endpoint | Method | URL |
|---|---|---|---|
| 19 | Create Designation | POST | `/designations` |
| 20 | List Designations | GET | `/designations` |
| 21 | Get Designation | GET | `/designations/{designation_id}` |
| 22 | Update Designation | PATCH | `/designations/{designation_id}` |
| 23 | Activate Designation | POST | `/designations/{designation_id}/activate` |
| 24 | Deactivate Designation | POST | `/designations/{designation_id}/deactivate` |

- **Validation:** `designation_name` required, unique per org among non-deleted → `409 DESIGNATION_NAME_EXISTS`.
- **Business rule:** block deactivate/delete if referenced by active employees → `409 DESIGNATION_IN_USE`.

---

## 6. Employee Management (`/api/v1/employees`) — feature key `employee`

Employee master fields (from `employees`): `employee_code` (req ≤30, **unique per org among non-deleted**),
`employee_uid` (≤50), `employee_name` (req ≤200), `display_name` (≤200), `mobile_country_code` (≤5, default
`+91`), `mobile_number` (req ≤20), `email` (≤200), `gender` (req, CHECK `Male|Female|Other`),
`master_branch_id` (req, FK→branches, same org), `dept_id` (req, FK→departments, same org),
`designation_id` (req, FK→designations, same org), `employee_type` (≤30, free-text — no DB CHECK),
`door_lock_permission` (bool, default false), `pf_account_number` (≤50), `uan_number` (≤12),
`esic_ip_number` (≤10), `address`, `date_of_joining` (date), `salary_type` (CHECK `Monthly|Hourly|Compliance`),
`monthly_salary` (Numeric(12,2), default 0), `payroll_group_id` (deferred→payroll_groups — see §11 Q4),
`date_of_birth` (date), `date_of_leaving` (date), `employment_status` (CHECK `active|inactive|terminated`,
default `active`), `profile_photo_url`, `is_deleted`, `created_by` (deferred→users).

| # | Endpoint | Method | URL | Permission |
|---|---|---|---|---|
| 25 | Create Employee | POST | `/employees` | `employee:create` |
| 26 | List Employees | GET | `/employees` | `employee:read` |
| 27 | Get Employee Details | GET | `/employees/{employee_id}` | `employee:read` |
| 28 | Update Employee | PATCH | `/employees/{employee_id}` | `employee:edit` |
| 29 | Activate Employee | POST | `/employees/{employee_id}/activate` | `employee:edit` |
| 30 | Deactivate Employee | POST | `/employees/{employee_id}/deactivate` | `employee:edit` |
| 31 | Terminate Employee | POST | `/employees/{employee_id}/terminate` | `employee:edit` |
| 32 | Transfer Employee | POST | `/employees/{employee_id}/transfer` | `employee:edit` |
| 33 | Promote Employee | POST | `/employees/{employee_id}/promote` | `employee:edit` |

**25. Create Employee** — body = master fields above.
- **Validation:** required fields present; `employee_code` unique per org among non-deleted
  (`409 EMPLOYEE_CODE_EXISTS`); `gender`/`salary_type` must match CHECK sets; `master_branch_id`/`dept_id`/
  `designation_id` must exist **in the caller's org** and be active (`404 BRANCH_NOT_FOUND` /
  `DEPARTMENT_NOT_FOUND` / `DESIGNATION_NOT_FOUND`); `email` valid if present; dates well-formed;
  `monthly_salary` ≥ 0.
- **Success:** `201` → employee object. Optionally creates an initial `employee_status_history` row
  (`new_status=active`).
- **Status:** 201, 404, 409, 422.

**26. List Employees** — **Query:** `page`, `page_size`, `search` (employee_code/name/mobile/email),
filters: `employment_status`, `branch_id` (master_branch_id), `dept_id`, `designation_id`, `employee_type`,
`gender`, `include_deleted` (default false); `sort_by` (`employee_code|employee_name|date_of_joining|created_at`),
`sort_dir`. Data-scoped by branch/department access. **Success:** `200` paginated summary rows.

**27. Get Employee Details** — `200` → full employee + optional `?expand=` for `bank_details`,
`emergency_contacts`, `references`, `documents`, `tags`, `status_history`. `404 EMPLOYEE_NOT_FOUND`.

**28. Update Employee** — PATCH; any master field except identity keys. Uniqueness re-checked on
`employee_code` change. Changing `master_branch_id`/`dept_id`/`designation_id` here is allowed but
**Transfer/Promote (32/33) are the preferred, audited paths**. `employment_status` is **not** changed here
(use 29–31). `200`; `404`, `409 EMPLOYEE_CODE_EXISTS`.

**29/30. Activate / Deactivate** — set `employment_status` to `active`/`inactive`; append
`employee_status_history` (previous/new status, `changed_by`, `effective_date`, optional `reason`).
Body: `{ "effective_date"?, "reason"? }`. `200`; `404`. Idempotent.

**31. Terminate** — sets `employment_status='terminated'` and `date_of_leaving`; appends status history.
Body: `{ "effective_date" (req), "date_of_leaving"?, "reason"? }`. `200`; `404`;
`409 EMPLOYEE_ALREADY_TERMINATED`.

**32. Transfer** — changes `master_branch_id` and/or `dept_id`. Body:
`{ "master_branch_id"?, "dept_id"?, "effective_date"?, "reason"? }`. Targets must exist/active in the org.
**Note:** there is no transfer-history table; the change context (`reason`/`effective_date`) is recorded to
the **Activity Log**, not a dedicated column (see §11 Q3). `200`; `404` on unknown target.

**33. Promote** — changes `designation_id` (and optionally `monthly_salary`). Body:
`{ "designation_id" (req), "monthly_salary"?, "effective_date"?, "reason"? }`. Same history caveat as
Transfer. `200`; `404 DESIGNATION_NOT_FOUND`.

> **Delete Employee:** soft-delete via `DELETE /employees/{employee_id}` (sets `is_deleted=true`) may be
> added under `employee:delete`; the schema supports it (`is_deleted`). Included as **#25a** if desired —
> flagged in §11 Q6 since it was not in the requested list.

> **Update Reporting Manager / Reporting hierarchy:** **NOT SUPPORTED** — no manager/reporting column or
> hierarchy table exists. Omitted; see §11 Q1.

---

## 7. Employee Documents (`/api/v1/employees/{employee_id}/documents`)

Backed by `employee_documents` (`document_type` CHECK `aadhar_card|driving_licence|pan_card|passport_photo|other`,
`file_url`, `original_filename`, `file_size_bytes`, `uploaded_by`, `is_deleted`). Files stored via
`infrastructure/storage/` (URL/key persisted, never raw bytes).

| # | Endpoint | Method | URL | Permission |
|---|---|---|---|---|
| 34 | Upload Document | POST | `/employees/{employee_id}/documents` | `employee:edit` |
| 35 | List Documents | GET | `/employees/{employee_id}/documents` | `employee:read` |
| 36 | Download Document | GET | `/employees/{employee_id}/documents/{document_id}` | `employee:read` |
| 37 | Delete Document | DELETE | `/employees/{employee_id}/documents/{document_id}` | `employee:edit` |

- **34.** `multipart/form-data`: `document_type` (CHECK), `file` (binary). Server validates content-type/size
  from config, generates the storage key (does not trust client filename), stores original filename as
  metadata. `201` → document metadata (no filesystem path). Errors: `404 EMPLOYEE_NOT_FOUND`,
  `422` (bad type/oversize/unsupported extension).
- **35.** `200` → list of non-deleted documents (metadata only).
- **36.** `200` → file stream or a short-lived signed URL (per storage backend). `404 DOCUMENT_NOT_FOUND`.
- **37.** soft-delete (`is_deleted=true`). `204`. `404 DOCUMENT_NOT_FOUND`.

---

## 8. Employee Profile Sub-Records & Status History

Tenant/employee-scoped. All governed by the `employee` key (`read` for GET, `edit` for mutations). Each
sub-record row belongs to one employee (FK `employee_id`).

### 8.1 Bank Details (`/employees/{employee_id}/bank-details`) — `employee_bank_details`
Fields: `bank_name` (≤150), `bank_branch_name` (≤150), `account_number` (≤30), `ifsc_code` (≤15),
`is_primary` (bool, default true), `is_deleted`.

| # | Endpoint | Method | URL |
|---|---|---|---|
| 38 | List Bank Details | GET | `/employees/{employee_id}/bank-details` |
| 39 | Add Bank Detail | POST | `/employees/{employee_id}/bank-details` |
| 40 | Update Bank Detail | PATCH | `/employees/{employee_id}/bank-details/{bank_detail_id}` |
| 41 | Delete Bank Detail | DELETE | `/employees/{employee_id}/bank-details/{bank_detail_id}` (soft) |

Business rule: at most one `is_primary=true` per employee (§9). `ifsc_code`/`account_number` format validated
at the app layer.

### 8.2 Emergency Contacts (`/employees/{employee_id}/emergency-contacts`) — `employee_emergency_contacts`
Fields: `contact_country_code` (≤5, default `+91`), `contact_number` (req ≤20), `contact_person_name`
(req ≤200), `relation` (≤100), `address`, `is_deleted`.

| # | Endpoint | Method | URL |
|---|---|---|---|
| 42 | List Emergency Contacts | GET | `/employees/{employee_id}/emergency-contacts` |
| 43 | Add Emergency Contact | POST | `/employees/{employee_id}/emergency-contacts` |
| 44 | Update Emergency Contact | PATCH | `.../emergency-contacts/{emergency_contact_id}` |
| 45 | Delete Emergency Contact | DELETE | `.../emergency-contacts/{emergency_contact_id}` (soft) |

### 8.3 References (`/employees/{employee_id}/references`) — `employee_references`
Fields: `reference_name` (req ≤200), `reference_country_code` (≤5, default `+91`), `reference_contact_number`
(req ≤20), `sort_order` (smallint, default 1), `is_deleted`.

| # | Endpoint | Method | URL |
|---|---|---|---|
| 46 | List References | GET | `/employees/{employee_id}/references` |
| 47 | Add Reference | POST | `/employees/{employee_id}/references` |
| 48 | Update Reference | PATCH | `.../references/{reference_id}` |
| 49 | Delete Reference | DELETE | `.../references/{reference_id}` (soft) |

### 8.4 Tags (`/employees/{employee_id}/tags`) — `employee_tags`
Fields: `tag_label` (req ≤100), `tag_color` (≤10), `is_status_tag` (bool, default false), `created_by`.
**No `is_deleted`** → tags are hard-deleted.

| # | Endpoint | Method | URL |
|---|---|---|---|
| 50 | List Tags | GET | `/employees/{employee_id}/tags` |
| 51 | Add Tag | POST | `/employees/{employee_id}/tags` |
| 52 | Delete Tag | DELETE | `/employees/{employee_id}/tags/{tag_id}` (hard delete) |

### 8.5 Status History (`/employees/{employee_id}/status-history`) — `employee_status_history` (read-only)
Append-only; written by Activate/Deactivate/Terminate. Fields: `previous_status`, `new_status`
(CHECK `active|inactive|terminated`), `changed_by`, `reason`, `effective_date`, `created_at`.

| # | Endpoint | Method | URL | Permission |
|---|---|---|---|---|
| 53 | List Status History | GET | `/employees/{employee_id}/status-history` | `employee:read` |

`200` → chronological history rows. No create/update/delete (system-maintained).

Common errors for §8: `404 EMPLOYEE_NOT_FOUND`, `404 <RECORD>_NOT_FOUND`, `422`.

---

## 9. Business Rules

- **Tenant isolation:** all branch/dept/designation/employee operations are scoped to the caller's `org_id`;
  cross-org access returns `404` within scope. Organization endpoints are platform/super-admin.
- **Data scope:** employee/branch reads filtered by `user_branch_access`/`user_department_access` (super
  admin exempt).
- **Uniqueness:** `org_code` global; `employee_code`, `dept_name`, `designation_name` unique per org among
  non-deleted rows (partial unique indexes).
- **Referential guards:** cannot deactivate/soft-delete a branch/department/designation still referenced by
  active (non-deleted) employees (`*_IN_USE`).
- **Status lifecycle:** `active ↔ inactive`, and `→ terminated` (terminal); every transition writes
  `employee_status_history`. Terminate sets `date_of_leaving`.
- **Transfer/Promote:** update the relevant FK(s); context (reason/effective_date) is captured only in the
  Activity Log (no dedicated history table).
- **Bank details:** at most one primary account per employee.
- **Documents:** enforce content-type/size from config; server-generated storage keys; original filename kept
  as metadata only.
- **`employee_type`** is free-text (no DB CHECK); any app-level allowlist is a business decision (§11 Q5).

---

## 10. Validation Rules (schema-derived summary)

| Entity | Field | Rule |
|---|---|---|
| Organization | `org_code` | req, ≤20, globally unique |
| Organization | `org_name` | req, ≤200 |
| Organization | `contact_email` | ≤150, valid email |
| Branch | `branch_name` | req, ≤200 |
| Branch | `latitude`/`longitude` | Numeric(10,7); lat −90..90, lng −180..180 |
| Branch | `allowed_radius_meters` | smallint > 0 |
| Department | `dept_name` | req, ≤150, unique/org (non-deleted) |
| Designation | `designation_name` | req, ≤150, unique/org (non-deleted) |
| Employee | `employee_code` | req, ≤30, unique/org (non-deleted) |
| Employee | `employee_name` | req, ≤200 |
| Employee | `mobile_number` (+`mobile_country_code`) | req, ≤20 (+≤5) |
| Employee | `gender` | req, ∈ `Male,Female,Other` |
| Employee | `salary_type` | ∈ `Monthly,Hourly,Compliance` (if present) |
| Employee | `employment_status` | ∈ `active,inactive,terminated` (via lifecycle endpoints) |
| Employee | `master_branch_id`/`dept_id`/`designation_id` | req, exist & active in caller's org |
| Employee | `monthly_salary` | ≥ 0 |
| Document | `document_type` | ∈ `aadhar_card,driving_licence,pan_card,passport_photo,other` |
| Emergency contact | `contact_number`,`contact_person_name` | required |
| Reference | `reference_name`,`reference_contact_number` | required |
| Tag | `tag_label` | req, ≤100 |

Invalid filter/sort/pagination params → `422`.

---

## 11. Permission Matrix

| Feature key | create | read | edit | delete |
|---|---|---|---|---|
| `organization` (super-admin) | Create Org | List/Get Org | Update, Activate/Deactivate | *(not exposed)* |
| `branch` | Create Branch | List/Get Branch | Update, Activate/Deactivate | *(soft via edit)* |
| `department` | Create Dept | List/Get Dept | Update, Activate/Deactivate | *(soft via edit)* |
| `designation` | Create Desig | List/Get Desig | Update, Activate/Deactivate | *(soft via edit)* |
| `employee` | Create Employee | List/Get, sub-records read, documents read, status history | Update, Activate/Deactivate/Terminate/Transfer/Promote, sub-record & document mutations | Delete Employee (if enabled, §11 Q6) |

Super admins bypass feature checks; tenant isolation always applies.

---

## 12. Error Handling

Standard error envelope via `core/exceptions/handlers.py`. Module error codes (proposed, to be registered in
`employee/exceptions.py`): `ORG_NOT_FOUND`(404), `ORG_CODE_EXISTS`(409), `BRANCH_NOT_FOUND`(404),
`BRANCH_IN_USE`(409), `DEPARTMENT_NOT_FOUND`(404), `DEPARTMENT_NAME_EXISTS`(409), `DEPARTMENT_IN_USE`(409),
`DESIGNATION_NOT_FOUND`(404), `DESIGNATION_NAME_EXISTS`(409), `DESIGNATION_IN_USE`(409),
`EMPLOYEE_NOT_FOUND`(404), `EMPLOYEE_CODE_EXISTS`(409), `EMPLOYEE_ALREADY_TERMINATED`(409),
`DOCUMENT_NOT_FOUND`(404), `BANK_DETAIL_NOT_FOUND`(404), `EMERGENCY_CONTACT_NOT_FOUND`(404),
`REFERENCE_NOT_FOUND`(404), `TAG_NOT_FOUND`(404), `VALIDATION_ERROR`(422), plus shared
`AUTH_NOT_AUTHENTICATED`(401)/`AUTH_FORBIDDEN`(403). Audit: all mutations recorded in the Activity Log
(actor, org, before/after where applicable); PII/secrets redacted in application logs.

---

## 13. Open Questions

1. **Reporting manager / hierarchy (Q1).** No `reporting_manager_id`/hierarchy exists in the schema.
   "Update Reporting Manager" and reporting hierarchy are **omitted**; they require a new column/table before
   they can be contracted. Confirm whether this is planned.
2. **Organization delete (Q2).** Tenant deletion is a platform concern; `DELETE /organizations/{id}` is not
   exposed (only `is_deleted` exists). Confirm the intended tenant-deprovisioning flow.
3. **Transfer/Promotion history (Q3).** Only status changes have a history table
   (`employee_status_history`). Transfer (branch/dept) and Promote (designation) changes are captured only in
   the Activity Log. Confirm whether a dedicated transfer/promotion history is required (would need schema).
4. **`payroll_group_id` ownership (Q4).** It is a column on `employees` but references the Payroll module.
   This contract exposes it as an optional field on create/update; confirm whether payroll-group assignment
   should instead be owned by the Payroll module's API.
5. **Feature-key catalog & `employee_type` values (Q5).** `permissions.py` is a stub; confirm the feature
   keys (`organization/branch/department/designation/employee`). `employee_type` has no DB CHECK — confirm
   the allowed values (if any) for app-level validation.
6. **Employee soft-delete endpoint (Q6).** `employees.is_deleted` supports soft delete, but "Delete Employee"
   was not in the requested list. Confirm whether to expose `DELETE /employees/{id}`.
7. **Envelope key names (Q7).** `shared/schemas/response.py` is a stub; final envelope field names must match
   once implemented (same open item as prior contracts).
