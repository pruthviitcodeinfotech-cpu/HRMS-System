"""fk supporting indexes

PostgreSQL indexes the PARENT side of a FOREIGN KEY (the referenced primary /
unique key) but never the CHILD side. Every unindexed child FK column therefore
costs a sequential scan twice over:

    * on JOIN / WHERE, whenever a query filters or joins on that column;
    * on parent DELETE/UPDATE, when the server must prove no child row still
      references the row being removed (ON DELETE RESTRICT / CASCADE / SET NULL).

A live-schema audit at revision 0017 found 89 unindexed child FK columns. This
revision does NOT index all 89: an index is a permanent tax on every INSERT,
UPDATE and DELETE of the table, so only columns with demonstrated read or
referential-integrity value are covered here. 25 indexes are created, in four
evidence-backed groups (see the block comments in `upgrade()`).

Deliberately NOT indexed:
    * Actor columns (`created_by`, `updated_by`, `reviewed_by`, `adjusted_by`,
      `marked_by`, `applied_by`, `assigned_by`, `granted_by`, ...). ~40 of the
      89. No repository filters or joins on them; they are write-once audit
      stamps, so an index would be pure write overhead.
    * Payroll-module-owned tables (payroll_*, finalized_payroll_runs,
      attendance_adjustment*, employee_payroll_group_assignments). Indexing them
      without a matching ORM `__table_args__` declaration would make
      `alembic revision --autogenerate` immediately want to DROP the index.
    * activity_logs.employee_id — already served by the existing
      (org_id, employee_id) composite; the audit repository always leads with
      org_id, and employees are soft-deleted, so no parent DELETE ever fires.
    * working_hours_config(_history) and employee_import_logs — no repository or
      service reads these tables today; an index would buy nothing.

Every identifier below is <= 63 characters (PostgreSQL's NAMEDATALEN limit); the
longest is `ix_loan_advance_transactions_loan_advance_id` at 43.

Revision ID: 0018_fk_supporting_indexes
Revises: 0017_employee_settlement_state
Create Date: 2026-07-11
"""

from collections.abc import Sequence
from typing import Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0018_fk_supporting_indexes"
down_revision: Union[str, None] = "0017_employee_settlement_state"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# (index_name, table_name, [columns]) — single source of truth so that
# downgrade() drops exactly what upgrade() creates.
INDEXES: list[tuple[str, str, list[str]]] = [
    # ----- 1. Employee-detail satellites ------------------------------------
    # GET /employees/{id} `selectinload`s eight to-many collections; each emits
    # `SELECT ... WHERE employee_id IN (...)`. Without these, every one of those
    # round-trips is a full sequential scan of the satellite table.
    # (biometrics / punch_branches / holiday_assignments / leave_allocations /
    #  leave_balances already have an employee_id-leading unique index.)
    ("ix_employee_bank_details_employee_id", "employee_bank_details", ["employee_id"]),
    ("ix_employee_documents_employee_id", "employee_documents", ["employee_id"]),
    ("ix_employee_emergency_contacts_employee_id", "employee_emergency_contacts", ["employee_id"]),
    ("ix_employee_references_employee_id", "employee_references", ["employee_id"]),
    ("ix_employee_tags_employee_id", "employee_tags", ["employee_id"]),
    ("ix_employee_status_history_employee_id", "employee_status_history", ["employee_id"]),
    # ----- 2. Tenant scoping (org_id) ---------------------------------------
    # Every list query is org-scoped. Where the repository reliably pairs org_id
    # with a second predicate or sort key, a composite is used: the leading
    # org_id column still satisfies the FK-lookup requirement, and the trailing
    # column additionally serves the filter / ORDER BY.
    ("ix_branches_org_id", "branches", ["org_id"]),
    # AttendancePunchRepository.search(): WHERE org_id = ? ORDER BY punch_time DESC
    ("ix_attendance_punches_org_id_punch_time", "attendance_punches", ["org_id", "punch_time"]),
    # AttendancePenaltyRepository._search_stmt(): WHERE org_id = ? [AND status = ?]
    ("ix_attendance_penalties_org_id_status", "attendance_penalties", ["org_id", "status"]),
    # ShiftAssignmentRepository: WHERE org_id = ? [AND employee_id = ?]
    ("ix_shift_assignments_org_id_employee_id", "shift_assignments", ["org_id", "employee_id"]),
    # ----- 3. FK columns filtered / joined by real queries -------------------
    # attendance/repository.py:103 — WHERE attendance_days.shift_id = ?
    ("ix_attendance_days_shift_id", "attendance_days", ["shift_id"]),
    # shift/repository.py:108,119 — WHERE shift_assignments.shift_id = ?
    ("ix_shift_assignments_shift_id", "shift_assignments", ["shift_id"]),
    ("ix_roster_shift_id", "roster", ["shift_id"]),
    # employee/organization/approvals/dashboard repositories filter employees by
    # these three and JOIN departments / branches / designations on them. They
    # also guard the "is this department still in use?" delete check.
    ("ix_employees_dept_id", "employees", ["dept_id"]),
    ("ix_employees_designation_id", "employees", ["designation_id"]),
    ("ix_employees_master_branch_id", "employees", ["master_branch_id"]),
    # rbac/repository.py:93 — WHERE users.employee_id = ?  (login -> employee)
    # notifications/service.py:589 — WHERE users.employee_id IN (...)
    ("ix_users_employee_id", "users", ["employee_id"]),
    # leave/repository.py:82 — WHERE employee_leave_balances.leave_type_id = ?
    # (leave_type in-use guard; the existing uq leads with employee_id and so
    #  cannot serve a leave_type_id-only lookup.)
    ("ix_employee_leave_balances_leave_type_id", "employee_leave_balances", ["leave_type_id"]),
    (
        "ix_employee_holiday_assignments_template_id",
        "employee_holiday_assignments",
        ["template_id"],
    ),
    # ----- 4. ON DELETE RESTRICT parents ------------------------------------
    # The child column MUST be indexed or every parent delete sequentially scans
    # the child table to enforce the constraint.
    ("ix_employee_biometrics_device_id", "employee_biometrics", ["device_id"]),
    ("ix_user_branch_access_branch_id", "user_branch_access", ["branch_id"]),
    ("ix_user_department_access_department_id", "user_department_access", ["department_id"]),
    ("ix_user_template_assignments_template_id", "user_template_assignments", ["template_id"]),
    (
        "ix_arrears_transactions_employee_arrears_id",
        "arrears_transactions",
        ["employee_arrears_id"],
    ),
    (
        "ix_loan_advance_transactions_loan_advance_id",
        "loan_advance_transactions",
        ["loan_advance_id"],
    ),
]

# PostgreSQL truncates identifiers at NAMEDATALEN-1 = 63 bytes, which would
# silently collide two names. Fail loudly at import time instead.
_TOO_LONG = [name for name, _table, _cols in INDEXES if len(name) > 63]
if _TOO_LONG:  # pragma: no cover - guard, never true in a committed revision
    raise ValueError(f"index name(s) exceed PostgreSQL's 63-char limit: {_TOO_LONG}")


def upgrade() -> None:
    for name, table, cols in INDEXES:
        op.create_index(name, table, cols)


def downgrade() -> None:
    for name, table, _cols in reversed(INDEXES):
        op.drop_index(name, table_name=table)
