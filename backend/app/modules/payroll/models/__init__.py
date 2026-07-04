"""Payroll ORM models.

All models are re-exported here so the module can be imported as a single unit
(e.g. by the Alembic migration environment and, later, by repositories).

NOT owned by this module (referenced but implemented elsewhere):
    * employees (Employee Management)
    * loan_advance_records / arrear_records -> Settlements module
      (feed payroll_computed_rows.loan_advance_deduction / arrears_amount at
      computation time; no FK columns exist in this module's tables)
"""

from app.modules.payroll.models.adjustments import (
    AttendanceAdjustment,
    AttendanceAdjustmentExtraHours,
    AttendanceAdjustmentPenalty,
)
from app.modules.payroll.models.run import FinalizedPayrollRun, PayrollComputedRow
from app.modules.payroll.models.settings import (
    EmployeePayrollGroupAssignment,
    PayrollColumnSetting,
    PayrollGroup,
    PayrollSalaryCycle,
    PayrollSetting,
)

__all__ = [
    "PayrollSetting",
    "PayrollGroup",
    "EmployeePayrollGroupAssignment",
    "PayrollSalaryCycle",
    "PayrollColumnSetting",
    "AttendanceAdjustment",
    "AttendanceAdjustmentPenalty",
    "AttendanceAdjustmentExtraHours",
    "FinalizedPayrollRun",
    "PayrollComputedRow",
]
