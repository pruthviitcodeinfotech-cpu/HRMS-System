# Settings Management API Contract

> Module: `app/modules/settings`
> API Version: `v1` — all routes under `API_V1_PREFIX` (`/api/v1`).
> Status: **Contract only** (no FastAPI/SQLAlchemy/Pydantic/service/repository code).
> Sources of truth: `docs/architecture.md` (Backend Architecture), migration `0011_settings` (+ `0016`),
> the settings model (`settings/models.py`), and the approved prior API Contracts.

Covers the two org-scoped settings tables this module owns — `org_settings` (general/system/org config) and
`org_salary_slip_settings` (payslip settings) — plus a fixed-toggle feature view. **Excludes** Authentication,
RBAC, Employee, Shift, Attendance, Leave, Approval, Payroll, Settlements, Hardware, Notifications, Activity
Log, Dashboard, Reports.

> **Scope note (per approved decisions).** Several requested "settings" live in **other modules** and are
> **already contracted** — not re-exposed here:
> - **Leave Settings** → `leave_settings` (Leave module).
> - **Payroll (calculation) Settings** → `payroll_settings` (Payroll module). Only **payslip** settings
>   (`org_salary_slip_settings`) live here.
> - **Full Attendance Settings** → `org_attendance_settings` (Employee module). Only the
>   `enable_regularization` / `enable_photo_punch` toggles live here (inside `org_settings`).
>
> **Notification Settings** are **unsupported** (no preferences table anywhere) — §8 Q2. **Feature
> Configuration** maps to the **fixed** boolean columns only (no generic feature-flag store) — §8 Q3.
> **Configuration versioning** is **not supported** (no version/history table) — §8 Q4.

---

## 1. Module Overview

### Purpose
Manage the organization's single configuration row (`org_settings`) and payslip settings
(`org_salary_slip_settings`), both **one row per org**.

### Responsibilities
- `org_settings`: shift/attendance/hardware/org toggles + device sync time + org sync/pass codes.
- `org_salary_slip_settings`: company branding + payslip release/branch-wise toggles.
- A fixed-toggle "features" view over the boolean columns of both tables.

### Dependencies
| Dependency | Location / Module | Used for |
|---|---|---|
| Auth/permission deps | `core/dependencies/auth.py` | `current_user`, `current_org`, `require_permission` |
| Tenant middleware | `core/middleware/tenant.py` | `org_id` scoping |
| RBAC | `rbac` | `settings` feature permission |
| Users (read) | `rbac` (`users`) | `updated_by` |
| Storage | `infrastructure/storage/` | `company_logo_url` upload |
| Activity Log (audit) | `audit` | records settings changes (change history — no in-module version table) |
| Cross-module settings (referenced only) | `leave` (`leave_settings`), `payroll` (`payroll_settings`), `employee` (`org_attendance_settings`) | pointers; managed by those modules |

**Tables owned:** `org_settings`, `org_salary_slip_settings`. Both `UNIQUE(org_id)` (exactly one row per org).

### Module boundaries
- Owns only the two tables above. Does **not** manage leave/payroll-calculation/full-attendance settings
  (other modules). FKs: `org_id`→organizations (RESTRICT), `updated_by`→users (SET NULL) — both enforced.

---

## 2. Authorization Model

Feature permission × tenant scope. Super admins bypass; tenant isolation (`org_id`) always applies. All
endpoints require `Authorization: Bearer <access_token>`.

**Proposed feature key** (register in `core/security/permissions.py` — §8 Q5): `settings`
(`read` for gets/view; `edit` for update/reset/feature-toggle). Org settings are administrative — typically
restricted to org-admin/super-admin.

---

## 3. Request & Response Standards

Reuses the shared envelope (`data`/`error`/`meta.request_id`). BIGINT integer IDs; `device_sync_time` as
`HH:MM[:SS]`; timezone-aware `created_at`/`updated_at`. No pagination (single-row resources).

**Secrets:** `pass_code` (device pairing) is sensitive — masked/omitted in responses (returned only to
permitted roles; never logged). `sync_code` is treated as sensitive config.

Common omitted errors: `401 AUTH_NOT_AUTHENTICATED`, `403 AUTH_FORBIDDEN`, `422 VALIDATION_ERROR`.

---

## 4. Organization / System Settings (`/api/v1/settings/organization`) — feature key `settings`

`org_settings` fields (one per org): `advance_shift_enabled` (bool), `enable_regularization` (bool),
`enable_photo_punch` (bool), `device_sync_time` (Time, default `16:51:00`), `sync_code` (≤50, required),
`pass_code` (≤20, required, sensitive), `updated_by`, `created_at`, `updated_at`.

| # | Endpoint | Method | URL | Permission |
|---|---|---|---|---|
| 1 | View Configuration (combined) | GET | `/settings` | `settings:read` |
| 2 | Get Organization / System Settings | GET | `/settings/organization` | `settings:read` |
| 3 | Update Organization / System Settings | PATCH | `/settings/organization` | `settings:edit` |
| 4 | Reset Organization Settings | POST | `/settings/organization/reset` | `settings:edit` |

- **1. View Configuration** — `200` → both owned settings blocks (`organization` + `salary_slip`) plus
  read-only **pointers** to cross-module settings (leave/payroll/attendance) indicating their owning module.
- **2. Get** — `200` → the org_settings row (`pass_code` masked). Auto-creates defaults on first read if
  absent, or `404 SETTINGS_NOT_FOUND` (implementation choice — §8 Q1).
- **3. Update** — PATCH any field; **upsert** the single org row; `updated_by=caller`. **Validation:**
  `sync_code` ≤50 required; `pass_code` ≤20 required; `device_sync_time` valid; booleans typed. `200`.
