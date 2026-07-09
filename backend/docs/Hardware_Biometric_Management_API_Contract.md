# Hardware / Biometric Management API Contract

> Module: `app/modules/hardware`
> API Version: `v1` — all routes under `API_V1_PREFIX` (`/api/v1`).
> Status: **Contract only** (no FastAPI/SQLAlchemy/Pydantic/service/repository code).
> Sources of truth: `docs/architecture.md` (Backend Architecture), migration `0012_hardware_biometric_devices`
> (+ `0013`, `0016`), the hardware model (`hardware/models.py`), `hardware/constants.py`, and the approved
> Authentication, RBAC, Employee, Attendance, and prior API Contracts.

> **IMPORTANT — scope (per approved decision).** This module owns a **single registry table**
> (`biometric_devices`) and, per its own model docstring, contains **"no ADMS/eSSL communication, sync, or
> device logic."** This contract therefore covers **device registry, configuration, branch assignment,
> enable/disable, and status/health reads + a heartbeat write** only. Features with **no backing tables** —
> Sync History / Failed Sync / Retry, Connection History, Attendance Import (logs/history/validate), Device
> Commands (restart/refresh/test), Diagnostics, and Storage Status — are **not** contracted here (see §10).
> Actual device I/O and attendance-log ingestion produce **attendance punches** owned by the **Attendance**
> module and are **not** duplicated here.

**Excludes** Authentication, RBAC, Employee, Shift, Attendance, Leave, Approval, Payroll, Settlements,
Notifications, Settings, Dashboard, Reports.

---

## 1. Module Overview

### Purpose
Maintain the master registry of ADMS-compatible biometric attendance devices (identity, network, ADMS config,
status, health/stats), so other modules (Attendance punches, Employee biometrics, org attendance settings) can
reference a physical device.

### Responsibilities
- Device registry CRUD (`biometric_devices`).
- Device configuration (network + ADMS fields), branch assignment, enable/disable (`is_active`).
- Status/connectivity/health **reads** + a **heartbeat/status write** (updates the device row; no history).

### Dependencies
| Dependency | Location / Module | Used for |
|---|---|---|
| Auth/permission deps | `core/dependencies/auth.py` | `current_user`, `current_org`, `require_permission` |
| Tenant middleware | `core/middleware/tenant.py` | `org_id` scoping |
| RBAC data scope | `rbac` | branch access filters device lists |
| Employee (read) | `employee` | `branches` for assignment; `employee_biometrics.device_id` references devices |
| Attendance (read) | `attendance` | `attendance_punches.device_id` references devices; sync/ingest is Attendance's, not here |
| Response/pagination schemas | `shared/schemas/` | envelope + paginated lists |
| Activity Log (audit) | `audit` | records device create/update/enable/disable/config changes |

**Table owned:** `biometric_devices` (only). It is the FK target of `employee_biometrics.device_id`,
`org_attendance_settings.device_id`, and `attendance_punches.device_id`.

### Module boundaries
- Registry only. There is **no** sync/import/command/history schema and **no** device-communication logic in
  this module. The heartbeat endpoint updates the single device row (no log). Real device polling, ADMS
  ingestion, and punch creation belong to the integration/Attendance layer.
- `org_id`→organizations (RESTRICT), `branch_id`→branches (SET NULL), `created_by`/`updated_by`→users
  (SET NULL) are **enforced** FKs.

---

## 2. Authorization Model

Two-layer RBAC: feature permission (CRUD on `feature_key`) × data scope (branch access). Super admins bypass
feature checks; tenant isolation (`org_id`) always applies. All endpoints require
`Authorization: Bearer <access_token>`.

**Proposed feature key** (register in `core/security/permissions.py` — §10 Q4): `device`
(`create`/`read`/`edit`/`delete`). Device lists are branch-data-scoped. The **heartbeat** write requires
`device:edit` **or** a dedicated device-agent credential (§10 Q3).

---

## 3. Request & Response Standards

Reuses the shared envelope + pagination (`data`/`error`/`meta.request_id`; `data.items`+`page`+`page_size`+
`total`). BIGINT integer IDs; timezone-aware timestamps; `ip_address` as text (INET); empty lists →
`items: []`.

**Secrets:** `communication_key` and `sync_key` are **never returned** in any response (write-only).

### Pagination / Filtering / Sorting
`page` (≥1, default 1), `page_size` (bounded). Filter/sort allowlists; invalid field → `422`. Repository
applies `org_id` + branch data scope before optional filters.

**Enumerations (DB CHECK):** `status` ∈ `online, offline, disabled, maintenance` (default `offline`);
`protocol` ∈ `tcp_ip, adms, usb` (default `tcp_ip`). `port`/`adms_port` ∈ 1–65535; device stats ≥ 0.

Common omitted errors (all protected endpoints): `401 AUTH_NOT_AUTHENTICATED`, `403 AUTH_FORBIDDEN`,
`422 VALIDATION_ERROR`.

---

## 4. Device Management (`/api/v1/devices`) — feature key `device`

