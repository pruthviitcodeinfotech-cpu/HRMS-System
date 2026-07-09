# Leave Management API Contract

> Module: `app/modules/leave`
> API Version: `v1` — all routes under `API_V1_PREFIX` (`/api/v1`).
> Status: **Contract only** (no FastAPI/SQLAlchemy/Pydantic/service/repository code).
> Sources of truth: `docs/architecture.md` (Backend Architecture), migration `0003_leave_holiday_management`
> (+ `0008`, `0016`), the leave models (`leave/models/leave.py`, `holiday.py`), `leave/constants.py`, and
> the approved Authentication, RBAC, Employee, Shift, and Attendance API Contracts.

Covers leave configuration (types + org cycle), balances/allocations/adjustments, leave requests, and holiday
templates/calendar. **Excludes** Authentication, RBAC, Employee, Shift, Attendance, Approval, Payroll,
Settlements, Notifications, Settings, Hardware, Dashboard, Reports. Cross-module tables (employees, users,
approval_requests) are referenced/read only.

---

## 1. Module Overview

### Purpose
Define leave types (with embedded allocation/carry-forward/encashment policy), configure the org leave cycle,
maintain per-employee leave balances and adjustments, process leave requests (apply/edit/cancel + reads), and
manage holiday templates/calendars.

### Responsibilities
- Leave types (`leave_types`) and org leave-cycle config (`leave_settings`).
- Employee leave allocations (`employee_leave_allocations`) and balances (`employee_leave_balances`).
- Manual balance adjustments — credit/debit/adjust + history (`leave_balance_adjustments`).
- Leave requests (`leave_requests`): apply, edit, cancel, read. **Approve/Reject is the Approval module.**
- Holiday templates ("groups") + holiday items + employee holiday assignment
  (`holiday_templates`, `holiday_template_items`, `employee_holiday_assignments`).

### Dependencies
| Dependency | Location / Module | Used for |
|---|---|---|
| Auth/permission deps | `core/dependencies/auth.py` | `current_user`, `current_org`, `require_permission` |
| Tenant middleware | `core/middleware/tenant.py` | `org_id` scoping |
| RBAC data scope | `rbac` | branch/department access filters employee reads |
| Employee module (service) | `employee` | validate `employee_id`; resolve caller's own employee for self-service |
| Approval module | `approvals` | leave request approval (`approval_requests`, `request_type='leave'`) — **out of scope here** |
| Attendance (read) | `attendance` | `attendance_days.leave_id` links an approved leave to a day — read by attendance, not written here |
| Response/pagination schemas | `shared/schemas/` | envelope + paginated lists |
| Activity Log (audit) | `audit` | records config changes, adjustments, request lifecycle |

**Tables owned:** `leave_settings`, `leave_types`, `employee_leave_allocations`, `employee_leave_balances`,
`leave_balance_adjustments`, `leave_requests`, `holiday_templates`, `holiday_template_items`,
`employee_holiday_assignments`.

### Module boundaries
- Owns leave/holiday data. Does not own employees or users (referenced by ID; FKs to `employees` are deferred
  columns, `leave_type_id` FKs are enforced intra-module).
- **Leave approval/rejection** is performed by the Approval module; this contract only *applies/edits/cancels*
  requests and reads their status. `leave_requests.status/reviewed_by/reviewed_at/rejection_reason` are set by
  that flow.
- **No dedicated `leave_policies` table** — per-type policy lives on `leave_types`; org cycle on
  `leave_settings` (§12 Q1). **No comp-off schema** (§12 Q2).

---

## 2. Authorization Model

Two-layer RBAC: feature permission (CRUD on `feature_key`) × data scope (branch/department access). Super
admins bypass feature checks; tenant isolation (`org_id`) always applies. All endpoints require
`Authorization: Bearer <access_token>`.

**Proposed feature keys** (register in `core/security/permissions.py` — §12 Q5): `leave_type`, `leave_config`,
`leave_balance`, `leave_request`, `holiday`. Employee-related reads are additionally filtered by branch/
department data scope.

