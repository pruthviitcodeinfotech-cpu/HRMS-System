"""resolve deferred device foreign keys

Adds the previously-deferred FOREIGN KEY constraints that reference the now-
existing biometric_devices table (created in 0012). The device_id columns
already exist and are BIGINT (Employee Management, 0001; standardized in 0009);
this migration ONLY adds the constraints — it does NOT recreate or alter the
tables/columns.

    1. employee_biometrics.device_id     -> biometric_devices.id
       (column is NOT NULL -> ON DELETE RESTRICT)
    2. org_attendance_settings.device_id -> biometric_devices.id
       (column is NULLABLE -> ON DELETE SET NULL)

NOTE: the deferred column on org_attendance_settings is named `device_id`.

Revision ID: 0013_resolve_deferred_device_fks
Revises: 0012_hardware_biometric_devices
Create Date: 2026-07-06
"""

from collections.abc import Sequence
from typing import Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0013_resolve_deferred_device_fks"
down_revision: Union[str, None] = "0012_hardware_biometric_devices"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_foreign_key(
        "fk_employee_biometrics_device_id_biometric_devices",
        "employee_biometrics",
        "biometric_devices",
        ["device_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_org_attendance_settings_device_id_biometric_devices",
        "org_attendance_settings",
        "biometric_devices",
        ["device_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_org_attendance_settings_device_id_biometric_devices",
        "org_attendance_settings",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_employee_biometrics_device_id_biometric_devices",
        "employee_biometrics",
        type_="foreignkey",
    )
