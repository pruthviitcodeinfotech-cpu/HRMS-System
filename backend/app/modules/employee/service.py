"""Employee Management — service layer (business rules & orchestration).

Implements the behaviour of the Employee-Management API Contract (section 7): the
employee master lifecycle (create / edit / get / list / search), employment-status
management (activate / deactivate / exit / rehire), and org assignment
(branch / department / designation / reporting manager).

Design rules honoured here:

* **No direct database access.** All persistence goes through the Employee
  repositories (:class:`EmployeeRepository`, :class:`BranchRepository`,
  :class:`DepartmentRepository`, :class:`DesignationRepository`) and, for
  status-history and self-service-user side effects, through the shared
  :class:`BaseRepository` and the RBAC :class:`UserRepository`.
* **Validate all cross-module references before processing.** Branch, department,
  designation, reporting-manager, and self-service-user references are resolved and
  checked against the caller's ``org_id`` before any write.
* The service owns the transaction boundary (:class:`BaseService`).

Schema-reconciliation notes (the models are the source of truth):

* ``employment_status`` is modelled as ``active | inactive | terminated``. The
  contract's "On Notice → Exited" lifecycle maps onto ``terminated`` (there is no
  "On Notice" column); the notice period is expressed by
  ``resignation_date`` ≤ ``last_working_day`` recorded on the exit event.
* The ``employees`` table has **no ``reporting_manager_id`` column** and no
  self-referential FK. :meth:`assign_reporting_manager` therefore fully validates
  the manager reference but cannot persist it — see that method.
* Actual biometric **device enrollment is asynchronous** and owned by the Hardware
  module's enrollment service. Create returns ``device_enrollment`` placeholders in
  ``Pending`` state for the requested devices; this service performs no device I/O.
"""

from __future__ import annotations

from app.core.exceptions.base import (
    ConflictException,
    NotFoundException,
    ValidationException,
)
from app.modules.audit.constants import ActionType
from app.modules.audit.service import AuditService
from app.modules.employee.constants import EmploymentStatus
from app.modules.employee.models import Employee, EmployeeDocument
from app.modules.employee.models.satellites import EmployeeStatusHistory
from app.modules.employee.repository import (
    BranchRepository,
    DepartmentRepository,
    DesignationRepository,
    EmployeeRepository,
)
from app.modules.employee.schemas import (
    BranchRefSchema,
    DepartmentRefSchema,
    DesignationRefSchema,
    DeviceEnrollmentStatusSchema,
    EmployeeAttendancePermissionSchema,
    EmployeeBankDetailSchema,
    EmployeeBiometricSchema,
    EmployeeCreateRequest,
    EmployeeCreateResponse,
    EmployeeDetailSchema,
    EmployeeDocumentCreateRequest,
    EmployeeDocumentSchema,
    EmployeeEmergencyContactSchema,
    EmployeeExitRequest,
    EmployeeListQuery,
    EmployeeListResponse,
    EmployeePhotoUploadRequest,
    EmployeePunchBranchSchema,
    EmployeeReferenceSchema,
    EmployeeRehireRequest,
    EmployeeSalarySchema,
    EmployeeSchema,
    EmployeeStatusHistorySchema,
    EmployeeSummarySchema,
    EmployeeTagSchema,
    EmployeeUpdateRequest,
)
from app.modules.rbac.repository import UserRepository
from app.shared.base.repository import BaseRepository
from app.shared.base.service import BaseService
from app.shared.utils.datetime import utcnow

from sqlalchemy.ext.asyncio import AsyncSession

_CODE_PREFIX = "EMP"
_CODE_PAD = 5
_AUDIT_MODULE = "Employee Management"


