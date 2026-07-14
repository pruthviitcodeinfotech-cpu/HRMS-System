# HRMS Enterprise Admin Web Application: Routing & Layout Architecture

This document defines the routing, layout, page hierarchy, and navigation architecture for the **Enterprise HR & Payroll Management System (HRMS) Admin Web Application**. It outlines how Next.js App Router features are structured to enforce security, ensure performance, and provide a premium user experience.

---

## 1. Next.js App Router Structure

The application separates routing paths and layout definitions using Next.js App Router conventions. By using Route Groups, we decouple layout styles and middleware constraints without affecting the URL path.

### Routing Directory Map

```
src/
  middleware.ts                  # Edge middleware for session & tenant validation
  app/
    layout.tsx                   # Root HTML, Global CSS, and Root Providers
    providers.tsx                # Global Providers: TanStack Query, Theme, Toasts
    not-found.tsx                # App-wide 404 Page (dead routes)
    error.tsx                    # App-wide Error Boundary
    
    # -------------------------------------------------------------
    # 1. Unauthenticated Route Group (Auth flow layout)
    # -------------------------------------------------------------
    (auth)/
      layout.tsx                 # Centralized Card Layout with marketing panel
      login/
        page.tsx                 # Login UI (Username/Password or Email invite validation)
        error.tsx                # Error boundary for login failures
      forgot-password/
        page.tsx                 # Reset token request form
      reset-password/
        page.tsx                 # New password confirmation page
        
    # -------------------------------------------------------------
    # 2. Authenticated Route Group (Dashboard Workspace Shell)
    # -------------------------------------------------------------
    (dashboard)/
      layout.tsx                 # Dashboard Shell (Sidebar, Header, User Menu, Heartbeat)
      loading.tsx                # Shell Shimmer Skeleton (Sidebar and Header placeholders)
      error.tsx                  # Dashboard-specific error handler (keeps nav intact)
      
      dashboard/
        page.tsx                 # High-level analytical dashboard widgets
        
      # -- Employee Management Sub-Module --
      employees/
        layout.tsx               # Secondary Nav: Directory, Documents, Import Logs
        page.tsx                 # Directory data grid (AG Grid)
        not-found.tsx            # Triggers if employee_id is not found
        [id]/
          layout.tsx             # Record Banner Layout: Photo, Code, Tab Nav
          page.tsx               # Default: Demographic & Personal Details
          salary/
            page.tsx             # Salary details tab (permission gated)
          documents/
            page.tsx             # Document repository tab
          history/
            page.tsx             # Status history timeline (Rehires/Exits)
            
      # -- Shift Management Sub-Module --
      shifts/
        layout.tsx               # Secondary Nav: Roster Grid, Shift Templates
        page.tsx                 # Weekly interactive scheduler grid
        templates/
          page.tsx               # Template builder list
          
      # -- Attendance Sub-Module --
      attendance/
        layout.tsx               # Secondary Nav: Daily logs, corrections, lock gates
        page.tsx                 # Live punch records grid
        corrections/
          page.tsx               # Correction approvals queue
        locks/
          page.tsx               # Monthly lock constraints
          
      # -- Leaves Sub-Module --
      leaves/
        layout.tsx               # Secondary Nav: Applications, Balances, Policies
        page.tsx                 # Pending leave requests
        balances/
          page.tsx               # Master leave balance list
        policies/
          page.tsx               # Policy rule mapping
          
      # -- Payroll Sub-Module --
      payroll/
        layout.tsx               # Secondary Nav: Run History, Groups, Slips
        page.tsx                 # Active/Previous payroll cycles
        [cycleId]/
          page.tsx               # Cycle execution pipeline (preview, lock, finalize)
        groups/
          page.tsx               # Payroll groups setup
        slips/
          page.tsx               # Slips generation dashboard
          
      # -- Settings & Administration --
      settings/
        layout.tsx               # Settings Nav: Org details, Branch settings, RBAC
        page.tsx                 # Org master profile details
        branches/
          page.tsx               # Branch list and geofencing limits
        departments/
          page.tsx               # Department designations setup
        rbac/
          page.tsx               # Role rights template modifications
```