**Self-service:** an employee may Apply/Edit/Cancel their **own** leave requests and view their **own**
balances/holidays (resolved via `users.employee_id`) without the admin feature permission; acting on **other**
employees requires the corresponding feature permission + data scope.

---

## 3. Request & Response Standards

Reuses the shared envelope + pagination.
- **Success:** `{ "success": true, "data": {…}, "error": null, "meta": { "request_id": "…" } }`
- **Error:** `{ "success": false, "data": null, "error": { "code", "message", "details"? }, "meta": {…} }`
- **Paginated:** `data.items` + `page`, `page_size`, `total`.
- BIGINT integer IDs; dates `YYYY-MM-DD`; day counts as decimals (`Numeric(6,2)` balances, `Numeric(4,1)`
  request duration — e.g. half-day = `0.5`); timezone-aware timestamps; empty lists → `items: []`.

### Pagination / Filtering / Sorting
`page` (≥1, default 1), `page_size` (bounded). Filters/sorts are explicit allowlists; invalid field → `422`.
Repository applies `org_id` + data scope before optional filters.

**Enumerations:** `leave_types.allocation_frequency|carry_forward_frequency|encashment_frequency` ∈
`monthly, yearly` (DB CHECK); `leave_settings.leave_cycle` ∈ `calendar_year, financial_year` (app-level, no
CHECK); `employee_leave_allocations.allocation_source` ∈ `auto, manual` (app-level);
`leave_balance_adjustments.adjustment_type` ∈ `manual, bulk_adjust, bulk_update` (app-level);
`leave_requests.status` ∈ `pending, approved, rejected` (DB CHECK).

Common omitted errors (all protected endpoints): `401 AUTH_NOT_AUTHENTICATED`, `403 AUTH_FORBIDDEN`,
`422 VALIDATION_ERROR`.

---

## 4. Leave Types (`/api/v1/leave-types`) — feature key `leave_type`

`leave_types` fields: `name` (≤100), `alias` (≤50, **unique per org**), `description`, `auto_allocation_count`
(Numeric(6,2)), `allocation_frequency` (CHECK `monthly|yearly`, default monthly), `carry_forward_count`
(default 0), `carry_forward_frequency` (CHECK), `encashment_enabled` (bool), `encashment_limit`
(required when `encashment_enabled`), `encashment_frequency` (CHECK, nullable), `is_active`, `is_deleted`,
timestamps, `created_by`/`updated_by`.

| # | Endpoint | Method | URL | Permission |
|---|---|---|---|---|
| 1 | Create Leave Type | POST | `/leave-types` | `leave_type:create` |
| 2 | List Leave Types | GET | `/leave-types` | `leave_type:read` |
| 3 | Get Leave Type Details | GET | `/leave-types/{leave_type_id}` | `leave_type:read` |
| 4 | Update Leave Type | PATCH | `/leave-types/{leave_type_id}` | `leave_type:edit` |
| 5 | Delete Leave Type (soft) | DELETE | `/leave-types/{leave_type_id}` | `leave_type:delete` |

- **Validation:** `name`/`alias` required; `alias` unique per org (`409 LEAVE_TYPE_ALIAS_EXISTS`);
  frequencies ∈ `monthly,yearly`; **if `encashment_enabled=true` then `encashment_limit` required**
  (`ck_leave_types_encashment_limit_required`); counts ≥ 0.
- **Business rules:** `is_active` toggled via Update (enable/disable). Soft delete blocked if referenced by
  active balances/requests (`409 LEAVE_TYPE_IN_USE`). Policy attributes (allocation/carry-forward/encashment)
  are part of this record — there is no separate policy entity (§12 Q1).
- **Success:** `201`/`200`/`204`. **Errors:** `404 LEAVE_TYPE_NOT_FOUND`, `409 LEAVE_TYPE_ALIAS_EXISTS`,
  `409 LEAVE_TYPE_IN_USE`.

---

## 5. Leave Cycle Configuration (`/api/v1/leave-settings`) — feature key `leave_config`

