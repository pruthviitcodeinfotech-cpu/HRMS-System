"""Shift Management ORM models.

All models are re-exported here so the module can be imported as a single unit
(e.g. by the Alembic migration environment and, later, by repositories).
"""

from app.modules.shift.models.assignment import (
    EmployeeWeekoff,
    Roster,
    ShiftAssignment,
)
from app.modules.shift.models.shift import Shift, ShiftDayTiming
from app.modules.shift.models.working_hours import (
    WorkingHoursConfig,
    WorkingHoursConfigHistory,
)

__all__ = [
    "Shift",
    "ShiftDayTiming",
    "ShiftAssignment",
    "EmployeeWeekoff",
    "Roster",
    "WorkingHoursConfig",
    "WorkingHoursConfigHistory",
]