`biometric_devices` fields: **Identity** `device_name` (≤150), `device_code` (≤50, **unique per org**),
`serial_number` (≤100, **globally unique**), `model`, `manufacturer`; **Network** `ip_address` (INET),
`port` (1–65535), `protocol` (CHECK), `domain` (≤255), `mac_address` (≤17); **ADMS** `adms_enabled`,
`adms_server`, `adms_port`, `cloud_id`, `communication_key`✱, `sync_key`✱, `timezone`; **Status**
`status` (CHECK), `last_seen_at`, `last_sync_at`, `firmware_version`, `software_version`; **Stats**
`total_users`, `total_fingerprints`, `total_faces`, `total_cards`, `total_logs`; **Location**
`installation_location`, `remarks`; **Audit** `is_active`, `org_id`, `branch_id`, `created_by`/`updated_by`.
✱ write-only secrets.

| # | Endpoint | Method | URL | Permission |
|---|---|---|---|---|
| 1 | Register Device | POST | `/devices` | `device:create` |
| 2 | List / Search Devices | GET | `/devices` | `device:read` |
| 3 | Get Device Details | GET | `/devices/{device_id}` | `device:read` |
| 4 | Update Device | PATCH | `/devices/{device_id}` | `device:edit` |
| 5 | Delete Device | DELETE | `/devices/{device_id}` | `device:delete` |

- **1. Register** — `{ "device_name", "device_code", "serial_number", "model"?, "manufacturer"?, "branch_id"?, network+ADMS fields?, "installation_location"?, "remarks"? }`.
  **Validation:** `device_name`/`device_code`/`serial_number` required; `serial_number` globally unique
  (`409 DEVICE_SERIAL_EXISTS`); `device_code` unique per org (`409 DEVICE_CODE_EXISTS`); `protocol` ∈ CHECK;
  `port`/`adms_port` 1–65535; `branch_id` (if set) must belong to the caller's org. `status` defaults
  `offline`; `is_active` defaults true. `201` (secrets not echoed).
- **2. List / Search** — filters `search` (name/code/serial), `status` (→ **Online/Offline devices**),
  `protocol`, `branch_id`, `is_active`, `adms_enabled`; sort `device_name`/`created_at`/`last_seen_at`.
  Branch-data-scoped. `200` paginated.
- **3. Get** — `200` → full device (secrets redacted). `404 DEVICE_NOT_FOUND`.
- **4. Update** — editable identity/network/location fields; uniqueness re-checked on `device_code`/
  `serial_number`. `updated_by=caller`. `200`.
- **5. Delete** — hard delete; **blocked if referenced** by `attendance_punches`, `employee_biometrics`, or
  `org_attendance_settings` → `409 DEVICE_IN_USE`. Prefer **Disable** (§5) for retiring a device. `204`.

---

## 5. Device Configuration (`/api/v1/devices/{device_id}`) — feature key `device`

| # | Endpoint | Method | URL | Permission |
|---|---|---|---|---|
| 6 | Get Device Configuration | GET | `/devices/{device_id}/configuration` | `device:read` |
| 7 | Update Device Configuration | PATCH | `/devices/{device_id}/configuration` | `device:edit` |
| 8 | Assign Device to Branch | PUT | `/devices/{device_id}/branch` | `device:edit` |
| 9 | Enable Device | POST | `/devices/{device_id}/enable` | `device:edit` |
| 10 | Disable Device | POST | `/devices/{device_id}/disable` | `device:edit` |

- **6. Get Configuration** — network (`ip_address`, `port`, `protocol`, `domain`, `mac_address`) + ADMS
  (`adms_enabled`, `adms_server`, `adms_port`, `cloud_id`, `timezone`) + whether keys are set (booleans, not
  the secret values). `200`.
- **7. Update Configuration** — the same network/ADMS fields, plus `communication_key`/`sync_key`
  (write-only). `protocol` ∈ CHECK; ports 1–65535. `200`.
- **8. Assign to Branch** — `{ "branch_id": <int|null> }`; branch must be in the caller's org; `null`
  unassigns. `200`; `404 BRANCH_NOT_FOUND`.
- **9/10. Enable / Disable** — toggle **`is_active`** (administrative). Disabling does not delete or change
  connectivity `status`. `200` (idempotent).
- **Assign to Organization:** `org_id` is fixed at registration (org = tenant); there is **no cross-org
  reassignment** endpoint (§10 Q2).

---

## 6. Device Connectivity & Status (`/api/v1/devices`) — feature key `device`

| # | Endpoint | Method | URL | Permission |
|---|---|---|---|---|
| 11 | Check Device Status / Connectivity | GET | `/devices/{device_id}/status` | `device:read` |
| 12 | Device Heartbeat / Status Report | PUT | `/devices/{device_id}/heartbeat` | `device:edit` (or device-agent) |

- **11. Status** — `200` → `{ status, last_seen_at, last_sync_at, is_active }` (includes **Last Sync Time** and
  last communication). **Online/Offline device lists** are `GET /devices?status=online|offline` (§4.2).
