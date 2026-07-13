"""Multi-Organization Switch Service — Phase 3.

:class:`OrganizationSwitchService` is the business-logic layer for changing a
user's active organization context.  It:

1. Validates that the user's *account* is active (``users.is_active``).
2. Delegates membership validation to :class:`OrganizationMembershipService`.
3. Validates that the *target organization* itself is active and not deleted.
4. Re-resolves the effective permissions (rights-template ⊕ custom overrides)
   and data scope (branch/department IDs) scoped to the target org.
5. Issues a new short-lived access token carrying:
   - ``org_id``         = target org
   - ``permissions``    = re-resolved for the target org
   - ``branch_ids``     = re-resolved for the target org
   - ``department_ids`` = re-resolved for the target org
   - ``sid``            = **unchanged** (same session / refresh token)
6. Writes an audit log entry under ``module="auth"``, ``sub_module="org_switch"``.

Architecture invariants preserved
──────────────────────────────────
* The *session* (refresh token / ``user_sessions`` row) is **never replaced**.
  The org-switch only issues a new *access* token; the session lifecycle is
  unchanged.  This means:
    - No new ``user_sessions`` row is created.
    - The existing refresh token continues to be valid.
    - Revoking the session still invalidates the switched context.
* ``users.org_id`` (home org) is **never mutated** — it is a static property
  of the user account.
* All existing RBAC guards (``ensure_same_org``, ``require_permission``) work
  correctly because they read ``org_id`` from the **new token's** claims.
* Tenant isolation is maintained — the new token's ``org_id`` is the target org,
  so all downstream repository queries automatically scope to that org.

Dependencies
────────────
``OrganizationSwitchService`` depends on:
    * :class:`~app.modules.auth.repository.AuthUserRepository`  — fetch user
    * :class:`~app.modules.auth.repository.OrgRepository`        — validate org
    * :class:`~app.modules.auth.org_membership_service.OrganizationMembershipService`
    * :class:`~app.modules.audit.service.AuditService`           — audit trail
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config.settings import settings
from app.core.exceptions.base import NotFoundException
from app.core.security.jwt import create_access_token
from app.modules.audit.constants import ActionType
from app.modules.audit.service import AuditService
from app.modules.auth.exceptions import (
    OrgInactiveException,
    OrgMembershipNotFoundException,
    OrgSwitchNotAllowedException,
)
from app.modules.auth.org_membership_service import OrganizationMembershipService
from app.modules.auth.repository import AuthUserRepository, OrgRepository
from app.modules.auth.schemas import AccessTokenResponse, OrganizationSummarySchema
from app.modules.rbac.models import RightsTemplatePermission, UserCustomPermission
from app.shared.base.service import BaseService


class OrganizationSwitchService(BaseService):
    """Business logic for switching the active organization context.

    ``session_id`` (from the JWT ``sid`` claim) is required so the new token
    maintains the link to the existing session row, which lets revoke/logout
    work correctly after a switch.

    This service is **stateless** with respect to organization context —
    every call is a fresh resolution from the database.  No in-memory cache
    is used so that permission changes (e.g. an admin revokes a role in the
    target org) are reflected on the next switch call.
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)
        self._users = AuthUserRepository(session)
        self._orgs = OrgRepository(session)
        self._memberships = OrganizationMembershipService(session)
        self._audit = AuditService(session)

    # -----------------------------------------------------------------------
    # Public API
    # -----------------------------------------------------------------------

    async def switch_organization(
        self,
        *,
        user_id: int,
        target_org_id: int,
        session_id: int,
    ) -> AccessTokenResponse:
        """Switch the calling user's active organization and return a new access token.

        Parameters
        ──────────
        user_id       : The authenticated user (from the current JWT ``sub`` claim).
        target_org_id : The ``org_id`` to switch into.
        session_id    : The numeric ``user_sessions.id`` from the current JWT ``sid``
                        claim.  Written into the new token's ``sid`` so the session
                        link is preserved.

        Returns
        ───────
        :class:`~app.modules.auth.schemas.AccessTokenResponse` — contains only
        the *new* access token.  The caller's refresh token is unchanged; they
        should continue to present the same refresh token for future refreshes.

        Raises
        ──────
        :class:`~app.modules.auth.exceptions.OrgSwitchNotAllowedException`
            When the user's account is inactive.
        :class:`~app.modules.auth.exceptions.OrgMembershipNotFoundException`
            When the user has no active membership in ``target_org_id``.
        :class:`~app.modules.auth.exceptions.OrgInactiveException`
            When the target organization is inactive or deleted.
        :class:`~app.core.exceptions.base.NotFoundException`
            When the user row cannot be found (should not happen if the JWT is
            still valid, but guards against edge cases).
        """
        # Step 1: Load the user and verify account is active.
        user = await self._users.get_active_by_id(user_id)
        if user is None:
            raise NotFoundException(
                f"User {user_id} not found.",
                code="USER_NOT_FOUND",
            )
        if not user.is_active:
            raise OrgSwitchNotAllowedException(
                "Your account is inactive. Organization switching is not available.",
                code="ORG_SWITCH_NOT_ALLOWED",
            )

        # Step 2: Verify the user holds an active membership in the target org.
        # OrgMembershipNotFoundException is raised automatically if not.
        await self._memberships.get_membership(user_id, target_org_id)

        # Step 3: Verify the target organization is active and not deleted.
        org = await self._orgs.get_active_by_id(target_org_id)
        if org is None:
            raise OrgInactiveException(
                f"Organization {target_org_id} is inactive or does not exist.",
                code="ORG_INACTIVE",
            )

        # Step 4: Resolve permissions and data scope for the target org.
        merged, branch_ids, department_ids = await self._resolve_authz(
            user_id, org_id=target_org_id
        )

        # Step 5: Issue a new access token for the target org.
        access_token = self._issue_access_token(
            user=user,
            session_id=session_id,
            org_id=target_org_id,
            merged=merged,
            branch_ids=branch_ids,
            department_ids=department_ids,
        )

        # Step 6: Audit the switch event (inside a transaction — flush only).
        async with self.transaction():
            await self._audit.record(
                org_id=target_org_id,
                module="auth",
                sub_module="org_switch",
                action_type=ActionType.UPDATE,
                title="Organization switched",
                description=(
                    f"User '{user.name}' (id={user_id}) switched active organization "
                    f"to '{org.org_name}' (org_id={target_org_id})."
                ),
                performed_by_user_id=user_id,
                performed_by_name=user.name,
            )

        return AccessTokenResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=settings.access_token_ttl,
            refresh_token=None,  # Refresh token is unchanged after a switch.
        )

    # -----------------------------------------------------------------------
    # Membership information (delegates to OrganizationMembershipService)
    # -----------------------------------------------------------------------

    async def list_user_organizations(
        self, user_id: int
    ) -> list[OrganizationSummarySchema]:
        """Return the list of organizations the user belongs to (for org-picker UIs).

        Delegates entirely to :class:`OrganizationMembershipService` and is
        provided here as a convenience so callers only need one service instance.
        """
        return await self._memberships.list_organizations(user_id)

    # -----------------------------------------------------------------------
    # Internal helpers (mirrors AuthService._resolve_authz / _issue_access_token)
    # -----------------------------------------------------------------------

    async def _resolve_authz(
        self, user_id: int, *, org_id: int
    ) -> tuple[dict[str, dict[str, bool]], list[int], list[int]]:
        """Resolve effective permissions and data scope for ``(user_id, org_id)``.

        Identical logic to ``AuthService._resolve_authz``; duplicated here so
        ``OrganizationSwitchService`` has no import dependency on ``AuthService``.
        Both call the same repository methods — no divergence risk.
        """
        template_rows = await self._users.get_template_permissions(user_id, org_id)
        custom_rows = await self._users.get_custom_permissions(user_id, org_id)
        merged = self._merge_permissions(template_rows, custom_rows)
        branch_ids = await self._users.get_branch_ids(user_id, org_id)
        department_ids = await self._users.get_department_ids(user_id, org_id)
        return merged, branch_ids, department_ids

    @staticmethod
    def _merge_permissions(
        template_rows: list[RightsTemplatePermission],
        custom_rows: list[UserCustomPermission],
    ) -> dict[str, dict[str, bool]]:
        """Merge template permissions and custom overrides into an effective map.

        Custom-permission rows WIN over template rows on conflict (per the RBAC
        contract).  The merge is idempotent and produces a flat dict:
            ``{feature_key: {can_create, can_read, can_edit, can_delete}}``.
        """
        merged: dict[str, dict[str, bool]] = {}
        for row in template_rows:
            merged[row.feature_key] = {
                "can_create": row.can_create,
                "can_read": row.can_read,
                "can_edit": row.can_edit,
                "can_delete": row.can_delete,
            }
        for row in custom_rows:
            merged[row.feature_key] = {
                "can_create": row.can_create,
                "can_read": row.can_read,
                "can_edit": row.can_edit,
                "can_delete": row.can_delete,
            }
        return merged

    @staticmethod
    def _issue_access_token(
        *,
        user: Any,
        session_id: int,
        org_id: int,
        merged: dict[str, dict[str, bool]],
        branch_ids: list[int],
        department_ids: list[int],
    ) -> str:
        """Build a new access token scoped to ``org_id``.

        ``org_id`` is passed explicitly (not read from ``user.org_id``) so the
        token targets the *switched* org, not the home org.
        """
        permissions = [{"feature_key": key, **flags} for key, flags in merged.items()]
        extra_claims: dict[str, Any] = {
            "org_id": org_id,
            "is_super_admin": user.is_super_admin,
            "is_active": user.is_active,
            "sid": str(session_id),
            "roles": ["super_admin"] if user.is_super_admin else [],
            "permissions": permissions,
            "branch_ids": branch_ids,
            "department_ids": department_ids,
        }
        return create_access_token(user.id, extra_claims=extra_claims)


__all__ = ["OrganizationSwitchService"]
