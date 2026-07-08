# Notification Management API Contract

> Module: `app/modules/notifications`
> API Version: `v1` — all routes under `API_V1_PREFIX` (`/api/v1`).
> Status: **Contract only** (no FastAPI/SQLAlchemy/Pydantic/service/repository code).
> Sources of truth: `docs/architecture.md` (Backend Architecture), migration `0014_notifications`
> (+ `0016`), the notifications model (`notifications/models.py`), and the approved Authentication, RBAC,
> Employee, and prior API Contracts.

Covers the in-app notification message table (`notifications`) and per-user recipient state
(`notification_recipients`): admin creation/targeting, the user notification center, read/archive/delete
actions, bulk operations, and a per-recipient state timeline. **Excludes** Authentication, RBAC, Employee,
Shift, Attendance, Leave, Approval, Payroll, Settlements, Hardware, Settings, Dashboard, Reports.

> **Scope note (per the model docstring):** delivery providers, templates, preferences, websocket state, and
> background jobs are **outside** this database layer. Delivery is represented only by
> `notification_recipients.delivered_at` (a single timestamp) — there is no multi-attempt delivery log
> (§10 Q1). Real-time push (WebSocket) is a delivery surface, not part of this contract.

---

## 1. Module Overview

### Purpose
Store in-app notification messages and each recipient's per-user state (delivered/read/archived/deleted), and
expose an admin creation/targeting surface plus a user-facing notification center with actions.

### Responsibilities
- Notification messages (`notifications`): create (admin/system), read, list/search/filter.
- Recipient state (`notification_recipients`): assign to users, view recipients + delivery status.
- User notification center: my notifications, unread, count, recent; mark read/unread, archive/unarchive,
  delete; bulk operations; per-recipient timeline.

### Dependencies
| Dependency | Location / Module | Used for |
|---|---|---|
| Auth/permission deps | `core/dependencies/auth.py` | `current_user`, `current_org`, `require_permission` |
| Tenant middleware | `core/middleware/tenant.py` | `org_id` scoping |
| RBAC | `rbac` | admin permission to create/target; resolving role-based targeting to users |
| Users | `rbac` (`users`) | recipients are **users** (`user_id`), `created_by` |
| Employee (read) | `employee` | resolve an employee → their user when targeting by employee |
| WebSocket infra | `infrastructure/websockets/` | real-time push (delivery surface) — **out of scope** |
| Response/pagination schemas | `shared/schemas/` | envelope + paginated lists |
| Activity Log (audit) | `audit` | notification audit history (§9) — **owned by audit module** |

**Tables owned:** `notifications`, `notification_recipients`.

### Module boundaries
- Recipients are **users** (`notification_recipients.user_id → users`). Targeting by employee/role resolves to
  user accounts at the service layer.
