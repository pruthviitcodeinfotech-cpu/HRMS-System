"""Attendance Management — service layer (business logic & orchestration).

Implements the business logic of the Attendance Management API Contract (Section 11).
Integrates with Employee, Shift, approvals (regularization), and Audit services.
All database access is performed strictly via repositories.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions.base import ConflictException, NotFoundException, ValidationException
from app.modules.approvals.models import ApprovalRequest, AttendanceRegularizationRequest
from app.modules.attendance.constants import (
    ApprovalStatus,
    AttendanceDayStatus,
    AttendanceSource,
    PenaltyStatus,
    PenaltyType,
    PenaltyUnit,
    PunchSource,
    PunchType,
)
from app.modules.attendance.exceptions import (
    AttendanceDayExistsException,
    AttendanceDayNotFoundException,
    EmployeeNotFoundException,
    PenaltyAlreadyWaivedException,
    PenaltyNotFoundException,
    RegularizationDisabledException,
    ShiftNotFoundException,
)
from app.modules.attendance.models import AttendanceDay, AttendancePenalty
from app.modules.attendance.repository import (
    AttendanceDayRepository,
    AttendancePenaltyRepository,
    AttendancePunchRepository,
    EmployeeLookupRepository,
    ShiftLookupRepository,
)
from app.modules.attendance.schemas import (
    AttendanceCorrectionApproveRequest,
    AttendanceCorrectionCreateRequest,
    AttendanceCorrectionSchema,
    AttendanceDailyListResponse,
    AttendanceDailyQuery,
    AttendanceDailySchema,
    AttendanceDayDetailSchema,
    AttendanceLockRequest,
    AttendanceLogsQuery,
    AttendanceLogsResponse,
    AttendanceManualCreateRequest,
    AttendanceMissingPunchSchema,
    AttendanceMissingPunchesQuery,
    AttendanceMissingPunchesResponse,
    AttendanceMonthlyDaySchema,
    AttendancePenaltySchema,
    AttendancePunchSchema,
)
from app.modules.audit.constants import ActionType
from app.modules.audit.service import AuditService
from app.modules.employee.models.employee import Employee
from app.modules.settings.repository import OrgSettingsRepository
from app.modules.shift.schemas import ShiftResolveQuery
from app.modules.shift.service import ShiftService
from app.shared.base.repository import BaseRepository
from app.shared.base.service import BaseService
from app.shared.schemas.pagination import PaginatedResponse
from app.shared.utils.datetime import utcnow


class AttendanceService(BaseService):
    """Attendance Management business rules engine and orchestration service."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)
        # Main module repositories
        self.days = AttendanceDayRepository(session)
        self.punches = AttendancePunchRepository(session)
        self.penalties = AttendancePenaltyRepository(session)

        # Cross-module lookup readers
        self.employees = EmployeeLookupRepository(session)
        self.shifts = ShiftLookupRepository(session)
        self.org_settings = OrgSettingsRepository(session)

        # Audit logger
        self.audit = AuditService(session)

        # Base repositories for external approvals references
        self.regularization_requests = BaseRepository(session, AttendanceRegularizationRequest)
        self.approval_requests = BaseRepository(session, ApprovalRequest)

    # =========================================================================
    # Helpers & Validations
    # =========================================================================

    async def _actor_name(self, org_id: int, actor_id: int) -> str:
        """Resolve the acting user's display name for auditing (best-effort)."""
        from app.modules.rbac.repository import UserRepository
        user = await UserRepository(self.session).get_active_by_id(actor_id, org_id)
        name = getattr(user, "name", None)
        return name if isinstance(name, str) and name else f"user #{actor_id}"

    async def _audit(
        self,
        *,
        org_id: int,
        actor_id: int,
        action_type: ActionType,
        title: str,
        description: str,
        employee_id: int | None = None,
        employee_name: str | None = None,
        sub_module: str | None = None,
    ) -> None:
        """Record a structured log inside the active transaction boundary."""
        await self.audit.record(
            org_id=org_id,
            module="Attendance Management",
            sub_module=sub_module,
            action_type=action_type,
            title=title,
            description=description,
            performed_by_user_id=actor_id,
            performed_by_name=await self._actor_name(org_id, actor_id),
            employee_id=employee_id,
            employee_name=employee_name,
        )

    async def _require_regularization_enabled(self, org_id: int) -> None:
        """Reject the request when Settings has regularization turned off for the org.

        ``org_settings.enable_regularization`` is the organization-wide toggle owned by the
        Settings module. An org with no settings row has never enabled it, so the schema
        default (``false``) applies and regularization stays off.
        """
        settings = await self.org_settings.get_by_org_id(org_id)
        if settings is None or not settings.enable_regularization:
            raise RegularizationDisabledException()

    async def _validate_employee(self, org_id: int, employee_id: int) -> Employee:
        """Ensure an active employee exists in the tenant's context."""
        employee = await self.employees.get_active_by_id(employee_id, org_id)
        if not employee:
            raise EmployeeNotFoundException(f"Employee {employee_id} not found in this organization.")
        return employee

    # =========================================================================
    # Attendance Days CRUD & Manual Marks
    # =========================================================================

    async def create_attendance_day(
        self,
        org_id: int,
        actor_id: int,
        *,
        employee_id: int,
        attendance_date: date,
        status: AttendanceDayStatus,
        shift_id: int | None = None,
        leave_id: int | None = None,
        remarks: str | None = None,
    ) -> AttendanceDayDetailSchema:
        """Directly create/override a daily attendance record without punches."""
        employee = await self._validate_employee(org_id, employee_id)
        if shift_id and not await self.shifts.exists_active(org_id, shift_id):
            raise ShiftNotFoundException(f"Shift {shift_id} not found.")

        # Check uniqueness constraint
        existing = await self.days.get_by_employee_date(org_id, employee_id, attendance_date)
        if existing:
            raise AttendanceDayExistsException(
                f"Attendance day already exists for employee {employee_id} on {attendance_date}."
            )

        payload = {
            "org_id": org_id,
            "employee_id": employee_id,
            "attendance_date": attendance_date,
            "shift_id": shift_id,
            "status": status.value,
            "source": AttendanceSource.MANUAL.value,
            "leave_id": leave_id,
            "remarks": remarks,
            "marked_by": actor_id,
            "created_by": actor_id,
            "updated_by": actor_id,
        }

        async with self.transaction():
            day = await self.days.create(payload)
            await self._audit(
                org_id=org_id,
                actor_id=actor_id,
                action_type=ActionType.INSERT,
                title="Manual Attendance Day Marked",
                description=f"Marked manual attendance day on {attendance_date} with status {status.value}.",
                employee_id=employee_id,
                employee_name=employee.employee_name,
            )

        return await self.get_attendance_day(org_id, day.id)

    async def create_manual_attendance(
        self,
        org_id: int,
        actor_id: int,
        data: AttendanceManualCreateRequest,
    ) -> AttendanceDayDetailSchema:
        """Mark manual attendance containing a punch-in and punch-out event (onboards a manual entry)."""
        employee = await self._validate_employee(org_id, data.employee_id)
        existing = await self.days.get_by_employee_date(org_id, data.employee_id, data.date)
        if existing:
            raise AttendanceDayExistsException(
                f"Attendance day already exists for employee {data.employee_id} on {data.date}."
            )

        async with self.transaction():
            # Resolve shift of the day
            shift_id = None
            expected_start = None
            expected_end = None
            shift_resolve = await ShiftService(self.session).resolve_shift(
                org_id=org_id,
                query=ShiftResolveQuery(employee_id=data.employee_id, date=data.date),
            )
            if shift_resolve.shift:
                shift_id = shift_resolve.shift.shift_id
                shift_detail = await self.shifts.get_active_by_id(shift_id, org_id)
                if shift_detail:
                    weekday = (data.date.weekday() + 1) % 7
                    timing = next((t for t in shift_detail.day_timings if t.day_of_week == weekday), None)
                    if not timing:
                        timing = next((t for t in shift_detail.day_timings if t.day_of_week is None), None)
                    if timing:
                        expected_start = timing.start_time
                        expected_end = timing.end_time

            # Create attendance day record placeholder
            day = await self.days.create(
                {
                    "org_id": org_id,
                    "employee_id": data.employee_id,
                    "attendance_date": data.date,
                    "shift_id": shift_id,
                    "expected_start_time": expected_start,
                    "expected_end_time": expected_end,
                    "status": AttendanceDayStatus.PRESENT.value,
                    "source": AttendanceSource.MANUAL.value,
                    "marked_by": actor_id,
                    "remarks": data.reason,
                    "created_by": actor_id,
                    "updated_by": actor_id,
                }
            )

            # Insert raw punches
            await self.punches.create(
                {
                    "org_id": org_id,
                    "employee_id": data.employee_id,
                    "attendance_day_id": day.id,
                    "punch_type": PunchType.IN.value,
                    "punch_time": data.in_time,
                    "sequence_no": 1,
                    "punch_source": PunchSource.MANUAL_ENTRY.value,
                    "is_valid": True,
                    "created_by": actor_id,
                }
            )
            await self.punches.create(
                {
                    "org_id": org_id,
                    "employee_id": data.employee_id,
                    "attendance_day_id": day.id,
                    "punch_type": PunchType.OUT.value,
                    "punch_time": data.out_time,
                    "sequence_no": 2,
                    "punch_source": PunchSource.MANUAL_ENTRY.value,
                    "is_valid": True,
                    "created_by": actor_id,
                }
            )

            # Perform initial metrics computation
            await self._recompute_day_metrics(org_id, day)

            await self._audit(
                org_id=org_id,
                actor_id=actor_id,
                action_type=ActionType.INSERT,
                title="Manual Attendance Checked In/Out",
                description=f"Logged manual check-in at {data.in_time} and check-out at {data.out_time}.",
                employee_id=data.employee_id,
                employee_name=employee.employee_name,
            )

        return await self.get_attendance_day(org_id, day.id)

    async def override_attendance_day(
        self,
        org_id: int,
        actor_id: int,
        day_id: int,
        updates: dict[str, Any],
    ) -> AttendanceDayDetailSchema:
        """Override an attendance day's fields manually (Endpoint 2: Override Attendance)."""
        day = await self.days.get_by_id_in_org(day_id, org_id)
        if not day:
            raise AttendanceDayNotFoundException()

        employee = await self._validate_employee(org_id, day.employee_id)

        clean_updates = {
            "source": AttendanceSource.MANUAL.value,
            "marked_by": actor_id,
            "updated_by": actor_id,
        }

        # Validate external keys if changing
        if "shift_id" in updates:
            shift_id = updates["shift_id"]
            if shift_id and not await self.shifts.exists_active(org_id, shift_id):
                raise ShiftNotFoundException()
            clean_updates["shift_id"] = shift_id

        for field in (
            "status",
            "leave_id",
            "remarks",
            "total_working_minutes",
            "total_break_minutes",
            "overtime_minutes",
            "late_minutes",
            "early_leaving_minutes",
        ):
            if field in updates:
                clean_updates[field] = updates[field]

        async with self.transaction():
            await self.days.update(day, clean_updates)
            await self._audit(
                org_id=org_id,
                actor_id=actor_id,
                action_type=ActionType.UPDATE,
                title="Manual Attendance Override",
                description=f"Overrode attendance parameters for {day.attendance_date}.",
                employee_id=day.employee_id,
                employee_name=employee.employee_name,
            )

        return await self.get_attendance_day(org_id, day.id)

    async def get_attendance_day(
        self,
        org_id: int,
        day_id: int,
    ) -> AttendanceDayDetailSchema:
        """Fetch attendance day detail with eagerly loaded punches and penalties."""
        day = await self.days.get_detail(day_id, org_id)
        if not day:
            raise AttendanceDayNotFoundException()
        return AttendanceDayDetailSchema.model_validate(day)

    async def list_attendance_days(
        self,
        org_id: int,
        query: AttendanceDailyQuery,
        branch_scope: list[int] | None = None,
    ) -> AttendanceDailyListResponse:
        """List and search paginated attendance day summaries (Endpoint 3)."""
        rows = await self.days.search(
            org_id,
            date=query.date,
            branch_id=query.branch_id,
            dept_id=query.department_id,
            branch_scope=branch_scope,
            page=query.page,
            page_size=query.page_size,
        )
        total = await self.days.search_count(
            org_id,
            date=query.date,
            branch_id=query.branch_id,
            dept_id=query.department_id,
            branch_scope=branch_scope,
        )
        items = [AttendanceDailySchema.model_validate(row) for row in rows]
        return AttendanceDailyListResponse.build(
            items=items,
            page=query.page,
            page_size=query.page_size,
            total_records=total,
        )

    async def get_employee_attendance_history(
        self,
        org_id: int,
        employee_id: int,
        date_from: date | None = None,
        date_to: date | None = None,
        page: int = 1,
        page_size: int = 25,
    ) -> AttendanceDailyListResponse:
        """Retrieve paginated attendance history for a single employee (Endpoint 5)."""
        await self._validate_employee(org_id, employee_id)
        rows = await self.days.search(
            org_id,
            employee_id=employee_id,
            date_from=date_from,
            date_to=date_to,
            page=page,
            page_size=page_size,
        )
        total = await self.days.search_count(
            org_id,
            employee_id=employee_id,
            date_from=date_from,
            date_to=date_to,
        )
        items = [AttendanceDailySchema.model_validate(row) for row in rows]
        return AttendanceDailyListResponse.build(
            items=items,
            page=page,
            page_size=page_size,
            total_records=total,
        )

    async def get_attendance_calendar_view(
        self,
        org_id: int,
        employee_id: int,
        month: int,
        year: int,
    ) -> list[AttendanceMonthlyDaySchema]:
        """Fetch all calendar day cells for an employee across a calendar month (Endpoint 6)."""
        await self._validate_employee(org_id, employee_id)
        start_date = date(year, month, 1)
        if month == 12:
            end_date = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = date(year, month + 1, 1) - timedelta(days=1)

        rows = await self.days.search(
            org_id,
            employee_id=employee_id,
            date_from=start_date,
            date_to=end_date,
            page=1,
            page_size=100,
        )
        # Build month list
        return [AttendanceMonthlyDaySchema.model_validate(r) for r in rows]

    # =========================================================================
    # Punch Management
    # =========================================================================

    async def add_manual_punch(
        self,
        org_id: int,
        actor_id: int,
        employee_id: int,
        punch_time: datetime,
        punch_type: PunchType,
        latitude: Decimal | None = None,
        longitude: Decimal | None = None,
    ) -> AttendancePunchSchema:
        """Manually append a raw punch log, triggering lazy recalculation (Endpoint 7)."""
        employee = await self._validate_employee(org_id, employee_id)
        punch_date = punch_time.date()

        async with self.transaction():
            # Check or create daily summary block
            day = await self.days.get_by_employee_date(org_id, employee_id, punch_date)
            if not day:
                shift_id = None
                expected_start = None
                expected_end = None
                shift_resolve = await ShiftService(self.session).resolve_shift(
                    org_id=org_id,
                    query=ShiftResolveQuery(employee_id=employee_id, date=punch_date),
                )
                if shift_resolve.shift:
                    shift_id = shift_resolve.shift.shift_id
                    shift_detail = await self.shifts.get_active_by_id(shift_id, org_id)
                    if shift_detail:
                        weekday = (punch_date.weekday() + 1) % 7
                        timing = next((t for t in shift_detail.day_timings if t.day_of_week == weekday), None)
                        if not timing:
                            timing = next((t for t in shift_detail.day_timings if t.day_of_week is None), None)
                        if timing:
                            expected_start = timing.start_time
                            expected_end = timing.end_time

                day = await self.days.create(
                    {
                        "org_id": org_id,
                        "employee_id": employee_id,
                        "attendance_date": punch_date,
                        "shift_id": shift_id,
                        "expected_start_time": expected_start,
                        "expected_end_time": expected_end,
                        "status": AttendanceDayStatus.NOT_MARKED.value,
                        "source": AttendanceSource.SYSTEM.value,
                        "created_by": actor_id,
                        "updated_by": actor_id,
                    }
                )

            # Determine day-local sequence no
            punches_list = await self.punches.get_for_day(org_id, day.id)
            seq_no = len(punches_list) + 1

            punch = await self.punches.create(
                {
                    "org_id": org_id,
                    "employee_id": employee_id,
                    "attendance_day_id": day.id,
                    "punch_type": punch_type.value,
                    "punch_time": punch_time,
                    "sequence_no": seq_no,
                    "punch_source": PunchSource.MANUAL_ENTRY.value,
                    "latitude": latitude,
                    "longitude": longitude,
                    "is_valid": True,
                    "created_by": actor_id,
                }
            )

            # Recompute day metrics dynamically to keep summary synced
            await self._recompute_day_metrics(org_id, day)

            await self._audit(
                org_id=org_id,
                actor_id=actor_id,
                action_type=ActionType.INSERT,
                title="Manual Punch Appended",
                description=f"Appended manual {punch_type.value} punch at {punch_time}.",
                employee_id=employee_id,
                employee_name=employee.employee_name,
            )

        return AttendancePunchSchema.model_validate(punch)

    async def list_punches(
        self,
        org_id: int,
        query: AttendanceLogsQuery,
    ) -> AttendanceLogsResponse:
        """Search and filter raw punch transactions (Endpoint 8)."""
        rows = await self.punches.search(
            org_id,
            employee_id=query.employee_id,
            device_id=query.device_id,
            from_date=query.from_date,
            to_date=query.to_date,
            page=query.page,
            page_size=query.page_size,
        )
        total = await self.punches.search_count(
            org_id,
            employee_id=query.employee_id,
            device_id=query.device_id,
            from_date=query.from_date,
            to_date=query.to_date,
        )
        items = [AttendancePunchSchema.model_validate(row) for row in rows]
        return AttendanceLogsResponse.build(
            items=items,
            page=query.page,
            page_size=query.page_size,
            total_records=total,
        )

    async def get_day_punches(
        self,
        org_id: int,
        day_id: int,
    ) -> list[AttendancePunchSchema]:
        """Fetch all chronological punches associated with a day (Endpoint 9)."""
        day = await self.days.get_by_id_in_org(day_id, org_id)
        if not day:
            raise AttendanceDayNotFoundException()
        punches = await self.punches.get_for_day(org_id, day_id)
        return [AttendancePunchSchema.model_validate(p) for p in punches]

    async def get_employee_punch_timeline(
        self,
        org_id: int,
        employee_id: int,
        date_from: date,
        date_to: date,
    ) -> list[AttendancePunchSchema]:
        """Expose chronological punch history for an employee in a range (Endpoint 10)."""
        await self._validate_employee(org_id, employee_id)
        punches = await self.punches.get_timeline(org_id, employee_id, date_from, date_to)
        return [AttendancePunchSchema.model_validate(p) for p in punches]

    # =========================================================================
    # Penalties
    # =========================================================================

    async def apply_penalty(
        self,
        org_id: int,
        actor_id: int,
        *,
        employee_id: int,
        attendance_day_id: int,
        penalty_type: PenaltyType,
        penalty_unit: PenaltyUnit,
        penalty_value: Decimal,
        remarks: str | None = None,
    ) -> AttendancePenaltySchema:
        """Apply a manual penalty to an attendance day (Endpoint 11)."""
        if penalty_value < Decimal("0"):
            raise ValidationException("Penalty value cannot be negative.")

        employee = await self._validate_employee(org_id, employee_id)
        day = await self.days.get_by_id_in_org(attendance_day_id, org_id)
        if not day or day.employee_id != employee_id:
            raise NotFoundException("Attendance day matching employee context not found.")

        payload = {
            "org_id": org_id,
            "employee_id": employee_id,
            "attendance_day_id": attendance_day_id,
            "penalty_type": penalty_type.value,
            "penalty_unit": penalty_unit.value,
            "penalty_value": penalty_value,
            "status": PenaltyStatus.ACTIVE.value,
            "applied_by": actor_id,
            "remarks": remarks,
            "is_deleted": False,
        }

        async with self.transaction():
            penalty = await self.penalties.create(payload)
            await self._audit(
                org_id=org_id,
                actor_id=actor_id,
                action_type=ActionType.INSERT,
                title="Attendance Penalty Applied",
                description=f"Applied {penalty_type.value} penalty of {penalty_value} {penalty_unit.value}.",
                employee_id=employee_id,
                employee_name=employee.employee_name,
            )

        return AttendancePenaltySchema.model_validate(penalty)

    async def list_penalties(
        self,
        org_id: int,
        *,
        employee_id: int | None = None,
        status: PenaltyStatus | None = None,
        page: int = 1,
        page_size: int = 25,
    ) -> PaginatedResponse[AttendancePenaltySchema]:
        """Search and filter attendance penalty records (Endpoint 12)."""
        rows = await self.penalties.search(
            org_id,
            employee_id=employee_id,
            status=status.value if status else None,
            page=page,
            page_size=page_size,
        )
        total = await self.penalties.search_count(
            org_id,
            employee_id=employee_id,
            status=status.value if status else None,
        )
        items = [AttendancePenaltySchema.model_validate(row) for row in rows]
        return PaginatedResponse.build(
            items=items,
            page=page,
            page_size=page_size,
            total_records=total,
        )

    async def get_penalty_details(
        self,
        org_id: int,
        penalty_id: int,
    ) -> AttendancePenaltySchema:
        """Retrieve fine details of a specific penalty (Endpoint 13)."""
        penalty = await self.penalties.get_by_id_in_org(penalty_id, org_id)
        if not penalty or penalty.is_deleted:
            raise PenaltyNotFoundException()
        return AttendancePenaltySchema.model_validate(penalty)

    async def waive_penalty(
        self,
        org_id: int,
        actor_id: int,
        penalty_id: int,
        remarks: str | None = None,
    ) -> AttendancePenaltySchema:
        """Waive (soft-delete / close) a penalty with reason audit (Endpoint 14)."""
        penalty = await self.penalties.get_by_id_in_org(penalty_id, org_id)
        if not penalty or penalty.is_deleted:
            raise PenaltyNotFoundException()
        if penalty.status == PenaltyStatus.WAIVED.value:
            raise PenaltyAlreadyWaivedException()

        employee = await self._validate_employee(org_id, penalty.employee_id)

        waive_remarks = f"Waived: {remarks}" if remarks else "Waived by administrator"
        combined_remarks = f"{penalty.remarks} | {waive_remarks}" if penalty.remarks else waive_remarks

        async with self.transaction():
            await self.penalties.update(
                penalty,
                {
                    "status": PenaltyStatus.WAIVED.value,
                    "remarks": combined_remarks,
                    "is_deleted": True,
                },
            )
            await self._audit(
                org_id=org_id,
                actor_id=actor_id,
                action_type=ActionType.UPDATE,
                title="Attendance Penalty Waived",
                description=f"Waived penalty {penalty_id} for {employee.employee_name}.",
                employee_id=penalty.employee_id,
                employee_name=employee.employee_name,
            )

        return AttendancePenaltySchema.model_validate(penalty)

    async def get_employee_penalty_history(
        self,
        org_id: int,
        employee_id: int,
    ) -> list[AttendancePenaltySchema]:
        """Fetch complete penalty history (active/waived) for an employee (Endpoint 15)."""
        await self._validate_employee(org_id, employee_id)
        stmt = select(AttendancePenalty).where(
            AttendancePenalty.employee_id == employee_id,
            AttendancePenalty.org_id == org_id,
        )
        res = await self.session.execute(stmt)
        return [AttendancePenaltySchema.model_validate(row) for row in res.scalars().all()]

    # =========================================================================
    # Summarization & Analytics
    # =========================================================================

    async def get_daily_summary(
        self,
        org_id: int,
        date_val: date,
        branch_id: int | None = None,
        dept_id: int | None = None,
        shift_id: int | None = None,
    ) -> dict[str, Any]:
        """Aggregate attendance stats for the entire dashboard daily grid view (Endpoint 16)."""
        stmt = select(AttendanceDay)
        if branch_id or dept_id:
            stmt = stmt.join(Employee, AttendanceDay.employee_id == Employee.employee_id)

        conds = [AttendanceDay.org_id == org_id, AttendanceDay.attendance_date == date_val]
        if branch_id:
            conds.append(Employee.branch_id == branch_id)
        if dept_id:
            conds.append(Employee.department_id == dept_id)
        if shift_id:
            conds.append(AttendanceDay.shift_id == shift_id)

        stmt = stmt.where(*conds)
        days = (await self.session.execute(stmt)).scalars().all()

        counts = {
            "present": 0,
            "absent": 0,
            "half_day": 0,
            "week_off": 0,
            "holiday": 0,
            "on_leave": 0,
            "not_marked": 0,
        }
        late_count = 0
        early_exit_count = 0
        total_working = 0
        total_overtime = 0

        for d in days:
            status = d.status or "not_marked"
            if status in counts:
                counts[status] += 1
            if d.late_minutes and d.late_minutes > 0:
                late_count += 1
            if d.early_leaving_minutes and d.early_leaving_minutes > 0:
                early_exit_count += 1
            total_working += d.total_working_minutes or 0
            total_overtime += d.overtime_minutes or 0

        return {
            "date": date_val,
            "headcount": len(days),
            "statuses": counts,
            "late_count": late_count,
            "early_exit_count": early_exit_count,
            "total_working_minutes": total_working,
            "total_overtime_minutes": total_overtime,
        }

    async def get_monthly_summary(
        self,
        org_id: int,
        month: int,
        year: int,
        employee_id: int | None = None,
        branch_id: int | None = None,
        dept_id: int | None = None,
        shift_id: int | None = None,
    ) -> list[dict[str, Any]]:
        """Summarize working analytics per employee over a month (Endpoint 17)."""
        start_date = date(year, month, 1)
        if month == 12:
            end_date = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = date(year, month + 1, 1) - timedelta(days=1)

        stmt = select(AttendanceDay)
        if branch_id or dept_id:
            stmt = stmt.join(Employee, AttendanceDay.employee_id == Employee.employee_id)

        conds = [
            AttendanceDay.org_id == org_id,
            AttendanceDay.attendance_date >= start_date,
            AttendanceDay.attendance_date <= end_date,
        ]
        if employee_id:
            conds.append(AttendanceDay.employee_id == employee_id)
        if branch_id:
            conds.append(Employee.branch_id == branch_id)
        if dept_id:
            conds.append(Employee.department_id == dept_id)
        if shift_id:
            conds.append(AttendanceDay.shift_id == shift_id)

        stmt = stmt.where(*conds)
        days = (await self.session.execute(stmt)).scalars().all()

        emp_summary: dict[int, dict[str, Any]] = {}
        for d in days:
            emp_id = d.employee_id
            if emp_id not in emp_summary:
                emp_summary[emp_id] = {
                    "employee_id": emp_id,
                    "days_present": 0,
                    "days_absent": 0,
                    "days_half_day": 0,
                    "days_on_leave": 0,
                    "days_week_off": 0,
                    "days_holiday": 0,
                    "total_working_minutes": 0,
                    "total_overtime_minutes": 0,
                    "total_late_minutes": 0,
                    "total_early_leaving_minutes": 0,
                }
            metrics = emp_summary[emp_id]
            status = d.status
            if status == "present":
                metrics["days_present"] += 1
            elif status == "absent":
                metrics["days_absent"] += 1
            elif status == "half_day":
                metrics["days_half_day"] += 1
            elif status == "on_leave":
                metrics["days_on_leave"] += 1
            elif status == "week_off":
                metrics["days_week_off"] += 1
            elif status == "holiday":
                metrics["days_holiday"] += 1

            metrics["total_working_minutes"] += d.total_working_minutes or 0
            metrics["total_overtime_minutes"] += d.overtime_minutes or 0
            metrics["total_late_minutes"] += d.late_minutes or 0
            metrics["total_early_leaving_minutes"] += d.early_leaving_minutes or 0

        return list(emp_summary.values())

    # =========================================================================
    # Reports
    # =========================================================================

    async def get_employee_attendance_report(
        self,
        org_id: int,
        employee_id: int,
        date_from: date,
        date_to: date,
    ) -> dict[str, Any]:
        """Format a singular detailed report for one employee in a range (Endpoint 18)."""
        employee = await self._validate_employee(org_id, employee_id)
        days = await self.days.search(
            org_id,
            employee_id=employee_id,
            date_from=date_from,
            date_to=date_to,
            page=1,
            page_size=1000,
        )

        present = absent = half_day = leave = week_off = holiday = 0
        working = overtime = late = early = 0

        details = []
        for d in days:
            status = d.status
            if status == "present":
                present += 1
            elif status == "absent":
                absent += 1
            elif status == "half_day":
                half_day += 1
            elif status == "on_leave":
                leave += 1
            elif status == "week_off":
                week_off += 1
            elif status == "holiday":
                holiday += 1

            working += d.total_working_minutes or 0
            overtime += d.overtime_minutes or 0
            late += d.late_minutes or 0
            early += d.early_leaving_minutes or 0

            details.append(
                {
                    "date": d.attendance_date,
                    "status": status,
                    "in_time": d.first_punch_in,
                    "out_time": d.last_punch_out,
                    "working_minutes": d.total_working_minutes,
                    "late_minutes": d.late_minutes,
                }
            )

        return {
            "employee_id": employee_id,
            "employee_name": employee.employee_name,
            "date_from": date_from,
            "date_to": date_to,
            "totals": {
                "days_present": present,
                "days_absent": absent,
                "days_half_day": half_day,
                "days_on_leave": leave,
                "days_week_off": week_off,
                "days_holiday": holiday,
                "total_working_minutes": working,
                "total_overtime_minutes": overtime,
                "total_late_minutes": late,
                "total_early_leaving_minutes": early,
            },
            "records": details,
        }

    async def get_department_attendance_report(
        self,
        org_id: int,
        dept_id: int,
        date_from: date,
        date_to: date,
    ) -> dict[str, Any]:
        """Aggregate daily metrics for all members of a department (Endpoint 19)."""
        stmt = select(Employee).where(
            Employee.department_id == dept_id,
            Employee.org_id == org_id,
            Employee.is_deleted.is_(False),
        )
        employees = (await self.session.execute(stmt)).scalars().all()

        emp_reports = []
        tot_present = tot_absent = tot_half = tot_leave = 0
        tot_working = tot_overtime = tot_late = tot_early = 0

        for emp in employees:
            rep = await self.get_employee_attendance_report(org_id, emp.employee_id, date_from, date_to)
            emp_reports.append(rep)
            t = rep["totals"]
            tot_present += t["days_present"]
            tot_absent += t["days_absent"]
            tot_half += t["days_half_day"]
            tot_leave += t["days_on_leave"]
            tot_working += t["total_working_minutes"]
            tot_overtime += t["total_overtime_minutes"]
            tot_late += t["total_late_minutes"]
            tot_early += t["total_early_leaving_minutes"]

        return {
            "department_id": dept_id,
            "date_from": date_from,
            "date_to": date_to,
            "totals": {
                "days_present": tot_present,
                "days_absent": tot_absent,
                "days_half_day": tot_half,
                "days_on_leave": tot_leave,
                "total_working_minutes": tot_working,
                "total_overtime_minutes": tot_overtime,
                "total_late_minutes": tot_late,
                "total_early_leaving_minutes": tot_early,
            },
            "employees": emp_reports,
        }

    async def get_branch_attendance_report(
        self,
        org_id: int,
        branch_id: int,
        date_from: date,
        date_to: date,
    ) -> dict[str, Any]:
        """Aggregate daily metrics for all members of a branch (Endpoint 20)."""
        stmt = select(Employee).where(
            Employee.branch_id == branch_id,
            Employee.org_id == org_id,
            Employee.is_deleted.is_(False),
        )
        employees = (await self.session.execute(stmt)).scalars().all()

        emp_reports = []
        tot_present = tot_absent = tot_half = tot_leave = 0
        tot_working = tot_overtime = tot_late = tot_early = 0

        for emp in employees:
            rep = await self.get_employee_attendance_report(org_id, emp.employee_id, date_from, date_to)
            emp_reports.append(rep)
            t = rep["totals"]
            tot_present += t["days_present"]
            tot_absent += t["days_absent"]
            tot_half += t["days_half_day"]
            tot_leave += t["days_on_leave"]
            tot_working += t["total_working_minutes"]
            tot_overtime += t["total_overtime_minutes"]
            tot_late += t["total_late_minutes"]
            tot_early += t["total_early_leaving_minutes"]

        return {
            "branch_id": branch_id,
            "date_from": date_from,
            "date_to": date_to,
            "totals": {
                "days_present": tot_present,
                "days_absent": tot_absent,
                "days_half_day": tot_half,
                "days_on_leave": tot_leave,
                "total_working_minutes": tot_working,
                "total_overtime_minutes": tot_overtime,
                "total_late_minutes": tot_late,
                "total_early_leaving_minutes": tot_early,
            },
            "employees": emp_reports,
        }

    async def get_shift_attendance_report(
        self,
        org_id: int,
        shift_id: int,
        date_from: date,
        date_to: date,
    ) -> dict[str, Any]:
        """Aggregate daily metrics grouped by shift (Endpoint 21)."""
        days = await self.days.search(
            org_id,
            shift_id=shift_id,
            date_from=date_from,
            date_to=date_to,
            page=1,
            page_size=10000,
        )

        present = absent = half_day = leave = 0
        working = overtime = late = early = 0
        details = []

        for d in days:
            status = d.status
            if status == "present":
                present += 1
            elif status == "absent":
                absent += 1
            elif status == "half_day":
                half_day += 1
            elif status == "on_leave":
                leave += 1

            working += d.total_working_minutes or 0
            overtime += d.overtime_minutes or 0
            late += d.late_minutes or 0
            early += d.early_leaving_minutes or 0

            details.append(
                {
                    "employee_id": d.employee_id,
                    "date": d.attendance_date,
                    "status": status,
                    "working_minutes": d.total_working_minutes,
                }
            )

        return {
            "shift_id": shift_id,
            "date_from": date_from,
            "date_to": date_to,
            "totals": {
                "days_present": present,
                "days_absent": absent,
                "days_half_day": half_day,
                "days_on_leave": leave,
                "total_working_minutes": working,
                "total_overtime_minutes": overtime,
                "total_late_minutes": late,
                "total_early_leaving_minutes": early,
            },
            "records": details,
        }

    # =========================================================================
    # Regularization & Corrections
    # =========================================================================

    async def request_correction(
        self,
        org_id: int,
        actor_id: int,
        data: AttendanceCorrectionCreateRequest,
    ) -> AttendanceCorrectionSchema:
        """Create a regularization request along with its polymorphic approval record."""
        await self._require_regularization_enabled(org_id)
        employee = await self._validate_employee(org_id, data.employee_id)
        day = await self.days.get_by_employee_date(org_id, data.employee_id, data.date)
        if not day:
            raise AttendanceDayNotFoundException()

        # Build original punch time format representation
        old_time_str = "None"
        if day.first_punch_in and day.last_punch_out:
            old_time_str = f"{day.first_punch_in.strftime('%H:%M')} - {day.last_punch_out.strftime('%H:%M')}"

        new_time_str = f"{data.requested_in.strftime('%H:%M')} - {data.requested_out.strftime('%H:%M')}"

        async with self.transaction():
            # Create AttendanceRegularizationRequest
            reg_req = await self.regularization_requests.create(
                {
                    "employee_id": data.employee_id,
                    "attendance_date": data.date,
                    "old_punch_time": old_time_str,
                    "new_punch_time": new_time_str,
                    "employee_reason": data.reason,
                    "status": ApprovalStatus.PENDING.value,
                }
            )

            # Create polymorphic ApprovalRequest
            await self.approval_requests.create(
                {
                    "org_id": org_id,
                    "request_type": "attendance",
                    "reference_id": reg_req.id,
                    "employee_id": data.employee_id,
                    "status": ApprovalStatus.PENDING.value,
                    "created_by": actor_id,
                }
            )

            await self._audit(
                org_id=org_id,
                actor_id=actor_id,
                action_type=ActionType.INSERT,
                title="Regularization Correction Requested",
                description=f"Requested time correction for {data.date} to {new_time_str}.",
                employee_id=data.employee_id,
                employee_name=employee.employee_name,
            )

        return AttendanceCorrectionSchema.model_validate(reg_req)

    async def approve_correction(
        self,
        org_id: int,
        actor_id: int,
        request_id: int,
        data: AttendanceCorrectionApproveRequest,
    ) -> AttendanceCorrectionSchema:
        """Process an attendance regularization approval decision, applying changes if approved."""
        # Find approval request
        stmt = select(ApprovalRequest).where(
            ApprovalRequest.id == request_id,
            ApprovalRequest.org_id == org_id,
        )
        approval = (await self.session.execute(stmt)).scalar_one_or_none()
        if not approval:
            raise NotFoundException("Approval request not found.")

        if approval.status != ApprovalStatus.PENDING.value:
            raise ConflictException("Request is already processed.", code="request_already_processed")

        # Find regularization request
        reg_req = await self.regularization_requests.get_by_id(approval.reference_id)
        if not reg_req:
            raise NotFoundException("Regularization request details not found.")

        employee = await self._validate_employee(org_id, reg_req.employee_id)

        async with self.transaction():
            # Update approval
            await self.approval_requests.update(
                approval,
                {
                    "status": data.decision.value,
                    "reviewed_by": actor_id,
                    "reviewed_at": utcnow(),
                    "reject_remarks": data.comment,
                },
            )

            # Update regularization
            await self.regularization_requests.update(
                reg_req,
                {
                    "status": data.decision.value,
                },
            )

            if data.decision == ApprovalStatus.APPROVED:
                day = await self.days.get_by_employee_date(org_id, reg_req.employee_id, reg_req.attendance_date)
                if day:
                    # Invalidate existing punches for the day
                    existing_punches = await self.punches.get_for_day(org_id, day.id)
                    for p in existing_punches:
                        await self.punches.update(p, {"is_valid": False})

                    # Parse new punches from new_punch_time
                    time_parts = reg_req.new_punch_time.split(" - ")
                    in_t = datetime.strptime(time_parts[0], "%H:%M").time()
                    out_t = datetime.strptime(time_parts[1], "%H:%M").time()

                    # Use same timezone as prior punch or default
                    tz = day.first_punch_in.tzinfo if day.first_punch_in else None
                    in_dt = datetime.combine(reg_req.attendance_date, in_t).replace(tzinfo=tz)
                    out_dt = datetime.combine(reg_req.attendance_date, out_t).replace(tzinfo=tz)
                    if out_t < in_t:
                        out_dt += timedelta(days=1)

                    # Create corrected punches
                    await self.punches.create(
                        {
                            "org_id": org_id,
                            "employee_id": reg_req.employee_id,
                            "attendance_day_id": day.id,
                            "punch_type": PunchType.IN.value,
                            "punch_time": in_dt,
                            "sequence_no": len(existing_punches) + 1,
                            "punch_source": PunchSource.MANUAL_ENTRY.value,
                            "is_valid": True,
                            "created_by": actor_id,
                        }
                    )
                    await self.punches.create(
                        {
                            "org_id": org_id,
                            "employee_id": reg_req.employee_id,
                            "attendance_day_id": day.id,
                            "punch_type": PunchType.OUT.value,
                            "punch_time": out_dt,
                            "sequence_no": len(existing_punches) + 2,
                            "punch_source": PunchSource.MANUAL_ENTRY.value,
                            "is_valid": True,
                            "created_by": actor_id,
                        }
                    )

                    # Update day regularized status
                    await self.days.update(day, {"is_regularized": True})

                    # Recompute day metrics dynamically
                    await self._recompute_day_metrics(org_id, day)

            await self._audit(
                org_id=org_id,
                actor_id=actor_id,
                action_type=ActionType.UPDATE,
                title="Regularization Processing Completed",
                description=f"Regularization request {request_id} resolved with status {data.decision.value}.",
                employee_id=reg_req.employee_id,
                employee_name=employee.employee_name,
            )

        return AttendanceCorrectionSchema.model_validate(reg_req)

    # =========================================================================
    # Missing Punches Analysis
    # =========================================================================

    async def get_missing_punches(
        self,
        org_id: int,
        query: AttendanceMissingPunchesQuery,
    ) -> AttendanceMissingPunchesResponse:
        """Scan daily summaries to flag incomplete punch pairs (Endpoint 11/Missing punches)."""
        # Search all attendance days in range
        days = await self.days.search(
            org_id,
            date_from=query.from_date,
            date_to=query.to_date,
            page=1,
            page_size=10000,
        )

        missing_records = []
        for d in days:
            # Check for missing punch pairs
            if d.first_punch_in and not d.last_punch_out:
                # Missing OUT punch
                employee = await self.employees.get_active_by_id(d.employee_id, org_id)
                if employee:
                    missing_records.append(
                        AttendanceMissingPunchSchema(
                            employee_id=d.employee_id,
                            employee_code=employee.employee_code,
                            employee_name=employee.employee_name,
                            attendance_date=d.attendance_date,
                            punch_time=d.first_punch_in,
                            punch_type=PunchType.IN,
                            missing_type=PunchType.OUT,
                        )
                    )
            elif not d.first_punch_in and d.last_punch_out:
                # Missing IN punch
                employee = await self.employees.get_active_by_id(d.employee_id, org_id)
                if employee:
                    missing_records.append(
                        AttendanceMissingPunchSchema(
                            employee_id=d.employee_id,
                            employee_code=employee.employee_code,
                            employee_name=employee.employee_name,
                            attendance_date=d.attendance_date,
                            punch_time=d.last_punch_out,
                            punch_type=PunchType.OUT,
                            missing_type=PunchType.IN,
                        )
                    )

        # Pagination simulation
        offset = query.offset
        limit = query.limit
        paginated_items = missing_records[offset : offset + limit]

        return AttendanceMissingPunchesResponse.build(
            items=paginated_items,
            page=query.page,
            page_size=query.page_size,
            total_records=len(missing_records),
        )

    # =========================================================================
    # Locked Period Freeze
    # =========================================================================

    async def lock_attendance(
        self,
        org_id: int,
        actor_id: int,
        data: AttendanceLockRequest,
    ) -> bool:
        """Freeze mutations for a specific date range (no-op as there is no DB backing for locks)."""
        await self._audit(
            org_id=org_id,
            actor_id=actor_id,
            action_type=ActionType.UPDATE,
            title="Attendance Lock Triggered",
            description=f"Locked attendance from {data.period_start} to {data.period_end}.",
        )
        return True

    # =========================================================================
    # Computation Engine
    # =========================================================================

    async def recompute_attendance(
        self,
        org_id: int,
        actor_id: int,
        employee_id: int,
        date_val: date,
    ) -> AttendanceDayDetailSchema:
        """Recompute daily metrics on-demand for a given employee and date."""
        await self._validate_employee(org_id, employee_id)
        day = await self.days.get_by_employee_date(org_id, employee_id, date_val)
        if not day:
            raise AttendanceDayNotFoundException()

        async with self.transaction():
            # Update expected times from Resolved Shift
            shift_resolve = await ShiftService(self.session).resolve_shift(
                org_id=org_id,
                query=ShiftResolveQuery(employee_id=employee_id, date=date_val),
            )
            if shift_resolve.shift:
                shift_detail = await self.shifts.get_active_by_id(shift_resolve.shift.shift_id, org_id)
                if shift_detail:
                    weekday = (date_val.weekday() + 1) % 7
                    timing = next((t for t in shift_detail.day_timings if t.day_of_week == weekday), None)
                    if not timing:
                        timing = next((t for t in shift_detail.day_timings if t.day_of_week is None), None)
                    if timing:
                        await self.days.update(
                            day,
                            {
                                "shift_id": shift_resolve.shift.shift_id,
                                "expected_start_time": timing.start_time,
                                "expected_end_time": timing.end_time,
                            },
                        )

            await self._recompute_day_metrics(org_id, day)

            await self._audit(
                org_id=org_id,
                actor_id=actor_id,
                action_type=ActionType.UPDATE,
                title="Attendance Recomputation Completed",
                description=f"Recomputed daily metrics for {date_val}.",
                employee_id=employee_id,
            )

        return await self.get_attendance_day(org_id, day.id)

    async def _recompute_day_metrics(self, org_id: int, day: AttendanceDay) -> None:
        """Compute worked minutes, break minutes, late arrival, early leaving, and overtime fields."""
        punches = await self.punches.get_for_day(org_id, day.id)
        valid_punches = sorted([p for p in punches if p.is_valid], key=lambda p: p.punch_time)

        first_in = None
        last_out = None
        total_working = 0
        total_break = 0

        # Extract first in and last out
        ins = [p.punch_time for p in valid_punches if p.punch_type == PunchType.IN.value]
        outs = [p.punch_time for p in valid_punches if p.punch_type == PunchType.OUT.value]
        if ins:
            first_in = min(ins)
        if outs:
            last_out = max(outs)

        # Working segments pairing calculation
        current_in = None
        current_break_out = None

        for p in valid_punches:
            ptype = p.punch_type
            ptime = p.punch_time

            if ptype in (PunchType.IN.value, PunchType.BREAK_IN.value):
                if current_in is None:
                    current_in = ptime
                if ptype == PunchType.BREAK_IN.value and current_break_out is not None:
                    break_dur = int((ptime - current_break_out).total_seconds() / 60)
                    total_break += max(0, break_dur)
                    current_break_out = None
            elif ptype in (PunchType.OUT.value, PunchType.BREAK_OUT.value):
                if current_in is not None:
                    dur = int((ptime - current_in).total_seconds() / 60)
                    total_working += max(0, dur)
                    current_in = None
                if ptype == PunchType.BREAK_OUT.value:
                    current_break_out = ptime

        late_min = 0
        early_min = 0
        overtime_min = 0

        if first_in and day.expected_start_time:
            tz = first_in.tzinfo
            expected_start = datetime.combine(day.attendance_date, day.expected_start_time).replace(tzinfo=tz)
            if first_in > expected_start:
                late_min = int((first_in - expected_start).total_seconds() / 60)

        if last_out and day.expected_end_time:
            tz = last_out.tzinfo
            expected_end = datetime.combine(day.attendance_date, day.expected_end_time).replace(tzinfo=tz)
            if day.expected_end_time < day.expected_start_time:
                expected_end += timedelta(days=1)

            if last_out < expected_end:
                early_min = int((expected_end - last_out).total_seconds() / 60)
            elif last_out > expected_end:
                overtime_min = int((last_out - expected_end).total_seconds() / 60)

        # Determine daily status if not overridden
        status = day.status
        if day.source != AttendanceSource.MANUAL.value:
            if day.leave_id:
                status = AttendanceDayStatus.ON_LEAVE.value
            else:
                # Check resolved weekly off
                shift_resolve = await ShiftService(self.session).resolve_shift(
                    org_id=org_id,
                    query=ShiftResolveQuery(employee_id=day.employee_id, date=day.attendance_date),
                )
                if shift_resolve.is_weekly_off:
                    status = AttendanceDayStatus.WEEK_OFF.value if not valid_punches else AttendanceDayStatus.PRESENT.value
                else:
                    if not valid_punches:
                        status = AttendanceDayStatus.ABSENT.value
                    elif total_working >= 480:
                        status = AttendanceDayStatus.PRESENT.value
                    elif total_working >= 240:
                        status = AttendanceDayStatus.HALF_DAY.value
                    else:
                        status = AttendanceDayStatus.ABSENT.value

        await self.days.update(
            day,
            {
                "first_punch_in": first_in,
                "last_punch_out": last_out,
                "total_working_minutes": total_working,
                "total_break_minutes": total_break,
                "late_minutes": late_min,
                "early_leaving_minutes": early_min,
                "overtime_minutes": overtime_min,
                "status": status,
            },
        )


__all__ = ["AttendanceService"]
