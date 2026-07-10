"""Settings Management — service layer (business logic & orchestration).

Implements every business rule defined in the approved Settings Management API Contract.
All database access is performed strictly via repositories.

Sections:
  1.  Get / View Configuration (combined view)
  2.  Organization / System Settings  (GET, PATCH, Reset)
  3.  Salary-Slip Settings            (GET, PATCH)
  4.  Feature Configuration           (View, Enable/Disable)
  5.  Settings History                (read-only, delegated to audit)
  6.  Cross-module pointer helpers    (read-only)
"""

from __future__ import annotations

import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.audit.constants import ActionType
from app.modules.audit.service import AuditService
from app.modules.rbac.repository import UserRepository
from app.modules.settings.constants import (
    ALL_FEATURE_KEYS,
    CROSS_MODULE_POINTERS,
    ORG_SETTINGS_FEATURE_KEYS,
)
from app.modules.settings.exceptions import (
    SettingsNotFoundException,
    SettingsValidationException,
    UnknownFeatureException,
)
from app.modules.settings.models import OrgSalarySlipSettings, OrgSettings
from app.modules.settings.repository import (
    OrgSalarySlipSettingsRepository,
    OrgSettingsRepository,
    SettingsCrossModuleRepository,
)
from app.shared.base.service import BaseService


