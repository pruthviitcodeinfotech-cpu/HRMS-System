"""Unit tests for ``ApprovalService`` business logic (repositories mocked).

Covers approval CRUD, pending list, history, details, status, timeline,
dashboard aggregates, decision propagation (leave, attendance, login reset),
bulk actions, cancellations, submissions, data scope, and error handling.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.core.exceptions.base import ConflictException, NotFoundException
from app.modules.approvals.constants import ApprovalStatus, RequestType
from app.modules.approvals.exceptions import (
    ApprovalAlreadyDecidedException,
    ApprovalForbiddenScopeException,
    ApprovalNotFoundException,
    RejectRemarksRequiredException,
    SelfApprovalNotAllowedException,
)
from app.modules.approvals.schemas import (
    ApprovalDetailsSchema,
    ApprovalStatusSchema,
    ApprovalTimelineEventSchema,
)

_NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------


def _approval(**overrides: object) -> SimpleNamespace:
    base: dict[str, object] = {
        "id": 1,
        "org_id": 1,
        "request_type": "leave",
        "request_subtype": "annual",
        "reference_id": 100,
        "employee_id": 5,
        "status": "pending",
        "requested_at": _NOW,
        "reviewed_at": None,
        "reviewed_by": None,
        "reject_remarks": None,
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def _employee(**overrides: object) -> SimpleNamespace:
    base: dict[str, object] = {
        "employee_id": 5,
        "org_id": 1,
        "employee_name": "John Doe",
        "master_branch_id": 10,
        "dept_id": 20,
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def _user(**overrides: object) -> SimpleNamespace:
    base: dict[str, object] = {
        "id": 9,
        "employee_id": 6,
        "org_id": 1,
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def _leave_request(**overrides: object) -> SimpleNamespace:
    base: dict[str, object] = {
        "id": 100,
        "employee_id": 5,
        "leave_type_id": 1,
        "start_date": date(2026, 1, 1),
        "duration_days": 3,
        "status": "pending",
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def _leave_balance(**overrides: object) -> SimpleNamespace:
    base: dict[str, object] = {
        "id": 1,
        "employee_id": 5,
        "leave_type_id": 1,
        "cycle_year": 2026,
        "used": 0,
        "closing_balance": 10,
    }
    base.update(overrides)
    return SimpleNamespace(**base)


# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------


@pytest.fixture
def approval_service():
    """A real :class:`ApprovalService` with every repository replaced by an ``AsyncMock``."""
    from app.modules.approvals.service import ApprovalService

    svc = ApprovalService(AsyncMock())
    for attr in (
        "approvals",
        "attendance_regularizations",
        "login_resets",
        "employees",
        "users",
        "leave_requests",
        "leave_balances",
        "leave_settings",
        "audit",
    ):
        setattr(svc, attr, AsyncMock())

    # Set up some sensible default returns
    svc.approvals.get_by_id_in_org.return_value = _approval()
    svc.approvals.get_source_record.return_value = SimpleNamespace(id=100)
    svc.approvals.search.return_value = []
    svc.approvals.search_count.return_value = 0
    svc.approvals.get_pending_counts_by_type.return_value = {"leave": 1}
    svc.approvals.get_recent_decisions.return_value = []
    svc.approvals.create.return_value = _approval()
    svc.approvals.update.return_value = _approval()

    svc.employees.get_active_by_id.return_value = _employee()
    svc.users.get_by_id.return_value = _user()
    
    svc.leave_requests.get_by_id.return_value = _leave_request()
    svc.leave_requests.update.return_value = _leave_request()
    svc.leave_balances.get_by_employee_type_year.return_value = _leave_balance()
    svc.leave_balances.update.return_value = _leave_balance()
    svc.leave_settings.get_by_org_id.return_value = None

    svc.attendance_regularizations.create.return_value = SimpleNamespace(id=101)
    svc.attendance_regularizations.has_pending_request.return_value = False
    
    svc.login_resets.create.return_value = SimpleNamespace(id=102)
    svc.login_resets.has_pending_request.return_value = False

    return svc


# ===========================================================================
# 1. Read operations, searches & dashboards
# ===========================================================================


async def test_list_pending_approvals(approval_service) -> None:
    approval_service.approvals.search.return_value = [_approval()]
    approval_service.approvals.search_count.return_value = 1
    result = await approval_service.list_pending_approvals(
        org_id=1, branch_id=10, dept_id=20, page=1, page_size=25
    )
    assert result.pagination.total_records == 1
    assert len(result.items) == 1
    approval_service.approvals.search.assert_awaited_once_with(
        1,
        status=ApprovalStatus.PENDING,
        branch_id=10,
        dept_id=20,
        page=1,
        page_size=25,
    )


async def test_get_approval_history(approval_service) -> None:
    approval_service.approvals.search.return_value = [_approval(status="approved")]
    approval_service.approvals.search_count.return_value = 1
    result = await approval_service.get_approval_history(
        org_id=1, request_type=RequestType.LEAVE, page=1, page_size=25
    )
    assert result.pagination.total_records == 1
    assert result.items[0].status == "approved"


async def test_get_approval_details_success(approval_service) -> None:
    result = await approval_service.get_approval_details(org_id=1, approval_id=1)
    assert result["approval"].id == 1
    assert result["source"].id == 100


async def test_get_approval_details_not_found(approval_service) -> None:
    approval_service.approvals.get_by_id_in_org.return_value = None
    with pytest.raises(ApprovalNotFoundException):
        await approval_service.get_approval_details(org_id=1, approval_id=404)


async def test_get_approval_status(approval_service) -> None:
    result = await approval_service.get_approval_status(org_id=1, approval_id=1)
    assert result["status"] == "pending"


async def test_get_approval_timeline_pending(approval_service) -> None:
    result = await approval_service.get_approval_timeline(org_id=1, approval_id=1)
    assert len(result) == 1
    assert result[0]["event"] == "requested"


async def test_get_approval_timeline_decided(approval_service) -> None:
    approval_service.approvals.get_by_id_in_org.return_value = _approval(
        status="approved", reviewed_by=9, reviewed_at=_NOW
    )
    result = await approval_service.get_approval_timeline(org_id=1, approval_id=1)
    assert len(result) == 2
    assert result[0]["event"] == "requested"
    assert result[1]["event"] == "approved"


async def test_get_pending_approval_count(approval_service) -> None:
    result = await approval_service.get_pending_approval_count(org_id=1)
    assert result["pending_count"] == 1
    assert result["by_request_type"]["leave"] == 1


async def test_get_recent_decisions(approval_service) -> None:
    approval_service.approvals.get_recent_decisions.return_value = [_approval(status="approved")]
    result = await approval_service.get_recent_decisions(org_id=1, decision=ApprovalStatus.APPROVED)
    assert len(result) == 1
    assert result[0].status == "approved"


# ===========================================================================
# 2. Decision propagation (Approve)
# ===========================================================================


async def test_approve_leave_request_success(approval_service) -> None:
    result = await approval_service.approve_request(
        org_id=1, approval_id=1, reviewer_id=9, remarks="Looks good"
    )
    assert result.id == 1
    # Check leave request updated
    approval_service.leave_requests.update.assert_awaited_once()
    # Check leave balance deducted
    approval_service.leave_balances.update.assert_awaited_once()
    # Check audit log recorded
    approval_service.audit.record.assert_awaited_once()


async def test_approve_request_already_decided(approval_service) -> None:
    approval_service.approvals.get_by_id_in_org.return_value = _approval(status="approved")
    with pytest.raises(ApprovalAlreadyDecidedException):
        await approval_service.approve_request(org_id=1, approval_id=1, reviewer_id=9)


async def test_approve_request_self_approval(approval_service) -> None:
    # Reviewer's employee ID matches approval employee ID
    approval_service.users.get_by_id.return_value = _user(employee_id=5)
    with pytest.raises(SelfApprovalNotAllowedException):
        await approval_service.approve_request(org_id=1, approval_id=1, reviewer_id=9)


async def test_approve_request_forbidden_branch(approval_service) -> None:
    with pytest.raises(ApprovalForbiddenScopeException):
        await approval_service.approve_request(
            org_id=1, approval_id=1, reviewer_id=9, branch_id=999
        )


async def test_approve_request_forbidden_dept(approval_service) -> None:
    with pytest.raises(ApprovalForbiddenScopeException):
        await approval_service.approve_request(
            org_id=1, approval_id=1, reviewer_id=9, dept_id=999
        )


async def test_approve_leave_request_insufficient_balance(approval_service) -> None:
    # Leave request duration is 3, closing balance is 1
    approval_service.leave_balances.get_by_employee_type_year.return_value = _leave_balance(
        closing_balance=1
    )
    with pytest.raises(ConflictException) as exc:
        await approval_service.approve_request(org_id=1, approval_id=1, reviewer_id=9)
    assert "Insufficient leave balance" in exc.value.message


async def test_approve_attendance_regularization(approval_service) -> None:
    # Mock AttendanceService to verify routing
    from unittest.mock import patch
    approval_service.approvals.get_by_id_in_org.return_value = _approval(
        request_type=RequestType.ATTENDANCE.value
    )
    
    with patch("app.modules.attendance.service.AttendanceService.approve_correction") as mock_correction:
        await approval_service.approve_request(org_id=1, approval_id=1, reviewer_id=9)
        mock_correction.assert_awaited_once()


async def test_approve_login_reset(approval_service) -> None:
    approval_service.approvals.get_by_id_in_org.return_value = _approval(
        request_type=RequestType.LOGIN_RESET.value
    )
    result = await approval_service.approve_request(org_id=1, approval_id=1, reviewer_id=9)
    assert result.id == 1
    approval_service.login_resets.update.assert_awaited_once()


# ===========================================================================
# 3. Decision propagation (Reject)
# ===========================================================================


async def test_reject_request_success(approval_service) -> None:
    result = await approval_service.reject_request(
        org_id=1, approval_id=1, reject_remarks="Not allowed", reviewer_id=9
    )
    assert result.id == 1
    # Check leave request status updated to rejected
    approval_service.leave_requests.update.assert_awaited_once()
    # Reject does not deduct balance
    approval_service.leave_balances.update.assert_not_awaited()
    approval_service.audit.record.assert_awaited_once()


async def test_reject_request_missing_remarks(approval_service) -> None:
    with pytest.raises(RejectRemarksRequiredException):
        await approval_service.reject_request(
            org_id=1, approval_id=1, reject_remarks="", reviewer_id=9
        )


# ===========================================================================
# 4. Bulk decisions
# ===========================================================================


async def test_bulk_approve_success(approval_service) -> None:
    result = await approval_service.bulk_approve(
        org_id=1, approval_ids=[1, 2], reviewer_id=9
    )
    assert len(result) == 2
    assert result[0]["success"] is True
    assert result[1]["success"] is True


async def test_bulk_approve_with_partial_failure(approval_service) -> None:
    # Set get_by_id_in_org to return None for ID 2 (leads to ApprovalNotFoundException)
    def side_effect(org_id, approval_id):
        if approval_id == 2:
            return None
        return _approval(id=1)

    approval_service.approvals.get_by_id_in_org.side_effect = side_effect

    result = await approval_service.bulk_approve(
        org_id=1, approval_ids=[1, 2], reviewer_id=9
    )
    assert len(result) == 2
    assert result[0]["success"] is True
    assert result[1]["success"] is False
    assert result[1]["error"]["code"] == "APPROVAL_NOT_FOUND"


async def test_bulk_reject_success(approval_service) -> None:
    result = await approval_service.bulk_reject(
        org_id=1, approval_ids=[1, 2], reject_remarks="Bulk reject reason", reviewer_id=9
    )
    assert len(result) == 2
    assert result[0]["success"] is True
    assert result[1]["success"] is True


# ===========================================================================
# 5. Cancellations & Submissions
# ===========================================================================


async def test_cancel_approval_request_success(approval_service) -> None:
    await approval_service.cancel_approval_request(org_id=1, approval_id=1, user_id=9)
    approval_service.leave_requests.delete.assert_awaited_once()
    approval_service.approvals.delete.assert_awaited_once()


async def test_cancel_approval_request_already_decided(approval_service) -> None:
    approval_service.approvals.get_by_id_in_org.return_value = _approval(status="approved")
    with pytest.raises(ApprovalAlreadyDecidedException):
        await approval_service.cancel_approval_request(org_id=1, approval_id=1, user_id=9)


async def test_submit_approval_request_success(approval_service) -> None:
    result = await approval_service.submit_approval_request(
        org_id=1,
        request_type=RequestType.LEAVE,
        reference_id=100,
        employee_id=5,
        created_by=9,
    )
    assert result.id == 1
    approval_service.approvals.create.assert_awaited_once()


async def test_submit_attendance_regularization_duplicate(approval_service) -> None:
    approval_service.attendance_regularizations.has_pending_request.return_value = True
    with pytest.raises(ConflictException) as exc:
        await approval_service.submit_attendance_regularization(
            org_id=1,
            employee_id=5,
            attendance_date=date(2026, 1, 1),
            requested_in=datetime(2026, 1, 1, 9, 0),
            requested_out=datetime(2026, 1, 1, 18, 0),
            reason="Forgot to punch",
            actor_id=9,
        )
    assert "A pending regularization request already exists" in exc.value.message


async def test_submit_login_reset_request_duplicate(approval_service) -> None:
    approval_service.login_resets.has_pending_request.return_value = True
    with pytest.raises(ConflictException) as exc:
        await approval_service.submit_login_reset_request(
            org_id=1,
            employee_id=5,
            request_subtype="mobile_device",
            request_description="Reset device credentials",
            created_by=9,
        )
    assert "A pending login reset request already exists" in exc.value.message