---

## 2. Route Categorization (Public vs. Protected)

The route namespace is divided into distinct security tiers, managed by the Next.js Edge Middleware.

```
                  [ Incoming Request ]
                           |
                           v
              +------------+------------+
              |   Does Path Match Auth? |
              +------------+------------+
                           |
            +--------------+--------------+
            | Yes                         | No
            v                             v
  +---------+---------+         +---------+---------+
  |  Has valid JWT?   |         |  Has valid JWT?   |
  +---------+---------+         +---------+---------+
            |                             |
      +-----+-----+                 +-----+-----+
      | Yes       | No              | Yes       | No
      v           v                 v           v
  Redirect to   Allow Auth        Allow       Redirect to
  /dashboard    Page              Access      /login
```

### 1. Authentication Routes (Public/Guest Only)
*   **Paths:** `/login`, `/forgot-password`, `/reset-password`.
*   **Access Rules:** Restricted to unauthenticated users. If an authenticated user with a valid JWT attempts to access these routes, the middleware redirects them to `/dashboard`.

### 2. Protected Routes (Authenticated Only)
*   **Paths:** `/dashboard`, `/employees`, `/shifts`, `/attendance`, `/leaves`, `/payroll`, `/settings`.
*   **Access Rules:** Requires a valid, unexpired JWT. If the token is missing or invalid, the request is redirected to `/login`, storing the original URL as a redirect parameter.

### 3. Public Routes
*   **Paths:** `/api/health` (Next.js server status), `/404`, `/500`.
*   **Access Rules:** Always accessible without cookies, tokens, or headers.

---

## 3. Layout Responsibilities

To avoid re-rendering entire screen elements on sub-route transitions, layout responsibilities are separated into nested files.

```
+------------------------------------------------------------+
| 1. Root Layout (Global providers, font faces)              |
|  +------------------------------------------------------+  |
|  | 2. Dashboard Shell Layout (Sidebar, Header, Session) |  |
|  |  +------------------------------------------------+  |  |
|  |  | 3. Module Sub-Layout (Sub-headers, Tabs)       |  |  |
|  |  |  +------------------------------------------+  |  |  |
|  |  |  | 4. Record-Level Layout (Profile Summary) |  |  |  |
|  |  |  |   +------------------------------------+ |  |  |  |
|  |  |  |   | 5. Page Component View             | |  |  |  |
|  |  |  |   +------------------------------------+ |  |  |  |
|  |  |  +------------------------------------------+  |  |  |
|  |  +------------------------------------------------+  |  |
|  +------------------------------------------------------+  |
+------------------------------------------------------------+
```

### Root Layout (`src/app/layout.tsx`)
*   **Responsibility:** Instantiates the HTML baseline.
*   **Key Operations:**
    *   Defines language tags and loads font styles.
    *   Injects global CSS files.
    *   Mounts root context providers (`src/app/providers.tsx`) including TanStack Query, Theme Providers, and Toast notification structures.

### Auth Layout (`src/app/(auth)/layout.tsx`)
*   **Responsibility:** Renders the authentication screen interface.
*   **Key Operations:**
    *   Features a split-pane layout: a login dialog form on one side, and product branding graphics on the other.
    *   Does not render sidebars, headers, or global navigation controls.

### Dashboard Layout (`src/app/(dashboard)/layout.tsx`)
*   **Responsibility:** Renders the main workspace shell for the authenticated admin interface.
*   **Key Operations:**
    *   Renders the primary navigation sidebar and header.
    *   Initializes the `AuthProvider` which decodes tenant metadata (`org_id`) and RBAC permissions from the JWT.
    *   Spawns background session keepers (e.g., token refresh monitors).
    *   Renders global alerts (e.g., connectivity loss alerts).

