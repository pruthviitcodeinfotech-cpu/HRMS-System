# Authentication API Contract

> Module: `app/modules/auth`
> API Version: `v1` — all routes are served under `API_V1_PREFIX` (`/api/v1`).
> Status: **Contract only.** No FastAPI/SQLAlchemy/Pydantic/service/repository code is defined here.
> Source of truth: `docs/architecture.md` (Backend Architecture), migration `0007_user_management_rbac`
> (Authentication DB schema), `modules/README.md` (module responsibilities), and `.env.example` (JWT config).

This contract documents **only** the endpoints supported by the approved architecture and the existing
database schema. Endpoints implied by common auth systems but **not** backed by the current schema
(password reset, email verification, account lockout) are intentionally **not** contracted here and are
listed in **§9 Open Questions**.

---

## 1. Module Overview

### Purpose

Provide authentication for the HRMS platform: verify user credentials, issue and refresh JWT access
tokens, and manage user sessions (refresh-token lifecycle). Authorization decisions (RBAC feature
permissions and branch/department data scope) are **enforced** using data owned by the `rbac` module but
are consumed here to build the authenticated request context.

### Scope

**In scope (this contract):**

- Credential login and JWT access-token + refresh-token issuance.
- Access-token refresh using a valid refresh token.
- Logout (revocation of the current session/refresh token).
- Retrieval of the current authenticated user (`/me`).
- Session management: list the current user's sessions, revoke a specific session, revoke all other
  sessions.

**Explicitly out of scope (owned by other modules or unsupported by current schema):**

- User creation/registration, profile edits, and **self-service password change** — owned by the
  **User Management & RBAC** module (the `users` table is created by migration `0007_user_management_rbac`).
  Per the decision recorded for this contract, `change-password` is **deferred to the User module**.
- Rights templates, permission assignment, branch/department scoping management — owned by the `rbac`
  module.
- Password reset, email verification, and account lockout — **no supporting schema exists** (see §9).
- **Token validation is not a public endpoint.** It is implemented as the shared `current_user`
  dependency (see §3).

### Responsibilities

| Responsibility | Notes |
|---|---|
| Authenticate credentials (email + password) | Verify `password_hash` via `core/security/password.py`. |
| Issue JWT access tokens | HS256, short-lived (`ACCESS_TOKEN_TTL`). |
| Issue/refresh refresh tokens | Backed by `user_sessions` rows; revocable. |
| Persist and revoke sessions | `user_sessions.is_active` / `revoked_at`. |
| Reject invalid principals | Inactive, soft-deleted, revoked-session, and invalid-token users are rejected before service logic. |
| Provide authenticated user context | For `/me` and for downstream `current_user` / `require_permission` dependencies. |

### Dependencies

| Dependency | Location | Used for |
|---|---|---|
| Password hashing | `core/security/password.py` | Verify credentials. |
| JWT sign/verify | `core/security/jwt.py` | Access + refresh token encode/decode. |
| Permission registry | `core/security/permissions.py` | Feature-key catalog (consumed for authorization context). |
| Auth dependencies | `core/dependencies/auth.py` | `current_user`, `current_org`, `require_permission`. |
| DB session | `core/dependencies/db.py` | One async session per request. |
| Tenant middleware | `core/middleware/tenant.py` | Resolves `org_id` context (see §9 for login-time resolution). |
| Request context middleware | `core/middleware/request_context.py` | Correlation/request id in every response. |
| Response envelope | `shared/schemas/response.py` | Standard success/error envelope. |
| Pagination schema | `shared/schemas/pagination.py` | Paginated session list. |
| RBAC tables (read) | migration `0007_user_management_rbac` | Effective permissions/scope for `/me` context. |

**Schema tables consumed** (from `0007_user_management_rbac`): `users`, `user_sessions`, and — for
authorization context — `rights_templates`, `rights_template_permissions`, `user_template_assignments`,
`user_custom_permissions`, `user_branch_access`, `user_department_access`.

---

## 2. Authentication Flow

The project uses **JWT access tokens + revocable refresh tokens**, as defined in the Backend Architecture
("Authentication and RBAC flow"). Access tokens protect both HTTP APIs and WebSocket entry points.

### 2.1 Login

