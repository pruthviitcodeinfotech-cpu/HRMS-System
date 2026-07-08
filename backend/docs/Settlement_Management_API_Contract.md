# Settlement Management API Contract (Loans, Advances & Arrears)

> Module: `app/modules/settlements`
> API Version: `v1` — all routes under `API_V1_PREFIX` (`/api/v1`).
> Status: **Contract only** (no FastAPI/SQLAlchemy/Pydantic/service/repository code).
> Sources of truth: `docs/architecture.md` (Backend Architecture), migration `0006_settlements`
> (+ `0008`, `0016`), the settlements model (`settlements/models.py`), `settlements/constants.py`, and the
> approved Authentication, RBAC, Employee, and Payroll API Contracts.

> **IMPORTANT — scope reconciliation (per approved decision).** The Settlement module's schema is a
> **loan/advance + arrears ledger** system, **not** a Full & Final (F&F) settlement system. This contract is
> therefore written for what the schema supports: **Loans & Advances**, **Arrears**, their **transaction
> ledgers**, a combined **settlement statement/history**, and a **summary**. The requested **Full & Final
> Settlement**, **Settlement Components**, **Settlement Calculations**, and **Settlement Approvals** have
> **no backing tables** and are **not** contracted here (see §11). Cross-module tables (employees, payroll,
> users) are referenced/read only.

**Excludes** Authentication, RBAC, Employee, Shift, Attendance, Leave, Approval, Payroll, Notifications,
Settings, Hardware, Dashboard, Reports.

---

## 1. Module Overview

### Purpose
Manage employee **loans & advances** (header + credit/debit ledger, with installment/outstanding tracking)
and **arrears** (header + credit/debit ledger), and expose a combined settlement statement/history/summary.

### Responsibilities
- Loans & Advances: create, read, update, close; ledger transactions (`employee_loans_advances`,
  `loan_advance_transactions`).
- Arrears: read/list header (one per employee); ledger transactions (`employee_arrears`,
  `arrears_transactions`).
- Combined employee settlement statement/history and outstanding summary.

### Dependencies
| Dependency | Location / Module | Used for |
|---|---|---|
| Auth/permission deps | `core/dependencies/auth.py` | `current_user`, `current_org`, `require_permission` |
| Tenant middleware | `core/middleware/tenant.py` | `org_id` scoping |
| RBAC data scope | `rbac` | branch/department access on employee-related reads |
| Employee (service) | `employee` | validate `employee_id` |
| Payroll | `payroll` | `source='payroll'` ledger entries (`payroll_run_id`) posted by payroll finalization — **read/deferred** |
| Storage | `infrastructure/storage/` | settlement-statement PDF rendering/download |
| Response/pagination schemas | `shared/schemas/` | envelope + paginated lists |
| Activity Log (audit) | `audit` | settlement audit history (§9) |

**Tables owned:** `employee_loans_advances`, `loan_advance_transactions`, `employee_arrears`,
`arrears_transactions`. **Not implemented:** `settlement_logs_view` (a UNION-over-ledgers view whose SQL the
architecture leaves undefined — the combined statement is computed in the service instead, §8).

### Module boundaries
- Owns the ledger data. Intra-module FKs (`loan_advance_id`, `employee_arrears_id`) are enforced with
  **ON DELETE RESTRICT**. `employee_id`/`org_id`/actor/`payroll_run_id` are deferred reference columns.
- `source='payroll'` transactions originate from the Payroll module's run finalization; this contract does
  not duplicate payroll processing.

---

## 2. Authorization Model

Two-layer RBAC: feature permission (CRUD on `feature_key`) × data scope (branch/department access on
`employee_id`). Super admins bypass feature checks; tenant isolation (`org_id`) always applies. All endpoints
require `Authorization: Bearer <access_token>`.

**Proposed feature keys** (register in `core/security/permissions.py` — §11 Q4): `loan_advance`, `arrears`,
and `settlement` (read-only combined statement/history/summary). Employee-related reads are additionally
branch/department data-scoped. Self-service (own loans/arrears/statement) may be permitted (§11 Q5).

---

## 3. Request & Response Standards

Reuses the shared envelope + pagination (`data`/`error`/`meta.request_id`; `data.items`+`page`+`page_size`+
`total`). BIGINT integer IDs; money as decimals per `Numeric(12,2)`; dates `YYYY-MM-DD`; timezone-aware
timestamps; empty lists → `items: []`.

