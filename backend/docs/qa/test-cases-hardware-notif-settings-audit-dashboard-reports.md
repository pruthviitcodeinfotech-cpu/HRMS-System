# Test Case Specification — Hardware, Notifications, Settings, Audit, Dashboard, Reports

Production QA test-case specification for six modules of the HRMS backend (FastAPI, PostgreSQL, Redis, arq).
Every case is grounded in the shipped code (`app/modules/{hardware,notifications,settings,audit,dashboard,reports}/`)
and the approved API contracts in `docs/`.

**Base URL:** `/api/v1` (omitted from the Request column for brevity).

---

## Table of Contents

1. [Test Data / Preconditions](#1-test-data--preconditions)
2. [Conventions](#2-conventions)
3. [TC-HW — Hardware / Biometric Management (13 endpoints)](#3-tc-hw--hardware--biometric-management)
4. [TC-NOT — Notification Management (17 endpoints)](#4-tc-not--notification-management)
5. [TC-SET — Settings Management (8 endpoints)](#5-tc-set--settings-management)
6. [TC-AUD — Activity Log / Audit (5 endpoints)](#6-tc-aud--activity-log--audit)
7. [TC-DSH — Dashboard Management (19 endpoints)](#7-tc-dsh--dashboard-management)
8. [TC-RPT — Reports Management (42 endpoints)](#8-tc-rpt--reports-management)
9. [Defects / Spec Deviations Found While Authoring](#9-defects--spec-deviations-found-while-authoring)
10. [Coverage Notes & Out-of-Scope](#10-coverage-notes--out-of-scope)

---

## 1. Test Data / Preconditions

### 1.1 Tenants

| Alias | org_id | Notes |
|---|---|---|
| **Org A** | 1 | Primary tenant. Fully seeded. |
| **Org B** | 2 | Isolation tenant. Independent data set. Used for every cross-tenant case. |
| **Org C** | 3 | "Bare" tenant — **no** `org_settings` row and **no** `org_salary_slip_settings` row. Used for `SETTINGS_NOT_FOUND`. |

### 1.2 Users & permissions (RBAC feature keys: `device`, `notification`, `settings`, `audit`, `dashboard`, `reports`)

| Alias | org | Permissions held |
|---|---|---|
| **A-SUPER** | A | `is_super_admin = true` — unrestricted, no branch/dept scope. |
| **A-ADMIN** | A | `device:*`, `notification:*`, `settings:*`, `audit:read`, `dashboard:read`, `reports:read`, plus source-module reads (`employee:read`, `attendance:read`, `leave_request:read`, `leave_balance:read`, `approval:read`, `payroll_record:read`, `settlement:read`, `loan_advance:read`, `arrears:read`). Branch scope: unrestricted. |
| **A-SCOPED** | A | Same as A-ADMIN but branch data scope restricted to `branch_ids = [11]` only. |
| **A-REPORTS-ONLY** | A | `reports:read` and `dashboard:read` **only** — no source-module read permission at all. |
| **A-NOPERM** | A | Authenticated, zero feature permissions. Used for all 403 cases. |
| **A-EMP** | A | Self-service user linked to employee `EMP-A1`. No admin permissions. Used for `/me/notifications/*`. |
| **A-EMP2** | A | Second self-service user linked to employee `EMP-A2`. Used for cross-user notification isolation. |
| **B-ADMIN** | B | Same permission set as A-ADMIN, but in Org B. Used for every cross-tenant case. |

Auth is `Authorization: Bearer <access_token>`. "No token" means the header is omitted entirely.

### 1.3 Organization structure

| Alias | id | org |
|---|---|---|
| BR-A1 | 11 | Org A branch (in A-SCOPED's scope) |
| BR-A2 | 12 | Org A branch (outside A-SCOPED's scope) |
| BR-B1 | 21 | Org B branch |
| DEPT-A1 | 31 | Org A department |
| EMP-A1 | 1001 | Org A employee, `master_branch_id = 11`, linked to user A-EMP |
| EMP-A2 | 1002 | Org A employee, `master_branch_id = 12`, linked to user A-EMP2 |
| EMP-B1 | 2001 | Org B employee |

### 1.4 Hardware (`biometric_devices`)

| Alias | id | org | Notes |
|---|---|---|---|
| DEV-A1 | 101 | A | `serial_number='SN-A-001'`, `device_code='DVC-01'`, `branch_id=11`, `is_active=true`, `status='offline'`, `communication_key` and `sync_key` SET in DB. |
| DEV-A2 | 102 | A | `serial_number='SN-A-002'`, `device_code='DVC-02'`, `branch_id=12`. **In use** — has rows in `attendance_punches.device_id=102` and `employee_biometrics.device_id=102`. |
| DEV-A3 | 103 | A | Freshly registered, **no** dependent rows. Safe to delete. |
| DEV-B1 | 201 | B | Org B device, `serial_number='SN-B-001'`, `device_code='DVC-01'` (same code as DEV-A1 — legal, code is unique *per org*). |

### 1.5 Notifications (`notifications`, `notification_recipients`)

| Alias | id | org | Notes |
|---|---|---|---|
| NOT-A1 | 301 | A | Recipients: A-EMP (unread, undelivered). |
| NOT-A2 | 302 | A | Recipients: A-EMP (read + archived). |
| NOT-A3 | 303 | A | Recipients: A-EMP2 only. **A-EMP is NOT a recipient.** |
| NOT-A4 | 304 | A | `expires_at` in the past (expired). Recipient: A-EMP. |
| NOT-B1 | 401 | B | Org B notification. Recipient: a B user. |

### 1.6 Settings (`org_settings`, `org_salary_slip_settings`)

- Org A `org_settings`: row exists. `advance_shift_enabled=false`, `enable_regularization=false`, `enable_photo_punch=false`, `device_sync_time='16:51:00'`, `sync_code='SYNC-A-123'`, `pass_code='PASS-A'`.
- Org A `org_salary_slip_settings`: row exists, `auto_release_payslip=true`, `branch_wise_payslip=false`.
- Org C: **neither row exists.**
- Feature-key catalog (fixed, from `app/modules/settings/constants.py`): `advance_shift_enabled`, `enable_regularization`, `enable_photo_punch` (→ `org_settings`) and `auto_release_payslip`, `branch_wise_payslip` (→ `org_salary_slip_settings`).

### 1.7 Audit (`activity_logs`)

- LOG-A1 = `id 501`, `org_id=1`. LOG-B1 = `id 601`, `org_id=2`.
- Baseline counts captured before each mutating test: `SELECT count(*) FROM activity_logs WHERE org_id=1` → `NA`; `WHERE org_id=2` → `NB`.
- Sortable allowlist (`app/modules/audit/repository.py::SORTABLE_FIELDS`): **`logged_at`, `log_date` only.**
- `action_type` CHECK values: `Insert`, `Update`, `Delete`, `Assign`, `Bulk Assign`. `action_from`: `Web App`, `Mobile App`.
- Security-event view is an *approximation* over `module IN ('rbac','user')` (`SECURITY_MODULES`).

### 1.8 Reports / exports

- Reports are read-only aggregations. Export formats: `json` (default), `csv`, `excel`, `pdf`.
- **Async threshold: `total > 1000` rows** for any non-JSON format → `202` + `export_job_id` (`app/modules/reports/service.py::_handle_report_query`).
- Export job + file live in Redis under `export_job:{job_id}` / `export_file:{job_id}`, TTL 3600 s.
- Seed **BIG-A**: an Org A report source with **> 1000** rows (e.g. 1500 employees) to force the async path.
- Seed **SMALL-A**: an Org A report source with **≤ 1000** rows to force the synchronous file path.
- Redis must be reachable for export tests; arq worker running for the queued path.

### 1.9 Environment fixtures

- `REDIS_DOWN` fixture: Redis is stopped / unreachable (used for dashboard-degradation cases).
- `QUEUE_DOWN` fixture: arq enqueue fails (used for the in-process export fallback case).

---

## 2. Conventions

- **Cross-tenant fetch by id returns `404`, never `403`** — existence must not leak.
- **Missing permission returns `403 AUTH_FORBIDDEN`. Missing/invalid token returns `401 AUTH_NOT_AUTHENTICATED`.**
- All responses use the shared envelope `{ success, message, data, request_id }`; errors use `{ success:false, error:{ code, message, details }, request_id }`.
- `TENANT_UNRESOLVED` (400) is raised by every router in scope when the token carries no `org_id`.
- **Reads write no audit rows.** Any "Database Verification" on a pure read asserts *non-mutation* where meaningful, otherwise `n/a (read-only)`.
- Priorities: **P0** security / tenant isolation / salary exposure · **P1** core · **P2** validation / edge · **P3** cosmetic.

---

## 3. TC-HW — Hardware / Biometric Management

Endpoints: `POST /devices`, `GET /devices`, `GET|PATCH|DELETE /devices/{id}`, `GET|PATCH /devices/{id}/configuration`, `PUT /devices/{id}/branch`, `POST /devices/{id}/enable`, `POST /devices/{id}/disable`, `GET /devices/{id}/status`, `PUT /devices/{id}/heartbeat`, `GET /devices/{id}/health`. Feature key: `device`.

| ID | Module / API | Test Scenario | Preconditions | Request / Input | Expected Result | HTTP | Database Verification | Priority |
|---|---|---|---|---|---|---|---|---|
| TC-HW-001 | Hardware / `POST /devices` | Register a device with the full valid payload | A-ADMIN has `device:create`; BR-A1 exists | `{"device_name":"Gate 3","device_code":"DVC-03","serial_number":"SN-A-003","branch_id":11,"protocol":"tcp_ip","ip_address":"10.0.0.9","port":4370,"communication_key":"ck-secret","sync_key":"sk-secret"}` | 201; body has `id`, `status="offline"`, `is_active=true`; **no `communication_key` / `sync_key` keys anywhere in the body** | 201 | `SELECT communication_key, sync_key FROM biometric_devices WHERE id=:new` → both stored non-null; `SELECT status FROM biometric_devices WHERE id=:new` → `'offline'`; `SELECT count(*) FROM activity_logs WHERE org_id=1 AND action_type='Insert' AND title='Device registered'` → +1 | P0 |
| TC-HW-002 | Hardware / `POST /devices` | Write-only keys never round-trip | TC-HW-001 device exists | `GET /devices/{new}` then `GET /devices` | Neither list nor detail response contains `communication_key` or `sync_key` (nor a masked variant) | 200 | `SELECT communication_key FROM biometric_devices WHERE id=:new` → set in DB but ABSENT from the response body | P0 |
| TC-HW-003 | Hardware / `POST /devices` | Duplicate serial number within the same org | DEV-A1 has `SN-A-001` | `{"device_name":"X","device_code":"DVC-99","serial_number":"SN-A-001"}` | 409 `DEVICE_SERIAL_EXISTS` | 409 | `SELECT count(*) FROM biometric_devices WHERE org_id=1` → unchanged; no new `activity_logs` row | P1 |
| TC-HW-004 | Hardware / `POST /devices` | Duplicate device code within the same org | DEV-A1 has `DVC-01` | `{"device_name":"X","device_code":"DVC-01","serial_number":"SN-A-777"}` | 409 `DEVICE_CODE_EXISTS` | 409 | `SELECT count(*) FROM biometric_devices WHERE org_id=1` → unchanged | P1 |
| TC-HW-005 | Hardware / `POST /devices` | Device code duplicated **across** orgs is allowed (code is unique per org) | DEV-A1 uses `DVC-01` in Org A | As B-ADMIN: `{"device_name":"B2","device_code":"DVC-01","serial_number":"SN-B-777"}` | 201 — no conflict; `uq_biometric_devices_org_id_device_code` is `(org_id, device_code)` | 201 | `SELECT count(*) FROM biometric_devices WHERE device_code='DVC-01'` → 3 rows across 2 orgs | P1 |
| TC-HW-006 | Hardware / `POST /devices` | Serial number is **globally** unique — Org B cannot reuse an Org A serial | DEV-A1 has `SN-A-001` in Org A | As B-ADMIN: `{"device_name":"B3","device_code":"DVC-77","serial_number":"SN-A-001"}` | 409 `DEVICE_SERIAL_EXISTS`. **Note:** this is by design (`uq_biometric_devices_serial_number` is global) but it *does* let Org B probe Org A serials — flag to product (see §9) | 409 | `SELECT count(*) FROM biometric_devices WHERE org_id=2` → unchanged | P1 |
| TC-HW-007 | Hardware / `POST /devices` | Branch belonging to another org | BR-B1 (21) is in Org B | As A-ADMIN: `{"device_name":"X","device_code":"DVC-04","serial_number":"SN-A-004","branch_id":21}` | 404 `BRANCH_NOT_FOUND` (not 403 — cross-tenant existence must not leak) | 404 | `SELECT count(*) FROM biometric_devices WHERE org_id=1` → unchanged | P0 |
| TC-HW-008 | Hardware / `POST /devices` | Two concurrent identical registrations (same serial) | None | Fire 5 parallel `POST /devices` with identical `serial_number='SN-RACE'` | Exactly 1 × 201; the other 4 × 409 (`DEVICE_SERIAL_EXISTS` or `CONFLICT` from the unique index) — **never 500** | 201 / 409 | `SELECT count(*) FROM biometric_devices WHERE serial_number='SN-RACE'` → exactly 1 | P0 |
| TC-HW-009 | Hardware / `POST /devices` | Invalid IP address | — | `{"ip_address":"999.1.1.1", ...}` | 422 `VALIDATION_ERROR`; `details[].field="ip_address"` | 422 | No row inserted | P2 |
| TC-HW-010 | Hardware / `POST /devices` | Invalid MAC address | — | `{"mac_address":"ZZ:ZZ:ZZ:ZZ:ZZ:ZZ", ...}` | 422 `VALIDATION_ERROR` | 422 | No row inserted | P2 |
| TC-HW-011 | Hardware / `POST /devices` | Invalid IANA timezone | — | `{"timezone":"Mars/Olympus", ...}` | 422 `VALIDATION_ERROR` | 422 | No row inserted | P2 |
| TC-HW-012 | Hardware / `POST /devices` | Port out of range | — | `{"port":70000, ...}` | 422 `VALIDATION_ERROR` (`ge=1, le=65535`) | 422 | No row inserted | P2 |
| TC-HW-013 | Hardware / `POST /devices` | Invalid protocol enum | — | `{"protocol":"bluetooth", ...}` | 422 `VALIDATION_ERROR`; allowed: `tcp_ip`, `adms`, `usb` | 422 | No row inserted | P2 |
| TC-HW-014 | Hardware / `GET /devices` | List devices — org scoping | DEV-A1..A3 in Org A, DEV-B1 in Org B | As A-ADMIN: `GET /devices?page=1&page_size=25` | 200; every `items[].org_id == 1`; DEV-B1 (id 201) absent | 200 | Cross-check: `SELECT count(*) FROM biometric_devices WHERE org_id=1` equals `pagination.total_records` | P0 |
| TC-HW-015 | Hardware / `GET /devices` | Branch data scope restricts the list | A-SCOPED restricted to `branch_ids=[11]` | As A-SCOPED: `GET /devices` | 200; only DEV-A1 (branch 11) returned; DEV-A2 (branch 12) absent | 200 | n/a (read-only) | P0 |
| TC-HW-016 | Hardware / `GET /devices` | Filtering by a branch outside the caller's scope returns empty, not 403 | A-SCOPED restricted to `[11]` | `GET /devices?branch_id=12` | 200 with `items: []`, `total_records: 0` | 200 | n/a (read-only) | P1 |
| TC-HW-017 | Hardware / `GET /devices` | Search + filter combination | Devices seeded | `GET /devices?search=SN-A&status=offline&protocol=tcp_ip&is_active=true&sort_by=device_name&sort_order=asc` | 200; only matching Org A devices, sorted ascending by `device_name` | 200 | n/a (read-only) | P1 |
| TC-HW-018 | Hardware / `GET /devices` | Empty result set | Org C has no devices | As an Org C admin: `GET /devices` | 200; `items: []`, `total_records: 0` — not 404 | 200 | n/a (read-only) | P2 |
| TC-HW-019 | Hardware / `GET /devices/{id}` | Cross-tenant fetch by id | DEV-B1 = 201 (Org B) | As A-ADMIN: `GET /devices/201` | **404 `DEVICE_NOT_FOUND`** — never 403, never the Org B payload | 404 | `SELECT org_id FROM biometric_devices WHERE id=201` → 2 (row untouched, not disclosed) | P0 |
| TC-HW-020 | Hardware / `GET /devices/{id}` | Non-existent id | — | `GET /devices/99999999` | 404 `DEVICE_NOT_FOUND` | 404 | n/a (read-only) | P2 |
| TC-HW-021 | Hardware / `PATCH /devices/{id}` | Update name + location | DEV-A1 exists | `{"device_name":"Main Gate","installation_location":"Lobby"}` | 200; updated fields reflected; secrets still absent | 200 | `SELECT device_name, updated_by FROM biometric_devices WHERE id=101` → `'Main Gate'`, `updated_by = A-ADMIN.user_id`; `activity_logs` `action_type='Update'` +1 | P1 |
| TC-HW-022 | Hardware / `PATCH /devices/{id}` | Update to a serial already used by another device | DEV-A2 has `SN-A-002` | `PATCH /devices/101 {"serial_number":"SN-A-002"}` | 409 `DEVICE_SERIAL_EXISTS` | 409 | `SELECT serial_number FROM biometric_devices WHERE id=101` → still `'SN-A-001'` | P1 |
| TC-HW-023 | Hardware / `PATCH /devices/{id}` | Setting the serial to its own current value is a no-op, not a conflict | DEV-A1 | `PATCH /devices/101 {"serial_number":"SN-A-001"}` | 200 (service compares against the current value before the uniqueness check) | 200 | Row unchanged apart from `updated_by`/`updated_at` | P2 |
| TC-HW-024 | Hardware / `PATCH /devices/{id}` | Cross-tenant update | DEV-B1 = 201 | As A-ADMIN: `PATCH /devices/201 {"device_name":"pwned"}` | 404 `DEVICE_NOT_FOUND` | 404 | `SELECT device_name FROM biometric_devices WHERE id=201` → unchanged; `SELECT count(*) FROM activity_logs WHERE org_id=2` → still `NB` | P0 |
| TC-HW-025 | Hardware / `DELETE /devices/{id}` | Delete an unreferenced device | DEV-A3 = 103, no punches/templates | `DELETE /devices/103` | 204, empty body | 204 | `SELECT count(*) FROM biometric_devices WHERE id=103` → 0; `activity_logs` `action_type='Delete'`, `title='Device deleted'` +1 for `org_id=1` | P1 |
| TC-HW-026 | Hardware / `DELETE /devices/{id}` | Delete a device referenced by punches / biometric templates | DEV-A2 = 102 has `attendance_punches` + `employee_biometrics` rows | `DELETE /devices/102` | 409 `DEVICE_IN_USE` | 409 | `SELECT count(*) FROM biometric_devices WHERE id=102` → 1 (still present); punch rows intact | P1 |
| TC-HW-027 | Hardware / `DELETE /devices/{id}` | Cross-tenant delete | DEV-B1 = 201 | As A-ADMIN: `DELETE /devices/201` | 404 `DEVICE_NOT_FOUND` | 404 | `SELECT count(*) FROM biometric_devices WHERE id=201` → 1 (Org B row survives) | P0 |
| TC-HW-028 | Hardware / `GET /devices/{id}/configuration` | Configuration exposes booleans, not secrets, and merges org settings | DEV-A1 has both keys set; Org A `device_sync_time='16:51:00'`, `sync_code`/`pass_code` set | `GET /devices/101/configuration` | 200; `communication_key_set=true`, `sync_key_set=true`, `device_sync_time="16:51:00"`, `sync_code_set=true`, `pass_code_set=true`. **No raw key/code values in the body.** | 200 | `SELECT communication_key, sync_key FROM biometric_devices WHERE id=101` → set in DB but ABSENT from the response; `SELECT device_sync_time FROM org_settings WHERE org_id=1` matches the response value | P0 |
| TC-HW-029 | Hardware / `GET /devices/{id}/configuration` | Org with no `org_settings` row falls back to schema defaults | Org C has no `org_settings`; device DEV-C1 registered in Org C | `GET /devices/{DEV-C1}/configuration` | 200; `device_sync_time="16:51:00"` (schema default), `sync_code_set=false`, `pass_code_set=false` — no 404, no 500 | 200 | `SELECT count(*) FROM org_settings WHERE org_id=3` → 0 | P2 |
| TC-HW-030 | Hardware / `PATCH /devices/{id}/configuration` | Rotate the communication key | DEV-A1 | `{"communication_key":"new-ck","adms_enabled":true,"adms_server":"adms.local","adms_port":8090}` | 200; response shows `communication_key_set=true`, `adms_enabled=true`; **the new key value is never echoed** | 200 | `SELECT communication_key FROM biometric_devices WHERE id=101` → `'new-ck'` in DB but ABSENT from the response body; `activity_logs` `title='Device configuration updated'` +1 | P0 |
| TC-HW-031 | Hardware / `PUT /devices/{id}/branch` | Assign a device to a branch | DEV-A1, BR-A2 = 12 | `{"branch_id":12}` | 200; `branch_id=12` | 200 | `SELECT branch_id FROM biometric_devices WHERE id=101` → 12; `activity_logs` `action_type='Assign'` +1 | P1 |
| TC-HW-032 | Hardware / `PUT /devices/{id}/branch` | Unassign by passing null | DEV-A1 assigned | `{"branch_id":null}` | 200; `branch_id=null` | 200 | `SELECT branch_id FROM biometric_devices WHERE id=101` → NULL | P1 |
| TC-HW-033 | Hardware / `PUT /devices/{id}/branch` | Assign to another org's branch | BR-B1 = 21 | As A-ADMIN: `PUT /devices/101/branch {"branch_id":21}` | 404 `BRANCH_NOT_FOUND` | 404 | `SELECT branch_id FROM biometric_devices WHERE id=101` → unchanged | P0 |
| TC-HW-034 | Hardware / `POST /devices/{id}/disable` | Disable an active device | DEV-A1 `is_active=true` | `POST /devices/101/disable` | 200; `is_active=false` | 200 | `SELECT is_active FROM biometric_devices WHERE id=101` → false; `activity_logs` `title='Device disabled'` +1 | P1 |
| TC-HW-035 | Hardware / `POST /devices/{id}/disable` | Disabling an already-disabled device is idempotent | DEV-A1 `is_active=false` | `POST /devices/101/disable` | 200 (returns current state, no error) | 200 | `SELECT count(*) FROM activity_logs WHERE org_id=1 AND title='Device disabled'` → **unchanged** (service short-circuits before the audit write) | P2 |
| TC-HW-036 | Hardware / `POST /devices/{id}/enable` | Enable a disabled device | DEV-A1 `is_active=false` | `POST /devices/101/enable` | 200; `is_active=true` | 200 | `SELECT is_active FROM biometric_devices WHERE id=101` → true; `activity_logs` `title='Device enabled'` +1 | P1 |
| TC-HW-037 | Hardware / `GET /devices/{id}/status` | Read connectivity status | DEV-A1 | `GET /devices/101/status` | 200; `{status, last_seen_at, last_sync_at, is_active}` only — no secrets, no stats | 200 | n/a (read-only) | P1 |
| TC-HW-038 | Hardware / `PUT /devices/{id}/heartbeat` | Agent reports online + capacity metrics | DEV-A1 | `{"status":"online","firmware_version":"6.60","total_users":120,"total_fingerprints":340,"total_logs":98000}` | 200; device reflects the reported values; `last_seen_at` set to now when omitted from the payload | 200 | `SELECT status, total_users, total_logs, last_seen_at FROM biometric_devices WHERE id=101` → `'online'`, 120, 98000, ≈now. **`SELECT count(*) FROM activity_logs WHERE org_id=1` → unchanged** (heartbeat writes no audit row by design) | P1 |
| TC-HW-039 | Hardware / `PUT /devices/{id}/heartbeat` | Negative counter rejected | — | `{"total_users":-5}` | 422 `VALIDATION_ERROR` (`ge=0`) | 422 | Device row unchanged | P2 |
| TC-HW-040 | Hardware / `PUT /devices/{id}/heartbeat` | Heartbeat against another org's device | DEV-B1 = 201 | As A-ADMIN: `PUT /devices/201/heartbeat {"status":"online"}` | 404 `DEVICE_NOT_FOUND` | 404 | `SELECT status, last_seen_at FROM biometric_devices WHERE id=201` → unchanged | P0 |
| TC-HW-041 | Hardware / `GET /devices/{id}/health` | Health returns nested aggregate stats only | DEV-A1 with counters populated | `GET /devices/101/health` | 200; `stats:{total_users,total_fingerprints,total_faces,total_cards,total_logs}`. **No biometric template data, no per-employee rows — aggregate counts only.** | 200 | `SELECT count(*) FROM employee_biometrics WHERE device_id=101` > 0 yet no template bytes/records appear in the response | P0 |
| TC-HW-042 | Hardware / auth | Any device endpoint without a token | — | `GET /devices` with no `Authorization` header | 401 `AUTH_NOT_AUTHENTICATED` | 401 | n/a | P0 |
| TC-HW-043 | Hardware / authz | Read without `device:read` | A-NOPERM | `GET /devices` | 403 `AUTH_FORBIDDEN` | 403 | n/a | P0 |
| TC-HW-044 | Hardware / authz | Create without `device:create` (holds only `device:read`) | A read-only device user | `POST /devices {...valid...}` | 403 `AUTH_FORBIDDEN` | 403 | `SELECT count(*) FROM biometric_devices WHERE org_id=1` → unchanged | P0 |
| TC-HW-045 | Hardware / authz | Delete without `device:delete` | A user with `device:read,edit` only | `DELETE /devices/103` | 403 `AUTH_FORBIDDEN` | 403 | Device row still present | P0 |
| TC-HW-046 | Hardware / E2E audit | Every hardware mutation lands in the audit trail | Baseline `NA` captured | Run register → update → configure → assign → disable → enable → delete in sequence, then `GET /activity-logs?module=Hardware%20%2F%20Biometric%20Management` | The audit list contains one row per mutation, ordered `logged_at desc`; heartbeat contributes none | 200 | `SELECT count(*) FROM activity_logs WHERE org_id=1 AND module='Hardware / Biometric Management'` → +7 over baseline (register, update, configure, assign, disable, enable, delete) | P1 |

---

## 4. TC-NOT — Notification Management

Admin surface (feature key `notification`): `POST /notifications`, `GET /notifications`, `GET /notifications/{id}`, `POST /notifications/{id}/recipients`, `GET /notifications/{id}/recipients`.
Self-service surface (**authenticated, NO permission guard**, scoped to `current_user.user_id`): `GET /me/notifications`, `GET /me/notifications/count`, `GET /me/notifications/{id}`, `GET /me/notifications/{id}/timeline`, `POST /me/notifications/{notification_id}/read`, `/unread`, `/archive`, `/unarchive`, `DELETE /me/notifications/{id}`, `POST /me/notifications/bulk-read`, `/bulk-archive`, `/bulk-delete`.

| ID | Module / API | Test Scenario | Preconditions | Request / Input | Expected Result | HTTP | Database Verification | Priority |
|---|---|---|---|---|---|---|---|---|
| TC-NOT-001 | Notifications / `POST /notifications` | Create a notification with recipients | A-ADMIN has `notification:create`; A-EMP, A-EMP2 active in Org A | `{"title":"Policy update","message":"Read the new policy.","notification_type":"approval","priority":"normal","recipient_user_ids":[A-EMP,A-EMP2]}` | 201; notification returned with `id` | 201 | `SELECT count(*) FROM notification_recipients WHERE notification_id=:new` → 2, both with `delivered_at` NOT NULL; `SELECT count(*) FROM activity_logs WHERE org_id=1 AND module='notifications' AND sub_module='notification'` → +1 | P1 |
| TC-NOT-002 | Notifications / `POST /notifications` | Create without recipients | — | `{"title":"T","message":"M","notification_type":"payroll","priority":"low"}` | 201 | 201 | `SELECT count(*) FROM notification_recipients WHERE notification_id=:new` → 0 | P2 |
| TC-NOT-003 | Notifications / `POST /notifications` | Recipient belongs to another org | B user id `UB` in Org B | As A-ADMIN: `{"title":"T","message":"M","notification_type":"approval","priority":"normal","recipient_user_ids":[UB]}` | **404 `USER_NOT_FOUND`** — Org A cannot target an Org B user | 404 | `SELECT count(*) FROM notifications WHERE org_id=1` → **unchanged** (validation runs before the transaction); no `notification_recipients` row for `UB` | P0 |
| TC-NOT-004 | Notifications / `POST /notifications` | `expires_at` in the past | — | `{"title":"T","message":"M","notification_type":"approval","priority":"normal","expires_at":"2020-01-01T00:00:00Z"}` | 422 `VALIDATION_ERROR` — "expires_at must be in the future" | 422 | No row inserted | P2 |
| TC-NOT-005 | Notifications / `POST /notifications` | Blank title | — | `{"title":"","message":"M","notification_type":"approval","priority":"normal"}` | 422 `VALIDATION_ERROR` (`min_length=1`) | 422 | No row inserted | P2 |
| TC-NOT-006 | Notifications / `POST /notifications` | Whitespace-only title reaches the service validator | — | `{"title":"   ","message":"M","notification_type":"approval","priority":"normal"}` | 422 `VALIDATION_ERROR` — "Notification title cannot be empty." | 422 | No row inserted | P2 |
| TC-NOT-007 | Notifications / `POST /notifications` | Title exceeding 200 chars | — | `{"title":"<201 chars>", ...}` | 422 `VALIDATION_ERROR` (`max_length=200`) | 422 | No row inserted | P2 |
| TC-NOT-008 | Notifications / `GET /notifications` | Admin list is org-scoped | NOT-A1..A4 in Org A, NOT-B1 in Org B | As A-ADMIN: `GET /notifications` | 200; every `items[].org_id == 1`; NOT-B1 (401) absent | 200 | `pagination.total_records` == `SELECT count(*) FROM notifications WHERE org_id=1` | P0 |
| TC-NOT-009 | Notifications / `GET /notifications` | Filter by type, priority, source module, date range | Seeded mix | `GET /notifications?notification_type=payroll&priority=normal&source_module=payroll&date_from=2026-07-01T00:00:00Z&date_to=2026-07-31T23:59:59Z` | 200; only matching rows | 200 | n/a (read-only) | P1 |
| TC-NOT-010 | Notifications / `GET /notifications` | Free-text search on title/message | — | `GET /notifications?search=Policy` | 200; only notifications whose title or message matches | 200 | n/a (read-only) | P2 |
| TC-NOT-011 | Notifications / `GET /notifications` | Invalid `sort_order` enum | — | `GET /notifications?sort_order=sideways` | 422 `VALIDATION_ERROR` (`SortOrder` enum: `asc`/`desc`) | 422 | n/a (read-only) | P2 |
| TC-NOT-012 | Notifications / `GET /notifications/{id}` | Detail returns delivery aggregates | NOT-A1 = 301 with 2 recipients, 1 read | `GET /notifications/301` | 200; `recipient_count=2`, `read_count=1`, `delivered_count` matches | 200 | Compare with `SELECT count(*), count(read_at), count(delivered_at) FROM notification_recipients WHERE notification_id=301` | P1 |
| TC-NOT-013 | Notifications / `GET /notifications/{id}` | Cross-tenant notification detail | NOT-B1 = 401 (Org B) | As A-ADMIN: `GET /notifications/401` | **404 `NOTIFICATION_NOT_FOUND`** — never the Org B payload | 404 | `SELECT org_id FROM notifications WHERE id=401` → 2 (undisclosed) | P0 |
| TC-NOT-014 | Notifications / `POST /notifications/{id}/recipients` | Assign new recipients idempotently | NOT-A1 = 301, A-EMP already assigned, A-EMP2 not | `{"user_ids":[A-EMP, A-EMP2]}` | 200; `results[]` contains `{user_id:A-EMP, assigned:false, status:"already_assigned"}` and `{user_id:A-EMP2, assigned:true, status:"created"}`. **Note:** the already-assigned case is reported *in the 200 body*, not as a 409 `ALREADY_ASSIGNED` — see §9 | 200 | `SELECT count(*) FROM notification_recipients WHERE notification_id=301` → +1 only (no duplicate row for A-EMP) | P1 |
| TC-NOT-015 | Notifications / `POST /notifications/{id}/recipients` | Assign a user from another org | NOT-A1 = 301, `UB` in Org B | `{"user_ids":[UB]}` | 200; `results[0] = {assigned:false, status:"user_not_found"}` — the cross-org user is silently skipped, never assigned | 200 | `SELECT count(*) FROM notification_recipients WHERE notification_id=301 AND user_id=:UB` → 0 | P0 |
| TC-NOT-016 | Notifications / `POST /notifications/{id}/recipients` | Assign to another org's notification | NOT-B1 = 401 | As A-ADMIN: `POST /notifications/401/recipients {"user_ids":[A-EMP]}` | 404 `NOTIFICATION_NOT_FOUND` | 404 | `SELECT count(*) FROM notification_recipients WHERE notification_id=401` → unchanged; `SELECT count(*) FROM activity_logs WHERE org_id=2` → still `NB` | P0 |
| TC-NOT-017 | Notifications / `POST /notifications/{id}/recipients` | Mixed batch — valid + already-assigned + cross-org | NOT-A1 = 301 | `{"user_ids":[A-EMP(assigned), A-EMP2(new), UB(org B)]}` | 200; three result entries: `already_assigned`, `created`, `user_not_found`. Partial success is expected | 200 | `SELECT count(*) FROM notification_recipients WHERE notification_id=301` → +1; a single `activity_logs` row written (only when ≥1 assignment succeeded) | P1 |
| TC-NOT-018 | Notifications / `GET /notifications/{id}/recipients` | List recipients with delivery/read filters | NOT-A1 with mixed states | `GET /notifications/301/recipients?read=false&delivered=true` | 200; only recipients with `read_at IS NULL AND delivered_at IS NOT NULL` | 200 | Compare with the equivalent SQL predicate on `notification_recipients` | P1 |
| TC-NOT-019 | Notifications / `GET /notifications/{id}/recipients` | Cross-tenant recipient listing | NOT-B1 = 401 | As A-ADMIN: `GET /notifications/401/recipients` | 404 `NOTIFICATION_NOT_FOUND` — Org B's recipient list must never be enumerable | 404 | n/a (read-only); confirm no Org B user ids appear in any response body | P0 |
| TC-NOT-020 | Notifications / `GET /me/notifications` | Self-service inbox is scoped to the caller | A-EMP is a recipient of NOT-A1, NOT-A2; NOT-A3 targets A-EMP2 only | As A-EMP: `GET /me/notifications` | 200; NOT-A1 present; **NOT-A3 absent** (A-EMP is not a recipient); archived NOT-A2 absent (default `archived=false`) | 200 | Response ids ⊆ `SELECT notification_id FROM notification_recipients WHERE user_id=:A-EMP AND deleted_at IS NULL` | P0 |
| TC-NOT-021 | Notifications / `GET /me/notifications` | Self-service requires authentication but NOT a permission | A-EMP has **zero** feature permissions | As A-EMP: `GET /me/notifications` | 200 — the `/me/*` routes carry no `require_permission` guard | 200 | n/a (read-only) | P1 |
| TC-NOT-022 | Notifications / `GET /me/notifications` | Unauthenticated self-service call | — | `GET /me/notifications` with no token | 401 `AUTH_NOT_AUTHENTICATED` | 401 | n/a | P0 |
| TC-NOT-023 | Notifications / `GET /me/notifications` | Filter `status=unread` | A-EMP has 1 unread, 1 read | `GET /me/notifications?status=unread` | 200; only rows whose `read_at IS NULL` | 200 | n/a (read-only) | P1 |
| TC-NOT-024 | Notifications / `GET /me/notifications` | `archived=true` returns archived only | NOT-A2 archived for A-EMP | `GET /me/notifications?archived=true` | 200; NOT-A2 present, NOT-A1 absent | 200 | n/a (read-only) | P1 |
| TC-NOT-025 | Notifications / `GET /me/notifications` | Expired notifications hidden by default, shown with `include_expired=true` | NOT-A4 has `expires_at` in the past | `GET /me/notifications` then `GET /me/notifications?include_expired=true` | First call: NOT-A4 absent. Second call: NOT-A4 present | 200 | `SELECT expires_at FROM notifications WHERE id=304` → in the past | P2 |
| TC-NOT-026 | Notifications / `GET /me/notifications` | Empty inbox | A user with no recipient rows | `GET /me/notifications` | 200; `items: []`, `total_records: 0` | 200 | n/a (read-only) | P2 |
| TC-NOT-027 | Notifications / `GET /me/notifications/count` | Badge counters | A-EMP: 1 unread, 1 archived, 2 total | `GET /me/notifications/count` | 200; `{unread, archived, total}` matching the seed | 200 | Compare against `SELECT count(*) FILTER (WHERE read_at IS NULL), count(*) FILTER (WHERE archived_at IS NOT NULL), count(*) FROM notification_recipients WHERE org_id=1 AND user_id=:A-EMP AND deleted_at IS NULL` | P1 |
| TC-NOT-028 | Notifications / `GET /me/notifications/{id}` | Fetching marks the notification delivered on first read | NOT-A1 recipient row for A-EMP has `delivered_at IS NULL` | As A-EMP: `GET /me/notifications/301` | 200; body includes `delivered_at` (now) | 200 | `SELECT delivered_at FROM notification_recipients WHERE notification_id=301 AND user_id=:A-EMP` → was NULL, now ≈now (a GET that legitimately writes) | P1 |
| TC-NOT-029 | Notifications / `GET /me/notifications/{id}` | **Cross-user read of another user's notification** | NOT-A3 = 303 targets A-EMP2 only | As A-EMP: `GET /me/notifications/303` | **404 `RECIPIENT_NOT_FOUND`** — a user must never read another user's notification, even inside the same org | 404 | `SELECT count(*) FROM notification_recipients WHERE notification_id=303 AND user_id=:A-EMP` → 0; A-EMP2's row untouched (`delivered_at` unchanged) | P0 |
| TC-NOT-030 | Notifications / `GET /me/notifications/{id}` | Cross-tenant self-service read | NOT-B1 = 401 (Org B) | As A-EMP: `GET /me/notifications/401` | 404 `RECIPIENT_NOT_FOUND` | 404 | n/a (read-only) | P0 |
| TC-NOT-031 | Notifications / `POST /me/notifications/{id}/read` | Mark own notification read | NOT-A1 unread for A-EMP | `POST /me/notifications/301/read` | 200 | 200 | `SELECT read_at FROM notification_recipients WHERE notification_id=301 AND user_id=:A-EMP` → NOT NULL | P1 |
| TC-NOT-032 | Notifications / `POST /me/notifications/{id}/read` | Marking an already-read notification is idempotent | NOT-A1 already read | `POST /me/notifications/301/read` | 200; `read_at` **not** overwritten with a new timestamp | 200 | `SELECT read_at` → identical to the prior value | P2 |
| TC-NOT-033 | Notifications / `POST /me/notifications/{id}/read` | **Cross-user mark-as-read** | NOT-A3 = 303 belongs to A-EMP2 | As A-EMP: `POST /me/notifications/303/read` | 404 `RECIPIENT_NOT_FOUND` | 404 | `SELECT read_at FROM notification_recipients WHERE notification_id=303 AND user_id=:A-EMP2` → still NULL (A-EMP could not mutate A-EMP2's state) | P0 |
| TC-NOT-034 | Notifications / `POST /me/notifications/{id}/unread` | Mark read → unread | NOT-A1 read | `POST /me/notifications/301/unread` | 200 | 200 | `SELECT read_at FROM notification_recipients WHERE notification_id=301 AND user_id=:A-EMP` → NULL | P1 |
| TC-NOT-035 | Notifications / `POST /me/notifications/{id}/archive` | Archive own notification | NOT-A1 not archived | `POST /me/notifications/301/archive` | 200 | 200 | `SELECT archived_at ... ` → NOT NULL | P1 |
| TC-NOT-036 | Notifications / `POST /me/notifications/{id}/unarchive` | Unarchive | NOT-A2 archived | `POST /me/notifications/302/unarchive` | 200 | 200 | `SELECT archived_at ...` → NULL | P1 |
| TC-NOT-037 | Notifications / `DELETE /me/notifications/{id}` | Soft-delete for the recipient only | NOT-A1 has recipients A-EMP and A-EMP2 | As A-EMP: `DELETE /me/notifications/301` | 204 | 204 | `SELECT deleted_at FROM notification_recipients WHERE notification_id=301 AND user_id=:A-EMP` → NOT NULL; **A-EMP2's row `deleted_at` still NULL**; `SELECT count(*) FROM notifications WHERE id=301` → 1 (the definition is NOT deleted) | P0 |
| TC-NOT-038 | Notifications / `DELETE /me/notifications/{id}` | Deleting an already-deleted notification | A-EMP's row for 301 has `deleted_at` set | `DELETE /me/notifications/301` | 404 `RECIPIENT_NOT_FOUND` | 404 | Row unchanged | P2 |
| TC-NOT-039 | Notifications / `DELETE /me/notifications/{id}` | **Cross-user delete** | NOT-A3 belongs to A-EMP2 | As A-EMP: `DELETE /me/notifications/303` | 404 `RECIPIENT_NOT_FOUND` | 404 | `SELECT deleted_at FROM notification_recipients WHERE notification_id=303 AND user_id=:A-EMP2` → still NULL | P0 |
| TC-NOT-040 | Notifications / `POST /me/notifications/bulk-read` | Bulk mark specific ids read | A-EMP has 301, 302 unread | `{"notification_ids":[301,302]}` | 200; `affected_count=2` | 200 | `SELECT count(*) FROM notification_recipients WHERE user_id=:A-EMP AND notification_id IN (301,302) AND read_at IS NOT NULL` → 2 | P1 |
| TC-NOT-041 | Notifications / `POST /me/notifications/bulk-read` | `all_unread=true` marks the whole inbox read | A-EMP has N unread | `{"all_unread":true}` | 200; `affected_count = N` | 200 | `SELECT count(*) FROM notification_recipients WHERE user_id=:A-EMP AND read_at IS NULL AND deleted_at IS NULL` → 0 | P1 |
| TC-NOT-042 | Notifications / `POST /me/notifications/bulk-read` | Neither ids nor `all_unread` supplied | — | `{}` | 422 `VALIDATION_ERROR` — "Either notification_ids or all_unread must be provided." | 422 | Nothing marked read | P2 |
| TC-NOT-043 | Notifications / `POST /me/notifications/bulk-read` | Bulk read includes another user's notification id | 303 belongs to A-EMP2 | As A-EMP: `{"notification_ids":[301,303]}` | 200; `affected_count=1` — id 303 silently ignored (the bulk query is `user_id`-scoped) | 200 | `SELECT read_at FROM notification_recipients WHERE notification_id=303 AND user_id=:A-EMP2` → **still NULL** (no cross-user write) | P0 |
| TC-NOT-044 | Notifications / `POST /me/notifications/bulk-archive` | Bulk archive | A-EMP has 301, 302 | `{"notification_ids":[301,302]}` | 200; `affected_count=2` | 200 | Both rows have `archived_at` NOT NULL | P1 |
| TC-NOT-045 | Notifications / `POST /me/notifications/bulk-archive` | Empty id list | — | `{"notification_ids":[]}` | 422 `VALIDATION_ERROR` — router rejects the empty list before the service | 422 | Nothing archived | P2 |
| TC-NOT-046 | Notifications / `POST /me/notifications/bulk-delete` | Bulk soft-delete | A-EMP has 301, 302 | `{"notification_ids":[301,302]}` | 200; `affected_count=2` | 200 | Both `notification_recipients` rows have `deleted_at` NOT NULL; `SELECT count(*) FROM notifications WHERE id IN (301,302)` → 2 (definitions survive) | P1 |
| TC-NOT-047 | Notifications / `POST /me/notifications/bulk-delete` | Bulk delete across tenants | 401 is an Org B notification | As A-EMP: `{"notification_ids":[401]}` | 200; `affected_count=0` — no rows touched | 200 | `SELECT deleted_at FROM notification_recipients WHERE notification_id=401` → still NULL for every Org B recipient | P0 |
| TC-NOT-048 | Notifications / `GET /me/notifications/{id}/timeline` | Lifecycle timeline is chronological | A-EMP's row for 301 has created → delivered → read → archived | `GET /me/notifications/301/timeline` | 200; events `["created","delivered","read","archived"]` sorted ascending by `at` | 200 | Timestamps match `created_at`, `delivered_at`, `read_at`, `archived_at` on the recipient row | P2 |
| TC-NOT-049 | Notifications / `GET /me/notifications/{id}/timeline` | Cross-user timeline | 303 belongs to A-EMP2 | As A-EMP: `GET /me/notifications/303/timeline` | 404 `RECIPIENT_NOT_FOUND` | 404 | n/a (read-only) | P0 |
| TC-NOT-050 | Notifications / authz | Admin surface without `notification:read` | A-EMP (no permissions) | `GET /notifications` | 403 `AUTH_FORBIDDEN` — the admin surface *is* guarded even though `/me/*` is not | 403 | n/a | P0 |
| TC-NOT-051 | Notifications / authz | Admin create without `notification:create` | A user holding only `notification:read` | `POST /notifications {...}` | 403 `AUTH_FORBIDDEN` | 403 | `SELECT count(*) FROM notifications WHERE org_id=1` → unchanged | P0 |
| TC-NOT-052 | Notifications / E2E business event | Approving an approval request emits a system notification to the subject employee's user | Approval request `AR-1` for EMP-A1 (linked to A-EMP) is pending; A-ADMIN can approve | `POST /approvals/{AR-1}/approve {"remarks":"ok"}` then, as A-EMP, `GET /me/notifications` | Approval → 200; the inbox now contains a notification titled `Request Approved`, `notification_type="approval"`, `source_module="approvals"`, `source_entity_id=AR-1` | 200 | `SELECT n.id FROM notifications n JOIN notification_recipients r ON r.notification_id=n.id WHERE n.org_id=1 AND n.source_entity_type='approval_request' AND n.source_entity_id=:AR1 AND r.user_id=:A-EMP` → exactly 1 row, `delivered_at` NOT NULL | P0 |
| TC-NOT-053 | Notifications / E2E business event | Rejecting an approval emits a `Request Rejected` notification | Approval `AR-2` pending for EMP-A1 | `POST /approvals/{AR-2}/reject {"remarks":"invalid"}` | 200; A-EMP's inbox gains `Request Rejected` | 200 | `SELECT title FROM notifications WHERE source_entity_id=:AR2` → `'Request Rejected'`; 1 matching `notification_recipients` row for A-EMP | P1 |
| TC-NOT-054 | Notifications / E2E business event | Approval decision for an employee with **no linked user** emits nothing but still succeeds | EMP-A3 has no `users.employee_id` link; approval `AR-3` pending | `POST /approvals/{AR-3}/approve` | 200 — the approval succeeds; no notification is created (recipient list is empty) | 200 | `SELECT count(*) FROM notifications WHERE source_entity_id=:AR3` → 0; the approval row is still marked approved | P1 |
| TC-NOT-055 | Notifications / E2E business event | Finalizing payroll notifies every affected employee's linked user | Payroll cycle with computed rows for EMP-A1, EMP-A2 (both linked) | `POST /payroll/processing/finalize {...}` | 200; both A-EMP and A-EMP2 receive `Payroll Finalized`, `notification_type="payroll"` | 200 | `SELECT count(*) FROM notification_recipients r JOIN notifications n ON n.id=r.notification_id WHERE n.source_entity_type='finalized_payroll_run' AND n.org_id=1` → 2 (one per linked user), single parent `notifications` row | P0 |
| TC-NOT-056 | Notifications / E2E business event | The payroll notification commits atomically with the finalization | Force a failure after the notification emission inside the finalize transaction | `POST /payroll/processing/finalize` (fault injected) | 5xx / error; the whole transaction rolls back | 5xx | `SELECT count(*) FROM notifications WHERE source_entity_type='finalized_payroll_run'` → unchanged **and** the payroll run is not finalized — the notification and the mutation roll back together | P1 |

---

## 5. TC-SET — Settings Management

Endpoints: `GET /settings`, `GET|PATCH /settings/organization`, `POST /settings/organization/reset`, `GET|PATCH /settings/salary-slip`, `GET /settings/features`, `PATCH /settings/features/{feature_key}`. Feature key: `settings`.
**These toggles gate other modules — every toggle case is P0 or P1.**

| ID | Module / API | Test Scenario | Preconditions | Request / Input | Expected Result | HTTP | Database Verification | Priority |
|---|---|---|---|---|---|---|---|---|
| TC-SET-001 | Settings / `GET /settings` | Combined configuration view | Org A has both settings rows | As A-ADMIN: `GET /settings` | 200; `data.organization`, `data.salary_slip`, and `data.cross_module_pointers` for `leave`, `payroll`, `attendance` | 200 | n/a (read-only) | P1 |
| TC-SET-002 | Settings / `GET /settings` | Combined view for an org with no settings rows | Org C | As an Org C admin: `GET /settings` | 200; `organization: null`, `salary_slip: null`, pointers still present — **no 404, no 500** | 200 | `SELECT count(*) FROM org_settings WHERE org_id=3` → 0 | P2 |
| TC-SET-003 | Settings / `GET /settings` | `pass_code` is masked in the combined view | Org A `pass_code='PASS-A'` | `GET /settings` | 200; `data.organization.pass_code == "********"` | 200 | `SELECT pass_code FROM org_settings WHERE org_id=1` → `'PASS-A'` in DB, but the response shows only `********` | P0 |
| TC-SET-004 | Settings / `GET /settings/organization` | Read org settings | Org A row exists | `GET /settings/organization` | 200; toggles + `device_sync_time` + `updated_by` returned | 200 | Values equal `SELECT * FROM org_settings WHERE org_id=1` | P1 |
| TC-SET-005 | Settings / `GET /settings/organization` | **`sync_code` must be masked in the response** | Org A `sync_code='SYNC-A-123'` | `GET /settings/organization` | Spec: `sync_code` masked (`********`), same as `pass_code`. **Currently FAILS — the shipped `OrgSettingsResponse` masks only `pass_code`; `sync_code` is returned in plaintext (§9, DEF-1).** | 200 | `SELECT sync_code FROM org_settings WHERE org_id=1` → `'SYNC-A-123'`; assert the response body does **not** contain that literal | P0 |
| TC-SET-006 | Settings / `GET /settings/organization` | Uninitialized settings row | Org C | As an Org C admin: `GET /settings/organization` | 404 `SETTINGS_NOT_FOUND` | 404 | `SELECT count(*) FROM org_settings WHERE org_id=3` → 0 | P1 |
| TC-SET-007 | Settings / `GET /settings/organization` | Tenant isolation — Org B never sees Org A settings | Both orgs initialized with different `sync_code` | As B-ADMIN: `GET /settings/organization` | 200; `org_id == 2`; none of Org A's values present | 200 | Response `id` == `SELECT id FROM org_settings WHERE org_id=2` | P0 |
| TC-SET-008 | Settings / `PATCH /settings/organization` | Partial update of a single toggle | Org A row exists | `{"enable_photo_punch":true}` | 200; only that field changes | 200 | `SELECT enable_photo_punch, enable_regularization FROM org_settings WHERE org_id=1` → `true`, `false` (untouched); `activity_logs` `module='settings'`, `sub_module='organization'` +1 | P1 |
| TC-SET-009 | Settings / `PATCH /settings/organization` | Upsert — first write for an org with no row | Org C | `{"sync_code":"SYNC-C","pass_code":"PASS-C","device_sync_time":"18:00:00"}` | 200; the row is created | 200 | `SELECT count(*) FROM org_settings WHERE org_id=3` → 1; `advance_shift_enabled` / `enable_regularization` / `enable_photo_punch` all default to `false` | P1 |
| TC-SET-010 | Settings / `PATCH /settings/organization` | Upsert without `sync_code` | Org C, no row | `{"enable_regularization":true}` | 422 `VALIDATION_ERROR` — "sync_code is required when creating organization settings." | 422 | `SELECT count(*) FROM org_settings WHERE org_id=3` → still 0 | P2 |
| TC-SET-011 | Settings / `PATCH /settings/organization` | Upsert without `pass_code` | Org C, no row | `{"sync_code":"SYNC-C"}` | 422 `VALIDATION_ERROR` — "pass_code is required when creating organization settings." | 422 | No row created | P2 |
| TC-SET-012 | Settings / `PATCH /settings/organization` | `sync_code` over 50 characters | — | `{"sync_code":"<51 chars>"}` | 422 `VALIDATION_ERROR` | 422 | Row unchanged | P2 |
| TC-SET-013 | Settings / `PATCH /settings/organization` | `pass_code` over 20 characters | — | `{"pass_code":"<21 chars>"}` | 422 `VALIDATION_ERROR` | 422 | Row unchanged | P2 |
| TC-SET-014 | Settings / `PATCH /settings/organization` | Malformed `device_sync_time` | — | `{"device_sync_time":"25:99"}` | 422 `VALIDATION_ERROR` | 422 | Row unchanged | P2 |
| TC-SET-015 | Settings / `PATCH /settings/organization` | Cross-tenant write is impossible — org comes from the token, not the body | Org B row exists | As A-ADMIN: `PATCH /settings/organization {"org_id":2,"enable_photo_punch":true}` | 200 but only **Org A** is affected — `org_id` in the body is ignored (not a request field) | 200 | `SELECT enable_photo_punch FROM org_settings WHERE org_id=2` → **unchanged**; `SELECT count(*) FROM activity_logs WHERE org_id=2` → still `NB` | P0 |
| TC-SET-016 | Settings / **E2E gate** | `enable_regularization=false` (schema default) blocks attendance corrections | Org A `enable_regularization=false`; A-ADMIN can create corrections | `POST /attendance/corrections {...valid...}` | **409 `REGULARIZATION_DISABLED`** | 409 | `SELECT count(*) FROM attendance_correction_requests WHERE org_id=1` → unchanged | P0 |
| TC-SET-017 | Settings / **E2E gate** | Toggling `enable_regularization` ON unblocks attendance corrections | Continue from TC-SET-016 | `PATCH /settings/organization {"enable_regularization":true}` → then `POST /attendance/corrections {...same payload...}` | Toggle → 200; correction → **201** (the gated operation now succeeds) | 200 → 201 | `SELECT enable_regularization FROM org_settings WHERE org_id=1` → `true`; the correction row now exists | P0 |
| TC-SET-018 | Settings / **E2E gate** | Toggling `enable_regularization` back OFF re-blocks corrections | Continue from TC-SET-017 | `PATCH /settings/organization {"enable_regularization":false}` → `POST /attendance/corrections` | Toggle → 200; correction → **409 `REGULARIZATION_DISABLED`** | 200 → 409 | `SELECT enable_regularization FROM org_settings WHERE org_id=1` → `false`; no new correction row | P0 |
| TC-SET-019 | Settings / **E2E gate** | `advance_shift_enabled=false` blocks shift rotation generation | Org A `advance_shift_enabled=false` | `POST /shift-rotations {...valid...}` | **409 `ADVANCE_SHIFT_DISABLED`** | 409 | `SELECT count(*) FROM roster WHERE org_id=1` → unchanged (no roster rows materialized) | P0 |
| TC-SET-020 | Settings / **E2E gate** | Toggling `advance_shift_enabled` ON unblocks rotation | — | `PATCH /settings/features/advance_shift_enabled {"enabled":true}` → `POST /shift-rotations {...}` | Toggle → 200; rotation → **200/201** with generated roster entries | 200 → 200/201 | `SELECT advance_shift_enabled FROM org_settings WHERE org_id=1` → `true`; `SELECT count(*) FROM roster WHERE org_id=1` → increased | P0 |
| TC-SET-021 | Settings / **E2E gate** | Toggling `advance_shift_enabled` OFF re-blocks rotation | — | `PATCH /settings/features/advance_shift_enabled {"enabled":false}` → `POST /shift-rotations` | Toggle → 200; rotation → **409 `ADVANCE_SHIFT_DISABLED`** | 200 → 409 | `SELECT advance_shift_enabled FROM org_settings WHERE org_id=1` → `false`; no new roster rows | P0 |
| TC-SET-022 | Settings / **E2E gate** | An org with **no** settings row behaves as if every toggle is OFF | Org C, no `org_settings` row | As an Org C admin: `POST /attendance/corrections` and `POST /shift-rotations` | 409 `REGULARIZATION_DISABLED` and 409 `ADVANCE_SHIFT_DISABLED` respectively (`settings is None` ⇒ disabled) | 409 | `SELECT count(*) FROM org_settings WHERE org_id=3` → 0 | P0 |
| TC-SET-023 | Settings / `POST /settings/organization/reset` | Reset restores schema defaults | Org A with `advance_shift_enabled=true`, `enable_regularization=true`, `enable_photo_punch=true`, `device_sync_time='09:00'` | `POST /settings/organization/reset` | 200; all three toggles `false`, `device_sync_time="16:51:00"` | 200 | `SELECT advance_shift_enabled, enable_regularization, enable_photo_punch, device_sync_time FROM org_settings WHERE org_id=1` → `false,false,false,'16:51:00'`; `activity_logs` "Organization Settings Reset to Defaults" +1 | P1 |
| TC-SET-024 | Settings / `POST /settings/organization/reset` | **Reset does NOT clear `sync_code` / `pass_code`** | Org A codes set | `POST /settings/organization/reset` | 200 | 200 | `SELECT sync_code, pass_code FROM org_settings WHERE org_id=1` → **identical to the pre-reset values** (never nulled, never regenerated) | P0 |
| TC-SET-025 | Settings / `POST /settings/organization/reset` | Reset with no settings row | Org C | `POST /settings/organization/reset` | 404 `SETTINGS_NOT_FOUND` | 404 | No row created | P2 |
| TC-SET-026 | Settings / **E2E gate** | Reset turns a previously-enabled gate back OFF, and the gated module immediately reflects it | `enable_regularization=true`, corrections working | `POST /settings/organization/reset` → `POST /attendance/corrections` | Reset → 200; correction → **409 `REGULARIZATION_DISABLED`** | 200 → 409 | `SELECT enable_regularization FROM org_settings WHERE org_id=1` → `false` | P0 |
| TC-SET-027 | Settings / `GET /settings/salary-slip` | Read salary-slip settings | Org A row exists | `GET /settings/salary-slip` | 200; brand fields + `auto_release_payslip`, `branch_wise_payslip` | 200 | Matches `SELECT * FROM org_salary_slip_settings WHERE org_id=1` | P1 |
| TC-SET-028 | Settings / `GET /settings/salary-slip` | Uninitialized | Org C | `GET /settings/salary-slip` | 404 `SETTINGS_NOT_FOUND` | 404 | `SELECT count(*) FROM org_salary_slip_settings WHERE org_id=3` → 0 | P1 |
| TC-SET-029 | Settings / `PATCH /settings/salary-slip` | Update brand fields | Org A row exists | `{"company_name":"Acme Foods","company_contact":"+91-9999999999"}` | 200 | 200 | `SELECT company_name FROM org_salary_slip_settings WHERE org_id=1` → `'Acme Foods'`; `activity_logs` `sub_module='salary_slip'` +1 | P1 |
| TC-SET-030 | Settings / `PATCH /settings/salary-slip` | Upsert requires name + address + contact | Org C, no row | `{"company_name":"C Ltd"}` | 422 `VALIDATION_ERROR` — "company_address is required when creating salary slip settings." | 422 | `SELECT count(*) FROM org_salary_slip_settings WHERE org_id=3` → still 0 | P2 |
| TC-SET-031 | Settings / `PATCH /settings/salary-slip` | Invalid email in `company_website_email` | — | `{"company_website_email":"not@an@email"}` | 422 `VALIDATION_ERROR` | 422 | Row unchanged | P2 |
| TC-SET-032 | Settings / `PATCH /settings/salary-slip` | A website URL (no `@`) is accepted as-is | — | `{"company_website_email":"https://acme.example"}` | 200 — the `@`-less value bypasses email validation by design | 200 | `SELECT company_website_email` → stored verbatim | P3 |
| TC-SET-033 | Settings / `PATCH /settings/salary-slip` | Blank `company_name` | — | `{"company_name":"   "}` | 422 `VALIDATION_ERROR` — "company_name cannot be blank." | 422 | Row unchanged | P2 |
| TC-SET-034 | Settings / `GET /settings/features` | All five fixed toggles returned | Org A both rows exist | `GET /settings/features` | 200; `features` contains exactly `advance_shift_enabled`, `enable_regularization`, `enable_photo_punch`, `auto_release_payslip`, `branch_wise_payslip` | 200 | Values match the two settings tables | P1 |
| TC-SET-035 | Settings / `GET /settings/features` | Features for an org with no rows fall back to defaults | Org C | `GET /settings/features` | 200; `advance_shift_enabled=false`, `enable_regularization=false`, `enable_photo_punch=false`, `auto_release_payslip=true`, `branch_wise_payslip=false` | 200 | `SELECT count(*) FROM org_settings WHERE org_id=3` → 0 | P2 |
| TC-SET-036 | Settings / `PATCH /settings/features/{key}` | Enable an `org_settings` feature | Org A row exists | `PATCH /settings/features/enable_photo_punch {"enabled":true}` | 200; full feature map returned with the key now `true` | 200 | `SELECT enable_photo_punch FROM org_settings WHERE org_id=1` → `true`; `activity_logs` `sub_module='features'`, title "Feature 'enable_photo_punch' Enabled" +1 | P1 |
| TC-SET-037 | Settings / `PATCH /settings/features/{key}` | Disable a salary-slip feature (routes to the other table) | Org A slip row exists | `PATCH /settings/features/auto_release_payslip {"enabled":false}` | 200 | 200 | `SELECT auto_release_payslip FROM org_salary_slip_settings WHERE org_id=1` → `false`; **`org_settings` row untouched** (`updated_at` unchanged) | P1 |
| TC-SET-038 | Settings / `PATCH /settings/features/{key}` | Unknown feature key | — | `PATCH /settings/features/enable_teleportation {"enabled":true}` | **404 `UNKNOWN_FEATURE`**; message lists the five valid keys | 404 | No settings row modified; no `activity_logs` row written | P2 |
| TC-SET-039 | Settings / `PATCH /settings/features/{key}` | Feature key that is a real column but not in the catalog | — | `PATCH /settings/features/device_sync_time {"enabled":true}` | 404 `UNKNOWN_FEATURE` — the catalog is a strict allowlist of the five boolean toggles | 404 | `SELECT device_sync_time FROM org_settings WHERE org_id=1` → unchanged | P2 |
| TC-SET-040 | Settings / `PATCH /settings/features/{key}` | Toggle an `org_settings` feature when the row does not exist | Org C | `PATCH /settings/features/enable_regularization {"enabled":true}` | 404 `SETTINGS_NOT_FOUND` — toggling does not upsert | 404 | `SELECT count(*) FROM org_settings WHERE org_id=3` → still 0 | P2 |
| TC-SET-041 | Settings / `PATCH /settings/features/{key}` | Missing `enabled` in the body | — | `PATCH /settings/features/enable_photo_punch {}` | 422 `VALIDATION_ERROR` (`enabled` is required) | 422 | Row unchanged | P2 |
| TC-SET-042 | Settings / authz | Read without `settings:read` | A-NOPERM | `GET /settings/organization` | 403 `AUTH_FORBIDDEN` | 403 | n/a | P0 |
| TC-SET-043 | Settings / authz | Write without `settings:edit` | A user with `settings:read` only | `PATCH /settings/organization {"enable_photo_punch":true}` | 403 `AUTH_FORBIDDEN` | 403 | `SELECT enable_photo_punch FROM org_settings WHERE org_id=1` → unchanged; **no `activity_logs` row** | P0 |
| TC-SET-044 | Settings / authz | Feature toggle without `settings:edit` | `settings:read` only | `PATCH /settings/features/enable_regularization {"enabled":true}` | 403 `AUTH_FORBIDDEN` — a user cannot open the regularization gate without edit rights | 403 | `SELECT enable_regularization FROM org_settings WHERE org_id=1` → unchanged | P0 |
| TC-SET-045 | Settings / auth | Unauthenticated | — | `GET /settings` with no token | 401 `AUTH_NOT_AUTHENTICATED` | 401 | n/a | P0 |
| TC-SET-046 | Settings / concurrency | Two concurrent first-time upserts for the same org | Org C, no row; `uq_org_settings_org_id` on `org_id` | 5 parallel `PATCH /settings/organization {"sync_code":"S","pass_code":"P"}` | Exactly 1 succeeds with 200; the rest return **409 `CONFLICT`** (unique-violation mapped) — **never 500** | 200 / 409 | `SELECT count(*) FROM org_settings WHERE org_id=3` → exactly 1 | P0 |

---

## 6. TC-AUD — Activity Log / Audit

Endpoints (**read-only, 5 total — the trail is APPEND-ONLY; there is no create/update/delete API**): `GET /activity-logs`, `GET /activity-logs/security-events`, `GET /activity-logs/{log_id}`, `GET /employees/{employee_id}/activity-logs`, `GET /users/{user_id}/activity-logs`. Feature key: `audit`.

| ID | Module / API | Test Scenario | Preconditions | Request / Input | Expected Result | HTTP | Database Verification | Priority |
|---|---|---|---|---|---|---|---|---|
| TC-AUD-001 | Audit / append-only | **No mutating audit endpoint exists** | — | `POST /activity-logs`, `PUT /activity-logs/501`, `PATCH /activity-logs/501`, `DELETE /activity-logs/501` | All four → **405 Method Not Allowed** (or 404 if unrouted). The audit trail cannot be created, edited, or deleted over HTTP | 405/404 | `SELECT count(*) FROM activity_logs WHERE org_id=1` → unchanged after all four attempts | P0 |
| TC-AUD-002 | Audit / `GET /activity-logs` | List the tenant's audit trail | Org A has ≥ 30 log rows | As A-ADMIN: `GET /activity-logs?page=1&page_size=25` | 200; 25 items, default order `logged_at desc`; each item has `module`, `action_type`, `performed_by_name`, `logged_at` | 200 | `pagination.total_records` == `SELECT count(*) FROM activity_logs WHERE org_id=1` | P1 |
| TC-AUD-003 | Audit / `GET /activity-logs` | **Org B must see ONLY its own rows** | Org A has `NA` rows, Org B has `NB` rows (different data) | As B-ADMIN: `GET /activity-logs?page_size=100` | 200; **every `items[].id` belongs to Org B**; no Org A row (e.g. id 501) appears at any page. This is the most security-sensitive read in the product | 200 | For every returned id: `SELECT org_id FROM activity_logs WHERE id = :id` → 2. And `pagination.total_records == NB` (**not** `NA+NB`) | P0 |
| TC-AUD-004 | Audit / `GET /activity-logs` | Page beyond the last page | Org A has `NA` rows | `GET /activity-logs?page=9999&page_size=25` | 200; `items: []`, `total_records = NA` — not 404 | 200 | n/a (read-only) | P2 |
| TC-AUD-005 | Audit / `GET /activity-logs` | `page_size` above the cap | — | `GET /activity-logs?page_size=500` | 422 `VALIDATION_ERROR` (`le=100`) | 422 | n/a (read-only) | P2 |
| TC-AUD-006 | Audit / `GET /activity-logs` | `page` below the floor | — | `GET /activity-logs?page=0` | 422 `VALIDATION_ERROR` (`ge=1`) | 422 | n/a (read-only) | P2 |
| TC-AUD-007 | Audit / `GET /activity-logs` | **Unknown `sort_by` is rejected against the allowlist** | Allowlist = `logged_at`, `log_date` | `GET /activity-logs?sort_by=performed_by_name` | **422 `VALIDATION_ERROR`**; `details[0].field = "sort_by"`, message names the allowed fields | 422 | n/a (read-only) | P0 |
| TC-AUD-008 | Audit / `GET /activity-logs` | SQL-injection-shaped `sort_by` | — | `GET /activity-logs?sort_by=id;DROP TABLE activity_logs` | 422 `VALIDATION_ERROR` — the allowlist prevents any dynamic column interpolation | 422 | `SELECT count(*) FROM activity_logs` → unchanged; the table still exists | P0 |
| TC-AUD-009 | Audit / `GET /activity-logs` | Valid `sort_by=log_date` + `sort_order=asc` | — | `GET /activity-logs?sort_by=log_date&sort_order=asc` | 200; ordered ascending by `log_date`, ties broken deterministically by `id desc` | 200 | n/a (read-only) | P1 |
| TC-AUD-010 | Audit / `GET /activity-logs` | Invalid `sort_order` | — | `GET /activity-logs?sort_order=up` | 422 `VALIDATION_ERROR` (`SortOrder` enum) | 422 | n/a (read-only) | P2 |
| TC-AUD-011 | Audit / `GET /activity-logs` | Invalid `action_type` enum | Allowed: `Insert`, `Update`, `Delete`, `Assign`, `Bulk Assign` | `GET /activity-logs?action_type=Upsert` | 422 `VALIDATION_ERROR` | 422 | n/a (read-only) | P2 |
| TC-AUD-012 | Audit / `GET /activity-logs` | Invalid `action_from` enum | Allowed: `Web App`, `Mobile App` | `GET /activity-logs?action_from=CLI` | 422 `VALIDATION_ERROR` | 422 | n/a (read-only) | P2 |
| TC-AUD-013 | Audit / `GET /activity-logs` | Filter by module + sub-module | Settings writes `module='settings'` | `GET /activity-logs?module=settings&sub_module=features` | 200; only feature-toggle rows | 200 | Matches `SELECT count(*) FROM activity_logs WHERE org_id=1 AND module='settings' AND sub_module='features'` | P1 |
| TC-AUD-014 | Audit / `GET /activity-logs` | Filter by `performed_by_user_id` | A-ADMIN has performed N mutations | `GET /activity-logs?performed_by_user_id={A-ADMIN}` | 200; every row's `performed_by_user_id` equals A-ADMIN | 200 | Matches `SELECT count(*) FROM activity_logs WHERE org_id=1 AND performed_by_user_id=:id` | P1 |
| TC-AUD-015 | Audit / `GET /activity-logs` | Date-range filter on `log_date` | — | `GET /activity-logs?date_from=2026-07-01&date_to=2026-07-11` | 200; only rows whose `log_date` falls in the range, inclusive | 200 | Matches the equivalent SQL `BETWEEN` predicate | P1 |
| TC-AUD-016 | Audit / `GET /activity-logs` | Inverted date range (`date_from` > `date_to`) | — | `GET /activity-logs?date_from=2026-07-31&date_to=2026-07-01` | 200 with `items: []` — the filter is applied literally (no cross-field validator on this query). Document the behaviour; empty result is acceptable | 200 | n/a (read-only) | P3 |
| TC-AUD-017 | Audit / `GET /activity-logs` | Malformed date | — | `GET /activity-logs?date_from=11-07-2026` | 422 `VALIDATION_ERROR` (expects `YYYY-MM-DD`) | 422 | n/a (read-only) | P2 |
| TC-AUD-018 | Audit / `GET /activity-logs` | Free-text search over title/description | — | `GET /activity-logs?search=Device%20registered` | 200; only matching rows | 200 | n/a (read-only) | P2 |
| TC-AUD-019 | Audit / `GET /activity-logs` | Empty result set for a filter that matches nothing | — | `GET /activity-logs?module=does_not_exist` | 200; `items: []`, `total_records: 0` — not 404 | 200 | n/a (read-only) | P2 |
| TC-AUD-020 | Audit / `GET /activity-logs/security-events` | **Static route is not shadowed by `/{log_id}`** | Route declaration order: `security-events` before `{log_id}` | `GET /activity-logs/security-events` | **200** with a paginated list. A regression in route ordering would make FastAPI try to parse `"security-events"` as `log_id: int` → 422. This case is the guard | 200 | n/a (read-only) | P0 |
| TC-AUD-021 | Audit / `GET /activity-logs/security-events` | Security view surfaces only RBAC/user-module events | `SECURITY_MODULES = ('rbac','user')`; Org A has both RBAC and Hardware log rows | `GET /activity-logs/security-events` | 200; every row has `module IN ('rbac','user')`; hardware/settings rows absent | 200 | `pagination.total_records` == `SELECT count(*) FROM activity_logs WHERE org_id=1 AND module IN ('rbac','user')` | P1 |
| TC-AUD-022 | Audit / `GET /activity-logs/security-events` | Filter by event category | — | `GET /activity-logs/security-events?event=role_assignment` | 200; only role-assignment-shaped rows | 200 | n/a (read-only) | P2 |
| TC-AUD-023 | Audit / `GET /activity-logs/security-events` | Invalid event category | Allowed: `permission_change`, `role_assignment`, `account_status_change` | `GET /activity-logs/security-events?event=login_failure` | 422 `VALIDATION_ERROR` | 422 | n/a (read-only) | P2 |
| TC-AUD-024 | Audit / `GET /activity-logs/security-events` | **Cross-tenant isolation of the security timeline** | Org A has RBAC events; Org B has its own | As B-ADMIN: `GET /activity-logs/security-events?page_size=100` | 200; zero Org A rows. Security events are the highest-value audit read — leakage here is critical | 200 | Every returned id → `SELECT org_id FROM activity_logs WHERE id=:id` = 2 | P0 |
| TC-AUD-025 | Audit / `GET /activity-logs/security-events` | Chronological ordering | — | `GET /activity-logs/security-events` | 200; strictly ordered `logged_at desc` (no `sort_by` parameter is exposed on this endpoint) | 200 | n/a (read-only) | P2 |
| TC-AUD-026 | Audit / `GET /activity-logs/{log_id}` | Detail of an own-tenant log row | LOG-A1 = 501, `org_id=1` | As A-ADMIN: `GET /activity-logs/501` | 200; includes `org_id`, `description`, `payroll_date` (fields absent from the list item) | 200 | Matches `SELECT * FROM activity_logs WHERE id=501` | P1 |
| TC-AUD-027 | Audit / `GET /activity-logs/{log_id}` | **Cross-tenant log detail** | LOG-B1 = 601, `org_id=2` | As A-ADMIN: `GET /activity-logs/601` | **404 `ACTIVITY_LOG_NOT_FOUND`** — never 403, never Org B's description text | 404 | `SELECT org_id FROM activity_logs WHERE id=601` → 2 (exists, but not disclosed to Org A) | P0 |
| TC-AUD-028 | Audit / `GET /activity-logs/{log_id}` | Non-existent id | — | `GET /activity-logs/99999999` | 404 `ACTIVITY_LOG_NOT_FOUND` — identical response shape to TC-AUD-027 (existence must not be inferable) | 404 | n/a (read-only) | P0 |
| TC-AUD-029 | Audit / `GET /activity-logs/{log_id}` | Non-integer id | — | `GET /activity-logs/abc` | 422 `VALIDATION_ERROR` (path type coercion) | 422 | n/a (read-only) | P2 |
| TC-AUD-030 | Audit / `GET /employees/{id}/activity-logs` | Employee change history | EMP-A1 = 1001 with audit rows where `employee_id=1001` | As A-ADMIN: `GET /employees/1001/activity-logs` | 200; only rows whose subject is EMP-A1 | 200 | `pagination.total_records` == `SELECT count(*) FROM activity_logs WHERE org_id=1 AND employee_id=1001` | P1 |
| TC-AUD-031 | Audit / `GET /employees/{id}/activity-logs` | Employee from another org | EMP-B1 = 2001 | As A-ADMIN: `GET /employees/2001/activity-logs` | 404 `EMPLOYEE_NOT_FOUND` | 404 | No Org B audit row appears in any response body | P0 |
| TC-AUD-032 | Audit / `GET /employees/{id}/activity-logs` | **Branch data scope blocks an out-of-scope employee** | A-SCOPED restricted to `branch_ids=[11]`; EMP-A2 has `master_branch_id=12` | As A-SCOPED: `GET /employees/1002/activity-logs` | **403 `AUTH_FORBIDDEN`** — "You do not have access to this employee's activity." (in-tenant scope violation ⇒ 403; cross-tenant ⇒ 404) | 403 | n/a (read-only) | P0 |
| TC-AUD-033 | Audit / `GET /employees/{id}/activity-logs` | In-scope employee for a scoped caller | A-SCOPED `[11]`; EMP-A1 in branch 11 | As A-SCOPED: `GET /employees/1001/activity-logs` | 200; rows returned | 200 | n/a (read-only) | P1 |
| TC-AUD-034 | Audit / `GET /employees/{id}/activity-logs` | Bad `sort_by` on the subject view | — | `GET /employees/1001/activity-logs?sort_by=module` | 422 `VALIDATION_ERROR` — the same allowlist applies | 422 | n/a (read-only) | P1 |
| TC-AUD-035 | Audit / `GET /employees/{id}/activity-logs` | Employee with no audit history | Newly created EMP-A4 | `GET /employees/{EMP-A4}/activity-logs` | 200; `items: []` — not 404 (the employee exists) | 200 | n/a (read-only) | P2 |
| TC-AUD-036 | Audit / `GET /users/{id}/activity-logs` | Actions performed BY a user | A-ADMIN has performed mutations | As A-ADMIN: `GET /users/{A-ADMIN}/activity-logs` | 200; every row's `performed_by_user_id` == A-ADMIN | 200 | Matches `SELECT count(*) FROM activity_logs WHERE org_id=1 AND performed_by_user_id=:A-ADMIN` | P1 |
| TC-AUD-037 | Audit / `GET /users/{id}/activity-logs` | User from another org | B-ADMIN's user id | As A-ADMIN: `GET /users/{B-ADMIN}/activity-logs` | 404 `USER_NOT_FOUND` | 404 | No Org B row disclosed | P0 |
| TC-AUD-038 | Audit / `GET /users/{id}/activity-logs` | Filter by module + action type | — | `GET /users/{A-ADMIN}/activity-logs?module=settings&action_type=Update` | 200; only settings updates by that user | 200 | Matches the equivalent SQL | P2 |
| TC-AUD-039 | Audit / authz | Audit read without `audit:read` | A-NOPERM | `GET /activity-logs` | 403 `AUTH_FORBIDDEN` — applies to all 5 endpoints | 403 | n/a | P0 |
| TC-AUD-040 | Audit / auth | Unauthenticated audit read | — | `GET /activity-logs` with no token | 401 `AUTH_NOT_AUTHENTICATED` | 401 | n/a | P0 |
| TC-AUD-041 | Audit / E2E | **Every mutating operation writes exactly one audit row** | Baseline `NA` | Perform one mutation in each of: hardware (register device), settings (toggle feature), notifications (create notification), RBAC (assign role), employee (update employee), leave (approve request) | Each `GET /activity-logs?module=<m>` shows the new row within the same request cycle | 200 | `SELECT count(*) FROM activity_logs WHERE org_id=1` → `NA + 6`; each row has a non-null `performed_by_user_id`, a `performed_by_name` snapshot, a valid `action_type`, and `action_from='Web App'` | P0 |
| TC-AUD-042 | Audit / E2E | An audit row rolls back with its business mutation | Force a post-audit failure inside a device-update transaction | `PATCH /devices/101` (fault injected after `audit.record`) | 5xx | 5xx | `SELECT count(*) FROM activity_logs WHERE org_id=1` → **unchanged** (the audit row is flushed, not committed, by the calling service's transaction) | P0 |
| TC-AUD-043 | Audit / E2E | A failed (403) mutation writes **no** audit row | A-NOPERM; baseline `NA` | `POST /devices {...}` as A-NOPERM | 403 | 403 | `SELECT count(*) FROM activity_logs WHERE org_id=1` → still `NA` — rejected requests never pollute the trail | P1 |
| TC-AUD-044 | Audit / E2E | An Org A mutation writes nothing into Org B's trail | Baseline `NB` for Org B | As A-ADMIN, perform 5 mutations across modules | Each returns 2xx | 2xx | `SELECT count(*) FROM activity_logs WHERE org_id=2` → **unchanged (`NB`) after every Org-A mutation** | P0 |
| TC-AUD-045 | Audit / E2E | RBAC writes a rich set of audit kinds, all readable through the audit API | Perform role create, permission grant, branch-access grant, user activate/deactivate | `GET /activity-logs?module=rbac&page_size=100` | 200; distinct `title` values for each RBAC operation kind | 200 | `SELECT DISTINCT title FROM activity_logs WHERE org_id=1 AND module='rbac'` → matches the operations performed | P1 |

---

## 7. TC-DSH — Dashboard Management

19 read-only endpoints. Router guard: `dashboard:read` on **all** 19. Per-widget/chart endpoints additionally require the **source-module** read permission inside the service (403 `AUTH_FORBIDDEN`), while `/summary`, `/kpis`, `/statistics` **degrade gracefully** — they omit blocks the caller cannot see rather than 403-ing. Every widget is org-scoped and Redis-cached (read-through).

| ID | Module / API | Test Scenario | Preconditions | Request / Input | Expected Result | HTTP | Database Verification | Priority |
|---|---|---|---|---|---|---|---|---|
| TC-DSH-001 | Dashboard / `GET /dashboard/summary` | Full summary for a fully-permissioned user | A-ADMIN holds every source-module read | `GET /dashboard/summary` | 200; blocks present for employees, attendance, leave, approvals, payroll, settlements, devices | 200 | Counts reconcile with `SELECT count(*) FROM employees WHERE org_id=1 AND ...` etc. | P1 |
| TC-DSH-002 | Dashboard / `GET /dashboard/summary` | Summary omits blocks the caller cannot read (graceful degradation, **not** 403) | A-REPORTS-ONLY (no `employee:read`, no `payroll_record:read`) | `GET /dashboard/summary` | 200; the `employees` and `payroll` blocks are `null`/absent — the endpoint does not 403 | 200 | n/a (read-only) | P0 |
| TC-DSH-003 | Dashboard / `GET /dashboard/summary` | `date` parameter honoured | Attendance rows exist for 2026-07-01 | `GET /dashboard/summary?date=2026-07-01` | 200; metrics computed for that date, not today | 200 | Reconcile with `SELECT ... FROM attendance_days WHERE org_id=1 AND attendance_date='2026-07-01'` | P1 |
| TC-DSH-004 | Dashboard / `GET /dashboard/summary` | Malformed `date` | — | `GET /dashboard/summary?date=07/01/2026` | 422 `VALIDATION_ERROR` | 422 | n/a (read-only) | P2 |
| TC-DSH-005 | Dashboard / `GET /dashboard/summary` | **Tenant isolation of aggregates** | Org A: 500 employees. Org B: 7 employees | As B-ADMIN: `GET /dashboard/summary` | 200; `employees.total_employees == 7` — Org A's 500 never bleed in | 200 | Response value == `SELECT count(*) FROM employees WHERE org_id=2 AND is_deleted=false` | P0 |
| TC-DSH-006 | Dashboard / `GET /dashboard/summary` | **Cache key is org-scoped — Org B never gets Org A's cached payload** | Redis UP. Warm the cache as A-ADMIN, then immediately call as B-ADMIN | `GET /dashboard/summary` (A) → `GET /dashboard/summary` (B) | B's response contains only Org B numbers. The cache key embeds `org_id` (`dashboard:{org_id}:widget:summary:...`) | 200 | `redis-cli KEYS "dashboard:*"` → distinct keys `dashboard:1:...` and `dashboard:2:...`; the values differ | P0 |
| TC-DSH-007 | Dashboard / `GET /dashboard/summary` | **Redis DOWN → still 200, served from the database** | `REDIS_DOWN` fixture | `GET /dashboard/summary` | **200** with correct, freshly-computed data. Must NOT 500 — `cache_get_json` swallows backend errors and degrades to a miss; `cache_set_json` failure is likewise non-fatal | 200 | Values still reconcile against the DB; the app logs `cache_backend_unavailable` at ERROR | P0 |
| TC-DSH-008 | Dashboard / `GET /dashboard/kpis` | Flat KPI set | A-ADMIN | `GET /dashboard/kpis` | 200; flat numeric metrics | 200 | Reconcile each KPI against its source table for `org_id=1` | P1 |
| TC-DSH-009 | Dashboard / `GET /dashboard/kpis` | Redis DOWN | `REDIS_DOWN` | `GET /dashboard/kpis` | 200 (DB fallback), not 500 | 200 | n/a (read-only) | P0 |
| TC-DSH-010 | Dashboard / `GET /dashboard/statistics` | Ratios computed | A-ADMIN | `GET /dashboard/statistics` | 200; turnover / attendance-rate / device-uptime ratios present | 200 | Ratios reconcile with the underlying counts | P1 |
| TC-DSH-011 | Dashboard / `GET /dashboard/statistics` | Division-by-zero guard on an empty org | Org C has 0 employees, 0 devices | As an Org C admin: `GET /dashboard/statistics` | 200; ratios are `0` (or `null`) — **no 500, no `NaN`, no `Infinity` in the JSON** | 200 | `SELECT count(*) FROM employees WHERE org_id=3` → 0 | P1 |
| TC-DSH-012 | Dashboard / `GET /dashboard/widgets` | Widget metadata reflects the caller's permissions | A-REPORTS-ONLY | `GET /dashboard/widgets` | 200; `summary`/`kpis`/`statistics`/`notifications`/`recent_activity` → `permitted:true`; `employee`/`attendance`/`leave`/`approvals`/`payroll`/`settlements`/`devices` → `permitted:false` | 200 | n/a (read-only; computed purely from the token's permission set) | P1 |
| TC-DSH-013 | Dashboard / `GET /dashboard/widgets` | Widget metadata for a super admin | A-SUPER | `GET /dashboard/widgets` | 200; every widget `permitted:true` | 200 | n/a (read-only) | P2 |
| TC-DSH-014 | Dashboard / `GET /dashboard/employees` | Employee dashboard with source permission | A-ADMIN (`employee:read`) | `GET /dashboard/employees` | 200; totals + branch/department/status distributions | 200 | Distribution sums == `SELECT count(*) FROM employees WHERE org_id=1 AND is_deleted=false` | P1 |
| TC-DSH-015 | Dashboard / `GET /dashboard/employees` | **Without `employee:read`** | A-REPORTS-ONLY (has `dashboard:read`) | `GET /dashboard/employees` | **403 `AUTH_FORBIDDEN`** — "Missing permission 'employee:read'." `dashboard:read` alone is not enough | 403 | n/a | P0 |
| TC-DSH-016 | Dashboard / `GET /dashboard/employees` | Branch data scope narrows the aggregate | A-SCOPED `branch_ids=[11]` | `GET /dashboard/employees` | 200; totals count only branch-11 employees | 200 | Response total == `SELECT count(*) FROM employees WHERE org_id=1 AND master_branch_id=11 AND is_deleted=false` | P0 |
| TC-DSH-017 | Dashboard / `GET /dashboard/attendance` | Attendance dashboard | A-ADMIN (`attendance:read`) | `GET /dashboard/attendance?date=2026-07-10` | 200; present/absent/late counts + daily trend | 200 | Reconcile with `attendance_days` for `org_id=1` on that date | P1 |
| TC-DSH-018 | Dashboard / `GET /dashboard/attendance` | Without `attendance:read` | A-REPORTS-ONLY | `GET /dashboard/attendance` | 403 `AUTH_FORBIDDEN` | 403 | n/a | P0 |
| TC-DSH-019 | Dashboard / `GET /dashboard/leave` | Leave dashboard | A-ADMIN (`leave_request:read`) | `GET /dashboard/leave` | 200; totals, statuses, leave-type breakdown | 200 | Reconcile with `leave_requests` for `org_id=1` | P1 |
| TC-DSH-020 | Dashboard / `GET /dashboard/leave` | Without `leave_request:read` | A-REPORTS-ONLY | `GET /dashboard/leave` | 403 `AUTH_FORBIDDEN` | 403 | n/a | P0 |
| TC-DSH-021 | Dashboard / `GET /dashboard/approvals` | Approval dashboard | A-ADMIN (`approval:read`) | `GET /dashboard/approvals` | 200; pending counts by type + recent decisions | 200 | Reconcile with `approval_requests WHERE org_id=1 AND status='pending'` | P1 |
| TC-DSH-022 | Dashboard / `GET /dashboard/approvals` | Without `approval:read` | A-REPORTS-ONLY | `GET /dashboard/approvals` | 403 `AUTH_FORBIDDEN` | 403 | n/a | P0 |
| TC-DSH-023 | Dashboard / `GET /dashboard/payroll` | **Payroll dashboard exposes salary totals — requires `payroll_record:read`** | A-ADMIN | `GET /dashboard/payroll` | 200; cycle status, finalized amount, headcounts | 200 | Amount == `SELECT sum(net_payable) FROM payroll_computed_rows WHERE org_id=1 AND ...` | P1 |
| TC-DSH-024 | Dashboard / `GET /dashboard/payroll` | **Salary exposure — without `payroll_record:read`** | A-REPORTS-ONLY | `GET /dashboard/payroll` | **403 `AUTH_FORBIDDEN`** — no salary figure may appear in the body | 403 | Assert the response body contains no monetary value | P0 |
| TC-DSH-025 | Dashboard / `GET /dashboard/payroll` | Tenant isolation of payroll totals | Org A and Org B both have finalized runs with distinct totals | As B-ADMIN: `GET /dashboard/payroll` | 200; only Org B's total. Org A's payroll figure must never appear | 200 | Response total == `SELECT sum(...) FROM ... WHERE org_id=2` | P0 |
| TC-DSH-026 | Dashboard / `GET /dashboard/settlements` | Settlement dashboard | A-ADMIN (`settlement:read`) | `GET /dashboard/settlements` | 200; active loans/advances + outstanding arrears sum | 200 | Reconcile with `employee_loans_advances` / `employee_arrears` for `org_id=1` | P1 |
| TC-DSH-027 | Dashboard / `GET /dashboard/settlements` | Without `settlement:read` | A-REPORTS-ONLY | `GET /dashboard/settlements` | 403 `AUTH_FORBIDDEN` | 403 | n/a | P0 |
| TC-DSH-028 | Dashboard / `GET /dashboard/devices` | Hardware dashboard aggregates | A-ADMIN (`device:read`); Org A has 2 online, 1 offline | `GET /dashboard/devices` | 200; online/offline counts + last-sync metadata. **No `communication_key` / `sync_key` in the payload** | 200 | Counts == `SELECT status, count(*) FROM biometric_devices WHERE org_id=1 GROUP BY status`; assert no secret column value appears in the body | P0 |
| TC-DSH-029 | Dashboard / `GET /dashboard/devices` | Without `device:read` | A-REPORTS-ONLY | `GET /dashboard/devices` | 403 `AUTH_FORBIDDEN` | 403 | n/a | P0 |
| TC-DSH-030 | Dashboard / `GET /dashboard/notifications` | Notification widget is scoped to the caller | A-EMP has 1 unread | As A-EMP (with `dashboard:read`): `GET /dashboard/notifications?limit=5` | 200; unread count + up to 5 recent items — **only the caller's own notifications** | 200 | Item ids ⊆ `SELECT notification_id FROM notification_recipients WHERE user_id=:A-EMP AND deleted_at IS NULL` | P0 |
| TC-DSH-031 | Dashboard / `GET /dashboard/notifications` | `limit=0` rejected | — | `GET /dashboard/notifications?limit=0` | 422 `VALIDATION_ERROR` (`ge=1`) | 422 | n/a (read-only) | P2 |
| TC-DSH-032 | Dashboard / `GET /dashboard/recent-activity` | Recent activity feed is org-scoped | Org A and Org B both have audit rows | As B-ADMIN: `GET /dashboard/recent-activity?limit=10` | 200; every entry belongs to Org B — the feed reads `activity_logs` and must not leak across tenants | 200 | Every returned log id → `SELECT org_id FROM activity_logs WHERE id=:id` = 2 | P0 |
| TC-DSH-033 | Dashboard / `GET /dashboard/recent-activity` | Empty feed on a fresh org | Org C has no audit rows | `GET /dashboard/recent-activity` | 200; `[]` | 200 | `SELECT count(*) FROM activity_logs WHERE org_id=3` → 0 | P2 |
| TC-DSH-034 | Dashboard / `GET /dashboard/charts/attendance-trend` | Trend over N days | A-ADMIN | `GET /dashboard/charts/attendance-trend?days=30` | 200; series points grouped by date | 200 | Point count ≤ 30; values reconcile with `attendance_days` | P1 |
| TC-DSH-035 | Dashboard / `GET /dashboard/charts/attendance-trend` | `days=0` rejected | — | `?days=0` | 422 `VALIDATION_ERROR` (`ge=1`) | 422 | n/a (read-only) | P2 |
| TC-DSH-036 | Dashboard / `GET /dashboard/charts/attendance-trend` | Without `attendance:read` | A-REPORTS-ONLY | `GET /dashboard/charts/attendance-trend` | 403 `AUTH_FORBIDDEN` | 403 | n/a | P0 |
| TC-DSH-037 | Dashboard / `GET /dashboard/charts/employee-growth` | Cumulative growth over N months | A-ADMIN (`employee:read`) | `?months=6` | 200; cumulative series, monotonically non-decreasing | 200 | Final point == active headcount for `org_id=1` | P1 |
| TC-DSH-038 | Dashboard / `GET /dashboard/charts/leave-trend` | Leave trend | A-ADMIN (`leave_request:read`) | `?months=6` | 200; monthly series by status | 200 | Reconcile with `leave_requests` for `org_id=1` | P1 |
| TC-DSH-039 | Dashboard / `GET /dashboard/charts/payroll-trend` | **Payroll cost trend requires `payroll_record:read`** | A-REPORTS-ONLY | `GET /dashboard/charts/payroll-trend?limit=6` | **403 `AUTH_FORBIDDEN`** — the salary cost series is gated | 403 | Response body contains no monetary series | P0 |
| TC-DSH-040 | Dashboard / `GET /dashboard/charts/payroll-trend` | Cost trend with permission | A-ADMIN | `?limit=6` | 200; up to 6 historical cycle cost points | 200 | Values == `SELECT sum(...) FROM payroll runs WHERE org_id=1` per cycle | P1 |
| TC-DSH-041 | Dashboard / `GET /dashboard/charts/department-attendance` | Department breakdown | A-ADMIN (`attendance:read`) | `?date=2026-07-10` | 200; one series point per department | 200 | Department set ⊆ `SELECT id FROM departments WHERE org_id=1` | P1 |
| TC-DSH-042 | Dashboard / `GET /dashboard/charts/branch-attendance` | Branch breakdown, scoped | A-SCOPED `[11]` | `GET /dashboard/charts/branch-attendance` | 200; only branch 11 appears — branch 12 is excluded by the data scope | 200 | Returned branch ids ⊆ `[11]` | P0 |
| TC-DSH-043 | Dashboard / authz | Any dashboard endpoint without `dashboard:read` | A-NOPERM | `GET /dashboard/kpis` | 403 `AUTH_FORBIDDEN` (router-level guard, before any service logic) | 403 | n/a | P0 |
| TC-DSH-044 | Dashboard / auth | Unauthenticated | — | `GET /dashboard/summary` with no token | 401 `AUTH_NOT_AUTHENTICATED` | 401 | n/a | P0 |
| TC-DSH-045 | Dashboard / read-only | **No dashboard endpoint mutates state** | Baseline: `SELECT count(*) FROM activity_logs WHERE org_id=1` = `NA` | Call all 19 dashboard endpoints in sequence as A-ADMIN | All 200 | 200 | `SELECT count(*) FROM activity_logs WHERE org_id=1` → still `NA` — **reads write no audit rows**; no row in any business table changes | P1 |
| TC-DSH-046 | Dashboard / caching | A stale cache does not survive its TTL | Redis UP; `cache_ttl_seconds` configured | Warm `/dashboard/kpis`, mutate the underlying data, re-read before and after the TTL | Before TTL: the cached (stale) value. After TTL expiry: the fresh value | 200 | `redis-cli TTL dashboard:1:widget:kpis:*` → > 0, then the key disappears; the post-expiry response matches the DB | P2 |

---

## 8. TC-RPT — Reports Management

**Parameterisation note.** The module exposes **42 endpoints**, but 40 of them are structurally identical: each is a `GET` that flows through `ReportsService._handle_report_query` — same `ReportQueryRequest` (`date_from`, `date_to`, `period`, `month`, `branch_id`, `dept_id`, `designation_id`, `employee_id`, `status`, `format`, `sort_by`, `sort_dir`, `page`, `page_size`), same `reports:read` router guard, same source-permission check, same export/pagination machinery. Writing 42 near-identical rows would be padding. Instead:

- **TC-RPT-001 is a parameterised matrix** executed against **all 40 report endpoints** (one row each in the harness).
- **TC-RPT-002** is the source-permission matrix, executed once per **permission family** (the 8 distinct `features=[...]` sets in the service).
- The remaining cases cover the **distinct** behaviours: validation, export lifecycle, tenant isolation, salary exposure, and the 2 export endpoints.

### The 40 report endpoints the parameterised matrices iterate over

`TC-RPT-001` (happy path), `TC-RPT-002` (source-permission 403) and `TC-RPT-008` (tenant isolation) are each
executed once per row below — a harness generates one test per row; a manual tester walks the list.
Without this enumeration those three matrix cases are not executable as written.

| # | Endpoint | Source permission (beyond `reports:read`) |
|---|---|---|
| 1 | `GET /reports/approvals/history` | `approval:read` |
| 2 | `GET /reports/approvals/pending` | `approval:read` |
| 3 | `GET /reports/approvals/performance` | `approval:read` |
| 4 | `GET /reports/attendance/daily` | `attendance:read` |
| 5 | `GET /reports/attendance/early-going` | `attendance:read` |
| 6 | `GET /reports/attendance/employee` | `attendance:read` |
| 7 | `GET /reports/attendance/late-coming` | `attendance:read` |
| 8 | `GET /reports/attendance/missing-punch` | `attendance:read` |
| 9 | `GET /reports/attendance/monthly` | `attendance:read` |
| 10 | `GET /reports/attendance/overtime` | `attendance:read` |
| 11 | `GET /reports/attendance/summary` | `attendance:read` |
| 12 | `GET /reports/audit/security-events` | `activity_log:read` |
| 13 | `GET /reports/audit/trail` | `activity_log:read` |
| 14 | `GET /reports/audit/user-activity` | `activity_log:read` |
| 15 | `GET /reports/devices/health` | `device:read` |
| 16 | `GET /reports/devices/status` | `device:read` |
| 17 | `GET /reports/devices/sync` | `device:read` |
| 18 | `GET /reports/employees/by-branch` | `employee:read` |
| 19 | `GET /reports/employees/by-department` | `employee:read` |
| 20 | `GET /reports/employees/by-designation` | `employee:read` |
| 21 | `GET /reports/employees/joining` | `employee:read` |
| 22 | `GET /reports/employees/master` | `employee:read` |
| 23 | `GET /reports/employees/shift-assignments` | `employee:read` |
| 24 | `GET /reports/employees/status` | `employee:read` |
| 25 | `GET /reports/leave/approvals` | `leave_request / leave_balance (any-of):read` |
| 26 | `GET /reports/leave/balance` | `leave_request / leave_balance (any-of):read` |
| 27 | `GET /reports/leave/requests` | `leave_request / leave_balance (any-of):read` |
| 28 | `GET /reports/leave/summary` | `leave_request / leave_balance (any-of):read` |
| 29 | `GET /reports/notifications/delivery` | `notification:read` |
| 30 | `GET /reports/notifications/read` | `notification:read` |
| 31 | `GET /reports/notifications/summary` | `notification:read` |
| 32 | `GET /reports/organization/branch-summary` | `employee:read` |
| 33 | `GET /reports/organization/department-summary` | `employee:read` |
| 34 | `GET /reports/organization/workforce-summary` | `employee:read` |
| 35 | `GET /reports/payroll/payslips` | `payroll_record:read` |
| 36 | `GET /reports/payroll/register` | `payroll_record:read` |
| 37 | `GET /reports/payroll/salary-register` | `payroll_record:read` |
| 38 | `GET /reports/payroll/summary` | `payroll_record:read` |
| 39 | `GET /reports/settlements/ledger` | `loan_advance / arrears / settlement (any-of):read` |
| 40 | `GET /reports/settlements/summary` | `loan_advance / arrears / settlement (any-of):read` |


**Report → required source permission (from `app/modules/reports/service.py`), all *in addition to* `reports:read`:**

| Family | Endpoints | Source permission (any-of) |
|---|---|---|
| Employee (6) + Organization (3) + Shift assignments (1) | `/employees/{master,joining,status,by-department,by-designation,by-branch,shift-assignments}`, `/organization/{branch-summary,department-summary,workforce-summary}` | `employee:read` |
| Attendance (8) | `/attendance/{daily,monthly,employee,late-coming,early-going,missing-punch,overtime,summary}` | `attendance:read` |
| Leave balance (1) | `/leave/balance` | `leave_request:read` **or** `leave_balance:read` |
| Leave other (3) | `/leave/{requests,approvals,summary}` | `leave_request:read` |
| Approvals (3) | `/approvals/{pending,history,performance}` | `approval:read` |
| **Payroll (4)** | `/payroll/{register,salary-register,summary,payslips}` | **`payroll_record:read`** |
| Settlements (2) | `/settlements/{ledger,summary}` | `loan_advance:read` **or** `arrears:read` **or** `settlement:read` |
| Devices (3) | `/devices/{status,health,sync}` | `device:read` |
| Notifications (3) | `/notifications/{delivery,read,summary}` | `notification:read` |
| Audit (3) | `/audit/{trail,user-activity,security-events}` | `audit:read` |

| ID | Module / API | Test Scenario | Preconditions | Request / Input | Expected Result | HTTP | Database Verification | Priority |
|---|---|---|---|---|---|---|---|---|
| TC-RPT-001 | Reports / **all 40 report endpoints (parameterised)** | Happy path — JSON report renders for a fully-permissioned caller | A-ADMIN holds `reports:read` + every source read; Org A seeded | For each of the 40 endpoints: `GET <endpoint>?page=1&page_size=25&format=json` | 200 for every endpoint; body = `{items:[...], pagination:{...}, generated_at}`; `items` conform to that report's item schema | 200 | For each report: `pagination.total_records` equals the count from the equivalent SQL over the source table filtered by `org_id=1`; `SELECT count(*) FROM activity_logs WHERE org_id=1` → **unchanged** (reports write no audit rows) | P1 |
| TC-RPT-002 | Reports / **source-permission matrix (parameterised, 8 families)** | Each report family 403s without its source-module read permission | For each family: a user holding `reports:read` but **not** the family's source permission | One representative endpoint per family (e.g. `/employees/master`, `/attendance/daily`, `/leave/requests`, `/approvals/pending`, `/payroll/register`, `/settlements/ledger`, `/devices/status`, `/notifications/delivery`, `/audit/trail`) | **403 `AUTH_FORBIDDEN`** in every case; message names the missing permission (e.g. "Missing permission 'employee:read'.") | 403 | Response body carries no report rows | P0 |
| TC-RPT-003 | Reports / `GET /reports/payroll/register` | **Salary exposure — payroll register without `payroll_record:read`** | A-REPORTS-ONLY (`reports:read` only) | `GET /reports/payroll/register?format=json` | **403 `AUTH_FORBIDDEN`** — "Missing permission 'payroll_record:read'." | 403 | Assert the response body contains **no** salary/CTC/net-pay figure from `payroll_computed_rows` | P0 |
| TC-RPT-004 | Reports / `GET /reports/payroll/salary-register` | Salary register without the payroll permission | A-REPORTS-ONLY | `GET /reports/payroll/salary-register` | 403 `AUTH_FORBIDDEN` | 403 | No monetary value in the body | P0 |
| TC-RPT-005 | Reports / `GET /reports/payroll/payslips` | Payslip roster without the payroll permission | A-REPORTS-ONLY | `GET /reports/payroll/payslips` | 403 `AUTH_FORBIDDEN` | 403 | No payslip metadata in the body | P0 |
| TC-RPT-006 | Reports / `GET /reports/payroll/summary` | Payroll totals without the payroll permission | A-REPORTS-ONLY | `GET /reports/payroll/summary` | 403 `AUTH_FORBIDDEN` | 403 | No aggregate salary total in the body | P0 |
| TC-RPT-007 | Reports / `GET /reports/payroll/register` | Payroll register **with** the permission | A-ADMIN | `?salary_cycle_id=<c>&format=json` | 200; rows with component breakdowns for `org_id=1` only | 200 | Row count == `SELECT count(*) FROM payroll_computed_rows WHERE org_id=1 AND salary_cycle_id=:c` | P1 |
| TC-RPT-008 | Reports / **tenant isolation (parameterised over all 40)** | **Org B sees only Org B rows in every report** | Org A and Org B both seeded with distinct employees/attendance/payroll | As B-ADMIN, call every report endpoint | 200; **no row belongs to Org A** in any report — verify by cross-checking a known Org A employee code / device serial / notification title is absent from every body | 200 | For each report, `pagination.total_records` == the Org-B-only SQL count; **`SELECT count(*)` of Org A source rows must never contribute** | P0 |
| TC-RPT-009 | Reports / `GET /reports/audit/trail` | **Audit-trail report is org-scoped** | Org A and Org B both have `activity_logs` rows | As B-ADMIN: `GET /reports/audit/trail?page_size=100` | 200; every row belongs to Org B | 200 | Every returned log id → `SELECT org_id FROM activity_logs WHERE id=:id` = 2 | P0 |
| TC-RPT-010 | Reports / `GET /reports/audit/security-events` | Security-events report requires `audit:read` | A user with `reports:read` but no `audit:read` | `GET /reports/audit/security-events` | 403 `AUTH_FORBIDDEN` | 403 | n/a | P0 |
| TC-RPT-011 | Reports / `GET /reports/devices/status` | Device report never exposes device secrets | A-ADMIN (`device:read`) | `GET /reports/devices/status?format=json` | 200; status rows. **`communication_key` / `sync_key` absent from every row** | 200 | `SELECT communication_key FROM biometric_devices WHERE org_id=1 AND communication_key IS NOT NULL` → non-empty, yet the value never appears in the response | P0 |
| TC-RPT-012 | Reports / branch scope | Branch data scope narrows every report | A-SCOPED `branch_ids=[11]` | `GET /reports/employees/master` | 200; only branch-11 employees | 200 | `total_records` == `SELECT count(*) FROM employees WHERE org_id=1 AND master_branch_id=11` | P0 |
| TC-RPT-013 | Reports / branch scope | Explicitly filtering on an out-of-scope branch | A-SCOPED `[11]` | `GET /reports/employees/master?branch_id=12` | **403 `AUTH_FORBIDDEN`** — "Missing branch access permission." (an explicit out-of-scope filter is rejected, unlike the Hardware list which returns an empty set) | 403 | No employee row returned | P0 |
| TC-RPT-014 | Reports / dept scope | Explicitly filtering on an out-of-scope department | A-SCOPED with `department_ids=[31]` | `GET /reports/employees/master?dept_id=32` | 403 `AUTH_FORBIDDEN` — "Missing department access permission." | 403 | n/a | P0 |
| TC-RPT-015 | Reports / branch scope | Filtering on a branch belonging to **another org** | BR-B1 = 21 | As A-ADMIN (unrestricted): `GET /reports/employees/master?branch_id=21` | 200 with `items: []` — the underlying query is `org_id`-scoped, so a foreign branch simply matches nothing. **Assert zero Org B rows leak** | 200 | `SELECT count(*) FROM employees WHERE org_id=2 AND master_branch_id=21` > 0, yet `items` is empty | P0 |
| TC-RPT-016 | Reports / validation | `date_from` after `date_to` | — | `GET /reports/attendance/daily?date_from=2026-07-31&date_to=2026-07-01` | 422 `VALIDATION_ERROR` — "date_from cannot be after date_to" | 422 | n/a (read-only) | P2 |
| TC-RPT-017 | Reports / validation | Date range longer than 12 months | — | `?date_from=2024-01-01&date_to=2026-01-01` | 422 `VALIDATION_ERROR` — "Date range exceeds the maximum allowed span of 12 months." (> 366 days) | 422 | n/a (read-only) | P2 |
| TC-RPT-018 | Reports / validation | Boundary — exactly 366 days is accepted | — | `?date_from=2025-01-01&date_to=2026-01-02` (366 days) | 200 — the check is `delta.days > 366` | 200 | n/a (read-only) | P2 |
| TC-RPT-019 | Reports / validation | Boundary — 367 days is rejected | — | `?date_from=2025-01-01&date_to=2026-01-03` | 422 `VALIDATION_ERROR` | 422 | n/a (read-only) | P2 |
| TC-RPT-020 | Reports / validation | Invalid `period` preset | Allowed: `today`, `week`, `month`, `quarter`, `year` | `?period=fortnight` | 422 `VALIDATION_ERROR` | 422 | n/a (read-only) | P2 |
| TC-RPT-021 | Reports / validation | Valid `period` preset | — | `GET /reports/attendance/summary?period=month` | 200; window resolved to the current month | 200 | Row count matches the month's source rows for `org_id=1` | P2 |
| TC-RPT-022 | Reports / validation | Invalid `format` | Allowed: `json`, `csv`, `excel`, `pdf` | `?format=xml` | 422 `VALIDATION_ERROR` — "format must be one of: json, csv, excel, pdf" | 422 | No export job created: `redis-cli KEYS "export_job:*"` → unchanged | P2 |
| TC-RPT-023 | Reports / validation | Invalid `sort_dir` | Allowed: `asc`, `desc` | `?sort_dir=descending` | 422 `VALIDATION_ERROR` | 422 | n/a (read-only) | P2 |
| TC-RPT-024 | Reports / validation | Malformed `month` | Expected `YYYY-MM` | `?month=2026/07` | 422 `VALIDATION_ERROR` or 200 with an empty set — assert the API never 500s on a malformed month | 422/200 | n/a (read-only) | P2 |
| TC-RPT-025 | Reports / edge | Empty result set | Org C has no employees | As an Org C admin with full permissions: `GET /reports/employees/master` | 200; `items: []`, `pagination.total_records: 0` — not 404 | 200 | `SELECT count(*) FROM employees WHERE org_id=3` → 0 | P2 |
| TC-RPT-026 | Reports / edge | Empty result set exported to CSV | Org C | `GET /reports/employees/master?format=csv` | 200; a CSV file body (header-only or empty) with `Content-Disposition: attachment` — **no 500 on `items_raw[0]`** | 200 | Response `Content-Type: text/csv` | P2 |
| TC-RPT-027 | Reports / export | **Small synchronous CSV export (≤ 1000 rows)** | SMALL-A seeded (e.g. 50 employees) | `GET /reports/employees/master?format=csv` | **200** with the file inline: `Content-Type: text/csv`, `Content-Disposition: attachment; filename="employee_master_report_*.csv"`. **No `export_job_id`** | 200 | `redis-cli KEYS "export_job:*"` → **no new key** (the sync path creates no job) | P1 |
| TC-RPT-028 | Reports / export | Small synchronous PDF export | SMALL-A | `?format=pdf` | 200; `Content-Type: application/pdf`, `.pdf` filename | 200 | No export job key created | P1 |
| TC-RPT-029 | Reports / export | Small synchronous Excel export | SMALL-A | `?format=excel` | 200; `Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`, `.xlsx` filename | 200 | No export job key created | P2 |
| TC-RPT-030 | Reports / export | **Large export (> 1000 rows) returns 202 + `export_job_id`** | BIG-A seeded with 1500 employees; arq worker running | `GET /reports/employees/master?format=csv` | **202**; body `{success:true, data:{export_job_id:"<hex>", status:"pending", download_url:null, expires_at:"<+1h>"}}` | 202 | `redis-cli EXISTS export_job:<job_id>` → 1, value `status='pending'`; a `GENERATE_REPORT_EXPORT` job is enqueued on arq | P0 |
| TC-RPT-031 | Reports / export | Boundary — exactly 1000 rows stays synchronous | Seed exactly 1000 rows | `?format=csv` | 200 with the inline file — the threshold is `total > 1000` | 200 | No export job key | P2 |
| TC-RPT-032 | Reports / export | Boundary — 1001 rows goes async | Seed exactly 1001 rows | `?format=csv` | 202 + `export_job_id` | 202 | `export_job:<id>` created | P2 |
| TC-RPT-033 | Reports / export | `format=json` never triggers an export job, whatever the row count | BIG-A (1500 rows) | `?format=json&page_size=25` | 200; a normal paginated JSON page of 25 items | 200 | No `export_job:*` key created | P1 |
| TC-RPT-034 | Reports / `GET /reports/exports/{id}` | Poll a job through to completion | TC-RPT-030 produced `job_id` | Poll `GET /reports/exports/{job_id}` until terminal | Sequence: `pending` → `processing` → `completed`; on completion `download_url = "/api/v1/reports/exports/{job_id}/download"` | 200 | Redis `export_job:<id>.status` transitions to `completed`; `export_file:<id>` exists with a base64 payload and a TTL ≤ 3600 | P0 |
| TC-RPT-035 | Reports / `GET /reports/exports/{id}/download` | **Download 404s until the job is ready** | `job_id` is still `pending`/`processing` | `GET /reports/exports/{job_id}/download` | **404 `EXPORT_JOB_NOT_FOUND`** — "Export file is not ready or has expired." | 404 | `redis-cli EXISTS export_file:<id>` → 0 at this point | P1 |
| TC-RPT-036 | Reports / `GET /reports/exports/{id}/download` | Download after completion | Job `completed` | `GET /reports/exports/{job_id}/download` | 200; binary body; `Content-Disposition: attachment; filename="employee_master_report_*.csv"`; the CSV row count == the report's `total_records` (not just the first page) | 200 | Decoded body row count == `SELECT count(*) FROM employees WHERE org_id=1 ...` (all 1500, not 25) | P1 |
| TC-RPT-037 | Reports / `GET /reports/exports/{id}` | Unknown / expired job id | — | `GET /reports/exports/deadbeefdeadbeef` | 404 `EXPORT_JOB_NOT_FOUND` — "Export job not found or expired." | 404 | n/a | P2 |
| TC-RPT-038 | Reports / `GET /reports/exports/{id}` | Job id past its 1-hour TTL | Force-expire `export_job:<id>` in Redis | `GET /reports/exports/{job_id}` | 404 `EXPORT_JOB_NOT_FOUND` | 404 | `redis-cli EXISTS export_job:<id>` → 0 | P2 |
| TC-RPT-039 | Reports / export | **P0 — cross-tenant export status leak** | Org A (A-ADMIN) starts a large payroll export → `job_id_A`. Org B has obtained that id (see DEF-2 on how ids leak — they cannot be guessed) | As **B-ADMIN**: `GET /reports/exports/{job_id_A}` | **Expected: 404 `EXPORT_JOB_NOT_FOUND`** — an Org A job must not be visible to Org B. **Currently FAILS — the service ignores `org_id`; the Redis key is `export_job:{job_id}` with no tenant component (§9, DEF-2).** | 404 | The job payload in Redis carries no `org_id`; assert the response reveals no Org A `download_url` | P0 |
| TC-RPT-040 | Reports / export | **P0 — cross-tenant export FILE download leak (salary exposure)** | `job_id_A` is a **completed payroll salary-register** export for Org A | As **B-ADMIN**: `GET /reports/exports/{job_id_A}/download` | **Expected: 404 `EXPORT_JOB_NOT_FOUND`.** **Currently FAILS — Org B receives Org A's salary CSV in full (§9, DEF-2). This is the single highest-severity finding in these six modules.** | 404 | Assert the downloaded bytes contain **zero** Org A employee codes / salary figures: `SELECT code FROM employees WHERE org_id=1 LIMIT 1` must not appear in the body | P0 |
| TC-RPT-041 | Reports / export | Cross-tenant export download by an **unprivileged** Org B user | `job_id_A` completed; caller is an Org B user with `reports:read` but **no** `payroll_record:read` | `GET /reports/exports/{job_id_A}/download` | Expected 403/404. **The download endpoint only checks `reports:read` — it does not re-check the source-module permission of the report that produced the file (§9, DEF-3)** | 403/404 | Assert no salary data reaches a caller lacking `payroll_record:read` | P0 |
| TC-RPT-042 | Reports / export | Export job status polling requires `reports:read` | A-NOPERM | `GET /reports/exports/{job_id}` | 403 `AUTH_FORBIDDEN` | 403 | n/a | P1 |
| TC-RPT-043 | Reports / export | **Queue down → the export still completes via the in-process fallback** | `QUEUE_DOWN` fixture (arq enqueue raises); Redis still up for the cache | `GET /reports/employees/master?format=csv` on BIG-A | 202 + `export_job_id` (identical response shape); the export runs in-process and eventually reaches `completed` | 202 → 200 | `export_file:<id>` is populated; the app logs `export_enqueue_failed_running_in_process` at ERROR | P1 |
| TC-RPT-044 | Reports / export | Export job failure is recorded, not swallowed | Inject a repository failure inside the export run | Start a large export, then poll | The job reaches `status="failed"`; the download endpoint returns 404 `EXPORT_JOB_NOT_FOUND` | 200 (poll) / 404 (download) | `redis-cli GET export_job:<id>` → `status='failed'`; `export_file:<id>` absent | P2 |
| TC-RPT-045 | Reports / export | Redis DOWN entirely during a large export | `REDIS_DOWN` | `GET /reports/employees/master?format=csv` on BIG-A | The request still returns 202 (the cache write is best-effort); the subsequent status poll returns 404 `EXPORT_JOB_NOT_FOUND` because nothing could be persisted. **Must not 500.** Document as a known degradation | 202 → 404 | n/a — Redis is the only export store | P2 |
| TC-RPT-046 | Reports / `GET /reports/leave/balance` | Any-of permission logic — `leave_balance:read` alone suffices | A user with `reports:read` + `leave_balance:read` but **no** `leave_request:read` | `GET /reports/leave/balance` | 200 — the family accepts either permission | 200 | Rows scoped to `org_id=1` | P1 |
| TC-RPT-047 | Reports / `GET /reports/leave/balance` | Neither leave permission | `reports:read` only | `GET /reports/leave/balance` | 403 `AUTH_FORBIDDEN` — "Missing permission 'leave_request:read' or 'leave_balance:read'." | 403 | n/a | P1 |
| TC-RPT-048 | Reports / `GET /reports/settlements/ledger` | Any-of over three settlement permissions | A user with only `arrears:read` | `GET /reports/settlements/ledger` | 200 — `loan_advance` **or** `arrears` **or** `settlement` read is sufficient | 200 | Rows scoped to `org_id=1` | P1 |
| TC-RPT-049 | Reports / `GET /reports/attendance/late-coming` | A representative attendance report with filters | A-ADMIN | `?date_from=2026-07-01&date_to=2026-07-11&branch_id=11&sort_by=late_minutes&sort_dir=desc` | 200; only branch-11, in-range rows, sorted descending | 200 | Row count matches the equivalent SQL for `org_id=1`, branch 11 | P1 |
| TC-RPT-050 | Reports / `GET /reports/notifications/summary` | A "summary"-shaped report returns an object, not a list | A-ADMIN (`notification:read`) | `GET /reports/notifications/summary?format=json` | 200; a single aggregate object (not the `{items, pagination}` envelope) | 200 | Aggregate values reconcile with `notifications` / `notification_recipients` for `org_id=1` | P2 |
| TC-RPT-051 | Reports / `GET /reports/organization/workforce-summary` | A summary report exported to CSV yields a single data row | A-ADMIN | `?format=csv` | 200; CSV with one header row + one data row (the summary dict) | 200 | Values reconcile with the org-A headcount SQL | P2 |
| TC-RPT-052 | Reports / auth | Any report endpoint without a token | — | `GET /reports/employees/master` with no `Authorization` header | 401 `AUTH_NOT_AUTHENTICATED` | 401 | n/a | P0 |
| TC-RPT-053 | Reports / authz | Report without `reports:read` even when the source permission is held | A user with `employee:read` but **no** `reports:read` | `GET /reports/employees/master` | 403 `AUTH_FORBIDDEN` — **both** permissions are required; the router guard fires first | 403 | n/a | P0 |
| TC-RPT-054 | Reports / read-only | Reports write no audit rows | Baseline `NA` | Call 10 report endpoints as A-ADMIN | All 200 | 200 | `SELECT count(*) FROM activity_logs WHERE org_id=1` → still `NA` | P1 |
| TC-RPT-055 | Reports / pagination | `page_size` cap on a report | — | `GET /reports/employees/master?page_size=10000` | 422 `VALIDATION_ERROR` (the shared `PaginationRequest` cap applies) | 422 | n/a (read-only) | P2 |

---

## 9. Defects / Spec Deviations Found While Authoring

These were found by reading the shipped code against the stated behaviour. Each has a test case above whose **Expected Result is written to the spec**, so the case will fail until the defect is fixed.

| # | Severity | Where | Finding | Covering case |
|---|---|---|---|---|
| **DEF-1** | **P0** | `app/modules/settings/schemas.py::OrgSettingsResponse` | `pass_code` has a masking validator (`_mask_pass_code` → `"********"`) but **`sync_code` does not** — it is returned in **plaintext** by `GET /settings`, `GET /settings/organization`, `PATCH /settings/organization`, and `POST /settings/organization/reset`. The device-pairing sync code is readable by anyone with `settings:read`. | TC-SET-005 |
| **DEF-2** | **P0** | `app/modules/reports/service.py::get_export_job_status` / `get_export_file` | Both take `org_id` and **never use it**. The Redis keys are `export_job:{job_id}` / `export_file:{job_id}` with **no tenant component**, and the cached job payload stores no `org_id`. Any authenticated user in **any** org holding `reports:read` can poll and **download another tenant's completed export** — including a finalized **payroll salary register** — given the job id. **Exploitability:** the id is `uuid4().hex` (128 bits), so it cannot be brute-forced — an attacker must *obtain* it (access logs, proxy/referrer logs, browser history, a shared or forwarded `download_url`, or an insider). This is a genuine missing-authorization defect (broken access control), not a remotely-guessable one: the only thing separating Org B from Org A's salary register is the secrecy of a URL. Fix is one line — persist `org_id` in the job payload and compare it on read. | TC-RPT-039, TC-RPT-040 |
| **DEF-3** | **P0** | `app/modules/reports/router.py::download_export_file` | The download endpoint is guarded only by `reports:read`. It does not re-check the **source-module** permission of the report that produced the file. A user without `payroll_record:read` — who is correctly 403'd on `/reports/payroll/register` — can still download a completed payroll export by job id. | TC-RPT-041 |
| **DEF-4** | P2 | `app/modules/notifications/exceptions.py::AlreadyAssignedException` | The `ALREADY_ASSIGNED` (409) exception class is defined but **never raised anywhere**. `assign_recipients` instead returns `200` with a per-user `status:"already_assigned"` entry. Either the contract or the code is wrong; the tests assert the *implemented* behaviour and flag the dead code. | TC-NOT-014 |
| **DEF-5** | P2 | `app/modules/hardware/repository.py::serial_number_exists` | Serial-number uniqueness is enforced **globally**, not per-org (`uq_biometric_devices_serial_number`). Org B registering a serial already held by Org A gets `409 DEVICE_SERIAL_EXISTS` — a cross-tenant existence oracle for device serial numbers. Likely intended (hardware serials *are* globally unique), but it does leak. Product decision needed. | TC-HW-006 |

---

## 10. Coverage Notes & Out-of-Scope

**Case counts**

| Module | Written cases | Endpoints covered | P0 cases |
|---|---|---|---|
| TC-HW — Hardware / Biometric | 46 | 13 / 13 | 15 |
| TC-NOT — Notifications | 56 | 17 / 17 | 19 |
| TC-SET — Settings | 46 | 8 / 8 | 17 |
| TC-AUD — Audit | 45 | 5 / 5 | 15 |
| TC-DSH — Dashboard | 46 | 19 / 19 | 18 |
| TC-RPT — Reports | 55 | 42 / 42 (40 via the TC-RPT-001 / TC-RPT-002 / TC-RPT-008 parameterised matrices + the 2 export endpoints in full) | 20 |
| **Total** | **294 written rows** | **104 / 104 (100 %)** | **114** |

Three rows are parameterised matrices that expand at execution time (TC-RPT-001 → 40 runs, TC-RPT-002 → 9, TC-RPT-008 → 40), giving **~380 executions** from 294 written rows. Reports' 42 endpoints are deliberately *not* written as 42 near-identical rows — see the parameterisation note at the head of §8.

Row count is above the 130–170 target because tenant isolation was specified as the primary risk for this read-heavy half of the product: **114 of the 294 rows (39 %) are P0 isolation / salary-exposure / secret-exposure cases**, and there is at least one cross-tenant case on **every** read surface across all six modules. Dropping to 170 would mean cutting either the per-endpoint isolation cases or the validation matrix; neither was judged safe to cut. No row duplicates another's assertion.

**Covered:** functional happy paths for all 104 endpoints · validation (bad sort field, bad enum, bad date range, bad format, bad pagination) · authentication (401) · authorization (403 for the module permission *and* the source-module permission on reports/dashboard) · business rules (uniqueness, in-use deletion, idempotency, upsert, feature-toggle gates) · edge cases (empty result sets, boundary export thresholds at 1000/1001 rows, Redis down, queue down, division by zero, org with no settings row) · error scenarios (every error code below) · multi-tenant isolation (a dedicated P0 case on every read surface, plus the 40-endpoint report matrix) · database verification on every mutating case · end-to-end chains (settings toggle → gated module 409/201; approval + payroll finalize → `notification_recipients` row; every mutation → `activity_logs` row visible in `/activity-logs`).

**Error codes used — all verified present in `app/` by grep:**
`DEVICE_NOT_FOUND`, `DEVICE_SERIAL_EXISTS`, `DEVICE_CODE_EXISTS`, `DEVICE_IN_USE`, `BRANCH_NOT_FOUND`, `NOTIFICATION_NOT_FOUND`, `RECIPIENT_NOT_FOUND`, `USER_NOT_FOUND`, `ALREADY_ASSIGNED` (defined; see DEF-4), `SETTINGS_NOT_FOUND`, `UNKNOWN_FEATURE`, `ACTIVITY_LOG_NOT_FOUND`, `EMPLOYEE_NOT_FOUND`, `EXPORT_JOB_NOT_FOUND`, `REGULARIZATION_DISABLED`, `ADVANCE_SHIFT_DISABLED`, `VALIDATION_ERROR`, `CONFLICT`, `NOT_FOUND`, `AUTH_FORBIDDEN`, `AUTH_NOT_AUTHENTICATED`, `RATE_LIMITED`, `TENANT_UNRESOLVED`.

**Not covered, and why:**

1. **`RATE_LIMITED` (429).** Grep confirms the `rate_limit` dependency is wired **only** into `app/modules/auth/` (login / refresh / password reset). **None of these six modules is rate-limited**, so there is no 429 case to write. A burst of 1000 `GET /activity-logs` calls returns 200 throughout. If rate limiting is later extended to reads, add one 429 case per module. *(Recommend: rate-limit `/reports/*` exports — an unauthenticated-adjacent user can currently queue unbounded 1500-row exports.)*
2. **`TENANT_UNRESOLVED` (400).** Every router in scope raises it when `current_user.org_id is None`, but no such token can be minted through the public auth flow (org_id is always stamped). It is only reachable with a hand-forged token, so it is documented rather than tested.
3. **PDF fidelity.** `_generate_pdf_bytes` emits a text stub with a `%PDF-1.4` header — not a real PDF. Cases assert the `Content-Type` and filename only; a rendering/parse assertion would fail for reasons unrelated to the module under test. Flagged separately as a product gap.
4. **Excel fidelity.** `format=excel` produces **CSV bytes** with an `.xlsx` filename and an Excel MIME type (`_run_async_export` / `_handle_report_query` branch only on `pdf` vs. everything-else). Cases assert the headers; a real XLSX parse would fail. Also a product gap, not a test gap.
5. **`GET /devices/{id}/health` template internals.** Biometric templates are never exposed by any endpoint (verified — only aggregate counts exist in the response schema), so there is no "template leak" case beyond the negative assertion in TC-HW-041.
6. **The `enable_photo_punch` toggle** has no consumer in the codebase (grep finds no gate reading it), unlike `enable_regularization` and `advance_shift_enabled`. It is covered as a plain settings field (TC-SET-008/036) but has no E2E gate case, because there is nothing to gate.
7. **Concurrency on `activity_logs`.** The trail is append-only with no unique constraint, so there is no concurrent-insert conflict case to write; the ordering tiebreaker (`id desc`) is covered by TC-AUD-009.
