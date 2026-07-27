"""User Profile — service layer.

Self-service identity: every method acts on the caller's own row — there is no
"act on another user" path here (that lives in the RBAC / employee modules).
Mutations are audited like every other module: one Activity-Log row per change,
written inside the same transaction as the mutation.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security.password import hash_password, verify_password
from app.infrastructure.storage.client import LocalStorageClient, UploadedFile, get_storage_client
from app.modules.audit.constants import ActionType
from app.modules.audit.service import AuditService
from app.modules.auth.repository import UserSessionRepository
from app.modules.employee.models.employee import Employee
from app.modules.profile.constants import AUDIT_MODULE, PROFILE_PHOTO_PREFIX
from app.modules.profile.exceptions import (
    IncorrectCurrentPasswordException,
    MobileNumberExistsException,
    NoEmployeeLinkedException,
    ProfileNotFoundException,
)
from app.modules.profile.repository import ProfileRepository
from app.modules.profile.schemas import (
    BranchSummary,
    ChangePasswordRequest,
    ChangePasswordResponse,
    EmployeeSummary,
    OrganizationSummary,
    ProfilePhotoResponse,
    ProfileSchema,
    ProfileUpdateRequest,
)
from app.modules.rbac.models.user import User
from app.shared.base.service import BaseService
from app.shared.utils.datetime import utcnow


class ProfileService(BaseService):
    """Business rules for ``GET/PUT /profile`` and ``/profile/change-password``."""

    _SUB_MODULE = "profile"

    def __init__(self, session: AsyncSession, storage: LocalStorageClient | None = None) -> None:
        super().__init__(session)
        self.profile = ProfileRepository(session)
        self.sessions = UserSessionRepository(session)
        self.audit = AuditService(session)
        self._storage = storage

    # --- GET /profile ------------------------------------------------------
    async def get_profile(self, *, user_id: int, org_id: int) -> ProfileSchema:
        """Return the caller's own identity, organization, branch, and role."""
        return await self._build_profile(user_id=user_id, org_id=org_id)

    # --- PUT /profile --------------------------------------------------------
    async def update_profile(
        self, *, user_id: int, org_id: int, data: ProfileUpdateRequest
    ) -> ProfileSchema:
        """Update the caller's mobile number. Re-checks per-org uniqueness."""
        user = await self._get_user_or_404(user_id, org_id)
        updates = data.model_dump(exclude_unset=True, exclude_none=True)
        if not updates:
            return await self._build_profile(user_id=user_id, org_id=org_id)

        new_code = updates.get("mobile_country_code", user.mobile_country_code)
        new_number = updates.get("mobile_number", user.mobile_number)
        if (new_code, new_number) != (user.mobile_country_code, user.mobile_number):
            if await self.profile.mobile_exists(
                org_id, new_code, new_number, exclude_user_id=user_id
            ):
                raise MobileNumberExistsException()

        async with self.transaction():
            await self.profile.update_user(user, updates)
            await self._audit(
                org_id=org_id,
                actor_id=user_id,
                action_type=ActionType.UPDATE,
                title="Profile updated",
                description="Updated mobile number.",
            )
        return await self._build_profile(user_id=user_id, org_id=org_id)

    # --- PUT /profile/change-password -----------------------------------------
    async def change_password(
        self,
        *,
        user_id: int,
        org_id: int,
        data: ChangePasswordRequest,
        current_session_id: int | None,
    ) -> ChangePasswordResponse:
        """Verify the current password, replace it, and log out every other session.

        A password change is a "this account may have been compromised or shared"
        signal, so every session other than the one making this request is revoked —
        an attacker holding a stolen access token is cut off as soon as the
        legitimate owner changes their password, without logging the caller
        themselves out of the device they are actively using.
        """
        user = await self._get_user_or_404(user_id, org_id)
        if not user.password_hash or not verify_password(
            data.current_password, user.password_hash
        ):
            raise IncorrectCurrentPasswordException()

        async with self.transaction():
            await self.profile.update_user(
                user, {"password_hash": hash_password(data.new_password)}
            )
            revoked_count = await self.sessions.revoke_all_for_user(
                user_id, when=utcnow(), exclude_session_id=current_session_id
            )
            await self._audit(
                org_id=org_id,
                actor_id=user_id,
                action_type=ActionType.UPDATE,
                title="Password changed",
                description=(
                    f"Changed account password and logged out {revoked_count} "
                    "other session(s)."
                ),
            )
        return ChangePasswordResponse(revoked_session_count=revoked_count)

    # --- PUT /profile/photo ----------------------------------------------------
    async def update_profile_photo(
        self, *, user_id: int, org_id: int, upload: UploadedFile
    ) -> ProfilePhotoResponse:
        """Upload and link a new profile photo (stored on the linked employee row)."""
        user = await self._get_user_or_404(user_id, org_id)
        employee = await self._get_linked_employee_or_409(user, org_id)

        storage = self._storage or get_storage_client()
        stored = await storage.save_upload(upload, prefix=PROFILE_PHOTO_PREFIX)

        async with self.transaction():
            employee = await self.profile.update_employee(
                employee, {"profile_photo_url": stored.key}
            )
            await self._audit(
                org_id=org_id,
                actor_id=user_id,
                action_type=ActionType.UPDATE,
                title="Profile photo updated",
                description="Updated profile photo.",
                employee_id=employee.employee_id,
                employee_name=employee.employee_name,
            )
        return ProfilePhotoResponse(profile_photo_url=employee.profile_photo_url)

    # --- internals -------------------------------------------------------------
    async def _get_user_or_404(self, user_id: int, org_id: int) -> User:
        user = await self.profile.get_user(user_id, org_id)
        if user is None:
            raise ProfileNotFoundException()
        return user

    async def _get_linked_employee_or_409(self, user: User, org_id: int) -> Employee:
        if user.employee_id is None:
            raise NoEmployeeLinkedException()
        employee = await self.profile.get_employee(user.employee_id, org_id)
        if employee is None:
            raise NoEmployeeLinkedException()
        return employee

    async def _build_profile(self, *, user_id: int, org_id: int) -> ProfileSchema:
        user = await self._get_user_or_404(user_id, org_id)
        organization = await self.profile.get_organization(org_id)
        if organization is None:
            raise ProfileNotFoundException()

        role_name = await self.profile.get_role_name(user_id, org_id)

        employee_summary: EmployeeSummary | None = None
        branch_summary: BranchSummary | None = None
        profile_photo_url: str | None = None

        if user.employee_id is not None:
            employee = await self.profile.get_employee(user.employee_id, org_id)
            if employee is not None:
                profile_photo_url = employee.profile_photo_url
                employee_summary = EmployeeSummary(
                    employee_id=employee.employee_id,
                    employee_code=employee.employee_code,
                    employee_name=employee.employee_name,
                    department_name=(
                        employee.department.dept_name if employee.department else None
                    ),
                    designation_name=(
                        employee.designation.designation_name if employee.designation else None
                    ),
                    date_of_joining=employee.date_of_joining,
                )
                if employee.master_branch is not None:
                    branch_summary = BranchSummary.model_validate(employee.master_branch)

        return ProfileSchema(
            user_id=user.id,
            name=user.name,
            email=user.email,
            mobile_country_code=user.mobile_country_code,
            mobile_number=user.mobile_number,
            is_super_admin=user.is_super_admin,
            is_active=user.is_active,
            role_name=role_name,
            profile_photo_url=profile_photo_url,
            last_login_at=user.last_login_at,
            created_at=user.created_at,
            organization=OrganizationSummary.model_validate(organization),
            branch=branch_summary,
            employee=employee_summary,
        )

    async def _actor_name(self, org_id: int, actor_id: int) -> str:
        user = await self.profile.get_user(actor_id, org_id)
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
        employee_id: int | None = None,
        employee_name: str | None = None,
    ) -> None:
        await self.audit.record(
            org_id=org_id,
            module=AUDIT_MODULE,
            sub_module=self._SUB_MODULE,
            action_type=action_type,
            title=title,
            description=description,
            performed_by_user_id=actor_id,
            performed_by_name=await self._actor_name(org_id, actor_id),
            employee_id=employee_id,
            employee_name=employee_name,
        )


__all__ = ["ProfileService"]