### Pagination / Filtering / Sorting
`page` (≥1, default 1), `page_size` (bounded). Filter/sort allowlists per endpoint; invalid field → `422`.
Repository applies `org_id` + data scope before optional filters.

**Enumerations (DB CHECK):** `employee_loans_advances.type` ∈ `loan, advance`; `...status` ∈ `active, closed`;
`loan_advance_transactions.transaction_type`/`arrears_transactions.transaction_type` ∈ `credit, debit`;
`loan_advance_transactions.type_label` ∈ `loan, advance`; `...source` ∈ `manual, payroll`.

Common omitted errors (all protected endpoints): `401 AUTH_NOT_AUTHENTICATED`, `403 AUTH_FORBIDDEN`,
`422 VALIDATION_ERROR`.

---

## 4. Loans & Advances (`/api/v1/loans-advances`) — feature key `loan_advance`

`employee_loans_advances` fields: `employee_id`, `name` (≤50), `type` (CHECK `loan|advance`, default `loan`),
`principal_amount` (**>0**), `monthly_installment` (**>0**), `total_debit` (**≥0**, default 0),
`outstanding_amount` (**≥0**), `transaction_date`, `status` (CHECK `active|closed`, default `active`),
`comment`, `created_by` (**required**), `updated_by`.

| # | Endpoint | Method | URL | Permission |
|---|---|---|---|---|
| 1 | Create Loan/Advance | POST | `/loans-advances` | `loan_advance:create` |
| 2 | List / Search Loans/Advances | GET | `/loans-advances` | `loan_advance:read` |
| 3 | Get Loan/Advance Details | GET | `/loans-advances/{id}` | `loan_advance:read` |
| 4 | Update Loan/Advance | PATCH | `/loans-advances/{id}` | `loan_advance:edit` |
| 5 | Close Loan/Advance | POST | `/loans-advances/{id}/close` | `loan_advance:edit` |
| 6 | Delete Loan/Advance | DELETE | `/loans-advances/{id}` | `loan_advance:delete` |

- **1. Create** — `{ "employee_id", "name", "type", "principal_amount", "monthly_installment", "transaction_date", "comment"? }`.
  `outstanding_amount` initialized to `principal_amount`; `total_debit=0`; `status='active'`; `created_by=caller`.
  **Validation:** `principal_amount>0`, `monthly_installment>0`; `type` ∈ CHECK set; employee exists in org.
  `201`.
- **2. List / Search** — filters `employee_id`, `type`, `status`, `date_from`/`date_to`, `search` (name),
  `branch_id`, `dept_id`; sort `transaction_date`/`outstanding_amount`. Data-scoped. `200` paginated.
- **3. Get** — `200` → header + its `transactions`. `404 LOAN_ADVANCE_NOT_FOUND`.
- **4. Update** — editable fields (`name`, `monthly_installment`, `comment`, …); amounts recomputed by the
  service; `updated_by=caller`. Not editable once `closed` (`409 LOAN_ADVANCE_CLOSED`). `200`.
- **5. Close** — sets `status='closed'` (typically when `outstanding_amount=0`; forced-close is a business
  rule). `200`; `409 LOAN_ADVANCE_CLOSED` if already closed.
- **6. Delete** — hard delete; **blocked if ledger transactions exist** (`ON DELETE RESTRICT` →
  `409 LOAN_ADVANCE_HAS_TRANSACTIONS`). Intended only for an erroneous header with no transactions. `204`.

---

## 5. Loan/Advance Ledger (`/api/v1/loans-advances/{id}/transactions`) — feature key `loan_advance`

`loan_advance_transactions` (append-only ledger): `transaction_date`, `transaction_type` (CHECK
`credit|debit`), `amount`, `installment_amount` (nullable), `type_label` (CHECK `loan|advance`), `source`
(CHECK `manual|payroll`, default `manual`), `payroll_run_id` (deferred, nullable), `comment`, `created_by`.

| # | Endpoint | Method | URL | Permission |
|---|---|---|---|---|
| 7 | Add Ledger Transaction | POST | `/loans-advances/{id}/transactions` | `loan_advance:edit` |
| 8 | List Ledger Transactions | GET | `/loans-advances/{id}/transactions` | `loan_advance:read` |