- User-facing **actions act only on the caller's own recipient row** (resolved by `(notification_id,
  current_user)`); a user cannot alter another user's state.
- FKs: `notifications.org_id`→organizations (RESTRICT), `created_by`→users (SET NULL);
  `notification_recipients.notification_id`→notifications (CASCADE), `user_id`→users (CASCADE),
  `org_id`→organizations (RESTRICT).

---

## 2. Authorization Model

Two-layer RBAC where applicable: feature permission × tenant scope. Super admins bypass feature checks;
tenant isolation (`org_id`) always applies. All endpoints require `Authorization: Bearer <access_token>`.

**Proposed feature key** (register in `core/security/permissions.py` — §10 Q4): `notification`
(`create`/`read` for the **admin** surface — create notifications, assign recipients, view recipients,
org-wide list). The **user notification center** (my notifications, read/unread, archive/unarchive, delete,
bulk, timeline) is **self-service** — any authenticated user on their **own** recipient rows, **no** feature
permission required.

---

## 3. Request & Response Standards

Reuses the shared envelope + pagination (`data`/`error`/`meta.request_id`; `data.items`+`page`+`page_size`+
`total`). BIGINT integer IDs; timezone-aware ISO-8601 timestamps; empty lists → `items: []`.

### Pagination / Filtering / Sorting
`page` (≥1, default 1), `page_size` (bounded). Filter/sort allowlists; invalid field → `422`. Repository
applies `org_id` (+ `user_id` for the center) before optional filters.

**Enumerations:** `notification_type` and `priority` are **free-text (no DB CHECK)**; their allowed value sets
are an application-level catalog (§10 Q2), not schema-enforced.

Common omitted errors (all protected endpoints): `401 AUTH_NOT_AUTHENTICATED`, `403 AUTH_FORBIDDEN`,
`422 VALIDATION_ERROR`.

---

## 4. Notification Management (admin) (`/api/v1/notifications`) — feature key `notification`

`notifications` fields: `title` (≤200), `message` (text), `notification_type` (≤50), `priority` (≤20),
`source_module` (≤100), `source_entity_type` (≤100), `source_entity_id` (BIGINT), `created_by`, `created_at`,
`expires_at`.

| # | Endpoint | Method | URL | Permission |
|---|---|---|---|---|
| 1 | Create Notification | POST | `/notifications` | `notification:create` |
| 2 | List / Search / Filter Notifications | GET | `/notifications` | `notification:read` |
| 3 | Get Notification Details | GET | `/notifications/{notification_id}` | `notification:read` |

- **1. Create** — `{ "title", "message", "notification_type", "priority", "source_module"?, "source_entity_type"?, "source_entity_id"?, "expires_at"?, "recipient_user_ids"?: [int] }`.
  Creates the notification and (if `recipient_user_ids` given) the recipient rows. `created_by=caller`.
  **Validation:** `title`/`message`/`notification_type`/`priority` required; `expires_at` in the future if
  present; recipient users must belong to the org. **Note:** most notifications are **system-generated** by
  other modules via the event bus/service; this admin endpoint is for manual/broadcast messages. `201`.
- **2. List / Search / Filter** — filters `notification_type`, `priority`, `source_module`,
  `source_entity_type`/`source_entity_id`, `date_from`/`date_to`, `search` (title/message); sort `created_at`.
  Org-scoped. `200` paginated. (Admin view of all org notifications.)
- **3. Get** — `200` → notification + recipient count / delivery summary. `404 NOTIFICATION_NOT_FOUND`.

---

## 5. Recipient Management (admin) (`/api/v1/notifications/{notification_id}/recipients`) — feature key `notification`

`notification_recipients` fields: `notification_id`, `org_id`, `user_id`, `delivered_at`, `read_at`,
`archived_at`, `deleted_at`, `created_at`. **Unique `(notification_id, user_id)`**.

| # | Endpoint | Method | URL | Permission |
|---|---|---|---|---|
| 4 | Assign Notification to User(s) | POST | `/notifications/{notification_id}/recipients` | `notification:create` |
| 5 | View Recipients + Delivery Status | GET | `/notifications/{notification_id}/recipients` | `notification:read` |

- **4. Assign** — `{ "user_ids": [int] }`. Creates recipient rows (idempotent per `(notification_id,
  user_id)` — duplicates skipped). Users must be in the org. `200`/`207` per-item result.
  `409`/skip on already-assigned.
- **5. View Recipients** — `200` paginated recipients with **delivery status** (`delivered_at`) and state
  (`read_at`, `archived_at`, `deleted_at`) per user. Filters `delivered` (bool), `read` (bool).
  `404 NOTIFICATION_NOT_FOUND`.

---

## 6. User Notification Center (self-service) (`/api/v1/me/notifications`)

Operates on the **caller's own** recipient rows (joined to the notification). No feature permission required.

| # | Endpoint | Method | URL | Auth |
|---|---|---|---|---|
| 6 | My Notifications (list/search/filter/recent) | GET | `/me/notifications` | authenticated |
| 7 | My Notification Count | GET | `/me/notifications/count` | authenticated |
| 8 | Get My Notification | GET | `/me/notifications/{notification_id}` | authenticated |

- **6. My Notifications** — **Query:** `page`, `page_size`, `status` (`unread` → `read_at IS NULL`; `read`),
  `archived` (bool, default false → excludes archived), `notification_type`, `priority`, `source_module`,
  `include_expired` (default false), `sort_by` (`created_at` → **Recent**), `sort_dir`. Excludes rows with
  `deleted_at` set. `200` paginated (notification + this user's state).
  - **Unread Notifications** = `?status=unread`; **Recent** = default `sort_by=created_at desc`.
- **7. Count** — `200` → `{ unread_count, archived_count, total_count }` (excluding deleted). Optional
  `?type=` filter. Powers the bell badge.
- **8. Get My Notification** — `200` → the notification + the caller's recipient state; may set `delivered_at`
  on first fetch (business rule). `404 NOTIFICATION_NOT_FOUND` (or not a recipient).

---

## 7. Notification Actions (self-service) (`/api/v1/me/notifications/{notification_id}`)

Each acts on the caller's own recipient row.

| # | Endpoint | Method | URL | Auth |
|---|---|---|---|---|
| 9 | Mark as Read | POST | `/me/notifications/{notification_id}/read` | authenticated |
| 10 | Mark as Unread | POST | `/me/notifications/{notification_id}/unread` | authenticated |
| 11 | Archive Notification | POST | `/me/notifications/{notification_id}/archive` | authenticated |
| 12 | Unarchive Notification | POST | `/me/notifications/{notification_id}/unarchive` | authenticated |
| 13 | Delete Notification | DELETE | `/me/notifications/{notification_id}` | authenticated |

- **9/10.** set / clear `read_at` (idempotent). `200`.
- **11/12.** set / clear `archived_at` (idempotent). `200`.
- **13.** soft-delete: set `deleted_at` (excluded from center lists). `204`.
- **Errors:** `404 NOTIFICATION_NOT_FOUND` (or caller is not a recipient).

---

## 8. Bulk Operations (self-service) (`/api/v1/me/notifications`)

| # | Endpoint | Method | URL | Auth |
|---|---|---|---|---|
| 14 | Mark Multiple as Read | POST | `/me/notifications/bulk-read` | authenticated |
| 15 | Archive Multiple | POST | `/me/notifications/bulk-archive` | authenticated |
| 16 | Delete Multiple | POST | `/me/notifications/bulk-delete` | authenticated |

- Body `{ "notification_ids": [int] }` (or `{ "all_unread": true }` for bulk-read of all unread). Applies only
  to the caller's own recipient rows; returns `{ affected_count }`. `200`.

---

## 9. Notification History (`/api/v1/me/notifications/{notification_id}/timeline`)

| # | Endpoint | Method | URL | Auth |
|---|---|---|---|---|
| 17 | Notification Timeline | GET | `/me/notifications/{notification_id}/timeline` | authenticated |

- `200` → the recipient state timeline derivable from the row: `[ { event: "created", at: created_at },
  { event: "delivered", at: delivered_at }, { event: "read", at: read_at }, { event: "archived", at:
  archived_at }, { event: "deleted", at: deleted_at } ]` (entries present only when the timestamp is set).
- **Notification Audit History** is owned by the **Activity Log** module (not duplicated here).
- **Notification Delivery History** is **not supported** as a multi-attempt log — only `delivered_at` exists
  (§10 Q1).

---

## 10. Business Rules, Security & Open Questions

### Business Rules
- **Tenant isolation:** all operations scoped to `org_id`. Admin create/assign requires `notification` feature
  permission; center actions are self-service on the caller's own rows only.
- **Recipient uniqueness:** one recipient row per `(notification_id, user_id)`; assign is idempotent.
- **State toggles:** `read_at`/`archived_at` are set/cleared (Mark Read/Unread, Archive/Unarchive); `deleted_at`
  is a soft delete (excluded from center lists); `delivered_at` marks delivery.
- **Expiry:** `expires_at` notifications are excluded from the center by default (`include_expired=false`).
- **Cascade:** deleting a notification (admin/system) cascades to recipient rows (`ON DELETE CASCADE`);
  user-facing Delete is a **soft** per-recipient delete (`deleted_at`).
- **Type/priority** values are validated at the application layer (no DB CHECK).

### Error Handling
Module error codes (proposed, `notifications/exceptions.py`): `NOTIFICATION_NOT_FOUND`(404),
`RECIPIENT_NOT_FOUND`(404), `USER_NOT_FOUND`(404), `ALREADY_ASSIGNED`(409), `VALIDATION_ERROR`(422), plus
shared `AUTH_NOT_AUTHENTICATED`(401)/`AUTH_FORBIDDEN`(403). **Status codes:** 200, 201, 204, 207, 400, 401,
403, 404, 409, 422.

### Security Considerations
Users can read/modify **only their own** notifications; admin create/target requires the `notification`
permission + tenant scope; `source_entity_*` links are exposed only to permitted roles; bulk operations never
touch other users' rows; timestamps timezone-aware; no secrets/PII in logs; rate limiting on create/assign and
bulk endpoints.

### Permission Matrix
| Surface | Permission | Endpoints |
|---|---|---|
| Admin — Notifications | `notification:create` / `notification:read` | Create, List/Search, Get, Assign recipients, View recipients |
| User — Notification Center | self-service (own rows) | My Notifications, Count, Get, Read/Unread, Archive/Unarchive, Delete, bulk, Timeline |

Super admins bypass feature checks; tenant isolation always applies.

### Open Questions
1. **Delivery History (Q1).** Only a single `delivered_at` exists — there is no multi-attempt delivery log.
   "Notification Delivery History" is therefore limited to that timestamp (per-recipient) and the aggregate
   delivery status in §5. Confirm whether a richer delivery log is required (needs new schema).
2. **Type/priority catalog (Q2).** `notification_type` and `priority` have no DB CHECK; confirm the allowed
   value sets to validate at the application layer (and whether they should become CHECK constraints).
3. **Targeting model (Q3).** Recipients are **users**. Confirm whether targeting by role/branch/department or
   "broadcast to all org users" should be supported (resolved to recipient rows at the service layer) and the
   permission for broadcast.
4. **Feature-key catalog (Q4).** `permissions.py` is a stub; confirm the `notification` admin key and that the
   center is self-service (no key).
5. **Delivered-at trigger (Q5).** Whether `delivered_at` is set by the WebSocket/dispatch layer, on first
   fetch, or both — a service/delivery concern outside this contract; confirm the trigger.
6. **Envelope key names (Q6).** `shared/schemas/response.py` is a stub; final envelope field names must match
   once implemented (same open item as prior contracts).
