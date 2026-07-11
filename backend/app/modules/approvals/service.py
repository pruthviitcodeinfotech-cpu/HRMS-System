"""Approval Management — service layer (business logic & orchestration).

Implements the business logic of the Approval Management API Contract.
All database access is performed strictly via repositories.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions.base import AppException, ConflictException, NotFoundException
from app.modules.approvals.constants import ApprovalStatus, RequestType
from app.modules.approvals.exceptions import (
    ApprovalAlreadyDecidedException,
    ApprovalForbiddenScopeException,
    ApprovalNotFoundException,
    RejectRemarksRequiredException,
    SelfApprovalNotAllowedException,
)
from app.modules.approvals.models import (
    ApprovalRequest,
)
from app.modules.approvals.repository import (
    ApprovalRequestRepository,
    AttendanceRegularizationRequestRepository,
    LoginResetRequestRepository,
)
from app.modules.audit.constants import ActionType
from app.modules.audit.service import AuditService
from app.modules.employee.models.employee import Employee
from app.modules.employee.repository import EmployeeRepository
from app.modules.leave.constants import LeaveRequestStatus
from app.modules.leave.repository import (
    EmployeeLeaveBalanceRepository,
    LeaveRequestRepository,
    LeaveSettingRepository,
)
from app.modules.notifications.constants import NotificationType
from app.modules.rbac.repository import UserRepository
from app.shared.base.service import BaseService
from app.shared.schemas.pagination import PaginatedResponse
from app.shared.utils.datetime import utcnow

if TYPE_CHECKING:
    from app.modules.notifications.service import NotificationService


class ApprovalService(BaseService):
    """Business rules engine for single-level polymorphic approval requests."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)
        # Approval module repositories
        self.approvals = ApprovalRequestRepository(session)
        self.attendance_regularizations = AttendanceRegularizationRequestRepository(session)
        self.login_resets = LoginResetRequestRepository(session)

        # Cross-module referenced repositories
        self.employees = EmployeeRepository(session)
        self.users = UserRepository(session)
        self.leave_requests = LeaveRequestRepository(session)
        self.leave_balances = EmployeeLeaveBalanceRepository(session)
        self.leave_settings = LeaveSettingRepository(session)

        # Audit Logger
        self.audit = AuditService(session)

        # Cross-module notifier (constructed lazily — see _get_notifier).
        self.notifications: NotificationService | None = None

    # --- Helpers & Validations -----------------------------------------------

    def _get_notifier(self) -> NotificationService:
        """Return the notifications service, importing lazily to avoid module-level coupling."""
        if self.notifications is None:
            from app.modules.notifications.service import NotificationService

            self.notifications = NotificationService(self.session)
        return self.notifications

    async def _notify_requester_decision(
        self, org_id: int, approval: ApprovalRequest, reviewer_id: int, decision: str
    ) -> None:
        """Notify the subject employee's linked user about the decision on their request.

        Runs inside the caller's transaction so the notification commits atomically
        with the decision. Employees without a linked user account are skipped
        silently — a missing recipient must never block the approval itself.
        """
        notifier = self._get_notifier()
        recipient_ids = await notifier.resolve_user_ids_for_employees(
            org_id, [approval.employee_id]
        )
        if not recipient_ids:
            return

        request_label = str(approval.request_type).replace("_", " ")
        await notifier.emit_system_notification(
            org_id,
            recipient_user_ids=recipient_ids,
            title=f"Request {decision.capitalize()}",
            message=f"Your {request_label} request was {decision}.",
            notification_type=NotificationType.APPROVAL.value,
            source_module="approvals",
            source_entity_type="approval_request",
            source_entity_id=approval.id,
            created_by=reviewer_id,
        )

    async def _validate_employee(self, org_id: int, employee_id: int) -> Employee:
        """Validate employee existence and active status in organization context."""
        employee = await self.employees.get_active_by_id(employee_id, org_id)
        if not employee:
            raise NotFoundException("Employee not found or is out of organization context.")
        return employee

    async def _check_self_approval(self, approval_employee_id: int, reviewer_id: int) -> None:
        """Raise SelfApprovalNotAllowedException on a reviewer deciding their own request."""
        reviewer_user = await self.users.get_by_id(reviewer_id)
        if reviewer_user and reviewer_user.employee_id == approval_employee_id:
            raise SelfApprovalNotAllowedException()

    def get_cycle_year(self, start_date: date, leave_cycle: str, start_month: int) -> int:
        """Compute target cycle year for a date based on cycle configurations."""
        if leave_cycle == "financial_year":
            if start_date.month >= start_month:
                return start_date.year
            else:
                return start_date.year - 1
        return start_date.year

    # --- Read Operations -----------------------------------------------------

    async def list_pending_approvals(
        self,
        org_id: int,
        *,
        branch_id: int | None = None,
        dept_id: int | None = None,
        page: int = 1,
        page_size: int = 25,
    ) -> PaginatedResponse[ApprovalRequest]:
        """List and paginate pending approvals within the caller's permission and data scope."""
        items = await self.approvals.search(
            org_id,
            status=ApprovalStatus.PENDING,
            branch_id=branch_id,
            dept_id=dept_id,
            page=page,
            page_size=page_size,
        )
        total = await self.approvals.search_count(
            org_id,
            status=ApprovalStatus.PENDING,
            branch_id=branch_id,
            dept_id=dept_id,
        )
        return self.paginate(items, page=page, page_size=page_size, total_records=total)

    async def get_approval_history(
        self,
        org_id: int,
        *,
        branch_id: int | None = None,
        dept_id: int | None = None,
        request_type: RequestType | None = None,
        employee_id: int | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        page: int = 1,
        page_size: int = 25,
    ) -> PaginatedResponse[ApprovalRequest]:
        """List and paginate decided (approved/rejected) approvals matching filter criteria."""
        decided_statuses = [ApprovalStatus.APPROVED, ApprovalStatus.REJECTED]
        items = await self.approvals.search(
            org_id,
            status=decided_statuses,
            request_type=request_type,
            employee_id=employee_id,
            date_from=date_from,
            date_to=date_to,
            branch_id=branch_id,
            dept_id=dept_id,
            page=page,
            page_size=page_size,
        )
        total = await self.approvals.search_count(
            org_id,
            status=decided_statuses,
            request_type=request_type,
            employee_id=employee_id,
            date_from=date_from,
            date_to=date_to,
            branch_id=branch_id,
            dept_id=dept_id,
        )
        return self.paginate(items, page=page, page_size=page_size, total_records=total)

    async def get_approval_details(self, org_id: int, approval_id: int) -> dict[str, Any]:
        """Retrieve approval request envelope and its polymorphic source record details."""
        approval = await self.approvals.get_by_id_in_org(org_id, approval_id)
        if not approval:
            raise ApprovalNotFoundException()

        source_record = await self.approvals.get_source_record(
            approval.request_type, approval.reference_id
        )
        return {
            "approval": approval,
            "source": source_record,
        }

    async def get_approval_status(self, org_id: int, approval_id: int) -> dict[str, Any]:
        """Retrieve the current approval status details (status, reviewed_by, reviewed_at,
        reject_remarks)."""
        approval = await self.approvals.get_by_id_in_org(org_id, approval_id)
        if not approval:
            raise ApprovalNotFoundException()

        return {
            "status": approval.status,
            "reviewed_by": approval.reviewed_by,
            "reviewed_at": approval.reviewed_at,
            "reject_remarks": approval.reject_remarks,
        }

    async def get_approval_timeline(self, org_id: int, approval_id: int) -> list[dict[str, Any]]:
        """Retrieve the action timeline for a single-level request."""
        approval = await self.approvals.get_by_id_in_org(org_id, approval_id)
        if not approval:
            raise ApprovalNotFoundException()

        timeline = [
            {
                "event": "requested",
                "at": approval.requested_at,
                "by": approval.employee_id,
                "remarks": None,
            }
        ]

        if approval.status != ApprovalStatus.PENDING.value:
            timeline.append({
                "event": approval.status,
                "at": approval.reviewed_at,
                "by": approval.reviewed_by,
                "remarks": approval.reject_remarks,
            })

        return timeline

    # --- Dashboard aggregates -----------------------------------------------

    async def get_pending_approval_count(
        self,
        org_id: int,
        *,
        branch_id: int | None = None,
        dept_id: int | None = None,
    ) -> dict[str, Any]:
        """Get total pending counts and type-specific breakdown scoped by permissions."""
        counts = await self.approvals.get_pending_counts_by_type(
            org_id, branch_id=branch_id, dept_id=dept_id
        )
        total_pending = sum(counts.values())
        return {
            "pending_count": total_pending,
            "by_request_type": counts,
        }

    async def get_my_pending_approvals(
        self,
        org_id: int,
        *,
        branch_id: int | None = None,
        dept_id: int | None = None,
        page: int = 1,
        page_size: int = 25,
    ) -> PaginatedResponse[ApprovalRequest]:
        """Helper to get pending requests permitted to the caller (scope based)."""
        return await self.list_pending_approvals(
            org_id, branch_id=branch_id, dept_id=dept_id, page=page, page_size=page_size
        )

    async def get_recent_decisions(
        self,
        org_id: int,
        decision: ApprovalStatus,
        *,
        request_type: RequestType | None = None,
        branch_id: int | None = None,
        dept_id: int | None = None,
        limit: int = 10,
    ) -> list[ApprovalRequest]:
        """Fetch recently decided approval requests scoped by org and data scope."""
        return await self.approvals.get_recent_decisions(
            org_id,
            decision=decision,
            request_type=request_type,
            branch_id=branch_id,
            dept_id=dept_id,
            limit=limit,
        )

    # --- Decision Actions & Propagation -------------------------------------

    async def approve_request(
        self,
        org_id: int,
        approval_id: int,
        reviewer_id: int,
        remarks: str | None = None,
        branch_id: int | None = None,
        dept_id: int | None = None,
    ) -> ApprovalRequest:
        """Approve a pending request, performing validation and source module orchestration."""
        approval = await self.approvals.get_by_id_in_org(org_id, approval_id)
        if not approval:
            raise ApprovalNotFoundException()

        if approval.status != ApprovalStatus.PENDING.value:
            raise ApprovalAlreadyDecidedException()

        # Enforce branch/department data scope
        employee = await self._validate_employee(org_id, approval.employee_id)
        if branch_id is not None and employee.master_branch_id != branch_id:
            raise ApprovalForbiddenScopeException()
        if dept_id is not None and employee.dept_id != dept_id:
            raise ApprovalForbiddenScopeException()

        # Enforce no self-approval rule
        await self._check_self_approval(approval.employee_id, reviewer_id)

        async with self.transaction():
            if approval.request_type == RequestType.ATTENDANCE.value:
                # Orchestrate Attendance regularization correction in attendance module
                from app.modules.attendance.schemas import AttendanceCorrectionApproveRequest
                from app.modules.attendance.service import AttendanceService
                
                attendance_service = AttendanceService(self.session)
                await attendance_service.approve_correction(
                    org_id=org_id,
                    actor_id=reviewer_id,
                    request_id=approval_id,
                    data=AttendanceCorrectionApproveRequest(
                        decision=ApprovalStatus.APPROVED,
                        comment=remarks,
                    ),
                )

            elif approval.request_type == RequestType.LEAVE.value:
                leave_req = await self.leave_requests.get_by_id(approval.reference_id)
                if not leave_req:
                    raise NotFoundException("Leave request details not found.")

                await self.leave_requests.update(
                    leave_req,
                    {
                        "status": LeaveRequestStatus.APPROVED.value,
                        "reviewed_by": reviewer_id,
                        "reviewed_at": utcnow(),
                    },
                )

                # Deduct employee leave balance
                settings = await self.leave_settings.get_by_org_id(org_id)
                leave_cycle = settings.leave_cycle if settings else "calendar_year"
                start_month = settings.cycle_start_month if settings else 1
                cycle_year = self.get_cycle_year(leave_req.start_date, leave_cycle, start_month)

                balance = await self.leave_balances.get_by_employee_type_year(
                    employee_id=approval.employee_id,
                    leave_type_id=leave_req.leave_type_id,
                    cycle_year=cycle_year,
                )
                if not balance:
                    raise ConflictException("Employee leave balance not found for the cycle year.")

                if balance.closing_balance < leave_req.duration_days:
                    raise ConflictException("Insufficient leave balance.")

                await self.leave_balances.update(
                    balance,
                    {
                        "used": balance.used + leave_req.duration_days,
                        "closing_balance": balance.closing_balance - leave_req.duration_days,
                        "updated_by": reviewer_id,
                    },
                )

                # Update envelope
                await self.approvals.update(
                    approval,
                    {
                        "status": ApprovalStatus.APPROVED.value,
                        "reviewed_by": reviewer_id,
                        "reviewed_at": utcnow(),
                        "reject_remarks": remarks,
                    },
                )

            elif approval.request_type == RequestType.LOGIN_RESET.value:
                reset_req = await self.login_resets.get_by_id(approval.reference_id)
                if not reset_req:
                    raise NotFoundException("Login reset request details not found.")

                await self.login_resets.update(
                    reset_req,
                    {
                        "status": ApprovalStatus.APPROVED.value,
                        "reviewed_by": reviewer_id,
                        "reviewed_at": utcnow(),
                    },
                )

                # Update envelope
                await self.approvals.update(
                    approval,
                    {
                        "status": ApprovalStatus.APPROVED.value,
                        "reviewed_by": reviewer_id,
                        "reviewed_at": utcnow(),
                        "reject_remarks": remarks,
                    },
                )

            # Notify the subject employee's linked user (skipped when unlinked)
            await self._notify_requester_decision(
                org_id, approval, reviewer_id, ApprovalStatus.APPROVED.value
            )

            # Record audit logs
            await self.audit.record(
                org_id=org_id,
                module="approvals",
                sub_module=approval.request_type,
                action_type=ActionType.UPDATE,
                title="Approve Request",
                description=f"Approved {approval.request_type} request {approval_id} for employee "
                    f"{approval.employee_id}",
                performed_by_user_id=reviewer_id,
                performed_by_name=f"User {reviewer_id}",
                employee_id=approval.employee_id,
            )

        return approval

    async def reject_request(
        self,
        org_id: int,
        approval_id: int,
        reject_remarks: str,
        reviewer_id: int,
        branch_id: int | None = None,
        dept_id: int | None = None,
    ) -> ApprovalRequest:
        """Reject a pending request, performing validation and source module orchestration."""
        if not reject_remarks or not reject_remarks.strip():
            raise RejectRemarksRequiredException()

        approval = await self.approvals.get_by_id_in_org(org_id, approval_id)
        if not approval:
            raise ApprovalNotFoundException()

        if approval.status != ApprovalStatus.PENDING.value:
            raise ApprovalAlreadyDecidedException()

        # Enforce branch/department data scope
        employee = await self._validate_employee(org_id, approval.employee_id)
        if branch_id is not None and employee.master_branch_id != branch_id:
            raise ApprovalForbiddenScopeException()
        if dept_id is not None and employee.dept_id != dept_id:
            raise ApprovalForbiddenScopeException()

        # Enforce no self-approval rule
        await self._check_self_approval(approval.employee_id, reviewer_id)

        async with self.transaction():
            if approval.request_type == RequestType.ATTENDANCE.value:
                # Orchestrate Attendance regularization correction in attendance module
                from app.modules.attendance.schemas import AttendanceCorrectionApproveRequest
                from app.modules.attendance.service import AttendanceService
                
                attendance_service = AttendanceService(session=self.session)
                await attendance_service.approve_correction(
                    org_id=org_id,
                    actor_id=reviewer_id,
                    request_id=approval_id,
                    data=AttendanceCorrectionApproveRequest(
                        decision=ApprovalStatus.REJECTED,
                        comment=reject_remarks,
                    ),
                )

            elif approval.request_type == RequestType.LEAVE.value:
                leave_req = await self.leave_requests.get_by_id(approval.reference_id)
                if not leave_req:
                    raise NotFoundException("Leave request details not found.")

                await self.leave_requests.update(
                    leave_req,
                    {
                        "status": LeaveRequestStatus.REJECTED.value,
                        "reviewed_by": reviewer_id,
                        "reviewed_at": utcnow(),
                        "rejection_reason": reject_remarks,
                    },
                )

                # Update envelope
                await self.approvals.update(
                    approval,
                    {
                        "status": ApprovalStatus.REJECTED.value,
                        "reviewed_by": reviewer_id,
                        "reviewed_at": utcnow(),
                        "reject_remarks": reject_remarks,
                    },
                )

            elif approval.request_type == RequestType.LOGIN_RESET.value:
                reset_req = await self.login_resets.get_by_id(approval.reference_id)
                if not reset_req:
                    raise NotFoundException("Login reset request details not found.")

                await self.login_resets.update(
                    reset_req,
                    {
                        "status": ApprovalStatus.REJECTED.value,
                        "reviewed_by": reviewer_id,
                        "reviewed_at": utcnow(),
                        "reject_remarks": reject_remarks,
                    },
                )

                # Update envelope
                await self.approvals.update(
                    approval,
                    {
                        "status": ApprovalStatus.REJECTED.value,
                        "reviewed_by": reviewer_id,
                        "reviewed_at": utcnow(),
                        "reject_remarks": reject_remarks,
                    },
                )

            # Notify the subject employee's linked user (skipped when unlinked)
            await self._notify_requester_decision(
                org_id, approval, reviewer_id, ApprovalStatus.REJECTED.value
            )

            # Record audit logs
            await self.audit.record(
                org_id=org_id,
                module="approvals",
                sub_module=approval.request_type,
                action_type=ActionType.UPDATE,
                title="Reject Request",
                description=f"Rejected {approval.request_type} request {approval_id} for employee "
                    f"{approval.employee_id}",
                performed_by_user_id=reviewer_id,
                performed_by_name=f"User {reviewer_id}",
                employee_id=approval.employee_id,
            )

        return approval

    async def bulk_approve(
        self,
        org_id: int,
        approval_ids: list[int],
        reviewer_id: int,
        branch_id: int | None = None,
        dept_id: int | None = None,
    ) -> list[dict[str, Any]]:
        """Approve multiple pending requests in bulk, returning success/failure results per item."""
        results = []
        for approval_id in approval_ids:
            try:
                # Use a nested transaction savepoint to isolate this item's changes
                async with self.session.begin_nested():
                    await self.approve_request(
                        org_id=org_id,
                        approval_id=approval_id,
                        reviewer_id=reviewer_id,
                        branch_id=branch_id,
                        dept_id=dept_id,
                    )
                results.append({"id": approval_id, "success": True, "error": None})
            except AppException as e:
                results.append({
                    "id": approval_id,
                    "success": False,
                    "error": {"code": e.code, "message": e.message},
                })
            except Exception as e:
                results.append({
                    "id": approval_id,
                    "success": False,
                    "error": {"code": "SYSTEM_ERROR", "message": str(e)},
                })

        await self.commit()
        return results

    async def bulk_reject(
        self,
        org_id: int,
        approval_ids: list[int],
        reject_remarks: str,
        reviewer_id: int,
        branch_id: int | None = None,
        dept_id: int | None = None,
    ) -> list[dict[str, Any]]:
        """Reject multiple pending requests in bulk, returning success/failure results per item."""
        if not reject_remarks or not reject_remarks.strip():
            raise RejectRemarksRequiredException()

        results = []
        for approval_id in approval_ids:
            try:
                # Use a nested transaction savepoint to isolate this item's changes
                async with self.session.begin_nested():
                    await self.reject_request(
                        org_id=org_id,
                        approval_id=approval_id,
                        reject_remarks=reject_remarks,
                        reviewer_id=reviewer_id,
                        branch_id=branch_id,
                        dept_id=dept_id,
                    )
                results.append({"id": approval_id, "success": True, "error": None})
            except AppException as e:
                results.append({
                    "id": approval_id,
                    "success": False,
                    "error": {"code": e.code, "message": e.message},
                })
            except Exception as e:
                results.append({
                    "id": approval_id,
                    "success": False,
                    "error": {"code": "SYSTEM_ERROR", "message": str(e)},
                })

        await self.commit()
        return results

    # --- Cancellation & Submissions ------------------------------------------

    async def cancel_approval_request(self, org_id: int, approval_id: int, user_id: int) -> None:
        """Cancel a pending approval request (hard-deletes the approval envelope and source
        records)."""
        approval = await self.approvals.get_by_id_in_org(org_id, approval_id)
        if not approval:
            raise ApprovalNotFoundException()

        if approval.status != ApprovalStatus.PENDING.value:
            raise ApprovalAlreadyDecidedException()

        async with self.transaction():
            if approval.request_type == RequestType.ATTENDANCE.value:
                reg_req = await self.attendance_regularizations.get_by_id(approval.reference_id)
                if reg_req:
                    await self.attendance_regularizations.delete(reg_req)
            elif approval.request_type == RequestType.LEAVE.value:
                leave_req = await self.leave_requests.get_by_id(approval.reference_id)
                if leave_req:
                    await self.leave_requests.delete(leave_req)
            elif approval.request_type == RequestType.LOGIN_RESET.value:
                reset_req = await self.login_resets.get_by_id(approval.reference_id)
                if reset_req:
                    await self.login_resets.delete(reset_req)

            await self.approvals.delete(approval)

            # Record audit logs
            await self.audit.record(
                org_id=org_id,
                module="approvals",
                sub_module=approval.request_type,
                action_type=ActionType.DELETE,
                title="Cancel Approval Request",
                description=f"Cancelled pending {approval.request_type} request {approval_id} for "
                    f"employee {approval.employee_id}",
                performed_by_user_id=user_id,
                performed_by_name=f"User {user_id}",
                employee_id=approval.employee_id,
            )

    async def submit_approval_request(
        self,
        org_id: int,
        request_type: str | RequestType,
        reference_id: int,
        employee_id: int,
        created_by: int,
        request_subtype: str | None = None,
    ) -> ApprovalRequest:
        """Submit a generic/custom approval request envelope (raised by other business modules)."""
        # Validate employee
        await self._validate_employee(org_id, employee_id)

        type_val = request_type.value if isinstance(request_type, RequestType) else request_type

        # Verify target source record exists
        source_record = await self.approvals.get_source_record(type_val, reference_id)
        if not source_record:
            raise NotFoundException(f"Polymorphic source record not found for type {type_val} and "
                f"ID {reference_id}.")

        async with self.transaction():
            approval = await self.approvals.create({
                "org_id": org_id,
                "request_type": type_val,
                "request_subtype": request_subtype,
                "reference_id": reference_id,
                "employee_id": employee_id,
                "status": ApprovalStatus.PENDING.value,
            })

            # Record audit
            await self.audit.record(
                org_id=org_id,
                module="approvals",
                sub_module=type_val,
                action_type=ActionType.INSERT,
                title="Approval Requested",
                description=f"Submitted approval envelope for request type {type_val} and ID "
                    f"{reference_id}",
                performed_by_user_id=created_by,
                performed_by_name=f"User {created_by}",
                employee_id=employee_id,
            )

        return approval

    async def submit_attendance_regularization(
        self,
        org_id: int,
        employee_id: int,
        attendance_date: date,
        requested_in: datetime,
        requested_out: datetime,
        reason: str | None,
        actor_id: int,
    ) -> ApprovalRequest:
        """Submit a new attendance regularization correction and create the approval envelope."""
        # 1. Validate employee
        await self._validate_employee(org_id, employee_id)

        # 2. Check for duplicate pending request
        exists = await self.attendance_regularizations.has_pending_request(
            employee_id, attendance_date
        )
        if exists:
            raise ConflictException("A pending regularization request already exists for this "
                "date.")

        # Build original punch time format representation from existing punches if any
        from app.modules.attendance.models import AttendanceDay
        stmt = select(AttendanceDay).where(
            AttendanceDay.employee_id == employee_id,
            AttendanceDay.org_id == org_id,
            AttendanceDay.attendance_date == attendance_date,
        )
        day = (await self.session.execute(stmt.limit(1))).scalar_one_or_none()
        
        old_time_str = "None"
        if day and day.first_punch_in and day.last_punch_out:
            old_time_str = (
                f"{day.first_punch_in.strftime('%H:%M')} - "
                f"{day.last_punch_out.strftime('%H:%M')}"
            )

        new_time_str = f"{requested_in.strftime('%H:%M')} - {requested_out.strftime('%H:%M')}"

        async with self.transaction():
            # Create AttendanceRegularizationRequest
            reg_req = await self.attendance_regularizations.create({
                "employee_id": employee_id,
                "attendance_date": attendance_date,
                "old_punch_time": old_time_str,
                "new_punch_time": new_time_str,
                "employee_reason": reason,
                "status": ApprovalStatus.PENDING.value,
            })

            # Create polymorphic ApprovalRequest
            approval = await self.approvals.create({
                "org_id": org_id,
                "request_type": RequestType.ATTENDANCE.value,
                "reference_id": reg_req.id,
                "employee_id": employee_id,
                "status": ApprovalStatus.PENDING.value,
            })

            # Record audit
            await self.audit.record(
                org_id=org_id,
                module="approvals",
                sub_module=RequestType.ATTENDANCE.value,
                action_type=ActionType.INSERT,
                title="Regularization Requested",
                description=f"Requested correction for {attendance_date} to {new_time_str}",
                performed_by_user_id=actor_id,
                performed_by_name=f"User {actor_id}",
                employee_id=employee_id,
            )

        return approval

    async def submit_login_reset_request(
        self,
        org_id: int,
        employee_id: int,
        request_subtype: str | None,
        request_description: str,
        created_by: int,
    ) -> ApprovalRequest:
        """Submit a new login credentials reset request and create the approval envelope."""
        # 1. Validate employee
        await self._validate_employee(org_id, employee_id)

        # 2. Check for duplicate pending request
        exists = await self.login_resets.has_pending_request(employee_id)
        if exists:
            raise ConflictException("A pending login reset request already exists.")

        async with self.transaction():
            # Create LoginResetRequest
            reset_req = await self.login_resets.create({
                "employee_id": employee_id,
                "request_subtype": request_subtype,
                "request_description": request_description,
                "status": ApprovalStatus.PENDING.value,
            })

            # Create polymorphic ApprovalRequest
            approval = await self.approvals.create({
                "org_id": org_id,
                "request_type": RequestType.LOGIN_RESET.value,
                "request_subtype": request_subtype,
                "reference_id": reset_req.id,
                "employee_id": employee_id,
                "status": ApprovalStatus.PENDING.value,
            })

            # Record audit
            await self.audit.record(
                org_id=org_id,
                module="approvals",
                sub_module=RequestType.LOGIN_RESET.value,
                action_type=ActionType.INSERT,
                title="Login Reset Requested",
                description=f"Requested login credentials reset: {request_description}",
                performed_by_user_id=created_by,
                performed_by_name=f"User {created_by}",
                employee_id=employee_id,
            )

        return approval
