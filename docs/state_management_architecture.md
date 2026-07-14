# HRMS Enterprise Admin Web Application: State Management Architecture

This document defines the state management strategy for the **Enterprise HR & Payroll Management System (HRMS) Admin Web Application**. It establishes a clear boundary between server-derived state and client-side UI configurations, using TanStack Query and Zustand.

---

## 1. State Separation Boundary

To prevent data synchronization conflicts, the application enforces a strict separation of state:

```
                           [ State Category ]
                          /                  \
                         /                    \
             [ Server-Side State ]         [ Client-Side State ]
             - Originated from DB          - Transient UI configuration
             - Needs fetching/caching      - Independent of database
             - Shared across clients       - Unique to local browser
                     |                              |
                     v                              v
             [ TanStack Query ]                 [ Zustand ]
```

### Comparative Analysis Matrix

| Property | Server State (TanStack Query) | Client State (Zustand) |
| :--- | :--- | :--- |
| **Primary Tool** | TanStack Query (React Query) v5 | Zustand (with persistent middleware) |
| **Data Origin** | Database via FastAPI REST endpoints | Local browser runtime storage |
| **Primary Role** | Caching, synchronizing, and invalidating server-derived data. | Managing UI layouts, active settings, and theme states. |
| **Example Content** | Employee records, payroll calculation inputs, weekly shift lists. | Sidebar collapse, active dark mode, selected active branch. |
| **Caching Model** | Query key cache with custom stale and garbage collection times. | In-memory store; optional persistence to LocalStorage. |
| **Mutation Sync** | Auto-invalidation of lists on mutation success. | Direct state mutations via Zustand setter methods. |

---

## 2. Server State: TanStack Query

Server state is managed through TanStack Query, which handles request caching, background synchronization, and cache invalidation.

```
            [ Fetching / List Queries ]
                         |
                         v
     [ Query Key Factory: employeeKeys.list(filters) ]
                         |
                         v
       [ TanStack Query Cache Validation ]
        - Stale (staleTime elapsed)?
          * Yes: Fetch background data
          * No: Return cached data immediately
```

### 1. Query Key Factory Strategy
To keep cache invalidation predictable, query keys are managed centrally using a factory object per feature:

```typescript
// Conceptual structure of a Query Key Factory
export const employeeKeys = {
  all: ['employees'] as const,
  lists: () => [...employeeKeys.all, 'list'] as const,
  list: (filters: Record<string, any>) => [...employeeKeys.lists(), filters] as const,
  details: () => [...employeeKeys.all, 'detail'] as const,
  detail: (id: number) => [...employeeKeys.details(), id] as const,
};
```

### 2. Cache Strategy Configurations
*   **staleTime:** Configured globally to `5 minutes` (`300,000ms`) for static records. Critical tables (e.g. attendance locks) use a `staleTime` of `0` to force immediate validation.
*   **gcTime (Garbage Collection):** Configured globally to `30 minutes` (`1,800,000ms`). After this time, inactive query data is removed from memory.
*   **refetchOnWindowFocus:** Enabled only for operational dashboards (e.g., live biometric device connectivity status). Disabled globally for standard list pages to prevent redundant network requests.

### 3. Mutation Strategy & Invalidation
Mutations invalidate matching query list keys to ensure the interface reflects updates:

```typescript
// Invalidation flow inside a Custom Mutation hook
const queryClient = useQueryClient();

// On Mutation Success:
queryClient.invalidateQueries({ queryKey: employeeKeys.lists() });
queryClient.invalidateQueries({ queryKey: employeeKeys.detail(employeeId) });
```

### 4. Optimistic Updates
For actions requiring immediate feedback (e.g., approving an attendance correction or toggling door lock permissions), the application uses optimistic updates:
1.  **On Start:** Pauses outgoing queries for the query key, saves a snapshot of the current cache, and updates the cache values directly.
2.  **On Error:** Rolls back the cache to the saved snapshot.
3.  **On Settlement:** Refetches the data to ensure the client state matches the server state.

### 5. Pagination & Infinite Queries
*   **Standard List Pagination:** Handled by passing dynamic pagination states (`page`, `page_size`) to standard Query hooks, caching lists by page index.
*   **Infinite Scroll Queries (`useInfiniteQuery`):** Used for append-only logs (e.g. Activity Logs, Punch Records). The query fetches pages using a cursor-based format, binding new entries to the bottom of the list.

### 6. Background Refetching & Polling
Operational dashboard widgets (such as active biometric streams or pending approval counters) use the `refetchInterval` parameter to fetch updates in the background at regular intervals (e.g., every 30 seconds).

---

## 3. Client State: Zustand Stores

Zustand stores manage local, transient client state.

```
                      [ Zustand Stores ]
           /                 |                 \
          /                  |                  \
  [ UI & Layout Store ]  [ Context Store ]  [ Session Store ]
  - Sidebar collapse     - Active org       - Login state
  - Dark/Light theme     - Active branch    - Active JWT sid
```

### 1. Global UI & Theme Store (`useUiStore`)
*   **Responsibility:** Manages the dashboard shell's layout and rendering states.
*   **Properties:**
    *   `sidebarCollapsed` (boolean): Sidebar expansion state.
    *   `theme` (`'light' | 'dark' | 'system'`): Global theme configurations.
    *   `activeModal` (string | null): Tracks active modal identifiers to prevent rendering conflicts.

### 2. Context Store (`useContextStore`)
*   **Responsibility:** Manages active scoping parameters for multi-tenant data isolation.
*   **Properties:**
    *   `activeOrgId` (number): Scopes API calls to the selected organization.
    *   `activeBranchId` (number | null): Scopes directory searches to the selected branch.
    *   `activeDeptId` (number | null): Scopes directory searches to the selected department.

### 3. Session Store (`useSessionStore`)
*   **Responsibility:** Manages user session state and authentication status.
*   **Properties:**
    *   `isAuthenticated` (boolean): Quick check for middleware routing decisions.
    *   `user` (UserSnapshot | null): Active user metadata (name, email, avatar).
    *   `permissions` (EffectivePermissions | null): User permissions evaluated at login.

---

## 4. Zustand Persistence & Hydration

To prevent hydration mismatch bugs in Next.js Server-Side Rendering (SSR), stores that use persistent middleware must verify hydration before rendering client-specific data:

```typescript
// Conceptual structure of a Next.js safe store hydration hook
export function useHydratedStore<T>(
  useStore: (selector: (state: any) => T) => T,
  selector: (state: any) => T
): T | null {
  const [hydrated, setHydrated] = useState(false);
  const data = useStore(selector);

  useEffect(() => {
    setHydrated(true);
  }, []);

  return hydrated ? data : null;
}
```

### Storage Assignments
1.  **LocalStorage Integration:** Used for the Theme and User Preferences stores, preserving UI choices across browser sessions.
2.  **SessionStorage Integration:** Used for the Context store, resetting tenant filters when the browser tab is closed.
3.  **In-Memory Storage:** Used for the Session store to protect active session details, delegating security to HttpOnly cookies.