- **7. Add** — `{ "transaction_date", "transaction_type", "amount", "installment_amount"?, "type_label", "comment"? }`;
  `source='manual'`, `created_by=caller`. **Business rules:** a **debit** (repayment) increases `total_debit`
  and reduces `outstanding_amount`; a **credit** increases exposure; the service maintains header totals and
  may auto-`close` when `outstanding_amount` reaches 0. `amount>0`. Ledger is **append-only** (no update/
  delete). `201`; `404 LOAN_ADVANCE_NOT_FOUND`, `409 LOAN_ADVANCE_CLOSED`.
- **8. List** — filters `transaction_type`, `source`, `date_from`/`date_to`; sort `transaction_date`. `200`
  paginated.
- **Note:** `source='payroll'` entries (with `payroll_run_id`) are posted by Payroll run finalization — read
  here, not created via this endpoint (§11 Q3).

---

## 6. Arrears (`/api/v1/employees/{employee_id}/arrears`, `/arrears`) — feature key `arrears`

`employee_arrears` (**one per `(org, employee)`** — `UNIQUE(org_id, employee_id)`): `arrears_created` (≥0),
`arrears_paid` (≥0), `outstanding_arrears` (≥0).

| # | Endpoint | Method | URL | Permission |
|---|---|---|---|---|
| 9 | Get Employee Arrears | GET | `/employees/{employee_id}/arrears` | `arrears:read` |
| 10 | List Arrears | GET | `/arrears` | `arrears:read` |

- **9.** `200` → the employee's arrears header (or `404 ARREARS_NOT_FOUND` / empty if none yet). Self-service
  for own record.
- **10.** org-wide list; filters `employee_id`, `min_outstanding`, `branch_id`, `dept_id`; sort
  `outstanding_arrears`. Data-scoped. `200` paginated.
- **Note:** the header is created on the first arrears transaction (§7) — there is no standalone "create
  arrears header" endpoint.

---

## 7. Arrears Ledger (`/api/v1/employees/{employee_id}/arrears/transactions`) — feature key `arrears`

`arrears_transactions` (append-only ledger): `employee_arrears_id` (FK RESTRICT), `transaction_date`,
`transaction_type` (CHECK `credit|debit`), `amount`, `outstanding_before`, `outstanding_after`, `source`
(CHECK `manual|payroll`), `payroll_run_id` (deferred), `comment`, `created_by`.

| # | Endpoint | Method | URL | Permission |
|---|---|---|---|---|
| 11 | Add Arrears Transaction | POST | `/employees/{employee_id}/arrears/transactions` | `arrears:edit` |
| 12 | List Arrears Transactions | GET | `/employees/{employee_id}/arrears/transactions` | `arrears:read` |

- **11. Add** — `{ "transaction_date", "transaction_type", "amount", "comment"? }`; `source='manual'`,
  `created_by=caller`. **Creates the `employee_arrears` header if none exists.** A **credit** increases
  `arrears_created`/`outstanding_arrears`; a **debit** increases `arrears_paid` and reduces
  `outstanding_arrears`; the service captures `outstanding_before`/`outstanding_after` and updates the
  header. `amount>0`; a debit cannot exceed `outstanding_arrears` (`409 INSUFFICIENT_ARREARS`). `201`.
- **12. List** — filters `transaction_type`, `source`, `date_from`/`date_to`. `200` paginated.

---

## 8. Settlement Statement, History & Summary — feature key `settlement` (read)

Combined views over the two ledgers (the `settlement_logs_view` is **not implemented** in the DB; these are
computed in the service — §11 Q2).

| # | Endpoint | Method | URL | Permission |
|---|---|---|---|---|
| 13 | Employee Settlement History / Timeline | GET | `/employees/{employee_id}/settlement-history` | `settlement:read` |
| 14 | View Settlement Statement | GET | `/employees/{employee_id}/settlement-statement` | `settlement:read` |
| 15 | Download Settlement Statement | GET | `/employees/{employee_id}/settlement-statement/download` | `settlement:read` |
| 16 | Settlement Summary | GET | `/settlements/summary` | `settlement:read` |

- **13. History / Timeline** — chronological merge of `loan_advance_transactions` + `arrears_transactions`
  for the employee (query `date_from`/`date_to`, `source`). `200` paginated timeline entries
  (date, kind loan/advance/arrears, type credit/debit, amount, running outstanding, source, comment).
- **14. View Statement** — `200` → rendered statement payload: loan/advance headers + outstanding, arrears
  outstanding, and the combined ledger for a period. Self-service for own record.