`leave_settings` (org-level, **one row per org** — `UNIQUE(org_id)`): `leave_cycle`
(`calendar_year|financial_year`, default `calendar_year`), `cycle_start_month` (smallint 1–12, default 1),
timestamps, `created_by`/`updated_by`. This is the org-level "Leave Policy" per §12 Q1.

| # | Endpoint | Method | URL | Permission |
|---|---|---|---|---|
| 6 | Get Leave Cycle Config | GET | `/leave-settings` | `leave_config:read` |
| 7 | Update Leave Cycle Config | PUT | `/leave-settings` | `leave_config:edit` |

- **7. Update** — `{ "leave_cycle", "cycle_start_month" }`; **upsert** the single org row.
- **Validation:** `leave_cycle` ∈ `calendar_year,financial_year`; `cycle_start_month` 1–12.
- **Success:** `200`. **Note:** Create/Delete not exposed (exactly one config per org).

---

## 6. Leave Balances, Allocations & Adjustments — feature key `leave_balance`

`employee_leave_balances` (**unique** `(employee_id, leave_type_id, cycle_year)`): `opening_balance`,
`allocated`, `used`, `carried_forward`, `encashed`, `adjusted`, `closing_balance` (all Numeric(6,2)).
`employee_leave_allocations` records allocation events (`allocated_days`, `allocation_date`,
`allocation_source` `auto|manual`, `cycle_year`, `cycle_period`). `leave_balance_adjustments` records manual
changes (`adjustment_type` `manual|bulk_adjust|bulk_update`, signed `delta`, `new_balance`, `remarks`,
`adjusted_by` **required**).

| # | Endpoint | Method | URL | Permission |
|---|---|---|---|---|
| 8 | Get Employee Leave Balance | GET | `/employees/{employee_id}/leave-balances` | `leave_balance:read` |
| 9 | List Leave Balances | GET | `/leave-balances` | `leave_balance:read` |
| 10 | Credit Leave | POST | `/employees/{employee_id}/leave-balances/credit` | `leave_balance:edit` |
| 11 | Debit Leave | POST | `/employees/{employee_id}/leave-balances/debit` | `leave_balance:edit` |
| 12 | Adjust Leave Balance | POST | `/employees/{employee_id}/leave-balances/adjust` | `leave_balance:edit` |
| 13 | Leave Balance History | GET | `/employees/{employee_id}/leave-balances/history` | `leave_balance:read` |
| 14 | List Leave Allocations | GET | `/employees/{employee_id}/leave-allocations` | `leave_balance:read` |

- **8. Get Balance** — query `cycle_year` (default current), optional `leave_type_id`. `200` → balance rows
  (per type) with all balance fields. Self-service allowed for own employee.
- **9. List Balances** — query `page`, `page_size`, `leave_type_id`, `cycle_year`, `employee_id`, `branch_id`,
  `dept_id`. Data-scoped. `200` paginated.
- **10/11/12. Credit / Debit / Adjust** — body `{ "leave_type_id", "cycle_year", "days" (or "new_balance" for adjust), "adjustment_type"?, "remarks"? }`.
  Each writes a `leave_balance_adjustments` row and updates the matching `employee_leave_balances`
  (`adjusted`, `closing_balance`), with `adjusted_by = caller`:
  - **Credit** → positive `delta = +days`.
  - **Debit** → negative `delta = −days` (must not drive balance below 0 unless allowed — §7).
  - **Adjust** → `delta` computed to reach `new_balance` (or an explicit signed delta).
  - `adjustment_type` defaults to `manual`.
- **13. History** — query `cycle_year`, `leave_type_id`. `200` → `leave_balance_adjustments` for the employee
  (index `(employee_id, cycle_year)`).
- **14. List Allocations** — `200` → `employee_leave_allocations` (read-only; **auto-allocation is a
  background job**, not an API here — §12 Q6).
- **Validation:** `leave_type_id` exists/active in org; `days > 0` (credit/debit); `new_balance ≥ 0` (adjust);
  balance row exists or is created for `(employee, type, cycle_year)`.
