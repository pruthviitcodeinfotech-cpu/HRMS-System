# HRMS Enterprise Admin Web Application: Authentication & RBAC Architecture

This document defines the authentication lifecycle and Role-Based Access Control (RBAC) architecture for the **Enterprise HR & Payroll Management System (HRMS) Admin Web Application**. It outlines the security boundaries between the Next.js client, Edge middleware, and the FastAPI backend.

---

## 1. Backend Context & JWT Structure

The client application integrates with the existing FastAPI JWT backend. Authentication is validated using a signed JSON Web Token (JWT) using the `HS256` signature algorithm.

### Token Specifications
*   **Access Token TTL:** 15 minutes (`900` seconds).
*   **Refresh Token TTL:** 14 days (`1,209,600` seconds).
*   **Session Tracking:** The backend issues a unique Session ID (`sid`) mapped to a Redis-backed `user_sessions` database table. Revoking a session in Redis invalidates all active access/refresh pairs tied to that `sid` instantly.

### JWT Claims Payload Format
Upon successful authentication, the backend decodes user credentials into a token payload:

```json
{
  "sub": "user_id_long_value",
  "type": "access",
  "jti": "token_unique_identifier",
  "iat": 1783935600,
  "exp": 1783936500,
  "org_id": "organization_id_long_value",
  "is_super_admin": false,
  "is_active": true,
  "sid": "session_uuid_value",
  "roles": ["BranchAdmin"],
  "permissions": [
    { "feature_key": "employee", "can_create": true, "can_read": true, "can_edit": true, "can_delete": false },
    { "feature_key": "employee_salary", "can_create": false, "can_read": true, "can_edit": false, "can_delete": false }
  ],
  "branch_ids": [12, 14],
  "department_ids": [5, 8]
}
```

---

## 2. Token Storage Strategy (SSR Support)

To prevent Cross-Site Scripting (XSS) and Cross-Site Request Forgery (CSRF), and to support Next.js Server-Side Rendering (SSR), both tokens are stored in secure cookies.

```
                    [ Browser Storage ]
                  /                     \
                 /                       \
   [ access_token Cookie ]        [ refresh_token Cookie ]
   - HttpOnly: True               - HttpOnly: True
   - Secure: True                 - Secure: True
   - SameSite: Lax/Strict         - SameSite: Strict
   - Path: /                      - Path: /api/v1/auth/refresh
```

### 1. Access Token Cookie (`access_token`)
*   **Access Scope:** Accessible by Next.js Server Components and Edge Middleware.
*   **Security Flags:** `HttpOnly: true`, `Secure: true`, `SameSite: Lax`, `Path: /`.

### 2. Refresh Token Cookie (`refresh_token`)
*   **Access Scope:** Sent only to the `/auth/refresh` API endpoint.
*   **Security Flags:** `HttpOnly: true`, `Secure: true`, `SameSite: Strict`, `Path: /api/v1/auth/refresh`.

*This configuration prevents client-side scripts from reading the refresh token, securing session credentials from XSS attacks.*

---

## 3. Authentication & Session Lifecycles

### 1. Login Flow

```
[User submits login form]
       |
       v
[Axios: POST /auth/login]
       |
       v
[FastAPI: Validates credentials & creates session in Redis]
       |
       v
[FastAPI: Sends response with HTTP cookies: access_token & refresh_token]
       |
       v
[Axios Client: Intercepts success, clears stores, updates auth Zustand status]
       |
       v
[Next.js Router: Redirects to "/dashboard"]
```

### 2. Logout Flow

```
[User clicks Logout button]
       |
       v
[Axios: POST /auth/logout (passes session SID claim)]
       |
       v
[FastAPI: Deletes session in Redis, invalidating token access]
       |
       v
[FastAPI: Clears client cookies (sets expiry to epoch 1970)]
       |
       v
[Axios Client: Resets Zustand store, clears query caches]
       |
       v
[Next.js Router: Redirects to "/login"]
```

---

## 4. Token Expiry & Silent Refresh Flow

When the 15-minute access token expires, Axios interceptors handle session recovery silently:

```
[Axios Client sends request]
       |
       v
[API responds with 401 (token_expired)]
       |
       v
[Axios Response Interceptor intercepts 401]
       |
       v
[Axios Interceptor pauses queue and triggers Refresh Request]
       |
       +---> [POST /auth/refresh (Sends HttpOnly refresh_token cookie)]
                  |
                  +---(Success: 200)--> [Update access cookie, replay paused queue]
                  |
                  +---(Failure: 401)--> [Clear cookies, reset state, redirect to /login]
```

