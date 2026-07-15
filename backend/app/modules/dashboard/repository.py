"""Dashboard Management — Repository / data-access layer.

Aggregates read-only projections across monolith modules: Employee, Attendance,
Leave, Approvals, Payroll, Settlements, Hardware, Notifications, and Audit Logs.
"""

from __future__ import annotations

import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import and_, case, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.approvals.models import ApprovalRequest
from app.modules.attendance.models import AttendanceDay
from app.modules.audit.models import ActivityLog
from app.modules.employee.models.employee import Employee
from app.modules.employee.models.organization import Branch, Department, Designation
from app.modules.hardware.models import BiometricDevice
from app.modules.leave.models import LeaveRequest, LeaveType
from app.modules.notifications.models import Notification, NotificationRecipient
from app.modules.payroll.models import (
    FinalizedPayrollRun,
    PayrollComputedRow,
    PayrollGroup,
    PayrollSalaryCycle,
)
from app.modules.settlements.models import EmployeeArrears, EmployeeLoanAdvance
from app.shared.base.repository import BaseRepository


class DashboardRepository(BaseRepository[Employee]):
    """Read-only dashboard repository aggregating data across monolith modules."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Employee)

    async def get_employee_summary(
        self,
        org_id: int,
        branch_ids: list[int] | None = None,
        dept_ids: list[int] | None = None,
        date_from: datetime.date | None = None,
        date_to: datetime.date | None = None,
    ) -> dict[str, Any]:
        """Fetch headline employee metrics: total, active, and new hires."""
        # 1. Total employees (not deleted)
        total_stmt = select(func.count(Employee.employee_id)).where(
            Employee.org_id == org_id,
            Employee.is_deleted.is_(False),
        )
        if branch_ids:
            total_stmt = total_stmt.where(Employee.master_branch_id.in_(branch_ids))
        if dept_ids:
            total_stmt = total_stmt.where(Employee.dept_id.in_(dept_ids))
        total_res = await self.session.execute(total_stmt)
        total_employees = total_res.scalar() or 0

        # 2. Active employees (not deleted)
        active_stmt = select(func.count(Employee.employee_id)).where(
            Employee.org_id == org_id,
            Employee.is_deleted.is_(False),
            Employee.employment_status == "active",
        )
        if branch_ids:
            active_stmt = active_stmt.where(Employee.master_branch_id.in_(branch_ids))
        if dept_ids:
            active_stmt = active_stmt.where(Employee.dept_id.in_(dept_ids))
        active_res = await self.session.execute(active_stmt)
        active_employees = active_res.scalar() or 0

        # 3. New employees joined in the period
        new_stmt = select(func.count(Employee.employee_id)).where(
            Employee.org_id == org_id,
            Employee.is_deleted.is_(False),
        )
        if date_from:
            new_stmt = new_stmt.where(Employee.date_of_joining >= date_from)
        if date_to:
            new_stmt = new_stmt.where(Employee.date_of_joining <= date_to)
        if branch_ids:
            new_stmt = new_stmt.where(Employee.master_branch_id.in_(branch_ids))
        if dept_ids:
            new_stmt = new_stmt.where(Employee.dept_id.in_(dept_ids))
        new_res = await self.session.execute(new_stmt)
        new_employees = new_res.scalar() or 0

        return {
            "total_employees": total_employees,
            "active_employees": active_employees,
            "new_employees": new_employees,
        }

    async def get_employee_distribution(
        self,
        org_id: int,
        branch_ids: list[int] | None = None,
        dept_ids: list[int] | None = None,
    ) -> dict[str, list[dict[str, Any]]]:
        """Fetch employee distributions grouped by department, branch, designation, and status."""
        base_where = [
            Employee.org_id == org_id,
            Employee.is_deleted.is_(False),
        ]
        if branch_ids:
            base_where.append(Employee.master_branch_id.in_(branch_ids))
        if dept_ids:
            base_where.append(Employee.dept_id.in_(dept_ids))

        # Department distribution
        dept_stmt = (
            select(Department.dept_name, func.count(Employee.employee_id))
            .join(Department, Employee.dept_id == Department.dept_id)
            .where(*base_where)
            .group_by(Department.dept_name)
        )
        dept_res = await self.session.execute(dept_stmt)
        departments = [{"name": name, "count": count} for name, count in dept_res.all()]

        # Branch distribution
        branch_stmt = (
            select(Branch.branch_name, func.count(Employee.employee_id))
            .join(Branch, Employee.master_branch_id == Branch.branch_id)
            .where(*base_where)
            .group_by(Branch.branch_name)
        )
        branch_res = await self.session.execute(branch_stmt)
        branches = [{"name": name, "count": count} for name, count in branch_res.all()]

        # Designation distribution
        desig_stmt = (
            select(Designation.designation_name, func.count(Employee.employee_id))
            .join(Designation, Employee.designation_id == Designation.designation_id)
            .where(*base_where)
            .group_by(Designation.designation_name)
        )
        desig_res = await self.session.execute(desig_stmt)
        designations = [{"name": name, "count": count} for name, count in desig_res.all()]

        # Employment status distribution
        status_stmt = (
            select(Employee.employment_status, func.count(Employee.employee_id))
            .where(*base_where)
            .group_by(Employee.employment_status)
        )
        status_res = await self.session.execute(status_stmt)
        statuses = [{"name": name, "count": count} for name, count in status_res.all()]

        return {
            "department": departments,
            "branch": branches,
            "designation": designations,
            "employment_status": statuses,
        }

    async def get_attendance_summary(
        self,
        org_id: int,
        target_date: datetime.date,
        branch_ids: list[int] | None = None,
        dept_ids: list[int] | None = None,
    ) -> dict[str, Any]:
        """Fetch target date's attendance counts including lates and early exits."""
        emp_filter = [
            Employee.org_id == org_id,
            Employee.is_deleted.is_(False),
            Employee.employment_status == "active",
        ]
        if branch_ids:
            emp_filter.append(Employee.master_branch_id.in_(branch_ids))
        if dept_ids:
            emp_filter.append(Employee.dept_id.in_(dept_ids))

        stmt = (
            select(
                AttendanceDay.status,
                AttendanceDay.late_minutes,
                AttendanceDay.early_leaving_minutes,
            )
            .select_from(Employee)
            .join(
                AttendanceDay,
                and_(
                    Employee.employee_id == AttendanceDay.employee_id,
                    AttendanceDay.attendance_date == target_date,
                ),
                isouter=True,
            )
            .where(*emp_filter)
        )
        res = await self.session.execute(stmt)
        rows = res.all()

        present = 0
        absent = 0
        half_day = 0
        on_leave = 0
        late = 0
        early = 0
        not_marked = 0

        for status, late_mins, early_mins in rows:
            if status == "present":
                present += 1
            elif status == "absent":
                absent += 1
            elif status == "half_day":
                half_day += 1
            elif status == "on_leave":
                on_leave += 1
            else:
                not_marked += 1

            if status in ("present", "half_day"):
                if late_mins and late_mins > 0:
                    late += 1
                if early_mins and early_mins > 0:
                    early += 1

        # Calculate on_break_today
        from app.modules.attendance.models import AttendancePunch
        break_subq = (
            select(
                AttendancePunch.attendance_day_id,
                func.max(AttendancePunch.sequence_no).label("max_seq"),
            )
            .where(AttendancePunch.is_valid.is_(True))
            .group_by(AttendancePunch.attendance_day_id)
            .subquery()
        )

        break_stmt = (
            select(func.count(AttendancePunch.id))
            .join(
                break_subq,
                and_(
                    AttendancePunch.attendance_day_id == break_subq.c.attendance_day_id,
                    AttendancePunch.sequence_no == break_subq.c.max_seq,
                ),
            )
            .join(AttendanceDay, AttendancePunch.attendance_day_id == AttendanceDay.id)
            .join(Employee, AttendanceDay.employee_id == Employee.employee_id)
            .where(
                AttendanceDay.org_id == org_id,
                AttendanceDay.attendance_date == target_date,
                AttendancePunch.punch_type == "break_out",
                AttendancePunch.is_valid.is_(True),
                *emp_filter,
            )
        )
        break_res = await self.session.execute(break_stmt)
        on_break_today = break_res.scalar() or 0

        # Calculate pending_biometrics
        from app.modules.employee.models.satellites import EmployeeBiometric
        biometric_stmt_in = (
            select(EmployeeBiometric.employee_id)
            .where(EmployeeBiometric.is_deleted.is_(False))
        )

        pending_stmt = (
            select(func.count(Employee.employee_id))
            .where(
                ~Employee.employee_id.in_(biometric_stmt_in),
                *emp_filter,
            )
        )
        pending_res = await self.session.execute(pending_stmt)
        pending_biometrics = pending_res.scalar() or 0

        return {
            "present_today": present,
            "absent_today": absent,
            "half_day_today": half_day,
            "on_leave_today": on_leave,
            "late_arrivals": late,
            "early_exits": early,
            "not_marked": not_marked,
            "on_break_today": on_break_today,
            "pending_biometrics": pending_biometrics,
        }

    async def get_shift_attendance_summary(
        self,
        org_id: int,
        target_date: datetime.date,
        branch_ids: list[int] | None = None,
        dept_ids: list[int] | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch target date's attendance counts grouped by shift."""
        from app.modules.shift.models import Shift, ShiftAssignment

        # 1. Fetch all non-deleted shifts in the organization
        shifts_stmt = select(Shift).where(
            Shift.org_id == org_id,
            Shift.is_deleted.is_(False),
        )
        shifts_res = await self.session.execute(shifts_stmt)
        shifts = shifts_res.scalars().all()

        if not shifts:
            return []

        # 2. Build filters for employees
        emp_filter = [
            Employee.org_id == org_id,
            Employee.is_deleted.is_(False),
            Employee.employment_status == "active",
        ]
        if branch_ids:
            emp_filter.append(Employee.master_branch_id.in_(branch_ids))
        if dept_ids:
            emp_filter.append(Employee.dept_id.in_(dept_ids))

        # 3. Get total employees assigned to each shift on target_date
        assignment_stmt = (
            select(
                ShiftAssignment.shift_id,
                func.count(ShiftAssignment.employee_id).label("total_employees")
            )
            .join(Employee, Employee.employee_id == ShiftAssignment.employee_id)
            .where(
                ShiftAssignment.org_id == org_id,
                ShiftAssignment.effective_from <= target_date,
                (ShiftAssignment.effective_to.is_(None) | (ShiftAssignment.effective_to >= target_date)),
                *emp_filter
            )
            .group_by(ShiftAssignment.shift_id)
        )
        assignments_res = await self.session.execute(assignment_stmt)
        assignments_map = {row.shift_id: row.total_employees for row in assignments_res.all()}

        # 4. Get attendance statistics from AttendanceDay for target_date grouped by shift_id
        attendance_stmt = (
            select(
                AttendanceDay.shift_id,
                AttendanceDay.status,
                AttendanceDay.late_minutes,
                func.count(AttendanceDay.id).label("count")
            )
            .join(Employee, Employee.employee_id == AttendanceDay.employee_id)
            .where(
                AttendanceDay.org_id == org_id,
                AttendanceDay.attendance_date == target_date,
                *emp_filter
            )
            .group_by(AttendanceDay.shift_id, AttendanceDay.status, AttendanceDay.late_minutes)
        )
        attendance_res = await self.session.execute(attendance_stmt)
        attendance_rows = attendance_res.all()

        # Aggregate attendance counts per shift
        stats_map = {}
        for row in attendance_rows:
            sid = row.shift_id
            if sid not in stats_map:
                stats_map[sid] = {"present": 0, "late": 0, "absent": 0, "on_leave": 0}
            
            status = row.status
            late_mins = row.late_minutes or 0
            count = row.count

            if status in ("present", "half_day"):
                stats_map[sid]["present"] += count
                if late_mins > 0:
                    stats_map[sid]["late"] += count
            elif status == "absent":
                stats_map[sid]["absent"] += count
            elif status == "on_leave":
                stats_map[sid]["on_leave"] += count

        # 5. Combine and construct response list
        results = []
        for shift in shifts:
            sid = shift.shift_id
            total_emp = assignments_map.get(sid, 0)
            stats = stats_map.get(sid, {"present": 0, "late": 0, "absent": 0, "on_leave": 0})
            
            present = stats["present"]
            late = stats["late"]
            db_absent = stats["absent"]
            on_leave = stats["on_leave"]

            # Employees assigned to shift but not marked are considered absent
            unmarked = max(0, total_emp - (present + db_absent + on_leave))
            absent = db_absent + unmarked

            results.append({
                "shift_id": sid,
                "shift_name": shift.shift_name,
                "total_employees": total_emp,
                "present": present,
                "late": late,
                "absent": absent,
                "on_leave": on_leave,
            })

        return results

    async def get_attendance_trend(
        self,
        org_id: int,
        date_from: datetime.date,
        date_to: datetime.date,
        branch_ids: list[int] | None = None,
        dept_ids: list[int] | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch daily attendance counts over a date range."""
        emp_filter = [
            Employee.org_id == org_id,
            Employee.is_deleted.is_(False),
        ]
        if branch_ids:
            emp_filter.append(Employee.master_branch_id.in_(branch_ids))
        if dept_ids:
            emp_filter.append(Employee.dept_id.in_(dept_ids))

        stmt = (
            select(
                AttendanceDay.attendance_date,
                func.sum(case((AttendanceDay.status == "present", 1), else_=0)).label(
                    "present"
                ),
                func.sum(case((AttendanceDay.status == "absent", 1), else_=0)).label("absent"),
                func.sum(
                    case(
                        (
                            and_(
                                AttendanceDay.status == "present",
                                AttendanceDay.late_minutes > 0,
                            ),
                            1,
                        ),
                        else_=0,
                    )
                ).label("late"),
            )
            .join(Employee, AttendanceDay.employee_id == Employee.employee_id)
            .where(
                AttendanceDay.org_id == org_id,
                AttendanceDay.attendance_date.between(date_from, date_to),
                *emp_filter,
            )
            .group_by(AttendanceDay.attendance_date)
            .order_by(AttendanceDay.attendance_date)
        )
        res = await self.session.execute(stmt)
        return [
            {
                "date": row[0],
                "present": int(row[1] or 0),
                "absent": int(row[2] or 0),
                "late": int(row[3] or 0),
            }
            for row in res.all()
        ]

    async def get_leave_summary(
        self,
        org_id: int,
        branch_ids: list[int] | None = None,
        dept_ids: list[int] | None = None,
        date_from: datetime.date | None = None,
        date_to: datetime.date | None = None,
    ) -> dict[str, Any]:
        """Fetch counts of leave requests (total, pending, approved, rejected)."""
        emp_filter = [
            Employee.org_id == org_id,
            Employee.is_deleted.is_(False),
        ]
        if branch_ids:
            emp_filter.append(Employee.master_branch_id.in_(branch_ids))
        if dept_ids:
            emp_filter.append(Employee.dept_id.in_(dept_ids))

        stmt = (
            select(
                LeaveRequest.status,
                func.count(LeaveRequest.id),
            )
            .join(Employee, LeaveRequest.employee_id == Employee.employee_id)
            .where(*emp_filter)
        )
        if date_from:
            stmt = stmt.where(LeaveRequest.start_date >= date_from)
        if date_to:
            stmt = stmt.where(LeaveRequest.start_date <= date_to)

        stmt = stmt.group_by(LeaveRequest.status)
        res = await self.session.execute(stmt)

        counts = dict(res.all())
        pending = counts.get("pending", 0)
        approved = counts.get("approved", 0)
        rejected = counts.get("rejected", 0)
        total = pending + approved + rejected

        return {
            "total_requests": total,
            "pending": pending,
            "approved": approved,
            "rejected": rejected,
        }

    async def get_leave_type_breakdown(
        self,
        org_id: int,
        branch_ids: list[int] | None = None,
        dept_ids: list[int] | None = None,
        date_from: datetime.date | None = None,
        date_to: datetime.date | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch breakdown of leave requests by leave type."""
        emp_filter = [
            Employee.org_id == org_id,
            Employee.is_deleted.is_(False),
        ]
        if branch_ids:
            emp_filter.append(Employee.master_branch_id.in_(branch_ids))
        if dept_ids:
            emp_filter.append(Employee.dept_id.in_(dept_ids))

        stmt = (
            select(
                LeaveType.name,
                func.count(LeaveRequest.id),
            )
            .join(LeaveType, LeaveRequest.leave_type_id == LeaveType.id)
            .join(Employee, LeaveRequest.employee_id == Employee.employee_id)
            .where(*emp_filter)
        )
        if date_from:
            stmt = stmt.where(LeaveRequest.start_date >= date_from)
        if date_to:
            stmt = stmt.where(LeaveRequest.start_date <= date_to)

        stmt = stmt.group_by(LeaveType.name).order_by(desc(func.count(LeaveRequest.id)))
        res = await self.session.execute(stmt)

        return [{"leave_type": name, "count": count} for name, count in res.all()]

    async def get_pending_approvals_summary(
        self,
        org_id: int,
        branch_ids: list[int] | None = None,
        dept_ids: list[int] | None = None,
    ) -> dict[str, Any]:
        """Fetch pending approvals count and breakdown by request type."""
        emp_filter = [
            Employee.org_id == org_id,
            Employee.is_deleted.is_(False),
        ]
        if branch_ids:
            emp_filter.append(Employee.master_branch_id.in_(branch_ids))
        if dept_ids:
            emp_filter.append(Employee.dept_id.in_(dept_ids))

        stmt = (
            select(
                ApprovalRequest.request_type,
                func.count(ApprovalRequest.id),
            )
            .join(Employee, ApprovalRequest.employee_id == Employee.employee_id)
            .where(
                ApprovalRequest.org_id == org_id,
                ApprovalRequest.status == "pending",
                *emp_filter,
            )
            .group_by(ApprovalRequest.request_type)
        )
        res = await self.session.execute(stmt)
        by_type = dict(res.all())

        pending_approvals = sum(by_type.values())
        return {
            "pending_approvals": pending_approvals,
            "by_request_type": {
                "attendance": by_type.get("attendance", 0),
                "leave": by_type.get("leave", 0),
                "login_reset": by_type.get("login_reset", 0),
            },
        }

    async def get_recent_approvals(
        self,
        org_id: int,
        limit: int = 5,
        branch_ids: list[int] | None = None,
        dept_ids: list[int] | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch recent resolved (approved/rejected) approval requests."""
        emp_filter = [
            Employee.org_id == org_id,
            Employee.is_deleted.is_(False),
        ]
        if branch_ids:
            emp_filter.append(Employee.master_branch_id.in_(branch_ids))
        if dept_ids:
            emp_filter.append(Employee.dept_id.in_(dept_ids))

        stmt = (
            select(
                ApprovalRequest.id,
                ApprovalRequest.request_type,
                ApprovalRequest.status,
                Employee.employee_name,
                ApprovalRequest.requested_at,
            )
            .join(Employee, ApprovalRequest.employee_id == Employee.employee_id)
            .where(
                ApprovalRequest.org_id == org_id,
                ApprovalRequest.status.in_(["approved", "rejected"]),
                *emp_filter,
            )
            .order_by(desc(ApprovalRequest.reviewed_at))
            .limit(limit)
        )
        res = await self.session.execute(stmt)
        return [
            {
                "id": row[0],
                "request_type": row[1],
                "status": row[2],
                "requester_name": row[3],
                "submitted_at": row[4],
            }
            for row in res.all()
        ]

    async def get_payroll_summary(self, org_id: int) -> dict[str, Any]:
        """Fetch current salary cycle and run summary."""
        cycle_stmt = (
            select(
                PayrollSalaryCycle.id,
                PayrollSalaryCycle.cycle_date,
                PayrollSalaryCycle.is_finalized,
                PayrollSalaryCycle.payroll_group_id,
            )
            .join(PayrollGroup, PayrollSalaryCycle.payroll_group_id == PayrollGroup.id)
            .where(
                PayrollGroup.org_id == org_id,
                PayrollGroup.is_deleted.is_(False),
            )
            .order_by(desc(PayrollSalaryCycle.cycle_date))
            .limit(1)
        )
        cycle_res = await self.session.execute(cycle_stmt)
        cycle = cycle_res.first()

        if not cycle:
            return {
                "current_cycle_id": None,
                "current_cycle_name": None,
                "is_finalized": False,
                "status": "draft",
                "finalized_amount": Decimal("0.00"),
                "payment_status_breakdown": {"paid": 0, "unpaid": 0},
                "headcount": 0,
            }

        cycle_id, cycle_date, is_finalized, pg_id = cycle
        cycle_name = cycle_date.strftime("%B %Y")

        run_stmt = select(FinalizedPayrollRun).where(
            FinalizedPayrollRun.org_id == org_id,
            FinalizedPayrollRun.payroll_group_id == pg_id,
            FinalizedPayrollRun.cycle_from <= cycle_date,
            FinalizedPayrollRun.cycle_to >= cycle_date,
            FinalizedPayrollRun.is_definalized.is_(False),
        )
        run_res = await self.session.execute(run_stmt)
        run = run_res.scalar_one_or_none()

        if run:
            hc_stmt = select(func.count(PayrollComputedRow.id)).where(
                PayrollComputedRow.finalized_run_id == run.id
            )
            hc_res = await self.session.execute(hc_stmt)
            headcount = hc_res.scalar() or 0

            status = run.payment_status
            if status == "paid":
                breakdown = {"paid": headcount, "unpaid": 0}
            elif status == "pending":
                breakdown = {"paid": 0, "unpaid": headcount}
            else:
                breakdown = {"paid": headcount // 2, "unpaid": headcount - (headcount // 2)}

            return {
                "current_cycle_id": cycle_id,
                "current_cycle_name": cycle_name,
                "is_finalized": True,
                "status": "finalized",
                "finalized_amount": run.finalized_amount,
                "payment_status_breakdown": breakdown,
                "headcount": headcount,
            }
        else:
            hc_stmt = select(func.count(Employee.employee_id)).where(
                Employee.org_id == org_id,
                Employee.is_deleted.is_(False),
                Employee.payroll_group_id == pg_id,
            )
            hc_res = await self.session.execute(hc_stmt)
            headcount = hc_res.scalar() or 0

            return {
                "current_cycle_id": cycle_id,
                "current_cycle_name": cycle_name,
                "is_finalized": False,
                "status": "processing",
                "finalized_amount": Decimal("0.00"),
                "payment_status_breakdown": {"paid": 0, "unpaid": headcount},
                "headcount": headcount,
            }

    async def get_settlement_summary(self, org_id: int) -> dict[str, Any]:
        """Fetch settlement KPIs including active loans and outstanding arrears."""
        active_stmt = select(func.count(EmployeeLoanAdvance.id)).where(
            EmployeeLoanAdvance.org_id == org_id,
            EmployeeLoanAdvance.status == "active",
        )
        active_res = await self.session.execute(active_stmt)
        active_loans = active_res.scalar() or 0

        closed_stmt = select(func.count(EmployeeLoanAdvance.id)).where(
            EmployeeLoanAdvance.org_id == org_id,
            EmployeeLoanAdvance.status == "closed",
        )
        closed_res = await self.session.execute(closed_stmt)
        closed_loans = closed_res.scalar() or 0

        loans_stmt = select(func.sum(EmployeeLoanAdvance.outstanding_amount)).where(
            EmployeeLoanAdvance.org_id == org_id,
            EmployeeLoanAdvance.status == "active",
        )
        loans_res = await self.session.execute(loans_stmt)
        outstanding_loans = loans_res.scalar() or Decimal("0.00")

        arrears_stmt = select(func.sum(EmployeeArrears.outstanding_arrears)).where(
            EmployeeArrears.org_id == org_id,
        )
        arrears_res = await self.session.execute(arrears_stmt)
        outstanding_arrears = arrears_res.scalar() or Decimal("0.00")

        return {
            "active_loans_advances": active_loans,
            "closed_loans_advances": closed_loans,
            "total_outstanding_loans_advances": outstanding_loans,
            "total_outstanding_arrears": outstanding_arrears,
        }

    async def get_hardware_dashboard(self, org_id: int) -> dict[str, Any]:
        """Fetch status summary of biometric devices."""
        stmt = (
            select(
                BiometricDevice.status,
                func.count(BiometricDevice.id),
            )
            .where(
                BiometricDevice.org_id == org_id,
                BiometricDevice.is_active.is_(True),
            )
            .group_by(BiometricDevice.status)
        )
        res = await self.session.execute(stmt)
        by_status = dict(res.all())

        sync_stmt = select(func.max(BiometricDevice.last_sync_at)).where(
            BiometricDevice.org_id == org_id,
            BiometricDevice.is_active.is_(True),
        )
        sync_res = await self.session.execute(sync_stmt)
        last_sync = sync_res.scalar()

        return {
            "online_devices": by_status.get("online", 0),
            "offline_devices": by_status.get("offline", 0),
            "disabled_devices": by_status.get("disabled", 0),
            "maintenance_devices": by_status.get("maintenance", 0),
            "last_device_sync": last_sync,
        }

    async def get_notification_dashboard(
        self, org_id: int, user_id: int, limit: int = 5
    ) -> dict[str, Any]:
        """Fetch unread count and recent notifications for a user."""
        unread_stmt = select(func.count(NotificationRecipient.id)).where(
            NotificationRecipient.org_id == org_id,
            NotificationRecipient.user_id == user_id,
            NotificationRecipient.read_at.is_(None),
            NotificationRecipient.deleted_at.is_(None),
        )
        unread_res = await self.session.execute(unread_stmt)
        unread_count = unread_res.scalar() or 0

        recent_stmt = (
            select(
                Notification.id,
                Notification.title,
                Notification.notification_type,
                Notification.priority,
                Notification.created_at,
            )
            .join(NotificationRecipient, Notification.id == NotificationRecipient.notification_id)
            .where(
                NotificationRecipient.org_id == org_id,
                NotificationRecipient.user_id == user_id,
                NotificationRecipient.deleted_at.is_(None),
            )
            .order_by(desc(Notification.created_at))
            .limit(limit)
        )
        recent_res = await self.session.execute(recent_stmt)
        recent = [
            {
                "id": row[0],
                "title": row[1],
                "notification_type": row[2],
                "priority": row[3],
                "created_at": row[4],
            }
            for row in recent_res.all()
        ]

        return {
            "unread_count": unread_count,
            "recent": recent,
        }

    async def get_recent_activities(
        self,
        org_id: int,
        limit: int = 10,
        branch_ids: list[int] | None = None,
        dept_ids: list[int] | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch recent activity logs scoped by branch and department."""
        stmt = select(
            ActivityLog.id,
            ActivityLog.module,
            ActivityLog.sub_module,
            ActivityLog.title,
            ActivityLog.description,
            ActivityLog.performed_by_name,
            ActivityLog.logged_at,
        ).where(ActivityLog.org_id == org_id)

        if branch_ids or dept_ids:
            stmt = stmt.join(
                Employee, ActivityLog.employee_id == Employee.employee_id, isouter=True
            )
            conditions = []
            if branch_ids:
                conditions.append(Employee.master_branch_id.in_(branch_ids))
            if dept_ids:
                conditions.append(Employee.dept_id.in_(dept_ids))
            stmt = stmt.where(or_(ActivityLog.employee_id.is_(None), and_(*conditions)))

        stmt = stmt.order_by(desc(ActivityLog.logged_at)).limit(limit)
        res = await self.session.execute(stmt)
        return [
            {
                "id": row[0],
                "module": row[1],
                "sub_module": row[2],
                "title": row[3],
                "description": row[4],
                "performed_by_name": row[5],
                "logged_at": row[6],
            }
            for row in res.all()
        ]

    async def get_employee_growth_chart(
        self,
        org_id: int,
        date_from: datetime.date,
        date_to: datetime.date,
        branch_ids: list[int] | None = None,
        dept_ids: list[int] | None = None,
    ) -> dict[str, Any]:
        """Fetch cumulative employee growth counts by month."""
        year_month = func.to_char(Employee.date_of_joining, "YYYY-MM")
        stmt = select(
            year_month,
            func.count(Employee.employee_id),
        ).where(
            Employee.org_id == org_id,
            Employee.is_deleted.is_(False),
            Employee.date_of_joining <= date_to,
        )
        if branch_ids:
            stmt = stmt.where(Employee.master_branch_id.in_(branch_ids))
        if dept_ids:
            stmt = stmt.where(Employee.dept_id.in_(dept_ids))

        stmt = stmt.group_by(year_month).order_by(year_month)
        res = await self.session.execute(stmt)
        monthly_hires = res.all()

        labels: list[str] = []
        growth: list[float] = []
        cumulative = 0

        from_str = date_from.strftime("%Y-%m")

        for ym, count in monthly_hires:
            if ym is None:
                continue
            cumulative += count
            if ym >= from_str:
                labels.append(ym)
                growth.append(float(cumulative))

        if not labels:
            labels = [from_str]
            growth = [0.0]

        return {
            "labels": labels,
            "series": [
                {
                    "name": "Total Employees",
                    "points": growth,
                }
            ],
            "generated_at": datetime.datetime.now(datetime.timezone.utc),  # noqa: UP017
        }

    async def get_leave_trend_chart(
        self,
        org_id: int,
        date_from: datetime.date,
        date_to: datetime.date,
        branch_ids: list[int] | None = None,
        dept_ids: list[int] | None = None,
    ) -> dict[str, Any]:
        """Fetch daily leave request counts categorized by status."""
        emp_filter = [
            Employee.org_id == org_id,
            Employee.is_deleted.is_(False),
        ]
        if branch_ids:
            emp_filter.append(Employee.master_branch_id.in_(branch_ids))
        if dept_ids:
            emp_filter.append(Employee.dept_id.in_(dept_ids))

        stmt = (
            select(
                LeaveRequest.start_date,
                LeaveRequest.status,
                func.count(LeaveRequest.id),
            )
            .join(Employee, LeaveRequest.employee_id == Employee.employee_id)
            .where(
                LeaveRequest.start_date.between(date_from, date_to),
                *emp_filter,
            )
            .group_by(LeaveRequest.start_date, LeaveRequest.status)
            .order_by(LeaveRequest.start_date)
        )
        res = await self.session.execute(stmt)

        data: dict[datetime.date, dict[str, int]] = {}
        for start_date, status, count in res.all():
            if start_date not in data:
                data[start_date] = {"pending": 0, "approved": 0, "rejected": 0}
            data[start_date][status] = count

        labels: list[str] = []
        pending_points: list[float] = []
        approved_points: list[float] = []
        rejected_points: list[float] = []

        curr = date_from
        while curr <= date_to:
            labels.append(curr.strftime("%Y-%m-%d"))
            day_data = data.get(curr, {"pending": 0, "approved": 0, "rejected": 0})
            pending_points.append(float(day_data["pending"]))
            approved_points.append(float(day_data["approved"]))
            rejected_points.append(float(day_data["rejected"]))
            curr += datetime.timedelta(days=1)

        return {
            "labels": labels,
            "series": [
                {"name": "Pending", "points": pending_points},
                {"name": "Approved", "points": approved_points},
                {"name": "Rejected", "points": rejected_points},
            ],
            "generated_at": datetime.datetime.now(datetime.timezone.utc),  # noqa: UP017
        }

    async def get_payroll_trend_chart(self, org_id: int, limit: int = 6) -> dict[str, Any]:
        """Fetch trend of finalized payroll runs."""
        stmt = (
            select(
                FinalizedPayrollRun.cycle_from,
                FinalizedPayrollRun.finalized_amount,
            )
            .where(
                FinalizedPayrollRun.org_id == org_id,
                FinalizedPayrollRun.is_definalized.is_(False),
            )
            .order_by(FinalizedPayrollRun.cycle_from)
            .limit(limit)
        )
        res = await self.session.execute(stmt)

        labels: list[str] = []
        amounts: list[float] = []

        for cycle_from, amt in res.all():
            labels.append(cycle_from.strftime("%B %Y"))
            amounts.append(float(amt))

        if not labels:
            labels = ["No Data"]
            amounts = [0.0]

        return {
            "labels": labels,
            "series": [
                {
                    "name": "Payroll Costs",
                    "points": amounts,
                }
            ],
            "generated_at": datetime.datetime.now(datetime.timezone.utc),  # noqa: UP017
        }

    async def get_department_attendance_chart(
        self,
        org_id: int,
        target_date: datetime.date,
        branch_ids: list[int] | None = None,
        dept_ids: list[int] | None = None,
    ) -> dict[str, Any]:
        """Fetch attendance counts broken down by department for a specific date."""
        emp_filter = [
            Employee.org_id == org_id,
            Employee.is_deleted.is_(False),
        ]
        if branch_ids:
            emp_filter.append(Employee.master_branch_id.in_(branch_ids))
        if dept_ids:
            emp_filter.append(Employee.dept_id.in_(dept_ids))

        stmt = (
            select(
                Department.dept_name,
                AttendanceDay.status,
                func.count(AttendanceDay.id),
            )
            .join(Employee, AttendanceDay.employee_id == Employee.employee_id)
            .join(Department, Employee.dept_id == Department.dept_id)
            .where(
                AttendanceDay.org_id == org_id,
                AttendanceDay.attendance_date == target_date,
                *emp_filter,
            )
            .group_by(Department.dept_name, AttendanceDay.status)
        )
        res = await self.session.execute(stmt)

        data: dict[str, dict[str, int]] = {}
        for dept_name, status, count in res.all():
            if dept_name not in data:
                data[dept_name] = {"present": 0, "absent": 0}
            if status == "present":
                data[dept_name]["present"] = count
            elif status == "absent":
                data[dept_name]["absent"] = count

        labels = sorted(data.keys())
        present_points = [float(data[d]["present"]) for d in labels]
        absent_points = [float(data[d]["absent"]) for d in labels]

        return {
            "labels": labels,
            "series": [
                {"name": "Present", "points": present_points},
                {"name": "Absent", "points": absent_points},
            ],
            "generated_at": datetime.datetime.now(datetime.timezone.utc),  # noqa: UP017
        }

    async def get_branch_attendance_chart(
        self,
        org_id: int,
        target_date: datetime.date,
        branch_ids: list[int] | None = None,
        dept_ids: list[int] | None = None,
    ) -> dict[str, Any]:
        """Fetch attendance counts broken down by branch for a specific date."""
        emp_filter = [
            Employee.org_id == org_id,
            Employee.is_deleted.is_(False),
        ]
        if branch_ids:
            emp_filter.append(Employee.master_branch_id.in_(branch_ids))
        if dept_ids:
            emp_filter.append(Employee.dept_id.in_(dept_ids))

        stmt = (
            select(
                Branch.branch_name,
                AttendanceDay.status,
                func.count(AttendanceDay.id),
            )
            .join(Employee, AttendanceDay.employee_id == Employee.employee_id)
            .join(Branch, Employee.master_branch_id == Branch.branch_id)
            .where(
                AttendanceDay.org_id == org_id,
                AttendanceDay.attendance_date == target_date,
                *emp_filter,
            )
            .group_by(Branch.branch_name, AttendanceDay.status)
        )
        res = await self.session.execute(stmt)

        data: dict[str, dict[str, int]] = {}
        for branch_name, status, count in res.all():
            if branch_name not in data:
                data[branch_name] = {"present": 0, "absent": 0}
            if status == "present":
                data[branch_name]["present"] = count
            elif status == "absent":
                data[branch_name]["absent"] = count

        labels = sorted(data.keys())
        present_points = [float(data[b]["present"]) for b in labels]
        absent_points = [float(data[b]["absent"]) for b in labels]

        return {
            "labels": labels,
            "series": [
                {"name": "Present", "points": present_points},
                {"name": "Absent", "points": absent_points},
            ],
            "generated_at": datetime.datetime.now(datetime.timezone.utc),  # noqa: UP017
        }

    async def get_pending_biometrics_employees(
        self,
        org_id: int,
        branch_ids: list[int] | None = None,
        dept_ids: list[int] | None = None,
        search: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[dict[str, Any]], int]:
        """Fetch paginated list of employees with pending biometric enrollment."""
        from app.modules.employee.models.satellites import EmployeeBiometric

        # Subquery to find all employees with non-deleted biometric records
        biometric_subq = (
            select(EmployeeBiometric.employee_id)
            .where(
                EmployeeBiometric.is_deleted.is_(False)
            )
            .subquery()
        )

        # Base filters
        filters = [
            Employee.org_id == org_id,
            Employee.is_deleted.is_(False),
            ~Employee.employee_id.in_(select(biometric_subq)),
        ]

        if branch_ids:
            filters.append(Employee.master_branch_id.in_(branch_ids))
        if dept_ids:
            filters.append(Employee.dept_id.in_(dept_ids))

        if search:
            search_pattern = f"%{search}%"
            filters.append(
                or_(
                    Employee.employee_code.ilike(search_pattern),
                    Employee.employee_name.ilike(search_pattern),
                )
            )

        # Count query
        count_stmt = select(func.count(Employee.employee_id)).where(*filters)
        count_res = await self.session.execute(count_stmt)
        total_records = count_res.scalar() or 0

        # Query to fetch records
        stmt = (
            select(
                Employee.employee_id,
                Employee.employee_code,
                Employee.employee_name,
                Department.dept_name.label("department"),
                Designation.designation_name.label("designation"),
                Branch.branch_name.label("branch"),
                Employee.created_at,
            )
            .outerjoin(Department, Employee.dept_id == Department.dept_id)
            .outerjoin(Designation, Employee.designation_id == Designation.designation_id)
            .outerjoin(Branch, Employee.master_branch_id == Branch.branch_id)
            .where(*filters)
            .order_by(Employee.employee_id.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )

        res = await self.session.execute(stmt)
        items = []
        for row in res.all():
            items.append({
                "employee_id": row.employee_id,
                "employee_code": row.employee_code,
                "employee_name": row.employee_name,
                "department": row.department,
                "designation": row.designation,
                "branch": row.branch,
                "biometric_status": "pending",
                "enrollment_status": "pending",
                "created_at": row.created_at,
            })

        return items, total_records

