"""Employee Management — Pydantic v2 request/response DTOs.

Wire contract for the Employee-Management API (section 7 of the HRMS Complete API
Contract): the employee master list/profile, create/edit, document & photo upload,
exit/rehire lifecycle, and device mapping.

Reconciliation notes (the SQLAlchemy models are the source of truth):

* Field names mirror the ``employees`` and satellite table columns exactly
  (``employee_name``, ``mobile_number``/``mobile_country_code``,
  ``master_branch_id``, ``dept_id``, ``date_of_joining``, ...). The API contract
  uses generic illustrative names (``full_name``, ``phone``, ``branch_id``,
  ``joining_date``); those map onto the concrete columns above. This follows the
  established convention in :mod:`app.modules.rbac.schemas` — "field shapes mirror
  the tables; validation follows the API contract".
* ``employee_code`` is auto-generated and immutable; ``employment_status`` is
  driven by the dedicated exit/rehire endpoints. Neither is client-settable on
  create/update (mass-assignment guard, contract §13).
* Salary is segregated behind ``employee.salary.view``: it is exposed only via the
  optional nested :class:`EmployeeSalarySchema` on the detail response, which the
  service populates only when the caller holds that permission.
* Org-hierarchy consistency (designation ⊂ department ⊂ branch), FK existence,
  and "joining date not in the far future" require DB lookups and are enforced in
  the service layer, not here.

Reuses the shared foundation (:class:`app.shared.base.schema.BaseSchema`, the
paged envelope, and the shared email/phone validators). ORM-backed response
schemas use ``from_attributes`` so they build directly from model instances.
"""

from __future__ import annotations

import re
from datetime import date, datetime
from decimal import Decimal

from pydantic import Field, field_validator, model_validator

from app.modules.employee.constants import (
    AttendanceMethod,
    BiometricType,
    DocumentType,
    EmploymentStatus,
    Gender,
    SalaryType,
)
from app.shared.base.schema import BaseSchema
from app.shared.schemas.pagination import PaginatedResponse, PaginationRequest
from app.shared.utils.validators import is_valid_email, is_valid_phone, normalize_phone

# ===========================================================================
# Validation helpers
# ===========================================================================


def _validate_email(value: str) -> str:
    """Normalise and validate an email address."""
    normalised = value.strip().lower()
    if not is_valid_email(normalised):
        raise ValueError("invalid email format")
    return normalised


def _validate_phone(value: str) -> str:
    """Normalise and validate a phone number (7–15 digits, optional ``+``)."""
    normalised = normalize_phone(value)
    if not is_valid_phone(normalised):
        raise ValueError("invalid phone number")
    return normalised


# ===========================================================================
# Shared building blocks (org references, salary, device enrollment)
# ===========================================================================


class BranchRefSchema(BaseSchema):
    """Lightweight reference to the employee's branch."""

    branch_id: int
    branch_name: str


class DepartmentRefSchema(BaseSchema):
    """Lightweight reference to the employee's department."""

    dept_id: int
    dept_name: str


class DesignationRefSchema(BaseSchema):
    """Lightweight reference to the employee's designation."""

    designation_id: int
    designation_name: str


class EmployeeSalarySchema(BaseSchema):
    """Salary block — exposed only to callers holding ``employee.salary.view``."""

    salary_type: SalaryType | None = None
    monthly_salary: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    payroll_group_id: int | None = None


class DeviceEnrollmentStatusSchema(BaseSchema):
    """Async device-enrollment status returned after create (contract §7)."""

    device_id: int
    enrollment_status: str = Field(
        default="Pending", description="Enrollment progress: Pending until the device polls."
    )


# ===========================================================================
# Satellite response schemas (nested in the employee detail projection)
# ===========================================================================


class EmployeeBankDetailSchema(BaseSchema):
    """A persisted ``employee_bank_details`` row."""

    bank_detail_id: int
    bank_name: str | None = None
    bank_branch_name: str | None = None
    account_number: str | None = None
    ifsc_code: str | None = None
    is_primary: bool = True
    created_at: datetime
    updated_at: datetime


