"""Employee Management ORM models.

All models are re-exported here so the module can be imported as a single unit
(e.g. by the Alembic migration environment and, later, by repositories).
"""

from app.modules.employee.models.employee import Employee
from app.modules.employee.models.organization import (
    Branch,
    Department,
    Designation,
    Organization,
)
from app.modules.employee.models.satellites import (
    EmployeeAttendancePermission,
    EmployeeBankDetail,
    EmployeeBiometric,
    EmployeeDocument,
    EmployeeEmergencyContact,
    EmployeeImportLog,
    EmployeePunchBranch,
    EmployeeReference,
    EmployeeStatusHistory,
    EmployeeTag,
    OrgAttendanceSetting,
)

__all__ = [
    # organization structure
    "Organization",
    "Branch",
    "Department",
    "Designation",
    # employee master
    "Employee",
    # satellites
    "EmployeeBankDetail",
    "EmployeeDocument",
    "EmployeeEmergencyContact",
    "EmployeeReference",
    "EmployeeBiometric",
    "EmployeePunchBranch",
    "EmployeeAttendancePermission",
    "OrgAttendanceSetting",
    "EmployeeImportLog",
    "EmployeeTag",
    "EmployeeStatusHistory",
]
