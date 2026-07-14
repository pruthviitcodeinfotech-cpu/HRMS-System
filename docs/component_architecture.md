# HRMS Enterprise Admin Web Application: Component Architecture

This document defines the component categorization, naming rules, state containment, and composition strategy for the **Enterprise HR & Payroll Management System (HRMS) Admin Web Application**. It outlines how components are structured using React, Tailwind CSS, Radix UI, and AG Grid.

---

## 1. Atomic Component Strategy

To maintain UI consistency and support future scaling, the application uses an **Atomic Design Strategy**:

```
 [ Atoms ]       -->   [ Molecules ]     -->   [ Organisms ]      -->   [ Layouts ]
 Primitive UI          Composite UI            Feature Components         Structure
 (Button, Input)       (FormField, Card)       (EmployeeGrid)             (Sidebar, Shell)
```

### Component Classifications

1.  **Atoms (UI Primitives):** Stateless, single-purpose components (e.g., `Button`, `Input`, `Badge`, `Checkbox`). These are built using Radix UI primitives and styled with Tailwind CSS.
2.  **Molecules (Composite Controls):** Small, reusable combinations of atoms (e.g., a `FormField` component that binds an `Input`, a `Label`, and an `ErrorMessage` together, or a `MetricCard` widget).
3.  **Organisms (Feature Components):** Complex, context-aware layout blocks (e.g., `EmployeeDirectoryTable`, `ShiftSchedulerGrid`, `PayrollRunSummary`). These components are tied to a specific domain features, query APIs, and handle state changes.
4.  **Layouts (Structural Shells):** Base wrappers that define the page structure (e.g., `DashboardShell`, `ModulePageLayout`, `RecordDetailTabs`).

---

## 2. Component Directory Structure

Components are divided into two main categories: shared UI primitives and feature-specific components.

```
src/
  components/                  # Shared Components (Agnostic Design System)
    ui/                        # Atoms: Shadcn/Radix-based primitives
      button.tsx
      input.tsx
      dialog.tsx
      drawer.tsx
    data-display/              # Molecules: Visual containers
      data-grid.tsx            # AG Grid Community generic wrapper
      chart-wrapper.tsx        # Recharts generic card wrapper
    feedback/                  # Molecules: Alerts and indicators
      skeleton-loader.tsx
      confirm-dialog.tsx
  features/                    # Feature Components (Feature-Specific Organisms)
    employees/
      components/
        EmployeeTable.tsx      # Binds generic data-grid.tsx with Employee DTOs
        EmployeeForm.tsx       # Binds react-hook-form with Zod schemas
```

---

## 3. Core Component Strategies

### 1. Form Components (`react-hook-form` & Zod)
Forms are decoupled from page states and follow a standardized integration pattern:
*   **Separation of Concerns:** Forms are wrapped in a generic container component. The form itself handles validation and user inputs, while submit events are delegated to a parent component using callback props (e.g., `onSubmit`).
*   **Validation Integration:** Zod schemas validate inputs dynamically on the client side before they are submitted.
*   **Error Management:** Field-level validation messages are displayed directly within the corresponding `FormField` component, while server-side errors are displayed in a global form error banner.

### 2. Table Components (AG Grid Community Wrapper)
AG Grid Community is the primary data presentation tool for lists:
*   **Centralized Wrapper (`src/components/data-display/data-grid.tsx`):** Implements a standardized AG Grid wrapper that handles sorting, filtering, loading overlays, empty states, and theme changes.
*   **Feature Integration:** Feature components (e.g., `EmployeeTable.tsx`) configure the columns, cell renderers, and pagination options for the generic wrapper.
*   **Rendering Optimization:** Custom cell renderers are kept lightweight to prevent performance degradation when displaying large datasets.

### 3. Modals, Dialogs, and Drawers (Overlays)
Overlays are selected based on the complexity of the task they contain:

```
                      [ User Triggers Overlay ]
                                  |
            +---------------------+---------------------+
            | Is the form/content complex or simple?    |
            +---------------------+---------------------+
                                  |
            +---------------------+---------------------+
            | Simple (e.g., Confirmations, Quick Inputs)| Complex (e.g., Employee Hiring Wizard)
            v                                           v
    [ Dialog / Modal ]                              [ Drawer / Slide-Out ]
    - Centered popup                                - Right-aligned panel
    - High focus, low content                       - Full-height sidebar
    - Built via Radix Dialog                        - Built via Radix Dialog Sheet
```

*   **State Management:** The open/closed state of major overlays is managed through URL query parameters (e.g., `?drawer=create-employee`) or lightweight Zustand store state flags. This allows overlays to be lazy-loaded dynamically (`next/dynamic`), reducing initial bundle sizes.

---

## 4. Component Coding & Props Standards

### Naming Conventions
*   **Files & Folders:** Components use PascalCase (e.g., `EmployeeTable.tsx`).
*   **Sub-components:** Auxiliary sub-components are nested in subfolders named after the parent component (e.g., `EmployeeProfile/PersonalTab.tsx`).

### Props Standards
To maintain type safety, all components use typed props definitions:
1.  **Explicit Interfaces:** Every component defines a props interface named `<ComponentName>Props`.
2.  **HTML Element Extension:** Atomic primitives extend standard HTML elements to support standard attributes (e.g., `aria-` attributes):
    ```typescript
    export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
      label?: string;
      error?: string;
    }
    ```
3.  **Primitive Props Priority:** Prefer passing primitive types (e.g., `string`, `number`) over complex objects where possible. When passing domain entities, use the generated OpenAPI types (e.g., `EmployeeSummary`).

---

## 5. Composition Strategy

To avoid prop-drilling and build highly reusable interfaces, the application prioritizes component composition:

### 1. Children Injection (`React.ReactNode`)
Layouts and panels use the `children` prop to inject sub-components dynamically, allowing them to remain agnostic to the contents they display:

```typescript
// Conceptual layout composition pattern in TSX
interface DashboardShellProps {
  sidebar: React.ReactNode;
  header: React.ReactNode;
  children: React.ReactNode;
}

export function DashboardShell({ sidebar, header, children }: DashboardShellProps) {
  return (
    <div className="flex h-screen overflow-hidden">
      <aside className="w-64">{sidebar}</aside>
      <div className="flex flex-col flex-1">
        <header className="h-16">{header}</header>
        <main className="flex-1 overflow-y-auto">{children}</main>
      </div>
    </div>
  );
}
```

### 2. Compound Components
Complex components (e.g., dropdown menus, tabs, cards) use the compound component pattern. This exposes inner components through a parent namespace, making the DOM structure configurable while keeping state management encapsulated:

```typescript
// Conceptual usage pattern for Compound Components in Views
<Card>
  <Card.Header>
    <Card.Title>Employee Profile</Card.Title>
  </Card.Header>
  <Card.Content>
    <p>Demographic information summary.</p>
  </Card.Content>
</Card>
```