1. Client submits credentials (`email`, `password`) within a resolved tenant/org context (see §9 Q1).
2. The service looks up the active, non-deleted user by `(org_id, email)`.
3. On success it:
   - creates a `user_sessions` row (`session_token`, `expires_at = now + REFRESH_TOKEN_TTL`,
     `is_active = true`, optional `device_info`, `ip_address`),
   - updates `users.last_login_at`,
   - returns an **access token** (short-lived) and a **refresh token** (tied to the session).
4. Failure (unknown user, bad password, inactive, or soft-deleted user) returns a generic
   `401 AUTH_INVALID_CREDENTIALS` — credential-existence is not disclosed. An authenticated-but-inactive
   user is rejected with `403 AUTH_USER_INACTIVE` only where the user is already known to be a valid
   principal; login itself uses the generic failure.

### 2.2 Authenticated request

1. Client sends `Authorization: Bearer <access_token>`.
2. The `current_user` dependency verifies signature + expiry, then confirms the user is active, not
   soft-deleted, and (when the token carries a session reference) that the session is still active.
3. Invalid/expired/revoked → `401`; valid but not permitted for a given feature → `403`.

### 2.3 Refresh

1. Client submits a valid, non-expired, non-revoked refresh token.
2. The service validates the associated `user_sessions` row (`is_active = true`, `revoked_at IS NULL`,
   `expires_at > now`) and that the user is still active/non-deleted.
3. A **new access token** is issued. Refresh-token rotation behavior is a security decision (see §7 and
   §9 Q3).

### 2.4 Logout / revoke

1. Authenticated client requests logout (optionally naming a specific refresh token/session).
2. The corresponding `user_sessions` row(s) are revoked (`is_active = false`, `revoked_at = now`).
3. Subsequent use of the revoked refresh token → `401 AUTH_SESSION_REVOKED`. Existing access tokens
   remain valid until natural expiry (short TTL) unless a session reference is carried and checked.

### 2.5 Principal-rejection rules (all flows)

Per architecture, the following are rejected **before** service logic runs:

- Invalid/expired/malformed token.
- `users.is_active = false`.
- `users.deleted_at IS NOT NULL` (soft-deleted).
- Session revoked/expired (`user_sessions.is_active = false`, `revoked_at`, or `expires_at <= now`).

---

## 3. Authorization

### 3.1 RBAC integration

Authorization is **two-layer** (per architecture):

1. **Feature permission** — CRUD-style `feature_key` permissions resolved from:
   - the user's assigned rights template (`user_template_assignments` → `rights_template_permissions`), and
   - per-user overrides (`user_custom_permissions`), which take precedence.
2. **Data scope** — branch/department access from `user_branch_access` and `user_department_access`.

**Super admins** (`users.is_super_admin = true`) bypass feature-permission checks, but **tenant isolation
(`org_id`) always applies**.

### 3.2 Permission checks

- The **authentication endpoints in this contract are self-service** (a user acting on their own session
  and identity). They therefore require **authentication only** — no specific `feature_key` permission —
  except `login` and `refresh`, which are unauthenticated.
- General protected routes in other modules use the `require_permission` dependency, which checks the
  feature permission and branch/department scope before the router calls the service.
- Effective permissions/scope are exposed read-only via `GET /auth/me` so clients can drive UI state.

### 3.3 Token validation

Token validation is **internal** — implemented as the `current_user` dependency in
`core/dependencies/auth.py`, not exposed as a public endpoint. It performs:

- JWT signature verification (HS256, `JWT_SECRET`),
- expiry check,
- principal checks (active, non-deleted, session not revoked/expired).

The same validation guards HTTP routes **and** WebSocket connect (per architecture, sockets authenticate
on connect using the same user/session rules).

---

## 4. API Endpoints

Base path for all endpoints: **`/api/v1/auth`**.

| # | Name | Method | Path | Auth required |
|---|---|---|---|---|
| 1 | Login | POST | `/api/v1/auth/login` | No |
| 2 | Refresh Access Token | POST | `/api/v1/auth/refresh` | No (refresh token in body) |
| 3 | Logout | POST | `/api/v1/auth/logout` | Yes |
| 4 | Get Current User (Me) | GET | `/api/v1/auth/me` | Yes |
| 5 | List Sessions | GET | `/api/v1/auth/sessions` | Yes |
| 6 | Revoke a Session | DELETE | `/api/v1/auth/sessions/{session_id}` | Yes |
| 7 | Revoke All Other Sessions | POST | `/api/v1/auth/sessions/revoke-all` | Yes |