- **Errors:** `404 EMPLOYEE_NOT_FOUND`, `404 LEAVE_TYPE_NOT_FOUND`, `404 BALANCE_NOT_FOUND`,
  `409 INSUFFICIENT_BALANCE`.

---

## 7. Leave Requests (`/api/v1/leave-requests`) — feature key `leave_request`

`leave_requests` fields: `employee_id`, `leave_type_id` (FK), `start_date`, `end_date`
(**CHECK `end_date ≥ start_date`**), `duration_days` (Numeric(4,1)), `reason`, `status`
(CHECK `pending|approved|rejected`, default `pending`), `applied_on`, `reviewed_at`, `reviewed_by`,
`rejection_reason`, timestamps.

| # | Endpoint | Method | URL | Permission |
|---|---|---|---|---|
| 15 | Apply Leave | POST | `/leave-requests` | `leave_request:create` (or self) |
| 16 | Edit Leave Request | PATCH | `/leave-requests/{request_id}` | `leave_request:edit` (or self) |
| 17 | Cancel Leave Request | DELETE | `/leave-requests/{request_id}` | `leave_request:delete` (or self) |
| 18 | Get Leave Details | GET | `/leave-requests/{request_id}` | `leave_request:read` (or self) |
| 19 | List / Search Leave Requests | GET | `/leave-requests` | `leave_request:read` |

- **15. Apply Leave** — `{ "employee_id", "leave_type_id", "start_date", "end_date", "duration_days", "reason"? }`.
  Creates the request as `pending` and **initiates the approval entry via the Approval module**
  (`approval_requests`, `request_type='leave'`). Self-service defaults `employee_id` to the caller's employee.
  - **Validation:** `end_date ≥ start_date`; `duration_days > 0`; `leave_type_id` active in org; sufficient
    balance for the type/cycle (business rule); no overlapping request for the same employee/dates
    (`409 LEAVE_OVERLAP`).
  - `201`.
- **16. Edit** — allowed **only while `status='pending'`**; may change dates/type/reason/duration. `200`;
  `409 LEAVE_NOT_EDITABLE` if not pending.
- **17. Cancel** — **hard-delete**, allowed **only while `status='pending'`** (there is no `cancelled` status
  and no soft-delete — §12 Q3). `204`; `409 LEAVE_NOT_CANCELLABLE` if approved/rejected.
- **18. Get** — `200` → request incl. status/review fields. `404 LEAVE_REQUEST_NOT_FOUND`.
- **19. List / Search** — query `page`, `page_size`, `employee_id`, `leave_type_id`, `status`,
  `date_from`/`date_to` (overlap), `branch_id`, `dept_id`, `sort_by` (`applied_on|start_date`), `sort_dir`.
  Data-scoped. `200` paginated.
- **Approve / Reject** are **not** in this contract — the Approval module updates `status`/`reviewed_by`/
  `reviewed_at`/`rejection_reason`.

---

## 8. Holiday Management — feature key `holiday`

### 8.1 Holiday Groups / Templates (`/api/v1/holiday-templates`) — `holiday_templates`
Fields: `name` (≤150, **unique per org among non-deleted**), `holiday_count` (smallint, maintained),
`is_deleted`, timestamps, `created_by`/`updated_by`.

| # | Endpoint | Method | URL | Permission |
|---|---|---|---|---|
| 20 | Create Holiday Group | POST | `/holiday-templates` | `holiday:create` |
| 21 | List Holiday Groups | GET | `/holiday-templates` | `holiday:read` |
| 22 | Get Holiday Group | GET | `/holiday-templates/{template_id}` | `holiday:read` |
| 23 | Update Holiday Group | PATCH | `/holiday-templates/{template_id}` | `holiday:edit` |
| 24 | Delete Holiday Group (soft) | DELETE | `/holiday-templates/{template_id}` | `holiday:delete` |
| 25 | Assign Holiday Group to Employee | PUT | `/employees/{employee_id}/holiday-template` | `holiday:edit` |
| 26 | View Employee Holiday Assignment | GET | `/employees/{employee_id}/holiday-template` | `holiday:read` |

