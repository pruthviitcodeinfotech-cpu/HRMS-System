"""
Idempotent script to seed realistic attendance records for QA/testing of Branch Wise Punch Report.
Generates data for 35 employees across 30 days (2026-06-01 to 2026-06-30).
"""

import asyncio
import datetime
from sqlalchemy import select, delete

from app.core.database.session import get_session
from app.modules.rbac.models.user import User
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

async def main():
    async with get_session() as session:
        print("=" * 60)
        print("Branch Wise Punch Report QA Seeder — Starting")
        print("=" * 60)

        # 1. Organization Check
        org = await session.get(Organization, 1)
        if not org:
            org = Organization(
                org_id=1,
                org_code="ORG1",
                org_name="Test Organization",
                is_active=True,
                is_deleted=False
            )
            session.add(org)
            await session.flush()
            print("✓ Seeded Organization ID 1")
        else:
            print("✓ Organization ID 1 exists")

        # 2. Branches Seeding (ensure branches 1 to 4 exist)
        branches_cfg = [
            (1, "HQ Branch", "Mumbai", "Maharashtra"),
            (2, "West Branch", "Pune", "Maharashtra"),
            (3, "East Branch", "Kolkata", "West Bengal"),
            (4, "South Branch", "Bengaluru", "Karnataka"),
        ]
        for b_id, b_name, city, state in branches_cfg:
            existing = await session.get(Branch, b_id)
            if not existing:
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
                print(f"  ✦ Seeded Branch: {b_name} (ID {b_id})")
            else:
                print(f"  · Branch {b_name} (ID {b_id}) already exists")
        await session.flush()

        # 3. Departments Seeding (ensure departments 1 to 5 exist)
        depts_cfg = [
            (1, "Engineering"),
            (2, "Human Resources"),
            (3, "Sales"),
            (4, "Support"),
            (5, "Marketing"),
        ]
        for d_id, d_name in depts_cfg:
            existing = await session.get(Department, d_id)
            if not existing:
                session.add(
                    Department(dept_id=d_id, org_id=1, dept_name=d_name, is_active=True)
                )
                print(f"  ✦ Seeded Department: {d_name} (ID {d_id})")
            else:
                print(f"  · Department {d_name} (ID {d_id}) already exists")
        await session.flush()

        # 4. Designations Seeding (ensure designations 1 to 5 exist)
        desigs_cfg = [
            (1, "Software Engineer"),
            (2, "HR Manager"),
            (3, "Sales Lead"),
            (4, "Support Executive"),
            (5, "Tech Lead"),
        ]
        for dg_id, dg_name in desigs_cfg:
            existing = await session.get(Designation, dg_id)
            if not existing:
                session.add(
                    Designation(
                        designation_id=dg_id,
                        org_id=1,
                        designation_name=dg_name,
                        is_active=True,
                    )
                )
                print(f"  ✦ Seeded Designation: {dg_name} (ID {dg_id})")
            else:
                print(f"  · Designation {dg_name} (ID {dg_id}) already exists")
        await session.flush()

        # 5. Employees Seeding (35 QA/Demo Employees with IDs 201 to 235)
        # We will map:
        # - branch: loop over 1..4
        # - dept: loop over 1..5
        # - designation: loop over 1..5
        qa_employee_ids = list(range(201, 236))
        for emp_id in qa_employee_ids:
            # Deterministic mapping
            b_id = ((emp_id - 201) % 4) + 1
            d_id = ((emp_id - 201) % 5) + 1
            dg_id = ((emp_id - 201) % 5) + 1
            code = f"QAEMP{emp_id}"
            name = f"QA Employee {emp_id}"
            gender = "Male" if emp_id % 2 == 0 else "Female"

            existing = await session.get(Employee, emp_id)
            if not existing:
                session.add(
                    Employee(
                        employee_id=emp_id,
                        org_id=1,
                        employee_code=code,
                        employee_name=name,
                        display_name=name,
                        mobile_country_code="+91",
                        mobile_number=f"99999{emp_id:05d}",
                        email=f"{code.lower()}@example.com",
                        gender=gender,
                        master_branch_id=b_id,
                        dept_id=d_id,
                        designation_id=dg_id,
                        date_of_joining=datetime.date(2025, 1, 1),
                        employment_status="active",
                    )
                )
                print(f"  ✦ Seeded QA Employee: {name} (ID {emp_id})")
            else:
                # Update attributes to make sure they match
                existing.employee_code = code
                existing.employee_name = name
                existing.master_branch_id = b_id
                existing.dept_id = d_id
                existing.designation_id = dg_id
                existing.employment_status = "active"
                print(f"  · QA Employee {name} updated/synced")
        await session.flush()

        # 6. Delete existing AttendanceDay records for our QA Employees in the date range
        date_from = datetime.date(2026, 6, 1)
        date_to = datetime.date(2026, 6, 30)

        del_stmt = delete(AttendanceDay).where(
            AttendanceDay.employee_id.in_(qa_employee_ids),
            AttendanceDay.attendance_date.between(date_from, date_to)
        )
        await session.execute(del_stmt)
        await session.flush()
        print("✓ Cleared existing attendance days for QA employees in June 2026")

        # 7. Generate 30 days of attendance
        # We will loop through June 1 to June 30
        dates = []
        curr = date_from
        while curr <= date_to:
            dates.append(curr)
            curr += datetime.timedelta(days=1)

        attendance_rows_count = 0
        for emp_id in qa_employee_ids:
            for idx, dt in enumerate(dates):
                # Deterministic pattern to cover all scenarios
                # Options:
                # 0, 1, 2: Normal working hours (8-10 hours)
                # 3: No punch ("-")
                # 4: Missing punch (0h 0m with warning)
                # 5: Half-day
                # 6: Week Off (Sundays or specific rotation)
                # 7: Holiday (e.g. June 15 or rotation)
                # 8: Leave
                # 9: Overtime (10-12 hours)
                
                day_of_week = dt.weekday() # 6 is Sunday
                
                pattern_seed = (emp_id * 13 + idx * 7) % 10
                
                # Default values
                status = "present"
                first_in = None
                last_out = None
                work_mins = 0
                
                # Check for Sunday / Week Off first
                if day_of_week == 6: # Sunday
                    status = "week_off"
                elif dt == datetime.date(2026, 6, 15): # Specific Holiday
                    status = "holiday"
                else:
                    # Apply scenario pattern
                    if pattern_seed in (0, 1, 2):
                        # Normal working hours (8-10 hours)
                        status = "present"
                        work_mins = 480 + (pattern_seed * 40) # 480, 520, 560 mins
                        first_in = datetime.datetime.combine(dt, datetime.time(9, 0), tzinfo=datetime.timezone.utc)
                        last_out = first_in + datetime.timedelta(minutes=work_mins)
                    elif pattern_seed == 3:
                        # No punch ("-")
                        status = "absent"
                        work_mins = 0
                    elif pattern_seed == 4:
                        # Missing punch (0h 0m with warning) - represented by status present with no last_out
                        status = "present"
                        work_mins = 0
                        first_in = datetime.datetime.combine(dt, datetime.time(9, 0), tzinfo=datetime.timezone.utc)
                    elif pattern_seed == 5:
                        # Half-day
                        status = "half_day"
                        work_mins = 240
                        first_in = datetime.datetime.combine(dt, datetime.time(9, 0), tzinfo=datetime.timezone.utc)
                        last_out = first_in + datetime.timedelta(minutes=work_mins)
                    elif pattern_seed == 6:
                        # Leave
                        status = "on_leave"
                        work_mins = 0
                    elif pattern_seed == 7:
                        # Overtime (10-12 hours)
                        status = "present"
                        work_mins = 600 + (pattern_seed * 15) # 705 mins
                        first_in = datetime.datetime.combine(dt, datetime.time(9, 0), tzinfo=datetime.timezone.utc)
                        last_out = first_in + datetime.timedelta(minutes=work_mins)
                    else:
                        # Fallback to normal
                        status = "present"
                        work_mins = 510
                        first_in = datetime.datetime.combine(dt, datetime.time(9, 0), tzinfo=datetime.timezone.utc)
                        last_out = first_in + datetime.timedelta(minutes=work_mins)

                session.add(
                    AttendanceDay(
                        org_id=1,
                        employee_id=emp_id,
                        attendance_date=dt,
                        shift_id=1, # Day Shift
                        status=status,
                        first_punch_in=first_in,
                        last_punch_out=last_out,
                        total_working_minutes=work_mins,
                        source="system"
                    )
                )
                attendance_rows_count += 1

        await session.flush()
        await session.commit()
        print(f"✓ Successfully seeded {attendance_rows_count} attendance day records")
        print("=" * 60)
        print("Summary of Generated Seeding:")
        print(f"  - Employees Created/Synced: {len(qa_employee_ids)}")
        print(f"  - Dates Range: {date_from} to {date_to} ({len(dates)} days)")
        print(f"  - Branches Seeded: 4 (HQ, West, East, South)")
        print(f"  - Total Attendance Rows: {attendance_rows_count}")
        print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