All responses use the standard envelope defined in **§5**.

---

### 4.1 Login

- **Endpoint Name:** Login
- **Purpose:** Authenticate a user by credentials and issue an access token + refresh token, creating a
  session.
- **HTTP Method:** `POST`
- **URL:** `/api/v1/auth/login`
- **Authentication Required:** No
- **Required Permission:** None
- **Headers:**
  - `Content-Type: application/json`
  - Tenant-resolution header/context as required by the tenant middleware (see §9 Q1).
- **Path Parameters:** None
- **Query Parameters:** None
- **Request Body:**

  ```json
  {
    "email": "user@example.com",
    "password": "string",
    "device_info": "Chrome on Windows 11"
  }
  ```

  | Field | Type | Required | Notes |
  |---|---|---|---|
  | `email` | string | Yes | Matched against `users.email` within resolved `org_id`. |
  | `password` | string | Yes | Verified against `users.password_hash`. Never logged. |
  | `device_info` | string | No | Stored on `user_sessions.device_info` (≤ 500 chars). |

- **Validation Rules:** see §6 (email format; `password` non-empty; `device_info` ≤ 500 chars).
- **Success Response:** `200 OK`

  ```json
  {
    "success": true,
    "data": {
      "access_token": "<jwt>",
      "refresh_token": "<opaque-or-jwt>",
      "token_type": "bearer",
      "expires_in": 900,
      "user": {
        "id": 123,
        "org_id": 1,
        "name": "Jane Admin",
        "email": "user@example.com",
        "mobile_country_code": "+91",
        "mobile_number": "9876543210",
        "is_super_admin": false,
        "is_active": true,
        "employee_id": 456,
        "last_login_at": "2026-07-08T10:15:00Z"
      }
    },
    "error": null,
    "meta": { "request_id": "..." }
  }
  ```

  `expires_in` is `ACCESS_TOKEN_TTL` (900s). The refresh token maps to the created `user_sessions` row.

- **Error Responses:**

  | Code | HTTP | When |
  |---|---|---|
  | `AUTH_INVALID_CREDENTIALS` | 401 | Unknown email, wrong password, inactive, or soft-deleted user (generic, non-disclosing). |
  | `VALIDATION_ERROR` | 422 | Missing/invalid body fields. |
  | `RATE_LIMITED` | 429 | Too many login attempts (see §7). |
  | `TENANT_UNRESOLVED` | 400 | Org/tenant context could not be resolved (see §9 Q1). |

- **HTTP Status Codes:** `200`, `400`, `422`, `429`, `401`.
- **Notes:** Rate-limited. `ip_address` and `device_info` are captured to the session. `last_login_at`
  is updated on success.

---

### 4.2 Refresh Access Token

- **Endpoint Name:** Refresh Access Token
- **Purpose:** Exchange a valid refresh token for a new access token.
- **HTTP Method:** `POST`
- **URL:** `/api/v1/auth/refresh`
- **Authentication Required:** No (the refresh token itself is the credential)
- **Required Permission:** None
- **Headers:** `Content-Type: application/json`
- **Path Parameters:** None
- **Query Parameters:** None
- **Request Body:**

  ```json
  { "refresh_token": "<opaque-or-jwt>" }
  ```

  | Field | Type | Required | Notes |
  |---|---|---|---|
  | `refresh_token` | string | Yes | Must map to an active, non-expired `user_sessions` row. |

- **Validation Rules:** `refresh_token` non-empty (see §6).
- **Success Response:** `200 OK`

  ```json
  {
    "success": true,
    "data": {
      "access_token": "<jwt>",
      "token_type": "bearer",
      "expires_in": 900,
      "refresh_token": "<opaque-or-jwt>"
    },
    "error": null,
    "meta": { "request_id": "..." }
  }
  ```

  `refresh_token` is re-returned **only if rotation is enabled** (see §7 / §9 Q3); otherwise omit.