- **20–24.** `name` unique per org (non-deleted) → `409 HOLIDAY_TEMPLATE_NAME_EXISTS`. Get returns the
  template + its items. Soft-delete via `is_deleted`.
- **25. Assign** — `{ "template_id" }`. `employee_holiday_assignments` has **`UNIQUE(employee_id)`** → one
  template per employee; the prior template is recorded in `previous_template_id`, `assigned_by=caller`.
  `200`; `404 EMPLOYEE_NOT_FOUND`/`HOLIDAY_TEMPLATE_NOT_FOUND`.
- **26.** `200` → `{ template_id, previous_template_id, assigned_by, assigned_at }` or null.

### 8.2 Holidays / Template Items (`/api/v1/holiday-templates/{template_id}/holidays`) — `holiday_template_items`
Fields: `name` (≤150), `start_date`, `end_date` (**CHECK `end_date ≥ start_date`**), `day_of_week` (≤15,
nullable), `duration_days` (smallint, default 1), `is_deleted`, timestamps, `created_by`.

| # | Endpoint | Method | URL | Permission |
|---|---|---|---|---|
| 27 | Create Holiday | POST | `/holiday-templates/{template_id}/holidays` | `holiday:edit` |
| 28 | Update Holiday | PATCH | `/holiday-templates/{template_id}/holidays/{item_id}` | `holiday:edit` |
| 29 | Delete Holiday (soft) | DELETE | `/holiday-templates/{template_id}/holidays/{item_id}` | `holiday:edit` |
| 30 | List Holidays | GET | `/holiday-templates/{template_id}/holidays` | `holiday:read` |

- **Validation:** `name`, `start_date`, `end_date` required; `end_date ≥ start_date`; `duration_days ≥ 1`.
  Maintaining `holiday_templates.holiday_count` is a service concern.
- **Errors:** `404 HOLIDAY_TEMPLATE_NOT_FOUND`, `404 HOLIDAY_ITEM_NOT_FOUND`.

### 8.3 Holiday Calendar (`/api/v1/employees/{employee_id}/holidays`) — `holiday`
| # | Endpoint | Method | URL | Permission |
|---|---|---|---|---|
| 31 | Employee Holiday Calendar | GET | `/employees/{employee_id}/holidays` | `holiday:read` (or self) |

- Query `year` (or `date_from`/`date_to`). Returns the holidays from the employee's **assigned** holiday
  template within the range (join `employee_holiday_assignments` → `holiday_template_items`). `200` → dated
  holiday list. `404 EMPLOYEE_NOT_FOUND`. Self-service allowed for own employee.

---

## 9. Validation & Business Rules (summary)

- **Tenant isolation** on all operations; employee-related reads are branch/department data-scoped;
  self-service limited to the caller's own employee.
- **Leave type:** `alias` unique per org; `encashment_enabled ⇒ encashment_limit` required; frequencies ∈
  `monthly,yearly`.
- **Leave cycle:** exactly one `leave_settings` per org (upsert); `cycle_start_month` 1–12.
- **Balances:** unique per `(employee, type, cycle_year)`; adjustments record signed `delta` + `new_balance`
  and update `adjusted`/`closing_balance`; debit must respect available balance (`INSUFFICIENT_BALANCE`)
  unless negative balances are permitted by policy.
- **Allocations:** unique per `(employee, type, cycle_year, cycle_period)`; auto-allocation is a background
  job (not an API).
- **Leave requests:** `end_date ≥ start_date`; `duration_days > 0`; created `pending`; **edit/cancel only
  while pending**; cancel = hard-delete; no overlapping requests; approve/reject via Approval module.
- **Holidays:** template `name` unique per org (non-deleted); item `end_date ≥ start_date`; **one template
  per employee** (assignment), with `previous_template_id` history.

---

## 10. Permission Matrix

