"""User Profile — data-access layer.

Deliberately owns no model of its own: it composes the existing User (RBAC),
Employee, Organization, Branch, and RightsTemplate repositories into the
read/write operations the profile module needs. **Database operations only** —
no business rules; the service owns the commit boundary (methods only flush).
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.employee.models.employee import Employee
from app.modules.employee.models.organization import Branch, Organization
from app.modules.employee.repository import EmployeeRepository
from app.modules.organization.repository import BranchRepository, OrganizationRepository
from app.modules.rbac.models.rights import RightsTemplate
from app.modules.rbac.models.user import User
from app.modules.rbac.repository import (
    RightsTemplateRepository,
    UserRepository,
    UserTemplateAssignmentRepository,
)


class ProfileRepository:
    """Read/write access for the self-service profile projection."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.users = UserRepository(session)
        self.employees = EmployeeRepository(session)
        self.organizations = OrganizationRepository(session)
        self.branches = BranchRepository(session)
        self.template_assignments = UserTemplateAssignmentRepository(session)
        self.templates = RightsTemplateRepository(session)

    # --- Reads -----------------------------------------------------------
    async def get_user(self, user_id: int, org_id: int) -> User | None:
        """Return the caller's own (non-deleted) user row."""
        return await self.users.get_active_by_id(user_id, org_id)

    async def get_organization(self, org_id: int) -> Organization | None:
        """Return the caller's organization."""
        return await self.organizations.get_active(org_id)

    async def get_branch(self, org_id: int, branch_id: int) -> Branch | None:
        """Return a branch scoped to ``org_id``."""
        return await self.branches.get_by_id_in_org(org_id, branch_id)

    async def get_employee(self, employee_id: int, org_id: int) -> Employee | None:
        """Return the linked employee, with branch/department/designation eager-loaded."""
        return await self.employees.get_detail(employee_id, org_id)

    async def get_role_name(self, user_id: int, org_id: int) -> str | None:
        """Return the display name of the user's assigned rights template, if any."""
        assignment = await self.template_assignments.get_for_user(user_id)
        if assignment is None:
            return None
        template: RightsTemplate | None = await self.templates.get_active_by_id(
            assignment.template_id, org_id
        )
        return template.name if template is not None else None

    async def mobile_exists(
        self,
        org_id: int,
        mobile_country_code: str,
        mobile_number: str,
        *,
        exclude_user_id: int | None = None,
    ) -> bool:
        """Return whether another active user already uses this mobile in ``org_id``."""
        return await self.users.mobile_exists(
            org_id, mobile_country_code, mobile_number, exclude_user_id=exclude_user_id
        )

    # --- Writes ------------------------------------------------------------
    async def update_user(self, user: User, data: dict[str, Any]) -> User:
        """Apply ``data`` to the user row and flush (commit boundary owned by the service)."""
        return await self.users.update(user, data)

    async def update_employee(self, employee: Employee, data: dict[str, Any]) -> Employee:
        """Apply ``data`` to the linked employee row and flush."""
        return await self.employees.update(employee, data)


__all__ = ["ProfileRepository"]
