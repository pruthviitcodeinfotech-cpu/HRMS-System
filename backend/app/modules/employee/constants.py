"""Employee module: constants and enums.

These enums mirror the CHECK-constraint value sets defined in the approved
Employee Management Database Architecture. They are the single source of truth
for the allowed values enforced at the database level (see the models package).
Native PostgreSQL ENUM types are intentionally NOT used — the approved
architecture models these as VARCHAR columns with CHECK constraints, and that
is preserved.
"""

from enum import Enum


class EmploymentStatus(str, Enum):
    """employees.employment_status / employee_status_history.new_status."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    TERMINATED = "terminated"


class Gender(str, Enum):
    """employees.gender."""

    MALE = "Male"
    FEMALE = "Female"
    OTHER = "Other"


class SalaryType(str, Enum):
    """employees.salary_type."""

    MONTHLY = "Monthly"
    HOURLY = "Hourly"
    COMPLIANCE = "Compliance"


class DocumentType(str, Enum):
    """employee_documents.document_type."""

    AADHAR_CARD = "aadhar_card"
    DRIVING_LICENCE = "driving_licence"
    PAN_CARD = "pan_card"
    PASSPORT_PHOTO = "passport_photo"
    OTHER = "other"


class AttendanceMethod(str, Enum):
    """employee_attendance_permissions.attendance_method."""

    HARDWARE_DEVICE = "hardware_device"
    MOBILE_APP = "mobile_app"
    BOTH = "both"


class ImportType(str, Enum):
    """employee_import_logs.import_type."""

    CREATE = "create"
    UPDATE = "update"


class ImportStatus(str, Enum):
    """employee_import_logs.status."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class BiometricType(str, Enum):
    """employee_biometrics.biometric_type.

    NOTE: the approved architecture lists these values but defines NO CHECK
    constraint on this column, so no CHECK is applied at the DB level. This enum
    is provided for application-layer use only.
    """

    FINGERPRINT = "fingerprint"
    FACE = "face"
    CARD = "card"
    PIN = "pin"
