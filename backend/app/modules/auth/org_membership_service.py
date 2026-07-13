"""Multi-Organization Membership Service — Phase 3.

:class:`OrganizationMembershipService` is the business-logic layer responsible
for *reading* membership state: listing the organizations a user belongs to,
looking up a single membership, and validating that a user holds an active
membership in a specific organization.

Design rules (consistent with the rest of the codebase):
    * **Read-only** — this service makes no writes.  Creating / deactivating
      memberships is reserved for the future admin API (Phase 4+).
    * **No direct SQL** — all queries go through repositories.
    * **Transaction-free** — read-only services do not open transactions; any
      write callers (e.g. ``OrganizationSwitchService``) own their own boundary.
    * **No FastAPI imports** — the service is dependency-injected; it must stay
      framework-agnostic.

Relationship to ``OrganizationSwitchService``
─────────────────────────────────────────────
``OrganizationMembershipService`` validates *membership* (can this user see this
org?).  ``OrganizationSwitchService`` validates *switch eligibility* (is the org
active? is the user's account active?) and produces a new access token.  The two
services are deliberately separate so each one has a single, narrow reason to change.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.exceptions import OrgMembershipNotFoundException
from app.modules.auth.repository import OrgRepository
from app.modules.auth.schemas import OrganizationSummarySchema
from app.modules.rbac.models.membership import UserOrganizationMembership
from app.modules.rbac.repository import UserOrganizationMembershipRepository
from app.shared.base.service import BaseService


class OrganizationMembershipService(BaseService):
    """Read-only facade over ``user_organization_memberships``.

    Injected into :class:`~app.modules.auth.org_switch_service.OrganizationSwitchService`
    and (in Phase 4) into the ``GET /auth/my-organizations`` router dependency.

    All public methods are pure reads — they do not start transactions.
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)
        self._memberships = UserOrganizationMembershipRepository(session)
        self._orgs = OrgRepository(session)

    # -----------------------------------------------------------------------
    # Public API
    # -----------------------------------------------------------------------

    async def get_user_memberships(
        self, user_id: int, *, active_only: bool = True
    ) -> list[UserOrganizationMembership]:
        """Return all membership rows for a user.

        ``active_only=True`` (default) is the right choice for all end-user
        flows (token issuance, org-picker UI).  ``active_only=False`` is for
        admin / audit views.
        """
        return await self._memberships.get_memberships_for_user(user_id, active_only=active_only)

    async def list_organizations(self, user_id: int) -> list[OrganizationSummarySchema]:
        """Return the summary of every active org the user belongs to.

        Joins membership rows with the ``organizations`` table so the response
        includes the org name and code needed by a UI org-picker.

        Returned list is ordered: primary org first, then remaining orgs ordered
        by ``org_id`` (deterministic for stable UI rendering).

        Returns an empty list if the user has no active memberships (should not
        happen in practice — every user has at least a home-org membership).
        """
        memberships = await self._memberships.get_memberships_for_user(
            user_id, active_only=True
        )
        if not memberships:
            return []

        # Fetch org details for every membership in a single batch query.
        # N is typically very small (< 5 orgs per user) so N+1 is acceptable
        # here; if this becomes a bottleneck the repo can add a batch join.
        results: list[OrganizationSummarySchema] = []
        for membership in sorted(memberships, key=lambda m: (not m.is_primary, m.org_id)):
            org = await self._orgs.get_active_by_id(membership.org_id)
            if org is None:
                # Membership exists but org was deactivated — skip silently.
                continue
            results.append(
                OrganizationSummarySchema(
                    org_id=org.org_id,
                    org_code=org.org_code,
                    org_name=org.org_name,
                    is_primary=membership.is_primary,
                    is_active=membership.is_active,
                )
            )
        return results

    async def get_membership(
        self, user_id: int, org_id: int
    ) -> UserOrganizationMembership:
        """Return the membership row for ``(user_id, org_id)`` or raise.

        Raises :class:`~app.modules.auth.exceptions.OrgMembershipNotFoundException`
        when the user is not a member of the org or the membership is inactive.
        The distinction between "does not exist" and "exists but inactive" is
        intentionally not surfaced to the caller for security reasons.
        """
        membership = await self._memberships.get_membership(user_id, org_id)
        if membership is None or not membership.is_active:
            raise OrgMembershipNotFoundException(
                f"No active membership found for user {user_id} in organization {org_id}.",
                code="ORG_MEMBERSHIP_NOT_FOUND",
            )
        return membership

    async def is_active_member(self, user_id: int, org_id: int) -> bool:
        """Return ``True`` iff the user holds an active membership in ``org_id``.

        Prefer :meth:`get_membership` when you need the membership row itself;
        use this method when you only need a boolean check (e.g. in guards).
        """
        return await self._memberships.is_active_member(user_id, org_id)

    async def get_org_ids(self, user_id: int) -> list[int]:
        """Return the list of active org IDs for a user.

        Used when building ``available_org_ids`` in the JWT claims.
        """
        return await self._memberships.get_org_ids_for_user(user_id, active_only=True)


__all__ = ["OrganizationMembershipService"]