class EmployeeDocumentSchema(BaseSchema):
    """A persisted ``employee_documents`` row (metadata only; binary in storage).

    The storage key (``employee_documents.file_url``) is **never** exposed — the
    contract (§7 #34) requires "document metadata (no filesystem path)". Clients fetch
    the bytes through ``GET /employees/{id}/documents/{document_id}``.
    """

    document_id: int
    document_type: DocumentType
    original_filename: str | None = None
    file_size_bytes: int | None = None
    uploaded_by: int | None = None
    created_at: datetime
    updated_at: datetime


class EmployeeEmergencyContactSchema(BaseSchema):
    """A persisted ``employee_emergency_contacts`` row."""

    emergency_contact_id: int
    contact_country_code: str
    contact_number: str
    contact_person_name: str
    relation: str | None = None
    address: str | None = None
    created_at: datetime
    updated_at: datetime


class EmployeeReferenceSchema(BaseSchema):
    """A persisted ``employee_references`` row."""

    reference_id: int
    reference_name: str
    reference_country_code: str
    reference_contact_number: str
    sort_order: int = 1
    created_at: datetime
    updated_at: datetime


class EmployeeBiometricSchema(BaseSchema):
    """A persisted ``employee_biometrics`` row (device-enrollment bridge)."""

    biometric_id: int
    device_id: int
    biometric_type: BiometricType
    registered_at: datetime | None = None
    registered_by: int | None = None
    is_active: bool = True
    created_at: datetime
    updated_at: datetime


class EmployeePunchBranchSchema(BaseSchema):
    """A persisted ``employee_punch_branches`` assignment."""

    punch_branch_id: int
    branch_id: int
    assigned_by: int | None = None
    created_at: datetime


class EmployeeAttendancePermissionSchema(BaseSchema):
    """A persisted ``employee_attendance_permissions`` row."""

    att_perm_id: int
    attendance_method: AttendanceMethod
    mobile_attendance_enabled: bool = False
    geofencing_enabled: bool = False
    auto_punch_out_enabled: bool = False
    updated_by: int | None = None
    updated_at: datetime


class EmployeeTagSchema(BaseSchema):
    """A persisted ``employee_tags`` row."""

    tag_id: int
    tag_label: str
    tag_color: str | None = None
    is_status_tag: bool = False
    created_by: int | None = None
    created_at: datetime
    updated_at: datetime


class EmployeeStatusHistorySchema(BaseSchema):
    """A persisted ``employee_status_history`` row."""

    status_history_id: int
    previous_status: EmploymentStatus | None = None
    new_status: EmploymentStatus
    changed_by: int | None = None
    reason: str | None = None
    effective_date: date
    created_at: datetime


# ===========================================================================
# Employee — request schemas
# ===========================================================================


class EmployeeListQuery(PaginationRequest):
    """Query parameters for ``GET /employees`` (paginated, branch-scoped)."""

    branch_id: int | None = Field(default=None, description="Filter by master branch.")
    department_id: int | None = Field(default=None, description="Filter by department.")
    status: EmploymentStatus | None = Field(
        default=None, description="Filter by employment status."
    )
    q: str | None = Field(
        default=None, max_length=200, description="Free-text search (name / code / contact)."
    )