### Module Layouts (e.g., `src/app/(dashboard)/employees/layout.tsx`)
*   **Responsibility:** Provides secondary navigation paths within specific HRMS modules.
*   **Key Operations:**
    *   Renders a secondary horizontal toolbar containing view options (e.g., switching between "Directory List", "Document Repository", and "Import Logs").
    *   Avoids re-rendering the primary layout sidebar when navigating between tabs in the employee module.

### Record Layouts (e.g., `src/app/(dashboard)/employees/[id]/layout.tsx`)
*   **Responsibility:** Renders contextual detail summaries for specific records.
*   **Key Operations:**
    *   Displays a header card showing the employee's name, profile photo, employee code, and status.
    *   Provides tab navigation to switch between the details sub-pages (Profile, Salary, Documents, History) for the active ID, keeping the base layout elements in place.

---

## 4. Route Features (Dynamic and Special Files)

The architecture utilizes Next.js routing features to manage page states and loading flows.

### Dynamic Segments
*   **Target Entities:** Detailed views that depend on dynamic IDs, such as `employees/[id]` and `payroll/[cycleId]`.
*   **Data Scoping:** Sub-pages extract dynamic parameters (`params.id`) to fetch scoped records.
*   **Fallback Resolution:** If a query fails because the record ID does not exist, the component triggers Next.js's `notFound()` function, routing the user to a contextual 404 page.

### Loading Files (`loading.tsx`)
*   **Loading States:** Custom loading skeletons match the layout of the corresponding view.
*   **Shell Loading:** Placed within `(dashboard)/loading.tsx` to display skeleton blocks for the sidebar and header during initial login loading.
*   **Content Loading:** Placed within child directories (e.g., `employees/loading.tsx`) to show table row skeletons while data is being fetched.

### Error Files (`error.tsx`)
*   **Global Boundary:** Placed at `src/app/error.tsx` to catch layout crashes and render a recovery screen.
*   **Dashboard Boundary:** Placed at `(dashboard)/error.tsx` to handle failures in data loading or layout renders. If a feature crash occurs, the boundary replaces the main page content panel with a retry option, while keeping the main navigation sidebar active.

### Not Found Files (`not-found.tsx`)
*   **Fallback Pages:** Placed at `src/app/not-found.tsx` to handle requests to undefined URLs.
*   **Localized Fallbacks:** Placed in feature subfolders (e.g., `employees/not-found.tsx`) to render descriptive messages when an ID search returns no results.

---

## 5. Route Protection & Middleware Usage

The Edge Middleware (`src/middleware.ts`) acts as the entry guard, checking permissions, credentials, and tenant contexts before requests reach page components.

### Edge Middleware Logic Flow

```typescript
// Conceptual structure of the Edge Middleware execution flow
export async function middleware(request: NextRequest) {
  const token = request.cookies.get('access_token')?.value;
  const isAuthPage = request.nextUrl.pathname.startsWith('/login') || 
                     request.nextUrl.pathname.startsWith('/forgot-password');
  
  // 1. Session Verification
  if (!token) {
    if (!isAuthPage) {
      // Redirect unauthenticated requests to login
      const loginUrl = new URL('/login', request.url);
      loginUrl.searchParams.set('redirect', request.nextUrl.pathname);
      return NextResponse.redirect(loginUrl);
    }
    return NextResponse.next();
  }

  // 2. Token Validation & Context Redirection
  if (isAuthPage) {
    // Authenticated users are redirected away from auth pages
    return NextResponse.redirect(new URL('/dashboard', request.url));
  }

  // 3. Header Context Extraction
  const response = NextResponse.next();
  const claims = decodeJWTPayload(token); // Decodes JWT signature at Edge
  
  response.headers.set('x-org-id', claims.org_id);
  response.headers.set('x-user-id', claims.sub);
  
  return response;
}
```

