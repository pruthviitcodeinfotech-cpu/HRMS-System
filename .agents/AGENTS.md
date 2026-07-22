# Project Rules & Customizations

## 🌟 GOLDEN RULE: One Business Entity = One Implementation

> **One business entity = One implementation.**
> Every master entity (Department, Designation, Branch, Employee, Shift, Leave Type, Holiday, Role, Payroll Component, etc.) MUST have **exactly one source of truth** in the entire HRMS.
> Every screen, report, modal, filter, dashboard, API, export, and form MUST reuse that implementation.
> **Duplicate implementations are strictly prohibited.**

## Master Data & Dropdown Reuse Guidelines

Before implementing any report, feature, filter, modal, or form in the HRMS project, inspect existing HRMS modules and reuse their master data instead of creating new APIs, mock data, duplicate services, or duplicate database queries.

### Mandatory Pre-Implementation Search Protocol
Before writing or generating code for any feature, ALWAYS perform these 9 search checks:
1. Search the project for an existing **Module**.
2. Search for an existing **API Endpoint**.
3. Search for an existing **React Query Hook**.
4. Search for an existing **Service Layer Method**.
5. Search for an existing **TypeScript Interface / Type**.
6. Search for an existing **Pydantic Schema**.
7. Search for an existing **SQLAlchemy Model**.
8. Search for an existing **Repository Method**.
9. Search for an existing **DTO**.

**Rule**: If any matching component already exists, **REUSE IT**. Do NOT create duplicate implementations.

### Dropdown & Master Data Rules
1. **Department Dropdown**: Reuse the existing Department module (`useDepartments` from `@/features/employees/hooks`). Fetch departments using existing APIs. Show ONLY real departments from database.
2. **Designation Dropdown**: Reuse the existing Designation module (`useDesignations` from `@/features/employees/hooks`). Fetch designations using existing APIs. Show ONLY real designations from database.
3. **Branch Dropdown**: Reuse the existing Branch lookup API from Employee/Branch module.
4. **Shift Dropdown**: Reuse the existing Shift module from Shift Management.
5. **Employee Dropdown / Search**: Reuse the existing Employee module. Display only active employees (`employment_status = active`).
6. **Leave Type Dropdown**: Reuse the Leave Management module. Show only configured leave types.
7. **Holiday Data**: Reuse the Holiday Management module. Never hardcode holiday names or dates.
8. **General Master Data**: Always reuse existing master data lookup endpoints and services across the application to maintain a single source of truth.

### Master Data Module Mapping Matrix
- **Department** $\rightarrow$ Employee Module
- **Designation** $\rightarrow$ Employee Module
- **Branch** $\rightarrow$ Employee Module
- **Shift** $\rightarrow$ Shift Module
- **Employee** $\rightarrow$ Employee Module
- **Leave Type** $\rightarrow$ Leave Module
- **Holiday** $\rightarrow$ Holiday Module
- **Role** $\rightarrow$ Authentication / RBAC Module
- **Approval Level** $\rightarrow$ Approval Module
- **Payroll Component** $\rightarrow$ Payroll Module
- **Settlement Reason** $\rightarrow$ Settlement Module
- **Notification Template** $\rightarrow$ Notification Module
- **Biometric Device** $\rightarrow$ Hardware Module

### Anti-Patterns to Avoid
- ❌ Do NOT create duplicate lookup APIs or endpoints.
- ❌ Do NOT create duplicate React Query hooks.
- ❌ Do NOT create duplicate services.
- ❌ Do NOT create duplicate DTOs or schemas.
- ❌ Do NOT create duplicate interfaces or types.
- ❌ Do NOT create duplicate database queries.
- ❌ Do NOT create duplicate SQL views.
- ❌ Do NOT create duplicate models or tables.
- ❌ Do NOT create duplicate enums.
- ❌ Do NOT create mock dropdown values or hardcoded option arrays.
- ❌ Do NOT create new lookup tables if an existing table/module already exists.
