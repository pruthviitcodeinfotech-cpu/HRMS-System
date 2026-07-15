"""
Development-only seed script for Dashboard testing.

Populates realistic demo data for:
  - Branches, Departments, Designations
  - Shifts + ShiftDayTimings + ShiftAssignments
  - Biometric Devices
  - Leave Types + LeaveRequests
  - Employees (15 total, across 2 branches / 4 departments)
  - Employee Biometric Enrollments (10 enrolled, 5 pending → 5 pending_biometrics)
  - AttendanceDays + AttendancePunches for 2026-07-15
  - ApprovalRequests (3 pending: attendance, leave, login_reset)

Run:
  DATABASE_URL=postgresql+asyncpg://hrms:hrms@localhost:5432/hrms \\
  .venv/bin/python scripts/seed_dashboard.py

Idempotent: safe to run multiple times without creating duplicates.
"""

import asyncio
import datetime
from decimal import Decimal

from sqlalchemy import select

from app.core.database.session import get_session

# --------------------------------------------------------------------------
# Model imports — ALL models with FK → users must be imported so that
# SQLAlchemy's mapper can resolve the `users` table before any flush.
# --------------------------------------------------------------------------
from app.modules.rbac.models.user import User  # noqa: F401  — resolves FK
from app.modules.employee.models.organization import (
    Branch,
    Department,
    Designation,
    Organization,
)
from app.modules.employee.models.employee import Employee
from app.modules.employee.models.satellites import EmployeeBiometric
from app.modules.shift.models.shift import Shift, ShiftDayTiming
from app.modules.shift.models.assignment import ShiftAssignment
from app.modules.attendance.models import AttendanceDay, AttendancePunch
from app.modules.hardware.models import BiometricDevice
from app.modules.approvals.models import (
    ApprovalRequest,
    AttendanceRegularizationRequest,
    LoginResetRequest,
)
from app.modules.leave.models.leave import LeaveRequest, LeaveType

# Target date for attendance seeding
TARGET_DATE = datetime.date(2026, 7, 15)
UTC = datetime.timezone.utc


