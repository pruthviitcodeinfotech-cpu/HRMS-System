"""Employee Management — satellite and org-configuration models.

Tables:
    employee_bank_details, employee_documents, employee_emergency_contacts,
    employee_references, employee_biometrics, employee_punch_branches,
    employee_attendance_permissions, org_attendance_settings,
    employee_import_logs, employee_tags, employee_status_history.

Implements the approved Employee Management Database Architecture exactly.
All primary keys and foreign keys use BIGINT (project-wide PK convention);
non-key numeric columns (e.g. file_size_bytes, total/success/failed_rows) keep
their original INTEGER type.
DEFERRED cross-module FKs (plain columns for now):
    - *_by            -> users            (User Management module)
    - device_id       -> biometric_devices (Hardware / Biometric module)
"""

from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database.base import Base


class EmployeeBankDetail(Base):
    __tablename__ = "employee_bank_details"

    bank_detail_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    employee_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("employees.employee_id", name="fk_employee_bank_details_employee_id_employees"),
        nullable=False,
    )
    bank_name: Mapped[str | None] = mapped_column(String(150))
    bank_branch_name: Mapped[str | None] = mapped_column(String(150))
    account_number: Mapped[str | None] = mapped_column(String(30))
    ifsc_code: Mapped[str | None] = mapped_column(String(15))
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )

    __table_args__ = (
        # GET /employees/{id} `selectinload`s this satellite by employee_id.
        Index("ix_employee_bank_details_employee_id", "employee_id"),
    )

    employee: Mapped["Employee"] = relationship(back_populates="bank_details")  # noqa: F821


class EmployeeDocument(Base):
    __tablename__ = "employee_documents"

    document_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    employee_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("employees.employee_id", name="fk_employee_documents_employee_id_employees"),
        nullable=False,
    )
    document_type: Mapped[str] = mapped_column(String(50), nullable=False)
    file_url: Mapped[str] = mapped_column(Text, nullable=False)
    original_filename: Mapped[str | None] = mapped_column(String(255))
    file_size_bytes: Mapped[int | None] = mapped_column(Integer)  # data column (not a key)
    # DEFERRED cross-module FK -> users.id
    uploaded_by: Mapped[int | None] = mapped_column(BigInteger)
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )

    __table_args__ = (
        CheckConstraint(
            "document_type IN ('aadhar_card', 'driving_licence', 'pan_card', "
            "'passport_photo', 'other')",
            name="ck_employee_documents_document_type",
        ),
        # GET /employees/{id} `selectinload`s this satellite by employee_id.
        Index("ix_employee_documents_employee_id", "employee_id"),
    )

    employee: Mapped["Employee"] = relationship(back_populates="documents")  # noqa: F821


class EmployeeEmergencyContact(Base):
    __tablename__ = "employee_emergency_contacts"

    emergency_contact_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    employee_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "employees.employee_id",
            name="fk_employee_emergency_contacts_employee_id_employees",
        ),
        nullable=False,
    )
    contact_country_code: Mapped[str] = mapped_column(
        String(5), nullable=False, server_default=text("'+91'")
    )
    contact_number: Mapped[str] = mapped_column(String(20), nullable=False)
    contact_person_name: Mapped[str] = mapped_column(String(200), nullable=False)
    relation: Mapped[str | None] = mapped_column(String(100))
    address: Mapped[str | None] = mapped_column(Text)
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )

    __table_args__ = (
        # GET /employees/{id} `selectinload`s this satellite by employee_id.
        Index("ix_employee_emergency_contacts_employee_id", "employee_id"),
    )

    employee: Mapped["Employee"] = relationship(back_populates="emergency_contacts")  # noqa: F821


class EmployeeReference(Base):
    __tablename__ = "employee_references"

    reference_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    employee_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("employees.employee_id", name="fk_employee_references_employee_id_employees"),
        nullable=False,
    )
    reference_name: Mapped[str] = mapped_column(String(200), nullable=False)
    reference_country_code: Mapped[str] = mapped_column(
        String(5), nullable=False, server_default=text("'+91'")
    )
    reference_contact_number: Mapped[str] = mapped_column(String(20), nullable=False)
    sort_order: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default=text("1"))
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )

    __table_args__ = (
        # GET /employees/{id} `selectinload`s this satellite by employee_id.
        Index("ix_employee_references_employee_id", "employee_id"),
    )

    employee: Mapped["Employee"] = relationship(back_populates="references")  # noqa: F821


class EmployeeBiometric(Base):
    __tablename__ = "employee_biometrics"

    biometric_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    employee_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("employees.employee_id", name="fk_employee_biometrics_employee_id_employees"),
        nullable=False,
    )
    # DEFERRED cross-module FK -> biometric_devices.device_id (required column)
    device_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    biometric_type: Mapped[str] = mapped_column(
        String(30), nullable=False, server_default=text("'fingerprint'")
    )
    biometric_template: Mapped[str | None] = mapped_column(Text)
    registered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # DEFERRED cross-module FK -> users.id
    registered_by: Mapped[int | None] = mapped_column(BigInteger)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )

    __table_args__ = (
        Index(
            "uq_employee_biometrics_employee_id_device_id_biometric_type",
            "employee_id",
            "device_id",
            "biometric_type",
            unique=True,
            postgresql_where=text("is_deleted = false"),
        ),
        # FK -> biometric_devices ON DELETE RESTRICT: without this, every device
        # delete sequentially scans employee_biometrics to enforce the constraint.
        Index("ix_employee_biometrics_device_id", "device_id"),
    )

    employee: Mapped["Employee"] = relationship(back_populates="biometrics")  # noqa: F821


