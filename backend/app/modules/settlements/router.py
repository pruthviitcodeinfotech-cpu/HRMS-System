"""Settlement Management — HTTP routes (thin controllers).

Maps the Settlement Management API Contract onto FastAPI endpoints.
Controllers resolve dependencies, parse queries, call SettlementService,
and return standard SuccessResponse envelopes.
"""

from __future__ import annotations

import datetime
from decimal import Decimal
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import Response, StreamingResponse

from app.core.constants.enums import PermissionAction as A
from app.core.dependencies.auth import (
    CurrentUser,
    get_current_active_user,
    require_permission,
)
from app.core.dependencies.pagination import PaginationParams, pagination_params
from app.core.exceptions.base import AppException
from app.core.middleware.request_context import get_request_id
from app.modules.settlements.constants import (
    LoanAdvanceStatus,
    LoanAdvanceType,
    TransactionSource,
    TransactionType,
)
from app.modules.settlements.dependencies import SettlementServiceDep
from app.modules.settlements.schemas import (
    ArrearsSearchQuery,
    ArrearsTransactionCreateRequest,
    ArrearsTransactionListResponse,
    ArrearsTransactionSchema,
    ArrearsTransactionSearchQuery,
    EmployeeArrearsListResponse,
    EmployeeArrearsSchema,
    LoanAdvanceCreateRequest,
    LoanAdvanceDetailsSchema,
    LoanAdvanceListResponse,
    LoanAdvanceSchema,
    LoanAdvanceSearchQuery,
    LoanAdvanceTransactionCreateRequest,
    LoanAdvanceTransactionListResponse,
    LoanAdvanceTransactionSchema,
    LoanAdvanceTransactionSearchQuery,
    LoanAdvanceUpdateRequest,
    SettlementHistoryQuery,
    SettlementHistoryResponse,
    SettlementStatementQuery,
    SettlementStatementSchema,
    SettlementSummaryQuery,
    SettlementSummarySchema,
)
from app.shared.schemas.response import SuccessResponse, success_response

router = APIRouter(tags=["Settlement Management"])

# Feature-permission keys from permission matrix
_LOAN_ADVANCE = "loan_advance"
_ARREARS = "arrears"
_SETTLEMENT = "settlement"


# =========================================================================
# Common Dependencies & Helpers
# =========================================================================


def get_org_id(current_user: Annotated[CurrentUser, Depends(get_current_active_user)]) -> int:
    """Return the caller's tenant id, or raise TENANT_UNRESOLVED if absent."""
    if current_user.org_id is None:
        exc = AppException("Organization context is required.", code="TENANT_UNRESOLVED")
        exc.status_code = status.HTTP_400_BAD_REQUEST
        raise exc
    return current_user.org_id


OrgIdDep = Annotated[int, Depends(get_org_id)]
CurrentUserDep = Annotated[CurrentUser, Depends(get_current_active_user)]


def _ok(data: Any, message: str = "OK") -> dict[str, Any]:
    """Helper to wrap controller responses in the standard SuccessResponse envelope."""
    return success_response(data=data, message=message, request_id=get_request_id())


# =========================================================================
# 1. Loans & Advances Endpoints
# =========================================================================