### Request Queue Optimization
While the `/auth/refresh` request is in progress, any subsequent API calls are intercepted and held in a promise resolver queue. Once the refresh call succeeds, the queue is replayed; if it fails, the queue is rejected, and the session is terminated.

---

## 5. Route & UI Gating (Authorization)

The application enforces security at three distinct points: Route level (Server/Edge), Navigation level (Router), and Component level (React Tree).

```
[ Security Gateways ]
  |
  +---> 1. Edge Level (middleware.ts) Gating: Filters page requests on routing paths.
  |
  +---> 2. Menu Level (Layout Sidebar) Gating: Hides navigation links based on roles.
  |
  +---> 3. Component Level (PermissionGuard) Gating: Shows/hides buttons and form areas.
```

### 1. Page/Route Level Gating
Next.js Edge Middleware intercepts page requests, parsing the user's roles and permissions from the JWT claims to authorize access:
*   If the user lacks the required role or permission, the request is redirected to `/403` (Unauthorized).
*   If the session token is missing, the request is redirected to `/login`.

### 2. Menu/Sidebar Gating
Navigation layouts check permissions before rendering sidebar menu items:

```typescript
// Conceptual schema definition for Sidebar Navigation Links
interface NavItem {
  label: string;
  href: string;
  requiredPermission?: { feature: string; action: 'create' | 'read' | 'edit' | 'delete' };
  requiredRole?: string[];
}

const SIDEBAR_ITEMS: NavItem[] = [
  {
    label: 'Payroll Runs',
    href: '/payroll',
    requiredPermission: { feature: 'payroll', action: 'read' }
  },
  {
    label: 'RBAC Access Settings',
    href: '/settings/rbac',
    requiredRole: ['SuperAdmin']
  }
];
```

*The sidebar component filters items against the user's parsed token claims, preventing unauthorized links from rendering.*

### 3. Component Level Gating (`<PermissionGuard>`)
We wrap granular UI components (such as action buttons, input fields, and tab panels) in client-side permission guards:

```typescript
// Conceptual rendering validation in JSX views
<PermissionGuard 
  permission={{ feature: 'employee_salary', action: 'read' }} 
  fallback={<UnauthorizedAccessAlert />}
>
  <SalaryDetailCard data={employeeData.salary} />
</PermissionGuard>
```

#### Verification Rules:
1.  **Dotted Permission Mapping:** Converts dotted string inputs (e.g., `employee.salary.view` or `employee.create`) into structured JWT permissions checks.
2.  **Super-Admin Privilege:** Skip validation if `is_super_admin: true` is present in the token claims.
3.  **Scoped Constraints:** Evaluate `branch_ids` and `department_ids` from JWT claims to restrict access to records outside the user's scope (e.g., preventing a branch admin from modifying records in another branch).

---

## 6. API Authorization & Scoping Flow

Every outgoing network request uses headers to pass context, allowing the backend to enforce organization-level data isolation:

```
[Client State (Zustand/Query)]
       |
       |  (Injects Authorization Headers)
       v
[Axios Client Instance]
       |
       |  (Sets Headers)
       |  - Authorization: Bearer <access_token>
       |  - x-org-id: <org_id> (extracted from JWT)
       v
[FastAPI Gateway]
       |
       |  (Validates Signature & Decodes org_id)
       v
[Service Transaction Layer (Repository SQL Scope)]
       |
       +---> SELECT * FROM employees WHERE org_id = x_org_id AND branch_id IN (claims.branch_ids);
```

### Header Specifications
1.  **Authorization:** Contains the access token: `Bearer <access_token_value>`.
2.  **x-org-id:** Contains the tenant context ID (`org_id`). This ensures the request is scoped to the correct organization.

---

## 7. Error Handling & Session Expiry

### HTTP 403 (Forbidden) Handling
*   **Trigger:** The client sends a valid token, but lacks the permissions required for the endpoint.
*   **Resolution:** Axios interceptors display an error toast (via `Sonner`) indicating: `"Access Denied: You do not have permissions to perform this action."` The current page layout remains intact.

### HTTP 401 (Unauthorized) Handling
*   **Trigger:** The token is invalid, expired, or has been revoked.
*   **Resolution:** Triggers the silent refresh flow. If the refresh request fails, the user is redirected to `/login`.

### Redis Session Revocation Handling
*   **Trigger:** A SuperAdmin terminates a user's session from the admin panel, deleting the `sid` from Redis.
*   **Resolution:** The user's next API request returns a `401 Unauthorized` status. The token refresh request fails, clearing client cookies and redirecting the user to `/login`.