class EmployeePunchBranch(Base):
    __tablename__ = "employee_punch_branches"

    punch_branch_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    employee_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "employees.employee_id",
            name="fk_employee_punch_branches_employee_id_employees",
        ),
        nullable=False,
    )
    branch_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("branches.branch_id", name="fk_employee_punch_branches_branch_id_branches"),
        nullable=False,
    )
    # DEFERRED cross-module FK -> users.id
    assigned_by: Mapped[int | None] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )

    __table_args__ = (
        UniqueConstraint(
            "employee_id", "branch_id", name="uq_employee_punch_branches_employee_id_branch_id"
        ),
    )

    employee: Mapped["Employee"] = relationship(back_populates="punch_branches")  # noqa: F821
    branch: Mapped["Branch"] = relationship(back_populates="punch_branches")  # noqa: F821


class EmployeeAttendancePermission(Base):
    __tablename__ = "employee_attendance_permissions"

    att_perm_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    employee_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "employees.employee_id",
            name="fk_employee_attendance_permissions_employee_id_employees",
        ),
        nullable=False,
    )
    attendance_method: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'hardware_device'")
    )
    mobile_attendance_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    geofencing_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    auto_punch_out_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    # DEFERRED cross-module FK -> users.id
    updated_by: Mapped[int | None] = mapped_column(BigInteger)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )

    __table_args__ = (
        UniqueConstraint("employee_id", name="uq_employee_attendance_permissions_employee_id"),
        CheckConstraint(
            "attendance_method IN ('hardware_device', 'mobile_app', 'both')",
            name="ck_employee_attendance_permissions_attendance_method",
        ),
    )

    employee: Mapped["Employee"] = relationship(  # noqa: F821
        back_populates="attendance_permission"
    )


class OrgAttendanceSetting(Base):
    __tablename__ = "org_attendance_settings"

    setting_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    org_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("organizations.org_id", name="fk_org_attendance_settings_org_id_organizations"),
        nullable=False,
    )
    branch_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("branches.branch_id", name="fk_org_attendance_settings_branch_id_branches"),
    )
    # DEFERRED cross-module FK -> biometric_devices.device_id
    device_id: Mapped[int | None] = mapped_column(BigInteger)
    mobile_attendance_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    geofencing_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    auto_punch_out_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    biometric_attempt_count: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, server_default=text("7")
    )
    # DEFERRED cross-module FK -> users.id
    updated_by: Mapped[int | None] = mapped_column(BigInteger)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )

    __table_args__ = (
        UniqueConstraint(
            "org_id",
            "branch_id",
            "device_id",
            name="uq_org_attendance_settings_org_id_branch_id_device_id",
        ),
    )

    organization: Mapped["Organization"] = relationship(  # noqa: F821
        back_populates="attendance_settings"
    )
    branch: Mapped["Branch"] = relationship(back_populates="attendance_settings")  # noqa: F821


class EmployeeImportLog(Base):
    __tablename__ = "employee_import_logs"

    import_log_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    org_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("organizations.org_id", name="fk_employee_import_logs_org_id_organizations"),
        nullable=False,
    )
    import_type: Mapped[str] = mapped_column(
        String(30), nullable=False, server_default=text("'create'")
    )
    file_url: Mapped[str | None] = mapped_column(Text)
    original_filename: Mapped[str | None] = mapped_column(String(255))
    total_rows: Mapped[int | None] = mapped_column(Integer)  # data column (not a key)
    success_rows: Mapped[int | None] = mapped_column(Integer)  # data column (not a key)
    failed_rows: Mapped[int | None] = mapped_column(Integer)  # data column (not a key)
    error_details: Mapped[dict | None] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'pending'")
    )
    # DEFERRED cross-module FK -> users.id
    initiated_by: Mapped[int | None] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'processing', 'completed', 'failed')",
            name="ck_employee_import_logs_status",
        ),
        CheckConstraint(
            "import_type IN ('create', 'update')",
            name="ck_employee_import_logs_import_type",
        ),
    )

    organization: Mapped["Organization"] = relationship(back_populates="import_logs")  # noqa: F821


class EmployeeTag(Base):
    __tablename__ = "employee_tags"

    tag_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    employee_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("employees.employee_id", name="fk_employee_tags_employee_id_employees"),
        nullable=False,
    )
    tag_label: Mapped[str] = mapped_column(String(100), nullable=False)
    tag_color: Mapped[str | None] = mapped_column(String(10))
    is_status_tag: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    # DEFERRED cross-module FK -> users.id
    created_by: Mapped[int | None] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )

    __table_args__ = (
        # GET /employees/{id} `selectinload`s this satellite by employee_id.
        Index("ix_employee_tags_employee_id", "employee_id"),
    )

    employee: Mapped["Employee"] = relationship(back_populates="tags")  # noqa: F821


class EmployeeStatusHistory(Base):
    __tablename__ = "employee_status_history"

    status_history_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    employee_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "employees.employee_id",
            name="fk_employee_status_history_employee_id_employees",
        ),
        nullable=False,
    )
    previous_status: Mapped[str | None] = mapped_column(String(20))
    new_status: Mapped[str] = mapped_column(String(20), nullable=False)
    # DEFERRED cross-module FK -> users.id
    changed_by: Mapped[int | None] = mapped_column(BigInteger)
    reason: Mapped[str | None] = mapped_column(Text)
    effective_date: Mapped[date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )

    __table_args__ = (
        CheckConstraint(
            "new_status IN ('active', 'inactive', 'terminated')",
            name="ck_employee_status_history_new_status",
        ),
        # GET /employees/{id} `selectinload`s this satellite by employee_id.
        Index("ix_employee_status_history_employee_id", "employee_id"),
    )

    employee: Mapped["Employee"] = relationship(back_populates="status_history")  # noqa: F821
