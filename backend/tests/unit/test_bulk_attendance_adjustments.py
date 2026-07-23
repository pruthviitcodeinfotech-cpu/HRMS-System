"""Unit tests for Phase 2 Bulk Attendance Adjustments module."""

from datetime import date
import pytest
from pydantic import ValidationError

from app.modules.payroll.schemas import (
    BulkAttendanceAdjustmentCellUpdateSchema,
    BulkAttendanceAdjustmentBatchUpdateSchema,
    BulkAttendanceAdjustmentResetSchema,
)


def test_bulk_attendance_cell_update_validation():
    """Test validation of attendance status codes."""
    # Valid status codes
    valid = BulkAttendanceAdjustmentCellUpdateSchema(
        employee_id=1,
        attendance_date=date(2026, 7, 1),
        adjusted_status="fd",  # test uppercase normalization
        original_status="a",
    )
    assert valid.adjusted_status == "FD"

    # Invalid status code
    with pytest.raises(ValidationError):
        BulkAttendanceAdjustmentCellUpdateSchema(
            employee_id=1,
            attendance_date=date(2026, 7, 1),
            adjusted_status="INVALID_STATUS",
        )


def test_bulk_attendance_batch_update_schema():
    """Test batch update payload validation."""
    batch = BulkAttendanceAdjustmentBatchUpdateSchema(
        date_from=date(2026, 7, 1),
        date_to=date(2026, 7, 22),
        updates=[
            BulkAttendanceAdjustmentCellUpdateSchema(
                employee_id=1,
                attendance_date=date(2026, 7, 1),
                adjusted_status="A",
            ),
            BulkAttendanceAdjustmentCellUpdateSchema(
                employee_id=2,
                attendance_date=date(2026, 7, 2),
                adjusted_status="HD",
            ),
        ],
    )
    assert len(batch.updates) == 2


def test_bulk_attendance_reset_schema():
    """Test reset payload validation."""
    reset_payload = BulkAttendanceAdjustmentResetSchema(
        date_from=date(2026, 7, 1),
        date_to=date(2026, 7, 22),
        branch_id=1,
        employee_ids=[1, 2, 3],
    )
    assert reset_payload.branch_id == 1
    assert len(reset_payload.employee_ids) == 3