- **Error Responses:**

  | Code | HTTP | When |
  |---|---|---|
  | `AUTH_REFRESH_INVALID` | 401 | Refresh token unknown, malformed, or expired. |
  | `AUTH_SESSION_REVOKED` | 401 | Associated session was revoked. |
  | `AUTH_USER_INACTIVE` | 403 | User became inactive/soft-deleted since issuance. |
  | `VALIDATION_ERROR` | 422 | Missing `refresh_token`. |
  | `RATE_LIMITED` | 429 | Too many refresh attempts. |

- **HTTP Status Codes:** `200`, `401`, `403`, `422`, `429`.
- **Notes:** Rate-limited. Does not require an access token.

---

### 4.3 Logout

- **Endpoint Name:** Logout (Revoke Refresh Token / current session)
- **Purpose:** Revoke the caller's current session so its refresh token can no longer be used.
- **HTTP Method:** `POST`
- **URL:** `/api/v1/auth/logout`
- **Authentication Required:** Yes (`Bearer` access token)
- **Required Permission:** None (self-service)
- **Headers:** `Authorization: Bearer <access_token>`, `Content-Type: application/json`
- **Path Parameters:** None
- **Query Parameters:** None
- **Request Body:** (optional)

  ```json
  { "refresh_token": "<opaque-or-jwt>" }
  ```

  | Field | Type | Required | Notes |
  |---|---|---|---|
  | `refresh_token` | string | No | If provided, revokes that specific session (must belong to the caller). If omitted, revokes the session referenced by the access token. |

- **Validation Rules:** if `refresh_token` present, it must be a non-empty string owned by the caller.
- **Success Response:** `204 No Content` (no body).
- **Error Responses:**

  | Code | HTTP | When |
  |---|---|---|
  | `AUTH_NOT_AUTHENTICATED` | 401 | Missing/invalid/expired access token. |
  | `AUTH_SESSION_NOT_FOUND` | 404 | Provided `refresh_token`/session does not belong to the caller. |

- **HTTP Status Codes:** `204`, `401`, `404`.
- **Notes:** Sets `user_sessions.is_active = false`, `revoked_at = now`. Access tokens already issued
  remain valid until natural expiry unless a carried session reference is checked on each request.

---

### 4.4 Get Current User (Me)

- **Endpoint Name:** Get Current User
- **Purpose:** Return the authenticated user's profile plus effective authorization context.
- **HTTP Method:** `GET`
- **URL:** `/api/v1/auth/me`
- **Authentication Required:** Yes
- **Required Permission:** None (self)
- **Headers:** `Authorization: Bearer <access_token>`
- **Path Parameters:** None
- **Query Parameters:** None
- **Request Body:** None
- **Validation Rules:** None (identity taken from token).
- **Success Response:** `200 OK`

  ```json
  {
    "success": true,
    "data": {
      "id": 123,
      "org_id": 1,
      "name": "Jane Admin",
      "email": "user@example.com",
      "mobile_country_code": "+91",
      "mobile_number": "9876543210",
      "is_super_admin": false,
      "is_active": true,
      "employee_id": 456,
      "last_login_at": "2026-07-08T10:15:00Z",
      "permissions": [
        {
          "feature_key": "employee.master",
          "can_create": true,
          "can_read": true,
          "can_edit": false,
          "can_delete": false
        }
      ],
      "data_scope": {
        "branch_ids": [10, 11],
        "department_ids": [4]
      }
    },
    "error": null,
    "meta": { "request_id": "..." }
  }
  ```

  `permissions` is the effective set (template ⊕ custom overrides). For super admins, the response
  indicates full feature access via `is_super_admin = true` (see §9 Q4 on exact representation).

- **Error Responses:**

  | Code | HTTP | When |
  |---|---|---|
  | `AUTH_NOT_AUTHENTICATED` | 401 | Missing/invalid/expired token. |
  | `AUTH_USER_INACTIVE` | 403 | User inactive/soft-deleted. |

- **HTTP Status Codes:** `200`, `401`, `403`.
- **Notes:** Read-only. Password hash and other secrets are never returned.

---

### 4.5 List Sessions

- **Endpoint Name:** List Sessions
- **Purpose:** List the caller's own sessions (active and, optionally, historical).
- **HTTP Method:** `GET`
- **URL:** `/api/v1/auth/sessions`
- **Authentication Required:** Yes
- **Required Permission:** None (self)
- **Headers:** `Authorization: Bearer <access_token>`
- **Path Parameters:** None
- **Query Parameters:**

  | Param | Type | Required | Default | Notes |
  |---|---|---|---|---|
  | `page` | int | No | 1 | 1-based (per architecture pagination rules). |
  | `page_size` | int | No | module default | Bounded page size. |
  | `active_only` | bool | No | true | Allowlisted filter; when true returns only `is_active = true`. |

