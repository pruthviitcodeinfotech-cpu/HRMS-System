"""Settlement Management — Pydantic request/response schemas (DTOs).

Defines validation, serialization, and structure rules for employee loans,
advances, arrears, ledger transactions, combined settlement statement, history, and summaries.
"""

from __future__ import annotations

import datetime
from decimal import Decimal

from pydantic import Field, model_validator

from app.modules.settlements.constants import (
    LoanAdvanceStatus,
    LoanAdvanceType,
    TransactionSource,
    TransactionType,
)
from app.shared.base.schema import BaseSchema
from app.shared.schemas.pagination import PaginatedResponse, PaginationRequest

# ===========================================================================
# 1. Loans & Advances — Request/Query Schemas (DTOs)
# ===========================================================================


class LoanAdvanceCreateRequest(BaseSchema):
    """Payload for creating/registering a new loan or advance."""

    employee_id: int = Field(..., description="ID of the employee.")
    name: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Name or description for the loan/advance.",
    )
    type: LoanAdvanceType = Field(
        default=LoanAdvanceType.LOAN,
        description="Type: loan or advance.",
    )
    principal_amount: Decimal = Field(
        ...,
        gt=0,
        description="Principal amount of the loan/advance.",
    )
    monthly_installment: Decimal = Field(
        ...,
        gt=0,
        description="Monthly installment recovery amount.",
    )
    transaction_date: datetime.date = Field(
        ...,
        description="Date when the loan/advance was issued.",
    )
    comment: str | None = Field(default=None, description="Optional notes or context.")

    @model_validator(mode="after")
    def _validate_installment(self) -> LoanAdvanceCreateRequest:
        """Validate that monthly installment does not exceed principal amount."""
        if self.monthly_installment > self.principal_amount:
            raise ValueError("monthly_installment cannot exceed principal_amount")
        return self


class LoanAdvanceUpdateRequest(BaseSchema):
    """Payload for patching / updating an existing active loan/advance registry."""

    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=50,
        description="Updated name/description.",
    )
    monthly_installment: Decimal | None = Field(
        default=None,
        gt=0,
        description="Updated monthly installment recovery amount.",
    )
    comment: str | None = Field(default=None, description="Updated notes.")


class LoanAdvanceSearchQuery(PaginationRequest):
    """Query parameters for searching / filtering registered loans and advances."""

    employee_id: int | None = Field(default=None, description="Filter by employee ID.")
    type: LoanAdvanceType | None = Field(
        default=None,
        description="Filter by type: loan or advance.",
    )
    status: LoanAdvanceStatus | None = Field(
        default=None,
        description="Filter by status: active or closed.",
    )
    date_from: datetime.date | None = Field(
        default=None,
        description="Start range of transaction date.",
    )
    date_to: datetime.date | None = Field(
        default=None,
        description="End range of transaction date.",
    )
    search: str | None = Field(default=None, description="Free-text search on name.")
    branch_id: int | None = Field(default=None, description="Filter by branch ID.")
    dept_id: int | None = Field(default=None, description="Filter by department ID.")
    sort_by: str | None = Field(
        default=None,
        description="Field to sort by (e.g. transaction_date, outstanding_amount).",
    )
    sort_order: str | None = Field(
        default=None,
        description="Sort order: asc, desc.",
    )

    @model_validator(mode="after")
    def _validate_date_range(self) -> LoanAdvanceSearchQuery:
        """Validate that date_to is chronologically on or after date_from."""
        if self.date_from and self.date_to and self.date_to < self.date_from:
            raise ValueError("date_to must be on or after date_from")
        return self


# ===========================================================================
# 2. Loan/Advance Ledger — Request/Query Schemas (DTOs)
# ===========================================================================


class LoanAdvanceTransactionCreateRequest(BaseSchema):
    """Payload for adding a manual ledger entry to a loan or advance."""

    transaction_date: datetime.date = Field(
        ...,
        description="Date of the ledger transaction.",
    )
    transaction_type: TransactionType = Field(
        ...,
        description="Transaction type: credit or debit.",
    )
    amount: Decimal = Field(..., gt=0, description="Transaction amount.")
    installment_amount: Decimal | None = Field(
        default=None,
        gt=0,
        description="Optional new monthly installment amount adjustment.",
    )
    type_label: LoanAdvanceType = Field(
        ...,
        description="Type label: loan or advance.",
    )
    comment: str | None = Field(default=None, description="Optional notes or details.")


