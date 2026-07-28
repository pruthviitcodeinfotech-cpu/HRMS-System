"""Unit tests for Enterprise Attendance Regularization Workflow."""

from __future__ import annotations

import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.exceptions.base import ConflictException
from app.modules.attendance.exceptions import AttendancePeriodLockedException
from app.modules.attendance.schemas import (
    AttendanceCorrectionApproveRequest,
    AttendanceCorrectionCategory,
    AttendanceCorrectionCreateRequest,
)
from app.modules.attendance.service import AttendanceService
from app.modules.approvals.constants import ApprovalStatus

_ORG_ID = 10
_USER_ID = 99
_EMPLOYEE_ID = 242
_DATE = datetime.date(2026, 7, 28)
_NOW = datetime.datetime(2026, 7, 28, 12, 0, 0, tzinfo=datetime.timezone.utc)


def _make_service() -> AttendanceService:
    session = AsyncMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    return AttendanceService(session)


@pytest.mark.asyncio
async def test_request_correction_with_category_and_sla() -> None:
    svc = _make_service()
    svc._require_regularization_enabled = AsyncMock()
    svc._validate_employee = AsyncMock(return_value=SimpleNamespace(employee_name="Pruthvi"))
    svc.days.get_by_employee_date = AsyncMock(
        return_value=SimpleNamespace(
            id=1,
            first_punch_in=datetime.datetime(2026, 7, 28, 9, 0, 0, tzinfo=datetime.timezone.utc),
            last_punch_out=None,
        )
    )
    svc.check_period_locked = AsyncMock()

    created_reg = SimpleNamespace(
        id=101,
        employee_id=_EMPLOYEE_ID,
        attendance_date=_DATE,
        old_punch_time="09:00 - None",
        new_punch_time="09:00 - 18:00",
        employee_reason="Forgot to punch out",
        category="forgot_to_punch",
        attachment_url="https://example.com/proof.pdf",
        requested_in=datetime.datetime(2026, 7, 28, 9, 0, 0, tzinfo=datetime.timezone.utc),
        requested_out=datetime.datetime(2026, 7, 28, 18, 0, 0, tzinfo=datetime.timezone.utc),
        sla_due_date=_NOW + datetime.timedelta(hours=48),
        applied_on=_NOW,
        status="pending",
        is_escalated=False,
        escalation_level=0,
        created_at=_NOW,
        updated_at=_NOW,
    )
    svc.regularization_requests.create = AsyncMock(return_value=created_reg)
    svc.approval_requests.create = AsyncMock()
    svc._audit = AsyncMock()

    payload = AttendanceCorrectionCreateRequest(
        employee_id=_EMPLOYEE_ID,
        date=_DATE,
        requested_in=datetime.datetime(2026, 7, 28, 9, 0, 0, tzinfo=datetime.timezone.utc),
        requested_out=datetime.datetime(2026, 7, 28, 18, 0, 0, tzinfo=datetime.timezone.utc),
        reason="Forgot to punch out",
        category=AttendanceCorrectionCategory.FORGOT_TO_PUNCH,
        attachment_url="https://example.com/proof.pdf",
    )

    res = await svc.request_correction(_ORG_ID, _USER_ID, payload)
    assert res.id == 101
    assert res.category == "forgot_to_punch"
    svc.regularization_requests.create.assert_called_once()
    svc.approval_requests.create.assert_called_once()


@pytest.mark.asyncio
async def test_approve_correction_invalidates_punches_and_recomputes() -> None:
    svc = _make_service()
    approval = SimpleNamespace(
        id=50,
        org_id=_ORG_ID,
        reference_id=101,
        status="pending",
    )
    reg_req = SimpleNamespace(
        id=101,
        employee_id=_EMPLOYEE_ID,
        attendance_date=_DATE,
        new_punch_time="09:00 - 18:00",
        category="missing_punch_out",
        status="pending",
        applied_on=_NOW,
        created_at=_NOW,
        updated_at=_NOW,
    )
    day = SimpleNamespace(
        id=1,
        org_id=_ORG_ID,
        employee_id=_EMPLOYEE_ID,
        attendance_date=_DATE,
        first_punch_in=datetime.datetime(2026, 7, 28, 9, 0, 0, tzinfo=datetime.timezone.utc),
        last_punch_out=None,
    )

    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = approval
    svc.session.execute = AsyncMock(return_value=mock_res)

    svc.regularization_requests.get_by_id = AsyncMock(return_value=reg_req)
    svc.check_period_locked = AsyncMock()
    svc._validate_employee = AsyncMock(return_value=SimpleNamespace(employee_name="Pruthvi"))
    svc.approval_requests.update = AsyncMock()
    svc.regularization_requests.update = AsyncMock()
    svc.days.get_by_employee_date = AsyncMock(return_value=day)
    svc.days.update = AsyncMock()

    old_punch = SimpleNamespace(id=5, is_valid=True)
    svc.punches.get_for_day = AsyncMock(return_value=[old_punch])
    svc.punches.update = AsyncMock()
    svc.punches.create = AsyncMock()
    svc._recompute_day_metrics = AsyncMock()
    svc._audit = AsyncMock()

    approve_payload = AttendanceCorrectionApproveRequest(
        decision=ApprovalStatus.APPROVED,
        comment="Verified with manager",
    )

    res = await svc.approve_correction(_ORG_ID, _USER_ID, 50, approve_payload)
    svc.punches.update.assert_called_once_with(old_punch, {"is_valid": False})
    assert svc.punches.create.call_count == 2
    svc._recompute_day_metrics.assert_called_once_with(_ORG_ID, day)


@pytest.mark.asyncio
async def test_cancel_correction_pending_request() -> None:
    svc = _make_service()
    approval = SimpleNamespace(
        id=50,
        org_id=_ORG_ID,
        reference_id=101,
        status="pending",
    )
    reg_req = SimpleNamespace(
        id=101,
        employee_id=_EMPLOYEE_ID,
        attendance_date=_DATE,
        new_punch_time="09:00 - 18:00",
        status="pending",
        applied_on=_NOW,
        created_at=_NOW,
        updated_at=_NOW,
    )
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = approval
    svc.session.execute = AsyncMock(return_value=mock_res)
    svc.regularization_requests.get_by_id = AsyncMock(return_value=reg_req)
    svc.approval_requests.update = AsyncMock()
    svc.regularization_requests.update = AsyncMock()
    svc._audit = AsyncMock()

    res = await svc.cancel_correction(_ORG_ID, _USER_ID, 50)
    svc.approval_requests.update.assert_called_once()
    svc.regularization_requests.update.assert_called_once()