async def main() -> None:  # noqa: C901 — long but intentionally linear
    async with get_session() as session:
        print("=" * 60)
        print("Dashboard Seed — starting")
        print("=" * 60)

        # ------------------------------------------------------------------ #
        # 1. Organization (must already exist — created by seed_login.py)     #
        # ------------------------------------------------------------------ #
        org = await session.get(Organization, 1)
        if not org:
            raise RuntimeError(
                "Organization ID 1 not found. Run seed_login.py first."
            )
        print(f"✓ Organization '{org.org_name}' (ID 1) exists")

        # ------------------------------------------------------------------ #
        # 2. Branches                                                          #
        # ------------------------------------------------------------------ #
        branches = [
            (1, "HQ Branch", "Mumbai", "Maharashtra"),
            (2, "West Branch", "Pune", "Maharashtra"),
        ]
        for b_id, b_name, city, state in branches:
            if not await session.get(Branch, b_id):
                session.add(
                    Branch(
                        branch_id=b_id,
                        org_id=1,
                        branch_name=b_name,
                        city=city,
                        state=state,
                        country="India",
                        is_active=True,
                    )
                )
                print(f"  ✦ Seeded Branch '{b_name}' (ID {b_id})")
            else:
                print(f"  · Branch '{b_name}' (ID {b_id}) already exists")
        await session.flush()

        # ------------------------------------------------------------------ #
        # 3. Departments                                                       #
        # ------------------------------------------------------------------ #
        departments = [
            (1, "Engineering"),
            (2, "Human Resources"),
            (3, "Sales"),
            (4, "Support"),
        ]
        for d_id, d_name in departments:
            if not await session.get(Department, d_id):
                session.add(
                    Department(dept_id=d_id, org_id=1, dept_name=d_name, is_active=True)
                )
                print(f"  ✦ Seeded Department '{d_name}'")
            else:
                print(f"  · Department '{d_name}' already exists")
        await session.flush()

        # ------------------------------------------------------------------ #
        # 4. Designations                                                      #
        # ------------------------------------------------------------------ #
        designations = [
            (1, "Software Engineer"),
            (2, "HR Manager"),
            (3, "Sales Lead"),
            (4, "Support Executive"),
        ]
        for des_id, des_name in designations:
            if not await session.get(Designation, des_id):
                session.add(
                    Designation(
                        designation_id=des_id,
                        org_id=1,
                        designation_name=des_name,
                        is_active=True,
                    )
                )
                print(f"  ✦ Seeded Designation '{des_name}'")
            else:
                print(f"  · Designation '{des_name}' already exists")
        await session.flush()

        # ------------------------------------------------------------------ #
        # 5. Shifts + ShiftDayTimings                                          #
        # ------------------------------------------------------------------ #
        # (shift_id, name, start_time, end_time)
        shifts_cfg = [
            (1, "Day Shift",     datetime.time(9, 0),  datetime.time(18, 0)),
            (2, "Night Shift",   datetime.time(22, 0), datetime.time(7, 0)),
            (3, "Morning Shift", datetime.time(6, 0),  datetime.time(14, 0)),
        ]
        for s_id, s_name, s_start, s_end in shifts_cfg:
            if not await session.get(Shift, s_id):
                session.add(
                    Shift(shift_id=s_id, org_id=1, shift_name=s_name, shift_type="fixed")
                )
                await session.flush()
                for day in range(7):
                    session.add(
                        ShiftDayTiming(
                            shift_id=s_id,
                            day_of_week=day,
                            start_time=s_start,
                            end_time=s_end,
                            is_working_day=True,
                        )
                    )
                await session.flush()
                print(f"  ✦ Seeded Shift '{s_name}' with 7-day timings")
            else:
                print(f"  · Shift '{s_name}' (ID {s_id}) already exists")

        # ------------------------------------------------------------------ #
        # 6. Biometric Devices                                                 #
        # ------------------------------------------------------------------ #
        devices_cfg = [
            (1, "Main Entrance Fingerprint", "DEV-FP-01", "FP001SN", "online"),
            (2, "West Wing Facial Scanner",  "DEV-FC-02", "FC002SN", "offline"),
        ]
        for dev_id, dev_name, dev_code, serial, status in devices_cfg:
            if not await session.get(BiometricDevice, dev_id):
                session.add(
                    BiometricDevice(
                        id=dev_id,
                        org_id=1,
                        branch_id=1,
                        device_name=dev_name,
                        device_code=dev_code,
                        serial_number=serial,
                        status=status,
                        protocol="tcp_ip",
                    )
                )
                print(f"  ✦ Seeded Device '{dev_name}' ({status})")
            else:
                print(f"  · Device '{dev_name}' (ID {dev_id}) already exists")
        await session.flush()

        # ------------------------------------------------------------------ #
        # 7. Leave Type                                                        #
        # ------------------------------------------------------------------ #
        if not await session.get(LeaveType, 1):
            session.add(
                LeaveType(
                    id=1,
                    org_id=1,
                    name="Annual Leave",
                    alias="AL",
                    auto_allocation_count=Decimal("12.00"),
                    allocation_frequency="yearly",
                    carry_forward_count=Decimal("0.00"),
                    carry_forward_frequency="yearly",
                    is_active=True,
                )
            )
            await session.flush()
            print("  ✦ Seeded Leave Type 'Annual Leave'")
        else:
            print("  · Leave Type 'Annual Leave' already exists")

        # ------------------------------------------------------------------ #
        # 8. Employees  (15 employees across 2 branches / 4 departments)      #
        # ------------------------------------------------------------------ #
        # (emp_id, code, name, branch_id, dept_id, desig_id, shift_id, gender)
        # gender CHECK: 'Male' | 'Female' | 'Other'
        employees_cfg = [
            (101, "EMP001", "Jignesh Patel",       1, 1, 1, 1, "Male"),
            (102, "EMP002", "Amit Sharma",          1, 1, 1, 1, "Male"),
            (103, "EMP003", "Priya Nair",           1, 1, 1, 1, "Female"),
            (104, "EMP004", "Rajesh Kumar",         1, 2, 2, 1, "Male"),
            (105, "EMP005", "Sneha Patil",          1, 3, 3, 2, "Female"),
            (106, "EMP006", "Rohan Mehta",          1, 4, 4, 3, "Male"),
            (107, "EMP007", "Karan Johar",          2, 1, 1, 2, "Male"),
            (108, "EMP008", "Deepika Padukone",     2, 1, 1, 1, "Female"),  # On Leave
            (109, "EMP009", "Ranveer Singh",        2, 3, 3, 1, "Male"),
            (110, "EMP010", "Alia Bhatt",           2, 4, 4, 3, "Female"),
            (111, "EMP011", "Ranbir Kapoor",        1, 1, 1, 1, "Male"),   # Late arrival
            (112, "EMP012", "Katrina Kaif",         1, 1, 1, 1, "Female"), # On break
            (113, "EMP013", "Vicky Kaushal",        1, 1, 1, 1, "Male"),   # On break
            (114, "EMP014", "Kiara Advani",         2, 1, 1, 2, "Female"), # Pending regularization
            (115, "EMP015", "Sidharth Malhotra",    2, 4, 4, 3, "Male"),
        ]
        for emp_id, code, name, b_id, d_id, des_id, sh_id, gender in employees_cfg:
            if not await session.get(Employee, emp_id):
                session.add(
                    Employee(
                        employee_id=emp_id,
                        org_id=1,
                        employee_code=code,
                        employee_name=name,
                        display_name=name,
                        mobile_country_code="+91",
                        mobile_number=f"98765{emp_id:05d}",
                        email=f"{code.lower()}@example.com",
                        gender=gender,
                        master_branch_id=b_id,
                        dept_id=d_id,
                        designation_id=des_id,
                        date_of_joining=datetime.date(2025, 1, 1),
                        employment_status="active",
                    )
                )
                print(f"  ✦ Seeded Employee '{name}' ({code})")
                await session.flush()
            else:
                print(f"  · Employee '{name}' (ID {emp_id}) already exists")

            # Shift Assignment
            sa_res = await session.execute(
                select(ShiftAssignment).where(
                    ShiftAssignment.employee_id == emp_id,
                    ShiftAssignment.shift_id == sh_id,
                )
            )
            if not sa_res.scalar_one_or_none():
                session.add(
                    ShiftAssignment(
                        org_id=1,
                        employee_id=emp_id,
                        shift_id=sh_id,
                        effective_from=datetime.date(2025, 1, 1),
                    )
                )
                await session.flush()

        # ------------------------------------------------------------------ #
        # 9. Biometric Enrollments (101–110 enrolled; 111–115 = pending)      #
        # ------------------------------------------------------------------ #
        for emp_id in range(101, 111):
            bio_res = await session.execute(
                select(EmployeeBiometric).where(
                    EmployeeBiometric.employee_id == emp_id,
                    EmployeeBiometric.biometric_type == "fingerprint",
                )
            )
            if not bio_res.scalar_one_or_none():
                session.add(
                    EmployeeBiometric(
                        employee_id=emp_id,
                        device_id=1,
                        biometric_type="fingerprint",
                        biometric_template="DUMMY_TEMPLATE_DATA",
                        registered_at=datetime.datetime(2025, 6, 1, 10, 0, tzinfo=UTC),
                        is_active=True,
                        is_deleted=False,
                    )
                )
                print(f"  ✦ Biometric enrolled for Employee ID {emp_id}")
        await session.flush()
        print("  · Employees 111–115: no biometric → pending_biometrics = 5")

        # ------------------------------------------------------------------ #
        # 10. Approved Leave for EMP008 on TARGET_DATE                        #
        # ------------------------------------------------------------------ #
        leave_res = await session.execute(
            select(LeaveRequest).where(
                LeaveRequest.employee_id == 108,
                LeaveRequest.start_date == TARGET_DATE,
            )
        )
        leave_108 = leave_res.scalar_one_or_none()
        if not leave_108:
            leave_108 = LeaveRequest(
                id=801,
                employee_id=108,
                leave_type_id=1,
                start_date=TARGET_DATE,
                end_date=TARGET_DATE,
                duration_days=Decimal("1.0"),
                reason="Family Event",
                status="approved",
                applied_on=datetime.datetime(2026, 7, 14, 10, 0, tzinfo=UTC),
            )
            session.add(leave_108)
            await session.flush()
            print("  ✦ Seeded approved leave for EMP008 (Deepika)")
        else:
            print("  · Leave for EMP008 already exists")

        # ------------------------------------------------------------------ #
        # 11. Attendance Days for TARGET_DATE                                  #
        # ------------------------------------------------------------------ #
        async def get_or_create_day(
            emp_id: int,
            shift_id: int,
            status: str,
            first_punch: datetime.datetime | None = None,
            late_minutes: int = 0,
            leave_id: int | None = None,
        ) -> AttendanceDay:
            res = await session.execute(
                select(AttendanceDay).where(
                    AttendanceDay.employee_id == emp_id,
                    AttendanceDay.attendance_date == TARGET_DATE,
                )
            )
            day = res.scalar_one_or_none()
            if not day:
                day = AttendanceDay(
                    org_id=1,
                    employee_id=emp_id,
                    attendance_date=TARGET_DATE,
                    shift_id=shift_id,
                    status=status,
                    first_punch_in=first_punch,
                    late_minutes=late_minutes,
                    leave_id=leave_id,
                    source="system",
                )
                session.add(day)
                await session.flush()
                print(f"  ✦ AttendanceDay EMP{emp_id:03d} → {status}")
            return day

        # present — working normally
        day_101 = await get_or_create_day(101, 1, "present", datetime.datetime(2026, 7, 15,  9,  2, tzinfo=UTC))
        day_102 = await get_or_create_day(102, 1, "present", datetime.datetime(2026, 7, 15,  9,  5, tzinfo=UTC))
        day_103 = await get_or_create_day(103, 1, "present", datetime.datetime(2026, 7, 15,  8, 55, tzinfo=UTC))
        day_104 = await get_or_create_day(104, 1, "present", datetime.datetime(2026, 7, 15,  9,  0, tzinfo=UTC))
        day_105 = await get_or_create_day(105, 2, "present", datetime.datetime(2026, 7, 15, 21, 58, tzinfo=UTC))
        day_109 = await get_or_create_day(109, 1, "present", datetime.datetime(2026, 7, 15,  9,  4, tzinfo=UTC))
        day_110 = await get_or_create_day(110, 3, "present", datetime.datetime(2026, 7, 15,  6,  1, tzinfo=UTC))
        day_115 = await get_or_create_day(115, 3, "present", datetime.datetime(2026, 7, 15,  6,  3, tzinfo=UTC))

        # absent
        await get_or_create_day(106, 3, "absent")
        await get_or_create_day(107, 2, "absent")

        # on leave
        await get_or_create_day(108, 1, "on_leave", leave_id=leave_108.id)

        # late arrival (111)
        day_111 = await get_or_create_day(
            111, 1, "present",
            first_punch=datetime.datetime(2026, 7, 15, 9, 45, tzinfo=UTC),
            late_minutes=45,
        )

        # on break (112, 113)
        day_112 = await get_or_create_day(112, 1, "present", datetime.datetime(2026, 7, 15,  9,  1, tzinfo=UTC))
        day_113 = await get_or_create_day(113, 1, "present", datetime.datetime(2026, 7, 15,  9,  3, tzinfo=UTC))

        # ------------------------------------------------------------------ #
        # 12. Attendance Punches                                               #
        # ------------------------------------------------------------------ #
        # punch_type CHECK: 'in' | 'out' | 'break_in' | 'break_out'
        # punch_source CHECK: 'biometric_device' | 'mobile_app' | 'web_portal' | 'manual_entry'
        punches_cfg = [
            # (emp_id, day_id, punch_type, punch_time, seq_no)
            (101, day_101.id, "in",        datetime.datetime(2026, 7, 15,  9,  2, tzinfo=UTC), 1),
            (102, day_102.id, "in",        datetime.datetime(2026, 7, 15,  9,  5, tzinfo=UTC), 1),
            (103, day_103.id, "in",        datetime.datetime(2026, 7, 15,  8, 55, tzinfo=UTC), 1),
            (104, day_104.id, "in",        datetime.datetime(2026, 7, 15,  9,  0, tzinfo=UTC), 1),
            (105, day_105.id, "in",        datetime.datetime(2026, 7, 15, 21, 58, tzinfo=UTC), 1),
            (109, day_109.id, "in",        datetime.datetime(2026, 7, 15,  9,  4, tzinfo=UTC), 1),
            (110, day_110.id, "in",        datetime.datetime(2026, 7, 15,  6,  1, tzinfo=UTC), 1),
            (115, day_115.id, "in",        datetime.datetime(2026, 7, 15,  6,  3, tzinfo=UTC), 1),
            (111, day_111.id, "in",        datetime.datetime(2026, 7, 15,  9, 45, tzinfo=UTC), 1),
            # EMP012 — check in then break_out (currently on break)
            (112, day_112.id, "in",        datetime.datetime(2026, 7, 15,  9,  1, tzinfo=UTC), 1),
            (112, day_112.id, "break_out", datetime.datetime(2026, 7, 15, 13,  0, tzinfo=UTC), 2),
            # EMP013 — check in then break_out (currently on break)
            (113, day_113.id, "in",        datetime.datetime(2026, 7, 15,  9,  3, tzinfo=UTC), 1),
            (113, day_113.id, "break_out", datetime.datetime(2026, 7, 15, 13,  5, tzinfo=UTC), 2),
        ]
        for emp_id, day_id, p_type, p_time, seq in punches_cfg:
            exists = await session.execute(
                select(AttendancePunch).where(
                    AttendancePunch.employee_id == emp_id,
                    AttendancePunch.punch_time == p_time,
                )
            )
            if not exists.scalar_one_or_none():
                session.add(
                    AttendancePunch(
                        org_id=1,
                        employee_id=emp_id,
                        attendance_day_id=day_id,
                        punch_type=p_type,
                        punch_time=p_time,
                        sequence_no=seq,
                        punch_source="biometric_device",
                        device_id=1,
                        is_valid=True,
                    )
                )
                print(f"  ✦ Punch '{p_type}' for EMP{emp_id:03d}")
        await session.flush()

        # ------------------------------------------------------------------ #
        # 13. Pending Approvals                                                #
        # ------------------------------------------------------------------ #

        # 13a. Attendance Regularization (EMP014)
        if not await session.get(AttendanceRegularizationRequest, 901):
            session.add(
                AttendanceRegularizationRequest(
                    id=901,
                    employee_id=114,
                    attendance_date=datetime.date(2026, 7, 14),
                    new_punch_time="09:00:00",
                    employee_reason="Forgot to punch in",
                    status="pending",
                )
            )
            await session.flush()
            print("  ✦ Seeded AttendanceRegularizationRequest 901")

        if not await session.get(ApprovalRequest, 501):
            session.add(
                ApprovalRequest(
                    id=501,
                    org_id=1,
                    request_type="attendance",
                    reference_id=901,
                    employee_id=114,
                    status="pending",
                    requested_at=datetime.datetime(2026, 7, 14, 18, 0, tzinfo=UTC),
                )
            )
            print("  ✦ Seeded ApprovalRequest 501 (attendance)")

        # 13b. Pending Leave Request (EMP009)
        leave_pending_res = await session.execute(
            select(LeaveRequest).where(LeaveRequest.id == 802)
        )
        if not leave_pending_res.scalar_one_or_none():
            session.add(
                LeaveRequest(
                    id=802,
                    employee_id=109,
                    leave_type_id=1,
                    start_date=datetime.date(2026, 7, 20),
                    end_date=datetime.date(2026, 7, 22),
                    duration_days=Decimal("3.0"),
                    reason="Personal work",
                    status="pending",
                    applied_on=datetime.datetime(2026, 7, 15, 11, 0, tzinfo=UTC),
                )
            )
            await session.flush()
            print("  ✦ Seeded pending LeaveRequest 802")

        if not await session.get(ApprovalRequest, 502):
            session.add(
                ApprovalRequest(
                    id=502,
                    org_id=1,
                    request_type="leave",
                    reference_id=802,
                    employee_id=109,
                    status="pending",
                    requested_at=datetime.datetime(2026, 7, 15, 11, 0, tzinfo=UTC),
                )
            )
            print("  ✦ Seeded ApprovalRequest 502 (leave)")

        # 13c. Login Reset Request (EMP003)
        if not await session.get(LoginResetRequest, 902):
            session.add(
                LoginResetRequest(
                    id=902,
                    employee_id=103,
                    request_subtype="device_change",
                    request_description="Priya Nair requested a mobile device reset.",
                    status="pending",
                    applied_on=datetime.datetime(2026, 7, 15, 12, 0, tzinfo=UTC),
                )
            )
            await session.flush()
            print("  ✦ Seeded LoginResetRequest 902")

        if not await session.get(ApprovalRequest, 503):
            session.add(
                ApprovalRequest(
                    id=503,
                    org_id=1,
                    request_type="login_reset",
                    reference_id=902,
                    employee_id=103,
                    status="pending",
                    requested_at=datetime.datetime(2026, 7, 15, 12, 0, tzinfo=UTC),
                )
            )
            print("  ✦ Seeded ApprovalRequest 503 (login_reset)")

        await session.flush()
        await session.commit()

        # ------------------------------------------------------------
        # Invalidate any stale dashboard cache entries for this org.
        # The dashboard KPI endpoint caches results for 5 minutes.
        # After seeding new data we must clear those keys so the UI
        # receives fresh values.
        from app.core.cache.redis import get_redis, cache_delete
        redis = get_redis()
        # Using Redis SCAN would be safer for large keyspaces, but for dev
        # the key pattern is limited and inexpensive.
        cache_keys = await redis.keys("dashboard:1:*")
        if cache_keys:
            await cache_delete(*cache_keys)
            print(f"Invalidated {len(cache_keys)} dashboard cache keys")
        # ------------------------------------------------------------

if __name__ == "__main__":
    asyncio.run(main())