class LoanAdvanceTransactionSearchQuery(PaginationRequest):
    """Query parameters for filtering loan/advance ledger transactions."""

    transaction_type: TransactionType | None = Field(
        default=None,
        description="Filter by transaction type.",
    )
    source: TransactionSource | None = Field(
        default=None,
        description="Filter by source: manual or payroll.",
    )
    date_from: datetime.date | None = Field(
        default=None,
        description="Start range of transaction date.",
    )
    date_to: datetime.date | None = Field(
        default=None,
        description="End range of transaction date.",
    )
    sort_by: str | None = Field(
        default=None,
        description="Field to sort by (e.g. transaction_date).",
    )
    sort_order: str | None = Field(
        default=None,
        description="Sort order: asc, desc.",
    )

    @model_validator(mode="after")
    def _validate_date_range(self) -> LoanAdvanceTransactionSearchQuery:
        """Validate that date_to is chronologically on or after date_from."""
        if self.date_from and self.date_to and self.date_to < self.date_from:
            raise ValueError("date_to must be on or after date_from")
        return self


# ===========================================================================
# 3. Arrears — Query Schemas (DTOs)
# ===========================================================================


class ArrearsSearchQuery(PaginationRequest):
    """Query parameters for searching / filtering employee arrears."""

    employee_id: int | None = Field(default=None, description="Filter by employee ID.")
    min_outstanding: Decimal | None = Field(
        default=None,
        ge=0,
        description="Filter by minimum outstanding arrears.",
    )
    branch_id: int | None = Field(default=None, description="Filter by branch ID.")
    dept_id: int | None = Field(default=None, description="Filter by department ID.")
    sort_by: str | None = Field(
        default=None,
        description="Field to sort by (e.g. outstanding_arrears).",
    )
    sort_order: str | None = Field(
        default=None,
        description="Sort order: asc, desc.",
    )


# ===========================================================================
# 4. Arrears Ledger — Request/Query Schemas (DTOs)
# ===========================================================================


class ArrearsTransactionCreateRequest(BaseSchema):
    """Payload for adding a manual ledger entry to an employee's arrears."""

    transaction_date: datetime.date = Field(
        ...,
        description="Date of the ledger transaction.",
    )
    transaction_type: TransactionType = Field(
        ...,
        description="Transaction type: credit or debit.",
    )
    amount: Decimal = Field(..., gt=0, description="Transaction amount.")
    comment: str | None = Field(default=None, description="Optional notes or details.")


class ArrearsTransactionSearchQuery(PaginationRequest):
    """Query parameters for filtering arrears ledger transactions."""

    transaction_type: TransactionType | None = Field(
        default=None,
        description="Filter by transaction type.",
    )
    source: TransactionSource | None = Field(
        default=None,
        description="Filter by source: manual or payroll.",
    )
    date_from: datetime.date | None = Field(
        default=None,
        description="Start range of transaction date.",
    )
    date_to: datetime.date | None = Field(
        default=None,
        description="End range of transaction date.",
    )
    sort_by: str | None = Field(
        default=None,
        description="Field to sort by (e.g. transaction_date).",
    )
    sort_order: str | None = Field(
        default=None,
        description="Sort order: asc, desc.",
    )

    @model_validator(mode="after")
    def _validate_date_range(self) -> ArrearsTransactionSearchQuery:
        """Validate that date_to is chronologically on or after date_from."""
        if self.date_from and self.date_to and self.date_to < self.date_from:
            raise ValueError("date_to must be on or after date_from")
        return self


# ===========================================================================
# 5. Combined Settlement Views — Query Schemas (DTOs)
# ===========================================================================


class SettlementHistoryQuery(PaginationRequest):
    """Query parameters for fetching chronological combined history."""

    date_from: datetime.date | None = Field(
        default=None,
        description="Start range of timeline.",
    )
    date_to: datetime.date | None = Field(
        default=None,
        description="End range of timeline.",
    )
    source: TransactionSource | None = Field(
        default=None,
        description="Filter by source: manual or payroll.",
    )

    @model_validator(mode="after")
    def _validate_date_range(self) -> SettlementHistoryQuery:
        """Validate that date_to is chronologically on or after date_from."""
        if self.date_from and self.date_to and self.date_to < self.date_from:
            raise ValueError("date_to must be on or after date_from")
        return self


class SettlementStatementQuery(BaseSchema):
    """Query parameters for viewing or downloading statement."""

    date_from: datetime.date | None = Field(
        default=None,
        description="Start date of statement period.",
    )
    date_to: datetime.date | None = Field(
        default=None,
        description="End date of statement period.",
    )

    @model_validator(mode="after")
    def _validate_date_range(self) -> SettlementStatementQuery:
        """Validate that date_to is chronologically on or after date_from."""
        if self.date_from and self.date_to and self.date_to < self.date_from:
            raise ValueError("date_to must be on or after date_from")
        return self


class SettlementSummaryQuery(BaseSchema):
    """Query parameters for viewing outstanding settlement summary."""

    employee_id: int | None = Field(
        default=None,
        description="Scope summary to a specific employee (optional).",
    )