### Client-Side RBAC Gating
While the middleware manages page access, fine-grained UI authorization is handled in the React tree using helper guards:

*   **Wrapper Component Gating:** Hides UI elements based on user permissions.
    ```typescript
    // Usage in JSX
    <PermissionGuard permission="employee_salary:read">
      <SalaryDetailBlock data={employee.salary} />
    </PermissionGuard>
    ```
*   **Hook Gating:** Gates logic blocks based on user permissions.
    ```typescript
    // Usage in Custom Hook logic
    const { canViewSalary } = usePermissions();
    if (canViewSalary) { ... }
    ```

---

## 6. Navigation Flow

The diagrams below outline standard user navigation flows:

### Initial Authentication & Login Flow
```
[User lands on "/"]
       |
       v
[Middleware evaluates access token] --(No Token)--> [Redirect to "/login"]
       |                                                    |
       | (Token Valid)                                      v
       |                                            [User submits credentials]
       |                                                    |
       v                                                    v
[Redirect to "/dashboard"] <------------------- [API sets auth HTTP cookies]
```

### Expired Session Recovery Flow
```
[User triggers list update on "/employees"]
       |
       v
[Axios Client fires HTTP request]
       |
       v
[API responds with 401 Unauthorized token expired status]
       |
       v
[Axios Interceptor catches error, pauses requests queue]
       |
       v
[Axios Client requests Token Refresh "/auth/refresh"]
       |
       +------(Refresh Success)-----> [Update access cookies, retry queued requests]
       |
       +------(Refresh Failure)----> [Flush client stores, redirect to "/login"]
```

---

## 7. Breadcrumb Strategy

The breadcrumb path in the dashboard header displays the user's location in the application hierarchy.

```
Home  /  Employee Directory  /  Jane Doe  /  Salary Configurations
```

### Dynamic Path Parsing Flow

1.  **URL Extraction:** The breadcrumb component reads the current route path using `usePathname()` (e.g., `/employees/1592/salary`).
2.  **Segment Separation:** The path is split into individual tokens, filtering out empty entries: `['employees', '1592', 'salary']`.
3.  **Dynamic ID Detection:** The component parses each token:
    *   **Static segments:** Mapped to display names using a static lookup dictionary.
        *   `employees` -> `"Employee Directory"`
        *   `salary` -> `"Salary Configurations"`
    *   **Dynamic segments (numeric IDs):** The component displays a loader while fetching the display name. It checks the active query cache (e.g., TanStack Query cache for `employee_id: 1592`) to resolve the entity name (e.g., `"Jane Doe"`) and updates the breadcrumb display.
4.  **Clickable Link Construction:** Each breadcrumb item is converted into a link using its cumulative path alias (e.g., click on `Employee Directory` routes to `/employees`).

---

## 8. Summary of Routing & Layout Operations

| Route Segment | Layout Scope | Authentication Gating | Loading Presentation |
| :--- | :--- | :--- | :--- |
| `/login` | `(auth)/layout` | Redirects to `/dashboard` if JWT exists | Full card skeleton |
| `/dashboard` | `(dashboard)/layout` | Redirects to `/login` if JWT is missing | Dashboard widget grid shimmers |
| `/employees` | `(dashboard)/layout` -> `employees/layout` | Redirects to `/login` if JWT is missing | Data grid row shimmers |
| `/employees/[id]`| `(dashboard)/layout` -> `employees/layout` -> `[id]/layout` | Redirects to `/login` if JWT is missing | Profile card metadata shimmers |
| `/employees/[id]/salary` | `(dashboard)/layout` -> `employees/layout` -> `[id]/layout` | Gated by `employee_salary:read` permission | Tab area inline spinner |
| `/settings/rbac` | `(dashboard)/layout` -> `settings/layout` | Gated by `user:read` template configurations | Configuration form shimmers |