class EmployeeCreateRequest(BaseSchema):
    """Body for ``POST /employees`` (onboard an employee).

    ``employee_code`` is auto-generated server-side and is not accepted here.
    ``device_ids`` and ``create_self_service_user`` are transport-only fields that
    drive async device enrollment and optional self-service user creation.
    """

    # Identity
    employee_name: str = Field(..., min_length=2, max_length=200)
    display_name: str | None = Field(default=None, max_length=200)
    employee_uid: str | None = Field(default=None, max_length=50)
    gender: Gender

    # Contact
    mobile_country_code: str = Field(default="+91", max_length=5)
    mobile_number: str = Field(..., min_length=1, max_length=20)
    email: str | None = Field(default=None, max_length=200)
    address: str | None = None

    # Org assignment (designation ⊂ department ⊂ branch — verified in service)
    master_branch_id: int
    dept_id: int
    designation_id: int
    employee_type: str | None = Field(default=None, max_length=30)

    # Employment
    date_of_joining: date
    date_of_birth: date | None = None
    door_lock_permission: bool = False

    # Statutory identifiers
    pf_account_number: str | None = Field(default=None, max_length=50)
    uan_number: str | None = Field(default=None, max_length=12)
    esic_ip_number: str | None = Field(default=None, max_length=10)

    # Salary (persisted only for callers permitted to set pay)
    salary_type: SalaryType | None = None
    monthly_salary: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    payroll_group_id: int | None = None

    # Transport-only side effects
    device_ids: list[int] = Field(
        default_factory=list, description="Devices to queue biometric enrollment on."
    )
    create_self_service_user: bool = Field(
        default=False, description="Create a linked self-service user account (Module 01)."
    )

    @field_validator("email")
    @classmethod
    def _email(cls, value: str | None) -> str | None:
        return _validate_email(value) if value is not None else None

    @field_validator("mobile_number")
    @classmethod
    def _phone(cls, value: str) -> str:
        return _validate_phone(value)


class EmployeeUpdateRequest(BaseSchema):
    """Body for ``PUT /employees/{id}`` (partial update; all fields optional).

    Excludes ``employee_code`` (immutable) and ``employment_status`` (driven by the
    exit/rehire endpoints). Org reassignment re-validates hierarchy consistency in
    the service layer.
    """

    employee_name: str | None = Field(default=None, min_length=2, max_length=200)
    display_name: str | None = Field(default=None, max_length=200)
    employee_uid: str | None = Field(default=None, max_length=50)
    gender: Gender | None = None

    mobile_country_code: str | None = Field(default=None, max_length=5)
    mobile_number: str | None = Field(default=None, min_length=1, max_length=20)
    email: str | None = Field(default=None, max_length=200)
    address: str | None = None

    master_branch_id: int | None = None
    dept_id: int | None = None
    designation_id: int | None = None
    employee_type: str | None = Field(default=None, max_length=30)

    date_of_joining: date | None = None
    date_of_birth: date | None = None
    door_lock_permission: bool | None = None

    pf_account_number: str | None = Field(default=None, max_length=50)
    uan_number: str | None = Field(default=None, max_length=12)
    esic_ip_number: str | None = Field(default=None, max_length=10)

    salary_type: SalaryType | None = None
    monthly_salary: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    payroll_group_id: int | None = None

    @field_validator("email")
    @classmethod
    def _email(cls, value: str | None) -> str | None:
        return _validate_email(value) if value is not None else None

    @field_validator("mobile_number")
    @classmethod
    def _phone(cls, value: str | None) -> str | None:
        return _validate_phone(value) if value is not None else None


class EmployeeDocumentCreateRequest(BaseSchema):
    """Metadata part of ``POST /employees/{id}/documents`` (``multipart/form-data``).

    The binary arrives as the multipart ``file`` part; the **server** validates it
    (size / extension / content type) and generates the storage key. A client-supplied
    path is never accepted — it would be a path-traversal primitive (contract §7 #34:
    "Server validates content-type/size from config, generates the storage key (does
    not trust client filename)").
    """

    document_type: DocumentType
    expires_at: date | None = Field(
        default=None, description="Optional expiry for ID / contract documents."
    )


class EmployeePhotoUploadRequest(BaseSchema):
    """Body for ``POST /employees/{id}/photo`` (stores metadata, queues device push)."""

    file_url: str = Field(..., min_length=1, description="Object-storage path of the photo.")
    mime: str | None = Field(default=None, max_length=150, description="Image content-type.")


