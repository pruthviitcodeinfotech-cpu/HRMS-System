"""Leave & Holiday Management ORM models.

All models are re-exported here so the module can be imported as a single unit
(e.g. by the Alembic migration environment and, later, by repositories).

NOTE: `approval_requests` appears in this module's source PDF but is the
authoritative property of the Approval Requests module (with a different,
canonical schema). It is intentionally NOT implemented here, per the
"never implement another module" rule.
"""

from app.modules.leave.models.holiday import (
    EmployeeHolidayAssignment,
    HolidayTemplate,
    HolidayTemplateItem,
)
from app.modules.leave.models.leave import (
    EmployeeLeaveAllocation,
    EmployeeLeaveBalance,
    LeaveBalanceAdjustment,
    LeaveRequest,
    LeaveSetting,
    LeaveType,
)

__all__ = [
    "LeaveSetting",
    "LeaveType",
    "EmployeeLeaveAllocation",
    "EmployeeLeaveBalance",
    "LeaveBalanceAdjustment",
    "LeaveRequest",
    "HolidayTemplate",
    "HolidayTemplateItem",
    "EmployeeHolidayAssignment",
]
