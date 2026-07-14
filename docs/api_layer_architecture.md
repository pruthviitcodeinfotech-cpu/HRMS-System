# HRMS Enterprise Admin Web Application: API Layer Architecture

This document defines the network integration, data layer abstraction, and API communication strategies for the **Enterprise HR & Payroll Management System (HRMS) Admin Web Application**. It outlines how frontend calls interact with the FastAPI REST backend.

---

## 1. Network Core (Axios & Client Configurations)

Network requests are mediated by a single, pre-configured Axios client.

### Client Configuration (`src/lib/axios-client.ts`)
*   **Base URL:** Configured dynamically from type-safe environment variables (e.g. `process.env.NEXT_PUBLIC_API_URL/api/v1`).
*   **Timeout Threshold:** Configured to `30,000ms` (30 seconds) to allow for complex queries (e.g., payroll calculations, bulk report generation).
*   **Credentials Gating:** `withCredentials: true` is enabled globally, ensuring HttpOnly secure cookies are sent with every cross-origin request.

---

## 2. Axios Request & Response Interceptors

Interceptors act as hooks that process outgoing requests and incoming responses.

```
                      [ Client Request ]
                              |
                     (Request Interceptor)
                              v
                 - Injects Auth Bearer Token
                 - Appends "x-org-id" Header
                              |
                              v
                      [ Network Send ]
                              |
                              v
                      [ FastAPI Server ]
                              |
                              v
                     [ Network Receive ]
                              |
                    (Response Interceptor)
                              v
            +-----------------+-----------------+
            | Did Request Succeed (2xx)?        |
            +-----------------+-----------------+
                              |
            +-----------------+-----------------+
            | Yes                               | No
            v                                   v
  Extract data payload                Check status code:
  (returns raw JSON)                  - 401: Trigger Silent Refresh
                                      - 403: Show Gated Alert Toast
                                      - 422: Pass to Form Validator
                                      - 500: Show Global Error Banner
```

### 1. Request Interceptor
*   **JWT Injection:** Automatically reads the `access_token` cookie and injects it as a `Bearer` token inside the `Authorization` header.
*   **Tenancy Scoping:** Extracts the active `org_id` from client state and sets the `x-org-id` custom header, ensuring database queries are scoped to the correct tenant.

### 2. Response Interceptor (Success & Failure Handling)
*   **Success Unwrapping:** Extracts the standard API response envelope `{ data }` payload and returns it directly to caller hooks.
*   **Silent JWT Refresh (401 Response):** If an API call fails with a `401 Unauthorized` status and a `token_expired` error code, the interceptor:
    1. Pauses all subsequent outgoing network calls in a promise resolver queue.
    2. Makes a single `POST /auth/refresh` request to renew the access token.
    3. If the refresh succeeds, updates the client cookies and replays the queued requests.
    4. If the refresh fails, clears the client state and redirects the user to `/login`.

---

## 3. Global Error Handling Strategy

Errors are categorized and processed according to their HTTP status code:

| HTTP Status | Category | User Interface Presentation |
| :--- | :--- | :--- |
| **400 / 409** | Business Conflict (e.g., `EMPLOYEE_ALREADY_EXITED`) | Displays a contextual error message in a `Sonner` toast notification. |
| **401** | Unauthorized / Session Expiry | Initiates the silent refresh flow; redirects to `/login` if refresh fails. |
| **403** | Forbidden Gated Access | Displays a toast notification: *"Access Denied: Lacking permission."* |
| **422** | Request DTO Validation Fail | Maps backend error locations (e.g., `body.email`) to the corresponding form inputs in `react-hook-form`. |
| **500 / 503** | Server Crash | Displays a global crash banner with a *"Retry Connection"* button. |

---

## 4. API Directory & Layer Structure

The API layer is structured into three distinct layers to separate endpoints, queries, and type safety.

```
src/
  services/api-client/
    types.ts                   # Generated type interfaces (openapi-typescript)
  features/employees/
    services/
      employee-api.ts          # REST endpoints mapping Layer (Axios)
    hooks/
      use-employees-query.ts   # Server-State integration Layer (TanStack Query)
```

### Layer Roles

1.  **OpenAPI Schema Layer (`src/services/api-client/types.ts`):** Holds type definitions generated directly from the backend's OpenAPI spec, ensuring type alignment with backend models.
2.  **Service Integration Layer (`employee-api.ts`):** Defines the network request methods. This layer is responsible for mapping parameters, serializing payloads, and managing endpoints.
3.  **Server State Layer (`use-employees-query.ts`):** Integrates service calls with TanStack Query. It manages caching, cache invalidation, pagination, and data validation.

---

## 5. OpenAPI Type Integration Strategy