class EmployeeExitRequest(BaseSchema):
    """Body for ``POST /employees/{id}/exit`` (trigger off-boarding).

    Sets status to *On Notice* until the last working day, then de-maps devices,
    unassigns future shifts, and raises the pro-rata / F&F signal to Payroll.
    """

    resignation_date: date
    last_working_day: date
    reason: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def _validate_dates(self) -> EmployeeExitRequest:
        """Last working day must not precede the resignation date (contract 422)."""
        if self.last_working_day < self.resignation_date:
            raise ValueError("last_working_day must be on or after resignation_date")
        return self


class EmployeeRehireRequest(BaseSchema):
    """Body for ``POST /employees/{id}/rehire`` (reactivate, preserving history)."""

    date_of_joining: date = Field(..., description="New joining date for the re-hire.")


class EmployeeStatusChangeRequest(BaseSchema):
    """Body for ``POST /employees/{id}/activate`` / ``/deactivate`` (contract #29/#30)."""

    effective_date: date | None = Field(
        default=None, description="When the transition takes effect (defaults to today)."
    )
    reason: str | None = Field(default=None, max_length=500)


class EmployeeTerminateRequest(BaseSchema):
    """Body for ``POST /employees/{id}/terminate`` (contract #31 — terminal transition).

    ``date_of_leaving`` defaults to ``effective_date`` when omitted.
    """

    effective_date: date
    date_of_leaving: date | None = None
    reason: str | None = Field(default=None, max_length=500)


class EmployeeTransferRequest(BaseSchema):
    """Body for ``POST /employees/{id}/transfer`` (contract #32).

    Changes ``master_branch_id`` and/or ``dept_id``; the change context
    (``reason`` / ``effective_date``) is captured in the Activity Log only (§9).
    """

    master_branch_id: int | None = None
    dept_id: int | None = None
    effective_date: date | None = None
    reason: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def _require_target(self) -> EmployeeTransferRequest:
        """At least one transfer target (branch or department) must be supplied."""
        if self.master_branch_id is None and self.dept_id is None:
            raise ValueError("at least one of master_branch_id or dept_id is required")
        return self


class EmployeePromoteRequest(BaseSchema):
    """Body for ``POST /employees/{id}/promote`` (contract #33).

    ``monthly_salary`` is persisted only for callers holding the salary
    permission (same gate as create/update employee).
    """

    designation_id: int
    monthly_salary: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    effective_date: date | None = None
    reason: str | None = Field(default=None, max_length=500)


# ===========================================================================
# Sub-record request schemas (§8.1–8.4)
# ===========================================================================


def _validate_ifsc(value: str) -> str:
    """Normalise and app-layer-validate an IFSC code (4 letters, '0', 6 alnum)."""
    normalised = value.strip().upper()
    if not re.fullmatch(r"[A-Z]{4}0[A-Z0-9]{6}", normalised):
        raise ValueError("invalid IFSC code format")
    return normalised


def _validate_account_number(value: str) -> str:
    """Normalise and app-layer-validate a bank account number (alphanumeric, ≤30)."""
    normalised = value.replace(" ", "")
    if not normalised.isalnum():
        raise ValueError("account number must be alphanumeric")
    return normalised


class EmployeeBankDetailCreateRequest(BaseSchema):
    """Body for ``POST /employees/{id}/bank-details`` (contract #39)."""

    bank_name: str | None = Field(default=None, max_length=150)
    bank_branch_name: str | None = Field(default=None, max_length=150)
    account_number: str | None = Field(default=None, min_length=1, max_length=30)
    ifsc_code: str | None = Field(default=None, max_length=15)
    is_primary: bool = True

    @field_validator("ifsc_code")
    @classmethod
    def _ifsc(cls, value: str | None) -> str | None:
        return _validate_ifsc(value) if value is not None else None

    @field_validator("account_number")
    @classmethod
    def _account(cls, value: str | None) -> str | None:
        return _validate_account_number(value) if value is not None else None


class EmployeeBankDetailUpdateRequest(EmployeeBankDetailCreateRequest):
    """Body for ``PATCH /employees/{id}/bank-details/{bank_detail_id}`` (all optional)."""

    is_primary: bool | None = None


