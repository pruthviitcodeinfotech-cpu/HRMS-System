# HRMS Enterprise Admin Web Application: Forms & Error Handling Architecture

This document defines the validation, form state containment, API error parsing, and error reporting strategies for the **Enterprise HR & Payroll Management System (HRMS) Admin Web Application**.

---

## 1. Form Validation Strategy (React Hook Form & Zod)

The application uses **React Hook Form** to manage form state and **Zod** to handle schema validation.

```
 [ Form Input Change ]  -->  [ React Hook Form Control ]
                                       |
                                       v  (Triggers Resolver on Blur/Submit)
                            [ Zod Schema Validation ]
                                       |
                     +-----------------+-----------------+
                     | Is input structure valid?         |
                     +-----------------+-----------------+
                                       |
             +-------------------------+-------------------------+
             | Yes                                               | No
             v                                                   v
   Allow Submit event                                  Block submit, map errors
   (Calls backend API)                                 to FormField inputs
```

### 1. Schema Co-location
Zod validation schemas are defined within the types directory of their respective feature modules (e.g. `src/features/employees/types/schemas.ts`).

### 2. Validation Message Dictionary
To keep user feedback consistent, validation messages are managed in a central dictionary:

```typescript
// Conceptual structure of centralized validation messages
export const VALIDATION_MESSAGES = {
  required: (field: string) => `${field} is required.`,
  minLength: (field: string, count: number) => `${field} must be at least ${count} characters.`,
  maxLength: (field: string, count: number) => `${field} cannot exceed ${count} characters.`,
  invalidFormat: (field: string) => `Invalid ${field} format.`,
  dateOrder: (startField: string, endField: string) => `${endField} must be after or equal to ${startField}.`,
};
```

### 3. Type Inference
TypeScript interfaces for form inputs are derived directly from the Zod schemas:

```typescript
import { z } from 'zod';

export const employeeCreateSchema = z.object({
  employee_name: z.string().min(2, VALIDATION_MESSAGES.minLength('Name', 2)),
  email: z.string().email(VALIDATION_MESSAGES.invalidFormat('Email')),
});

// Inferred TypeScript Type
export type EmployeeCreateInput = z.infer<typeof employeeCreateSchema>;
```

---

## 2. Form Reusability Patterns

To avoid duplicate code, forms support both Create and Edit operations using a unified component design:

### 1. Unified Form Pattern
The form component accepts default values and a submission handler as props:

```typescript
interface EmployeeFormProps {
  defaultValues?: Partial<EmployeeCreateInput>;
  onSubmit: (data: EmployeeCreateInput) => Promise<void>;
  isSubmitting: boolean;
  isEdit?: boolean;
}
```

*   **Create Mode:** The parent page renders the form without initial values. The form uses default placeholder values and enables all inputs.
*   **Edit Mode:** The parent page fetches the record details and passes them as `defaultValues`. Read-only or immutable fields (such as the auto-generated `employee_code`) are disabled based on the `isEdit` flag.

### 2. Multi-Step Wizard Forms (e.g. Employee Onboarding)
For complex, multi-step forms:
1.  **Form Segmentation:** Each step is implemented as an independent form component with its own local Zod sub-schema validation.
2.  **State Management:** Completed step data is saved to a temporary Zustand wizard store.
3.  **Submission:** The final step collects the data from the store, validates the complete schema, and submits it to the API.

---

## 3. Client vs. Server Validation

Validation is enforced in two stages to prevent invalid requests:

```
[ User Action ] -> [ Client Gate: Zod Schema ] -> [ Server Gate: FastAPI DTO ] -> [ Database Constraints ]
```

### 1. Client-Side Validation
*   **Trigger:** Validates inputs on form submit or when focus leaves the input field (`mode: "onBlur"`).
*   **Execution:** Zod resolver validates fields against the schema. If validation fails, submit operations are blocked, and input errors are displayed immediately.

### 2. Server-Side Validation (FastAPI 422 Errors)
*   **Trigger:** Triggered when request payloads fail backend validation.
*   **Handling:** The response interceptor catches the `422 Unprocessable Entity` status code and maps the backend errors back to the form:

```typescript
// Backend Error Format (FastAPI ValidationError)
// { "detail": [{ "loc": ["body", "email"], "msg": "value is not a valid email" }] }

// Interceptor Maps Locations to Form Fields:
setError('email', { type: 'server', message: error.msg });
```

---

## 4. API Error Handling & Global Boundaries

### 1. API Response Error Envelope
All error responses from the backend follow a standardized envelope:

```json
{
  "success": false,
  "message": "Validation failed",
  "error": {
    "code": "duplicate_employee_code",
    "message": "The employee code EMP00021 has already been allocated.",
    "details": {
      "field": "employee_code",
      "value": "EMP00021"
    }
  },
  "meta": {}
}
```

### 2. Error Boundaries (`error.tsx`)
*   **Root Error Boundary:** Catches unexpected app-wide crashes, rendering a full-page error layout with a reload button.
*   **Layout Error Boundary:** Nested within the dashboard shell. If a dashboard component fails, the boundary displays an inline crash panel, allowing the user to navigate using the sidebar without refreshing the entire page.

---

## 5. Toast Notification Strategy (Sonner)

Toasts are used to provide immediate feedback on operations. The application uses different toast types based on the event:

*   **Success (Green Indicator):** Used for non-destructive operations (e.g., *"Shift assigned successfully"*). Toast automatically dismisses after 3 seconds.
*   **Alert (Amber Indicator):** Used for non-critical warnings (e.g., *"Biometric device connection timed out, retrying..."*). Toast automatically dismisses after 5 seconds.
*   **Error (Red Indicator):** Used for critical errors (e.g., *"Failed to finalize payroll cycle: server error"*). Includes a close button and remains visible until manually dismissed.

---

## 6. Request Retry Strategy (TanStack Query)

To avoid duplicate transactions, retries are configured based on the request type:

*   **Read Queries (GET):** Retries failed requests up to `2 times` automatically if the failure is caused by a network drop. Auth-specific calls (such as login requests) do not retry.
*   **Write Mutations (POST, PUT, DELETE):** Retries are disabled (`retry: false`) globally for modifying operations. This prevents duplicate submissions (e.g. submitting a payroll authorization request twice due to a network interruption).

---

## 7. Logging & Telemetry Strategy

The application logs events based on the environment to assist with debugging and error tracking:

*   **Development Mode:** Detailed console logs show request paylods, response times, and state transitions.
*   **Production Mode:** Console logs are disabled. Errors are processed by a logging service (such as Sentry):
    *   **Context:** Logged errors include the user ID, active organization ID, and error code, omitting personal data.
    *   **Level Gating:** Only warnings, critical API failures, and unhandled JS exceptions are reported.