class EmployeeService(BaseService):
    """Employee Management business logic (data access via repositories only)."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)
        self.employees = EmployeeRepository(session)
        self.branches = BranchRepository(session)
        self.departments = DepartmentRepository(session)
        self.designations = DesignationRepository(session)
        # Self-service-user link is a cross-module (RBAC) side effect.
        self.users = UserRepository(session)
        # Shared audit trail (writes participate in this service's transaction).
        self.audit = AuditService(session)
        # Satellite writes via the generic shared repository.
        self.status_history: BaseRepository[EmployeeStatusHistory] = BaseRepository(
            session, EmployeeStatusHistory
        )
        self.documents: BaseRepository[EmployeeDocument] = BaseRepository(
            session, EmployeeDocument
        )

    # =====================================================================
    # Create / update
    # =====================================================================
    async def create_employee(
        self,
        *,
        org_id: int,
        actor_id: int,
        data: EmployeeCreateRequest,
        can_set_salary: bool = True,
    ) -> EmployeeCreateResponse:
        """Onboard an employee: validate org FKs, auto-generate code, persist, and
        queue async device enrollment + optional self-service user.

        Enforces "Org FKs mandatory & active" and the designation ⊂ department ⊂
        branch consistency check (contract §10) before any write. ``can_set_salary``
        gates whether salary fields are persisted (``employee.salary.view``).
        """
        await self._validate_org_hierarchy(
            org_id,
            branch_id=data.master_branch_id,
            dept_id=data.dept_id,
            designation_id=data.designation_id,
        )

        payload: dict = {
            "org_id": org_id,
            "employee_name": data.employee_name,
            "display_name": data.display_name,
            "employee_uid": data.employee_uid,
            "gender": data.gender.value,
            "mobile_country_code": data.mobile_country_code,
            "mobile_number": data.mobile_number,
            "email": data.email,
            "address": data.address,
            "master_branch_id": data.master_branch_id,
            "dept_id": data.dept_id,
            "designation_id": data.designation_id,
            "employee_type": data.employee_type,
            "date_of_joining": data.date_of_joining,
            "date_of_birth": data.date_of_birth,
            "door_lock_permission": data.door_lock_permission,
            "pf_account_number": data.pf_account_number,
            "uan_number": data.uan_number,
            "esic_ip_number": data.esic_ip_number,
            "employment_status": EmploymentStatus.ACTIVE.value,
            "created_by": actor_id,
        }
        if can_set_salary:
            payload["salary_type"] = data.salary_type.value if data.salary_type else None
            payload["monthly_salary"] = data.monthly_salary
            payload["payroll_group_id"] = data.payroll_group_id

        if data.create_self_service_user:
            await self._validate_self_service_user(org_id, data)

        async with self.transaction():
            payload["employee_code"] = await self._next_employee_code(org_id)
            employee = await self.employees.create(payload)
            if data.create_self_service_user:
                await self._create_self_service_user(
                    org_id=org_id, actor_id=actor_id, employee=employee, data=data
                )
            await self._audit(
                org_id=org_id,
                actor_id=actor_id,
                action_type=ActionType.INSERT,
                title="Employee created",
                description=f"Created employee {employee.employee_code}.",
                employee=employee,
            )

        detail = await self._load_detail(org_id, employee.employee_id, include_salary=can_set_salary)
        enrollment = [
            DeviceEnrollmentStatusSchema(device_id=device_id) for device_id in data.device_ids
        ]
        return EmployeeCreateResponse(**detail.model_dump(), device_enrollment=enrollment)

    async def update_employee(
        self,
        *,
        org_id: int,
        actor_id: int,
        employee_id: int,
        data: EmployeeUpdateRequest,
        can_set_salary: bool = True,
    ) -> EmployeeDetailSchema:
        """Apply a partial update. Org reassignment re-validates hierarchy consistency.

        ``employee_code`` and ``employment_status`` are never updated here (immutable
        / lifecycle-driven). Salary fields are dropped when ``can_set_salary`` is
        false.
        """
        employee = await self._get_active_employee(org_id, employee_id)
        updates = data.model_dump(exclude_unset=True)

        if not can_set_salary:
            for field in ("salary_type", "monthly_salary", "payroll_group_id"):
                updates.pop(field, None)

        # Re-validate the org triple whenever any leg changes.
        if {"master_branch_id", "dept_id", "designation_id"} & updates.keys():
            await self._validate_org_hierarchy(
                org_id,
                branch_id=updates.get("master_branch_id", employee.master_branch_id),
                dept_id=updates.get("dept_id", employee.dept_id),
                designation_id=updates.get("designation_id", employee.designation_id),
            )

        for field in ("gender", "salary_type"):
            if updates.get(field) is not None and hasattr(updates[field], "value"):
                updates[field] = updates[field].value

        async with self.transaction():
            await self.employees.update(employee, updates)
            await self._audit(
                org_id=org_id,
                actor_id=actor_id,
                action_type=ActionType.UPDATE,
                title="Employee updated",
                description=f"Updated fields: {', '.join(sorted(updates)) or 'none'}.",
                employee=employee,
            )

        return await self._load_detail(org_id, employee_id, include_salary=can_set_salary)

    # =====================================================================
    # Read
    # =====================================================================
    async def get_employee(
        self, *, org_id: int, employee_id: int, include_salary: bool = False
    ) -> EmployeeDetailSchema:
        """Return the full profile of an employee (salary only when permitted)."""
        return await self._load_detail(org_id, employee_id, include_salary=include_salary)

    async def list_employees(
        self,
        *,
        org_id: int,
        query: EmployeeListQuery,
        branch_scope: list[int] | None = None,
    ) -> EmployeeListResponse:
        """Return a filtered, searched, paginated page of employees.

        ``branch_scope`` (from the caller's RBAC data scope) confines Branch-Admin
        results to their permitted branches; ``None`` means org-wide access.
        """
        status = query.status.value if query.status is not None else None
        common = {
            "search": query.q,
            "branch_id": query.branch_id,
            "department_id": query.department_id,
            "status": status,
            "branch_scope": branch_scope,
        }
        rows = await self.employees.search(
            org_id, page=query.page, page_size=query.page_size, **common
        )
        total = await self.employees.search_count(org_id, **common)
        items = [EmployeeSummarySchema.model_validate(row) for row in rows]
        return EmployeeListResponse.build(
            items=items, page=query.page, page_size=query.page_size, total_records=total
        )

    async def search_employees(
        self,
        *,
        org_id: int,
        query: EmployeeListQuery,
        branch_scope: list[int] | None = None,
    ) -> EmployeeListResponse:
        """Alias of :meth:`list_employees` — the list endpoint *is* the search surface."""
        return await self.list_employees(
            org_id=org_id, query=query, branch_scope=branch_scope
        )

    # =====================================================================
    # Employment-status management
    # =====================================================================
    async def activate_employee(
        self, *, org_id: int, actor_id: int, employee_id: int, reason: str | None = None
    ) -> EmployeeDetailSchema:
        """Set employment status to ``active`` (idempotency guarded)."""
        return await self.change_status(
            org_id=org_id,
            actor_id=actor_id,
            employee_id=employee_id,
            new_status=EmploymentStatus.ACTIVE,
            reason=reason,
        )

    async def deactivate_employee(
        self, *, org_id: int, actor_id: int, employee_id: int, reason: str | None = None
    ) -> EmployeeDetailSchema:
        """Set employment status to ``inactive`` (idempotency guarded)."""
        return await self.change_status(
            org_id=org_id,
            actor_id=actor_id,
            employee_id=employee_id,
            new_status=EmploymentStatus.INACTIVE,
            reason=reason,
        )

    async def change_status(
        self,
        *,
        org_id: int,
        actor_id: int,
        employee_id: int,
        new_status: EmploymentStatus,
        reason: str | None = None,
        effective_date=None,
    ) -> EmployeeDetailSchema:
        """Transition an employee to ``new_status`` and record status history.

        Rejects a no-op transition (already in the target status) as a conflict.
        """
        employee = await self._get_active_employee(org_id, employee_id)
        if employee.employment_status == new_status.value:
            raise ConflictException(
                f"Employee is already {new_status.value}.",
                code="EMPLOYEE_STATUS_UNCHANGED",
            )
        async with self.transaction():
            await self._apply_status(
                employee,
                new_status=new_status,
                actor_id=actor_id,
                reason=reason,
                effective_date=effective_date or utcnow().date(),
            )
            await self._audit(
                org_id=org_id,
                actor_id=actor_id,
                action_type=ActionType.UPDATE,
                title="Employee status changed",
                description=f"Status set to {new_status.value}.",
                employee=employee,
            )
        return await self._load_detail(org_id, employee_id, include_salary=False)

    async def exit_employee(
        self,
        *,
        org_id: int,
        actor_id: int,
        employee_id: int,
        data: EmployeeExitRequest,
    ) -> EmployeeDetailSchema:
        """Off-board an employee: record the last working day and terminate.

        The date logic (``last_working_day`` ≥ ``resignation_date``) is validated by
        the request schema; it is re-checked here (``invalid_exit_dates``) so
        non-HTTP callers get the contract error code. The downstream cascade (device
        de-map, future-shift unassignment, payroll pro-rata / F&F) is owned by the
        enrollment / payroll modules and is out of scope for this data-only service.
        """
        if data.last_working_day < data.resignation_date:
            raise ValidationException(
                "Last working day must be on or after the resignation date.",
                code="invalid_exit_dates",
            )
        employee = await self._get_active_employee(org_id, employee_id)
        if employee.employment_status == EmploymentStatus.TERMINATED.value:
            raise ConflictException(
                "Employee has already exited.", code="EMPLOYEE_ALREADY_EXITED"
            )
        async with self.transaction():
            await self._apply_status(
                employee,
                new_status=EmploymentStatus.TERMINATED,
                actor_id=actor_id,
                reason=data.reason,
                effective_date=data.last_working_day,
                extra_updates={"date_of_leaving": data.last_working_day},
            )
            await self._audit(
                org_id=org_id,
                actor_id=actor_id,
                action_type=ActionType.UPDATE,
                title="Employee exited",
                description=(
                    f"Exit recorded (last working day {data.last_working_day.isoformat()})."
                ),
                employee=employee,
            )
        return await self._load_detail(org_id, employee_id, include_salary=False)

    async def rehire_employee(
        self,
        *,
        org_id: int,
        actor_id: int,
        employee_id: int,
        data: EmployeeRehireRequest,
    ) -> EmployeeDetailSchema:
        """Reactivate a previously exited employee, preserving history (contract §10)."""
        employee = await self._get_active_employee(org_id, employee_id)
        if employee.employment_status == EmploymentStatus.ACTIVE.value:
            raise ConflictException(
                "Employee is already active.", code="EMPLOYEE_ALREADY_ACTIVE"
            )
        async with self.transaction():
            await self._apply_status(
                employee,
                new_status=EmploymentStatus.ACTIVE,
                actor_id=actor_id,
                reason="rehire",
                effective_date=data.date_of_joining,
                extra_updates={
                    "date_of_joining": data.date_of_joining,
                    "date_of_leaving": None,
                },
            )
            await self._audit(
                org_id=org_id,
                actor_id=actor_id,
                action_type=ActionType.UPDATE,
                title="Employee rehired",
                description=f"Rehired with joining date {data.date_of_joining.isoformat()}.",
                employee=employee,
            )
        return await self._load_detail(org_id, employee_id, include_salary=False)

    # =====================================================================
    # Org assignment
    # =====================================================================
    async def assign_branch(
        self, *, org_id: int, actor_id: int, employee_id: int, branch_id: int
    ) -> EmployeeDetailSchema:
        """Reassign an employee's master branch, re-validating hierarchy consistency."""
        employee = await self._get_active_employee(org_id, employee_id)
        await self._validate_org_hierarchy(
            org_id,
            branch_id=branch_id,
            dept_id=employee.dept_id,
            designation_id=employee.designation_id,
        )
        async with self.transaction():
            await self.employees.update(employee, {"master_branch_id": branch_id})
            await self._audit(
                org_id=org_id,
                actor_id=actor_id,
                action_type=ActionType.ASSIGN,
                title="Branch assigned",
                description=f"Master branch set to {branch_id}.",
                employee=employee,
            )
        return await self._load_detail(org_id, employee_id, include_salary=False)

    async def assign_department(
        self, *, org_id: int, actor_id: int, employee_id: int, dept_id: int
    ) -> EmployeeDetailSchema:
        """Reassign an employee's department, re-validating hierarchy consistency."""
        employee = await self._get_active_employee(org_id, employee_id)
        await self._validate_org_hierarchy(
            org_id,
            branch_id=employee.master_branch_id,
            dept_id=dept_id,
            designation_id=employee.designation_id,
        )
        async with self.transaction():
            await self.employees.update(employee, {"dept_id": dept_id})
            await self._audit(
                org_id=org_id,
                actor_id=actor_id,
                action_type=ActionType.ASSIGN,
                title="Department assigned",
                description=f"Department set to {dept_id}.",
                employee=employee,
            )
        return await self._load_detail(org_id, employee_id, include_salary=False)

    async def assign_designation(
        self, *, org_id: int, actor_id: int, employee_id: int, designation_id: int
    ) -> EmployeeDetailSchema:
        """Reassign an employee's designation, re-validating hierarchy consistency."""
        employee = await self._get_active_employee(org_id, employee_id)
        await self._validate_org_hierarchy(
            org_id,
            branch_id=employee.master_branch_id,
            dept_id=employee.dept_id,
            designation_id=designation_id,
        )
        async with self.transaction():
            await self.employees.update(employee, {"designation_id": designation_id})
            await self._audit(
                org_id=org_id,
                actor_id=actor_id,
                action_type=ActionType.ASSIGN,
                title="Designation assigned",
                description=f"Designation set to {designation_id}.",
                employee=employee,
            )
        return await self._load_detail(org_id, employee_id, include_salary=False)

    async def assign_reporting_manager(
        self, *, org_id: int, actor_id: int, employee_id: int, manager_employee_id: int
    ) -> EmployeeDetailSchema:
        """Validate a reporting-manager reference for an employee.

        Cross-reference validation performed: the employee exists and is active; the
        manager is a **different** active employee in the same organisation.

        Persistence note: the approved ``employees`` schema has no
        ``reporting_manager_id`` column (and no self-referential FK), so the
        relationship cannot be stored without a schema change — which is explicitly
        out of scope. This method therefore validates the reference and raises a
        clear :class:`ValidationException` rather than silently discarding it, so the
        caller is not misled into thinking the manager was recorded.
        """
        await self._get_active_employee(org_id, employee_id)
        if manager_employee_id == employee_id:
            raise ConflictException(
                "An employee cannot report to themselves.",
                code="REPORTING_MANAGER_SELF",
            )
        manager = await self.employees.get_reporting_manager(org_id, manager_employee_id)
        if manager is None:
            raise NotFoundException(
                "Reporting manager not found in this organisation.", code="not_found"
            )
        raise ValidationException(
            "Reporting-manager assignment is not supported by the current employee "
            "schema (no reporting_manager_id column).",
            code="REPORTING_MANAGER_NOT_SUPPORTED",
        )

    # =====================================================================
    # Documents / photo
    # =====================================================================
    async def add_document(
        self,
        *,
        org_id: int,
        actor_id: int,
        employee_id: int,
        data: EmployeeDocumentCreateRequest,
    ) -> EmployeeDocumentSchema:
        """Attach a document's metadata to an employee (pre-signed upload pattern).

        Only the persisted columns of ``employee_documents`` are written; ``mime`` /
        ``expires_at`` are transport hints for object storage and have no column in
        the approved schema, so they are intentionally not stored here.
        """
        employee = await self._get_active_employee(org_id, employee_id)
        async with self.transaction():
            document = await self.documents.create(
                {
                    "employee_id": employee_id,
                    "document_type": data.document_type.value,
                    "file_url": data.file_url,
                    "original_filename": data.original_filename,
                    "file_size_bytes": data.file_size_bytes,
                    "uploaded_by": actor_id,
                }
            )
            await self._audit(
                org_id=org_id,
                actor_id=actor_id,
                action_type=ActionType.INSERT,
                title="Document uploaded",
                description=f"Uploaded {data.document_type.value} document.",
                employee=employee,
                sub_module="Documents",
            )
        return EmployeeDocumentSchema.model_validate(document)

    async def set_photo(
        self,
        *,
        org_id: int,
        actor_id: int,
        employee_id: int,
        data: EmployeePhotoUploadRequest,
    ) -> EmployeeDetailSchema:
        """Store the employee's photo metadata (``profile_photo_url``).

        The device photo-push command is asynchronous and owned by the Hardware /
        enrollment module; this service only records the storage path.
        """
        employee = await self._get_active_employee(org_id, employee_id)
        async with self.transaction():
            await self.employees.update(employee, {"profile_photo_url": data.file_url})
            await self._audit(
                org_id=org_id,
                actor_id=actor_id,
                action_type=ActionType.UPDATE,
                title="Photo updated",
                description="Updated employee profile photo.",
                employee=employee,
                sub_module="Photo",
            )
        return await self._load_detail(org_id, employee_id, include_salary=False)

    # =====================================================================
    # Internal helpers
    # =====================================================================
    async def _get_active_employee(self, org_id: int, employee_id: int) -> Employee:
        """Return the active employee or raise :class:`NotFoundException` (``not_found``)."""
        employee = await self.employees.get_active_by_id(employee_id, org_id)
        if employee is None:
            raise NotFoundException("Employee not found.", code="not_found")
        return employee

    async def _actor_name(self, org_id: int, actor_id: int) -> str:
        """Resolve the acting user's display name for the audit snapshot (best-effort)."""
        user = await self.users.get_active_by_id(actor_id, org_id)
        name = getattr(user, "name", None)
        return name if isinstance(name, str) and name else f"user #{actor_id}"

    async def _audit(
        self,
        *,
        org_id: int,
        actor_id: int,
        action_type: ActionType,
        title: str,
        description: str,
        employee: Employee,
        sub_module: str | None = None,
    ) -> None:
        """Write one audit row for a mutation (inside the caller's transaction)."""
        await self.audit.record(
            org_id=org_id,
            module=_AUDIT_MODULE,
            sub_module=sub_module,
            action_type=action_type,
            title=title,
            description=description,
            performed_by_user_id=actor_id,
            performed_by_name=await self._actor_name(org_id, actor_id),
            employee_id=getattr(employee, "employee_id", None),
            employee_name=getattr(employee, "employee_name", None),
        )

    async def _validate_org_hierarchy(
        self, org_id: int, *, branch_id: int, dept_id: int, designation_id: int
    ) -> None:
        """Ensure branch, department, and designation all exist and are active in ``org_id``.

        The approved schema models branch / department / designation as independent
        children of the organisation (no inter-FK linking designation → department →
        branch), so the enforceable consistency rule is co-membership in the same
        organisation; each leg is confirmed active here before any write. A failure
        surfaces the contract's ``org_hierarchy_mismatch`` (422) code, with the
        message identifying the offending leg.
        """
        if not await self.branches.exists_active(org_id, branch_id):
            raise ValidationException(
                "Branch does not exist or is inactive.", code="org_hierarchy_mismatch"
            )
        if not await self.departments.exists_active(org_id, dept_id):
            raise ValidationException(
                "Department does not exist or is inactive.", code="org_hierarchy_mismatch"
            )
        if not await self.designations.exists_active(org_id, designation_id):
            raise ValidationException(
                "Designation does not exist or is inactive.", code="org_hierarchy_mismatch"
            )

    async def _next_employee_code(self, org_id: int) -> str:
        """Allocate a unique ``employee_code`` (concurrency-safe, via the repository).

        Delegates to :meth:`EmployeeRepository.allocate_employee_code`, which
        serialises concurrent allocation with a transaction-scoped advisory lock so
        no two concurrent creates receive the same code. Must be called inside the
        creating transaction so the lock covers the subsequent INSERT.
        """
        return await self.employees.allocate_employee_code(
            org_id, prefix=_CODE_PREFIX, pad=_CODE_PAD
        )

    async def _apply_status(
        self,
        employee: Employee,
        *,
        new_status: EmploymentStatus,
        actor_id: int,
        reason: str | None,
        effective_date,
        extra_updates: dict | None = None,
    ) -> None:
        """Persist a status change plus its history row (caller owns the transaction)."""
        previous = employee.employment_status
        updates: dict = {"employment_status": new_status.value}
        if extra_updates:
            updates.update(extra_updates)
        await self.employees.update(employee, updates)
        await self.status_history.create(
            {
                "employee_id": employee.employee_id,
                "previous_status": previous,
                "new_status": new_status.value,
                "changed_by": actor_id,
                "reason": reason,
                "effective_date": effective_date,
            }
        )

    async def _validate_self_service_user(
        self, org_id: int, data: EmployeeCreateRequest
    ) -> None:
        """Validate that a self-service user can be created for this employee (RBAC).

        Requires a unique email (used as the login) and a unique mobile in the org.
        """
        if not data.email:
            raise ValidationException(
                "An email is required to create a self-service user.",
                code="SELF_SERVICE_EMAIL_REQUIRED",
            )
        if await self.users.email_exists(org_id, data.email):
            raise ConflictException("Email already in use.", code="USER_EMAIL_EXISTS")
        if await self.users.mobile_exists(org_id, data.mobile_country_code, data.mobile_number):
            raise ConflictException("Mobile number already in use.", code="USER_MOBILE_EXISTS")

    async def _create_self_service_user(
        self, *, org_id: int, actor_id: int, employee: Employee, data: EmployeeCreateRequest
    ) -> None:
        """Create the linked self-service user (RBAC), invite-style (no password)."""
        await self.users.create(
            {
                "org_id": org_id,
                "name": data.employee_name,
                "email": data.email,
                "mobile_country_code": data.mobile_country_code,
                "mobile_number": data.mobile_number,
                "employee_id": employee.employee_id,
                "is_super_admin": False,
                "password_hash": None,
                "created_by": actor_id,
            }
        )

    async def _load_detail(
        self, org_id: int, employee_id: int, *, include_salary: bool
    ) -> EmployeeDetailSchema:
        """Fetch the eager-loaded employee and build the detail projection."""
        employee = await self.employees.get_detail(employee_id, org_id)
        if employee is None:
            raise NotFoundException("Employee not found.", code="not_found")
        return self._build_detail(employee, include_salary=include_salary)

    @staticmethod
    def _build_detail(employee: Employee, *, include_salary: bool) -> EmployeeDetailSchema:
        """Assemble :class:`EmployeeDetailSchema` from an eager-loaded ORM instance."""
        base = EmployeeSchema.model_validate(employee)
        salary = None
        if include_salary:
            salary = EmployeeSalarySchema(
                salary_type=employee.salary_type,
                monthly_salary=employee.monthly_salary,
                payroll_group_id=employee.payroll_group_id,
            )
        permission = employee.attendance_permission
        return EmployeeDetailSchema(
            **base.model_dump(),
            branch=(
                BranchRefSchema.model_validate(employee.master_branch)
                if employee.master_branch is not None
                else None
            ),
            department=(
                DepartmentRefSchema.model_validate(employee.department)
                if employee.department is not None
                else None
            ),
            designation=(
                DesignationRefSchema.model_validate(employee.designation)
                if employee.designation is not None
                else None
            ),
            salary=salary,
            bank_details=[
                EmployeeBankDetailSchema.model_validate(row) for row in employee.bank_details
            ],
            documents=[EmployeeDocumentSchema.model_validate(row) for row in employee.documents],
            emergency_contacts=[
                EmployeeEmergencyContactSchema.model_validate(row)
                for row in employee.emergency_contacts
            ],
            references=[
                EmployeeReferenceSchema.model_validate(row) for row in employee.references
            ],
            biometrics=[
                EmployeeBiometricSchema.model_validate(row) for row in employee.biometrics
            ],
            punch_branches=[
                EmployeePunchBranchSchema.model_validate(row) for row in employee.punch_branches
            ],
            attendance_permission=(
                EmployeeAttendancePermissionSchema.model_validate(permission)
                if permission is not None
                else None
            ),
            tags=[EmployeeTagSchema.model_validate(row) for row in employee.tags],
            status_history=[
                EmployeeStatusHistorySchema.model_validate(row) for row in employee.status_history
            ],
        )


__all__ = ["EmployeeService"]