To keep frontend and backend models synchronized, API type definitions are generated automatically.

```
[ FastAPI Backend Codebase ]
            |
            v  (Auto-generates JSON Schema)
[ OpenAPI Document JSON (/api/v1/openapi.json) ]
            |
            v  (Command: openapi-typescript)
[ TypeScript Client Schemas (services/api-client/types.ts) ]
            |
            +---> [ Zod schemas parsing ]
            +---> [ TanStack Query responses ]
            +---> [ Form input properties ]
```

### Typings Generation Pipeline
*   **Generator Tool:** `@/services/api-client/types.ts` is generated using the `openapi-typescript` CLI tool.
*   **Integration:**
    ```bash
    npx openapi-typescript http://localhost:8000/api/v1/openapi.json --output src/services/api-client/types.ts
    ```
*   **Usage in Code:**
    ```typescript
    import { components } from '@/services/api-client/types';
    
    // Extracted schemas
    export type EmployeeDetail = components['schemas']['EmployeeDetailSchema'];
    export type EmployeeCreateRequest = components['schemas']['EmployeeCreateRequest'];
    ```

---

## 6. Query Parameters: Pagination, Filtering, and Sorting

List endpoints use a standardized query parameter structure to manage pagination, sorting, and filtering:

```
GET /api/v1/employees?page=2&page_size=50&sort_by=employee_name&sort_order=asc&branch_id=14&status=active
```

### Parameter Specifications

1.  **Pagination Strategy:**
    *   **Standard Parameters:** `page` (1-indexed) and `page_size` (defaults to `50` in lists, configurable up to `500` for reports).
    *   **Response Envelope:**
        ```json
        {
          "success": true,
          "message": "Employees fetched successfully",
          "data": [ ... ],
          "meta": {
            "page": 2,
            "page_size": 50,
            "total_records": 1024,
            "total_pages": 21
          }
        }
        ```
2.  **Filtering Strategy:**
    *   **Search Queries:** The `q` query string parameter handles basic fuzzy searches across columns (e.g. searching by name or email).
    *   **Explicit Filters:** Exact matches are passed as individual query strings (e.g. `branch_id=12`, `dept_id=5`, `status=active`).
3.  **Sorting Strategy:**
    *   **Parameters:** `sort_by` (defines the target column, e.g. `created_at`) and `sort_order` (`asc` or `desc`).
    *   **Integration with AG Grid:** Grid listeners (e.g. `onSortChanged` and `onFilterChanged`) map states directly to these query parameters. This triggers TanStack Query to update its cache and fetch the filtered data.

---

## 7. File Upload & Download Strategy

### 1. File Upload Strategy (Pre-signed URL Pattern)
To keep file upload traffic off the application servers, the application uses a pre-signed upload pattern:

```
[Client App] --(1. Requests Upload Permission)--> [FastAPI App]
     ^                                                  |
     |                                          (Generates S3 URL)
     |                                                  v
     +------------(2. Returns S3 Presigned URL)---------+
     |
[Uploads file directly to S3 via PUT request]
     |
     v
[S3 Bucket Storage]
     |
     v
[Client App] --(3. Submits File URL & Metadata)--> [FastAPI App]
     |                                                  |
     v                                                  v
[Upload Complete] <----------------------------- [Saves URL to DB]
```

#### Upload Process:
1.  **Permission Request:** The client sends file metadata to the backend: `POST /employees/{id}/documents/presign` (payload: `{ filename: "id_card.png", mime: "image/png" }`).
2.  **URL Resolution:** The backend generates a pre-signed S3 URL (or temporary local path) and returns it to the client.
3.  **Direct Upload:** The client performs a direct `PUT` request containing the raw file binary to the pre-signed URL.
4.  **Save Metadata:** Once the upload completes, the client submits the file URL and metadata to the database: `POST /employees/{id}/documents` (payload: `{ file_url: "s3://...", document_type: "aadhar_card" }`).

### 2. File Download Strategy (Large File Exports)
For exporting data (e.g. Excel payroll summaries or bulk attendance sheets), we use a dual download strategy based on file size:

*   **Small Files (Synchronous):** The client requests the file directly: `GET /payroll/export?format=xlsx`. The server compiles the data in memory and returns a binary stream with a `Content-Disposition: attachment` header, which the browser downloads automatically.
*   **Large Files (Asynchronous):**
    1. **Trigger Job:** The client starts the export: `POST /payroll/export/job` (returns a unique `{ job_id }`).
    2. **Job Processing:** The backend processes the export task in a background Redis queue.
    3. **Polling:** The client polls the job status: `GET /payroll/export/job/{job_id}`.
    4. **Download:** Once the job status changes to `completed`, the client receives the file URL and downloads the file using a temporary helper link.
