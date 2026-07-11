"""Leave -> Approval integration.

Applying for leave must enrol the request into the approval workflow. Before Phase 2
``LeaveService.apply_leave`` created a pending ``LeaveRequest`` and stopped, and nothing
ever called ``ApprovalService.submit_approval_request``. The approval side's LEAVE branch
could therefore never fire and leave requests stayed pending forever.

These tests pin the seam: applying creates the ``ApprovalRequest`` envelope with
``request_type='leave'`` and ``reference_id=<leave request id>``, and no envelope is
created when the application is rejected by a business rule.

The approving half of the chain (envelope -> LeaveRequest.approved + balance deduction)
is covered by ``test_approval_service.py::test_approve_leave_request_success``.
"""

from __future__ import annotations

import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.exceptions.base import ValidationException
from app.modules.approvals.constants import RequestType
from app.modules.leave.exceptions import (
    InsufficientBalanceException,
    LeaveOverlapException,
)
from app.modules.leave.service import LeaveService

_ORG = 10
_EMPLOYEE = 42
_ACTOR = 101


def _payload(**overrides: object) -> dict:
    base: dict = {
        "employee_id": _EMPLOYEE,
        "leave_type_id": 3,
        "start_date": datetime.date(2026, 3, 2),
        "end_date": datetime.date(2026, 3, 4),
        "duration_days": 3,
        "reason": "Family function",
    }
    base.update(overrides)
    return base


@pytest.fixture
def leave_service() -> LeaveService:
    svc = LeaveService(AsyncMock())
    svc.session.add = MagicMock()

    # The employee lookup in _validate_employee goes straight through session.execute.
    employee = SimpleNamespace(employee_id=_EMPLOYEE, org_id=_ORG, employee_name="Alice")
    result = MagicMock()
    result.scalar_one_or_none.return_value = employee
    svc.session.execute = AsyncMock(return_value=result)

    for attr in (
        "leave_types",
        "settings",
        "balances",
        "adjustments",
        "allocations",
        "requests",
        "templates",
        "assignments",
        "items",
        "audit",
    ):
        setattr(svc, attr, AsyncMock())

    svc.leave_types.get_by_id_in_org.return_value = SimpleNamespace(
        id=3, name="Casual Leave", alias="CL", is_active=True
    )
    svc.settings.get_by_org_id.return_value = SimpleNamespace(
        leave_cycle="calendar_year", cycle_start_month=1
    )
    svc.requests.has_overlap.return_value = False
    svc.balances.get_by_employee_type_year.return_value = SimpleNamespace(closing_balance=10.0)
    svc.requests.create.return_value = SimpleNamespace(id=777, employee_id=_EMPLOYEE)
    return svc


async def test_apply_leave_creates_approval_envelope(leave_service: LeaveService) -> None:
    """The core Phase 2 integration: applying enrols the request into Approvals."""
    approvals = AsyncMock()
    with patch("app.modules.approvals.service.ApprovalService", return_value=approvals):
        request = await leave_service.apply_leave(_ORG, _payload(), applied_by=_ACTOR)

    assert request.id == 777
    leave_service.requests.create.assert_awaited_once()

    approvals.submit_approval_request.assert_awaited_once()
    kwargs = approvals.submit_approval_request.await_args.kwargs
    assert kwargs["org_id"] == _ORG
    assert kwargs["request_type"] is RequestType.LEAVE
    assert kwargs["reference_id"] == 777  # the just-created leave request
    assert kwargs["employee_id"] == _EMPLOYEE
    assert kwargs["created_by"] == _ACTOR

    # The leave application itself is audited.
    leave_service.audit.record.assert_awaited_once()


async def test_apply_leave_rejected_creates_no_envelope(leave_service: LeaveService) -> None:
    """An overlapping application must not leave an orphan approval envelope behind."""
    leave_service.requests.has_overlap.return_value = True
    approvals = AsyncMock()

    with patch("app.modules.approvals.service.ApprovalService", return_value=approvals):
        with pytest.raises(LeaveOverlapException):
            await leave_service.apply_leave(_ORG, _payload(), applied_by=_ACTOR)

    leave_service.requests.create.assert_not_awaited()
    approvals.submit_approval_request.assert_not_awaited()


async def test_apply_leave_insufficient_balance_creates_no_envelope(
    leave_service: LeaveService,
) -> None:
    leave_service.balances.get_by_employee_type_year.return_value = SimpleNamespace(
        closing_balance=1.0
    )
    approvals = AsyncMock()

    with patch("app.modules.approvals.service.ApprovalService", return_value=approvals):
        with pytest.raises(InsufficientBalanceException):
            await leave_service.apply_leave(_ORG, _payload(), applied_by=_ACTOR)

    leave_service.requests.create.assert_not_awaited()
    approvals.submit_approval_request.assert_not_awaited()


async def test_apply_leave_without_employee_id_is_a_validation_error(
    leave_service: LeaveService,
) -> None:
    """A caller with no linked employee gets a 422, not an unhandled ValueError -> 500."""
    with pytest.raises(ValidationException) as exc:
        await leave_service.apply_leave(_ORG, _payload(employee_id=None), applied_by=_ACTOR)
    assert exc.value.code == "EMPLOYEE_ID_REQUIRED"
    assert exc.value.status_code == 422