@router.post(
    "/loans-advances",
    response_model=SuccessResponse[LoanAdvanceSchema],
    status_code=status.HTTP_201_CREATED,
    summary="Create Loan/Advance",
    dependencies=[Depends(require_permission(_LOAN_ADVANCE, A.CREATE))],
)
async def create_loan_advance(
    payload: LoanAdvanceCreateRequest,
    service: SettlementServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Register and issue a new loan or advance header for an employee."""
    result = await service.create_loan_advance(
        org_id=org_id, data=payload.model_dump(), user_id=current_user.user_id
    )
    return _ok(result, "Loan/Advance created successfully.")


@router.get(
    "/loans-advances",
    response_model=SuccessResponse[LoanAdvanceListResponse],
    summary="List / Search Loans/Advances",
    dependencies=[Depends(require_permission(_LOAN_ADVANCE, A.READ))],
)
async def search_loans_advances(
    service: SettlementServiceDep,
    org_id: OrgIdDep,
    pagination: Annotated[PaginationParams, Depends(pagination_params)],
    employee_id: Annotated[int | None, Query(description="Filter by employee ID.")] = None,
    type: Annotated[LoanAdvanceType | None, Query(description="Filter by type.")] = None,
    status_filter: Annotated[
        LoanAdvanceStatus | None, Query(alias="status", description="Filter by status.")
    ] = None,
    date_from: Annotated[
        datetime.date | None, Query(description="Start range of transaction date.")
    ] = None,
    date_to: Annotated[
        datetime.date | None, Query(description="End range of transaction date.")
    ] = None,
    search: Annotated[str | None, Query(description="Free-text search on name.")] = None,
    branch_id: Annotated[int | None, Query(description="Filter by branch ID.")] = None,
    dept_id: Annotated[int | None, Query(description="Filter by department ID.")] = None,
    sort_by: Annotated[str | None, Query(description="Field to sort by.")] = None,
    sort_order: Annotated[str | None, Query(description="Sort order (asc/desc).")] = None,
) -> dict[str, Any]:
    """Search and filter through all employee loans & advances registries."""
    query = LoanAdvanceSearchQuery(
        page=pagination.page,
        page_size=pagination.page_size,
        employee_id=employee_id,
        type=type,
        status=status_filter,
        date_from=date_from,
        date_to=date_to,
        search=search,
        branch_id=branch_id,
        dept_id=dept_id,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    result = await service.search_loans_advances(org_id=org_id, query=query)
    return _ok(result)


@router.get(
    "/loans-advances/{id}",
    response_model=SuccessResponse[LoanAdvanceDetailsSchema],
    summary="Get Loan/Advance Details",
    dependencies=[Depends(require_permission(_LOAN_ADVANCE, A.READ))],
)
async def get_loan_advance(
    id: int,
    service: SettlementServiceDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Retrieve full details of a specific loan/advance along with transaction ledger."""
    loan = await service.get_loan_advance(org_id=org_id, loan_advance_id=id)
    # Fetch all transaction logs (up to max limit of 200)
    query = LoanAdvanceTransactionSearchQuery(page=1, page_size=200)
    txs_res = await service.list_loan_advance_transactions(
        org_id=org_id, loan_advance_id=id, query=query
    )

    details = LoanAdvanceDetailsSchema.model_validate(loan)
    details.transactions = txs_res.items
    return _ok(details)


@router.patch(
    "/loans-advances/{id}",
    response_model=SuccessResponse[LoanAdvanceSchema],
    summary="Update Loan/Advance",
    dependencies=[Depends(require_permission(_LOAN_ADVANCE, A.EDIT))],
)
async def update_loan_advance(
    id: int,
    payload: LoanAdvanceUpdateRequest,
    service: SettlementServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Modify parameters of an active loan/advance header."""
    result = await service.update_loan_advance(
        org_id=org_id,
        loan_advance_id=id,
        data=payload.model_dump(exclude_unset=True),
        user_id=current_user.user_id,
    )
    return _ok(result, "Loan/Advance updated successfully.")


@router.post(
    "/loans-advances/{id}/close",
    response_model=SuccessResponse[LoanAdvanceSchema],
    summary="Close Loan/Advance",
    dependencies=[Depends(require_permission(_LOAN_ADVANCE, A.EDIT))],
)
async def close_loan_advance(
    id: int,
    service: SettlementServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Manually mark an active loan/advance registry as closed."""
    result = await service.close_loan_advance(
        org_id=org_id, loan_advance_id=id, user_id=current_user.user_id
    )
    return _ok(result, "Loan/Advance closed successfully.")


@router.delete(
    "/loans-advances/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Loan/Advance",
    dependencies=[Depends(require_permission(_LOAN_ADVANCE, A.DELETE))],
)
async def delete_loan_advance(
    id: int,
    service: SettlementServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
) -> Response:
    """Delete a loan/advance registry header if no ledger transaction history exists."""
    await service.delete_loan_advance(
        org_id=org_id, loan_advance_id=id, user_id=current_user.user_id
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# =========================================================================
# 2. Loan/Advance Ledger Endpoints
# =========================================================================


@router.post(
    "/loans-advances/{id}/transactions",
    response_model=SuccessResponse[LoanAdvanceTransactionSchema],
    status_code=status.HTTP_201_CREATED,
    summary="Add Ledger Transaction",
    dependencies=[Depends(require_permission(_LOAN_ADVANCE, A.EDIT))],
)
async def add_loan_advance_transaction(
    id: int,
    payload: LoanAdvanceTransactionCreateRequest,
    service: SettlementServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Add a manual transaction log (credit or debit) to a loan/advance ledger."""
    result = await service.add_loan_advance_transaction(
        org_id=org_id,
        loan_advance_id=id,
        data=payload.model_dump(),
        user_id=current_user.user_id,
    )
    return _ok(result, "Ledger transaction added successfully.")


@router.get(
    "/loans-advances/{id}/transactions",
    response_model=SuccessResponse[LoanAdvanceTransactionListResponse],
    summary="List Ledger Transactions",
    dependencies=[Depends(require_permission(_LOAN_ADVANCE, A.READ))],
)
async def list_loan_advance_transactions(
    id: int,
    service: SettlementServiceDep,
    org_id: OrgIdDep,
    pagination: Annotated[PaginationParams, Depends(pagination_params)],
    transaction_type: Annotated[
        TransactionType | None, Query(description="Filter by type.")
    ] = None,
    source: Annotated[TransactionSource | None, Query(description="Filter by source.")] = None,
    date_from: Annotated[datetime.date | None, Query(description="Start date.")] = None,
    date_to: Annotated[datetime.date | None, Query(description="End date.")] = None,
    sort_by: Annotated[str | None, Query(description="Sort field.")] = None,
    sort_order: Annotated[str | None, Query(description="Sort order.")] = None,
) -> dict[str, Any]:
    """Retrieve filtered, paginated ledger transaction history of a loan/advance registry."""
    query = LoanAdvanceTransactionSearchQuery(
        page=pagination.page,
        page_size=pagination.page_size,
        transaction_type=transaction_type,
        source=source,
        date_from=date_from,
        date_to=date_to,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    result = await service.list_loan_advance_transactions(
        org_id=org_id, loan_advance_id=id, query=query
    )
    return _ok(result)


# =========================================================================
# 3. Arrears Endpoints
# =========================================================================


@router.get(
    "/employees/{employee_id}/arrears",
    response_model=SuccessResponse[EmployeeArrearsSchema],
    summary="Get Employee Arrears",
    dependencies=[Depends(require_permission(_ARREARS, A.READ))],
)
async def get_employee_arrears(
    employee_id: int,
    service: SettlementServiceDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Retrieve details of outstanding arrears for a specific employee."""
    result = await service.get_employee_arrears(org_id=org_id, employee_id=employee_id)
    return _ok(result)


@router.get(
    "/arrears",
    response_model=SuccessResponse[EmployeeArrearsListResponse],
    summary="List Arrears",
    dependencies=[Depends(require_permission(_ARREARS, A.READ))],
)
async def list_employee_arrears(
    service: SettlementServiceDep,
    org_id: OrgIdDep,
    pagination: Annotated[PaginationParams, Depends(pagination_params)],
    employee_id: Annotated[int | None, Query(description="Filter by employee ID.")] = None,
    min_outstanding: Annotated[
        Decimal | None, Query(description="Filter by minimum outstanding.")
    ] = None,
    branch_id: Annotated[int | None, Query(description="Filter by branch ID.")] = None,
    dept_id: Annotated[int | None, Query(description="Filter by department ID.")] = None,
    sort_by: Annotated[str | None, Query(description="Sort field.")] = None,
    sort_order: Annotated[str | None, Query(description="Sort order.")] = None,
) -> dict[str, Any]:
    """Search and paginate arrears registry headers across the organization."""
    query = ArrearsSearchQuery(
        page=pagination.page,
        page_size=pagination.page_size,
        employee_id=employee_id,
        min_outstanding=min_outstanding,
        branch_id=branch_id,
        dept_id=dept_id,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    result = await service.list_employee_arrears(org_id=org_id, query=query)
    return _ok(result)


# =========================================================================
# 4. Arrears Ledger Endpoints
# =========================================================================


@router.post(
    "/employees/{employee_id}/arrears/transactions",
    response_model=SuccessResponse[ArrearsTransactionSchema],
    status_code=status.HTTP_201_CREATED,
    summary="Add Arrears Transaction",
    dependencies=[Depends(require_permission(_ARREARS, A.EDIT))],
)
async def add_arrears_transaction(
    employee_id: int,
    payload: ArrearsTransactionCreateRequest,
    service: SettlementServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Add a manual transaction (credit or debit) to an employee's arrears ledger."""
    result = await service.add_arrears_transaction(
        org_id=org_id,
        employee_id=employee_id,
        data=payload.model_dump(),
        user_id=current_user.user_id,
    )
    return _ok(result, "Arrears transaction added successfully.")


@router.get(
    "/employees/{employee_id}/arrears/transactions",
    response_model=SuccessResponse[ArrearsTransactionListResponse],
    summary="List Arrears Transactions",
    dependencies=[Depends(require_permission(_ARREARS, A.READ))],
)
async def list_arrears_transactions(
    employee_id: int,
    service: SettlementServiceDep,
    org_id: OrgIdDep,
    pagination: Annotated[PaginationParams, Depends(pagination_params)],
    transaction_type: Annotated[
        TransactionType | None, Query(description="Filter by type.")
    ] = None,
    source: Annotated[TransactionSource | None, Query(description="Filter by source.")] = None,
    date_from: Annotated[datetime.date | None, Query(description="Start date.")] = None,
    date_to: Annotated[datetime.date | None, Query(description="End date.")] = None,
    sort_by: Annotated[str | None, Query(description="Sort field.")] = None,
    sort_order: Annotated[str | None, Query(description="Sort order.")] = None,
) -> dict[str, Any]:
    """Retrieve filtered, paginated transaction history logs for an employee's arrears."""
    query = ArrearsTransactionSearchQuery(
        page=pagination.page,
        page_size=pagination.page_size,
        transaction_type=transaction_type,
        source=source,
        date_from=date_from,
        date_to=date_to,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    result = await service.list_arrears_transactions(
        org_id=org_id, employee_id=employee_id, query=query
    )
    return _ok(result)


# =========================================================================
# 5. Combined Statement, History & Summary Endpoints
# =========================================================================


@router.get(
    "/employees/{employee_id}/settlement-history",
    response_model=SuccessResponse[SettlementHistoryResponse],
    summary="Employee Settlement History / Timeline",
    dependencies=[Depends(require_permission(_SETTLEMENT, A.READ))],
)
async def get_settlement_history(
    employee_id: int,
    service: SettlementServiceDep,
    org_id: OrgIdDep,
    pagination: Annotated[PaginationParams, Depends(pagination_params)],
    date_from: Annotated[datetime.date | None, Query(description="Start range.")] = None,
    date_to: Annotated[datetime.date | None, Query(description="End range.")] = None,
    source: Annotated[TransactionSource | None, Query(description="Filter by source.")] = None,
) -> dict[str, Any]:
    """Return chronological timeline entry log merging loan, advance, and arrears ledger logs."""
    query = SettlementHistoryQuery(
        page=pagination.page,
        page_size=pagination.page_size,
        date_from=date_from,
        date_to=date_to,
        source=source,
    )
    result = await service.get_settlement_history(
        org_id=org_id, employee_id=employee_id, query=query
    )
    return _ok(result)


@router.get(
    "/employees/{employee_id}/settlement-statement",
    response_model=SuccessResponse[SettlementStatementSchema],
    summary="View Settlement Statement",
    dependencies=[Depends(require_permission(_SETTLEMENT, A.READ))],
)
async def get_settlement_statement(
    employee_id: int,
    service: SettlementServiceDep,
    org_id: OrgIdDep,
    date_from: Annotated[datetime.date | None, Query(description="Start range.")] = None,
    date_to: Annotated[datetime.date | None, Query(description="End range.")] = None,
) -> dict[str, Any]:
    """Retrieve combined settlement statement payload.

    Includes summary exposure and running ledger logs.
    """
    query = SettlementStatementQuery(date_from=date_from, date_to=date_to)
    result = await service.get_settlement_statement(
        org_id=org_id, employee_id=employee_id, query=query
    )
    return _ok(result)


@router.get(
    "/employees/{employee_id}/settlement-statement/download",
    summary="Download Settlement Statement",
    dependencies=[Depends(require_permission(_SETTLEMENT, A.READ))],
)
async def download_settlement_statement(
    employee_id: int,
    service: SettlementServiceDep,
    org_id: OrgIdDep,
    date_from: Annotated[datetime.date | None, Query(description="Start range.")] = None,
    date_to: Annotated[datetime.date | None, Query(description="End range.")] = None,
) -> StreamingResponse:
    """Download the combined statement ledger in text/pdf representation."""
    import io

    query = SettlementStatementQuery(date_from=date_from, date_to=date_to)
    statement = await service.get_settlement_statement(
        org_id=org_id, employee_id=employee_id, query=query
    )

    # Generate layout structure of the statement receipt
    content = f"Settlement Statement for Employee ID: {employee_id}\n"
    content += f"Period: {date_from or 'Beginning'} to {date_to or 'Ending'}\n"
    content += f"Outstanding Loans/Advances: INR {statement['total_outstanding_loans_advances']}\n"
    content += f"Outstanding Arrears: INR {statement['total_outstanding_arrears']}\n"
    content += "\n--- Merged Ledger ---\n"
    for entry in statement["ledger"]:
        desc = entry["comment"] or ""
        content += (
            f"{entry['date']} | {entry['kind']} | {entry['transaction_type']} | "
            f"INR {entry['amount']} | Running: INR {entry['running_outstanding']} | "
            f"Source: {entry['source']} | {desc}\n"
        )

    buf = io.BytesIO(content.encode("utf-8"))
    return StreamingResponse(
        buf,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=statement_{employee_id}.pdf"},
    )


@router.get(
    "/settlements/summary",
    response_model=SuccessResponse[SettlementSummarySchema],
    summary="Settlement Summary",
    dependencies=[Depends(require_permission(_SETTLEMENT, A.READ))],
)
async def get_settlement_summary(
    service: SettlementServiceDep,
    org_id: OrgIdDep,
    employee_id: Annotated[int | None, Query(description="Filter by employee.")] = None,
) -> dict[str, Any]:
    """Retrieve organization-wide aggregate figures on active loans and total arrears."""
    query = SettlementSummaryQuery(employee_id=employee_id)
    result = await service.get_settlement_summary(org_id=org_id, query=query)
    return _ok(result)


# =========================================================================
# 6. F&F Settlement Preview, Approval & Finalization Endpoints
# =========================================================================


@router.get(
    "/employees/{employee_id}/settlement-preview",
    summary="Preview F&F Settlement",
    dependencies=[Depends(require_permission(_SETTLEMENT, A.READ))],
)
async def preview_ff_settlement(
    employee_id: int,
    service: SettlementServiceDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Calculate and preview dry-run Full & Final exposure for the employee."""
    result = await service.calculate_ff_settlement(org_id=org_id, employee_id=employee_id)
    return _ok(result)


@router.post(
    "/employees/{employee_id}/settlement-approve",
    summary="Approve F&F Settlement",
    dependencies=[Depends(require_permission(_SETTLEMENT, A.EDIT))],
)
async def approve_ff_settlement(
    employee_id: int,
    service: SettlementServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Record administrative approval of the Full & Final Settlement preview."""
    result = await service.approve_ff_settlement(
        org_id=org_id, employee_id=employee_id, user_id=current_user.user_id
    )
    return _ok(result, "F&F Settlement approved successfully.")


@router.post(
    "/employees/{employee_id}/settlement-finalize",
    summary="Finalize F&F Settlement",
    dependencies=[Depends(require_permission(_SETTLEMENT, A.EDIT))],
)
async def finalize_ff_settlement(
    employee_id: int,
    service: SettlementServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Process and finalize Full & Final Settlement, clearing all outstanding balances."""
    result = await service.finalize_ff_settlement(
        org_id=org_id, employee_id=employee_id, user_id=current_user.user_id
    )
    return _ok(result, "F&F Settlement finalized successfully.")
