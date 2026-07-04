"""Settlements module: constants and enums.

The approved Settlements Database Architecture declares several columns as
ENUM(...) types. To keep the whole HRMS schema consistent (this project uses
VARCHAR + CHECK for enumerated columns, not native PostgreSQL ENUM types), those
value sets are implemented as CHECK constraints — the allowed values are
preserved exactly. These enums are the single source of truth for those checks.
"""

from enum import Enum


class LoanAdvanceType(str, Enum):
    """employee_loans_advances.type / loan_advance_transactions.type_label.
    (Enforced by DB CHECK.)"""

    LOAN = "loan"
    ADVANCE = "advance"


class LoanAdvanceStatus(str, Enum):
    """employee_loans_advances.status. (Enforced by DB CHECK.)"""

    ACTIVE = "active"
    CLOSED = "closed"


class TransactionType(str, Enum):
    """loan_advance_transactions / arrears_transactions.transaction_type.
    (Enforced by DB CHECK.)"""

    CREDIT = "credit"
    DEBIT = "debit"


class TransactionSource(str, Enum):
    """loan_advance_transactions / arrears_transactions.source. (Enforced by DB CHECK.)"""

    MANUAL = "manual"
    PAYROLL = "payroll"
