# Approval Management API Contract

> Module: `app/modules/approvals`
> API Version: `v1` — all routes under `API_V1_PREFIX` (`/api/v1`).
> Status: **Contract only** (no FastAPI/SQLAlchemy/Pydantic/service/repository code).
> Sources of truth: `docs/architecture.md` (Backend Architecture), migration `0004_approval_requests`
> (+ `0008`, `0016`), the approvals models (`approvals/models.py`), and the approved Authentication, RBAC,
> Employee, Shift, Attendance, and Leave API Contracts.

A **generic, single-level approval engine** over `approval_requests`. It manages the approval *workflow*
(list / approve / reject / history / dashboard) for requests raised by other modules (Leave, Attendance
Regularization, Login-reset, and future types). It does **not** duplicate the business APIs of those modules.
**Excludes** Authentication, RBAC, Employee, Shift, Attendance, Leave, Payroll, Settlements, Notifications,
Settings, Hardware, Dashboard, Reports.

---

## 1. Module Overview

### Purpose
Provide a common approval envelope: track each pending request, let an authorized reviewer approve or reject
it (single level), and expose read/dashboard views. Approving/rejecting propagates the decision to the
**source** module that owns the underlying record.

### Responsibilities
- Manage `approval_requests`: read, approve, reject, bulk approve/reject.
- Expose the (single-level) status/timeline for a request and dashboard aggregates.
- On decision, orchestrate the source module's service to apply the outcome (e.g. Leave, Attendance
  regularization).

### Dependencies
| Dependency | Location / Module | Used for |
|---|---|---|
| Auth/permission deps | `core/dependencies/auth.py` | `current_user`, `current_org`, `require_permission` |
| Tenant middleware | `core/middleware/tenant.py` | `org_id` scoping |
| RBAC data scope | `rbac` | branch/department access filters approvals by `employee_id` |
| Employee module (service) | `employee` | resolve employee → branch/department for scope; display info |
| Leave module (service) | `leave` | apply an approved/rejected **leave** decision to `leave_requests` |
| Attendance (regularization) | this module's `attendance_regularization_requests` | source detail for `request_type='attendance'` |
| Auth/User (login-reset) | this module's `login_reset_requests` | source detail for `request_type='login_reset'` |
| Notifications (event) | `notifications` | notify requester on decision — **out of scope here** (event/side-effect) |
| Response/pagination schemas | `shared/schemas/` | envelope + paginated lists |
| Activity Log (audit) | `audit` | records every approve/reject action |

**Tables owned:** `approval_requests` (workflow envelope), plus the source-detail tables
`attendance_regularization_requests` and `login_reset_requests` (their *submission* endpoints are **not** in
this contract — see §11 Q5).

### Module boundaries
- Owns the **workflow** only. The creation of a leave request (Leave module), an attendance regularization,
  or a login-reset is a **business API** of the source and is not duplicated here.
- The approval engine is **single-level** (one reviewer, one decision). Multi-level workflow, approval
  levels, next-approver, and multi-step timelines are **not modeled** in the schema (§11 Q1).

---

## 2. Data Model (reference)

`approval_requests` fields: `id`, `org_id`, `request_type` (CHECK **`attendance | leave | login_reset`**),
`request_subtype` (≤50, nullable), `reference_id` (BIGINT — **polymorphic logical FK** to the source row by
`request_type`), `employee_id` (the subject employee), `status` (CHECK **`pending | approved | rejected`**,
default `pending`), `requested_at`, `reviewed_at` (nullable), `reviewed_by` (users, nullable),
`reject_remarks` (text, nullable), `created_at`. Indexes: `(org_id, status)`, `(org_id, status, request_type)`,
`(employee_id, status)`.

**Reference resolution:** `Get Approval Details` resolves the source record from `(request_type,
reference_id)` — `leave` → `leave_requests`, `attendance` → `attendance_regularization_requests`,
`login_reset` → `login_reset_requests` — read via the owning module.

