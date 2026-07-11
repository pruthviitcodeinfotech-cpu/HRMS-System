"""settlements

Creates the Settlements module schema: employee_loans_advances,
loan_advance_transactions, employee_arrears, arrears_transactions.

This module's approved architecture uses BIGINT `id` primary keys and INT
`org_id`. ENUM(...) columns from the PDF are implemented as VARCHAR + CHECK to
match the project-wide convention (values preserved exactly).

NOT created: `settlement_logs_view` — the approved architecture describes it as a
derived UNION view over the two transaction tables but does NOT define its SQL;
per the SQL rules it is not invented here. Add it once its definition is provided.

Intra-module FKs (enforced, RESTRICT on delete):
    * loan_advance_transactions.loan_advance_id -> employee_loans_advances
    * arrears_transactions.employee_arrears_id   -> employee_arrears

DEFERRED cross-module FOREIGN KEY constraints (columns created, constraints not):
    * org_id -> organizations : built `organizations` PK is `org_id` (INTEGER),
      this module references `organizations.id`; deferred pending naming/PK
      convention. Columns are INTEGER (matching this module's approved schema).
    * employee_id -> employees : built PK is `employee_id` (INTEGER), this module
      references `employees.id` (BIGINT); deferred. Columns are BIGINT.
    * created_by / updated_by -> users (User Management, not yet built).
    * payroll_run_id -> Payroll : target stated ambiguously in the architecture;
      deferred until confirmed. Columns are BIGINT.

NOTE: the PDF's `arrears_transactions` column list appears truncated at
`created_by`; `created_at` was added to match its sibling
`loan_advance_transactions`. Flagged for confirmation.

Revision ID: 0006_settlements
Revises: 0005_payroll
Create Date: 2026-07-04
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0006_settlements"
down_revision: Union[str, None] = "0005_payroll"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ----- employee_loans_advances -------------------------------------------
    op.create_table(
        "employee_loans_advances",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("org_id", sa.Integer(), nullable=False),  # deferred FK -> organizations
        sa.Column("employee_id", sa.BigInteger(), nullable=False),  # deferred FK -> employees
        sa.Column("name", sa.String(length=50), nullable=False),
        sa.Column("type", sa.String(length=20), server_default=sa.text("'loan'"), nullable=False),
        sa.Column("principal_amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("monthly_installment", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("total_debit", sa.Numeric(precision=12, scale=2), server_default=sa.text("0.00"), nullable=False),
        sa.Column("outstanding_amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("transaction_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(length=20), server_default=sa.text("'active'"), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("created_by", sa.BigInteger(), nullable=False),  # deferred FK -> users
        sa.Column("updated_by", sa.BigInteger(), nullable=True),  # deferred FK -> users
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_employee_loans_advances"),
        sa.CheckConstraint("type IN ('loan', 'advance')", name="ck_employee_loans_advances_type"),
        sa.CheckConstraint("status IN ('active', 'closed')", name="ck_employee_loans_advances_status"),
        sa.CheckConstraint("principal_amount > 0", name="ck_employee_loans_advances_principal_amount"),
        sa.CheckConstraint("monthly_installment > 0", name="ck_employee_loans_advances_monthly_installment"),
        sa.CheckConstraint("total_debit >= 0", name="ck_employee_loans_advances_total_debit"),
        sa.CheckConstraint("outstanding_amount >= 0", name="ck_employee_loans_advances_outstanding_amount"),
    )

    # ----- loan_advance_transactions -----------------------------------------
    op.create_table(
        "loan_advance_transactions",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("org_id", sa.Integer(), nullable=False),  # deferred FK -> organizations
        sa.Column("loan_advance_id", sa.BigInteger(), nullable=False),
        sa.Column("employee_id", sa.BigInteger(), nullable=False),  # deferred FK -> employees
        sa.Column("transaction_date", sa.Date(), nullable=False),
        sa.Column("transaction_type", sa.String(length=10), nullable=False),
        sa.Column("amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("installment_amount", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("type_label", sa.String(length=20), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("source", sa.String(length=10), server_default=sa.text("'manual'"), nullable=False),
        sa.Column("payroll_run_id", sa.BigInteger(), nullable=True),  # deferred FK -> payroll
        sa.Column("created_by", sa.BigInteger(), nullable=False),  # deferred FK -> users
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_loan_advance_transactions"),
        sa.ForeignKeyConstraint(
            ["loan_advance_id"], ["employee_loans_advances.id"],
            name="fk_loan_adv_txns_loan_advance_id_employee_loans_advances",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            "transaction_type IN ('credit', 'debit')",
            name="ck_loan_advance_transactions_transaction_type",
        ),
        sa.CheckConstraint("type_label IN ('loan', 'advance')", name="ck_loan_advance_transactions_type_label"),
        sa.CheckConstraint("source IN ('manual', 'payroll')", name="ck_loan_advance_transactions_source"),
    )
    op.create_index(
        "ix_loan_advance_transactions_employee_id_transaction_date",
        "loan_advance_transactions", ["employee_id", "transaction_date"],
    )
    op.create_index(
        "ix_loan_advance_transactions_org_id_transaction_date_type_label",
        "loan_advance_transactions", ["org_id", "transaction_date", "type_label"],
    )

    # ----- employee_arrears --------------------------------------------------
    op.create_table(
        "employee_arrears",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("org_id", sa.Integer(), nullable=False),  # deferred FK -> organizations
        sa.Column("employee_id", sa.BigInteger(), nullable=False),  # deferred FK -> employees
        sa.Column("arrears_created", sa.Numeric(precision=12, scale=2), server_default=sa.text("0.00"), nullable=False),
        sa.Column("arrears_paid", sa.Numeric(precision=12, scale=2), server_default=sa.text("0.00"), nullable=False),
        sa.Column("outstanding_arrears", sa.Numeric(precision=12, scale=2), server_default=sa.text("0.00"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_employee_arrears"),
        sa.UniqueConstraint("org_id", "employee_id", name="uq_employee_arrears_org_id_employee_id"),
        sa.CheckConstraint("arrears_created >= 0", name="ck_employee_arrears_arrears_created"),
        sa.CheckConstraint("arrears_paid >= 0", name="ck_employee_arrears_arrears_paid"),
        sa.CheckConstraint("outstanding_arrears >= 0", name="ck_employee_arrears_outstanding_arrears"),
    )

    # ----- arrears_transactions ----------------------------------------------
    op.create_table(
        "arrears_transactions",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("org_id", sa.Integer(), nullable=False),  # deferred FK -> organizations
        sa.Column("employee_arrears_id", sa.BigInteger(), nullable=False),
        sa.Column("employee_id", sa.BigInteger(), nullable=False),  # deferred FK -> employees
        sa.Column("transaction_date", sa.Date(), nullable=False),
        sa.Column("transaction_type", sa.String(length=10), nullable=False),
        sa.Column("amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("outstanding_before", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("outstanding_after", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("source", sa.String(length=10), server_default=sa.text("'manual'"), nullable=False),
        sa.Column("payroll_run_id", sa.BigInteger(), nullable=True),  # deferred FK -> payroll
        sa.Column("created_by", sa.BigInteger(), nullable=False),  # deferred FK -> users
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_arrears_transactions"),
        sa.ForeignKeyConstraint(
            ["employee_arrears_id"], ["employee_arrears.id"],
            name="fk_arrears_transactions_employee_arrears_id_employee_arrears",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            "transaction_type IN ('credit', 'debit')",
            name="ck_arrears_transactions_transaction_type",
        ),
        sa.CheckConstraint("source IN ('manual', 'payroll')", name="ck_arrears_transactions_source"),
    )
    op.create_index(
        "ix_arrears_transactions_employee_id_transaction_date",
        "arrears_transactions", ["employee_id", "transaction_date"],
    )
    op.create_index(
        "ix_arrears_transactions_org_id_transaction_date",
        "arrears_transactions", ["org_id", "transaction_date"],
    )


def downgrade() -> None:
    op.drop_index("ix_arrears_transactions_org_id_transaction_date", table_name="arrears_transactions")
    op.drop_index("ix_arrears_transactions_employee_id_transaction_date", table_name="arrears_transactions")
    op.drop_table("arrears_transactions")
    op.drop_table("employee_arrears")
    op.drop_index("ix_loan_advance_transactions_org_id_transaction_date_type_label", table_name="loan_advance_transactions")
    op.drop_index("ix_loan_advance_transactions_employee_id_transaction_date", table_name="loan_advance_transactions")
    op.drop_table("loan_advance_transactions")
    op.drop_table("employee_loans_advances")