class EmployeeEmergencyContactCreateRequest(BaseSchema):
    """Body for ``POST /employees/{id}/emergency-contacts`` (contract #43)."""

    contact_country_code: str = Field(default="+91", max_length=5)
    contact_number: str = Field(..., min_length=1, max_length=20)
    contact_person_name: str = Field(..., min_length=1, max_length=200)
    relation: str | None = Field(default=None, max_length=100)
    address: str | None = None

    @field_validator("contact_number")
    @classmethod
    def _phone(cls, value: str) -> str:
        return _validate_phone(value)


class EmployeeEmergencyContactUpdateRequest(BaseSchema):
    """Body for ``PATCH .../emergency-contacts/{emergency_contact_id}`` (all optional)."""

    contact_country_code: str | None = Field(default=None, max_length=5)
    contact_number: str | None = Field(default=None, min_length=1, max_length=20)
    contact_person_name: str | None = Field(default=None, min_length=1, max_length=200)
    relation: str | None = Field(default=None, max_length=100)
    address: str | None = None

    @field_validator("contact_number")
    @classmethod
    def _phone(cls, value: str | None) -> str | None:
        return _validate_phone(value) if value is not None else None


class EmployeeReferenceCreateRequest(BaseSchema):
    """Body for ``POST /employees/{id}/references`` (contract #47)."""

    reference_name: str = Field(..., min_length=1, max_length=200)
    reference_country_code: str = Field(default="+91", max_length=5)
    reference_contact_number: str = Field(..., min_length=1, max_length=20)
    sort_order: int = Field(default=1, ge=1, le=32767)

    @field_validator("reference_contact_number")
    @classmethod
    def _phone(cls, value: str) -> str:
        return _validate_phone(value)


class EmployeeReferenceUpdateRequest(BaseSchema):
    """Body for ``PATCH .../references/{reference_id}`` (all optional)."""

    reference_name: str | None = Field(default=None, min_length=1, max_length=200)
    reference_country_code: str | None = Field(default=None, max_length=5)
    reference_contact_number: str | None = Field(default=None, min_length=1, max_length=20)
    sort_order: int | None = Field(default=None, ge=1, le=32767)

    @field_validator("reference_contact_number")
    @classmethod
    def _phone(cls, value: str | None) -> str | None:
        return _validate_phone(value) if value is not None else None


class EmployeeTagCreateRequest(BaseSchema):
    """Body for ``POST /employees/{id}/tags`` (contract #51 — hard-deleted rows)."""

    tag_label: str = Field(..., min_length=1, max_length=100)
    tag_color: str | None = Field(default=None, max_length=10)
    is_status_tag: bool = False


class EmployeeDeviceMappingRequest(BaseSchema):
    """Body for ``POST /employees/{id}/device-mapping`` (link a device-local ID)."""

    device_id: int
    device_user_id: int = Field(..., description="Device-local numeric ID; unique per device.")


# ===========================================================================
# Employee — response schemas
# ===========================================================================


class EmployeeSummarySchema(BaseSchema):
    """Compact employee row for the list endpoint (no salary)."""

    employee_id: int
    org_id: int
    employee_code: str
    employee_name: str
    display_name: str | None = None
    mobile_country_code: str
    mobile_number: str
    email: str | None = None
    gender: Gender
    master_branch_id: int
    dept_id: int
    designation_id: int
    employee_type: str | None = None
    employment_status: EmploymentStatus
    date_of_joining: date | None = None
    profile_photo_url: str | None = None
    created_at: datetime


class EmployeeSchema(EmployeeSummarySchema):
    """Full flat projection of an ``employees`` row (salary excluded — segregated)."""

    employee_uid: str | None = None
    address: str | None = None
    door_lock_permission: bool = False
    pf_account_number: str | None = None
    uan_number: str | None = None
    esic_ip_number: str | None = None
    date_of_birth: date | None = None
    date_of_leaving: date | None = None
    is_deleted: bool = False
    created_by: int | None = None
    updated_at: datetime