- **Request Body:** None
- **Validation Rules:** invalid filter/sort/pagination → `422` (per architecture).
- **Success Response:** `200 OK` (paginated envelope)

  ```json
  {
    "success": true,
    "data": {
      "items": [
        {
          "id": 987,
          "device_info": "Chrome on Windows 11",
          "ip_address": "203.0.113.5",
          "created_at": "2026-07-08T10:15:00Z",
          "expires_at": "2026-07-22T10:15:00Z",
          "revoked_at": null,
          "is_active": true,
          "is_current": true
        }
      ],
      "page": 1,
      "page_size": 20,
      "total": 1
    },
    "error": null,
    "meta": { "request_id": "..." }
  }
  ```

  `session_token` is **never** returned. `is_current` marks the session tied to the calling access token.

- **Error Responses:**

  | Code | HTTP | When |
  |---|---|---|
  | `AUTH_NOT_AUTHENTICATED` | 401 | Missing/invalid token. |
  | `VALIDATION_ERROR` | 422 | Invalid pagination/filter parameter. |

- **HTTP Status Codes:** `200`, `401`, `422`.
- **Notes:** Empty result returns `items: []`, never `null` (per architecture).

---

### 4.6 Revoke a Session

- **Endpoint Name:** Revoke a Session (Revoke Refresh Token)
- **Purpose:** Revoke one specific session belonging to the caller.
- **HTTP Method:** `DELETE`
- **URL:** `/api/v1/auth/sessions/{session_id}`
- **Authentication Required:** Yes
- **Required Permission:** None (self; only the caller's own sessions)
- **Headers:** `Authorization: Bearer <access_token>`
- **Path Parameters:**

  | Param | Type | Notes |
  |---|---|---|
  | `session_id` | int | `user_sessions.id`; must belong to the caller. |

- **Query Parameters:** None
- **Request Body:** None
- **Validation Rules:** `session_id` is a positive integer.
- **Success Response:** `204 No Content`.
- **Error Responses:**

  | Code | HTTP | When |
  |---|---|---|
  | `AUTH_NOT_AUTHENTICATED` | 401 | Missing/invalid token. |
  | `AUTH_SESSION_NOT_FOUND` | 404 | Session not found within the caller's scope. |

- **HTTP Status Codes:** `204`, `401`, `404`.
- **Notes:** Sets `is_active = false`, `revoked_at = now`. Revoking the current session effectively logs
  the caller out. Idempotent: revoking an already-revoked session still returns `204`.

---

### 4.7 Revoke All Other Sessions

- **Endpoint Name:** Revoke All Other Sessions (logout everywhere else)
- **Purpose:** Revoke every session for the caller **except** the current one.
- **HTTP Method:** `POST`
- **URL:** `/api/v1/auth/sessions/revoke-all`
- **Authentication Required:** Yes
- **Required Permission:** None (self)
- **Headers:** `Authorization: Bearer <access_token>`
- **Path Parameters:** None
- **Query Parameters:** None
- **Request Body:** None
- **Validation Rules:** None.
- **Success Response:** `200 OK`

  ```json
  {
    "success": true,
    "data": { "revoked_count": 3 },
    "error": null,
    "meta": { "request_id": "..." }
  }
  ```

- **Error Responses:**

  | Code | HTTP | When |
  |---|---|---|
  | `AUTH_NOT_AUTHENTICATED` | 401 | Missing/invalid token. |

- **HTTP Status Codes:** `200`, `401`.
- **Notes:** The current session (identified via the access token's session reference) is preserved.
  Sets `is_active = false`, `revoked_at = now` on all other sessions.

---

## 5. Request & Response Standards

Per architecture ("API standards" / "Error handling"), all responses use the shared success/error
envelope from `shared/schemas`.

### 5.1 Success envelope

```json
{
  "success": true,
  "data": { },
  "error": null,
  "meta": { "request_id": "<correlation-id>" }
}
```

- `data` carries the resource or action result (object; `null` for `204` no-body responses).
- List endpoints place the collection under `data.items` with `page`, `page_size`, `total`
  (`shared/schemas/pagination.py`).

### 5.2 Error envelope

```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "AUTH_INVALID_CREDENTIALS",
    "message": "Invalid email or password.",
    "details": [
      { "field": "email", "message": "Invalid email format." }
    ]
  },
  "meta": { "request_id": "<correlation-id>" }
}
```

- `error.code` — stable, machine-readable application error code.
- `error.message` — human-readable, safe for clients (no secrets/SQL/tokens).
- `error.details` — optional field-level list (present for `VALIDATION_ERROR`).
- `meta.request_id` — correlation id from request-context middleware, included when available.

### 5.3 General rules (from architecture)

- ORM models are never returned directly; only Pydantic DTO shapes cross the boundary.
- Timestamps are timezone-aware ISO-8601 (e.g. `2026-07-08T10:15:00Z`).
- IDs are integers.
- Empty lists return `items: []`, not `null`.

> **Note on exact envelope key names:** `shared/schemas/response.py` is a foundation-phase stub. The
> shapes above follow the architecture's stated envelope rules; the concrete key names must match the
> shared response schema once implemented (see §9 Q5).

---

## 6. Validation Rules

| Endpoint | Field | Rule |
|---|---|---|
| Login | `email` | Required; valid email format; matched within `org_id`; max length 255 (per `users.email`). |
| Login | `password` | Required; non-empty string. (Complexity policy is **not defined** — see §9 Q2.) |
| Login | `device_info` | Optional; string; ≤ 500 chars (per `user_sessions.device_info`). |
| Refresh | `refresh_token` | Required; non-empty string. |
| Logout | `refresh_token` | Optional; non-empty string when present; must belong to caller. |
| List Sessions | `page` | Optional; integer ≥ 1. |
| List Sessions | `page_size` | Optional; integer within bounded range. |
| List Sessions | `active_only` | Optional; boolean; allowlisted filter. |
| Revoke Session | `session_id` (path) | Required; positive integer. |

Validation layering (per architecture): Pydantic (shape/type) → dependencies (auth/tenant/pagination) →
service (domain rules) → DB constraints (uniqueness/referential integrity). Invalid body → `422`;
invalid filter/sort/pagination → `422`.

---

## 7. Security Considerations

### JWT

- Algorithm: `HS256` (`JWT_ALGORITHM`). Signing secret: `JWT_SECRET` (environment-only, never committed).
- Access tokens are short-lived and used for both HTTP and WebSocket authentication.
- Token claims must not carry secrets or sensitive PII beyond what identity requires (subject/user id,
  org id, session reference, expiry).

### Refresh Tokens

- Backed by `user_sessions` rows and therefore **revocable** (unlike stateless access tokens).
- Stored as `user_sessions.session_token` (unique, ≤ 500 chars). The raw token value must be treated as a
  secret and never returned by list/read endpoints.

### Token Expiry

- Access token TTL: `ACCESS_TOKEN_TTL = 900` seconds (15 minutes).
- Refresh token TTL: `REFRESH_TOKEN_TTL = 1209600` seconds (14 days), reflected in
  `user_sessions.expires_at`.
- Expired refresh tokens/sessions are rejected with `401`.

### Password Rules

- Passwords are verified against `users.password_hash` using `core/security/password.py` (strong hashing
  required per architecture security baseline).
- A concrete password **complexity/strength policy is not defined** in the approved architecture or config
  (see §9 Q2). Login only requires a non-empty password.

### Session Security

- Sessions capture `ip_address` (INET) and `device_info` for auditability.
- Revocation sets `is_active = false` + `revoked_at`; revoked/expired sessions cannot refresh.
- Logout, single-session revoke, and revoke-all-others let users contain compromised sessions.
- Tenant isolation (`org_id`) applies to every session operation; a caller can only see/revoke their own
  sessions.

### Rate Limiting

- Auth-sensitive endpoints (`login`, `refresh`) must be rate-limited (architecture security baseline).
- Rate-limit breaches return `429 RATE_LIMITED`. *(429 is not enumerated in the architecture's HTTP status
  list; its use for the rate-limiting requirement is proposed here — see §9 Q6.)*

### Account Locking

- **Not supported by the current schema.** `users` has no `failed_login_attempts` / `locked_until`
  columns. `is_active = false` is an administrative deactivation, not automatic lockout. See §9 Q7.

### Additional

- No secrets, tokens, passwords, or PII in logs (architecture logging rules) — passwords, JWTs, refresh
  tokens, and session tokens are redacted.
- HTTPS termination in production; strict CORS allowlist per environment.

---

## 8. Error Handling

All errors flow through `core/exceptions/handlers.py` into the standard error envelope (§5.2), with
rollback on failed requests. Module-specific exceptions map to stable application error codes.

| Error Code | HTTP | Meaning |
|---|---|---|
| `AUTH_INVALID_CREDENTIALS` | 401 | Login failed (bad email/password, inactive, or soft-deleted) — non-disclosing. |
| `AUTH_NOT_AUTHENTICATED` | 401 | Missing/invalid/expired access token on a protected route. |
| `AUTH_TOKEN_INVALID` | 401 | Access token malformed or signature invalid. |
| `AUTH_TOKEN_EXPIRED` | 401 | Access token expired. |
| `AUTH_REFRESH_INVALID` | 401 | Refresh token unknown, malformed, or expired. |
| `AUTH_SESSION_REVOKED` | 401 | Session/refresh token was revoked. |
| `AUTH_USER_INACTIVE` | 403 | Authenticated principal is inactive/soft-deleted. |
| `AUTH_FORBIDDEN` | 403 | Authenticated but lacks required permission/scope (applies to protected non-auth routes). |
| `AUTH_SESSION_NOT_FOUND` | 404 | Session not found within the caller's scope. |
| `TENANT_UNRESOLVED` | 400 | Org/tenant context could not be resolved at login (see §9 Q1). |
| `VALIDATION_ERROR` | 422 | Request body/params failed validation (with `error.details`). |
| `RATE_LIMITED` | 429 | Rate limit exceeded on an auth-sensitive endpoint. |
| `INTERNAL_ERROR` | 500 | Unhandled error; generic message, details logged server-side only. |

> Error codes are proposed stable identifiers for this module; final code strings must be registered in
> the module's `exceptions.py` / `constants.py` during implementation.

---

## 9. Open Questions

The following cannot be fully determined from the approved architecture and current schema. They are
listed instead of assumed.

1. **Login-time tenant/org resolution (Q1).** `users` is unique on `(org_id, email)`, so login needs an
   `org_id` before authentication. The architecture states the tenant middleware resolves org context,
   but **the exact mechanism (subdomain, `X-Org` header, org slug in body, etc.) is not specified.**
   How is `org_id` resolved for the unauthenticated `login` request?
2. **Password complexity policy (Q2).** No password strength/complexity/expiry policy is defined in the
   architecture or config. What rules (length, character classes, history, expiry) apply? (Primarily
   relevant to the User module's change-password, but affects any admin-set passwords.)
3. **Refresh-token rotation (Q3).** Should `refresh` rotate the refresh token (invalidate old, issue new)
   or keep the same refresh token until expiry? The architecture does not specify.
4. **`/me` permission representation for super admins (Q4).** Should super admins receive an explicit
   full-permission list, a wildcard marker, or only the `is_super_admin` flag with client-side
   interpretation?
5. **Concrete envelope key names (Q5).** `shared/schemas/response.py` is a stub. Confirm the final field
   names for the success/error envelope (`data` / `error` / `meta.request_id`, etc.) so schemas match.
6. **`429` status usage (Q6).** Rate limiting is required, but `429` is not in the architecture's
   enumerated HTTP status list. Confirm `429 RATE_LIMITED` as the standard response for rate-limit
   breaches.
7. **Password reset, email verification, account lockout (Q7) — NOT contracted.** There are **no**
   supporting tables/columns in migrations `0001`–`0014` (no reset-token table, no `email_verified`
   column, no `failed_login_attempts`/`locked_until`). If these flows are required, they need new schema +
   migrations before they can be added to this contract. Endpoints such as *Forgot Password*, *Reset
   Password*, *Verify Reset Token*, *Verify Email*, and *Resend Verification Email* are therefore **not
   defined here**.
8. **Change Password ownership (Q8) — deferred.** Per the decision for this contract, self-service
   `change-password` is owned by the **User Management & RBAC** module, not `auth`. Confirm it will be
   contracted there.
```