# ===========================================================================
# 6. Response Schemas (DTOs)
# ===========================================================================


class LoanAdvanceSchema(BaseSchema):
    """Represents an employee loan or advance header record."""

    id: int = Field(..., description="Unique loan/advance registry ID.")
    org_id: int = Field(..., description="Organization/Tenant ID.")
    employee_id: int = Field(..., description="Employee ID.")
    name: str = Field(..., description="Name or description.")
    type: LoanAdvanceType = Field(..., description="Type: loan or advance.")
    principal_amount: Decimal = Field(..., description="Principal amount issued.")
    monthly_installment: Decimal = Field(
        ...,
        description="Monthly recovery installment amount.",
    )
    total_debit: Decimal = Field(..., description="Total amount repaid (debited).")
    outstanding_amount: Decimal = Field(..., description="Current outstanding amount.")
    transaction_date: datetime.date = Field(..., description="Date issued.")
    status: LoanAdvanceStatus = Field(..., description="Status: active or closed.")
    comment: str | None = Field(default=None, description="Optional notes.")
    created_by: int = Field(..., description="User ID of creator.")
    updated_by: int | None = Field(default=None, description="User ID of last updater.")
    created_at: datetime.datetime = Field(..., description="Registry creation timestamp.")
    updated_at: datetime.datetime = Field(
        ...,
        description="Last registry update timestamp.",
    )


class LoanAdvanceTransactionSchema(BaseSchema):
    """Represents a transaction entry in the loan/advance ledger."""

    id: int = Field(..., description="Unique transaction ID.")
    org_id: int = Field(..., description="Organization/Tenant ID.")
    loan_advance_id: int = Field(
        ...,
        description="Associated loan/advance registry ID.",
    )
    employee_id: int = Field(..., description="Employee ID.")
    transaction_date: datetime.date = Field(..., description="Transaction date.")
    transaction_type: TransactionType = Field(
        ...,
        description="Transaction type: credit or debit.",
    )
    amount: Decimal = Field(..., description="Transaction amount.")
    installment_amount: Decimal | None = Field(
        default=None,
        description="Revised monthly installment amount if set.",
    )
    type_label: LoanAdvanceType = Field(..., description="Type label: loan or advance.")
    comment: str | None = Field(default=None, description="Optional transaction notes.")
    source: TransactionSource = Field(
        ...,
        description="Source of transaction: manual or payroll.",
    )
    payroll_run_id: int | None = Field(
        default=None,
        description="Associated payroll run ID if posted via payroll.",
    )
    created_by: int = Field(..., description="User ID of creator.")
    created_at: datetime.datetime = Field(..., description="Transaction creation timestamp.")


class LoanAdvanceDetailsSchema(LoanAdvanceSchema):
    """Detailed loan/advance record including the ledger transactions list."""

    transactions: list[LoanAdvanceTransactionSchema] = Field(
        default_factory=list,
        description="List of ledger transactions.",
    )


class EmployeeArrearsSchema(BaseSchema):
    """Represents an employee arrears header record."""

    id: int = Field(..., description="Unique arrears registry ID.")
    org_id: int = Field(..., description="Organization/Tenant ID.")
    employee_id: int = Field(..., description="Employee ID.")
    arrears_created: Decimal = Field(
        ...,
        description="Total arrears created (credited).",
    )
    arrears_paid: Decimal = Field(..., description="Total arrears paid (debited).")
    outstanding_arrears: Decimal = Field(
        ...,
        description="Current outstanding arrears.",
    )
    created_at: datetime.datetime = Field(..., description="Arrears creation timestamp.")
    updated_at: datetime.datetime = Field(..., description="Last arrears update timestamp.")


class ArrearsTransactionSchema(BaseSchema):
    """Represents a transaction entry in the arrears ledger."""

    id: int = Field(..., description="Unique transaction ID.")
    org_id: int = Field(..., description="Organization/Tenant ID.")
    employee_arrears_id: int = Field(
        ...,
        description="Associated employee arrears registry ID.",
    )
    employee_id: int = Field(..., description="Employee ID.")
    transaction_date: datetime.date = Field(..., description="Transaction date.")
    transaction_type: TransactionType = Field(
        ...,
        description="Transaction type: credit or debit.",
    )
    amount: Decimal = Field(..., description="Transaction amount.")
    outstanding_before: Decimal = Field(
        ...,
        description="Outstanding arrears amount before transaction.",
    )
    outstanding_after: Decimal = Field(
        ...,
        description="Outstanding arrears amount after transaction.",
    )
    comment: str | None = Field(default=None, description="Optional transaction notes.")
    source: TransactionSource = Field(
        ...,
        description="Source of transaction: manual or payroll.",
    )
    payroll_run_id: int | None = Field(
        default=None,
        description="Associated payroll run ID if posted via payroll.",
    )
    created_by: int = Field(..., description="User ID of creator.")
    created_at: datetime.datetime = Field(..., description="Transaction creation timestamp.")