class EmployeeDetailSchema(EmployeeSchema):
    """Response for ``GET /employees/{id}`` — the full profile with nested links.

    ``salary`` **and** ``bank_details`` are populated only when the caller holds
    ``employee_salary:read`` — the same gate the standalone
    ``GET /employees/{id}/bank-details`` route enforces, so the embedded copy cannot be
    used to bypass it. Callers without it get the employee record with those sections
    omitted (``salary=None``, ``bank_details=[]``), not a ``403``.
    """

    branch: BranchRefSchema | None = None
    department: DepartmentRefSchema | None = None
    designation: DesignationRefSchema | None = None
    salary: EmployeeSalarySchema | None = None

    bank_details: list[EmployeeBankDetailSchema] = Field(default_factory=list)
    documents: list[EmployeeDocumentSchema] = Field(default_factory=list)
    emergency_contacts: list[EmployeeEmergencyContactSchema] = Field(default_factory=list)
    references: list[EmployeeReferenceSchema] = Field(default_factory=list)
    biometrics: list[EmployeeBiometricSchema] = Field(default_factory=list)
    punch_branches: list[EmployeePunchBranchSchema] = Field(default_factory=list)
    attendance_permission: EmployeeAttendancePermissionSchema | None = None
    tags: list[EmployeeTagSchema] = Field(default_factory=list)
    status_history: list[EmployeeStatusHistorySchema] = Field(default_factory=list)


class EmployeeCreateResponse(EmployeeDetailSchema):
    """Response for ``POST /employees`` — the new profile plus async enrollment."""

    device_enrollment: list[DeviceEnrollmentStatusSchema] = Field(default_factory=list)


class EmployeeDeviceMappingSchema(BaseSchema):
    """Response for ``POST /employees/{id}/device-mapping``."""

    employee_id: int
    device_id: int
    device_user_id: int
    enrollment_status: str = "Pending"


# ===========================================================================
# Paginated list response (reuse the shared paged envelope)
# ===========================================================================


class EmployeeListResponse(PaginatedResponse[EmployeeSummarySchema]):
    """Paginated ``GET /employees`` result."""


__all__ = [
    # building blocks
    "BranchRefSchema",
    "DepartmentRefSchema",
    "DesignationRefSchema",
    "EmployeeSalarySchema",
    "DeviceEnrollmentStatusSchema",
    # satellites
    "EmployeeBankDetailSchema",
    "EmployeeDocumentSchema",
    "EmployeeEmergencyContactSchema",
    "EmployeeReferenceSchema",
    "EmployeeBiometricSchema",
    "EmployeePunchBranchSchema",
    "EmployeeAttendancePermissionSchema",
    "EmployeeTagSchema",
    "EmployeeStatusHistorySchema",
    # requests
    "EmployeeListQuery",
    "EmployeeCreateRequest",
    "EmployeeUpdateRequest",
    "EmployeeDocumentCreateRequest",
    "EmployeePhotoUploadRequest",
    "EmployeeExitRequest",
    "EmployeeRehireRequest",
    "EmployeeStatusChangeRequest",
    "EmployeeTerminateRequest",
    "EmployeeTransferRequest",
    "EmployeePromoteRequest",
    "EmployeeBankDetailCreateRequest",
    "EmployeeBankDetailUpdateRequest",
    "EmployeeEmergencyContactCreateRequest",
    "EmployeeEmergencyContactUpdateRequest",
    "EmployeeReferenceCreateRequest",
    "EmployeeReferenceUpdateRequest",
    "EmployeeTagCreateRequest",
    "EmployeeDeviceMappingRequest",
    # responses
    "EmployeeSummarySchema",
    "EmployeeSchema",
    "EmployeeDetailSchema",
    "EmployeeCreateResponse",
    "EmployeeDeviceMappingSchema",
    "EmployeeListResponse",
]