- **4. Reset** — re-applies schema **defaults** to the toggle/time fields (`advance_shift_enabled=false`,
  `enable_regularization=false`, `enable_photo_punch=false`, `device_sync_time='16:51:00'`); `sync_code`/
  `pass_code` are **not** reset (no defaults — required values). `200`. (Reset is a re-apply operation; there
  is no snapshot/rollback — §8 Q4.)

> **"Attendance Settings"** requested by the task maps to the `enable_regularization` / `enable_photo_punch`
> fields of this resource. Full attendance configuration is owned by the Employee module
> (`org_attendance_settings`) and is not managed here.

---

## 5. Salary-Slip (Payslip) Settings (`/api/v1/settings/salary-slip`) — feature key `settings`

`org_salary_slip_settings` fields (one per org): `company_logo_url` (text), `company_name` (≤200, required),
`company_address` (text, required), `company_contact` (≤100, required), `company_website_email` (≤200),
`auto_release_payslip` (bool, default true), `branch_wise_payslip` (bool, default false), `updated_by`,
timestamps.

| # | Endpoint | Method | URL | Permission |
|---|---|---|---|---|
| 5 | Get Salary-Slip Settings | GET | `/settings/salary-slip` | `settings:read` |
| 6 | Update Salary-Slip Settings | PATCH | `/settings/salary-slip` | `settings:edit` |

- **5. Get** — `200` → the row. `404 SETTINGS_NOT_FOUND` (or defaults).
- **6. Update** — PATCH/upsert; `updated_by=caller`. **Validation:** `company_name`/`company_address`/
  `company_contact` required; `company_website_email` valid email if present; `company_logo_url` from the
  storage upload flow; booleans typed. `200`.

> This is the **payslip** portion of "Payroll Settings" the module owns; payroll **calculation** settings are
> owned by the Payroll module (`payroll_settings`).

---

## 6. Feature Configuration (`/api/v1/settings/features`) — feature key `settings`

Maps to the **fixed** boolean columns across the two owned tables (no dynamic feature-flag store).

| # | Endpoint | Method | URL | Permission |
|---|---|---|---|---|
| 7 | View Enabled Features | GET | `/settings/features` | `settings:read` |
| 8 | Enable / Disable Feature | PATCH | `/settings/features/{feature_key}` | `settings:edit` |

- **Feature keys (fixed):** `advance_shift_enabled`, `enable_regularization`, `enable_photo_punch`
  (from `org_settings`); `auto_release_payslip`, `branch_wise_payslip` (from `org_salary_slip_settings`).
- **7. View** — `200` → `{ feature_key: boolean }` for all fixed features.
- **8. Enable/Disable** — `{ "enabled": true|false }` sets the corresponding boolean column. `feature_key`
  must be in the fixed set → `404 UNKNOWN_FEATURE` otherwise. `200`.

> There is **no** generic/dynamic feature-flag table — only these known toggles (§8 Q3).

---

## 7. Business Rules, Security & Permission Matrix

### Business Rules
- **One row per org** (`UNIQUE(org_id)`); updates **upsert** the single row per resource.
- **Reset** re-applies defaults to toggle/time fields only (required codes untouched); no version snapshot.
- **Change history**: only `updated_by`/`updated_at` on the row; full change history is in the **Activity
  Log** module (no settings-version table here).
- Cross-module settings (leave/payroll/attendance) are referenced (pointers in View Configuration) but
  managed by their own modules.

### Security Considerations
- `settings:edit` restricted to org-admin/super-admin; tenant-scoped. `pass_code` (and `sync_code`) are
  sensitive — masked in responses, never logged; only permitted roles may read `pass_code`. All changes
  recorded in the Activity Log (actor, before/after). Company logo upload validated via the storage flow.

### Permission Matrix
| Feature key | read | edit |
|---|---|---|
| `settings` | View Configuration, Get org settings, Get salary-slip settings, View features | Update org settings, Reset, Update salary-slip settings, Enable/Disable feature |

Super admins bypass feature checks; tenant isolation always applies.

### Error Handling
Module error codes (proposed, `settings/exceptions.py`): `SETTINGS_NOT_FOUND`(404), `UNKNOWN_FEATURE`(404),
`VALIDATION_ERROR`(422), plus shared `AUTH_NOT_AUTHENTICATED`(401)/`AUTH_FORBIDDEN`(403). **Status codes:**
200, 400, 401, 403, 404, 422.

---

## 8. Open Questions

1. **First-read behavior (Q1).** On the first GET with no row yet — auto-create defaults vs return
   `404 SETTINGS_NOT_FOUND`. Note `sync_code`/`pass_code`/`company_*` are required with no defaults, so a full
   auto-create may not be possible; confirm the bootstrap flow (likely created at org provisioning).
2. **Notification Settings (Q2) — NOT supported.** No notification-preferences table exists (the Notifications
   module keeps preferences out of the DB). Omitted. Confirm whether notification preferences are planned
   (needs new schema).
3. **Feature Configuration (Q3).** Mapped to the fixed boolean columns; there is no generic feature-flag
   store. Confirm this is acceptable (else a `feature_flags` table would be needed).
4. **Reset & Versioning (Q4).** Reset re-applies defaults (no snapshot/rollback); configuration versioning is
   unsupported (no version/history table — changes are tracked via `updated_by`/`updated_at` + Activity Log).
   Confirm whether settings versioning is required.
5. **Feature-key catalog (Q5).** `permissions.py` is a stub; confirm the single `settings` key.
6. **Cross-module settings placement (Q6).** Leave/Payroll-calculation/full-Attendance settings remain in
   their own modules (already contracted); confirm they should not be surfaced via Settings.
7. **Envelope key names (Q7).** `shared/schemas/response.py` is a stub; final envelope field names must match
   once implemented (same open item as prior contracts).