class SettlementHistoryEntrySchema(BaseSchema):
    """A single timeline entry in the merged loan/advance and arrears transaction history."""

    date: datetime.date = Field(..., description="Transaction date.")
    kind: str = Field(
        ...,
        description="Kind of settlement entry: loan, advance, or arrears.",
    )
    transaction_type: TransactionType = Field(
        ...,
        description="Transaction type: credit or debit.",
    )
    amount: Decimal = Field(..., description="Transaction amount.")
    running_outstanding: Decimal = Field(
        ...,
        description="Running outstanding balance after this transaction.",
    )
    source: TransactionSource = Field(
        ...,
        description="Source of transaction: manual or payroll.",
    )
    comment: str | None = Field(default=None, description="Optional notes or details.")


class SettlementStatementSchema(BaseSchema):
    """Combined settlement statement payload for an employee."""

    employee_id: int = Field(..., description="Employee ID.")
    org_id: int = Field(..., description="Organization/Tenant ID.")
    loans_advances: list[LoanAdvanceSchema] = Field(
        default_factory=list,
        description="List of loan/advance header registries.",
    )
    total_outstanding_loans_advances: Decimal = Field(
        ...,
        description="Aggregate outstanding amount on all active loans/advances.",
    )
    arrears: EmployeeArrearsSchema | None = Field(
        default=None,
        description="Arrears header information.",
    )
    total_outstanding_arrears: Decimal = Field(
        ...,
        description="Outstanding arrears amount.",
    )
    statement_period_start: datetime.date | None = Field(
        default=None,
        description="Start date of the statement period.",
    )
    statement_period_end: datetime.date | None = Field(
        default=None,
        description="End date of the statement period.",
    )
    ledger: list[SettlementHistoryEntrySchema] = Field(
        default_factory=list,
        description="Chronologically merged transaction log ledger.",
    )


class SettlementSummarySchema(BaseSchema):
    """Aggregate settlement summary (e.g. for dashboard or organizational view)."""

    total_active_loans_advances: Decimal = Field(
        ...,
        description="Aggregate principal of all active loans and advances.",
    )
    total_outstanding_loans_advances: Decimal = Field(
        ...,
        description="Aggregate outstanding amount of all active loans and advances.",
    )
    total_outstanding_arrears: Decimal = Field(
        ...,
        description="Aggregate outstanding arrears.",
    )
    count_active: int = Field(
        ...,
        description="Count of active loans and advances.",
    )


# ===========================================================================
# 7. Paginated Response Envelopes
# ===========================================================================


class LoanAdvanceListResponse(PaginatedResponse[LoanAdvanceSchema]):
    """Paginated response containing a list of loan/advance headers."""


class LoanAdvanceTransactionListResponse(PaginatedResponse[LoanAdvanceTransactionSchema]):
    """Paginated response containing a list of loan/advance transactions."""


class EmployeeArrearsListResponse(PaginatedResponse[EmployeeArrearsSchema]):
    """Paginated response containing a list of employee arrears headers."""


class ArrearsTransactionListResponse(PaginatedResponse[ArrearsTransactionSchema]):
    """Paginated response containing a list of arrears transactions."""


class SettlementHistoryResponse(PaginatedResponse[SettlementHistoryEntrySchema]):
    """Paginated response containing a list of settlement history entries."""


__all__ = [
    # Requests / Queries
    "LoanAdvanceCreateRequest",
    "LoanAdvanceUpdateRequest",
    "LoanAdvanceSearchQuery",
    "LoanAdvanceTransactionCreateRequest",
    "LoanAdvanceTransactionSearchQuery",
    "ArrearsSearchQuery",
    "ArrearsTransactionCreateRequest",
    "ArrearsTransactionSearchQuery",
    "SettlementHistoryQuery",
    "SettlementStatementQuery",
    "SettlementSummaryQuery",
    # Responses / DTOs
    "LoanAdvanceSchema",
    "LoanAdvanceTransactionSchema",
    "LoanAdvanceDetailsSchema",
    "EmployeeArrearsSchema",
    "ArrearsTransactionSchema",
    "SettlementHistoryEntrySchema",
    "SettlementStatementSchema",
    "SettlementSummarySchema",
    # Paginated response wrappers
    "LoanAdvanceListResponse",
    "LoanAdvanceTransactionListResponse",
    "EmployeeArrearsListResponse",
    "ArrearsTransactionListResponse",
    "SettlementHistoryResponse",
]
