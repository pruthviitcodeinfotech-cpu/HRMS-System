# HRMS Enterprise Admin Web Application: Development Standards

This document establishes the official development standards, code style rules, version control strategies, and deployment guidelines for the **Enterprise HR & Payroll Management System (HRMS) Admin Web Application**.

---

## 1. Environment & Configuration Management

### 1. Environment Variables Configuration
To prevent runtime configuration errors, the application uses a dual environment approach:
*   **Variable Scopes:** All browser-accessible variables must be prefixed with `NEXT_PUBLIC_` (e.g. `NEXT_PUBLIC_API_URL`). Server-only variables (e.g., build hooks or private keys) must not use this prefix.
*   **Default Files:**
    *   `.env.example` — Template containing all required variable keys (must be kept updated).
    *   `.env.local` — Local override file for development (ignored by Git).
    *   `.env.production` — Production configuration presets.

### 2. Type-Safe Environment Verification (`src/config/env.ts`)
We parse and validate environment variables at startup using a Zod schema to ensure configuration errors cause a fast crash instead of silent failures:

```typescript
import { z } from 'zod';

const envSchema = z.object({
  NEXT_PUBLIC_API_URL: z.string().url(),
  NEXT_PUBLIC_APP_ENV: z.enum(['development', 'staging', 'production']),
  NEXT_PUBLIC_API_TIMEOUT: z.coerce.number().default(30000),
});

// Throws detailed validation errors on startup if variables are missing
export const env = envSchema.parse({
  NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL,
  NEXT_PUBLIC_APP_ENV: process.env.NEXT_PUBLIC_APP_ENV,
  NEXT_PUBLIC_API_TIMEOUT: process.env.NEXT_PUBLIC_API_TIMEOUT,
});
```

---

## 2. Coding Standards & TypeScript Best Practices

### 1. TypeScript Rules
*   **Strict Mode:** Enforce strict type checking in `tsconfig.json`.
*   **No Explicit `any`:** The use of `any` is forbidden. If a type is unknown, use `unknown` and perform type assertions.
*   **Return Type Annotation:** All exported functions, hooks, and services must explicitly define their return types.

### 2. React Best Practices
*   **Functional Components:** Enforce the use of functional components using hook-based state management.
*   **State Localization:** Keep state as local as possible. Do not lift state up or write to Zustand unless the state is shared across multiple pages or layouts.
*   **Memoization:** Limit the use of `useMemo` and `useCallback`. Use them only when passing complex object props to heavy third-party components (such as AG Grid or Recharts).

---

## 3. Naming Conventions

Consistency in naming ensures a clean and searchable codebase:

| Context | Casing Rules | Example |
| :--- | :--- | :--- |
| **Folders** | Kebab-case | `/shift-scheduler`, `/employee-profile` |
| **Component Files** | PascalCase | `EmployeeTable.tsx`, `Sidebar.tsx` |
| **Component Names** | PascalCase (matching file names) | `export function EmployeeTable() { ... }` |
| **Hooks Files & Functions**| camelCase (prefixed with `use`) | `useEmployeeQuery.ts`, `useAuth` |
| **API / Services** | camelCase (suffixed with `Api`) | `employeeApi.ts`, `shiftApi.ts` |
| **Pure Utilities / Helpers**| camelCase | `formatCurrency.ts`, `date.ts` |
| **Zod Schemas** | camelCase (suffixed with `Schema`) | `employeeCreateSchema.ts` |

---

## 4. Git Branching & Commit Message Strategy

### 1. Git Branching Model
The project uses a feature branch development flow:
*   **Main Branches:**
    *   `main` — Represents stable production code.
    *   `develop` — Integration branch for feature development.
*   **Supporting Branches:**
    *   `feature/<module>-<description>` (e.g. `feature/shifts-weekly-scheduler`).
    *   `bugfix/<module>-<bug-desc>` (e.g. `bugfix/payroll-refresh-loop`).
    *   `hotfix/<issue-desc>` (e.g. `hotfix/login-expired-cookies`).

### 2. Commit Message Rules (Semantic Commits)
Commit messages must follow the Angular Commit Message Format:

```
<type>(<scope>): <short summary description>
```

#### Allowed Commit Types:
*   `feat`: A new feature (e.g. `feat(employee): add status history timeline`).
*   `fix`: A bug fix (e.g. `fix(auth): correct token expired redirect loop`).
*   `docs`: Documentation changes.
*   `style`: Code style changes (formatting, missing semi-colons, no logic changes).
*   `refactor`: Code changes that neither fix a bug nor add a feature.
*   `test`: Adding missing tests or correcting existing tests.
*   `chore`: Tooling, dependency, or build pipeline updates.

---

## 5. Linting, Formatting, & Git Hooks Automations

### 1. Code Quality Automations (Husky & lint-staged)
We use Husky and lint-staged to run code quality checks automatically on every Git commit:

```
[ Developer runs: git commit ]
               |
               v (Triggers Husky pre-commit hook)
     [ Run lint-staged checks ]
               |
               +---> 1. Run Prettier (Formats modified files)
               +---> 2. Run ESLint (Fixes code styling rules)
               +---> 3. Run Vitest (Validates affected unit tests)
               |
               v (If checks pass)
[ Commit is created successfully ]
```

### 2. Primary ESLint Configurations
*   **Dependency Verification:** Enforce `react-hooks/exhaustive-deps` as an error.
*   **Clean Imports:** Disallow direct cross-feature imports, forcing developers to use the feature's public barrel file.
*   **Unused Imports:** Automatically remove unused variables and imports.

### 3. Prettier Formatting Rules
*   **Quote Style:** Double quotes (`singleQuote: false`).
*   **Statement Closures:** Enforce semicolons (`semi: true`).
*   **Indentation Scale:** 2 spaces.
*   **Trailing Commas:** Enforce trailing commas where valid in ES5 (objects, arrays).

---

## 6. Build & Deployment Strategies

### 1. Standard package.json Scripts
*   `npm run dev` — Starts the Next.js development server with hot-reload support.
*   `npm run build` — Compiles the application, runs TypeScript checks, and builds production chunks.
*   `npm run start` — Starts the built production server.
*   `npm run lint` — Runs ESLint checks across the project.
*   `npm run format` — Formats all source files using Prettier.
*   `npm run test` — Runs the test suite using Vitest.
*   `npm run test:coverage` — Generates test coverage reports.

### 2. Next.js Production Build Strategy
*   **Static Optimization:** Pages that do not use dynamic headers or parameters are pre-rendered as static HTML files during build time.
*   **Bundle Audits:** The build pipeline includes `@next/bundle-analyzer` to analyze JS bundle sizes, identifying and warning developers of heavy dependencies.

### 3. Containerized Deployment (Multi-Stage Dockerfile)
The application is deployed using a multi-stage Docker build to keep production container images lightweight:
1.  **Stage 1 (Install Dependencies):** Installs all package dependencies.
2.  **Stage 2 (Build Source):** Copies the source code and compiles the production build, running TypeScript checks.
3.  **Stage 3 (Production Runner):** Extracts only the compiled `.next/standalone` directory and static assets, discarding build tools and intermediate source code.