- **15. Download Statement** — `200` → PDF (via storage/render).
- **16. Summary** — query `employee_id` (or org-wide, data-scoped). `200` → `{ total_active_loans_advances,
  total_outstanding_loans_advances, total_outstanding_arrears, count_active }` aggregates.
- **Errors:** `404 EMPLOYEE_NOT_FOUND`.

---

## 9. Business Rules (summary)

- **Tenant isolation** on all operations; employee-related reads are branch/department data-scoped;
  self-service limited to the caller's own employee.
- **Loan/advance:** `principal_amount>0`, `monthly_installment>0`; `outstanding_amount≥0`, `total_debit≥0`
  (DB CHECKs); header totals maintained by the service from ledger entries; `active → closed`.
- **Arrears:** one header per `(org, employee)`; `outstanding_arrears = arrears_created − arrears_paid ≥ 0`;
  header auto-created on first transaction.
- **Ledgers are append-only** — no update/delete of transactions; intra-module FKs are `ON DELETE RESTRICT`
  (a header with transactions cannot be deleted).
- **Payroll-sourced** (`source='payroll'`) entries are posted by Payroll run finalization (with
  `payroll_run_id`), not created via the manual endpoints.
- **Settlement statement** = combined ledger computed on demand (no DB view yet).

---

## 10. Permission Matrix

| Feature key | create | read | edit | delete |
|---|---|---|---|---|
| `loan_advance` | Create loan/advance, Add ledger txn | List/Get, List ledger | Update, Close | Delete (only if no txns) |
| `arrears` | Add arrears txn (auto-creates header) | Get/List arrears, List ledger | (via txns) | — |
| `settlement` | — | History/Timeline, View/Download statement, Summary | — | — |

Super admins bypass feature checks; tenant isolation always applies; employee reads data-scoped; self-service
for own records (§11 Q5).

---

## 11. Error Handling, Security & Open Questions

**Error envelope** via `core/exceptions/handlers.py`. Module error codes (proposed, `settlements/exceptions.py`):
`LOAN_ADVANCE_NOT_FOUND`(404), `LOAN_ADVANCE_CLOSED`(409), `LOAN_ADVANCE_HAS_TRANSACTIONS`(409),
`ARREARS_NOT_FOUND`(404), `INSUFFICIENT_ARREARS`(409), `EMPLOYEE_NOT_FOUND`(404), `INVALID_TRANSACTION`(422),
`VALIDATION_ERROR`(422), plus shared `AUTH_NOT_AUTHENTICATED`(401)/`AUTH_FORBIDDEN`(403).

**HTTP status codes used:** 200, 201, 204, 400, 401, 403, 404, 409, 422.

**Security considerations:** every route enforces `require_permission` + tenant scope + branch/department data
scope; financial ledgers are sensitive — restricted to permitted roles and the employee's own record;
transactions/closures recorded in the Activity Log (actor, amounts, before/after outstanding); ledgers are
immutable; no secrets/PII in logs; timestamps timezone-aware; rate limiting on transaction and statement
endpoints.

### Open Questions
1. **Full & Final Settlement / Components / Calculations / Approvals (Q1) — NOT supported.** No schema exists
   for F&F settlement, settlement components, settlement calculations, or settlement approval status
   (loan/advance `status` is only `active|closed`). These sections are omitted. Confirm whether a true F&F
   settlement module is planned (needs entirely new schema).
2. **`settlement_logs_view` (Q2).** The architecture describes a UNION-over-ledgers view but leaves its SQL
   undefined/unimplemented. The combined statement/history is computed in the service; confirm whether the DB
   view should be defined (a schema/migration task) or the service computation is sufficient.
3. **Payroll linkage `payroll_run_id` (Q3).** The deferred target is ambiguous
   ("payroll_computed_rows.id or a payroll run table"). `source='payroll'` ledger entries are posted by
   Payroll finalization; confirm the exact FK target and the write ownership (Payroll vs Settlements).
4. **Feature-key catalog (Q4).** `permissions.py` is a stub; confirm `loan_advance`/`arrears`/`settlement`.
5. **Self-service (Q5).** Confirm employees may view their **own** loans/advances, arrears, and settlement
   statement (resolved via `users.employee_id`).
6. **Ledger corrections (Q6).** Ledgers are append-only (no update/delete). Confirm how corrections are made
   (reversing entries vs a correction flow) since there is no `is_removed`/soft-delete on these transaction
   tables.
7. **Envelope key names (Q7).** `shared/schemas/response.py` is a stub; final envelope field names must match
   once implemented (same open item as prior contracts).