| Feature key | create | read | edit | delete |
|---|---|---|---|---|
| `leave_type` | Create | List/Get | Update (incl. activate/deactivate) | Delete (soft) |
| `leave_config` | — | Get cycle config | Update cycle config | — |
| `leave_balance` | Credit/Debit/Adjust (writes adjustments) | Get/List balances, History, Allocations | (adjustments) | — |
| `leave_request` | Apply | Get/List/Search | Edit (pending) | Cancel (pending) |
| `holiday` | Create group/holiday | List/Get groups & holidays, Assignment, Calendar | Update group/holiday, Assign to employee | Delete group/holiday (soft) |

Self-service (own employee) permitted for Apply/Edit/Cancel/Get own requests, own balances, own holiday
calendar. Super admins bypass feature checks; tenant isolation always applies.

---

## 11. Error Handling & Security

**Error envelope** via `core/exceptions/handlers.py`. Module error codes (proposed, to be registered in
`leave/exceptions.py`): `LEAVE_TYPE_NOT_FOUND`(404), `LEAVE_TYPE_ALIAS_EXISTS`(409), `LEAVE_TYPE_IN_USE`(409),
`BALANCE_NOT_FOUND`(404), `INSUFFICIENT_BALANCE`(409), `LEAVE_REQUEST_NOT_FOUND`(404), `LEAVE_OVERLAP`(409),
`LEAVE_NOT_EDITABLE`(409), `LEAVE_NOT_CANCELLABLE`(409), `HOLIDAY_TEMPLATE_NOT_FOUND`(404),
`HOLIDAY_TEMPLATE_NAME_EXISTS`(409), `HOLIDAY_ITEM_NOT_FOUND`(404), `EMPLOYEE_NOT_FOUND`(404),
`VALIDATION_ERROR`(422), plus shared `AUTH_NOT_AUTHENTICATED`(401)/`AUTH_FORBIDDEN`(403).

**HTTP status codes used:** 200, 201, 204, 400, 401, 403, 404, 409, 422.

**Security considerations:** every route enforces `require_permission` (or self-service ownership) + tenant
scope + branch/department data scope on employee reads; balance adjustments and request lifecycle recorded in
the Activity Log (actor, org, `delta`/before-after); no secrets/PII in logs; timestamps timezone-aware; rate
limiting per the security baseline on adjustment and apply endpoints.

---

## 12. Open Questions

1. **Leave Policies (Q1).** No `leave_policies` table exists; per-type policy is embedded on `leave_types`
   and org cycle on `leave_settings`. This contract maps "Leave Policy" accordingly and omits standalone
   policy CRUD and "Assign Policy" (no policy-assignment table). Confirm this mapping.
2. **Comp Off (Q2) — NOT supported.** No comp-off table/earn/balance mechanism exists; it can only be modeled
   as a regular `leave_type` + balance. Comp-off endpoints are omitted. Confirm whether a first-class comp-off
   feature is planned (needs new schema).
3. **Leave cancellation (Q3).** No `cancelled` status (CHECK = pending/approved/rejected) and no soft-delete;
   Cancel is modeled as hard-delete of a *pending* request. Confirm this is acceptable (else a status/schema
   change is needed to retain cancelled history).
4. **Approve/Reject ownership (Q4).** Leave approval flows through the Approval module (`approval_requests`,
   `request_type='leave'`), so approve/reject endpoints are excluded here. Confirm the Approval contract will
   cover them and how `Apply Leave` should create the approval entry.
5. **Feature-key catalog (Q5).** `permissions.py` is a stub; confirm the proposed keys
   (`leave_type`/`leave_config`/`leave_balance`/`leave_request`/`holiday`) and self-service rules.
6. **Auto-allocation & recompute (Q6).** Auto allocation (`allocation_source='auto'`) and balance recompute
   on approval/cancellation are background/service behaviors, intentionally outside this API contract —
   confirm triggers.
7. **Negative balance / debit policy (Q7).** Whether debit/leave-consumption may drive a balance below zero
   is a policy decision not encoded in the schema — confirm the rule for `INSUFFICIENT_BALANCE`.
8. **Envelope key names (Q8).** `shared/schemas/response.py` is a stub; final envelope field names must match
   once implemented (same open item as prior contracts).