---

## 3. Authorization Model

Two-layer RBAC: feature permission (CRUD on `feature_key`) × data scope (branch/department access on the
request's `employee_id`). Super admins bypass feature checks; tenant isolation (`org_id`) always applies. All
endpoints require `Authorization: Bearer <access_token>`.

**Proposed feature key** (register in `core/security/permissions.py` — §11 Q4): `approval`
(`read` for views/dashboard; `edit` for approve/reject/bulk). Optional per-`request_type` gating (e.g.
approving a leave also requiring a leave-approval right) is **not** encoded in the schema — see §11 Q4.
There is **no assigned-approver** column, so a reviewer sees any pending request within their feature
permission + data scope.

---

## 4. Request & Response Standards

Reuses the shared envelope + pagination.
- **Success:** `{ "success": true, "data": {…}, "error": null, "meta": { "request_id": "…" } }`
- **Error:** `{ "success": false, "data": null, "error": { "code", "message", "details"? }, "meta": {…} }`
- **Paginated:** `data.items` + `page`, `page_size`, `total`.
- BIGINT integer IDs; timezone-aware ISO-8601 timestamps; empty lists → `items: []`.

### Pagination / Filtering / Sorting
`page` (≥1, default 1), `page_size` (bounded). Filter/sort allowlists per endpoint; invalid field → `422`.
Repository applies `org_id` + data scope before optional filters. Filterable: `status`, `request_type`,
`request_subtype`, `employee_id`, `date_from`/`date_to` (on `requested_at`), `branch_id`, `dept_id`. Sortable:
`requested_at`, `reviewed_at`, `status`.

Common omitted errors (all protected endpoints): `401 AUTH_NOT_AUTHENTICATED`, `403 AUTH_FORBIDDEN`,
`422 VALIDATION_ERROR`.

---

## 5. Approval Requests (read) (`/api/v1/approvals`) — feature key `approval`

| # | Endpoint | Method | URL | Permission |
|---|---|---|---|---|
| 1 | List / Search / Filter Approvals | GET | `/approvals` | `approval:read` |
| 2 | List Pending Approvals | GET | `/approvals/pending` | `approval:read` |
| 3 | Get Approval Details | GET | `/approvals/{approval_id}` | `approval:read` |
| 4 | Approval History | GET | `/approvals/history` | `approval:read` |

- **1. List / Search / Filter** — full filter/sort set (§4). `200` paginated envelopes (id, request_type,
  request_subtype, employee_id, status, requested_at, reviewed_at). Data-scoped.
- **2. List Pending** — convenience for `status='pending'` within the caller's permission + data scope
  (same shape as #1). `200` paginated.
- **3. Get Details** — `200` → the envelope + resolved `source` object (from `request_type`+`reference_id`)
  + review fields (`reviewed_by`, `reviewed_at`, `reject_remarks`). `404 APPROVAL_NOT_FOUND`.
- **4. Approval History** — decided requests (`status ∈ {approved, rejected}`); filters `request_type`,
  `employee_id`, `date_from`/`date_to`, `decision`. `200` paginated. (Per-request action history is a single
  step — see §7.)

---

## 6. Approval Actions (`/api/v1/approvals`) — feature key `approval:edit`

| # | Endpoint | Method | URL | Permission |
|---|---|---|---|---|
| 5 | Approve Request | POST | `/approvals/{approval_id}/approve` | `approval:edit` |
| 6 | Reject Request | POST | `/approvals/{approval_id}/reject` | `approval:edit` |
| 7 | Bulk Approve | POST | `/approvals/bulk-approve` | `approval:edit` |
| 8 | Bulk Reject | POST | `/approvals/bulk-reject` | `approval:edit` |

- **5. Approve** — no body (optional `{ "remarks"? }`). Sets `status='approved'`, `reviewed_by=caller`,
  `reviewed_at=now`. **Side-effect:** orchestrates the source module to apply the outcome (e.g. Leave →
  `leave_requests.status='approved'` + balance update; Attendance regularization → apply corrected punch).
  `200` → updated envelope.
- **6. Reject** — `{ "reject_remarks" (required) }`. Sets `status='rejected'`, `reviewed_by`, `reviewed_at`,
  `reject_remarks`; propagates rejection to the source. `200`.
- **7/8. Bulk** — `{ "approval_ids": [ … ], "reject_remarks"? }`. Applies the action per item within
  permission + scope; returns a per-item result (succeeded / skipped-with-reason). `200`/`207`.
- **Validation / Business rules:**
  - Only `status='pending'` may be approved/rejected → already-decided returns `409 APPROVAL_ALREADY_DECIDED`.
  - Reject requires non-empty `reject_remarks` (`422`).
  - A reviewer may not act outside their branch/department data scope.
  - Decision propagation to the source is transactional with the status change (service concern; documented
    as a business rule).
- **Errors:** `404 APPROVAL_NOT_FOUND`, `409 APPROVAL_ALREADY_DECIDED`, `422 REJECT_REMARKS_REQUIRED`.
- **Status:** 200, 207, 404, 409, 422.

> **Send Back / Return** and **Cancel Approval** are **not supported** — `status` has no `returned`/
> `cancelled` value and there is no soft-delete. Cancellation of the *underlying* request is handled by the
> source module (e.g. Leave cancel = delete pending leave request). See §11 Q2.

---

## 7. Approval Workflow (single-level) (`/api/v1/approvals/{approval_id}`) — feature key `approval:read`

| # | Endpoint | Method | URL | Permission |
|---|---|---|---|---|
| 9 | View Current Approval Status | GET | `/approvals/{approval_id}/status` | `approval:read` |
| 10 | View Approval Timeline / Previous Actions | GET | `/approvals/{approval_id}/timeline` | `approval:read` |

- **9. Current Status** — `200` → `{ status, reviewed_by, reviewed_at, reject_remarks }`.
- **10. Timeline / Previous Actions** — `200` → the **single-step** trail derivable from the row:
  `[ { event: "requested", at: requested_at }, { event: <status>, at: reviewed_at, by: reviewed_by, remarks:
  reject_remarks } ]` (the second entry present only once decided). This reflects the single-level schema.
- **Errors:** `404 APPROVAL_NOT_FOUND`.

> **Get Approval Levels**, **View Next Approver**, and true **Multi-level Approval** are **not supported** —
> there are no approval-level/step/workflow-definition/approver-assignment tables. See §11 Q1.

---

## 8. Dashboard (`/api/v1/approvals`) — feature key `approval:read`

Aggregations over `approval_requests`, scoped to the caller's org + permission + data scope.

| # | Endpoint | Method | URL | Permission |
|---|---|---|---|---|
| 11 | Pending Approval Count | GET | `/approvals/summary/pending-count` | `approval:read` |
| 12 | My Pending Approvals | GET | `/approvals/my-pending` | `approval:read` |
| 13 | Recently Approved | GET | `/approvals/recent?decision=approved` | `approval:read` |
| 14 | Recently Rejected | GET | `/approvals/recent?decision=rejected` | `approval:read` |

- **11. Pending Count** — `200` → `{ pending_count, by_request_type: { attendance, leave, login_reset } }`
  within scope. Optional `request_type` filter.
- **12. My Pending Approvals** — pending requests the caller is **permitted to approve** (RBAC feature +
  branch/department data scope). There is no assigned-approver column, so this is a permission/scope-based
  view, not an assignment-based one (§11 Q3). `200` paginated.
- **13/14. Recent Decisions** — `decision` (`approved|rejected`, req), optional `limit`/paging,
  `request_type`; ordered by `reviewed_at desc`. `200` paginated. (Listed as two dashboard items; one endpoint
  with a `decision` filter.)

---

## 9. Business Rules (summary)

- **Tenant isolation:** every operation scoped to `org_id`; cross-org → `404` within scope.
- **Data scope:** approvals filtered by the caller's branch/department access on `employee_id`; a reviewer
  cannot act outside scope.
- **Single decision:** only `pending` requests are actionable; approve/reject are terminal
  (`pending → approved|rejected`); re-deciding is rejected (`APPROVAL_ALREADY_DECIDED`).
- **Reject** requires `reject_remarks`.
- **Decision propagation:** approving/rejecting updates `approval_requests` **and** applies the outcome to the
  source record via the owning module's service, transactionally.
- **No self-approval** of one's own request (business guard, where the reviewer is the subject employee).
- **No Send Back / Cancel** (no status); **no multi-level / levels / next-approver** (no schema).

---

## 10. Permission Matrix

| Feature key | read | edit |
|---|---|---|
| `approval` | List/Search/Filter, Pending, Get Details, History, Status, Timeline, all Dashboard views | Approve, Reject, Bulk Approve, Bulk Reject |

Super admins bypass feature checks; tenant isolation always applies; all reads/actions are branch/department
data-scoped by the request's `employee_id`.

---

## 11. Error Handling, Security & Open Questions

**Error envelope** via `core/exceptions/handlers.py`. Module error codes (proposed, to be registered in
`approvals/exceptions.py`): `APPROVAL_NOT_FOUND`(404), `APPROVAL_ALREADY_DECIDED`(409),
`REJECT_REMARKS_REQUIRED`(422), `APPROVAL_FORBIDDEN_SCOPE`(403), `VALIDATION_ERROR`(422), plus shared
`AUTH_NOT_AUTHENTICATED`(401)/`AUTH_FORBIDDEN`(403).

**HTTP status codes used:** 200, 207 (bulk multi-status), 400, 401, 403, 404, 409, 422.

**Security considerations:** every route enforces `require_permission` + tenant scope + branch/department data
scope; every approve/reject is recorded in the Activity Log (actor, org, request id, before/after status,
remarks); bulk actions validate each item and never leak cross-org/out-of-scope rows; timestamps
timezone-aware; no secrets/PII in logs; rate limiting per the security baseline on action and bulk endpoints.

### Open Questions
1. **Multi-level workflow (Q1) — NOT supported.** No approval-levels/steps/workflow-definition/next-approver/
   assigned-approver tables exist; the engine is single-level. Multi-level Approval, Get Approval Levels, View
   Next Approver, and multi-step Timeline are omitted (single-step timeline provided). Confirm whether
   multi-level is planned (needs new schema).
2. **Send Back & Cancel (Q2) — NOT supported.** No `returned`/`cancelled` status and no soft-delete. Both are
   omitted; underlying-request cancellation stays with the source module. Confirm.
3. **My Pending Approvals model (Q3).** Defined as permission/scope-based (no assigned-approver column).
   Confirm this is acceptable vs introducing an approver-assignment column.
4. **Feature-key granularity (Q4).** `permissions.py` is a stub; confirm the single `approval` key vs
   per-`request_type` approval rights (e.g. separate leave-approval vs attendance-approval permissions).
5. **Source-detail submission (Q5).** `attendance_regularization_requests` and `login_reset_requests` are
   owned by this module but have no other module home; their **submission** endpoints are not in this
   workflow-only contract. Decide which contract owns creating them (and how `approval_requests` rows are
   raised for each `request_type`).
6. **Decision → source propagation (Q6).** Approve/reject must apply the outcome to the source
   (`leave_requests`, attendance regularization, login-reset). The orchestration/transaction boundary is a
   service concern; confirm the mechanism (direct service call vs domain event) is settled before
   implementation.
7. **Envelope key names (Q7).** `shared/schemas/response.py` is a stub; final envelope field names must match
   once implemented (same open item as prior contracts).