- **12. Heartbeat / Status Report** — a device agent/integration worker reports in:
  `{ "status"?, "last_seen_at"?, "last_sync_at"?, "firmware_version"?, "software_version"?, "total_users"?, "total_fingerprints"?, "total_faces"?, "total_cards"?, "total_logs"? }`.
  Updates the device row **only** (no history log). `status` ∈ CHECK; stats ≥ 0. `200`.
- **Connection History** is **not supported** (no history table — only the single `last_seen_at`); see §10.

---

## 7. Device Health (`/api/v1/devices/{device_id}/health`) — feature key `device` (read)

| # | Endpoint | Method | URL | Permission |
|---|---|---|---|---|
| 13 | Device Health Status | GET | `/devices/{device_id}/health` | `device:read` |

- `200` → `{ status, is_active, firmware_version, software_version, last_seen_at, last_sync_at,
  stats: { total_users, total_fingerprints, total_faces, total_cards, total_logs } }`.
- **Storage Status** (no storage-capacity column) and **Device Diagnostics** (no diagnostics table) are
  **not supported** (§10). **Firmware Version** and **Last Communication** are the fields above.

---

## 8. Business Rules (summary)

- **Tenant isolation:** all operations scoped to `org_id`; device lists branch-data-scoped.
- **Uniqueness:** `serial_number` globally unique; `device_code` unique per org.
- **Validation:** `protocol`/`status` ∈ CHECK sets; `port`/`adms_port` 1–65535; stats ≥ 0.
- **Enable/Disable** via `is_active` (administrative); connectivity `status` is separate and set by
  heartbeat/integration.
- **Delete** blocked while referenced by punches/employee-biometrics/org-attendance-settings — use Disable.
- **Branch assignment:** branch must be in the same org; `SET NULL` if the branch is deleted.
- **Secrets** (`communication_key`, `sync_key`) are write-only and never returned.
- **No sync/import/command/history** in this module — device I/O and attendance ingestion belong to the
  integration/Attendance layer.

---

## 9. Permission Matrix

| Feature key | create | read | edit | delete |
|---|---|---|---|---|
| `device` | Register | List/Search, Get, Get config, Status, Health | Update, Update config, Assign branch, Enable, Disable, Heartbeat | Delete (if not referenced) |

Super admins bypass feature checks; tenant isolation always applies; device lists are branch-data-scoped; the
heartbeat write may alternatively use a device-agent credential (§10 Q3).

---

## 10. Error Handling, Security & Open Questions

**Error envelope** via `core/exceptions/handlers.py`. Module error codes (proposed, `hardware/exceptions.py`):
`DEVICE_NOT_FOUND`(404), `DEVICE_SERIAL_EXISTS`(409), `DEVICE_CODE_EXISTS`(409), `DEVICE_IN_USE`(409),
`BRANCH_NOT_FOUND`(404), `INVALID_PORT`(422), `INVALID_STATUS`(422), `VALIDATION_ERROR`(422), plus shared
`AUTH_NOT_AUTHENTICATED`(401)/`AUTH_FORBIDDEN`(403).

**HTTP status codes used:** 200, 201, 204, 400, 401, 403, 404, 409, 422.

**Security considerations:** every route enforces `require_permission` + tenant scope + branch data scope;
`communication_key`/`sync_key` are write-only (never serialized) and redacted in logs; the heartbeat endpoint
must authenticate the reporting agent (device-agent credential or `device:edit`) and validate `device_id`
ownership; device create/update/config/enable/disable recorded in the Activity Log; IP/MAC and network config
returned only to permitted roles; rate limiting on heartbeat and list endpoints.

### Open Questions
1. **Unsupported sections (Q1) — NOT contracted.** Sync History / Failed Sync / Retry, Connection History,
   Attendance Import (logs/history/validate/view), Device Commands (restart/refresh/test/manual-sync), Device
   Diagnostics, and Storage Status have **no backing tables** and the module has no device-communication
   logic. They are omitted. Confirm whether these need new schema + an integration service (out of scope for
   this contract).
2. **Assign to Organization (Q2).** `org_id` is fixed at registration (org = tenant); no cross-org
   reassignment endpoint is exposed. Confirm this is intended.
3. **Heartbeat authentication (Q3).** The heartbeat/status-report write is intended for a device agent or
   integration worker. Confirm the auth mechanism (a dedicated device-agent credential vs an operator holding
   `device:edit`).
4. **Feature-key catalog (Q4).** `permissions.py` is a stub; confirm the single `device` key (vs finer-grained
   `device_config`/`device_status`).
5. **Sync/ingest ownership (Q5).** Triggering a sync and ingesting device logs produce **attendance punches**
   (Attendance module) and update `last_sync_at`; confirm the integration layer that performs this (and that
   it must not duplicate Attendance APIs).
6. **Envelope key names (Q6).** `shared/schemas/response.py` is a stub; final envelope field names must match
   once implemented (same open item as prior contracts).