class SettingsService(BaseService):
    """Settings Management business rules engine.

    Owns all business logic for:
    - org_settings (system/org/attendance/hardware configuration toggles)
    - org_salary_slip_settings (payslip brand & release configuration)
    - Feature toggle surface (fixed boolean columns)
    - Configuration history (via activity_logs audit trail)
    - Cross-module settings pointer view
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)
        self.org_settings = OrgSettingsRepository(session)
        self.salary_slip = OrgSalarySlipSettingsRepository(session)
        self.cross_module = SettingsCrossModuleRepository(session)
        self.users = UserRepository(session)
        self.audit = AuditService(session)

    # =========================================================================
    # 1. Combined Configuration View  (GET /settings)
    # =========================================================================

    async def get_configuration_view(
        self,
        org_id: int,
    ) -> dict[str, Any]:
        """Return both owned settings blocks plus read-only cross-module pointers.

        Endpoint: GET /api/v1/settings
        Permission: settings:read
        """
        org = await self.org_settings.get_by_org_id(org_id)
        slip = await self.salary_slip.get_by_org_id(org_id)

        return {
            "organization": org,
            "salary_slip": slip,
            "cross_module_pointers": CROSS_MODULE_POINTERS,
        }

    # =========================================================================
    # 2. Organization / System Settings
    # =========================================================================

    async def get_org_settings(self, org_id: int) -> OrgSettings:
        """Return the org_settings row for this organization.

        Endpoint: GET /api/v1/settings/organization
        Permission: settings:read
        Raises SettingsNotFoundException if the row has not been initialized.
        """
        settings = await self.org_settings.get_by_org_id(org_id)
        if settings is None:
            raise SettingsNotFoundException(
                "Organization settings have not been initialized for this tenant."
            )
        return settings

    async def update_org_settings(
        self,
        org_id: int,
        caller_user_id: int,
        caller_name: str,
        *,
        advance_shift_enabled: bool | None = None,
        enable_regularization: bool | None = None,
        enable_photo_punch: bool | None = None,
        device_sync_time: datetime.time | None = None,
        sync_code: str | None = None,
        pass_code: str | None = None,
    ) -> OrgSettings:
        """Patch (upsert) the org_settings row.

        Endpoint: PATCH /api/v1/settings/organization
        Permission: settings:edit

        Business rules:
        - sync_code max 50 chars; pass_code max 20 chars.
        - device_sync_time must be a valid time value.
        - updated_by is always set to the caller.
        - Upsert: creates the row if absent; updates otherwise.
        """
        # --- Validation -------------------------------------------------------
        if sync_code is not None and len(sync_code) > 50:
            raise SettingsValidationException("sync_code must not exceed 50 characters.")
        if pass_code is not None and len(pass_code) > 20:
            raise SettingsValidationException("pass_code must not exceed 20 characters.")

        existing = await self.org_settings.get_by_org_id(org_id)

        # Build update payload (only non-None fields)
        update_data: dict[str, Any] = {
            "updated_by": caller_user_id,
            "updated_at": datetime.datetime.now(datetime.timezone.utc),  # noqa: UP017
        }
        if advance_shift_enabled is not None:
            update_data["advance_shift_enabled"] = advance_shift_enabled
        if enable_regularization is not None:
            update_data["enable_regularization"] = enable_regularization
        if enable_photo_punch is not None:
            update_data["enable_photo_punch"] = enable_photo_punch
        if device_sync_time is not None:
            update_data["device_sync_time"] = device_sync_time
        if sync_code is not None:
            update_data["sync_code"] = sync_code.strip()
        if pass_code is not None:
            update_data["pass_code"] = pass_code.strip()

        async with self.transaction():
            if existing is None:
                # Upsert — create the row; required fields must be present
                if not update_data.get("sync_code"):
                    raise SettingsValidationException(
                        "sync_code is required when creating organization settings."
                    )
                if not update_data.get("pass_code"):
                    raise SettingsValidationException(
                        "pass_code is required when creating organization settings."
                    )
                update_data["org_id"] = org_id
                settings = await self.org_settings.create(update_data)
            else:
                settings = await self.org_settings.update(existing, update_data)

            await self.audit.record(
                org_id=org_id,
                module="settings",
                sub_module="organization",
                action_type=ActionType.UPDATE,
                title="Organization Settings Updated",
                description=(
                    f"Organization settings updated. Fields changed: {list(update_data.keys())}"
                ),
                performed_by_user_id=caller_user_id,
                performed_by_name=caller_name,
            )

        return settings

    async def reset_org_settings(
        self,
        org_id: int,
        caller_user_id: int,
        caller_name: str,
    ) -> OrgSettings:
        """Re-apply schema defaults to toggle/time fields only.

        Endpoint: POST /api/v1/settings/organization/reset
        Permission: settings:edit

        Business rules:
        - Only boolean toggle fields and device_sync_time are reset.
        - sync_code and pass_code are NEVER reset (required, no defaults).
        - Raises SettingsNotFoundException if no row exists.
        """
        settings = await self.org_settings.get_by_org_id(org_id)
        if settings is None:
            raise SettingsNotFoundException(
                "Organization settings have not been initialized for this tenant."
            )

        async with self.transaction():
            settings = await self.org_settings.reset_to_defaults(org_id, updated_by=caller_user_id)
            await self.audit.record(
                org_id=org_id,
                module="settings",
                sub_module="organization",
                action_type=ActionType.UPDATE,
                title="Organization Settings Reset to Defaults",
                description=(
                    "Organization settings toggle/time fields reset to defaults. "
                    "sync_code and pass_code were not modified."
                ),
                performed_by_user_id=caller_user_id,
                performed_by_name=caller_name,
            )

        return settings  # type: ignore[return-value]

    # =========================================================================
    # 3. Salary-Slip (Payslip) Settings
    # =========================================================================

    async def get_salary_slip_settings(self, org_id: int) -> OrgSalarySlipSettings:
        """Return the org_salary_slip_settings row for this organization.

        Endpoint: GET /api/v1/settings/salary-slip
        Permission: settings:read
        Raises SettingsNotFoundException if the row has not been initialized.
        """
        slip = await self.salary_slip.get_by_org_id(org_id)
        if slip is None:
            raise SettingsNotFoundException(
                "Salary slip settings have not been initialized for this tenant."
            )
        return slip

    async def update_salary_slip_settings(
        self,
        org_id: int,
        caller_user_id: int,
        caller_name: str,
        *,
        company_logo_url: str | None = None,
        company_name: str | None = None,
        company_address: str | None = None,
        company_contact: str | None = None,
        company_website_email: str | None = None,
        auto_release_payslip: bool | None = None,
        branch_wise_payslip: bool | None = None,
    ) -> OrgSalarySlipSettings:
        """Patch (upsert) the org_salary_slip_settings row.

        Endpoint: PATCH /api/v1/settings/salary-slip
        Permission: settings:edit

        Business rules:
        - company_name max 200, company_contact max 100, company_website_email max 200.
        - company_website_email validated as email if '@' is present.
        - Upsert: creates the row if absent; all required fields must be present.
        - updated_by is always set to caller.
        """
        # --- Validation -------------------------------------------------------
        if company_name is not None and len(company_name.strip()) == 0:
            raise SettingsValidationException("company_name cannot be blank.")
        if company_address is not None and len(company_address.strip()) == 0:
            raise SettingsValidationException("company_address cannot be blank.")
        if company_contact is not None and len(company_contact.strip()) == 0:
            raise SettingsValidationException("company_contact cannot be blank.")
        if company_name is not None and len(company_name) > 200:
            raise SettingsValidationException("company_name must not exceed 200 characters.")
        if company_contact is not None and len(company_contact) > 100:
            raise SettingsValidationException("company_contact must not exceed 100 characters.")
        if company_website_email is not None and len(company_website_email) > 200:
            raise SettingsValidationException(
                "company_website_email must not exceed 200 characters."
            )
        if company_website_email and "@" in company_website_email:
            from app.shared.utils.validators import is_valid_email

            if not is_valid_email(company_website_email.strip().lower()):
                raise SettingsValidationException("company_website_email is not a valid email.")

        existing = await self.salary_slip.get_by_org_id(org_id)

        # Build update payload (only non-None fields)
        update_data: dict[str, Any] = {
            "updated_by": caller_user_id,
            "updated_at": datetime.datetime.now(datetime.timezone.utc),  # noqa: UP017
        }
        if company_logo_url is not None:
            update_data["company_logo_url"] = company_logo_url
        if company_name is not None:
            update_data["company_name"] = company_name.strip()
        if company_address is not None:
            update_data["company_address"] = company_address.strip()
        if company_contact is not None:
            update_data["company_contact"] = company_contact.strip()
        if company_website_email is not None:
            update_data["company_website_email"] = company_website_email.strip().lower()
        if auto_release_payslip is not None:
            update_data["auto_release_payslip"] = auto_release_payslip
        if branch_wise_payslip is not None:
            update_data["branch_wise_payslip"] = branch_wise_payslip

        async with self.transaction():
            if existing is None:
                # Upsert — create; required fields must be present
                for required in ("company_name", "company_address", "company_contact"):
                    if not update_data.get(required):
                        raise SettingsValidationException(
                            f"{required} is required when creating salary slip settings."
                        )
                update_data["org_id"] = org_id
                slip = await self.salary_slip.create(update_data)
            else:
                slip = await self.salary_slip.update(existing, update_data)

            await self.audit.record(
                org_id=org_id,
                module="settings",
                sub_module="salary_slip",
                action_type=ActionType.UPDATE,
                title="Salary Slip Settings Updated",
                description=(
                    f"Salary slip settings updated. Fields changed: {list(update_data.keys())}"
                ),
                performed_by_user_id=caller_user_id,
                performed_by_name=caller_name,
            )

        return slip

    # =========================================================================
    # 4. Feature Configuration
    # =========================================================================

    async def get_features(self, org_id: int) -> dict[str, bool]:
        """Return the current state of all fixed boolean feature toggles.

        Endpoint: GET /api/v1/settings/features
        Permission: settings:read

        Returns a flat dict { feature_key: bool } for all five fixed keys.
        Absent rows yield False (feature disabled by default).
        """
        org = await self.org_settings.get_by_org_id(org_id)
        slip = await self.salary_slip.get_by_org_id(org_id)

        state: dict[str, bool] = {}

        # org_settings keys
        state["advance_shift_enabled"] = getattr(org, "advance_shift_enabled", False)
        state["enable_regularization"] = getattr(org, "enable_regularization", False)
        state["enable_photo_punch"] = getattr(org, "enable_photo_punch", False)

        # salary_slip keys
        state["auto_release_payslip"] = getattr(slip, "auto_release_payslip", True)
        state["branch_wise_payslip"] = getattr(slip, "branch_wise_payslip", False)

        return state

    async def set_feature(
        self,
        org_id: int,
        caller_user_id: int,
        caller_name: str,
        feature_key: str,
        enabled: bool,
    ) -> dict[str, bool]:
        """Toggle a fixed boolean feature column.

        Endpoint: PATCH /api/v1/settings/features/{feature_key}
        Permission: settings:edit

        Business rules:
        - feature_key must be in ALL_FEATURE_KEYS — raises UnknownFeatureException otherwise.
        - Updates the correct table based on which key set the feature belongs to.
        - Raises SettingsNotFoundException if the target settings row is missing.
        """
        if feature_key not in ALL_FEATURE_KEYS:
            raise UnknownFeatureException(
                f"Unknown feature key: '{feature_key}'. Valid keys are: {sorted(ALL_FEATURE_KEYS)}"
            )

        now = datetime.datetime.now(datetime.timezone.utc)  # noqa: UP017

        async with self.transaction():
            if feature_key in ORG_SETTINGS_FEATURE_KEYS:
                settings = await self.org_settings.get_by_org_id(org_id)
                if settings is None:
                    raise SettingsNotFoundException(
                        "Organization settings have not been initialized for this tenant."
                    )
                await self.org_settings.update(
                    settings,
                    {feature_key: enabled, "updated_by": caller_user_id, "updated_at": now},
                )

            else:  # SALARY_SLIP_FEATURE_KEYS
                slip = await self.salary_slip.get_by_org_id(org_id)
                if slip is None:
                    raise SettingsNotFoundException(
                        "Salary slip settings have not been initialized for this tenant."
                    )
                await self.salary_slip.update(
                    slip,
                    {feature_key: enabled, "updated_by": caller_user_id, "updated_at": now},
                )

            await self.audit.record(
                org_id=org_id,
                module="settings",
                sub_module="features",
                action_type=ActionType.UPDATE,
                title=f"Feature '{feature_key}' {'Enabled' if enabled else 'Disabled'}",
                description=(
                    f"Feature toggle '{feature_key}' set to "
                    f"{'enabled' if enabled else 'disabled'} by {caller_name}."
                ),
                performed_by_user_id=caller_user_id,
                performed_by_name=caller_name,
            )

        return await self.get_features(org_id)

    # =========================================================================
    # 5. Settings History  (read-only, delegated to audit trail)
    # =========================================================================

    async def get_settings_history(
        self,
        org_id: int,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        """Return paginated audit log entries tagged module='settings'.

        Change history is owned by the Activity Log module — no separate
        settings-version table exists (per contract §7).

        Returns a dict compatible with PaginatedResponse (items, page,
        page_size, total).
        """
        logs = await self.cross_module.get_settings_history(org_id, page=page, page_size=page_size)
        total = await self.cross_module.get_settings_history_count(org_id)
        return {
            "items": logs,
            "page": page,
            "page_size": page_size,
            "total": total,
        }

    # =========================================================================
    # 6. Cross-module pointer helpers  (read-only)
    # =========================================================================

    async def cross_module_settings_present(self, org_id: int) -> dict[str, bool]:
        """Check which cross-module settings rows exist for this org.

        Used by the service/router to enrich the configuration view with
        pointer availability flags.
        """
        return {
            "attendance": await self.cross_module.attendance_settings_exists(org_id),
            "payroll": await self.cross_module.payroll_settings_exists(org_id),
            "leave": await self.cross_module.leave_settings_exists(org_id),
        }
